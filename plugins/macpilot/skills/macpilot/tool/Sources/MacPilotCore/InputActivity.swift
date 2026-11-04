import AppKit

public struct InputActivityRecord: Codable {
    public var id: String
    public var ownerPID: Int32
    public var ownerStartID: String
    public var active: Bool
    public var updatedAt: Date
    public var kind: String
    public var controlRequestID: String? = nil
    public var taskID: String? = nil
    public var eventTag: Int64? = nil
    public var permitsAppSwitch: Bool? = nil
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
    private init(store: Store, kind: String, taskID: String, epoch: String, permitsAppSwitch: Bool) throws {
        self.store = store
        record = InputActivityRecord(id: UUID().uuidString.lowercased(), ownerPID: getpid(),
            ownerStartID: ProcessIdentity.startID(pid: getpid()) ?? "", active: true, updatedAt: Date(), kind: kind, controlRequestID: epoch, taskID: taskID, eventTag: InputOwnership.tag, permitsAppSwitch: permitsAppSwitch)
        guard !record.ownerStartID.isEmpty else { throw ToolFailure("activity_indicator_failed", "Cannot identify the input owner") }
        try publish()
    }
    private func publish() throws { try store.write(try JSONEncoder().encode(record), to: store.root.appendingPathComponent("input-activity.json")) }
    public static func begin(store: Store, kind: String, taskID: String, epoch: String, permitsAppSwitch: Bool = false) async throws -> InputActivityScope {
        try ControlHandoff.requireGrant(taskID: taskID, store: store, expectedEpoch: epoch)
        let scope = try InputActivityScope(store: store, kind: kind, taskID: taskID, epoch: epoch, permitsAppSwitch: permitsAppSwitch)
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
                if Self.hasActiveAcknowledgement(status, activityID: scope.record.id,
                    currentHostStartID: (status["pid"] as? Int32).flatMap { ProcessIdentity.startID(pid: $0) }) {
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
    nonisolated static func hasActiveAcknowledgement(_ value: [String: Any], activityID: String,
        now: Date = Date(), currentHostStartID: String?) -> Bool {
        guard value["activityID"] as? String == activityID, value["running"] as? Bool == true,
              value["visible"] as? Bool == true, value["controlActive"] as? Bool == true,
              value["presentationPhase"] as? String == "active",
              let updated = value["updatedAt"] as? Double,
              (-1..<1).contains(now.timeIntervalSince1970 - updated),
              let identity = value["processStartID"] as? String, !identity.isEmpty,
              currentHostStartID == identity else { return false }
        return true
    }
    public func verify() throws {
        let value = status()
        if let taskID = record.taskID { try ControlHandoff.requireGrant(taskID: taskID, store: store, expectedEpoch: record.controlRequestID) }
        guard !finished, Self.hasActiveAcknowledgement(value, activityID: record.id,
            currentHostStartID: (value["pid"] as? Int32).flatMap { ProcessIdentity.startID(pid: $0) }) else {
            throw ToolFailure("activity_indicator_failed", "The system input notice stopped; further input was blocked")
        }
    }
    public func finish() {
        guard !finished else { return }; finished = true; heartbeat?.cancel()
        record.active = false; record.updatedAt = Date(); try? publish()
    }
}

/// An ended notice reports release, never successful execution or live control.
/// Only an explicit finish can create it; a stale/crashed owner hides immediately.
struct InputActivityLifecycle {
    enum Phase: String { case hidden, active, ended }
    private(set) var phase: Phase = .hidden
    private(set) var activityID = ""
    private(set) var kind = ""
    private var endedUntil: Date?
    static let endedDuration: TimeInterval = 1.2

    mutating func update(record: InputActivityRecord?, live: Bool, now: Date) -> Bool {
        let previous = (phase, activityID, kind)
        if live, let record {
            phase = .active; activityID = record.id; kind = record.kind; endedUntil = nil
        } else if phase == .active {
            if let record, record.id == activityID, !record.active {
                phase = .ended; endedUntil = now.addingTimeInterval(Self.endedDuration)
            } else { phase = .hidden; endedUntil = nil }
        } else if phase == .ended, now >= (endedUntil ?? now) {
            phase = .hidden; endedUntil = nil
        }
        return previous != (phase, activityID, kind)
    }
}

public final class InputActivityPanel: NSPanel {
    public override var canBecomeKey: Bool { false }
    public override var canBecomeMain: Bool { false }
}

public final class InputActivityNoticeView: NSView {
    public var kind = "키보드"
    public var ended = false
    public var title: String { ended ? "MacPilot 입력 종료" : "MacPilot이 \(kind)를 사용 중" }
    public var hint: String { ended ? "직접 입력할 수 있습니다" : "직접 입력하면 MacPilot이 멈춥니다" }
    public override func draw(_ dirtyRect: NSRect) {
        let pill = NSBezierPath(roundedRect: bounds.insetBy(dx: 1, dy: 1), xRadius: 14, yRadius: 14)
        NSColor(calibratedWhite: 0.07, alpha: 0.94).setFill(); pill.fill()
        let accent = ended ? NSColor.white.withAlphaComponent(0.55) : NSColor.systemTeal
        accent.withAlphaComponent(0.8).setStroke(); pill.lineWidth = 1; pill.stroke()
        accent.setFill(); NSBezierPath(ovalIn: NSRect(x: 15, y: bounds.height - 26, width: 8, height: 8)).fill()
        let style = NSMutableParagraphStyle(); style.lineBreakMode = .byTruncatingTail
        (title as NSString).draw(in: NSRect(x: 33, y: bounds.height - 31, width: bounds.width - 46, height: 22), withAttributes: [
            .font: NSFont.systemFont(ofSize: 15, weight: .semibold), .foregroundColor: NSColor.white, .paragraphStyle: style])
        (hint as NSString).draw(in: NSRect(x: 33, y: bounds.height - 51, width: bounds.width - 46, height: 18), withAttributes: [
            .font: NSFont.systemFont(ofSize: 12), .foregroundColor: NSColor.white.withAlphaComponent(0.88), .paragraphStyle: style])
    }
}

/// Visible across Spaces and full-screen apps, with only narrow edge surfaces.
/// The notice and edges never take focus or accept mouse input.
@MainActor public final class InputActivityPresentation {
    public private(set) var panels: [InputActivityPanel] = []
    public private(set) var noticePanelCount = 0
    private var edgePanels: [InputActivityPanel] = []
    public var edgePanelCount: Int { edgePanels.count }
    public init() {}
    nonisolated public static func edgeFrames(_ frame: NSRect) -> [NSRect] {
        let width: CGFloat = 3
        return [NSRect(x: frame.minX, y: frame.minY, width: width, height: frame.height),
                NSRect(x: frame.maxX - width, y: frame.minY, width: width, height: frame.height),
                NSRect(x: frame.minX, y: frame.minY, width: frame.width, height: width),
                NSRect(x: frame.minX, y: frame.maxY - width, width: frame.width, height: width)]
    }
    nonisolated static func noticeFrame(_ visibleFrame: NSRect) -> NSRect {
        let margin = min(12, max(0, visibleFrame.width / 10), max(0, visibleFrame.height / 10))
        let size = NSSize(width: min(360, max(0, visibleFrame.width - margin * 2)),
                          height: min(64, max(0, visibleFrame.height - margin * 2)))
        return NSRect(x: visibleFrame.midX - size.width / 2, y: visibleFrame.maxY - margin - size.height,
                      width: size.width, height: size.height)
    }
    static func panel(_ frame: NSRect) -> InputActivityPanel {
        let panel = InputActivityPanel(contentRect: frame, styleMask: [.borderless, .nonactivatingPanel], backing: .buffered, defer: false)
        panel.title = "MacPilot Input Activity"; panel.isOpaque = false; panel.backgroundColor = .clear
        panel.isReleasedWhenClosed = false; panel.hasShadow = false; panel.ignoresMouseEvents = true; panel.level = .statusBar
        panel.collectionBehavior = [.canJoinAllSpaces, .canJoinAllApplications, .fullScreenAuxiliary, .ignoresCycle]
        return panel
    }
    public func show(kind: String, ended: Bool = false) {
        hide()
        for screen in NSScreen.screens {
            if !ended {
                for frame in Self.edgeFrames(screen.frame) {
                    let edge = Self.panel(frame); edge.backgroundColor = NSColor.systemTeal.withAlphaComponent(0.72)
                    panels.append(edge); edgePanels.append(edge)
                }
            }
            let frame = Self.noticeFrame(screen.visibleFrame)
            let notice = Self.panel(frame), view = InputActivityNoticeView(frame: NSRect(origin: .zero, size: frame.size))
            view.kind = kind; view.ended = ended
            view.setAccessibilityElement(true); view.setAccessibilityRole(.staticText)
            view.setAccessibilityLabel("\(view.title). \(view.hint)")
            notice.contentView = view; panels.append(notice); noticePanelCount += 1
        }
        panels.forEach { $0.orderFrontRegardless() }
    }
    public func animate(at time: Double, reducedMotion: Bool) {
        let alpha = reducedMotion ? 1 : 0.86 + 0.14 * sin(time * 2)
        for panel in edgePanels { panel.alphaValue = alpha }
    }
    public var isOnScreen: Bool {
        guard !panels.isEmpty, panels.allSatisfy({ $0.isVisible && $0.isOnActiveSpace }) else { return false }
        let rows = CGWindowListCopyWindowInfo([.optionOnScreenOnly, .excludeDesktopElements], kCGNullWindowID) as? [[String: Any]] ?? []
        let ids = Set(rows.compactMap { ($0[kCGWindowNumber as String] as? NSNumber)?.intValue })
        return panels.allSatisfy { ids.contains($0.windowNumber) }
    }
    public func hide() {
        panels.forEach { $0.orderOut(nil); $0.close() }; panels.removeAll(); edgePanels.removeAll(); noticePanelCount = 0
    }
}

@MainActor public final class InputActivityHost: NSObject, NSApplicationDelegate {
    private let store: Store, owner: StateLease
    private let presentation = InputActivityPresentation()
    private let controlHost: ControlHandoffHost
    private var lifecycle = InputActivityLifecycle()
    private var screenLayout: [NSRect] = []
    private var timer: Timer?, activityID = "", lastActivity = Date(), visible = false
    private init(store: Store) throws {
        self.store = store; owner = try store.lease(".input-activity-host.lock"); controlHost = ControlHandoffHost(store: store); super.init()
    }
    public func applicationWillFinishLaunching(_ notification: Notification) { NSApplication.shared.setActivationPolicy(.prohibited) }
    public func applicationDidFinishLaunching(_ notification: Notification) {
        NSApplication.shared.setActivationPolicy(.accessory)
        timer = Timer.scheduledTimer(withTimeInterval: 0.04, repeats: true) { [weak self] _ in Task { @MainActor in self?.tick() } }
        tick()
    }
    private func persist(running: Bool) {
        let status: [String: Any] = ["pid": getpid(), "processStartID": ProcessIdentity.startID(pid: getpid()) ?? "", "running": running,
            "activityID": activityID, "visible": visible, "controlActive": lifecycle.phase == .active,
            "presentationPhase": lifecycle.phase.rawValue, "noticeVisible": presentation.isOnScreen,
            "panelCount": presentation.panels.count, "noticePanelCount": presentation.noticePanelCount,
            "edgePanelCount": presentation.edgePanelCount, "screenCount": NSScreen.screens.count,
            "updatedAt": Date().timeIntervalSince1970,
            "inputTransparent": true, "takesFocus": false, "presentation": "all_screen_edges_and_notices"]
        if let data = try? jsonData(status) { try? store.write(data, to: store.root.appendingPathComponent("input-activity-status.json")) }
    }
    private func tick() {
        controlHost.tick()
        let worker = (try? store.read("input-activity.json")).flatMap { try? JSONDecoder().decode(InputActivityRecord.self, from: $0) }
        let workerLive = worker.map { $0.isLive(ownerStartID: ProcessIdentity.startID(pid: $0.ownerPID)) && $0.taskID == controlHost.activeTaskID && $0.controlRequestID == controlHost.activeEpoch } ?? false
        var record: InputActivityRecord?
        if let taskID = controlHost.activeTaskID, let epoch = controlHost.activeEpoch {
            record = workerLive ? worker : InputActivityRecord(id: epoch, ownerPID: getpid(),
                ownerStartID: ProcessIdentity.startID(pid: getpid()) ?? "", active: true, updatedAt: Date(), kind: "키보드·마우스", taskID: taskID)
        } else if lifecycle.phase == .active {
            record = InputActivityRecord(id: lifecycle.activityID, ownerPID: getpid(),
                ownerStartID: ProcessIdentity.startID(pid: getpid()) ?? "", active: false, updatedAt: Date(), kind: lifecycle.kind)
        }
        let live = controlHost.activeTaskID != nil
        let now = Date(), layout = NSScreen.screens.flatMap { [$0.frame, $0.visibleFrame] }
        let changed = lifecycle.update(record: record, live: live, now: now)
        if changed || screenLayout != layout {
            screenLayout = layout
            if lifecycle.phase == .hidden { presentation.hide() }
            else { presentation.show(kind: lifecycle.kind, ended: lifecycle.phase == .ended) }
        }
        activityID = lifecycle.activityID
        visible = lifecycle.phase == .active && presentation.isOnScreen
        if live {
            lastActivity = now
            presentation.animate(at: ProcessInfo.processInfo.systemUptime, reducedMotion: NSWorkspace.shared.accessibilityDisplayShouldReduceMotion)
        }
        persist(running: true)
        if !visible, !controlHost.pending, Date().timeIntervalSince(lastActivity) > 120 {
            timer?.invalidate(); persist(running: false); NSApplication.shared.terminate(nil)
        }
    }
    public static func run(store: Store) throws {
        let host = try InputActivityHost(store: store)
        NSApplication.shared.delegate = host
        withExtendedLifetime(host) { NSApplication.shared.run() }
    }
}
