import XCTest
@testable import MacPilotCore

final class PreviewTargetTests: XCTestCase {
    private func state() throws -> (URL, Store) {
        let parent = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: parent, withIntermediateDirectories: false)
        return (parent, try Store(root: parent.appendingPathComponent("state")))
    }
    @MainActor func testDifferentOrUnknownTargetCannotReturnPreviousHostsReceipt() async throws {
        let observation = CoreTests().observation()
        let exact: [String: Any] = ["status": "running", "pid": getpid(), "processStartID": ProcessIdentity.startID(pid: getpid())!,
            "targetPID": observation.pid, "targetStartID": observation.processStartID, "windowID": observation.windowID,
            "frameCount": 10, "sequence": "old-sequence", "launchSequence": "old-launch"]
        for changed in ["windowID", "targetPID", "targetStartID", "legacy", "failed", "no-frame"] {
            let (parent, store) = try state()
            defer { try? FileManager.default.removeItem(at: parent) }
            var status = exact
            switch changed {
            case "windowID": status[changed] = observation.windowID + 1
            case "targetPID": status[changed] = observation.pid + 1
            case "targetStartID": status[changed] = "reused-process-generation"
            case "legacy": status.removeValue(forKey: "targetPID"); status.removeValue(forKey: "targetStartID")
            case "failed": status["status"] = "failed"
            default: status["frameCount"] = 0
            }
            try store.write(jsonData(status), to: store.root.appendingPathComponent("preview-status.json"))
            // The live test process intentionally does not acknowledge the
            // preview command. Admission must fail rather than return old data.
            do {
                let result = try await PreviewActions.call(Arguments(["operation": "start", "timeoutMs": 100]), store: store, observation: observation)
                XCTFail("\(changed) returned a previous/unverified preview receipt: \(result)")
            } catch { XCTAssertTrue((error as? ToolFailure)?.code.hasPrefix("preview_") == true, "\(changed): \(error)") }
        }
    }
    @MainActor func testExactTargetStartPreservesPausedHiddenHost() async throws {
        let (parent, store) = try state()
        defer { try? FileManager.default.removeItem(at: parent) }
        let observation = CoreTests().observation()
        let status: [String: Any] = ["status": "running", "pid": getpid(), "processStartID": ProcessIdentity.startID(pid: getpid())!,
            "targetPID": observation.pid, "targetStartID": observation.processStartID, "windowID": observation.windowID,
            "frameCount": 10, "visible": false, "paused": true, "sequence": "same", "launchSequence": "same"]
        try store.write(jsonData(status), to: store.root.appendingPathComponent("preview-status.json"))
        let result = try await PreviewActions.call(Arguments(["operation": "start", "timeoutMs": 100]), store: store, observation: observation)
        XCTAssertEqual(result["pid"] as? Int32, getpid())
        XCTAssertEqual(result["visible"] as? Bool, false)
        XCTAssertEqual(result["paused"] as? Bool, true)
        XCTAssertFalse((try store.names(prefix: "preview-command")).contains("preview-command.json"))
    }
    @MainActor func testIndependentTerminalReceiptAndExactExitReconcileStopRace() async throws {
        let (parent, store) = try state()
        defer { try? FileManager.default.removeItem(at: parent) }
        let child = Process(); child.executableURL = URL(fileURLWithPath: "/bin/sleep"); child.arguments = ["0.25"]
        try child.run()
        let identity = try XCTUnwrap(ProcessIdentity.startID(pid: child.processIdentifier))
        let initial: [String: Any] = ["pid": child.processIdentifier, "processStartID": identity,
            "status": "running", "visible": true, "sequence": "previous-command"]
        try store.write(jsonData(initial), to: store.root.appendingPathComponent("preview-status.json"))
        let independentStop = Task { @MainActor in
            try await Task.sleep(nanoseconds: 50_000_000)
            var terminal = initial; terminal["status"] = "stopped"; terminal["visible"] = false
            try store.write(jsonData(terminal), to: store.root.appendingPathComponent("preview-status.json"))
        }
        defer { independentStop.cancel(); if child.isRunning { child.terminate() }; child.waitUntilExit() }
        do {
            try await PreviewActions.stopBeforeReplacement(initial, store: store, deadline: Date().addingTimeInterval(2))
            XCTAssertNotEqual(ProcessIdentity.startID(pid: child.processIdentifier), identity)
        } catch { XCTFail("Independent terminal receipt plus exact process exit must reconcile the stop race: \(error)") }
    }
}
