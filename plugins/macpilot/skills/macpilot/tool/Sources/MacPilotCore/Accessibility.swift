import AppKit
import ApplicationServices

public struct AXMenuItemInfo: Codable, Equatable {
    public var path: [String]
    public var title: String
    public var titleTruncated: Bool
    public var enabled: Bool
    public var selected: Bool?
    public var hasSubmenu: Bool
    public var actions: [String]
    public var actionsTruncated: Bool
}

@MainActor public enum AX {
    private static let systemWideMessagingTimeoutResult: AXError = {
        AXUIElementSetMessagingTimeout(AXUIElementCreateSystemWide(), 0.3)
    }()

    public static func ensureMessagingTimeout() throws {
        guard systemWideMessagingTimeoutResult == .success else {
            throw ToolFailure("ax_timeout_configuration_failed", "Cannot configure the process-wide 300 ms Accessibility messaging timeout")
        }
    }

    public static func mutationFailure(_ error: AXError, operation: String) -> ToolFailure {
        if error == .cannotComplete {
            return ToolFailure(
                "ax_outcome_uncertain",
                "Accessibility could not confirm \(operation) before its messaging timeout. The target may already have completed it; reobserve and reconcile target state before any retry."
            )
        }
        return ToolFailure("ax_failed", "\(operation) failed (\(error.rawValue)); reobserve before retry")
    }

    public static func requireMutationSuccess(_ error: AXError, operation: String) throws {
        guard error == .success else { throw mutationFailure(error, operation: operation) }
    }

