import AppKit

final class FixtureApplication: NSApplication {
    override func sendEvent(_ event:NSEvent) {
        if [.keyDown,.keyUp,.flagsChanged].contains(event.type) {
            if let fixture=delegate as? Fixture {
                let name = event.type == .keyDown ? "keyDown" : event.type == .keyUp ? "keyUp" : "flagsChanged"
                fixture.events[name,default:0] += 1
                if event.type == .keyDown {
                    fixture.heldKeys.insert(event.keyCode)
                    fixture.maximumHeldKeys = max(fixture.maximumHeldKeys, fixture.heldKeys.count)
                    fixture.keyDownTimes[event.keyCode] = ProcessInfo.processInfo.systemUptime
                } else if event.type == .keyUp {
                    fixture.heldKeys.remove(event.keyCode)
                    if let started = fixture.keyDownTimes.removeValue(forKey: event.keyCode) {
                        fixture.lastHoldSeconds = ProcessInfo.processInfo.systemUptime - started
                    }
                }
                fixture.save()
            }
            let info:[String:Any] = ["eventType":event.type.rawValue,"keyCode":event.keyCode,"flags":event.modifierFlags.rawValue,
                "characters":event.type == .flagsChanged ? "" : event.characters ?? "", "keyWindow":keyWindow?.windowNumber ?? 0]
            if let data=try? JSONSerialization.data(withJSONObject:info,options:[.sortedKeys]), let text=String(data:data,encoding:.utf8) { print(text); fflush(stdout) }
        }
        super.sendEvent(event)
    }
}

