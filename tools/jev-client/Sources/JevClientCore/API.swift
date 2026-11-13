import Foundation

public let typesafeBaseURL = URL(string: "https://api.typesafe.ai")!

/// Builds a TypeSafe request. The key goes only into the Authorization header, in memory.
public func makeRequest(path: String, method: String, body: Data?, key: String, timeout: TimeInterval) -> URLRequest {
    var request = URLRequest(url: typesafeBaseURL.appendingPathComponent(path))
    request.httpMethod = method
    request.timeoutInterval = timeout
    request.setValue("Bearer \(key)", forHTTPHeaderField: "Authorization")
    request.setValue("application/json", forHTTPHeaderField: "Accept")
    if let body {
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = body
    }
    return request
}

/// Checks that a System One request body is a JSON object with `state` and a nonempty `questions` collection.
/// Question design is left to the API, which returns 422 with field details.
public func validateAskBody(_ data: Data) throws {
    guard data.count <= 32 * 1024 * 1024 else { throw Failure("request exceeds 32 MiB") }
    guard let object = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
        throw Failure("request must be a JSON object such as {\"state\": ..., \"questions\": {...}}")
    }
    guard object["state"] != nil else { throw Failure("request needs `state`") }
    let questions = object["questions"]
    let count = (questions as? [String: Any])?.count ?? (questions as? [Any])?.count ?? 0
    guard count > 0 else { throw Failure("request needs at least one question in `questions`") }
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
        throw Failure("request timed out after \(Int(request.timeoutInterval))s; not retried because it may already have been billed")
    } catch let error as URLError {
        throw Failure("network error: \(error.localizedDescription)")
    }
}
