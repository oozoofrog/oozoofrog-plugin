import XCTest
@testable import JevComputerUse

final class TaskRunnerTests: XCTestCase {
    func testGUIOptionsKeepExplicitSettingsAndRejectIgnoredScopes() throws {
        let options = try GUIOptions(arguments:["--gui","--goal","owned","--simple","--no-preview","--codex-model","chosen-model"])
        XCTAssertEqual(options.goal,"owned"); XCTAssertTrue(options.chooseApps); XCTAssertFalse(options.showPreview); XCTAssertEqual(options.model,"chosen-model")
        for args in [["--gui","--simple","--auto"],["--gui","--apps","owned"],["--gui","--codex-model"],["--gui","--unknown"]] { XCTAssertThrowsError(try GUIOptions(arguments:args)) }
        XCTAssertEqual(try GUIOptions(arguments:["--gui"]).goal,"")
    }
    private func directory() throws -> URL {
        let url = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at:url,withIntermediateDirectories:true); return url
    }
    @MainActor func testDuplicateRunStopAndSubsequentRun() async throws {
        let session = RunSession(); var resume: CheckedContinuation<Void,Never>?
        let first = try session.start(status:{_ in}) { control in
            await withCheckedContinuation { resume = $0 }
            return RunReport(status:control.isCancelled ? "cancelled" : "verified_complete",goal:"owned",steps:[],finalObservation:"",directory:"fixture")
        }
        while resume == nil { await Task.yield() }
        XCTAssertTrue(session.active)
        XCTAssertThrowsError(try session.start(status:{_ in}) {_ in XCTFail("Duplicate run executed"); throw Failure("duplicate") })
        session.stop(); XCTAssertTrue(session.control?.isCancelled == true)
        resume?.resume(); await first.value
        XCTAssertFalse(session.active); XCTAssertEqual(session.report?.status,"cancelled")
        let next = try session.start(status:{_ in}) { control in
            XCTAssertFalse(control.isCancelled)
            return RunReport(status:"verified_complete",goal:"next",steps:[],finalObservation:"",directory:"fixture")
        }
        await next.value; XCTAssertEqual(session.report?.goal,"next"); XCTAssertFalse(session.active)
    }
    @MainActor func testCancellationAfterSelectionNeverStartsWorkflowAndWritesReport() async throws {
        let dir = try directory(); defer { try? FileManager.default.removeItem(at:dir) }
        var executed = false
        let runner = TaskRunner(resolve:{_,_,_,_,control,_ in control.stop(); return AppResolution(source:"goal",status:"resolved",apps:["owned"]) },execute:{_,_,_,_,_,_ in executed = true; throw Failure("must not execute") },requireCredential:{})
        let report = try await runner.run(request:RunRequest(arguments:["--goal","owned","--auto"]),directory:dir.path,model:nil,control:RunControl())
        XCTAssertFalse(executed); XCTAssertEqual(report.status,"cancelled"); XCTAssertTrue(report.steps.isEmpty)
        let saved = try JSONDecoder().decode(RunReport.self,from:Data(contentsOf:dir.appendingPathComponent("report.json")))
        XCTAssertEqual(saved.status,"cancelled"); XCTAssertEqual(saved.appSelection?.apps,["owned"])
    }
    @MainActor func testCredentialFailureDoesNotPromptOrSelect() async throws {
        let dir = try directory(); defer { try? FileManager.default.removeItem(at:dir) }
        try writeJSON([Step(index:99,observation:"previous")],dir.path + "/steps.json")
        let runner = TaskRunner(resolve:{_,_,_,_,_,_ in XCTFail("Must not select without credential"); return AppResolution(source:"goal",status:"error") },requireCredential:{throw Failure("Missing key: use GUI buttons")})
        let report = try await runner.run(request:RunRequest(arguments:["--goal","owned","--auto"]),directory:dir.path,model:nil,control:RunControl())
        XCTAssertEqual(report.status,"error"); XCTAssertTrue(report.error?.contains("Missing key") == true); XCTAssertTrue(report.steps.isEmpty)
    }
    @MainActor func testNativeGUISelectionWorksWithoutTTYAndRevalidatesOrder() async throws {
        let dir = try directory(); defer { try? FileManager.default.removeItem(at:dir) }
        let apps = [AppCandidate(bundle:"owned.a",name:"A",aliases:[],path:"/fixture",running:false),AppCandidate(bundle:"owned.b",name:"B",aliases:[],path:"/fixture",running:false)]
        var validated: [String] = []
        let resolver = AppResolver(discover:{AppDiscovery(apps:apps,roots:[],elapsedMS:0)},validate:{ids,_ in validated = ids},evaluate:{_ in XCTFail("GUI picker must not call JEV"); throw Failure("API")},picker:AppPickerIO(interactive:false,read:{XCTFail("GUI must not read stdin"); return nil},write:{_ in XCTFail("GUI must not print terminal list")}))
        let report = await resolver.resolve(spec:TaskSpec(goal:"owned"),simple:true,allowFallback:false,directory:dir.path,selection:{ candidates in XCTAssertEqual(candidates.count,2); return ["owned.b","owned.a"] })
        XCTAssertEqual(report.status,"resolved"); XCTAssertEqual(validated,["owned.b","owned.a"]); XCTAssertEqual(report.apps,validated)
        resolver.validate = {_,_ in throw Failure("App disappeared") }
        let stale = await resolver.resolve(spec:TaskSpec(goal:"owned"),simple:true,allowFallback:false,directory:dir.path,selection:{_ in ["owned.a"]})
        XCTAssertEqual(stale.status,"error"); XCTAssertTrue(stale.apps.isEmpty)
    }
    @MainActor func testCancellationDuringAppAPIPreservesCallAndDoesNotRepeat() async throws {
        let dir = try directory(); defer { try? FileManager.default.removeItem(at:dir) }
        let control = RunControl(); var calls = 0
        let app = AppCandidate(bundle:"owned",name:"Owned",aliases:[],path:"/fixture",running:false)
        let resolver = AppResolver(discover:{AppDiscovery(apps:[app],roots:[],elapsedMS:0)},validate:{_,_ in XCTFail("No validation after cancellation")},evaluate:{_ in calls += 1; control.stop(); return (AppSelectionReply(model:"test",answers:["next":AppSelectionAnswer(type:"choice",choice:"app_0",confidence:1)],usage:[:]),1)},picker:AppPickerIO(interactive:false,read:{nil},write:{_ in}))
        let result = await resolver.resolve(spec:TaskSpec(goal:"Owned"),simple:false,allowFallback:false,directory:dir.path,control:control)
        XCTAssertEqual(result.status,"cancelled"); XCTAssertEqual(calls,1); XCTAssertEqual(result.calls.count,1); XCTAssertTrue(result.apps.isEmpty)
    }
    @MainActor func testWorkflowStopsAfterDecisionOrFreshObservationBeforeInput() async throws {
        for boundary in ["decision","fresh"] {
            let dir = try directory(); defer { try? FileManager.default.removeItem(at:dir) }
            let control = RunControl(), workflow = Workflow(); var observed = 0, inputs = 0
            let observation = Observation(id:"owned",timestamp:Date(),front:nil,apps:[],nodes:[],displays:[],truncated:false,axError:nil,elapsedMS:0,target:AppInfo(pid:1,bundle:"owned",name:"Owned"))
            workflow.observeOverride = {_,_ in observed += 1; if boundary == "fresh" && observed == 2 { control.stop() }; return observation }
            workflow.decideOverride = {_,_,candidates,_,_ in
                if boundary == "decision" { control.stop() }
                let choice = try XCTUnwrap(candidates.first { $0.action?.kind == "key" && $0.action?.key == "return" })
                return Decision(choice:choice.id,confidence:1,apiMS:1,localMS:0,model:"test",usage:[:],response:"")
            }
            workflow.performOverride = {_,_,_ in inputs += 1 }
            let report = try await workflow.run(spec:TaskSpec(goal:"owned",apps:["owned"]),directory:dir.path,model:nil,control:control)
            XCTAssertEqual(inputs,0,boundary); XCTAssertEqual(report.status,"cancelled",boundary)
            XCTAssertEqual(report.steps.count,1); XCTAssertNil(report.steps[0].action)
        }
    }
}
