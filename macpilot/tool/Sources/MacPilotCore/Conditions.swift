import AppKit
import ApplicationServices

/// A fresh query is scoped to one process generation and one explicit window.
/// A selector never authorizes a mutation or falls back to another window.
public struct AXSelector: Codable, Equatable {
    public var role: String?
    public var identifier: String?
    public var title: String?
    public init(_ values: [String: Any]) throws {
        let a = Arguments(values)
        try a.only(["role", "identifier", "title"])
        role = try values["role"].map { _ in try a.string("role", limit: 512) }
        identifier = try values["identifier"].map { _ in try a.string("identifier", limit: 512) }
        title = try values["title"].map { _ in try a.string("title", limit: 2048) }
        guard [role, identifier, title].contains(where: { $0?.isEmpty == false }),
              [role, identifier, title].allSatisfy({ $0 == nil || !$0!.isEmpty }) else {
            throw ToolFailure("invalid_argument", "selector needs a nonempty exact role, identifier or title")
        }
    }
    public func matches(_ node: Node) -> Bool {
        (role == nil || node.role == role) && (identifier == nil || node.identifier == identifier)
            && (title == nil || node.title == title)
    }
    public var object: [String: Any] {
        var value: [String: Any] = [:]
        if let role { value["role"] = role }; if let identifier { value["identifier"] = identifier }; if let title { value["title"] = title }
        return value
    }
}

public struct AXCondition: Codable, Equatable {
    public enum Predicate: String, Codable { case exists, absent, enabled, disabled, focused, equals, contains, stable }
    public var selector: AXSelector?
    public var predicate: Predicate
    public var text: String?
    public var stableMs: Int
    public init(_ values: [String: Any]) throws {
        let a = Arguments(values)
        try a.only(["selector", "predicate", "text", "stableMs"])
        if let raw = values["selector"] {
            guard let object = raw as? [String: Any] else { throw ToolFailure("invalid_argument", "selector must be an object") }
            selector = try AXSelector(object)
        }
        guard let predicate = Predicate(rawValue: try a.string("predicate", limit: 32)) else {
            throw ToolFailure("invalid_argument", "Unsupported wait predicate")
        }
        self.predicate = predicate
        text = try values["text"].map { _ in try a.string("text", limit: 65_536) }
        stableMs = try a.integer("stableMs", default: 200, range: 100...2000)
        guard (predicate == .stable || selector != nil),
              ([Predicate.equals, .contains].contains(predicate) ? text != nil : text == nil),
              predicate == .stable || values["stableMs"] == nil else {
            throw ToolFailure("invalid_argument", "Text predicates need text; only stable may omit selector or specify stableMs")
        }
    }
    public var object: [String: Any] {
        var result: [String: Any] = ["predicate": predicate.rawValue]
        if let selector { result["selector"] = selector.object }; if let text { result["text"] = text }
        if predicate == .stable { result["stableMs"] = stableMs }; return result
    }
    public func selected(in observation: Observation) throws -> Node? {
        guard observation.coverage == "collected_window_tree", observation.diagnostics.isEmpty else {
            throw ToolFailure("partial_coverage", "A partial AX tree cannot prove target absence or selector uniqueness")
        }
        guard !observation.nodes.contains(where: { $0.identityTruncated == true }) else {
            throw ToolFailure("partial_identity", "A truncated AX identity cannot prove selector uniqueness")
        }
        guard let selector else { return nil }
        let matches = observation.nodes.filter(selector.matches)
        guard matches.count <= 1 else { throw ToolFailure("ambiguous_target", "The exact selector matches more than one node") }
        if let node = matches.first, node.secure { throw ToolFailure("secure_node", "Conditions do not read secure AX nodes") }
        return matches.first
    }
    public func evaluate(_ observation: Observation) throws -> Bool {
        let node = try selected(in: observation)
        switch predicate {
        case .exists: return node != nil
        case .absent: return node == nil
        case .enabled: return node?.enabled == true
        case .disabled: return node?.enabled == false
        case .focused: return node?.focused == true
        case .equals, .contains:
            guard let node else { return false }
            guard !node.valueTruncated else { throw ToolFailure("oversized_ax_value", "A truncated value cannot verify a text predicate") }
            guard let value = node.value else { return false }
            return predicate == .equals ? value == text! : value.contains(text!)
        case .stable: return selector == nil || node?.frame != nil
        }
    }
}

final class AXConditionObserver {
    private var observer: AXObserver?
    private var registrations: [(AXUIElement, String)] = []
    private(set) var changes = 0
    @MainActor init(pid: Int32, window: AXUIElement) {
        var candidate: AXObserver?
        let callback: AXObserverCallback = { _, _, _, raw in
            guard let raw else { return }
            Unmanaged<AXConditionObserver>.fromOpaque(raw).takeUnretainedValue().changes += 1
        }
        guard AXObserverCreate(pid, callback, &candidate) == .success, let candidate else { return }
        observer = candidate
        for target in [AX.app(pid), window] {
            for name in [kAXLayoutChangedNotification, kAXValueChangedNotification, kAXFocusedUIElementChangedNotification,
                         kAXMovedNotification, kAXResizedNotification, kAXUIElementDestroyedNotification] {
                if AXObserverAddNotification(candidate, target, name as CFString, Unmanaged.passUnretained(self).toOpaque()) == .success {
                    registrations.append((target, name))
                }
            }
        }
        CFRunLoopAddSource(CFRunLoopGetMain(), AXObserverGetRunLoopSource(candidate), .commonModes)
    }
    deinit {
        if let observer {
            CFRunLoopRemoveSource(CFRunLoopGetMain(), AXObserverGetRunLoopSource(observer), .commonModes)
            for (target, name) in registrations { AXObserverRemoveNotification(observer, target, name as CFString) }
        }
    }
}

