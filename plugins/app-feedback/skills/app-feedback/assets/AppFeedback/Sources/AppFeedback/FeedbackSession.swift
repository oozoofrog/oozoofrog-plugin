import Combine
import Foundation

/// Own this session at the settings root, outside changing Form/Section rows.
@MainActor
public final class FeedbackSession: ObservableObject {
    public let recipient: String
    public let labels: FeedbackLabels
    public let appInfo: FeedbackAppInfo
    private let content: (FeedbackAppInfo) -> FeedbackContent
    @Published public var composing: FeedbackMail?
    @Published public private(set) var status: String?
    @Published public private(set) var isCollecting = false
    #if DEBUG
    public var diagnostics: FeedbackDiagnostics?
    @Published public var attachesDiagnostics = true
    @Published public var checklist: [FeedbackCheck] = []
    @Published public private(set) var diagnosticsFile: URL?
    private var hasFallbackAttachment = false
    private var temporaryDirectory: URL?
    #endif

    public init(recipient: String, appInfo: FeedbackAppInfo, labels: FeedbackLabels = FeedbackLabels(),
                content: @escaping (FeedbackAppInfo) -> FeedbackContent = FeedbackContent.standard) {
        self.recipient = recipient
        self.appInfo = appInfo
        self.labels = labels
        self.content = content
    }

    /// Returns a mailto URL only when the native composer is unavailable. Never sends mail itself.
    public func prepare(canSendMail: Bool, temporaryRoot: URL? = nil) async -> URL? {
        guard !isCollecting, composing == nil else { return nil }
        status = nil
        isCollecting = true
        defer { isCollecting = false }
        var attachment: FeedbackAttachment?
        #if DEBUG
        clearTemporaryFile()
        hasFallbackAttachment = false
        if attachesDiagnostics, let diagnostics {
            do {
                attachment = try await diagnostics.attachment(checklist: checklist)
            } catch is CancellationError {
                return nil
            } catch {
                status = labels.collectionFailed
            }
        }
        #endif
        guard !Task.isCancelled else { return nil }
        let mail = FeedbackMail(recipient: recipient, content: content(appInfo), attachment: attachment,
                                attachmentNotice: labels.attachmentNotice)
        if canSendMail {
            composing = mail
            return nil
        }
        #if DEBUG
        if let attachment {
            hasFallbackAttachment = true
            let directory = (temporaryRoot ?? FileManager.default.temporaryDirectory)
                .appendingPathComponent("AppFeedback-\(UUID().uuidString)", isDirectory: true)
            temporaryDirectory = directory
            do {
                try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
                let file = directory.appendingPathComponent(attachment.fileName)
                try attachment.data.write(to: file, options: .atomic)
                diagnosticsFile = file
            } catch {
                clearTemporaryFile()
                appendStatus(labels.shareFailed)
            }
        }
        #endif
        guard let url = mail.mailtoURL else {
            openedMailLink(accepted: false)
            return nil
        }
        return url
    }

    public func openedMailLink(accepted: Bool) {
        if !accepted { appendStatus(labels.unavailable) }
        #if DEBUG
        if hasFallbackAttachment, diagnosticsFile != nil { appendStatus(labels.separateAttachment) }
        #endif
    }

    public func finish(_ outcome: FeedbackOutcome) {
        composing = nil
        if let message = labels.message(for: outcome) { appendStatus(message) }
    }

    public func addressCopied() { status = labels.copied }

    private func appendStatus(_ message: String) {
        status = status.map { $0 + "\n" + message } ?? message
    }

    /// Call when leaving settings, after any share sheet is dismissed. Only this session's file is removed.
    public func clearTemporaryFile() {
        #if DEBUG
        if let temporaryDirectory { try? FileManager.default.removeItem(at: temporaryDirectory) }
        temporaryDirectory = nil
        diagnosticsFile = nil
        #endif
    }
}
