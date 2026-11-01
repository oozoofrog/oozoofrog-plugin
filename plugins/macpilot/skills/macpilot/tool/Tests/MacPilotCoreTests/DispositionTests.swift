import XCTest
@testable import MacPilotCore

final class DispositionTests: XCTestCase {
    func testDeliveryControlsRetryWithoutChangingLegacyPayload() {
        let cases: [(String, String, String)] = [
            ("action_requested", "delivered_unverified", "unsafe"),
            ("dispatched_unverified", "delivered_unverified", "unsafe"),
            ("dispatch_interrupted", "delivery_uncertain", "unsafe"),
            ("value_unverified", "delivered_unverified", "unsafe"),
            ("value_verified", "delivered_verified", "unsafe"),
            ("close_unverified", "delivered_unverified", "unsafe"),
            ("minimize_state_unverified", "delivered_unverified", "unsafe"),
            ("move_unverified", "delivered_unverified", "unsafe"),
            ("resize_unverified", "delivered_unverified", "unsafe"),
            ("already_satisfied", "not_delivered", "safe"),
            ("future_status", "unknown", "unknown")
        ]
        for (status, delivery, retry) in cases {
            let result = Outcomes.attach("mac_ax", arguments: ["operation":"set_value"], value: ["status":status])
            let disposition = result["disposition"] as? [String:String]
            XCTAssertEqual(disposition?["delivery"], delivery, status)
            XCTAssertEqual(disposition?["retry"], retry, status)
            XCTAssertEqual(result["status"] as? String, status)
            XCTAssertNotNil(result["outcome"])
        }
    }

    func testNewDispositionPreservesLegacyDispatchAndExplicitAdapterEvidence() {
        let result = Outcomes.attach("mac_key", arguments: [:], value: ["status":"dispatched_unverified"])
        XCTAssertEqual((result["outcome"] as? [String:Any])?["dispatch"] as? String, "sent_or_unknown")
        let explicit = Outcomes.failure("mac_type", arguments: [:], beforeDispatch: false)
        let attached = Outcomes.attach("mac_ax", arguments: [:], value: ["status":"value_verified", "outcome":explicit.object])
        XCTAssertEqual((attached["disposition"] as? [String:String])?["delivery"], "delivery_uncertain")
    }

    func testReadAndControllerStateNeverProveTargetDelivery() {
        for (tool, args, status) in [
            ("mac_wait_for", [String:String](), "predicate_verified"),
            ("mac_task", ["operation":"finish"], "task_finished")
        ] {
            let result = Outcomes.attach(tool, arguments: args, value: ["status":status,"matches":true])
            XCTAssertEqual((result["disposition"] as? [String:String])?["delivery"], "not_delivered")
        }
    }

    func testFailureNeverAuthorizesBlindRetryAfterEnteringDispatch() {
        for (before, delivery, retry) in [(true,"not_delivered","safe"),(false,"delivery_uncertain","unsafe")] {
            let value = Outcomes.failure("mac_type", arguments: [:], beforeDispatch: before).object
            let disposition = value["disposition"] as? [String:String]
            XCTAssertEqual(disposition?["delivery"], delivery)
            XCTAssertEqual(disposition?["retry"], retry)
        }
    }

    func testAlreadySatisfiedAppAndWaitOnlyWorkflowDoNotClaimDelivery() {
        let app = Outcomes.attach("mac_app", arguments:["action":"unhide"], value:["status":"app_state_verified","actionDispatched":false])
        XCTAssertEqual((app["disposition"] as? [String:String])?["delivery"], "not_delivered")
        XCTAssertEqual((app["outcome"] as? [String:Any])?["effect"] as? String, "postcondition_verified")
        let workflow = Outcomes.attach("mac_workflow", arguments:["operation":"run"], value:["status":"workflow_verified","run":["mutationsDispatched":0]])
        XCTAssertEqual((workflow["disposition"] as? [String:String])?["delivery"], "not_delivered")
        let written = Outcomes.attach("mac_workflow", arguments:["operation":"run"], value:["status":"workflow_verified","run":["mutationsDispatched":1]])
        XCTAssertEqual((written["disposition"] as? [String:String])?["delivery"], "delivered_verified")
    }

    @MainActor func testAXTimeoutCarriesUncertainDeliveryAtItsSource() {
        let failure = AX.mutationFailure(.cannotComplete, operation: "test write")
        XCTAssertEqual(failure.code, "ax_outcome_uncertain")
        let disposition = failure.outcome?.object["disposition"] as? [String:String]
        XCTAssertEqual(disposition?["delivery"], "delivery_uncertain")
        XCTAssertEqual(disposition?["retry"], "unsafe")
    }

    func testMissingReadbackCannotVerifyEmptyValueAndMismatchStaysUnverified() {
        for (observed, expected, state) in [(nil as String?, "", "unavailable"), ("wrong", "wanted", "mismatch"), ("", "", "verified")] {
            let result = AX.valuePostcondition(expected:expected, observed:observed)
            XCTAssertEqual((result["postcondition"] as? [String:Any])?["state"] as? String, state)
            XCTAssertEqual(result["equalsRequestedText"] as? Bool, state == "verified")
        }
        let truncated = AX.valuePostcondition(expected:"abc", observed:"abcd", limit:3)
        XCTAssertEqual(truncated["equalsRequestedText"] as? Bool, false)
        XCTAssertEqual((truncated["postcondition"] as? [String:Any])?["state"] as? String, "unavailable")
    }

    func testLaterFailureKeepsReceiptAndExplicitCompletedOutcome() throws {
        let completed: [String:Any] = ["status":"action_requested", "requestID":"synthetic-receipt",
            "outcome":OperationOutcome(dispatch:"sent",effect:"unverified",retry:"observe_before_deciding").object]
        let failure = Outcomes.failure(ToolFailure("foreground_changed", "Synthetic guard failure"),
            tool:"mac_browser", arguments:["operation":"click"], beforeDispatch:false, completedResult:completed)
        let payload = failure.object
        XCTAssertEqual(payload["code"] as? String, "foreground_changed")
        XCTAssertEqual((payload["disposition"] as? [String:String])?["delivery"], "delivered_unverified")
        let after = (payload["details"] as? [String:Any])?["afterAction"] as? [String:Any]
        XCTAssertEqual(after?["requestID"] as? String, "synthetic-receipt")
        XCTAssertNoThrow(try JSONSerialization.data(withJSONObject:payload))
    }
}
