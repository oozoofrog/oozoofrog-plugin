// The simulator tool's window action: a booted simulator's screen, live, in a window of mac-cu, without Device Hub
// or Simulator.app.
//
// Undocumented parts: CoreSimulator's SimDeviceIOClient (SimDevice io) lists the io ports; the descriptor of a screen's
// port (SimDisplayIOSurfaceRenderable, SimDisplayRenderable) gives its framebuffer IOSurface, the same memory the
// simulator draws into, and calls back when pixels or surfaces change. The ports are proxies of CoreSimulatorService
// objects (ROCKRemoteProxy): they answer messages, not key-value coding.

import AppKit

/// The screens of a booted simulator that have a framebuffer (the descriptors of its io ports).
func framebufferScreens(of device: NSObject) -> [NSObject] {
    let ports = (device.value(forKey: "io") as? NSObject)?.value(forKey: "ioPorts") as? [NSObject] ?? []
    return ports.compactMap { $0.perform(NSSelectorFromString("descriptor"))?.takeUnretainedValue() as? NSObject }
        .filter { $0.responds(to: NSSelectorFromString("framebufferSurface")) && framebuffer(of: $0) != nil }
}

/// The framebuffer of a screen: its pixels before rotation.
func framebuffer(of screen: NSObject) -> IOSurfaceRef? {
    guard let object = screen.perform(NSSelectorFromString("framebufferSurface"))?.takeUnretainedValue() else { return nil }
    return (object as! IOSurfaceRef)
}

/// The framebuffer screen that shows active (matched by its proportions before rotation), or the largest one when the
/// device has one screen that is not turned.
func shownScreen(of device: NSObject, active: ActiveScreen?) -> NSObject? {
    let screens = framebufferScreens(of: device)
    func size(_ screen: NSObject) -> CGSize {
        framebuffer(of: screen).map { CGSize(width: IOSurfaceGetWidth($0), height: IOSurfaceGetHeight($0)) } ?? .zero
    }
    if let active {
        let match = screens.first { screen in
            let pixels = size(screen)
            return abs(pixels.width / active.unrotated.width - pixels.height / active.unrotated.height) < 0.02
        }
        if let match { return match }
    }
    return screens.max { size($0).width * size($0).height < size($1).width * size($1).height }
}

/// Mac virtual key codes (kVK_*) to USB HID keyboard usages (page 7): the keys as they are, so the simulator's own
/// keyboard layout (US, Korean two-set...) makes the characters. The Mac's input method is not used.
let hidUsages: [UInt16: UInt64] = [
    0x00: 0x04, 0x0B: 0x05, 0x08: 0x06, 0x02: 0x07, 0x0E: 0x08, 0x03: 0x09, 0x05: 0x0A, 0x04: 0x0B, 0x22: 0x0C, 0x26: 0x0D,
    0x28: 0x0E, 0x25: 0x0F, 0x2E: 0x10, 0x2D: 0x11, 0x1F: 0x12, 0x23: 0x13, 0x0C: 0x14, 0x0F: 0x15, 0x01: 0x16, 0x11: 0x17,
    0x20: 0x18, 0x09: 0x19, 0x0D: 0x1A, 0x07: 0x1B, 0x10: 0x1C, 0x06: 0x1D,                       // a to z
    0x12: 0x1E, 0x13: 0x1F, 0x14: 0x20, 0x15: 0x21, 0x17: 0x22, 0x16: 0x23, 0x1A: 0x24, 0x1C: 0x25, 0x19: 0x26, 0x1D: 0x27,  // 1 to 0
    0x24: 0x28, 0x35: 0x29, 0x33: 0x2A, 0x30: 0x2B, 0x31: 0x2C, 0x1B: 0x2D, 0x18: 0x2E, 0x21: 0x2F, 0x1E: 0x30, 0x2A: 0x31,
    0x29: 0x33, 0x27: 0x34, 0x32: 0x35, 0x2B: 0x36, 0x2F: 0x37, 0x2C: 0x38, 0x39: 0x39, 0x0A: 0x64,  // Return ... Caps Lock, ISO §
    0x7A: 0x3A, 0x78: 0x3B, 0x63: 0x3C, 0x76: 0x3D, 0x60: 0x3E, 0x61: 0x3F, 0x62: 0x40, 0x64: 0x41, 0x65: 0x42, 0x6D: 0x43,
    0x67: 0x44, 0x6F: 0x45,                                                                        // F1 to F12
    0x73: 0x4A, 0x74: 0x4B, 0x75: 0x4C, 0x77: 0x4D, 0x79: 0x4E, 0x7C: 0x4F, 0x7B: 0x50, 0x7D: 0x51, 0x7E: 0x52,  // Home ... Up
    0x47: 0x53, 0x4B: 0x54, 0x43: 0x55, 0x4E: 0x56, 0x45: 0x57, 0x4C: 0x58, 0x53: 0x59, 0x54: 0x5A, 0x55: 0x5B, 0x56: 0x5C,
    0x57: 0x5D, 0x58: 0x5E, 0x59: 0x5F, 0x5B: 0x60, 0x5C: 0x61, 0x52: 0x62, 0x41: 0x63, 0x51: 0x67,  // keypad
    0x66: 0x91, 0x68: 0x90,                                                                        // JIS Eisu, Kana (LANG2, LANG1)
    0x3B: 0xE0, 0x38: 0xE1, 0x3A: 0xE2, 0x37: 0xE3, 0x3E: 0xE4, 0x3C: 0xE5, 0x3D: 0xE6, 0x36: 0xE7,  // modifiers, left then right
]

