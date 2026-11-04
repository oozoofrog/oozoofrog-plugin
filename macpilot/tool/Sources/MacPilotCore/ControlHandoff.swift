import AppKit
import ApplicationServices

struct ControlHandoffRequest: Codable {
    var id: String
    var taskID: String
    var ownerPID: Int32
    var ownerStartID: String
    var updatedAt: Date
    var deadline: Date
    var goal: String
}

struct ControlHandoffStatus: Codable {
    var id: String
    var taskID: String
    var phase: String
    var hostPID: Int32
    var hostStartID: String
    var updatedAt: Date
    var reason: String?
    func isFresh(now: Date = Date(), hostIdentity: String?) -> Bool {
        !hostStartID.isEmpty && hostIdentity == hostStartID && (-1..<1).contains(now.timeIntervalSince(updatedAt))
    }
}

enum ControlHandoff {
    static func status(store: Store) -> ControlHandoffStatus? {
        (try? store.read("control-handoff-status.json")).flatMap { try? JSONDecoder().decode(ControlHandoffStatus.self, from: $0) }
    }
    static func requireGrant(taskID: String, store: Store, expectedEpoch: String? = nil) throws {
        let task = try Tasks.load(taskID, in: store)
        try Tasks.requireActive(task)
        guard !task.preserveForeground, let epoch = task.controlRequestID,
              expectedEpoch == nil || expectedEpoch == epoch,
              let status = status(store: store), status.id == epoch, status.taskID == task.id,
              status.phase == "granted", status.isFresh(hostIdentity: ProcessIdentity.startID(pid: status.hostPID)) else {
            try? Tasks.interrupt(taskID, reason: "control_handoff_lost", store: store, controlRequestID: expectedEpoch ?? task.controlRequestID)
            throw ToolFailure("control_handoff_required", "Foreground control needs a fresh user handoff; explicitly resume the task and choose Start control")
        }
    }
    @MainActor static func request(taskID: String, store: Store) async throws {
        let admission = try store.lease(".control-handoff-request.lock")
        defer { withExtendedLifetime(admission) {} }
        if let current = status(store: store), current.phase == "granted",
           current.isFresh(hostIdentity: ProcessIdentity.startID(pid: current.hostPID)),
           let owner = try? Tasks.load(current.taskID, in: store), owner.status == "active", owner.deadline > Date() {
            throw ToolFailure("foreground_control_busy", "Another task owns foreground control")
        }
        let request: ControlHandoffRequest = try {
            let lease = try store.lease(".tasks.lock"); defer { withExtendedLifetime(lease) {} }
            var task = try Tasks.load(taskID, in: store)
            try Tasks.requireActive(task)
            let id = UUID().uuidString.lowercased()
            guard let identity = ProcessIdentity.startID(pid: getpid()) else { throw ToolFailure("control_handoff_failed", "Cannot identify the requesting process") }
            let request = ControlHandoffRequest(id: id, taskID: task.id, ownerPID: getpid(), ownerStartID: identity,
                updatedAt: Date(), deadline: min(task.deadline, Date().addingTimeInterval(120)), goal: task.goal)
            // Publish before the task adopts this epoch. If the write fails,
            // admission cleanup still owns the task's prior epoch. The host
            // ignores this file until the matching awaiting task is saved.
            try store.write(JSONEncoder().encode(request), to: store.root.appendingPathComponent("control-handoff-request.json"))
            task.controlRequestID = id; task.status = "awaiting_control"; try Tasks.save(task, in: store)
            return request
        }()
        do {
            try DesktopSession.current().requireAvailable()
            guard CGPreflightListenEventAccess() else { throw ToolFailure("input_monitor_denied", "Foreground handoff requires Input Monitoring") }
            let host = status(store: store)
            if host == nil || !host!.isFresh(hostIdentity: ProcessIdentity.startID(pid: host!.hostPID)) {
                guard let executable = Bundle.main.executableURL else { throw ToolFailure("control_handoff_failed", "Cannot locate MacPilot") }
                let process = Process(); process.executableURL = executable; process.arguments = ["input-activity-host", store.root.path]
                process.standardInput = FileHandle.nullDevice; process.standardOutput = FileHandle.nullDevice; process.standardError = FileHandle.nullDevice
                try process.run()
            }
            var heartbeat = request
            while Date() < request.deadline {
                try Task.checkCancellation()
                if let value = status(store: store), value.id == request.id,
                   value.isFresh(hostIdentity: ProcessIdentity.startID(pid: value.hostPID)) {
                    if value.phase == "granted" { try requireGrant(taskID: taskID, store: store, expectedEpoch: request.id); return }
                    if ["declined", "revoked"].contains(value.phase) {
                        throw ToolFailure(value.reason ?? "control_handoff_declined", "Foreground control was not granted")
                    }
                }
                let task = try Tasks.load(taskID, in: store)
                guard ["awaiting_control", "active"].contains(task.status), task.controlRequestID == request.id else {
                    throw ToolFailure("control_handoff_cancelled", "Foreground handoff ended before control started")
                }
                heartbeat.updatedAt = Date()
                try store.write(JSONEncoder().encode(heartbeat), to: store.root.appendingPathComponent("control-handoff-request.json"))
                try await Task.sleep(nanoseconds: 80_000_000)
            }
            throw ToolFailure("control_handoff_timeout", "Foreground handoff expired without user acceptance")
        } catch {
            let code = (error as? ToolFailure)?.code ?? "control_handoff_cancelled"
            try? Tasks.queueControlFailure(taskID, epoch: request.id, reason: code, store: store)
            try? Tasks.interrupt(taskID, reason: code, store: store, controlRequestID: request.id)
            throw error
        }
    }
}

