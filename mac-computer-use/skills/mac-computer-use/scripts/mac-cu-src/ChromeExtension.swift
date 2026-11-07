// The extension engine of the browser tool: the user's own Chrome, with its logins, through the mac-cu
// Chrome extension (chrome-extension/ in the skill folder). The extension runs Chrome DevTools Protocol
// commands on the user's tab with chrome.debugger.
//
// Path of a command: mac-cu (this MCP session) → Unix socket extensionSocket → mac-cu as the native
// messaging host (Chrome starts it for the extension; runNativeHost) → stdio → the extension. Each agent
// session has its own mac-cu, and they all use the one host. The host answers only mac-cu itself (the
// same executable, same user), and the extension runs only the protocol commands listed in background.js.

import AppKit

let extensionSocket = FileManager.default.homeDirectoryForCurrentUser
    .appendingPathComponent("Library/Application Support/mac-cu/chrome.sock")
/// setup.py copies chrome-extension/ here: a folder that does not change with the plugin version.
let extensionFolder = FileManager.default.homeDirectoryForCurrentUser
    .appendingPathComponent("Library/Application Support/mac-cu/chrome-extension")

// MARK: - Unix socket (also the daemon socket, Daemon.swift)

func withAddress<T>(_ socket: URL, _ body: (UnsafePointer<sockaddr>, socklen_t) -> T) -> T {
    var address = sockaddr_un()
    address.sun_family = sa_family_t(AF_UNIX)
    withUnsafeMutableBytes(of: &address.sun_path) { buffer in
        buffer.copyBytes(from: Array(socket.path.utf8.prefix(buffer.count - 1)))
    }
    return withUnsafePointer(to: &address) {
        $0.withMemoryRebound(to: sockaddr.self, capacity: 1) { body($0, socklen_t(MemoryLayout<sockaddr_un>.size)) }
    }
}

/// Reads JSON lines from a socket until it closes or `each` returns false.
func readLines(_ fd: Int32, _ each: (Data) -> Bool) {
    var buffer = Data()
    var chunk = [UInt8](repeating: 0, count: 65536)
    while true {
        let count = read(fd, &chunk, chunk.count)
        if count <= 0 { return }
        buffer.append(contentsOf: chunk[0..<count])
        while let newline = buffer.firstIndex(of: 0x0a) {
            let line = Data(buffer[buffer.startIndex..<newline])
            buffer.removeSubrange(buffer.startIndex...newline)
            if !each(line) { return }
        }
    }
}

func writeAll(_ fd: Int32, _ data: Data) -> Bool {
    data.withUnsafeBytes { raw in
        var offset = 0
        while offset < raw.count {
            let written = write(fd, raw.baseAddress! + offset, raw.count - offset)
            if written <= 0 { return false }
            offset += written
        }
        return true
    }
}

func connectSocket(_ socket: URL) -> Int32? {
    let fd = Darwin.socket(AF_UNIX, SOCK_STREAM, 0)
    var on: Int32 = 1
    setsockopt(fd, SOL_SOCKET, SO_NOSIGPIPE, &on, socklen_t(MemoryLayout<Int32>.size))
    if withAddress(socket, { Darwin.connect(fd, $0, $1) }) == 0 { return fd }
    close(fd)
    return nil
}

// MARK: - Who may talk to the host

/// The file a process runs, resolved by the kernel: mac-cu sessions and the native host are the same file.
func executablePath(of pid: pid_t) -> String? {
    var buffer = [CChar](repeating: 0, count: 4 * Int(MAXPATHLEN))
    guard proc_pidpath(pid, &buffer, UInt32(buffer.count)) > 0 else { return nil }
    return String(cString: buffer)
}

