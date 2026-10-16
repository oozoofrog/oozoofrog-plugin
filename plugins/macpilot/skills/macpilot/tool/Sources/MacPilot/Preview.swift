import AppKit
import CryptoKit
import MacPilotCore

private class FeedbackView:NSView {
    var visibleRects:[CGRect]=[]
    func clipVisible(){NSGraphicsContext.current?.cgContext.clip(to:visibleRects)}
}
private final class CursorView: FeedbackView {
    var label = ""
    var color = NSColor.systemRed
    override var isFlipped:Bool { true }
    override func draw(_ dirtyRect:NSRect) {
        clipVisible()
        let path=NSBezierPath()
        let points:[NSPoint]=[.init(x:2,y:2),.init(x:2,y:27),.init(x:8,y:21),.init(x:13,y:32),.init(x:18,y:29),.init(x:13,y:18),.init(x:22,y:18)]
        path.move(to:points[0]);for point in points.dropFirst(){path.line(to:point)};path.close()
        NSColor.black.withAlphaComponent(0.6).setStroke();path.lineWidth=4;path.lineJoinStyle = .round;path.stroke()
        color.setFill();path.fill();NSColor.white.setStroke();path.lineWidth=1.5;path.stroke()
        let badge=NSBezierPath(roundedRect:NSRect(x:23,y:23,width:154,height:19),xRadius:5,yRadius:5)
        NSColor.black.withAlphaComponent(0.75).setFill();badge.fill()
        (String(label.prefix(18)) as NSString).draw(at:NSPoint(x:28,y:24),withAttributes:[.font:NSFont.boldSystemFont(ofSize:10),.foregroundColor:NSColor.white])
    }
}

private final class FocusOutlineView:FeedbackView {
    override func draw(_ dirtyRect:NSRect) {
        clipVisible()
        let path=NSBezierPath(roundedRect:bounds.insetBy(dx:3,dy:3),xRadius:13,yRadius:13)
        NSColor.controlAccentColor.withAlphaComponent(0.2).setStroke();path.lineWidth=6;path.stroke()
        NSColor.controlAccentColor.setStroke();path.lineWidth=2;path.stroke()
    }
}

private final class DraggableImageView:NSImageView {
    var openTarget:(()->Void)?
    private var pendingOpen=false
    override func acceptsFirstMouse(for event:NSEvent?)->Bool{true}
    override var mouseDownCanMoveWindow:Bool {true}
    override func mouseDown(with event:NSEvent){
        if event.clickCount==2{pendingOpen=true}else{window?.performDrag(with:event)}
    }
    override func mouseUp(with event:NSEvent){if pendingOpen{pendingOpen=false;openTarget?()}}
}
private final class PreviewSurface:NSView {
    override func acceptsFirstMouse(for event:NSEvent?)->Bool{true}
    override var mouseDownCanMoveWindow:Bool {true}
    override func mouseDown(with event:NSEvent){window?.performDrag(with:event)}
    var hover:((Bool)->Void)?
    override func updateTrackingAreas() {
        super.updateTrackingAreas();for area in trackingAreas{removeTrackingArea(area)}
        addTrackingArea(NSTrackingArea(rect:.zero,options:[.mouseEnteredAndExited,.activeAlways,.inVisibleRect],owner:self,userInfo:nil))
    }
    override func mouseEntered(with event:NSEvent){hover?(true)}
    override func mouseExited(with event:NSEvent){hover?(false)}
}

private final class PreviewPanel: NSPanel {
    override var canBecomeKey: Bool { false }
    override var canBecomeMain: Bool { false }
}

@MainActor final class SnapshotPanel: NSObject, NSWindowDelegate, NSApplicationDelegate {
    let panel: NSPanel
    private let image = DraggableImageView(), statusLabel = NSTextField(labelWithString:"화면 연결 중")
    let store: Store
    let observation: Observation
    let owner: StateLease
    let launchSequence: String
    var sequence: String
    var timer: Timer?, capture: LiveCapture?, latest: CGImage?
    var frameCount = 0, visible = true, paused = false, stopped = false
    var error: String?, frameDate: Date?, frameHash = ""
    var tray: NSStatusItem?

