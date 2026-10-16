import XCTest
@testable import MacPilotCore

final class TaskTests: XCTestCase {
    @MainActor func testTaskStateCursorsAndCancellationAreIsolated() throws {
        let parent = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: parent, withIntermediateDirectories: false)
        defer { try? FileManager.default.removeItem(at: parent) }
        let base = try Store(root: parent.appendingPathComponent("state"))
        let a = try Tasks.call(Arguments(["operation":"begin","goal":"A"]), store: base)["task"] as! [String:Any]
        let b = try Tasks.call(Arguments(["operation":"begin","goal":"B"]), store: base)["task"] as! [String:Any]
        let aid = a["id"] as! String, bid = b["id"] as! String
        let first = try Tasks.state(aid, in: base), second = try Tasks.state(bid, in: base)
        let o = CoreTests().observation()
        try first.savePointer(Pointer(windowID: o.windowID, pid: o.pid, x: -500, y: 320, cursorID: "red"))
        try first.savePointer(Pointer(windowID: o.windowID, pid: o.pid, x: -400, y: 340, cursorID: "blue"))
        try second.savePointer(Pointer(windowID: o.windowID, pid: o.pid, x: -200, y: 400, cursorID: "red"))
        XCTAssertEqual(try first.pointers(o).count, 2)
        XCTAssertEqual(first.pointer(o, cursorID: "red")?.x, -500)
        XCTAssertEqual(second.pointer(o, cursorID: "red")?.x, -200)
        _ = try Tasks.call(Arguments(["operation":"cancel","taskID":aid]), store: base)
        XCTAssertThrowsError(try Tasks.requireActive(Tasks.load(aid, in: base)))
        XCTAssertNoThrow(try Tasks.requireActive(Tasks.load(bid, in: base)))
        XCTAssertThrowsError(try Store.pointerName("../escape"))
        XCTAssertThrowsError(try Tasks.state("../escape", in: base))
    }

    func testCursorCurveHasExactEndpointsAndSmoothCurvedProgress() {
        let path=CursorTrajectory(from:CGPoint(x:10,y:30),to:CGPoint(x:610,y:30),bounds:CGRect(x:0,y:0,width:800,height:500))
        XCTAssertEqual(path.position(elapsed:0),path.start)
        XCTAssertEqual(path.position(elapsed:path.duration),path.end)
        XCTAssertGreaterThan(path.position(elapsed:path.duration/2).y,30)
        let early=path.position(elapsed:path.duration*0.01)
        XCTAssertLessThan(hypot(early.x-path.start.x,early.y-path.start.y),0.02)
        let late=path.position(elapsed:path.duration*0.99)
        XCTAssertLessThan(hypot(late.x-path.end.x,late.y-path.end.y),0.02)
        let retarget=CursorTrajectory(from:path.position(elapsed:0.2),to:CGPoint(x:200,y:300),bounds:CGRect(x:0,y:0,width:800,height:500))
        XCTAssertEqual(retarget.position(elapsed:0),path.position(elapsed:0.2))
    }

    func testDesktopFeedbackMasksOccludedPartsInsteadOfDrawingInForeground() {
        let target=CGRect(x:100,y:100,width:200,height:100)
        XCTAssertEqual(Geometry.visiblePortions(of:target,behind:[]),[target])
        XCTAssertTrue(Geometry.visiblePortions(of:target,behind:[target.insetBy(dx:-10,dy:-10)]).isEmpty)
        let cover=CGRect(x:180,y:80,width:200,height:160)
        let visible=Geometry.visiblePortions(of:target,behind:[cover])
        XCTAssertEqual(visible.reduce(0){$0+$1.width*$1.height},8000)
        XCTAssertTrue(visible.allSatisfy{!$0.intersects(cover)})
        XCTAssertEqual(Geometry.visiblePortions(of:target,behind:[cover,CGRect(x:0,y:0,width:180,height:1000)]),[])
    }

    func testResourceLeasesExcludeTheSameTargetAcrossStores() throws {
        let parent = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: parent, withIntermediateDirectories: false)
        defer { try? FileManager.default.removeItem(at: parent) }
        let first = try Store(root: parent.appendingPathComponent("state"))
        let second = try Store(root: first.root)
        var lease: StateLease? = try first.lease(".target-42.lock")
        XCTAssertThrowsError(try second.lease(".target-42.lock"))
        XCTAssertNoThrow(try second.lease(".target-43.lock"))
        withExtendedLifetime(lease) {}
        lease = nil
        XCTAssertNoThrow(try second.lease(".target-42.lock"))
    }
}
