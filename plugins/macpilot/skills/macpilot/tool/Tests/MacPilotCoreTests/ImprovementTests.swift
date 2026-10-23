import XCTest
@testable import MacPilotCore

final class ImprovementTests:XCTestCase {
    @MainActor func testUnavailableDesktopSessionIsExpectedAndDoesNotQueueImprovement() async throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: root) }
        let store = try Store(root: root)
        let identifier = await Improvements.capture(ToolFailure("gui_session_unavailable", "No current WindowServer session"),
                                                   tool: "mac_activate", task: nil, store: store)
        XCTAssertNil(identifier)
        XCTAssertTrue(try store.names(prefix: "improvement-").isEmpty)
    }

    @MainActor func testAutomaticFailureReportIsDurableDeduplicatedAndDoesNotCopyArguments() async throws {
        let root=FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at:root,withIntermediateDirectories:false)
        defer{try? FileManager.default.removeItem(at:root)}
        let store=try Store(root:root.appendingPathComponent("state")),engine=Engine(store:store)
        var identifiers:[String]=[]
        for _ in 0..<2{
            do{_ = try await engine.call("mac_nonexistent_probe",arguments:["text":"private payload must not be sent"]);XCTFail("Unknown tool should fail")}
            catch let error as ToolFailure{identifiers.append(try XCTUnwrap(error.improvementRequestID))}
        }
        XCTAssertEqual(identifiers.count,2);XCTAssertEqual(Set(identifiers).count,1)
        let record=try Improvements.load(identifiers[0],store:store)
        XCTAssertEqual(record.status,"pending");XCTAssertEqual(record.occurrences,2)
        XCTAssertFalse(jsonString(record.object).contains("private payload"))
        XCTAssertThrowsError(try Improvements.configuration(store))
        var completed=record;completed.status="completed";completed.response="Already diagnosed"
        try store.write(JSONEncoder().encode(completed),to:store.root.appendingPathComponent("improvement-\(record.id).json"))
        let result=try await Improvements.deliver(record.id,store:store,timeout:1000)
        XCTAssertEqual(result.status,"completed") // No destination or second model request is needed.
    }
}
