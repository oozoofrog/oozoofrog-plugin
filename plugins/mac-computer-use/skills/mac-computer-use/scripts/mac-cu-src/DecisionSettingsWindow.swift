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
        let w = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 540, height: 440),
                         styleMask: [.titled, .closable], backing: .buffered, defer: false)
        w.title = "OpenAI Decisions 설정"; w.delegate = self; w.isReleasedWhenClosed = false
        model.placeholderString = "gpt-6-luna"
        key.placeholderString = "새 키 입력 (비워두면 기존 키 유지)"
        let info = NSTextField(wrappingLabelWithString: "메뉴바 설정은 데몬 환경을 사용합니다. 요청 시 키 우선순위는 Keychain, 해당 MCP 세션, 데몬 환경 순입니다. 저장 모델은 환경보다 우선합니다. 연결 확인은 저장된 설정으로 합성 텍스트만 전송합니다.")
        info.textColor = .secondaryLabelColor
        func row(_ title: String, _ field: NSView) -> NSStackView {
            let label = NSTextField(labelWithString: title); label.widthAnchor.constraint(equalToConstant: 100).isActive = true
            let row = NSStackView(views: [label, field]); row.orientation = .horizontal; row.alignment = .centerY; row.spacing = 8
            return row
        }
        func button(_ title: String, _ action: Selector) -> NSButton { NSButton(title: title, target: self, action: action) }
        let buttons = NSStackView(views: [button("연결 확인", #selector(probe)), button("확인 취소", #selector(cancelProbe)), button("취소", #selector(cancel)), button("저장", #selector(save))])
        buttons.orientation = .horizontal; buttons.spacing = 8
        let stack = NSStackView(views: [row("모델", model), row("OpenAI API 키", key), deleteKey, info, source, status, buttons])
        stack.orientation = .vertical; stack.alignment = .leading; stack.spacing = 12; stack.translatesAutoresizingMaskIntoConstraints = false
        w.contentView!.addSubview(stack)
        NSLayoutConstraint.activate([stack.leadingAnchor.constraint(equalTo: w.contentView!.leadingAnchor, constant: 20), stack.trailingAnchor.constraint(equalTo: w.contentView!.trailingAnchor, constant: -20), stack.topAnchor.constraint(equalTo: w.contentView!.topAnchor, constant: 18), model.widthAnchor.constraint(equalToConstant: 370), key.widthAnchor.constraint(equalToConstant: 370), info.widthAnchor.constraint(equalToConstant: 490), source.widthAnchor.constraint(equalToConstant: 490), status.widthAnchor.constraint(equalToConstant: 490)])
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
        } catch { status.stringValue = error.localizedDescription }
    }
    @objc private func probe() {
        cancelProbe()
        do {
            let c = try DecisionSettings.resolve(session: sessionEnvironment(), defaults: defaults, readKey: readKey)
            let token = generation; status.stringValue = "연결 확인 중…"
            task = try transport.send(DecisionCodec.probe, config: c, timeout: 15) { [weak self] result in
                DispatchQueue.main.async {
                    guard let self = self, self.generation == token else { return }
                    self.task = nil
                    switch result {
                    case .success(let answer):
                        self.status.stringValue = answer["connection"]?["type"] as? String == "predicate" ? "연결 확인 성공" : "연결 실패: 테스트 요청이 거부되었습니다."
                    case .failure(let error): self.status.stringValue = "연결 실패: \(error.localizedDescription)"
                    }
                }
            }
        } catch { status.stringValue = "연결 실패: \(error.localizedDescription)" }
    }
    @objc private func cancelProbe() { generation += 1; task?.cancel(); task = nil; status.stringValue = "연결 확인 취소됨" }
    @objc private func cancel() { cancelProbe(); key.stringValue = ""; window?.close() }
    func windowWillClose(_ notification: Notification) { cancelProbe(); key.stringValue = "" }
}
