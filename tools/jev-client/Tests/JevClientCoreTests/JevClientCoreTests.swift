import Foundation
import Testing
@testable import JevClientCore

/// A fake `security` that logs argv and stdin, and serves a stored key for find-generic-password.
private func fakeSecurity(storedKey: String?) throws -> (Keychain, URL) {
    let dir = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
    try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
    let log = dir.appendingPathComponent("log")
    let script = dir.appendingPathComponent("security")
    let stored = storedKey.map { "echo '\($0)'; exit 0" } ?? "exit 44"
    try """
    #!/bin/sh
    echo "argv: $*" >> '\(log.path)'
    if [ "$1" = "-i" ]; then cat >> '\(log.path)'; touch '\(dir.path)/saved'; exit 0; fi
    if [ "$1" = "find-generic-password" ] && [ -f '\(dir.path)/saved' ]; then echo saved-key; exit 0; fi
    \(stored)
    """.write(to: script, atomically: true, encoding: .utf8)
    try FileManager.default.setAttributes([.posixPermissions: 0o755], ofItemAtPath: script.path)
    return (Keychain(securityPath: script.path), log)
}

@Test func environmentWinsOverKeychainAndFile() throws {
    let (keychain, _) = try fakeSecurity(storedKey: "keychain-key-123")
    let credential = resolveCredential(.typesafe, environment: ["TYPESAFE_API_KEY": "env-key-12345"], keychain: keychain)
    #expect(credential?.key == "env-key-12345")
    #expect(credential?.source == "env:TYPESAFE_API_KEY")
}

@Test func keychainThenLegacyFile() throws {
    let (keychain, _) = try fakeSecurity(storedKey: "keychain-key-123")
    #expect(resolveCredential(.typesafe, environment: [:], keychain: keychain)?.source == "keychain:local.jev-client/typesafe")

    let (empty, _) = try fakeSecurity(storedKey: nil)
    let file = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
    try "file-key-12345\n".write(to: file, atomically: true, encoding: .utf8)
    let fromFile = resolveCredential(.typesafe, environment: [:], keychain: empty, legacyFile: file)
    #expect(fromFile?.key == "file-key-12345")
    #expect(resolveCredential(.openai, environment: [:], keychain: empty, legacyFile: file) == nil)
}

@Test func writeSendsKeyOnStdinNotArgv() throws {
    let (keychain, log) = try fakeSecurity(storedKey: nil)
    try keychain.write(.openai, key: "sk-test-abcdef123")
    let lines = try String(contentsOf: log, encoding: .utf8).split(separator: "\n")
    let argvLines = lines.filter { $0.hasPrefix("argv:") }
    #expect(!argvLines.contains { $0.contains("sk-test-abcdef123") })
    #expect(lines.contains { $0.hasPrefix("add-generic-password -U -s local.openai-decisions -a openai") && $0.contains("sk-test-abcdef123") })
}

@Test func rejectsKeysThatCouldBreakTheSecurityCommand() {
    for bad in ["short", "has space key", "quote\"key123", "back\\slash123", "new\nline12345"] {
        #expect(throws: Failure.self) { try validateKey(bad) }
    }
    #expect(throws: Never.self) { try validateKey("sk-proj_ABC-123.xyz") }
}

@Test func askBodyValidation() {
    #expect(throws: Never.self) { try validateAskBody(Data(#"{"model":"jev-latest","state":"x","questions":{"q":{"type":"noul","instructions":"?"}}}"#.utf8)) }
    #expect(throws: Failure.self) { try validateAskBody(Data(#"{"state":"x","questions":{"q":{"type":"noul","instructions":"?"}}}"#.utf8)) }
    #expect(throws: Failure.self) { try validateAskBody(Data(#"{"model":"jev-latest","questions":{"q":{}}}"#.utf8)) }
    #expect(throws: Failure.self) { try validateAskBody(Data(#"{"model":"jev-latest","state":"x","questions":{}}"#.utf8)) }
    #expect(throws: Failure.self) { try validateAskBody(Data("[1]".utf8)) }
}

