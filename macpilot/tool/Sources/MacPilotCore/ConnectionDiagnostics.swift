import AppKit
import ApplicationServices
import Darwin

public enum MacPilotRuntime {
    public static let version = "3.5.1"
    public static let instanceID = UUID().uuidString.lowercased()
}

public enum InvocationTransport: String {
    case cli
    case mcpStdio = "mcp_stdio"
}

/// Process-level diagnostics deliberately do not acquire a task/input lease or
/// signal an existing server. A healthy probe cannot repair its caller's pipe.
@MainActor public enum ConnectionDiagnostics {
    static func identity(_ pid: Int32) -> [String: Any] {
        var result: [String: Any] = ["pid": pid]
        if let start = ProcessIdentity.startID(pid: pid) { result["processStartID"] = start }
        return result
    }

    static func baseline(_ a: Arguments, prefix: String) throws -> (Int32, String)? {
        let pidKey = "previous\(prefix)PID", startKey = "previous\(prefix)StartID"
        guard a.values[pidKey] != nil || a.values[startKey] != nil else { return nil }
        guard a.values[pidKey] != nil, a.values[startKey] != nil else {
            throw ToolFailure("invalid_argument", "\(pidKey) and \(startKey) must be supplied together")
        }
        let pid = Int32(try a.integer(pidKey, range: 1...Int(Int32.max)))
        let start = try a.string(startKey, limit: 64)
        guard start.split(separator: ".", omittingEmptySubsequences: false).count == 2,
              start.allSatisfy({ $0.isASCII && ($0.isNumber || $0 == ".") }),
              !start.hasPrefix("."), !start.hasSuffix(".") else {
            throw ToolFailure("invalid_argument", "\(startKey) must be a process start ID returned by status")
        }
        return (pid, start)
    }

    static func comparison(current: (Int32, String?), previous: (Int32, String), previousLiveStart: String?) -> [String: Any] {
        let relation: String
        if current.1 == nil { relation = "current_identity_unavailable" }
        else if current.0 == previous.0, current.1 == previous.1 { relation = "same_instance" }
        else { relation = "different_instance" }
        return ["relation": relation,
                "previousIdentityAvailable": previousLiveStart != nil,
                "previousInstanceRunning": previousLiveStart == previous.1,
                "previousPIDReused": previousLiveStart != nil && previousLiveStart != previous.1]
    }

    public static func status(transport: InvocationTransport, previousServer: (Int32, String)? = nil,
                              previousParent: (Int32, String)? = nil) -> [String: Any] {
        let pid = getpid(), parent = getppid()
        var server = identity(pid), parentIdentity = identity(parent)
        server["instanceID"] = MacPilotRuntime.instanceID
        server["executable"] = Bundle.main.executableURL?.path ?? CommandLine.arguments[0]
        if let previousServer {
            server["comparison"] = comparison(current: (pid, server["processStartID"] as? String), previous: previousServer,
                                               previousLiveStart: ProcessIdentity.startID(pid: previousServer.0))
        }
        if let previousParent {
            parentIdentity["comparison"] = comparison(current: (parent, parentIdentity["processStartID"] as? String), previous: previousParent,
                                                       previousLiveStart: ProcessIdentity.startID(pid: previousParent.0))
        }
        let session = DesktopSession.current()
        let permissions: [String: Any] = session.available ? ["accessibility": AXIsProcessTrusted(), "screenCapture": CGPreflightScreenCaptureAccess(),
                           "postEvent": CGPreflightPostEventAccess(), "inputMonitoring": CGPreflightListenEventAccess()] : DesktopSession.unknownPermissions
        return ["status": "connection_responding", "version": MacPilotRuntime.version,
                "transport": transport.rawValue, "server": server, "parent": parentIdentity,
                "permissions": permissions, "permissionsStatus": session.available ? "probed" : "not_probed",
                "allPermissionsGranted": session.available ? permissions.values.allSatisfy { ($0 as? Bool) == true } as Any : NSNull(),
                "desktopSession": session.object,
                "foregroundPID": session.available ? (NSWorkspace.shared.frontmostApplication?.processIdentifier ?? 0) as Any : NSNull(),
                "hostConnectionVerified": transport == .mcpStdio,
                "parentRole": "Parent process identity only; this does not identify its product or prove other chats are progressing",
                "verification": transport == .mcpStdio ? "This MCP call returned; GUI actions and business outcomes require separate verification" : "One-shot CLI responded; the host's MCP connection was not tested",
                "recovery": ["scopedHostReconnectAvailable": false, "hostRestartRequired": "not_established",
                             "nextAction": "Retry one read-only status call through the host. If unavailable, run connection-check and use CLI while keeping host recovery unverified.",
                             "retryMutations": false, "globalReloadPerformed": false, "processesSignalled": 0]]
    }

