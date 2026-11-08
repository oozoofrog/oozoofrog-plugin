import Foundation
import Security

struct DecisionServiceError: LocalizedError {
    let message: String
    init(_ message: String) { self.message = message }
    var errorDescription: String? { message }
}

struct DecisionConfiguration {
    var model = "gpt-6-luna"
    var apiKey = ""
    var source = "기본 설정"
    var keySource = "키 없음"
}

/// A separate bundle gets a separate service: development apps never edit the installed app's key.
enum DecisionSettings {
    static var keychainService: String { (Bundle.main.bundleIdentifier ?? "com.kakao.mac-cu") + ".decisions" }
    static let settingKey = "decisionConfiguration.v1"
    static let environmentNames = ["MAC_CU_DECISION_MODEL", "OPENAI_API_KEY", "MAC_CU_WEBINSPECTOR_DEBUG"]
    static func key() throws -> String {
        let query: [String: Any] = [kSecClass as String: kSecClassGenericPassword, kSecAttrService as String: keychainService,
            kSecAttrAccount as String: "openai", kSecReturnData as String: true, kSecMatchLimit as String: kSecMatchLimitOne,
            kSecUseAuthenticationUI as String: kSecUseAuthenticationUIFail]
        var item: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &item)
        if status == errSecItemNotFound { return "" }
        guard status == errSecSuccess, let data = item as? Data, let value = String(data: data, encoding: .utf8) else {
            throw DecisionServiceError("Keychain 키를 읽을 수 없습니다 (\(status)). 설정에서 키 접근을 확인하세요.")
        }
        return value
    }
    static func storeKey(_ value: String) throws {
        let query: [String: Any] = [kSecClass as String: kSecClassGenericPassword, kSecAttrService as String: keychainService, kSecAttrAccount as String: "openai"]
        if value.isEmpty {
            let status = SecItemDelete(query as CFDictionary)
            guard status == errSecSuccess || status == errSecItemNotFound else { throw DecisionServiceError("Keychain 삭제 실패 (\(status)).") }
            return
        }
        let attributes: [String: Any] = [kSecValueData as String: Data(value.utf8)]
        var status = SecItemUpdate(query as CFDictionary, attributes as CFDictionary)
        if status == errSecItemNotFound {
            var add = query.merging(attributes) { _, new in new }
            add[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
            status = SecItemAdd(add as CFDictionary, nil)
        }
        guard status == errSecSuccess else { throw DecisionServiceError("Keychain 저장 실패 (\(status)).") }
    }
    static func resolve(session: [String: String] = [:], environment: [String: String] = ProcessInfo.processInfo.environment,
                        defaults: UserDefaults = .standard, readKey: () throws -> String = key) throws -> DecisionConfiguration {
        var config = DecisionConfiguration()
        let env = environment.merging(session) { _, session in session }
        if let model = defaults.dictionary(forKey: settingKey)?["model"] as? String, !model.isEmpty {
            config.model = model
            config.source = "메뉴바 저장 설정 (환경 모델보다 우선)"
        } else if let model = env["MAC_CU_DECISION_MODEL"], !model.isEmpty {
            config.model = model
            config.source = session["MAC_CU_DECISION_MODEL"] != nil ? "MCP 세션 환경" : "데몬 환경"
        }
        let savedKey = try readKey()
        if !savedKey.isEmpty { config.apiKey = savedKey; config.keySource = "이 앱의 Keychain" }
        else if let key = session["OPENAI_API_KEY"], !key.isEmpty { config.apiKey = key; config.keySource = "현재 MCP 세션 OPENAI_API_KEY (메모리 전용)" }
        else if let key = environment["OPENAI_API_KEY"], !key.isEmpty { config.apiKey = key; config.keySource = "데몬 OPENAI_API_KEY (메모리 전용)" }
        return config
    }
    static func save(_ config: DecisionConfiguration, replacementKey: String?, defaults: UserDefaults = .standard) throws {
        try DecisionCodec.validate(config)
        if let replacementKey { try storeKey(replacementKey) }
        defaults.set(["model": config.model], forKey: settingKey)
    }
}

