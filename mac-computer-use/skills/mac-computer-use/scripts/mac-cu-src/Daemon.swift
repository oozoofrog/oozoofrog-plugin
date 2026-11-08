// The menu bar daemon (`mac-cu --daemon`, run from mac-cu.app) and the thin client (no arguments).
//
// One daemon per user does the work: the Accessibility and Screen Recording permissions belong to mac-cu.app
// itself (not to the app that runs the agent), and the approvals of a session, the devtools Chrome and the
// simulator connections stay while it runs. The menu shows the version, the sessions and what they do, the
// permissions, the modes, and checks for a plugin update.
//
// Claude Code and Codex start the client as the MCP stdio server. It connects to daemon.sock, and when the
// daemon does not run it starts it with `/usr/bin/open -a` (launchd starts the app, so the daemon is the
// responsible process of its permissions; a child process of the client would give them to the agent's app).
// Then it copies lines from stdin to the socket and back, without reading them.
//
// Socket protocol: one JSON line each way. Lines with a "mac-cu" key are control lines:
//   client → {"mac-cu":"hello","version":…,"agent":…,"env":{…}}  daemon → {"mac-cu":"hello","version":…}
//   client → {"mac-cu":"quit"}                                  the daemon removes the socket and exits
//   client → {"mac-cu":"permissions"}                           daemon → {"mac-cu":"permissions","accessibility":…,
//                                                                         "screenRecording":…,"text":…}
// Every other line is an MCP JSON-RPC message, answered on the same connection.

import AppKit

let supportFolder = savedAllowList.deletingLastPathComponent()
let daemonSocket = supportFolder.appendingPathComponent("daemon.sock")
let daemonBundle = supportFolder.appendingPathComponent("mac-cu.app")
let daemonBundleID = "com.kakao.mac-cu"

/// The Korean tool names of the Claude Code band (hooks/register.tsx TOOLS).
let toolNames = ["act": "앱 조작", "get_app_state": "창 읽기", "browser": "브라우저", "simulator": "시뮬레이터",
                 "webinspector": "웹 인스펙터", "decide": "판단"]

/// "1.14.0" is newer than "1.13.2".
func isNewer(_ a: String, than b: String) -> Bool {
    let (x, y) = (a.split(separator: ".").map { Int($0) ?? 0 }, b.split(separator: ".").map { Int($0) ?? 0 })
    return y.lexicographicallyPrecedes(x)
}

func writeLine(_ fd: Int32, _ message: [String: Any]) -> Bool {
    guard var data = try? JSONSerialization.data(withJSONObject: message, options: [.withoutEscapingSlashes]) else { return false }
    data.append(0x0a)
    return writeAll(fd, data)
}

/// Sends a line and returns the first line back (up to 10 seconds).
func exchange(_ fd: Int32, _ message: [String: Any]) -> [String: Any]? {
    var time = timeval(tv_sec: 10, tv_usec: 0)
    setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &time, socklen_t(MemoryLayout<timeval>.size))
    defer {
        time = timeval(tv_sec: 0, tv_usec: 0)
        setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &time, socklen_t(MemoryLayout<timeval>.size))
    }
    guard writeLine(fd, message) else { return nil }
    var reply: [String: Any]?
    readLines(fd) { line in
        reply = try? JSONSerialization.jsonObject(with: line) as? [String: Any]
        return false
    }
    return reply
}

// MARK: - Daemon

/// An agent session. approvedApps: the apps the user allowed for this session ("until the session ends").
final class AgentSession {
    let activityID = UUID()
    let fd: Int32
    var agent = "?"
    var version = ""
    var env: [String: String] = [:]
    var approvedApps: Set<String> = []
    var current: (tool: String, target: String, started: Date)?
    private let requestLock = NSLock()
    private var disconnected = false
    private var requestID = ""
    private var cancelledIDs: Set<String> = []
    init(fd: Int32) { self.fd = fd }
    func write(_ message: [String: Any]) { _ = writeLine(fd, message) }
    func beginRequest(_ id: Any?) {
        requestLock.lock(); defer { requestLock.unlock() }
        requestID = id.map { String(reflecting: $0) } ?? ""
    }
    func cancelRequest(_ id: Any) {
        requestLock.lock(); defer { requestLock.unlock() }
        cancelledIDs.insert(String(reflecting: id))
    }
    func endRequest() {
        requestLock.lock(); defer { requestLock.unlock() }
        cancelledIDs.remove(requestID)
        requestID = ""
    }
    func disconnect() {
        requestLock.lock(); defer { requestLock.unlock() }
        disconnected = true
    }
    var requestCancelled: Bool {
        requestLock.lock(); defer { requestLock.unlock() }
        return disconnected || cancelledIDs.contains(requestID)
    }
    var activityRequestID: String {
        requestLock.lock(); defer { requestLock.unlock() }
        return requestID
    }
}