    public static func call(_ a: Arguments, transport: InvocationTransport) async throws -> [String: Any] {
        let operation = try a.string("operation")
        try a.only(["operation", "previousServerPID", "previousServerStartID", "previousParentPID", "previousParentStartID", "timeoutMs"])
        let previousServer = try baseline(a, prefix: "Server"), previousParent = try baseline(a, prefix: "Parent")
        switch operation {
        case "status":
            guard a.values["timeoutMs"] == nil else { throw ToolFailure("invalid_argument", "timeoutMs applies only to probe") }
            return status(transport: transport, previousServer: previousServer, previousParent: previousParent)
        case "probe":
            let timeout = try a.integer("timeoutMs", default: 10000, range: 500...30000)
            let caller = status(transport: transport, previousServer: previousServer, previousParent: previousParent)
            guard let executable = Bundle.main.executableURL else { throw ToolFailure("process_launch_failed", "Cannot locate the current MacPilot executable") }
            return try await probe(executable: executable, timeout: timeout, caller: caller)
        default: throw ToolFailure("invalid_argument", "Connection operation must be status or probe")
        }
    }

    static func checkedTool(_ result: [String: Any]) throws -> [String: Any] {
        guard result["isError"] as? Bool == false, let object = result["structuredContent"] as? [String: Any] else {
            throw ToolFailure("mcp_probe_rejected", "Probe tool failed or omitted structuredContent")
        }
        return object
    }

    static func probe(executable: URL, timeout: Int, caller: [String: Any]) async throws -> [String: Any] {
        try Task.checkCancellation()
        let client = try ConnectionProbeClient(executable: executable, timeout: timeout)
        var phase = "initialize", result: [String: Any]
        do {
            let initialized = try await client.request("initialize", params: ["protocolVersion": "2025-11-25", "capabilities": [:],
                "clientInfo": ["name": "macpilot-connection-check", "version": MacPilotRuntime.version]])
            guard (initialized["serverInfo"] as? [String: Any])?["name"] as? String == "macpilot" else {
                throw ToolFailure("mcp_probe_protocol_error", "Unexpected MCP server identity")
            }
            try await client.notify("notifications/initialized")
            phase = "tools/list"
            let inventory = try await client.request("tools/list", params: [:])
            guard let tools = inventory["tools"] as? [[String: Any]], tools.contains(where: { $0["name"] as? String == "mac_connection" }) else {
                throw ToolFailure("mcp_probe_protocol_error", "Connection tool absent from MCP inventory")
            }
            phase = "mac_connection status"
            let connection = try checkedTool(await client.request("tools/call", params: ["name": "mac_connection", "arguments": ["operation": "status"]]))
            guard let server = connection["server"] as? [String: Any], server["pid"] as? Int32 == client.pid,
                  server["processStartID"] as? String == client.startID, connection["transport"] as? String == InvocationTransport.mcpStdio.rawValue else {
                throw ToolFailure("mcp_probe_protocol_error", "MCP response did not identify the owned probe process")
            }
            phase = "mac_doctor"
            let doctor = try checkedTool(await client.request("tools/call", params: ["name": "mac_doctor", "arguments": [:]]))
            result = ["status": "probe_passed", "serverInfo": initialized["serverInfo"] ?? [:], "toolCount": tools.count,
                      "probeConnection": connection, "permissions": doctor["permissions"] ?? [:],
                      "verification": "Isolated MCP handshake, inventory and read-only calls passed. This does not reconnect or verify the host's existing MCP connection."]
        } catch {
            result = ["status": "probe_failed", "phase": phase,
                      "code": error is CancellationError ? "cancelled" : (error as? ToolFailure)?.code ?? "mcp_probe_failed",
                      "verification": "Isolated probe failed; no existing host connection was changed"]
        }
        let cleanup = await client.close()
        if Task.isCancelled { throw CancellationError() }
        result["scope"] = "isolated_probe"
        result["hostConnectionVerified"] = false
        result["caller"] = caller
        result["cleanup"] = cleanup
        result["existingServersSignalled"] = 0
        result["globalReloadPerformed"] = false
        if cleanup["childExited"] as? Bool != true || cleanup["temporaryStateRemoved"] as? Bool != true {
            result["status"] = "probe_cleanup_failed"
        }
        return result
    }
}

