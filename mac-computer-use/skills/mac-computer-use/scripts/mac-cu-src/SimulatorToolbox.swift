import AppKit
import SwiftUI

struct SimulatorToolboxMotion {
    let delay: Double
    let duration: Double
    let bounce: Double

    init(row: Int, column: Int) {
        delay = Double((row * 2 + column) % 7) * 0.01
        duration = 0.44 + Double((row + column * 2) % 5) * 0.02
        bounce = 0.04 + Double((row + column) % 3) * 0.02
    }
}

func simulatorToolboxFrame(row: Int, column: Int, columns: Int, span: Int, in size: CGSize,
                           lcd: CGRect, expanded: Bool) -> CGRect {
    let heights: [CGFloat] = [44, 60, 44, 44, 44, 44, 64, 44]
    let scale = min(1, max(0, size.height) / simulatorToolboxHeight)
    let gap = 24 * scale
    let width = max(1, size.width - simulatorToolboxGap)
    let cell = max(1, (width - gap * CGFloat(columns - 1)) / CGFloat(columns))
    let top = heights.prefix(row).reduce(6, +) + CGFloat(row) * 24
    let x = CGFloat(column) * (cell + gap)
    let frame = CGRect(x: x, y: size.height - (top + heights[row]) * scale,
                       width: min(width - x, cell * CGFloat(span) + gap * CGFloat(span - 1)), height: heights[row] * scale)
    if expanded { return frame.offsetBy(dx: simulatorToolboxGap, dy: 0) }
    let closedHeight = min(size.height * 0.82, max(1, lcd.height))
    let verticalScale = closedHeight / max(1, size.height)
    // Keep the whole ordered grid behind the LCD edge, including a glass rim/shadow allowance.
    return CGRect(x: min(0, lcd.maxX) - 2 * simulatorToolboxRim - width * 0.82 + frame.minX * 0.82,
                  y: lcd.midY - closedHeight / 2 + frame.minY * verticalScale,
                  width: frame.width * 0.82, height: frame.height * verticalScale)
}

struct SimulatorToolActivity {
    let id = UUID()
    let connection: UUID?
    let request: String?
    let action: String
    let control: String
    let source: String
    let summary: String
    let started = Date()

    var title: String {
        ["button.home": "홈", "button.lock": "잠금", "button.side": "측면 버튼", "button.siri": "Siri", "rotate": "회전",
         "hinge": "접기", "crown": "Crown", "type": "글자 입력", "paste": "붙여넣기", "key": "키 전송",
         "gesture": "제스처", "describe": "화면 요소", "wait": "요소 대기", "tap": "탭", "press": "접근성 실행",
         "views": "UIView 검사", "screenshot": "캡처", "window": "LCD 창"][control] ?? action
    }

    init(arguments: [String: Any], source: String, connection: UUID? = nil, request: String? = nil) {
        self.connection = connection
        self.request = request
        let action = arguments["action"] as? String ?? ""
        self.action = action
        control = (arguments["button"] as? String).map { "\(action).\($0)" } ?? action
        self.source = source
        summary = arguments.keys.sorted().filter { $0 != "device" && $0 != "action" }.map { key in
            if key == "text" { return "글자 \((arguments[key] as? String ?? "").count)자" }
            if key == "frames" { return "접점 프레임 \((arguments[key] as? [Any] ?? []).count)개" }
            return "\(key)=\(String(describing: arguments[key]!).prefix(80))"
        }.joined(separator: " · ")
    }
}

/// Parallel contacts for the coordinate form. The backend performs the same HID validation as MCP calls.
func simulatorToolboxContacts(from: CGPoint, to: CGPoint?, fingers: Int, seconds: Double, screen: CGSize) throws -> [[String: Any]] {
    guard (1...3).contains(fingers), seconds.isFinite, seconds >= 0.02, seconds <= 10 else {
        throw NSError(domain: "SimulatorToolbox", code: 1, userInfo: [NSLocalizedDescriptionKey: "손가락은 1~3개, 시간은 0.02~10초로 입력하세요."])
    }
    func touches(_ at: CGPoint, phase: String) throws -> [[String: Any]] {
        try (0..<fingers).map { i in
            let x = at.x + CGFloat(i) * 24
            guard x.isFinite, at.y.isFinite, x >= 0, x < screen.width, at.y >= 0, at.y < screen.height else {
                throw NSError(domain: "SimulatorToolbox", code: 2, userInfo: [NSLocalizedDescriptionKey: "모든 접점이 LCD 화면 안에 있어야 합니다. 손가락 사이 간격은 24pt입니다."])
            }
            return ["id": i + 1, "phase": phase, "x": x, "y": at.y]
        }
    }
    var frames: [[String: Any]] = [["time": 0.0, "touches": try touches(from, phase: "down")]]
    if let to { frames.append(["time": seconds * 0.9, "touches": try touches(to, phase: "move")]) }
    frames.append(["time": seconds, "touches": try touches(to ?? from, phase: "up")])
    return frames
}

