import AppKit
import ApplicationServices

public struct WindowState: Codable, Equatable {
    public var exists: Bool
    public var title: String?
    public var frame: Rect?
    public var minimized: Bool?
    public var focused: Bool
    public var main: Bool?
    public var actions: [String]

    public init(exists: Bool, title: String? = nil, frame: Rect? = nil, minimized: Bool? = nil,
                focused: Bool = false, main: Bool? = nil, actions: [String] = []) {
        self.exists = exists
        self.title = title
        self.frame = frame
        self.minimized = minimized
        self.focused = focused
        self.main = main
        self.actions = actions
    }
}

public struct WindowActionResult: Codable, Equatable {
    public var status: String
    public var state: WindowState
    public var verification: String

    public init(status: String, state: WindowState, verification: String) {
        self.status = status
        self.state = state
        self.verification = verification
    }
}

@MainActor public enum WindowActions {
    private static func observedWindow(_ observation: Observation) throws -> AXUIElement {
        try Geometry.validateAge(observation)
        try ProcessIdentity.require(pid: observation.pid, expected: observation.processStartID)
        return try AX.root(observation)
    }

    private static func liveState(observation: Observation, window: AXUIElement) throws -> WindowState {
        guard let currentIdentity = ProcessIdentity.startID(pid: observation.pid) else {
            return WindowState(exists: false)
        }
        guard currentIdentity == observation.processStartID else {
            throw ToolFailure("stale_app_identity", "PID was reused while verifying the window operation")
        }
        let windows: [AXUIElement]
        do {
            windows = try AX.windows(observation.pid)
        } catch {
            if ProcessIdentity.startID(pid: observation.pid) == nil { return WindowState(exists: false) }
            throw error
        }
        guard windows.contains(where: { CFEqual($0, window) }) else { return WindowState(exists: false) }
        let focusedWindow = AX.element(AX.value(AX.app(observation.pid), kAXFocusedWindowAttribute))
        return WindowState(exists: true, title: AX.optionalString(window, kAXTitleAttribute), frame: AX.frame(window),
                           minimized: AX.optionalBool(window, kAXMinimizedAttribute),
                           focused: focusedWindow.map { CFEqual($0, window) } ?? false,
                           main: AX.optionalBool(window, kAXMainAttribute), actions: AX.actions(window))
    }

    private static func waitFor(observation: Observation, window: AXUIElement, timeout: TimeInterval = 1.5,
                                until predicate: (WindowState) -> Bool) async throws -> WindowState {
        let deadline = Date().addingTimeInterval(timeout)
        var latest = try liveState(observation: observation, window: window)
        while !predicate(latest), Date() < deadline {
            try await Task.sleep(nanoseconds: 50_000_000)
            latest = try liveState(observation: observation, window: window)
        }
        return latest
    }

    private static func perform(_ action: String, on window: AXUIElement) throws {
        guard AX.actions(window).contains(action) else { throw ToolFailure("unsupported_action", "Window does not expose \(action)") }
        let error = AXUIElementPerformAction(window, action as CFString)
        try AX.requireMutationSuccess(error, operation: "window \(action)")
    }

    private static func pointValue(_ point: CGPoint) throws -> AXValue {
        guard point.x.isFinite, point.y.isFinite, abs(point.x) <= 1e7, abs(point.y) <= 1e7 else {
            throw ToolFailure("invalid_argument", "Window position must contain finite bounded coordinates")
        }
        var point = point
        guard let result = AXValueCreate(.cgPoint, &point) else { throw ToolFailure("ax_failed", "Cannot create AX window position") }
        return result
    }

    private static func sizeValue(_ size: CGSize) throws -> AXValue {
        guard size.width.isFinite, size.height.isFinite, size.width > 0, size.height > 0,
              size.width <= 1e7, size.height <= 1e7 else {
            throw ToolFailure("invalid_argument", "Window size must contain finite positive bounded dimensions")
        }
        var size = size
        guard let result = AXValueCreate(.cgSize, &size) else { throw ToolFailure("ax_failed", "Cannot create AX window size") }
        return result
    }

    public static func state(_ observation: Observation) throws -> WindowState {
        let window = try observedWindow(observation)
        return try liveState(observation: observation, window: window)
    }

