import AppKit

private struct LCDCheckFailure: Error, CustomStringConvertible {
    let description: String
}

private func lcdExpect(_ value: @autoclosure () -> Bool, _ message: String) throws {
    if !value() { throw LCDCheckFailure(description: message) }
    print("PASS " + message)
    fflush(stdout)
}

private func lcdBackground<T>(_ work: @escaping () throws -> T) async throws -> T {
    try await withCheckedThrowingContinuation { continuation in
        handleQueue.async { continuation.resume(with: Result(catching: work)) }
    }
}

@MainActor
private func lcdPause(_ seconds: Double = 0.3) async {
    try? await Task.sleep(nanoseconds: UInt64(seconds * 1_000_000_000))
}

@MainActor
private func lcdDescendants(_ view: NSView) -> [NSView] { [view] + view.subviews.flatMap(lcdDescendants) }

@MainActor
private func lcdCapture(_ open: SimulatorWindow, name: String, output: URL) {
    let file = output.appendingPathComponent(name + ".png")
    let result = shell("/usr/sbin/screencapture", ["-x", "-o", "-l", String(open.window.windowNumber), file.path], timeout: 5)
    if result.status == 0, FileManager.default.fileExists(atPath: file.path) {
        print("LIVE_UI " + file.path)
        if let bytes = try? Data(contentsOf: file), let bitmap = NSBitmapImageRep(data: bytes) {
            print("LIVE_PIXELS size=\(bitmap.pixelsWide)x\(bitmap.pixelsHigh) cornerAlpha=\(bitmap.colorAt(x: 0, y: 0)?.alphaComponent ?? -1)")
        }
    } else { print("ENVIRONMENT screenshot unavailable: " + result.output) }
    fflush(stdout)
}

@MainActor
private func lcdPress(_ title: String, in view: NSView, open: SimulatorWindow) async throws {
    guard open.window.isKeyWindow && NSApp.isActive else {
        throw LCDCheckFailure(description: "ENVIRONMENT foreground lost before \(title): key=\(open.window.isKeyWindow), active=\(NSApp.isActive), front=\(NSWorkspace.shared.frontmostApplication?.bundleIdentifier ?? "unknown"). No further input sent.")
    }
    print("PASS Foreground LCD available before " + title)
    let button = lcdDescendants(view).compactMap { $0 as? NSButton }.first { $0.title == title || $0.accessibilityLabel() == title }
    try lcdExpect(button != nil && button!.isEnabled, "Native button available: " + title)
    button!.performClick(nil)
    for _ in 0..<300 {
        if !open.toolbox.busy && !open.toolbox.manualPending { return }
        await lcdPause(0.05)
    }
    throw LCDCheckFailure(description: "Command did not settle: " + title)
}

