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
        if route == "process" { event.postToPid(pid) } else { event.post(tap: .cghidEventTap) }
    }
    public static func keyEvents(key: String, modifiers: [String]) throws -> [CGEvent] {
        guard let code = keyCodes[key.lowercased()] else { throw ToolFailure("invalid_argument", "Unknown key name; use keyCode from the documented map") }
        let flags = try flags(modifiers)
        let source = CGEventSource(stateID: .privateState)
        return try [true, false].map { down in
            guard let event = CGEvent(keyboardEventSource: source, virtualKey: code, keyDown: down) else { throw ToolFailure("event_failed", "Cannot create key event") }
            event.flags = flags; return event
        }
    }
    public static func textEvents(_ text: String) throws -> [CGEvent] {
        let source = CGEventSource(stateID: .privateState)
        return try Geometry.unicodeChunks(text).flatMap { units -> [CGEvent] in
            try [true, false].map { down in
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
