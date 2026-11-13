import Foundation
import Testing
@testable import AppFeedback
#if DEBUG
import CryptoKit
#endif
#if os(iOS) && !targetEnvironment(macCatalyst)
import MessageUI
#endif

struct FeedbackTests {
    private let info = FeedbackAppInfo(name: "Sample", version: "1.2", build: "3", system: "Test OS", device: "Device")

    @Test func standardContentIncludesOnlySuppliedMetadata() {
        let content = FeedbackContent.standard(info)
        #expect(content.subject == "Sample feedback")
        #expect(content.body == "\n\n\n---\nApp: Sample 1.2 (3)\nOS: Test OS\nDevice: Device")
        #expect(FeedbackMail(recipient: "feedback@example.com", content: content).attachment == nil)
    }

    @Test func mailtoRoundTripsReservedCharacters() throws {
        let content = FeedbackContent(subject: "피드백 + & # ? %", body: "First\nSecond + & = % #")
        let mail = FeedbackMail(recipient: "feedback+test@example.com", content: content)
        let url = try #require(mail.mailtoURL)
        let parts = try #require(URLComponents(url: url, resolvingAgainstBaseURL: false))
        #expect(parts.scheme == "mailto")
        #expect(parts.path == mail.recipient)
        #expect(parts.queryItems?.first { $0.name == "subject" }?.value == content.subject)
        #expect(parts.queryItems?.first { $0.name == "body" }?.value == content.body)
        #expect(parts.percentEncodedQuery?.contains("%2B") == true)
    }

    @Test @MainActor func sessionRoutesAndFinishesWithoutClaimingDelivery() async throws {
        let session = FeedbackSession(recipient: "feedback@example.com", appInfo: info) {
            FeedbackContent(subject: "Custom \($0.name)", body: "User text")
        }
        #expect(await session.prepare(canSendMail: true) == nil)
        #expect(session.composing?.content.subject == "Custom Sample")
        #expect(session.composing?.attachment == nil)
        #expect(await session.prepare(canSendMail: true) == nil)
        session.finish(.handedOff)
        #expect(session.composing == nil)
        #expect(session.status == session.labels.handedOff)
        #expect(await session.prepare(canSendMail: false) != nil)
        session.openedMailLink(accepted: false)
        #expect(session.status == session.labels.unavailable)
        session.addressCopied()
        #expect(session.status == session.labels.copied)
    }

    @Test func outcomeMessagesKeepDraftAndCancellationDistinct() {
        let labels = FeedbackLabels()
        #expect(labels.message(for: .cancelled) == nil)
        #expect(labels.message(for: .savedDraft) == labels.savedDraft)
        #expect(labels.message(for: .failed) == labels.failed)
    }

    #if os(iOS) && !targetEnvironment(macCatalyst)
    @Test func nativeOutcomesMapTruthfully() {
        #expect(FeedbackOutcome(.sent, failed: false) == .handedOff)
        #expect(FeedbackOutcome(.saved, failed: false) == .savedDraft)
        #expect(FeedbackOutcome(.cancelled, failed: false) == .cancelled)
        #expect(FeedbackOutcome(.failed, failed: false) == .failed)
        #expect(FeedbackOutcome(.sent, failed: true) == .failed)
    }
    #endif

    #if DEBUG
    @Test func sealingRejectsWrongKeysTamperingAndMalformedData() throws {
        let key = Curve25519.KeyAgreement.PrivateKey()
        let plaintext = Data(#"{"event":"settingsOpened"}"#.utf8)
        let sealed = try FeedbackSealing.seal(plaintext, to: key.publicKey)
        #expect(sealed.prefix(8) == FeedbackSealing.magic)
        #expect(sealed.subdata(in: 8..<16) == FeedbackSealing.keyID(key.publicKey))
        #expect(try FeedbackSealing.open(sealed, with: key) == plaintext)
        #expect(sealed.range(of: plaintext) == nil)
        #expect(throws: (any Error).self) {
            try FeedbackSealing.open(sealed, with: Curve25519.KeyAgreement.PrivateKey())
        }
        for offset in [0, 8, 16, sealed.count - 1] {
            var changed = sealed
            changed[offset] ^= 1
            #expect(throws: (any Error).self) { try FeedbackSealing.open(changed, with: key) }
        }
        for length in [0, 7, 16, 48, 63] {
            #expect(throws: (any Error).self) { try FeedbackSealing.open(Data(sealed.prefix(length)), with: key) }
        }
    }

