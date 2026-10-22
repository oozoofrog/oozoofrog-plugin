import XCTest
@testable import JevComputerUse

final class CoreTests: XCTestCase {
    func testCredentialPrecedenceAndRuntimeReload() throws {
        let dir = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: dir) }
        let file = dir.appendingPathComponent(".typesafeai")
        try "first\n".write(to: file, atomically: true, encoding: .utf8)
        XCTAssertEqual(try credential(environment: ["TYPESAFE_API_KEY":"override"], home: dir.path), "override")
        XCTAssertEqual(try credential(environment: ["TYPESAFE_API_KEY":" "], home: dir.path), "first")
        try "second".write(to: file, atomically: true, encoding: .utf8)
        XCTAssertEqual(try credential(environment: [:], home: dir.path), "second")
        try "".write(to: file, atomically: true, encoding: .utf8)
        XCTAssertThrowsError(try credential(environment: [:], home: dir.path))
    }
    func testRejectsOutOfScopeAndUnusableActions() throws {
        XCTAssertThrowsError(try validateAction(Action(kind: "shell", text: "touch /tmp/x"), apps: ["owned"]))
        XCTAssertThrowsError(try validateAction(Action(kind: "launch", app: "unrelated"), apps: ["owned"]))
        XCTAssertThrowsError(try validateAction(Action(kind: "click", x: .nan, y: 1), apps: ["owned"]))
        XCTAssertThrowsError(try validateAction(Action(kind: "drag", x: 1, y: 1), apps: ["owned"]))
        XCTAssertThrowsError(try validateAction(Action(kind: "press"), apps: ["owned"]))
        XCTAssertNoThrow(try validateAction(Action(kind: "launch", app: "owned"), apps: ["owned"]))
    }
    @MainActor func testCandidateCoverageWithUnrelatedForeground() throws {
        let obs = Observation(id: "test", timestamp: Date(), front: AppInfo(pid: 1, bundle: "unrelated", name: "Other"), apps: [], nodes: [], displays: [], truncated: false, elapsedMS: 0)
        let spec = TaskSpec(goal: "Write a greeting", apps: ["owned"], generateText: true)
        let choices = Workflow().candidates(spec, obs, texts: ["hello"], generated: false, inspected: false, extra: [])
        XCTAssertTrue(choices.contains { $0.id == "delegateText" })
        XCTAssertTrue(choices.contains { $0.action?.app == "owned" })
        XCTAssertFalse(choices.contains { $0.action?.kind == "type" })
    }
}

final class StateTests: XCTestCase {
    func testMinimalTaskDefaults() throws {
        let task=try JSONDecoder().decode(TaskSpec.self,from:Data(#"{"goal":"observe","apps":["owned"]}"#.utf8))
        XCTAssertEqual(task.confidence,0.55); XCTAssertEqual(task.maxSteps,30); XCTAssertFalse(task.generateText)
    }
    func testStateGuardIgnoresDecorationButRejectsValueChange() {
        let node=Node(id:"w.0",role:"AXTextArea",title:"",value:"before",enabled:true,actions:[],frame:nil)
        let a=Observation(id:"a",timestamp:Date(),apps:[],nodes:[node],displays:[],truncated:false,elapsedMS:0)
        var b=a; b.nodes.append(Node(id:"w.1",role:"AXGroup",title:"",value:"",enabled:true,actions:[],frame:nil))
        XCTAssertTrue(stableTargetState(a,b))
        b.nodes[0].value="after"; XCTAssertFalse(stableTargetState(a,b))
    }
    @MainActor func testRequiredDelegateCannotBeSkipped() {
        let obs=Observation(id:"a",timestamp:Date(),apps:[],nodes:[],displays:[],truncated:false,elapsedMS:0)
        let spec=TaskSpec(goal:"inspect",apps:["owned"],inspectImage:true)
        let choices=Workflow().candidates(spec,obs,texts:[],generated:false,inspected:false,extra:[])
        XCTAssertFalse(choices.contains { $0.id=="done" }); XCTAssertTrue(choices.contains { $0.id=="delegateVision" })
    }
}
