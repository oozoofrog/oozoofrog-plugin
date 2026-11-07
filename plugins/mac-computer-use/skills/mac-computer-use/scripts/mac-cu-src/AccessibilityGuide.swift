// The guide for a permission (`mac-cu --accessibility-guide [app [icon app]]`, `--screen-recording-guide`):
// System Settings opens at the page of the permission in Privacy & Security, and a panel below its window
// shows mac-cu.app (the daemon, which holds the permissions). The user drags that icon into the list. The
// panel closes when the permission is on.

import AppKit
import ApplicationServices

enum Permission: String {
    case accessibility = "--accessibility-guide"
    case screenRecording = "--screen-recording-guide"

    var settings: URL {
        URL(string: "x-apple.systempreferences:com.apple.preference.security?"
            + (self == .accessibility ? "Privacy_Accessibility" : "Privacy_ScreenCapture"))!
    }

    var name: String { self == .accessibility ? "Accessibility" : "Screen Recording" }

    /// For Screen Recording, a new process asks: the answer in a process can stay the same after the user
    /// changes the setting.
    var isGranted: Bool {
        if self == .accessibility { return AXIsProcessTrusted() }
        let check = Process()
        check.executableURL = URL(fileURLWithPath: Bundle.main.executablePath ?? CommandLine.arguments[0])
        check.arguments = ["--check-screen-recording"]
        check.standardInput = FileHandle.nullDevice
        check.standardOutput = FileHandle.nullDevice
        check.standardError = FileHandle.nullDevice
        guard (try? check.run()) != nil else { return false }
        check.waitUntilExit()
        return check.terminationStatus == 0
    }
}

let accessibilitySettings = Permission.accessibility.settings

/// The apps of the parent processes, nearest first. The first is the app that macOS asks about for
/// this process. (The Claude app starts Claude Code as its own claude.app; a terminal app starts a shell.)
func parentApps() -> [URL] {
    var apps: [URL] = []
    var pid = getppid()
    while pid > 1 {
        var buffer = [CChar](repeating: 0, count: 4096)
        if proc_pidpath(pid, &buffer, UInt32(buffer.count)) > 0 {
            let path = String(cString: buffer)
            // An app in a framework (Python.app of python3) only runs a tool: macOS does not ask about it.
            if !path.contains(".framework/"), let range = path.range(of: ".app/Contents/MacOS/", options: .backwards) {
                apps.append(URL(fileURLWithPath: String(path[..<range.lowerBound]) + ".app"))
            }
        }
        var info = kinfo_proc()
        var size = MemoryLayout<kinfo_proc>.size
        var mib: [Int32] = [CTL_KERN, KERN_PROC, KERN_PROC_PID, pid]
        guard sysctl(&mib, 4, &info, &size, nil, 0) == 0, size > 0 else { break }
        pid = info.kp_eproc.e_ppid
    }
    return apps
}

func hasIcon(_ app: URL) -> Bool {
    let info = Bundle(url: app)?.infoDictionary
    return info?["CFBundleIconFile"] != nil || info?["CFBundleIconName"] != nil
}

/// Starts the guide as its own process: the MCP server has no windows, and its output is the MCP stream.
func showPermissionGuide(_ permission: Permission) {
    let guide = Process()
    guide.executableURL = URL(fileURLWithPath: Bundle.main.executablePath ?? CommandLine.arguments[0])
    // In mac-cu.app the permission is the daemon's own. The bare program's belongs to the nearest parent app
    // (claude.app of the Claude app has no icon: the panel then shows the icon of the nearest app with one).
    let apps = Bundle.main.bundleIdentifier == daemonBundleID ? [Bundle.main.bundleURL] : parentApps()
    let shown = apps.first(where: hasIcon) ?? apps.first
    guide.arguments = [permission.rawValue] + [apps.first, shown].compactMap { $0?.path }
    guide.standardInput = FileHandle.nullDevice
    guide.standardOutput = FileHandle.nullDevice
    guide.standardError = FileHandle.nullDevice
    try? guide.run()
}

