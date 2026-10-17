import AppKit
import ApplicationServices

/// Opens native System Settings with a compact attached drag source.
/// Optional synthetic drag never clicks TCC switches or native approval buttons.
@MainActor public enum PermissionSetup {
    static func settingsURL(for raw: String) throws -> URL {
        let first = try PermissionKind.plan(raw)[0]
        return URL(string: "x-apple.systempreferences:com.apple.preference.security?\(first.pane)")!
    }
    static func applicationURL(executable: URL) throws -> URL {
        let bundle = executable.deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()
        guard bundle.pathExtension == "app", executable.lastPathComponent == "macpilot",
              let info = Bundle(url: bundle), info.bundleIdentifier == "local.macpilot",
              info.executableURL?.standardizedFileURL == executable.standardizedFileURL else {
            throw ToolFailure("app_bundle_required", "Run signed bin/MacPilot.app; a raw SwiftPM executable is not a draggable app")
        }
        return bundle
    }

    struct Item {
        let element: AXUIElement
        let node: Node
    }
    static func items(_ root: AXUIElement) -> [Item] {
        // A bounded traversal also keeps authorization sheets out of logging.
        var result: [Item] = [], visited: [AXUIElement] = []
        let deadline = Date().addingTimeInterval(2)
        func walk(_ element: AXUIElement, path: [Int]) {
            guard result.count < 800, path.count < 24, Date() < deadline,
                  !visited.contains(where: { CFEqual($0, element) }) else { return }
            visited.append(element)
            let node = AX.node(element, path: path)
            result.append(Item(element: element, node: node))
            guard !node.secure, node.role != kAXSheetRole || path.isEmpty else { return }
            for (index, child) in ((AX.value(element, kAXChildrenAttribute) as? [AXUIElement]) ?? []).prefix(200).enumerated() {
                walk(child, path: path + [index])
            }
        }
        walk(root, path: [])
        return result
    }
    static func listNode(_ nodes: [Node], window: Rect, kind: PermissionKind) throws -> Node {
        guard kind.acceptsAppDrop else { throw ToolFailure("app_drop_unsupported", "This permission has no app-drop list") }
        // Screen Recording can contain a second audio-only list. The top list
        // is the combined screen/audio permission. Never select the sidebar.
        let candidates = nodes.filter {
            [kAXOutlineRole, kAXTableRole].contains($0.role) && $0.frame.map {
                $0.width > 150 && $0.height > 12 && $0.x >= window.x + window.width * 0.28 && window.cg.contains($0.cg)
            } == true
        }.sorted { ($0.frame?.y ?? 0) < ($1.frame?.y ?? 0) }
        guard let first = candidates.first else { throw ToolFailure("permission_list_unavailable", "The native app list is not exposed; use System Settings directly") }
        return first
    }
    private static func element(at path: [Int], root: AXUIElement) -> AXUIElement? {
        var current = root
        for index in path {
            guard let children = AX.value(current, kAXChildrenAttribute) as? [AXUIElement], children.indices.contains(index) else { return nil }
            current = children[index]
        }
        return current
    }
    private static func nativeWindow(kind: PermissionKind) throws -> (NSRunningApplication, AXUIElement) {
        guard let app = NSRunningApplication.runningApplications(withBundleIdentifier: "com.apple.systempreferences").first else {
            throw ToolFailure("settings_unavailable", "System Settings is not running")
        }
        let windows = try AX.windows(app.processIdentifier).filter { kind.titles.contains(AX.string($0, kAXTitleAttribute)) }
        guard windows.count == 1 else { throw ToolFailure("settings_pane_unconfirmed", "The requested native settings pane is not confirmed; no input sent") }
        return (app, windows[0])
    }
    private static func openPane(_ kind: PermissionKind, deadline: Date) async throws -> (NSRunningApplication, AXUIElement) {
        guard NSWorkspace.shared.open(try settingsURL(for: kind.rawValue)) else { throw ToolFailure("settings_open_failed", "Cannot open System Settings") }
        while Date() < deadline {
            try Task.checkCancellation()
            if let result = try? nativeWindow(kind: kind) { return result }
            try await Task.sleep(nanoseconds: 100_000_000)
        }
        throw ToolFailure("settings_pane_unconfirmed", "Requested settings pane did not become available; no drag sent")
    }
    private static func row(_ list: AXUIElement) -> Bool {
        items(list).contains { $0.node.value == "MacPilot" || $0.node.title == "MacPilot" }
    }
    private static func pendingPrompt(_ settings: AXUIElement) -> NativePermissionPrompt {
        let sheets = items(settings).filter { $0.node.role == kAXSheetRole }
        let labels = sheets.flatMap { items($0.element) }.map(\.node)
        let result = NativePermissionPrompt.classify(buttons: labels.filter { $0.role == kAXButtonRole }.map(\.title),
            hasSecureInput: labels.contains { $0.secure }, hasSheet: !sheets.isEmpty)
        if result == .none, ["com.apple.SecurityAgent", "com.apple.LocalAuthentication.UIAgent", "com.apple.CoreServicesUIAgent"].contains(NSWorkspace.shared.frontmostApplication?.bundleIdentifier ?? "") {
            return .authenticationRequired
        }
        return result
    }
    private static func hit(_ point: CGPoint, expectedPID: Int32, frame: Rect) -> Bool {
        let cocoa = CGPoint(x: point.x, y: CGDisplayBounds(CGMainDisplayID()).height - point.y)
        let id = NSWindow.windowNumber(at: cocoa, belowWindowWithWindowNumber: 0)
        guard let rows = CGWindowListCopyWindowInfo([.optionIncludingWindow, .excludeDesktopElements], CGWindowID(id)) as? [[String: Any]],
              let info = rows.first, (info[kCGWindowOwnerPID as String] as? NSNumber)?.int32Value == expectedPID,
              let raw = info[kCGWindowBounds as String] as? [String: Any], let actual = CGRect(dictionaryRepresentation: raw as CFDictionary) else { return false }
        return Rect(actual) == frame
    }
    static func drag(from source: CGPoint, to destination: CGPoint,
                     sourceWindow: NSWindow, targetWindow: AXUIElement,
                     sourceApp: NSRunningApplication, targetApp: NSRunningApplication,
                     validate: () throws -> Void) async throws {
        try Input.preflight()
        func sourceFrame() -> Rect {
            let frame = sourceWindow.frame
            return Rect(CGRect(x: frame.minX, y: CGDisplayBounds(CGMainDisplayID()).height-frame.maxY, width: frame.width, height: frame.height))
        }
        let beforeSource = sourceFrame()
        guard sourceWindow.isVisible, let beforeTarget = AX.frame(targetWindow),
              let sourceID = ProcessIdentity.startID(pid: sourceApp.processIdentifier),
              let targetID = ProcessIdentity.startID(pid: targetApp.processIdentifier) else { throw ToolFailure("stale_app_identity", "Native windows are unavailable") }
        // Keep native Settings as the key app throughout the drag. A non-key
        // source panel does not need to activate or expose an AXWindow.
        try validate()
        guard [sourceApp.processIdentifier, targetApp.processIdentifier].contains(NSWorkspace.shared.frontmostApplication?.processIdentifier ?? 0),
              hit(source, expectedPID: sourceApp.processIdentifier, frame: beforeSource),
              hit(destination, expectedPID: targetApp.processIdentifier, frame: beforeTarget) else {
            throw ToolFailure("occluded_target", "Attached icon or native settings list is obscured; no drag sent")
        }
        let eventSource = CGEventSource(stateID: .privateState)
        var held = false, last = source
        func post(_ type: CGEventType, _ point: CGPoint) throws {
            guard let event = CGEvent(mouseEventSource: eventSource, mouseType: type, mouseCursorPosition: point, mouseButton: .left) else { throw ToolFailure("event_failed", "Cannot create native drag event") }
            event.flags = []; event.post(tap: .cghidEventTap)
        }
        defer {
            if held {
                // Cancel the active drag before releasing, rather than dropping
                // on an unconfirmed window after a user switch or cancellation.
                for event in (try? Input.keyEvents(key: "escape", modifiers: [])) ?? [] { event.post(tap: .cghidEventTap) }
                try? post(.leftMouseUp, last)
            }
        }
        try post(.mouseMoved, source)
        try post(.leftMouseDown, source); held = true
        try await Task.sleep(nanoseconds: 120_000_000)
        for step in 1...36 {
            try Task.checkCancellation(); try Input.preflight()
            try ProcessIdentity.require(pid: sourceApp.processIdentifier, expected: sourceID)
            try ProcessIdentity.require(pid: targetApp.processIdentifier, expected: targetID)
            guard sourceWindow.isVisible && sourceFrame() == beforeSource, AX.frame(targetWindow) == beforeTarget,
                  [sourceApp.processIdentifier, targetApp.processIdentifier].contains(NSWorkspace.shared.frontmostApplication?.processIdentifier ?? 0) else {
                throw ToolFailure("settings_target_changed", "Native window geometry or foreground changed; drag cancelled")
            }
            last = CGPoint(x: source.x + (destination.x-source.x) * Double(step)/36,
                           y: source.y + (destination.y-source.y) * Double(step)/36)
            try post(.leftMouseDragged, last)
            try await Task.sleep(nanoseconds: 25_000_000)
        }
        try validate()
        guard hit(destination, expectedPID: targetApp.processIdentifier, frame: beforeTarget) else { throw ToolFailure("occluded_target", "Native target was obscured; drag cancelled") }
        try post(.leftMouseUp, destination); held = false
    }