final class Canvas: NSView {
    var record: ((String) -> Void)?
    override var acceptsFirstResponder: Bool { true }
    override init(frame:NSRect) {
        super.init(frame:frame)
        setAccessibilityElement(true); setAccessibilityRole(.group); setAccessibilityLabel("입력 캔버스"); setAccessibilityIdentifier("canvas")
    }
    required init?(coder:NSCoder) { fatalError() }
    override func draw(_ dirtyRect:NSRect) {
        NSColor.controlAccentColor.withAlphaComponent(0.15).setFill(); bounds.fill()
        ("클릭 · 드래그 · 스크롤 검증" as NSString).draw(at:NSPoint(x:18,y:50),withAttributes:[.font:NSFont.systemFont(ofSize:18)])
    }
    override func mouseDown(with event:NSEvent) { record?("mouseDown") }
    override func mouseUp(with event:NSEvent) { record?("mouseUp") }
    override func rightMouseDown(with event:NSEvent) { record?("rightMouseDown") }
    override func rightMouseUp(with event:NSEvent) { record?("rightMouseUp") }
    override func mouseDragged(with event:NSEvent) { record?("mouseDragged") }
    override func scrollWheel(with event:NSEvent) { record?("scrollWheel") }
}
final class Fixture: NSObject, NSApplicationDelegate, NSTextFieldDelegate {
    let window = NSWindow(contentRect:NSRect(x:180,y:220,width:640,height:440),styleMask:[.titled,.closable,.miniaturizable,.resizable],backing:.buffered,defer:false)
    let field = NSTextField(string:"초기 값"), secure = NSSecureTextField(string:"synthetic-secret")
    let counter = NSTextField(labelWithString:"0"), canvas = Canvas(frame:NSRect(x:24,y:36,width:590,height:120))
    var clicks = 0, events: [String:Int] = [:]
    var heldKeys: Set<UInt16> = []
    var maximumHeldKeys = 0
    var keyDownTimes: [UInt16: Double] = [:]
    var lastHoldSeconds = 0.0
    var focusShiftArmed = false
    let directory: URL
    var timer: Timer?
    var twin: NSWindow?
    init(directory:URL) { self.directory=directory; super.init() }
    func applicationDidFinishLaunching(_ notification:Notification) {
        window.title = "MacPilot 검증 전용"; window.isReleasedWhenClosed = false
        let root = window.contentView!
        let label = NSTextField(labelWithString:"로컬 입력 검증"); label.font = .boldSystemFont(ofSize:24); label.frame=NSRect(x:24,y:382,width:500,height:36); root.addSubview(label)
        field.frame=NSRect(x:24,y:320,width:590,height:34); field.setAccessibilityIdentifier("literal-text"); field.delegate=self; root.addSubview(field)
        secure.frame=NSRect(x:24,y:264,width:590,height:30); secure.setAccessibilityIdentifier("secure-text"); root.addSubview(secure)
        let button = NSButton(title:"증가",target:self,action:#selector(increment)); button.frame=NSRect(x:24,y:200,width:120,height:36); button.setAccessibilityIdentifier("increment"); root.addSubview(button)
        counter.frame=NSRect(x:160,y:206,width:120,height:24); counter.setAccessibilityIdentifier("counter"); root.addSubview(counter)
        let shift = NSButton(title:"보안 전환",target:self,action:#selector(armFocusShift)); shift.frame=NSRect(x:230,y:200,width:100,height:36); shift.setAccessibilityIdentifier("arm-focus-shift"); root.addSubview(shift)
        let disabled = NSButton(title:"비활성",target:nil,action:nil); disabled.isEnabled=false; disabled.frame=NSRect(x:340,y:200,width:120,height:36); disabled.setAccessibilityIdentifier("disabled"); root.addSubview(disabled)
        let sheet = NSButton(title:"시트",target:self,action:#selector(showSheet)); sheet.frame=NSRect(x:480,y:200,width:120,height:36); sheet.setAccessibilityIdentifier("show-sheet"); root.addSubview(sheet)
        canvas.record = { [weak self] name in self?.events[name,default:0] += 1; self?.save() }; root.addSubview(canvas)
        let menu=NSMenu(); let appItem=NSMenuItem(); menu.addItem(appItem)
        let sub=NSMenu(); sub.addItem(withTitle:"Quit Fixture",action:#selector(NSApplication.terminate(_:)),keyEquivalent:"q"); appItem.submenu=sub
        let editItem=NSMenuItem(title:"Edit",action:nil,keyEquivalent:""); menu.addItem(editItem)
        let edit=NSMenu(title:"Edit"); edit.autoenablesItems=false
        let select=NSMenuItem(title:"Select All",action:#selector(selectAllText),keyEquivalent:"a"); select.target=self; edit.addItem(select); editItem.submenu=edit
        let twinItem=NSMenuItem(title:"Twin Window",action:#selector(showTwin),keyEquivalent:""); twinItem.target=self; edit.addItem(twinItem)
        NSApp.mainMenu=menu
        window.makeKeyAndOrderFront(nil); NSApp.activate(ignoringOtherApps:true); window.makeFirstResponder(field)
        timer=Timer.scheduledTimer(withTimeInterval:0.2,repeats:true) { [weak self] _ in self?.save() }
        save()
    }
    @objc func increment() { clicks += 1; counter.stringValue=String(clicks); save() }
    @objc func showTwin() {
        let copy=NSWindow(contentRect:.zero,styleMask:window.styleMask,backing:.buffered,defer:false)
        copy.setFrame(window.frame,display:false);copy.title=window.title;copy.isReleasedWhenClosed=false
        let label=NSTextField(labelWithString:"Twin window fixture");label.frame=NSRect(x:24,y:100,width:400,height:30)
        label.setAccessibilityIdentifier("twin-proof");copy.contentView?.addSubview(label)
        twin=copy;copy.orderFrontRegardless();save()
    }
    @objc func armFocusShift() {
        focusShiftArmed = true
        window.makeFirstResponder(field)
        events["focusShiftArmed",default:0] += 1
        save()
    }
    @objc func selectAllText() { field.currentEditor()?.selectAll(nil); events["selectAll",default:0] += 1; save() }
    @objc func showSheet() {
        let alert=NSAlert(); alert.messageText="검증 시트"; alert.addButton(withTitle:"닫기")
        alert.beginSheetModal(for:window) { [weak self] _ in self?.events["sheetClosed",default:0] += 1; self?.save() }
    }
    func controlTextDidChange(_ notification:Notification) {
        if focusShiftArmed, let changed = notification.object as? NSTextField, changed === field {
            focusShiftArmed = false
            window.makeFirstResponder(secure)
            events["focusShiftedToSecure",default:0] += 1
        }
        save()
    }
    func save() {
        let cg = CGEvent(source:nil)?.location ?? .zero
        let selection=field.currentEditor()?.selectedRange ?? NSRange(location:0,length:0)
        let state:[String:Any] = ["heldKeys":Array(heldKeys).sorted(),"maximumHeldKeys":maximumHeldKeys,"lastHoldSeconds":lastHoldSeconds,"pid":getpid(),"text":field.stringValue,"buttonCount":clicks,"events":events,"selection":["start":selection.location,"length":selection.length],
            "secureUnchanged":secure.stringValue == "synthetic-secret","focusShiftArmed":focusShiftArmed,
            "active":NSApp.isActive,"sheetOpen":window.attachedSheet != nil,"windowNumber":window.windowNumber,"twinWindowNumber":twin?.windowNumber ?? 0,"systemCursor":["x":cg.x,"y":cg.y]]
        if let data=try? JSONSerialization.data(withJSONObject:state,options:[.sortedKeys,.prettyPrinted]) { try? data.write(to:directory.appendingPathComponent("state.json"),options:.atomic) }
    }
}
let fixtureEnvironment = ProcessInfo.processInfo.environment
let fixtureDirectory = fixtureEnvironment["MACPILOT_FIXTURE_DIR"]
    ?? fixtureEnvironment["MAC_CU_FIXTURE_DIR"]
    ?? NSTemporaryDirectory() + "macpilot-fixture"
let dir = URL(fileURLWithPath:fixtureDirectory,isDirectory:true)
try FileManager.default.createDirectory(at:dir,withIntermediateDirectories:true,attributes:[.posixPermissions:0o700])
// Dispatch the public Objective-C class method to the subclass itself.
// Swift's imported shared property can select NSApplication's singleton first.
let app=FixtureApplication.perform(NSSelectorFromString("sharedApplication"))!.takeUnretainedValue() as! NSApplication
app.setActivationPolicy(.regular)
let fixture=Fixture(directory:dir); app.delegate=fixture
app.run()
