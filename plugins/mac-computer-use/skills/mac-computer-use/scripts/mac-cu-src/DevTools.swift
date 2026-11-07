// The devtools engine of the browser tool: a separate Chrome with its own profile
// (~/Library/Application Support/mac-cu/browser-profile, kept over plugin updates), controlled through the
// Chrome DevTools Protocol on 127.0.0.1.
// The user's own Chrome profile cannot be used: Chrome does not allow remote debugging on it.

import AppKit

final class DevTools: CDPEngine {
    static var shared: DevTools?
    static let port = 9222

    let appName = "Google Chrome"
    var pid: pid_t? { launched?.isTerminated == false ? launched?.processIdentifier : nil }
    var launched: NSRunningApplication?
    var targetID: String?
    var socket: URLSessionWebSocketTask?

    private let lock = NSLock()
    private var nextID = 0
    private var waiters: [Int: DispatchSemaphore] = [:]
    private var replies: [Int: [String: Any]] = [:]
    private var requestOrder: [String] = []
    private var requests: [String: [String: Any]] = [:]
    private var consoleLines: [String] = []

    /// Connect to the devtools Chrome. Starts it in the background when it does not run.
    static func connect() throws -> DevTools {
        try approve("Google Chrome (devtools)", bundleID: "mac-cu.devtools")
        let devTools = shared ?? DevTools()
        if (try? devTools.http("/json/version")) == nil {
            try devTools.launch()
        }
        if devTools.socket == nil || devTools.socket?.state != .running {
            guard let page = try devTools.pages().first(where: { $0["id"] as? String == devTools.targetID })
                    ?? devTools.pages().first else { throw ToolError("The devtools Chrome has no tab.") }
            try devTools.attach(page)
        }
        shared = devTools
        return devTools
    }

    func launch() throws {
        guard let url = NSWorkspace.shared.urlForApplication(withBundleIdentifier: "com.google.Chrome") else {
            throw ToolError("Google Chrome is not installed.")
        }
        let profile = supportFolder.appendingPathComponent("browser-profile").path
        let configuration = NSWorkspace.OpenConfiguration()
        configuration.activates = false
        configuration.createsNewApplicationInstance = true
        configuration.arguments = ["--remote-debugging-port=\(DevTools.port)", "--user-data-dir=\(profile)",
                                   "--no-first-run", "--no-default-browser-check", "about:blank"]
        let front = frontmostPID()
        let done = DispatchSemaphore(value: 0)
        NSWorkspace.shared.openApplication(at: url, configuration: configuration) { app, _ in
            self.launched = app
            done.signal()
        }
        _ = done.wait(timeout: .now() + 15)
        for _ in 0..<60 {
            if (try? http("/json/version")) != nil {
                // Chrome comes to the front when it starts, also with activates false.
                usleep(500_000)
                if let front, front != launched?.processIdentifier, frontmostPID() == launched?.processIdentifier {
                    NSRunningApplication(processIdentifier: front)?.activate()
                }
                return
            }
            usleep(250_000)
        }
        throw ToolError("The devtools Chrome did not start (port \(DevTools.port)).")
    }

    // MARK: HTTP endpoints and the WebSocket

    func http(_ path: String, method: String = "GET") throws -> Any {
        var request = URLRequest(url: URL(string: "http://127.0.0.1:\(DevTools.port)\(path)")!, timeoutInterval: 5)
        request.httpMethod = method
        var result: Data?
        let done = DispatchSemaphore(value: 0)
        URLSession.shared.dataTask(with: request) { data, response, _ in
            if (response as? HTTPURLResponse)?.statusCode == 200 { result = data }
            done.signal()
        }.resume()
        _ = done.wait(timeout: .now() + 6)
        guard let result else { throw ToolError("No answer from the devtools Chrome at \(path).") }
        return (try? JSONSerialization.jsonObject(with: result)) ?? String(data: result, encoding: .utf8) ?? ""
    }

    func pages() throws -> [[String: Any]] {
        (try http("/json/list") as? [[String: Any]] ?? []).filter { $0["type"] as? String == "page" }
    }

    func attach(_ page: [String: Any]) throws {
        guard let id = page["id"] as? String, let address = page["webSocketDebuggerUrl"] as? String,
              let url = URL(string: address) else { throw ToolError("The tab has no debugger address.") }
        socket?.cancel(with: .goingAway, reason: nil)
        targetID = id
        let task = URLSession.shared.webSocketTask(with: url)
        task.maximumMessageSize = 64 * 1024 * 1024
        socket = task
        task.resume()
        receive(task)
        _ = try send("Network.enable")
        _ = try send("Runtime.enable")
    }

