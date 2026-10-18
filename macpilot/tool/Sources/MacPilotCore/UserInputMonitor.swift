import AppKit
import ApplicationServices

enum InputOwnership {
    // An attribution tag, not a security credential or a physical-device claim.
    static let tag = Int64.random(in: 1...Int64.max)
    static func stamp(_ event: CGEvent) { event.setIntegerValueField(.eventSourceUserData, value: tag) }
    static func owns(_ event: CGEvent) -> Bool {
        event.getIntegerValueField(.eventSourceUserData) == tag
            && event.getIntegerValueField(.eventSourceUnixProcessID) == Int64(getpid())
    }
}

/// Passive monitoring only: never swallows, remaps, records, or replays user input.
final class UserInputMonitor {
    private var tap: CFMachPort?
    private var source: CFRunLoopSource?
    private(set) var reason: String?
    private(set) var externalEvents = 0
    init() throws {
        guard CGPreflightListenEventAccess() else {
            throw ToolFailure("input_monitor_denied", "Global input needs Input Monitoring so MacPilot can yield to the user before sending events")
        }
        let types: [CGEventType] = [.keyDown, .keyUp, .flagsChanged, .mouseMoved, .leftMouseDown, .leftMouseUp,
                                    .rightMouseDown, .otherMouseDown, .leftMouseDragged, .rightMouseDragged, .scrollWheel]
        let mask = types.reduce(CGEventMask(0)) { $0 | (CGEventMask(1) << $1.rawValue) }
        tap = CGEvent.tapCreate(tap: .cgSessionEventTap, place: .headInsertEventTap, options: .listenOnly,
                               eventsOfInterest: mask, callback: { _, type, event, raw in
            guard let raw else { return Unmanaged.passUnretained(event) }
            let monitor = Unmanaged<UserInputMonitor>.fromOpaque(raw).takeUnretainedValue()
            monitor.receive(type, event: event)
            return Unmanaged.passUnretained(event)
        }, userInfo: Unmanaged.passUnretained(self).toOpaque())
        guard let tap, let source = CFMachPortCreateRunLoopSource(kCFAllocatorDefault, tap, 0) else {
            throw ToolFailure("input_monitor_unavailable", "A passive input monitor could not be created; no global input was sent")
        }
        self.source = source
        CFRunLoopAddSource(CFRunLoopGetMain(), source, .commonModes); CGEvent.tapEnable(tap: tap, enable: true)
        guard CGEvent.tapIsEnabled(tap: tap) else { throw ToolFailure("input_monitor_unavailable", "Input monitoring did not start") }
    }
    // Kept separate for tests of event provenance without a system event tap.
    init(testing: Bool) {}
    func receive(_ type: CGEventType, event: CGEvent) {
        if type == .tapDisabledByTimeout || type == .tapDisabledByUserInput {
            reason = "input_monitor_lost"
        } else if !InputOwnership.owns(event) {
            externalEvents += 1; reason = "user_input_interrupted"
        }
    }
    func verify() throws {
        if let reason { throw ToolFailure(reason, "System input stopped; observe the current target and explicitly resume the interrupted task before sending more input") }
        guard let tap, CGEvent.tapIsEnabled(tap: tap) else {
            throw ToolFailure("input_monitor_lost", "Input monitoring stopped; pending owned keys are being released")
        }
    }
    deinit {
        if let tap { CGEvent.tapEnable(tap: tap, enable: false); CFMachPortInvalidate(tap) }
        if let source { CFRunLoopRemoveSource(CFRunLoopGetMain(), source, .commonModes) }
    }
}
