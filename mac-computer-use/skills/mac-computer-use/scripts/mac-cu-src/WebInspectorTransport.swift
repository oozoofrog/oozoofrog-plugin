// Byte streams to a Web Inspector service: the simulator's webinspectord_sim Unix socket, and a USB device
// through usbmuxd, lockdownd (TLS with the Mac's pair record) and the com.apple.webinspector service.
// Ported from the iwi CLI.

import Foundation
import Security

struct InspectorError: Error, CustomStringConvertible {
    let description: String
    init(_ description: String) { self.description = description }
}

// MARK: - Byte streams

/// read returns 0 at the end of the stream.
protocol ByteStream: AnyObject {
    func read(_ buf: UnsafeMutableRawPointer, _ count: Int) throws -> Int
    func write(_ data: Data) throws
    func close()
}

extension ByteStream {
    func readExactly(_ n: Int) throws -> Data {
        var out = Data(count: n)
        var got = 0
        try out.withUnsafeMutableBytes { p in
            while got < n {
                let r = try read(p.baseAddress! + got, n - got)
                if r == 0 { throw InspectorError("The connection closed.") }
                got += r
            }
        }
        return out
    }

    /// A 4-byte big-endian length and the payload (the framing of lockdown and of the Remote Web Inspector).
    func readFrame() throws -> Data {
        let h = try readExactly(4)
        let n = Int(h[0]) << 24 | Int(h[1]) << 16 | Int(h[2]) << 8 | Int(h[3])
        guard n < 1 << 28 else { throw InspectorError("A frame is too long: \(n) bytes.") }
        return try readExactly(n)
    }

    func writeFrame(_ payload: Data) throws {
        var f = Data(capacity: payload.count + 4)
        withUnsafeBytes(of: UInt32(payload.count).bigEndian) { f.append(contentsOf: $0) }
        f.append(payload)
        try write(f)
    }
}

final class FDStream: ByteStream {
    let fd: Int32
    private var closed = false
    private let lock = NSLock()

    init(fd: Int32) {
        self.fd = fd
        var one: Int32 = 1
        setsockopt(fd, SOL_SOCKET, SO_NOSIGPIPE, &one, socklen_t(MemoryLayout<Int32>.size))
    }

    static func unix(_ path: String) throws -> FDStream {
        let fd = socket(AF_UNIX, SOCK_STREAM, 0)
        guard fd >= 0 else { throw InspectorError("No socket: \(String(cString: strerror(errno)))") }
        var addr = sockaddr_un()
        addr.sun_family = sa_family_t(AF_UNIX)
        let bytes = Array(path.utf8CString)
        guard bytes.count <= MemoryLayout.size(ofValue: addr.sun_path) else { Darwin.close(fd); throw InspectorError("The socket path is too long.") }
        withUnsafeMutableBytes(of: &addr.sun_path) { dst in
            for (i, b) in bytes.enumerated() { dst[i] = UInt8(bitPattern: b) }
        }
        let rc = withUnsafePointer(to: &addr) {
            $0.withMemoryRebound(to: sockaddr.self, capacity: 1) { connect(fd, $0, socklen_t(MemoryLayout<sockaddr_un>.size)) }
        }
        guard rc == 0 else {
            let e = String(cString: strerror(errno))
            Darwin.close(fd)
            throw InspectorError("No connection to \(path): \(e)")
        }
        return FDStream(fd: fd)
    }

    func read(_ buf: UnsafeMutableRawPointer, _ count: Int) throws -> Int {
        while true {
            let r = Darwin.read(fd, buf, count)
            if r >= 0 { return r }
            if errno == EINTR { continue }
            throw InspectorError(String(cString: strerror(errno)))
        }
    }

    func write(_ data: Data) throws {
        try data.withUnsafeBytes { p in
            var off = 0
            while off < p.count {
                let r = Darwin.write(fd, p.baseAddress! + off, p.count - off)
                if r < 0 {
                    if errno == EINTR { continue }
                    throw InspectorError(String(cString: strerror(errno)))
                }
                off += r
            }
        }
    }