@MainActor
private func lcdRun(_ id: String, output: URL) async throws {
    let device = try await lcdBackground { try bootedDevice(id) }
    let original = try await lcdBackground { try activeScreen(of: device) }
    let originalAngle = original?.foldable == true ? try await lcdBackground { try hingeAngle(of: device) } : nil
    let originalRotation = original?.rotation ?? "rot0"
    print("INITIAL device=\(id) screen=\(original?.id ?? "none") rotation=\(originalRotation) angle=\(originalAngle.map(String.init(describing:)) ?? "n/a")")
    var open = SimulatorWindow(device: device, active: original)
    simulatorWindows[id] = open
    let nativeRun = open.content.chrome.onRun
    open.content.chrome.onRun = { arguments in
        print("NATIVE_CONTROL \(arguments)")
        nativeRun(arguments)
    }
    bringSimulatorWindowToFront(open)
    await lcdPause(1)
    var testFailure: Error?
    do {
        try lcdExpect(open.surface != nil && open.window.isVisible, "Actual CoreSimulator framebuffer visible")
        try lcdExpect(!open.window.styleMask.contains(.titled) && open.window.standardWindowButton(.closeButton) == nil, "No title bar or traffic lights")
        try lcdExpect(open.window.alphaValue == 1 && open.view.layer!.backgroundColor!.alpha == 1, "Opaque LCD independent of preview opacity")
        try lcdExpect(open.window.isKeyWindow && open.window.firstResponder === open.view, "Borderless activation and keyboard focus")
        try lcdExpect(open.toolbarDocking?.toolbar.isVisible == true, "Floating main toolbar is visible")
        if let docking = open.toolbarDocking {
            docking.detach("basic")
            try lcdExpect(docking.panels["basic"]?.isVisible == true && open.content.chrome.controls.window === docking.panels["basic"], "Actual basic controls detach into one visible panel")
            docking.attach("basic")
            try lcdExpect(docking.panels["basic"] == nil && open.content.chrome.controls.window === docking.toolbar, "Actual basic controls rejoin the main toolbar")
        }
        DecisionSettingsWindow.shared.show()
        await lcdPause(0.4)
        guard let settings = NSApp.windows.first(where: { $0.title == "OpenAI Decisions 설정" && $0.isVisible }) else {
            throw LCDCheckFailure(description: "Native settings window did not open")
        }
        try lcdExpect(lcdDescendants(settings.contentView!).contains { $0 is NSSecureTextField }, "Settings use a secure key field without issuing a network request")
        let settingsCapture = output.appendingPathComponent("settings.png")
        let settingsShot = shell("/usr/sbin/screencapture", ["-x", "-o", "-l", String(settings.windowNumber), settingsCapture.path], timeout: 5)
        print(settingsShot.status == 0 ? "LIVE_UI " + settingsCapture.path : "ENVIRONMENT settings screenshot unavailable")
        settings.close()
        bringSimulatorWindowToFront(open)
        await lcdPause(0.3)
        lcdCapture(open, name: "01-device", output: output)
        open.content.layoutSubtreeIfNeeded()
        let grip = open.content.chrome.grip
        let point = grip.convert(CGPoint(x: 20, y: 20), to: open.content)
        try lcdExpect(open.content.hitTest(point) === grip, "Handle hit does not enter LCD")
        try lcdExpect(open.content.hitTest(CGPoint(x: 1, y: 1)) == nil, "Transparent margin has no AppKit hit")
        // Production geometry, not a fake framebuffer: test inverse mappings after multiple native resizes.
        let originalFrame = open.window.frame
        for factor: CGFloat in [0.75, 1] {
            open.window.setFrame(CGRect(x: originalFrame.minX, y: originalFrame.maxY - originalFrame.height * factor,
                                        width: originalFrame.width * factor, height: originalFrame.height * factor), display: true)
            open.content.layoutSubtreeIfNeeded(); open.view.layoutSubtreeIfNeeded()
            let guest = CGPoint(x: open.view.shownPoints.width * 0.4, y: open.view.shownPoints.height * 0.6)
            let local = simulatorTouchPosition(guest, viewport: open.view.bounds, screen: open.view.shownPoints)!
            let event = NSEvent.mouseEvent(with: .leftMouseDown, location: open.view.convert(local, to: nil), modifierFlags: [],
                                           timestamp: 0, windowNumber: open.window.windowNumber, context: nil, eventNumber: 1, clickCount: 1, pressure: 1)!
            let back = open.view.screenPoint(event, clamp: false)!
            try lcdExpect(hypot(back.x - guest.x, back.y - guest.y) < 0.001, "Native resized view maps guest points at backing scale \(open.window.backingScaleFactor)")
        }
        // Exercise actual HID touch through production NSEvent handling, then observe the guest tree.
        // Start in SpringBoard: other apps can also expose a navigation element named Settings.
        try await lcdPress("홈", in: open.content.chrome.controls, open: open)
        await lcdPause(0.5)
        let elements = try await lcdBackground { try simulatorElements(device, screen: activeScreen(of: device)) }
        if let settings = elements.first(where: { $0.label == "Settings" || $0.label == "설정" }) {
            let rect = settings.frame
            let local = simulatorTouchPosition(CGPoint(x: rect.midX, y: rect.midY), viewport: open.view.bounds, screen: open.view.shownPoints)!
            let location = open.view.convert(local, to: nil)
            for type: NSEvent.EventType in [.leftMouseDown, .leftMouseUp] {
                let event = NSEvent.mouseEvent(with: type, location: location, modifierFlags: [], timestamp: 0,
                                               windowNumber: open.window.windowNumber, context: nil, eventNumber: 2, clickCount: 1, pressure: 1)!
                if type == .leftMouseDown { open.view.mouseDown(with: event) } else { open.view.mouseUp(with: event) }
            }
            await lcdPause(1)
            let after = try await lcdBackground { try simulatorElements(device, screen: activeScreen(of: device)) }
            try lcdExpect(!after.map(\.label).elementsEqual(elements.map(\.label)), "LCD NSEvent tap changed the actual guest accessibility tree")
        } else { print("SKIP guest tap: Settings icon was not present; no arbitrary app tapped") }
        try await lcdPress("홈", in: open.content.chrome.controls, open: open)
        let home = try await lcdBackground { try simulatorElements(device, screen: activeScreen(of: device)) }
        try lcdExpect(home.contains { $0.label == "Settings" || $0.label == "설정" }, "Home button result observed in actual SpringBoard tree")
        // Settings supports both inner-display orientations; SpringBoard may lock its orientation.
        if let settings = home.first(where: { $0.label == "Settings" || $0.label == "설정" }) {
            let local = simulatorTouchPosition(CGPoint(x: settings.frame.midX, y: settings.frame.midY), viewport: open.view.bounds, screen: open.view.shownPoints)!
            let location = open.view.convert(local, to: nil)
            for type: NSEvent.EventType in [.leftMouseDown, .leftMouseUp] {
                let event = NSEvent.mouseEvent(with: type, location: location, modifierFlags: [], timestamp: 0,
                    windowNumber: open.window.windowNumber, context: nil, eventNumber: 3, clickCount: 1, pressure: 1)!
                if type == .leftMouseDown { open.view.mouseDown(with: event) } else { open.view.mouseUp(with: event) }
            }
            await lcdPause(1)
        }
        // The folded cover's SpringBoard stays portrait. Test rotation on the real inner display.
        var beforeRotation = originalRotation
        if originalAngle != nil {
            let request: [String: Any] = ["action": "hinge", "degrees": 180.0]
            _ = try await lcdBackground { try executeSimulatorCommand(request, device: device, activity: SimulatorToolActivity(arguments: request, source: "live validation")) }
            open.show(try await lcdBackground { try activeScreen(of: device) })
            beforeRotation = open.active?.rotation ?? originalRotation
            await lcdPause(0.5)
        }
        let actualBeforeRotation = try await lcdBackground { try activeScreen(of: device) }
        beforeRotation = actualBeforeRotation?.rotation ?? beforeRotation
        open.show(actualBeforeRotation)
        print("ROTATE_BEFORE \(beforeRotation) points=\(String(describing: actualBeforeRotation?.points))")
        try await lcdPress("회전", in: open.content.chrome.controls, open: open)
        let turned = try await lcdBackground { try activeScreen(of: device) }
        print("ROTATE_AFTER \(turned?.rotation ?? "none") points=\(String(describing: turned?.points))")
        if turned?.rotation != beforeRotation {
            try lcdExpect(true, "Rotate button result read from actual device")
        } else {
            print("FAIL Rotate button result read from actual device; independent checks continue")
            testFailure = LCDCheckFailure(description: "Rotate button did not change actual device readback")
        }
        open.show(turned)
        if originalAngle != nil {
            let request: [String: Any] = ["action": "hinge", "degrees": 130.0]
            _ = try await lcdBackground { try executeSimulatorCommand(request, device: device, activity: SimulatorToolActivity(arguments: request, source: "live validation")) }
            await lcdPause(0.5)
            let actual = try await lcdBackground { try hingeAngle(of: device) }
            try lcdExpect(abs(actual - 130) < 8, "Hinge backend result read from actual device")
            open.show(try await lcdBackground { try activeScreen(of: device) })
            await lcdPause(0.5)
            lcdCapture(open, name: "02-fold", output: output)
        }
        open.toggleFocus(); await lcdPause()
        try lcdExpect(open.content.focused && open.toolbarDocking?.toolbar.isVisible == false && open.toolbarDocking?.panels.values.allSatisfy({ !$0.isVisible }) == true && !open.content.chrome.handle.isHidden, "Focus mode hides tool panels and preserves handle/menu")
        lcdCapture(open, name: "03-focus", output: output)
        open.toggleToolbox(); await lcdPause(1)
        try lcdExpect(!open.content.focused && open.content.toolsVisible && !open.toolbox.isHidden, "Tool toggle returns from focus mode")
        lcdCapture(open, name: "04-tools", output: output)
        open.toggleToolbox(); await lcdPause(1)
        // A held modifier + manual contact must be released when focus leaves the view.
        open.key(0xE1, down: true)
        let p = CGPoint(x: 50, y: 50)
        open.view.touching = true; open.view.lastFingers = (p, nil); open.touch(p, nil, phase: 0)
        let other = SimulatorDeviceWindow(contentRect: CGRect(x: 50, y: 50, width: 100, height: 100), styleMask: .borderless, backing: .buffered, defer: false)
        other.isReleasedWhenClosed = false
        other.makeKeyAndOrderFront(nil); await lcdPause()
        try lcdExpect(open.heldKeys.isEmpty && !open.view.touching && open.view.scrollFinger == nil, "Actual focus transfer released held keys and manual contact")
        other.close(); bringSimulatorWindowToFront(open)
        let response = try await lcdBackground {
            let request: [String: Any] = ["action": "screenshot"]
            return try executeSimulatorCommand(request, device: device, activity: SimulatorToolActivity(arguments: request, source: "live validation"))
        }
        let items = response["content"] as? [[String: Any]] ?? []
        let image = simulatorActiveCaptureData(items)
        try lcdExpect(image != nil && NSImage(data: image!) != nil, "Existing capture backend returned the actual active display")
        let capture = output.appendingPathComponent("active-display.jpg")
        try image!.write(to: capture, options: .atomic)
        let savedImage = try Data(contentsOf: capture)
        try lcdExpect(savedImage == image, "Saved capture bytes match backend result")
        open.preparePreview()
        let old = open
        open.window.close(); await lcdPause()
        try lcdExpect(simulatorWindows[id] == nil && old.timer?.isValid == false && old.preview?.panel.isVisible != true, "Close cleaned timer, callbacks, registry and preview")
        open = SimulatorWindow(device: device, active: try await lcdBackground { try activeScreen(of: device) })
        simulatorWindows[id] = open
        bringSimulatorWindowToFront(open); await lcdPause()
        try lcdExpect(open.window.isVisible && open.surface != nil, "Closed window reopened with actual framebuffer")
        open.window.miniaturize(nil); await lcdPause()
        try lcdExpect(open.window.isMiniaturized, "Borderless window minimized")
        bringSimulatorWindowToFront(open); await lcdPause()
        try lcdExpect(!open.window.isMiniaturized && open.window.isKeyWindow, "Dock restore path restored the minimized LCD")
    } catch { testFailure = error }
    // Always restore the chosen simulator's original hinge/orientation, including on failed assertions.
    var restorationFailure: Error?
    do {
        if let originalAngle {
            let args: [String: Any] = ["action": "hinge", "degrees": originalAngle]
            _ = try await lcdBackground { try executeSimulatorCommand(args, device: device, activity: SimulatorToolActivity(arguments: args, source: "live restoration")) }
        }
        let orientation = ["rot0": "portrait", "rot90": "landscape-left", "rot270": "landscape-right", "rot180": "upside-down"][originalRotation] ?? "portrait"
        let args: [String: Any] = ["action": "rotate", "orientation": orientation]
        _ = try await lcdBackground { try executeSimulatorCommand(args, device: device, activity: SimulatorToolActivity(arguments: args, source: "live restoration")) }
        let restored = try await lcdBackground { try activeScreen(of: device) }
        print("RESTORED rotation=\(restored?.rotation ?? "none")")
        if let originalAngle { print("RESTORED angle=\(try await lcdBackground { try hingeAngle(of: device) }) expected=\(originalAngle)") }
        open.show(restored); await lcdPause()
        lcdCapture(open, name: "05-restored", output: output)
    } catch { restorationFailure = error }
    open.window.close()
    if let restorationFailure { throw LCDCheckFailure(description: "Restoration failed: \(restorationFailure); original failure: \(String(describing: testFailure))") }
    if let testFailure { throw testFailure }
    print("PASS live native checks. Input was programmatic AppKit delivery in a foreground native window; physical drag, global pointer pass-through, extra displays, VoiceOver and real device shutdown require separate manual checks.")
}

