import AppKit

/// A contact is performed by the control itself: click, hold or drag, without a coordinate form.
final class SimulatorGesturePad: NSControl {
    let fingers: Int
    var screenSize = CGSize(width: 1, height: 1)
    var frames: [[String: Any]] = []
    var onError: (Error) -> Void = { _ in }
    private var start: CGPoint?
    private var started: TimeInterval = 0

    init(fingers: Int) {
        self.fingers = fingers
        super.init(frame: .zero)
        focusRingType = .exterior
        setAccessibilityElement(true)
        setAccessibilityRole(.button)
        setAccessibilityLabel("\(fingers)손가락 · 누르기 또는 드래그")
        toolTip = "\(fingers)손가락으로 누르거나 드래그 · Space: 화면 중앙 누르기"
    }
    required init?(coder: NSCoder) { fatalError() }
    override var acceptsFirstResponder: Bool { true }
    override var isFlipped: Bool { true }
    override func draw(_ dirtyRect: NSRect) {
        let compact = bounds.height < 42 || bounds.width < 80
        let text = (compact ? "\(fingers)손가락" : "\(fingers)손가락\n누르기 · 드래그") as NSString
        let style = NSMutableParagraphStyle()
        style.alignment = .center
        text.draw(in: bounds.insetBy(dx: 2, dy: compact ? max(0, (bounds.height - 14) / 2) : 6), withAttributes: [.font: NSFont.systemFont(ofSize: 11),
            .foregroundColor: isEnabled ? NSColor.labelColor : .disabledControlTextColor, .paragraphStyle: style])
    }
    private func point(_ event: NSEvent) -> CGPoint {
        let p = convert(event.locationInWindow, from: nil)
        return CGPoint(x: min(max(0, p.x / max(1, bounds.width)), 1) * max(0, screenSize.width - 1 - CGFloat(fingers - 1) * 24),
                       y: min(max(0, p.y / max(1, bounds.height)), 1) * max(0, screenSize.height - 1))
    }
    override func mouseDown(with event: NSEvent) {
        guard isEnabled else { return }
        window?.makeFirstResponder(self)
        start = point(event)
        started = event.timestamp
    }
    override func mouseUp(with event: NSEvent) {
        guard isEnabled, let from = start else { start = nil; return }
        start = nil
        let to = point(event)
        perform(from: from, to: hypot(to.x - from.x, to.y - from.y) > 3 ? to : nil, seconds: min(10, max(0.05, event.timestamp - started)))
    }
    func perform(from: CGPoint, to: CGPoint?, seconds: Double) {
        guard isEnabled else { return }
        do {
            frames = try simulatorToolboxContacts(from: from, to: to, fingers: fingers, seconds: seconds, screen: screenSize)
            sendAction(action, to: target)
        } catch { onError(error) }
    }
    override func accessibilityPerformPress() -> Bool {
        guard isEnabled else { return false }
        perform(from: CGPoint(x: max(0, (screenSize.width - CGFloat(fingers - 1) * 24) / 2), y: screenSize.height / 2), to: nil, seconds: 0.1)
        return true
    }
    override func keyDown(with event: NSEvent) {
        if event.keyCode == 0x31 || event.keyCode == 0x24 { _ = accessibilityPerformPress() }
        else { super.keyDown(with: event) }
    }
}