@Test func requestKeepsKeyInHeaderOnly() {
    let request = makeRequest(path: "v1/models", method: "GET", body: nil, key: "secret-key-123", timeout: 30)
    #expect(request.url?.absoluteString == "https://api.typesafe.ai/v1/models")
    #expect(request.value(forHTTPHeaderField: "Authorization") == "Bearer secret-key-123")
    #expect(!(request.url?.absoluteString.contains("secret") ?? true))
}

@Test func redactsEchoedKey() {
    let out = redact(Data("invalid key secret-key-123 given".utf8), secret: "secret-key-123")
    #expect(String(decoding: out, as: UTF8.self) == "invalid key [REDACTED] given")
}

@Test func invalidRequestsUseTheInvalidExitCode() {
    do {
        try validateAskBody(Data("[1]".utf8))
        Issue.record("expected a failure")
    } catch {
        #expect((error as? Failure)?.code == ExitCode.invalid)
    }
}

@Test func timeoutParsingIsStrict() throws {
    #expect(try parseTimeout(nil) == 60)
    #expect(try parseTimeout("2.5") == 2.5)
    for bad in ["abc", "0", "301", "nan", ""] {
        #expect(throws: Failure.self) { try parseTimeout(bad) }
    }
}

@Test func extraHeadersAreSent() {
    let request = makeRequest(path: "v1/systemone", method: "POST", body: Data("{}".utf8), key: "secret-key-123", timeout: 30,
                              headers: ["TypeSafe-Danger-Zone-Long-Context": "true"])
    #expect(request.value(forHTTPHeaderField: "TypeSafe-Danger-Zone-Long-Context") == "true")
}

private func summary(_ json: String) throws -> [String: Any] {
    try JSONSerialization.jsonObject(with: summarize(Data(json.utf8))) as? [String: Any] ?? [:]
}

@Test func summaryCoversTheThreeAnswerTypes() throws {
    let result = try summary(#"""
    {"model":"jev-1.14.0","usage":{"input_tokens":296,"output_tokens":20},"answers":{
      "refund":{"type":"noul","noul":0.98},
      "tone":{"type":"choice","choice":"angry","confidence":0.9,"probabilities":{"angry":0.8,"calm":0.2}},
      "urgency":{"type":"score","score":1.7,"confidence":0.6,"probabilities":{"0":0.1,"1":0.1,"2":0.8}}}}
    """#)
    #expect(result["contract"] as? Int == 1)
    #expect(result["provider"] as? String == "jev")
    #expect(result["model"] as? String == "jev-1.14.0")
    #expect(result["complete"] as? Bool == true)
    #expect((result["usage"] as? [String: Any])?["input_tokens"] as? Int == 296)
    let answers = result["answers"] as? [[String: Any]] ?? []
    #expect(answers.map { $0["name"] as? String } == ["refund", "tone", "urgency"])
    #expect(answers[0]["type"] as? String == "yesno")
    #expect(answers[0]["probability"] as? Double == 0.98)
    #expect(answers[1]["answer"] as? String == "angry")
    #expect(answers[1]["probability"] as? Double == 0.8)
    #expect(answers[1]["confidence"] == nil)
    #expect(answers[2]["answer"] as? Double == 1.7)
    let text = String(decoding: try summarize(Data(#"{"answers":{"a":{"type":"noul","noul":0.98}}}"#.utf8)), as: UTF8.self)
    #expect(text.contains(#""probability":0.98}"#) || text.contains(#""probability":0.98,"#))
}

@Test func summaryMarksUnusableAnswersIncomplete() throws {
    let result = try summary(#"{"answers":{"a":{"type":"noul","noul":1.5},"b":{"type":"box","box":[0,0,1,1]}}}"#)
    #expect(result["complete"] as? Bool == false)
    #expect((result["answers"] as? [[String: Any]])?.allSatisfy { $0["type"] as? String == "unknown" } == true)
    #expect(throws: Failure.self) { try summarize(Data(#"{"error":"x"}"#.utf8)) }
}
