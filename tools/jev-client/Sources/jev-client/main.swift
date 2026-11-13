import AppKit
import Foundation
import JevClientCore

let usage = """
jev-client — TypeSafe Jev (System One) client and API key registration

  jev-client status                         credential sources, no network
  jev-client models                         GET /v1/models (checks the key)
  jev-client ask [--input FILE] [--timeout SECONDS]
                                            POST /v1/systemone with the JSON request on stdin or FILE
  jev-client key set typesafe|openai [--file PATH | --pasteboard | --stdin]
                                            save a key in the login Keychain (default: hidden prompt)
  jev-client key import-legacy              copy ~/.typesafeai into Keychain (the file is kept)
  jev-client key status
  jev-client key delete typesafe|openai

TypeSafe key order: TYPESAFE_API_KEY, Keychain local.jev-client/typesafe, ~/.typesafeai.
The OpenAI key is stored where openai-decisions reads it: Keychain local.openai-decisions/openai.
"""

func option(_ name: String, in args: [String]) -> String? {
    guard let index = args.firstIndex(of: name), index + 1 < args.count else { return nil }
    return args[index + 1]
}

func provider(_ value: String?) throws -> Provider {
    guard let value, let provider = Provider(rawValue: value) else { throw Failure("name the key: typesafe or openai") }
    return provider
}

func readKey(_ args: [String], for provider: Provider) throws -> String {
    let raw: String
    if let path = option("--file", in: args) {
        guard let data = FileManager.default.contents(atPath: path) else { throw Failure("cannot read \(path)") }
        raw = String(decoding: data, as: UTF8.self)
    } else if args.contains("--pasteboard") {
        guard let text = NSPasteboard.general.string(forType: .string) else { throw Failure("the pasteboard has no text") }
        raw = text
    } else if args.contains("--stdin") {
        raw = String(decoding: FileHandle.standardInput.readDataToEndOfFile(), as: UTF8.self)
    } else {
        var buffer = [CChar](repeating: 0, count: 1024)
        guard readpassphrase("\(provider.rawValue) API key (hidden): ", &buffer, buffer.count, RPP_REQUIRE_TTY) != nil else {
            throw Failure("no terminal for a hidden prompt; use --file, --pasteboard or --stdin")
        }
        raw = String(cString: buffer)
        buffer.withUnsafeMutableBufferPointer { $0.update(repeating: 0) }
    }
    return raw.trimmingCharacters(in: .whitespacesAndNewlines)
}

func emit(_ result: HTTPResult, secret: String) throws {
    let body = redact(result.body, secret: secret)
    guard (200..<300).contains(result.status) else {
        FileHandle.standardError.write(body)
        FileHandle.standardError.write(Data("\n".utf8))
        let hint = result.status == 401 ? " (key rejected; register it again with `jev-client key set typesafe`)" : ""
        throw Failure("TypeSafe API returned HTTP \(result.status)\(hint)")
    }
    FileHandle.standardOutput.write(body)
    if body.last != UInt8(ascii: "\n") { FileHandle.standardOutput.write(Data("\n".utf8)) }
}

func typesafeCredential() throws -> Credential {
    guard let credential = resolveCredential(.typesafe) else {
        throw Failure("no TypeSafe key; run `jev-client key set typesafe`")
    }
    return credential
}

func run(_ args: [String]) async throws {
    let keychain = Keychain()
    switch args.first {
    case "status":
        var report: [String: Any] = [:]
        for provider in Provider.allCases {
            report[provider.rawValue] = resolveCredential(provider)?.source ?? NSNull()
        }
        report["network_checked"] = false
        let data = try JSONSerialization.data(withJSONObject: report, options: [.prettyPrinted, .sortedKeys])
        print(String(decoding: data, as: UTF8.self))
    case "models":
        let credential = try typesafeCredential()
        let request = makeRequest(path: "v1/models", method: "GET", body: nil, key: credential.key, timeout: 30)
        try emit(try await send(request), secret: credential.key)
    case "ask":
        let body: Data
        if let path = option("--input", in: args) {
            guard let data = FileManager.default.contents(atPath: path) else { throw Failure("cannot read \(path)") }
            body = data
        } else {
            body = FileHandle.standardInput.readDataToEndOfFile()
        }
        try validateAskBody(body)
        let timeout = TimeInterval(option("--timeout", in: args) ?? "60") ?? 60
        guard (1...300).contains(timeout) else { throw Failure("--timeout must be 1-300 seconds") }
        let credential = try typesafeCredential()
        let request = makeRequest(path: "v1/systemone", method: "POST", body: body, key: credential.key, timeout: timeout)
        try emit(try await send(request), secret: credential.key)
    case "key":
        let rest = Array(args.dropFirst())
        switch rest.first {
        case "set":
            let target = try provider(rest.dropFirst().first)
            let key = try readKey(rest, for: target)
            try keychain.write(target, key: key)
            print("Saved the \(target.rawValue) key in Keychain \(target.service)/\(target.account).")
        case "import-legacy":
            let file = FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent(".typesafeai")
            guard let data = try? Data(contentsOf: file) else { throw Failure("~/.typesafeai not found") }
            try keychain.write(.typesafe, key: String(decoding: data, as: UTF8.self).trimmingCharacters(in: .whitespacesAndNewlines))
            print("Copied ~/.typesafeai into Keychain local.jev-client/typesafe. The file was kept for other tools.")
        case "status":
            for target in Provider.allCases {
                print("\(target.rawValue): keychain \(keychain.exists(target) ? "saved" : "not saved") (\(target.service)/\(target.account))")
            }
        case "delete":
            let target = try provider(rest.dropFirst().first)
            try keychain.delete(target)
            print("Deleted the \(target.rawValue) key from Keychain.")
        default:
            throw Failure("unknown key command\n\n\(usage)")
        }
    case "-h", "--help", "help", nil:
        print(usage)
    default:
        throw Failure("unknown command \(args[0])\n\n\(usage)")
    }
}

do {
    try await run(Array(CommandLine.arguments.dropFirst()))
} catch {
    FileHandle.standardError.write(Data("jev-client: \(error)\n".utf8))
    exit(1)
}