    init(store:Store, observation:Observation, sequence:String) throws {
        self.store = store; self.observation = observation
        self.owner = try store.lease(".preview-owner.lock")
        self.launchSequence = sequence; self.sequence = sequence
        let width:CGFloat=380,height:CGFloat=max(160,min(360,380*observation.windowFrame.height/observation.windowFrame.width))
        let screen=NSScreen.main?.visibleFrame ?? NSRect(x:0,y:0,width:1440,height:900)
        panel = PreviewPanel(contentRect:NSRect(x:screen.maxX-width-24,y:screen.minY+24,width:width,height:height),
                        styleMask:[.borderless,.nonactivatingPanel],backing:.buffered,defer:false)
        super.init()
        panel.title = "MacPilot Preview"
        panel.isFloatingPanel = true; panel.level = .floating; panel.hidesOnDeactivate = false
        panel.isReleasedWhenClosed = false; panel.delegate = self
        panel.backgroundColor = .clear;panel.isOpaque=false;panel.hasShadow=true
        panel.isMovableByWindowBackground=false
        panel.collectionBehavior=[.fullScreenAuxiliary,.moveToActiveSpace]
        let root=PreviewSurface(frame:panel.contentView!.bounds)
        root.wantsLayer=true;root.layer?.cornerRadius=14;root.layer?.masksToBounds=true
        root.layer?.borderColor=NSColor.white.withAlphaComponent(0.3).cgColor;root.layer?.borderWidth=1
        root.layer?.backgroundColor=NSColor.black.cgColor
        panel.contentView=root
        image.frame=root.bounds;image.imageScaling = .scaleProportionallyUpOrDown;image.autoresizingMask=[.width,.height]
        root.addSubview(image)
        image.openTarget={ [weak self] in self?.activateTarget() }
        let controls=NSVisualEffectView(frame:NSRect(x:0,y:0,width:width,height:36))
        controls.material = .hudWindow;controls.blendingMode = .withinWindow;controls.autoresizingMask=[.width];controls.alphaValue=0
        let stack=NSStackView(frame:NSRect(x:8,y:4,width:width-16,height:28));stack.orientation = .horizontal;stack.spacing=8;stack.autoresizingMask=[.width]
        for (symbol,label,action) in [("arrow.up.forward.app","창 열기",#selector(activateTarget)),("pause.fill","일시정지",#selector(togglePause)),("eye.slash","숨기기",#selector(hide)),("xmark","중단",#selector(stop))] {
            let button=NSButton(image:NSImage(systemSymbolName:symbol,accessibilityDescription:label)!,target:self,action:action)
            button.bezelStyle = .inline;button.toolTip=label;stack.addArrangedSubview(button)
        }
        statusLabel.font = .systemFont(ofSize:11);stack.addArrangedSubview(statusLabel)
        controls.addSubview(stack);root.addSubview(controls)
        root.hover={inside in controls.alphaValue=inside ? 1 : 0}
        let item = NSStatusBar.system.statusItem(withLength:NSStatusItem.variableLength)
        item.button?.title = "MP"
        let menu = NSMenu()
        for (title, action) in [("대상 창 열고 프리뷰 닫기",#selector(activateTarget)),("프리뷰 표시",#selector(show)),("프리뷰 숨기기",#selector(hide)),
                                ("일시정지 / 계속",#selector(togglePause)),("커서 표시 / 숨기기",#selector(toggleOverlay)),("프리뷰 크게 / 작게",#selector(toggleSize)),("프리뷰 중단",#selector(stop))] {
            let entry = NSMenuItem(title:title,action:action,keyEquivalent:""); entry.target = self; menu.addItem(entry)
        }
        item.menu = menu; tray = item
        capture = LiveCapture(receive: { [weak self] frame in self?.receive(frame) }, failure: { [weak self] message in
            self?.error = message; self?.statusLabel.stringValue = "캡처 중단"; self?.persist()
        })
        timer = Timer.scheduledTimer(withTimeInterval:0.15,repeats:true) { [weak self] _ in
            Task { @MainActor in self?.tick() }
        }
        Task { @MainActor [weak self] in
            guard let self else { return }
            do { try await capture?.start(windowID:observation.windowID,pid:observation.pid) }
            catch { self.error = error.localizedDescription; self.persist() }
        }
        panel.orderFrontRegardless()
        persist()
    }
    func receive(_ frame:CGImage) {
        guard !paused, !stopped else { return }
        latest = frame; frameCount += 1; frameDate = Date(); error = nil
        if let png = try? Capture.png(frame) {
            frameHash = SHA256.hash(data:png).map { String(format:"%02x",$0) }.joined()
            try? store.write(png,to:store.root.appendingPathComponent("preview-frame.png"))
        }
        render(); persist()
    }
    func currentObservation() -> Observation? {
        guard ProcessIdentity.startID(pid:observation.pid) == observation.processStartID,
              let rows = CGWindowListCopyWindowInfo([.optionAll,.excludeDesktopElements],kCGNullWindowID) as? [[String:Any]],
              let row = rows.first(where: { ($0[kCGWindowNumber as String] as? UInt32) == observation.windowID
                  && ($0[kCGWindowOwnerPID as String] as? Int32) == observation.pid }),
              let bounds = row[kCGWindowBounds as String] as? [String:Double],
              let x = bounds["X"], let y = bounds["Y"], let w = bounds["Width"], let h = bounds["Height"], w > 0, h > 0 else { return nil }
        var current = observation
        current.windowFrame = Rect(CGRect(x:x,y:y,width:w,height:h))
        return current
    }
    func render() {
        guard let base = latest, let current = currentObservation() else { return }
        let pointers = (try? store.pointers(current)) ?? []
        image.image = NSImage(cgImage:base,size:NSSize(width:base.width,height:base.height))
        let age=frameDate.map { Date().timeIntervalSince($0) } ?? 0
        statusLabel.stringValue = error != nil ? "캡처 오류" : paused ? "일시정지" : age > 5 ? "프레임 갱신 대기 · \(Int(age))초" : "라이브 · 커서 \(pointers.count)개"
    }
    func tick() {
        guard !stopped else { return }
        if store.root.lastPathComponent.hasPrefix("task-") {
            guard let parent = try? Store(root:store.root.deletingLastPathComponent()),
                  let record = try? Tasks.load(String(store.root.lastPathComponent.dropFirst(5)),in:parent),
                  record.status == "active", record.deadline > Date() else { stop(); return }
        }
        if let data = try? store.read("preview-command.json"), let command = try? JSONSerialization.jsonObject(with:data) as? [String:Any],
           let next = command["sequence"] as? String, next != sequence {
            sequence = next
            switch command["operation"] as? String {
            case "hide": hide()
            case "show": show()
            case "pause": setPaused(true)
            case "resume": setPaused(false)
            case "overlay": toggleOverlay()
            case "stop": stop(); return
            default: break
            }
        }
        guard currentObservation() != nil else {
            error = "대상 프로세스 또는 창이 종료됐습니다"; statusLabel.stringValue = "대상 연결 끊김"
            persist(); return
        }
        render(); persist()
    }
    func persist() {
        let state:[String:Any] = ["status":stopped ? "stopped" : (error == nil ? "running" : "failed"),
            "pid":getpid(), "processStartID":ProcessIdentity.startID(pid:getpid()) ?? "", "sequence":sequence,
            "launchSequence":launchSequence,"visible":visible,"paused":paused,"overlayEnabled":DesktopOverlayActions.status(store)["overlayEnabled"] ?? false,
            "overlayCount":DesktopOverlayActions.status(store)["overlayCount"] ?? 0,"presentation":"borderless_overlay","titlebar":false,"frameCount":frameCount,
            "frameAgeSeconds":frameDate.map { Date().timeIntervalSince($0) } ?? -1,
            "frameSHA256":frameHash,"lastFrame":frameDate.map { ISO8601DateFormatter().string(from:$0) } ?? "",
            "updatedAt":ISO8601DateFormatter().string(from:Date()),"windowID":observation.windowID,
            "error":error ?? "", "screenshot":store.root.appendingPathComponent("preview-frame.png").path]
        if let data = try? jsonData(state) { try? store.write(data,to:store.root.appendingPathComponent("preview-status.json")) }
    }
    @objc func activateTarget() {
        guard !stopped else{return}
        Task { @MainActor [weak self] in
            guard let self else{return}
            do {
                let resources=try Store(root:store.root.lastPathComponent.hasPrefix("task-") ? store.root.deletingLastPathComponent() : store.root)
                let input=try resources.lease(".system-input.lock"),target=try resources.lease(".target-\(observation.pid).lock")
                defer{withExtendedLifetime((input,target)){}}
                let engine=Engine(store:store,baseStore:resources)
                let fresh=try await engine.observe(pid:observation.pid,processStartID:observation.processStartID,windowID:observation.windowID,
                    screenshot:false,maxNodes:1,maxDepth:1,privateAPI:observation.windowIdentityBackend=="_AXUIElementGetWindow")
                let result=try await WindowActions.focus(fresh,node:nil,timeoutMilliseconds:2000)
                guard result["status"] as? String=="focus_verified" else{throw ToolFailure("focus_unverified","대상 창의 전경 상태를 확인하지 못했습니다")}
                try store.write(jsonData(result),to:store.root.appendingPathComponent("preview-open-result.json"))
                stop()
            } catch {
                self.error=error.localizedDescription;statusLabel.stringValue="창 열기 실패";statusLabel.toolTip=error.localizedDescription;persist()
            }
        }
    }
    @objc func hide() { visible = false; panel.orderOut(nil); persist() }
    @objc func show() { visible = true; panel.orderFrontRegardless(); render(); persist() }
    func setPaused(_ value:Bool) {
        guard paused != value else { return }
        paused = value; render(); persist()
        Task { @MainActor [weak self] in
            guard let self else { return }
            await capture?.stop()
            if !paused && !stopped {
                do { try await capture?.start(windowID:observation.windowID,pid:observation.pid) }
                catch { self.error = error.localizedDescription; persist() }
            }
        }
    }
    @objc func togglePause() { setPaused(!paused) }
    @objc func toggleOverlay() {
        Task { @MainActor in _ = try? await DesktopOverlayActions.control(store,enabled:DesktopOverlayActions.status(store)["overlayEnabled"] as? Bool != true) }
    }
    @objc func toggleSize() {
        let width:CGFloat=panel.frame.width < 500 ? 600 : 380
        let height=max(160,min(480,width*observation.windowFrame.height/observation.windowFrame.width))
        panel.setFrame(NSRect(x:panel.frame.maxX-width,y:panel.frame.minY,width:width,height:height),display:true)
    }
    @objc func stop() {
        guard !stopped else { return }
        stopped = true; timer?.invalidate(); hide(); persist()
        if let tray { NSStatusBar.system.removeStatusItem(tray) }
        Task { @MainActor [capture] in await capture?.stop(); NSApplication.shared.terminate(nil) }
    }
    func windowShouldClose(_ sender:NSWindow) -> Bool { hide(); return false }
    func applicationWillFinishLaunching(_ notification:Notification) { NSApplication.shared.setActivationPolicy(.prohibited) }
    func applicationDidFinishLaunching(_ notification:Notification) {
        NSApplication.shared.setActivationPolicy(.accessory)
        if visible { panel.orderFrontRegardless() }
    }
    static func run(store:Store,id:String,sequence:String = UUID().uuidString.lowercased()) throws {
        let observation = try store.load(id)
        try ProcessIdentity.require(pid:observation.pid,expected:observation.processStartID)
        let preview = try SnapshotPanel(store:store,observation:observation,sequence:sequence)
        NSApplication.shared.delegate = preview
        withExtendedLifetime(preview) { NSApplication.shared.run() }
    }
}

@MainActor final class DesktopOverlay:NSObject,NSApplicationDelegate {
    let store:Store,owner:StateLease
    let outline=NSPanel(contentRect:.zero,styleMask:[.borderless,.nonactivatingPanel],backing:.buffered,defer:false)
    var cursors:[String:NSPanel]=[:],timer:Timer?,animationTimer:Timer?
    var positions:[String:CGPoint]=[:],motions:[String:(path:CursorTrajectory,started:Double)]=[:],destinations:[String:CGPoint]=[:]
    var feedbackRegions:[CGRect]=[],feedbackVisible=false
    var enabled=true,stopped=false,sequence="",observationID="",highlightVisible=false
    var targetWindowID:UInt32=0,regionCount=0,targetSequence=""
    init(store:Store) throws {
        self.store=store;owner=try store.lease(".overlay-owner.lock");super.init()
        outline.contentView=FocusOutlineView(frame:.zero);configure(outline)
        timer=Timer.scheduledTimer(withTimeInterval:0.08,repeats:true){[weak self] _ in Task{@MainActor in self?.tick()}}
        animationTimer=Timer.scheduledTimer(withTimeInterval:1.0/60,repeats:true){[weak self] _ in Task{@MainActor in self?.animate()}}
        tick()
    }
    func configure(_ panel:NSPanel) {
        panel.title="MacPilot Desktop Feedback"
        panel.backgroundColor = .clear;panel.isOpaque=false;panel.hasShadow=false
        panel.ignoresMouseEvents=true;panel.level = .normal
        panel.collectionBehavior=[.canJoinAllSpaces,.fullScreenAuxiliary]
    }
    func tick() {
        guard !stopped else{return}
        if store.root.lastPathComponent.hasPrefix("task-") {
            guard let parent=try? Store(root:store.root.deletingLastPathComponent()),
                  let task=try? Tasks.load(String(store.root.lastPathComponent.dropFirst(5)),in:parent),
                  task.status=="active",task.deadline>Date() else{stop();return}
        }
        if let data=try? store.read("overlay-command.json"),let command=try? JSONSerialization.jsonObject(with:data) as? [String:Any],
           let next=command["sequence"] as? String,next != sequence {
            sequence=next;enabled=command["enabled"] as? Bool ?? true
        }
        guard let data=try? store.read("overlay-target.json"),let target=try? JSONSerialization.jsonObject(with:data) as? [String:Any],
              let id=target["observation"] as? String,let o=try? store.load(id),
              ProcessIdentity.startID(pid:o.pid)==o.processStartID else{stop();return}
        observationID=id;targetWindowID=o.windowID;targetSequence=target["targetSequence"] as? String ?? ""
        let rows=CGWindowListCopyWindowInfo([.optionAll,.excludeDesktopElements],kCGNullWindowID) as? [[String:Any]] ?? []
        guard let row=rows.first(where:{($0[kCGWindowNumber as String] as? UInt32)==o.windowID && ($0[kCGWindowOwnerPID as String] as? Int32)==o.pid}),
              let bounds=row[kCGWindowBounds as String] as? [String:Any],let frame=CGRect(dictionaryRepresentation:bounds as CFDictionary) else{stop();return}
        let above=CGWindowListCopyWindowInfo([.optionOnScreenAboveWindow,.excludeDesktopElements],o.windowID) as? [[String:Any]] ?? []
        let occluders=above.compactMap { item -> CGRect? in
            // Dock owns a transparent, screen-sized input surface whose alpha is 1.
            // Its bounding box is not opaque content. Window ordering still keeps
            // feedback below the actual Dock pixels.
            if let pid=item[kCGWindowOwnerPID as String] as? Int32,
               NSRunningApplication(processIdentifier:pid)?.bundleIdentifier=="com.apple.dock" { return nil }
            guard (item[kCGWindowOwnerPID as String] as? Int32) != getpid(),
                  item[kCGWindowName as String] as? String != "MacPilot Desktop Feedback",
                  (item[kCGWindowAlpha as String] as? Double ?? 1)>0.01,
                  let bounds=item[kCGWindowBounds as String] as? [String:Any] else{return nil}
            return CGRect(dictionaryRepresentation:bounds as CFDictionary)
        }
        let regions=Geometry.visiblePortions(of:frame,behind:occluders)
        regionCount=regions.count;feedbackRegions=regions
        let visible=enabled && !regions.isEmpty && (row[kCGWindowIsOnscreen as String] as? Bool == true)
        feedbackVisible=visible
        let top=CGDisplayBounds(CGMainDisplayID()).height
        let nsFrame=NSRect(x:frame.minX,y:top-frame.maxY,width:frame.width,height:frame.height)
        outline.setFrame(nsFrame,display:true);outline.contentView?.frame=NSRect(origin:.zero,size:nsFrame.size)
        if let view=outline.contentView as? FocusOutlineView {
            view.visibleRects=regions.map{CGRect(x:$0.minX-frame.minX,y:frame.maxY-$0.maxY,width:$0.width,height:$0.height)}
            view.needsDisplay=true
        }
        let activity=target["activityAt"] as? Double ?? 0
        let audit=(try? FileManager.default.attributesOfItem(atPath:store.root.appendingPathComponent("audit.jsonl").path)[.modificationDate] as? Date)?.timeIntervalSince1970 ?? 0
        let age=Date().timeIntervalSince1970-max(activity,audit)
        outline.alphaValue=age<0.7 ? 1 : 0.6
        highlightVisible=visible
        if visible{outline.order(.above,relativeTo:Int(o.windowID))}else{outline.orderOut(nil)}
        var current=o;current.windowFrame=Rect(frame)
        let pointers=(try? store.pointers(current)) ?? []
        let active=Set(pointers.map{$0.cursorID ?? "primary"})
        for key in Array(cursors.keys) where !active.contains(key){
            cursors.removeValue(forKey:key)?.orderOut(nil);positions.removeValue(forKey:key);motions.removeValue(forKey:key);destinations.removeValue(forKey:key)
        }
        for (index,pointer) in pointers.enumerated() {
            let key=pointer.cursorID ?? "primary"
            let panel:NSPanel
            if let old=cursors[key]{panel=old}else{
                panel=NSPanel(contentRect:NSRect(x:0,y:0,width:184,height:45),styleMask:[.borderless,.nonactivatingPanel],backing:.buffered,defer:false)
                configure(panel)
                let view=CursorView(frame:panel.contentView!.bounds)
                view.color=key=="blue" ? .systemBlue : key=="red" ? .systemRed : index.isMultiple(of:2) ? .systemPurple : .systemTeal
                panel.contentView=view;cursors[key]=panel
            }
            let destination=CGPoint(x:pointer.x,y:pointer.y)
            if let previous=positions[key],destinations[key] != destination {
                motions[key]=(CursorTrajectory(from:previous,to:destination,bounds:frame),ProcessInfo.processInfo.systemUptime)
            } else if positions[key]==nil {positions[key]=destination}
            destinations[key]=destination
            if let view=panel.contentView as? CursorView{view.label=pointer.label ?? "작업 위치"}
        }
        animate()
        persist(count:cursors.values.filter{$0.isVisible}.count)
    }
    func animate() {
        guard !stopped else{return}
        let now=ProcessInfo.processInfo.systemUptime,top=CGDisplayBounds(CGMainDisplayID()).height
        for (key,panel) in cursors {
            if let motion=motions[key] {
                positions[key]=motion.path.position(elapsed:now-motion.started)
                if now-motion.started>=motion.path.duration{motions.removeValue(forKey:key)}
            }
            guard let point=positions[key] else{continue}
            panel.setFrameOrigin(NSPoint(x:point.x-2,y:top-point.y-43))
            if let view=panel.contentView as? CursorView {
                view.visibleRects=feedbackRegions.map{CGRect(x:$0.minX-point.x+2,y:$0.minY-point.y+2,width:$0.width,height:$0.height)}
                view.needsDisplay=true
            }
            if feedbackVisible && feedbackRegions.contains(where:{$0.contains(point)}) {panel.order(.above,relativeTo:outline.windowNumber)}else{panel.orderOut(nil)}
        }
    }
    func persist(count:Int) {
        let result:[String:Any]=["status":stopped ? "stopped":"running","pid":getpid(),"processStartID":ProcessIdentity.startID(pid:getpid()) ?? "",
                                "sequence":sequence,"observation":observationID,"targetSequence":targetSequence,"overlayEnabled":enabled,"overlayCount":count,
                                "highlightVisible":highlightVisible,"targetWindowID":targetWindowID,"motionRule":"cubic_bezier_minimum_jerk","animationCount":motions.count,"positions":positions.mapValues{["x":$0.x,"y":$0.y]},"visibleRegionCount":regionCount,"outlineWindowID":outline.windowNumber,"cursorStyle":"arrow","cursorSurface":"desktop","labelKind":"action_or_target","updatedAt":Date().timeIntervalSince1970]
        if let data=try? jsonData(result){try? store.write(data,to:store.root.appendingPathComponent("overlay-status.json"))}
    }
    func stop() {
        stopped=true;timer?.invalidate();animationTimer?.invalidate();outline.orderOut(nil);cursors.values.forEach{$0.orderOut(nil)};highlightVisible=false;persist(count:0)
        NSApplication.shared.terminate(nil)
    }
    static func run(store:Store) throws {
        let controller=try DesktopOverlay(store:store);NSApplication.shared.delegate=controller
        withExtendedLifetime(controller){NSApplication.shared.run()}
    }
}
