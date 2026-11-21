import XCTest
@testable import Clips

final class ClipTests: XCTestCase {
    @MainActor
    func testReviewAfterThreeDistinctSavedClips() async throws {
        let suite = UUID().uuidString
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { defaults.removePersistentDomain(forName: suite) }
        let library = ClipLibrary(defaults: defaults)
        var calls = 0
        for clip in ["", "A", "A", "B"] {
            if library.save(clip) {
                await library.requestAfterSave(version: "1", isReady: { true }) { calls += 1 }
            }
        }
        XCTAssertEqual(calls, 0)
        XCTAssertEqual(library.clips, ["A", "B"])
        XCTAssertTrue(library.save("C"))
        await library.requestAfterSave(version: "1", isReady: { false }) { calls += 1 }
        let interrupted = Task {
            await library.requestAfterSave(version: "1", isReady: { true }) { calls += 1 }
        }
        interrupted.cancel()
        await interrupted.value
        XCTAssertEqual(calls, 0)
        await library.requestAfterSave(version: "1", isReady: { true }) { calls += 1 }
        XCTAssertEqual(calls, 1)
        let reopened = ClipLibrary(defaults: defaults)
        XCTAssertTrue(reopened.save("D"))
        await reopened.requestAfterSave(version: "1", isReady: { true }) { calls += 1 }
        XCTAssertEqual(calls, 1)
    }
}
