import AppKit
import ApplicationServices

// Development-only drag to an owned drop target. Never targets System Settings
// and never clicks a permission switch. Arguments come from a fresh observation.
guard [7, 8].contains(CommandLine.arguments.count),
      let sourcePID = Int32(CommandLine.arguments[1]), let sourceID = UInt32(CommandLine.arguments[2]),
      let sourceX = Double(CommandLine.arguments[3]), let sourceY = Double(CommandLine.arguments[4]),
      CGPreflightPostEventAccess() else {
    fatalError("Expected helper PID, window ID, drag X/Y, app path, process start ID, and Post Event consent")
}
let expected = URL(fileURLWithPath: CommandLine.arguments[5]).resolvingSymlinksInPath()
let expectedStartID = CommandLine.arguments[6]
let expectedBundleID = CommandLine.arguments.count == 8 ? CommandLine.arguments[7] : "local.macpilot"
func startID(_ pid: Int32) -> String? {
    var info = proc_bsdinfo()
    guard proc_pidinfo(pid, PROC_PIDTBSDINFO, 0, &info, Int32(MemoryLayout<proc_bsdinfo>.size)) == MemoryLayout<proc_bsdinfo>.size else { return nil }
    return "\(info.pbi_start_tvsec).\(info.pbi_start_tvusec)"
}
func helperFrame() -> CGRect? {
    guard startID(sourcePID) == expectedStartID,
          let rows = CGWindowListCopyWindowInfo([.optionIncludingWindow], sourceID) as? [[String: Any]],
          let row = rows.first, (row[kCGWindowOwnerPID as String] as? NSNumber)?.int32Value == sourcePID,
          (row[kCGWindowName as String] as? String).map({ $0 == "MacPilot 권한 안내" }) ?? true,
          let bounds = row[kCGWindowBounds as String] as? [String: Any] else { return nil }
    return CGRect(dictionaryRepresentation: bounds as CFDictionary)
}
func finish(_ result: [String: Any], _ code: Int32) -> Never {
    let data = try! JSONSerialization.data(withJSONObject: result, options: [.sortedKeys])
    print(String(data: data, encoding: .utf8)!)
    exit(code)
}

final class DropTarget: NSView {
    override init(frame: NSRect) {
        super.init(frame: frame)
        registerForDraggedTypes([.fileURL])
    }
    required init?(coder: NSCoder) { fatalError("init(coder:) has not been implemented") }
    override func draw(_ dirtyRect: NSRect) {
        NSColor.windowBackgroundColor.setFill(); dirtyRect.fill()
        ("MacPilot 파일 드래그 검증" as NSString).draw(at: NSPoint(x: 40, y: 100), withAttributes: [.font: NSFont.systemFont(ofSize: 18), .foregroundColor: NSColor.labelColor])
    }
    override func draggingEntered(_ sender: NSDraggingInfo) -> NSDragOperation { .copy }
    override func prepareForDragOperation(_ sender: NSDraggingInfo) -> Bool { true }
    override func performDragOperation(_ sender: NSDraggingInfo) -> Bool {
        let urls = sender.draggingPasteboard.readObjects(forClasses: [NSURL.self]) as? [URL] ?? []
        let received = urls.first?.resolvingSymlinksInPath()
        let matched = received?.path == expected.path && urls.count == 1
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) {
            finish(["status": matched ? "passed" : "failed", "actualFileURL": received?.path ?? "", "expectedFileURL": expected.path, "nativeDragAndDrop": true, "systemSettingsChanged": false], matched ? 0 : 2)
        }
        return matched
    }
}

NSApplication.shared.setActivationPolicy(.accessory)
guard startID(sourcePID) == expectedStartID,
      let app = NSRunningApplication(processIdentifier: sourcePID), app.bundleIdentifier == expectedBundleID,
      let screen = NSScreen.main else { finish(["status": "blocked", "reason": "Owned helper identity changed; no input sent", "actualStartID": startID(sourcePID) ?? "", "bundleID": NSRunningApplication(processIdentifier: sourcePID)?.bundleIdentifier ?? "", "sourceFrameAvailable": helperFrame() != nil], 2) }
let target = NSWindow(contentRect: NSRect(x: screen.visibleFrame.minX + 80, y: screen.visibleFrame.midY - 120, width: 400, height: 240), styleMask: [.titled], backing: .buffered, defer: false)
target.title = "MacPilot Permission Drop Fixture"
target.contentView = DropTarget(frame: NSRect(x: 0, y: 0, width: 400, height: 240))
target.orderFrontRegardless()
let endCocoa = target.convertPoint(toScreen: NSPoint(x: 200, y: 120))
let end = CGPoint(x: endCocoa.x, y: CGDisplayBounds(CGMainDisplayID()).height - endCocoa.y)
let start = CGPoint(x: sourceX, y: sourceY)
let settings = NSRunningApplication.runningApplications(withBundleIdentifier: "com.apple.systempreferences").first
settings?.activate(options: [.activateAllWindows])
let initialForeground = settings?.processIdentifier
DispatchQueue.global().asyncAfter(deadline: .now() + 1.5) {
    guard let sourceFrame = helperFrame(), sourceFrame.contains(start),
          NSWorkspace.shared.frontmostApplication?.processIdentifier == initialForeground else {
        finish(["status": "blocked", "reason": "Source identity or foreground changed; no input sent"], 2)
    }
    let cocoaStart = NSPoint(x: start.x, y: CGDisplayBounds(CGMainDisplayID()).height - start.y)
    guard NSWindow.windowNumber(at: cocoaStart, belowWindowWithWindowNumber: 0) == Int(sourceID) else {
        finish(["status": "blocked", "reason": "Source is obscured; no input sent"], 2)
    }
    let eventSource = CGEventSource(stateID: .privateState)
    func post(_ type: CGEventType, _ point: CGPoint) {
        let event = CGEvent(mouseEventSource: eventSource, mouseType: type, mouseCursorPosition: point, mouseButton: .left)!
        event.flags = []; event.post(tap: .cghidEventTap)
    }
    post(.mouseMoved, start); Thread.sleep(forTimeInterval: 0.1)
    post(.leftMouseDown, start); Thread.sleep(forTimeInterval: 0.15)
    for i in 1...40 {
        post(.leftMouseDragged, CGPoint(x: start.x + (end.x - start.x) * Double(i) / 40, y: start.y + (end.y - start.y) * Double(i) / 40))
        Thread.sleep(forTimeInterval: 0.035)
    }
    post(.leftMouseUp, end)
}
DispatchQueue.main.asyncAfter(deadline: .now() + 10) { finish(["status": "failed", "reason": "No native drop received"], 2) }
NSApplication.shared.run()
