import XCTest
@testable import JevComputerUse

@MainActor final class RequestIntentTests: XCTestCase {
    private let emptyContext = RequestContext(apps:[],windows:[],windowsComplete:true)
    private func directory() throws -> URL { let url = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString); try FileManager.default.createDirectory(at:url,withIntermediateDirectories:true); return url }
    private func reply(_ body: IntentRequest, choices: [String:String], low: String? = nil) -> AppSelectionReply {
        AppSelectionReply(model:"deterministic-fixture",answers:Dictionary(uniqueKeysWithValues:body.questions.keys.map { key in
            (key,AppSelectionAnswer(type:"choice",choice:choices[key] ?? ["content":"action","vision":"no","readiness":"ready","literal":"none","source":"none","target":"not_required","delivery":"app","writeSource":"no"][key]!,confidence:key == low ? 0.4 : 0.99))
        }),usage:["input_tokens":19,"output_tokens":8])
    }
    private func resolve(_ input:NaturalRequest, context:RequestContext? = nil, choices:[String:String] = [:], low:String? = nil, inspect:((IntentRequest)->Void)? = nil) async throws -> RequestResolution {
        let dir = try directory(); defer { try? FileManager.default.removeItem(at:dir) }
        let resolver = RequestIntentResolver(evaluate:{ body in inspect?(body); return (self.reply(body,choices:choices,low:low),3,700) })
        return try await resolver.resolve(input,context:context ?? emptyContext,directory:dir.path,control:RunControl())
    }
    func testLiteralCopiesOriginalUnicodeWhitespaceAndUTF16Offsets() async throws {
        let payload = "  😀 e\u{301} 한글\n두 번째 줄\t "
        let request = "텍스트 편집기에 \"" + payload + "\"를 그대로 입력해줘"
        let span = try XCTUnwrap(RequestSpans.candidates(in:request).first { $0.text == payload })
        let resolution = try await resolve(NaturalRequest(original:request),choices:["content":"literal","literal":span.id])
        let spec = try resolution.taskSpec()
        XCTAssertEqual(spec.texts,[payload]); XCTAssertEqual(resolution.literal?.rangeUTF16,span.rangeUTF16)
        XCTAssertEqual(try RequestSpans.exact(span,in:request),payload)
        XCTAssertEqual(span.rangeUTF16.length,payload.utf16.count)
        XCTAssertFalse(spec.generateText); XCTAssertFalse(spec.inspectImage); XCTAssertNil(spec.expectText); XCTAssertNil(spec.expectApp)
        XCTAssertEqual(resolution.originalRequest,request)
    }
    func testControlLabelDoesNotBecomePayloadOrInvokeDelegates() async throws {
        let resolution = try await resolve(NaturalRequest(original:"열린 창에서 ‘확인’ 버튼을 눌러줘"))
        let spec = try resolution.taskSpec()
        XCTAssertTrue(spec.texts.isEmpty); XCTAssertFalse(spec.generateText); XCTAssertFalse(spec.inspectImage)
    }
    func testOriginalWritingAndVisualInterpretationAreIndependent() async throws {
        let writing = try await resolve(NaturalRequest(original:"텍스트 편집기에 회의 준비 목록을 새로 써줘"),choices:["content":"generate"])
        XCTAssertTrue(try writing.taskSpec().generateText); XCTAssertFalse(try writing.taskSpec().inspectImage)
        let window = RequestWindow(id:31,app:"owned",appName:"Owned",title:"사진")
        let visual = try await resolve(NaturalRequest(original:"이 사진을 설명해줘"),context:RequestContext(apps:[],windows:[window],windowsComplete:true),choices:["vision":"yes","target":"window_31","delivery":"ui"])
        XCTAssertEqual(visual.delivery,.ui); XCTAssertFalse(try visual.taskSpec().generateText); XCTAssertTrue(try visual.taskSpec().inspectImage)
    }
    func testVisualDescriptionUsesInterpretIntentAndPreservesSelectedWindow() async throws {
        let window = RequestWindow(id:32,app:"owned",appName:"Owned",title:"사진")
        let question = RequestQuestion(field:.target,prompt:"창 선택",options:[RequestOption(id:"window_32",title:"사진",app:"owned",window:32)])
        let answer = RequestAnswer(question:question,option:question.options[0])
        let result = try await resolve(NaturalRequest(original:"그림을 설명해줘",answers:[answer]),context:RequestContext(apps:[],windows:[window],windowsComplete:true),choices:["content":"interpret","vision":"yes","target":"missing","readiness":"target","delivery":"ui"])
        XCTAssertEqual(result.status,"resolved"); XCTAssertEqual(result.target,window)
        XCTAssertEqual(result.content,.interpret); XCTAssertEqual(result.delivery,.ui)
        XCTAssertTrue(try result.taskSpec().inspectImage); XCTAssertFalse(try result.taskSpec().generateText)
        var appWrite = result; appWrite.delivery = .app
        XCTAssertThrowsError(try appWrite.taskSpec())
        let writeRequest = try await resolve(NaturalRequest(original:"화면을 설명해서 다른 앱에 써줘"),context:RequestContext(apps:[],windows:[window],windowsComplete:true),choices:["content":"interpret","vision":"yes","target":"window_32","delivery":"app"])
        XCTAssertEqual(writeRequest.status,"visual_destination_unresolved"); XCTAssertThrowsError(try writeRequest.taskSpec())
    }
    func testVisionAssistedNativeActionRetainsExistingExecutionPath() async throws {
        let window = RequestWindow(id:33,app:"owned",appName:"Owned",title:"캔버스")
        let result = try await resolve(NaturalRequest(original:"화면의 파란 원을 눌러줘"),context:RequestContext(apps:[],windows:[window],windowsComplete:true),choices:["content":"action","vision":"yes","target":"window_33","delivery":"app"])
        XCTAssertEqual(result.status,"resolved"); XCTAssertEqual(result.delivery,.app)
        let spec = try result.taskSpec(); XCTAssertTrue(spec.inspectImage); XCTAssertFalse(spec.generateText)
        XCTAssertEqual(spec.apps,["owned"]); XCTAssertEqual(spec.initialWindowID,33)
    }
    func testVisualReplyRequiresConcreteWindowEvenIfModelSaysNotRequired() async throws {
        let window = RequestWindow(id:32,app:"owned",appName:"Owned",title:"사진")
        let result = try await resolve(NaturalRequest(original:"Owned 화면의 그림을 설명해줘"),context:RequestContext(apps:[],windows:[window],windowsComplete:true),choices:["vision":"yes","target":"not_required","delivery":"ui"])
        XCTAssertEqual(result.status,"needs_input"); XCTAssertEqual(result.question?.field,.target)
        XCTAssertEqual(result.question?.options.first?.window,32)
    }
    func testSourceTransformationDefaultsToUIWithoutInventingWritePermission() async throws {
        let window = RequestWindow(id:41,app:"owned",appName:"Owned",title:"회의 메모")
        let resolution = try await resolve(NaturalRequest(original:"열린 회의 메모를 세 줄로 요약해줘"),context:RequestContext(apps:[],windows:[window],windowsComplete:true),choices:["content":"transform","delivery":"ui","target":"window_41"])
        XCTAssertEqual(resolution.content,.transform); XCTAssertEqual(resolution.delivery,.ui); XCTAssertFalse(resolution.writeSource)
        XCTAssertEqual(resolution.target?.id,41); XCTAssertTrue(try resolution.taskSpec().sourceTransform)
        XCTAssertNil(try resolution.taskSpec().expectText)
    }
    func testAmbiguousDocumentSelectionPreservesOriginalConstraintsAndWindowID() async throws {
        let a = RequestWindow(id:51,app:"owned",appName:"Owned",title:"회의 메모")
        let b = RequestWindow(id:52,app:"owned",appName:"Owned",title:"제안서")
        let context = RequestContext(apps:[],windows:[a,b],windowsComplete:true)
        let original = "열린 문서를 세 줄로 요약해줘. 원문은 바꾸지 마."
        let first = try await resolve(NaturalRequest(original:original),context:context,choices:["content":"transform","delivery":"ui","target":"missing","readiness":"target"])
        let question = try XCTUnwrap(first.question)
        XCTAssertEqual(question.field,.target)
        let answer = RequestAnswer(question:question,option:try XCTUnwrap(question.options.first { $0.window == 52 }))
        let next = try await resolve(NaturalRequest(original:original,answers:[answer]),context:context,choices:["content":"transform","delivery":"ui","target":"window_52"])
        XCTAssertEqual(next.originalRequest,original); XCTAssertEqual(next.target,b)
        XCTAssertTrue(try next.taskSpec().goal.hasPrefix(original)); XCTAssertFalse(next.writeSource)
    }
    func testMissingLiteralFollowUpCopiesWholeAnswerIncludingBoundaryWhitespace() async throws {
        let original = "텍스트 편집기에 내가 준 문구를 그대로 입력해줘"
        let first = try await resolve(NaturalRequest(original:original),choices:["content":"literal"])
        let question = try XCTUnwrap(first.question); XCTAssertEqual(question.field,.literal)
        let payload = "\n 😀 한글  \n"
        let next = try await resolve(NaturalRequest(original:original,answers:[RequestAnswer(question:question,text:payload)]),choices:["content":"literal","literal":"answer_literal"])
        XCTAssertEqual(try next.taskSpec().texts,[payload]); XCTAssertEqual(next.originalRequest,original)
    }
    func testSuppliedSourceIsDistinctFromLiteralOutputAndBrief() async throws {
        let original = "다음 원문을 한 문장으로 요약해줘: ‘매출은 10% 늘었다. 비용은 5% 줄었다.’"
        let span = try XCTUnwrap(RequestSpans.candidates(in:original).first { $0.text == "매출은 10% 늘었다. 비용은 5% 줄었다." })
        let resolution = try await resolve(NaturalRequest(original:original),choices:["content":"transform","delivery":"ui","source":span.id])
        XCTAssertEqual(resolution.transformSource?.text,span.text); XCTAssertTrue(try resolution.taskSpec().texts.isEmpty)
        XCTAssertEqual(try resolution.taskSpec().sourceText,span.text)
    }
    func testUnsupportedAndLowConfidenceDoNotBecomeExecutablePlans() async throws {
        let unsupported = try await resolve(NaturalRequest(original:"이미지를 생성해줘"),choices:["readiness":"unsupported"])
        XCTAssertEqual(unsupported.status,"unsupported"); XCTAssertThrowsError(try unsupported.taskSpec())
        let uncertain = try await resolve(NaturalRequest(original:"그거 해줘"),low:"content")
        XCTAssertEqual(uncertain.status,"needs_input"); XCTAssertNil(uncertain.content); XCTAssertFalse(uncertain.inspectImage)
    }
    func testExplicitNativeActionIsNotAClassifierWideBan() async throws {
        _ = try await resolve(NaturalRequest(original:"내가 지정한 앱에서 내가 지정한 동작을 해줘"),inspect:{ body in
            XCTAssertFalse(body.questions["readiness"]!.instructions.contains("No purchases"))
            XCTAssertTrue(body.questions["readiness"]!.instructions.contains("concretely requested"))
        })
    }
    func testStaleSelectedWindowRequiresFreshFollowUp() async throws {
        let old = RequestOption(id:"window_1",title:"Old",app:"owned",window:1)
        let question = RequestQuestion(field:.target,prompt:"어느 문서?",options:[old])
        let current = RequestWindow(id:2,app:"owned",appName:"Owned",title:"New")
        let result = try await resolve(NaturalRequest(original:"문서를 요약해줘",answers:[RequestAnswer(question:question,option:old)]),context:RequestContext(apps:[],windows:[current],windowsComplete:true),choices:["content":"transform","delivery":"ui"])
        XCTAssertEqual(result.status,"needs_input"); XCTAssertEqual(result.question?.options.first?.window,2); XCTAssertNil(result.target)
    }
    func testCancellationAfterIntentCallPreservesUsageAndPreventsPlan() async throws {
        let dir = try directory(); defer { try? FileManager.default.removeItem(at:dir) }
        let control = RunControl()
        let resolver = RequestIntentResolver(evaluate:{ body in control.stop(); return (self.reply(body,choices:[:]),4,500) })
        let result = try await resolver.resolve(NaturalRequest(original:"버튼을 눌러줘"),context:emptyContext,directory:dir.path,control:control)
        XCTAssertEqual(result.status,"cancelled"); XCTAssertEqual(result.calls.count,1); XCTAssertEqual(result.calls[0].reply.usage["input_tokens"],19)
        XCTAssertThrowsError(try result.taskSpec())
    }
    func testUnusedDestinationUncertaintyDoesNotBlockOrdinaryActionOrLiteral() async throws {
        let action = try await resolve(NaturalRequest(original:"확인 버튼을 눌러줘"),low:"delivery")
        XCTAssertEqual(action.status,"resolved"); XCTAssertEqual(action.delivery,.app)
        let request = "텍스트 편집기에 ‘안녕’을 입력해줘"
        let span = try XCTUnwrap(RequestSpans.candidates(in:request).first { $0.text == "안녕" })
        let literal = try await resolve(NaturalRequest(original:request),choices:["content":"literal","literal":span.id],low:"delivery")
        XCTAssertEqual(literal.status,"resolved"); XCTAssertEqual(try literal.taskSpec().texts,["안녕"])
    }
    func testExplicitCLIOptionsAndPredicatesRemainUnchanged() throws {
        let request = try RunRequest(arguments:["--goal","owned","--apps","owned.app","--text","  literal\n","--generate-text","--inspect-image","--expect-text","EXACT"])
        XCTAssertEqual(request.spec.texts,["  literal\n"]); XCTAssertTrue(request.spec.generateText); XCTAssertTrue(request.spec.inspectImage)
        XCTAssertEqual(request.spec.expectText,"EXACT"); XCTAssertEqual(request.spec.apps,["owned.app"])
        XCTAssertFalse(request.spec.sourceTransform); XCTAssertNil(request.spec.initialWindowID)
        XCTAssertTrue(try GUIOptions(arguments:["--gui","--simple"]).chooseApps)
    }
    func testVisualEvidencePrecedesWritingAndCannotCompleteBeforeTextInput() {
        let workflow = Workflow()
        let observation = Observation(id:"owned",timestamp:Date(),front:nil,apps:[],nodes:[],displays:[],truncated:false,axError:nil,elapsedMS:0,target:AppInfo(pid:1,bundle:"owned",name:"Owned"))
        let spec = TaskSpec(goal:"describe image in app",apps:["owned"],generateText:true,inspectImage:true)
        let before = workflow.candidates(spec,observation,texts:[],generated:false,inspected:false,extra:[])
        XCTAssertTrue(before.contains { $0.id == "delegateVision" })
        XCTAssertFalse(before.contains { $0.id == "delegateText" })
        let inspected = workflow.candidates(spec,observation,texts:[],generated:false,inspected:true,extra:[])
        XCTAssertTrue(inspected.contains { $0.id == "delegateText" })
        XCTAssertFalse(inspected.contains { $0.id == "done" })
        let pending = workflow.candidates(spec,observation,texts:["description"],generated:true,inspected:true,extra:[])
        XCTAssertFalse(pending.contains { $0.id == "done" })
    }
    func testDoneIsUnavailableUntilSuppliedOrGeneratedTextWasApplied() {
        let workflow = Workflow()
        let observation = Observation(id:"owned",timestamp:Date(),front:nil,apps:[],nodes:[],displays:[],truncated:false,axError:nil,elapsedMS:0,target:AppInfo(pid:1,bundle:"owned",name:"Owned"))
        for generated in [false,true] {
            let spec = TaskSpec(goal:"write",apps:["owned"],generateText:generated)
            let pending = workflow.candidates(spec,observation,texts:["not yet typed"],generated:generated,inspected:false,extra:[])
            XCTAssertFalse(pending.contains { $0.id == "done" })
            let applied = workflow.candidates(spec,observation,texts:[],generated:generated,inspected:false,extra:[])
            XCTAssertTrue(applied.contains { $0.id == "done" })
        }
    }
    func testSourceReadOnlyGuardBlocksWritesButAllowsNewDestination() throws {
        XCTAssertThrowsError(try validateProtectedSourceAction(Action(kind:"type",text:"summary"),observedWindow:7,protectedWindow:7))
        XCTAssertThrowsError(try validateProtectedSourceAction(Action(kind:"key",key:"v",modifiers:["cmd"]),observedWindow:7,protectedWindow:7))
        XCTAssertNoThrow(try validateProtectedSourceAction(Action(kind:"key",key:"n",modifiers:["cmd"]),observedWindow:7,protectedWindow:7))
        XCTAssertNoThrow(try validateProtectedSourceAction(Action(kind:"type",text:"summary"),observedWindow:8,protectedWindow:7))
        XCTAssertNoThrow(try validateProtectedSourceAction(Action(kind:"type",text:"summary"),observedWindow:7,protectedWindow:nil))
    }
}
