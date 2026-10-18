import AppKit

public struct InputActivityRecord: Codable {
    public var id: String
    public var ownerPID: Int32
    public var ownerStartID: String
    public var active: Bool
    public var updatedAt: Date
    public var kind: String
    public func isLive(now: Date = Date(), ownerStartID current: String?) -> Bool {
        active && current == ownerStartID && now.timeIntervalSince(updatedAt) >= -1 && now.timeIntervalSince(updatedAt) < 1.5
    }
}

/// One scope is protected by the existing shared system-input lease.
@MainActor public final class InputActivityScope {
    private let store: Store
    private var record: InputActivityRecord
    private var heartbeat: Task<Void, Never>?
    private var finished = false
    private init(store: Store, kind: String) throws {
        self.store = store
        record = InputActivityRecord(id: UUID().uuidString.lowercased(), ownerPID: getpid(),
            ownerStartID: ProcessIdentity.startID(pid: getpid()) ?? "", active: true, updatedAt: Date(), kind: kind)
        guard !record.ownerStartID.isEmpty else { throw ToolFailure("activity_indicator_failed", "Cannot identify the input owner") }
        try publish()
    }
    private func publish() throws { try store.write(try JSONEncoder().encode(record), to: store.root.appendingPathComponent("input-activity.json")) }
    public static func begin(store: Store, kind: String) async throws -> InputActivityScope {
        let scope = try InputActivityScope(store: store, kind: kind)
        do {
            let status = scope.status()
            let running = (status["pid"] as? Int32).flatMap { pid in
                (status["processStartID"] as? String).map { ProcessIdentity.startID(pid: pid) == $0 }
            } ?? false
            if !running || status["running"] as? Bool != true {
                guard let executable = Bundle.main.executableURL else { throw ToolFailure("activity_indicator_failed", "Cannot locate MacPilot") }
                let process = Process(); process.executableURL = executable
                process.arguments = ["input-activity-host", store.root.path]
                process.standardInput = FileHandle.nullDevice; process.standardOutput = FileHandle.nullDevice; process.standardError = FileHandle.nullDevice
                try process.run()
            }
            let deadline = Date().addingTimeInterval(5)
            while Date() < deadline {
                try Task.checkCancellation()
                // Cold AppKit launch may exceed the stale-owner threshold under
                // build/system load. Keep the waiting owner live until ack.
                scope.record.updatedAt = Date(); try scope.publish()
                let status = scope.status()
                if status["activityID"] as? String == scope.record.id, status["visible"] as? Bool == true {
                    scope.heartbeat = Task { @MainActor [weak scope] in
                        while !Task.isCancelled {
                            do {
                                try await Task.sleep(nanoseconds: 200_000_000)
                                guard let scope, !scope.finished else { return }
                                scope.record.updatedAt = Date(); try scope.publish()
                            } catch { return }
                        }
                    }
                    return scope
                }
                try await Task.sleep(nanoseconds: 30_000_000)
            }
            throw ToolFailure("activity_indicator_failed", "System input notice did not become visible; input was not sent")
        } catch { scope.finish(); throw error }
    }
    private func status() -> [String: Any] {
        guard let data = try? store.read("input-activity-status.json"), let value = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else { return [:] }
        return value
    }
    public func verify() throws {
        let value = status()
        guard !finished, value["activityID"] as? String == record.id, value["visible"] as? Bool == true,
              let updated = value["updatedAt"] as? Double, Date().timeIntervalSince1970 - updated < 1,
              let pid = value["pid"] as? Int32, let identity = value["processStartID"] as? String,
              ProcessIdentity.startID(pid: pid) == identity else {
            throw ToolFailure("activity_indicator_failed", "The system input notice stopped; further input was blocked")
        }
    }
    public func finish() {
        guard !finished else { return }; finished = true; heartbeat?.cancel()
        record.active = false; record.updatedAt = Date(); try? publish()
    }
}

public final class InputActivityPanel: NSPanel {
    public override var canBecomeKey: Bool { false }
    public override var canBecomeMain: Bool { false }
}

public final class InputActivityNoticeView: NSView {
    public var kind = "키보드"
    public override func draw(_ dirtyRect: NSRect) {
        let pill = NSBezierPath(roundedRect: bounds.insetBy(dx: 1, dy: 1), xRadius: 14, yRadius: 14)
        NSColor(calibratedWhite: 0.07, alpha: 0.94).setFill(); pill.fill()
        NSColor.systemTeal.withAlphaComponent(0.8).setStroke(); pill.lineWidth = 1; pill.stroke()
        NSColor.systemTeal.setFill(); NSBezierPath(ovalIn: NSRect(x: 13, y: 13, width: 7, height: 7)).fill()
        ("MacPilot 조작 중 · \(kind)" as NSString).draw(at: NSPoint(x: 28, y: 9), withAttributes: [
            .font: NSFont.systemFont(ofSize: 12, weight: .semibold), .foregroundColor: NSColor.white])
    }
}

