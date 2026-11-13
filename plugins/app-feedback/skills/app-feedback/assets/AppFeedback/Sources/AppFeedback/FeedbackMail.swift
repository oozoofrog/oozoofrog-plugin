import Foundation

public struct FeedbackAppInfo: Equatable, Sendable {
    public let name: String
    public let version: String
    public let build: String
    public let system: String
    public let device: String

    public init(name: String, version: String, build: String, system: String, device: String) {
        self.name = name
        self.version = version
        self.build = build
        self.system = system
        self.device = device
    }
}

public struct FeedbackContent: Equatable, Sendable {
    public let subject: String
    public let body: String

    public init(subject: String, body: String) {
        self.subject = subject
        self.body = body
    }

    public static func standard(_ info: FeedbackAppInfo) -> Self {
        Self(subject: "\(info.name) feedback",
             body: "\n\n\n---\nApp: \(info.name) \(info.version) (\(info.build))"
                + "\nOS: \(info.system)\nDevice: \(info.device)")
    }
}

/// Only the Debug encryption path can construct an attachment.
public struct FeedbackAttachment: Equatable, Sendable {
    public let data: Data
    public let fileName: String
    public static let mimeType = "application/octet-stream"

    #if DEBUG
    init(encryptedData: Data) {
        data = encryptedData
        fileName = "feedback-\(UUID().uuidString).afdiag"
    }
    #else
    private init(data: Data, fileName: String) {
        self.data = data
        self.fileName = fileName
    }
    #endif
}

public struct FeedbackMail: Identifiable, Equatable, Sendable {
    public let id = UUID()
    public let recipient: String
    public let content: FeedbackContent
    public let attachment: FeedbackAttachment?
    public let attachmentNotice: String

    public init(recipient: String, content: FeedbackContent,
                attachment: FeedbackAttachment? = nil,
                attachmentNotice: String = "Encrypted diagnostics attached.") {
        self.recipient = recipient
        self.content = content
        #if DEBUG
        self.attachment = attachment
        #else
        self.attachment = nil
        #endif
        self.attachmentNotice = attachmentNotice
    }

    public var body: String {
        content.body + (attachment == nil ? "" : "\n" + attachmentNotice)
    }

    /// mailto cannot carry attachments, so it must not claim one is attached.
    public var mailtoURL: URL? {
        var components = URLComponents()
        components.scheme = "mailto"
        components.path = recipient
        components.queryItems = [URLQueryItem(name: "subject", value: content.subject),
                                 URLQueryItem(name: "body", value: content.body)]
        // Some mail handlers decode '+' as a space even outside form submissions.
        components.percentEncodedQuery = components.percentEncodedQuery?
            .replacingOccurrences(of: "+", with: "%2B")
        return components.url
    }
}

/// A composer handoff is not confirmation of delivery.
public enum FeedbackOutcome: Equatable, Sendable {
    case handedOff, savedDraft, cancelled, failed
}

/// Replace these strings with the host app's localized copy.
public struct FeedbackLabels: Sendable {
    public var title = "Feedback"
    public var write = "Write feedback email"
    public var collecting = "Collecting diagnostics"
    public var attach = "Attach encrypted diagnostics"
    public var share = "Share encrypted diagnostics"
    public var copyAddress = "Copy email address"
    public var copied = "Email address copied."
    public var unavailable = "Email is unavailable. Copy the address and use another email app."
    public var separateAttachment = "Email links cannot attach files. Share the encrypted file separately."
    public var collectionFailed = "Diagnostics could not be prepared. Continuing without an attachment."
    public var shareFailed = "The encrypted file could not be prepared for sharing."
    public var attachmentNotice = "Encrypted diagnostics attached."
    public var handedOff = "Email handed to Mail. Delivery cannot be confirmed here."
    public var savedDraft = "Draft saved. It has not been sent."
    public var failed = "Email could not be sent. Copy the address and use another email app."
    public var checklist = "Checks"
    public var unchecked = "Not checked"
    public var passed = "Passed"
    public var failedCheck = "Failed"
    public var note = "Note (do not include personal information)"

    public init() {}

    public func message(for outcome: FeedbackOutcome) -> String? {
        switch outcome {
        case .handedOff: handedOff
        case .savedDraft: savedDraft
        case .cancelled: nil
        case .failed: failed
        }
    }
}