let connectionsLock = NSLock()
var connections: [AgentSession] = []
/// The connection whose request handle() runs now: approve() and the env values read it.
var currentSession: AgentSession?
// shortcut: one serial queue, so an approval dialog of one session (up to 3 minutes) holds the other sessions;
// make the app tools alone serial when sessions overlap often.
let handleQueue = DispatchQueue(label: "mac-cu.handle")
var menuBar: MenuBar?

func quitDaemon() -> Never {
    // A paste's restore timer would not run after exit: put the user's pasteboard back now.
    if Thread.isMainThread { pasteboardRestore?.perform() } else { DispatchQueue.main.sync { pasteboardRestore?.perform() } }
    if Bundle.main.bundleIdentifier == daemonBundleID { unlink(daemonSocket.path) }
    exit(0)
}

func runDaemon() -> Never {
    guard Bundle.main.bundleIdentifier == daemonBundleID else {
        fputs("--daemon runs only from \(daemonBundle.path) (setup.py builds it).\n", stderr)
        exit(1)
    }
    signal(SIGPIPE, SIG_IGN)
    if let other = connectSocket(daemonSocket) {  // Another daemon answers already.
        close(other)
        exit(0)
    }
    try? FileManager.default.createDirectory(at: supportFolder, withIntermediateDirectories: true)
    unlink(daemonSocket.path)
    let server = socket(AF_UNIX, SOCK_STREAM, 0)
    guard withAddress(daemonSocket, { bind(server, $0, $1) }) == 0, listen(server, 16) == 0 else { exit(1) }
    chmod(daemonSocket.path, 0o600)
    let host = executablePath(of: getpid())
    Thread.detachNewThread {
        while true {
            let client = accept(server, nil, nil)
            guard client >= 0 else { continue }
            Thread.detachNewThread { serve(client, host: host) }
        }
    }
    // LCD windows promote the menu-bar daemon to a Dock application while they are open.
    NSApplication.shared.setActivationPolicy(.accessory)
    if let path = Bundle.main.path(forResource: "AppIcon", ofType: "icns") {
        NSApp.applicationIconImage = NSImage(contentsOfFile: path)
    }
    menuBar = MenuBar()
    NSApp.delegate = menuBar
    NSApplication.shared.run()
    quitDaemon()
}