/// A bounded duplex MCP client for one owned subprocess. Never attaches to an
/// existing PID, reloads Codex configuration, or replays a mutating operation.
@MainActor private final class ConnectionProbeClient {
    private let process = Process(), input = Pipe(), output = Pipe()
    private let state: URL
    private let deadline: UInt64
    private var buffer = Data(), sequence = 0, receivedBytes = 0
    let pid: Int32
    let startID: String

    init(executable: URL, timeout: Int) throws {
        deadline = DispatchTime.now().uptimeNanoseconds + UInt64(timeout) * 1_000_000
        state = FileManager.default.temporaryDirectory.appendingPathComponent("macpilot-connection-\(UUID().uuidString)", isDirectory: true)
        try FileManager.default.createDirectory(at: state, withIntermediateDirectories: false, attributes: [.posixPermissions: 0o700])
        process.executableURL = executable
        process.arguments = ["mcp"]
        var environment = ProcessInfo.processInfo.environment
        // Store creates and marks a previously nonexistent child directory. An
        // existing, unmarked temporary directory is intentionally rejected.
        environment["MACPILOT_STATE_DIR"] = state.appendingPathComponent("state", isDirectory: true).path
        environment.removeValue(forKey: "MAC_COMPUTER_USE_STATE_DIR")
        process.environment = environment
        process.standardInput = input
        process.standardOutput = output
        process.standardError = FileHandle.nullDevice
        do {
            for handle in [input.fileHandleForWriting, output.fileHandleForReading] {
                let fd = handle.fileDescriptor, flags = fcntl(fd, F_GETFL)
                guard flags >= 0, fcntl(fd, F_SETFL, flags | O_NONBLOCK) >= 0, fcntl(fd, F_SETNOSIGPIPE, 1) >= 0 else {
                    throw ToolFailure("mcp_probe_transport_failed", "Cannot configure bounded probe pipes")
                }
            }
            try process.run()
        } catch {
            try? FileManager.default.removeItem(at: state)
            throw ToolFailure("mcp_probe_launch_failed", "Cannot launch a dedicated MacPilot MCP probe")
        }
        pid = process.processIdentifier
        startID = ProcessIdentity.startID(pid: pid) ?? ""
        // The parent must not retain the child's ends of the pipes.
        try? input.fileHandleForReading.close()
        try? output.fileHandleForWriting.close()
    }

    private func checkDeadline() throws {
        try Task.checkCancellation()
        guard DispatchTime.now().uptimeNanoseconds < deadline else { throw ToolFailure("mcp_probe_timeout", "MCP probe deadline elapsed") }
    }

