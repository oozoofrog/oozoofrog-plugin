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

    @MainActor func withEngine(_ body: (Engine) async throws -> Void) async throws {
        let parent = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: parent, withIntermediateDirectories: false)
        defer { try? FileManager.default.removeItem(at: parent) }
        try await body(Engine(store: Store(root: parent.appendingPathComponent("state"))))
    }

    @MainActor func testPartialReadCanRecoverToCompleteMatchingObservation() async throws {
        try await withEngine { engine in
            let condition = try AXCondition(["selector":["identifier":"field"], "predicate":"equals", "text":"done"])
            let pid = ProcessInfo.processInfo.processIdentifier, identity = try XCTUnwrap(ProcessIdentity.startID(pid: pid))
            var reads = 0
            let result = try await Conditions.wait(condition, pid: pid, identity: identity, windowID: 1,
                timeoutMs: 2000, pollMs: 1, engine: engine, observationProvider: { _ in
                    reads += 1
                    var value = self.observation([self.node(value: "done")])
                    value.id = reads == 1 ? "partial-read" : "complete-read"
                    if reads == 1 { value.coverage = "partial" }
                    try engine.store.write(jsonData(value.object), to: engine.store.root.appendingPathComponent(value.id + ".json"))
                    return value
                })
            XCTAssertEqual(result["matches"] as? Bool, true)
            XCTAssertGreaterThanOrEqual(reads, 2)
            XCTAssertFalse(FileManager.default.fileExists(atPath: engine.store.root.appendingPathComponent("partial-read.json").path))
            XCTAssertTrue(FileManager.default.fileExists(atPath: engine.store.root.appendingPathComponent("complete-read.json").path))
        }
    }

    @MainActor func testUnresolvedPartialReadAtDeadlineRemainsUnknown() async throws {
        for completeFirst in [false, true] {
            try await withEngine { engine in
                let condition = try AXCondition(["selector":["identifier":"field"], "predicate":"equals", "text":"done"])
                let pid = ProcessInfo.processInfo.processIdentifier, identity = try XCTUnwrap(ProcessIdentity.startID(pid: pid))
                var reads = 0
                do {
                    _ = try await Conditions.wait(condition, pid: pid, identity: identity, windowID: 1,
                        timeoutMs: 200, pollMs: 1, engine: engine, observationProvider: { _ in
                            reads += 1
                            var value = self.observation([self.node(value: "waiting")])
                            if !completeFirst || reads > 1 { value.coverage = "partial" }
                            return value
                        })
                    XCTFail("An unresolved partial read must not become a negative predicate result")
                } catch { XCTAssertEqual((error as? ToolFailure)?.code, "partial_coverage") }
                XCTAssertGreaterThan(reads, completeFirst ? 2 : 1)
            }
        }
    }

    @MainActor func testCompleteFalseReadAfterPartialResolvesUncertaintyAtDeadline() async throws {
        try await withEngine { engine in
            let condition = try AXCondition(["selector":["identifier":"field"], "predicate":"equals", "text":"done"])
            let pid = ProcessInfo.processInfo.processIdentifier, identity = try XCTUnwrap(ProcessIdentity.startID(pid: pid))
            var reads = 0
            let result = try await Conditions.wait(condition, pid: pid, identity: identity, windowID: 1,
                timeoutMs: 200, pollMs: 1, engine: engine, observationProvider: { _ in
                    reads += 1
                    var value = self.observation([self.node(value: "waiting")])
                    if reads == 1 { value.coverage = "partial" }
                    return value
                })
            XCTAssertEqual(result["status"] as? String, "predicate_timeout")
            XCTAssertEqual(result["matches"] as? Bool, false)
        }
    }

    @MainActor func testToleratedGeometryFailureCannotClearPendingPartialRead() async throws {
        try await withEngine { engine in
            let condition = try AXCondition(["selector":["identifier":"field"], "predicate":"exists"])
            let pid = ProcessInfo.processInfo.processIdentifier, identity = try XCTUnwrap(ProcessIdentity.startID(pid: pid))
            var reads = 0
            do {
                _ = try await Conditions.wait(condition, pid: pid, identity: identity, windowID: 1,
                    timeoutMs: 200, pollMs: 1, engine: engine, observationProvider: { _ in
                        reads += 1
                        if reads > 1 { throw ToolFailure("app_metadata_unavailable", "Synthetic transient read failure") }
                        var value = self.observation([]); value.coverage = "partial"; return value
                    })
                XCTFail("A tolerated geometry error cannot clear an unresolved partial read")
            } catch { XCTAssertEqual((error as? ToolFailure)?.code, "partial_coverage") }
            XCTAssertGreaterThan(reads, 1)
        }
    }

    @MainActor func testUnsafePredicateFailuresAreNotRetried() async throws {
        var secure = node(); secure.secure = true
        var identity = node(); identity.identityTruncated = true
        var truncated = node(value: "done"); truncated.valueTruncated = true
        let cases: [([Node], String)] = [([secure], "secure_node"), ([identity], "partial_identity"),
                                        ([truncated], "oversized_ax_value"), ([node(), node("twin")], "ambiguous_target")]
        for (nodes, code) in cases {
            try await withEngine { engine in
                let condition = try AXCondition(["selector":["identifier":"field"], "predicate":"equals", "text":"done"])
                let pid = ProcessInfo.processInfo.processIdentifier, startID = try XCTUnwrap(ProcessIdentity.startID(pid: pid))
                var reads = 0
                do {
                    _ = try await Conditions.wait(condition, pid: pid, identity: startID, windowID: 1,
                        timeoutMs: 2000, pollMs: 1, engine: engine, observationProvider: { _ in reads += 1; return self.observation(nodes) })
                    XCTFail("Unsafe predicate failure must remain an error")
                } catch { XCTAssertEqual((error as? ToolFailure)?.code, code) }
                XCTAssertEqual(reads, 1)
            }
        }
    }

    @MainActor func testPartialReadResetsStableFrameInterval() async throws {
        try await withEngine { engine in
            let condition = try AXCondition(["selector":["identifier":"field"], "predicate":"stable", "stableMs":100])
            let pid = ProcessInfo.processInfo.processIdentifier, identity = try XCTUnwrap(ProcessIdentity.startID(pid: pid))
            var reads = 0, recoveredAt: UInt64?
            let result = try await Conditions.wait(condition, pid: pid, identity: identity, windowID: 1,
                timeoutMs: 2000, pollMs: 1, engine: engine, observationProvider: { _ in
                    reads += 1
                    var value = self.observation([self.node()])
                    if reads == 2 {
                        try await Task.sleep(nanoseconds: 200_000_000)
                        value.coverage = "partial"
                    } else if reads == 3 { recoveredAt = DispatchTime.now().uptimeNanoseconds }
                    return value
                })
            XCTAssertEqual(result["matches"] as? Bool, true)
            let recovery = try XCTUnwrap(recoveredAt)
            XCTAssertGreaterThanOrEqual(DispatchTime.now().uptimeNanoseconds - recovery, 100_000_000)
        }
    }
}