final class ControlHandoffPanel: NSPanel {
    var decline: (() -> Void)?
    override var canBecomeKey: Bool { true }
    override var canBecomeMain: Bool { true }
    override func cancelOperation(_ sender: Any?) { decline?() }
    override func performKeyEquivalent(with event: NSEvent) -> Bool {
        if event.keyCode == 53 { decline?(); return true }
        if event.keyCode == 36 || event.keyCode == 76 { return true }
        return super.performKeyEquivalent(with: event)
    }
    override func keyDown(with event: NSEvent) {
        if event.keyCode == 53 { decline?(); return }
        // Return must never accept a stray key from the user's previous work.
        if event.keyCode == 36 || event.keyCode == 76 { return }
        super.keyDown(with: event)
    }
}

@MainActor final class ControlHandoffOverlay: NSObject {
    private(set) var panels: [ControlHandoffPanel] = []
    var decide: ((Bool) -> Void)?
    func show(goal: String, permissionOnly: Bool = false) {
        hide()
        for screen in NSScreen.screens {
            let panel = ControlHandoffPanel(contentRect: screen.frame, styleMask: [.borderless], backing: .buffered, defer: false)
            panel.title = "MacPilot Control Handoff"; panel.isOpaque = false
            panel.backgroundColor = NSColor.black.withAlphaComponent(0.86); panel.level = .screenSaver
            panel.isReleasedWhenClosed = false; panel.collectionBehavior = [.canJoinAllSpaces, .canJoinAllApplications, .fullScreenAuxiliary]
            panel.decline = { [weak self] in self?.decide?(false) }
            let content = NSView(frame: NSRect(origin: .zero, size: screen.frame.size))
            let heading = NSTextField(wrappingLabelWithString: permissionOnly ? "MacPilot 권한 설정을 열까요?" : "MacPilot에 키보드와 마우스 제어를 넘길까요?")
            heading.font = .systemFont(ofSize: 26, weight: .semibold); heading.textColor = .white
            let goalLabel = NSTextField(wrappingLabelWithString: goal.isEmpty ? "요청한 작업을 시작합니다." : goal)
            goalLabel.font = .systemFont(ofSize: 16); goalLabel.textColor = .white
            goalLabel.maximumNumberOfLines = 4; goalLabel.lineBreakMode = .byTruncatingTail; goalLabel.toolTip = goal
            let hint = NSTextField(wrappingLabelWithString: permissionOnly ? "시스템 설정과 안내를 엽니다. 권한은 시스템 설정에서 직접 승인하세요." : "제어 시작을 선택해야 작업이 시작됩니다. 직접 입력하면 MacPilot이 멈춥니다.")
            hint.font = .systemFont(ofSize: 14); hint.textColor = .white
            let later = NSButton(title: "나중에", target: self, action: #selector(declineControl))
            let start = NSButton(title: permissionOnly ? "설정 열기" : "제어 시작", target: self, action: #selector(startControl))
            later.bezelStyle = .rounded; start.bezelStyle = .rounded
            later.keyEquivalent = ""; start.keyEquivalent = ""
            later.setAccessibilityIdentifier("macpilot-control-later"); start.setAccessibilityIdentifier("macpilot-control-start")
            let buttons = NSStackView(views: [later, start]); buttons.orientation = .horizontal; buttons.spacing = 16
            let stack = NSStackView(views: [heading, goalLabel, hint, buttons]); stack.orientation = .vertical
            stack.alignment = .leading; stack.spacing = 20; stack.translatesAutoresizingMaskIntoConstraints = false
            content.addSubview(stack); panel.contentView = content
            NSLayoutConstraint.activate([stack.centerXAnchor.constraint(equalTo: content.centerXAnchor),
                stack.centerYAnchor.constraint(equalTo: content.centerYAnchor),
                stack.widthAnchor.constraint(equalToConstant: min(620, max(100, screen.frame.width - 64)))])
            panel.defaultButtonCell = nil; panel.initialFirstResponder = later
            panels.append(panel); panel.orderFrontRegardless()
        }
        NSApplication.shared.activate(ignoringOtherApps: true)
        panels.first?.makeKeyAndOrderFront(nil)
    }
    @objc private func startControl() { decide?(true) }
    @objc private func declineControl() { decide?(false) }
    func hide() { panels.forEach { $0.orderOut(nil); $0.close() }; panels.removeAll() }
    var ownsFocus: Bool { NSWorkspace.shared.frontmostApplication?.processIdentifier == getpid() && panels.contains { $0.isKeyWindow } }
    static var inputReleased: Bool {
        NSEvent.pressedMouseButtons == 0 && NSEvent.modifierFlags.intersection([.shift,.control,.option,.command,.function]).isEmpty
            && !(0...127).contains(where: { CGEventSource.keyState(.combinedSessionState, key: CGKeyCode($0)) })
    }
}

/// The shared AppKit host owns both consent UI and continuous idle monitoring.
@MainActor final class ControlHandoffHost {
    private let store: Store
    private let overlay = ControlHandoffOverlay()
    private var request: ControlHandoffRequest?
    private(set) var phase = "hidden"
    private var reason: String?
    private var monitor: UserInputMonitor?
    private var restoring = false
    private var previousPID: Int32?, previousStartID: String?
    private var foregroundPID: Int32?, foregroundStartID: String?
    init(store: Store) { self.store = store; overlay.decide = { [weak self] in self?.decide($0) } }
    var activeTaskID: String? { phase == "granted" ? request?.taskID : nil }
    var activeEpoch: String? { phase == "granted" ? request?.id : nil }
    var pending: Bool { phase == "pending" }
    private var focusDeadline = Date.distantPast
    private var attainedFocus = false
    private func persist() {
        guard let request else { return }
        let value = ControlHandoffStatus(id: request.id, taskID: request.taskID, phase: phase, hostPID: getpid(),
            hostStartID: ProcessIdentity.startID(pid: getpid()) ?? "", updatedAt: Date(), reason: reason)
        if let data = try? JSONEncoder().encode(value) { try? store.write(data, to: store.root.appendingPathComponent("control-handoff-status.json")) }
    }
    private func activity() -> InputActivityRecord? {
        guard let data = try? store.read("input-activity.json"), let value = try? JSONDecoder().decode(InputActivityRecord.self, from: data),
              value.taskID == request?.taskID, value.controlRequestID == request?.id, value.isLive(ownerStartID: ProcessIdentity.startID(pid: value.ownerPID)) else { return nil }
        return value
    }
    private func owns(_ event: CGEvent) -> Bool {
        guard let record = activity(), let tag = record.eventTag else { return false }
        // Cross-process attribution only; this is not an input security boundary.
        return event.getIntegerValueField(.eventSourceUnixProcessID) == Int64(record.ownerPID)
            && event.getIntegerValueField(.eventSourceUserData) == tag
    }
    private func revoke(_ code: String, declined: Bool = false) {
        guard let request else { return }
        let returnFocus = phase == "pending" && NSWorkspace.shared.frontmostApplication?.processIdentifier == getpid()
        monitor = nil; restoring = false; overlay.hide(); phase = declined ? "declined" : "revoked"; reason = code
        if returnFocus { restorePrevious() }
        try? Tasks.queueControlFailure(request.taskID, epoch: request.id, reason: code, store: store)
        try? Tasks.interrupt(request.taskID, reason: code, store: store, controlRequestID: request.id); persist()
    }
    private func decide(_ accepted: Bool) {
        guard phase == "pending", overlay.ownsFocus else { return }
        guard accepted else { revoke("control_handoff_declined", declined: true); return }
        // A native button action runs on mouseUp. Do not arm over held keys,
        // modifiers or buttons, and do not use a time window that ignores input.
        guard ControlHandoffOverlay.inputReleased else { return }
        do { monitor = try UserInputMonitor(ownsEvent: { [weak self] in self?.owns($0) ?? false }) }
        catch { revoke((error as? ToolFailure)?.code ?? "input_monitor_lost"); return }
        overlay.hide(); restoring = true; restorePrevious()
    }
    private func restorePrevious() {
        guard let pid = previousPID, let identity = previousStartID, ProcessIdentity.startID(pid: pid) == identity else { return }
        NSRunningApplication(processIdentifier: pid)?.activate(options: [])
    }
    func tick() {
        let incoming = (try? store.read("control-handoff-request.json")).flatMap { try? JSONDecoder().decode(ControlHandoffRequest.self, from: $0) }
        if let incoming, incoming.id != request?.id,
           let task = try? Tasks.load(incoming.taskID, in: store), task.status == "awaiting_control", task.controlRequestID == incoming.id {
            // A new requester can arrive after the previous requester dies.
            // Preserve the pre-overlay app because restoration is asynchronous.
            let replacingPending = phase == "pending" && NSWorkspace.shared.frontmostApplication?.processIdentifier == getpid()
            let inheritedPID = replacingPending ? previousPID : nil
            let inheritedIdentity = replacingPending ? previousStartID : nil
            if phase == "granted" || phase == "pending" { revoke("control_replaced") }
            request = incoming; reason = nil; phase = "pending"; monitor = nil; restoring = false
            previousPID = inheritedPID ?? NSWorkspace.shared.frontmostApplication?.processIdentifier
            previousStartID = inheritedIdentity ?? previousPID.flatMap { ProcessIdentity.startID(pid: $0) }
            attainedFocus = false; focusDeadline = Date().addingTimeInterval(2)
            overlay.show(goal: incoming.goal)
        }
        guard let request else { return }
        if phase == "revoked" || phase == "declined" {
            // Revocation is immediately fail-closed in host status. If another
            // caller held the task lock, retry its durable state transition.
            try? Tasks.interrupt(request.taskID, reason: reason ?? "control_handoff_lost", store: store, controlRequestID: request.id)
            persist(); return
        }
        guard let task = try? Tasks.load(request.taskID, in: store), task.controlRequestID == request.id,
              task.deadline > Date(), ["active", "awaiting_control"].contains(task.status) else {
            if phase == "pending" || phase == "granted" { revoke("control_task_ended") }
            persist(); return
        }
        if phase == "pending" {
            guard let incoming, incoming.id == request.id, incoming.deadline > Date(),
                  incoming.ownerStartID == ProcessIdentity.startID(pid: incoming.ownerPID),
                  (-1..<1.5).contains(Date().timeIntervalSince(incoming.updatedAt)) else { revoke("control_handoff_timeout"); return }
            if restoring {
                do { try monitor?.verify() }
                catch { revoke((error as? ToolFailure)?.code ?? "input_monitor_lost"); return }
                guard let pid = previousPID, let identity = previousStartID, ProcessIdentity.startID(pid: pid) == identity else { revoke("foreground_changed"); return }
                if NSWorkspace.shared.frontmostApplication?.processIdentifier == pid {
                    do {
                        let lease = try store.lease(".tasks.lock"); defer { withExtendedLifetime(lease) {} }
                        var current = try Tasks.load(task.id, in: store)
                        guard current.status == "awaiting_control", current.controlRequestID == request.id else { revoke("control_task_ended"); return }
                        current.status = "active"; try Tasks.save(current, in: store)
                        foregroundPID = pid; foregroundStartID = identity; restoring = false; phase = "granted"
                    } catch { revoke((error as? ToolFailure)?.code ?? "control_handoff_failed") }
                }
            } else if overlay.ownsFocus { attainedFocus = true }
            else if attainedFocus || Date() > focusDeadline { revoke("control_handoff_focus_lost") }
        } else if phase == "granted" {
            do { try monitor?.verify(); if monitor == nil { throw ToolFailure("input_monitor_lost", "Control monitor is unavailable") } }
            catch { revoke((error as? ToolFailure)?.code ?? "input_monitor_lost"); return }
            let current = NSWorkspace.shared.frontmostApplication?.processIdentifier
            let identity = current.flatMap { ProcessIdentity.startID(pid: $0) }
            if current != foregroundPID || identity != foregroundStartID {
                if activity()?.permitsAppSwitch == true { foregroundPID = current; foregroundStartID = identity }
                else { revoke("foreground_changed"); return }
            }
        }
        persist()
    }
}