/// The app icon. A drag gives the app's file to the place where it is dropped.
final class AppIconView: NSImageView, NSDraggingSource {
    var app: URL!

    override func acceptsFirstMouse(for event: NSEvent?) -> Bool { true }
    override var mouseDownCanMoveWindow: Bool { false }
    override func resetCursorRects() { addCursorRect(bounds, cursor: .openHand) }
    override func mouseDown(with event: NSEvent) {}
    override func mouseDragged(with event: NSEvent) {
        let item = NSDraggingItem(pasteboardWriter: app as NSURL)
        item.setDraggingFrame(bounds, contents: image)
        beginDraggingSession(with: [item], event: event, source: self)
    }

    func draggingSession(_ session: NSDraggingSession, sourceOperationMaskFor context: NSDraggingContext) -> NSDragOperation {
        .copy
    }
}

final class AccessibilityGuide: NSObject {
    static let size = NSSize(width: 400, height: 96)
    let panel: NSPanel
    let icon = AppIconView()
    let title = NSTextField(labelWithString: "")
    let detail = NSTextField(wrappingLabelWithString: "")
    let ghost = CALayer()
    let started = Date()
    let permission: Permission
    var timer: Timer?

    init(_ permission: Permission, app: URL, iconApp: URL) {
        self.permission = permission
        panel = NSPanel(contentRect: NSRect(origin: .zero, size: AccessibilityGuide.size),
                        styleMask: [.borderless, .nonactivatingPanel], backing: .buffered, defer: false)
        panel.isOpaque = false
        panel.backgroundColor = .clear
        panel.hasShadow = true
        panel.level = .floating
        panel.hidesOnDeactivate = false
        panel.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary, .ignoresCycle]
        super.init()

        let background = NSVisualEffectView(frame: NSRect(origin: .zero, size: AccessibilityGuide.size))
        background.material = .hudWindow
        background.blendingMode = .behindWindow
        background.state = .active
        background.wantsLayer = true
        background.layer?.cornerRadius = 12
        background.layer?.masksToBounds = true
        panel.contentView = background

        let name = FileManager.default.displayName(atPath: app.path)
        let image = NSWorkspace.shared.icon(forFile: iconApp.path)
        icon.frame = NSRect(x: 20, y: 18, width: 60, height: 60)
        icon.image = image
        icon.app = app
        icon.setAccessibilityLabel(name)
        icon.toolTip = app.path

        // A copy of the icon that moves up into the list, again and again: the drag to do.
        let ghostView = NSView(frame: NSRect(origin: .zero, size: AccessibilityGuide.size))
        ghostView.wantsLayer = true
        ghost.frame = icon.frame
        ghost.contents = image
        ghost.contentsGravity = .resizeAspect
        ghost.contentsScale = NSScreen.main?.backingScaleFactor ?? 2
        ghost.opacity = 0
        let rise = CABasicAnimation(keyPath: "position.y")
        rise.byValue = 70
        let fade = CAKeyframeAnimation(keyPath: "opacity")
        fade.values = [0, 0.8, 0.8, 0]
        fade.keyTimes = [0, 0.15, 0.6, 1]
        let move = CAAnimationGroup()
        move.animations = [rise, fade]
        move.duration = 1.4
        move.timingFunction = CAMediaTimingFunction(name: .easeInEaseOut)
        let loop = CAAnimationGroup()
        loop.animations = [move]
        loop.duration = 2.2
        loop.repeatCount = .infinity
        ghost.add(loop, forKey: "drag")

        title.frame = NSRect(x: 96, y: 52, width: 268, height: 22)
        title.font = .boldSystemFont(ofSize: 14)
        title.stringValue = "Drag “\(name)” into the list above"
        title.lineBreakMode = .byTruncatingMiddle
        detail.frame = NSRect(x: 96, y: 12, width: 284, height: 38)
        detail.font = .systemFont(ofSize: 12)
        detail.textColor = .secondaryLabelColor
        detail.isSelectable = false
        detail.stringValue = permission == .accessibility
            ? "mac-cu needs the Accessibility permission for this app. If it is in the list already, turn it on."
            : "mac-cu needs Screen Recording for this app, for screenshots. If it is in the list already, turn it on."

