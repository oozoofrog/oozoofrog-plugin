#if os(iOS) && !targetEnvironment(macCatalyst)
import MessageUI
import SwiftUI
import UIKit

/// A stable container owns the sheet. Put the entire settings Form inside this host.
public struct FeedbackHost<Content: View>: View {
    @ObservedObject private var session: FeedbackSession
    private let content: Content

    public init(session: FeedbackSession, @ViewBuilder content: () -> Content) {
        self.session = session
        self.content = content()
    }

    public var body: some View {
        content.sheet(item: $session.composing) { mail in
            FeedbackComposer(mail: mail, onFinish: session.finish)
                .ignoresSafeArea()
        }
    }
}

public struct FeedbackSection: View {
    @ObservedObject private var session: FeedbackSession
    @Environment(\.openURL) private var openURL

    public init(session: FeedbackSession) { self.session = session }

    public var body: some View {
        Section {
            #if DEBUG
            if session.diagnostics != nil {
                Toggle(session.labels.attach, isOn: $session.attachesDiagnostics)
                if session.attachesDiagnostics {
                    ForEach($session.checklist) { $check in
                        Picker(check.title, selection: $check.answer) {
                            Text(session.labels.unchecked).tag(FeedbackCheck.Answer.unchecked)
                            Text(session.labels.passed).tag(FeedbackCheck.Answer.passed)
                            Text(session.labels.failedCheck).tag(FeedbackCheck.Answer.failed)
                        }
                        TextField(session.labels.note, text: $check.note)
                    }
                }
            }
            #endif
            Button {
                Task {
                    if let url = await session.prepare(canSendMail: MFMailComposeViewController.canSendMail()) {
                        openURL(url) { session.openedMailLink(accepted: $0) }
                    }
                }
            } label: {
                HStack {
                    Label(session.labels.write, systemImage: "envelope")
                    if session.isCollecting {
                        ProgressView()
                        Text(session.labels.collecting)
                    }
                }
            }
            .disabled(session.isCollecting || session.composing != nil)
            #if DEBUG
            if let file = session.diagnosticsFile {
                ShareLink(item: file) { Label(session.labels.share, systemImage: "square.and.arrow.up") }
            }
            #endif
            Button {
                UIPasteboard.general.string = session.recipient
                session.addressCopied()
            } label: {
                Label(session.labels.copyAddress, systemImage: "doc.on.doc")
            }
            Text(verbatim: session.recipient).font(.footnote)
            if let status = session.status { Text(status).font(.footnote) }
        } header: {
            Text(session.labels.title)
        } footer: {
            #if DEBUG
            if session.attachesDiagnostics, let diagnostics = session.diagnostics {
                Text(diagnostics.disclosure)
            }
            #endif
        }
        .disabled(session.isCollecting)
    }
}

extension FeedbackOutcome {
    init(_ result: MFMailComposeResult, failed: Bool) {
        guard !failed else { self = .failed; return }
        switch result {
        case .sent: self = .handedOff
        case .saved: self = .savedDraft
        case .cancelled: self = .cancelled
        default: self = .failed
        }
    }
}

private struct FeedbackComposer: UIViewControllerRepresentable {
    let mail: FeedbackMail
    let onFinish: (FeedbackOutcome) -> Void

    func makeCoordinator() -> Coordinator { Coordinator(onFinish: onFinish) }

    func makeUIViewController(context: Context) -> MFMailComposeViewController {
        let controller = MFMailComposeViewController()
        controller.mailComposeDelegate = context.coordinator
        controller.setToRecipients([mail.recipient])
        controller.setSubject(mail.content.subject)
        controller.setMessageBody(mail.body, isHTML: false)
        #if DEBUG
        if let attachment = mail.attachment {
            controller.addAttachmentData(attachment.data, mimeType: FeedbackAttachment.mimeType,
                                         fileName: attachment.fileName)
        }
        #endif
        return controller
    }

    func updateUIViewController(_ controller: MFMailComposeViewController, context: Context) {}

    final class Coordinator: NSObject, MFMailComposeViewControllerDelegate {
        let onFinish: (FeedbackOutcome) -> Void
        init(onFinish: @escaping (FeedbackOutcome) -> Void) { self.onFinish = onFinish }
        func mailComposeController(_ controller: MFMailComposeViewController,
                                   didFinishWith result: MFMailComposeResult, error: Error?) {
            onFinish(FeedbackOutcome(result, failed: error != nil))
        }
    }
}
#endif