/// One connection: control lines on this thread, requests one at a time on handleQueue.
func serve(_ fd: Int32, host: String?) {
    if let peer = refusal(of: fd, host: host) {
        _ = writeLine(fd, ["mac-cu": "hello", "error": "The mac-cu daemon refused \(peer): only mac-cu at " +
                           "\(host ?? daemonBundle.path) may use it. Run setup.py again."])
        close(fd)
        return
    }
    let connection = AgentSession(fd: fd)
    connectionsLock.lock()
    connections.append(connection)
    connectionsLock.unlock()
    readLines(fd) { line in
        guard let message = try? JSONSerialization.jsonObject(with: line) as? [String: Any] else { return true }
        switch message["mac-cu"] as? String {
        case "hello":
            connection.agent = message["agent"] as? String ?? "?"
            connection.version = message["version"] as? String ?? ""
            connection.env = (message["env"] as? [String: String] ?? [:]).filter {
                DecisionSettings.environmentNames.contains($0.key)
            }
            connection.write(["mac-cu": "hello", "version": bundleVersion])
        case "quit":
            quitDaemon()
        case "permissions":
            handleQueue.async {
                currentSession = connection
                defer { currentSession = nil }
                let accessibility = requestAccessibility(), screenRecording = requestScreenRecording()
                connection.write(["mac-cu": "permissions", "accessibility": accessibility, "screenRecording": screenRecording,
                                  "text": (accessibility ? "The accessibility API is allowed." : accessibilityHelp) + "\n"
                                      + (screenRecording ? "Screen Recording is allowed." : screenRecordingHelp)])
            }
        case .some:
            break
        case nil:
            if message["method"] as? String == "notifications/cancelled" {
                if let id = (message["params"] as? [String: Any])?["requestId"] { connection.cancelRequest(id) }
                return true
            }
            handleQueue.async {
                currentSession = connection
                connection.beginRequest(message["id"])
                defer { connection.endRequest(); currentSession = nil }
                let params = message["params"] as? [String: Any] ?? [:]
                if message["method"] as? String == "tools/call" {
                    let arguments = params["arguments"] as? [String: Any] ?? [:]
                    let target = ["app", "page", "engine", "device"].lazy.compactMap { arguments[$0] as? String }.first ?? ""
                    connectionsLock.lock()
                    connection.current = (params["name"] as? String ?? "", target, Date())
                    connectionsLock.unlock()
                    DispatchQueue.main.async { menuBar?.showBusy(true) }
                }
                if let reply = handle(message) { connection.write(reply) }
                connectionsLock.lock()
                connection.current = nil
                connectionsLock.unlock()
                DispatchQueue.main.async { menuBar?.showBusy(false) }
            }
        }
        return true
    }
    connection.disconnect()
    connectionsLock.lock()
    connections.removeAll { $0 === connection }
    connectionsLock.unlock()
    handleQueue.async { close(fd) }  // After the requests of this connection that still wait.
}

// MARK: - The menu

let modeNames = ["input": "조작 방식", "show": "작업 표시"]
let modeLabels = ["auto": "auto · 뒤에서 조작하고, 안 될 때만 앞으로", "background": "background · 항상 뒤에서만",
                  "foreground": "foreground · 매번 앞으로 가져와 조작",
                  "glow": "glow · 빛과 포인터", "steps": "steps · 빛·포인터와 목표·단계", "off": "off · 표시 없음"]

final class MenuBar: NSObject, NSMenuDelegate, NSApplicationDelegate, NSMenuItemValidation {
    let item = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
    let menu = NSMenu()
    let lcdMenu = NSMenu(title: "LCD")
    var updateTitle = "업데이트 확인…"
    var newVersion: String?
    private var busy = false
    private var trackingMenu = false

