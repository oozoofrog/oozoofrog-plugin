import XCTest
@testable import JevComputerUse

@MainActor final class NaturalTaskRunnerTests: XCTestCase {
    private func directory() throws -> URL { let url = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString); try FileManager.default.createDirectory(at:url,withIntermediateDirectories:true); return url }
    private let context = RequestContext(apps:[],windows:[],windowsComplete:true)
    private let app = AppCandidate(bundle:"owned.app",name:"Owned",aliases:[],path:"/owned-fixture",running:true)
    private func outcome(_ request:NaturalRequest,content:ContentIntent = .action,delivery:DeliveryIntent = .app) -> RequestResolution {
        var result = RequestResolution(originalRequest:request.original,status:"resolved",answers:request.answers,content:content)
        result.delivery = delivery
        result.app = request.answers.last(where: { $0.question.field == .app })?.option?.app
        return result
    }
    func testGUIIntentRunsBeforeAppSelectionAndAutomaticGenerationReachesWorkflow() async throws {
        let dir = try directory(); defer { try? FileManager.default.removeItem(at:dir) }
        var order: [String] = []
        let runner = TaskRunner(resolve:{ spec,_,_,_,_,_ in order.append("apps"); XCTAssertTrue(spec.generateText); XCTAssertFalse(spec.inspectImage); return AppResolution(source:"goal",status:"resolved",apps:[self.app.bundle]) },execute:{ spec,dir,_,_,_,_ in
            order.append("execute"); XCTAssertTrue(spec.generateText); XCTAssertTrue(spec.texts.isEmpty); XCTAssertNil(spec.expectText); XCTAssertNil(spec.expectApp)
            return RunReport(status:"jev_observed_complete",goal:spec.goal,steps:[],finalObservation:"",directory:dir)
        },requireCredential:{})
        let natural = NaturalTaskRunner(runner:runner,intent:{ request,_,_,_ in order.append("intent"); return self.outcome(request,content:.generate) },context:{self.context},discover:{AppDiscovery(apps:[self.app],roots:[],elapsedMS:0)},validate:{_,_ in})
        let result = try await natural.run(request:"Owned에 회의 준비 목록을 써줘",directory:dir.path,model:nil,control:RunControl(),followUp:nil)
        XCTAssertEqual(order,["intent","apps","execute"]); XCTAssertEqual(result.requestResolution?.content,.generate)
        XCTAssertEqual(result.requestResolution?.originalRequest,result.goal)
    }
    func testOrdinaryActionNeverEnablesUnusedDelegates() async throws {
        let dir = try directory(); defer { try? FileManager.default.removeItem(at:dir) }
        var executions = 0
        let runner = TaskRunner(resolve:{_,_,_,_,_,_ in AppResolution(source:"goal",status:"resolved",apps:[self.app.bundle]) },execute:{ spec,dir,_,_,_,_ in executions += 1; XCTAssertFalse(spec.generateText); XCTAssertFalse(spec.inspectImage); XCTAssertFalse(spec.sourceTransform); XCTAssertTrue(spec.texts.isEmpty); return RunReport(status:"jev_observed_complete",goal:spec.goal,steps:[],finalObservation:"",directory:dir) },requireCredential:{})
        let natural = NaturalTaskRunner(runner:runner,intent:{ request,_,_,_ in self.outcome(request) },context:{self.context},discover:{AppDiscovery(apps:[self.app],roots:[],elapsedMS:0)},validate:{_,_ in})
        let result = try await natural.run(request:"Owned에서 확인 버튼을 눌러줘",directory:dir.path,model:nil,control:RunControl(),followUp:nil)
        XCTAssertEqual(executions,1); XCTAssertEqual(result.status,"jev_observed_complete")
    }
    func testSourceOnlyTransformationRepliesWithoutAnyAppInputOrSelection() async throws {
        let dir = try directory(); defer { try? FileManager.default.removeItem(at:dir) }
        let original = "열린 회의 메모를 세 줄로 요약해줘. 원문은 바꾸지 마."
        let selected = RequestWindow(id:9,app:app.bundle,appName:app.name,title:"회의 메모")
        let runner = TaskRunner(resolve:{_,_,_,_,_,_ in XCTFail("No destination selection for a UI reply"); return AppResolution(source:"test",status:"error") },execute:{_,dir,_,_,_,_ in XCTFail("No native input"); return RunReport(status:"error",goal:"",steps:[],finalObservation:"",directory:dir) },requireCredential:{})
        let natural = NaturalTaskRunner(runner:runner,intent:{ request,_,_,_ in var result = self.outcome(request,content:.transform,delivery:.ui); result.target = selected; return result },context:{self.context},readSource:{ resolution,_,_ in XCTAssertEqual(resolution.target,selected); return try DocumentSource.supplied("실제 원문\n둘째 줄") },reply:{ resolution,source,dir,_,_ in XCTAssertEqual(source?.text,"실제 원문\n둘째 줄"); XCTAssertEqual(resolution.originalRequest,original); return RunReport(status:"content_delivered",goal:original,steps:[],finalObservation:"",directory:dir,completionSource:"delegate_response",response:"요약") })
        let result = try await natural.run(request:original,directory:dir.path,model:nil,control:RunControl(),followUp:nil)
        XCTAssertEqual(result.status,"content_delivered"); XCTAssertEqual(result.response,"요약"); XCTAssertEqual(result.requestResolution?.target?.id,9)
    }
    func testAppFollowUpFillsOnlyAppAndRetainsOriginalConstraints() async throws {
        let dir = try directory(); defer { try? FileManager.default.removeItem(at:dir) }
        let original = "문구를 입력해줘. 다른 문서는 바꾸지 마."
        var selections = 0, executions = 0, questions = 0
        let runner = TaskRunner(resolve:{ spec,_,_,_,_,_ in selections += 1; if spec.apps.isEmpty { return AppResolution(source:"goal",status:"uncertain") }; return AppResolution(source:"explicit",status:"resolved",apps:spec.apps) },execute:{ spec,dir,_,_,_,_ in executions += 1; XCTAssertEqual(spec.apps,[self.app.bundle]); XCTAssertTrue(spec.goal.hasPrefix(original)); XCTAssertNil(spec.expectText); return RunReport(status:"jev_observed_complete",goal:spec.goal,steps:[],finalObservation:"",directory:dir) },requireCredential:{})
        let natural = NaturalTaskRunner(runner:runner,intent:{ request,_,_,_ in self.outcome(request) },context:{self.context},discover:{AppDiscovery(apps:[self.app],roots:[],elapsedMS:0)},validate:{ ids,_ in XCTAssertEqual(ids,[self.app.bundle]) })
        let result = try await natural.run(request:original,directory:dir.path,model:nil,control:RunControl(),followUp:{ question in questions += 1; XCTAssertEqual(question.field,.app); return RequestAnswer(question:question,option:question.options[0]) })
        XCTAssertEqual(selections,2); XCTAssertEqual(executions,1); XCTAssertEqual(questions,1)
        XCTAssertEqual(result.goal,original); XCTAssertEqual(result.requestResolution?.answers.count,1)
    }
    func testAlteredQuestionOptionsWithSameIDCannotExpandScope() async throws {
        let dir = try directory(); defer { try? FileManager.default.removeItem(at:dir) }
        let question = RequestQuestion(field:.app,prompt:"어느 앱?",options:[RequestOption(id:app.bundle,title:app.name,app:app.bundle)])
        let runner = TaskRunner(resolve:{_,_,_,_,_,_ in XCTFail("No app selection after tampering"); return AppResolution(source:"test",status:"error") },requireCredential:{})
        let natural = NaturalTaskRunner(runner:runner,intent:{ request,_,_,_ in var result = self.outcome(request); result.status="needs_input"; result.question=question; return result },context:{self.context})
        let result = try await natural.run(request:"Owned에서 작업",directory:dir.path,model:nil,control:RunControl(),followUp:{ offered in var changed = offered; let injected = RequestOption(id:"unrelated",title:"Unrelated",app:"unrelated"); changed.options=[injected]; return RequestAnswer(question:changed,option:injected) })
        XCTAssertEqual(result.status,"error"); XCTAssertEqual(result.requestResolution?.answers.count,0)
    }
    func testMissingSourceAsksSourceFieldAndResumesExactSuppliedText() async throws {
        let dir = try directory(); defer { try? FileManager.default.removeItem(at:dir) }
        var reads = 0, asks = 0
        let original = "회의 메모를 요약해줘. 두 문장으로."
        let supplied = "  😀 원문\n둘째 줄  "
        let natural = NaturalTaskRunner(runner:TaskRunner(requireCredential:{}),intent:{ request,_,_,_ in var result = self.outcome(request,content:.transform,delivery:.ui); if let text = request.answers.last?.text { result.transformSource = RequestSpan(id:"source",source:"source_followup",rangeUTF16:AXTextRange(location:0,length:text.utf16.count),text:text) }; return result },context:{self.context},readSource:{ result,_,_ in reads += 1; guard let text = result.transformSource?.text else { throw Failure("Partial source") }; return try DocumentSource.supplied(text) },reply:{ result,source,dir,_,_ in XCTAssertEqual(source?.text,supplied); XCTAssertEqual(result.originalRequest,original); return RunReport(status:"content_delivered",goal:original,steps:[],finalObservation:"",directory:dir,response:"요약") })
        let result = try await natural.run(request:original,directory:dir.path,model:nil,control:RunControl(),followUp:{ question in asks += 1; XCTAssertEqual(question.field,.source); return RequestAnswer(question:question,text:supplied) })
        XCTAssertEqual(result.status,"content_delivered"); XCTAssertEqual(reads,2); XCTAssertEqual(asks,1)
        XCTAssertEqual(result.requestResolution?.transformSource?.text,supplied)
    }
    func testCancellationDuringFollowUpDoesNotConsumeAnswerOrExecute() async throws {
        let dir = try directory(); defer { try? FileManager.default.removeItem(at:dir) }
        let control = RunControl(), question = RequestQuestion(field:.literal,prompt:"문구?",allowsText:true)
        let runner = TaskRunner(resolve:{_,_,_,_,_,_ in XCTFail("No app selection after cancellation"); return AppResolution(source:"test",status:"error") },requireCredential:{})
        let natural = NaturalTaskRunner(runner:runner,intent:{ request,_,_,_ in var result = self.outcome(request); result.status="needs_input"; result.question=question; return result },context:{self.context})
        let result = try await natural.run(request:"문구 입력",directory:dir.path,model:nil,control:control,followUp:{ question in control.stop(); return RequestAnswer(question:question,text:"not applied") })
        XCTAssertEqual(result.status,"cancelled"); XCTAssertTrue(result.requestResolution?.answers.isEmpty == true)
    }
    func testUnsupportedRequestDoesNotResolveAppsOrExecute() async throws {
        let dir = try directory(); defer { try? FileManager.default.removeItem(at:dir) }
        let runner = TaskRunner(resolve:{_,_,_,_,_,_ in XCTFail("No app selection"); return AppResolution(source:"test",status:"error") },requireCredential:{})
        let natural = NaturalTaskRunner(runner:runner,intent:{ request,_,_,_ in var result = self.outcome(request); result.status="unsupported"; return result },context:{self.context})
        let result = try await natural.run(request:"영상 생성",directory:dir.path,model:nil,control:RunControl(),followUp:nil)
        XCTAssertEqual(result.status,"request_unsupported"); XCTAssertTrue(result.steps.isEmpty)
    }
    func testDelegateCancellationStopsWaitingAndAppliesNoResult() async throws {
        let dir = try directory(); defer { try? FileManager.default.removeItem(at:dir) }
        let executable = dir.appendingPathComponent("owned-waiting-delegate")
        try "#!/bin/sh\nwhile :; do :; done\n".write(to:executable,atomically:true,encoding:.utf8)
        try FileManager.default.setAttributes([.posixPermissions:0o700],ofItemAtPath:executable.path)
        let control = RunControl()
        let stop = Task { @MainActor in try await Task.sleep(nanoseconds:50_000_000); control.stop() }
        let start = Date()
        do { _ = try await Codex(executable:executable.path).invoke(goal:"owned",image:nil,directory:dir.path,model:nil,control:control); XCTFail("Expected cancellation") }
        catch { XCTAssertTrue(error is CancellationError) }
        _ = try await stop.value
        XCTAssertLessThan(Date().timeIntervalSince(start),2)
        XCTAssertFalse(FileManager.default.fileExists(atPath:dir.appendingPathComponent("codex-result.json").path))
    }
}
