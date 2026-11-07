import AppKit

enum SimulatorWindowVisibility: String {
    case foreground = "전경", background = "배경", minimized = "최소화", hidden = "숨김", otherSpace = "다른 데스크탑"

    static func resolve(isMiniaturized: Bool, isHidden: Bool, isOnActiveSpace: Bool, isForeground: Bool) -> Self {
        if isMiniaturized { return .minimized }
        if isHidden { return .hidden }
        if !isOnActiveSpace { return .otherSpace }
        return isForeground ? .foreground : .background
    }
}

func simulatorWindowVisibility(_ window: NSWindow) -> SimulatorWindowVisibility {
    let windows = CGWindowListCopyWindowInfo([.optionOnScreenOnly, .excludeDesktopElements], kCGNullWindowID) as? [[String: Any]] ?? []
    let front = windows.first { entry in
        guard entry[kCGWindowLayer as String] as? Int == window.level.rawValue,
              (entry[kCGWindowAlpha as String] as? Double ?? 1) > 0,
              entry[kCGWindowOwnerName as String] as? String != "focus-overlay",
              let bounds = entry[kCGWindowBounds as String] as? NSDictionary,
              let frame = CGRect(dictionaryRepresentation: bounds)
        else { return false }
        return frame.width > 40 && frame.height > 40
    }
    return .resolve(isMiniaturized: window.isMiniaturized,
                    isHidden: NSApp.isHidden || !window.isVisible,
                    isOnActiveSpace: window.isOnActiveSpace,
                    isForeground: front?[kCGWindowNumber as String] as? Int == window.windowNumber &&
                        (NSApp.isActive || window.styleMask.contains(.nonactivatingPanel)))
}

/// A separate hit target keeps preview clicks out of the simulator's input view.
final class SimulatorPreviewClickView: NSView {
    var onOpen: () -> Void = {}
    var contextMenu: (() -> NSMenu)?
    private var dragEvent: NSEvent?

    override func acceptsFirstMouse(for event: NSEvent?) -> Bool { true }
    override var mouseDownCanMoveWindow: Bool { false }
    override func resetCursorRects() { addCursorRect(bounds, cursor: .pointingHand) }

    override func mouseDown(with event: NSEvent) {
        window?.orderFrontRegardless()
        dragEvent = event
        if event.clickCount == 2 { dragEvent = nil; onOpen() }
    }

    override func mouseDragged(with event: NSEvent) {
        guard let start = dragEvent,
              hypot(event.locationInWindow.x - start.locationInWindow.x, event.locationInWindow.y - start.locationInWindow.y) > 3
        else { return }
        dragEvent = nil
        window?.performDrag(with: start)
    }

    override func mouseUp(with event: NSEvent) { dragEvent = nil }
    override func accessibilityPerformPress() -> Bool { onOpen(); return true }
    override func menu(for event: NSEvent) -> NSMenu? { contextMenu?() }
}

private final class SimulatorPreviewSettings: NSObject, NSMenuItemValidation {
    static let shared = SimulatorPreviewSettings()
    private let previews = NSHashTable<SimulatorPreviewWindow>.weakObjects()
    private let panels = NSHashTable<NSPanel>.weakObjects()
    private let percentages = [25, 50, 75, 100]
    private let opacityKey = "simulatorPreviewOpacity"
    private let hiddenKey = "hidePreview"

    var opacity: Double {
        let saved = UserDefaults.standard.double(forKey: opacityKey)
        return percentages.map { Double($0) / 100 }.contains(saved) ? saved : 0.75
    }
    var isHidden: Bool { UserDefaults.standard.bool(forKey: hiddenKey) }

    func register(_ preview: SimulatorPreviewWindow) {
        previews.add(preview)
        register(preview.panel)
    }

    func register(_ panel: NSPanel) { panels.add(panel); panel.alphaValue = opacity }