    public static func focus(_ observation: Observation, node: AXUIElement?, timeoutMilliseconds: Int) async throws -> [String: Any] {
        let window = try observedWindow(observation)
        guard let application = NSRunningApplication(processIdentifier: observation.pid) else {
            throw ToolFailure("app_unavailable", "Target application exited")
        }
        if AX.bool(window, kAXMinimizedAttribute) { try AX.set(window, kAXMinimizedAttribute, kCFBooleanFalse) }
        application.unhide()
        var settable = DarwinBoolean(false)
        if AXUIElementIsAttributeSettable(window, kAXMainAttribute as CFString, &settable) == .success, settable.boolValue {
            try AX.set(window, kAXMainAttribute, kCFBooleanTrue)
        }
        _ = application.activate(options: [])
        try perform(kAXRaiseAction, on: window)
        let app = AX.app(observation.pid)
        if AXUIElementIsAttributeSettable(app, kAXFocusedWindowAttribute as CFString, &settable) == .success, settable.boolValue {
            try AX.set(app, kAXFocusedWindowAttribute, window)
        }
        if let node { try AX.set(node, kAXFocusedAttribute, kCFBooleanTrue) }
        let deadline = Date().addingTimeInterval(Double(timeoutMilliseconds) / 1000)
        var state = try liveState(observation: observation, window: window)
        var foreground = false, nodeFocused = node == nil
        repeat {
            try Task.checkCancellation()
            try ProcessIdentity.require(pid: observation.pid, expected: observation.processStartID)
            state = try liveState(observation: observation, window: window)
            foreground = NSWorkspace.shared.frontmostApplication?.processIdentifier == observation.pid
            if let node { nodeFocused = AX.element(AX.value(app, kAXFocusedUIElementAttribute)).map { CFEqual($0, node) } ?? false }
            if foreground && state.focused && nodeFocused { break }
            try await Task.sleep(nanoseconds: 50_000_000)
        } while Date() < deadline
        return ["status":foreground && state.focused && nodeFocused ? "focus_verified" : "focus_unverified",
                "foregroundVerified":foreground, "windowVerified":state.focused, "nodeVerified":nodeFocused,
                "pid":observation.pid, "windowID":observation.windowID,
                "verification":"Foreground PID, selected AX window and optional focused element were reread; reobserve before input"]
    }

    @discardableResult public static func raise(_ observation: Observation) async throws -> WindowState {
        let window = try observedWindow(observation)
        try ProcessIdentity.require(pid: observation.pid, expected: observation.processStartID)
        try perform(kAXRaiseAction, on: window)
        try await Task.sleep(nanoseconds: 50_000_000)
        return try liveState(observation: observation, window: window)
    }

    @discardableResult public static func close(_ observation: Observation) async throws -> WindowState {
        let window = try observedWindow(observation)
        guard let button = AX.element(AX.value(window, kAXCloseButtonAttribute)),
              AX.bool(button, kAXEnabledAttribute, default: true) else {
            throw ToolFailure("unsupported_action", "Window has no enabled close button")
        }
        let exposed = AX.actions(button)
        guard exposed.contains(kAXPressAction) else { throw ToolFailure("unsupported_action", "Window close button does not expose AXPress") }
        try ProcessIdentity.require(pid: observation.pid, expected: observation.processStartID)
        let error = AXUIElementPerformAction(button, kAXPressAction as CFString)
        try AX.requireMutationSuccess(error, operation: "window close")
        return try await waitFor(observation: observation, window: window, until: { !$0.exists })
    }

    @discardableResult public static func setMinimized(_ minimized: Bool, observation: Observation) async throws -> WindowState {
        let window = try observedWindow(observation)
        try ProcessIdentity.require(pid: observation.pid, expected: observation.processStartID)
        try AX.set(window, kAXMinimizedAttribute, (minimized ? kCFBooleanTrue : kCFBooleanFalse))
        return try await waitFor(observation: observation, window: window, until: { $0.minimized == minimized })
    }

    @discardableResult public static func minimize(_ observation: Observation) async throws -> WindowState {
        try await setMinimized(true, observation: observation)
    }

    @discardableResult public static func unminimize(_ observation: Observation) async throws -> WindowState {
        try await setMinimized(false, observation: observation)
    }

    @discardableResult public static func toggleFullScreen(_ observation: Observation) async throws -> WindowActionResult {
        let window = try observedWindow(observation)
        guard let button = AX.element(AX.value(window, kAXFullScreenButtonAttribute)),
              AX.bool(button, kAXEnabledAttribute, default: true) else {
            throw ToolFailure("unsupported_action", "Window has no enabled full-screen button")
        }
        guard AX.actions(button).contains(kAXPressAction) else {
            throw ToolFailure("unsupported_action", "Window full-screen button does not expose AXPress")
        }
        try ProcessIdentity.require(pid: observation.pid, expected: observation.processStartID)
        let error = AXUIElementPerformAction(button, kAXPressAction as CFString)
        try AX.requireMutationSuccess(error, operation: "window full-screen toggle")
        try await Task.sleep(nanoseconds: 100_000_000)
        let state = try liveState(observation: observation, window: window)
        return WindowActionResult(status: "requested_unverified", state: state,
                                  verification: "Public AX exposes a toggle button but no full-screen state attribute; reobserve the requested result")
    }

    @discardableResult public static func move(_ observation: Observation, to origin: CGPoint) async throws -> WindowState {
        let window = try observedWindow(observation)
        try ProcessIdentity.require(pid: observation.pid, expected: observation.processStartID)
        try AX.set(window, kAXPositionAttribute, try pointValue(origin))
        return try await waitFor(observation: observation, window: window, until: {
            guard let frame = $0.frame else { return false }
            return abs(frame.x - origin.x) <= 0.5 && abs(frame.y - origin.y) <= 0.5
        })
    }

    @discardableResult public static func resize(_ observation: Observation, to size: CGSize) async throws -> WindowState {
        let window = try observedWindow(observation)
        try ProcessIdentity.require(pid: observation.pid, expected: observation.processStartID)
        try AX.set(window, kAXSizeAttribute, try sizeValue(size))
        return try await waitFor(observation: observation, window: window, until: {
            guard let frame = $0.frame else { return false }
            return abs(frame.width - size.width) <= 0.5 && abs(frame.height - size.height) <= 0.5
        })
    }
}
