import AppKit

private final class ToolboxTestLCD: NSView {
    override var acceptsFirstResponder: Bool { true }
}

@main
struct SimulatorToolboxSelfcheck {
    static func descendants(_ view: NSView) -> [NSView] { [view] + view.subviews.flatMap(descendants) }

    static func pump(_ seconds: Double, sample: () -> Void = {}) {
        let deadline = Date(timeIntervalSinceNow: seconds)
        while Date() < deadline {
            CATransaction.flush()
            RunLoop.current.run(until: min(deadline, Date(timeIntervalSinceNow: 1.0 / 240)))
            sample()
        }
    }

    static func near(_ a: CGRect, _ b: CGRect, tolerance: CGFloat = 0.001) -> Bool {
        abs(a.minX - b.minX) < tolerance && abs(a.minY - b.minY) < tolerance &&
        abs(a.width - b.width) < tolerance && abs(a.height - b.height) < tolerance
    }

    static func checkGeometry() {
        for bezel: CGFloat in [12, 17, 20] {
            for portrait in [CGSize(width: 162, height: 197), CGSize(width: 211, height: 257),
                             CGSize(width: 320, height: 568), CGSize(width: 430, height: 932),
                             CGSize(width: 466, height: 678), CGSize(width: 768, height: 1024), CGSize(width: 1376, height: 1032)] {
                for screen in [portrait, CGSize(width: portrait.height, height: portrait.width)] {
                    for size in [CGSize(width: 460, height: 360), CGSize(width: 600, height: 376),
                                 CGSize(width: 900, height: 700), CGSize(width: 1440, height: 900)] {
                        for open in [true, false] {
                            let geometry = simulatorDeviceLayout(in: size, screen: screen, bezel: bezel, toolsVisible: open)
                            assert(near(geometry.body, simulatorDeviceLayout(in: size, screen: screen, bezel: bezel, toolsVisible: open).body))
                            let viewport = CGRect(origin: .zero, size: size)
                            assert(viewport.contains(geometry.body) && geometry.body.contains(geometry.lcd))
                            assert(abs(geometry.body.maxY - (size.height - 16)) < 0.001)
                            assert(abs(geometry.lcd.width / geometry.lcd.height - screen.width / screen.height) < 0.001)
                            if open { assert(viewport.contains(geometry.tools) && !geometry.body.intersects(geometry.tools)) }
                            let localLCD = geometry.lcd.offsetBy(dx: -geometry.tools.minX, dy: -geometry.tools.minY)
                            for expanded in [true, false] {
                                var frames: [CGRect] = []
                                for row in 0..<8 {
                                    let columns = [0, 2, 6].contains(row) ? 3 : 2
                                    for column in 0..<columns {
                                        let frame = simulatorToolboxFrame(row: row, column: column, columns: columns, span: 1,
                                                                          in: geometry.tools.size, lcd: localLCD, expanded: expanded)
                                        assert(frame.width > 0 && frame.height > 0)
                                        if expanded { assert(CGRect(origin: .zero, size: geometry.tools.size).contains(frame)) }
                                        else {
                                            assert(frame.maxX <= min(0, localLCD.maxX) - 2 * simulatorToolboxRim + 0.001)
                                            assert(frame.minY >= localLCD.minY && frame.maxY <= localLCD.maxY)
                                            assert(frame.insetBy(dx: -simulatorToolboxRim, dy: -simulatorToolboxRim)
                                                .intersection(CGRect(origin: .zero, size: geometry.tools.size)).isEmpty)
                                        }
                                        if column > 0 { assert(frame.minX > frames.last!.maxX) }
                                        for other in frames { assert(!frame.intersects(other)) }
                                        frames.append(frame)
                                    }
                                }
                            }
                        }
                    }
                    for height: CGFloat in [160, 240, 320, 420, 576, 800] {
                        let original = CGRect(origin: .zero, size: CGSize(width: height * screen.width / screen.height, height: height))
                        var lcd = original
                        for _ in 0..<50 {
                            for open in [true, false] {
                                let envelope = simulatorLCDContentSize(forLCD: lcd.size, bezel: bezel, toolsVisible: open)
                                let geometry = simulatorDeviceLayout(in: envelope, screen: screen, bezel: bezel, toolsVisible: open)
                                lcd = CGRect(origin: .zero, size: geometry.lcd.size)
                                assert(near(lcd, original, tolerance: 0.000001), "Toggle fitting must not accumulate LCD scale changes")
                                assert(abs(geometry.body.minX - 16) < 0.001 && abs(envelope.height - geometry.body.maxY - 16) < 0.001)
                                let tools = simulatorToolboxSize(forLCD: lcd.size, bezel: bezel)
                                assert(tools.width >= 280 && tools.width <= 360 && tools.height >= 344 && tools.height <= 576)
                            }
                        }
                    }
                }
            }
        }
        let watch = simulatorToolboxSize(forLCD: CGSize(width: 420 * 211 / 257, height: 420), bezel: 20)
        assert(watch.height == 460 && watch.width < 360)
        print("PASS toolbox geometry: Watch/phone/tablet, both orientations, bounded ordered endpoints and rim clearance, adaptive compact sizes, 50 toggle cycles without LCD scale/anchor drift.")
    }