@MainActor public enum Conditions {
    public static func call(_ a: Arguments, engine: Engine) async throws -> [String: Any] {
        try a.only(["pid", "processStartID", "windowID", "condition", "timeoutMs", "pollMs", "maxNodes", "maxDepth", "privateAPI"])
        let pid = Int32(try a.integer("pid", range: 1...Int(Int32.max)))
        let identity = try a.string("processStartID", limit: 64)
        let windowID = UInt32(try a.integer("windowID", range: 1...Int(UInt32.max)))
        guard let raw = a.values["condition"] as? [String: Any] else { throw ToolFailure("invalid_argument", "condition must be an object") }
        let condition = try AXCondition(raw)
        let timeout = try a.integer("timeoutMs", default: 5000, range: 50...30_000)
        let poll = try a.integer("pollMs", default: 100, range: 50...1000)
        let maxNodes = try a.integer("maxNodes", default: 500, range: 1...1000)
        let maxDepth = try a.integer("maxDepth", default: 20, range: 1...30)
        let privateAPI = try a.bool("privateAPI")
        return try await wait(condition, pid: pid, identity: identity, windowID: windowID, timeoutMs: timeout,
                              pollMs: poll, maxNodes: maxNodes, maxDepth: maxDepth, privateAPI: privateAPI, engine: engine)
    }
    static func wait(_ condition: AXCondition, pid: Int32, identity: String, windowID: UInt32, timeoutMs: Int,
                     pollMs: Int = 100, maxNodes: Int = 500, maxDepth: Int = 20, privateAPI: Bool = false,
                     engine: Engine, checkState:() throws -> Void = {}) async throws -> [String: Any] {
        let started = DispatchTime.now().uptimeNanoseconds
        let deadline = started + UInt64(timeoutMs) * 1_000_000
        var observer: AXConditionObserver?, latest: Observation?, previousFrame: Rect?, stableSince: UInt64?
        var attempts = 0, wakes = 0, lastGeometryError: String?
        repeat {
            try Task.checkCancellation(); try checkState(); try ProcessIdentity.require(pid: pid, expected: identity)
            attempts += 1
            do {
                let beforeRead = DispatchTime.now().uptimeNanoseconds
                if beforeRead >= deadline { break }
                let observation = try await engine.observe(pid: pid, processStartID: identity, windowID: windowID, screenshot: false,
                                                           maxNodes: maxNodes, maxDepth: maxDepth, privateAPI: privateAPI,
                                                           collectionTimeoutMilliseconds: max(1, Int((deadline - beforeRead) / 1_000_000)))
                if let previous = latest { try? engine.store.remove(previous.id + ".json") }
                latest = observation
                if observer == nil { observer = AXConditionObserver(pid: pid, window: try AX.root(observation)) }
                var matched = try condition.evaluate(observation)
                let now = DispatchTime.now().uptimeNanoseconds
                if condition.predicate == .stable {
                    let frame = try condition.selected(in: observation)?.frame ?? (condition.selector == nil ? observation.windowFrame : nil)
                    if !matched || frame == nil { stableSince = nil; previousFrame = nil; matched = false }
                    else {
                        if previousFrame != frame { previousFrame = frame; stableSince = now }
                        if stableSince == nil { stableSince = now }
                        matched = now - stableSince! >= UInt64(condition.stableMs) * 1_000_000
                    }
                }
                if matched, now <= deadline {
                    return ["status": "predicate_verified", "matches": true, "attempts": attempts, "notificationWakes": wakes,
                            "elapsedMilliseconds": Int((now - started) / 1_000_000), "observation": observation.object,
                            "scope": "Exactly the declared condition in the selected process generation and window"]
                }
                lastGeometryError = nil
            } catch let failure as ToolFailure where ["stale_observation", "ambiguous_ax_window", "app_metadata_unavailable"].contains(failure.code) {
                // Read again in the same explicit window while it moves. Never repeat an action.
                lastGeometryError = failure.code; stableSince = nil; previousFrame = nil
            }
            if DispatchTime.now().uptimeNanoseconds >= deadline { break }
            let seen = observer?.changes ?? 0
            let until = min(deadline, DispatchTime.now().uptimeNanoseconds + UInt64(pollMs) * 1_000_000)
            while DispatchTime.now().uptimeNanoseconds < until {
                try Task.checkCancellation(); try checkState(); try await Task.sleep(nanoseconds: 10_000_000)
                if (observer?.changes ?? 0) != seen { wakes += 1; break }
            }
        } while DispatchTime.now().uptimeNanoseconds < deadline
        var result: [String: Any] = ["status": "predicate_timeout", "matches": false, "attempts": attempts,
                                    "notificationWakes": wakes, "elapsedMilliseconds": Int((DispatchTime.now().uptimeNanoseconds - started) / 1_000_000),
                                    "scope": "Only the declared condition; no mutation was sent"]
        if let latest { result["observation"] = latest.object }; if let lastGeometryError { result["lastGeometryError"] = lastGeometryError }
        return result
    }
}
