import AppKit

private final class PreviewOverflowButton: NSButton {
    override func acceptsFirstMouse(for event: NSEvent?) -> Bool { true }
}

private final class SimulatorPreviewOverflow: NSObject {
    let panel: NSPanel
    private let button = PreviewOverflowButton(title: "", target: nil, action: nil)
    private var ids: [String] = []

    override init() {
        panel = NSPanel(contentRect: .zero, styleMask: [.borderless, .nonactivatingPanel], backing: .buffered, defer: false)
        super.init()
        panel.title = "추가 시뮬레이터 프리뷰"
        panel.isReleasedWhenClosed = false
        panel.level = .floating
        panel.isOpaque = false
        panel.backgroundColor = .clear
        panel.hasShadow = false
        panel.hidesOnDeactivate = false
        panel.animationBehavior = .none
        panel.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary, .ignoresCycle]
        button.bezelStyle = .rounded
        button.font = .systemFont(ofSize: 12, weight: .semibold)
        button.target = self
        button.action = #selector(openMenu)
        panel.contentView = button
        SimulatorPreviewWindow.configureOverlay(panel)
    }

    func show(ids: [String], frame: CGRect) {
        self.ids = ids
        button.title = "+\(ids.count)"
        button.setAccessibilityLabel("추가 시뮬레이터 프리뷰 \(ids.count)개")
        if panel.frame != frame { panel.setFrame(frame, display: true) }
        if !panel.isVisible { panel.orderFrontRegardless() }
    }

    @objc private func openMenu() {
        let menu = NSMenu()
        for id in ids {
            guard let open = simulatorWindows[id] else { continue }
            let item = NSMenuItem(title: open.deviceName, action: #selector(openLCD(_:)), keyEquivalent: "")
            item.target = self
            item.representedObject = id
            menu.addItem(item)
        }
        menu.popUp(positioning: nil, at: NSPoint(x: 0, y: button.bounds.maxY), in: button)
    }

    func reveal(_ id: String) -> Bool {
        guard ids.contains(id) else { return false }
        openMenu()
        return true
    }

    @objc private func openLCD(_ sender: NSMenuItem) {
        if let id = sender.representedObject as? String, let open = simulatorWindows[id] { bringSimulatorWindowToFront(open) }
    }
}

/// One arrangement pass for all LCDs, so per-window visibility updates cannot fight over the same corner.
final class SimulatorPreviewStacks {
    static let shared = SimulatorPreviewStacks()
    private var overflow: [UInt32: SimulatorPreviewOverflow] = [:]
    private var updating = false

    var windowNumbers: Set<Int> { Set(overflow.values.map { $0.panel.windowNumber }) }

    func arrangeAll() {
        for open in simulatorWindows.values { open.preview?.resetManualPlacement() }
        update()
    }

    func revealOverflow(_ id: String) {
        for extra in overflow.values where extra.reveal(id) { return }
    }

    func update() {
        guard !updating else { return }
        updating = true
        defer { updating = false }
        let screens = NSScreen.screens
        var groups: [UInt32: (screen: NSScreen, windows: [SimulatorWindow])] = [:]
        for open in simulatorWindows.values {
            guard open.previewEligible else {
                open.preview?.isCollapsed = false
                if open.preview?.panel.isVisible == true { open.preview?.hide() }
                continue
            }
            open.preparePreview()
            let manualScreen = open.preview?.manualFrame.flatMap { rect in
                screens.filter { $0.visibleFrame.intersects(rect) }.max {
                    let a = $0.visibleFrame.intersection(rect), b = $1.visibleFrame.intersection(rect)
                    return a.width * a.height < b.width * b.height
                }
            }
            guard let screen = manualScreen ?? open.window.screen ?? screens.first else { open.preview?.hide(); continue }
            let id = (screen.deviceDescription[NSDeviceDescriptionKey("NSScreenNumber")] as? NSNumber)?.uint32Value ?? 0
            if groups[id] == nil { groups[id] = (screen, []) }
            groups[id]?.windows.append(open)
        }
        for id in Array(overflow.keys) where groups[id] == nil {
            overflow[id]?.panel.close()
            overflow[id] = nil
        }
        for (id, group) in groups {
            let items = group.windows.map {
                SimulatorPreviewLayoutItem(id: $0.id, name: $0.deviceName, screenSize: $0.view.shownPoints, manualFrame: $0.preview?.manualFrame)
            }
            let layout = layoutSimulatorPreviews(items, in: group.screen.visibleFrame)
            for open in group.windows {
                guard let preview = open.preview else { continue }
                preview.isCollapsed = layout.frames[open.id] == nil
                if let frame = layout.frames[open.id] {
                    preview.applyLayout(frame)
                    if !preview.panel.isVisible { preview.show() }
                } else if preview.panel.isVisible { preview.hide() }
            }
            if let frame = layout.overflowFrame, !layout.overflow.isEmpty {
                let extra = overflow[id] ?? SimulatorPreviewOverflow()
                overflow[id] = extra
                extra.show(ids: layout.overflow, frame: frame)
            } else {
                overflow[id]?.panel.close()
                overflow[id] = nil
            }
        }
    }
}
