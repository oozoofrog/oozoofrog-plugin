// A complete, validated touch timeline: one call owns its contacts from the first down to the last up.
import Foundation
import CoreGraphics

enum SimulatorGesturePhase: String {
    case down, move, up
}

struct SimulatorGestureTouch {
    let id: Int
    let phase: SimulatorGesturePhase
    let point: CGPoint
}

struct SimulatorGestureFrame {
    let time: Double
    let touches: [SimulatorGestureTouch]
    let active: [Int: CGPoint]

    var contacts: [GestureContact] {
        (active.map { GestureContact(id: $0.key, point: $0.value, touching: true) }
            + touches.filter { $0.phase == .up }.map { GestureContact(id: $0.id, point: $0.point, touching: false) })
            .sorted { $0.id < $1.id }
    }
}

struct SimulatorGestureSample {
    let time: Double
    let contacts: [GestureContact]
}

struct SimulatorGestureTimeline {
    static let maximumDuration = 10.0
    static let maximumFrames = 1201
    let frames: [SimulatorGestureFrame]
    let maximumContacts: Int
    var duration: Double { frames.last?.time ?? 0 }

    init(arguments: [String: Any], size: CGSize) throws {
        guard size.width.isFinite, size.height.isFinite, size.width > 0, size.height > 0 else {
            throw ToolError("The simulator has no valid screen size for a gesture.")
        }
        guard let input = arguments["frames"] as? [[String: Any]], !input.isEmpty,
              input.count <= Self.maximumFrames else {
            throw ToolError("gesture needs frames: 1...\(Self.maximumFrames) timestamped touch frames.")
        }
        func number(_ value: Any?) -> Double? {
            guard let number = value as? NSNumber, CFGetTypeID(number) != CFBooleanGetTypeID() else { return nil }
            let value = number.doubleValue
            return value.isFinite ? value : nil
        }
        var parsed: [SimulatorGestureFrame] = []
        var active: [Int: CGPoint] = [:]
        var previousTime = -Double.infinity
        var maximumContacts = 0
        for (index, item) in input.enumerated() {
            let location = "gesture frames[\(index)]"
            guard let time = number(item["time"]), time >= 0, time <= Self.maximumDuration,
                  time > previousTime else {
                throw ToolError("\(location).time must increase strictly, from 0 to \(Int(Self.maximumDuration)) seconds; combine simultaneous changes in one frame.")
            }
            guard let changes = item["touches"] as? [[String: Any]], changes.count <= 3 else {
                throw ToolError("\(location).touches must contain at most 3 contact changes.")
            }
            var seen: Set<Int> = []
            var touches: [SimulatorGestureTouch] = []
            for change in changes {
                guard let value = number(change["id"]), value.rounded() == value, (1...3).contains(value) else {
                    throw ToolError("\(location): each touch id must be an integer from 1 to 3.")
                }
                let id = Int(value)
                guard seen.insert(id).inserted else {
                    throw ToolError("\(location): touch id \(id) occurs twice; combine its change into one entry.")
                }
                guard let name = change["phase"] as? String, let phase = SimulatorGesturePhase(rawValue: name) else {
                    throw ToolError("\(location): touch \(id) phase must be down, move or up.")
                }
                guard let x = number(change["x"]), let y = number(change["y"]),
                      x >= 0, y >= 0, x <= size.width, y <= size.height else {
                    throw ToolError("\(location): touch \(id) needs finite x and y within the \(Int(size.width))×\(Int(size.height)) point screen.")
                }
                let point = CGPoint(x: x, y: y)
                switch phase {
                case .down:
                    guard active[id] == nil else { throw ToolError("\(location): touch \(id) is already down.") }
                    active[id] = point
                case .move, .up:
                    guard active[id] != nil else { throw ToolError("\(location): touch \(id) must go down before \(name).") }
                    if phase == .up { active[id] = nil } else { active[id] = point }
                }
                touches.append(SimulatorGestureTouch(id: id, phase: phase, point: point))
            }
            maximumContacts = max(maximumContacts, active.count)
            parsed.append(SimulatorGestureFrame(time: time, touches: touches, active: active))
            previousTime = time
        }
        guard maximumContacts > 0 else { throw ToolError("gesture needs at least one down and up contact.") }
        guard active.isEmpty else { throw ToolError("gesture must end with every contact up; still down: \(active.keys.sorted()).") }
        frames = parsed
        self.maximumContacts = maximumContacts
    }

    /// Interpolate only contacts already down; a later down must not start before its timestamp.
    func samples() -> [SimulatorGestureSample] {
        var result: [SimulatorGestureSample] = []
        var previous: SimulatorGestureFrame?
        for frame in frames {
            if let before = previous, !before.active.isEmpty {
                let destinations = Dictionary(uniqueKeysWithValues: frame.touches
                    .filter { $0.phase != .down }.map { ($0.id, $0.point) })
                let moving = before.active.contains { id, point in destinations[id].map { $0 != point } ?? false }
                if moving {
                    let interval = frame.time - before.time
                    var tick = 1
                    while Double(tick) / 60 < interval {
                        let elapsed = Double(tick) / 60, fraction = elapsed / interval
                        let contacts = before.active.map { id, point -> GestureContact in
                            let destination = destinations[id] ?? point
                            return GestureContact(id: id,
                                point: CGPoint(x: point.x + (destination.x - point.x) * fraction,
                                               y: point.y + (destination.y - point.y) * fraction), touching: true)
                        }.sorted { $0.id < $1.id }
                        result.append(SimulatorGestureSample(time: before.time + elapsed, contacts: contacts))
                        tick += 1
                    }
                }
            }
            result.append(SimulatorGestureSample(time: frame.time, contacts: frame.contacts))
            previous = frame
        }
        return result
    }
}

var simulatorGestureLinks: [String: GestureHIDLink] = [:]

func runSimulatorGesture(arguments: [String: Any], device: NSObject, screen: ActiveScreen?, cancelled: () -> Bool) throws -> String {
    let timeline = try SimulatorGestureTimeline(arguments: arguments, size: screen?.points ?? screenSize(of: device))
    guard !cancelled() else { throw ToolError("The gesture was cancelled before it started.") }
    _ = try hidLink(for: device)
    let id = udid(of: device)
    let link: GestureHIDLink
    if let cached = simulatorGestureLinks[id] { link = cached } else {
        link = try GestureHIDLink(device: device)
        simulatorGestureLinks[id] = link
    }
    var finished = false
    defer {
        if !finished {
            try? link.reset(screen: screen)
            simulatorGestureLinks[id] = nil
        }
    }
    try link.reset(screen: screen)
    let start = ProcessInfo.processInfo.systemUptime
    for sample in timeline.samples() {
        while true {
            guard !cancelled() else { throw ToolError("The gesture was cancelled.") }
            let remaining = start + sample.time - ProcessInfo.processInfo.systemUptime
            if remaining <= 0 { break }
            Thread.sleep(forTimeInterval: min(remaining, 0.01))
        }
        if !sample.contacts.isEmpty { try link.send(sample.contacts, screen: screen) }
    }
    try link.reset(screen: screen)
    finished = true
    return "Sent a gesture with up to \(timeline.maximumContacts) \(timeline.maximumContacts == 1 ? "finger" : "fingers") (\(timeline.frames.count) frames, \(String(format: "%.3f", timeline.duration)) seconds)."
}
