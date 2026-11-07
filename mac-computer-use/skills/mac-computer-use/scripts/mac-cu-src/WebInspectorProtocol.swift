// The Remote Web Inspector (RWI) protocol: a 4-byte length and a binary plist {__selector, __argument}. The
// simulator (webinspectord_sim Unix socket) and a device (com.apple.webinspector service) use the same one.
// A page session sends WebKit Inspector protocol JSON in it. Ported from the iwi CLI.

import Foundation

var webInspectorDebug: Bool { currentSession?.env["MAC_CU_WEBINSPECTOR_DEBUG"] != nil }
func dlog(_ s: @autoclosure () -> String) { if webInspectorDebug { fputs("[webinspector] \(s())\n", stderr) } }

struct WebPage {
    let id: Int
    var title: String, url: String, type: String
    var inUse: Bool
}

struct WebApp {
    let id: String
    var name: String, bundleID: String
    var isProxy: Bool
    var isActive: Bool       // false: the app is in the background, and its pages can stop answering commands.
    var pages: [WebPage]?    // nil: no listing yet.
}

final class RWIClient {
    let connID = UUID().uuidString
    private let stream: ByteStream
    private let writeLock = NSLock()
    private let cond = NSCondition()
    private var apps: [String: WebApp] = [:]
    private var gotAppList = false
    private var closed = false
    private var lastActivity = Date()
    private var partial: [String: Data] = [:]
    /// (app ID, destination sender, JSON message). Called on the reader thread.
    var onData: ((String, String?, String) -> Void)?

    init(stream: ByteStream) { self.stream = stream }

    func start() {
        Thread.detachNewThread { [self] in
            do {
                while true {
                    let frame = try stream.readFrame()
                    guard let m = try PropertyListSerialization.propertyList(from: frame, format: nil) as? [String: Any],
                          let sel = m["__selector"] as? String else { continue }
                    handle(sel, m["__argument"] as? [String: Any] ?? [:])
                }
            } catch {}
            cond.lock(); closed = true; cond.broadcast(); cond.unlock()
        }
        send("_rpc_reportIdentifier:", ["WIRConnectionIdentifierKey": connID])
        // Without the connection identifier, webinspectord_sim (iOS 27.1) logs "Unexpected type" and closes the connection.
        send("_rpc_getConnectedApplications:", ["WIRConnectionIdentifierKey": connID])
    }

    func close() { stream.close() }

    func send(_ selector: String, _ args: [String: Any] = [:]) {
        guard let body = try? PropertyListSerialization.data(fromPropertyList: ["__selector": selector, "__argument": args], format: .binary, options: 0) else { return }
        writeLock.lock(); defer { writeLock.unlock() }
        try? stream.writeFrame(body)
    }

    private func requestListing(_ a: WebApp) {
        guard !a.isProxy else { return }
        send("_rpc_forwardGetListing:", ["WIRConnectionIdentifierKey": connID, "WIRApplicationIdentifierKey": a.id])
    }

    private static func parseApp(_ d: [String: Any]) -> WebApp? {
        guard let id = d["WIRApplicationIdentifierKey"] as? String else { return nil }
        // WIRIsApplicationActiveKey: 2 is foreground, 1 is background (simulator, iOS 26.5). Without the key, active.
        return WebApp(id: id, name: d["WIRApplicationNameKey"] as? String ?? id,
                      bundleID: d["WIRApplicationBundleIdentifierKey"] as? String ?? "",
                      isProxy: d["WIRIsApplicationProxyKey"] as? Bool ?? false,
                      isActive: (d["WIRIsApplicationActiveKey"] as? Int ?? 2) >= 2, pages: nil)
    }