/// The view that draws the framebuffer turned as the screen is shown, fitted to the window, and passes the Mac's
/// mouse, keyboard and scroll events to the simulator.
final class SimulatorScreenView: NSView {
    let screenLayer = CALayer()
    let touchOverlay = SimulatorTouchOverlay()
    var rotation = "rot0" { didSet { needsLayout = true } }
    var pixels = CGSize(width: 1, height: 1) { didSet { needsLayout = true } }
    weak var owner: SimulatorWindow?
    /// The simulator's screen in points as shown.
    var shownPoints = CGSize(width: 1, height: 1)
    var deviceMask: SimulatorDeviceMask? { didSet { needsLayout = true } }

    override init(frame: NSRect) {
        super.init(frame: frame)
        wantsLayer = true
        layer!.backgroundColor = NSColor.black.cgColor
        screenLayer.contentsGravity = .resize
        screenLayer.magnificationFilter = .linear
        layer!.addSublayer(screenLayer)
        layer!.addSublayer(touchOverlay.layer)
    }
    required init?(coder: NSCoder) { fatalError() }

    var turned: Bool { rotation == "rot90" || rotation == "rot270" }

    override func layout() {
        super.layout()
        let shown = turned ? CGSize(width: pixels.height, height: pixels.width) : pixels
        let scale = min(bounds.width / shown.width, bounds.height / shown.height)
        CATransaction.begin()
        CATransaction.setDisableActions(true)
        screenLayer.bounds = CGRect(x: 0, y: 0, width: pixels.width * scale, height: pixels.height * scale)
        screenLayer.position = CGPoint(x: bounds.midX, y: bounds.midY)
        // rotN turns the framebuffer N degrees clockwise on the screen; the layer's angles go counterclockwise.
        let degrees: [String: CGFloat] = ["rot90": -90, "rot180": 180, "rot270": 90]
        screenLayer.setAffineTransform(CGAffineTransform(rotationAngle: (degrees[rotation] ?? 0) * .pi / 180))
        if let deviceMask {
            let mask = layer!.mask ?? CALayer()
            mask.contents = deviceMask.image
            mask.bounds = CGRect(origin: .zero, size: turned ? CGSize(width: bounds.height, height: bounds.width) : bounds.size)
            mask.position = CGPoint(x: bounds.midX, y: bounds.midY)
            mask.setAffineTransform(CGAffineTransform(rotationAngle: (degrees[rotation] ?? 0) * .pi / 180))
            layer!.mask = mask
        } else { layer!.mask = nil }
        touchOverlay.layout(viewport: bounds, screen: shownPoints)
        CATransaction.commit()
    }

    // MARK: Input

    override var acceptsFirstResponder: Bool { true }
    override func acceptsFirstMouse(for event: NSEvent?) -> Bool { true }

    /// View points per screen point.
    var scale: CGFloat { min(bounds.width / shownPoints.width, bounds.height / shownPoints.height) }

    /// A point of this view in points of the simulator's screen as shown; nil outside the screen unless clamped.
    func screenPoint(_ event: NSEvent, clamp: Bool) -> CGPoint? {
        let p = convert(event.locationInWindow, from: nil)  // From the bottom left.
        let left = bounds.midX - shownPoints.width * scale / 2, bottom = bounds.midY - shownPoints.height * scale / 2
        var s = CGPoint(x: (p.x - left) / scale, y: shownPoints.height - (p.y - bottom) / scale)
        if clamp {
            s = CGPoint(x: min(max(s.x, 0), shownPoints.width), y: min(max(s.y, 0), shownPoints.height))
        } else if !CGRect(origin: .zero, size: shownPoints).contains(s) {
            return nil
        }
        if !clamp, let deviceMask, !deviceMask.contains(s, size: shownPoints, rotation: rotation) { return nil }
        return s
    }

