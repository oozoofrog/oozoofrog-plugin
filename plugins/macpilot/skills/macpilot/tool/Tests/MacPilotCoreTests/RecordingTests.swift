import XCTest
@testable import MacPilotCore

@MainActor final class RecordingTests: XCTestCase {
    func testCaptureScopeAndBudgetsAreValidatedBeforePermissionOrFileCreation() throws {
        let window: [String: Any] = ["operation": "record", "source": "window", "pid": 1, "processStartID": "fixture", "windowID": 2]
        let display: [String: Any] = ["operation": "record", "source": "display", "displayID": 3]
        XCTAssertNoThrow(try Recording.Request(Arguments(window)))
        XCTAssertNoThrow(try Recording.Request(Arguments(display)))
        for patch in [["displayID": 3], ["region": ["x": 0, "y": 0, "width": 10, "height": 10]], ["pid": true], ["windowID": 0], ["durationSeconds": 0], ["durationSeconds": 121],
                      ["fps": 0], ["fps": 61], ["maxDimension": 3841], ["systemAudio": "yes"], ["microphone": true]] as [[String: Any]] {
            XCTAssertThrowsError(try Recording.Request(Arguments(window.merging(patch) { _, new in new })))
        }
        XCTAssertThrowsError(try Recording.Request(Arguments(display.merging(["pid": 1]) { _, new in new })))
        XCTAssertThrowsError(try Recording.Request(Arguments(display.merging(["region": ["x": -1, "y": 0, "width": 10, "height": 10]]) { _, new in new })))
        XCTAssertNoThrow(try Recording.Request(Arguments(display.merging(["region": ["x": 0, "y": 0, "width": 100, "height": 50]]) { _, new in new })))
        XCTAssertThrowsError(try Recording.Request(Arguments(["operation": "record", "source": "window", "windowID": 2])))
    }
    func testEncodingGeometryIsEvenAndBoundedAcrossRetinaAndPortrait() throws {
        for size in [CGSize(width: 1501, height: 951), CGSize(width: 4000, height: 3000), CGSize(width: 799, height: 1601)] {
            let (width, height) = try Recording.dimensions(size: size, pixelScale: 2, maximum: 1920)
            XCTAssertEqual(width % 2, 0); XCTAssertEqual(height % 2, 0)
            XCTAssertLessThanOrEqual(max(width, height), 1920)
            XCTAssertLessThan(abs(Double(width) / Double(height) - size.width / size.height), 0.01)
        }
        XCTAssertThrowsError(try Recording.dimensions(size: .zero, pixelScale: 1, maximum: 1920))
        XCTAssertThrowsError(try Recording.dimensions(size: CGSize(width: CGFloat.infinity, height: 20), pixelScale: 1, maximum: 1920))
    }
    func testInspectorRejectsNonMediaWithoutCreatingOutput() async throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: false)
        defer { try? FileManager.default.removeItem(at: root) }
        let state = try Store(root: root.appendingPathComponent("state")), engine = Engine(store: state)
        let path = root.appendingPathComponent("empty.mp4"); try Data().write(to: path)
        do {
            _ = try await engine.call("mac_record", arguments: ["operation": "inspect", "path": path.path])
            XCTFail("Empty media must fail")
        } catch { XCTAssertEqual((error as? ToolFailure)?.code, "invalid_media") }
        XCTAssertFalse(try FileManager.default.contentsOfDirectory(atPath: state.root.path).contains { $0.hasSuffix(".mp4") || $0.hasSuffix(".png") })
    }
}