    func close() {
        lock.lock(); defer { lock.unlock() }
        if closed { return }
        closed = true
        shutdown(fd, SHUT_RDWR)
        Darwin.close(fd)
    }

    deinit { close() }
}

// MARK: - TLS (SecureTransport)

/// TLS on an FDStream. The client authenticates with the host certificate that lockdown asks for. The
/// device certificate is self-signed, so the stream does not verify it. A SecureTransport context is not
/// thread-safe: the socket is non-blocking, poll waits, and SSLRead and SSLWrite run only in the lock.
final class TLSStream: ByteStream {
    private let base: FDStream
    private var ctx: SSLContext
    private let lock = NSLock()

    init(_ base: FDStream, identity: SecIdentity) throws {
        guard let c = SSLCreateContext(nil, .clientSide, .streamType) else { throw InspectorError("No TLS context.") }
        self.base = base
        self.ctx = c
        _ = fcntl(base.fd, F_SETFL, fcntl(base.fd, F_GETFL) | O_NONBLOCK)

        let readCb: SSLReadFunc = { conn, data, len in
            let fd = Unmanaged<TLSStream>.fromOpaque(conn).takeUnretainedValue().base.fd
            let want = len.pointee
            while true {
                let r = Darwin.read(fd, data, want)
                if r > 0 { len.pointee = r; return r < want ? errSSLWouldBlock : noErr }
                len.pointee = 0
                if r == 0 { return errSSLClosedGraceful }
                if errno == EINTR { continue }
                return errno == EAGAIN ? errSSLWouldBlock : errSSLClosedAbort
            }
        }
        let writeCb: SSLWriteFunc = { conn, data, len in
            let fd = Unmanaged<TLSStream>.fromOpaque(conn).takeUnretainedValue().base.fd
            let want = len.pointee
            var off = 0
            while off < want {
                let r = Darwin.write(fd, data + off, want - off)
                if r > 0 { off += r; continue }
                if r < 0 && errno == EINTR { continue }
                if r < 0 && errno == EAGAIN {
                    var p = pollfd(fd: fd, events: Int16(POLLOUT), revents: 0)
                    poll(&p, 1, 1000)
                    continue
                }
                len.pointee = off
                return errSSLClosedAbort
            }
            len.pointee = off
            return noErr
        }
        try Self.check(SSLSetIOFuncs(c, readCb, writeCb), "SSLSetIOFuncs")
        try Self.check(SSLSetConnection(c, Unmanaged.passUnretained(self).toOpaque()), "SSLSetConnection")
        try Self.check(SSLSetCertificate(c, [identity] as CFArray), "SSLSetCertificate")
        try Self.check(SSLSetProtocolVersionMin(c, .tlsProtocol1), "SSLSetProtocolVersionMin")
        // The device certificate is self-signed: stop at server authentication, then continue without a check.
        try Self.check(SSLSetSessionOption(c, .breakOnServerAuth, true), "SSLSetSessionOption")

        var r: OSStatus
        repeat {
            r = SSLHandshake(c)
            if r == errSSLWouldBlock { wait(POLLIN) }
        } while r == errSSLWouldBlock || r == Self.serverAuthCompleted
        try Self.check(r, "The TLS handshake")
    }

    private static let serverAuthCompleted: OSStatus = -9841   // errSSLServerAuthCompleted (not in Swift)

    private static func check(_ s: OSStatus, _ what: String) throws {
        if s != noErr { throw InspectorError("\(what) failed (OSStatus \(s)).") }
    }

    private func wait(_ events: Int32) {
        var p = pollfd(fd: base.fd, events: Int16(events), revents: 0)
        poll(&p, 1, 500)
    }

    func read(_ buf: UnsafeMutableRawPointer, _ count: Int) throws -> Int {
        while true {
            lock.lock()
            var n = 0
            let r = SSLRead(ctx, buf, count, &n)
            lock.unlock()
            if n > 0 { return n }
            switch r {
            case errSSLWouldBlock: wait(POLLIN)
            case errSSLClosedGraceful, errSSLClosedAbort: return 0
            case noErr: continue
            default: throw InspectorError("SSLRead failed (OSStatus \(r)).")
            }
        }
    }