/// Only mac-cu itself, run by the same user, may send commands to the extension (or to the daemon): the socket
/// would otherwise hand the DevTools protocol on the user's logged-in tabs to every program on the Mac.
/// Returns what the peer is when it is refused, nil when it may talk.
func refusal(of client: Int32, host: String?) -> String? {
    var uid: uid_t = 0, gid: gid_t = 0
    guard getpeereid(client, &uid, &gid) == 0, uid == getuid() else { return "a program of another user" }
    var pid: pid_t = 0
    var size = socklen_t(MemoryLayout<pid_t>.size)
    guard getsockopt(client, SOL_LOCAL, LOCAL_PEERPID, &pid, &size) == 0, pid > 0,
          let peer = executablePath(of: pid) else { return "an unknown program" }
    guard let host, peer == host else { return peer }
    return nil
}

// MARK: - The native messaging host

/// Request id → the socket of the mac-cu session that sent it.
private final class HostRoutes {
    let lock = NSLock()
    var waiting: [String: Int32] = [:]
}

/// `mac-cu chrome-extension://<id>/`: Chrome starts mac-cu so as the native messaging host of the extension.
/// It sends JSON lines from mac-cu sessions to the extension (a 4-byte length, then the JSON) and each
/// reply back to the session that sent the request, until Chrome closes stdin.
func runNativeHost() -> Never {
    signal(SIGPIPE, SIG_IGN)
    try? FileManager.default.createDirectory(at: extensionSocket.deletingLastPathComponent(), withIntermediateDirectories: true)
    // shortcut: a host of a second Chrome profile with the extension takes the socket over; use one profile.
    unlink(extensionSocket.path)
    let server = socket(AF_UNIX, SOCK_STREAM, 0)
    guard withAddress(extensionSocket, { bind(server, $0, $1) }) == 0, listen(server, 16) == 0 else { exit(1) }
    chmod(extensionSocket.path, 0o600)
    let host = executablePath(of: getpid())
    let routes = HostRoutes()
    Thread.detachNewThread {
        while true {
            let client = accept(server, nil, nil)
            guard client >= 0 else { continue }
            Thread.detachNewThread {
                if let peer = refusal(of: client, host: host) {
                    // One answer, so that the caller sees why; then the door closes.
                    readLines(client) { line in
                        let id = (try? JSONSerialization.jsonObject(with: line) as? [String: Any])?["id"] as? String ?? ""
                        let error = "The mac-cu extension host refused \(peer): only mac-cu at \(host ?? "its own path") may use " +
                            "the extension. After a plugin update, run setup.py again and reload mac-cu in chrome://extensions " +
                            "(Chrome then starts the host from the new folder)."
                        if let reply = try? JSONSerialization.data(withJSONObject: ["id": id, "error": error]) {
                            _ = writeAll(client, reply + Data([0x0a]))
                        }
                        return false
                    }
                    close(client)
                    return
                }
                readLines(client) { line in
                    guard let id = (try? JSONSerialization.jsonObject(with: line) as? [String: Any])?["id"] as? String else { return true }
                    var length = UInt32(line.count).littleEndian  // Chrome reads the length in the Mac's byte order.
                    routes.lock.lock()
                    routes.waiting[id] = client
                    FileHandle.standardOutput.write(Data(bytes: &length, count: 4) + line)
                    routes.lock.unlock()
                    return true
                }
                // A late reply must not reach a later session that gets the same fd number.
                routes.lock.lock()
                routes.waiting = routes.waiting.filter { $0.value != client }
                routes.lock.unlock()
                close(client)
            }
        }
    }
    let input = FileHandle.standardInput
    while true {
        let header = input.readData(ofLength: 4)
        guard header.count == 4 else { break }
        let length = header.withUnsafeBytes { $0.loadUnaligned(as: UInt32.self) }.littleEndian
        let message = input.readData(ofLength: Int(length))
        guard let id = (try? JSONSerialization.jsonObject(with: message) as? [String: Any])?["id"] as? String else { continue }
        routes.lock.lock()
        let client = routes.waiting.removeValue(forKey: id)
        routes.lock.unlock()
        if let client { _ = writeAll(client, message + Data([0x0a])) }
    }
    unlink(extensionSocket.path)
    exit(0)
}

// MARK: - The engine

