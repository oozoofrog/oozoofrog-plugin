import XCTest
import ApplicationServices
@testable import MacPilotCore

final class UserInputTests: XCTestCase {
    func event() -> CGEvent { CGEvent(keyboardEventSource: CGEventSource(stateID: .privateState), virtualKey: 123, keyDown: true)! }
    func testOwnProvenanceDoesNotStopButForeignProvenanceDoes() {
        let monitor = UserInputMonitor(testing: true), own = event()
        InputOwnership.stamp(own)
        own.setIntegerValueField(.eventSourceUnixProcessID, value:Int64(getpid()))
        monitor.receive(.keyDown, event:own); XCTAssertNil(monitor.reason)
        let foreign = event(); foreign.setIntegerValueField(.eventSourceUserData, value:0)
        monitor.receive(.keyDown, event:foreign)
        XCTAssertEqual(monitor.reason,"user_input_interrupted"); XCTAssertEqual(monitor.externalEvents,1)
    }
    func testTagAloneDoesNotAuthenticateAnEvent() {
        let monitor = UserInputMonitor(testing:true), foreign = event()
        InputOwnership.stamp(foreign); foreign.setIntegerValueField(.eventSourceUnixProcessID, value:Int64(getpid()+1))
        monitor.receive(.mouseMoved, event:foreign); XCTAssertEqual(monitor.reason,"user_input_interrupted")
    }
    func testMonitorLossFailsClosedWithoutRecordingKeyContent() {
        let monitor = UserInputMonitor(testing:true)
        monitor.receive(.tapDisabledByTimeout, event:event())
        XCTAssertThrowsError(try monitor.verify()) { XCTAssertEqual(($0 as? ToolFailure)?.code,"input_monitor_lost") }
    }
    @MainActor func testInterruptedTaskRequiresExplicitResumeAndRetainsDeadline() throws {
        let parent = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at:parent, withIntermediateDirectories:false)
        defer { try? FileManager.default.removeItem(at:parent) }
        let store = try Store(root:parent.appendingPathComponent("state"))
        let task = try Tasks.call(Arguments(["operation":"begin"]),store:store)["task"] as! [String:Any]
        let id = task["id"] as! String, deadline = try Tasks.load(id,in:store).deadline
        let state = try Tasks.state(id,in:store), observation = CoreTests().observation()
        try state.save(observation)
        try Tasks.interrupt(id,reason:"user_input_interrupted",store:store)
        XCTAssertThrowsError(try Tasks.requireActive(Tasks.load(id,in:store)))
        XCTAssertEqual(try Tasks.load(id,in:store).interruptionReason,"user_input_interrupted")
        _ = try Tasks.call(Arguments(["operation":"resume","taskID":id]),store:store)
        XCTAssertNoThrow(try Tasks.requireActive(Tasks.load(id,in:store)))
        XCTAssertEqual(try Tasks.load(id,in:store).deadline,deadline)
        XCTAssertThrowsError(try state.load(observation.id))
        XCTAssertThrowsError(try Tasks.call(Arguments(["operation":"resume","taskID":id]),store:store))
    }
}
