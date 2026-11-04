import AppKit

@MainActor public enum PreviewActions {
    public static func status(_ store: Store) -> [String: Any]? {
        guard let data = try? store.read("preview-status.json"),
              let status = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else { return nil }
        var merged=status
        let overlay=DesktopOverlayActions.status(store)
        for key in ["overlayCount","overlayEnabled","highlightVisible"] { merged[key]=overlay[key] ?? (key == "overlayCount" ? 0 : false) }
        return merged
    }
    private static func isRunning(_ state: [String: Any]) -> Bool {
        guard let pid = state["pid"] as? Int32, let identity = state["processStartID"] as? String,
              ProcessIdentity.startID(pid: pid) == identity else { return false }
        return state["status"] as? String != "stopped"
    }
    private static func canReuse(_ value: [String: Any], observation: Observation) -> Bool {
        value["status"] as? String == "running" && (value["frameCount"] as? Int ?? 0) > 0
            && value["targetPID"] as? Int32 == observation.pid
            && value["targetStartID"] as? String == observation.processStartID
            && value["windowID"] as? UInt32 == observation.windowID
    }
    static func stopBeforeReplacement(_ current: [String: Any], store: Store, deadline: Date) async throws {
        guard let pid = current["pid"] as? Int32, let identity = current["processStartID"] as? String,
              ProcessIdentity.startID(pid: pid) == identity else { return }
        let alreadyStopped = current["status"] as? String == "stopped"
        let sequence = alreadyStopped ? (current["sequence"] as? String ?? "") : UUID().uuidString.lowercased()
        if !alreadyStopped {
            try store.write(jsonData(["operation": "stop", "sequence": sequence, "hostPID": pid, "hostStartID": identity]),
                to: store.root.appendingPathComponent("preview-command.json"))
        }
        var hidden = false
        while Date() < deadline {
            try Task.checkCancellation()
            if let value = status(store), value["pid"] as? Int32 == pid,
               value["processStartID"] as? String == identity,
               value["status"] as? String == "stopped", value["visible"] as? Bool == false,
               let receiptSequence = value["sequence"] as? String, !receiptSequence.isEmpty {
                // A native stop or target/task loss can become terminal between
                // our read and command. That exact generation cannot process a
                // fresh sequence once stopped; its terminal receipt plus actual
                // exit is sufficient. A running receipt still cannot qualify.
                hidden = true
            }
            if ProcessIdentity.startID(pid: pid) != identity {
                guard hidden else { throw ToolFailure("preview_stop_unconfirmed", "Previous preview exited without a matching hidden acknowledgement; no replacement was started") }
                return
            }
            try await Task.sleep(nanoseconds: 25_000_000)
        }
        throw ToolFailure("preview_stopping", "Previous preview did not acknowledge stop and exit before timeout; no replacement was started")
    }
    public static func call(_ a: Arguments, store: Store, observation: Observation?) async throws -> [String: Any] {
        try a.only(["operation", "observation", "enabled", "timeoutMs"])
        let operation = try a.string("operation")
        let timeout = try a.integer("timeoutMs", default: 10_000, range: 100...20_000)
        if operation == "overlay" { return try await DesktopOverlayActions.control(store,enabled:a.bool("enabled",default:true)) }
        if operation == "status" {
            var result = status(store) ?? ["status":"not_started"]
            result["running"] = isRunning(result)
            return result
        }
        guard ["start", "hide", "show", "pause", "resume", "stop"].contains(operation) else {
            throw ToolFailure("invalid_argument", "Unsupported preview operation")
        }
        let lease = try store.lease(".preview-control.lock")
        defer { withExtendedLifetime(lease) {} }
        let deadline = Date().addingTimeInterval(Double(timeout) / 1000)
        let sequence = UUID().uuidString.lowercased()
        var launched: Process?
        var expectedHost: (pid: Int32, identity: String)?
        if operation == "start" {
            guard let observation else { throw ToolFailure("invalid_argument", "start requires a fresh observation") }
            if let current = status(store) {
                if isRunning(current), canReuse(current, observation: observation) { return current }
                try await stopBeforeReplacement(current, store: store, deadline: deadline)
            }
            try Task.checkCancellation()
            guard Date() < deadline else { throw ToolFailure("preview_timeout", "Preview replacement exhausted its deadline before launch") }
            try store.remove("preview-command.json")
            guard let executable = Bundle.main.executableURL else { throw ToolFailure("preview_failed", "Cannot locate this MacPilot executable") }
            let process = Process(); process.executableURL = executable
            process.arguments = ["preview-host", store.root.path, observation.id, sequence]
            process.standardInput = FileHandle.nullDevice; process.standardOutput = FileHandle.nullDevice; process.standardError = FileHandle.nullDevice
            try process.run(); launched = process
            guard let identity = ProcessIdentity.startID(pid: process.processIdentifier) else {
                throw ToolFailure("preview_failed", "Cannot identify the newly launched preview host")
            }
            expectedHost = (process.processIdentifier, identity)
        } else {
            guard let current = status(store), isRunning(current), let pid = current["pid"] as? Int32,
                  let identity = current["processStartID"] as? String else {
                throw ToolFailure("preview_not_running", "Start this task's preview first")
            }
            expectedHost = (pid, identity)
            try store.write(jsonData(["operation": operation, "sequence": sequence, "enabled": try a.bool("enabled", default: true),
                "hostPID": pid, "hostStartID": identity]), to: store.root.appendingPathComponent("preview-command.json"))
        }
        while Date() < deadline {
            try Task.checkCancellation()
            if let current = status(store), let expectedHost,
               current["pid"] as? Int32 == expectedHost.pid, current["processStartID"] as? String == expectedHost.identity,
               current["sequence"] as? String == sequence {
                if current["status"] as? String == "failed" { throw ToolFailure("preview_failed", current["error"] as? String ?? "Live preview failed") }
                if operation != "start" { return current }
                if let observation, current["launchSequence"] as? String == sequence,
                   canReuse(current, observation: observation), isRunning(current) { return current }
            }
            if let launched, !launched.isRunning { throw ToolFailure("preview_failed", "The new preview host exited before its target's first frame") }
            try await Task.sleep(nanoseconds: 25_000_000)
        }
        throw ToolFailure("preview_timeout", "Preview command was submitted but its matching target acknowledgement was not observed; inspect status before retrying")
    }

}

