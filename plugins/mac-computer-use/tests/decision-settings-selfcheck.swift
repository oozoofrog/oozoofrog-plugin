import AppKit

final class SettingsProbeProtocol: URLProtocol {
    static let lock = NSLock()
    static var mode = "success"
    static var capturedBody: Data?
    static var requests = 0
    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }
    override func startLoading() {
        var bytes = request.httpBody ?? Data()
        if bytes.isEmpty, let stream = request.httpBodyStream {
            stream.open(); defer { stream.close() }
            var buffer = [UInt8](repeating: 0, count: 4096)
            while true { let n = stream.read(&buffer, maxLength: buffer.count); if n <= 0 { break }; bytes.append(contentsOf: buffer.prefix(n)) }
        }
        Self.lock.lock(); let mode = Self.mode; Self.capturedBody = bytes; Self.requests += 1; Self.lock.unlock()
        if mode == "pending" { return }
        if mode == "timeout" { client?.urlProtocol(self, didFailWithError: URLError(.timedOut)); return }
        let answer: [String: Any] = mode == "refusal" ? ["name": "connection", "type": "refusal"] : ["name": "connection", "type": "predicate", "probability": 0.99]
        let body: [String: Any] = mode == "unauthorized"
            ? ["error": ["message": "fixture-secret-must-not-appear"]]
            : ["model": "gpt-6-luna", "answers": [answer], "unexpected_token": "fixture-secret-must-not-appear"]
        client?.urlProtocol(self, didReceive: HTTPURLResponse(url: request.url!, statusCode: mode == "unauthorized" ? 401 : 200, httpVersion: nil, headerFields: nil)!, cacheStoragePolicy: .notAllowed)
        client?.urlProtocol(self, didLoad: try! JSONSerialization.data(withJSONObject: body))
        client?.urlProtocolDidFinishLoading(self)
    }
    override func stopLoading() { client?.urlProtocol(self, didFailWithError: URLError(.cancelled)) }
}