    // Mouse: one finger; with Option held when the button goes down, two fingers mirrored about the screen's center
    // (pinch and rotate, as Simulator.app does).
    var touching = false, twoFingers = false

    func fingers(_ event: NSEvent, clamp: Bool) -> (CGPoint, CGPoint?)? {
        guard let p = screenPoint(event, clamp: clamp) else { return nil }
        return (p, twoFingers ? CGPoint(x: shownPoints.width - p.x, y: shownPoints.height - p.y) : nil)
    }

    override func mouseDown(with event: NSEvent) {
        window?.makeFirstResponder(self)  // The click makes the window key; the keyboard then comes here.
        twoFingers = event.modifierFlags.contains(.option)
        guard let (p, q) = fingers(event, clamp: false) else { return }
        touching = true
        owner?.touch(p, q, phase: 0)
    }

    override func mouseDragged(with event: NSEvent) {
        guard touching, let (p, q) = fingers(event, clamp: true) else { return }
        owner?.touch(p, q, phase: 1)
    }

    override func mouseUp(with event: NSEvent) {
        guard touching, let (p, q) = fingers(event, clamp: true) else { return }
        touching = false
        owner?.touch(p, q, phase: 2)
    }

    // Keyboard: the keys as they are, held while the Mac key is held (iOS repeats a held key itself).

    /// Shift-Command-H: the home button; Shift-Command-L: the lock button (as Simulator.app's Home and Lock, which use
    /// Command-L; with Shift here so that Command-L still reaches apps such as Safari).
    func button(for event: NSEvent) -> UInt64? {
        guard event.modifierFlags.intersection(.deviceIndependentFlagsMask).subtracting(.capsLock) == [.command, .shift] else { return nil }
        return [0x04: 0x40, 0x25: 0x30][event.keyCode]
    }

    override func keyDown(with event: NSEvent) {
        if event.isARepeat { return }
        if let button = button(for: event) { owner?.button(button); return }
        guard let usage = hidUsages[event.keyCode] else { return }
        owner?.key(usage, down: true)
        // The Mac sends no key up for a key pressed with Command held: release it now.
        if event.modifierFlags.contains(.command) { owner?.key(usage, down: false) }
    }

    override func keyUp(with event: NSEvent) {
        if event.keyCode == 0x11, event.modifierFlags.intersection(.deviceIndependentFlagsMask) == [.command, .shift] { return }
        guard button(for: event) == nil, let usage = hidUsages[event.keyCode] else { return }
        owner?.key(usage, down: false)
    }

    /// Command keys come here before keyDown; the window takes them all, so no Mac shortcut runs while it is in front.
    override func performKeyEquivalent(with event: NSEvent) -> Bool {
        guard window?.firstResponder === self, event.type == .keyDown else { return false }
        if event.keyCode == 0x11, event.modifierFlags.intersection(.deviceIndependentFlagsMask) == [.command, .shift] {
            owner?.toggleToolbox()
            return true
        }
        keyDown(with: event)
        return true
    }

    override func flagsChanged(with event: NSEvent) {
        guard let usage = hidUsages[event.keyCode] else { return }
        if event.keyCode == 0x39 {  // Caps Lock: one press for each change (it switches the input language on iOS when set so).
            owner?.key(usage, down: true)
            owner?.key(usage, down: false)
            return
        }
        let flags: [UInt16: NSEvent.ModifierFlags] = [0x38: .shift, 0x3C: .shift, 0x3B: .control, 0x3E: .control,
                                                      0x3A: .option, 0x3D: .option, 0x37: .command, 0x36: .command]
        owner?.key(usage, down: event.modifierFlags.contains(flags[event.keyCode] ?? []))
    }

    override func resignFirstResponder() -> Bool {
        owner?.releaseKeys()
        return super.resignFirstResponder()
    }

    // Scroll: a finger drag (trackpad: down when the gesture begins, up when it ends; mouse wheel: one short drag for
    // each notch). Apple Watch: the Digital Crown. Momentum events are left out: iOS makes its own after the finger lifts.
    var scrollFinger: CGPoint?

