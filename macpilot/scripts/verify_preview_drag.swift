import AppKit

// Development-only input check against the explicitly selected, owned preview.
NSApplication.shared.setActivationPolicy(.prohibited)
guard (3...4).contains(CommandLine.arguments.count),let pid=Int32(CommandLine.arguments[1]),let id=UInt32(CommandLine.arguments[2]),CGPreflightPostEventAccess() else{fatalError("Expected owned preview PID, window ID and Post Event consent")}
func frame() -> CGRect {
    let rows=CGWindowListCopyWindowInfo([.optionIncludingWindow],id) as? [[String:Any]] ?? []
    guard let row=rows.first, row[kCGWindowOwnerPID as String] as? Int32 == pid,
          row[kCGWindowName as String] as? String == "MacPilot Preview",
          let bounds=row[kCGWindowBounds as String] as? [String:Any],let value=CGRect(dictionaryRepresentation:bounds as CFDictionary) else{fatalError("Owned preview identity changed")}
    return value
}
let before=frame(),foreground=NSWorkspace.shared.frontmostApplication?.processIdentifier ?? 0
let start=CGPoint(x:before.midX,y:before.minY+min(60,before.height/3))
let cocoa=NSPoint(x:start.x,y:CGDisplayBounds(CGMainDisplayID()).height-start.y)
guard NSWindow.windowNumber(at:cocoa,belowWindowWithWindowNumber:0)==Int(id) else{fatalError("Owned preview is obscured; no input was sent")}
let source=CGEventSource(stateID:.privateState)
func post(_ type:CGEventType,_ point:CGPoint) {
    guard let event=CGEvent(mouseEventSource:source,mouseType:type,mouseCursorPosition:point,mouseButton:.left) else{fatalError("Cannot create test event")}
    event.flags=[];event.post(tap:.cghidEventTap)
}
post(.mouseMoved,start);Thread.sleep(forTimeInterval:0.1)
post(.leftMouseDown,start);Thread.sleep(forTimeInterval:0.1)
for step in 1...20 { post(.leftMouseDragged,CGPoint(x:start.x-Double(step)*4,y:start.y-Double(step)*3));Thread.sleep(forTimeInterval:0.03) }
post(.leftMouseUp,CGPoint(x:start.x-80,y:start.y-60));Thread.sleep(forTimeInterval:0.3)
let after=frame(),afterForeground=NSWorkspace.shared.frontmostApplication?.processIdentifier ?? 0
let moved=abs(after.minX-before.minX)>40 && abs(after.minY-before.minY)>30
let value:[String:Any]=["dragMovedPreview":moved,"foregroundPreserved":foreground==afterForeground,"before":[before.minX,before.minY,before.width,before.height],"after":[after.minX,after.minY,after.width,after.height]]
var report=value
if CommandLine.arguments.count==4,let targetPID=Int32(CommandLine.arguments[3]) {
    let point=CGPoint(x:after.midX,y:after.minY+60)
    for click in 1...2 {
        for type:CGEventType in [.leftMouseDown,.leftMouseUp] {
            let event=CGEvent(mouseEventSource:source,mouseType:type,mouseCursorPosition:point,mouseButton:.left)!
            event.flags=[];event.setIntegerValueField(.mouseEventClickState,value:Int64(click));event.post(tap:.cghidEventTap)
            Thread.sleep(forTimeInterval:0.08)
        }
    }
    let deadline=Date().addingTimeInterval(5)
    var hidden=false
    repeat {
        let windows=CGWindowListCopyWindowInfo([.optionOnScreenOnly],kCGNullWindowID) as? [[String:Any]] ?? []
        hidden = !windows.contains{($0[kCGWindowNumber as String] as? UInt32)==id}
        if hidden && NSWorkspace.shared.frontmostApplication?.processIdentifier==targetPID{break}
        Thread.sleep(forTimeInterval:0.1)
    }while Date()<deadline
    report["previewHidden"]=hidden;report["expectedTargetPID"]=targetPID;report["actualForegroundPID"]=NSWorkspace.shared.frontmostApplication?.processIdentifier ?? 0
    report["doubleClickRaisedTargetAndClosedPreview"]=hidden && NSWorkspace.shared.frontmostApplication?.processIdentifier==targetPID
}
let data=try JSONSerialization.data(withJSONObject:report,options:[.sortedKeys]);print(String(data:data,encoding:.utf8)!)
if CommandLine.arguments.count==4,report["doubleClickRaisedTargetAndClosedPreview"] as? Bool != true{exit(2)}
guard moved,foreground==afterForeground else{exit(2)}