    private func receive(_ task: URLSessionWebSocketTask) {
        task.receive { [weak self] result in
            guard let self, case .success(let message) = result else { return }
            if case .string(let text) = message, let data = text.data(using: .utf8),
               let object = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
                self.handle(object)
            }
            self.receive(task)
        }
    }

    func send(_ method: String, _ params: [String: Any] = [:], timeout: Double = 20) throws -> [String: Any] {
        guard let socket else { throw ToolError("Not connected to the devtools Chrome.") }
        let waiter = DispatchSemaphore(value: 0)
        lock.lock()
        nextID += 1
        let id = nextID
        waiters[id] = waiter
        lock.unlock()
        let data = try JSONSerialization.data(withJSONObject: ["id": id, "method": method, "params": params])
        socket.send(.string(String(data: data, encoding: .utf8)!)) { _ in }
        let answered = waiter.wait(timeout: .now() + timeout) == .success
        lock.lock()
        let reply = replies.removeValue(forKey: id)
        waiters[id] = nil
        lock.unlock()
        guard answered, let reply else { throw ToolError("\(method): no answer from the devtools Chrome.") }
        if let error = reply["error"] as? [String: Any] { throw ToolError("\(method): \(error["message"] ?? error)") }
        return reply["result"] as? [String: Any] ?? [:]
    }

    private func handle(_ message: [String: Any]) {
        lock.lock()
        defer { lock.unlock() }
        if let id = message["id"] as? Int {
            replies[id] = message
            waiters[id]?.signal()
            return
        }
        let params = message["params"] as? [String: Any] ?? [:]
        switch message["method"] as? String {
        case "Network.requestWillBeSent":
            guard let id = params["requestId"] as? String, let request = params["request"] as? [String: Any] else { return }
            if requests[id] == nil { requestOrder.append(id) }
            requests[id] = ["method": request["method"] ?? "", "url": request["url"] ?? "", "type": params["type"] ?? ""]
            if requestOrder.count > 500 { requests[requestOrder.removeFirst()] = nil }
        case "Network.responseReceived":
            guard let id = params["requestId"] as? String, let response = params["response"] as? [String: Any] else { return }
            requests[id]?["status"] = response["status"]
            requests[id]?["mime"] = response["mimeType"]
        case "Network.loadingFailed":
            guard let id = params["requestId"] as? String else { return }
            requests[id]?["failed"] = params["errorText"]
        case "Runtime.consoleAPICalled":
            let args = (params["args"] as? [[String: Any]] ?? []).map { "\($0["value"] ?? $0["description"] ?? $0["type"] ?? "")" }
            consoleLines.append("\(params["type"] ?? "log"): " + args.joined(separator: " "))
        case "Runtime.exceptionThrown":
            let details = params["exceptionDetails"] as? [String: Any] ?? [:]
            let exception = details["exception"] as? [String: Any]
            consoleLines.append("exception: \(exception?["description"] ?? details["text"] ?? "")")
        default:
            return
        }
        if consoleLines.count > 300 { consoleLines.removeFirst(consoleLines.count - 300) }
    }

    // MARK: BrowserEngine

    func cdp(_ method: String, _ params: [String: Any]) throws -> [String: Any] { try send(method, params) }

    func tabs() throws -> String {
        let lines = try pages().map { page -> String in
            let id = page["id"] as? String ?? ""
            return "\(id)\(id == targetID ? " *" : "") \(page["title"] ?? "") — \(page["url"] ?? "")"
        }
        return "Tabs (id, * = the tab mac-cu works on):\n" + lines.joined(separator: "\n")
    }

    func open(_ url: String) throws {
        let encoded = url.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? url
        guard let page = try http("/json/new?\(encoded)", method: "PUT") as? [String: Any] else {
            throw ToolError("The devtools Chrome did not open a tab.")
        }
        try attach(page)
    }

    func navigate(_ url: String) throws {
        let result = try send("Page.navigate", ["url": url])
        if let error = result["errorText"] as? String { throw ToolError("Could not open \(url): \(error)") }
    }

    func selectTab(_ tab: String) throws {
        guard let page = try pages().first(where: { $0["id"] as? String == tab }) else {
            throw ToolError("No tab \(tab). Use the tabs action for the ids.")
        }
        _ = try http("/json/activate/\(tab)")
        try attach(page)
    }

    func closeTab(_ tab: String) throws {
        _ = try http("/json/close/\(tab)")
        if tab == targetID {
            socket = nil
            if let page = try pages().first { try attach(page) }
        }
    }

    func history(_ step: String) throws {
        if step == "reload" { _ = try send("Page.reload") } else { _ = try evaluate("history.\(step)()") }
    }

    func network(filter: String?, limit: Int) throws -> String {
        lock.lock()
        let rows = requestOrder.compactMap { id in requests[id].map { (id: id, record: $0) } }
        lock.unlock()
        return requestLines(rows, filter: filter, limit: limit)
    }

    func console(limit: Int) throws -> String {
        lock.lock()
        let lines = consoleLines.suffix(limit)
        lock.unlock()
        return "Console messages since mac-cu connected to this tab:\n" + (lines.isEmpty ? "none" : lines.joined(separator: "\n"))
    }

    func quit() throws {
        _ = try? send("Browser.close", timeout: 3)
        socket?.cancel(with: .goingAway, reason: nil)
        DevTools.shared = nil
    }
}