func simulatorToolboxViewRequest(_ input: String) -> [String: Any] {
    let parts = input.split(separator: ">", maxSplits: 1, omittingEmptySubsequences: false).map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
    if parts.count == 2 { return ["action": "views", "app": parts[0], "query": parts[1]] }
    return ["action": "views", "query": input]
}

final class SimulatorToolboxView: NSView {
    var onRun: ([String: Any]) -> Void = { _ in }
    var onAvailabilityChanged: (Bool) -> Void = { _ in }
    var confirmAction: (String) -> Bool = SimulatorToolboxView.confirm
    private(set) var screenSize = CGSize(width: 1, height: 1)
    private(set) var busy = false
    private(set) var manualPending = false
    private var current: UUID?
    private var lastManual: [String: Any]?
    private var actions: [NSControl: () throws -> [String: Any]] = [:]
    private var actionNames: [NSControl: String] = [:]
    private var history: [String] = []
    private struct Component {
        let glass: SimulatorGlassView
        let control: NSControl
        let row: Int
        let column: Int
        let columns: Int
        let span: Int
    }
    private var components: [Component] = []
    private let isWatch: Bool
    private let angle = NSSlider(value: 180, minValue: 0, maxValue: 180, target: nil, action: nil)
    private let angleLabel = NSTextField(labelWithString: "접기 각도")
    private var angleGlass: SimulatorGlassView?
    private var orientationControl: NSPopUpButton?
    let report = NSPopover()
    private let status = NSButton(title: "활동 · 대기", target: nil, action: nil)
    private let argumentsLabel = NSTextField(wrappingLabelWithString: "")
    private let result = NSTextView()
    private let recent = NSTextField(wrappingLabelWithString: "")
    private let images = NSStackView()
    private var expanded = false
    private var transitioning = false
    private var animationVersion = 0
    private var animationTargets: [CGRect] = []
    private var animationRequested = false
    private var animationCompleted = false
    private var settlement: DispatchWorkItem?
    private var transitionCompletion: (() -> Void)?
    var retractionLCD = CGRect(x: -simulatorToolboxWidth, y: 0, width: simulatorToolboxWidth, height: simulatorToolboxHeight) {
        didSet { if oldValue != retractionLCD { needsLayout = true } }
    }
    private var acceptsInput: Bool { expanded && !transitioning && !isHiddenOrHasHiddenAncestor }
    var glassSpacing: CGFloat { 18 * min(1, max(0, bounds.height) / simulatorToolboxHeight) }
    var visibleGlassFrames: [CGRect] { components.filter { !$0.glass.isHidden }.map { $0.glass.frame } }
    var clippedGlassFrames: [CGRect] { visibleGlassFrames.map { $0.intersection(bounds) }.filter { !$0.isEmpty } }
    var glassIsRetracted: Bool {
        visibleGlassFrames.allSatisfy {
            $0.maxX + simulatorToolboxRim <= min(0, retractionLCD.maxX) &&
            $0.insetBy(dx: -simulatorToolboxRim, dy: -simulatorToolboxRim).intersection(bounds).isEmpty
        }
    }