    @Test @MainActor func diagnosticsIncludeChecklistOnlyInsideEncryptedFile() async throws {
        let key = Curve25519.KeyAgreement.PrivateKey()
        let diagnostics = FeedbackDiagnostics(publicKeyBase64: key.publicKey.rawRepresentation.base64EncodedString(),
                                              disclosure: "Sample events only") { Data(#"{"event":"opened"}"#.utf8) }
        let attachment = try await diagnostics.attachment(checklist: [.init(id: "sample", title: "Opens settings")])
        let report = try #require(JSONSerialization.jsonObject(
            with: FeedbackSealing.open(attachment.data, with: key)) as? [String: Any])
        let checks = try #require(report["checklist"] as? [[String: Any]])
        #expect(checks.first?["answer"] as? String == "unchecked")
        let mail = FeedbackMail(recipient: "feedback@example.com", content: .standard(info), attachment: attachment)
        #expect(mail.body.hasSuffix(mail.attachmentNotice))
        #expect(!mail.body.contains("Opens settings"))
        #expect(!mail.mailtoURL!.absoluteString.contains("Encrypted"))
        #expect(attachment.fileName.hasSuffix(".afdiag"))
    }

    @Test @MainActor func disabledDiagnosticsNeverCallsProviderAndFailuresRemainVisible() async throws {
        var calls = 0
        let key = Curve25519.KeyAgreement.PrivateKey()
        let session = FeedbackSession(recipient: "feedback@example.com", appInfo: info)
        session.diagnostics = FeedbackDiagnostics(publicKeyBase64: key.publicKey.rawRepresentation.base64EncodedString(),
                                                 disclosure: "Sample") {
            calls += 1
            throw CocoaError(.fileReadUnknown)
        }
        session.attachesDiagnostics = false
        _ = await session.prepare(canSendMail: true)
        #expect(calls == 0)
        session.finish(.cancelled)
        session.attachesDiagnostics = true
        _ = await session.prepare(canSendMail: false)
        session.openedMailLink(accepted: true)
        #expect(calls == 1)
        #expect(session.status == session.labels.collectionFailed)
        #expect(!session.isCollecting)
    }

    @Test @MainActor func invalidKeyDoesNotCollectAndInvalidReportsAreRejected() async throws {
        var collected = false
        let invalid = FeedbackDiagnostics(publicKeyBase64: "invalid", disclosure: "Sample") {
            collected = true
            return Data()
        }
        await #expect(throws: (any Error).self) { try await invalid.attachment() }
        #expect(!collected)
        let key = Curve25519.KeyAgreement.PrivateKey().publicKey.rawRepresentation.base64EncodedString()
        for report in [Data("[]".utf8), Data("not JSON".utf8), Data(repeating: 0, count: 2_000_001)] {
            let diagnostics = FeedbackDiagnostics(publicKeyBase64: key, disclosure: "Sample") { report }
            await #expect(throws: (any Error).self) { try await diagnostics.attachment() }
        }
    }

    @Test @MainActor func cancellationDoesNotPresentMail() async {
        let key = Curve25519.KeyAgreement.PrivateKey().publicKey.rawRepresentation.base64EncodedString()
        let session = FeedbackSession(recipient: "feedback@example.com", appInfo: info)
        session.diagnostics = FeedbackDiagnostics(publicKeyBase64: key, disclosure: "Sample") {
            throw CancellationError()
        }
        #expect(await session.prepare(canSendMail: true) == nil)
        #expect(session.composing == nil)
        #expect(!session.isCollecting)
    }

    /// Optional integration input is generated afresh by verify.py, never a checked-in key.
    @Test @MainActor func exportLibraryAttachmentForToolRoundTrip() async throws {
        let environment = ProcessInfo.processInfo.environment
        guard let publicKey = environment["APP_FEEDBACK_TEST_PUBLIC_KEY"],
              let output = environment["APP_FEEDBACK_TEST_OUTPUT"] else { return }
        let directory = URL(fileURLWithPath: output, isDirectory: true)
        let session = FeedbackSession(recipient: "feedback@example.com", appInfo: info)
        session.diagnostics = FeedbackDiagnostics(publicKeyBase64: publicKey, disclosure: "Synthetic events") {
            Data(#"{"event":"sampleOpened"}"#.utf8)
        }
        #expect(await session.prepare(canSendMail: false, temporaryRoot: directory) != nil)
        let file = try #require(session.diagnosticsFile)
        try Data(contentsOf: file).write(to: directory.appendingPathComponent("roundtrip.afdiag"))
        session.openedMailLink(accepted: false)
        #expect(session.status?.contains(session.labels.unavailable) == true)
        #expect(session.status?.contains(session.labels.separateAttachment) == true)
        session.clearTemporaryFile()
        #expect(!FileManager.default.fileExists(atPath: file.path))
    }
    #else
    @Test @MainActor func releaseNeverProducesAttachmentOrCollectionStatus() async {
        let session = FeedbackSession(recipient: "feedback@example.com", appInfo: info)
        _ = await session.prepare(canSendMail: true)
        #expect(session.composing?.attachment == nil)
        #expect(session.status == nil)
        #expect(session.composing?.body.contains("diagnostics") == false)
    }
    #endif
}