    private func handle(_ selector: String, _ args: [String: Any]) {
        dlog("← \(selector)")
        switch selector {
        case "_rpc_reportConnectedApplicationList:":
            let dict = args["WIRApplicationDictionaryKey"] as? [String: [String: Any]] ?? [:]
            cond.lock()
            apps = Dictionary(uniqueKeysWithValues: dict.values.compactMap(Self.parseApp).map { ($0.id, $0) })
            gotAppList = true
            let list = Array(apps.values)
            cond.unlock()
            list.forEach(requestListing)
        case "_rpc_applicationConnected:", "_rpc_applicationUpdated:":
            guard var a = Self.parseApp(args) else { break }
            cond.lock()
            a.pages = apps[a.id]?.pages
            apps[a.id] = a
            cond.unlock()
            if selector == "_rpc_applicationConnected:" { requestListing(a) }
        case "_rpc_applicationDisconnected:":
            if let id = args["WIRApplicationIdentifierKey"] as? String { cond.lock(); apps[id] = nil; cond.unlock() }
        case "_rpc_applicationSentListing:":
            guard let id = args["WIRApplicationIdentifierKey"] as? String else { break }
            let listing = args["WIRListingKey"] as? [String: [String: Any]] ?? [:]
            let pages = listing.values.compactMap { d -> WebPage? in
                guard let pid = d["WIRPageIdentifierKey"] as? Int else { return nil }
                return WebPage(id: pid, title: d["WIRTitleKey"] as? String ?? "", url: d["WIRURLKey"] as? String ?? "",
                               type: d["WIRTypeKey"] as? String ?? "", inUse: d["WIRConnectionIdentifierKey"] != nil)
            }.sorted { $0.id < $1.id }
            cond.lock(); apps[id]?.pages = pages; cond.unlock()
        case "_rpc_applicationSentData:":
            guard let appID = args["WIRApplicationIdentifierKey"] as? String else { break }
            // A large message comes in WIRPartialMessageKey parts and a last WIRFinalMessageKey.
            var data = args["WIRMessageDataKey"] as? Data
            if let part = args["WIRPartialMessageKey"] as? Data {
                partial[appID, default: Data()].append(part)
            } else if let fin = args["WIRFinalMessageKey"] as? Data {
                data = (partial.removeValue(forKey: appID) ?? Data()) + fin
            }
            if let data, let text = String(data: data, encoding: .utf8) { onData?(appID, args["WIRDestinationKey"] as? String, text) }
        default: break
        }
        cond.lock(); lastActivity = Date(); cond.broadcast(); cond.unlock()
    }

    /// Collects the apps and their pages until no message comes for `quiet` seconds after the app list.
    /// The simulator's webinspectord starts again for each connection, and the apps connect to it in the few
    /// hundred milliseconds after the first list, so a full first list does not end the wait.
    func waitForListings(timeout: TimeInterval, quiet: TimeInterval = 1.0) -> [WebApp] {
        let deadline = Date().addingTimeInterval(timeout)
        cond.lock(); defer { cond.unlock() }
        while !closed {
            let until = gotAppList ? min(deadline, lastActivity.addingTimeInterval(quiet)) : deadline
            if Date() >= until { break }
            _ = cond.wait(until: until)
        }
        return apps.values.sorted { $0.id < $1.id }
    }
}

/// Sends WebKit Inspector protocol commands to one page and waits for each answer.
/// Current WebKit wraps page messages in the Target domain: after targetCreated the session wraps them,
/// and without it (a JSContext, for example) it sends them directly.
final class PageSession {
    private let client: RWIClient
    private let appID: String
    private let pageID: Int
    private let sender = UUID().uuidString
    private let lock = NSLock()
    private let targetReady = DispatchSemaphore(value: 0)
    private var targetID: String?
    private var nextID = 0
    private var pending: [Int: Pending] = [:]
    private var enabledDomains: [String] = []
    private static let outerBase = 1_000_000
    static let defaultTimeout: TimeInterval = 15

    private final class Pending {
        let sem = DispatchSemaphore(value: 0)
        var result: [String: Any] = [:]
        var error: String?
    }

    /// Protocol events (method, params). Called on the reader thread.
    var onEvent: ((String, [String: Any]) -> Void)?

    init(client: RWIClient, appID: String, pageID: Int) {
        self.client = client; self.appID = appID; self.pageID = pageID
    }

    private var routing: [String: Any] {
        ["WIRConnectionIdentifierKey": client.connID, "WIRApplicationIdentifierKey": appID,
         "WIRPageIdentifierKey": pageID, "WIRSenderKey": sender]
    }

    func open() {
        client.onData = { [weak self] app, dest, text in
            guard let self, app == self.appID, dest == nil || dest == self.sender else { return }
            self.receive(text)
        }
        client.send("_rpc_forwardSocketSetup:", routing.merging(["WIRAutomaticallyPause": false]) { $1 })
        _ = targetReady.wait(timeout: .now() + 2)
    }

