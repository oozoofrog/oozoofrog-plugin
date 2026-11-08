import AppKit

/// Layout belongs to one UDID. No view, panel, or input state is shared between devices.
struct SimulatorToolbarLayout: Codable {
    var version = 1
    var attached = true
    var leftSide = false
    var toolbarFrame: CGRect?
    var deviceFrame: CGRect?
    var detached: [String: CGRect] = [:]
}

func simulatorRestoredPanelFrame(_ frame: CGRect, screens: [CGRect], fallback: CGRect) -> CGRect {
    guard frame.origin.x.isFinite, frame.origin.y.isFinite, frame.width.isFinite, frame.height.isFinite,
          frame.width >= 80, frame.height >= 40 else { return fallback }
    guard let screen = screens.max(by: { a, b in
        func score(_ rect: CGRect) -> CGFloat {
            let intersection = frame.intersection(rect)
            if !intersection.isNull { return intersection.width * intersection.height + 1 }
            return -hypot(frame.midX - rect.midX, frame.midY - rect.midY)
        }
        return score(a) < score(b)
    }) else { return fallback }
    return simulatorConstrainedFrame(frame, to: screen)
}

/// Only the two edges of this device are eligible; other devices cannot acquire its toolbar.
func simulatorToolbarSnapSide(_ toolbar: CGRect, device: CGRect, distance: CGFloat = 32) -> Bool? {
    let overlap = min(toolbar.maxY, device.maxY) - max(toolbar.minY, device.minY)
    guard overlap >= min(60, min(toolbar.height, device.height) / 2) else { return nil }
    let right = abs(toolbar.minX - device.maxX - 12)
    let left = abs(toolbar.maxX - device.minX + 12)
    if min(left, right) <= distance { return left < right }
    return nil
}

final class SimulatorToolbarPanel: NSPanel {
    override var canBecomeKey: Bool { true }
    override var canBecomeMain: Bool { false }
    init() {
        super.init(contentRect: .zero, styleMask: [.borderless, .nonactivatingPanel], backing: .buffered, defer: false)
        isReleasedWhenClosed = false
        isOpaque = false
        backgroundColor = .clear
        hasShadow = true
        hidesOnDeactivate = false
        isFloatingPanel = false
        becomesKeyOnlyIfNeeded = false // Unlike mini previews, these panels own editable controls.
        level = .normal
        isMovable = false // Our grip separates panel motion from guest input and device motion.
        collectionBehavior = [.moveToActiveSpace, .fullScreenAuxiliary]
    }
}

/// Native event tracking, without an event monitor, nested event loop, or recurring timer.
final class SimulatorToolbarGrip: NSView {
    let label = NSTextField(labelWithString: "")
    let menuButton = NSButton()
    var menuBuilder: () -> NSMenu = { NSMenu() }
    var onBegin: (CGPoint) -> Void = { _ in }
    var onDrag: (CGPoint) -> Void = { _ in }
    var onEnd: () -> Void = {}
    private var start: CGPoint?
    private var dragging = false
    init(title: String) {
        super.init(frame: .zero)
        label.stringValue = "⠿  " + title
        label.font = .systemFont(ofSize: 12, weight: .semibold)
        label.textColor = .labelColor
        label.lineBreakMode = .byTruncatingMiddle
        addSubview(label)
        menuButton.image = NSImage(systemSymbolName: "ellipsis.circle", accessibilityDescription: nil)?.withSymbolConfiguration(.init(pointSize: 18, weight: .medium))
        menuButton.isBordered = false
        menuButton.target = self; menuButton.action = #selector(openMenu)
        menuButton.setAccessibilityLabel(title + " · 배치 메뉴")
        menuButton.toolTip = "분리 · 재결합 · 기본 배치"
        addSubview(menuButton)
        setAccessibilityElement(false)
        label.setAccessibilityLabel(title + " · 드래그로 이동, 툴바 위에 놓아 재결합")
        toolTip = "손잡이 드래그로 이동 · 도킹 대상이 강조되면 놓아 결합"
    }
    required init?(coder: NSCoder) { fatalError() }
    override func layout() {
        super.layout()
        label.frame = CGRect(x: 12, y: 9, width: max(0, bounds.width - 56), height: 20)
        menuButton.frame = CGRect(x: bounds.width - 42, y: 1, width: 40, height: 36)
    }
    override func hitTest(_ point: NSPoint) -> NSView? {
        let local = convert(point, from: superview)
        guard bounds.contains(local) else { return nil }
        if menuButton.frame.contains(local) { return menuButton }
        return self // Labels never swallow the move grip.
    }
    override func resetCursorRects() { addCursorRect(bounds, cursor: .openHand) }
    override func acceptsFirstMouse(for event: NSEvent?) -> Bool { true }
    override var mouseDownCanMoveWindow: Bool { false }
    override func mouseDown(with event: NSEvent) { start = NSEvent.mouseLocation; dragging = false }
    override func mouseDragged(with event: NSEvent) {
        guard let start else { return }
        let point = NSEvent.mouseLocation
        if !dragging {
            guard hypot(point.x - start.x, point.y - start.y) >= 4 else { return }
            dragging = true
            onBegin(start)
        }
        onDrag(point)
    }
    override func mouseUp(with event: NSEvent) { cancelDrag() }
    func cancelDrag() {
        let wasDragging = dragging
        dragging = false; start = nil
        if wasDragging { onEnd() }
    }
    @objc private func openMenu() { menuBuilder().popUp(positioning: nil, at: CGPoint(x: 0, y: bounds.minY), in: self) }
}