final class ChromeExtension: CDPEngine {
    let appName: String
    let pid: pid_t?

    /// Approval for Google Chrome, and starts it in the background when it does not run.
    init() throws {
        let chrome = try session(for: "Google Chrome")
        appName = chrome.name
        pid = chrome.app.processIdentifier
        // A Chrome that just started needs a moment to start the extension and its host.
        for _ in 0..<20 {
            if let fd = ChromeExtension.connect() {
                close(fd)
                return
            }
            usleep(250_000)
        }
        throw ToolError("""
            The mac-cu Chrome extension does not answer. Is it installed? The user installs it once: \
            chrome://extensions > Developer mode on > Load unpacked > the folder \(extensionFolder.path) \
            (setup.py copies it there and registers its native messaging host; run setup.py first if the \
            folder is missing). Ask the user before you change browser settings. If it is installed, it must \
            be on, and Chrome must use the profile where it is installed. Or use "engine": "apple_events" or "devtools".
            """)
    }

    static func connect() -> Int32? { connectSocket(extensionSocket) }

    /// Sends a command to the extension (background.js run) and returns its result.
    func call(_ method: String, _ params: [String: Any] = [:], timeout: Int = 30) throws -> Any? {
        guard let fd = ChromeExtension.connect() else { throw ToolError("The mac-cu Chrome extension is not connected any more. Is Chrome open?") }
        defer { close(fd) }
        var time = timeval(tv_sec: timeout, tv_usec: 0)
        setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &time, socklen_t(MemoryLayout<timeval>.size))
        let id = UUID().uuidString
        var line = try JSONSerialization.data(withJSONObject: ["id": id, "method": method, "params": params])
        line.append(0x0a)
        guard writeAll(fd, line) else { throw ToolError("Could not send \(method) to the mac-cu Chrome extension.") }
        var reply: [String: Any]?
        readLines(fd) { data in
            guard let answer = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                  answer["id"] as? String == id else { return true }  // a late answer to an earlier request
            reply = answer
            return false
        }
        guard let reply else { throw ToolError("\(method): no answer from the mac-cu Chrome extension in \(timeout) seconds.") }
        if let error = reply["error"] as? String { throw ToolError("\(method): \(error)") }
        return reply["result"]
    }

    func cdp(_ method: String, _ params: [String: Any]) throws -> [String: Any] {
        try call("cdp", ["method": method, "params": params]) as? [String: Any] ?? [:]
    }

    func tabs() throws -> String {
        let lines = (try call("tabs") as? [[String: Any]] ?? []).map { tab in
            "\(tab["id"] ?? "")\(tab["current"] as? Bool == true ? " *" : "") \(tab["title"] ?? "") — \(tab["url"] ?? "")"
        }
        return lines.isEmpty ? "No open tabs." : "Tabs (id, * = the tab mac-cu works on):\n" + lines.joined(separator: "\n")
    }

    func open(_ url: String) throws { _ = try call("open", ["url": url]) }
    func navigate(_ url: String) throws { _ = try call("navigate", ["url": url]) }
    func selectTab(_ tab: String) throws { _ = try call("select", ["tab": tab]) }
    func closeTab(_ tab: String) throws { _ = try call("close", ["tab": tab]) }
    func history(_ step: String) throws { _ = try call(step) }

    func network(filter: String?, limit: Int) throws -> String {
        let records = (try call("log") as? [String: Any])?["requests"] as? [[String: Any]] ?? []
        return requestLines(records.map { (id: "\($0["id"] ?? "")", record: $0) }, filter: filter, limit: limit)
    }

    func console(limit: Int) throws -> String {
        let lines = ((try call("log") as? [String: Any])?["console"] as? [String] ?? []).suffix(limit)
        return "Console messages since mac-cu connected to this tab:\n" + (lines.isEmpty ? "none" : lines.joined(separator: "\n"))
    }

    func quit() throws { throw ToolError("quit is for the devtools engine. mac-cu does not close the user's browser.") }
}