    override func scrollWheel(with event: NSEvent) {
        guard event.momentumPhase.isEmpty, let owner else { return }
        let precise = event.hasPreciseScrollingDeltas
        let dx = event.scrollingDeltaX * (precise ? 1 : 10) / scale, dy = event.scrollingDeltaY * (precise ? 1 : 10) / scale
        if owner.isWatch {
            if event.phase.isEmpty { owner.crown(nil, dy) } else { owner.crown(UInt64(event.phase.rawValue), dy) }
            return
        }
        func clamped(_ p: CGPoint) -> CGPoint {
            CGPoint(x: min(max(p.x, 0), shownPoints.width), y: min(max(p.y, 0), shownPoints.height))
        }
        switch event.phase {
        case .began:
            guard let p = screenPoint(event, clamp: false) else { return }
            scrollFinger = p
            owner.touch(p, nil, phase: 0)
        case .changed:
            guard let p = scrollFinger else { return }
            scrollFinger = clamped(CGPoint(x: p.x + dx, y: p.y + dy))
            owner.touch(scrollFinger!, nil, phase: 1)
        case .ended, .cancelled:
            guard let p = scrollFinger else { return }
            scrollFinger = nil
            owner.touch(p, nil, phase: 2)
        default:
            guard event.phase.isEmpty, let p = screenPoint(event, clamp: false) else { return }
            // iOS takes a drag only once the finger has moved about 10 points (GestureProbe: notches of 1 to 9 points
            // were not pans, 16 and more were); add them, so that a slow notch scrolls too and a scroll view moves by the notch.
            let length = hypot(dx, dy), stretch = length > 0 ? 1 + 10 / length : 1
            owner.drag(from: p, to: clamped(CGPoint(x: p.x + dx * stretch, y: p.y + dy * stretch)))
        }
    }
}

/// One simulator's window. Main thread only, except refresh(), which reads CoreDevice off it.
final class SimulatorWindow: NSObject, NSWindowDelegate {
    let id: String  // the simulator's UDID
    let device: NSObject
    let window: NSWindow
    let view: SimulatorScreenView
    let toolbox: SimulatorToolboxView
    let content: SimulatorLCDContentView
    private let toolboxToggle = NSButton(title: "도구", target: nil, action: nil)
    let token = NSUUID()
    var screen: NSObject?
    var surface: IOSurfaceRef?
    var active: ActiveScreen?
    var touchesActive = false
    var preview: SimulatorPreviewWindow?
    var previewView: SimulatorScreenView?
    var drawPending = false
    var timer: Timer?
    private var displayRefresh = SimulatorDisplayRefresh()
    private var deviceMasks: [String: SimulatorDeviceMask] = [:]
    private var angleRefreshPending = false
    var isWatch = false
    /// Keyboard usages the simulator holds down now (main thread).
    var heldKeys: Set<UInt64> = []

    init(device: NSObject, active: ActiveScreen?) {
        self.device = device
        id = udid(of: device)
        let points = active?.points ?? screenSize(of: device)
        let visible = NSScreen.main?.visibleFrame.size ?? CGSize(width: 1200, height: 800)
        // Points at their size, smaller to fit the Mac screen, and larger for a small screen (Apple Watch) up to 420 high.
        let fit = min(max(1, 420 / points.height), visible.height * 0.85 / points.height, visible.width * 0.85 / points.width)
        view = SimulatorScreenView(frame: NSRect(x: 0, y: 0, width: points.width * fit, height: points.height * fit))
        let watch = ((device.value(forKey: "runtime") as? NSObject)?.value(forKey: "name") as? String ?? "").hasPrefix("watchOS")
        toolbox = SimulatorToolboxView(deviceName: device.value(forKey: "name") as? String ?? "Simulator", isWatch: watch)
        content = SimulatorLCDContentView(lcd: view, tools: toolbox, appearance: simulatorDeviceAppearance(device))
        window = NSWindow(contentRect: view.frame, styleMask: [.titled, .closable, .resizable, .miniaturizable],
                          backing: .buffered, defer: false)
        super.init()
        window.isReleasedWhenClosed = false
        window.isOpaque = false
        window.backgroundColor = .clear
        window.titlebarAppearsTransparent = true
        window.hasShadow = false
        window.collectionBehavior.insert(.moveToActiveSpace)
        window.contentView = content
        view.owner = self
        window.makeFirstResponder(view)  // Keys typed in the window go to the simulator without a click first.
        isWatch = watch
        toolbox.onRun = { [weak self] arguments in
            guard let self else { return }
            handleQueue.async {
                let previous = currentSession
                currentSession = nil
                defer { currentSession = previous }
                let activity = SimulatorToolActivity(arguments: arguments, source: "직접 조작")
                _ = try? executeSimulatorCommand(arguments, device: self.device, activity: activity)
            }
        }
        toolboxToggle.target = self
        toolboxToggle.action = #selector(toggleToolbox)
        toolboxToggle.setButtonType(.toggle)
        toolboxToggle.image = NSImage(systemSymbolName: "slider.horizontal.3", accessibilityDescription: nil)
        toolboxToggle.imagePosition = .imageLeading
        toolboxToggle.toolTip = "도구 · ⇧⌘T"
        toolboxToggle.setAccessibilityLabel("도구")
        let accessory = NSTitlebarAccessoryViewController()
        accessory.layoutAttribute = .right
        toolboxToggle.frame = NSRect(x: 0, y: 0, width: 76, height: 24)
        accessory.view = toolboxToggle
        window.addTitlebarAccessoryViewController(accessory)
        window.delegate = self
        window.center()
        show(active)
        resizeLCD(CGSize(width: points.width * fit, height: points.height * fit))
        if UserDefaults.standard.bool(forKey: "simulatorToolbox.\(id)") { toggleToolbox() }
        // shortcut: folds and turns are read from CoreDevice every 2 seconds (0.15 s each); use the screen's
        // displayPropertiesChanged callback if this lags or costs too much.
        timer = Timer.scheduledTimer(withTimeInterval: 2, repeats: true) { [weak self] _ in self?.refresh() }
    }