    func write(_ data: Data) throws {
        try data.withUnsafeBytes { p in
            lock.lock(); defer { lock.unlock() }
            var off = 0
            while off < p.count {
                var n = 0
                let r = SSLWrite(ctx, p.baseAddress! + off, p.count - off, &n)
                off += n
                if r == errSSLWouldBlock { wait(POLLOUT) } else if r != noErr { throw InspectorError("SSLWrite failed (OSStatus \(r)).") }
            }
        }
    }

    func close() { base.close() }
}

// MARK: - usbmuxd

struct MuxDevice: Hashable {
    let id: Int
    let serial: String
    let isUSB: Bool
}

struct PairRecord {
    let hostID: String
    let systemBUID: String
    let certificate: Data
    let privateKey: Data

    /// The SecIdentity that SecureTransport needs, made in memory without the keychain.
    /// The system openssl (/usr/bin/openssl) changes the PEM to PKCS#12.
    func identity() throws -> SecIdentity {
        let p12 = try runTool("/usr/bin/openssl", ["pkcs12", "-export", "-passout", "pass:x"], input: privateKey + Data("\n".utf8) + certificate)
        var items: CFArray?
        let opts: [String: Any] = [kSecImportExportPassphrase as String: "x", kSecImportToMemoryOnly as String: true]
        let st = SecPKCS12Import(p12 as CFData, opts as CFDictionary, &items)
        guard st == errSecSuccess, let first = (items as? [[String: Any]])?.first,
              let id = first[kSecImportItemIdentity as String] else {
            throw InspectorError("The pair certificate did not import as a SecIdentity (OSStatus \(st)).")
        }
        return id as! SecIdentity
    }
}

/// Runs a command with input on its stdin (not mac-cu's stdin: that is the MCP channel) and returns its stdout.
@discardableResult
func runTool(_ path: String, _ args: [String], input: Data? = nil) throws -> Data {
    let p = Process()
    p.executableURL = URL(fileURLWithPath: path)
    p.arguments = args
    let out = Pipe(), inp = Pipe()
    p.standardOutput = out
    p.standardError = FileHandle.nullDevice
    p.standardInput = inp
    try p.run()
    if let input { inp.fileHandleForWriting.write(input) }
    try? inp.fileHandleForWriting.close()
    let data = out.fileHandleForReading.readDataToEndOfFile()
    p.waitUntilExit()
    guard p.terminationStatus == 0 else { throw InspectorError("\(path) exited with \(p.terminationStatus).") }
    return data
}

enum Usbmux {
    static let path = "/var/run/usbmuxd"

    private static func send(_ s: FDStream, _ msg: [String: Any]) throws {
        var m = msg
        m["ClientVersionString"] = "mac-cu"
        m["ProgName"] = "mac-cu"
        let body = try PropertyListSerialization.data(fromPropertyList: m, format: .xml, options: 0)
        var packet = Data()
        for v in [UInt32(16 + body.count), 1, 8, 1] { withUnsafeBytes(of: v.littleEndian) { packet.append(contentsOf: $0) } }
        try s.write(packet + body)
    }

    private static func recv(_ s: FDStream) throws -> [String: Any] {
        let h = try s.readExactly(16)
        let len = Int(UInt32(littleEndian: h.withUnsafeBytes { $0.loadUnaligned(as: UInt32.self) }))
        let body = try s.readExactly(len - 16)
        return try PropertyListSerialization.propertyList(from: body, format: nil) as? [String: Any] ?? [:]
    }

    /// Sends one request on a new connection and returns the answer.
    private static func call(_ msg: [String: Any]) throws -> [String: Any] {
        let s = try FDStream.unix(path)
        defer { s.close() }
        try send(s, msg)
        return try recv(s)
    }