final class SimulatorToolbarModuleView: NSView {
    let key: String
    let title: String
    let grip: SimulatorToolbarGrip
    let content: NSView
    let contentHeight: CGFloat
    private let header: SimulatorGlassView
    var totalHeight: CGFloat { contentHeight + 44 }
    init(key: String, title: String, content: NSView, height: CGFloat) {
        self.key = key; self.title = title; self.content = content; contentHeight = height
        grip = SimulatorToolbarGrip(title: title)
        header = SimulatorGlassView(content: grip)
        super.init(frame: .zero)
        header.cornerRadius = 14
        addSubview(header)
        addSubview(content)
        setAccessibilityElement(false)
        setAccessibilityLabel(title)
    }
    required init?(coder: NSCoder) { fatalError() }
    override func layout() {
        super.layout()
        header.frame = CGRect(x: 0, y: bounds.height - 38, width: bounds.width, height: 38)
        content.frame = CGRect(x: 0, y: 0, width: bounds.width, height: max(0, bounds.height - 44))
        content.layoutSubtreeIfNeeded()
    }
}

private final class SimulatorToolbarCanvas: NSView {
    var arrange: (CGRect) -> Void = { _ in }
    override func layout() { super.layout(); arrange(bounds) }
}

/// Moves the existing chrome and toolbox views into one sidebar or individual panels.
/// This coordinator has no backend queue and cannot duplicate or synthesize a simulator action.
final class SimulatorToolbarDocking: NSObject, NSWindowDelegate {
    let ownerID: String
    private let deviceName: String
    let toolbar = SimulatorToolbarPanel()
    private(set) var modules: [SimulatorToolbarModuleView] = []
    private(set) var panels: [String: SimulatorToolbarPanel] = [:]
    private(set) var placement = SimulatorToolbarLayout()
    let toolbarGrip: SimulatorToolbarGrip
    private let root = SimulatorToolbarCanvas()
    private let backdrop: SimulatorGlassView
    private let scroll = NSScrollView()
    private let document = NSView()
    private let defaults: UserDefaults
    private weak var device: NSWindow?
    private let tools: SimulatorToolboxView
    private var draggingKey: String?
    private var dragOrigin = CGPoint.zero
    private var dragStart = CGPoint.zero
    private var dockCandidate: Bool?
    private var moduleCandidate = false
    private var arranging = false
    private var suspended = true
    private var focused = false
    private var advancedVisible = false
    private var closed = false
    private var configuring = true
    var onInputCleanup: () -> Void = {}
    var onDeviceMenu: () -> NSMenu = { NSMenu() }
    var onSettings: (() -> Void)?
    var onStateChange: () -> Void = {}
    private var storageKey: String { "simulatorToolbarLayout.v1." + ownerID }
    var panelWindowNumbers: Set<Int> { Set(([toolbar] + Array(panels.values)).filter { $0.isVisible }.map(\.windowNumber)) }
    var opaqueWindowShapes: [Int: [CGRect]] {
        var shapes: [Int: [CGRect]] = [:]
        for panel in [toolbar] + Array(panels.values) where panel.isVisible {
            // Register an empty shape for translucent glass so the occlusion code never
            // falls back to the rectangular WindowServer envelope.
            guard NSWorkspace.shared.accessibilityDisplayShouldReduceTransparency else {
                shapes[panel.windowNumber] = []
                continue
            }
            if panel === toolbar { shapes[panel.windowNumber] = [panel.frame] }
            else if let module = panel.contentView as? SimulatorToolbarModuleView {
                var frames = module.subviews.filter { $0 is SimulatorGlassView }.map { panel.convertToScreen($0.convert($0.bounds, to: nil)) }
                if module.content === tools {
                    frames += tools.clippedGlassFrames.map { panel.convertToScreen(tools.convert($0, to: nil)) }
                }
                shapes[panel.windowNumber] = frames
            }
        }
        return shapes
    }