@MainActor
private func lcdRunBackground(_ id: String, output: URL) async throws {
    let device = try await lcdBackground { try bootedDevice(id) }
    let original = try await lcdBackground { try activeScreen(of: device) }
    let originalAngle = original?.foldable == true ? try await lcdBackground { try hingeAngle(of: device) } : nil
    let originalRotation = original?.rotation ?? "rot0"
    print("BACKGROUND_ONLY initial rotation=\(originalRotation) angle=\(String(describing: originalAngle))")
    var open = SimulatorWindow(device: device, active: original)
    simulatorWindows[id] = open
    open.window.orderBack(nil)
    await lcdPause(0.5)
    var failure: Error?
    func command(_ args: [String: Any]) async throws -> [String: Any] {
        try await lcdBackground { try executeSimulatorCommand(args, device: device, activity: SimulatorToolActivity(arguments: args, source: "background live validation")) }
    }
    do {
        try lcdExpect(open.surface != nil && open.window.isVisible, "Background native window has the actual framebuffer")
        if originalAngle != nil {
            let opening = try await command(["action": "hinge", "degrees": 180.0])
            let openingText = (opening["content"] as? [[String: Any]] ?? []).compactMap { $0["text"] as? String }.joined(separator: " ")
            print("DEVICE_READBACK " + openingText)
            if openingText.contains("SpringBoard is not following the hinge") {
                // One documented non-destructive recovery, only when the backend reports this exact condition.
                print("RECOVERY documented sleep/wake pair; no reboot/reset")
                _ = try await command(["action": "button", "button": "lock"])
                _ = try await command(["action": "button", "button": "lock"])
                _ = try await command(["action": "hinge", "degrees": 180.0])
            }
            let inner = try await lcdBackground { try activeScreen(of: device) }
            open.show(inner)
            let flat = try await lcdBackground { try hingeAngle(of: device) }
            try lcdExpect(abs(flat - 180) < 8, "Background backend opened real Duo hinge")
            _ = try await command(["action": "rotate", "orientation": "landscape-left"])
            let turned = try await lcdBackground { try activeScreen(of: device) }
            print("ROTATION_READBACK before=\(inner?.rotation ?? "none") after=\(turned?.rotation ?? "none")")
            if turned?.rotation != inner?.rotation { print("PASS Rotation observed on real Duo inner display") }
            else {
                print("ENVIRONMENT rotation unchanged after actual readback; independent checks continue")
                failure = LCDCheckFailure(description: "Device did not rotate; see actual readback and retained screenshot")
            }
            open.show(turned); await lcdPause(0.5)
            lcdCapture(open, name: "01-rotated", output: output)
            _ = try await command(["action": "hinge", "degrees": 130.0])
            let angle = try await lcdBackground { try hingeAngle(of: device) }
            try lcdExpect(abs(angle - 130) < 8, "Partial fold read back from real Duo")
            open.show(try await lcdBackground { try activeScreen(of: device) })
            await lcdPause(0.5)
            lcdCapture(open, name: "02-fold", output: output)
        }
        open.toggleFocus(); await lcdPause(0.5)
        try lcdExpect(open.content.focused && open.toolbarDocking?.toolbar.isVisible == false && open.toolbarDocking?.panels.values.allSatisfy({ !$0.isVisible }) == true && !open.content.chrome.handle.isHidden, "Native focus presentation hides tool panels and retains the menu/handle")
        lcdCapture(open, name: "03-focus", output: output)
        open.toggleToolbox(); await lcdPause(1)
        try lcdExpect(!open.content.focused && open.content.toolsVisible && !open.toolbox.isHidden, "Native tool presentation returns from focus mode")
        lcdCapture(open, name: "04-tools", output: output)
        open.toggleToolbox(); await lcdPause(1)
        let response = try await command(["action": "screenshot"])
        let image = simulatorActiveCaptureData(response["content"] as? [[String: Any]] ?? [])
        try lcdExpect(image != nil && NSImage(data: image!) != nil, "Background capture backend returned actual active-display image")
        let target = output.appendingPathComponent("active-display.jpg")
        try image!.write(to: target, options: .atomic)
        let saved = try Data(contentsOf: target)
        try lcdExpect(saved == image, "Capture write/retrieval bytes match actual backend result")
        // Exercise the production cleanup handler with real held HID input, without changing Mac focus.
        open.key(0xE1, down: true)
        let contact = CGPoint(x: 2, y: 2)
        open.view.touching = true; open.view.lastFingers = (contact, nil)
        open.touch(contact, nil, phase: 0)
        _ = try await lcdBackground { true } // Queue barrier: down events were sent.
        open.windowDidResignKey(Notification(name: NSWindow.didResignKeyNotification))
        _ = try await lcdBackground { true } // Queue barrier: cleanup up events were sent.
        await lcdPause()
        try lcdExpect(open.heldKeys.isEmpty && !open.view.touching && !open.touchesActive, "Production focus-loss handler released actual HID key/contact (delegate invoked by harness)")
        open.preparePreview()
        let opacity = SimulatorPreviewWindow.opacityMenu().items.first { $0.tag == 25 }!
        _ = NSApp.sendAction(opacity.action!, to: opacity.target, from: opacity)
        try lcdExpect(open.preview?.panel.alphaValue == 0.25 && open.window.alphaValue == 1, "Actual preview opacity change leaves LCD fully opaque")
        let old = open
        open.window.close(); await lcdPause()
        try lcdExpect(simulatorWindows[id] == nil && old.timer?.isValid == false && old.preview?.panel.isVisible != true, "Native close cleaned registry/timer/preview")
        open = SimulatorWindow(device: device, active: try await lcdBackground { try activeScreen(of: device) })
        simulatorWindows[id] = open
        open.window.orderBack(nil); await lcdPause()
        try lcdExpect(open.window.isVisible && open.surface != nil, "Native reopen reconnected the actual framebuffer")
    } catch { failure = error }
    var restoreFailure: Error?
    do {
        if let originalAngle { _ = try await command(["action": "hinge", "degrees": originalAngle]) }
        let orientation = ["rot0": "portrait", "rot90": "landscape-left", "rot270": "landscape-right", "rot180": "upside-down"][originalRotation] ?? "portrait"
        _ = try await command(["action": "rotate", "orientation": orientation])
        let restored = try await lcdBackground { try activeScreen(of: device) }
        try lcdExpect(restored?.rotation == originalRotation, "Original device rotation restored")
        if let originalAngle {
            let restoredAngle = try await lcdBackground { try hingeAngle(of: device) }
            try lcdExpect(abs(restoredAngle - originalAngle) < 8, "Original device hinge restored")
        }
        open.show(restored); await lcdPause(0.5)
        lcdCapture(open, name: "05-restored", output: output)
    } catch { restoreFailure = error }
    open.window.close()
    if let restoreFailure { throw LCDCheckFailure(description: "Restoration failed: \(restoreFailure), check failure: \(String(describing: failure))") }
    if let failure { throw failure }
    print("PASS background-only backend/native presentation checks. No Mac input or activation was sent. This does not verify physical controls, foreground focus transfer, minimize/Dock UI or device shutdown.")
}

