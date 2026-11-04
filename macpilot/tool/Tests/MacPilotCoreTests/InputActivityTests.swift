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
    func testNoticeFitsOffsetAndSmallVisibleFrames() {
        for screen in [NSRect(x: -1920, y: 120, width: 1920, height: 1055),
                       NSRect(x: 100, y: -900, width: 320, height: 240)] {
            let notice = InputActivityPresentation.noticeFrame(screen)
            XCTAssertTrue(screen.contains(notice))
            XCTAssertEqual(notice.midX, screen.midX)
            XCTAssertLessThanOrEqual(notice.width, 360)
            XCTAssertEqual(notice.height, 64)
        }
    }
    func testEndedNoticeCannotAcknowledgeControlAndHostMustStayFresh() {
        let now = Date()
        let active: [String: Any] = ["activityID": "a", "running": true, "visible": true, "controlActive": true,
            "presentationPhase": "active", "updatedAt": now.timeIntervalSince1970, "processStartID": "host"]
        func valid(_ value: [String: Any], at date: Date = now, identity: String? = "host") -> Bool {
            InputActivityScope.hasActiveAcknowledgement(value, activityID: "a", now: date, currentHostStartID: identity)
        }
        XCTAssertTrue(valid(active))
        XCTAssertFalse(valid(active, identity: "replacement"))
        XCTAssertFalse(valid(active, identity: nil))
        XCTAssertFalse(valid(active, at: now.addingTimeInterval(1)))
        XCTAssertFalse(valid(active, at: now.addingTimeInterval(-2)))
        for (key, value): (String, Any) in [("activityID", "b"), ("running", false), ("visible", false),
                                           ("controlActive", false), ("presentationPhase", "ended")] {
            var changed = active; changed[key] = value
            XCTAssertFalse(valid(changed), key)
        }
    }
    func testExplicitFinishShowsBoundedEndedStateAndNextActivityReplacesIt() {
        let now = Date()
        var lifecycle = InputActivityLifecycle()
        var record = InputActivityRecord(id: "a", ownerPID: 42, ownerStartID: "1.1", active: true, updatedAt: now, kind: "키보드")
        XCTAssertTrue(lifecycle.update(record: record, live: true, now: now))
        XCTAssertEqual(lifecycle.phase, .active)
        record.active = false
        XCTAssertTrue(lifecycle.update(record: record, live: false, now: now))
        XCTAssertEqual(lifecycle.phase, .ended)
        XCTAssertFalse(lifecycle.update(record: record, live: false, now: now.addingTimeInterval(1)))
        XCTAssertTrue(lifecycle.update(record: record, live: false, now: now.addingTimeInterval(1.2)))
        XCTAssertEqual(lifecycle.phase, .hidden)
        // An old inactive record cannot make a new host show a release notice.
        XCTAssertFalse(lifecycle.update(record: record, live: false, now: now.addingTimeInterval(2)))
        record.active = true
        _ = lifecycle.update(record: record, live: true, now: now)
        record.active = false
        _ = lifecycle.update(record: record, live: false, now: now)
        record.id = "b"; record.kind = "마우스"; record.active = true
        XCTAssertTrue(lifecycle.update(record: record, live: true, now: now.addingTimeInterval(0.2)))
        XCTAssertEqual(lifecycle.phase, .active)
        XCTAssertEqual(lifecycle.activityID, "b")
        XCTAssertEqual(lifecycle.kind, "마우스")
    }
    func testStaleOrMissingOwnerHidesInsteadOfClaimingRelease() {
        let now = Date()
        let record = InputActivityRecord(id: "a", ownerPID: 42, ownerStartID: "1.1", active: true, updatedAt: now, kind: "키보드")
        for lost in [record, nil] {
            var lifecycle = InputActivityLifecycle()
            _ = lifecycle.update(record: record, live: true, now: now)
            XCTAssertTrue(lifecycle.update(record: lost, live: false, now: now))
            XCTAssertEqual(lifecycle.phase, .hidden)
        }
    }
    @MainActor func testNoticeAndEdgePanelsCannotTakeInputOrFocus() {
        _ = NSApplication.shared
        let panel = InputActivityPresentation.panel(NSRect(x: 0, y: 0, width: 360, height: 64))
        XCTAssertTrue(panel.ignoresMouseEvents)
        XCTAssertFalse(panel.canBecomeKey); XCTAssertFalse(panel.canBecomeMain)
        XCTAssertFalse(panel.isOpaque); XCTAssertEqual(panel.level, .statusBar)
        XCTAssertTrue(panel.collectionBehavior.contains(.fullScreenAuxiliary))
        XCTAssertTrue(panel.collectionBehavior.contains(.canJoinAllSpaces))
        XCTAssertTrue(panel.collectionBehavior.contains(.canJoinAllApplications))
        panel.close()
    }
    @MainActor func testActiveAndEndedNoticesHaveDistinctNoncolorText() {
        let view = InputActivityNoticeView(frame: NSRect(x: 0, y: 0, width: 360, height: 64))
        view.kind = "마우스"
        XCTAssertEqual(view.title, "MacPilot이 마우스를 사용 중")
        XCTAssertEqual(view.hint, "직접 입력하면 MacPilot이 멈춥니다")
        view.ended = true
        XCTAssertEqual(view.title, "MacPilot 입력 종료")
        XCTAssertEqual(view.hint, "직접 입력할 수 있습니다")
    }
}
