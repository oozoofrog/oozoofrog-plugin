import XCTest
@testable import MacPilotCore

final class ImageSearchTests: XCTestCase {
    func vector(_ index:Int) -> [Double] { var value = Array(repeating:0.0,count:768); value[index] = 1; return value }
    func testEmbeddingsRejectWrongDimensionsNonfiniteAndUnnormalizedData() throws {
        XCTAssertTrue(EmbeddingMath.valid(vector(0)))
        XCTAssertFalse(EmbeddingMath.valid([1,0]))
        XCTAssertFalse(EmbeddingMath.valid(Array(repeating:1,count:768)))
        var nonfinite = vector(0); nonfinite[1] = .nan
        XCTAssertFalse(EmbeddingMath.valid(nonfinite))
        XCTAssertEqual(try EmbeddingMath.cosine(vector(0),vector(0)),1)
        XCTAssertEqual(try EmbeddingMath.cosine(vector(0),vector(1)),0)
        XCTAssertThrowsError(try EmbeddingMath.cosine(vector(0),nonfinite))
    }
    func testDuplicateAndWeakCandidatesDoNotAuthorizeSelection() {
        XCTAssertFalse(EmbeddingMath.accepted(scores:[0.9,0.9],minimum:0.65,margin:0.05))
        XCTAssertFalse(EmbeddingMath.accepted(scores:[0.64,0.1],minimum:0.65,margin:0.05))
        XCTAssertFalse(EmbeddingMath.accepted(scores:[0.8,0.79],minimum:0.65,margin:0.05))
        XCTAssertTrue(EmbeddingMath.accepted(scores:[0.8,0.6],minimum:0.65,margin:0.05))
    }
    @MainActor func testCacheContentIdentityAndCorruptionDoNotReuseWrongVectors() throws {
        try TraceTests().withStore { store in
            let first = EmbeddingCache.hash(Data("model-1:image-one".utf8)), second = EmbeddingCache.hash(Data("model-1:image-two".utf8))
            XCTAssertNotEqual(first,second)
            try EmbeddingCache.save(first,vector:vector(0),store:store)
            XCTAssertEqual(EmbeddingCache.read(first,store:store),vector(0)); XCTAssertNil(EmbeddingCache.read(second,store:store))
            try store.write(Data("corrupt".utf8),to:store.root.appendingPathComponent(try EmbeddingCache.name(first)))
            XCTAssertNil(EmbeddingCache.read(first,store:store))
            XCTAssertThrowsError(try EmbeddingCache.name("../outside"))
        }
    }
    @MainActor func testDisabledFeatureNeedsNoModelOrPythonAndDoesNotObserveTarget() async throws {
        let parent = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at:parent,withIntermediateDirectories:false)
        defer { try? FileManager.default.removeItem(at:parent) }
        let store = try Store(root:parent.appendingPathComponent("state")), engine = Engine(store:store)
        let status = try await engine.call("mac_image_search",arguments:["operation":"status"])
        XCTAssertEqual((status["settings"] as? [String:Any])?["enabled"] as? Bool,false)
        let doctor = try await engine.call("mac_doctor",arguments:[:])
        XCTAssertNotNil((doctor["optionalRuntimeDependencies"] as? [String:Any])?["imageSearch"])
        XCTAssertTrue(((doctor["capabilities"] as? [String:String])?["languageModel"] ?? "").contains("optional local EmbeddingGemma 2"))
        do { _ = try await engine.call("mac_image_search",arguments:["operation":"search","observation":"invalid","query":"save"]); XCTFail() }
        catch { XCTAssertEqual((error as? ToolFailure)?.code,"image_search_disabled") }
        _ = try await engine.call("mac_image_search",arguments:["operation":"configure","enabled":false])
        XCTAssertFalse((try ImageSearch.settings(store)).enabled)
    }
    @MainActor func testDistinctPositionsStayDistinctDespiteIdenticalContent() {
        let first = CGRect(x:0,y:0,width:100,height:100), other = CGRect(x:200,y:0,width:100,height:100)
        XCTAssertTrue(ImageSearch.overlaps(first,first)); XCTAssertFalse(ImageSearch.overlaps(first,other))
        XCTAssertTrue(ImageSearch.overlaps(CGRect(x:0,y:0,width:340,height:340),CGRect(x:90,y:110,width:160,height:120)))
    }
}
