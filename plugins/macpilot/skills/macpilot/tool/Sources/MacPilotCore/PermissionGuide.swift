import AppKit
import ApplicationServices
import UniformTypeIdentifiers

@MainActor final class PermissionAppDragView: NSView, NSDraggingSource {
    let applicationURL: URL
    private let icon: NSImage
    private var initial: NSEvent?
    var isDraggable = true
    var dragState: ((Bool) -> Void)?
    var didEndDrag: ((NSDragOperation) -> Void)?
    var menuProvider: (() -> NSMenu)?
    var primaryAction: (() -> Void)?
    var interactionBegan: (() -> Void)?
    init(applicationURL: URL) {
        self.applicationURL = applicationURL
        icon = NSWorkspace.shared.icon(forFile: applicationURL.path)
        super.init(frame: .zero)
        setAccessibilityElement(true)
        setAccessibilityRole(.image)
        setAccessibilityLabel("MacPilot 앱 아이콘")
        setAccessibilityIdentifier("permission.appDrag")
    }
    required init?(coder: NSCoder) { fatalError("init(coder:) has not been implemented") }
    override func acceptsFirstMouse(for event: NSEvent?) -> Bool { true }
    override func resetCursorRects() { if isDraggable { addCursorRect(bounds, cursor: .openHand) } }
    override func draw(_ dirtyRect: NSRect) { icon.draw(in: bounds.insetBy(dx: 16, dy: 16)) }
    override func menu(for event: NSEvent) -> NSMenu? { interactionBegan?(); return menuProvider?() }
    override func accessibilityPerformPress() -> Bool { interactionBegan?(); primaryAction?(); return true }
    func draggingItem(at point: NSPoint) -> NSDraggingItem {
        let item = NSDraggingItem(pasteboardWriter: applicationURL as NSURL)
        item.setDraggingFrame(NSRect(x: point.x-28, y: point.y-28, width: 56, height: 56), contents: icon)
        return item
    }
    override func mouseDown(with event: NSEvent) { interactionBegan?(); initial = event }
    override func mouseUp(with event: NSEvent) {
        if initial != nil, !isDraggable { primaryAction?() }
        initial = nil
    }
    override func mouseDragged(with event: NSEvent) {
        guard isDraggable, let down = initial, hypot(event.locationInWindow.x-down.locationInWindow.x, event.locationInWindow.y-down.locationInWindow.y) >= 4 else { return }
        initial = nil; dragState?(true)
        let session = beginDraggingSession(with: [draggingItem(at: convert(down.locationInWindow, from: nil))], event: down, source: self)
        session.animatesToStartingPositionsOnCancelOrFail = true
    }
    func draggingSession(_ session: NSDraggingSession, sourceOperationMaskFor context: NSDraggingContext) -> NSDragOperation { .copy }
    func ignoreModifierKeys(for session: NSDraggingSession) -> Bool { true }
    func draggingSession(_ session: NSDraggingSession, endedAt screenPoint: NSPoint, operation: NSDragOperation) { dragState?(false); didEndDrag?(operation) }
}

@MainActor private final class PermissionIconPanel: NSPanel {
    override var canBecomeKey: Bool { false }
    override var canBecomeMain: Bool { false }
}

/// The visible surface contains one app icon. Secondary actions live in its
/// context menu; VoiceOver receives the same actions and permission state.
@MainActor final class PermissionSetupController: NSObject, NSWindowDelegate {
    let applicationURL: URL
    let window: NSPanel
    let drag: PermissionAppDragView
    let onboarding: PermissionDragOnboarding
    private var plan: [PermissionKind]
    private var index = 0
    private var targetBundleID: String
    private var timer: Timer?
    private var busy = false
    private var dragging = false
    private var task: Task<Void, Never>?
    private var requested: Set<String> = []
    private var store: Store?
    private var targetState: PermissionState = .unknown
    private var message = ""
    private var permissionGranted: Bool?
    var kind: PermissionKind { plan[index] }

