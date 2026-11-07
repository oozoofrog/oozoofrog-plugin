// swiftc ../skills/mac-computer-use/scripts/mac-cu-src/SimulatorGestures.swift simulator-gestures-selfcheck.swift -o /tmp/mac-cu-gesture-selfcheck
import Foundation

// The self-check replaces device I/O; it never connects to a simulator.
struct ToolError: Error { let message: String; init(_ message: String) { self.message = message } }
struct ActiveScreen { let points: CGSize }
struct GestureContact { let id: Int; let point: CGPoint; let touching: Bool }
func screenSize(of device: NSObject) -> CGSize { CGSize(width: 1000, height: 1000) }
func udid(of device: NSObject) -> String { "selfcheck" }
func hidLink(for device: NSObject) throws -> NSObject { NSObject() }
final class GestureHIDLink {
    static var created = 0
    static var resets = 0
    static var sent: [[GestureContact]] = []
    static var failSend = false
    static var failReset = false
    init(device: NSObject) throws { Self.created += 1 }
    func send(_ contacts: [GestureContact], screen: ActiveScreen?) throws {
        if Self.failSend { throw ToolError("send failed") }
        Self.sent.append(contacts)
    }
    func reset(screen: ActiveScreen?) throws {
        Self.resets += 1
        if Self.failReset { throw ToolError("reset failed") }
    }
}

