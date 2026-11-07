// Raw UniversalHID digitizer reports: IndigoDigitizerEvent itself has only two contact fields.
import AppKit
import XPC

struct GestureContact {
    let id: Int
    let point: CGPoint
    let touching: Bool
}

/// Xcode 27.2's digitizer descriptor: report 9, five 40-bit contacts, five identities, remote timestamp.
// shortcut: this is the Xcode 27.2 report layout; recheck the shipped descriptor after a layout change.
func gestureHIDReport(_ contacts: [GestureContact], screen: ActiveScreen?, size: CGSize, timestamp: UInt64) throws -> Data {
    guard contacts.count <= 3, Set(contacts.map(\.id)).count == contacts.count,
          contacts.allSatisfy({ (1...3).contains($0.id) }) else {
        throw ToolError("A gesture report needs at most three distinct contact ids, from 1 to 3.")
    }
    guard size.width.isFinite, size.height.isFinite, size.width > 0, size.height > 0 else {
        throw ToolError("The simulator has no valid screen size for gestures.")
    }
    var bytes = [UInt8](repeating: 0, count: 58)
    bytes[0] = 9
    bytes[1] = UInt8(contacts.count)
    bytes[2] = 5
    for (slot, contact) in contacts.sorted(by: { $0.id < $1.id }).enumerated() {
        let at = screen?.normalized(contact.point) ?? CGPoint(x: contact.point.x / size.width, y: contact.point.y / size.height)
        guard at.x.isFinite, at.y.isFinite, (0...1).contains(at.x), (0...1).contains(at.y) else {
            throw ToolError("Gesture contact \(contact.id) is outside the simulator screen.")
        }
        let offset = 3 + slot * 5
        bytes[offset] = UInt8(contact.id - 1) | (contact.touching ? 0xC0 : 0)
        for (axis, value) in [at.x, at.y].enumerated() {
            let coordinate = UInt16((value * 65535).rounded())
            bytes[offset + 1 + axis * 2] = UInt8(truncatingIfNeeded: coordinate)
            bytes[offset + 2 + axis * 2] = UInt8(truncatingIfNeeded: coordinate >> 8)
        }
        // Contact records are packed, but index and identity survive a different finger lifting.
        bytes[40 + contact.id - 1] = UInt8(contact.id)
    }
    for byte in 0..<8 { bytes[45 + byte] = UInt8(truncatingIfNeeded: timestamp >> (byte * 8)) }
    return Data(bytes)
}

final class GestureHIDLink {
    private let deviceID: String
    private let connection: xpc_connection_t
    private let queue = DispatchQueue(label: "mac-cu.gesture-hid")
    private let lock = NSLock()
    private var failure: String?
    private let size: CGSize
    private var services: [UInt64: String] = [:]
    private var mainService: UInt64?
    private var lastService: UInt64?
    private var lastScreen: ActiveScreen?
    private var active: [GestureContact] = []
    private var warmed: Set<UInt64> = []

    init(device: NSObject) throws {
        deviceID = udid(of: device)
        size = screenSize(of: device)
        connection = try simulatorConnection(device, "com.apple.coredevice.feature.remote.universalhidservice")
        xpc_connection_set_target_queue(connection, queue)
        xpc_connection_set_event_handler(connection) { [weak self] event in
            if let self, let reason = Self.error(in: event) {
                self.lock.lock()
                if self.failure == nil { self.failure = reason }
                self.lock.unlock()
            }
        }
        xpc_connection_resume(connection)
        do {
            let payload = xpc_dictionary_create(nil, nil, 0)
            xpc_dictionary_set_value(payload, "connectedServices", xpc_dictionary_create(nil, nil, 0))
            let reply = try reply(to: message(payload), operation: "list gesture touchscreens")
            guard let listed = xpc_dictionary_get_array(reply, "connectedServices") else {
                throw ToolError("The simulator did not list its gesture touchscreens.")
            }
            xpc_array_apply(listed) { _, service in
                if xpc_get_type(service) == XPC_TYPE_DICTIONARY,
                   xpc_dictionary_get_uint64(service, "PrimaryUsagePage") == 0x0D,
                   xpc_dictionary_get_uint64(service, "PrimaryUsage") == 0x04 {
                    let display = xpc_dictionary_get_string(service, "displayUUID").map { String(cString: $0) } ?? ""
                    self.services[xpc_dictionary_get_uint64(service, "_ServiceID")] = display
                }
                return true
            }
            guard !services.isEmpty else { throw ToolError("The simulator has no UniversalHID touchscreen for gestures.") }
            let integrated = (displays(of: udid(of: device)) ?? []).filter {
                ($0["type"] as? [String: Any])?["integrated"] != nil
            }
            // A single-screen simulator omits active, even with its backlight on.
            let display = integrated.count == 1 ? integrated.first : integrated.first { $0["active"] as? Bool == true }
            if let uniqueID = display?["uniqueId"] as? String {
                mainService = services.first(where: { $0.value.caseInsensitiveCompare(uniqueID) == .orderedSame })?.key
            }
        } catch {
            xpc_connection_cancel(connection)
            throw error
        }
    }

    deinit { xpc_connection_cancel(connection) }

