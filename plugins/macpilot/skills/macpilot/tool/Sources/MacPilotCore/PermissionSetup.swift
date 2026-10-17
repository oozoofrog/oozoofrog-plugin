import AppKit
import ApplicationServices

/// A file drag only adds an app to System Settings. The user still approves
/// the permission there; no AX action or synthetic input changes a TCC toggle.
@MainActor public enum PermissionSetup {
    static func settingsURL(for kind: String) throws -> URL {
        let pane: String
        switch kind {
        case "accessibility": pane = "Privacy_Accessibility"
        case "screenCapture": pane = "Privacy_ScreenCapture"
        default: throw ToolFailure("invalid_argument", "Setup kind must be accessibility or screenCapture")
        }
        return URL(string: "x-apple.systempreferences:com.apple.preference.security?\(pane)")!
    }

    static func applicationURL(executable: URL) throws -> URL {
        let bundle = executable.deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()
        guard bundle.pathExtension == "app", executable.lastPathComponent == "macpilot",
              let info = Bundle(url: bundle), info.bundleIdentifier == "local.macpilot",
              info.executableURL?.standardizedFileURL == executable.standardizedFileURL else {
            throw ToolFailure("app_bundle_required", "Run the signed bin/MacPilot.app bundle; a raw SwiftPM executable cannot be added as this application")
        }
        return bundle
    }

    public static func open(kind: String, timeout: Int) async throws -> [String: Any] {
        _ = try settingsURL(for: kind)
        guard let executable = Bundle.main.executableURL else { throw ToolFailure("app_bundle_required", "Cannot locate MacPilot.app") }
        let url = try applicationURL(executable: executable)
        let configuration = NSWorkspace.OpenConfiguration()
        configuration.arguments = ["permission-setup", kind]
        configuration.createsNewApplicationInstance = true
        configuration.activates = true
        let app: NSRunningApplication = try await withCallbackDeadline(
            timeoutMilliseconds: timeout,
            timeoutFailure: ToolFailure("permission_setup_timeout", "Permission setup launch timed out; the window may still open. Check before retrying.")
        ) { finish in
            NSWorkspace.shared.openApplication(at: url, configuration: configuration) { app, error in
                if let app { finish(.success(app)) }
                else { finish(.failure(error ?? ToolFailure("permission_setup_failed", "Cannot open permission setup"))) }
            }
        }
        return ["status": "permission_setup_launch_accepted", "pid": app.processIdentifier,
                "applicationPath": url.path, "kind": kind, "approvalRequired": true,
                "verification": "Application launch accepted; the helper reports its own permissions. Recheck the calling MCP with mac_doctor after user approval."]
    }

    public static func run(kind: String) throws {
        _ = try settingsURL(for: kind)
        guard let executable = Bundle.main.executableURL else { throw ToolFailure("app_bundle_required", "Cannot locate MacPilot.app") }
        let controller = PermissionSetupController(applicationURL: try applicationURL(executable: executable), kind: kind)
        NSApplication.shared.setActivationPolicy(.accessory)
        controller.show()
        controller.openSettings()
        NSApplication.shared.run()
        withExtendedLifetime(controller) {}
    }
}

@MainActor final class PermissionAppDragView: NSView, NSDraggingSource {
    let applicationURL: URL
    var didEndDrag: ((NSDragOperation) -> Void)?
    private let icon: NSImage
    private var mouseDownEvent: NSEvent?

    init(applicationURL: URL) {
        self.applicationURL = applicationURL
        icon = NSWorkspace.shared.icon(forFile: applicationURL.path)
        super.init(frame: .zero)
        translatesAutoresizingMaskIntoConstraints = false
        wantsLayer = true
        layer?.cornerRadius = 12
        layer?.borderWidth = 1
        layer?.borderColor = NSColor.separatorColor.cgColor
        setAccessibilityElement(true)
        setAccessibilityRole(.image)
        setAccessibilityLabel("MacPilot.app — 권한 목록으로 드래그")
        setAccessibilityHelp("실제 앱 파일을 시스템 설정의 앱 목록으로 드래그합니다. 키보드로 추가하려면 Finder에서 보기를 사용하세요.")
        setAccessibilityIdentifier("permission.appDrag")
    }

    required init?(coder: NSCoder) { fatalError("init(coder:) has not been implemented") }
    override func acceptsFirstMouse(for event: NSEvent?) -> Bool { true }
    override func resetCursorRects() { addCursorRect(bounds, cursor: .openHand) }