    init(deviceName: String, isWatch: Bool) {
        self.isWatch = isWatch
        super.init(frame: CGRect(x: 0, y: 0, width: simulatorToolboxWidth + simulatorToolboxGap, height: simulatorToolboxHeight))
        clipsToBounds = true
        setAccessibilityElement(false)
        setAccessibilityLabel(deviceName + " 도구")
        for (column, item) in [("홈", "home"), ("잠금", "lock"), ("Siri", "siri")].enumerated() {
            add(button(item.0), name: "button." + item.1, row: 0, column: column, columns: 3) { ["action": "button", "button": item.1] }
        }
        if isWatch {
            for (column, item) in [("Crown 위로", -60.0), ("Crown 아래로", 60.0)].enumerated() {
                add(button(item.0), name: "crown", row: 1, column: column) { ["action": "crown", "amount": item.1] }
            }
        } else {
            let orientation = NSPopUpButton()
            orientation.addItems(withTitles: ["세로", "가로 왼쪽", "가로 오른쪽", "거꾸로"])
            orientation.isBordered = false
            orientationControl = orientation
            orientation.setAccessibilityLabel("방향 · 선택 즉시 회전")
            add(orientation, name: "rotate", row: 1, column: 0) {
                ["action": "rotate", "orientation": ["portrait", "landscape-left", "landscape-right", "upside-down"][orientation.indexOfSelectedItem]]
            }
            angle.isContinuous = false
            angle.setAccessibilityLabel("접기 각도 · 놓으면 적용")
            let slider = angle
            add(angle, name: "hinge", row: 1, column: 1) { ["action": "hinge", "degrees": slider.doubleValue] }
            angleGlass = components.last?.glass
            angleLabel.font = .systemFont(ofSize: 11)
            angleGlass?.content.addSubview(angleLabel)
            angleGlass?.isHidden = true
        }
        let text = field("기기로 보낼 글자 ⏎")
        add(text, name: "type", row: 2, column: 0, columns: 3, span: 2) { ["action": "type", "text": text.stringValue] }
        add(button("붙여넣기…"), name: "paste", row: 2, column: 2, columns: 3) {
            ["action": "paste", "text": NSPasteboard.general.string(forType: .string) ?? ""]
        }
        let key = field("키 · Return, cmd+a ⏎")
        add(key, name: "key", row: 3, column: 0) { ["action": "key", "key": key.stringValue] }
        for (row, column, name, title) in [(3, 1, "describe", "화면 요소 검색 ⏎"), (4, 0, "wait", "기다릴 요소 ⏎"),
                                          (4, 1, "tap", "탭할 요소 ⏎"), (5, 0, "press", "접근성 실행 ⏎"), (5, 1, "views", "UIView · 앱ID > 클래스 ⏎")] {
            let input = field(title)
            add(input, name: name, row: row, column: column) {
                if name == "views" { return simulatorToolboxViewRequest(input.stringValue) }
                var value: [String: Any] = ["action": name]
                value[["describe", "views"].contains(name) ? "query" : "target"] = input.stringValue
                if name == "wait" { value["timeout"] = 10 }
                return value
            }
        }
        for index in 0..<3 {
            let pad = SimulatorGesturePad(fingers: index + 1)
            pad.onError = { [weak self] in self?.fail($0) }
            add(pad, name: "gesture", row: 6, column: index, columns: 3) { ["action": "gesture", "frames": pad.frames] }
        }
        let capture = NSPopUpButton(frame: .zero, pullsDown: true)
        capture.addItems(withTitles: ["캡처", "화면 캡처", "가이드 캡처"])
        capture.isBordered = false
        capture.setAccessibilityLabel("캡처 · 메뉴에서 바로 실행")
        add(capture, name: "screenshot", row: 7, column: 0) { ["action": "screenshot", "guides": capture.indexOfSelectedItem == 2] }
        status.target = self
        status.action = #selector(showReport(_:))
        status.isBordered = false
        status.setAccessibilityLabel("활동과 도구 응답")
        addComponent(status, name: "report", row: 7, column: 1)
        configureReport()
        updateInteraction()
    }
    required init?(coder: NSCoder) { fatalError() }

    private func button(_ title: String) -> NSButton {
        let control = NSButton(title: title, target: nil, action: nil)
        control.isBordered = false
        control.font = .systemFont(ofSize: 12, weight: .medium)
        return control
    }
    private func field(_ title: String) -> NSTextField {
        let control = NSTextField(string: "")
        control.placeholderString = title
        control.setAccessibilityLabel(title)
        control.isBordered = false
        control.drawsBackground = false
        control.font = .systemFont(ofSize: 12)
        control.lineBreakMode = .byTruncatingTail
        (control.cell as? NSTextFieldCell)?.sendsActionOnEndEditing = false
        return control
    }
    private func add(_ control: NSControl, name: String, row: Int, column: Int, columns: Int = 2, span: Int = 1,
                     build: @escaping () throws -> [String: Any]) {
        control.target = self
        control.action = #selector(execute(_:))
        actions[control] = build
        addComponent(control, name: name, row: row, column: column, columns: columns, span: span)
    }
    private func addComponent(_ control: NSControl, name: String, row: Int, column: Int, columns: Int = 2, span: Int = 1) {
        let content = NSView()
        content.addSubview(control)
        let glass = SimulatorGlassView(content: content)
        glass.layoutContent = { [weak self, weak control] bounds in
            guard let self, let control else { return }
            self.layout(control, in: bounds)
            self.finishTransitionIfReady()
        }
        glass.setAccessibilityElement(false)
        addSubview(glass)
        actionNames[control] = name
        components.append(Component(glass: glass, control: control, row: row, column: column, columns: columns, span: span))
    }