    /// Shows the framebuffer of the screen that is on, turned as it is shown.
    func show(_ active: ActiveScreen?) {
        displayRefresh.changed()
        let previous = view.shownPoints
        if self.active?.id != active?.id || self.active?.rotation != active?.rotation {
            view.touchOverlay.clear()
            previewView?.touchOverlay.clear()
        }
        self.active = active
        let next = shownScreen(of: device, active: active)
        if next !== screen {
            stopCallbacks()
            screen = next
            startCallbacks()
        }
        surface = screen.flatMap(framebuffer(of:))
        view.screenLayer.contents = surface
        if let surface { view.pixels = CGSize(width: IOSurfaceGetWidth(surface), height: IOSurfaceGetHeight(surface)) }
        view.rotation = active?.rotation ?? "rot0"
        let points = active?.points ?? screenSize(of: device)
        view.shownPoints = points
        content.screen = points
        let maskKey = active?.id ?? "main"
        if deviceMasks[maskKey] == nil { deviceMasks[maskKey] = content.deviceAppearance.mask(for: points, rotation: view.rotation) }
        view.deviceMask = deviceMasks[maskKey]
        if let mask = view.deviceMask {
            content.screenCornerFraction = mask.cornerFraction * CGFloat(mask.bitmap.pixelsWide) / CGFloat(min(mask.bitmap.pixelsWide, mask.bitmap.pixelsHigh))
        } else { content.screenCornerFraction = content.deviceAppearance.fallbackCorner / min(points.width, points.height) }
        view.needsLayout = true
        if previous != points && previous.width > 1 && previous.height > 1 {
            let scale = min(view.bounds.width / previous.width, view.bounds.height / previous.height)
            resizeLCD(CGSize(width: points.width * scale, height: points.height * scale))
        }
        toolbox.updateScreen(points, name: active?.name ?? "LCD", foldable: active?.foldable ?? false, rotation: view.rotation)
        if active?.foldable == true && !angleRefreshPending {
            angleRefreshPending = true
            handleQueue.async { [weak self] in
                guard let self else { return }
                let angle = try? hingeAngle(of: self.device)
                DispatchQueue.main.async { [weak self] in
                    self?.angleRefreshPending = false
                    if let angle { self?.toolbox.updateAngle(angle) }
                }
            }
        }
        content.needsLayout = true
        let name = device.value(forKey: "name") as? String ?? id
        window.title = active.map { "\(name) — \($0.name)" } ?? name
        updatePreview()
        menuBar?.refreshWindowStatus()
    }

    func showPreview() {
        guard needsPreview, !SimulatorPreviewWindow.isHiddenByUser else { return }
        preparePreview()
        preview?.resume()
        SimulatorPreviewStacks.shared.update()
        if preview?.isCollapsed == true { SimulatorPreviewStacks.shared.revealOverflow(id) }
        else if preview?.panel.isVisible == true { preview?.show() }
        menuBar?.refreshWindowStatus()
    }

    var previewEligible: Bool {
        !SimulatorPreviewWindow.isHiddenByUser && !NSApp.isHidden &&
            (window.isVisible || window.isMiniaturized) && preview?.dismissed != true && needsPreview
    }

    var deviceName: String { device.value(forKey: "name") as? String ?? id }

