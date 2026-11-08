import AppKit

/// Borderless LCDs still participate in activation, key delivery, Dock restore and window cycling.
final class SimulatorDeviceWindow: NSWindow {
    var interactiveMove = false
    override init(contentRect: NSRect, styleMask: NSWindow.StyleMask, backing: NSWindow.BackingStoreType, defer flag: Bool) {
        super.init(contentRect: contentRect, styleMask: styleMask, backing: backing, defer: flag)
        isMovable = true
        isMovableByWindowBackground = false
    }
    override var canBecomeKey: Bool { true }
    override var canBecomeMain: Bool { true }
    override func constrainFrameRect(_ frameRect: NSRect, to screen: NSScreen?) -> NSRect {
        // AppKit's borderless constraint can otherwise fight performDrag between displays.
        interactiveMove ? frameRect : super.constrainFrameRect(frameRect, to: screen)
    }
}

final class SimulatorMoveGrip: NSView {
    let label = NSTextField(labelWithString: "")
    var onManipulate: () -> Void = {}
    var onEndManipulate: () -> Void = {}
    private var dragging = false
    override init(frame: NSRect) {
        super.init(frame: frame)
        label.font = .systemFont(ofSize: 12, weight: .semibold)
        label.lineBreakMode = .byTruncatingMiddle
        addSubview(label)
        toolTip = "기기 이동 · 드래그"
        setAccessibilityElement(true)
        setAccessibilityRole(.handle)
        setAccessibilityLabel("기기 이동 손잡이")
        setAccessibilityHelp("드래그로 창 이동. 기기 메뉴에서 크기와 위치를 조절할 수 있습니다.")
    }
    required init?(coder: NSCoder) { fatalError() }
    override func layout() { super.layout(); label.frame = bounds.insetBy(dx: 12, dy: 10) }
    override func hitTest(_ point: NSPoint) -> NSView? { bounds.contains(convert(point, from: superview)) ? self : nil }
    override func resetCursorRects() { addCursorRect(bounds, cursor: .openHand) }
    override func acceptsFirstMouse(for event: NSEvent?) -> Bool { true }
    override var mouseDownCanMoveWindow: Bool { false }
    override func mouseDown(with event: NSEvent) {
        guard let window else { return }
        dragging = true
        onManipulate()
        window.isMovable = true // Borderless windows do not inherit the titled-window default.
        (window as? SimulatorDeviceWindow)?.interactiveMove = true
        window.makeKeyAndOrderFront(nil)
        NSCursor.closedHand.push()
        defer {
            NSCursor.pop()
            cancelDrag()
        }
        window.performDrag(with: event)
    }
    func cancelDrag() {
        guard dragging else { return }
        dragging = false
        (window as? SimulatorDeviceWindow)?.interactiveMove = false
        onEndManipulate()
    }
}

final class SimulatorResizeGrip: NSView {
    var onManipulate: () -> Void = {}
    var onEndManipulate: () -> Void = {}
    private var start: (point: CGPoint, frame: CGRect)?
    override init(frame: NSRect) {
        super.init(frame: frame)
        wantsLayer = true
        layer?.cornerRadius = 12
        toolTip = "기기 크기 조절 · 드래그 (기기 메뉴에서도 조절 가능)"
        setAccessibilityElement(true)
        setAccessibilityRole(.handle)
        setAccessibilityLabel("기기 크기 조절")
    }
    required init?(coder: NSCoder) { fatalError() }
    override func draw(_ dirtyRect: NSRect) {
        let contrast = NSWorkspace.shared.accessibilityDisplayShouldIncreaseContrast
        NSColor.controlBackgroundColor.withAlphaComponent(NSWorkspace.shared.accessibilityDisplayShouldReduceTransparency ? 1 : 0.82).setFill()
        NSBezierPath(roundedRect: bounds.insetBy(dx: 2, dy: 2), xRadius: 12, yRadius: 12).fill()
        NSColor.labelColor.setStroke()
        let path = NSBezierPath()
        path.lineWidth = contrast ? 2.5 : 2
        path.lineCapStyle = .round
        let c = CGPoint(x: bounds.midX, y: bounds.midY)
        path.move(to: CGPoint(x: c.x - 6, y: c.y - 6)); path.line(to: CGPoint(x: c.x + 6, y: c.y + 6))
        path.move(to: CGPoint(x: c.x, y: c.y + 6)); path.line(to: CGPoint(x: c.x + 6, y: c.y + 6)); path.line(to: CGPoint(x: c.x + 6, y: c.y))
        path.move(to: CGPoint(x: c.x - 6, y: c.y)); path.line(to: CGPoint(x: c.x - 6, y: c.y - 6)); path.line(to: CGPoint(x: c.x, y: c.y - 6))
        path.stroke()
    }
    override func resetCursorRects() { addCursorRect(bounds, cursor: .crosshair) }
    override var mouseDownCanMoveWindow: Bool { false }
    override func acceptsFirstMouse(for event: NSEvent?) -> Bool { true }
    override func mouseDown(with event: NSEvent) {
        guard let window else { return }
        onManipulate()
        window.makeKeyAndOrderFront(nil)
        start = (NSEvent.mouseLocation, window.frame)
    }
    override func mouseDragged(with event: NSEvent) {
        guard let window, let start else { return }
        let cursor = NSEvent.mouseLocation
        let size = CGSize(width: max(window.contentMinSize.width, start.frame.width + cursor.x - start.point.x),
                          height: max(window.contentMinSize.height, start.frame.height - cursor.y + start.point.y))
        let frame = CGRect(x: start.frame.minX, y: start.frame.maxY - size.height, width: size.width, height: size.height)
        window.setFrame(simulatorConstrainedFrame(frame, to: window.screen?.visibleFrame ?? frame), display: true)
    }
    func cancelDrag() {
        guard start != nil else { return }
        start = nil
        onEndManipulate()
    }
    override func mouseUp(with event: NSEvent) { cancelDrag() }
}

