import AppKit

@main
struct SimulatorWindowPresentationSelfcheck {
    static func main() {
        typealias State = SimulatorWindowVisibility
        assert(State.resolve(isMiniaturized: true, isHidden: true, isOnActiveSpace: false, isForeground: true) == .minimized)
        assert(State.resolve(isMiniaturized: false, isHidden: true, isOnActiveSpace: false, isForeground: true) == .hidden)
        assert(State.resolve(isMiniaturized: false, isHidden: false, isOnActiveSpace: false, isForeground: true) == .otherSpace)
        assert(State.resolve(isMiniaturized: false, isHidden: false, isOnActiveSpace: true, isForeground: true) == .foreground)
        assert(State.resolve(isMiniaturized: false, isHidden: false, isOnActiveSpace: true, isForeground: false) == .background)

        let content = NSView(frame: NSRect(x: 0, y: 0, width: 100, height: 100))
        let screen = NSView(frame: content.bounds)
        let click = SimulatorPreviewClickView(frame: content.bounds)
        content.addSubview(screen)
        content.addSubview(click, positioned: .above, relativeTo: screen)
        assert(content.hitTest(NSPoint(x: 10, y: 10)) === click)
        var opened = 0
        click.onOpen = { opened += 1 }
        func event(_ count: Int) -> NSEvent {
            NSEvent.mouseEvent(with: .leftMouseDown, location: NSPoint(x: 10, y: 10), modifierFlags: [],
                               timestamp: 0, windowNumber: 0, context: nil, eventNumber: count, clickCount: count, pressure: 1)!
        }
        let single = event(1)
        assert(click.acceptsFirstMouse(for: single))
        click.mouseDown(with: single)
        click.mouseUp(with: single)
        assert(opened == 0)
        click.mouseDown(with: event(2))
        assert(opened == 1)
        assert(click.accessibilityPerformPress())
        assert(opened == 2)

        NSApplication.shared.setActivationPolicy(.accessory)
        let savedOpacity = UserDefaults.standard.object(forKey: "simulatorPreviewOpacity") as? NSObject
        let savedHidden = UserDefaults.standard.object(forKey: "hidePreview") as? NSObject
        var contextOpened = 0
        let preview = SimulatorPreviewWindow(title: "LCD selfcheck", screenView: NSView(frame: content.bounds),
                                             onOpen: { contextOpened += 1 }, onStateChange: {})
        assert(preview.panel.isFloatingPanel && preview.panel.level == .floating)
        assert(preview.panel.styleMask.contains(.nonactivatingPanel))
        assert(!preview.panel.styleMask.contains(.titled))
        assert(!preview.panel.isOpaque && preview.panel.backgroundColor == .clear && !preview.panel.hasShadow)
        assert(!preview.panel.hidesOnDeactivate && preview.panel.becomesKeyOnlyIfNeeded)
        preview.setName("iPhone test")
        assert(preview.panel.contentView!.subviews.compactMap { $0 as? NSTextField }.first?.stringValue == "iPhone test")
        preview.applyLayout(CGRect(x: 100, y: 100, width: 137.5, height: 222))
        preview.windowDidMove(Notification(name: NSWindow.didMoveNotification))
        assert(preview.manualFrame == nil)
        preview.panel.setFrameOrigin(NSPoint(x: 300, y: 200))
        preview.windowDidMove(Notification(name: NSWindow.didMoveNotification))
        let moved = preview.panel.frame
        assert(preview.manualFrame == moved)
        preview.applyLayout(moved)
        assert(preview.manualFrame == moved)
        preview.resetManualPlacement()
        assert(preview.manualFrame == nil)
        let opacity = SimulatorPreviewWindow.opacityMenu()
        assert(opacity.items.map(\.title) == ["25%", "50%", "75%", "100%"])
        assert(opacity.items.filter { $0.state == .on }.count == 1)
        let selected = opacity.items.first { $0.state == .on }!
        assert(preview.panel.alphaValue == Double(selected.tag) / 100)
        for invalid in [0, -25, 125] {
            let item = NSMenuItem(title: "invalid", action: selected.action, keyEquivalent: "")
            item.target = selected.target
            item.tag = invalid
            assert(NSApp.sendAction(item.action!, to: item.target, from: item))
            assert(preview.panel.alphaValue == Double(selected.tag) / 100)
        }
        let hidden = SimulatorPreviewWindow.hiddenMenuItem()
        assert(hidden.title == "프리뷰 숨김")
        assert(hidden.state == (SimulatorPreviewWindow.isHiddenByUser ? .on : .off))
        let hit = preview.panel.contentView!.subviews.compactMap { $0 as? SimulatorPreviewClickView }.first!
        let context = hit.menu(for: event(1))!
        assert(context.items.filter { !$0.isSeparatorItem }.map(\.title) == ["LCD 창 보기", "불투명도", "프리뷰 숨김", "이 프리뷰 숨김"])
        assert(context.items[1].submenu!.items.map(\.title) == opacity.items.map(\.title))
        let open = context.items[0]
        assert(NSApp.sendAction(open.action!, to: open.target, from: open))
        assert(contextOpened == 1)
        assert(!preview.panel.isVisible && !preview.dismissed)
        preview.hide()
        assert(!preview.panel.isVisible && !preview.dismissed)
        let close = context.items.last!
        assert(NSApp.sendAction(close.action!, to: close.target, from: close))
        assert(preview.dismissed)
        preview.hide()
        assert(preview.dismissed)
        preview.resume()
        assert(!preview.dismissed)
        assert(savedOpacity == UserDefaults.standard.object(forKey: "simulatorPreviewOpacity") as? NSObject)
        assert(savedHidden == UserDefaults.standard.object(forKey: "hidePreview") as? NSObject)
        print("Simulator window presentation checks passed: visibility, preview input, borderless HUD, opacity menu, global hide and context open/dismiss without changing saved preferences.")
    }
}
