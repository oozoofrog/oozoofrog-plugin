import XCTest
@testable import JevComputerUse

@MainActor final class FakeAX: AXSource {
    var metrics=AXMetrics()
    var records: [String:Node]=[:], edges:[String:[String]]=[:], failed:Set<String>=[]
    var textReads=0
    var parents:[String:String]=[:]
    func nativeParent(_ ref:String)->String? { parents[ref] }
    init(count:Int=5) {
        records["root"]=Node(id:"root",role:"AXWindow",title:"Owned",value:"",enabled:true,actions:[],frame:nil)
        edges["root"]=(0..<count).map { "n\($0)" }
        for id in edges["root"]! { records[id]=Node(id:id,role:"AXButton",title:id,value:"",enabled:true,actions:["AXPress"],frame:nil) }
    }
    func metadata(_ ref:String)->Node? { metrics.batchCalls += 1; return failed.contains(ref) ? nil : records[ref] }
    func childCount(_ ref:String)->Int? { metrics.childCountCalls += 1; return failed.contains(ref) ? nil : (edges[ref]?.count ?? 0) }
    func children(_ ref:String,offset:Int,count:Int)->[String]? { metrics.childPageCalls += 1; return failed.contains(ref) ? nil : Array((edges[ref] ?? []).dropFirst(offset).prefix(count)) }
    func text(_ ref:String,range:AXTextRange?)throws->String { textReads += 1; let value=records[ref]?.value ?? ""; if let r=range { let utf16=Array(value.utf16); guard r.location <= utf16.count, r.length <= utf16.count-r.location else { throw Failure("Range out of bounds") }; return String(decoding:utf16[r.location..<r.location+r.length],as:UTF16.self) }; return value }
    func selectedText(_ ref:String)->String { "selected" }
}