    override func draw(_ dirtyRect: NSRect) {
        NSColor.controlBackgroundColor.setFill()
        NSBezierPath(roundedRect: bounds, xRadius: 12, yRadius: 12).fill()
        icon.draw(in: NSRect(x: (bounds.width - 64) / 2, y: 47, width: 64, height: 64))
        let style = NSMutableParagraphStyle()
        style.alignment = .center
        ("MacPilot.app" as NSString).draw(in: NSRect(x: 8, y: 17, width: bounds.width - 16, height: 22),
            withAttributes: [.font: NSFont.systemFont(ofSize: 14, weight: .semibold), .foregroundColor: NSColor.labelColor, .paragraphStyle: style])
    }

    func draggingItem(at point: NSPoint) -> NSDraggingItem {
        // NSURL supplies public.file-url, including escaping/non-ASCII paths.
        let item = NSDraggingItem(pasteboardWriter: applicationURL as NSURL)
        item.setDraggingFrame(NSRect(x: point.x - 32, y: point.y - 32, width: 64, height: 64), contents: icon)
        return item
    }

    override func mouseDown(with event: NSEvent) { mouseDownEvent = event }
    override func mouseUp(with event: NSEvent) { mouseDownEvent = nil }
    override func mouseDragged(with event: NSEvent) {
        guard let initial = mouseDownEvent else { return }
        guard hypot(event.locationInWindow.x - initial.locationInWindow.x, event.locationInWindow.y - initial.locationInWindow.y) >= 4 else { return }
        mouseDownEvent = nil
        let item = draggingItem(at: convert(initial.locationInWindow, from: nil))
        beginDraggingSession(with: [item], event: initial, source: self)
    }

    func draggingSession(_ session: NSDraggingSession, sourceOperationMaskFor context: NSDraggingContext) -> NSDragOperation { .copy }
    func ignoreModifierKeys(for session: NSDraggingSession) -> Bool { true }
    func draggingSession(_ session: NSDraggingSession, endedAt screenPoint: NSPoint, operation: NSDragOperation) { didEndDrag?(operation) }
}

@MainActor private final class PermissionSetupContentView: NSView {
    override func draw(_ dirtyRect: NSRect) {
        NSColor.windowBackgroundColor.setFill()
        dirtyRect.fill()
    }
}

@MainActor final class PermissionSetupController: NSObject, NSWindowDelegate {
    let applicationURL: URL
    let window: NSWindow
    let selector = NSSegmentedControl(labels: ["손쉬운 사용", "화면 캡처"], trackingMode: .selectOne, target: nil, action: nil)
    let status = NSTextField(wrappingLabelWithString: "")
    let feedback = NSTextField(wrappingLabelWithString: "")
    private var timer: Timer?
    var kind: String { selector.selectedSegment == 0 ? "accessibility" : "screenCapture" }

