import Foundation

public let typesafeBaseURL = URL(string: "https://api.typesafe.ai")!

/// Builds a TypeSafe request. The key goes only into the Authorization header, in memory.
public func makeRequest(path: String, method: String, body: Data?, key: String, timeout: TimeInterval, headers: [String: String] = [:]) -> URLRequest {
    var request = URLRequest(url: typesafeBaseURL.appendingPathComponent(path))
    request.httpMethod = method
    request.timeoutInterval = timeout
    request.setValue("Bearer \(key)", forHTTPHeaderField: "Authorization")
    request.setValue("application/json", forHTTPHeaderField: "Accept")
    if let body {
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = body
    }
    for (name, value) in headers { request.setValue(value, forHTTPHeaderField: name) }
    return request
}

/// Checks that a System One request body is a JSON object with `model`, `state` and a nonempty `questions` collection.
/// Question design is left to the API, which returns 422 with field details.
public func validateAskBody(_ data: Data) throws {
    func invalid(_ message: String) -> Failure { Failure(message, code: ExitCode.invalid) }
    guard data.count <= 32 * 1024 * 1024 else { throw invalid("request exceeds 32 MiB") }
    guard let object = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
        throw invalid("request must be a JSON object such as {\"model\": \"jev-latest\", \"state\": ..., \"questions\": {...}}")
    }
    guard let model = object["model"] as? String, !model.isEmpty else {
        throw invalid("request needs `model`, for example \"jev-latest\"")
    }
    guard object["state"] != nil else { throw invalid("request needs `state`") }
    let questions = object["questions"]
    let count = (questions as? [String: Any])?.count ?? (questions as? [Any])?.count ?? 0
    guard count > 0 else { throw invalid("request needs at least one question in `questions`") }
}

/// Parses `--timeout`: a whole or decimal number of seconds from 1 to 300.
public func parseTimeout(_ text: String?) throws -> TimeInterval {
    guard let text else { return 60 }
    guard let value = TimeInterval(text), value.isFinite, (1...300).contains(value) else {
        throw Failure("--timeout must be 1-300 seconds", code: ExitCode.invalid)
    }
    return value
}

/// Version of the summary and exit-code contract shared with `openai-decisions`.
public let contractVersion = 1

/// Converts a System One response into the summary shape shared with `openai-decisions --summary`:
/// one entry per question with `name`, `type` (`yesno`, `choice`, `score`, or `unknown`) and the usable numbers.
/// `probability` is P(yes) for `yesno` and the probability of the selected option for `choice`.
/// Confidence is left out because the two providers compute it differently.
public func summarize(_ response: Data) throws -> Data {
    guard let object = try? JSONSerialization.jsonObject(with: response) as? [String: Any],
          let answers = object["answers"] as? [String: Any] else {
        throw Failure("the API response has no `answers` object", code: ExitCode.apiFailure)
    }
    func unit(_ value: Any?) -> Double? {
        guard let number = value as? NSNumber, CFGetTypeID(number) != CFBooleanGetTypeID() else { return nil }
        let double = number.doubleValue
        return double.isFinite && (0...1).contains(double) ? double : nil
    }
    /// Shortest decimal text for the value, so 0.98 is not written as 0.97999999999999998.
    func json(_ value: Double) -> NSDecimalNumber { NSDecimalNumber(string: "\(value)") }
    var complete = true
    let entries: [[String: Any]] = answers.keys.sorted().map { name in
        let answer = answers[name] as? [String: Any] ?? [:]
        var entry: [String: Any] = ["name": name, "type": "unknown"]
        switch answer["type"] as? String {
        case "noul":
            if let probability = unit(answer["noul"]) {
                entry["type"] = "yesno"
                entry["probability"] = json(probability)
            }
        case "choice":
            if let choice = answer["choice"] as? String,
               let probability = unit((answer["probabilities"] as? [String: Any])?[choice]) {
                entry["type"] = "choice"
                entry["answer"] = choice
                entry["probability"] = json(probability)
            }
        case "score":
            if let score = answer["score"] as? NSNumber, score.doubleValue.isFinite {
                entry["type"] = "score"
                entry["answer"] = json(score.doubleValue)
            }
        default:
            break
        }
        if entry["type"] as? String == "unknown" { complete = false }
        return entry
    }
    var summary: [String: Any] = [
        "contract": contractVersion, "provider": "jev", "complete": complete && !entries.isEmpty, "answers": entries,
    ]
    if let model = object["model"] as? String { summary["model"] = model }
    if let tokens = (object["usage"] as? [String: Any])?["input_tokens"] as? NSNumber {
        summary["usage"] = ["input_tokens": tokens]
    }
    return try JSONSerialization.data(withJSONObject: summary, options: [.sortedKeys])
}

public struct HTTPResult: Sendable {
    public let status: Int
    public let body: Data
}

/// One attempt, no automatic retry: a timed-out request may already have been billed.
public func send(_ request: URLRequest) async throws -> HTTPResult {
    let configuration = URLSessionConfiguration.ephemeral
    configuration.waitsForConnectivity = false
    let session = URLSession(configuration: configuration)
    defer { session.finishTasksAndInvalidate() }
    do {
        let (data, response) = try await session.data(for: request)
        return HTTPResult(status: (response as? HTTPURLResponse)?.statusCode ?? 0, body: data)
    } catch let error as URLError where error.code == .timedOut {
        throw Failure("request timed out after \(Int(request.timeoutInterval))s; not retried because it may already have been billed", code: ExitCode.apiFailure)
    } catch let error as URLError {
        throw Failure("network error: \(error.localizedDescription)", code: ExitCode.apiFailure)
    }
}