@main
enum SimulatorGestureSelfcheck {
    static func touch(_ id: Any, _ phase: String = "down", _ x: Any = 100, _ y: Any = 100) -> [String: Any] {
        ["id": id, "phase": phase, "x": x, "y": y]
    }
    static func frame(_ time: Any, _ touches: [[String: Any]]) -> [String: Any] { ["time": time, "touches": touches] }
    static func timeline(_ frames: [[String: Any]]) throws -> SimulatorGestureTimeline {
        try SimulatorGestureTimeline(arguments: ["frames": frames], size: CGSize(width: 1000, height: 1000))
    }
    static func reject(_ frames: [[String: Any]]) {
        do { _ = try timeline(frames); preconditionFailure("Accepted an invalid gesture") } catch is ToolError { } catch {
            preconditionFailure("Unexpected validation error: \(error)")
        }
    }
    static func clearIO() {
        simulatorGestureLinks.removeAll()
        GestureHIDLink.created = 0
        GestureHIDLink.resets = 0
        GestureHIDLink.sent = []
        GestureHIDLink.failSend = false
        GestureHIDLink.failReset = false
    }
    static func main() throws {
        reject([])
        reject([frame(0, [])])
        reject([frame(0, [touch(1)])])
        reject([frame(0, [touch(1, "move")])])
        reject([frame(0, [touch(1, "up")])])
        reject([frame(0, [touch(1), touch(1)])])
        reject([frame(0, [touch(1)]), frame(0.5, [touch(1)])])
        reject([frame(0, [touch(1)]), frame(0, [touch(1, "up")])])
        reject([frame(1, [touch(1)]), frame(0.5, [touch(1, "up")])])
        reject([frame(0, [touch(1)]), frame(10.01, [touch(1, "up")])])
        reject(Array(repeating: frame(0, []), count: SimulatorGestureTimeline.maximumFrames + 1))
        for time: Any in [-1, Double.infinity, Double.nan, true] { reject([frame(time, [touch(1)])]) }
        for id: Any in [0, 4, 1.5, true] { reject([frame(0, [touch(id)])]) }
        for x: Any in [-1, 1001, Double.infinity, Double.nan, true] { reject([frame(0, [touch(1, "down", x)])]) }
        reject([frame(0, [touch(1, "cancel")])])

        let three = try timeline([
            frame(0, [touch(1), touch(2, "down", 200), touch(3, "down", 300)]),
            frame(1, [touch(1, "move", 400), touch(2, "up", 200)]),
            frame(2, [touch(1, "up", 400), touch(3, "up", 300)])
        ])
        precondition(three.maximumContacts == 3)
        let samples = three.samples()
        let half = samples.first { abs($0.time - 0.5) < 0.000001 }!
        precondition(half.contacts.count == 3)
        precondition(half.contacts[0].point.x == 250)
        precondition(half.contacts[1].point.x == 200 && half.contacts[1].touching)
        precondition(half.contacts[2].point.x == 300 && half.contacts[2].touching)
        let second = samples.first { $0.time == 1 }!
        precondition(second.contacts.first { $0.id == 2 }?.touching == false)
        precondition(samples.last!.contacts.allSatisfy { !$0.touching })

        let delayed = try timeline([
            frame(0.5, [touch(1)]), frame(1, [touch(1, "move", 300), touch(2, "down", 500)]),
            frame(2, [touch(1, "up", 600), touch(2, "up", 800)])
        ]).samples()
        precondition(delayed.first!.time == 0.5)
        precondition(delayed.filter { $0.time < 1 }.allSatisfy { $0.contacts.count == 1 })
        let beforeUp = delayed.last { $0.time < 2 }!
        precondition(beforeUp.contacts.allSatisfy(\.touching))
        precondition(beforeUp.contacts[0].point.x > 590)
        let repeated = try timeline([
            frame(0, [touch(1)]), frame(0.1, [touch(1, "up")]),
            frame(0.2, [touch(1)]), frame(0.3, [touch(1, "up")])
        ])
        precondition(repeated.maximumContacts == 1 && repeated.samples().count == 4)
        let replaced = try timeline([
            frame(0, [touch(1), touch(2)]), frame(0.1, [touch(3), touch(1, "up")]),
            frame(0.2, [touch(2, "up"), touch(3, "up")])
        ])
        precondition(replaced.maximumContacts == 2)

        let quick = ["frames": [frame(0, [touch(1), touch(2), touch(3)]),
                                frame(0.001, [touch(1, "up"), touch(2, "up"), touch(3, "up")])]]
        clearIO()
        _ = try runSimulatorGesture(arguments: quick, device: NSObject(), screen: nil, cancelled: { false })
        precondition(GestureHIDLink.created == 1 && GestureHIDLink.resets == 2)
        precondition(GestureHIDLink.sent.count == 2 && GestureHIDLink.sent[0].count == 3)
        precondition(GestureHIDLink.sent[1].allSatisfy { !$0.touching })
        clearIO()
        GestureHIDLink.failSend = true
        do { _ = try runSimulatorGesture(arguments: quick, device: NSObject(), screen: nil, cancelled: { false }); preconditionFailure() }
        catch let error as ToolError { precondition(error.message == "send failed") }
        precondition(GestureHIDLink.resets == 2 && simulatorGestureLinks.isEmpty)
        clearIO()
        GestureHIDLink.failReset = true
        do { _ = try runSimulatorGesture(arguments: quick, device: NSObject(), screen: nil, cancelled: { false }); preconditionFailure() }
        catch let error as ToolError { precondition(error.message == "reset failed") }
        precondition(GestureHIDLink.resets == 2 && GestureHIDLink.sent.isEmpty && simulatorGestureLinks.isEmpty)
        clearIO()
        var checks = 0
        do {
            _ = try runSimulatorGesture(arguments: quick, device: NSObject(), screen: nil, cancelled: { checks += 1; return checks > 2 })
            preconditionFailure()
        } catch let error as ToolError { precondition(error.message.contains("cancelled")) }
        precondition(GestureHIDLink.resets == 2 && simulatorGestureLinks.isEmpty)
        clearIO()
        do { _ = try runSimulatorGesture(arguments: ["frames": []], device: NSObject(), screen: nil, cancelled: { false }); preconditionFailure() }
        catch is ToolError { }
        precondition(GestureHIDLink.created == 0)
        print("Simulator gesture validation, interpolation, atomic contacts and cleanup checks passed.")
    }
}