    public static func app(_ pid: Int32) -> AXUIElement {
        _ = systemWideMessagingTimeoutResult
        let element = AXUIElementCreateApplication(pid)
        AXUIElementSetMessagingTimeout(element, 0.3)
        return element
    }
    public static func value(_ e: AXUIElement, _ name: String) -> CFTypeRef? {
        var result: CFTypeRef?
        guard AXUIElementCopyAttributeValue(e, name as CFString, &result) == .success else { return nil }
        return result
    }
    public static func element(_ raw: CFTypeRef?) -> AXUIElement? {
        guard let raw, CFGetTypeID(raw) == AXUIElementGetTypeID() else { return nil }
        return (raw as! AXUIElement)
    }
    public static func boundedString(_ e: AXUIElement, _ name: String, limit: Int = 4096) -> (value: String, truncated: Bool) {
        guard let raw = value(e, name) as? String else { return ("", false) }
        return boundedString(raw, limit: limit)
    }
    public nonisolated static func boundedString(_ raw: String, limit: Int) -> (value: String, truncated: Bool) {
        let limit = max(0, limit)
        guard raw.utf8.count > limit else { return (raw, false) }
        var bytes = Array(raw.utf8.prefix(limit))
        while !bytes.isEmpty {
            if let value = String(bytes: bytes, encoding: .utf8) { return (value, true) }
            bytes.removeLast()
        }
        return ("", true)
    }
    public static func string(_ e: AXUIElement, _ name: String, limit: Int = 4096) -> String {
        boundedString(e, name, limit: limit).value
    }
    public static func bool(_ e: AXUIElement, _ name: String, default fallback: Bool = false) -> Bool { (value(e, name) as? NSNumber)?.boolValue ?? fallback }
    public static func optionalString(_ e: AXUIElement, _ name: String, limit: Int = 4096) -> String? {
        guard let raw = value(e, name) as? String else { return nil }
        return boundedString(raw, limit: limit).value
    }
    public static func optionalBool(_ e: AXUIElement, _ name: String) -> Bool? {
        guard let raw = value(e, name) as? NSNumber, CFGetTypeID(raw) == CFBooleanGetTypeID() else { return nil }
        return raw.boolValue
    }
    public static func number(_ e: AXUIElement, _ name: String) -> Double? {
        guard let raw = value(e, name) as? NSNumber, CFGetTypeID(raw) != CFBooleanGetTypeID(), raw.doubleValue.isFinite else { return nil }
        return raw.doubleValue
    }
    public static func frame(_ e: AXUIElement) -> Rect? {
        guard let p = value(e, kAXPositionAttribute), let s = value(e, kAXSizeAttribute),
              CFGetTypeID(p) == AXValueGetTypeID(), CFGetTypeID(s) == AXValueGetTypeID() else { return nil }
        var point = CGPoint.zero, size = CGSize.zero
        guard AXValueGetValue(p as! AXValue, .cgPoint, &point), AXValueGetValue(s as! AXValue, .cgSize, &size) else { return nil }
        guard point.x.isFinite, point.y.isFinite, size.width.isFinite, size.height.isFinite else { return nil }
        return Rect(CGRect(origin: point, size: size))
    }
    public static func windows(_ pid: Int32) throws -> [AXUIElement] {
        try ensureMessagingTimeout()
        guard AXIsProcessTrusted() else { throw ToolFailure("accessibility_denied", "Enable Accessibility for this executable or its responsible host in System Settings") }
        var raw: CFTypeRef?
        let error = AXUIElementCopyAttributeValue(app(pid), kAXWindowsAttribute as CFString, &raw)
        guard error == .success, let result = raw as? [AXUIElement] else { throw ToolFailure("ax_unavailable", "AXWindows failed: \(error.rawValue)") }
        return result
    }
    public static func actionSnapshot(_ e: AXUIElement, maxCount: Int = 64, maxNameBytes: Int = 256) -> (names: [String], truncated: Bool) {
        var names: CFArray?; _ = AXUIElementCopyActionNames(e, &names)
        let raw = names as? [String] ?? []
        var truncated = raw.count > maxCount
        let bounded = raw.prefix(maxCount).map {
            let result = boundedString($0, limit: maxNameBytes)
            truncated = truncated || result.truncated
            return result.value
        }
        return (bounded, truncated)
    }
    public static func actions(_ e: AXUIElement) -> [String] {
        actionSnapshot(e).names
    }
    public static func node(_ e: AXUIElement, path: [Int], secureAncestor: Bool = false) -> Node {
        let role = boundedString(e, kAXRoleAttribute, limit: 256)
        let subrole = boundedString(e, kAXSubroleAttribute, limit: 256)
        let title = boundedString(e, kAXTitleAttribute)
        let identifier = boundedString(e, kAXIdentifierAttribute)
        let exposedActions = actionSnapshot(e)
        let secure = secureAncestor || subrole.value == "AXSecureTextField" || role.value == "AXSecureTextField"
        let raw = secure ? nil : value(e, kAXValueAttribute)
        let text: String?
        if let s = raw as? String { text = s }
        else if let n = raw as? NSNumber { text = n.stringValue }
        else { text = nil }
        let boundedValue = text.map { boundedString($0, limit: 4096) }
        return Node(id: path.isEmpty ? "root" : path.map(String.init).joined(separator: "."), path: path,
                    role: role.value, subrole: subrole.value, title: title.value,
                    identifier: identifier.value, value: boundedValue?.value,
                    valueTruncated: boundedValue?.truncated ?? false, enabled: bool(e, kAXEnabledAttribute, default: true),
                    secure: secure, focused: bool(e, kAXFocusedAttribute),
                    description: secure ? nil : optionalString(e, kAXDescriptionAttribute),
                    help: secure ? nil : optionalString(e, kAXHelpAttribute),
                    placeholder: secure ? nil : optionalString(e, kAXPlaceholderValueAttribute),
                    selected: optionalBool(e, kAXSelectedAttribute), expanded: optionalBool(e, kAXExpandedAttribute),
                    minValue: secure ? nil : number(e, kAXMinValueAttribute), maxValue: secure ? nil : number(e, kAXMaxValueAttribute),
                    frame: frame(e), actions: exposedActions.names,
                    identityTruncated: role.truncated || subrole.truncated || title.truncated || identifier.truncated,
                    actionsTruncated: exposedActions.truncated)
    }
    public static func collect(_ root: AXUIElement, maxNodes: Int, maxDepth: Int, timeoutMilliseconds: Int = 5000) -> ([Node], String, [String]) {
        var nodes: [Node] = [], diagnostics: [String] = []
        var visited: [AXUIElement] = []
        let deadline = DispatchTime.now().uptimeNanoseconds + UInt64(max(1, min(5000, timeoutMilliseconds))) * 1_000_000
        func walk(_ e: AXUIElement, _ path: [Int], _ secure: Bool) {
            guard nodes.count < maxNodes, DispatchTime.now().uptimeNanoseconds < deadline, !Task.isCancelled else { diagnostics.append("node_or_time_budget"); return }
            guard !visited.contains(where: { CFEqual($0, e) }) else { diagnostics.append("cycle_or_shared_child"); return }
            visited.append(e)
            let n = node(e, path: path, secureAncestor: secure); nodes.append(n)
            if n.secure { return }
            var count = 0
            let countError = AXUIElementGetAttributeValueCount(e, kAXChildrenAttribute as CFString, &count)
            if countError == .attributeUnsupported || countError == .noValue { return }
            guard countError == .success else { diagnostics.append("children_count:\(countError.rawValue)"); return }
            guard count > 0 else { return }
            guard path.count < maxDepth else { diagnostics.append("depth_budget"); return }
            let limit = min(count, maxNodes - nodes.count)
            guard limit > 0 else { diagnostics.append("node_budget"); return }
            var children: CFArray?
            let error = AXUIElementCopyAttributeValues(e, kAXChildrenAttribute as CFString, 0, limit, &children)
            guard error == .success, let list = children as? [AXUIElement] else { diagnostics.append("children_read:\(error.rawValue)"); return }
            if limit < count { diagnostics.append("child_page_truncated") }
            for (i, child) in list.enumerated() { walk(child, path + [i], n.secure) }
        }
        walk(root, [], false)
        return (nodes, diagnostics.isEmpty ? "collected_window_tree" : "partial", Array(Set(diagnostics)).sorted())
    }
    public static func root(_ observation: Observation) throws -> AXUIElement {
        let list = try windows(observation.pid)
        if observation.windowIdentityBackend == "_AXUIElementGetWindow" {
            // An IME may add utility AX windows that cannot provide a native
            // window ID. Inspect only the already observed geometry and title;
            // still require the exact private ID and a unique match.
            let candidates = list.filter { frame($0) == observation.windowFrame && string($0, kAXTitleAttribute) == observation.windowTitle }
            let matches = try candidates.filter { try PrivateAPI.windowID($0) == observation.windowID }
            guard matches.count == 1, let root = matches.first, frame(root) == observation.windowFrame,
                  string(root, kAXTitleAttribute) == observation.windowTitle else {
                throw ToolFailure("stale_observation", "Private window identity or observed geometry changed")
            }
            return root
        }
        // AXWindows order can change after an input-source switch or sheet
        // closure. Follow only the same unique frame/title; an index is not an
        // identity. Overlapping twins remain ambiguous and are rejected.
        let matches = list.filter { frame($0) == observation.windowFrame }
        guard matches.count == 1, let root = matches.first else { throw ToolFailure("stale_observation", "AX window mapping is no longer unique") }
        guard string(root, kAXTitleAttribute) == observation.windowTitle else { throw ToolFailure("stale_observation", "AX window geometry or title changed") }
        return root
    }
    public static func resolve(_ observation: Observation, nodeID: String, requireEnabled: Bool = true,
                               requireStableValue: Bool = true) throws -> AXUIElement {
        guard let expected = observation.nodes.first(where: { $0.id == nodeID }), !expected.secure else { throw ToolFailure("invalid_node", "Node is absent or secure") }
        guard expected.identityTruncated != true else {
            throw ToolFailure("oversized_ax_identity", "Selected node has a truncated Accessibility identity and cannot be targeted safely")
        }
        if requireStableValue, expected.valueTruncated {
            throw ToolFailure("oversized_ax_value", "Selected node has a truncated Accessibility value and cannot be stale-checked safely")
        }
        var current = try root(observation)
        for depth in 0...expected.path.count {
            let prefix = Array(expected.path.prefix(depth))
            guard let old = observation.nodes.first(where: { $0.path == prefix }),
                  old.identityTruncated != true,
                  node(current, path: prefix).identity == old.identity,
                  !node(current, path: prefix).secure else { throw ToolFailure("stale_observation", "Node or ancestor identity changed") }
            if depth < expected.path.count {
                var raw: CFArray?
                let error = AXUIElementCopyAttributeValues(current, kAXChildrenAttribute as CFString, expected.path[depth], 1, &raw)
                guard error == .success, let children = raw as? [AXUIElement], let child = children.first else { throw ToolFailure("stale_observation", "Node path changed") }
                current = child
            }
        }
        let fresh = node(current, path: expected.path)
        guard fresh.frame == expected.frame,
              !requireStableValue || (fresh.value == expected.value && fresh.valueTruncated == expected.valueTruncated) else {
            throw ToolFailure("stale_observation", "Node value or geometry changed")
        }
        if requireEnabled && !fresh.enabled { throw ToolFailure("disabled_control", "Control is disabled") }
        // A sheet can make underlying controls inert. Require the selected node to be inside it.
        let window = try root(observation)
        let children = value(window, kAXChildrenAttribute) as? [AXUIElement] ?? []
        let focusedWindow = element(value(app(observation.pid), kAXFocusedWindowAttribute))
        let modalFocus = focusedWindow.map { bool($0, kAXModalAttribute) || string($0, kAXRoleAttribute) == "AXSheet" } ?? false
        let hasSheet = children.contains { string($0, kAXRoleAttribute) == "AXSheet" }
        if hasSheet || (modalFocus && focusedWindow.map { !CFEqual($0,window) } == true) {
            let inSheet = (0...expected.path.count).contains { depth in
                observation.nodes.first(where: { $0.path == Array(expected.path.prefix(depth)) })?.role == "AXSheet"
            }
            guard inSheet else { throw ToolFailure("modal_sheet", "Observe and select a node inside the current sheet") }
        }
        return current
    }
    public static func hits(_ observation: Observation, point: CGPoint) -> [Node] {
        observation.nodes.filter { !$0.secure && $0.enabled && $0.frame?.cg.contains(point) == true }
            .sorted { a,b in
                if a.path.count != b.path.count { return a.path.count > b.path.count }
                let ar = a.frame!.cg, br = b.frame!.cg
                return ar.width*ar.height < br.width*br.height
            }
    }
    public static func checkFocused(_ observation: Observation, nodeID: String, requireStableValue: Bool = true) throws -> AXUIElement {
        let selected = try resolve(observation, nodeID: nodeID, requireStableValue: requireStableValue)
        guard let focused = element(value(app(observation.pid), kAXFocusedUIElementAttribute)), CFEqual(selected, focused) else {
            throw ToolFailure("focus_mismatch", "Keyboard target must be the app's currently focused AX node; focus and observe again")
        }
        return selected
    }

