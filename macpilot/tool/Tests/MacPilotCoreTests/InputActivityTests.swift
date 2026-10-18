import AppKit
import XCTest
@testable import MacPilotCore

final class InputActivityTests: XCTestCase {
    func testActivityRequiresFreshHeartbeatAndExactOwnerIdentity() {
        let now = Date()
        var record = InputActivityRecord(id: "test", ownerPID: 42, ownerStartID: "1.1", active: true, updatedAt: now, kind: "키보드")
        XCTAssertTrue(record.isLive(now: now, ownerStartID: "1.1"))
        XCTAssertFalse(record.isLive(now: now, ownerStartID: "2.1"))
        XCTAssertFalse(record.isLive(now: now, ownerStartID: nil))
        XCTAssertFalse(record.isLive(now: now.addingTimeInterval(2), ownerStartID: "1.1"))
        record.active = false
        XCTAssertFalse(record.isLive(now: now, ownerStartID: "1.1"))
    }
    func testEdgesCoverEverySideWithoutFullScreenInputSurface() {
        let screen = NSRect(x: -1440, y: -200, width: 1440, height: 900)
        let edges = InputActivityPresentation.edgeFrames(screen)
        XCTAssertEqual(edges.count, 4)
        XCTAssertTrue(edges.allSatisfy { screen.contains($0) && min($0.width, $0.height) == 3 })
        XCTAssertLessThan(edges.reduce(0) { $0 + $1.width * $1.height }, screen.width * screen.height * 0.02)
    }
    @MainActor func testNoticeAndEdgePanelsCannotTakeInputOrFocus() {
        _ = NSApplication.shared
        let panel = InputActivityPresentation.panel(NSRect(x: 0, y: 0, width: 264, height: 34))
        XCTAssertTrue(panel.ignoresMouseEvents)
        XCTAssertFalse(panel.canBecomeKey); XCTAssertFalse(panel.canBecomeMain)
        XCTAssertFalse(panel.isOpaque); XCTAssertEqual(panel.level, .statusBar)
        XCTAssertTrue(panel.collectionBehavior.contains(.fullScreenAuxiliary))
        XCTAssertTrue(panel.collectionBehavior.contains(.canJoinAllSpaces))
        XCTAssertTrue(panel.collectionBehavior.contains(.canJoinAllApplications))
        panel.close()
    }
}
