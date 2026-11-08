import AppKit

@main
struct SimulatorToolbarDockingSelfcheck {
    static func descendants(_ view: NSView) -> [NSView] { [view] + view.subviews.flatMap(descendants) }
    static func main() throws {
        _ = NSApplication.shared
        let suite = "mac-cu.toolbar-selfcheck." + UUID().uuidString
        let defaults = UserDefaults(suiteName: suite)!
        defer { defaults.removePersistentDomain(forName: suite) }
        func fixture(_ id: String) -> (SimulatorDeviceWindow, SimulatorLCDContentView, SimulatorToolbarDocking) {
            let tools = SimulatorToolboxView(deviceName: id, isWatch: false)
            let lcd = NSView(frame: CGRect(x: 0, y: 0, width: 320, height: 500))
            let content = SimulatorLCDContentView(lcd: lcd, tools: tools, appearance: SimulatorDeviceAppearance(typeName: "iPhone"))
            content.externalToolbar = true
            content.screen = CGSize(width: 466, height: 678)
            let owner = SimulatorDeviceWindow(contentRect: CGRect(x: 80, y: 100, width: 430, height: 700), styleMask: [.borderless, .resizable], backing: .buffered, defer: false)
            owner.isReleasedWhenClosed = false
            owner.contentView = content
            content.layoutSubtreeIfNeeded()
            let docking = SimulatorToolbarDocking(ownerID: id, name: id, device: owner, chrome: content.chrome, tools: tools, defaults: defaults)
            return (owner, content, docking)
        }
        let (owner, content, docking) = fixture("A")
        let (otherOwner, otherContent, other) = fixture("B")
        defer { docking.close(); owner.close(); other.close(); otherOwner.close() }
        // These are offscreen AppKit fixtures. Never activate, orderFront a device, or inject input.
        assert(!owner.isVisible && !otherOwner.isVisible)
        assert(docking.modules.count == 6 && docking.panels.isEmpty)
        assert(docking.toolbar.canBecomeKey && !docking.toolbar.canBecomeMain)
        assert(!docking.toolbar.becomesKeyOnlyIfNeeded && !docking.toolbar.styleMask.contains(.titled))
        let grip = content.chrome.grip
        assert(content.hitTest(grip.convert(CGPoint(x: 20, y: 20), to: content)) === grip)
        assert(!content.body.frame.intersects(content.chrome.resize.frame))
        assert(content.bounds.contains(content.chrome.resize.frame), "External sidebar layout must retain an onscreen resize target")
        for module in docking.modules {
            assert(module.window === docking.toolbar)
            assert(module.grip.hitTest(CGPoint(x: 24, y: 20)) === module.grip)
        }
        var cleanup = 0
        docking.onInputCleanup = { cleanup += 1 }
        let input = descendants(content.tools).compactMap { $0 as? NSTextField }.first { $0.placeholderString == "기기로 보낼 글자 ⏎" }!
        input.stringValue = "미전송 초안"
        let target = input.target as AnyObject?
        let action = input.action
        let basic = docking.modules.first { $0.key == "basic" }!
        let advanced = docking.modules.first { $0.key == "advanced" }!
        docking.setAdvancedVisible(true)
        docking.detach("advanced")
        let advancedPanel = docking.panels["advanced"]!
        assert(input.window === advancedPanel && advanced.content === content.tools)
        assert(input.stringValue == "미전송 초안" && input.target as AnyObject? === target && input.action == action)
        assert(!advanced.isHidden, "A detached module must not retain its sidebar collapse flag")
        content.tools.setFloatingPresentation(true)
        assert(!content.tools.isHidden, "Floating toolbox presentation must remove the old embedded hidden state")
        let panelFrame = advancedPanel.frame
        let toolFrame = content.tools.frame
        let hidden = content.tools.isHidden
        content.frame.size = CGSize(width: 540, height: 630)
        content.focused = true
        content.layoutSubtreeIfNeeded()
        assert(advancedPanel.frame == panelFrame && content.tools.frame == toolFrame && content.tools.isHidden == hidden,
               "LCD layout must never overwrite a reparented module's frame or visibility")
        content.focused = false
        content.layoutSubtreeIfNeeded()
        assert(content.chrome.controls.window === docking.toolbar && content.chrome.controls.superview === basic)
        docking.detach("status")
        let statusPanel = docking.panels["status"]!
        statusPanel.contentView!.layoutSubtreeIfNeeded()
        let feedback = descendants(statusPanel.contentView!).compactMap { $0 as? NSTextField }
            .first { $0.accessibilityLabel() == "시뮬레이터 조작 결과" }!
        let statusFrame = feedback.frame
        docking.detach("basic")
        let basicPanel = docking.panels["basic"]!
        basicPanel.setContentSize(CGSize(width: 420, height: 130))
        basicPanel.contentView!.layoutSubtreeIfNeeded()
        assert(feedback.frame == statusFrame, "Basic module layout must not overwrite another panel's status text")
        docking.attach("status")
        let detachedFrame = basicPanel.frame
        owner.setFrameOrigin(CGPoint(x: owner.frame.minX + 34, y: owner.frame.minY + 18))
        docking.deviceDidMove()
        assert(basicPanel.frame == detachedFrame, "A detached module must not follow its device")
        assert(other.panels.isEmpty && otherContent.chrome.controls.window === other.toolbar)
        // Use the same callbacks as the native grip, with synthetic screen coordinates only.
        basic.grip.onBegin(basicPanel.frame.origin)
        let dockPoint = CGPoint(x: docking.toolbar.frame.midX, y: docking.toolbar.frame.midY)
        basic.grip.onDrag(dockPoint)
        assert(docking.toolbarGrip.label.stringValue.contains("놓으면"), "Docking must expose a live target before release")
        basic.grip.onEnd()
        assert(docking.panels["basic"] == nil && basic.window === docking.toolbar)
        assert(cleanup > 0)
        func choose(_ title: String, menu: NSMenu) {
            let item = menu.items.first { $0.title == title }!
            _ = NSApp.sendAction(item.action!, to: item.target, from: item)
        }
        choose("메인 도구를 독립 이동", menu: docking.menu(includeDeviceMenu: false))
        let independent = docking.toolbar.frame
        owner.setFrameOrigin(CGPoint(x: owner.frame.minX + 24, y: owner.frame.minY - 12))
        docking.deviceDidMove()
        assert(!docking.placement.attached && docking.toolbar.frame == independent)
        choose("메인 도구를 기기에 결합", menu: docking.menu(includeDeviceMenu: false))
        assert(docking.placement.attached)
        assert(!docking.menu(includeDeviceMenu: false).items.contains { $0.submenu != nil }, "Device/toolbar menus must not recurse")
        docking.setFocused(true)
        assert(!docking.toolbar.isVisible && !advancedPanel.isVisible)
        docking.setFocused(false)
        docking.suspend(); docking.resume()
        assert(!docking.toolbar.isVisible, "An offscreen or closed owner must not spawn a visible tool panel")
        // Abort an in-progress grip through focus loss; a late mouseUp cannot redock it.
        basic.grip.onBegin(docking.toolbar.frame.origin)
        docking.windowDidResignKey(Notification(name: NSWindow.didResignKeyNotification, object: docking.toolbar))
        basic.grip.onEnd()
        assert(docking.panels["basic"] != nil)
        // Explicit delegate close rejoins a panel instead of orphaning its only control view.
        let closingPanel = docking.panels["basic"]!
        assert(!docking.windowShouldClose(closingPanel) && docking.panels["basic"] == nil)
        docking.detach("input")
        docking.deviceDidMove()
        let savedFrame = owner.frame
        docking.close()
        assert(!docking.toolbar.isVisible && !advancedPanel.isVisible)
        let (restoredOwner, restoredContent, restoredDocking) = fixture("A")
        defer { restoredDocking.close(); restoredOwner.close() }
        restoredDocking.restoreDeviceFrame()
        assert(restoredDocking.panels["advanced"] != nil && restoredDocking.panels["input"] != nil)
        let visibleScreens = NSScreen.screens.map(\.visibleFrame)
        let expected = simulatorRestoredPanelFrame(savedFrame, screens: visibleScreens, fallback: restoredOwner.frame)
        assert(restoredOwner.frame == expected)
        restoredDocking.resetLayout()
        assert(restoredDocking.panels.isEmpty && restoredDocking.placement.attached)
        assert(descendants(restoredDocking.toolbar.contentView!).contains { $0 === restoredContent.chrome.controls })
        assert(!otherOwner.isVisible && other.panels.isEmpty, "Reset is scoped to its device")
        let display = CGRect(x: -1600, y: 80, width: 1600, height: 900)
        let restored = simulatorRestoredPanelFrame(CGRect(x: 9000, y: -8000, width: 2200, height: 1800), screens: [display], fallback: display)
        assert(display.contains(restored))
        assert(simulatorRestoredPanelFrame(CGRect(x: CGFloat.nan, y: 0, width: 300, height: 100), screens: [display], fallback: display) == display)
        let deviceFrame = CGRect(x: 100, y: 100, width: 300, height: 600)
        assert(simulatorToolbarSnapSide(CGRect(x: 412, y: 110, width: 380, height: 550), device: deviceFrame) == false)
        assert(simulatorToolbarSnapSide(CGRect(x: -292, y: 110, width: 380, height: 550), device: deviceFrame) == true)
        assert(simulatorToolbarSnapSide(CGRect(x: 412, y: 900, width: 380, height: 550), device: deviceFrame) == nil)
        print("PASS offscreen toolbar docking: six real modules, one control/action owner, preserved drafts, reparent/layout isolation, per-device ownership, attached/independent motion, docking feedback, focus-loss drag cleanup, close/rejoin, scoped persistence/reset and screen recovery. No live pointer or rendered UI verified.")
    }
}
