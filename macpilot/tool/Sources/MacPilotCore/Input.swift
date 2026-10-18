import AppKit
import Carbon

@MainActor public enum Input {
    public static let keyCodes: [String: CGKeyCode] = [
        "a":0,"s":1,"d":2,"f":3,"h":4,"g":5,"z":6,"x":7,"c":8,"v":9,"b":11,
        "q":12,"w":13,"e":14,"r":15,"y":16,"t":17,"1":18,"2":19,"3":20,"4":21,
        "6":22,"5":23,"=":24,"9":25,"7":26,"-":27,"8":28,"0":29,
        "]":30,"o":31,"u":32,"[":33,"i":34,"p":35,"return":36,"l":37,"j":38,
        "'":39,"k":40,";":41,"\\":42,",":43,"/":44,"n":45,"m":46,".":47,
        "tab":48,"space":49,"`":50,"delete":51,"escape":53,
        "f1":122,"f2":120,"f3":99,"f4":118,"f5":96,"f6":97,"f7":98,"f8":100,
        "f9":101,"f10":109,"f11":103,"f12":111,"home":115,"end":119,
        "pageup":116,"pagedown":121,"forwarddelete":117,"left":123,"right":124,"down":125,"up":126
    ]
    public static func flags(_ names: [String]) throws -> CGEventFlags {
        var flags: CGEventFlags = []
        for name in names {
            switch name {
            case "command": flags.insert(.maskCommand)
            case "shift": flags.insert(.maskShift)
            case "option": flags.insert(.maskAlternate)
            case "control": flags.insert(.maskControl)
            default: throw ToolFailure("invalid_argument", "Unknown modifier: \(name)")
            }
        }
        return flags
    }
    public static func preflight() throws {
        guard AXIsProcessTrusted(), CGPreflightPostEventAccess() else { throw ToolFailure("event_post_denied", "Accessibility / Post Event access is required") }
        guard !IsSecureEventInputEnabled() else { throw ToolFailure("secure_input", "Secure Event Input is active; synthetic input is blocked") }
    }
    public static func route(_ route: String, observation: Observation) throws {
        guard ["process", "global"].contains(route) else { throw ToolFailure("invalid_argument", "route must be process or global") }
        if route == "global" {
            guard NSWorkspace.shared.frontmostApplication?.processIdentifier == observation.pid else { throw ToolFailure("foreground_mismatch", "Global input requires the selected app to be foreground") }
        }
    }
    public static func post(_ event: CGEvent, route: String, pid: Int32) {
        InputOwnership.stamp(event)
        if route == "process" { event.postToPid(pid) } else { event.post(tap: .cghidEventTap) }
    }
    public static func keyEvents(key: String, modifiers: [String], stateID: CGEventSourceStateID = .privateState) throws -> [CGEvent] {
        guard let code = keyCodes[key.lowercased()] else { throw ToolFailure("invalid_argument", "Unknown key name; use keyCode from the documented map") }
        _ = try flags(modifiers) // Validate before creating any events.
        let source = CGEventSource(stateID: stateID)
        // GHOST and other event-driven clients track modifier transitions, rather
        // than reconstructing held keys from the flags on the printable key.
        let selected = modifierKeys.filter { modifiers.contains($0.name) }
        var held: CGEventFlags = [], events: [CGEvent] = []
        func event(_ code: CGKeyCode, down: Bool, flags: CGEventFlags, modifier: Bool = false) throws -> CGEvent {
            guard let event = CGEvent(keyboardEventSource: source, virtualKey: code, keyDown: down) else {
                throw ToolFailure("event_failed", "Cannot create key event")
            }
            if modifier { event.type = .flagsChanged }
            event.flags = flags
            return event
        }
        for item in selected {
            held.insert(item.flag)
            events.append(try event(item.code, down:true, flags:held, modifier:true))
        }
        events.append(try event(code, down:true, flags:held))
        events.append(try event(code, down:false, flags:held))
        for item in selected.reversed() {
            held.remove(item.flag)
            events.append(try event(item.code, down:false, flags:held, modifier:true))
        }
        return events
    }
    private static let modifierKeys: [(name:String, code:CGKeyCode, flag:CGEventFlags)] = [
        ("control",59,.maskControl), ("option",58,.maskAlternate),
        ("shift",56,.maskShift), ("command",55,.maskCommand)
    ]
    public static func isKeyPress(_ event: CGEvent) -> Bool {
        if event.type == .keyDown { return true }
        guard event.type == .flagsChanged,
              let item = modifierKeys.first(where: { Int64($0.code) == event.getIntegerValueField(.keyboardEventKeycode) }) else { return false }
        return event.flags.contains(item.flag)
    }
    public static func heldKeyEvents(_ keys: [String], stateID: CGEventSourceStateID = .privateState) throws -> [(down: CGEvent, up: CGEvent)] {
        let names = keys.map { $0.lowercased() }
        guard !names.isEmpty, names.count <= 8, Set(names).count == names.count else {
            throw ToolFailure("invalid_argument", "Use one to eight distinct physical key names")
        }
        // Prepare the entire set before posting any down event.
        return try names.map { name in
            let events = try keyEvents(key: name, modifiers: [], stateID: stateID)
            return (events[0], events[1])
        }
    }
    public static func textEvents(_ text: String) throws -> [CGEvent] {
        let source = CGEventSource(stateID: .privateState)
        // One Unicode scalar per event: clients may consume only the first
        // scalar. Keep a non-BMP scalar's UTF-16 surrogate pair together.
        return try text.unicodeScalars.flatMap { scalar -> [CGEvent] in
            let units = Array(String(scalar).utf16)
            return try [true, false].map { down in
                guard let event = CGEvent(keyboardEventSource: source, virtualKey: 0, keyDown: down) else { throw ToolFailure("event_failed", "Cannot create Unicode event") }
                event.flags = []; units.withUnsafeBufferPointer { event.keyboardSetUnicodeString(stringLength: $0.count, unicodeString: $0.baseAddress) }
                return event
            }
        }
    }
    public static func mouseEvent(_ type: CGEventType, point: CGPoint, observation: Observation, button: CGMouseButton = .left, clicks: Int = 1) throws -> CGEvent {
        // Quartz-native construction preserves global coordinates during dispatch.
        // NSEvent.mouseEvent(...).cgEvent can retain window-local coordinate metadata.
        guard let event = CGEvent(mouseEventSource: CGEventSource(stateID: .privateState), mouseType: type,
                                  mouseCursorPosition: point, mouseButton: type == .rightMouseDown || type == .rightMouseUp ? .right : button) else {
            throw ToolFailure("event_failed", "Cannot create mouse event")
        }
        event.location = point; event.flags = []; event.setIntegerValueField(.mouseEventClickState, value: Int64(clicks))
        address(event, observation: observation)
        return event
    }
    public static func address(_ event: CGEvent, observation: Observation) {
        // Named public CGEventField cases (public since 10.7), never raw numeric fields.
        event.setIntegerValueField(.mouseEventWindowUnderMousePointer, value: Int64(observation.windowID))
        event.setIntegerValueField(.mouseEventWindowUnderMousePointerThatCanHandleThisEvent, value: Int64(observation.windowID))
    }
    public static func globalHitTest(_ point: CGPoint, observation: Observation) throws {
        // The public AppKit hit test respects transparent and ignoresMouseEvents windows.
        // Rectangle-only CGWindow enumeration can mistake an inert full-screen overlay for a blocker.
        let cocoaPoint = CGPoint(x: point.x, y: CGDisplayBounds(CGMainDisplayID()).height - point.y)
        let hit = NSWindow.windowNumber(at: cocoaPoint, belowWindowWithWindowNumber: 0)
        guard hit == Int(observation.windowID) else {
            throw ToolFailure("occluded_target", "Hit window \(hit) differs from target \(observation.windowID); global input was not sent")
        }
    }
}