    init(applicationURL: URL, plan: [PermissionKind], targetBundleID: String) {
        self.applicationURL = applicationURL; self.plan = plan; self.targetBundleID = targetBundleID
        drag = PermissionAppDragView(applicationURL: applicationURL)
        onboarding = PermissionDragOnboarding(applicationURL: applicationURL)
        window = PermissionIconPanel(contentRect: NSRect(x: 0, y: 0, width: 88, height: 88), styleMask: [.borderless, .nonactivatingPanel], backing: .buffered, defer: false)
        super.init()
        window.title = "MacPilot 권한 안내"
        window.isReleasedWhenClosed = false; window.delegate = self
        window.hidesOnDeactivate = false; window.isFloatingPanel = false
        window.level = .normal; window.animationBehavior = .none
        window.isOpaque = false; window.backgroundColor = .clear; window.hasShadow = true
        window.isMovableByWindowBackground = false
        window.setAccessibilityElement(true)
        window.setAccessibilityRole(.window)
        window.setAccessibilitySubrole(.floatingWindow)
        let material = NSVisualEffectView(frame: NSRect(x: 0, y: 0, width: 88, height: 88))
        material.material = .popover; material.blendingMode = .behindWindow; material.state = .active
        material.wantsLayer = true; material.layer?.cornerRadius = 18; material.layer?.masksToBounds = true
        // Layer clipping alone does not mask the WindowServer backdrop material.
        // The native mask also gives the window shadow the same rounded outline.
        let mask = NSImage(size: NSSize(width: 37, height: 37), flipped: false) { rect in
            NSColor.white.setFill()
            NSBezierPath(roundedRect: rect, xRadius: 18, yRadius: 18).fill()
            return true
        }
        mask.capInsets = NSEdgeInsets(top: 18, left: 18, bottom: 18, right: 18)
        material.maskImage = mask
        window.contentView = material
        drag.frame = material.bounds; drag.autoresizingMask = [.width, .height]
        material.addSubview(drag)
        drag.interactionBegan = { [weak self] in self?.onboarding.userDidInteract() }
        drag.dragState = { [weak self] in self?.dragging = $0 }
        drag.didEndDrag = { [weak self] operation in
            self?.message = operation.isEmpty ? "드롭을 확인하지 못했습니다. 권한 목록에 다시 놓아주세요." : "드롭이 수락됐습니다. macOS에서 인증과 스위치를 확인하세요."
            self?.refresh()
        }
        drag.menuProvider = { [weak self] in self?.makeMenu() ?? NSMenu() }
        drag.primaryAction = { [weak self] in
            guard let self else { return }
            if self.kind.acceptsAppDrop { self.autoAdd() } else if self.kind == .automation { self.request() } else { self.openSettings() }
        }
        refresh()
    }
    func makeMenu() -> NSMenu {
        let menu = NSMenu()
        menu.autoenablesItems = false
        let label = NSMenuItem(title: kind.label, action: nil, keyEquivalent: ""); label.isEnabled = false; menu.addItem(label)
        func add(_ title: String, _ action: Selector, enabled: Bool = true) {
            let item = NSMenuItem(title: title, action: action, keyEquivalent: ""); item.target = self; item.isEnabled = enabled && !busy; menu.addItem(item)
        }
        if kind.acceptsAppDrop { add("자동으로 추가", #selector(autoAdd), enabled: AXIsProcessTrusted() && CGPreflightPostEventAccess()) }
        if kind.acceptsAppDrop { add("드래그 안내 다시 보기", #selector(replayOnboarding), enabled: !NSWorkspace.shared.accessibilityDisplayShouldReduceMotion) }
        if kind.systemRequest || kind == .automation { add("macOS 승인 요청", #selector(request), enabled: !requested.contains(kind.rawValue+targetBundleID)) }
        add("설정 열기", #selector(openSettings)); add("다시 확인", #selector(recheck))
        if plan.count > 1 { add("다음 권한", #selector(next), enabled: index+1 < plan.count); add("이전 권한", #selector(previous), enabled: index > 0) }
        if kind == .automation { add("대상 앱 선택…", #selector(chooseTarget)) }
        let permissions = NSMenu()
        for raw in ["all"] + PermissionKind.allCases.map(\.rawValue) {
            let item = NSMenuItem(title: raw == "all" ? "기본 권한 순서" : PermissionKind(rawValue: raw)!.label, action: #selector(selectKind(_:)), keyEquivalent: "")
            item.target = self; item.representedObject = raw; item.isEnabled = !busy
            item.state = raw == kind.rawValue ? .on : .off
            permissions.addItem(item)
        }
        let group = NSMenuItem(title: "다른 권한", action: nil, keyEquivalent: ""); group.submenu = permissions; menu.addItem(group)
        menu.addItem(.separator()); add("안내 닫기", #selector(closeGuide))
        return menu
    }
    private func resources() throws -> Store {
        if let store { return store }; let store = try Store(); self.store = store; return store
    }
    private func perform(_ operation: @escaping @MainActor () async throws -> Void) {
        guard !busy else { return }; busy = true
        task = Task { @MainActor [weak self] in
            guard let self else { return }
            defer { self.busy = false; self.dragging = false; self.refresh(); self.task = nil }
            do { try await operation() } catch { self.message = error.localizedDescription; NSSound.beep() }
        }
    }
    static func attachmentFrame(settings: CGRect, panel: CGSize, visible: CGRect) -> CGRect {
        let gap: CGFloat = 8, left = settings.minX-panel.width-8, right = settings.maxX+8
        let x = left >= visible.minX ? left : right+panel.width <= visible.maxX ? right : max(visible.minX, min(settings.minX+gap, visible.maxX-panel.width))
        return CGRect(x: x, y: max(visible.minY, min(settings.maxY-panel.height-120, visible.maxY-panel.height)), width: panel.width, height: panel.height)
    }
    private func followSettings() {
        guard !dragging else { onboarding.pause(); return }
        guard let app = NSRunningApplication.runningApplications(withBundleIdentifier: "com.apple.systempreferences").first,
              let rows = CGWindowListCopyWindowInfo([.optionOnScreenOnly, .excludeDesktopElements], kCGNullWindowID) as? [[String: Any]] else { window.orderOut(nil); onboarding.pause(); return }
        let windows = rows.filter { ($0[kCGWindowOwnerPID as String] as? NSNumber)?.int32Value == app.processIdentifier && ($0[kCGWindowLayer as String] as? Int) == 0 }.compactMap { row -> (CGRect, String)? in
            guard let bounds = row[kCGWindowBounds as String] as? [String: Any], let frame = CGRect(dictionaryRepresentation: bounds as CFDictionary), frame.width > 400, frame.height > 300 else { return nil }
            return (CGRect(x: frame.minX, y: CGDisplayBounds(CGMainDisplayID()).height-frame.maxY, width: frame.width, height: frame.height), row[kCGWindowName as String] as? String ?? "")
        }.sorted { $0.0.width*$0.0.height > $1.0.width*$1.0.height }
        guard let target = windows.first else {
            window.orderOut(nil)
            onboarding.pause()
            return
        }
        let active = NSWorkspace.shared.frontmostApplication?.processIdentifier
        guard active == app.processIdentifier || active == getpid() else { window.orderOut(nil); onboarding.pause(); return }
        let screen = NSScreen.screens.max { $0.frame.intersection(target.0).width*$0.frame.intersection(target.0).height < $1.frame.intersection(target.0).width*$1.frame.intersection(target.0).height }
        guard let screen else { onboarding.pause(); return }
        guard target.1.isEmpty || kind.titles.contains(target.1) else { window.orderOut(nil); onboarding.pause(); return }
        window.setFrame(Self.attachmentFrame(settings: target.0, panel: window.frame.size, visible: screen.visibleFrame), display: true)
        window.orderFrontRegardless()
        let hasDialog = rows.contains { row in
            guard (row[kCGWindowOwnerPID as String] as? NSNumber)?.int32Value == app.processIdentifier,
                  (row[kCGWindowLayer as String] as? Int) == 0,
                  let raw = row[kCGWindowBounds as String] as? [String: Any],
                  let frame = CGRect(dictionaryRepresentation: raw as CFDictionary) else { return false }
            let cocoa = CGRect(x: frame.minX, y: CGDisplayBounds(CGMainDisplayID()).height-frame.maxY, width: frame.width, height: frame.height)
            return frame.width > 150 && frame.height > 80 && target.0.contains(cocoa) && frame.width*frame.height < target.0.width*target.0.height*0.85
        }
        onboarding.update(source: window, settings: target.0, kind: kind, allowed: permissionGranted,
                          eligible: !busy && !hasDialog, reducedMotion: NSWorkspace.shared.accessibilityDisplayShouldReduceMotion)
    }
    func show() {
        // Public accessibility overrides expose a non-key utility panel without
        // making it steal focus from the native drop target.
        NSApplication.shared.setAccessibilityWindows([window])
        NSApplication.shared.setAccessibilityChildren([window])
        timer = Timer.scheduledTimer(withTimeInterval: 0.5, repeats: true) { [weak self] _ in Task { @MainActor in self?.refresh(); self?.followSettings() } }
        print(jsonString(["status": "permission_guide_running", "pid": getpid(), "applicationPath": applicationURL.path, "source": "attached_icon", "finderOpened": false])); fflush(stdout)
    }
    func refresh() {
        drag.isDraggable = kind.acceptsAppDrop
        let granted: Bool?
        switch kind {
        case .accessibility: granted = AXIsProcessTrusted()
        case .screenCapture: granted = CGPreflightScreenCaptureAccess()
        case .postEvent: granted = CGPreflightPostEventAccess()
        case .inputMonitoring: granted = CGPreflightListenEventAccess()
        default: granted = nil
        }
        permissionGranted = granted
        let state = granted.map { $0 ? "허용됨" : "미허용" } ?? (kind == .automation ? targetState.label : "시스템 설정에서 확인")
        drag.toolTip = "\(kind.label) · \(state)\n\(message.isEmpty ? "앱 아이콘을 권한 목록으로 드래그하세요. 우클릭하면 자동 추가와 다른 권한을 선택할 수 있습니다." : message)"
        drag.setAccessibilityHelp(drag.toolTip)
        drag.setAccessibilityValue(state)
        drag.setAccessibilityCustomActions([
            NSAccessibilityCustomAction(name: "자동으로 추가", target: self, selector: #selector(accessibleAutoAdd)),
            NSAccessibilityCustomAction(name: "드래그 안내 다시 보기", target: self, selector: #selector(accessibleReplay)),
            NSAccessibilityCustomAction(name: "다음 권한", target: self, selector: #selector(accessibleNext))
        ])
    }
    @objc private func accessibleAutoAdd() -> Bool { guard kind.acceptsAppDrop else { return false }; autoAdd(); return true }
    @objc private func accessibleReplay() -> Bool { guard kind.acceptsAppDrop, !NSWorkspace.shared.accessibilityDisplayShouldReduceMotion else { return false }; replayOnboarding(); return true }
    @objc func replayOnboarding() { onboarding.replay(); followSettings() }
    @objc private func accessibleNext() -> Bool { guard index+1 < plan.count else { return false }; next(); return true }
    @objc func openSettings() {
        perform { [self] in
            let lease = try resources().lease(".system-input.lock"); defer { withExtendedLifetime(lease) {} }
            guard NSWorkspace.shared.open(try PermissionSetup.settingsURL(for: kind.rawValue)) else { throw ToolFailure("settings_open_failed", "시스템 설정을 열지 못했습니다.") }
            try await Task.sleep(nanoseconds: 250_000_000); followSettings()
        }
    }
    @objc func selectKind(_ sender: NSMenuItem) {
        guard !busy, let raw = sender.representedObject as? String, let selected = try? PermissionKind.plan(raw) else { return }
        plan = selected; index = 0; message = ""; refresh(); openSettings()
    }
    @objc func previous() { guard !busy, index > 0 else { return }; index -= 1; message = ""; refresh(); openSettings() }
    @objc func next() { guard !busy, index+1 < plan.count else { return }; index += 1; message = ""; refresh(); openSettings() }
    @objc func recheck() {
        guard kind == .automation else { refresh(); return }
        perform { [self] in targetState = try await PermissionCenter.automation(bundleID: targetBundleID, request: false, timeout: 3000) }
    }
    @objc func chooseTarget() {
        guard !busy else { return }
        do {
            let lease = try resources().lease(".system-input.lock"); defer { withExtendedLifetime(lease) {} }
            let panel = NSOpenPanel(); panel.allowedContentTypes = [.applicationBundle]; panel.title = "Automation 대상 앱 선택"
            guard panel.runModal() == .OK, let url = panel.url, let id = Bundle(url: url)?.bundleIdentifier else { return }
            targetBundleID = id; targetState = .unknown; refresh()
        } catch { message = error.localizedDescription; refresh() }
    }
    @objc func request() {
        onboarding.userDidInteract()
        let selected = kind, target = targetBundleID
        perform { [self] in
            let lease = try resources().lease(".system-input.lock"); defer { withExtendedLifetime(lease) {} }
            guard !requested.contains(selected.rawValue+target) else { return }; requested.insert(selected.rawValue+target)
            if selected == .automation {
                guard let url = NSWorkspace.shared.urlForApplication(withBundleIdentifier: target) else { throw ToolFailure("app_not_installed", "대상 앱을 찾지 못했습니다.") }
                _ = try await NSWorkspace.shared.openApplication(at: url, configuration: NSWorkspace.OpenConfiguration())
                targetState = try await PermissionCenter.automation(bundleID: target, request: true, timeout: 60_000)
            } else if selected.systemRequest { _ = try await SystemActions.permission(Arguments(["kind": selected.rawValue])) }
            message = "macOS의 인증·재실행 안내를 직접 확인하세요."
        }
    }
    @objc func autoAdd() {
        onboarding.userDidInteract()
        let selected = kind
        guard selected.acceptsAppDrop else { return }
        perform { [self] in
            let lease = try resources().lease(".system-input.lock"); defer { withExtendedLifetime(lease) {} }
            try Input.preflight()
            guard NSWorkspace.shared.open(try PermissionSetup.settingsURL(for: selected.rawValue)) else { throw ToolFailure("settings_open_failed", "Cannot open System Settings") }
            try await Task.sleep(nanoseconds: 350_000_000); followSettings(); dragging = true
            let result = try await PermissionSetup.autoRegister(selected, source: drag, window: window, timeout: 10_000)
            switch result["status"] as? String {
            case "registered", "already_listed": message = "MacPilot 목록 등록을 확인했습니다. 인증·스위치는 macOS에서 확인하세요."
            case "restart_required": message = "macOS 재실행 안내를 직접 선택하세요."
            case "authentication_required": message = "macOS 인증 창에서 직접 승인하세요."
            case "native_confirmation_required": message = "macOS 확인 창에서 직접 선택하세요."
            default: message = "등록 결과를 확인하지 못했습니다. 목록을 확인한 뒤 직접 드래그하세요."
            }
            print(jsonString(["status": "permission_auto_add_result", "kind": selected.rawValue, "result": result])); fflush(stdout)
        }
    }
    @objc func closeGuide() { window.close() }
    func windowWillClose(_ notification: Notification) {
        onboarding.pause(); onboarding.panel.close()
        timer?.invalidate(); task?.cancel()
        NSApplication.shared.stop(nil)
        NSApplication.shared.postEvent(NSEvent.otherEvent(with: .applicationDefined, location: .zero, modifierFlags: [], timestamp: 0, windowNumber: 0, context: nil, subtype: 0, data1: 0, data2: 0)!, atStart: false)
    }
}