    static func devices() throws -> [MuxDevice] {
        let list = try call(["MessageType": "ListDevices"])["DeviceList"] as? [[String: Any]] ?? []
        var bySerial: [String: MuxDevice] = [:]
        for d in list {
            guard let props = d["Properties"] as? [String: Any],
                  let id = props["DeviceID"] as? Int, let serial = props["SerialNumber"] as? String else { continue }
            let dev = MuxDevice(id: id, serial: serial, isUSB: props["ConnectionType"] as? String == "USB")
            if bySerial[serial] == nil || dev.isUSB { bySerial[serial] = dev }
        }
        return bySerial.values.sorted { $0.serial < $1.serial }
    }

    /// After the connection, the stream is a raw tunnel to the port of the device.
    static func connect(_ dev: MuxDevice, port: UInt16) throws -> FDStream {
        let s = try FDStream.unix(path)
        do {
            try send(s, ["MessageType": "Connect", "DeviceID": dev.id, "PortNumber": Int(port.byteSwapped)])
            let r = try recv(s)
            guard r["Number"] as? Int == 0 else { throw InspectorError("The device refused port \(port) (usbmuxd code \(r["Number"] ?? "?")).") }
            return s
        } catch { s.close(); throw error }
    }

    static func pairRecord(udid: String) throws -> PairRecord {
        let r = try call(["MessageType": "ReadPairRecord", "PairRecordID": udid])
        guard let data = r["PairRecordData"] as? Data,
              let p = try PropertyListSerialization.propertyList(from: data, format: nil) as? [String: Any],
              let hostID = p["HostID"] as? String, let buid = p["SystemBUID"] as? String,
              let cert = p["HostCertificate"] as? Data, let key = p["HostPrivateKey"] as? Data else {
            throw InspectorError("The device is not paired with this Mac. Unlock it and choose Trust This Computer.")
        }
        return PairRecord(hostID: hostID, systemBUID: buid, certificate: cert, privateKey: key)
    }
}

// MARK: - lockdown

struct DeviceInfo {
    var name = "", productVersion = "", buildVersion = "", productType = ""
}

enum Lockdown {
    private static func rpc(_ s: ByteStream, _ req: [String: Any]) throws -> [String: Any] {
        var r = req
        r["Label"] = "mac-cu"
        try s.writeFrame(PropertyListSerialization.data(fromPropertyList: r, format: .xml, options: 0))
        let d = try PropertyListSerialization.propertyList(from: s.readFrame(), format: nil) as? [String: Any] ?? [:]
        if let e = d["Error"] as? String { throw InspectorError("lockdown \(req["Request"] ?? ""): \(e)") }
        return d
    }

    /// Opens a lockdownd session, reads the device information, and returns a stream to com.apple.webinspector.
    static func openWebInspector(_ dev: MuxDevice) throws -> (stream: ByteStream, info: DeviceInfo) {
        let pair = try Usbmux.pairRecord(udid: dev.serial)
        let identity = try pair.identity()

        let raw = try Usbmux.connect(dev, port: 62078)
        defer { raw.close() }
        var s: ByteStream = raw
        _ = try rpc(s, ["Request": "QueryType"])
        let session = try rpc(s, ["Request": "StartSession", "HostID": pair.hostID, "SystemBUID": pair.systemBUID])
        if session["EnableSessionSSL"] as? Bool == true { s = try TLSStream(raw, identity: identity) }

        let values = try rpc(s, ["Request": "GetValue"])["Value"] as? [String: Any] ?? [:]
        let info = DeviceInfo(name: values["DeviceName"] as? String ?? dev.serial,
                              productVersion: values["ProductVersion"] as? String ?? "",
                              buildVersion: values["BuildVersion"] as? String ?? "",
                              productType: values["ProductType"] as? String ?? "")

        let svc = try rpc(s, ["Request": "StartService", "Service": "com.apple.webinspector"])
        guard let port = svc["Port"] as? Int else { throw InspectorError("No port for the webinspector service.") }
        let conn = try Usbmux.connect(dev, port: UInt16(port))
        if svc["EnableServiceSSL"] as? Bool == true {
            do { return (try TLSStream(conn, identity: identity), info) } catch { conn.close(); throw error }
        }
        return (conn, info)
    }
}