/// All controls live outside the LCD; no chrome event can become a guest touch.
final class SimulatorDeviceChrome: NSObject, NSPopoverDelegate {
    let grip = SimulatorMoveGrip()
    let resize = SimulatorResizeGrip()
    let handle: SimulatorGlassView
    let controls: SimulatorGlassView
    let rail: SimulatorGlassView
    let information = SimulatorGlassView(content: NSView())
    let folding = SimulatorGlassView(content: NSView())
    let activity = SimulatorGlassView(content: NSView())
    private let identity = NSTextField(wrappingLabelWithString: "기기 연결 확인 중…")
    private(set) var usesFloatingModules = false
    private let menuButton = NSButton()
    private var primary: [NSButton] = []
    private var auxiliary: [NSButton] = []
    private let fold = NSButton()
    private let angle = NSSlider(value: 180, minValue: 0, maxValue: 180, target: nil, action: nil)
    private let angleLabel = NSTextField(labelWithString: "실제 각도 읽는 중…")
    private let feedback = NSTextField(labelWithString: "준비됨")
    private let responseButton = NSButton()
    private let hinge = NSPopover()
    private var presets: [NSButton] = []
    private var foldable = false
    private var orientation = "portrait"
    private var busy = false
    var toolsVisible = false
    var touchesVisible = true
    var keyboardEnabled = true
    var onRun: ([String: Any]) -> Void = { _ in }
    var onMenu: () -> NSMenu = { NSMenu() }
    var onTools: () -> Void = {}
    var onKeyboard: () -> Void = {}
    var onTouches: () -> Void = {}
    var onResponse: (NSView) -> Void = { _ in }