    func close() { client.send("_rpc_forwardDidClose:", routing) }

    private func rawSend(_ obj: [String: Any]) {
        guard let d = try? JSONSerialization.data(withJSONObject: obj) else { return }
        dlog("→ \(String(decoding: d, as: UTF8.self).prefix(300))")
        client.send("_rpc_forwardSocketData:", routing.merging(["WIRSocketDataKey": d]) { $1 })
    }

    @discardableResult
    func command(_ method: String, _ params: [String: Any] = [:], timeout: TimeInterval? = nil) throws -> [String: Any] {
        let timeout = timeout ?? Self.defaultTimeout
        let p = Pending()
        lock.lock(); nextID += 1; let id = nextID; pending[id] = p; let tid = targetID
        if method.hasSuffix(".enable") { enabledDomains.append(String(method.dropLast(".enable".count))) }
        lock.unlock()
        var msg: [String: Any] = ["id": id, "method": method]
        if !params.isEmpty { msg["params"] = params }
        if let tid {
            let inner = String(decoding: try JSONSerialization.data(withJSONObject: msg), as: UTF8.self)
            rawSend(["id": id + Self.outerBase, "method": "Target.sendMessageToTarget", "params": ["targetId": tid, "message": inner]])
        } else {
            rawSend(msg)
        }
        defer { lock.lock(); pending[id] = nil; lock.unlock() }
        if p.sem.wait(timeout: .now() + timeout) == .timedOut {
            throw InspectorError("""
                No answer to \(method) in \(Int(timeout)) seconds. The app can be in the background, or the web view \
                is not on the screen (about:blank, for example), so the page does not run.
                """)
        }
        if let e = p.error { throw InspectorError("\(method): \(e)") }
        return p.result
    }

    private func receive(_ text: String) {
        dlog("← \(text.prefix(300))")
        guard let m = try? JSONSerialization.jsonObject(with: Data(text.utf8)) as? [String: Any] else { return }
        if let method = m["method"] as? String {
            let p = m["params"] as? [String: Any] ?? [:]
            switch method {
            case "Target.targetCreated":
                let info = p["targetInfo"] as? [String: Any] ?? [:]
                guard info["type"] as? String == "page", let id = info["targetId"] as? String else { break }
                if info["isProvisional"] as? Bool == true {
                    // A move to another site makes a provisional target in a new process. Enable the domains on it
                    // now, so that their events continue after the move.
                    lock.lock(); let domains = enabledDomains; lock.unlock()
                    for (i, d) in domains.enumerated() {
                        let inner = "{\"id\":\(900_000 + i),\"method\":\"\(d).enable\"}"
                        rawSend(["id": 950_000 + i, "method": "Target.sendMessageToTarget", "params": ["targetId": id, "message": inner]])
                    }
                    if info["isPaused"] as? Bool == true { rawSend(["id": 999_998, "method": "Target.resume", "params": ["targetId": id]]) }
                    break
                }
                lock.lock(); targetID = id; lock.unlock()
                if info["isPaused"] as? Bool == true { rawSend(["id": 999_999, "method": "Target.resume", "params": ["targetId": id]]) }
                targetReady.signal()
            case "Target.didCommitProvisionalTarget":
                lock.lock(); targetID = p["newTargetId"] as? String; lock.unlock()
            case "Target.dispatchMessageFromTarget":
                if let inner = p["message"] as? String { receive(inner) }
            case "Target.targetDestroyed": break
            default: onEvent?(method, p)
            }
        } else if let id = m["id"] as? Int {
            // The answer to the outer Target.sendMessageToTarget fails the inner command only when it is an error.
            let isOuter = id >= Self.outerBase
            let key = isOuter ? id - Self.outerBase : id
            let err = (m["error"] as? [String: Any])?["message"] as? String
            lock.lock(); let p = pending[key]; lock.unlock()
            guard let p, !isOuter || err != nil else { return }
            p.error = err
            p.result = m["result"] as? [String: Any] ?? [:]
            p.sem.signal()
        }
    }
}

// MARK: - Discovery

/// One Web Inspector socket: a booted simulator, or a USB or network device.
struct Endpoint {
    let id: String
    let name: String
    let kind: String   // "simulator" or "device"
    let version: String
    let open: () throws -> (stream: ByteStream, name: String?, version: String?)
}

