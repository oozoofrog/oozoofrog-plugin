import XCTest
@testable import MacPilotCore

final class OverlayLifecycleTests: XCTestCase {
    func testLegacyAndCLILeasesExpireAtThirtySecondsWithoutFollowingAuditActivity() throws {
        let now = Date(timeIntervalSince1970: 1000)
        let legacy = try JSONDecoder().decode(OverlayTarget.self, from:
            Data(#"{"observation":"o","activityAt":970,"targetSequence":"legacy"}"#.utf8))
        XCTAssertEqual(legacy.endReason(now: now, currentOwnerStartID: nil), "idle_expired")
        var cli = OverlayTarget(observation: "o", activityAt: 970.001, targetSequence: "cli",
            ownerPID: 42, ownerStartID: "1.1", ownerTransport: "cli")
        XCTAssertNil(cli.endReason(now: now, currentOwnerStartID: nil), "A one-shot CLI may exit while its bounded display lease remains")
        cli.activityAt = 969.9
        XCTAssertEqual(cli.endReason(now: now, currentOwnerStartID: "1.1"), "idle_expired")
    }
    func testMCPOwnerDeathOrPIDReuseEndsAnOtherwiseFreshLease() {
        let target = OverlayTarget(observation: "o", activityAt: 1000, targetSequence: "mcp",
            ownerPID: 42, ownerStartID: "1.1", ownerTransport: "mcp_stdio")
        let now = Date(timeIntervalSince1970: 1000.5)
        XCTAssertNil(target.endReason(now: now, currentOwnerStartID: "1.1"))
        XCTAssertEqual(target.endReason(now: now, currentOwnerStartID: nil), "owner_exited")
        XCTAssertEqual(target.endReason(now: now, currentOwnerStartID: "2.1"), "owner_exited")
        XCTAssertEqual(target.endReason(now: Date(timeIntervalSince1970: 1030), currentOwnerStartID: "1.1"), "idle_expired")
    }
    func testFutureOrInvalidActivityCannotKeepFeedbackAlive() {
        for activity in [Double.infinity, Double.nan, 1002] {
            let target = OverlayTarget(observation: "o", activityAt: activity, targetSequence: "bad")
            XCTAssertEqual(target.endReason(now: Date(timeIntervalSince1970: 1000), currentOwnerStartID: nil), "invalid_activity_time")
        }
    }
    func testPartialOwnerIsNotAcceptedAsLegacyLease() {
        for target in [OverlayTarget(observation: "o", activityAt: 1000, targetSequence: "bad", ownerPID: 42),
                       OverlayTarget(observation: "o", activityAt: 1000, targetSequence: "bad", ownerTransport: "mcp_stdio")] {
            XCTAssertEqual(target.endReason(now: Date(timeIntervalSince1970: 1000), currentOwnerStartID: "1.1"), "invalid_owner")
        }
    }
    private func state() throws -> (parent: URL, store: Store) {
        let parent = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: parent, withIntermediateDirectories: false)
        return (parent, try Store(root: parent.appendingPathComponent("state")))
    }
    @MainActor func testStopNeedsNoObservationAndKeepsPersistedPointer() async throws {
        let (parent, store) = try state()
        defer { try? FileManager.default.removeItem(at: parent) }
        try store.savePointer(Pointer(windowID: 7, pid: 42, x: 10, y: 20))
        let before = try store.read("pointer.json")
        do {
            let result = try await Engine(store: store).call("mac_cursors", arguments: ["operation": "stop"])
            XCTAssertEqual(result["status"] as? String, "overlay_not_running")
            XCTAssertEqual(result["running"] as? Bool, false)
            XCTAssertEqual(try store.read("pointer.json"), before)
        } catch { XCTFail("Feedback cleanup must work without a live observation: \(error)") }
    }
    @MainActor func testCancelledOrExpiredTaskCanStopFeedbackWithoutBecomingActive() async throws {
        let (parent, store) = try state()
        defer { try? FileManager.default.removeItem(at: parent) }
        let engine = Engine(store: store)
        for expired in [false, true] {
            let result = try Tasks.call(Arguments(["operation": "begin"]), store: store)
            let id = (result["task"] as! [String: Any])["id"] as! String
            var task = try Tasks.load(id, in: store)
            if expired { task.deadline = Date().addingTimeInterval(-1) }
            else { task.status = "cancelled" }
            try Tasks.save(task, in: store)
            do {
                let stopped = try await engine.call("mac_cursors", arguments: ["operation": "stop", "taskID": id])
                XCTAssertEqual(stopped["status"] as? String, "overlay_not_running")
            } catch { XCTFail("Terminal task feedback must remain stoppable: \(error)") }
            let unchanged = try Tasks.load(id, in: store)
            XCTAssertEqual(unchanged.status, task.status)
            XCTAssertEqual(unchanged.deadline, task.deadline)
            do {
                _ = try await engine.call("mac_pointer", arguments: ["taskID": id, "observation": "stale", "x": 0, "y": 0, "space": "screen"])
                XCTFail("Cleanup must not revive ordinary input")
            } catch { XCTAssertEqual((error as? ToolFailure)?.code, expired ? "task_expired" : "task_cancelled") }
        }
    }
}