    override init() {
        handle = SimulatorGlassView(content: NSView())
        controls = SimulatorGlassView(content: NSView())
        rail = SimulatorGlassView(content: NSView())
        super.init()
        handle.content.addSubview(grip)
        configure(menuButton, title: "기기 메뉴", symbol: "ellipsis.circle", action: #selector(openMenu))
        menuButton.title = ""
        handle.content.addSubview(menuButton)
        handle.layoutContent = { [weak self] bounds in
            self?.grip.frame = CGRect(x: 0, y: 0, width: max(0, bounds.width - 44), height: bounds.height)
            self?.menuButton.frame = CGRect(x: bounds.width - 44, y: 2, width: 42, height: bounds.height - 4)
        }
        let home = make("홈", "house", #selector(home))
        let rotate = make("회전", "rotate.right", #selector(rotate))
        configure(fold, title: "접기", symbol: "rectangle.split.2x1", action: #selector(showHinge))
        let capture = make("캡처", "camera", #selector(capture))
        primary = [home, rotate, fold, capture]
        for button in primary { button.imagePosition = .imageAbove; controls.content.addSubview(button) }
        feedback.font = .systemFont(ofSize: 12, weight: .medium)
        feedback.lineBreakMode = .byTruncatingMiddle
        feedback.alignment = .center
        feedback.setAccessibilityLabel("시뮬레이터 조작 결과")
        controls.content.addSubview(feedback)
        controls.layoutContent = { [weak self] bounds in self?.layoutControls(bounds) }
        auxiliary = [make("잠금", "lock", #selector(lock)), make("키보드 입력", "keyboard", #selector(keyboard)),
                     make("터치 표시", "hand.point.up.left", #selector(touches)), make("고급 도구", "slider.horizontal.3", #selector(tools))]
        for (i, button) in auxiliary.enumerated() {
            button.title = ""
            if i > 0 { button.setButtonType(.toggle) }
            rail.content.addSubview(button)
        }
        rail.layoutContent = { [weak self] bounds in
            guard let self else { return }
            let height = min(48, bounds.height / CGFloat(self.auxiliary.count))
            for (i, button) in self.auxiliary.enumerated() {
                button.frame = CGRect(x: 3, y: bounds.height - CGFloat(i + 1) * height, width: bounds.width - 6, height: height)
            }
        }
        configureHinge()
        updateControls()
    }

    private func configure(_ button: NSButton, title: String, symbol: String, action: Selector) {
        button.title = title
        button.image = NSImage(systemSymbolName: symbol, accessibilityDescription: nil)?.withSymbolConfiguration(.init(pointSize: 18, weight: .medium))
        button.font = .systemFont(ofSize: 12, weight: .medium)
        button.contentTintColor = .labelColor
        button.imagePosition = .imageLeading
        button.isBordered = false
        button.target = self
        button.action = action
        button.toolTip = title
        button.setAccessibilityLabel(title)
    }
    private func make(_ title: String, _ symbol: String, _ action: Selector) -> NSButton {
        let button = NSButton(); configure(button, title: title, symbol: symbol, action: action); return button
    }
    private func layoutControls(_ bounds: CGRect) {
        let visible = primary.filter { !$0.isHidden }
        let gap: CGFloat = 6
        let width = (bounds.width - 16 - gap * CGFloat(visible.count - 1)) / CGFloat(visible.count)
        for (i, button) in visible.enumerated() {
            button.frame = CGRect(x: 8 + CGFloat(i) * (width + gap), y: usesFloatingModules ? 2 : 16, width: width, height: bounds.height - (usesFloatingModules ? 4 : 18))
        }
        if !usesFloatingModules {
            feedback.frame = CGRect(x: 8, y: 1, width: bounds.width - 16, height: 14)
        }
    }
    func updateDevice(name: String, runtime: String, connected: Bool, foldable: Bool, isWatch: Bool, rotation: String, primaryDisplay: Bool = true) {
        self.foldable = foldable
        // Duo's inner display reports rot90 for the picker's portrait state
        // and rot0 for landscape-left. The cover and single-screen devices use
        // the usual axes. Always choose from readback, never from a prior click.
        let quarterTurn = rotation == "rot90" || rotation == "rot270"
        let portrait = foldable && !primaryDisplay ? quarterTurn : !quarterTurn
        orientation = portrait ? "landscape-left" : "portrait"
        grip.label.stringValue = "⠿  \(name) · \(connected ? "연결됨" : "화면 대기") · \(runtime)"
        grip.setAccessibilityValue(grip.label.stringValue)
        grip.toolTip = grip.label.stringValue + " · 드래그로 이동"
        identity.stringValue = "\(name) · \(runtime)\n\(connected ? "연결됨" : "화면 대기")"
        fold.isHidden = !foldable || usesFloatingModules
        if usesFloatingModules && !foldable { angleLabel.stringValue = "이 기기는 접기를 지원하지 않습니다" }
        primary[1].isHidden = isWatch
        controls.needsLayout = true
        updateControls()
    }
    func updateAngle(_ degrees: Double) {
        fold.title = "접기 \(Int(degrees.rounded()))°"
        fold.setAccessibilityLabel("접기 · 실제 각도 \(Int(degrees.rounded()))도")
        angleLabel.stringValue = "실제 각도 \(Int(degrees.rounded()))° · 놓으면 적용"
        if !angle.isHighlighted { angle.doubleValue = degrees }
    }
    func setBusy(_ value: Bool) { busy = value; updateControls() }
    func showFeedback(_ message: String, failed: Bool = false) {
        feedback.stringValue = message
        feedback.toolTip = message
        feedback.textColor = failed ? .systemRed : .labelColor
        activity.tint = failed ? .systemRed : busy ? .controlAccentColor : nil
        NSAccessibility.post(element: feedback, notification: .valueChanged)
    }
    func closePopovers() { hinge.close() }
    func updateControls() {
        for button in primary { button.isEnabled = !busy }
        auxiliary.first?.isEnabled = !busy
        angle.isEnabled = foldable && !busy
        presets.forEach { $0.isEnabled = foldable && !busy }
        auxiliary[1].state = keyboardEnabled ? .on : .off
        auxiliary[2].state = touchesVisible ? .on : .off
        auxiliary[3].state = toolsVisible ? .on : .off
        for button in auxiliary { button.contentTintColor = button.state == .on ? .controlAccentColor : .labelColor }
        controls.tint = busy ? .controlAccentColor : nil
    }
    /// Transfer existing controls once; no action or draft is copied into another window.
    func enableFloatingModules() {
        guard !usesFloatingModules else { return }
        usesFloatingModules = true
        hinge.close()
        if let root = hinge.contentViewController?.view {
            folding.content.addSubview(root)
            folding.layoutContent = { root.frame = $0 }
            hinge.contentViewController = nil
        }
        feedback.removeFromSuperview()
        activity.content.addSubview(feedback)
        feedback.maximumNumberOfLines = 2
        feedback.lineBreakMode = .byWordWrapping
        feedback.alignment = .left
        configure(responseButton, title: "응답", symbol: "text.bubble", action: #selector(response))
        activity.content.addSubview(responseButton)
        activity.layoutContent = { [weak self] bounds in
            self?.feedback.frame = CGRect(x: 14, y: 10, width: max(0, bounds.width - 100), height: max(0, bounds.height - 20))
            self?.responseButton.frame = CGRect(x: bounds.width - 80, y: 8, width: 72, height: bounds.height - 16)
        }
        identity.font = .systemFont(ofSize: 12, weight: .medium)
        identity.textColor = .labelColor
        information.content.addSubview(identity)
        information.layoutContent = { [weak self] in self?.identity.frame = $0.insetBy(dx: 14, dy: 8) }
        for (i, button) in auxiliary.enumerated() {
            button.title = ["잠금", "키보드", "터치 표시", "고급 도구"][i]
            button.imagePosition = .imageAbove
        }
        rail.layoutContent = { [weak self] bounds in
            guard let self else { return }
            let width = (bounds.width - 16) / 4
            for (i, button) in self.auxiliary.enumerated() {
                button.frame = CGRect(x: 8 + CGFloat(i) * width, y: 4, width: width, height: bounds.height - 8)
            }
        }
        fold.isHidden = true
        controls.needsLayout = true
        updateControls()
    }

    private func configureHinge() {
        let root = NSView(frame: CGRect(x: 0, y: 0, width: 300, height: 130))
        angleLabel.frame = CGRect(x: 16, y: 94, width: 268, height: 20)
        root.addSubview(angleLabel)
        angle.frame = CGRect(x: 16, y: 58, width: 268, height: 28)
        angle.isContinuous = false
        angle.target = self; angle.action = #selector(applyAngle)
        angle.setAccessibilityLabel("접기 각도 · 놓으면 적용")
        root.addSubview(angle)
        for (i, item) in [("접기", 0), ("반쯤 펼침", 130), ("펼침", 180)].enumerated() {
            let button = NSButton(title: item.0, target: self, action: #selector(preset(_:)))
            button.tag = item.1
            button.frame = CGRect(x: 12 + i * 94, y: 14, width: 90, height: 32)
            button.toolTip = "\(item.0) · \(item.1)° 적용"
            button.setAccessibilityLabel(button.toolTip)
            root.addSubview(button); presets.append(button)
        }
        let controller = NSViewController(); controller.view = root
        hinge.contentViewController = controller
        hinge.behavior = .transient
        hinge.delegate = self
    }
    func popoverDidClose(_ notification: Notification) { fold.setAccessibilityExpanded(false) }
    @objc private func openMenu() { onMenu().popUp(positioning: nil, at: CGPoint(x: 0, y: menuButton.bounds.minY), in: menuButton) }
    private func run(_ arguments: [String: Any]) { if !busy { onRun(arguments) } }
    @objc private func home() { run(["action": "button", "button": "home"]) }
    @objc private func lock() { run(["action": "button", "button": "lock"]) }
    @objc private func rotate() { run(["action": "rotate", "orientation": orientation]) }
    @objc private func capture() { run(["action": "screenshot"]) }
    @objc private func keyboard() { onKeyboard() }
    @objc private func touches() { onTouches() }
    @objc private func tools() { onTools() }
    @objc private func response() { onResponse(responseButton) }
    @objc private func showHinge() {
        guard foldable, !busy else { return }
        if hinge.isShown { hinge.close() } else { hinge.show(relativeTo: fold.bounds, of: fold, preferredEdge: .maxY) }
        fold.setAccessibilityExpanded(hinge.isShown)
    }
    @objc private func applyAngle() { run(["action": "hinge", "degrees": angle.doubleValue]) }
    @objc private func preset(_ button: NSButton) { run(["action": "hinge", "degrees": Double(button.tag)]) }
}

/// Multi-screen backend responses put a label immediately before each image.
func simulatorActiveCaptureData(_ items: [[String: Any]]) -> Data? {
    var first: Data?
    var active = false
    for item in items {
        if let text = item["text"] as? String { active = text.contains("(on:") }
        if let encoded = item["data"] as? String, let image = Data(base64Encoded: encoded) {
            if active { return image }
            if first == nil { first = image }
        }
    }
    return first
}