    func opacityMenu() -> NSMenu {
        let menu = NSMenu(title: "불투명도")
        for percentage in percentages {
            let item = NSMenuItem(title: "\(percentage)%", action: #selector(setOpacity(_:)), keyEquivalent: "")
            item.tag = percentage
            item.target = self
            item.state = Double(percentage) / 100 == opacity ? .on : .off
            menu.addItem(item)
        }
        return menu
    }

    func hiddenMenuItem() -> NSMenuItem {
        let item = NSMenuItem(title: "프리뷰 숨김", action: #selector(toggleHidden(_:)), keyEquivalent: "")
        item.target = self
        item.state = isHidden ? .on : .off
        return item
    }

    @objc private func setOpacity(_ sender: NSMenuItem) {
        guard percentages.contains(sender.tag) else { return }
        UserDefaults.standard.set(Double(sender.tag) / 100, forKey: opacityKey)
        for panel in panels.allObjects { panel.alphaValue = opacity }
        sender.menu?.items.forEach { $0.state = $0 === sender ? .on : .off }
    }

    @objc private func toggleHidden(_ sender: NSMenuItem) {
        UserDefaults.standard.set(!isHidden, forKey: hiddenKey)
        sender.state = isHidden ? .on : .off
        for preview in previews.allObjects {
            if isHidden { preview.hide() }
            preview.changed()
        }
    }

    func validateMenuItem(_ item: NSMenuItem) -> Bool {
        item.state = item.action == #selector(toggleHidden(_:)) ? (isHidden ? .on : .off) :
            (Double(item.tag) / 100 == opacity ? .on : .off)
        return true
    }
}

final class SimulatorPreviewWindow: NSObject, NSWindowDelegate {
    let panel: NSPanel
    private(set) var dismissed = false
    private(set) var manualFrame: CGRect?
    var isCollapsed = false
    private var lastLayoutFrame: CGRect?
    private var applyingLayout = false
    private let caption = NSTextField(labelWithString: "")
    private let onOpen: () -> Void
    private let onStateChange: () -> Void

    static var isHiddenByUser: Bool { SimulatorPreviewSettings.shared.isHidden }
    static func opacityMenu() -> NSMenu { SimulatorPreviewSettings.shared.opacityMenu() }
    static func hiddenMenuItem() -> NSMenuItem { SimulatorPreviewSettings.shared.hiddenMenuItem() }
    static func configureOverlay(_ panel: NSPanel) { SimulatorPreviewSettings.shared.register(panel) }

    init(title: String, screenView: NSView, onOpen: @escaping () -> Void, onStateChange: @escaping () -> Void) {
        let source = screenView.bounds.size
        let fit = min(240 / max(source.width, 1), 320 / max(source.height, 1))
        let size = NSSize(width: max(source.width * fit, 80), height: max(source.height * fit, 80))
        panel = NSPanel(contentRect: NSRect(origin: .zero, size: size),
                        styleMask: [.borderless, .nonactivatingPanel],
                        backing: .buffered, defer: false)
        self.onOpen = onOpen
        self.onStateChange = onStateChange
        super.init()
        panel.title = "프리뷰 — " + title
        panel.isReleasedWhenClosed = false
        panel.isFloatingPanel = true
        panel.level = .floating
        panel.isOpaque = false
        panel.backgroundColor = .clear
        panel.hasShadow = false
        panel.animationBehavior = .none
        panel.hidesOnDeactivate = false
        panel.becomesKeyOnlyIfNeeded = true
        panel.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary, .ignoresCycle]
        panel.contentMinSize = .zero
        panel.delegate = self

        let content = NSView(frame: NSRect(origin: .zero, size: size))
        screenView.frame = NSRect(x: 0, y: simulatorPreviewCaptionHeight, width: size.width, height: max(0, size.height - simulatorPreviewCaptionHeight))
        screenView.autoresizingMask = [.width, .height]
        content.addSubview(screenView)
        caption.frame = NSRect(x: 0, y: 0, width: size.width, height: simulatorPreviewCaptionHeight)
        caption.autoresizingMask = [.width]
        caption.alignment = .center
        caption.lineBreakMode = .byTruncatingTail
        caption.font = .systemFont(ofSize: 11, weight: .medium)
        let shadow = NSShadow()
        shadow.shadowColor = NSColor.black
        shadow.shadowBlurRadius = 3
        shadow.shadowOffset = NSSize(width: 0, height: -1)
        caption.attributedStringValue = NSAttributedString(string: title, attributes: [.foregroundColor: NSColor.white, .shadow: shadow])
        caption.toolTip = title
        content.addSubview(caption)
        let click = SimulatorPreviewClickView(frame: content.bounds)
        click.autoresizingMask = [.width, .height]
        click.onOpen = onOpen
        click.contextMenu = { [weak self] in self?.contextMenu() ?? NSMenu() }
        click.toolTip = "더블 클릭하면 \(title) 창을 전경으로 가져옵니다"
        click.setAccessibilityElement(true)
        click.setAccessibilityRole(.button)
        click.setAccessibilityLabel("\(title) 창을 전경으로 가져오기")
        click.setAccessibilityHelp(click.toolTip)
        content.addSubview(click, positioned: .above, relativeTo: screenView)
        panel.contentView = content
        SimulatorPreviewSettings.shared.register(self)
    }

    func setName(_ name: String) {
        guard caption.stringValue != name else { return }
        let attributes = caption.attributedStringValue.attributes(at: 0, effectiveRange: nil)
        caption.attributedStringValue = NSAttributedString(string: name, attributes: attributes)
        caption.toolTip = name
    }

    func applyLayout(_ frame: CGRect) {
        applyingLayout = true
        lastLayoutFrame = frame
        if panel.frame != frame { panel.setFrame(frame, display: true) }
        lastLayoutFrame = panel.frame
        if manualFrame != nil { manualFrame = panel.frame }
        applyingLayout = false
    }

    func resetManualPlacement() { manualFrame = nil }
    func resume() { dismissed = false }

    func show() {
        guard !Self.isHiddenByUser else { return }
        dismissed = false
        if NSApp.isHidden { NSApp.unhideWithoutActivation() }
        if panel.isMiniaturized { panel.deminiaturize(nil) }
        panel.orderFrontRegardless()
        changed()
    }

    func hide() { panel.orderOut(nil) }
    func close() { panel.close() }

    private func contextMenu() -> NSMenu {
        let menu = NSMenu()
        let open = NSMenuItem(title: "LCD 창 보기", action: #selector(openLCD), keyEquivalent: "")
        open.target = self
        menu.addItem(open)
        let opacity = NSMenuItem(title: "불투명도", action: nil, keyEquivalent: "")
        opacity.submenu = Self.opacityMenu()
        menu.addItem(opacity)
        menu.addItem(Self.hiddenMenuItem())
        menu.addItem(.separator())
        let close = NSMenuItem(title: "이 프리뷰 숨김", action: #selector(dismissPreview), keyEquivalent: "")
        close.target = self
        menu.addItem(close)
        return menu
    }

    @objc private func openLCD() { onOpen() }
    @objc private func dismissPreview() { close() }

    fileprivate func changed() { DispatchQueue.main.async { [onStateChange] in onStateChange() } }
    func windowDidBecomeKey(_ notification: Notification) { changed() }
    func windowDidResignKey(_ notification: Notification) { changed() }
    func windowDidChangeOcclusionState(_ notification: Notification) { changed() }
    func windowDidMiniaturize(_ notification: Notification) { changed() }
    func windowDidDeminiaturize(_ notification: Notification) { changed() }
    func windowDidMove(_ notification: Notification) {
        guard !applyingLayout, let lastLayoutFrame, panel.frame != lastLayoutFrame else { return }
        manualFrame = panel.frame
        changed()
    }
    func windowDidChangeScreen(_ notification: Notification) { changed() }
    func windowWillClose(_ notification: Notification) { dismissed = true; changed() }
}