@main
struct DecisionSettingsSelfcheck {
    @MainActor static func descendants(_ view: NSView) -> [NSView] { [view] + view.subviews.flatMap(descendants) }
    @MainActor static func wait(_ condition: () -> Bool) async {
        for _ in 0..<200 {
            if condition() { return }
            try? await Task.sleep(nanoseconds: 10_000_000)
        }
        fatalError("Settings probe did not settle")
    }
    @MainActor static func run() async {
        let previous = NSWorkspace.shared.frontmostApplication
        defer { previous?.activate(options: []) }
        let suite = "decision-settings-selfcheck-" + UUID().uuidString
        let defaults = UserDefaults(suiteName: suite)!
        defer { defaults.removePersistentDomain(forName: suite) }
        let configuration = URLSessionConfiguration.ephemeral; configuration.protocolClasses = [SettingsProbeProtocol.self]
        let session = URLSession(configuration: configuration)
        defer { session.invalidateAndCancel() }
        var storedKey = "fixture-secret-must-not-appear"
        let settings = DecisionSettingsWindow(defaults: defaults, readKey: { storedKey }, writeKey: { storedKey = $0 }, transport: DecisionTransport(session: session))
        settings.show()
        let window = NSApp.windows.first { $0.title == "OpenAI Decisions 설정" }!
        defer { window.close() }
        window.orderOut(nil)
        window.contentView!.layoutSubtreeIfNeeded()
        let views = descendants(window.contentView!)
        let probe = views.compactMap { $0 as? NSButton }.first { $0.title == "연결 확인" }!
        let cancel = views.compactMap { $0 as? NSButton }.first { $0.title == "확인 취소" }!
        let request = views.compactMap { $0 as? NSTextView }.first { $0.accessibilityLabel() == "연결 확인 요청" }!
        let result = views.compactMap { $0 as? NSTextView }.first { $0.accessibilityLabel() == "연결 확인 결과 · 검증된 응답" }!
        assert(!request.isEditable && request.isSelectable && !result.isEditable && result.isSelectable)
        probe.performClick(nil)
        await wait { probe.isEnabled }
        assert(request.string.contains("POST https://api.openai.com/v1/decisions") && !request.string.contains("Authorization"))
        let body = try! JSONSerialization.jsonObject(with: Data(request.string[request.string.firstIndex(of: "{")!...].utf8)) as! NSDictionary
        let sent = SettingsProbeProtocol.lock.withLock { SettingsProbeProtocol.capturedBody! }
        assert(body == (try! JSONSerialization.jsonObject(with: sent) as! NSDictionary), "Displayed body must equal the actual request, not an example")
        let displayed = try! JSONSerialization.jsonObject(with: Data(result.string[result.string.firstIndex(of: "{")!...].utf8)) as! [String: [String: Any]]
        assert(abs((displayed["connection"]?["probability"] as! Double) - 0.99) < 0.000001)
        assert(displayed["connection"]?["type"] as? String == "predicate" && result.string.contains("소요 시간"))
        assert(!request.string.contains(storedKey) && !result.string.contains(storedKey))
        assert(request.bounds.width > 400 && result.bounds.width > 400, "The text itself must fit its report viewport")
        if let path = ProcessInfo.processInfo.environment["DECISION_SETTINGS_CAPTURE"] {
            window.makeKeyAndOrderFront(nil)
            try? await Task.sleep(nanoseconds: 300_000_000)
            let capture = Process(); capture.executableURL = URL(fileURLWithPath: "/usr/sbin/screencapture")
            capture.arguments = ["-x", "-o", "-l", String(window.windowNumber), path]
            try! capture.run(); capture.waitUntilExit(); assert(capture.terminationStatus == 0)
            print("Synthetic mock settings UI capture: " + path)
            window.orderOut(nil)
        }
        for mode in ["unauthorized", "timeout", "refusal"] {
            SettingsProbeProtocol.lock.withLock { SettingsProbeProtocol.mode = mode }
            probe.performClick(nil); await wait { probe.isEnabled }
            let expected = mode == "unauthorized" ? "HTTP 401" : mode == "timeout" ? "초과" : "unknown"
            assert(result.string.contains(expected), "The failure/refusal must stay visible")
            assert(!result.string.contains(storedKey))
        }
        SettingsProbeProtocol.lock.withLock { SettingsProbeProtocol.mode = "pending" }
        let beforePending = SettingsProbeProtocol.lock.withLock { SettingsProbeProtocol.requests }
        probe.performClick(nil)
        await wait { SettingsProbeProtocol.lock.withLock { SettingsProbeProtocol.requests } > beforePending }
        assert(!probe.isEnabled && cancel.isEnabled)
        cancel.performClick(nil)
        let cancelled = result.string
        assert(probe.isEnabled && !cancel.isEnabled && cancelled.contains("취소"))
        try? await Task.sleep(nanoseconds: 100_000_000)
        assert(result.string == cancelled, "Late cancellation callback must not overwrite the displayed result")
        let count = SettingsProbeProtocol.lock.withLock { SettingsProbeProtocol.requests }
        storedKey = ""
        probe.performClick(nil)
        assert(request.string.contains("전송하지") && result.string.contains("API 키가 없습니다"))
        assert(SettingsProbeProtocol.lock.withLock { SettingsProbeProtocol.requests } == count)
        var wire = URLRequest(url: URL(string: "https://api.openai.com/v1/decisions")!)
        wire.setValue("Bearer fixture-secret-must-not-appear", forHTTPHeaderField: "Authorization")
        wire.httpBody = Data("{\"input\":\"fixture-secret-must-not-appear\"}".utf8)
        assert(!DecisionProbeDisplay.request(wire, redacting: "fixture-secret-must-not-appear").contains("fixture-secret-must-not-appear"))
        assert(!DecisionProbeDisplay.failure(DecisionServiceError("fixture-secret-must-not-appear"), redacting: "fixture-secret-must-not-appear").contains("fixture-secret-must-not-appear"))
        window.setContentSize(NSSize(width: 600, height: 480)); window.contentView!.layoutSubtreeIfNeeded()
        let outer = window.contentView!.subviews.compactMap { $0 as? NSScrollView }.first!
        assert(outer.documentView!.frame.height > outer.contentView.bounds.height, "Compact windows must scroll to every control and report")
        assert(request.enclosingScrollView!.bounds.width > 400 && result.enclosingScrollView!.bounds.width > 400)
        print("PASS decision settings: actual request body, decoded response, elapsed time, no credentials, HTTP/auth/timeout/refusal, cancellation, missing-key admission and compact scroll layout")
    }
    static func main() {
        let app = NSApplication.shared; app.setActivationPolicy(.accessory)
        Task { @MainActor in await run(); exit(0) }
        app.run()
    }
}