    static func autoRegister(_ kind: PermissionKind, source: PermissionAppDragView, window: NSWindow, timeout: Int) async throws -> [String: Any] {
        guard kind.acceptsAppDrop else { throw ToolFailure("app_drop_unsupported", "This permission uses native consent rather than app drag") }
        let deadline = Date().addingTimeInterval(Double(timeout)/1000)
        let (settingsApp, settings) = try await openPane(kind, deadline: deadline)
        guard let frame = AX.frame(settings) else { throw ToolFailure("settings_unavailable", "Cannot read native settings geometry") }
        let list = try listNode(items(settings).map(\.node), window: frame, kind: kind)
        guard let listElement = element(at: list.path, root: settings), let targetFrame = list.frame else { throw ToolFailure("permission_list_unavailable", "Native list disappeared") }
        let prompt = pendingPrompt(settings)
        if prompt != .none {
            return ["status": prompt.rawValue, "registrationVerified": row(listElement)]
        }
        if row(listElement) {
            return ["status": "already_listed", "registrationVerified": true, "rowIdentity": "display_name_only"]
        }
        let cocoa = source.convert(NSPoint(x: 44, y: source.bounds.midY), to: nil)
        let screen = window.convertPoint(toScreen: cocoa)
        let from = CGPoint(x: screen.x, y: CGDisplayBounds(CGMainDisplayID()).height - screen.y)
        let to = CGPoint(x: targetFrame.x + min(160, targetFrame.width*0.35), y: targetFrame.y + min(20, targetFrame.height/2))
        let application = source.applicationURL
        try await drag(from: from, to: to, sourceWindow: window, targetWindow: settings, sourceApp: NSRunningApplication.current, targetApp: settingsApp) {
            guard source.applicationURL == application, kind.titles.contains(AX.string(settings, kAXTitleAttribute)),
                  let current = try? listNode(items(settings).map(\.node), window: AX.frame(settings) ?? frame, kind: kind), current.frame == targetFrame else {
                throw ToolFailure("settings_target_changed", "Attached icon or native permission pane changed; drag cancelled")
            }
        }
        let verifyUntil = min(deadline, Date().addingTimeInterval(3))
        repeat {
            try Task.checkCancellation()
            let prompt = pendingPrompt(settings)
            if prompt != .none {
                return ["status": prompt.rawValue, "dragAttempted": true,
                        "registrationVerified": element(at: list.path, root: settings).map(row) ?? false]
            }
            if let current = element(at: list.path, root: settings), row(current) {
                settingsApp.activate(options: [])
                return ["status": "registered", "dragAttempted": true, "registrationVerified": true, "rowIdentity": "display_name_only"]
            }
            try await Task.sleep(nanoseconds: 100_000_000)
        } while Date() < verifyUntil
        return ["status": "registration_unconfirmed", "dragAttempted": true, "registrationVerified": false]
    }