/// Maps tool questions to the OpenAI Decisions API.
enum DecisionCodec {
    static func validate(_ config: DecisionConfiguration) throws {
        guard config.model == "gpt-6-luna" else { throw DecisionServiceError("OpenAI Decisions는 gpt-6-luna 모델만 지원합니다.") }
    }
    static func probability(_ value: Any?) throws -> Double {
        guard let n = value as? NSNumber, CFGetTypeID(n) != CFBooleanGetTypeID(), n.doubleValue.isFinite,
              (0...1).contains(n.doubleValue) else { throw DecisionServiceError("응답 확률/confidence가 0…1 범위의 유한수가 아닙니다.") }
        return n.doubleValue
    }
    static func parts(_ value: Any) throws -> Any {
        if let text = value as? String { return text }
        guard let parts = value as? [[String: Any]], !parts.isEmpty else { throw DecisionServiceError("지원하지 않는 판단 입력 형식입니다.") }
        return try parts.map { part -> [String: Any] in
            switch part["type"] as? String {
            case "input_text":
                guard let text = part["text"] as? String else { throw DecisionServiceError("텍스트 입력이 잘못되었습니다.") }
                return ["type": "input_text", "text": text]
            case "input_image":
                guard let url = part["image_url"] as? String else { throw DecisionServiceError("이미지 URL이 없습니다.") }
                if url.hasPrefix("data:") {
                    guard let split = url.range(of: ";base64,"), ["data:image/png", "data:image/jpeg", "data:image/webp", "data:image/gif"].contains(String(url[..<split.lowerBound])),
                          let data = Data(base64Encoded: String(url[split.upperBound...])), !data.isEmpty else { throw DecisionServiceError("잘못된 이미지 data URL입니다.") }
                } else {
                    guard let parsed = URL(string: url), parsed.scheme == "https", parsed.host != nil, parsed.user == nil, parsed.password == nil else { throw DecisionServiceError("이미지는 base64 data URL 또는 공개 HTTPS URL이어야 합니다.") }
                }
                return ["type": "input_image", "image_url": url]
            default: throw DecisionServiceError("지원하지 않는 입력 파트입니다.")
            }
        }
    }
    static func input(_ state: Any) throws -> Any {
        if let text = state as? String { return text }
        guard let messages = state as? [[String: Any]], !messages.isEmpty else { throw DecisionServiceError("판단할 텍스트/이미지 입력이 없습니다.") }
        return try messages.map { message -> [String: Any] in
            guard let role = message["role"] as? String, ["user", "system", "developer"].contains(role), let content = message["content"] else { throw DecisionServiceError("지원하지 않는 입력 메시지 역할 또는 내용입니다.") }
            return ["role": role, "content": try parts(content)]
        }
    }
    static func question(_ id: String, _ value: Any) throws -> [String: Any] {
        guard !id.isEmpty, let q = value as? [String: Any], let type = q["type"] as? String else { throw DecisionServiceError("질문 id/type이 잘못되었습니다.") }
        guard let instructions = q["instructions"] else { throw DecisionServiceError("질문 instructions가 필요합니다.") }
        var result: [String: Any] = ["name": id, "type": type, "instructions": try parts(instructions)]
        switch type {
        case "predicate": break
        case "choice", "score":
            let key = type == "choice" ? "choices" : "levels"
            let name = type == "choice" ? "value" : "label"
            guard let entries = q[key] as? [[String: String]], (type == "choice" ? (2...255) : (2...10)).contains(entries.count),
                  entries.allSatisfy({ !($0[name] ?? "").isEmpty && !($0["description"] ?? "").isEmpty }),
                  Set(entries.compactMap { $0[name] }).count == entries.count else { throw DecisionServiceError("질문의 선택지 또는 점수 수준이 잘못되었습니다.") }
            result[key] = entries
        default: throw DecisionServiceError("지원하지 않는 질문 type입니다.")
        }
        return result
    }
    static func request(_ body: [String: Any], config: DecisionConfiguration, timeout: TimeInterval = 60) throws -> URLRequest {
        try validate(config)
        guard let questions = body["questions"] as? [String: Any], (1...400).contains(questions.count), let state = body["input"] else { throw DecisionServiceError("판단 입력과 질문 1…400개가 필요합니다.") }
        guard !config.apiKey.isEmpty else { throw DecisionServiceError("OpenAI API 키가 없습니다. 메뉴바 설정에서 Keychain에 저장하거나 MCP 환경 키를 설정하세요.") }
        if let override = body["model"] as? String, !override.isEmpty, override != config.model { throw DecisionServiceError("요청 모델은 gpt-6-luna여야 합니다.") }
        let payload: [String: Any] = ["model": config.model, "input": try input(state), "questions": try questions.keys.sorted().map { try question($0, questions[$0]!) }]
        var request = URLRequest(url: URL(string: "https://api.openai.com/v1/decisions")!, timeoutInterval: timeout)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("Bearer " + config.apiKey, forHTTPHeaderField: "Authorization")
        request.httpBody = try JSONSerialization.data(withJSONObject: payload, options: [.sortedKeys])
        return request
    }
    static func decode(_ data: Data, questions: [String: Any], config: DecisionConfiguration) throws -> [String: [String: Any]] {
        guard let object = try JSONSerialization.jsonObject(with: data) as? [String: Any] else { throw DecisionServiceError("판단 응답은 JSON 객체여야 합니다.") }
        guard object["model"] as? String == config.model, let answers = object["answers"] as? [[String: Any]], answers.count == questions.count else { throw DecisionServiceError("OpenAI 응답 모델 또는 질문 수가 다릅니다.") }
        var result: [String: [String: Any]] = [:]
        for (index, answer) in answers.enumerated() {
            guard let name = answer["name"] as? String, name == questions.keys.sorted()[index], result[name] == nil, let q = questions[name], let type = answer["type"] as? String else { throw DecisionServiceError("응답 질문 name이 누락·중복되었거나 예상 밖입니다.") }
            let expected = try question(name, q)
            if type == "refusal" { result[name] = ["type": "unknown"]; continue }
            guard type == expected["type"] as? String else { throw DecisionServiceError("응답 질문 type이 다릅니다.") }
            if type == "predicate" {
                result[name] = ["type": "predicate", "probability": try probability(answer["probability"])]; continue
            }
            let confidence = try probability(answer["confidence"])
            guard let probabilities = answer["probabilities"] as? [[String: Any]] else { throw DecisionServiceError("확률 배열이 없습니다.") }
            let labels = type == "score" ? (expected["levels"] as! [[String: String]]).map { $0["label"]! } : []
            let options = type == "choice" ? (expected["choices"] as! [[String: String]]).map { $0["value"]! } : labels.indices.map(String.init)
            guard probabilities.count == options.count else { throw DecisionServiceError("확률 선택지가 누락되었습니다.") }
            var distribution: [String: Double] = [:]
            for entry in probabilities {
                let value: String
                if type == "choice" {
                    guard let v = entry["value"] as? String else { throw DecisionServiceError("선택 value의 자료형이 다릅니다.") }; value = v
                } else {
                    guard let v = entry["value"] as? NSNumber, CFGetTypeID(v) != CFBooleanGetTypeID(), v.doubleValue.isFinite,
                          v.doubleValue == Double(v.intValue), options.indices.contains(v.intValue), entry["label"] as? String == labels[v.intValue] else { throw DecisionServiceError("점수 value/label이 다릅니다.") }
                    value = String(v.intValue)
                }
                guard options.contains(value), distribution[value] == nil else { throw DecisionServiceError("확률 선택 value가 중복되었거나 예상 밖입니다.") }
                distribution[value] = try probability(entry["probability"])
            }
            guard abs(distribution.values.reduce(0, +) - 1) < 0.001 else { throw DecisionServiceError("확률 합계가 1이 아닙니다.") }
            var converted: [String: Any] = ["type": type, "confidence": confidence, "probabilities": distribution]
            if type == "choice" {
                guard let choice = answer["choice"] as? String, let selected = distribution[choice],
                      selected + 0.001 >= (distribution.values.max() ?? 0) else { throw DecisionServiceError("선택 응답 value와 확률 분포가 다릅니다.") }
                converted["choice"] = choice
            } else {
                guard let n = answer["score"] as? NSNumber, CFGetTypeID(n) != CFBooleanGetTypeID(), n.doubleValue.isFinite,
                      (0...Double(options.count - 1)).contains(n.doubleValue),
                      abs(n.doubleValue - options.enumerated().reduce(0.0) { $0 + Double($1.offset) * distribution[$1.element]! }) < 0.001 else { throw DecisionServiceError("점수와 확률 분포가 일치하지 않습니다.") }
                converted["score"] = n.doubleValue
            }
            result[name] = converted
        }
        guard Set(result.keys) == Set(questions.keys) else { throw DecisionServiceError("응답 질문이 누락되었습니다.") }
        return result
    }
    static let probe: [String: Any] = ["input": "Synthetic connection test: the word is READY.", "questions": ["connection": ["type": "predicate", "instructions": "Does the synthetic text contain READY?"]]]
}

