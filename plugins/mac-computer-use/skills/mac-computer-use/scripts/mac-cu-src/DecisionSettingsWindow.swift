import AppKit

/// The daemon uses its own environment; tests may inject a session and isolated stores.
final class DecisionSettingsWindow: NSObject, NSWindowDelegate {
    static let shared = DecisionSettingsWindow()
    var sessionEnvironment: () -> [String: String] = { [:] }
    private let defaults: UserDefaults
    private let readKey: () throws -> String
    private let writeKey: (String) throws -> Void
    private let transport: DecisionTransport
    private var window: NSWindow?
    private let model = NSTextField()
    private let key = NSSecureTextField()
    private let deleteKey = NSButton(checkboxWithTitle: "저장된 OpenAI 키 삭제", target: nil, action: nil)
    private let source = NSTextField(wrappingLabelWithString: "")
    private let status = NSTextField(wrappingLabelWithString: "연결 확인 전")
    private let requestText = NSTextView()
    private let resultText = NSTextView()
    private var probeButton: NSButton!
    private var cancelProbeButton: NSButton!
    private var task: URLSessionDataTask?
    private var generation = 0

    init(defaults: UserDefaults = .standard, readKey: @escaping () throws -> String = DecisionSettings.key,
         writeKey: @escaping (String) throws -> Void = DecisionSettings.storeKey,
         transport: DecisionTransport = .shared) {
        self.defaults = defaults; self.readKey = readKey; self.writeKey = writeKey; self.transport = transport
        super.init()
    }
    func show() {
        precondition(Thread.isMainThread)
        if window == nil { build() }
        load()
        window?.center(); window?.makeKeyAndOrderFront(nil); NSApp.activate(ignoringOtherApps: true)
    }
    private func build() {
        let height = min(820, (NSScreen.main?.visibleFrame.height ?? 920) - 80)
        let w = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 720, height: max(560, height)),
                         styleMask: [.titled, .closable, .resizable], backing: .buffered, defer: false)
        w.title = "OpenAI Decisions 설정"; w.delegate = self; w.isReleasedWhenClosed = false
        w.minSize = NSSize(width: 600, height: 500)
        model.placeholderString = "gpt-6-luna"
        key.placeholderString = "새 키 입력 (비워두면 기존 키 유지)"
        let info = NSTextField(wrappingLabelWithString: "메뉴바 설정은 데몬 환경을 사용합니다. 키 우선순위는 Keychain → 현재 MCP 세션 → 데몬 환경이며, 저장 모델은 환경보다 우선합니다. 연결 확인은 저장된 설정으로 합성 텍스트만 전송합니다. 요청·결과에는 API 키와 인증 헤더를 표시하지 않습니다.")
        info.textColor = .secondaryLabelColor; info.font = .systemFont(ofSize: 12)
        func row(_ title: String, _ field: NSView) -> NSStackView {
            let label = NSTextField(labelWithString: title); label.widthAnchor.constraint(equalToConstant: 100).isActive = true
            let row = NSStackView(views: [label, field]); row.orientation = .horizontal; row.alignment = .centerY; row.spacing = 8
            field.setContentHuggingPriority(.defaultLow, for: .horizontal)
            return row
        }
        func button(_ title: String, _ action: Selector) -> NSButton { NSButton(title: title, target: self, action: action) }
        probeButton = button("연결 확인", #selector(probe))
        cancelProbeButton = button("확인 취소", #selector(cancelProbe)); cancelProbeButton.isEnabled = false
        let buttons = NSStackView(views: [probeButton, cancelProbeButton, button("취소", #selector(cancel)), button("저장", #selector(save))])
        buttons.orientation = .horizontal; buttons.spacing = 8
        requestText.string = "연결 확인을 누르면 실제 전송할 요청을 표시합니다."
        resultText.string = "아직 연결 확인 결과가 없습니다."
        func report(_ title: String, _ text: NSTextView, height: CGFloat) -> [NSView] {
            let label = NSTextField(labelWithString: title); label.font = .boldSystemFont(ofSize: 12)
            text.isEditable = false; text.isSelectable = true
            text.font = .monospacedSystemFont(ofSize: 11.5, weight: .regular)
            text.textColor = .labelColor; text.backgroundColor = .textBackgroundColor
            text.textContainerInset = NSSize(width: 10, height: 8)
            text.isVerticallyResizable = true; text.isHorizontallyResizable = false
            text.autoresizingMask = [.width]; text.textContainer?.widthTracksTextView = true
            text.setAccessibilityLabel(title)
            let scroll = NSScrollView(); scroll.hasVerticalScroller = true; scroll.borderType = .bezelBorder
            scroll.documentView = text
            scroll.heightAnchor.constraint(equalToConstant: height).isActive = true
            return [label, scroll]
        }
        let views: [NSView] = [row("모델", model), row("OpenAI API 키", key), deleteKey, info, source, buttons, status]
            + report("연결 확인 요청", requestText, height: 170)
            + report("연결 확인 결과 · 검증된 응답", resultText, height: 180)
        let stack = NSStackView(views: views)
        stack.orientation = .vertical; stack.alignment = .leading; stack.spacing = 10; stack.translatesAutoresizingMaskIntoConstraints = false
        let document = DecisionSettingsDocumentView(); document.translatesAutoresizingMaskIntoConstraints = false
        document.addSubview(stack)
        let scroll = NSScrollView(); scroll.hasVerticalScroller = true; scroll.autohidesScrollers = true
        scroll.translatesAutoresizingMaskIntoConstraints = false; scroll.documentView = document
        w.contentView!.addSubview(scroll)
        NSLayoutConstraint.activate([
            scroll.leadingAnchor.constraint(equalTo: w.contentView!.leadingAnchor), scroll.trailingAnchor.constraint(equalTo: w.contentView!.trailingAnchor),
            scroll.topAnchor.constraint(equalTo: w.contentView!.topAnchor), scroll.bottomAnchor.constraint(equalTo: w.contentView!.bottomAnchor),
            document.widthAnchor.constraint(equalTo: scroll.contentView.widthAnchor),
            stack.leadingAnchor.constraint(equalTo: document.leadingAnchor, constant: 20), stack.trailingAnchor.constraint(equalTo: document.trailingAnchor, constant: -20),
            stack.topAnchor.constraint(equalTo: document.topAnchor, constant: 18), stack.bottomAnchor.constraint(equalTo: document.bottomAnchor, constant: -18)
        ])
        for view in views where view !== deleteKey && view !== buttons {
            view.widthAnchor.constraint(equalTo: stack.widthAnchor).isActive = true
        }
        window = w
    }
    private func load() {
        do {
            let c = try DecisionSettings.resolve(session: sessionEnvironment(), defaults: defaults, readKey: readKey)
            model.stringValue = c.model
            key.stringValue = ""; deleteKey.state = .off
            source.stringValue = "설정 출처: \(c.source)\n키 출처: \(c.keySource)"
        } catch { status.stringValue = error.localizedDescription }
    }
    @objc private func save() {
        do {
            var c = DecisionConfiguration()
            c.model = model.stringValue.trimmingCharacters(in: .whitespacesAndNewlines)
            if c.model.isEmpty { c.model = "gpt-6-luna" }
            try DecisionCodec.validate(c)
            if deleteKey.state == .on && !key.stringValue.isEmpty { throw DecisionServiceError("키 입력과 삭제를 동시에 선택할 수 없습니다.") }
            if deleteKey.state == .on { try writeKey("") } else if !key.stringValue.isEmpty { try writeKey(key.stringValue) }
            defaults.set(["model": c.model], forKey: DecisionSettings.settingKey)
            cancelProbe(); load(); status.stringValue = "저장됨 · 연결 확인 전"
            requestText.string = "저장된 설정으로 연결 확인을 실행하세요."
            resultText.string = "설정이 변경되었습니다. 아직 연결 확인하지 않았습니다."
        } catch { status.stringValue = error.localizedDescription }
    }
    @objc private func probe() {
        cancelProbe()
        requestText.string = "요청 준비 중…"; resultText.string = "응답 대기 중…"
        var secret = ""
        let start = DispatchTime.now().uptimeNanoseconds
        do {
            let c = try DecisionSettings.resolve(session: sessionEnvironment(), defaults: defaults, readKey: readKey)
            secret = c.apiKey
            let request = try DecisionCodec.request(DecisionCodec.probe, config: c, timeout: 15)
            requestText.string = DecisionProbeDisplay.request(request, redacting: secret)
            let token = generation; status.stringValue = "연결 확인 중…"
            probeButton.isEnabled = false; cancelProbeButton.isEnabled = true
            task = try transport.send(DecisionCodec.probe, config: c, timeout: 15) { [weak self] result in
                DispatchQueue.main.async {
                    guard let self = self, self.generation == token else { return }
                    self.task = nil
                    self.probeButton.isEnabled = true; self.cancelProbeButton.isEnabled = false
                    let elapsed = Double(DispatchTime.now().uptimeNanoseconds - start) / 1_000_000_000
                    switch result {
                    case .success(let answer):
                        self.status.stringValue = answer["connection"]?["type"] as? String == "predicate" ? "연결 확인 성공" : "연결 실패: 테스트 요청이 거부되었습니다."
                        self.resultText.string = DecisionProbeDisplay.result(answer, elapsed: elapsed, redacting: c.apiKey)
                    case .failure(let error):
                        let message = DecisionProbeDisplay.failure(error, redacting: c.apiKey)
                        self.status.stringValue = "연결 실패: " + message
                        self.resultText.string = "소요 시간: \(String(format: "%.2f", elapsed))초\n\n" + message
                    }
                }
            }
        } catch {
            probeButton.isEnabled = true; cancelProbeButton.isEnabled = false
            requestText.string = "전송하지 않았습니다. 저장된 설정과 API 키를 확인하세요."
            let message = DecisionProbeDisplay.failure(error, redacting: secret)
            status.stringValue = "연결 실패: " + message; resultText.string = message
        }
    }
    @objc private func cancelProbe() {
        generation += 1
        let running = task != nil
        task?.cancel(); task = nil
        probeButton?.isEnabled = true; cancelProbeButton?.isEnabled = false
        if running {
            status.stringValue = "연결 확인 취소됨"
            resultText.string = "사용자가 연결 확인을 취소했습니다. 이 요청의 늦은 응답은 표시하지 않습니다."
        }
    }
    @objc private func cancel() { cancelProbe(); key.stringValue = ""; window?.close() }
    func windowWillClose(_ notification: Notification) { cancelProbe(); key.stringValue = "" }
}

/// Only the JSON body is displayed: request headers (including Authorization) never enter the report.
enum DecisionProbeDisplay {
    private static func redact(_ text: String, secret: String) -> String {
        secret.isEmpty ? text : text.replacingOccurrences(of: secret, with: "[REDACTED]")
    }
    private static func json(_ value: Any) -> String {
        guard let data = try? JSONSerialization.data(withJSONObject: value, options: [.prettyPrinted, .sortedKeys, .withoutEscapingSlashes]),
              let text = String(data: data, encoding: .utf8) else { return "JSON 표시 실패" }
        return text
    }
    static func request(_ request: URLRequest, redacting secret: String) -> String {
        let body = request.httpBody.flatMap { try? JSONSerialization.jsonObject(with: $0) }
        return redact("\(request.httpMethod ?? "POST") \(request.url?.absoluteString ?? "")\n\n" + (body.map(json) ?? "본문 없음"), secret: secret)
    }
    static func result(_ answers: [String: [String: Any]], elapsed: TimeInterval, redacting secret: String) -> String {
        redact("소요 시간: \(String(format: "%.2f", elapsed))초\n\n" + json(answers), secret: secret)
    }
    static func failure(_ error: Error, redacting secret: String) -> String {
        redact((error as? DecisionServiceError)?.message ?? "판단 요청을 완료하지 못했습니다.", secret: secret)
    }
}

private final class DecisionSettingsDocumentView: NSView {
    override var isFlipped: Bool { true }
}
