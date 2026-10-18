import XCTest
@testable import MacPilotCore

final class TraceTests: XCTestCase {
    @MainActor func withStore(_ body:(Store) throws -> Void) throws {
        let parent = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at:parent,withIntermediateDirectories:false)
        defer { try? FileManager.default.removeItem(at:parent) }
        try body(Store(root:parent.appendingPathComponent("state")))
    }
    @MainActor func testTextIsOptInAndSecureValuesRemainExcluded() throws {
        var o = CoreTests().observation()
        var clear = ConditionTests().node(value:"synthetic-private-value")
        clear.title = "synthetic-private-title"
        var secure = clear; secure.id = "secret"; secure.identifier = "synthetic-secret-id"; secure.secure = true
        o.nodes = [clear,secure]
        var settings = TraceSettings()
        var encoded = String(data:try JSONEncoder().encode(Tracing.snapshot(o,settings:settings)),encoding:.utf8)!
        XCTAssertFalse(encoded.contains("synthetic-private-value")); XCTAssertFalse(encoded.contains("synthetic-private-title"))
        settings.captureText = true
        let snapshot = Tracing.snapshot(o,settings:settings)
        XCTAssertEqual(snapshot.nodes[0].value,"synthetic-private-value")
        XCTAssertNil(snapshot.nodes[1].value); XCTAssertNil(snapshot.nodes[1].title); XCTAssertEqual(snapshot.nodes[1].identifier,"")
        encoded = String(data:try JSONEncoder().encode(snapshot.nodes[1]),encoding:.utf8)!
        XCTAssertFalse(encoded.contains("synthetic-private")); XCTAssertFalse(encoded.contains("synthetic-secret"))
    }
    func record(_ time:String) -> TraceRecord {
        TraceRecord(id:UUID().uuidString.lowercased(),createdISO8601:time,tool:"mac_ax",status:"action_requested",elapsedMilliseconds:5,
                    outcome:OperationOutcome(dispatch:"sent",effect:"unverified",retry:"observe_before_deciding"),changedNodeIDs:[],captureErrors:[])
    }
    @MainActor func testRetentionAndClearOnlyRemoveOwnedTraceNamespace() throws {
        try withStore { store in
            var settings = TraceSettings(); settings.enabled = true; settings.maxEntries = 1
            let unrelated = CoreTests().observation(); try store.save(unrelated)
            try store.write(Data("keep".utf8),to:store.root.appendingPathComponent("unrelated.txt"))
            var first = record("2026-10-18T00:00:00.001Z")
            first.before = TraceSnapshot(observationID:unrelated.id,coverage:"partial",nodes:[],screenshot:unrelated.id+".png")
            let second = record("2026-10-18T00:00:00.002Z")
            try Tracing.save(first,store:store,settings:settings); try Tracing.save(second,store:store,settings:settings)
            XCTAssertThrowsError(try Tracing.load(first.id,store:store)); XCTAssertNoThrow(try Tracing.load(second.id,store:store))
            XCTAssertNoThrow(try store.load(unrelated.id)); XCTAssertEqual(try store.read("unrelated.txt"),Data("keep".utf8))
            _ = try Tracing.call(Arguments(["operation":"clear"]),store:store)
            XCTAssertEqual(try Tracing.recordNames(store),[]); XCTAssertNoThrow(try store.load(unrelated.id))
        }
    }
    @MainActor func testExportEscapesUntrustedContentAndRejectsPaths() throws {
        try withStore { store in
            var value = record("2026-10-18T00:00:00.001Z"); value.tool = "<script>alert(1)</script>"
            try Tracing.save(value,store:store,settings:TraceSettings())
            let exported = try Tracing.call(Arguments(["operation":"export","traceID":value.id]),store:store)
            let text = try String(contentsOfFile:exported["path"] as! String,encoding:.utf8)
            XCTAssertFalse(text.contains("<script>alert(1)</script>")); XCTAssertTrue(text.contains("&lt;script&gt;"))
            XCTAssertThrowsError(try Tracing.call(Arguments(["operation":"read","traceID":"../secret"]),store:store))
        }
    }
    @MainActor func testExplicitConfigurationRecoversCorruptSettingsWithSafeDefaults() throws {
        try withStore { store in
            try store.write(Data("broken".utf8),to:store.root.appendingPathComponent("trace-settings.json"))
            XCTAssertThrowsError(try Tracing.settings(store))
            _ = try Tracing.call(Arguments(["operation":"configure","enabled":true]),store:store)
            let value = try Tracing.settings(store)
            XCTAssertTrue(value.enabled); XCTAssertFalse(value.captureText); XCTAssertFalse(value.captureScreenshots)
        }
    }
    @MainActor func testHTMLExportsCountTowardTheSameStorageBudget() throws {
        try withStore { store in
            var settings = TraceSettings(); settings.maxBytes = 1_048_576
            let value = record("2026-10-18T00:00:00.001Z")
            try Tracing.save(value,store:store,settings:settings)
            try store.write(Data(repeating:65,count:1_048_576),to:store.root.appendingPathComponent("trace-view-\(value.id).html"))
            XCTAssertThrowsError(try Tracing.save(value,store:store,settings:settings))
            XCTAssertNil(try store.byteCount("trace-view-\(value.id).html"))
            XCTAssertNil(try store.byteCount("trace-\(value.id).json"))
        }
    }
}
