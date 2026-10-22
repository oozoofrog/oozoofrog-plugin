import AppKit
import XCTest
@testable import JevComputerUse

final class RunPresentationTests: XCTestCase {
    func testStaleAndOutOfOrderEventsCannotReplaceCurrentContent() {
        let first = UUID(), second = UUID(); var state = RunPresentationState()
        state.apply(.init(runID:first,sequence:0,fact:.request("first")))
        state.apply(.init(runID:first,sequence:2,fact:.source("complete source","owned")))
        state.apply(.init(runID:first,sequence:1,fact:.result("out of order")))
        XCTAssertEqual(state.source,"complete source"); XCTAssertTrue(state.result.isEmpty)
        state.apply(.init(runID:second,sequence:0,fact:.request("second")))
        state.apply(.init(runID:first,sequence:3,fact:.result("stale")))
        state.apply(.init(runID:first,sequence:0,fact:.request("stale restart")))
        XCTAssertEqual(state.request,"second"); XCTAssertTrue(state.source.isEmpty); XCTAssertTrue(state.result.isEmpty)
    }
    func testOnlyActualInputAndWholeDocumentProvenanceAreRecorded() {
        let id = UUID(); var state = RunPresentationState()
        for (sequence,fact) in [RunPresentationEvent.Fact.request("summarize"),.source("all source","owned"),.action("press"),.result("actual delegate answer"),.outcome("uncertain")].enumerated() {
            state.apply(.init(runID:id,sequence:sequence,fact:fact))
        }
        XCTAssertEqual(state.inputs,0); XCTAssertTrue(state.hasDocumentProvenance)
        XCTAssertEqual(state.result,"actual delegate answer"); XCTAssertEqual(state.outcome,"uncertain")
        XCTAssertEqual(state.history.count,state.historyFocus.count)
        state.apply(.init(runID:id,sequence:5,fact:.input("press"))); XCTAssertEqual(state.inputs,1)
    }
    func testSingleClockFreezePreservesVelocityAndPosition() {
        var motion = SpatialMotion(); motion.target = 1
        for _ in 0..<12 { motion.advance(0.016,reducedMotion:false) }
        motion.frozen = true; let time = motion.time, focus = motion.focus, velocity = motion.velocity
        for _ in 0..<200 { motion.advance(0.016,reducedMotion:false) }
        XCTAssertEqual(motion.time,time); XCTAssertEqual(motion.focus,focus); XCTAssertEqual(motion.velocity,velocity)
        motion.frozen = false; motion.advance(0.016,reducedMotion:false)
        XCTAssertGreaterThan(motion.time,time); XCTAssertGreaterThan(motion.focus,focus)
        motion.advance(0.016,reducedMotion:true); XCTAssertEqual(motion.focus,1)
    }
    @MainActor func testPaginationPreservesEntireUnicodeSourceAndResult() {
        let original = String(repeating:"원문 👨‍👩‍👧‍👦 e\u{301} 🐸\n",count:150)
        let pages = SpatialWorkspace.pages(original)
        XCTAssertGreaterThan(pages.count,1); XCTAssertEqual(pages.joined(),original)
        XCTAssertTrue(SpatialWorkspace.pages("").isEmpty)
        XCTAssertEqual(SpatialWorkspace.pages("last line").joined(),"last line")
    }
    @MainActor func testReadabilityPagesFitAtDefaultAndMinimumWindowFontSizes() {
        let text = String(repeating:"가독성을 검토합니다. 한글과 English, 👨‍👩‍👧‍👦 e\u{301}를 보존합니다.\n\n",count:12)
        for size:CGFloat in [19,25,29] {
            let font = NSFont.systemFont(ofSize:size,weight:.medium)
            let pages = SpatialWorkspace.pages(text,font:font)
            XCTAssertEqual(pages.joined(),text)
            for page in pages {
                let (storage,layout,container) = SpatialWorkspace.textLayout(page,font:font,size:CGSize(width:295,height:193))
                XCTAssertEqual(layout.glyphRange(for:container).length,layout.numberOfGlyphs)
                XCTAssertLessThanOrEqual(layout.usedRect(for:container).maxY,193)
                withExtendedLifetime(storage) {}
            }
        }
    }
    @MainActor func testPauseResumeBlocksEffectsAtBoundary() async throws {
        let control = RunControl(); var effects = [String]()
        control.requestPause()
        let task = Task { @MainActor in try await control.checkpoint(); effects.append("input") }
        while !control.isPaused { await Task.yield() }
        XCTAssertTrue(effects.isEmpty); XCTAssertTrue(control.pauseRequested)
        control.resume(); try await task.value
        XCTAssertEqual(effects,["input"]); XCTAssertFalse(control.isPaused)
    }
    @MainActor func testStopAndTaskCancellationReleasePausedContinuationOnce() async throws {
        for cancelTask in [false,true] {
            let control = RunControl(); control.requestPause(); var input = false
            let task = Task { @MainActor in try await control.checkpoint(); input = true }
            while !control.isPaused { await Task.yield() }
            if cancelTask { task.cancel() } else { control.stop(); control.stop() }
            do { try await task.value; XCTFail("Must throw cancellation") } catch { XCTAssertTrue(error is CancellationError) }
            control.resume(); XCTAssertFalse(input)
        }
    }
    @MainActor func testWorkflowRevalidatesAfterPauseBeforeNativeInput() async throws {
        let path = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at:path) }
        let control = RunControl(), workflow = Workflow(); var observations = 0, input = 0
        let observation = Observation(id:"owned",timestamp:Date(),front:nil,apps:[],nodes:[],displays:[],truncated:false,axError:nil,elapsedMS:0,target:AppInfo(pid:1,bundle:"owned",name:"Owned"))
        workflow.observeOverride = { _,_ in observations += 1; return observation }
        workflow.decideOverride = { _,_,choices,_,_ in
            control.requestPause()
            let choice = try XCTUnwrap(choices.first { $0.action?.kind == "key" && $0.action?.key == "return" })
            return Decision(choice:choice.id,confidence:1,apiMS:0,localMS:0,model:"fixture",usage:[:],response:"")
        }
        workflow.performOverride = { _,_,_ in XCTAssertGreaterThanOrEqual(observations,2); input += 1 }
        var spec = TaskSpec(goal:"owned",apps:["owned"]); spec.maxSteps = 1; spec.settleMS = 0
        let task = Task { @MainActor in try await workflow.run(spec:spec,directory:path.path,model:nil,control:control) }
        while !control.isPaused { await Task.yield() }
        XCTAssertEqual(input,0); XCTAssertEqual(observations,1)
        control.resume(); _ = try await task.value; XCTAssertEqual(input,1)
    }
    @MainActor func testPauseDuringFreshObservationRequiresAnotherFreshObservation() async throws {
        let path = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at:path) }
        let control = RunControl(), workflow = Workflow(); var observations = 0, inputs = 0
        let original = Observation(id:"owned",timestamp:Date(),front:nil,apps:[],nodes:[],displays:[],truncated:false,axError:nil,elapsedMS:0,target:AppInfo(pid:1,bundle:"owned",name:"Owned"))
        workflow.observeOverride = { _,_ in
            observations += 1
            if observations == 2 { control.requestPause() }
            var value = original
            if observations >= 3 { value.target = AppInfo(pid:2,bundle:"owned",name:"Changed") }
            return value
        }
        workflow.decideOverride = { _,_,choices,_,_ in
            let choice = try XCTUnwrap(choices.first { $0.action?.kind == "key" && $0.action?.key == "return" })
            return Decision(choice:choice.id,confidence:1,apiMS:0,localMS:0,model:"fixture",usage:[:],response:"")
        }
        workflow.performOverride = { _,_,_ in inputs += 1 }
        var spec = TaskSpec(goal:"owned",apps:["owned"]); spec.maxSteps = 1; spec.settleMS = 0
        let task = Task { @MainActor in try await workflow.run(spec:spec,directory:path.path,model:nil,control:control) }
        while !control.isPaused { await Task.yield() }
        XCTAssertEqual(observations,2); XCTAssertEqual(inputs,0)
        control.resume(); let report = try await task.value
        XCTAssertEqual(observations,3); XCTAssertEqual(inputs,0)
        XCTAssertTrue(report.steps.first?.error?.contains("Target UI changed") == true)
    }
}
