import XCTest
@testable import MacPilotCore

final class ConditionTests: XCTestCase {
    func node(_ id: String = "control", value: String? = nil) -> Node {
        Node(id: id, path: [0], role: "AXTextField", subrole: "", title: "", identifier: "field", value: value,
             valueTruncated: false, enabled: true, secure: false, focused: false, frame: Rect(CGRect(x: 1, y: 2, width: 100, height: 20)), actions: [])
    }
    func observation(_ nodes: [Node]) -> Observation {
        var o = CoreTests().observation(); o.coverage = "collected_window_tree"; o.diagnostics = []; o.nodes = nodes; return o
    }
    func testReacquisitionUsesIdentityRatherThanPriorPath() throws {
        let condition = try AXCondition(["selector":["identifier":"field"], "predicate":"equals", "text":"done"])
        XCTAssertFalse(try condition.evaluate(observation([node(value: "loading")])))
        var replacement = node("0.4", value: "done"); replacement.path = [4]
        XCTAssertTrue(try condition.evaluate(observation([replacement])))
        XCTAssertEqual(try condition.selected(in: observation([replacement]))?.id, "0.4")
    }
    func testPartialAndTruncatedTreesCannotProveAbsenceOrUniqueness() throws {
        let condition = try AXCondition(["selector":["identifier":"field"], "predicate":"absent"])
        var partial = observation([]); partial.coverage = "partial"
        XCTAssertThrowsError(try condition.evaluate(partial))
        var truncated = node(); truncated.identityTruncated = true
        XCTAssertThrowsError(try condition.evaluate(observation([truncated])))
        XCTAssertTrue(try condition.evaluate(observation([])))
    }
    func testAmbiguousSecureAndTruncatedValuesAreRejected() throws {
        let condition = try AXCondition(["selector":["identifier":"field"], "predicate":"equals", "text":"done"])
        XCTAssertThrowsError(try condition.evaluate(observation([node(value: "done"), node("twin", value: "done")])))
        var secure = node(value: "done"); secure.secure = true
        XCTAssertThrowsError(try condition.evaluate(observation([secure])))
        var truncated = node(value: "done"); truncated.valueTruncated = true
        XCTAssertThrowsError(try condition.evaluate(observation([truncated])))
    }
    func testConditionsDistinguishMissingDisabledFocusedAndText() throws {
        let selector: [String: Any] = ["identifier":"field"]
        var disabled = node(); disabled.enabled = false
        XCTAssertTrue(try AXCondition(["selector":selector, "predicate":"disabled"]).evaluate(observation([disabled])))
        XCTAssertFalse(try AXCondition(["selector":selector, "predicate":"disabled"]).evaluate(observation([])))
        var focused = node(); focused.focused = true
        XCTAssertTrue(try AXCondition(["selector":selector, "predicate":"focused"]).evaluate(observation([focused])))
        XCTAssertTrue(try AXCondition(["selector":selector, "predicate":"contains", "text":"한글 😀"]).evaluate(observation([node(value:"saved 한글 😀 file")])))
    }
    func testInvalidOrUnboundedConditionDoesNotReachRuntime() throws {
        for raw: [String: Any] in [["predicate":"unknown"], ["predicate":"exists"], ["predicate":"equals","selector":["identifier":"field"]],
                                  ["predicate":"exists","selector":["identifier":""]], ["predicate":"stable","stableMs":true],
                                  ["predicate":"stable","stableMs":100_000], ["predicate":"exists","selector":["identifier":"field"],"text":"unexpected"]] {
            XCTAssertThrowsError(try AXCondition(raw))
        }
        XCTAssertNoThrow(try AXCondition(["predicate":"stable"]))
    }
}