    static func checkTransitions(isWatch: Bool, screen: CGSize, size: CGSize) {
        let motions = (0..<8).flatMap { row in (0..<3).map { SimulatorToolboxMotion(row: row, column: $0) } }
        assert(motions.allSatisfy { (0...0.060001).contains($0.delay) && (0.44...0.520001).contains($0.duration) && (0.04...0.080001).contains($0.bounce) })
        assert(Set(motions.map(\.delay)).count == 7 && Set(motions.map(\.duration)).count == 5)

        let fixture = "\(isWatch ? "Watch" : "Phone") \(Int(size.width))×\(Int(size.height))"
        let box = SimulatorToolboxView(deviceName: fixture, isWatch: isWatch)
        box.updateScreen(screen, name: "Fixture", foldable: false)
        let lcd = ToolboxTestLCD(frame: CGRect(x: 0, y: 0, width: 400, height: 600))
        let content = SimulatorLCDContentView(lcd: lcd, tools: box, appearance: SimulatorDeviceAppearance(typeName: isWatch ? "Apple Watch" : "iPhone"))
        content.screen = screen
        let window = NSWindow(contentRect: CGRect(origin: .zero, size: size), styleMask: .borderless, backing: .buffered, defer: false)
        window.isReleasedWhenClosed = false
        window.contentView = content
        defer { window.close() }
        content.needsLayout = true
        content.layoutSubtreeIfNeeded()
        let glasses = box.subviews.compactMap { $0 as? SimulatorGlassView }
        let controls = glasses.flatMap { $0.content.subviews.compactMap { $0 as? NSControl } }.filter { $0.action != nil }
        let input = controls.compactMap { $0 as? NSTextField }.first { $0.placeholderString == "기기로 보낼 글자 ⏎" }!
        input.stringValue = "전환 중에도 남을 draft"
        var requests = 0
        box.onRun = { _ in requests += 1 }
        var immediate = 0
        content.animateTools(true, animated: false) { immediate += 1 }
        assert(immediate == 1 && !box.isHidden)
        assert(!box.clipsToBounds, "Resting glass rims must not be clipped")
        let targets = box.visibleGlassFrames
        assert(controls.allSatisfy { $0.isHiddenOrHasHiddenAncestor ? !$0.isEnabled : $0.isEnabled })
        assert(window.makeFirstResponder(input))
        content.animateTools(false, animated: false) { immediate += 1 }
        assert(immediate == 2 && box.isHidden && window.firstResponder === lcd)
        assert(box.clippedGlassFrames.isEmpty, "Hidden glass must not occlude another LCD")
        let closed = box.visibleGlassFrames
        for (shown, hidden) in zip(targets, closed) {
            assert(hidden.maxX <= -2 * simulatorToolboxRim + 0.001 && hidden.minX < shown.minX)
            assert(hidden.width < shown.width && hidden.height < shown.height)
        }
        assert(box.glassIsRetracted)
        assert(box.hitTest(box.frame.origin) == nil)
        assert(controls.allSatisfy { !$0.isEnabled && $0.refusesFirstResponder && $0.isAccessibilityHidden() })
        assert(glasses.allSatisfy { $0.isAccessibilityHidden() })
        let pad = controls.compactMap { $0 as? SimulatorGesturePad }.first!
        assert(!pad.accessibilityPerformPress())
        let hiddenActivity = SimulatorToolActivity(arguments: ["action": "type"], source: "에이전트")
        box.start(hiddenActivity);box.finish(hiddenActivity, response: ["content": []])
        assert(controls.allSatisfy { !$0.isEnabled })
        _ = NSApp.sendAction(input.action!, to: input.target, from: input)
        assert(requests == 0 && input.stringValue == "전환 중에도 남을 draft")
        print("PASS toolbox parameters/input: shrinking endpoints with rim clearance, 0–60ms delays/0.44–0.52s responses, immediate hide, focus, AX/action gating and drafts.")

        guard #available(macOS 15, *), !NSWorkspace.shared.accessibilityDisplayShouldReduceMotion else {
            print("SKIP native spring sampling (\(fixture)): macOS 15+ and Reduce Motion off are required.")
            return
        }
        guard CGDisplayIsAsleep(CGMainDisplayID()) == 0, CGDisplayIsActive(CGMainDisplayID()) != 0 else {
            print("SKIP native spring sampling (\(fixture)): the main display is asleep/inactive and has no animation frame clock; rerun with the display awake.")
            return
        }
        var staleOpen = 0, staleClose = 0, latest = 0
        pump(0.1)
        content.animateTools(true) { staleOpen += 1 }
        var samples: [[CGRect]] = []
        pump(0.12) { samples.append(box.visibleGlassFrames) }
        assert(samples.contains { frames in zip(frames, closed).contains { abs($0.minX - $1.minX) > 2 } }, "Native frame samples must actually move")
        assert(samples.contains { frames in zip(zip(frames, closed), targets).contains {
            $0.0.width > $0.1.width + 0.1 && $0.0.width < $1.width - 0.1 &&
            $0.0.height > $0.1.height + 0.1 && $0.0.height < $1.height - 0.1
        } }, "Native intermediate frames must grow in width and height")
        assert(samples.contains { frames in
            let distances = zip(frames, closed).map { $0.minX - $1.minX }
            return distances.max()! - distances.min()! > 4
        }, "Native components must have different progress, not one shared animation")
        let beforeClose = box.visibleGlassFrames
        box.needsLayout = true;box.layoutSubtreeIfNeeded()
        assert(box.visibleGlassFrames == beforeClose, "Layout must not reset a live spring")
        content.animateTools(false) { staleClose += 1; window.setContentSize(CGSize(width: 500, height: 700)) }
        assert(box.visibleGlassFrames == beforeClose, "Retarget must not jump to an endpoint")
        var afterClose: [CGRect] = []
        pump(0.02) { if afterClose.isEmpty && box.visibleGlassFrames != beforeClose { afterClose = box.visibleGlassFrames } }
        assert(!afterClose.isEmpty && afterClose[0].minX >= beforeClose[0].minX - 1, "First retarget sample should carry the incoming spring velocity")
        assert(afterClose[0].width >= beforeClose[0].width - 0.2 && afterClose[0].height >= beforeClose[0].height - 0.2,
               "Initial size velocity should also carry across a reversal")
        assert(controls.allSatisfy { !$0.isEnabled && $0.isAccessibilityHidden() })
        let beforeReopen = box.visibleGlassFrames
        content.animateTools(true) { latest += 1 }
        assert(box.visibleGlassFrames == beforeReopen)
        let deadline = Date(timeIntervalSinceNow: 2)
        while latest == 0 && Date() < deadline { pump(0.01) }
        pump(0.15)
        assert(staleOpen == 0 && staleClose == 0 && latest == 1, "Only the latest completion may hide or resize")
        assert(!box.isHidden && content.toolsVisible && content.bounds.width == size.width)
        assert(controls.allSatisfy { $0.isHiddenOrHasHiddenAncestor ? !$0.isEnabled && $0.isAccessibilityHidden() : $0.isEnabled && !$0.isAccessibilityHidden() })
        for (frame, target) in zip(box.visibleGlassFrames, targets) { assert(near(frame, target, tolerance: 0.1)) }
        assert(input.stringValue == "전환 중에도 남을 draft" && requests == 0)

