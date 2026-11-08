import AppKit

/// One material per component, batched by the shared native container.
final class SimulatorGlassView: NSView {
    let content: NSView
    private let effect: NSView
    private let solid = NSView()
    private var solidMode = false
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
        solid.wantsLayer = true
        addSubview(solid)
        NSWorkspace.shared.notificationCenter.addObserver(self, selector: #selector(updateStyle), name: NSWorkspace.accessibilityDisplayOptionsDidChangeNotification, object: nil)
        setAccessibilityElement(false)
        updateStyle()
    }
    required init?(coder: NSCoder) { fatalError() }
    deinit { NSWorkspace.shared.notificationCenter.removeObserver(self) }
    override func viewDidChangeEffectiveAppearance() { super.viewDidChangeEffectiveAppearance(); updateStyle() }
    @objc private func updateStyle() {
        let radius = min(cornerRadius, min(bounds.width, bounds.height) / 2)
        let opaque = NSWorkspace.shared.accessibilityDisplayShouldReduceTransparency
        effect.isHidden = opaque
        solid.isHidden = !opaque
        if solidMode != opaque {
            solidMode = opaque
            if #available(macOS 26, *), let glass = effect as? NSGlassEffectView {
                glass.contentView = opaque ? nil : content
            }
            if opaque { solid.addSubview(content) }
            else if #available(macOS 26, *), effect is NSGlassEffectView {}
            else { effect.addSubview(content) }
        }
        solid.layer?.backgroundColor = NSColor.windowBackgroundColor.cgColor
        solid.layer?.cornerRadius = radius
        layer?.cornerRadius = radius
        layer?.borderWidth = NSWorkspace.shared.accessibilityDisplayShouldIncreaseContrast ? 2 : 0.5
        layer?.borderColor = NSColor.labelColor.withAlphaComponent(NSWorkspace.shared.accessibilityDisplayShouldIncreaseContrast ? 0.8 : 0.18).cgColor
        if #available(macOS 26, *), let glass = effect as? NSGlassEffectView {
            glass.cornerRadius = radius
            glass.tintColor = tint
        } else {
            effect.wantsLayer = true
            effect.layer?.cornerRadius = radius
            effect.layer?.masksToBounds = true
        }
    }
    override func resizeSubviews(withOldSize oldSize: NSSize) {
        super.resizeSubviews(withOldSize: oldSize)
        needsLayout = true
    }
    override func layout() {
        super.layout()
        effect.frame = bounds
        solid.frame = bounds
        content.frame = bounds
        updateStyle()
        layoutContent?(bounds)
    }
}

final class SimulatorLCDContentView: NSView {
    let lcd: NSView
    let tools: SimulatorToolboxView
    let deviceAppearance: SimulatorDeviceAppearance
    let body: SimulatorDeviceBodyView
    let chrome = SimulatorDeviceChrome()
    private let canvas = NSView()
    private let container: NSView
    private var transitioning = false
    var screen = CGSize(width: 1, height: 1)
    var screenCornerFraction: CGFloat = 0.08
    var externalToolbar = false
    var toolsVisible = false
    var focused = false
    var lcdSizeLimit: CGSize?
    var opaqueFrames: [CGRect] {
        var frames = [body.frame]
        if NSWorkspace.shared.accessibilityDisplayShouldReduceTransparency {
            frames += [chrome.handle.frame] + (focused || externalToolbar ? [] : [chrome.controls.frame, chrome.rail.frame])
            frames += !externalToolbar && !tools.isHidden ? tools.clippedGlassFrames.map { tools.convert($0, to: self) } : []
        }
        return frames
    }

    init(lcd: NSView, tools: SimulatorToolboxView, appearance: SimulatorDeviceAppearance) {
        self.lcd = lcd
        self.tools = tools
        self.deviceAppearance = appearance
        body = SimulatorDeviceBodyView()
        body.addSubview(lcd)
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
        for view in [chrome.handle, chrome.controls, chrome.rail, chrome.resize] { canvas.addSubview(view) }
        tools.isHidden = true
    }
    required init?(coder: NSCoder) { fatalError() }