/// Explicit, foreground-only temporary selection; never enables a new input source.
@MainActor public final class KeyboardInputSourceScope {
    private let original: TISInputSource
    private let selected: TISInputSource
    private var finished = false
    private static func identifier(_ source:TISInputSource) -> String {
        guard let p = TISGetInputSourceProperty(source,kTISPropertyInputSourceID) else { return "" }
        return Unmanaged<CFString>.fromOpaque(p).takeUnretainedValue() as String
    }
    public static func currentID() -> String { identifier(TISCopyCurrentKeyboardInputSource().takeRetainedValue()) }
    public init() throws {
        original = TISCopyCurrentKeyboardInputSource().takeRetainedValue()
        selected = TISCopyCurrentASCIICapableKeyboardLayoutInputSource().takeRetainedValue()
        guard !Self.identifier(original).isEmpty, !Self.identifier(selected).isEmpty else {
            throw ToolFailure("input_source_unavailable","Cannot identify current and ASCII keyboard sources")
        }
        guard TISSelectInputSource(selected) == noErr else {
            throw ToolFailure("input_source_unavailable","Cannot select the existing ASCII keyboard layout")
        }
    }
    public func verify() throws {
        guard Self.currentID() == Self.identifier(selected) else {
            throw ToolFailure("input_source_changed","Keyboard input source changed; input stopped")
        }
    }
    @discardableResult public func restore() -> [String:Any] {
        guard !finished else { return ["restored":Self.currentID() == Self.identifier(original)] }
        finished = true
        let current = Self.currentID()
        // Do not replace a user's intervening selection.
        if current == Self.identifier(selected) { _ = TISSelectInputSource(original) }
        return ["original":Self.identifier(original),"selected":Self.identifier(selected),
                "restored":Self.currentID() == Self.identifier(original),
                "verification":"Input source was reread; a concurrent different selection is preserved"]
    }
}