    init(ownerID: String, name: String, device: NSWindow, chrome: SimulatorDeviceChrome,
         tools: SimulatorToolboxView, defaults: UserDefaults = .standard) {
        self.ownerID = ownerID; deviceName = name
        self.device = device; self.tools = tools; self.defaults = defaults
        toolbarGrip = SimulatorToolbarGrip(title: name + " · 메인 도구")
        backdrop = SimulatorGlassView(content: root)
        super.init()
        chrome.enableFloatingModules()
        tools.removeFromSuperview()
        tools.setFloatingPresentation(false)
        modules = [
            .init(key: "information", title: "기기 정보", content: chrome.information, height: 58),
            .init(key: "basic", title: "기본 조작", content: chrome.controls, height: 64),
            .init(key: "input", title: "보조 입력", content: chrome.rail, height: 64),
            .init(key: "fold", title: "접기", content: chrome.folding, height: 130),
            .init(key: "advanced", title: "고급 도구", content: tools, height: simulatorToolboxHeight),
            .init(key: "status", title: "상태와 응답", content: chrome.activity, height: 62)
        ]
        toolbar.title = name + " · 메인 도구"
        toolbar.contentView = backdrop
        toolbar.delegate = self
        root.addSubview(toolbarGrip)
        scroll.drawsBackground = false; scroll.hasVerticalScroller = true
        scroll.documentView = document
        root.addSubview(scroll)
        root.arrange = { [weak self] in self?.arrangeRoot($0) }
        toolbarGrip.menuBuilder = { [weak self] in self?.menu() ?? NSMenu() }
        configure(grip: toolbarGrip, key: nil)
        for module in modules {
            module.grip.label.stringValue = "⠿  " + module.title + " · " + name
            module.grip.label.setAccessibilityLabel(name + " · " + module.title + " · 드래그로 분리 또는 재결합")
            module.grip.menuBuilder = { [weak self, weak module] in self?.menu(module: module?.key) ?? NSMenu() }
            configure(grip: module.grip, key: module.key)
        }
        if let data = defaults.data(forKey: storageKey), let saved = try? JSONDecoder().decode(SimulatorToolbarLayout.self, from: data), saved.version == 1 {
            placement = saved
        }
        NotificationCenter.default.addObserver(self, selector: #selector(screensChanged), name: NSApplication.didChangeScreenParametersNotification, object: nil)
        let visible = device.screen?.visibleFrame ?? NSScreen.main?.visibleFrame ?? CGRect(x: 0, y: 0, width: 1200, height: 800)
        let initial = CGRect(x: device.frame.maxX + 12, y: device.frame.maxY - min(780, visible.height - 24), width: 388, height: min(780, visible.height - 24))
        toolbar.setFrame(restored(placement.toolbarFrame ?? initial, fallback: simulatorConstrainedFrame(initial, to: visible)), display: false)
        for key in Array(placement.detached.keys) where modules.contains(where: { $0.key == key }) { detach(key, save: false) }
        rebuild()
        if placement.attached { followDevice() }
        configuring = false
        scroll.contentView.scroll(to: CGPoint(x: 0, y: max(0, document.bounds.height - scroll.contentSize.height)))
        scroll.reflectScrolledClipView(scroll.contentView)
    }
    deinit { NotificationCenter.default.removeObserver(self) }
    private var screens: [CGRect] { NSScreen.screens.map(\.visibleFrame) }
    private func restored(_ frame: CGRect, fallback: CGRect) -> CGRect { simulatorRestoredPanelFrame(frame, screens: screens, fallback: fallback) }
    private func cleanup() {
        onInputCleanup()
        for panel in [toolbar] + Array(panels.values) { panel.makeFirstResponder(nil) }
        tools.report.close()
    }
    func restoreDeviceFrame() {
        guard let device, let frame = placement.deviceFrame else { return }
        device.setFrame(restored(frame, fallback: device.frame), display: false)
        if placement.attached { followDevice() }
    }
    private func configure(grip: SimulatorToolbarGrip, key: String?) {
        grip.onBegin = { [weak self] point in
            guard let self, !self.closed else { return }
            self.cleanup()
            self.draggingKey = key ?? "toolbar"
            self.dragStart = point
            if let key { self.detach(key, save: false) }
            else { self.placement.attached = false }
            self.dragOrigin = (key.flatMap { self.panels[$0] } ?? self.toolbar).frame.origin
        }
        grip.onDrag = { [weak self] point in self?.drag(to: point) }
        grip.onEnd = { [weak self] in self?.finishDrag() }
    }
    private func drag(to point: CGPoint) {
        guard let key = draggingKey else { return }
        let panel = key == "toolbar" ? toolbar : panels[key]
        guard let panel else { return }
        panel.setFrameOrigin(CGPoint(x: dragOrigin.x + point.x - dragStart.x, y: dragOrigin.y + point.y - dragStart.y))
        if key == "toolbar", let device {
            dockCandidate = simulatorToolbarSnapSide(toolbar.frame, device: device.frame)
            backdrop.tint = dockCandidate == nil ? nil : .controlAccentColor
            toolbarGrip.label.stringValue = deviceName + (dockCandidate == nil ? " · 메인 도구 · 독립 이동" : " · 놓으면 기기에 결합")
        } else {
            moduleCandidate = !focused && toolbar.frame.insetBy(dx: -28, dy: -28).contains(point)
            backdrop.tint = moduleCandidate ? .controlAccentColor : nil
            toolbarGrip.label.stringValue = deviceName + (moduleCandidate ? " · 놓으면 메인 도구에 재결합" : " · 메인 도구")
        }
    }
    private func finishDrag() {
        guard let key = draggingKey else { return }
        draggingKey = nil
        if key == "toolbar" {
            if let left = dockCandidate { placement.attached = true; placement.leftSide = left; followDevice() }
            else { toolbar.setFrame(restored(toolbar.frame, fallback: toolbar.frame), display: true) }
        } else if moduleCandidate { attach(key) }
        else if let panel = panels[key] { panel.setFrame(restored(panel.frame, fallback: toolbar.frame), display: true) }
        dockCandidate = nil; moduleCandidate = false; backdrop.tint = nil
        toolbarGrip.label.stringValue = "⠿  " + deviceName + " · 메인 도구 · " + (placement.attached ? "기기에 결합" : "독립 이동")
        save(); onStateChange()
    }
    func detach(_ key: String, save shouldSave: Bool = true) {
        guard !closed, panels[key] == nil, let module = modules.first(where: { $0.key == key }) else { return }
        cleanup()
        let oldFrame = module.window.map { $0.convertToScreen(module.convert(module.bounds, to: nil)) }
        module.removeFromSuperview()
        module.isHidden = false
        let panel = SimulatorToolbarPanel()
        panel.title = toolbar.title + " · " + module.title
        // Publish ownership before setFrame: AppKit synchronously reenters windowDidResize.
        panels[key] = panel
        panel.contentView = module; panel.delegate = self
        let initial = oldFrame ?? toolbar.frame
        let desired = CGRect(origin: initial.origin, size: CGSize(width: 372, height: module.totalHeight))
        panel.setFrame(restored(placement.detached[key] ?? desired, fallback: toolbar.frame), display: false)
        module.layoutSubtreeIfNeeded()
        rebuild(); updateVisibility()
        if shouldSave { save(); onStateChange() }
    }
    func attach(_ key: String) {
        guard let panel = panels[key], let module = modules.first(where: { $0.key == key }) else { return }
        cleanup()
        panel.contentView = nil
        panel.orderOut(nil); panel.delegate = nil; panel.close()
        panels[key] = nil; placement.detached[key] = nil
        document.addSubview(module)
        rebuild(); updateVisibility(); save(); onStateChange()
    }
    private func rebuild() {
        for module in modules where panels[module.key] == nil {
            if module.superview !== document { module.removeFromSuperview(); document.addSubview(module) }
            module.isHidden = module.key == "advanced" && !advancedVisible
        }
        root.needsLayout = true
        backdrop.layoutSubtreeIfNeeded()
        arrangeRoot(root.bounds)
    }
    private func arrangeRoot(_ bounds: CGRect) {
        guard !arranging else { return }
        arranging = true; defer { arranging = false }
        toolbarGrip.frame = CGRect(x: 4, y: max(0, bounds.height - 44), width: max(0, bounds.width - 8), height: 40)
        scroll.frame = CGRect(x: 8, y: 8, width: max(0, bounds.width - 16), height: max(0, bounds.height - 56))
        let visible = modules.filter { panels[$0.key] == nil && !$0.isHidden }
        let height = visible.reduce(CGFloat(8)) { $0 + $1.totalHeight + 12 }
        document.frame = CGRect(x: 0, y: 0, width: scroll.contentSize.width, height: max(height, scroll.contentSize.height))
        var top = document.bounds.height - 4
        for module in visible {
            module.frame = CGRect(x: 4, y: top - module.totalHeight, width: max(1, document.bounds.width - 8), height: module.totalHeight)
            top = module.frame.minY - 12
            module.layoutSubtreeIfNeeded()
        }
    }
    func showStatusResponse() {
        guard let module = modules.first(where: { $0.key == "status" }) else { return }
        resume()
        if panels["status"] == nil { document.scrollToVisible(module.frame) }
        tools.showResponse(from: module.content)
    }
    func setAdvancedVisible(_ visible: Bool) {
        cleanup()
        advancedVisible = visible
        tools.setFloatingPresentation(visible && !focused && !suspended)
        rebuild(); updateVisibility()
        if visible, let module = modules.first(where: { $0.key == "advanced" }), panels["advanced"] == nil {
            document.scrollToVisible(module.frame)
        }
    }
    func setFocused(_ value: Bool) {
        cleanup(); focused = value
        if value { cancelDrags() }
        updateVisibility()
    }
    func resume() { guard !closed else { return }; suspended = false; updateVisibility() }
    func suspend() { cleanup(); suspended = true; cancelDrags(); updateVisibility() }
    private func updateVisibility() {
        let visible = !closed && !suspended && !focused && device?.isVisible == true && device?.isMiniaturized != true
        if visible { toolbar.orderFront(nil) } else { toolbar.orderOut(nil) }
        for (key, panel) in panels {
            if visible && (key != "advanced" || advancedVisible) { panel.orderFront(nil) }
            else { panel.orderOut(nil) }
        }
        tools.setFloatingPresentation(visible && advancedVisible)
    }
    func deviceDidMove() {
        guard device != nil else { return }
        if placement.attached && draggingKey != "toolbar" { followDevice() }
        if draggingKey == nil { save() }
    }
    private func followDevice() {
        guard let device else { return }
        let x = placement.leftSide ? device.frame.minX - toolbar.frame.width - 12 : device.frame.maxX + 12
        var frame = CGRect(origin: CGPoint(x: x, y: device.frame.maxY - toolbar.frame.height), size: toolbar.frame.size)
        if let screen = device.screen?.visibleFrame {
            // Prefer the opposite edge if this display has room there.
            let oppositeX = placement.leftSide ? device.frame.maxX + 12 : device.frame.minX - toolbar.frame.width - 12
            if !screen.contains(frame), screen.contains(CGRect(x: oppositeX, y: frame.minY, width: frame.width, height: frame.height)) {
                frame.origin.x = oppositeX; placement.leftSide.toggle()
            }
            frame = simulatorConstrainedFrame(frame, to: screen)
        }
        toolbar.setFrame(frame, display: true)
    }
    func resetLayout() {
        cleanup(); cancelDrags()
        for key in Array(panels.keys) { attach(key) }
        placement = SimulatorToolbarLayout()
        if let screen = device?.screen?.visibleFrame {
            toolbar.setContentSize(CGSize(width: min(388, screen.width), height: min(780, screen.height - 24)))
        }
        followDevice(); rebuild(); updateVisibility(); save(); onStateChange()
    }
    private func save() {
        guard !closed, !configuring else { return }
        placement.toolbarFrame = toolbar.frame
        placement.deviceFrame = device?.frame
        placement.detached = panels.mapValues(\.frame)
        if let data = try? JSONEncoder().encode(placement) { defaults.set(data, forKey: storageKey) }
    }
    func close() {
        guard !closed else { return }
        cleanup(); cancelDrags(); save(); closed = true
        for panel in [toolbar] + Array(panels.values) { panel.delegate = nil; panel.orderOut(nil); panel.close() }
        panels.removeAll()
    }
    private func cancelDrags() {
        toolbarGrip.cancelDrag()
        for module in modules { module.grip.cancelDrag() }
        draggingKey = nil; dockCandidate = nil; moduleCandidate = false; backdrop.tint = nil
    }
    @objc private func screensChanged() {
        guard !closed else { return }
        if draggingKey != nil { cancelDrags() }
        for panel in [toolbar] + Array(panels.values) { panel.setFrame(restored(panel.frame, fallback: panel.frame), display: true) }
        if placement.attached { followDevice() }
        rebuild(); save()
    }
    func windowDidResignKey(_ notification: Notification) {
        onInputCleanup()
        // A mouse drag can end by switching applications or by opening a sheet.
        if draggingKey != nil { cancelDrags() }
    }
    func windowDidMove(_ notification: Notification) { if draggingKey == nil { save() } }
    func windowDidResize(_ notification: Notification) { rebuild() }
    func windowShouldClose(_ sender: NSWindow) -> Bool {
        if let key = panels.first(where: { $0.value === sender })?.key { attach(key) }
        else { suspend() }
        return false
    }
    func menu(module key: String? = nil, includeDeviceMenu: Bool = true) -> NSMenu {
        let menu = NSMenu(title: "도구 배치")
        func add(_ title: String, _ action: Selector, value: String? = nil, state: Bool = false) {
            let item = NSMenuItem(title: title, action: action, keyEquivalent: "")
            item.target = self; item.representedObject = value; item.state = state ? .on : .off
            menu.addItem(item)
        }
        if let key, let module = modules.first(where: { $0.key == key }) {
            add(module.title + (panels[key] == nil ? " · 독립 패널로 분리" : " · 메인 도구에 재결합"), #selector(toggleModule(_:)), value: key)
            menu.addItem(.separator())
        }
        add("메인 도구를 기기에 결합", #selector(attachToolbar), state: placement.attached)
        add("메인 도구를 독립 이동", #selector(detachToolbar), state: !placement.attached)
        for module in modules { add(module.title + (panels[module.key] == nil ? " · 분리" : " · 재결합"), #selector(toggleModule(_:)), value: module.key) }
        menu.addItem(.separator())
        add("기본 배치", #selector(reset))
        if onSettings != nil { add("판단 API 설정…", #selector(settings)) }
        if includeDeviceMenu {
            let deviceItem = NSMenuItem(title: "기기 메뉴", action: nil, keyEquivalent: "")
            deviceItem.submenu = onDeviceMenu(); menu.addItem(deviceItem)
        }
        return menu
    }
    @objc private func toggleModule(_ sender: NSMenuItem) {
        guard let key = sender.representedObject as? String else { return }
        if panels[key] == nil { detach(key) } else { attach(key) }
    }
    @objc private func attachToolbar() { cleanup(); placement.attached = true; followDevice(); save(); onStateChange() }
    @objc private func detachToolbar() { cleanup(); placement.attached = false; save(); onStateChange() }
    @objc private func reset() { resetLayout() }
    @objc private func settings() { onSettings?() }
}
