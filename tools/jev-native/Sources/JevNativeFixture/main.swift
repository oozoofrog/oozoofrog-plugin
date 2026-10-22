import AppKit
import Foundation

final class Canvas: NSView {
    var last=NSPoint(x:40,y:40), drags=0, scroll=0.0
    let logPath: String
    init(frame:NSRect,logPath:String) { self.logPath=logPath; super.init(frame:frame); setAccessibilityElement(true); setAccessibilityRole(.group); setAccessibilityLabel("Owned drag and scroll canvas"); update() }
    required init?(coder:NSCoder) { fatalError() }
    override func acceptsFirstMouse(for event:NSEvent?) -> Bool { true }
    override var acceptsFirstResponder:Bool { true }
    func update() { setAccessibilityValue("drags=\(drags), scroll=\(scroll), x=\(Int(last.x)), y=\(Int(last.y))"); needsDisplay=true }
    func record(_ e:NSEvent) {
        let data:[String:Any] = ["type":e.type.rawValue,"x":e.locationInWindow.x,"y":e.locationInWindow.y,"window":e.windowNumber,"marker":e.cgEvent?.getIntegerValueField(.eventSourceUserData) ?? 0,"appActive":NSApp.isActive,"front":NSWorkspace.shared.frontmostApplication?.bundleIdentifier ?? "unknown"]
        guard let bytes=try? JSONSerialization.data(withJSONObject:data) else { return }
        if !FileManager.default.fileExists(atPath:logPath) { FileManager.default.createFile(atPath:logPath,contents:nil) }
        if let h=FileHandle(forWritingAtPath:logPath) { h.seekToEndOfFile(); h.write(bytes); h.write(Data([10])); try? h.close() }
    }
    override func mouseDown(with e:NSEvent) { last=convert(e.locationInWindow,from:nil); record(e); update() }
    override func mouseDragged(with e:NSEvent) { last=convert(e.locationInWindow,from:nil); drags+=1; record(e); update() }
    override func mouseUp(with e:NSEvent) { last=convert(e.locationInWindow,from:nil); record(e); update() }
    override func scrollWheel(with e:NSEvent) { scroll += e.scrollingDeltaY; record(e); update() }
    override func draw(_ rect:NSRect) { NSColor.windowBackgroundColor.setFill(); rect.fill(); NSColor.systemIndigo.setFill(); NSBezierPath(ovalIn:NSRect(x:last.x-12,y:last.y-12,width:24,height:24)).fill(); let text="Drag events: \(drags) · Scroll: \(Int(scroll))"; (text as NSString).draw(at:NSPoint(x:15,y:15),withAttributes:[.font:NSFont.systemFont(ofSize:16),.foregroundColor:NSColor.labelColor]) }
}
let app=NSApplication.shared
app.setActivationPolicy(CommandLine.arguments.contains("--regular") ? .regular : .accessory)
let window=NSWindow(contentRect:NSRect(x:180,y:180,width:480,height:300),styleMask:[.titled,.closable,.resizable],backing:.buffered,defer:false)
window.title="JEV Owned Native Fixture"
let scenarioIndex=CommandLine.arguments.firstIndex(of:"--scenario")
var queryFixture: QueryFixture?
if let scenarioIndex, CommandLine.arguments.indices.contains(scenarioIndex+1) {
    let scenario=CommandLine.arguments[scenarioIndex+1]
    let log=CommandLine.arguments.firstIndex(of:"--log").flatMap { CommandLine.arguments.indices.contains($0+1) ? CommandLine.arguments[$0+1] : nil } ?? "/tmp/jev-query-fixture-events.jsonl"
    queryFixture=MainActor.assumeIsolated { QueryFixture(window:window,scenario:scenario,logPath:log) }
} else {
    let canvas=Canvas(frame:NSRect(x:0,y:0,width:480,height:300),logPath:CommandLine.arguments.dropFirst().first ?? "/tmp/jev-owned-fixture-events.jsonl")
    window.contentView=canvas; window.makeFirstResponder(canvas); window.orderFrontRegardless()
}
print("fixture_pid=\(ProcessInfo.processInfo.processIdentifier)"); fflush(stdout)
app.run()