    func send(_ contacts: [GestureContact], screen: ActiveScreen?) throws {
        let service = try service(for: screen)
        if let previous = lastService, previous != service, !active.isEmpty {
            throw ToolError("The simulator screen changed during a gesture. Release the contacts and start again.")
        }
        var frame = contacts
        let ids = Set(contacts.map(\.id))
        frame += active.filter { !ids.contains($0.id) }.map { GestureContact(id: $0.id, point: $0.point, touching: false) }
        try sendReport(frame, screen: screen, service: service)
    }

    func reset(screen: ActiveScreen?) throws {
        let service = try lastService ?? self.service(for: screen)
        defer {
            active = []; lastService = nil; lastScreen = nil
            showSimulatorTouches(deviceID, contacts: [], screen: screen)
        }
        var releaseError: Error?
        if !active.isEmpty {
            do {
                try sendReport(active.map { GestureContact(id: $0.id, point: $0.point, touching: false) }, screen: lastScreen, service: service)
            } catch { releaseError = error }
        }
        let reset = xpc_dictionary_create(nil, nil, 0)
        xpc_dictionary_set_uint64(reset, "_0", service)
        let payload = xpc_dictionary_create(nil, nil, 0)
        xpc_dictionary_set_value(payload, "resetGestureState", reset)
        xpc_connection_send_message(connection, message(payload))
        try barrier()
        if let releaseError { throw releaseError }
        if !warmed.contains(service) {
            // dtuhidd queues early touches until backboardd opens the virtual touchscreen.
            try sendReport([GestureContact(id: 1, point: .zero, touching: false)], screen: screen, service: service)
            Thread.sleep(forTimeInterval: 1)  // Xcode 27.2 buffered the first contacts for about 0.75 s.
            warmed.insert(service)
        }
    }

    private func service(for screen: ActiveScreen?) throws -> UInt64 {
        let expected = 0x100 | (screen?.target ?? 0)
        if screen?.foldable != true, let mainService { return mainService }
        if services[expected] != nil { return expected }
        if screen?.foldable != true, services.count == 1, let only = services.keys.first { return only }
        let listed = services.sorted(by: { $0.key < $1.key }).map { "0x\(String($0.key, radix: 16)) (display \($0.value.isEmpty ? "unknown" : $0.value))" }.joined(separator: ", ")
        throw ToolError("The simulator screen has no matching UniversalHID touchscreen for gestures: expected 0x\(String(expected, radix: 16)); available: \(listed).")
    }

    private func sendReport(_ contacts: [GestureContact], screen: ActiveScreen?, service: UInt64) throws {
        // UniversalHID.HIDTime.now uses raw mach ticks; dtuhidd adds remote time as a child event.
        let report = try gestureHIDReport(contacts, screen: screen, size: size, timestamp: mach_absolute_time())
        lastService = service
        lastScreen = screen
        active = contacts  // Keep even pending lifts until dtuhidd acknowledges them.
        let send = xpc_dictionary_create(nil, nil, 0)
        report.withUnsafeBytes { xpc_dictionary_set_data(send, "_0", $0.baseAddress!, report.count) }
        xpc_dictionary_set_uint64(send, "_1", service)
        let payload = xpc_dictionary_create(nil, nil, 0)
        xpc_dictionary_set_value(payload, "send", send)
        xpc_connection_send_message(connection, message(payload))
        try barrier()
        active = contacts.filter(\.touching)
        showSimulatorTouches(deviceID, contacts: contacts, screen: screen)
    }

    private func message(_ payload: xpc_object_t? = nil, barrier: Bool = false) -> xpc_object_t {
        let message = xpc_dictionary_create(nil, nil, 0)
        xpc_dictionary_set_string(message, "messageType", "Request")
        xpc_dictionary_set_bool(message, "isBarrier", barrier)
        if let payload { xpc_dictionary_set_value(message, "payload", payload) }
        return message
    }

    private func barrier() throws {
        // A local send barrier only drains the client's queue; this acknowledgement comes from dtuhidd.
        _ = try reply(to: message(barrier: true), operation: "acknowledge a gesture report")
    }

    private func reply(to message: xpc_object_t, operation: String) throws -> xpc_object_t {
        try checkFailure()
        let done = DispatchSemaphore(value: 0)
        var result: xpc_object_t?
        xpc_connection_send_message_with_reply(connection, message, queue) { event in
            result = event
            done.signal()
        }
        guard done.wait(timeout: .now() + 2) == .success, let result else {
            throw ToolError("The simulator did not \(operation) within 2 seconds.")
        }
        if let reason = Self.error(in: result) { throw ToolError("Simulator gesture HID: \(reason)") }
        try checkFailure()
        guard xpc_get_type(result) == XPC_TYPE_DICTIONARY else { throw ToolError("The simulator gave an invalid gesture HID reply.") }
        return result
    }

    private func checkFailure() throws {
        lock.lock()
        let reason = failure
        lock.unlock()
        if let reason { throw ToolError("Simulator gesture HID: \(reason)") }
    }

    private static func error(in event: xpc_object_t) -> String? {
        if xpc_get_type(event) == XPC_TYPE_ERROR {
            return xpc_dictionary_get_string(event, XPC_ERROR_KEY_DESCRIPTION).map { String(cString: $0) } ?? "connection failed"
        }
        guard xpc_get_type(event) == XPC_TYPE_DICTIONARY,
              let error = xpc_dictionary_get_value(event, "CoreDevice.error") ?? xpc_dictionary_get_value(event, "error") else { return nil }
        let description = xpc_copy_description(error)
        defer { free(description) }
        return String(cString: description)
    }
}
