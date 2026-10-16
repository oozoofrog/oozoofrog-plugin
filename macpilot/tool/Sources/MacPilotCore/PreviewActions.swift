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
        let sequence = UUID().uuidString.lowercased()
        if operation == "start" {
            guard let observation else { throw ToolFailure("invalid_argument", "start requires a fresh observation") }
            if let current = status(store), isRunning(current) { return current }
            if let old=status(store),old["status"] as? String=="stopped",let pid=old["pid"] as? Int32,let identity=old["processStartID"] as? String {
                let deadline=Date().addingTimeInterval(2.5)
                while ProcessIdentity.startID(pid:pid)==identity,Date()<deadline {try await Task.sleep(nanoseconds:50_000_000)}
                guard ProcessIdentity.startID(pid:pid) != identity else{throw ToolFailure("preview_stopping","Previous preview is still stopping; inspect status")}
            }
            try store.remove("preview-command.json")
            guard let executable = Bundle.main.executableURL else { throw ToolFailure("preview_failed", "Cannot locate this MacPilot executable") }
            let process = Process()
            process.executableURL = executable
            process.arguments = ["preview-host", store.root.path, observation.id, sequence]
            process.standardInput = FileHandle.nullDevice
            process.standardOutput = FileHandle.nullDevice
            process.standardError = FileHandle.nullDevice
            try process.run()
        } else {
            guard ["hide","show","pause","resume","stop","overlay"].contains(operation) else {
                throw ToolFailure("invalid_argument", "Unsupported preview operation")
            }
            guard let current = status(store), isRunning(current) else { throw ToolFailure("preview_not_running", "Start this task's preview first") }
            let command: [String: Any] = ["operation":operation, "sequence":sequence, "enabled":try a.bool("enabled", default: true)]
            try store.write(jsonData(command), to: store.root.appendingPathComponent("preview-command.json"))
        }
        let deadline = Date().addingTimeInterval(Double(timeout) / 1000)
        while Date() < deadline {
            try Task.checkCancellation()
            if let current = status(store), current["sequence"] as? String == sequence {
                if current["status"] as? String == "failed" { throw ToolFailure("preview_failed", current["error"] as? String ?? "Live preview failed") }
                if operation != "start" || (current["frameCount"] as? Int ?? 0) > 0 { return current }
            }
            try await Task.sleep(nanoseconds: 50_000_000)
        }
        throw ToolFailure("preview_timeout", "Preview command was submitted but its acknowledgement was not observed; inspect status before retrying")
    }
}

/// Desktop feedback has its own process and lifetime; hiding the preview does not hide cursors.
@MainActor public enum DesktopOverlayActions {
    public static func status(_ store:Store) -> [String:Any] {
        guard let data=try? store.read("overlay-status.json"),
              var result=try? JSONSerialization.jsonObject(with:data) as? [String:Any],
              let pid=result["pid"] as? Int32,let identity=result["processStartID"] as? String,
              ProcessIdentity.startID(pid:pid)==identity else { return ["status":"not_started","overlayCount":0,"highlightVisible":false] }
        result["running"]=result["status"] as? String != "stopped";return result
    }
    public static func ensure(_ store:Store,observation:Observation) async throws -> [String:Any] {
        let targetSequence=UUID().uuidString.lowercased()
        try store.write(jsonData(["observation":observation.id,"activityAt":Date().timeIntervalSince1970,"targetSequence":targetSequence]),to:store.root.appendingPathComponent("overlay-target.json"))
        if status(store)["running"] as? Bool != true {
            guard let executable=Bundle.main.executableURL else{throw ToolFailure("overlay_failed","Cannot locate MacPilot")}
            let process=Process();process.executableURL=executable;process.arguments=["overlay-host",store.root.path]
            process.standardInput=FileHandle.nullDevice;process.standardOutput=FileHandle.nullDevice;process.standardError=FileHandle.nullDevice
            try process.run()
        }
        let deadline=Date().addingTimeInterval(2)
        repeat {
            try Task.checkCancellation()
            let result=status(store)
            if result["running"] as? Bool == true,result["observation"] as? String==observation.id,result["targetSequence"] as? String==targetSequence { return result }
            try await Task.sleep(nanoseconds:40_000_000)
        } while Date()<deadline
        throw ToolFailure("overlay_timeout","Desktop overlay did not acknowledge the target; inspect overlay status before restarting")
    }
    public static func control(_ store:Store,enabled:Bool) async throws -> [String:Any] {
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
}
