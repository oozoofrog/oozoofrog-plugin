import AppKit

/// One material per component, batched by the shared native container.
final class SimulatorGlassView: NSView {
    let content: NSView
    private let effect: NSView
    var layoutContent: ((CGRect) -> Void)?
    var cornerRadius: CGFloat = 22 { didSet { updateStyle() } }
    var tint: NSColor? { didSet { updateStyle() } }

    init(content: NSView, interactive: Bool = true) {
        self.content = content
        if #available(macOS 26, *) {
            let glass = NSGlassEffectView()
            glass.style = .regular
            if #available(macOS 27, *) { glass.effectIsInteractive = interactive }
            glass.contentView = content
            effect = glass
        } else {
            let material = NSVisualEffectView()
            material.material = .hudWindow
            material.blendingMode = .behindWindow
            material.addSubview(content)
            effect = material
        }
        super.init(frame: .zero)
        wantsLayer = true
        clipsToBounds = false
        addSubview(effect)
        setAccessibilityElement(false)
        updateStyle()
    }
    required init?(coder: NSCoder) { fatalError() }
    private func updateStyle() {
        let radius = min(cornerRadius, min(bounds.width, bounds.height) / 2)
        if #available(macOS 26, *), let glass = effect as? NSGlassEffectView {
            glass.cornerRadius = radius
            glass.tintColor = tint
        } else {
            effect.wantsLayer = true
            effect.layer?.cornerRadius = radius
        }
    }
    override func resizeSubviews(withOldSize oldSize: NSSize) {
        super.resizeSubviews(withOldSize: oldSize)
        needsLayout = true
    }
    override func layout() {
        super.layout()
        effect.frame = bounds
        content.frame = bounds
        updateStyle()
        layoutContent?(bounds)
    }
}

final class SimulatorLCDContentView: NSView {
    let lcd: NSView
    let tools: SimulatorToolboxView
    let deviceAppearance: SimulatorDeviceAppearance
    let body: SimulatorGlassView
    private let canvas = NSView()
    private let container: NSView
    private var transitioning = false
    var screen = CGSize(width: 1, height: 1)
    var screenCornerFraction: CGFloat = 0.08
    var toolsVisible = false
    var opaqueFrames: [CGRect] {
        if NSWorkspace.shared.accessibilityDisplayShouldReduceTransparency {
            return [body.frame] + (!tools.isHidden ? tools.clippedGlassFrames.map { tools.convert($0, to: self) } : [])
        }
        return [lcd.convert(lcd.bounds, to: self)]
    }

    init(lcd: NSView, tools: SimulatorToolboxView, appearance: SimulatorDeviceAppearance) {
        self.lcd = lcd
        self.tools = tools
        self.deviceAppearance = appearance
        let bezel = NSView()
        bezel.addSubview(lcd)
        body = SimulatorGlassView(content: bezel, interactive: false)
        if #available(macOS 26, *) {
            let glass = NSGlassEffectContainerView()
            glass.spacing = 18
            glass.contentView = canvas
            container = glass
        } else { container = canvas }
        super.init(frame: lcd.frame)
        clipsToBounds = false
        addSubview(container)
        canvas.addSubview(tools)
        canvas.addSubview(body)
        tools.isHidden = true
    }
    required init?(coder: NSCoder) { fatalError() }

    func animateTools(_ expanded: Bool, animated: Bool = true, completion: @escaping () -> Void) {
        if let responder = window?.firstResponder as? NSView,
           responder.isDescendant(of: tools) || responder === tools || responder === window?.fieldEditor(false, for: nil) {
            window?.makeFirstResponder(lcd)
        }
        toolsVisible = expanded
        tools.isHidden = false
        transitioning = true
        needsLayout = true
        layoutSubtreeIfNeeded()
        tools.animateExpansion(expanded, animated: animated) { [weak self] in
            guard let self, self.toolsVisible == expanded else { return }
            self.transitioning = false
            self.tools.isHidden = !expanded
            completion()
        }
    }

    override func resizeSubviews(withOldSize oldSize: NSSize) {
        super.resizeSubviews(withOldSize: oldSize)
        needsLayout = true
    }
    override func layout() {
        super.layout()
        container.frame = bounds
        canvas.frame = bounds
        let geometry = simulatorDeviceLayout(in: bounds.size, screen: screen, bezel: deviceAppearance.bezel, toolsVisible: toolsVisible || transitioning)
        body.frame = geometry.body
        body.cornerRadius = min(geometry.lcd.width, geometry.lcd.height) * screenCornerFraction + deviceAppearance.bezel
        body.layoutSubtreeIfNeeded()
        lcd.frame = CGRect(origin: CGPoint(x: deviceAppearance.bezel, y: deviceAppearance.bezel), size: geometry.lcd.size)
        tools.frame = geometry.tools
        tools.retractionLCD = tools.convert(geometry.lcd, from: self)
        if #available(macOS 26, *), let glass = container as? NSGlassEffectContainerView { glass.spacing = tools.glassSpacing }
    }
}