    private static func requireMenuTime(_ deadline: Date) throws {
        guard Date() < deadline else {
            throw ToolFailure("menu_traversal_timeout", "Menu traversal exceeded its two-second Accessibility budget")
        }
    }

    private static func boundedChildren(_ e: AXUIElement, limit: Int, deadline: Date) throws -> (elements: [AXUIElement], truncated: Bool) {
        guard (1...128).contains(limit) else { throw ToolFailure("invalid_argument", "Menu traversal limit must be between 1 and 128") }
        try requireMenuTime(deadline)
        var count = 0
        let countError = AXUIElementGetAttributeValueCount(e, kAXChildrenAttribute as CFString, &count)
        if countError == .attributeUnsupported || countError == .noValue { return ([], false) }
        guard countError == .success else { throw ToolFailure("ax_unavailable", "AXChildren count failed: \(countError.rawValue)") }
        guard count > 0 else { return ([], false) }
        let readCount = min(count, limit)
        try requireMenuTime(deadline)
        var raw: CFArray?
        let error = AXUIElementCopyAttributeValues(e, kAXChildrenAttribute as CFString, 0, readCount, &raw)
        guard error == .success, let children = raw as? [AXUIElement] else {
            throw ToolFailure("ax_unavailable", "AXChildren read failed: \(error.rawValue)")
        }
        return (children, readCount < count)
    }

