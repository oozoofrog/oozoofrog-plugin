import Foundation

final class MockDecisionProtocol: URLProtocol {
    static var handler: ((URLRequest) -> (Int, Data))!
    static var failure: URLError?
    static var stall = false
    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }
    override func startLoading() {
        if Self.stall { return }
        if let failure = Self.failure { client?.urlProtocol(self, didFailWithError: failure); return }
        let (status, data) = Self.handler(request)
        client?.urlProtocol(self, didReceive: HTTPURLResponse(url: request.url!, statusCode: status, httpVersion: nil, headerFields: nil)!, cacheStoragePolicy: .notAllowed)
        client?.urlProtocol(self, didLoad: data); client?.urlProtocolDidFinishLoading(self)
    }
    override func stopLoading() {}
}
@main struct DecisionChecks {
    static func require(_ condition: Bool, _ label: String) { if !condition { fatalError(label) } }
    static func json(_ object: Any) -> Data { try! JSONSerialization.data(withJSONObject: object) }
    static func main() throws {
        let configuration = URLSessionConfiguration.ephemeral; configuration.protocolClasses = [MockDecisionProtocol.self]
        let transport = DecisionTransport(session: URLSession(configuration: configuration))
        var config = DecisionConfiguration(); config.model = "gpt-6-luna"; config.apiKey = "synthetic-key"
        let body: [String: Any] = ["input": [["role": "user", "content": [["type": "input_text", "text": "synthetic"], ["type": "input_image", "image_url": "data:image/png;base64,AQ=="]]]], "questions": [
            "a": ["type": "predicate", "instructions": "visible?"],
            "b": ["type": "choice", "instructions": "which?", "choices": [["value": "x", "description": "X"], ["value": "y", "description": "Y"]]],
            "c": ["type": "score", "instructions": "how?", "levels": [["label": "0", "description": "low"], ["label": "1", "description": "high"]]],
            "d": ["type": "predicate", "instructions": "refuse?"]]]
        let answer: [[String: Any]] = [
            ["name": "a", "type": "predicate", "probability": 0.9],
            ["name": "b", "type": "choice", "choice": "x", "confidence": 0.8, "probabilities": [["value": "x", "probability": 0.8], ["value": "y", "probability": 0.2]]],
            ["name": "c", "type": "score", "score": 0.25, "confidence": 0.7, "probabilities": [["value": 0, "label": "0", "probability": 0.75], ["value": 1, "label": "1", "probability": 0.25]]],
            ["name": "d", "type": "refusal"]]
        func run(_ status: Int, _ data: Data) throws -> Result<[String: [String: Any]], Error> {
            MockDecisionProtocol.handler = { request in
                require(request.url?.absoluteString == "https://api.openai.com/v1/decisions", "endpoint")
                require(request.value(forHTTPHeaderField: "Authorization") == "Bearer synthetic-key", "header")
                var bytes = request.httpBody ?? Data()
                if bytes.isEmpty, let stream = request.httpBodyStream {
                    stream.open(); defer { stream.close() }; var buffer = [UInt8](repeating: 0, count: 4096)
                    while true { let count = stream.read(&buffer, maxLength: buffer.count); if count <= 0 { break }; bytes.append(contentsOf: buffer.prefix(count)) }
                }
                let sent = try! JSONSerialization.jsonObject(with: bytes) as! [String: Any]
                require(sent["state"] == nil && sent["model"] as? String == "gpt-6-luna", "body")
                let input = sent["input"] as! [[String: Any]]; let parts = input[0]["content"] as! [[String: Any]]
                require(parts[0]["type"] as? String == "input_text" && parts[1]["type"] as? String == "input_image", "image conversion")
                let qs = sent["questions"] as! [[String: Any]]
                require(qs.map { $0["type"] as! String } == ["predicate", "choice", "score", "predicate"], "question conversion")
                require((qs[0]["instructions"] as! String).contains("visible"), "instructions")
                return (status, data)
            }
            let semaphore = DispatchSemaphore(value: 0); var result: Result<[String: [String: Any]], Error>!
            _ = try transport.send(body, config: config) { result = $0; semaphore.signal() }
            require(semaphore.wait(timeout: .now() + 5) == .success, "completion timeout")
            return result
        }
        let valid = try run(200, json(["model": "gpt-6-luna", "answers": answer])).get()
        require(valid["a"]?["probability"] as? Double == 0.9 && valid["b"]?["choice"] as? String == "x" && valid["c"]?["score"] as? Double == 0.25 && valid["d"]?["type"] as? String == "unknown", "decode")
        func fails(_ result: Result<[String: [String: Any]], Error>) -> Bool { if case .failure = result { return true }; return false }
        for status in [401, 403, 429, 500, 302] { require(fails(try run(status, Data())), "HTTP failure") }
        require(fails(try run(200, Data("bad".utf8))), "malformed")
        for code in [URLError.timedOut, URLError.cancelled] {
            MockDecisionProtocol.failure = URLError(code)
            require(fails(try run(200, Data())), "network error")
            MockDecisionProtocol.failure = nil
        }
        var wrong = answer; wrong[0]["probability"] = true
        require(fails(try run(200, json(["model": "gpt-6-luna", "answers": wrong]))), "bool probability")
        wrong = answer; wrong[0]["probability"] = 1.1
        require(fails(try run(200, json(["model": "gpt-6-luna", "answers": wrong]))), "range")
        wrong = answer; wrong[1]["name"] = "a"
        require(fails(try run(200, json(["model": "gpt-6-luna", "answers": wrong]))), "duplicate")
        wrong = answer; wrong[2]["score"] = 0.9
        require(fails(try run(200, json(["model": "gpt-6-luna", "answers": wrong]))), "score mismatch")
        require(fails(try run(200, json(["model": "wrong", "answers": answer]))), "model")
        require(fails(try run(200, json(["model": "gpt-6-luna", "answers": Array(answer.dropLast())]))), "missing")
        do { _ = try DecisionCodec.probability(Double.nan); fatalError("nan") } catch {}
        let suite = "mac-cu-decision-test-" + UUID().uuidString; let defaults = UserDefaults(suiteName: suite)!
        defer { defaults.removePersistentDomain(forName: suite) }
        let resolved = try DecisionSettings.resolve(session: ["OPENAI_API_KEY": "session"], environment: ["OPENAI_API_KEY": "process"], defaults: defaults, readKey: { "stored" })
        require(resolved.apiKey == "stored", "key precedence")
        require(try DecisionSettings.resolve(session: ["OPENAI_API_KEY": "session"], environment: ["OPENAI_API_KEY": "process"], defaults: defaults, readKey: { "" }).apiKey == "session", "session precedence")
        require(try DecisionSettings.resolve(environment: ["OPENAI_API_KEY": "process"], defaults: defaults, readKey: { "" }).apiKey == "process", "environment precedence")
        do { _ = try DecisionCodec.input([["role": "assistant", "content": "text"]]); fatalError("assistant role") } catch {}
        MockDecisionProtocol.stall = true
        let start = DispatchTime.now().uptimeNanoseconds
        do { _ = try transport.sendWaiting(body, config: config, timeout: 0.08); fatalError("timeout") } catch {}
        require(Double(DispatchTime.now().uptimeNanoseconds - start) / 1e9 < 0.5, "overall deadline")
        let lock = NSLock(); var cancelled = false
        DispatchQueue.global().asyncAfter(deadline: .now() + 0.05) { lock.lock(); cancelled = true; lock.unlock() }
        let cancelStart = DispatchTime.now().uptimeNanoseconds
        do { _ = try transport.sendWaiting(body, config: config, timeout: 2, isCancelled: { lock.lock(); defer { lock.unlock() }; return cancelled }); fatalError("cancel") } catch {}
        require(Double(DispatchTime.now().uptimeNanoseconds - cancelStart) / 1e9 < 0.5, "request cancellation")
        DispatchQueue.global().asyncAfter(deadline: .now() + 0.05) { DecisionPendingRequests.cancelForInputCleanup() }
        do { _ = try transport.sendWaiting(body, config: config, timeout: 2); fatalError("cleanup") } catch {}
        MockDecisionProtocol.stall = false
        require(!fails(try run(200, json(["model": "gpt-6-luna", "answers": answer]))), "request after cancellation")
        let finishCleanup = DecisionPendingRequests.beginInputCleanup()
        do { _ = try transport.sendWaiting(body, config: config); fatalError("new judgment blocked during queued input release") } catch {}
        require(DecisionPendingRequests.inputState.pending, "input release remains pending until delivered")
        finishCleanup(); finishCleanup() // Completion is idempotent, including a failed HID connection.
        require(!DecisionPendingRequests.inputState.pending, "input release completed")
        let waiting = DispatchSemaphore(value: 0)
        var inspections = 0
        lock.lock(); cancelled = false; lock.unlock()
        let responseData = json(["model": "gpt-6-luna", "answers": answer])
        MockDecisionProtocol.handler = { _ in
            require(waiting.wait(timeout: .now() + 1) == .success, "waiter entered before response")
            lock.lock(); cancelled = true; lock.unlock()
            return (200, responseData)
        }
        do {
            _ = try transport.sendWaiting(body, config: config, timeout: 2, isCancelled: {
                inspections += 1
                lock.lock(); let value = cancelled; lock.unlock()
                if inspections == 2 { waiting.signal() }
                return value
            })
            fatalError("successful callback must not bypass cancellation recorded during wait")
        } catch {}
        let latch = DecisionReplyLatch()
        latch.finish(.failure(DecisionServiceError("synthetic cancellation")))
        latch.finish(.success(valid)) // A late network completion cannot overwrite cancellation.
        require(latch.ready.wait(timeout: .now() + 0.1) == .success, "single completion delivered")
        require(latch.ready.wait(timeout: .now() + 0.01) == .timedOut, "duplicate completion suppressed")
        do { _ = try latch.get(); fatalError("late success replaced cancellation") } catch {}
        print("decision service self-check passed")
    }
}