/// Visible across Spaces and full-screen apps, with only narrow edge surfaces.
/// The notice and edges never take focus or accept mouse input.
@MainActor public final class InputActivityPresentation {
    public private(set) var panels: [InputActivityPanel] = []
    public init() {}
    nonisolated public static func edgeFrames(_ frame: NSRect) -> [NSRect] {
        let width: CGFloat = 3
        return [NSRect(x: frame.minX, y: frame.minY, width: width, height: frame.height),
                NSRect(x: frame.maxX - width, y: frame.minY, width: width, height: frame.height),
                NSRect(x: frame.minX, y: frame.minY, width: frame.width, height: width),
                NSRect(x: frame.minX, y: frame.maxY - width, width: frame.width, height: width)]
    }
    static func panel(_ frame: NSRect) -> InputActivityPanel {
        let panel = InputActivityPanel(contentRect: frame, styleMask: [.borderless, .nonactivatingPanel], backing: .buffered, defer: false)
        panel.title = "MacPilot Input Activity"; panel.isOpaque = false; panel.backgroundColor = .clear
        panel.isReleasedWhenClosed = false; panel.hasShadow = false; panel.ignoresMouseEvents = true; panel.level = .statusBar
        panel.collectionBehavior = [.canJoinAllSpaces, .canJoinAllApplications, .fullScreenAuxiliary, .ignoresCycle]
        return panel
    }
    public func show(kind: String) {
        hide()
        for screen in NSScreen.screens {
            for frame in Self.edgeFrames(screen.frame) {
                let edge = Self.panel(frame); edge.backgroundColor = NSColor.systemTeal.withAlphaComponent(0.72)
                panels.append(edge)
            }
        }
        if let screen = NSScreen.main ?? NSScreen.screens.first {
            let frame = NSRect(x: screen.visibleFrame.midX - 132, y: screen.visibleFrame.maxY - 48, width: 264, height: 34)
            let notice = Self.panel(frame), view = InputActivityNoticeView(frame: NSRect(origin: .zero, size: frame.size))
            view.kind = kind; view.setAccessibilityElement(true); view.setAccessibilityRole(.staticText)
            view.setAccessibilityLabel("MacPilot 조작 중. \(kind) 사용 중")
            notice.contentView = view; panels.append(notice)
        }
        panels.forEach { $0.orderFrontRegardless() }
    }
    public func animate(at time: Double, reducedMotion: Bool) {
        let alpha = reducedMotion ? 1 : 0.86 + 0.14 * sin(time * 2)
        for panel in panels.dropLast() { panel.alphaValue = alpha }
    }
    public var isOnScreen: Bool {
        guard !panels.isEmpty, panels.allSatisfy({ $0.isVisible && $0.isOnActiveSpace }) else { return false }
        let rows = CGWindowListCopyWindowInfo([.optionOnScreenOnly, .excludeDesktopElements], kCGNullWindowID) as? [[String: Any]] ?? []
        let ids = Set(rows.compactMap { ($0[kCGWindowNumber as String] as? NSNumber)?.intValue })
        return panels.allSatisfy { ids.contains($0.windowNumber) }
    }
    public func hide() { panels.forEach { $0.orderOut(nil); $0.close() }; panels.removeAll() }
}

@MainActor public final class InputActivityHost: NSObject, NSApplicationDelegate {
    private let store: Store, owner: StateLease
    private let presentation = InputActivityPresentation()
    private var timer: Timer?, activityID = "", lastActivity = Date(), visible = false
    private init(store: Store) throws {
        self.store = store; owner = try store.lease(".input-activity-host.lock"); super.init()
    }
    public func applicationWillFinishLaunching(_ notification: Notification) { NSApplication.shared.setActivationPolicy(.prohibited) }
    public func applicationDidFinishLaunching(_ notification: Notification) {
        NSApplication.shared.setActivationPolicy(.accessory)
        timer = Timer.scheduledTimer(withTimeInterval: 0.04, repeats: true) { [weak self] _ in Task { @MainActor in self?.tick() } }
        tick()
    }
    private func persist(running: Bool) {
        let status: [String: Any] = ["pid": getpid(), "processStartID": ProcessIdentity.startID(pid: getpid()) ?? "", "running": running,
            "activityID": activityID, "visible": visible, "panelCount": presentation.panels.count, "updatedAt": Date().timeIntervalSince1970,
            "inputTransparent": true, "takesFocus": false, "presentation": "screen_edges_and_notice"]
        if let data = try? jsonData(status) { try? store.write(data, to: store.root.appendingPathComponent("input-activity-status.json")) }
    }
    private func tick() {
        let record = (try? store.read("input-activity.json")).flatMap { try? JSONDecoder().decode(InputActivityRecord.self, from: $0) }
        let live = record.map { $0.isLive(ownerStartID: ProcessIdentity.startID(pid: $0.ownerPID)) } ?? false
        if live, let record {
            if presentation.panels.isEmpty || record.id != activityID { presentation.show(kind: record.kind) }
            visible = presentation.isOnScreen; activityID = record.id; lastActivity = Date()
            presentation.animate(at: ProcessInfo.processInfo.systemUptime, reducedMotion: NSWorkspace.shared.accessibilityDisplayShouldReduceMotion)
        } else if !presentation.panels.isEmpty { presentation.hide(); visible = false }
        persist(running: true)
        if !visible, Date().timeIntervalSince(lastActivity) > 120 {
            timer?.invalidate(); persist(running: false); NSApplication.shared.terminate(nil)
        }
    }
    public static func run(store: Store) throws {
        let host = try InputActivityHost(store: store)
        NSApplication.shared.delegate = host
        withExtendedLifetime(host) { NSApplication.shared.run() }
    }
}
