import XCTest
@testable import MacPilotCore

final class NativeFileTests: XCTestCase {
    @MainActor func testCopyMoveReadAndNoOverwriteUseRealSyntheticFiles() async throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at:root,withIntermediateDirectories:false)
        defer { try? FileManager.default.removeItem(at:root) }
        let engine = Engine(store:try Store(root:root.appendingPathComponent("state")))
        let original = root.appendingPathComponent("한글😀.txt").path
        let copy = root.appendingPathComponent("copy.txt").path
        let moved = root.appendingPathComponent("moved.txt").path
        let written = try await engine.call("mac_files",arguments:["operation":"write","path":original,"text":"한글 😀 e\u{301}"])
        XCTAssertEqual(written["status"] as? String,"file_write_verified")
        do {
            _ = try await engine.call("mac_files",arguments:["operation":"write","path":original,"text":"overwrite"])
            XCTFail("Existing content must not be replaced implicitly")
        } catch { XCTAssertEqual((error as? ToolFailure)?.code,"destination_exists") }
        let copied = try await engine.call("mac_files",arguments:["operation":"copy","path":original,"destination":copy])
        XCTAssertEqual(copied["contentHashVerified"] as? Bool,true)
        let movedResult = try await engine.call("mac_files",arguments:["operation":"move","path":copy,"destination":moved])
        XCTAssertEqual(movedResult["sourceExists"] as? Bool,false)
        let read = try await engine.call("mac_files",arguments:["operation":"read","path":moved])
        XCTAssertEqual(read["text"] as? String,"한글 😀 e\u{301}")
        XCTAssertEqual(try String(contentsOfFile:original,encoding:.utf8),"한글 😀 e\u{301}")
        let results = try await engine.call("mac_files",arguments:["operation":"search","path":root.path,"query":"moved"])
        XCTAssertEqual((results["items"] as? [[String:Any]])?.count,1)
        let nested = root.appendingPathComponent("nested")
        try FileManager.default.createDirectory(at:nested,withIntermediateDirectories:false)
        try Data("deep".utf8).write(to:nested.appendingPathComponent("deep.txt"))
        let bounded = try await engine.call("mac_files",arguments:["operation":"search","path":root.path,"query":"deep","maxDepth":1])
        XCTAssertEqual(bounded["coverage"] as? String,"partial")
        let directoryCopy = try await engine.call("mac_files",arguments:["operation":"copy","path":nested.path,"destination":root.appendingPathComponent("nested-copy").path])
        XCTAssertEqual(directoryCopy["status"] as? String,"file_copy_unverified")
        do {
            _ = try await engine.call("mac_files",arguments:["operation":"copy","path":root.path,"destination":root.appendingPathComponent("recursive").path])
            XCTFail("Recursive destination must fail")
        } catch { XCTAssertEqual((error as? ToolFailure)?.code,"invalid_argument") }
    }
}
