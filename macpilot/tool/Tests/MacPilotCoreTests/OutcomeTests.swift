import XCTest
@testable import MacPilotCore

final class OutcomeTests: XCTestCase {
    func testAcceptedAndPartialAreNotVerifiedOrRetryable() {
        for status in ["action_requested", "dispatched_unverified", "dispatch_interrupted", "shortcut_completed", "script_completed", "open_accepted"] {
            let result = Outcomes.result("mac_key", arguments: [:], value: ["status": status])
            XCTAssertEqual(result.retry, "observe_before_deciding")
            XCTAssertEqual(result.effect, "unverified")
        }
    }
    func testPredicateScopeDoesNotBecomeWholeTaskSuccess() {
        let passed = Outcomes.result("mac_wait_for", arguments: [:], value: ["status":"predicate_verified", "matches":true])
        XCTAssertEqual(passed.scope, "selected_predicate"); XCTAssertEqual(passed.dispatch, "not_applicable")
        let timedOut = Outcomes.result("mac_wait_for", arguments: [:], value: ["status":"predicate_timeout", "matches":false])
        XCTAssertEqual(timedOut.effect, "predicate_not_met"); XCTAssertEqual(timedOut.retry, "read_again")
        let task = Outcomes.result("mac_task", arguments:["operation":"finish"], value:["status":"task_finished"])
        XCTAssertEqual(task.scope, "controller_state"); XCTAssertEqual(task.effect, "state_recorded")
    }
    func testExistingStatusesAndPayloadArePreserved() {
        let attached = Outcomes.attach("mac_ax", arguments:["operation":"set_value"], value:["status":"value_verified", "equalsRequestedText":true])
        XCTAssertEqual(attached["status"] as? String, "value_verified")
        XCTAssertEqual(attached["equalsRequestedText"] as? Bool, true)
        XCTAssertEqual((attached["outcome"] as? [String:Any])?["scope"] as? String,"operation_postcondition")
    }
    func testFailuresAreConservativeAfterDispatchStarts() {
        XCTAssertEqual(Outcomes.failure("mac_type", arguments:[:], beforeDispatch:true).dispatch, "not_sent")
        XCTAssertEqual(Outcomes.failure("mac_type", arguments:[:], beforeDispatch:false).retry, "observe_before_deciding")
        XCTAssertEqual(Outcomes.failure("mac_observe", arguments:[:], beforeDispatch:false).effect, "read_failed")
    }
    func testReadClassificationRespectsOptionalWrites() {
        XCTAssertTrue(Outcomes.isRead("mac_system",arguments:["operation":"audio"]))
        XCTAssertFalse(Outcomes.isRead("mac_system",arguments:["operation":"audio","muted":false]))
        XCTAssertFalse(Outcomes.isRead("mac_system",arguments:["operation":"audio","volume":0.5]))
        XCTAssertTrue(Outcomes.isRead("mac_window",arguments:["operation":"state"]))
        XCTAssertFalse(Outcomes.isRead("mac_window",arguments:["operation":"close"]))
    }
}