    private func write(_ object: [String: Any]) async throws {
        var data = try jsonData(object); data.append(10)
        var offset = 0
        while offset < data.count {
            try checkDeadline()
            let count = data.withUnsafeBytes { bytes in
                Darwin.write(input.fileHandleForWriting.fileDescriptor, bytes.baseAddress!.advanced(by: offset), data.count - offset)
            }
            if count > 0 { offset += count }
            else if count < 0 && [EAGAIN, EWOULDBLOCK, EINTR].contains(errno) { try await Task.sleep(nanoseconds: 10_000_000) }
            else { throw ToolFailure("mcp_probe_disconnected", "Owned probe input closed") }
        }
    }

    func notify(_ method: String) async throws { try await write(["jsonrpc": "2.0", "method": method]) }

    func request(_ method: String, params: [String: Any]) async throws -> [String: Any] {
        sequence += 1
        let id = sequence
        try await write(["jsonrpc": "2.0", "id": id, "method": method, "params": params])
        while true {
            try checkDeadline()
            if let newline = buffer.firstIndex(of: 10) {
                let line = Data(buffer[..<newline]); buffer.removeSubrange(...newline)
                guard line.count <= 2_000_000,
                      let message = (try? JSONSerialization.jsonObject(with: line)) as? [String: Any],
                      message["jsonrpc"] as? String == "2.0" else {
                    throw ToolFailure("mcp_probe_protocol_error", "Invalid or oversized MCP response")
                }
                if message["method"] is String {
                    if let requestID = message["id"] {
                        try await write(["jsonrpc": "2.0", "id": requestID, "error": ["code": -32601, "message": "Connection probe does not approve additional actions"]])
                    }
                    continue
                }
                guard let replyID = message["id"] as? NSNumber, CFGetTypeID(replyID) != CFBooleanGetTypeID(),
                      replyID.intValue == id, replyID.doubleValue == Double(id), message["error"] == nil,
                      let result = message["result"] as? [String: Any] else {
                    throw ToolFailure("mcp_probe_protocol_error", "MCP reply ID or result did not match the request")
                }
                return result
            }
            var bytes = [UInt8](repeating: 0, count: 65536)
            let count = Darwin.read(output.fileHandleForReading.fileDescriptor, &bytes, bytes.count)
            if count > 0 {
                buffer.append(contentsOf: bytes.prefix(count)); receivedBytes += count
                guard buffer.count <= 2_000_000, receivedBytes <= 8_000_000 else { throw ToolFailure("mcp_probe_protocol_error", "Probe output exceeds its limit") }
            } else if count == 0 { throw ToolFailure("mcp_probe_disconnected", "Owned probe exited before replying") }
            else if [EAGAIN, EWOULDBLOCK, EINTR].contains(errno) { try await Task.sleep(nanoseconds: 10_000_000) }
            else { throw ToolFailure("mcp_probe_transport_failed", "Cannot read owned probe output") }
        }
    }

    func close() async -> [String: Any] {
        try? input.fileHandleForWriting.close()
        var signalled = false
        for signalToSend in [Int32(0), SIGTERM, SIGKILL] {
            if signalToSend != 0, process.isRunning, !startID.isEmpty, ProcessIdentity.startID(pid: pid) == startID {
                _ = Darwin.kill(pid, signalToSend); signalled = true
            }
            let until = DispatchTime.now().uptimeNanoseconds + 250_000_000
            while process.isRunning && DispatchTime.now().uptimeNanoseconds < until {
                // Cleanup must also finish when the caller has been cancelled.
                _ = await Task.detached { usleep(10_000) }.value
            }
            if !process.isRunning { break }
        }
        try? output.fileHandleForReading.close()
        var removed = false
        if !process.isRunning {
            do { try FileManager.default.removeItem(at: state); removed = true } catch {}
        }
        return ["childPID": pid, "childStartID": startID, "childExited": !process.isRunning,
                "ownedChildSignalled": signalled, "temporaryStateRemoved": removed]
    }
}
