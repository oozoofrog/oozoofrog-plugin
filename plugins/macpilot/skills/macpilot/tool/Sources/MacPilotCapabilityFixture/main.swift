import AppKit
import ApplicationServices

func writeJSON(_ value:Any,_ url:URL) throws { try JSONSerialization.data(withJSONObject:value,options:[.sortedKeys]).write(to:url,options:.atomic) }
func readJSON(_ url:URL) -> [String:Any] { guard let data = try? Data(contentsOf:url) else {return [:]}; return (try? JSONSerialization.jsonObject(with:data) as? [String:Any]) ?? [:] }
var duplicateImages = false
var changedImage = false
final class FixtureApp: NSApplication {
    override func sendEvent(_ event: NSEvent) {
        if let fixture = delegate as? Fixture, event.type == .keyDown || event.type == .keyUp {
            if event.type == .keyDown { fixture.down += 1; fixture.held.insert(event.keyCode) }
            else { fixture.up += 1; fixture.held.remove(event.keyCode) }
            fixture.save()
        }
        super.sendEvent(event)
    }
}
final class ImageGrid: NSView {
    override func draw(_ dirtyRect: NSRect) {
        NSColor(calibratedRed: 0.14, green: 0.19, blue: 0.25, alpha: 1).setFill(); bounds.fill()
        for (i, tile) in tiles.enumerated() {
            let rect = NSRect(x: 24 + (i % 4) * 240, y: 24 + (i / 4) * 240, width: 216, height: 216)
            tileImage(duplicateImages && i == 1 ? tiles[0] : (changedImage && i == 0 ? tiles[5] : tile), label: false, dark: false).draw(in: rect)
            NSColor.black.setStroke(); NSBezierPath(rect: rect).stroke()
        }
    }
}
final class Fixture: NSObject, NSApplicationDelegate, NSTextFieldDelegate {
    let directory: URL
    let window = NSWindow(contentRect: NSRect(x: 210, y: 240, width: 560, height: 360),
                          styleMask: [.titled, .closable, .resizable], backing: .buffered, defer: false)
    let field = NSTextField(string: "initial synthetic value")
    let secret = NSSecureTextField(string: "PROBE_SECRET_MUST_NOT_APPEAR")
    let count = NSTextField(labelWithString: "0")
    var ready = NSButton(title: "Ready", target: nil, action: nil)
    var status = NSTextField(labelWithString: "loading")
    var duplicate: NSButton?
    var clicks = 0, noops = 0, down = 0, up = 0
    var held: Set<UInt16> = []
    var timer: Timer?
    var lastCommand = ""
    var focusShiftArmed = false
    var gridCenters: [[String: Any]] = []
    init(_ directory: URL) { self.directory = directory; super.init() }
    func applicationDidFinishLaunching(_ notification: Notification) {
        window.title = "MacPilot capability fixture"; window.isReleasedWhenClosed = false
        let root = window.contentView!
        field.frame = NSRect(x: 20, y: 290, width: 515, height: 30); field.setAccessibilityIdentifier("literal"); field.delegate = self; root.addSubview(field)
        secret.frame = NSRect(x: 20, y: 245, width: 515, height: 26); secret.setAccessibilityIdentifier("secret"); root.addSubview(secret)
        count.frame = NSRect(x: 20, y: 205, width: 150, height: 24); count.setAccessibilityIdentifier("counter"); root.addSubview(count)
        for (title, identifier, selector, x) in [("Increment", "increment", #selector(increment), 20.0),
                                                ("No effect", "noop", #selector(noop), 180.0),
                                                ("Delayed", "delayed", #selector(delayed), 340.0)] {
            let button = NSButton(title: title, target: self, action: selector)
            button.frame = NSRect(x: x, y: 155, width: 140, height: 35); button.setAccessibilityIdentifier(identifier); root.addSubview(button)
        }
        ready.frame = NSRect(x: 20, y: 100, width: 140, height: 35); ready.setAccessibilityIdentifier("ready"); ready.isEnabled = false; root.addSubview(ready)
        status.frame = NSRect(x: 20, y: 50, width: 350, height: 25); status.setAccessibilityIdentifier("status"); root.addSubview(status)
        window.makeKeyAndOrderFront(nil); NSApp.activate(ignoringOtherApps: true); window.makeFirstResponder(field)
        timer = Timer.scheduledTimer(withTimeInterval: 0.02, repeats: true) { [weak self] _ in self?.tick() }
        save()
    }
    @objc func increment() { clicks += 1; count.stringValue = String(clicks); save() }
    @objc func noop() { noops += 1; save() }
    @objc func delayed() { DispatchQueue.main.asyncAfter(deadline: .now() + 0.8) { self.increment() } }
    func tick() {
        let command = readJSON(directory.appendingPathComponent("command.json"))
        guard let id = command["id"] as? String, id != lastCommand else { return }
        lastCommand = id
        let delay = command["delay"] as? Double ?? 0
        DispatchQueue.main.asyncAfter(deadline: .now() + delay) { self.command(command) }
    }
    func command(_ command: [String: Any]) {
        switch command["action"] as? String {
        case "enable": ready.isEnabled = true; NSAccessibility.post(element: ready, notification: .valueChanged)
        case "replace":
            let frame = status.frame; status.removeFromSuperview(); status = NSTextField(labelWithString: "complete")
            status.frame = frame; status.setAccessibilityIdentifier("status"); window.contentView!.addSubview(status)
            NSAccessibility.post(element: window, notification: .layoutChanged)
        case "replace_silent":
            let frame = status.frame; status.removeFromSuperview(); status = NSTextField(labelWithString: "silent complete")
            status.frame = frame; status.setAccessibilityIdentifier("status"); window.contentView!.addSubview(status)
        case "hide": status.removeFromSuperview(); NSAccessibility.post(element: window, notification: .layoutChanged)
        case "duplicate":
            let button = NSButton(title: "Ready twin", target: nil, action: nil)
            button.frame = NSRect(x: 200, y: 100, width: 140, height: 35); button.setAccessibilityIdentifier("ready")
            window.contentView!.addSubview(button); duplicate = button
        case "move":
            let original = window.frame
            for i in 1...8 { DispatchQueue.main.asyncAfter(deadline: .now() + Double(i) * 0.06) {
                self.window.setFrameOrigin(NSPoint(x: original.minX + Double(i) * 5, y: original.minY)); self.save()
            } }
        case "focus": window.makeFirstResponder(field)
        case "arm_shift": focusShiftArmed = true; window.makeFirstResponder(field)
        case "image_grid":
            window.setContentSize(NSSize(width: 1008, height: 768))
            window.contentView = ImageGrid(frame: NSRect(x: 0, y: 0, width: 1008, height: 768))
            gridCenters = tiles.enumerated().map { i, tile in
                ["id": tile.id, "x": Double(24 + (i % 4) * 240 + 108) / window.frame.width,
                 "y": (window.frame.height - Double(24 + (i / 4) * 240 + 108)) / window.frame.height]
            }
        case "duplicate_images": duplicateImages = true; window.contentView?.needsDisplay = true
        case "change_image": changedImage = true; window.contentView?.needsDisplay = true
        case "quit": NSApp.terminate(nil)
        default: break
        }
        save()
    }
    func controlTextDidChange(_ notification: Notification) {
        if focusShiftArmed, let changed = notification.object as? NSTextField, changed === field {
            focusShiftArmed = false; window.makeFirstResponder(secret)
        }
        save()
    }
    func save() {
        try? writeJSON(["pid": getpid(), "windowID": window.windowNumber, "clicks": clicks, "noops": noops,
                        "text": field.stringValue, "ready": ready.isEnabled, "status": status.stringValue,
                        "held": held.sorted(), "keyDown": down, "keyUp": up, "command": lastCommand,
                        "active": NSApp.isActive, "focusShiftArmed": focusShiftArmed,
                        "gridCenters": gridCenters,
                        "secureUnchanged": secret.stringValue == "PROBE_SECRET_MUST_NOT_APPEAR"], directory.appendingPathComponent("state.json"))
    }
}

struct Tile {
    let id: String, symbol: String, label: String
}
let tiles = [Tile(id: "folder", symbol: "folder.fill", label: "Open folder"),
             Tile(id: "trash", symbol: "trash.fill", label: "Delete"),
             Tile(id: "search", symbol: "magnifyingglass", label: "Search"),
             Tile(id: "save", symbol: "square.and.arrow.down", label: "Save file"),
             Tile(id: "share", symbol: "square.and.arrow.up", label: "Share"),
             Tile(id: "play", symbol: "play.fill", label: "Play"),
             Tile(id: "pause", symbol: "pause.fill", label: "Pause"),
             Tile(id: "settings", symbol: "gearshape.fill", label: "Settings"),
             Tile(id: "lock", symbol: "lock.fill", label: "Lock"),
             Tile(id: "calendar", symbol: "calendar", label: "Calendar"),
             Tile(id: "printer", symbol: "printer.fill", label: "Print"),
             Tile(id: "heart", symbol: "heart.fill", label: "Favorite")]
@MainActor func tileImage(_ tile: Tile, label: Bool, dark: Bool, size: Int = 256) -> NSImage {
    let image = NSImage(size: NSSize(width: size, height: size)); image.lockFocus()
    (dark ? NSColor(calibratedWhite: 0.12, alpha: 1) : .white).setFill(); NSRect(x: 0, y: 0, width: size, height: size).fill()
    if let symbol = NSImage(systemSymbolName: tile.symbol, accessibilityDescription: nil)?.withSymbolConfiguration(.init(pointSize: 90, weight: .regular)) {
        let tinted = NSImage(size: symbol.size); tinted.lockFocus()
        symbol.draw(at: .zero, from: .zero, operation: .sourceOver, fraction: 1)
        (dark ? NSColor.white : NSColor.black).set(); NSRect(origin: .zero, size: symbol.size).fill(using: .sourceIn); tinted.unlockFocus()
        let ratio = min(120 / tinted.size.width, 120 / tinted.size.height)
        let width = tinted.size.width * ratio, height = tinted.size.height * ratio
        tinted.draw(in: NSRect(x: (Double(size)-width)/2, y: label ? 95 : (Double(size)-height)/2, width: width, height: height))
    }
    if label {
        let attributes: [NSAttributedString.Key: Any] = [.font: NSFont.systemFont(ofSize: 24), .foregroundColor: dark ? NSColor.white : NSColor.black]
        let text = tile.label as NSString, width = text.size(withAttributes: attributes).width
        text.draw(at: NSPoint(x: (Double(size)-width)/2, y: 35), withAttributes: attributes)
    }
    image.unlockFocus(); return image
}
let arguments = Array(CommandLine.arguments.dropFirst())
if arguments == ["--external-input"] {
    guard CGPreflightPostEventAccess() else {
        print("{\"status\":\"error\",\"code\":\"post_event_denied\"}"); exit(2)
    }
    var location = CGEvent(source:nil)!.location; location.x += 1
    CGEvent(mouseEventSource:CGEventSource(stateID:.privateState),mouseType:.mouseMoved,mouseCursorPosition:location,mouseButton:.left)!.post(tap:.cghidEventTap)
    RunLoop.current.run(until:Date().addingTimeInterval(0.1))
    print("{\"status\":\"foreign_input_sent\",\"preflightPostEvent\":true}"); exit(0)
}
guard arguments.count == 1 else { fatalError("Expected an owned fixture directory") }
let app = FixtureApp.shared, fixture = Fixture(URL(fileURLWithPath:arguments[0]))
app.setActivationPolicy(.regular); app.delegate = fixture; app.run()
