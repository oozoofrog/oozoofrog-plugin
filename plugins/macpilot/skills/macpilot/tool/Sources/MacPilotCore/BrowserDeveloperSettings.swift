import AppKit
import ApplicationServices

/// Browser-owned UI only. There is intentionally no approval flag, environment
/// override, preference-file writer or remote-debugging backend.
@MainActor public enum BrowserDeveloperSettings {
    struct Request {
        let operation: String, browser: String, setting: String, identity: String
        let pid: Int32, windowID: UInt32?, timeout: Int
        init(_ a: Arguments) throws {
            try a.only(["operation", "browser", "setting", "pid", "processStartID", "windowID", "timeoutMs"])
            operation = try a.string("operation"); browser = try a.string("browser")
            setting = try a.string("setting"); identity = try a.string("processStartID", limit: 64)
            pid = Int32(try a.integer("pid", range: 1...Int(Int32.max)))
            windowID = a.values["windowID"] == nil ? nil : UInt32(try a.integer("windowID", range: 1...Int(UInt32.max)))
            timeout = try a.integer("timeoutMs", default: 60_000, range: 5_000...120_000)
            guard ["status", "prepare", "enable"].contains(operation),
                  (browser == "safari" && windowID == nil && ["developer_features", "javascript_apple_events"].contains(setting)) ||
                  (browser == "chrome" && setting == "extension_developer_mode" && windowID != nil) else {
                throw ToolFailure("invalid_argument", "Use Safari developer_features/javascript_apple_events, or Chrome extension_developer_mode with an exact windowID")
            }
        }
        var labels: [String] {
            switch setting {
            case "developer_features": return ["Show features for web developers", "Show Develop menu in menu bar", "웹 개발자를 위한 기능 보기", "메뉴 막대에서 개발자용 메뉴 보기"]
            case "javascript_apple_events": return ["Allow JavaScript from Apple Events", "Apple 이벤트에서 JavaScript 허용"]
            default: return ["Developer mode", "개발자 모드"]
            }
        }
        var description: String {
            switch setting {
            case "developer_features": return "Safari의 웹 개발자 기능을 켭니다."
            case "javascript_apple_events": return "Safari에서 Apple Events를 통한 웹페이지 JavaScript 실행을 허용합니다."
            default: return "선택한 Chrome 창의 프로필에서 확장 프로그램 개발자 모드를 켭니다."
            }
        }
    }
    struct Control {
        let root: AXUIElement, node: AXUIElement
        let label: String, enabled: Bool, writable: Bool
    }
    static func requireBrowser(_ r: Request) throws {
        try ProcessIdentity.require(pid: r.pid, expected: r.identity)
        let expected = r.browser == "safari" ? "com.apple.Safari" : "com.google.Chrome"
        guard NSRunningApplication(processIdentifier: r.pid)?.bundleIdentifier == expected else {
            throw ToolFailure("browser_target_mismatch", "PID is not the selected browser")
        }
        guard AXIsProcessTrusted() else { throw ToolFailure("accessibility_denied", "Browser settings require Accessibility access") }
        try AX.ensureMessagingTimeout()
    }
    // Bounded traversal. A partial tree must never be treated as an absent or
    // unique control. Secure fields and web contents are not returned as text.
    static func elements(_ root: AXUIElement) throws -> [AXUIElement] {
        var result: [AXUIElement] = [], pending = [(root, 0)]
        let deadline = Date().addingTimeInterval(3)
        while let (e, depth) = pending.popLast() {
            try Task.checkCancellation()
            guard result.count < 1500, Date() < deadline else { throw ToolFailure("settings_tree_partial", "Settings AX tree exceeded its bounded traversal") }
            if result.contains(where: { CFEqual($0, e) }) { continue }
            result.append(e)
            if AX.string(e, kAXSubroleAttribute) == "AXSecureTextField" { continue }
            var count = 0
            let error = AXUIElementGetAttributeValueCount(e, kAXChildrenAttribute as CFString, &count)
            if error == .attributeUnsupported || error == .noValue { continue }
            guard error == .success else { throw ToolFailure("settings_ui_unavailable", "Cannot read settings children") }
            if count == 0 { continue }
            guard depth < 28, count <= 1500 - result.count else { throw ToolFailure("settings_tree_partial", "Settings tree is too deep or wide") }
            var raw: CFArray?
            guard AXUIElementCopyAttributeValues(e, kAXChildrenAttribute as CFString, 0, count, &raw) == .success,
                  let children = raw as? [AXUIElement] else { throw ToolFailure("settings_ui_unavailable", "Cannot read settings subtree") }
            pending.append(contentsOf: children.reversed().map { ($0, depth + 1) })
        }
        return result
    }
    static func roots(_ r: Request, engine: Engine) throws -> [AXUIElement] {
        let windows = try AX.windows(r.pid)
        guard r.browser == "chrome" else { return windows }
        guard let row = engine.windowRows(pid: r.pid).first(where: { ($0["windowID"] as? UInt32) == r.windowID }),
              let frame = row["frame"] as? [String: Double] else { throw ToolFailure("window_unavailable", "Selected Chrome window is gone") }
        let matches = windows.filter { AX.frame($0)?.object == frame }
        guard matches.count == 1 else { throw ToolFailure("ambiguous_window", "Selected Chrome AX window mapping is not unique") }
        return matches
    }
    static func control(_ r: Request, engine: Engine) throws -> Control {
        try requireBrowser(r)
        var matches: [Control] = []
        for root in try roots(r, engine: engine) {
            // Safari web pages cannot impersonate the native Preferences window.
            if r.browser == "safari", AX.string(root, kAXIdentifierAttribute).hasPrefix("SafariWindow") { continue }
            let tree = try elements(root)
            let scope: AXUIElement?
            if r.browser == "safari" {
                let panes = tree.filter { ["SafariAdvancedPreferencesView", "SafariDeveloperPreferencesView"].contains(AX.string($0, kAXIdentifierAttribute)) }
                guard panes.count == 1 else { continue }; scope = panes[0]
            } else {
                let pages = tree.filter { AX.string($0, kAXRoleAttribute) == "AXWebArea" && (AX.value($0, kAXURLAttribute) as? URL)?.absoluteString == "chrome://extensions/" }
                guard pages.count == 1 else { continue }; scope = pages[0]
            }
            for node in try elements(scope!) where AX.string(node, kAXRoleAttribute) == kAXCheckBoxRole && r.labels.contains(AX.string(node, kAXTitleAttribute)) {
                guard let value = AX.value(node, kAXValueAttribute) as? NSNumber, [0, 1].contains(value.intValue) else {
                    throw ToolFailure("settings_state_unknown", "Developer toggle has no binary AX value")
                }
                matches.append(Control(root: root, node: node, label: AX.string(node, kAXTitleAttribute), enabled: value.boolValue,
                                       writable: AX.bool(node, kAXEnabledAttribute, default: false) && AX.actions(node).contains(kAXPressAction)))
            }
        }
        guard matches.count == 1 else { throw ToolFailure(matches.isEmpty ? "settings_ui_required" : "ambiguous_setting", "Open the selected native settings pane; only a unique supported toggle is accepted. Safari JavaScript requires developer_features first") }
        return matches[0]
    }
    static func pressMenu(_ paths: [[String]], request r: Request) throws {
        for path in paths {
            do { _ = try AX.resolveMenuItem(pid: r.pid, titlePath: path) }
            catch let failure as ToolFailure where failure.code == "menu_item_unavailable" { continue }
            _ = try AX.pressMenuItem(pid: r.pid, processStartID: r.identity, titlePath: path); return
        }
        throw ToolFailure("unsupported_settings_ui", "Browser menu is unavailable in this version or language")
    }
    static func prepare(_ r: Request, engine: Engine) async throws {
        try requireBrowser(r)
        if r.browser == "chrome" {
            if (try? control(r, engine: engine)) != nil { return }
            let observation = try await engine.observe(pid: r.pid, processStartID: r.identity, windowID: r.windowID,
                                                       screenshot: false, maxNodes: 1, maxDepth: 1)
            let focus = try await WindowActions.focus(observation, node: nil, timeoutMilliseconds: 1500)
            guard focus["status"] as? String == "focus_verified" else { throw ToolFailure("focus_unverified", "Cannot select the approved Chrome window") }
            try ProcessIdentity.require(pid: r.pid, expected: r.identity)
            try pressMenu([["Window", "Extensions"], ["창", "확장 프로그램"]], request: r)
        } else {
            try pressMenu([["Safari", "Settings…"], ["Safari", "설정…"], ["Safari", "Preferences…"]], request: r)
            let labels = r.setting == "developer_features" ? ["Advanced", "고급"] : ["Developer", "개발자"]
            var buttons: [AXUIElement] = []
            let paneDeadline = Date().addingTimeInterval(3)
            repeat {
                buttons = []
                for root in try AX.windows(r.pid) where !AX.string(root, kAXIdentifierAttribute).hasPrefix("SafariWindow") {
                    for toolbar in try elements(root) where AX.string(toolbar, kAXRoleAttribute) == kAXToolbarRole {
                        buttons += try elements(toolbar).filter { AX.string($0, kAXRoleAttribute) == kAXButtonRole && labels.contains(AX.string($0, kAXTitleAttribute)) }
                    }
                }
                if !buttons.isEmpty { break }
                try await Task.sleep(nanoseconds: 100_000_000)
            } while Date() < paneDeadline
            guard buttons.count == 1 else { throw ToolFailure("settings_prerequisite_required", "Safari settings tab is unavailable; enable developer_features separately first if needed") }
            try ProcessIdentity.require(pid: r.pid, expected: r.identity)
            try AX.requireMutationSuccess(AXUIElementPerformAction(buttons[0], kAXPressAction as CFString), operation: "select Safari settings pane")
        }
        let deadline = Date().addingTimeInterval(3)
        repeat {
            if (try? control(r, engine: engine)) != nil { return }
            try await Task.sleep(nanoseconds: 100_000_000)
        } while Date() < deadline
        _ = try control(r, engine: engine)
    }
    static func humanConfirmation(_ message: String, timeout: Int) async throws -> Bool {
        let script = """
        function run() {
          const app=Application.currentApplication(); app.includeStandardAdditions=true;
          try {
            const answer=app.displayDialog(\(jsonString(message)), {withTitle:'MacPilot — 브라우저 설정 승인',
              buttons:['취소','허용'], defaultButton:'취소', cancelButton:'취소', givingUpAfter:\(timeout / 1000)});
            return JSON.stringify({approved:answer.buttonReturned==='허용' && !answer.gaveUp});
          } catch(error) { if (error.errorNumber===-128 || String(error).includes('-128')) return '{"approved":false}'; throw error; }
        }
        """
        let output = try await CommandRunner.run(executable: URL(fileURLWithPath: "/usr/bin/osascript"), arguments: ["-l", "JavaScript"],
                                                standardInput: script, timeoutMilliseconds: timeout + 1000, maxOutputBytes: 4096)
        guard output.exitCode == 0, !output.stdoutTruncated,
              let data = output.stdout.data(using: .utf8), let value = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let approved = value["approved"] as? Bool else { throw ToolFailure("approval_unavailable", "Native approval was not received; no developer setting was changed") }
        return approved
    }
    // Test seams stay internal. The CLI/MCP entry always calls humanConfirmation.
    static func approvedEnable<State>(initial: State, isEnabled: (State) -> Bool, confirm: () async throws -> Bool,
                                      reread: () throws -> State, same: (State, State) -> Bool,
                                      press: () throws -> Void, verify: () async throws -> Bool) async throws -> String {
        if isEnabled(initial) { return "already_enabled" }
        guard try await confirm() else { return "approval_declined" }
        try Task.checkCancellation()
        let fresh = try reread()
        guard same(initial, fresh) else { throw ToolFailure("settings_target_changed", "Browser settings changed while approval was pending; prepare again") }
        if isEnabled(fresh) { return "already_enabled" }
        do { try press() }
        catch let error as ToolFailure where error.code == "ax_outcome_uncertain" {
            // A slow browser may complete AXPress after its messaging deadline.
            guard try await verify() else { throw error }; return "enabled_verified"
        }
        guard try await verify() else { throw ToolFailure("settings_outcome_unconfirmed", "Enable was dispatched once; reread status before any retry. A browser-owned confirmation may require the user") }
        return "enabled_verified"
    }
    public static func call(_ a: Arguments, engine: Engine) async throws -> [String: Any] {
        var result = try await execute(a, engine: engine, confirm: humanConfirmation)
        if result["approval"] as? String == "confirmation_accepted" { result["approval"] = "native_dialog_accepted" }
        return result
    }
    static func execute(_ a: Arguments, engine: Engine, confirm: (String, Int) async throws -> Bool) async throws -> [String: Any] {
        let r = try Request(a)
        try requireBrowser(r)
        if r.operation != "status" { try await prepare(r, engine: engine) }
        let initial = try control(r, engine: engine)
        var status = "settings_status"
        if r.operation == "enable" {
            guard initial.enabled || initial.writable else { throw ToolFailure("settings_managed_or_disabled", "Browser policy or UI disables this setting") }
            let message = "\(r.description)\n\n브라우저: \(r.browser)\nPID: \(r.pid)\n시작 ID: \(r.identity)\n창: \(AX.string(initial.root, kAXTitleAttribute))\n설정: \(initial.label)\n범위: \(r.browser == "safari" ? "현재 macOS 사용자의 Safari" : "선택한 창의 Chrome 프로필 (프로필 이름은 검증하지 않음)")\n\n이 설정 하나만 켭니다. 허용하려면 직접 ‘허용’을 누르세요."
            status = try await approvedEnable(initial: initial, isEnabled: { $0.enabled },
                confirm: { try await confirm(message, r.timeout) }, reread: { try control(r, engine: engine) },
                same: { CFEqual($0.root, $1.root) && CFEqual($0.node, $1.node) && $0.label == $1.label && $1.writable },
                press: {
                    try Task.checkCancellation(); try requireBrowser(r)
                    try AX.requireMutationSuccess(AXUIElementPerformAction(initial.node, kAXPressAction as CFString), operation: "enable approved developer setting")
                }, verify: {
                    let deadline = Date().addingTimeInterval(3)
                    repeat {
                        try Task.checkCancellation()
                        let fresh = try control(r, engine: engine)
                        guard CFEqual(initial.root, fresh.root) else { throw ToolFailure("settings_target_changed", "Settings window changed during verification") }
                        if fresh.enabled { return true }
                        try await Task.sleep(nanoseconds: 100_000_000)
                    } while Date() < deadline
                    return false
                })
        }
        // A declined dialog can coincide with user closing the settings window.
        let final = status == "approval_declined" ? nil : try control(r, engine: engine)
        return ["status": status, "browser": r.browser, "setting": r.setting, "pid": r.pid, "processStartID": r.identity,
                "windowTitle": AX.string(initial.root, kAXTitleAttribute), "windowID": r.windowID.map { $0 as Any } ?? NSNull(), "label": initial.label,
                "canEnable": final.map { $0.writable as Any } ?? NSNull(),
                "enabled": final.map { $0.enabled as Any } ?? NSNull(), "approval": status == "enabled_verified" ? "confirmation_accepted" : "not_used_or_declined",
                "verification": "Selected browser-owned AX checkbox value; no DOM execution, extension installation or Automation permission was tested"]
    }
}
