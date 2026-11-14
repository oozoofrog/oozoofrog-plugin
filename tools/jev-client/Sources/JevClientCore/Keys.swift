import Foundation

/// A provider whose API key this tool stores in the macOS login Keychain.
public enum Provider: String, CaseIterable, Sendable {
    case typesafe, openai

    /// Keychain item. The OpenAI entry is the one `openai-decisions` reads first.
    public var service: String { self == .typesafe ? "local.jev-client" : "local.openai-decisions" }
    public var account: String { self == .typesafe ? "typesafe" : "openai" }
    public var environmentName: String { self == .typesafe ? "TYPESAFE_API_KEY" : "OPENAI_API_KEY" }
}

/// Exit codes shared with `openai-decisions`, so callers can tell failures apart.
public enum ExitCode {
    /// Any other failure (for example a Keychain write).
    public static let failure: Int32 = 1
    /// Bad arguments or request. Nothing was sent.
    public static let invalid: Int32 = 2
    /// No usable credential. Nothing was sent.
    public static let notReady: Int32 = 3
    /// The request was sent or attempted and failed; it may have been billed. Not a negative answer.
    public static let apiFailure: Int32 = 4
}

public struct Failure: Error, CustomStringConvertible {
    public let description: String
    /// Process exit code: see `ExitCode`.
    public let code: Int32
    public init(_ description: String, code: Int32 = ExitCode.failure) {
        self.description = description
        self.code = code
    }
}

/// Runs `/usr/bin/security`. Writes go through `security -i` on stdin so the key never appears in argv.
public struct Keychain: Sendable {
    public var securityPath: String

    public init(securityPath: String = ProcessInfo.processInfo.environment["JEV_CLIENT_SECURITY_BIN"] ?? "/usr/bin/security") {
        self.securityPath = securityPath
    }

    public func read(_ provider: Provider) -> String? {
        let result = try? run(["find-generic-password", "-s", provider.service, "-a", provider.account, "-w"])
        guard let result, result.status == 0 else { return nil }
        let key = String(decoding: result.stdout, as: UTF8.self).trimmingCharacters(in: .whitespacesAndNewlines)
        return key.isEmpty ? nil : key
    }

    public func exists(_ provider: Provider) -> Bool {
        (try? run(["find-generic-password", "-s", provider.service, "-a", provider.account]))?.status == 0
    }

    public func write(_ provider: Provider, key: String) throws {
        try validateKey(key)
        let command = "add-generic-password -U -s \(provider.service) -a \(provider.account) -l \"\(provider.service) \(provider.account)\" -w \"\(key)\"\n"
        let result = try run(["-i"], stdin: Data(command.utf8))
        guard result.status == 0, exists(provider) else {
            throw Failure("Keychain did not save the \(provider.rawValue) key (security exit \(result.status))")
        }
    }

    public func delete(_ provider: Provider) throws {
        let result = try run(["delete-generic-password", "-s", provider.service, "-a", provider.account])
        guard result.status == 0 else { throw Failure("no saved \(provider.rawValue) key in Keychain") }
    }

    private func run(_ arguments: [String], stdin: Data? = nil) throws -> (status: Int32, stdout: Data) {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: securityPath)
        process.arguments = arguments
        let output = Pipe()
        process.standardOutput = output
        process.standardError = FileHandle.nullDevice
        let input = Pipe()
        process.standardInput = stdin == nil ? FileHandle.nullDevice : input
        try process.run()
        if let stdin {
            input.fileHandleForWriting.write(stdin)
            try? input.fileHandleForWriting.close()
        }
        let data = output.fileHandleForReading.readDataToEndOfFile()
        process.waitUntilExit()
        return (process.terminationStatus, data)
    }
}

/// API keys are single tokens. Rejecting whitespace and quotes also keeps the `security -i` line unambiguous.
public func validateKey(_ key: String) throws {
    guard key.count >= 8, key.count <= 512,
          key.unicodeScalars.allSatisfy({ $0.value > 0x20 && $0.value < 0x7F && $0 != "\"" && $0 != "\\" && $0 != "'" })
    else { throw Failure("that does not look like an API key (one token of printable ASCII, 8-512 characters)") }
}

public struct Credential: Sendable {
    public let key: String
    public let source: String
}

/// Order: environment variable, Keychain, then (TypeSafe only) the legacy `~/.typesafeai` file.
public func resolveCredential(
    _ provider: Provider,
    environment: [String: String] = ProcessInfo.processInfo.environment,
    keychain: Keychain = Keychain(),
    legacyFile: URL = FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent(".typesafeai")
) -> Credential? {
    if let key = environment[provider.environmentName], !key.isEmpty {
        return Credential(key: key, source: "env:\(provider.environmentName)")
    }
    if let key = keychain.read(provider) {
        return Credential(key: key, source: "keychain:\(provider.service)/\(provider.account)")
    }
    if provider == .typesafe, let data = try? Data(contentsOf: legacyFile) {
        let key = String(decoding: data, as: UTF8.self).trimmingCharacters(in: .whitespacesAndNewlines)
        if !key.isEmpty { return Credential(key: key, source: "file:~/.typesafeai") }
    }
    return nil
}

public func redact(_ data: Data, secret: String) -> Data {
    guard !secret.isEmpty, let text = String(data: data, encoding: .utf8) else { return data }
    return Data(text.replacingOccurrences(of: secret, with: "[REDACTED]").utf8)
}
