#if DEBUG
import CryptoKit
import Foundation

public struct FeedbackCheck: Codable, Identifiable, Equatable, Sendable {
    public enum Answer: String, Codable, CaseIterable, Sendable { case unchecked, passed, failed }
    public let id: String
    public let title: String
    public var answer: Answer
    public var note: String

    public init(id: String, title: String, answer: Answer = .unchecked, note: String = "") {
        self.id = id
        self.title = title
        self.answer = answer
        self.note = note
    }
}

/// The host supplies a bounded, redacted JSON object; no log store is created by this package.
@MainActor
public struct FeedbackDiagnostics {
    public let publicKeyBase64: String
    public let disclosure: String
    public let collect: @MainActor () async throws -> Data

    public init(publicKeyBase64: String, disclosure: String,
                collect: @escaping @MainActor () async throws -> Data) {
        self.publicKeyBase64 = publicKeyBase64
        self.disclosure = disclosure
        self.collect = collect
    }

    public func attachment(checklist: [FeedbackCheck] = []) async throws -> FeedbackAttachment {
        guard let rawKey = Data(base64Encoded: publicKeyBase64) else {
            throw FeedbackDiagnosticError.invalidPublicKey
        }
        let key = try Curve25519.KeyAgreement.PublicKey(rawRepresentation: rawKey)
        let data = try await collect()
        try Task.checkCancellation()
        guard data.count <= FeedbackSealing.maximumPlaintextBytes else {
            throw FeedbackDiagnosticError.tooLarge
        }
        guard let diagnostics = try JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            throw FeedbackDiagnosticError.invalidJSON
        }
        let checks = try JSONSerialization.jsonObject(with: JSONEncoder().encode(checklist))
        let report = try JSONSerialization.data(withJSONObject: [
            "format": 1, "diagnostics": diagnostics, "checklist": checks
        ], options: [.sortedKeys])
        return try FeedbackAttachment(encryptedData: FeedbackSealing.seal(report, to: key))
    }
}

public enum FeedbackDiagnosticError: Error {
    case invalidPublicKey, invalidJSON, tooLarge, malformed, unknownKey
}

/// Format v1: magic (8), key fingerprint (8), encapsulated key (32), authenticated ciphertext.
/// Keep the format in step with scripts/feedback_diagnostics.swift; integration tests cross this boundary.
enum FeedbackSealing {
    static let magic = Data("AFDIAG1\0".utf8)
    static let info = Data("AppFeedback diagnostics v1".utf8)
    static let suite = HPKE.Ciphersuite.Curve25519_SHA256_ChachaPoly
    static let maximumPlaintextBytes = 2_000_000

    static func keyID(_ key: Curve25519.KeyAgreement.PublicKey) -> Data {
        Data(SHA256.hash(data: key.rawRepresentation).prefix(8))
    }

    static func seal(_ plaintext: Data, to key: Curve25519.KeyAgreement.PublicKey) throws -> Data {
        guard plaintext.count <= maximumPlaintextBytes else { throw FeedbackDiagnosticError.tooLarge }
        let compressed = try (plaintext as NSData).compressed(using: .lzfse) as Data
        let header = magic + keyID(key)
        var sender = try HPKE.Sender(recipientKey: key, ciphersuite: suite, info: info)
        let ciphertext = try sender.seal(compressed, authenticating: header)
        return header + sender.encapsulatedKey + ciphertext
    }

    static func open(_ sealed: Data, with key: Curve25519.KeyAgreement.PrivateKey) throws -> Data {
        guard sealed.count >= 64, sealed.prefix(8) == magic else { throw FeedbackDiagnosticError.malformed }
        let bytes = Data(sealed)
        let header = bytes.prefix(16)
        guard header.suffix(8) == keyID(key.publicKey) else { throw FeedbackDiagnosticError.unknownKey }
        var recipient = try HPKE.Recipient(privateKey: key, ciphersuite: suite, info: info,
                                           encapsulatedKey: bytes.subdata(in: 16..<48))
        let compressed = try recipient.open(bytes.subdata(in: 48..<bytes.count), authenticating: header)
        return try (compressed as NSData).decompressed(using: .lzfse) as Data
    }
}
#endif
