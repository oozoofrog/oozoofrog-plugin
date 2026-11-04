import AppKit
import XCTest
@testable import MacPilotCore

final class ControlHandoffTests: XCTestCase {
    @MainActor func testCocoaCancelAndEscapeDeclineWhileReturnCannotAccept() {
        _ = NSApplication.shared
        let panel = ControlHandoffPanel(contentRect: .zero, styleMask: [.borderless], backing: .buffered, defer: false)
        var declined = 0; panel.decline = { declined += 1 }
        func key(_ code: UInt16, characters: String) -> NSEvent {
            NSEvent.keyEvent(with: .keyDown, location: .zero, modifierFlags: [], timestamp: 0,
                windowNumber: panel.windowNumber, context: nil, characters: characters,
                charactersIgnoringModifiers: characters, isARepeat: false, keyCode: code)!
        }
        XCTAssertTrue(panel.performKeyEquivalent(with: key(36, characters: "\r")))
        XCTAssertTrue(panel.performKeyEquivalent(with: key(76, characters: "\r")))
        XCTAssertEqual(declined, 0)
        XCTAssertTrue(panel.performKeyEquivalent(with: key(53, characters: "\u{1b}")))
        XCTAssertEqual(declined, 1)
        panel.cancelOperation(nil); XCTAssertEqual(declined, 2)
        panel.close()
    }
    func testGrantNeedsFreshExactHostIdentity() {
        let now = Date()
        let status = ControlHandoffStatus(id: "epoch", taskID: "task", phase: "granted", hostPID: 42,
            hostStartID: "host-generation", updatedAt: now)
        XCTAssertTrue(status.isFresh(now: now, hostIdentity: "host-generation"))
        XCTAssertFalse(status.isFresh(now: now, hostIdentity: "reused-pid"))
        XCTAssertFalse(status.isFresh(now: now, hostIdentity: nil))
        XCTAssertFalse(status.isFresh(now: now.addingTimeInterval(1), hostIdentity: "host-generation"))
        XCTAssertFalse(status.isFresh(now: now.addingTimeInterval(-2), hostIdentity: "host-generation"))
    }
    @MainActor func testTaskFlagAloneCannotGrantAndEpochMustMatchLiveHost() throws {
        let parent = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: parent, withIntermediateDirectories: false)
        defer { try? FileManager.default.removeItem(at: parent) }
        let store = try Store(root: parent.appendingPathComponent("state"))
        let value = try Tasks.call(Arguments(["operation": "begin", "preserveForeground": false]), store: store)
        let id = (value["task"] as! [String: Any])["id"] as! String
        XCTAssertThrowsError(try ControlHandoff.requireGrant(taskID: id, store: store))
        XCTAssertEqual(try Tasks.load(id, in: store).status, "interrupted")
        var task = try Tasks.load(id, in: store); task.status = "active"; task.controlRequestID = "epoch"
        try Tasks.save(task, in: store)
        var grant = ControlHandoffStatus(id: "epoch", taskID: id, phase: "granted", hostPID: getpid(),
            hostStartID: ProcessIdentity.startID(pid: getpid())!, updatedAt: Date())
        func save() throws { try store.write(JSONEncoder().encode(grant), to: store.root.appendingPathComponent("control-handoff-status.json")) }
        try save()
        XCTAssertNoThrow(try ControlHandoff.requireGrant(taskID: id, store: store))
        XCTAssertThrowsError(try ControlHandoff.requireGrant(taskID: id, store: store, expectedEpoch: "previous-epoch"))
        XCTAssertEqual(try Tasks.load(id, in: store).status, "active", "A stale worker must not interrupt the newly granted epoch")
        grant.id = "old-epoch"; try save()
        XCTAssertThrowsError(try ControlHandoff.requireGrant(taskID: id, store: store))
        task.status = "active"; try Tasks.save(task, in: store)
        grant.id = "epoch"; grant.phase = "revoked"; try save()
        XCTAssertThrowsError(try ControlHandoff.requireGrant(taskID: id, store: store))
    }
    func testConcreteForegroundRoutesAndPermissionBootstrapAreSeparate() {
        let foreground: [(String, [String: Any])] = [("mac_key", ["route": "global"]), ("mac_activate", [:]),
            ("mac_focus", [:]), ("mac_reveal", [:]), ("mac_script", [:]), ("mac_shortcuts", ["operation": "run"]),
            ("mac_window", ["operation": "raise"]), ("mac_app", ["action": "unhide"]),
            ("mac_browser", ["operation": "select", "activate": true]), ("mac_permission", ["operation": "request"])]
        for (tool, args) in foreground { XCTAssertTrue(Engine.requiresForegroundControl(tool, arguments: args), tool) }
        let background: [(String, [String: Any])] = [("mac_key", ["route": "process"]), ("mac_observe", [:]),
            ("mac_ax", ["operation": "action"]), ("mac_click", [:]), ("mac_menu", ["operation": "press"]),
            ("mac_window", ["operation": "state"]), ("mac_shortcuts", ["operation": "list"]),
            ("mac_launch", ["activate": false]), ("mac_permission", ["operation": "setup"])]
        for (tool, args) in background { XCTAssertFalse(Engine.requiresForegroundControl(tool, arguments: args), tool) }
    }
    @MainActor func testAwaitingTaskCanBeCancelledAndInterrupted() throws {
        let parent = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: parent, withIntermediateDirectories: false)
        defer { try? FileManager.default.removeItem(at: parent) }
        let store = try Store(root: parent.appendingPathComponent("state"))
        let value = try Tasks.call(Arguments(["operation": "begin"]), store: store)
        let id = (value["task"] as! [String: Any])["id"] as! String
        var task = try Tasks.load(id, in: store); task.status = "awaiting_control"; try Tasks.save(task, in: store)
        _ = try Tasks.call(Arguments(["operation": "cancel", "taskID": id]), store: store)
        XCTAssertEqual(try Tasks.load(id, in: store).status, "cancelled")
        task.status = "awaiting_control"; try Tasks.save(task, in: store)
        try Tasks.interrupt(id, reason: "control_handoff_declined", store: store)
        XCTAssertEqual(try Tasks.load(id, in: store).status, "interrupted")
    }
    @MainActor func testAdmissionFailureSurvivesLockContentionWithoutCrossingEpoch() throws {
        let parent = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: parent, withIntermediateDirectories: false)
        defer { try? FileManager.default.removeItem(at: parent) }
        let store = try Store(root: parent.appendingPathComponent("state"))
        let value = try Tasks.call(Arguments(["operation": "begin"]), store: store)
        let id = (value["task"] as! [String: Any])["id"] as! String
        var task = try Tasks.load(id, in: store); task.controlRequestID = "old"; try Tasks.save(task, in: store)
        var lease: StateLease? = try store.lease(".tasks.lock")
        try Tasks.queueControlFailure(id, epoch: "old", reason: "admission_failed", store: store)
        XCTAssertEqual(try Tasks.load(id, in: store).status, "active")
        withExtendedLifetime(lease) {}; lease = nil
        XCTAssertEqual(try Tasks.load(id, in: store).status, "interrupted")
        _ = try Tasks.call(Arguments(["operation": "resume", "taskID": id]), store: store)
        XCTAssertEqual(try Tasks.load(id, in: store).status, "active", "A consumed failure must not re-interrupt an explicit resume")
        task.controlRequestID = "new"; task.status = "active"; try Tasks.save(task, in: store)
        try Tasks.queueControlFailure(id, epoch: "old", reason: "late_old_failure", store: store)
        XCTAssertEqual(try Tasks.load(id, in: store).status, "active")
        try Tasks.interrupt(id, reason: "late_old_worker", store: store, controlRequestID: "old")
        XCTAssertEqual(try Tasks.load(id, in: store).status, "active")
    }
    func testEveryMouseButtonReleaseAndDragCanRevokeControl() {
        for type: CGEventType in [.rightMouseUp, .otherMouseUp, .otherMouseDragged] {
            XCTAssertTrue(UserInputMonitor.monitoredTypes.contains(type))
            let monitor = UserInputMonitor(testing: true)
            let event = CGEvent(source: nil)!
            monitor.receive(type, event: event)
            XCTAssertEqual(monitor.reason, "user_input_interrupted")
        }
    }
}