    var needsPreview: Bool {
        let size = view.shownPoints
        let rect = CGRect(x: view.bounds.midX - size.width * view.scale / 2, y: view.bounds.midY - size.height * view.scale / 2,
                          width: size.width * view.scale, height: size.height * view.scale)
        let shapes = Dictionary(uniqueKeysWithValues: simulatorWindows.values.filter { $0 !== self }.map { open in
            (open.window.windowNumber, open.content.opaqueFrames.map { open.window.convertToScreen(open.content.convert($0, to: nil)) })
        })
        return simulatorWindowNeedsPreview(window, ignoring: Set(simulatorWindows.values.compactMap { $0.preview?.panel.windowNumber })
            .union(SimulatorPreviewStacks.shared.windowNumbers), contentFrame: window.convertToScreen(view.convert(rect, to: nil)), shapedWindows: shapes)
    }

    @objc func toggleToolbox() {
        // Move focus before hiding the tools so their field editor cannot keep taking keys invisibly.
        window.makeFirstResponder(view)
        let lcd = view.bounds.size
        let expanded = !content.toolsVisible
        toolboxToggle.state = expanded ? .on : .off
        UserDefaults.standard.set(expanded, forKey: "simulatorToolbox.\(id)")
        if expanded { content.toolsVisible = true; resizeLCD(lcd) }
        content.animateTools(expanded) { [weak self] in
            guard let self else { return }
            if !expanded { self.resizeLCD(self.view.bounds.size) }
            self.content.needsLayout = true
            self.content.layoutSubtreeIfNeeded()
            menuBar?.refreshWindowStatus()
        }
    }

    private func resizeLCD(_ size: CGSize) {
        let visible = window.screen?.visibleFrame ?? NSScreen.main?.visibleFrame ?? window.frame
        let chrome = window.frame.height - window.contentRect(forFrameRect: window.frame).height
        let points = content.screen
        let minimumScale = 160 / max(1, max(points.width, points.height))
        let minimum = simulatorLCDContentSize(forLCD: CGSize(width: points.width * minimumScale, height: points.height * minimumScale),
                                             bezel: content.deviceAppearance.bezel, toolsVisible: content.toolsVisible)
        window.contentMinSize = CGSize(width: min(visible.width, minimum.width), height: min(visible.height - chrome, minimum.height))
        guard !window.styleMask.contains(.fullScreen) else { content.needsLayout = true; return }
        let requested = simulatorLCDContentSize(forLCD: size, bezel: content.deviceAppearance.bezel, toolsVisible: content.toolsVisible)
        let desired = CGSize(width: min(visible.width, max(minimum.width, requested.width)),
                             height: min(visible.height - chrome, max(minimum.height, requested.height)))
        var frame = window.frameRect(forContentRect: CGRect(origin: .zero, size: desired))
        frame.origin = CGPoint(x: min(max(window.frame.minX, visible.minX), visible.maxX - frame.width),
                               y: min(max(window.frame.maxY - frame.height, visible.minY), visible.maxY - frame.height))
        window.setFrame(frame, display: true)
        content.needsLayout = true
        content.layoutSubtreeIfNeeded()
    }

    func preparePreview() {
        if preview == nil {
            let points = view.shownPoints
            let fit = min(260 / points.width, 280 / points.height)
            let image = SimulatorScreenView(frame: NSRect(x: 0, y: 0, width: points.width * fit, height: points.height * fit))
            image.layer?.backgroundColor = NSColor.clear.cgColor
            image.layer?.cornerRadius = 12
            image.layer?.masksToBounds = true
            previewView = image
            preview = SimulatorPreviewWindow(title: window.title, screenView: image,
                                            onOpen: { [weak self] in if let self { bringSimulatorWindowToFront(self) } },
                                            onStateChange: { menuBar?.refreshWindowStatus() })
        }
        updatePreview()
    }

    func updatePreview() {
        guard let preview, let image = previewView else { return }
        image.screenLayer.contents = surface
        image.pixels = view.pixels
        image.rotation = view.rotation
        image.shownPoints = view.shownPoints
        image.deviceMask = view.deviceMask
        preview.panel.title = "프리뷰 — " + window.title
        preview.setName(deviceName)
    }

    typealias Register = @convention(c) (AnyObject, Selector, NSUUID, AnyObject) -> Void