struct Connection {
    let id: String
    var name: String
    let kind: String
    var version: String
    var client: RWIClient?
    var apps: [WebApp] = []
    var error: String?
}

enum Discovery {
    /// The webinspectord_sim socket of each simulator (lsof), named by the Devices/<UDID> in the command of its launchd_sim.
    static func simulators() -> [Endpoint] {
        guard let out = try? runTool("/usr/sbin/lsof", ["-aUc", "launchd_sim", "-F", "pn"]) else { return [] }
        var found: [(udid: String, socket: String)] = []
        var pid = ""
        for line in String(decoding: out, as: UTF8.self).split(separator: "\n") {
            if line.hasPrefix("p") { pid = String(line.dropFirst()) }
            else if line.hasPrefix("n"), line.hasSuffix("com.apple.webinspectord_sim.socket"),
                    let cmd = try? runTool("/bin/ps", ["-p", pid, "-o", "command="]),
                    let m = String(decoding: cmd, as: UTF8.self).firstMatch(of: #/Devices/([0-9A-Fa-f-]{36})//#),
                    !found.contains(where: { $0.udid == String(m.1).uppercased() }) {   // launchd_sim can open the socket twice.
                found.append((String(m.1).uppercased(), String(line.dropFirst())))
            }
        }
        if found.isEmpty { return [] }

        var names: [String: (name: String, version: String)] = [:]
        if let data = try? runTool("/usr/bin/xcrun", ["simctl", "list", "-j", "devices"]),
           let root = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any],
           let byRuntime = root["devices"] as? [String: [[String: Any]]] {
            for (runtime, list) in byRuntime {
                // com.apple.CoreSimulator.SimRuntime.iOS-26-5 -> 26.5
                let parts = (runtime.split(separator: ".").last ?? "").split(separator: "-")
                let version = parts.count > 1 ? parts.dropFirst().joined(separator: ".") : ""
                for d in list { if let u = d["udid"] as? String, let n = d["name"] as? String { names[u.uppercased()] = (n, version) } }
            }
        }
        return found.map { f in
            let info = names[f.udid]
            return Endpoint(id: f.udid, name: info?.name ?? f.udid, kind: "simulator", version: info?.version ?? "") {
                (try FDStream.unix(f.socket), nil, nil)
            }
        }
    }

    static func devices() -> [Endpoint] {
        ((try? Usbmux.devices()) ?? []).map { dev in
            Endpoint(id: dev.serial, name: dev.serial, kind: "device", version: "") {
                let (s, info) = try Lockdown.openWebInspector(dev)
                return (s, info.name, info.productVersion)
            }
        }
    }

    /// Connects to all endpoints at the same time and gets their apps and pages. A failed one has the reason in error.
    static func connect(_ endpoints: [Endpoint], timeout: TimeInterval = 3) -> [Connection] {
        var results = [Connection?](repeating: nil, count: endpoints.count)
        let lock = NSLock()
        DispatchQueue.concurrentPerform(iterations: endpoints.count) { i in
            let ep = endpoints[i]
            var c = Connection(id: ep.id, name: ep.name, kind: ep.kind, version: ep.version)
            do {
                let (stream, name, version) = try ep.open()
                if let name { c.name = name }
                if let version { c.version = version }
                let client = RWIClient(stream: stream)
                client.start()
                c.client = client
                // The simulator's webinspectord stops when its last client disconnects, and launchd_sim starts it
                // again up to 10 seconds later. A connection waits in the socket queue until then: wait, do not
                // connect again (a closed connection in the queue makes the new webinspectord stop at once).
                c.apps = client.waitForListings(timeout: ep.kind == "simulator" ? max(timeout, 12) : timeout)
            } catch { c.error = "\(error)" }
            lock.lock(); results[i] = c; lock.unlock()
        }
        return results.compactMap { $0 }
    }
}

struct Candidate {
    let conn: Connection
    let app: WebApp
    let page: WebPage
    var ref: String { "\(conn.id)/\(app.id)/\(page.id)" }
}

extension Array where Element == Connection {
    var candidates: [Candidate] {
        flatMap { c in c.apps.flatMap { a in (a.pages ?? []).map { Candidate(conn: c, app: a, page: $0) } } }
    }
}