/// Persistent development launch: production controls and menu, isolated settings, no test actions.
func runSimulatorWindowPreview(id: String, output: URL) -> Never {
    let session = CGSessionCopyCurrentDictionary() as? [String: Any] ?? [:]
    guard session["CGSSessionScreenIsLocked"] as? Bool != true,
          CGDisplayIsAsleep(CGMainDisplayID()) == 0, CGDisplayIsActive(CGMainDisplayID()) != 0 else {
        fputs("ENVIRONMENT: unlocked active interactive desktop required.\n", stderr); exit(2)
    }
    NSApplication.shared.setActivationPolicy(.regular)
    menuBar = MenuBar()
    NSApp.delegate = menuBar
    Task { @MainActor in
        do {
            let device = try await lcdBackground { try bootedDevice(id) }
            let active = try await lcdBackground { try activeScreen(of: device) }
            let open = SimulatorWindow(device: device, active: active)
            simulatorWindows[id] = open
            bringSimulatorWindowToFront(open)
            await lcdPause(1)
            let grip = open.window.convertToScreen(open.content.chrome.grip.convert(open.content.chrome.grip.bounds, to: nil))
            let info: [String: Any] = ["pid": ProcessInfo.processInfo.processIdentifier,
                "window": open.window.windowNumber, "device": id,
                "visible": open.window.isVisible, "framebuffer": open.surface != nil,
                "titled": open.window.styleMask.contains(.titled), "alpha": open.window.alphaValue,
                "toolbar": open.toolbarDocking?.toolbar.windowNumber ?? -1,
                "grip": ["x": grip.minX, "y": grip.minY, "width": grip.width, "height": grip.height]]
            try JSONSerialization.data(withJSONObject: info, options: .prettyPrinted).write(to: output.appendingPathComponent("ready.json"))
            lcdCapture(open, name: "preview-device", output: output)
        } catch {
            try? error.localizedDescription.write(to: output.appendingPathComponent("error.txt"), atomically: true, encoding: .utf8)
            NSApp.terminate(nil)
        }
    }
    NSApplication.shared.run()
    exit(0)
}