    func animateTools(_ expanded: Bool, animated: Bool = true, completion: @escaping () -> Void) {
        if externalToolbar {
            toolsVisible = expanded
            completion()
            return
        }
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

    /// Ignore the transparent envelope; visible components alone can receive pointer events.
    override func hitTest(_ point: NSPoint) -> NSView? {
        let p = convert(point, from: superview)
        guard bounds.contains(p) else { return nil }
        let children: [NSView] = externalToolbar ? [chrome.resize, chrome.handle, body] : [chrome.resize, chrome.handle, chrome.controls, chrome.rail, body, tools]
        for child in children where !child.isHidden {
            let local = child.convert(p, from: self)
            if child === tools {
                guard tools.clippedGlassFrames.contains(where: { $0.contains(local) }) else { continue }
            } else {
                let radius: CGFloat = child === body ? body.cornerRadius : (child.layer?.cornerRadius ?? 0)
                guard NSBezierPath(roundedRect: child.bounds, xRadius: radius, yRadius: radius).contains(local) else { continue }
            }
            return child.hitTest(child.superview!.convert(p, from: self))
        }
        return nil
    }
    override func resizeSubviews(withOldSize oldSize: NSSize) {
        super.resizeSubviews(withOldSize: oldSize)
        needsLayout = true
    }
    override func layout() {
        super.layout()
        container.frame = bounds
        canvas.frame = bounds
        let geometry = simulatorDeviceLayout(in: bounds.size, screen: screen, bezel: deviceAppearance.bezel, toolsVisible: !externalToolbar && (toolsVisible || transitioning), focused: focused, lcdSizeLimit: lcdSizeLimit, externalToolbar: externalToolbar)
        body.frame = geometry.body
        body.cornerRadius = min(geometry.lcd.width, geometry.lcd.height) * screenCornerFraction + deviceAppearance.bezel
        chrome.handle.frame = geometry.handle
        if !externalToolbar {
            chrome.controls.frame = geometry.controls
            chrome.controls.isHidden = focused
            chrome.rail.frame = geometry.rail
            chrome.rail.isHidden = focused
        }
        chrome.resize.frame = geometry.resize
        chrome.resize.isHidden = focused
        lcd.wantsLayer = true
        lcd.layer?.cornerRadius = min(geometry.lcd.width, geometry.lcd.height) * screenCornerFraction
        lcd.layer?.masksToBounds = true
        body.layoutSubtreeIfNeeded()
        lcd.frame = CGRect(origin: CGPoint(x: deviceAppearance.bezel, y: deviceAppearance.bezel), size: geometry.lcd.size)
        if !externalToolbar {
            tools.frame = geometry.tools
            tools.retractionLCD = tools.convert(geometry.lcd, from: self)
        }
        if #available(macOS 26, *), let glass = container as? NSGlassEffectContainerView { glass.spacing = tools.glassSpacing }
    }
}

/// The device is opaque. Only surrounding controls use system glass.
final class SimulatorDeviceBodyView: NSView {
    var cornerRadius: CGFloat = 30 { didSet { updateStyle() } }
    override init(frame: CGRect) {
        super.init(frame: frame)
        wantsLayer = true
        clipsToBounds = false
        NSWorkspace.shared.notificationCenter.addObserver(self, selector: #selector(updateStyle), name: NSWorkspace.accessibilityDisplayOptionsDidChangeNotification, object: nil)
        updateStyle()
    }
    required init?(coder: NSCoder) { fatalError() }
    deinit { NSWorkspace.shared.notificationCenter.removeObserver(self) }
    @objc private func updateStyle() {
        layer?.backgroundColor = NSColor(white: 0.075, alpha: 1).cgColor
        layer?.cornerRadius = cornerRadius
        layer?.borderWidth = NSWorkspace.shared.accessibilityDisplayShouldIncreaseContrast ? 2 : 1
        layer?.borderColor = NSColor(white: 0.65, alpha: 1).cgColor
        layer?.shadowColor = NSColor.black.cgColor
        layer?.shadowOpacity = 0.3
        layer?.shadowRadius = 12
        layer?.shadowOffset = CGSize(width: 0, height: -4)
    }
    override func layout() {
        super.layout()
        layer?.shadowPath = CGPath(roundedRect: bounds, cornerWidth: cornerRadius, cornerHeight: cornerRadius, transform: nil)
    }
}