    func startCallbacks() {
        guard let screen else { return }
        func register(_ name: String, _ block: AnyObject) {
            let selector = NSSelectorFromString(name)
            guard screen.responds(to: selector) else { return }
            unsafeBitCast(screen.method(for: selector), to: Register.self)(screen, selector, token, block)
        }
        // Pixels changed in the same surface: setContentsChanged (as SimulatorKit does) makes Core Animation read them
        // again; setting the same contents would change nothing. One draw per main-loop turn.
        let damage: @convention(block) (AnyObject?) -> Void = { [weak self] _ in
            DispatchQueue.main.async {
                guard let self, !self.drawPending else { return }
                self.drawPending = true
                DispatchQueue.main.async {
                    self.drawPending = false
                    self.view.screenLayer.perform(NSSelectorFromString("setContentsChanged"))
                    self.previewView?.screenLayer.perform(NSSelectorFromString("setContentsChanged"))
                }
            }
        }
        // The screen made a new framebuffer (for example a new size).
        let surfaces: @convention(block) (AnyObject?) -> Void = { [weak self] _ in
            DispatchQueue.main.async { guard let self else { return }; self.show(self.active) }
        }
        register("registerCallbackWithUUID:damageRectanglesCallback:", damage as AnyObject)
        register("registerCallbackWithUUID:ioSurfacesChangeCallback:", surfaces as AnyObject)
    }

    func stopCallbacks() {
        guard let screen else { return }
        for name in ["unregisterDamageRectanglesCallbackWithUUID:", "unregisterIOSurfacesChangeCallbackWithUUID:"]
        where screen.responds(to: NSSelectorFromString(name)) {
            screen.perform(NSSelectorFromString(name), with: token)
        }
    }

    /// Follows a fold or a turn; closes the window when the simulator shuts down.
    func refresh() {
        guard let ticket = displayRefresh.begin() else { return }
        let device = self.device
        DispatchQueue.global().async { [weak self] in
            let booted = isBooted(device)
            let result: Result<ActiveScreen?, Error> = booted ? Result { try activeScreen(of: device) } : .success(nil)
            DispatchQueue.main.async {
                guard let self else { return }
                let current = self.displayRefresh.finish(ticket)
                if !booted { self.window.close(); return }
                guard current, case let .success(active) = result else { return }
                if active?.id != self.active?.id || active?.rotation != self.active?.rotation { self.show(active) }
            }
        }
    }

    // MARK: Input, sent on handleQueue: one at a time with the tools' requests, which use the same HID connection.

    func perform(_ work: @escaping (HIDLink, ActiveScreen?) -> Void) {
        let device = self.device, active = self.active
        handleQueue.async { if let link = try? hidLink(for: device) { work(link, active) } }
    }

    func touch(_ point: CGPoint, _ second: CGPoint?, phase: UInt64) {
        perform { $0.touch(point, phase: phase, screen: $1, second: second) }
    }

    /// A drag over about 0.15 s: a pan (and so a scroll view) recognizes it, where a touch that ends where it began
    /// moving does not (seen with GestureProbe for mouse wheel notches).
    func drag(from: CGPoint, to: CGPoint) {
        perform { link, screen in
            link.touch(from, phase: 0, screen: screen)
            for step in 1...8 {
                usleep(16_000)
                let t = CGFloat(step) / 8
                link.touch(CGPoint(x: from.x + (to.x - from.x) * t, y: from.y + (to.y - from.y) * t), phase: 1, screen: screen)
            }
            link.touch(to, phase: 2, screen: screen)
        }
    }

    func key(_ usage: UInt64, down: Bool) {
        if down { heldKeys.insert(usage) } else { heldKeys.remove(usage) }
        perform { link, _ in link.key(usage, down: down) }
    }

    /// Lets go of the keys held when the window stops taking the keyboard, so none stays down in the simulator.
    func releaseKeys() {
        for usage in heldKeys { key(usage, down: false) }
    }

    func button(_ usage: UInt64) {
        perform { link, _ in
            link.button(page: 0x0C, usage: usage, down: true)
            usleep(100_000)
            link.button(page: 0x0C, usage: usage, down: false)
        }
    }

    /// A crown event with a scroll phase, or a whole turn without one (a mouse wheel).
    func crown(_ phase: UInt64?, _ dy: Double) {
        perform { link, _ in if let phase { link.crownEvent(phase, dy) } else { link.crown(dy) } }
    }

    func windowDidBecomeKey(_ notification: Notification) {
        recentSimulatorWindowID = id
        menuBar?.refreshWindowStatus()
    }

    func windowDidResignKey(_ notification: Notification) {
        releaseKeys()
        menuBar?.refreshWindowStatus()
    }