    private static func menuBar(_ pid: Int32) throws -> AXUIElement {
        try ensureMessagingTimeout()
        guard AXIsProcessTrusted() else { throw ToolFailure("accessibility_denied", "Enable Accessibility for this executable or its responsible host in System Settings") }
        guard pid > 0, let result = element(value(app(pid), kAXMenuBarAttribute)) else {
            throw ToolFailure("menu_unavailable", "Application has no accessible menu bar")
        }
        return result
    }

    private static func isMenuItem(_ e: AXUIElement, deadline: Date) throws -> Bool {
        try requireMenuTime(deadline)
        let role = string(e, kAXRoleAttribute)
        return role == kAXMenuBarItemRole || role == kAXMenuItemRole
    }

    private static func menuItems(below parent: AXUIElement, limit: Int, deadline: Date) throws -> [AXUIElement] {
        let direct = try boundedChildren(parent, limit: limit, deadline: deadline)
        guard !direct.truncated else { throw ToolFailure("menu_traversal_limit", "Menu level exceeds the bounded traversal limit") }
        var immediate: [AXUIElement] = []
        for element in direct.elements where try isMenuItem(element, deadline: deadline) {
            immediate.append(element)
        }
        if !immediate.isEmpty { return immediate }

        var result: [AXUIElement] = []
        for container in direct.elements {
            try requireMenuTime(deadline)
            guard string(container, kAXRoleAttribute) == kAXMenuRole else { continue }
            let remaining = limit - result.count
            guard remaining > 0 else { throw ToolFailure("menu_traversal_limit", "Menu level exceeds the bounded traversal limit") }
            let children = try boundedChildren(container, limit: remaining, deadline: deadline)
            guard !children.truncated else { throw ToolFailure("menu_traversal_limit", "Menu level exceeds the bounded traversal limit") }
            for child in children.elements where try isMenuItem(child, deadline: deadline) {
                result.append(child)
            }
        }
        return result
    }

