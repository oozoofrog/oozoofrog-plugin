import XCTest
@testable import MacPilotCore

@MainActor final class BrowserDeveloperTests: XCTestCase {
    func testRejectApprovalBypassAndCrossBrowserSettings() throws {
        let base: [String: Any] = ["operation": "enable", "browser": "safari", "setting": "developer_features", "pid": 42, "processStartID": "test"]
        XCTAssertNoThrow(try BrowserDeveloperSettings.Request(Arguments(base)))
        for extra in [["approved": true], ["approvalID": "fake"], ["setting": "extension_developer_mode"], ["browser": "edge"], ["operation": "disable"], ["pid": true], ["timeoutMs": 0], ["windowID": 12]] as [[String: Any]] {
            XCTAssertThrowsError(try BrowserDeveloperSettings.Request(Arguments(base.merging(extra) { _, new in new })))
        }
        let chrome = base.merging(["browser": "chrome", "setting": "extension_developer_mode"]) { _, new in new }
        XCTAssertThrowsError(try BrowserDeveloperSettings.Request(Arguments(chrome)))
        XCTAssertNoThrow(try BrowserDeveloperSettings.Request(Arguments(chrome.merging(["windowID": 12]) { _, new in new })))
    }
    func testDeclineAndAlreadyEnabledNeverPress() async throws {
        var prompts = 0, presses = 0
        for initial in [false, true] {
            let result = try await BrowserDeveloperSettings.approvedEnable(initial: initial, isEnabled: { $0 }, confirm: { prompts += 1; return false },
                reread: { XCTFail("Declined/already enabled must not reread"); return false }, same: { $0 == $1 }, press: { presses += 1 }, verify: { XCTFail("Must not verify a mutation"); return true })
            XCTAssertEqual(result, initial ? "already_enabled" : "approval_declined")
        }
        XCTAssertEqual(prompts, 1); XCTAssertEqual(presses, 0)
    }
    func testApprovalFailureAndChangedTargetCannotMutate() async throws {
        var presses = 0
        do {
            _ = try await BrowserDeveloperSettings.approvedEnable(initial: false, isEnabled: { $0 }, confirm: { throw ToolFailure("approval_unavailable", "fixture") },
                reread: { false }, same: { _, _ in true }, press: { presses += 1 }, verify: { true })
            XCTFail("Confirmation failure must propagate")
        } catch { XCTAssertEqual((error as? ToolFailure)?.code, "approval_unavailable") }
        do {
            _ = try await BrowserDeveloperSettings.approvedEnable(initial: 1, isEnabled: { _ in false }, confirm: { true },
                reread: { 2 }, same: { $0 == $1 }, press: { presses += 1 }, verify: { true })
            XCTFail("Changed scope must fail")
        } catch { XCTAssertEqual((error as? ToolFailure)?.code, "settings_target_changed") }
        XCTAssertEqual(presses, 0)
    }
    func testSingleDispatchAndOutcomeReconciliation() async throws {
        for uncertain in [false, true] {
            var presses = 0, verifications = 0
            let result = try await BrowserDeveloperSettings.approvedEnable(initial: false, isEnabled: { $0 }, confirm: { true }, reread: { false }, same: { _, _ in true },
                press: { presses += 1; if uncertain { throw ToolFailure("ax_outcome_uncertain", "fixture") } }, verify: { verifications += 1; return true })
            XCTAssertEqual(result, "enabled_verified"); XCTAssertEqual(presses, 1); XCTAssertEqual(verifications, 1)
        }
        var presses = 0
        do {
            _ = try await BrowserDeveloperSettings.approvedEnable(initial: false, isEnabled: { $0 }, confirm: { true }, reread: { false }, same: { _, _ in true },
                press: { presses += 1 }, verify: { false })
            XCTFail("Unverified state must fail")
        } catch { XCTAssertEqual((error as? ToolFailure)?.code, "settings_outcome_unconfirmed") }
        XCTAssertEqual(presses, 1)
    }
    func testCancellationAfterApprovalCannotPress() async throws {
        var pressed = false
        let worker = Task { @MainActor in
            try await BrowserDeveloperSettings.approvedEnable(initial: false, isEnabled: { $0 }, confirm: {
                withUnsafeCurrentTask { $0?.cancel() }; return true
            }, reread: { false }, same: { _, _ in true }, press: { pressed = true }, verify: { true })
        }
        do { _ = try await worker.value; XCTFail("Cancelled work must stop") }
        catch { XCTAssertTrue(error is CancellationError) }
        XCTAssertFalse(pressed)
    }
    func testBackgroundTaskRejectsPreparationBeforeAnyBrowserUI() async throws {
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: directory) }
        let store = try Store(root: directory), engine = Engine(store: store)
        let task = try Tasks.call(Arguments(["operation": "begin", "goal": "Read without activation"]), store: store)["task"] as! [String: Any]
        for operation in ["prepare", "enable"] {
            do {
                _ = try await engine.call("mac_browser_developer", arguments: ["taskID": task["id"]!, "operation": operation,
                    "browser": "safari", "setting": "developer_features", "pid": 42, "processStartID": "unused"])
                XCTFail("Background task must reject UI activation")
            } catch { XCTAssertEqual((error as? ToolFailure)?.code, "foreground_required") }
        }
    }
    /// Development-only integration seam. Never changes a personal profile.
    /// The harness owns the Chrome PID/profile named in its config and leaves
    /// the production native-confirmation path untouched.
    func testOwnedChromeRuntime() async throws {
        guard let path = ProcessInfo.processInfo.environment["MACPILOT_DEVELOPER_TEST_CONFIG"] else { throw XCTSkip("Owned Chrome runtime requires explicit harness config") }
        let config = try JSONSerialization.jsonObject(with: Data(contentsOf: URL(fileURLWithPath: path))) as! [String: Any]
        let base = config["arguments"] as! [String: Any]
        let store = try Store(root: URL(fileURLWithPath: config["stateDirectory"] as! String))
        let engine = Engine(store: store)
        func arguments(_ operation: String) -> Arguments { Arguments(base.merging(["operation": operation]) { _, new in new }) }
        let initial = try await BrowserDeveloperSettings.call(arguments("status"), engine: engine)
        XCTAssertEqual(initial["enabled"] as? Bool, false)
        var asked = false
        let declined = try await BrowserDeveloperSettings.execute(arguments("enable"), engine: engine, confirm: { message, _ in
            asked = true; XCTAssertTrue(message.contains("확장 프로그램 개발자 모드"))
            XCTAssertTrue(message.contains(String(base["pid"] as! Int))); return false
        })
        XCTAssertTrue(asked); XCTAssertEqual(declined["status"] as? String, "approval_declined")
        let afterDecline = try await BrowserDeveloperSettings.call(arguments("status"), engine: engine)
        XCTAssertEqual(afterDecline["enabled"] as? Bool, false)
        // Native prompt is exercised through its unattended five-second expiry.
        let timed = base.merging(["operation": "enable", "timeoutMs": 5000]) { _, new in new }
        let timeout = try await BrowserDeveloperSettings.call(Arguments(timed), engine: engine)
        XCTAssertEqual(timeout["status"] as? String, "approval_declined")
        let afterExpiry = try await BrowserDeveloperSettings.call(arguments("status"), engine: engine)
        XCTAssertEqual(afterExpiry["enabled"] as? Bool, false)
        let enabled = try await BrowserDeveloperSettings.execute(arguments("enable"), engine: engine, confirm: { _, _ in true })
        XCTAssertEqual(enabled["status"] as? String, "enabled_verified")
        XCTAssertEqual(enabled["enabled"] as? Bool, true)
        let repeated = try await BrowserDeveloperSettings.execute(arguments("enable"), engine: engine, confirm: { _, _ in XCTFail("Already enabled must not prompt"); return true })
        XCTAssertEqual(repeated["status"] as? String, "already_enabled")
        let record: [String: Any] = ["initial": initial, "declined": declined, "expiredNativePrompt": timeout, "enabledWithTestConfirmation": enabled, "repeated": repeated,
                                  "approvalEvidence": "Native expiry plus internal simulated consent for owned Chrome; no real human acceptance claimed"]
        try JSONSerialization.data(withJSONObject: record, options: [.prettyPrinted, .sortedKeys]).write(to: URL(fileURLWithPath: config["reportPath"] as! String))
    }
}