/// Desktop feedback has its own process and lifetime; hiding the preview does not hide cursors.
@MainActor public enum DesktopOverlayActions {
    private static func recordedStatus(_ store: Store) -> [String: Any]? {
        guard let data = try? store.read("overlay-status.json") else { return nil }
        return try? JSONSerialization.jsonObject(with: data) as? [String: Any]
    }
    public static func status(_ store:Store) -> [String:Any] {
        guard let data=try? store.read("overlay-status.json"),
              var result=try? JSONSerialization.jsonObject(with:data) as? [String:Any],
              let pid=result["pid"] as? Int32,let identity=result["processStartID"] as? String,
              ProcessIdentity.startID(pid:pid)==identity else { return ["status":"not_started","overlayCount":0,"highlightVisible":false] }
        result["running"]=result["status"] as? String != "stopped";return result
    }
    private static func waitForStoppedHost(_ store: Store) async throws {
        guard let value = recordedStatus(store), value["status"] as? String == "stopped",
              let pid = value["pid"] as? Int32, let identity = value["processStartID"] as? String else { return }
        let deadline = Date().addingTimeInterval(3)
        while ProcessIdentity.startID(pid: pid) == identity, Date() < deadline {
            try Task.checkCancellation()
            try await Task.sleep(nanoseconds: 40_000_000)
        }
        guard ProcessIdentity.startID(pid: pid) != identity else {
            throw ToolFailure("overlay_stopping", "The previous desktop feedback host is still stopping; no replacement was launched")
        }
    }
    public static func ensure(_ store: Store, observation: Observation,
                              transport: InvocationTransport = .cli) async throws -> [String: Any] {
        let lease = try store.lease(".overlay-control.lock")
        defer { withExtendedLifetime(lease) {} }
        try await waitForStoppedHost(store)
        let targetSequence = UUID().uuidString.lowercased()
        let ownerStartID = ProcessIdentity.startID(pid: getpid())
        if transport == .mcpStdio, ownerStartID == nil { throw ToolFailure("overlay_failed", "Cannot identify the owning MCP process") }
        let target = OverlayTarget(observation: observation.id, activityAt: Date().timeIntervalSince1970,
            targetSequence: targetSequence, ownerPID: getpid(), ownerStartID: ownerStartID, ownerTransport: transport.rawValue)
        try store.write(JSONEncoder().encode(target), to: store.root.appendingPathComponent("overlay-target.json"))
        var launched: Process?
        let deadline = Date().addingTimeInterval(3)
        while Date() < deadline {
            try Task.checkCancellation()
            let result = status(store)
            if result["running"] as? Bool == true, result["observation"] as? String == observation.id,
               result["targetSequence"] as? String == targetSequence { return result }
            if result["running"] as? Bool != true, launched == nil {
                try await waitForStoppedHost(store)
                guard let executable = Bundle.main.executableURL else { throw ToolFailure("overlay_failed", "Cannot locate MacPilot") }
                let process = Process(); process.executableURL = executable; process.arguments = ["overlay-host", store.root.path]
                process.standardInput = FileHandle.nullDevice; process.standardOutput = FileHandle.nullDevice; process.standardError = FileHandle.nullDevice
                try process.run(); launched = process
            }
            if let launched, !launched.isRunning { throw ToolFailure("overlay_failed", "The new desktop feedback host exited before acknowledging its target") }
            try await Task.sleep(nanoseconds: 40_000_000)
        }
        throw ToolFailure("overlay_timeout", "Desktop overlay did not acknowledge the target; inspect overlay status before restarting")
    }
    public static func control(_ store:Store,enabled:Bool) async throws -> [String:Any] {
        let lease = try store.lease(".overlay-control.lock"); defer { withExtendedLifetime(lease) {} }
        let sequence=UUID().uuidString.lowercased()
        try store.write(jsonData(["enabled":enabled,"sequence":sequence]),to:store.root.appendingPathComponent("overlay-command.json"))
        let deadline=Date().addingTimeInterval(2)
        repeat {
            try Task.checkCancellation()
            let result=status(store)
            if result["sequence"] as? String==sequence{return result}
            if result["running"] as? Bool != true{return result}
            try await Task.sleep(nanoseconds:40_000_000)
        } while Date()<deadline
        throw ToolFailure("overlay_timeout","Desktop overlay control is unconfirmed")
    }
    /// Cleanup needs neither a fresh observation nor an active task. It only
    /// targets this state's recorded process generation and never signals it.
    public static func stop(_ store: Store) async throws -> [String: Any] {
        let lease = try store.lease(".overlay-control.lock")
        defer { withExtendedLifetime(lease) {} }
        guard let current = recordedStatus(store), let pid = current["pid"] as? Int32,
              let identity = current["processStartID"] as? String,
              ProcessIdentity.startID(pid: pid) == identity else {
            return ["status": "overlay_not_running", "running": false, "overlayCount": 0, "highlightVisible": false]
        }
        let sequence = UUID().uuidString.lowercased()
        try store.write(jsonData(["operation": "stop", "sequence": sequence, "hostPID": pid, "hostStartID": identity]),
            to: store.root.appendingPathComponent("overlay-command.json"))
        let deadline = Date().addingTimeInterval(3)
        var hidden = false
        while Date() < deadline {
            try Task.checkCancellation()
            if let value = recordedStatus(store), value["pid"] as? Int32 == pid,
               value["processStartID"] as? String == identity,
               value["status"] as? String == "stopped",
               value["overlayCount"] as? Int == 0, value["highlightVisible"] as? Bool == false,
               value["sequence"] as? String == sequence || current["status"] as? String == "stopped" {
                hidden = true
            }
            if ProcessIdentity.startID(pid: pid) != identity {
                guard hidden else { throw ToolFailure("overlay_stop_unconfirmed", "The recorded overlay process exited without a matching hidden acknowledgement") }
                return ["status": "overlay_stopped", "running": false, "overlayCount": 0, "highlightVisible": false,
                        "pid": pid, "processStartID": identity, "sequence": sequence, "processExited": true]
            }
            try await Task.sleep(nanoseconds: 40_000_000)
        }
        throw ToolFailure("overlay_stop_timeout", "Desktop feedback stop was submitted, but hidden acknowledgement and process exit were not both confirmed")
    }
}
