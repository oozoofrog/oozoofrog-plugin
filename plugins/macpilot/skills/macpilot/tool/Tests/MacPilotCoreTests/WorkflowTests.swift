import XCTest
@testable import MacPilotCore

final class WorkflowTests: XCTestCase {
    func definition() -> [String:Any] {
        ["name":"literal_recipe","parameters":["text"],"steps":[
            ["action":"set_value","selector":["identifier":"literal-text"],"parameter":"text",
             "postcondition":["selector":["identifier":"literal-text"],"predicate":"equals","textParameter":"text"]],
            ["action":"press","selector":["identifier":"increment"],
             "postcondition":["selector":["identifier":"counter"],"predicate":"equals","text":"1"]]
        ]]
    }
    @MainActor func testWholePlanRejectsLateUnsafeStepBeforeExecution() throws {
        var value = definition(), steps = value["steps"] as! [[String:Any]]
        steps.append(["action":"shell","text":"not permitted"]); value["steps"] = steps
        XCTAssertThrowsError(try WorkflowDefinition(value))
        steps.removeLast(); steps[1].removeValue(forKey:"postcondition"); value["steps"] = steps
        XCTAssertThrowsError(try WorkflowDefinition(value))
    }
    @MainActor func testParametersStayLiteralAndReferencesAreValidated() throws {
        let plan = try WorkflowDefinition(definition())
        let expected = "한글 😀 $(not executed) `literal`"
        XCTAssertEqual(try plan.steps[0].condition.resolve(["text":expected]).text,expected)
        var bad = definition(); bad["parameters"] = ["other"]
        XCTAssertThrowsError(try WorkflowDefinition(bad))
        XCTAssertThrowsError(try Workflows.name("../outside"))
    }
    @MainActor func testSaveRefusesSilentOverwriteAndRevalidatesStoredDefinition() async throws {
        let parent = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at:parent,withIntermediateDirectories:false)
        defer { try? FileManager.default.removeItem(at:parent) }
        let store = try Store(root:parent.appendingPathComponent("state")), engine = Engine(store:store)
        _ = try await engine.call("mac_workflow",arguments:["operation":"save","definition":definition()])
        do { _ = try await engine.call("mac_workflow",arguments:["operation":"save","definition":definition()]); XCTFail() }
        catch { XCTAssertEqual((error as? ToolFailure)?.code,"workflow_exists") }
        _ = try await engine.call("mac_workflow",arguments:["operation":"save","definition":definition(),"overwrite":true])
        var corrupt = definition(); corrupt["steps"] = [["action":"shell"]]
        try store.write(jsonData(corrupt),to:store.root.appendingPathComponent("workflow-definition-literal_recipe.json"))
        XCTAssertThrowsError(try Workflows.load("literal_recipe",store:store))
    }
}