    public static func open(kind: String, timeout: Int, targetBundleID: String = "com.apple.Safari") async throws -> [String: Any] {
        _ = try PermissionKind.plan(kind)
        guard let executable = Bundle.main.executableURL else { throw ToolFailure("app_bundle_required", "Cannot locate MacPilot.app") }
        let application = try applicationURL(executable: executable)
        let configuration = NSWorkspace.OpenConfiguration()
        configuration.arguments = ["permission-setup-ui", kind, targetBundleID]
        configuration.createsNewApplicationInstance = true
        configuration.activates = false
        let app: NSRunningApplication = try await withCallbackDeadline(timeoutMilliseconds: timeout,
            timeoutFailure: ToolFailure("permission_setup_timeout", "Native setup launch timed out; inspect System Settings before retrying")) { finish in
            NSWorkspace.shared.openApplication(at: application, configuration: configuration) { app, error in
                if let app { finish(.success(app)) }
                else { finish(.failure(error ?? ToolFailure("permission_setup_failed", "Cannot launch the attached permission guide"))) }
            }
        }
        return ["status": "permission_setup_launch_accepted", "pid": app.processIdentifier, "applicationPath": application.path,
                "kind": kind, "approvalRequired": true, "verification": "Guide launch accepted. User drag or optional auto-add, native approval, and current MCP permissions must be checked separately."]
    }

    public static func run(kind: String, targetBundleID: String) throws {
        let plan = try PermissionKind.plan(kind)
        guard let executable = Bundle.main.executableURL else { throw ToolFailure("app_bundle_required", "Cannot locate MacPilot.app") }
        let controller = PermissionSetupController(applicationURL: try applicationURL(executable: executable), plan: plan, targetBundleID: targetBundleID)
        NSApplication.shared.setActivationPolicy(.accessory)
        controller.show()
        controller.openSettings()
        NSApplication.shared.run()
        withExtendedLifetime(controller) {}
    }
}