final class AXStoreTests:XCTestCase {
    @MainActor func testTailBeyond600IsReachableWithoutFalseNoMatch()throws {
        let source=FakeAX(count:720),store=AXStore(source:source)
        store.begin(roots:[("root","w")],budget:40)
        let missing=try store.find(AXFilter(nameContains:"n719"))
        XCTAssertTrue(missing.nodes.isEmpty); XCTAssertEqual(missing.coverage,.partial)
        XCTAssertLessThan(source.metrics.batchCalls,50)
        while store.overview().coverage == .partial { _ = try store.expand(nil,budget:120) }
        XCTAssertEqual(try store.find(AXFilter(nameContains:"n719")).nodes.count,1)
        XCTAssertEqual(store.overview().coverage,.complete)
    }
    @MainActor func testCursorRejectsDifferentFilterParentAndRevision()throws {
        let source=FakeAX(),store=AXStore(source:source); store.begin(roots:[("root","w")])
        let cursor=try XCTUnwrap(store.find(AXFilter(role:"AXButton"),limit:1).cursor)
        XCTAssertThrowsError(try store.find(AXFilter(nameContains:"n"),cursor:cursor))
        let root=try XCTUnwrap(store.nodes.first { $0.role == "AXWindow" }?.id)
        XCTAssertThrowsError(try store.children(root,cursor:cursor))
        XCTAssertEqual(try store.find(AXFilter(role:"AXButton"),cursor:cursor,limit:1).nodes.first?.title,"n1")
        let childrenCursor=try XCTUnwrap(store.children(root,limit:1).cursor)
        let child=try XCTUnwrap(store.nodes.first { $0.title == "n0" }?.id)
        XCTAssertThrowsError(try store.children(child,cursor:childrenCursor))
        store.begin(roots:[("root","w")]); XCTAssertThrowsError(try store.find(AXFilter(role:"AXButton"),cursor:cursor))
    }
    @MainActor func testSecureSubtreeExcludedWithoutUnknownCoverage()throws {
        let source=FakeAX(count:2); source.records["n0"]?.subrole="AXSecureTextField"; source.records["n0"]?.value="secret"; source.edges["n0"]=["n1"]
        let store=AXStore(source:source);store.begin(roots:[("root","w")])
        XCTAssertFalse(store.nodes.contains { $0.subrole == "AXSecureTextField" || $0.value == "secret" }); XCTAssertEqual(store.overview().coverage,.complete)
    }
    @MainActor func testSameLabelsKeepAncestryAndStatus()throws {
        let source=FakeAX(count:2);source.records["n0"]?.role="AXGroup";source.records["n0"]?.title="Left";source.records["n1"]?.role="AXGroup";source.records["n1"]?.title="Right"
        for id in ["l","r"] { source.records[id]=Node(id:id,role:"AXButton",title:"Apply",value:"",enabled:true,actions:["AXPress"],frame:nil,selected:id=="r",checked:id=="r") }
        source.edges["n0"]=["l"];source.edges["n1"]=["r"]
        let store=AXStore(source:source);store.begin(roots:[("root","w")])
        let right=try store.find(AXFilter(nameContains:"Apply",selected:true,checked:true,ancestorContains:"Right"))
        XCTAssertEqual(right.nodes.count,1);XCTAssertEqual(right.nodes[0].ancestors?.last,"Right")
    }
    @MainActor func testUTF16RangeIsLazyAndExact()throws {
        let source=FakeAX(count:1);source.records["n0"]?.role="AXTextArea";source.records["n0"]?.value="A😀한B"
        let store=AXStore(source:source);store.begin(roots:[("root","w")]);XCTAssertEqual(source.textReads,0)
        let handle=try XCTUnwrap(store.nodes.first {$0.role=="AXTextArea"}?.id)
        XCTAssertEqual(try store.read(handle,fields:[.value],textRangeUTF16:AXTextRange(location:1,length:3)).value,"😀한")
        XCTAssertThrowsError(try store.read(handle,fields:[.value],textRangeUTF16:AXTextRange(location:-1,length:2)))
        XCTAssertThrowsError(try store.read(handle,fields:[.value],textRangeUTF16:AXTextRange(location:20,length:1)))
    }
    @MainActor func testPartialInvalidationExpiresHandlesAndRetainsUnrelatedRefs()throws {
        let source=FakeAX(count:4),store=AXStore(source:source);store.begin(roots:[("root","w")])
        let revision=store.revision,old=store.nodes.first {$0.title=="n2"}!.id;let reads=source.metrics.batchCalls
        store.invalidate(ref:"n1");XCTAssertNotEqual(store.revision,revision);XCTAssertThrowsError(try store.read(old,fields:[.metadata]))
        source.records["n1"]?.title="updated"; _ = try store.expand(nil)
        XCTAssertEqual(source.metrics.batchCalls-reads,1);XCTAssertTrue(store.nodes.contains {$0.title=="updated"});XCTAssertEqual(store.changes(sinceRevision:revision).changed,["w.1"])
        store.begin(roots:[("root","w")]);XCTAssertTrue(store.changes(sinceRevision:revision).changed.isEmpty)
    }
    @MainActor func testUnknownAndRootInvalidationForceRefresh()throws {
        for ref:String? in [nil,"not-loaded","root"] { let store=AXStore(source:FakeAX());store.begin(roots:[("root","w")]);let old=store.nodes[0].id,revision=store.revision;store.invalidate(ref:ref);XCTAssertTrue(store.requiresRefresh);XCTAssertNotEqual(store.revision,revision);XCTAssertTrue(store.nodes.isEmpty);XCTAssertThrowsError(try store.read(old,fields:[.metadata]));XCTAssertEqual(store.overview().coverage,.unknown) }
    }
    @MainActor func testSourceFailureDoesNotProveAbsence()throws {
        let source=FakeAX();source.failed.insert("n2");let store=AXStore(source:source);store.begin(roots:[("root","w")]);XCTAssertEqual(try store.find(AXFilter(nameContains:"n2")).coverage,.unknown)
    }
    @MainActor func testCandidatePagingIncludesEveryTailAction()throws {
        let workflow=Workflow(),source=FakeAX(count:720),store=AXStore(source:source);store.begin(roots:[("root","w")],budget:1024)
        workflow.native.axStore=store
        let app=AppInfo(pid:123,bundle:"owned.fixture",name:"Owned")
        let obs=Observation(id:"owned",timestamp:Date(),front:app,apps:[app],nodes:store.nodes,displays:[],truncated:false,axError:nil,elapsedMS:0,target:app,axOverview:store.overview())
        let spec=TaskSpec(goal:"Press n719",apps:[app.bundle]);var targets=Set<String>()
        for page in 0..<8 { workflow.native.candidatePage=page;let choices=workflow.candidates(spec,obs,texts:[],generated:false,inspected:false,extra:[]);XCTAssertLessThanOrEqual(choices.count,255);targets.formUnion(choices.compactMap {$0.action?.target}) }
        XCTAssertTrue(targets.contains(store.nodes.first {$0.title=="n719"}!.id))
    }
    @MainActor func testPreferredExpansionDoesNotCollectUnrelatedBranches()throws {
        let source=FakeAX(count:2)
        for group in ["n0","n1"] { source.records[group]?.role="AXGroup";source.edges[group]=(0..<30).map { group+"-\($0)" };for id in source.edges[group]! { source.records[id]=Node(id:id,role:"AXButton",title:id,value:"",enabled:true,actions:["AXPress"],frame:nil) } }
        let store=AXStore(source:source);store.begin(roots:[("root","w")],budget:3)
        let handle=store.nodes.first {$0.title=="n1"}!.id;_ = try store.expand(handle,budget:100)
        XCTAssertEqual(store.nodes.filter {$0.ancestors?.last=="n1"}.count,30)
        XCTAssertFalse(store.nodes.contains {$0.ancestors?.last=="n0"})
        XCTAssertEqual(store.overview().coverage,.partial)
    }
    @MainActor func testCompactEvidenceKeepsAncestryAndBoundsRepeatedValues()throws {
        let app=AppInfo(pid:123,bundle:"owned.fixture",name:"Owned")
        let nodes=(0..<100).map { index in Node(id:"\(index)",role:"AXStaticText",title:"Result \(index)",value:String(repeating:"value",count:500),enabled:true,actions:[],frame:nil,ancestors:["Right controls"]) }
        let obs=Observation(id:"owned",timestamp:Date(),front:app,apps:[app],nodes:nodes,displays:[],truncated:true,axError:nil,elapsedMS:0,target:app)
        let state=Jev.compactState(goal:"Owned",observation:obs,history:[]),values=state["values"] as! [[String:Any]]
        XCTAssertLessThanOrEqual(values.count,16);XCTAssertEqual(state["omittedValueNodes"] as? Int,84)
        XCTAssertEqual(values.first?["context"] as? String,"Right controls")
        XCTAssertEqual(values.first?["title"] as? String,"Result 0")
        XCTAssertLessThanOrEqual(values.reduce(0) {$0+($1["value"] as! String).count},6000)
    }
    @MainActor func testNativeParentEvidenceIsIndependentOfChildTraversalEdges()throws {
        let source=FakeAX(count:1);source.parents["n0"]="native-group";let store=AXStore(source:source);store.begin(roots:[("root","w")])
        let child=store.nodes.first {$0.title=="n0"}!
        XCTAssertNotEqual(store.sourceRef(child.parent!),store.nativeParentSnapshot(child.id))
        XCTAssertNoThrow(try store.validateNativeParent(child.id,currentRef:"native-group"))
        XCTAssertThrowsError(try store.validateNativeParent(child.id,currentRef:"moved-group"))
    }
    @MainActor func testOmittedShortResultHasReachableReadAndBecomesVisible()throws {
        let source=FakeAX(count:20)
        for index in 0..<20 { source.records["n\(index)"]?.role="AXStaticText";source.records["n\(index)"]?.value="status \(index)" }
        source.records["n19"]?.value="LATE-RESULT-731"
        let store=AXStore(source:source);store.begin(roots:[("root","w")])
        let workflow=Workflow();workflow.native.axStore=store
        let app=AppInfo(pid:123,bundle:"owned.fixture",name:"Owned")
        var obs=Observation(id:"owned",timestamp:Date(),front:app,apps:[app],nodes:store.nodes,displays:[],truncated:false,axError:nil,elapsedMS:0,target:app,axOverview:store.overview())
        let late=store.nodes.first {$0.value=="LATE-RESULT-731"}!
        XCTAssertFalse(Jev.projectedValues(obs).contains {$0.0.id==late.id})
        let candidates=workflow.candidates(TaskSpec(goal:"Read late result",apps:[app.bundle]),obs,texts:[],generated:false,inspected:false,extra:[])
        let read=try XCTUnwrap(candidates.first {$0.query?.kind == .read && $0.query?.handle == late.id}?.query)
        _ = try workflow.native.applyQuery(read);obs.nodes=workflow.native.observationNodes();obs.axReadHandle=workflow.native.lastAXReadHandle
        XCTAssertEqual(Jev.projectedValues(obs).first?.1,"LATE-RESULT-731")
    }
    @MainActor func testFullReadChunkIsVisibleAndNextRangeStartsAtWireEnd()throws {
        let app=AppInfo(pid:123,bundle:"owned.fixture",name:"Owned")
        let text=String(repeating:"😀",count:500)+"MIDDLE-MARKER"+String(repeating:"a",count:987)
        let node=Node(id:"text",role:"AXTextArea",title:"Owned",value:text,enabled:true,actions:[],frame:nil,valueTruncated:true,textLengthUTF16:4000,valueRangeUTF16:AXTextRange(location:512,length:2000))
        let obs=Observation(id:"owned",timestamp:Date(),front:app,apps:[app],nodes:[node],displays:[],truncated:false,axError:nil,elapsedMS:0,target:app,axReadHandle:node.id)
        let projected=try XCTUnwrap(Jev.projectedValues(obs).first?.1);XCTAssertTrue(projected.contains("MIDDLE-MARKER"));XCTAssertEqual(projected.utf16.count,2000)
        let choices=Workflow().candidates(TaskSpec(goal:"Read owned",apps:[app.bundle]),obs,texts:[],generated:false,inspected:false,extra:[])
        XCTAssertEqual(choices.first {$0.query?.kind == .read}?.query?.rangeUTF16?.location,2512)
        let boundary=Jev.prefixUTF16("a😀b",limit:2);XCTAssertEqual(boundary,"a");XCTAssertEqual(boundary.utf16.count,1)
    }
}