    func setFloatingPresentation(_ visible: Bool) {
        expanded = visible
        isHidden = !visible
        transitioning = false
        animationVersion += 1
        settlement?.cancel(); settlement = nil
        transitionCompletion = nil
        report.close()
        clipsToBounds = true
        needsLayout = true
        updateInteraction()
    }

    func updateScreen(_ size: CGSize, name: String, foldable: Bool, rotation: String = "rot0") {
        screenSize = size
        angleGlass?.isHidden = !foldable
        for item in components { (item.control as? SimulatorGesturePad)?.screenSize = size }
        if let orientationControl, !orientationControl.isHighlighted {
            let selected = ["rot0": 0, "rot180": 3, "rot90": foldable ? 1 : 2, "rot270": foldable ? 2 : 1][rotation] ?? 0
            orientationControl.selectItem(at: selected)
        }
        needsLayout = true
    }
    func updateAngle(_ degrees: Double) {
        guard !angle.isHighlighted, !manualPending else { return }
        angle.doubleValue = degrees
        angleLabel.stringValue = "접기 · \(Int(degrees))°"
    }

    private func frames() -> [CGRect] {
        components.map { item in
            simulatorToolboxFrame(row: item.row, column: item.column, columns: item.columns, span: item.span,
                                  in: bounds.size, lcd: retractionLCD, expanded: expanded)
        }
    }
    override func layout() {
        super.layout()
        guard bounds.width >= 72, bounds.height > 0 else { return }
        let targets = frames()
        if transitioning && targets != animationTargets { animateFrames(targets) }
        for (index, item) in components.enumerated() {
            if !transitioning { item.glass.frame = targets[index] }
            item.glass.layoutSubtreeIfNeeded()
        }
        updateInteraction()
    }
    private func layout(_ control: NSControl, in bounds: CGRect) {
        let height = max(0, min(bounds.height - 8, control is SimulatorGesturePad ? 48 : 26))
        let inset: CGFloat = control is SimulatorGesturePad ? 4 : 10
        control.frame = CGRect(x: inset, y: (bounds.height - height) / 2, width: max(0, bounds.width - 2 * inset), height: height)
        control.needsDisplay = true
        if control === angle {
            let sliderHeight = min(24, max(0, (bounds.height - 6) / 2))
            let labelHeight = min(18, max(0, bounds.height - sliderHeight - 6))
            angle.controlSize = bounds.height < 52 ? .small : .regular
            angle.frame = CGRect(x: 10, y: 2, width: max(0, bounds.width - 20), height: sliderHeight)
            angleLabel.frame = CGRect(x: 12, y: bounds.height - 2 - labelHeight, width: max(0, bounds.width - 24), height: labelHeight)
        }
    }
    override func resizeSubviews(withOldSize oldSize: NSSize) {
        super.resizeSubviews(withOldSize: oldSize)
        needsLayout = true
    }
    override func hitTest(_ point: NSPoint) -> NSView? {
        guard acceptsInput, bounds.contains(convert(point, from: superview)) else { return nil }
        return super.hitTest(point)
    }

    private func updateInteraction() {
        onAvailabilityChanged(busy || manualPending)
        for item in components {
            let visible = acceptsInput && !item.glass.isHidden && bounds.contains(item.glass.frame)
            item.glass.setAccessibilityHidden(!visible)
            item.control.setAccessibilityHidden(!visible)
            item.control.refusesFirstResponder = !visible
            item.control.isEnabled = visible && (actions[item.control] == nil || item.control is NSTextField || (!busy && !manualPending))
        }
    }

    func animateExpansion(_ open: Bool, animated: Bool, completion: @escaping () -> Void) {
        layoutSubtreeIfNeeded()
        expanded = open
        transitioning = true
        animationRequested = animated
        transitionCompletion = completion
        clipsToBounds = true
        report.close()
        updateInteraction()
        animateFrames(frames())
    }