/// Never follow redirects, including 307/308: credentials and evidence stay on the selected origin.
final class DecisionRedirectGuard: NSObject, URLSessionTaskDelegate {
    func urlSession(_ session: URLSession, task: URLSessionTask, willPerformHTTPRedirection response: HTTPURLResponse,
                    newRequest request: URLRequest, completionHandler: @escaping (URLRequest?) -> Void) { completionHandler(nil) }
}
/// Only synchronous tool judgments register here, not settings connection probes. A held HID
/// input must be released promptly even when handleQueue is waiting for a network response.
enum DecisionPendingRequests {
    private static let lock = NSLock()
    private static var cancellations: [UUID: () -> Void] = [:]
    private static var cleanupIDs: Set<UUID> = []
    private static var generation: UInt64 = 0
    static var inputState: (pending: Bool, generation: UInt64) {
        lock.lock(); defer { lock.unlock() }
        return (!cleanupIDs.isEmpty, generation)
    }
    static func register(_ cancel: @escaping () -> Void) -> UUID {
        lock.lock(); defer { lock.unlock() }
        let id = UUID(); cancellations[id] = cancel; return id
    }
    static func remove(_ id: UUID) {
        lock.lock(); defer { lock.unlock() }
        cancellations.removeValue(forKey: id)
    }
    static func cancelForInputCleanup() {
        lock.lock(); generation &+= 1; let active = Array(cancellations.values); lock.unlock()
        active.forEach { $0() }
    }
    /// Keep new judgments out until the queued HID release has actually completed.
    static func beginInputCleanup() -> () -> Void {
        let id = UUID()
        lock.lock(); cleanupIDs.insert(id); generation &+= 1
        let active = Array(cancellations.values); lock.unlock()
        active.forEach { $0() }
        return {
            lock.lock(); cleanupIDs.remove(id); lock.unlock()
        }
    }
}