        content.animateTools(false) { staleClose += 1 }
        pump(0.08)
        content.animateTools(true, animated: false) { immediate += 1 }
        assert(immediate == 3 && !box.isHidden && box.visibleGlassFrames == targets)
        pump(0.8)
        assert(staleClose == 0 && !box.isHidden && box.visibleGlassFrames == targets, "Immediate retarget must cancel the pending spring")
        content.animateTools(false, animated: false) {}
        assert(box.isHidden && box.visibleGlassFrames == closed)
        content.animateTools(true) { staleOpen += 1 }
        content.animateTools(false) { staleClose += 1 }
        content.animateTools(true, animated: false) { immediate += 1 }
        assert(immediate == 4 && !box.isHidden && box.visibleGlassFrames == targets)
        pump(0.8)
        assert(staleOpen == 0 && staleClose == 0 && !box.isHidden && box.visibleGlassFrames == targets, "Reversals before the first delayed tick must preserve the latest state")
        var cancelled = 0, closedCompletion = 0, reopened = 0
        content.animateTools(false, animated: false) {}
        content.animateTools(true) { cancelled += 1 }
        content.animateTools(false) { closedCompletion += 1 }
        pump(1.2)
        assert(cancelled == 0 && closedCompletion == 1 && box.isHidden && box.visibleGlassFrames == closed, "An animated reversal before the first tick must finish closed exactly once")
        content.animateTools(true, animated: false) {}
        content.animateTools(false) { cancelled += 1 }
        pump(0.01)
        content.animateTools(true) { reopened += 1 }
        pump(1.2)
        assert(cancelled == 0 && reopened == 1 && !box.isHidden && box.visibleGlassFrames == targets, "An animated reversal during the first 60ms must finish open")
        content.animateTools(false) { cancelled += 1 }
        pump(0.42)
        content.animateTools(true) { reopened += 1 }
        pump(1.2)
        assert(cancelled == 0 && reopened == 2 && !box.isHidden && box.visibleGlassFrames == targets, "Reopening near the closing completion must keep the window open")
        content.animateTools(false, animated: false) {}
        content.animateTools(true) { reopened += 1 }
        pump(0.08)
        window.setContentSize(CGSize(width: 800, height: 500))
        content.needsLayout = true;content.layoutSubtreeIfNeeded()
        box.needsLayout = true;box.layoutSubtreeIfNeeded()
        let resizedTargets = box.subviews.compactMap { $0 as? SimulatorGlassView }.map { $0.frame }
        pump(1.2)
        assert(reopened == 3 && box.visibleGlassFrames.allSatisfy { box.bounds.contains($0) }, "Completion must lay out against the latest bounds after resizing")
        assert(box.subviews.compactMap { $0 as? SimulatorGlassView }.map { $0.frame } != resizedTargets, "Resize must retarget the live frames")
        assert(controls.allSatisfy { $0.isHiddenOrHasHiddenAncestor ? !$0.isEnabled : $0.isEnabled })
        var retractedBeforeHidden = false, closeFinished = 0
        var closingSamples: [[CGRect]] = []
        let openFrames = box.visibleGlassFrames
        content.animateTools(false) {
            assert(box.glassIsRetracted && box.clippedGlassFrames.isEmpty, "Never hide/resize while any glass rim remains across the edge")
            closeFinished += 1
        }
        pump(1.2) {
            closingSamples.append(box.visibleGlassFrames)
            if !box.isHidden && box.glassIsRetracted { retractedBeforeHidden = true }
        }
        assert(closeFinished == 1 && box.isHidden && retractedBeforeHidden, "The tail must be fully clipped before the completion hides tools")
        let closedFrames = box.visibleGlassFrames
        assert(closingSamples.contains { frames in zip(zip(frames, closedFrames), openFrames).contains {
            $0.0.width > $0.1.width + 0.1 && $0.0.width < $1.width - 0.1 &&
            $0.0.height > $0.1.height + 0.1 && $0.0.height < $1.height - 0.1
        } }, "Closing must also have intermediate shrinking frames")
        print("PASS native AppKit/SwiftUI spring frame sampling (\(fixture)): x/size motion, distinct component progress, position/initial size velocity carry, early/middle/late reversals, stale completion suppression, immediate interruption, resize retargeting and fully clipped tail before hide. No onscreen glass rendering was inspected.")
    }

    static func main() throws {
        _ = NSApplication.shared
        checkGeometry()
        assert(simulatorToolboxViewRequest("WKWebView")["query"] as? String == "WKWebView")
        let customApp = simulatorToolboxViewRequest(" com.example.Probe > WKWebView ")
        assert(customApp["app"] as? String == "com.example.Probe" && customApp["query"] as? String == "WKWebView")
        for (name, family) in [("iPhone Duo", SimulatorDeviceAppearance.Family.phone), ("iPad Pro", .tablet), ("Apple Watch Ultra", .watch), ("Unknown", .other)] {
            let device = SimulatorDeviceAppearance(typeName: name)
            assert(device.family == family)
            for screen in [CGSize(width: 466, height: 678), CGSize(width: 951, height: 669), CGSize(width: 211, height: 257)] {
                for size in [CGSize(width: 900, height: 700), CGSize(width: 460, height: 360)] {
                    for open in [true, false] {
                        let layout = simulatorDeviceLayout(in: size, screen: screen, bezel: device.bezel, toolsVisible: open)
                        assert(CGRect(origin: .zero, size: size).contains(layout.body))
                        assert(layout.body.contains(layout.lcd))
                        assert(abs(size.height - layout.body.maxY - 16) < 0.001)
                        assert(abs(layout.lcd.width / layout.lcd.height - screen.width / screen.height) < 0.001)
                        if open { assert(!layout.body.intersects(layout.tools) && layout.tools.maxX <= size.width) }
                    }
                }
            }
        }
        let resources = URL(fileURLWithPath: "/Library/Developer/CoreSimulator/Profiles/DeviceTypes/iPhone Duo.simdevicetype/Contents/Resources")
        if FileManager.default.fileExists(atPath: resources.path) {
            let appearance = SimulatorDeviceAppearance(typeName: "iPhone Duo", resources: resources)
            let outer = appearance.mask(for: CGSize(width: 466, height: 678), rotation: "rot0")!
            let inner = appearance.mask(for: CGSize(width: 951, height: 669), rotation: "rot90")!
            assert(abs(outer.aspect - 466.0 / 678) < 0.001 && abs(inner.aspect - 669.0 / 951) < 0.001)
            for rotation in ["rot0", "rot90", "rot180", "rot270"] {
                assert(outer.contains(CGPoint(x: 233, y: 339), size: CGSize(width: 466, height: 678), rotation: rotation))
                assert(!outer.contains(.zero, size: CGSize(width: 466, height: 678), rotation: rotation))
            }
        }
        let box = SimulatorToolboxView(deviceName: "iPhone Duo", isWatch: false)
        box.updateScreen(CGSize(width: 466, height: 678), name: "LCD", foldable: true)
        box.layoutSubtreeIfNeeded()
        box.animateExpansion(true, animated: false) {}
        let all = descendants(box)
        func button(_ title: String) -> NSButton { all.compactMap { $0 as? NSButton }.first { $0.title == title }! }
        func field(_ placeholder: String) -> NSTextField { all.compactMap { $0 as? NSTextField }.first { $0.placeholderString == placeholder }! }
        func send(_ control: NSControl) { _ = NSApp.sendAction(control.action!, to: control.target, from: control) }
        var requests: [[String: Any]] = []
        var fail = false
        var allow = true
        var confirmations: [String] = []
        box.confirmAction = { confirmations.append($0); return allow }
        box.onRun = { request in
            requests.append(request)
            let activity = SimulatorToolActivity(arguments: request, source: "직접 조작")
            box.start(activity)
            box.finish(activity, response: ["isError": fail, "content": [["type": "text", "text": "response"]]])
        }
        for (title, name) in [("홈", "home"), ("잠금", "lock"), ("Siri", "siri")] {
            button(title).performClick(nil)
            assert(requests.last?["button"] as? String == name)
        }
        let orientation = all.compactMap { $0 as? NSPopUpButton }.first { $0.itemTitles.contains("세로") }!
        for (index, name) in ["portrait", "landscape-left", "landscape-right", "upside-down"].enumerated() {
            orientation.selectItem(at: index)
            send(orientation)
            assert(requests.last?["orientation"] as? String == name)
        }
        assert(!all.compactMap { $0 as? NSButton }.contains { ["회전", "각도 적용", "전송", "키로 입력", "누르기", "쓸기"].contains($0.title) })
        let slider = all.compactMap { $0 as? NSSlider }.first!
        slider.doubleValue = 45
        send(slider)
        assert(requests.last?["degrees"] as? Double == 45)
        let input = field("기기로 보낼 글자 ⏎")
        input.stringValue = "하이"
        fail = true
        send(input)
        let status = all.compactMap { $0 as? NSButton }.first { $0.accessibilityLabel() == "활동과 도구 응답" }!
        assert(status.title.hasPrefix("실패"))
        let recovery = status.menu!.items.first { $0.title == "같은 글자 붙여넣기…" }!
        input.stringValue = "작성 중인 새 글자"
        allow = false
        let beforeCancel = requests.count
        _ = NSApp.sendAction(recovery.action!, to: recovery.target, from: recovery)
        assert(requests.count == beforeCancel)
        allow = true; fail = false
        _ = NSApp.sendAction(recovery.action!, to: recovery.target, from: recovery)
        assert(requests.last?["action"] as? String == "paste" && requests.last?["text"] as? String == "하이")
        assert(input.stringValue == "작성 중인 새 글자")
        let key = field("키 · Return, cmd+a ⏎")
        key.stringValue = "cmd+a"; send(key)
        assert(requests.last?["key"] as? String == "cmd+a")
        for (placeholder, action) in [("화면 요소 검색 ⏎", "describe"), ("기다릴 요소 ⏎", "wait"), ("탭할 요소 ⏎", "tap"), ("접근성 실행 ⏎", "press"), ("UIView · 앱ID > 클래스 ⏎", "views")] {
            let control = field(placeholder)
            control.stringValue = "Counter";send(control)
            assert(requests.last?["action"] as? String == action)
            assert(requests.last?[["describe", "views"].contains(action) ? "query" : "target"] as? String == "Counter")
        }
        for pad in all.compactMap({ $0 as? SimulatorGesturePad }) {
            for end in [nil, CGPoint(x: 100, y: 200)] {
                pad.perform(from: CGPoint(x: 10, y: 20), to: end, seconds: 0.3)
                let frames = requests.last?["frames"] as! [[String: Any]]
                assert(frames.count == (end == nil ? 2 : 3))
                assert((frames.first!["touches"] as! [[String: Any]]).count == pad.fingers)
                assert((frames.last!["touches"] as! [[String: Any]]).allSatisfy { $0["phase"] as? String == "up" })
            }
            _ = pad.accessibilityPerformPress()
            assert(requests.last?["action"] as? String == "gesture")
        }
        let capture = all.compactMap { $0 as? NSPopUpButton }.first { $0.itemTitles.contains("가이드 캡처") }!
        for index in [1, 2] {
            capture.selectItem(at: index);send(capture)
            assert(requests.last?["guides"] as? Bool == (index == 2))
        }
        let activity = SimulatorToolActivity(arguments: ["action": "type", "text": "private text"], source: "에이전트")
        assert(!activity.summary.contains("private text"))
        box.start(activity)
        let beforeBusy = requests.count
        send(input)
        assert(requests.count == beforeBusy && input.stringValue == "작성 중인 새 글자")
        box.finish(activity, response: ["content": []])
        let image = NSImage(size: CGSize(width: 2, height: 2))
        image.lockFocus(); NSColor.blue.setFill(); NSBezierPath.fill(CGRect(x: 0, y: 0, width: 2, height: 2)); image.unlockFocus()
        let picture: [String: Any] = ["type": "image", "data": image.tiffRepresentation!.base64EncodedString()]
        for _ in 0..<2 {
            let item = SimulatorToolActivity(arguments: ["action": "screenshot"], source: "직접 조작")
            box.start(item);box.finish(item, response: ["content": [picture, picture]])
            assert(descendants(box.report.contentViewController!.view).filter { $0 is NSImageView }.count == 2)
        }
        let lcd = NSView(frame: CGRect(x: 0, y: 0, width: 400, height: 600))
        let content = SimulatorLCDContentView(lcd: lcd, tools: box, appearance: SimulatorDeviceAppearance(typeName: "iPhone"))
        content.screen = CGSize(width: 466, height: 678)
        content.frame.size = CGSize(width: 900, height: 700)
        content.animateTools(true, animated: false) {}
        for controlSize in [CGSize(width: 360, height: 576), CGSize(width: 360, height: 344), CGSize(width: 280, height: 344), CGSize(width: 220, height: 344)] {
            let size = CGSize(width: controlSize.width + simulatorToolboxGap, height: controlSize.height)
            box.frame.size = size;box.layoutSubtreeIfNeeded()
            let frames = box.visibleGlassFrames
            for (index, frame) in frames.enumerated() {
                assert(CGRect(origin: .zero, size: size).contains(frame))
                for other in frames.dropFirst(index + 1) {
                    let dx = max(0, max(frame.minX - other.maxX, other.minX - frame.maxX))
                    let dy = max(0, max(frame.minY - other.maxY, other.minY - frame.maxY))
                    assert(hypot(dx, dy) > box.glassSpacing, "Resting glass surfaces must stay separate")
                }
            }
            let hinge = box.subviews.compactMap { $0 as? SimulatorGlassView }.first { $0.content.subviews.contains { $0 is NSSlider } }!
            let track = hinge.content.subviews.first { $0 is NSSlider }!
            let label = hinge.content.subviews.first { $0 is NSTextField }!
            assert(hinge.content.bounds.contains(track.frame) && hinge.content.bounds.contains(label.frame))
            assert(!track.frame.intersects(label.frame), "Compact hinge track and caption must not overlap")
            if controlSize.width >= simulatorToolboxMinimumSize.width {
                for control in descendants(box).compactMap({ $0 as? NSControl }).filter({ !($0 is NSSlider) }) {
                    assert(control.bounds.height >= 14 && control.bounds.width >= 44, "Resting controls must retain usable native text/pad bounds")
                }
            }
            for pad in descendants(box).compactMap({ $0 as? SimulatorGesturePad }) {
                let bitmap = pad.bitmapImageRepForCachingDisplay(in: pad.bounds)!
                pad.cacheDisplay(in: pad.bounds, to: bitmap)
                var bands = 0, previousHadInk = false
                for y in 0..<bitmap.pixelsHigh {
                    let hasInk = (0..<bitmap.pixelsWide).contains { (bitmap.colorAt(x: $0, y: y)?.alphaComponent ?? 0) > 0.3 }
                    if hasInk && !previousHadInk { bands += 1 }
                    previousHadInk = hasInk
                }
                assert(bands == (size.height == 576 ? 2 : 1), "Gesture pads must render both full-size labels or one complete compact label")
            }
        }
        content.frame.size = CGSize(width: 600, height: 360)
        content.needsLayout = true;content.layoutSubtreeIfNeeded()
        if #available(macOS 26, *) {
            let container = descendants(content).compactMap { $0 as? NSGlassEffectContainerView }.first!
            assert(container.spacing == box.glassSpacing && container.spacing < 24 * 344 / 576)
        }
        let watch = SimulatorToolboxView(deviceName: "Apple Watch", isWatch: true)
        let watchViews = descendants(watch)
        assert(watchViews.compactMap { $0 as? NSButton }.contains { $0.title == "Crown 아래로" })
        assert(watchViews.compactMap { $0 as? NSSlider }.isEmpty)
        assert(watchViews.compactMap { $0 as? NSPopUpButton }.allSatisfy { !$0.itemTitles.contains("세로") })
        if #available(macOS 26, *) { assert(descendants(content).filter { $0 is NSGlassEffectContainerView }.count == 1) }
        checkTransitions(isWatch: false, screen: CGSize(width: 466, height: 678), size: CGSize(width: 900, height: 700))
        let watchLCD = CGSize(width: 420 * 211 / 257, height: 420)
        checkTransitions(isWatch: true, screen: CGSize(width: 211, height: 257),
                         size: simulatorLCDContentSize(forLCD: watchLCD, bezel: 20, toolsVisible: true))
        checkTransitions(isWatch: true, screen: CGSize(width: 211, height: 257), size: CGSize(width: 600, height: 376))
        print("LCD glass toolbox checks passed: device profiles/masks, bounded aspect-fit, one direct control per action, 1–3 finger pads, consent/recovery, drafts, images and separate capsules.")
    }
}