    private func finishTransitionIfReady() {
        guard transitioning, animationCompleted, expanded || glassIsRetracted else { return }
        transitioning = false
        settlement?.cancel(); settlement = nil
        clipsToBounds = !expanded
        needsLayout = true
        updateInteraction()
        let completion = transitionCompletion
        transitionCompletion = nil
        completion?()
    }

    private func animateFrames(_ targets: [CGRect]) {
        settlement?.cancel()
        settlement = nil
        animationVersion += 1
        let version = animationVersion
        animationTargets = targets
        animationCompleted = false
        var remaining = components.count
        let finished = { [weak self] in
            guard let self, self.animationVersion == version else { return }
            remaining -= 1
            guard remaining == 0 else { return }
            self.animationCompleted = true
            // The AppKit bridge has no completion criterion parameter; check live rim bounds before hiding.
            self.finishTransitionIfReady()
        }
        let animate = animationRequested && !NSWorkspace.shared.accessibilityDisplayShouldReduceMotion
        if #available(macOS 15, *), animate {
            // The native bridge can drop completion for a property retargeted during its initial
            // delay, leaving subpixel residuals forever. Settle once after the spring's response
            // envelope; generation checks and cancellation preserve every live reversal.
            let work = DispatchWorkItem { [weak self] in
                guard let self, self.animationVersion == version, self.transitioning else { return }
                for (i, item) in self.components.enumerated() { item.glass.frame = targets[i] }
                self.animationCompleted = true
                self.finishTransitionIfReady()
            }
            settlement = work
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.85, execute: work)
        }
        for (index, item) in components.enumerated() {
            if #available(macOS 15, *), animate, !item.glass.isHidden {
                let motion = SimulatorToolboxMotion(row: item.row, column: item.column)
                // Retarget the live native spring; assigning an endpoint first discards its position and velocity.
                NSAnimationContext.animate(.spring(duration: motion.duration, bounce: motion.bounce).delay(motion.delay)) {
                    item.glass.frame = targets[index]
                } completion: { finished() }
            } else {
                item.glass.frame = targets[index]
                item.glass.layoutSubtreeIfNeeded()
                finished()
            }
        }
    }

    func start(_ activity: SimulatorToolActivity) {
        current = activity.id
        busy = true
        status.title = "사용 중 · " + activity.title
        argumentsLabel.stringValue = activity.source + " · " + activity.summary
        for item in components where actions[item.control] != nil {
            item.glass.tint = actionNames[item.control] == activity.action || actionNames[item.control] == activity.control ? .controlAccentColor : nil
        }
        updateInteraction()
    }
    func finish(_ activity: SimulatorToolActivity, response: [String: Any]) {
        if current == nil { start(activity) }
        guard current == activity.id else { return }
        busy = false
        if activity.source == "직접 조작" { manualPending = false }
        let failed = response["isError"] as? Bool == true
        let state = failed ? "실패" : "응답 완료"
        status.title = state + " · " + activity.title
        history.insert(state + " · " + activity.source + " · " + activity.title, at: 0)
        history = Array(history.prefix(8))
        recent.stringValue = history.joined(separator: "\n")
        let content = response["content"] as? [[String: Any]] ?? []
        result.string = activity.action == "window" && !failed ? "LCD 창 열림" : content.compactMap { $0["text"] as? String }.joined(separator: "\n")
        for child in images.arrangedSubviews { images.removeArrangedSubview(child); child.removeFromSuperview() }
        for item in content where item["type"] as? String == "image" {
            guard let encoded = item["data"] as? String, let data = Data(base64Encoded: encoded), let image = NSImage(data: data) else { continue }
            let picture = NSImageView()
            picture.image = image
            picture.imageScaling = .scaleProportionallyUpOrDown
            picture.setAccessibilityLabel("캡처 결과")
            picture.heightAnchor.constraint(equalToConstant: 180).isActive = true
            images.addArrangedSubview(picture)
            picture.widthAnchor.constraint(equalTo: images.widthAnchor).isActive = true
        }
        for item in components {
            item.glass.tint = failed && item.control === status ? .systemRed : nil
        }
        updateInteraction()
        let menu = NSMenu()
        if failed && activity.source == "직접 조작" && lastManual != nil {
            let retry = NSMenuItem(title: "같은 입력으로 재시도", action: #selector(retryLast), keyEquivalent: "")
            retry.target = self
            menu.addItem(retry)
            if lastManual?["action"] as? String == "type" {
                let paste = NSMenuItem(title: "같은 글자 붙여넣기…", action: #selector(recoverTextInput), keyEquivalent: "")
                paste.target = self
                menu.addItem(paste)
            }
        }
        status.menu = menu
        NSAccessibility.post(element: status, notification: .valueChanged)
    }
    func submitFromChrome(_ arguments: [String: Any]) { submit(arguments, fromChrome: true) }
    func showResponse() { showReport(status) }
    func showResponse(from anchor: NSView) {
        if report.isShown { report.close() }
        else { report.show(relativeTo: anchor.bounds, of: anchor, preferredEdge: .maxX) }
    }
    private func submit(_ arguments: [String: Any], fromChrome: Bool = false) {
        guard (fromChrome || acceptsInput), !busy, !manualPending else { return }
        lastManual = arguments
        manualPending = true
        status.title = "대기 중 · 직접 조작"
        updateInteraction()
        onRun(arguments)
    }
    @objc private func execute(_ sender: NSControl) {
        guard acceptsInput, sender.isEnabled, !busy, !manualPending else { return }
        do {
            guard let arguments = try actions[sender]?() else { return }
            if let action = arguments["action"] as? String, ["views", "paste"].contains(action), !confirmAction(action) { return }
            submit(arguments)
        } catch { fail(error) }
    }
    private func fail(_ error: Error) {
        status.title = "입력 오류"
        result.string = error.localizedDescription
        status.menu = nil
    }
    @objc private func retryLast() { if let lastManual { submit(lastManual) } }
    @objc private func recoverTextInput() {
        guard acceptsInput, let text = lastManual?["text"] as? String, !text.isEmpty, confirmAction("paste") else { return }
        submit(["action": "paste", "text": text])
    }
    @objc private func showReport(_ sender: NSButton) {
        guard sender.isEnabled else { return }
        if report.isShown { report.close() }
        else { report.show(relativeTo: sender.bounds, of: sender, preferredEdge: .maxX) }
    }
    private func configureReport() {
        let stack = NSStackView(views: [argumentsLabel])
        stack.orientation = .vertical
        stack.alignment = .leading
        stack.spacing = 10
        result.isEditable = false
        result.isSelectable = true
        result.font = .monospacedSystemFont(ofSize: 11, weight: .regular)
        result.isVerticallyResizable = true
        result.isHorizontallyResizable = false
        result.textContainer?.widthTracksTextView = true
        result.setAccessibilityLabel("도구 응답")
        let textScroll = NSScrollView()
        textScroll.hasVerticalScroller = true
        textScroll.documentView = result
        textScroll.heightAnchor.constraint(equalToConstant: 220).isActive = true
        stack.addArrangedSubview(textScroll)
        images.orientation = .vertical
        images.alignment = .leading
        stack.addArrangedSubview(images)
        recent.font = .systemFont(ofSize: 11)
        stack.addArrangedSubview(recent)
        let scroll = NSScrollView(frame: CGRect(x: 0, y: 0, width: 380, height: 500))
        scroll.hasVerticalScroller = true
        scroll.documentView = stack
        stack.translatesAutoresizingMaskIntoConstraints = false
        NSLayoutConstraint.activate([stack.widthAnchor.constraint(equalTo: scroll.contentView.widthAnchor, constant: -24),
                                     stack.leadingAnchor.constraint(equalTo: scroll.contentView.leadingAnchor, constant: 12),
                                     stack.topAnchor.constraint(equalTo: scroll.contentView.topAnchor, constant: 12)])
        for child in stack.arrangedSubviews { child.widthAnchor.constraint(equalTo: stack.widthAnchor).isActive = true }
        let controller = NSViewController()
        controller.view = scroll
        report.contentViewController = controller
        report.behavior = .transient
    }
    private static func confirm(_ action: String) -> Bool {
        let alert = NSAlert()
        alert.messageText = action == "views" ? "전면 앱을 잠시 정지하고 검사할까요?" : "기기에 붙여넣을까요?"
        alert.informativeText = action == "views" ? "UIView 검사 동안 앱이 약 20초간 멈춥니다." : "Mac과 부팅된 다른 기기의 클립보드에도 전달됩니다. iOS에서 붙여넣기 허용이 필요할 수 있습니다."
        alert.addButton(withTitle: "실행")
        alert.addButton(withTitle: "취소")
        return alert.runModal() == .alertFirstButtonReturn
    }
}
