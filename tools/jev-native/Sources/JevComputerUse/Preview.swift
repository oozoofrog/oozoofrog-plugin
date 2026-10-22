import AppKit
import ScreenCaptureKit

/// UI for one controller session. No input is forwarded by clicking this preview.
@MainActor final class PreviewController: NSObject, NSWindowDelegate {
    private let panel: NSPanel
    private let imageView = NSImageView()
    private let caption = NSTextField(labelWithString: "작업할 창을 기다리고 있어요")
    private let status = NSTextField(labelWithString: "작업을 준비하고 있어요")
    private let pointerDot = NSView(frame: NSRect(x:0,y:0,width:10,height:10))
    private var targetBounds: Rect?
    private var liveTask: Task<Void,Never>?
    private var liveWindow: (UInt32,CGRect)?
    private var statusItem: NSStatusItem!
    var cancelRequested = false
    var onStop: (() -> Void)?
    private(set) var userHidden = false
    override init() {
        panel = NSPanel(contentRect: NSRect(x: 0,y: 0,width: 320,height: 250), styleMask: [.titled, .closable, .nonactivatingPanel, .utilityWindow], backing: .buffered, defer: false)
        super.init()
        panel.title = "작업 미리보기"; panel.level = .floating; panel.hidesOnDeactivate = false; panel.isReleasedWhenClosed = false; panel.delegate = self
        panel.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
        let content = NSView(frame: NSRect(x: 0,y: 0,width: 320,height: 250)); panel.contentView = content
        imageView.frame = NSRect(x: 8,y: 52,width: 304,height: 190); imageView.imageScaling = .scaleProportionallyUpOrDown; imageView.autoresizingMask = [.width, .height]; content.addSubview(imageView)
        pointerDot.wantsLayer = true; pointerDot.layer?.cornerRadius = 5; pointerDot.layer?.borderWidth = 2; pointerDot.layer?.borderColor = NSColor.systemPink.cgColor; pointerDot.layer?.backgroundColor = NSColor.systemPink.withAlphaComponent(0.4).cgColor; pointerDot.isHidden = true; imageView.addSubview(pointerDot)
        caption.frame = NSRect(x: 10,y: 29,width: 300,height: 18); caption.font = .systemFont(ofSize: 11, weight: .medium); caption.lineBreakMode = .byTruncatingMiddle; content.addSubview(caption)
        status.frame = NSRect(x: 10,y: 8,width: 300,height: 17); status.font = .monospacedSystemFont(ofSize: 10, weight: .regular); status.textColor = .secondaryLabelColor; content.addSubview(status)
        if let screen = NSScreen.main { let visible = screen.visibleFrame; panel.setFrameOrigin(NSPoint(x: visible.maxX-336,y: visible.minY+16)) }
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength); statusItem.button?.title = "작업"
        let menu = NSMenu(); let toggle = NSMenuItem(title: "작업 미리보기 표시 / 숨기기", action: #selector(togglePreview), keyEquivalent: ""); toggle.target = self; menu.addItem(toggle)
        let stop = NSMenuItem(title: "작업 중지", action: #selector(stopRequested), keyEquivalent: ""); stop.target = self; menu.addItem(stop)
        menu.addItem(.separator()); let quit = NSMenuItem(title: "작업 도우미 종료", action: #selector(quitController), keyEquivalent: "q"); quit.target = self; menu.addItem(quit); statusItem.menu = menu
        NSApp.setActivationPolicy(.regular)
        if let icon = Bundle.main.url(forResource:"JevNative",withExtension:"icns").flatMap({ NSImage(contentsOf:$0) }) { NSApp.applicationIconImage = icon }
        show()
    }
    func beginRun() { cancelRequested = false; imageView.image = nil; pointerDot.isHidden = true; caption.stringValue = "작업할 창을 기다리고 있어요"; phase("Starting"); show() }
    func finish() { liveTask?.cancel(); liveTask = nil; liveWindow = nil }
    func show() { userHidden = false; panel.orderFrontRegardless() }
    @objc func togglePreview() { if panel.isVisible { hide() } else { show() } }
    func hide() { userHidden = true; panel.orderOut(nil) }
    func windowShouldClose(_ sender: NSWindow) -> Bool { hide(); return false }
    @objc func stopRequested() { cancelRequested = true; onStop?(); status.stringValue = "중지하고 있어요" }
    @objc func quitController() { cancelRequested = true; onStop?(); NSApp.terminate(nil) }
    func update(image: CGImage?, target: String, phase: String, bounds: Rect? = nil) {
        caption.stringValue = target; status.stringValue = UserStatus.progress(phase)
        targetBounds = bounds
        if let image { imageView.image = NSImage(cgImage: image, size: .zero) }
        // Updating a hidden preview must never unhide it or activate the target app.
    }
    func pointer(_ p: CGPoint) {
        guard let bounds = targetBounds, let image = imageView.image, bounds.width > 0, bounds.height > 0 else { return }
        let scale = min(imageView.bounds.width / image.size.width, imageView.bounds.height / image.size.height)
        let width = image.size.width*scale, height = image.size.height*scale
        let x = (imageView.bounds.width-width)/2 + (p.x-bounds.x)/bounds.width*width
        let y = (imageView.bounds.height-height)/2 + (1-(p.y-bounds.y)/bounds.height)*height
        pointerDot.setFrameOrigin(NSPoint(x:x-5,y:y-5)); pointerDot.isHidden = false
    }
    func live(window: SCWindow) {
        if let current=liveWindow, current.0==window.windowID, current.1==window.frame { return }
        liveTask?.cancel(); liveWindow=(window.windowID,window.frame)
        let filter=SCContentFilter(desktopIndependentWindow:window)
        let config=SCStreamConfiguration(); config.width=320; config.height=max(1,Int(320*window.frame.height/max(1,window.frame.width))); config.showsCursor=false
        liveTask=Task { @MainActor [weak self] in
            while !Task.isCancelled {
                guard let self else { return }
                if !self.userHidden, let image=try? await SCScreenshotManager.captureImage(contentFilter:filter,configuration:config) { self.imageView.image=NSImage(cgImage:image,size:.zero) }
                do { try await Task.sleep(nanoseconds:250_000_000) } catch { return }
            }
        }
    }
    func phase(_ text: String) { status.stringValue = UserStatus.progress(text) }
    func dockReopen() { show() }
}

@MainActor final class AppDelegate: NSObject, NSApplicationDelegate {
    static var preview: PreviewController?
    static var goal: GoalWindowController?
    private static var terminationPending = false
    static func completePendingTermination() {
        if terminationPending { terminationPending = false; NSApp.reply(toApplicationShouldTerminate: true) }
    }
    func applicationShouldTerminate(_ sender: NSApplication) -> NSApplication.TerminateReply {
        if Self.goal?.session.active == true { Self.terminationPending = true; Self.goal?.requestStop(); return .terminateLater }
        return .terminateNow
    }
    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool { if let goal = Self.goal { goal.show() } else { Self.preview?.dockReopen() }; return false }
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { false }
}