    private static func menuInfo(_ item: AXUIElement, path: [String], deadline: Date) throws -> AXMenuItemInfo {
        try requireMenuTime(deadline)
        let childCount: Int = {
            var count = 0
            return AXUIElementGetAttributeValueCount(item, kAXChildrenAttribute as CFString, &count) == .success ? count : 0
        }()
        try requireMenuTime(deadline); let title = boundedString(item, kAXTitleAttribute)
        try requireMenuTime(deadline); let enabled = bool(item, kAXEnabledAttribute, default: true)
        try requireMenuTime(deadline); let selected = optionalBool(item, kAXSelectedAttribute)
        try requireMenuTime(deadline); let exposedActions = actionSnapshot(item)
        return AXMenuItemInfo(path: path, title: title.value, titleTruncated: title.truncated, enabled: enabled,
                              selected: selected, hasSubmenu: childCount > 0,
                              actions: exposedActions.names, actionsTruncated: exposedActions.truncated)
    }

    public static func topLevelMenuItems(pid: Int32, maxItems: Int = 64) throws -> [AXMenuItemInfo] {
        let deadline = Date().addingTimeInterval(2)
        let items = try menuItems(below: menuBar(pid), limit: maxItems, deadline: deadline)
        return try items.map {
            try requireMenuTime(deadline)
            let title = boundedString($0, kAXTitleAttribute)
            return try menuInfo($0, path: [title.value], deadline: deadline)
        }
    }

    public static func resolveMenuItem(pid: Int32, titlePath: [String], maxItemsPerLevel: Int = 64) throws -> AXUIElement {
        try resolveMenuItem(pid: pid, titlePath: titlePath, maxItemsPerLevel: maxItemsPerLevel,
                            deadline: Date().addingTimeInterval(2))
    }

    private static func resolveMenuItem(pid: Int32, titlePath: [String], maxItemsPerLevel: Int,
                                        deadline: Date) throws -> AXUIElement {
        guard (1...8).contains(titlePath.count),
              titlePath.allSatisfy({ !$0.isEmpty && $0.utf8.count <= 512 }) else {
            throw ToolFailure("invalid_argument", "Menu title path must contain 1 to 8 nonempty titles of at most 512 bytes")
        }
        guard (1...128).contains(maxItemsPerLevel) else {
            throw ToolFailure("invalid_argument", "Menu traversal limit must be between 1 and 128")
        }
        var parent = try menuBar(pid)
        for title in titlePath {
            try requireMenuTime(deadline)
            let items = try menuItems(below: parent, limit: maxItemsPerLevel, deadline: deadline)
            var matches: [AXUIElement] = []
            for item in items {
                try requireMenuTime(deadline)
                if string(item, kAXTitleAttribute) == title { matches.append(item) }
            }
            guard !matches.isEmpty else { throw ToolFailure("menu_item_unavailable", "Menu title path was not found") }
            guard matches.count == 1 else { throw ToolFailure("ambiguous_menu_item", "Menu title is not unique at its level") }
            parent = matches[0]
        }
        return parent
    }

    @discardableResult public static func pressMenuItem(pid: Int32, processStartID: String,
                                                        titlePath: [String], maxItemsPerLevel: Int = 64) throws -> AXMenuItemInfo {
        let deadline = Date().addingTimeInterval(2)
        let item = try resolveMenuItem(pid: pid, titlePath: titlePath, maxItemsPerLevel: maxItemsPerLevel, deadline: deadline)
        try requireMenuTime(deadline)
        guard bool(item, kAXEnabledAttribute, default: true) else { throw ToolFailure("disabled_control", "Menu item is disabled") }
        try requireMenuTime(deadline)
        let exposed = actions(item)
        guard let action = [kAXPressAction, kAXPickAction].first(where: { exposed.contains($0) }) else {
            throw ToolFailure("unsupported_action", "Menu item exposes neither AXPress nor AXPick")
        }
        let info = try menuInfo(item, path: titlePath, deadline: deadline)
        try requireMenuTime(deadline)
        try ProcessIdentity.require(pid: pid, expected: processStartID)
        let error = AXUIElementPerformAction(item, action as CFString)
        try requireMutationSuccess(error, operation: "menu action")
        return info
    }

    public static func set(_ e: AXUIElement, _ name: String, _ raw: CFTypeRef) throws {
        var settable = DarwinBoolean(false)
        let check = AXUIElementIsAttributeSettable(e, name as CFString, &settable)
        guard check == .success, settable.boolValue else { throw ToolFailure("not_settable", "\(name) is not settable (\(check.rawValue))") }
        let error = AXUIElementSetAttributeValue(e, name as CFString, raw)
        try requireMutationSuccess(error, operation: "setting \(name)")
    }
}
