import XCTest
@testable import JevComputerUse

final class ExplicitCompletionTests:XCTestCase {
    func observation(_ text:String="result=right",app:String="owned.fixture") -> Observation {
        let target=AppInfo(pid:123,bundle:app,name:"Owned")
        return Observation(id:"owned",timestamp:Date(),front:target,apps:[target],nodes:[Node(id:"result",role:"AXStaticText",title:"Fixture result",value:text,enabled:true,actions:[],frame:nil)],displays:[],truncated:false,axError:nil,elapsedMS:0,target:target)
    }
    func testAllDeclaredConditionsAndDelegateGates() {
        var spec=TaskSpec(goal:"Owned",apps:["owned.fixture"],generateText:true,inspectImage:true,expectText:"result=right",expectApp:"owned.fixture")
        XCTAssertFalse(explicitCompletion(spec,observation:observation(),pendingTexts:[],generated:false,inspected:true))
        XCTAssertFalse(explicitCompletion(spec,observation:observation(),pendingTexts:[],generated:true,inspected:false))
        XCTAssertFalse(explicitCompletion(spec,observation:observation(),pendingTexts:["pending"],generated:true,inspected:true))
        XCTAssertFalse(explicitCompletion(spec,observation:observation("result=left"),pendingTexts:[],generated:true,inspected:true))
        XCTAssertFalse(explicitCompletion(spec,observation:observation(app:"other.fixture"),pendingTexts:[],generated:true,inspected:true))
        XCTAssertTrue(explicitCompletion(spec,observation:observation(),pendingTexts:[],generated:true,inspected:true))
        spec.expectText=nil;spec.expectApp=nil
        XCTAssertFalse(explicitCompletion(spec,observation:observation(),pendingTexts:[],generated:true,inspected:true))
    }
    @MainActor func testFreshObservedPredicateCompletesWithoutModelRejudgment()async throws {
        let workflow=Workflow();var mutated=false,decisions=0
        workflow.observeOverride={_,_ in self.observation(mutated ? "result=right" : "result=idle") }
        workflow.decideOverride={_,_,candidates,_,_ in
            decisions += 1
            let action=try XCTUnwrap(candidates.first {$0.action?.kind=="key" && $0.action?.key=="return"})
            return Decision(choice:action.id,confidence:1,apiMS:0,localMS:0,model:"test",usage:[:],response:"{}")
        }
        workflow.performOverride={_,_,_ in mutated=true }
        let directory=FileManager.default.temporaryDirectory.appendingPathComponent("jev-completion-"+UUID().uuidString)
        defer { try? FileManager.default.removeItem(at:directory) }
        let report=try await workflow.run(spec:TaskSpec(goal:"Owned right",apps:["owned.fixture"],maxSteps:2,settleMS:0,expectText:"result=right",expectApp:"owned.fixture"),directory:directory.path,model:nil)
        XCTAssertEqual(report.status,"verified_complete");XCTAssertEqual(report.completionSource,"explicit_postconditions");XCTAssertEqual(decisions,1);XCTAssertNotNil(report.steps.last?.afterObservation)
        let final=try JSONDecoder().decode(Observation.self,from:Data(contentsOf:URL(fileURLWithPath:report.finalObservation)))
        XCTAssertEqual(final.nodes.first?.value,"result=right")
    }
    func testModalStateChangesInvalidateFullObservationGuard() {
        var a=observation(),b=a;a.axModalStamps=[];b.axModalStamps=[AXModalStamp(role:"AXSheet",title:"Owned",frame:nil)]
        XCTAssertFalse(stableTargetState(a,b))
    }
}