func runSimulatorWindowLiveCheck() -> Never {
    let session = CGSessionCopyCurrentDictionary() as? [String: Any] ?? [:]
    guard session["CGSSessionScreenIsLocked"] as? Bool != true,
          CGDisplayIsAsleep(CGMainDisplayID()) == 0, CGDisplayIsActive(CGMainDisplayID()) != 0 else {
        fputs("ENVIRONMENT: unlocked active interactive desktop required.\n", stderr); exit(2)
    }
    let env = ProcessInfo.processInfo.environment
    guard let id = env["LCD_CHECK_UDID"], let path = env["LCD_CHECK_OUTPUT"] else { exit(2) }
    let backgroundOnly = env["LCD_CHECK_BACKEND_ONLY"] == "1"
    NSApplication.shared.setActivationPolicy(backgroundOnly ? .accessory : .regular)
    if !backgroundOnly {
        menuBar = MenuBar()
        NSApp.delegate = menuBar
    }
    Task { @MainActor in
        do {
            if backgroundOnly { try await lcdRunBackground(id, output: URL(fileURLWithPath: path)) }
            else { try await lcdRun(id, output: URL(fileURLWithPath: path)) }
            exit(0)
        }
        catch { print("FAIL \(error)"); fflush(stdout); exit(1) }
    }
    NSApplication.shared.run()
    exit(0)
}
