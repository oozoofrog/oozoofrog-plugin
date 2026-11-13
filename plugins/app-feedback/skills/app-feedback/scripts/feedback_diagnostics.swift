#!/usr/bin/env swift
import Foundation
#if os(macOS)
import CryptoKit
import Security

// AppFeedback v1 envelope. Cross-checked against real library attachments by verify.py.
private let magic = Data("AFDIAG1\0".utf8)
private let info = Data("AppFeedback diagnostics v1".utf8)
private let suite = HPKE.Ciphersuite.Curve25519_SHA256_ChachaPoly

private enum ToolError: Error {
    case usage, keychain(OSStatus), malformed, unknownKey, outputExists
}

private struct Arguments {
    let command: String
    let input: String?
    let service: String
    let account: String
    let output: String?

    init(_ arguments: [String]) throws {
        guard let command = arguments.first,
              ["generate-key", "public-key", "decrypt"].contains(command) else { throw ToolError.usage }
        var rest = Array(arguments.dropFirst())
        var input: String?
        if command == "decrypt" {
            guard let first = rest.first, !first.hasPrefix("--") else { throw ToolError.usage }
            input = rest.removeFirst()
        }
        var options: [String: String] = [:]
        while !rest.isEmpty {
            let flag = rest.removeFirst()
            guard ["--service", "--account", "--out"].contains(flag),
                  options[flag] == nil, let value = rest.first,
                  !value.isEmpty, !value.hasPrefix("--") else { throw ToolError.usage }
            options[flag] = rest.removeFirst()
        }
        guard let service = options["--service"], let account = options["--account"],
              (command == "decrypt" ? options["--out"] != nil : options["--out"] == nil) else {
            throw ToolError.usage
        }
        self.command = command
        self.input = input
        self.service = service
        self.account = account
        self.output = options["--out"]
    }

    var keyQuery: [String: Any] {
        [kSecClass as String: kSecClassGenericPassword,
         kSecAttrService as String: service, kSecAttrAccount as String: account]
    }
}

private func keyID(_ key: Curve25519.KeyAgreement.PublicKey) -> Data {
    Data(SHA256.hash(data: key.rawRepresentation).prefix(8))
}

private func printPublicKey(_ key: Curve25519.KeyAgreement.PrivateKey) throws {
    let object = ["keyID": keyID(key.publicKey).map { String(format: "%02x", $0) }.joined(),
                  "publicKeyBase64": key.publicKey.rawRepresentation.base64EncodedString()]
    FileHandle.standardOutput.write(try JSONSerialization.data(withJSONObject: object, options: [.sortedKeys]))
    print()
}

private func readKey(_ arguments: Arguments) throws -> Curve25519.KeyAgreement.PrivateKey {
    var query = arguments.keyQuery
    query[kSecReturnData as String] = true
    query[kSecMatchLimit as String] = kSecMatchLimitOne
    var result: CFTypeRef?
    let status = SecItemCopyMatching(query as CFDictionary, &result)
    guard status == errSecSuccess, let raw = result as? Data else { throw ToolError.keychain(status) }
    return try Curve25519.KeyAgreement.PrivateKey(rawRepresentation: raw)
}

private func generateKey(_ arguments: Arguments) throws {
    let key = Curve25519.KeyAgreement.PrivateKey()
    var attributes = arguments.keyQuery
    attributes[kSecAttrLabel as String] = "\(arguments.service) / \(arguments.account)"
    attributes[kSecValueData as String] = key.rawRepresentation
    // SecItemAdd refuses an existing service/account pair; never replace a developer key.
    let status = SecItemAdd(attributes as CFDictionary, nil)
    guard status == errSecSuccess else { throw ToolError.keychain(status) }
    try printPublicKey(key)
}

private func decrypt(_ arguments: Arguments) throws {
    guard let input = arguments.input, let output = arguments.output else { throw ToolError.usage }
    let destination = URL(fileURLWithPath: output)
    guard !FileManager.default.fileExists(atPath: destination.path) else { throw ToolError.outputExists }
    let sealed = try Data(contentsOf: URL(fileURLWithPath: input))
    guard sealed.count >= 64, sealed.prefix(8) == magic else { throw ToolError.malformed }
    let key = try readKey(arguments)
    let header = sealed.prefix(16)
    guard header.suffix(8) == keyID(key.publicKey) else { throw ToolError.unknownKey }
    var recipient = try HPKE.Recipient(privateKey: key, ciphersuite: suite, info: info,
                                       encapsulatedKey: sealed.subdata(in: 16..<48))
    let compressed = try recipient.open(sealed.subdata(in: 48..<sealed.count), authenticating: header)
    let plaintext = try (compressed as NSData).decompressed(using: .lzfse) as Data
    // Reserve a private file exclusively. Failed decryption never creates an output file.
    let descriptor = Darwin.open(destination.path, O_WRONLY | O_CREAT | O_EXCL, S_IRUSR | S_IWUSR)
    guard descriptor >= 0 else { throw ToolError.outputExists }
    let handle = FileHandle(fileDescriptor: descriptor, closeOnDealloc: true)
    do {
        try handle.write(contentsOf: plaintext)
        try handle.close()
    } catch {
        try? handle.close()
        try? FileManager.default.removeItem(at: destination)
        throw error
    }
    print(destination.path)
}

do {
    let arguments = try Arguments(Array(CommandLine.arguments.dropFirst()))
    switch arguments.command {
    case "generate-key": try generateKey(arguments)
    case "public-key": try printPublicKey(readKey(arguments))
    default: try decrypt(arguments)
    }
} catch {
    let message: String
    switch error {
    case ToolError.usage:
        message = "usage: generate-key | public-key | decrypt INPUT --out NEW_OUTPUT; "
            + "all commands require --service APP_SERVICE --account KEY_NAME"
    case ToolError.keychain(let status): message = "keychain operation failed (\(status)); existing keys are never replaced"
    case ToolError.malformed: message = "not an AppFeedback v1 attachment"
    case ToolError.unknownKey: message = "selected key does not match the attachment"
    case ToolError.outputExists: message = "output exists or cannot be created; choose a new writable path"
    default: message = "operation failed (\((error as NSError).domain)#\((error as NSError).code))"
    }
    FileHandle.standardError.write(Data("feedback_diagnostics: \(message)\n".utf8))
    exit(1)
}
#else
FileHandle.standardError.write(Data("feedback_diagnostics requires macOS.\n".utf8))
exit(1)
#endif