final class DecisionReplyLatch {
    let ready = DispatchSemaphore(value: 0)
    private let lock = NSLock()
    private var value: Result<[String: [String: Any]], Error>?
    func finish(_ result: Result<[String: [String: Any]], Error>) {
        lock.lock()
        guard value == nil else { lock.unlock(); return }
        value = result; lock.unlock(); ready.signal()
    }
    func get() throws -> [String: [String: Any]] {
        lock.lock(); let result = value; lock.unlock()
        guard let result else { throw DecisionServiceError("판단 응답이 없습니다.") }
        return try result.get()
    }
}

final class DecisionTransport {
    static let shared = DecisionTransport()
    let session: URLSession
    init(session: URLSession? = nil) {
        self.session = session ?? URLSession(configuration: .ephemeral, delegate: DecisionRedirectGuard(), delegateQueue: nil)
    }
    /// Cancellation and a monotonic overall deadline do not depend on an eventual network callback.
    func sendWaiting(_ body: [String: Any], config: DecisionConfiguration, timeout: TimeInterval = 60,
                     isCancelled: () -> Bool = { false }) throws -> [String: [String: Any]] {
        let inputState = DecisionPendingRequests.inputState
        guard !isCancelled(), !inputState.pending else { throw DecisionServiceError("입력 해제 중이거나 판단이 취소되었습니다.") }
        let deadline = DispatchTime.now() + max(0, timeout)
        let latch = DecisionReplyLatch()
        let task = try send(body, config: config, timeout: timeout) { latch.finish($0) }
        let registration = DecisionPendingRequests.register {
            task.cancel()
            latch.finish(.failure(DecisionServiceError("입력 해제를 위해 판단을 취소했습니다.")))
        }
        defer { DecisionPendingRequests.remove(registration) }
        while true {
            if isCancelled() || DecisionPendingRequests.inputState.generation != inputState.generation {
                task.cancel()
                throw DecisionServiceError("판단이 취소되었습니다.")
            }
            if latch.ready.wait(timeout: min(deadline, .now() + .milliseconds(25))) == .success {
                if isCancelled() || DecisionPendingRequests.inputState.generation != inputState.generation {
                    task.cancel()
                    throw DecisionServiceError("판단이 취소되었습니다.")
                }
                guard DispatchTime.now() < deadline else {
                    task.cancel()
                    throw DecisionServiceError("판단 전체 제한 시간이 초과되었습니다.")
                }
                return try latch.get()
            }
            if DispatchTime.now() >= deadline {
                task.cancel()
                throw DecisionServiceError("판단 전체 제한 시간이 초과되었습니다.")
            }
        }
    }
    @discardableResult
    func send(_ body: [String: Any], config: DecisionConfiguration, timeout: TimeInterval = 60,
              completion: @escaping (Result<[String: [String: Any]], Error>) -> Void) throws -> URLSessionDataTask {
        let request = try DecisionCodec.request(body, config: config, timeout: timeout)
        let questions = body["questions"] as! [String: Any]
        let task = session.dataTask(with: request) { data, response, error in
            completion(Result {
                if let error = error as? URLError {
                    switch error.code {
                    case .cancelled: throw DecisionServiceError("연결 확인/판단이 취소되었습니다.")
                    case .timedOut: throw DecisionServiceError("연결 시간이 초과되었습니다. 잠시 후 다시 시도하세요.")
                    default: throw DecisionServiceError("서버와 통신할 수 없습니다. 네트워크와 주소를 확인하세요 (\(error.code.rawValue)).")
                    }
                }
                if error != nil { throw DecisionServiceError("판단 서버 통신 오류입니다.") }
                guard let status = (response as? HTTPURLResponse)?.statusCode else { throw DecisionServiceError("HTTP 응답을 받지 못했습니다.") }
                guard status == 200 else {
                    let message: String
                    switch status {
                    case 401: message = "인증 실패: API 키를 확인하세요."
                    case 403: message = "접근 거부: 계정·프로젝트 권한과 지원 지역을 확인하세요."
                    case 429: message = "요청 한도 또는 사용량 한도를 초과했습니다."
                    case 500...599: message = "서버 오류입니다. 잠시 후 다시 시도하세요."
                    case 300...399: message = "서버가 다른 주소로 이동을 요청했습니다. 키 보호를 위해 전송을 중단했습니다."
                    default: message = "요청이 거부되었습니다. 모델과 설정을 확인하세요."
                    }
                    throw DecisionServiceError("\(message) (HTTP \(status))")
                }
                return try DecisionCodec.decode(data ?? Data(), questions: questions, config: config)
            })
        }
        task.resume(); return task
    }
}