    func windowDidMiniaturize(_ notification: Notification) { menuBar?.refreshWindowStatus() }
    func windowDidDeminiaturize(_ notification: Notification) { menuBar?.refreshWindowStatus() }
    func windowDidChangeOcclusionState(_ notification: Notification) { menuBar?.refreshWindowStatus() }
    func windowDidMove(_ notification: Notification) { menuBar?.refreshWindowStatus() }
    func windowDidChangeScreen(_ notification: Notification) { menuBar?.refreshWindowStatus() }

    func windowWillClose(_ notification: Notification) {
        releaseKeys()
        view.touchOverlay.clear()
        timer?.invalidate()
        stopCallbacks()
        simulatorWindows[id] = nil
        previewView?.touchOverlay.clear()
        preview?.close()
        updateSimulatorWindowPresentation()
    }
}

/// The open windows, by UDID. Main thread only.
var simulatorWindows: [String: SimulatorWindow] = [:]
var recentSimulatorWindowID: String?

func updateSimulatorWindowPresentation() {
    let policy: NSApplication.ActivationPolicy = simulatorWindows.isEmpty ? .accessory : .regular
    if NSApp.activationPolicy() != policy { NSApp.setActivationPolicy(policy) }
    menuBar?.refreshWindowStatus()
}

/// Shared by the tool, Dock, menu and preview; these callers already run on the main thread.
func bringSimulatorWindowToFront(_ open: SimulatorWindow) {
    updateSimulatorWindowPresentation()
    recentSimulatorWindowID = open.id
    open.window.deminiaturize(nil)
    NSApp.activate(ignoringOtherApps: true)
    open.window.makeKeyAndOrderFront(nil)
    menuBar?.refreshWindowStatus()
}

/// Both HID transports publish only after sending; the main thread owns every viewer layer.
func showSimulatorTouches(_ id: String, contacts: [GestureContact], screen: ActiveScreen?) {
    DispatchQueue.main.async {
        guard let open = simulatorWindows[id] else { return }
        let touching = contacts.contains(where: \.touching)
        let began = touching && !open.touchesActive
        open.touchesActive = touching
        if open.active?.id != screen?.id || open.active?.rotation != screen?.rotation {
            if began { open.show(screen) }
            else {
                open.view.touchOverlay.clear()
                open.previewView?.touchOverlay.clear()
                return
            }
        }
        open.view.touchOverlay.update(contacts)
        open.previewView?.touchOverlay.update(contacts)
    }
}

/// The window action: opens (or brings to the front) the live window of a simulator, or closes it.
func simulatorWindowAction(_ device: NSObject, active: ActiveScreen?, close: Bool) throws -> String {
    let id = udid(of: device)
    let name = device.value(forKey: "name") as? String ?? id
    if close {
        let closed: Bool = DispatchQueue.main.sync {
            guard let open = simulatorWindows[id] else { return false }
            open.window.close()
            return true
        }
        return closed ? "Closed the window of \(name)." : "\(name) has no mac-cu window open."
    }
    guard shownScreen(of: device, active: active) != nil else {
        throw ToolError("\(name) gave no framebuffer, so mac-cu cannot show its screen. Wait until it has booted, then try again.")
    }
    let presentation: (size: CGSize, masked: Bool, tools: Bool) = DispatchQueue.main.sync {
        let open = simulatorWindows[id] ?? SimulatorWindow(device: device, active: active)
        simulatorWindows[id] = open
        open.show(active)
        bringSimulatorWindowToFront(open)
        return (open.view.bounds.size, open.view.deviceMask != nil, open.content.toolsVisible)
    }
    let points = active?.points ?? screenSize(of: device)
    let material: String
    if #available(macOS 26, *) { material = "native Liquid Glass" } else { material = "system material" }
    return """
        Opened a window with the live screen of \(name)\(active.map { " (\($0.name))" } ?? ""), \
        \(Int(points.width))×\(Int(points.height)) points, shown \(Int(presentation.size.width))×\(Int(presentation.size.height)) on the Mac. \
        The device container uses \(material) and \(presentation.masked ? "the simulator model's display mask" : "rounded display corners as a fallback"). \
        Right-side tool components are \(presentation.tools ? "shown" : "hidden"); 도구 or Shift-Command-T toggles them. \
        Colored numbered fingers follow sent touches and fade on lift. It follows folds and turns, and closes when the simulator \
        shuts down. The user can use the simulator in it: clicks and drags touch (Option-drag: two fingers), the keyboard \
        types into it, scrolling scrolls (the crown on Apple Watch), Shift-Command-H presses home and Shift-Command-L lock. \
        Close it with its close button or window with close: true.
        """
}
