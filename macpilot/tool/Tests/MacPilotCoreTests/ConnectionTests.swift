import XCTest
import Darwin
@testable import MacPilotCore

final class ConnectionTests: XCTestCase {
    @MainActor func testStatusHasStableInstanceAndExplicitTransportScope() throws {
        let start = try XCTUnwrap(ProcessIdentity.startID(pid: getpid()))
        let first = ConnectionDiagnostics.status(transport: .cli, previousServer: (getpid(), start))
        let second = ConnectionDiagnostics.status(transport: .mcpStdio)
        XCTAssertEqual(first["hostConnectionVerified"] as? Bool, false)
        XCTAssertEqual(second["hostConnectionVerified"] as? Bool, true)
        let server = try XCTUnwrap(first["server"] as? [String: Any])
        XCTAssertEqual(server["pid"] as? Int32, getpid())
        XCTAssertEqual(server["processStartID"] as? String, start)
        XCTAssertEqual(server["instanceID"] as? String, (second["server"] as? [String: Any])?["instanceID"] as? String)
        XCTAssertEqual((server["comparison"] as? [String: Any])?["relation"] as? String, "same_instance")
        XCTAssertEqual((first["parent"] as? [String: Any])?["pid"] as? Int32, getppid())
        XCTAssertEqual((first["recovery"] as? [String: Any])?["processesSignalled"] as? Int, 0)
    }

    @MainActor func testComparisonDoesNotConfusePIDReuseWithOriginalProcess() {
        let reused = ConnectionDiagnostics.comparison(current: (10, "2.1"), previous: (10, "1.1"), previousLiveStart: "2.1")
        XCTAssertEqual(reused["relation"] as? String, "different_instance")
        XCTAssertEqual(reused["previousPIDReused"] as? Bool, true)
        XCTAssertEqual(reused["previousInstanceRunning"] as? Bool, false)
        let unknown = ConnectionDiagnostics.comparison(current: (10, nil), previous: (10, "1.1"), previousLiveStart: nil)
        XCTAssertEqual(unknown["relation"] as? String, "current_identity_unavailable")
        XCTAssertEqual(unknown["previousIdentityAvailable"] as? Bool, false)
    }

    @MainActor func testDiagnosticsAvailableWhileAnotherCallOwnsTheStoreLease() async throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: root) }
        let store = try Store(root: root)
        let lease = try store.lease(".execution.lock")
        defer { withExtendedLifetime(lease) {} }
        let result = try await Engine(store: store, transport: .mcpStdio).call("mac_connection", arguments: ["operation": "status"])
        XCTAssertEqual(result["status"] as? String, "connection_responding")
        XCTAssertEqual(result["hostConnectionVerified"] as? Bool, true)
    }

    @MainActor func testDiagnosticsRejectIncompleteIdentityAndMutationOptions() async {
        for input: [String: Any] in [
            ["operation": "status", "previousServerPID": getpid()],
            ["operation": "status", "previousParentStartID": "1.1"],
            ["operation": "status", "previousServerPID": true, "previousServerStartID": "1.1"],
            ["operation": "status", "previousServerPID": getpid(), "previousServerStartID": "../1"],
            ["operation": "status", "timeoutMs": 1000],
            ["operation": "probe", "timeoutMs": 0],
            ["operation": "restart"], ["operation": "status", "kill": true],
            ["operation": "status", "taskID": UUID().uuidString]
        ] {
            do { _ = try await ConnectionDiagnostics.call(Arguments(input), transport: .cli); XCTFail("Accepted invalid arguments: \(input)") }
            catch { XCTAssertEqual((error as? ToolFailure)?.code, "invalid_argument") }
        }
    }

    private func fixture(_ body: String) throws -> URL {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent("connection-test-\(UUID().uuidString)")
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: false, attributes: [.posixPermissions: 0o700])
        let path = root.appendingPathComponent("fixture")
        try Data(("#!/bin/sh\n" + body + "\n").utf8).write(to: path)
        try FileManager.default.setAttributes([.posixPermissions: 0o700], ofItemAtPath: path.path)
        return path
    }

    @MainActor func testEOFAndWrongReplyFailAndCleanOnlyOwnedProbe() async throws {
        for (script, code) in [("exit 0", "mcp_probe_disconnected"),
                               ("read -r line\nprintf '%s\\n' '{\"jsonrpc\":\"2.0\",\"id\":true,\"result\":{}}'", "mcp_probe_protocol_error"),
                               ("read -r line\nprintf '%s\\n' '{\"jsonrpc\":\"2.0\",\"id\":999,\"result\":{}}'", "mcp_probe_protocol_error")] {
            let executable = try fixture(script)
            defer { try? FileManager.default.removeItem(at: executable.deletingLastPathComponent()) }
            let result = try await ConnectionDiagnostics.probe(executable: executable, timeout: 1000, caller: [:])
            XCTAssertEqual(result["status"] as? String, "probe_failed")
            XCTAssertEqual(result["phase"] as? String, "initialize")
            XCTAssertEqual(result["code"] as? String, code)
            XCTAssertEqual(result["hostConnectionVerified"] as? Bool, false)
            XCTAssertEqual(result["existingServersSignalled"] as? Int, 0)
            let cleanup = try XCTUnwrap(result["cleanup"] as? [String: Any])
            XCTAssertEqual(cleanup["childExited"] as? Bool, true)
            XCTAssertEqual(cleanup["temporaryStateRemoved"] as? Bool, true)
        }
    }

    @MainActor func testTimeoutAndCancellationReapOnlyOwnedChild() async throws {
        let executable = try fixture("exec /bin/sleep 10")
        defer { try? FileManager.default.removeItem(at: executable.deletingLastPathComponent()) }
        let began = Date()
        let result = try await ConnectionDiagnostics.probe(executable: executable, timeout: 100, caller: [:])
        XCTAssertLessThan(Date().timeIntervalSince(began), 2)
        XCTAssertEqual(result["code"] as? String, "mcp_probe_timeout")
        let cleanup = try XCTUnwrap(result["cleanup"] as? [String: Any])
        XCTAssertEqual(cleanup["childExited"] as? Bool, true)
        XCTAssertEqual(cleanup["ownedChildSignalled"] as? Bool, true)
        XCTAssertEqual(cleanup["temporaryStateRemoved"] as? Bool, true)
        let temporary = FileManager.default.temporaryDirectory
        let before = Set(try FileManager.default.contentsOfDirectory(atPath: temporary.path).filter { $0.hasPrefix("macpilot-connection-") })
        let work = Task { @MainActor in try await ConnectionDiagnostics.probe(executable: executable, timeout: 10000, caller: [:]) }
        try await Task.sleep(nanoseconds: 30_000_000)
        work.cancel()
        do { _ = try await work.value; XCTFail("Cancellation must propagate") } catch { XCTAssertTrue(error is CancellationError) }
        let after = Set(try FileManager.default.contentsOfDirectory(atPath: temporary.path).filter { $0.hasPrefix("macpilot-connection-") })
        XCTAssertEqual(before, after, "Cancellation must remove the owned temporary state")
    }
}
