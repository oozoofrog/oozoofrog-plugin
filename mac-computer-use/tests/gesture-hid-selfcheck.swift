// Build with SimulatorGestureHID.swift only; these stubs make accidental device access fail immediately.
import AppKit
import XPC

struct ToolError: Error { let message: String; init(_ message: String) { self.message = message } }
struct ActiveScreen {
    let target: UInt64 = 1
    let foldable = true
    func normalized(_ point: CGPoint) -> CGPoint { CGPoint(x: point.y / 400, y: (200 - point.x) / 200) }
}
func simulatorConnection(_ device: NSObject, _ service: String) throws -> xpc_connection_t { fatalError("Offline selfcheck opened a device") }
func screenSize(of device: NSObject) -> CGSize { fatalError("Offline selfcheck read a device") }
func udid(of device: NSObject) -> String { fatalError("Offline selfcheck read a device") }
func displays(of id: String) -> [[String: Any]]? { fatalError("Offline selfcheck read a device") }
func showSimulatorTouches(_ id: String, contacts: [GestureContact], screen: ActiveScreen?) { fatalError("Offline selfcheck displayed a device") }

@main
struct GestureHIDSelfcheck {
    static func main() throws {
        let size = CGSize(width: 200, height: 400)
        let timestamp: UInt64 = 0x0807060504030201
        func encode(_ contacts: [GestureContact], screen: ActiveScreen? = nil) throws -> [UInt8] {
            Array(try gestureHIDReport(contacts, screen: screen, size: size, timestamp: timestamp))
        }
        let three = try encode([
            GestureContact(id: 3, point: CGPoint(x: 200, y: 400), touching: true),
            GestureContact(id: 1, point: .zero, touching: true),
            GestureContact(id: 2, point: CGPoint(x: 100, y: 200), touching: true),
        ])
        assert(three.count == 58 && Array(three[0..<3]) == [9, 3, 5])
        assert(three[3] == 0xC0 && three[8] == 0xC1 && three[13] == 0xC2)
        assert(Array(three[4..<8]) == [0, 0, 0, 0])
        assert(Array(three[9..<13]) == [0, 128, 0, 128])
        assert(Array(three[14..<18]) == [255, 255, 255, 255])
        assert(Array(three[40..<45]) == [1, 2, 3, 0, 0])
        assert(Array(three[45..<53]) == [1, 2, 3, 4, 5, 6, 7, 8])
        let remaining = try encode([GestureContact(id: 3, point: CGPoint(x: 100, y: 200), touching: true)])
        assert(remaining[1] == 1 && remaining[3] == 0xC2)
        assert(Array(remaining[40..<45]) == [0, 0, 3, 0, 0])
        let lifted = try encode([GestureContact(id: 2, point: CGPoint(x: 100, y: 200), touching: false)])
        assert(lifted[1] == 1 && lifted[3] == 1 && lifted[41] == 2)
        let turned = try encode([GestureContact(id: 1, point: CGPoint(x: 200, y: 400), touching: true)], screen: ActiveScreen())
        assert(Array(turned[4..<8]) == [255, 255, 0, 0])
        let empty = try encode([])
        assert(empty[1] == 0)
        for bad in [
            [GestureContact(id: 0, point: .zero, touching: true)],
            [GestureContact(id: 4, point: .zero, touching: true)],
            [GestureContact(id: 1, point: .zero, touching: true), GestureContact(id: 1, point: .zero, touching: true)],
            [GestureContact(id: 1, point: CGPoint(x: -1, y: 0), touching: true)],
            [GestureContact(id: 1, point: CGPoint(x: CGFloat.infinity, y: 0), touching: true)],
            [GestureContact(id: 1, point: CGPoint(x: CGFloat.nan, y: 0), touching: true)],
        ] {
            do { _ = try encode(bad); assertionFailure("Accepted an invalid gesture report") } catch is ToolError { }
        }
        print("Gesture HID selfcheck passed: three contacts, stable identities after lifts, rotation, timestamps and invalid input.")
    }
}
