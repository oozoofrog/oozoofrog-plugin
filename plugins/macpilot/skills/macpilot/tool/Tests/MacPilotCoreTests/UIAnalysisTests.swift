import XCTest
@testable import MacPilotCore

final class UIAnalysisTests: XCTestCase {
    func node(_ id: String = "0", role: String = "AXButton", text: String = "Save", secure: Bool = false, enabled: Bool = true) -> Node {
        Node(id:id,path:[Int(id) ?? 0],role:role,subrole:"",title:text,identifier:"field-\(id)",value:text,
             valueTruncated:false,enabled:enabled,secure:secure,focused:false,
             frame:Rect(CGRect(x:10,y:10,width:100,height:30)),actions:["AXPress"])
    }
    func observation(_ nodes: [Node]) -> Observation {
        var value = CoreTests().observation(); value.nodes = nodes
        value.windowFrame = Rect(CGRect(x:0,y:0,width:500,height:300)); return value
    }
    func summary(_ nodes: [Node], query: String? = nil, role: String? = nil, interactive: Bool = false, inWindow: Bool = false,
                 offset: Int = 0, limit: Int = 50) -> [String: Any] {
        UIAnalysisModel.summarize(observation(nodes),query:query,role:role,interactiveOnly:interactive,inWindowOnly:inWindow,offset:offset,limit:limit)
    }
    func testSearchIsLiteralAndCaseInsensitive() {
        XCTAssertTrue(UIAnalysisModel.matches(node(text:"한글 A.*B 😀"),query:"a.*b"))
        XCTAssertFalse(UIAnalysisModel.matches(node(text:"A xyz B"),query:"a.*b"))
        XCTAssertTrue(UIAnalysisModel.matches(node(text:"한글 A.*B 😀"),query:"😀"))
    }
    func testSearchDoesNotSelectOneDuplicate() {
        let value = summary([node("0"),node("1")],query:"save")
        XCTAssertEqual(value["matchedCount"] as? Int,2)
        XCTAssertEqual((value["nodes"] as? [[String:Any]])?.count,2)
        XCTAssertNil(value["selectedNode"])
    }
    func testSecureProviderTextIsNeverEmittedOrSearched() throws {
        var secure = node(text:"SECRET",secure:true); secure.description = "SECRET"; secure.help = "SECRET"; secure.placeholder = "SECRET"
        XCTAssertFalse(UIAnalysisModel.matches(secure,query:"SECRET"))
        let object = UIAnalysisModel.object(secure)
        let encoded = try JSONSerialization.data(withJSONObject:object)
        XCTAssertFalse(String(decoding:encoded,as:UTF8.self).contains("SECRET"))
        XCTAssertEqual(object["secure"] as? Bool,true)
    }
    func testLongProviderTextHasAnExplicitBoundedDisplayBudget() throws {
        var long = node(text:String(repeating:"한",count:4096))
        long.actions = Array(repeating:String(repeating:"\n",count:256),count:64)
        long.identifier = long.title; long.description = long.title; long.placeholder = long.title; long.help = long.title
        let object = UIAnalysisModel.object(long)
        XCTAssertTrue((object["displayTruncatedFields"] as? [String])?.contains("value") == true)
        XCTAssertLessThanOrEqual((object["value"] as? String)?.utf8.count ?? 0,1024)
        let result = summary(Array(repeating:long,count:100),limit:100)
        XCTAssertLessThan(try JSONSerialization.data(withJSONObject:result).count,1_000_000)
    }
    func testRoleAndInteractiveFiltersPreserveCounts() {
        let value = summary([node("0"),node("1",enabled:false),node("2",role:"AXStaticText")],role:"AXButton",interactive:true)
        XCTAssertEqual(value["totalCollectedNodes"] as? Int,3)
        XCTAssertEqual(value["matchedCount"] as? Int,1)
        XCTAssertEqual((value["roleCounts"] as? [String:Int])?["AXButton"],2)
    }
    func testPaginationHasIndependentCollectionAndPageCoverage() {
        let value = summary([node("0"),node("1"),node("2")],offset:1,limit:1)
        XCTAssertEqual(value["matchedCount"] as? Int,3)
        XCTAssertEqual(value["returnedCount"] as? Int,1)
        XCTAssertEqual(value["nextOffset"] as? Int,2)
        XCTAssertEqual(value["coverage"] as? String,"partial")
        XCTAssertEqual(value["absenceEstablished"] as? Bool,false)
    }
    func testEmptyOrBeyondLastPageCannotEstablishAbsence() {
        for value in [summary([],query:"missing"),summary([node()],offset:99)] {
            XCTAssertEqual(value["returnedCount"] as? Int,0)
            XCTAssertEqual(value["absenceEstablished"] as? Bool,false)
            XCTAssertEqual(value["hasMore"] as? Bool,false)
        }
    }
    func testWindowIntersectionIsNotClaimedAsVisibility() {
        var outside = node("1"); outside.frame = Rect(CGRect(x:900,y:900,width:50,height:50))
        let value = summary([node(),outside],inWindow:true)
        XCTAssertEqual(value["matchedCount"] as? Int,1)
        XCTAssertEqual(value["occlusionTested"] as? Bool,false)
    }
    func testRangeChecksUTF16UnitsAndRejectsOverflow() throws {
        let text = "가😀z"
        XCTAssertEqual(text.utf16.count,4)
        try UIAnalysisModel.validateRange(start:1,length:2,count:text.utf16.count)
        try UIAnalysisModel.validateRange(start:4,length:0,count:4)
        for tuple in [(4,1,4),(-1,1,4),(0,4097,5000),(Int.max,1,4),(0,1,-1)] {
            XCTAssertThrowsError(try UIAnalysisModel.validateRange(start:tuple.0,length:tuple.1,count:tuple.2))
        }
    }
    func testAnalysisCatalogAndOutcomesAreReadOnly() throws {
        let tool = try XCTUnwrap(ToolCatalog.tools.first { $0["name"] as? String == "mac_analyze" })
        XCTAssertEqual((tool["annotations"] as? [String:Any])?["readOnlyHint"] as? Bool,true)
        let outcome = Outcomes.result("mac_analyze",arguments:["operation":"inspect"],value:["status":"ui_inspected"])
        XCTAssertEqual(outcome.dispatch,"not_applicable"); XCTAssertEqual(outcome.effect,"read_completed")
    }
    @MainActor func testInvalidAnalysisArgumentsDoNotReadTarget() async throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at:root,withIntermediateDirectories:false)
        defer { try? FileManager.default.removeItem(at:root) }
        let engine = Engine(store:try Store(root:root.appendingPathComponent("state")))
        for arguments: [String:Any] in [
            ["operation":"unknown"], ["operation":"search","query":""], ["operation":"inspect","text":"write"],
            ["operation":"read_text","node":"0","start":0,"length":4097], ["operation":"hit_test","x":true,"y":0],
            ["operation":"summary","maxNodes":1001], ["operation":"summary","query":String(repeating:"a",count:513)]
        ] {
            do { _ = try await engine.analyzeUI(Arguments(arguments)); XCTFail("Expected invalid argument") }
            catch let error as ToolFailure { XCTAssertEqual(error.code,"invalid_argument") }
        }
    }
}