    init(applicationURL: URL, kind: String) {
        self.applicationURL = applicationURL
        window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 416, height: 660), styleMask: [.titled, .closable, .miniaturizable], backing: .buffered, defer: false)
        super.init()
        window.title = "MacPilot 권한 설정"
        window.isReleasedWhenClosed = false
        window.delegate = self
        let stack = NSStackView()
        stack.orientation = .vertical
        stack.alignment = .leading
        stack.spacing = 14
        stack.translatesAutoresizingMaskIntoConstraints = false
        let content = PermissionSetupContentView()
        window.contentView = content
        content.addSubview(stack)
        NSLayoutConstraint.activate([stack.leadingAnchor.constraint(equalTo: content.leadingAnchor, constant: 24), stack.trailingAnchor.constraint(equalTo: content.trailingAnchor, constant: -24), stack.topAnchor.constraint(equalTo: content.topAnchor, constant: 24), stack.bottomAnchor.constraint(lessThanOrEqualTo: content.bottomAnchor, constant: -20)])

        let title = NSTextField(labelWithString: "앱을 권한 목록에 추가")
        title.font = .systemFont(ofSize: 20, weight: .semibold)
        stack.addArrangedSubview(title)
        selector.selectedSegment = kind == "screenCapture" ? 1 : 0
        selector.target = self
        selector.action = #selector(selectionChanged)
        selector.setAccessibilityIdentifier("permission.kind")
        stack.addArrangedSubview(selector)

        let instructions = NSTextField(wrappingLabelWithString: "1. 설정 열기를 누르세요.\n2. 아래 앱을 설정의 앱 목록으로 드래그하세요.\n3. 추가된 앱의 스위치를 켜세요.")
        instructions.font = .systemFont(ofSize: 13)
        stack.addArrangedSubview(instructions)
        let drag = PermissionAppDragView(applicationURL: applicationURL)
        drag.didEndDrag = { [weak self] operation in
            self?.feedback.stringValue = operation.isEmpty ? "드롭이 수락되지 않았습니다. 설정 목록의 ＋로 앱을 추가할 수도 있습니다." : "드롭이 수락됐습니다. 설정에서 앱의 스위치를 켜세요."
            self?.refresh()
        }
        stack.addArrangedSubview(drag)
        NSLayoutConstraint.activate([drag.widthAnchor.constraint(equalTo: stack.widthAnchor), drag.heightAnchor.constraint(equalToConstant: 132)])
        let path = NSTextField(wrappingLabelWithString: applicationURL.path)
        path.font = .systemFont(ofSize: 11)
        path.textColor = .secondaryLabelColor
        path.isSelectable = true
        stack.addArrangedSubview(path)
        let buttons = NSStackView(views: [button("설정 열기", #selector(openSettings), "permission.openSettings"), button("Finder에서 보기", #selector(reveal), "permission.reveal")])
        buttons.spacing = 8
        stack.addArrangedSubview(buttons)
        status.font = .systemFont(ofSize: 13, weight: .medium)
        status.setAccessibilityIdentifier("permission.status")
        stack.addArrangedSubview(status)
        feedback.font = .systemFont(ofSize: 12)
        feedback.textColor = .secondaryLabelColor
        feedback.stringValue = "상태는 이 창 프로세스 기준입니다. 기존 MCP 권한은 mac_doctor로 다시 확인하세요."
        stack.addArrangedSubview(feedback)
        let help = NSTextField(wrappingLabelWithString: "macOS가 ChatGPT·Codex 등 호스트 앱을 요청하면 해당 앱도 허용하세요. 재시작 안내가 나오면 해당 앱을 다시 실행하세요.")
        help.font = .systemFont(ofSize: 11)
        help.textColor = .secondaryLabelColor
        stack.addArrangedSubview(help)
        for view in stack.arrangedSubviews where view is NSTextField {
            view.widthAnchor.constraint(equalTo: stack.widthAnchor).isActive = true
        }
        refresh()
    }

    private func button(_ title: String, _ action: Selector, _ identifier: String) -> NSButton {
        let button = NSButton(title: title, target: self, action: action)
        button.setAccessibilityIdentifier(identifier)
        return button
    }

    func show() {
        if let screen = NSScreen.main {
            let frame = screen.visibleFrame
            window.setFrameTopLeftPoint(NSPoint(x: frame.minX + 24, y: frame.maxY - 40))
        }
        window.makeKeyAndOrderFront(nil)
        NSApplication.shared.activate(ignoringOtherApps: true)
        timer = Timer.scheduledTimer(withTimeInterval: 1, repeats: true) { [weak self] _ in
            Task { @MainActor in self?.refresh() }
        }
        print(String(data: try! jsonData(["status": "permission_setup_visible", "pid": getpid(), "applicationPath": applicationURL.path, "approvalRequired": true]), encoding: .utf8)!)
        fflush(stdout)
    }

    @objc func selectionChanged() { refresh() }
    @objc func openSettings() {
        guard let url = try? PermissionSetup.settingsURL(for: kind) else { return }
        feedback.stringValue = NSWorkspace.shared.open(url) ? "설정의 앱 목록으로 MacPilot.app을 드래그하세요." : "설정을 열지 못했습니다. 시스템 설정 → 개인정보 보호 및 보안에서 열어주세요."
    }
    @objc func reveal() { NSWorkspace.shared.activateFileViewerSelecting([applicationURL]) }
    func refresh() {
        let ax = AXIsProcessTrusted(), screen = CGPreflightScreenCaptureAccess()
        status.stringValue = "이 창의 권한\n손쉬운 사용: \(ax ? "허용됨" : "미허용")  ·  화면 캡처: \(screen ? "허용됨" : "미허용")"
        status.textColor = ax && screen ? .systemGreen : .labelColor
    }
    func windowWillClose(_ notification: Notification) {
        timer?.invalidate()
        NSApplication.shared.stop(nil)
        NSApplication.shared.postEvent(NSEvent.otherEvent(with: .applicationDefined, location: .zero, modifierFlags: [], timestamp: 0, windowNumber: 0, context: nil, subtype: 0, data1: 0, data2: 0)!, atStart: false)
    }
}