    override init() {
        super.init()
        showBusy(false)
        menu.delegate = self
        item.menu = menu
        lcdMenu.delegate = self
        let main = NSMenu()
        let application = NSMenu()
        let settings = NSMenuItem(title: "설정…", action: #selector(showDecisionSettings), keyEquivalent: ",")
        settings.target = self
        application.addItem(settings)
        application.addItem(.separator())
        let quit = NSMenuItem(title: "mac-cu 종료", action: #selector(quit), keyEquivalent: "q")
        quit.target = self
        application.addItem(quit)
        let appItem = NSMenuItem(title: "mac-cu", action: nil, keyEquivalent: "")
        appItem.submenu = application
        main.addItem(appItem)
        let edit = NSMenu(title: "편집")
        for (title, selector, key) in [("실행 취소", "undo:", "z"), ("다시 실행", "redo:", "Z"),
                                       ("오려두기", "cut:", "x"), ("복사", "copy:", "c"),
                                       ("붙여넣기", "paste:", "v"), ("모두 선택", "selectAll:", "a")] {
            let entry = NSMenuItem(title: title, action: #selector(editToolboxText(_:)), keyEquivalent: key.lowercased())
            entry.keyEquivalentModifierMask = key == "Z" ? [.command, .shift] : [.command]
            entry.target = self
            entry.representedObject = selector
            edit.addItem(entry)
        }
        let editItem = NSMenuItem(title: "편집", action: nil, keyEquivalent: "")
        editItem.submenu = edit
        main.addItem(editItem)
        let lcdItem = NSMenuItem(title: "LCD", action: nil, keyEquivalent: "")
        lcdItem.submenu = lcdMenu
        main.addItem(lcdItem)
        NSApp.mainMenu = main
        SimulatorStatusBoard.shared.onChange = { [weak self] in
            SimulatorStatusWindow.shared.redraw()
            self?.refreshWindowStatus()
        }
        SimulatorStatusBoard.shared.start()
        for name in [NSApplication.didBecomeActiveNotification, NSApplication.didResignActiveNotification,
                     NSApplication.didHideNotification, NSApplication.didUnhideNotification] {
            NotificationCenter.default.addObserver(self, selector: #selector(windowStatusChanged), name: name, object: NSApp)
        }
        NotificationCenter.default.addObserver(self, selector: #selector(windowStatusChanged), name: NSApplication.didChangeScreenParametersNotification, object: nil)
        for name in [NSWorkspace.didActivateApplicationNotification, NSWorkspace.activeSpaceDidChangeNotification] {
            NSWorkspace.shared.notificationCenter.addObserver(self, selector: #selector(windowStatusChanged), name: name, object: nil)
        }
    }

    func showBusy(_ busy: Bool) {
        self.busy = busy
        refreshWindowStatus()
    }

    func refreshWindowStatus() {
        let name = busy ? "rectangle.and.hand.point.up.left.filled" : "rectangle.and.hand.point.up.left"
        item.button?.image = NSImage(systemSymbolName: name, accessibilityDescription: "mac-cu")
        item.button?.imagePosition = .imageLeft
        let windows = simulatorWindows.values.sorted { $0.window.title < $1.window.title }
        SimulatorPreviewStacks.shared.update()
        let background = windows.filter { simulatorWindowVisibility($0.window) != .foreground }.count
        item.button?.title = windows.count == 1 ? " LCD · \(simulatorWindowVisibility(windows[0].window).rawValue)" :
            windows.isEmpty ? "" : " LCD \(windows.count) · 배경 \(background)"
        item.button?.toolTip = (["mac-cu \(bundleVersion)"] + windows.map {
            "\($0.window.title) · \(simulatorWindowVisibility($0.window).rawValue)"
        }).joined(separator: "\n")
        if !trackingMenu { updateLCDMenu() }
    }

    @objc func windowStatusChanged(_ notification: Notification) {
        DispatchQueue.main.async { [weak self] in self?.refreshWindowStatus() }
    }

    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool {
        let open = recentSimulatorWindowID.flatMap { simulatorWindows[$0] } ?? simulatorWindows.values.first
        if let open { bringSimulatorWindowToFront(open) }
        return false
    }

    func applicationShouldTerminate(_ sender: NSApplication) -> NSApplication.TerminateReply { quitDaemon() }

    func menuNeedsUpdate(_ menu: NSMenu) {
        if menu === lcdMenu { updateLCDMenu(); return }
        menu.removeAllItems()
        menu.addItem(label("mac-cu \(bundleVersion)"))
        let settings = NSMenuItem(title: "설정…", action: #selector(showDecisionSettings), keyEquivalent: ",")
        settings.target = self
        menu.addItem(settings)
        if !simulatorWindows.isEmpty {
            menu.addItem(.separator())
            appendLCDItems(to: menu)
        }
        connectionsLock.lock()
        let sessions = connections.map { ($0.agent, $0.current) }
        connectionsLock.unlock()
        if sessions.isEmpty { menu.addItem(label("연결된 세션 없음")) }
        for (agent, current) in sessions {
            guard let current else {
                menu.addItem(label("\(agent) · 대기"))
                continue
            }
            let elapsed = String(format: "경과 %.1f초", Date().timeIntervalSince(current.started))
            menu.addItem(label([agent, toolNames[current.tool] ?? current.tool, current.target, elapsed].filter { !$0.isEmpty }.joined(separator: " · ")))
        }
        menu.addItem(.separator())
        let simulators = SimulatorStatusBoard.shared.statuses
        menu.addItem(label(simulators.isEmpty ? "부팅된 시뮬레이터 없음" : "시뮬레이터 \(simulators.count)대"))
        for status in simulators { menu.addItem(label("  " + status.line)) }
        let window = NSMenuItem(title: "시뮬레이터 상태 창 열기…", action: #selector(showSimulators), keyEquivalent: "")
        window.target = self
        menu.addItem(window)
        menu.addItem(.separator())
        for permission in [Permission.accessibility, .screenRecording] {
            let granted = permission.isGranted
            let name = permission == .accessibility ? "손쉬운 사용" : "화면 기록"
            let entry = NSMenuItem(title: "\(name) \(granted ? "✓" : "✗")", action: granted ? nil : #selector(guide(_:)), keyEquivalent: "")
            entry.target = self
            entry.representedObject = permission.rawValue
            menu.addItem(entry)
        }
        menu.addItem(.separator())
        let current = modes()
        for choice in modeChoices {
            let submenu = NSMenu()
            for value in choice.values {
                let entry = NSMenuItem(title: modeLabels[value] ?? value, action: #selector(setMode(_:)), keyEquivalent: "")
                entry.target = self
                entry.representedObject = "\(choice.name)=\(value)"
                entry.state = current[choice.name] == value ? .on : .off
                submenu.addItem(entry)
            }
            let entry = NSMenuItem(title: modeNames[choice.name] ?? choice.name, action: nil, keyEquivalent: "")
            entry.submenu = submenu
            menu.addItem(entry)
        }
        menu.addItem(.separator())
        let update = NSMenuItem(title: newVersion.map { "\($0)으로 업데이트" } ?? updateTitle,
                                action: newVersion == nil ? #selector(checkUpdate) : #selector(runUpdate), keyEquivalent: "")
        update.target = self
        menu.addItem(update)
        let quit = NSMenuItem(title: "종료", action: #selector(quit), keyEquivalent: "")
        quit.target = self
        menu.addItem(quit)
    }

    func menuWillOpen(_ menu: NSMenu) { trackingMenu = true }
    func menuDidClose(_ menu: NSMenu) { trackingMenu = false; refreshWindowStatus() }

    func updateLCDMenu() {
        lcdMenu.removeAllItems()
        if simulatorWindows.isEmpty { lcdMenu.addItem(label("열린 LCD 창 없음")) }
        else { appendLCDItems(to: lcdMenu) }
    }

    func appendLCDItems(to menu: NSMenu) {
        let windows = simulatorWindows.values.sorted { $0.window.title < $1.window.title }
        menu.addItem(label("LCD 창 \(windows.count)개"))
        let recent = recentSimulatorWindowID.flatMap { simulatorWindows[$0]?.id } ?? windows.first?.id
        for open in windows {
            let visibility = simulatorWindowVisibility(open.window)
            let entry = NSMenuItem(title: "\(open.window.title) · \(visibility.rawValue)", action: #selector(showLCD(_:)), keyEquivalent: "")
            entry.target = self
            entry.representedObject = open.id
            entry.state = visibility == .foreground ? .on : .off
            menu.addItem(entry)
            let panel = open.preview?.panel
            let needsPreview = open.needsPreview
            let state = SimulatorPreviewWindow.isHiddenByUser ? "설정으로 숨김" : !needsPreview ? "숨김 (LCD 보임)" :
                open.preview?.dismissed == true ? "개별 숨김" : open.preview?.isCollapsed == true ? "접힘 (+N)" :
                panel.map { $0.isVisible || $0.isMiniaturized ? simulatorWindowVisibility($0).rawValue : "닫힘" } ?? "자동 표시"
            let preview = NSMenuItem(title: "프리뷰 · \(state)", action: #selector(showLCDPreview(_:)), keyEquivalent: "")
            preview.target = self
            preview.representedObject = open.id
            preview.indentationLevel = 1
            preview.isEnabled = needsPreview && !SimulatorPreviewWindow.isHiddenByUser
            if menu === lcdMenu && open.id == recent {
                preview.keyEquivalent = "p"
                preview.keyEquivalentModifierMask = [.command, .shift]
            }
            menu.addItem(preview)
            let tools = NSMenuItem(title: "도구 표시", action: #selector(toggleLCDTools(_:)), keyEquivalent: "")
            tools.target = self
            tools.representedObject = open.id
            tools.state = open.content.toolsVisible ? .on : .off
            tools.indentationLevel = 1
            if menu === lcdMenu && open.id == recent {
                tools.keyEquivalent = "t"
                tools.keyEquivalentModifierMask = [.command, .shift]
            }
            menu.addItem(tools)
            let device = NSMenuItem(title: "기기 메뉴", action: nil, keyEquivalent: "")
            device.submenu = open.deviceMenu()
            device.indentationLevel = 1
            menu.addItem(device)
        }
        let opacity = NSMenuItem(title: "프리뷰 불투명도", action: nil, keyEquivalent: "")
        opacity.submenu = SimulatorPreviewWindow.opacityMenu()
        menu.addItem(opacity)
        menu.addItem(SimulatorPreviewWindow.hiddenMenuItem())
        let arrange = NSMenuItem(title: "프리뷰 전체 정렬", action: #selector(arrangePreviews), keyEquivalent: "")
        arrange.target = self
        menu.addItem(arrange)
    }

    func label(_ title: String) -> NSMenuItem {
        let entry = NSMenuItem(title: title, action: nil, keyEquivalent: "")
        entry.isEnabled = false
        return entry
    }

    @objc func showSimulators() { SimulatorStatusWindow.shared.show() }

    @objc func showDecisionSettings() {
        // Menu actions have no requesting MCP session. Never reuse the last client's key.
        DecisionSettingsWindow.shared.show()
    }

    @objc func showLCD(_ sender: NSMenuItem) {
        if let id = sender.representedObject as? String, let open = simulatorWindows[id] { bringSimulatorWindowToFront(open) }
    }

    @objc func showLCDPreview(_ sender: NSMenuItem) {
        if let id = sender.representedObject as? String { simulatorWindows[id]?.showPreview() }
    }

    @objc func toggleLCDTools(_ sender: NSMenuItem) {
        if let id = sender.representedObject as? String { simulatorWindows[id]?.toggleToolbox() }
    }

    @objc func arrangePreviews() {
        SimulatorPreviewStacks.shared.arrangeAll()
        refreshWindowStatus()
    }

    func validateMenuItem(_ item: NSMenuItem) -> Bool {
        if item.action == #selector(editToolboxText(_:)) { return NSApp.keyWindow?.firstResponder is NSTextView }
        guard item.action == #selector(showLCDPreview(_:)) else { return true }
        guard let id = item.representedObject as? String, let open = simulatorWindows[id] else { return false }
        return open.needsPreview && !SimulatorPreviewWindow.isHiddenByUser
    }

    @objc func editToolboxText(_ sender: NSMenuItem) {
        guard let editor = NSApp.keyWindow?.firstResponder as? NSTextView,
              let action = sender.representedObject as? String else { return }
        if action == "undo:" { editor.undoManager?.undo() }
        else if action == "redo:" { editor.undoManager?.redo() }
        else { NSApp.sendAction(NSSelectorFromString(action), to: editor, from: sender) }
    }

    @objc func guide(_ sender: NSMenuItem) {
        if let permission = Permission(rawValue: sender.representedObject as? String ?? "") { showPermissionGuide(permission) }
    }

    @objc func setMode(_ sender: NSMenuItem) {
        let parts = (sender.representedObject as? String ?? "").split(separator: "=").map(String.init)
        guard parts.count == 2 else { return }
        var current = modes()
        current[parts[0]] = parts[1]
        _ = saveModes(current)
    }

    /// This distribution leaves Plugin updates to the selected host and installed setup script.
    @objc func checkUpdate() { showUpdateGuidance() }
    @objc func runUpdate() { showUpdateGuidance() }

    @objc func quit() { quitDaemon() }
}

/// Explain manual updates without mutating a different marketplace or installation.
func showUpdateGuidance() {
    NSApplication.shared.setActivationPolicy(.accessory)
    let alert = NSAlert()
    alert.messageText = "mac-cu 수동 업데이트"
    alert.informativeText = "호스트에서 mac-computer-use@oozoofrog-plugin을 업데이트한 뒤, 설치된 스킬의 scripts/setup.py --agent codex (또는 claude)를 다시 실행하고 새 세션을 시작하세요."
    NSApp.activate(ignoringOtherApps: true)
    alert.runModal()
}

func runUpdateCommand() -> Never {
    showUpdateGuidance()
    exit(0)
}

// MARK: - Client

/// -n: a new instance even when a guide or dialog of the same app runs (Launch Services counts those as the app);
/// a second daemon sees the first one's socket and exits at once.
func openDaemon() {
    let open = Process()
    open.executableURL = URL(fileURLWithPath: "/usr/bin/open")
    open.arguments = ["-g", "-n", "-a", daemonBundle.path, "--args", "--daemon"]
    open.standardOutput = FileHandle.nullDevice
    open.standardError = FileHandle.nullDevice
    try? open.run()
    open.waitUntilExit()
}

/// Asks the daemon on fd to quit and waits until it has closed the socket (it removes the socket file first).
func stopDaemon(_ fd: Int32) {
    _ = writeLine(fd, ["mac-cu": "quit"])
    readLines(fd) { _ in true }
    close(fd)
}

/// Connects and says hello. Starts the daemon when it does not run, and replaces an older one (after a plugin
/// update, until the next call). Returns nil with the reason on stderr.
func connectDaemon(hello: [String: Any]) -> Int32? {
    for attempt in 0..<2 {
        var fd = connectSocket(daemonSocket)
        if fd == nil {
            openDaemon()
            for _ in 0..<50 where fd == nil {
                usleep(100_000)
                fd = connectSocket(daemonSocket)
            }
        }
        guard let fd else {
            fputs("mac-cu.app did not start from \(daemonBundle.path). Run setup.py.\n", stderr)
            return nil
        }
        guard let reply = exchange(fd, hello) else {
            close(fd)
            fputs("The mac-cu daemon did not answer.\n", stderr)
            return nil
        }
        if let error = reply["error"] as? String {
            close(fd)
            fputs(error + "\n", stderr)
            return nil
        }
        if attempt == 1 || !isNewer(bundleVersion, than: reply["version"] as? String ?? "0") { return fd }
        stopDaemon(fd)
    }
    return nil
}

/// The MCP stdio server that the agent starts: lines go to the daemon and its lines come back.
func runClient() -> Never {
    signal(SIGPIPE, SIG_IGN)
    let apps = parentApps()
    let agent = (apps.first(where: hasIcon) ?? apps.first).map { $0.deletingPathExtension().lastPathComponent } ?? "terminal"
    let env = ProcessInfo.processInfo.environment.filter { DecisionSettings.environmentNames.contains($0.key) }
    let hello: [String: Any] = ["mac-cu": "hello", "version": bundleVersion, "agent": agent, "env": env]
    let lock = NSLock()
    var socket: Int32?
    func connection() -> Int32? {
        lock.lock()
        defer { lock.unlock() }
        if let socket { return socket }
        guard let fd = connectDaemon(hello: hello) else { return nil }
        socket = fd
        Thread.detachNewThread {
            readLines(fd) { line in
                FileHandle.standardOutput.write(line + Data([0x0a]))
                return true
            }
            lock.lock()
            if socket == fd { socket = nil }  // The daemon quit: the next line connects again.
            lock.unlock()
            close(fd)
        }
        return fd
    }
    while let line = readLine(strippingNewline: true) {
        var sent = false
        for _ in 0..<2 where !sent {
            guard let fd = connection() else { break }
            sent = writeAll(fd, Data(line.utf8) + Data([0x0a]))
            if !sent {
                lock.lock()
                if socket == fd { socket = nil }
                lock.unlock()
            }
        }
        if !sent, let id = (try? JSONSerialization.jsonObject(with: Data(line.utf8)) as? [String: Any])?["id"] {
            _ = writeLine(1, ["jsonrpc": "2.0", "id": id, "error": ["code": -32000, "message": "mac-cu could not reach its daemon (see stderr). Run setup.py."]])
        }
    }
    exit(0)
}

/// `mac-cu --quit-daemon` (setup.py, before it starts the new build): quit the daemon when it runs.
func runQuitDaemonCommand() -> Never {
    if let fd = connectSocket(daemonSocket) { stopDaemon(fd) }
    exit(0)
}