        let close = FirstMouseButton(title: "✕", target: self, action: #selector(finish))
        close.isBordered = false
        close.frame = NSRect(x: AccessibilityGuide.size.width - 30, y: AccessibilityGuide.size.height - 30, width: 22, height: 22)
        close.setAccessibilityLabel("Close")

        ghostView.layer?.addSublayer(ghost)
        for view in [icon, title, detail, ghostView, close] { background.addSubview(view) }

        NSWorkspace.shared.open(permission.settings)
        place()
        panel.orderFrontRegardless()
        timer = Timer.scheduledTimer(withTimeInterval: 0.25, repeats: true) { [weak self] _ in self?.tick() }
    }

    /// Below the System Settings window, or at the bottom of the screen without that window.
    func place() {
        let size = AccessibilityGuide.size
        guard let screen = NSScreen.screens.first else { return }
        var origin = NSPoint(x: screen.visibleFrame.midX - size.width / 2, y: screen.visibleFrame.minY + 40)
        if let settings = settingsWindow() {
            let top = screen.frame.height - settings.minY  // Window list bounds have the origin at the top left.
            let bottom = top - settings.height
            origin = NSPoint(x: settings.midX - size.width / 2, y: bottom - size.height - 8)
            if let visible = NSScreen.screens.first(where: { $0.frame.contains(NSPoint(x: settings.midX, y: top - 1)) })?.visibleFrame,
               origin.y < visible.minY {
                origin.y = bottom + 16  // No room below: over the bottom of the window.
            }
        }
        if panel.frame.origin != origin { panel.setFrameOrigin(origin) }
    }

    func settingsWindow() -> CGRect? {
        guard let pid = NSRunningApplication.runningApplications(withBundleIdentifier: "com.apple.systempreferences").first?.processIdentifier,
              let windows = CGWindowListCopyWindowInfo([.optionOnScreenOnly, .excludeDesktopElements], kCGNullWindowID) as? [[String: Any]]
        else { return nil }
        for window in windows where window[kCGWindowOwnerPID as String] as? pid_t == pid && window[kCGWindowLayer as String] as? Int == 0 {
            if let bounds = window[kCGWindowBounds as String] as? NSDictionary,
               let rect = CGRect(dictionaryRepresentation: bounds), rect.height > 100 {
                return rect
            }
        }
        return nil
    }

    var checks = 0

    func tick() {
        checks += 1
        // Screen Recording asks a new process: once a second is enough.
        if (permission == .accessibility || checks % 4 == 0) && permission.isGranted {
            timer?.invalidate()
            ghost.removeAllAnimations()
            title.stringValue = "Allowed"
            detail.stringValue = permission == .accessibility
                ? "mac-cu can use apps now. Try the request again."
                : "If macOS asks to quit and reopen the app, do it. Then try the request again."
            DispatchQueue.main.asyncAfter(deadline: .now() + 2.5) { exit(0) }
            return
        }
        if Date().timeIntervalSince(started) > 600 { finish() }
        place()
    }

    @objc func finish() { exit(0) }
}

/// A button that works on the first click, while another app is active.
final class FirstMouseButton: NSButton {
    override func acceptsFirstMouse(for event: NSEvent?) -> Bool { true }
}

/// Opens the settings page and, when the app is known, shows the guide until the permission is on.
func runPermissionGuide(_ permission: Permission, app: URL?, iconApp: URL?) -> Never {
    guard let app else {
        NSWorkspace.shared.open(permission.settings)
        exit(0)
    }
    NSApplication.shared.setActivationPolicy(.accessory)
    let guide = AccessibilityGuide(permission, app: app, iconApp: iconApp ?? app)
    withExtendedLifetime(guide) { NSApplication.shared.run() }
    exit(0)
}
