// Simulator status on the Mac: the booted simulators, the screen that is on and its rotation, and which agent session
// uses each (simulator-pilot's `sim-pilot claim`), in mac-cu's menu bar menu and in a small window that keeps itself
// up to date. It is the same for Claude Code, Codex and the person: nothing here depends on an agent.

import AppKit

struct SimulatorStatus {
    let name: String
    let udid: String
    let runtime: String
    let screen: String   // "LCD-1 rot90", or "" when devicectl gives no displays
    let user: String     // the session that claimed it (its note, else its id), or ""
    let since: String

    var line: String {
        [name, runtime, screen.isEmpty ? nil : "화면 \(screen)", user.isEmpty ? "사용 기록 없음" : "사용: \(user)"]
            .compactMap { $0 }.joined(separator: " · ")
    }
}

/// simulator-pilot's claims (Library/Application Support/sim-pilot/claims.json): udid → (who, since), for sessions
/// whose process still runs.
func simulatorClaims() -> [String: (String, String)] {
    let file = FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library/Application Support/sim-pilot/claims.json")
    guard let data = try? Data(contentsOf: file),
          let all = try? JSONSerialization.jsonObject(with: data) as? [String: [String: Any]] else { return [:] }
    var claims: [String: (String, String)] = [:]
    for (udid, claim) in all {
        let pid = (claim["pid"] as? NSNumber)?.int32Value ?? 0
        guard pid > 0, kill(pid, 0) == 0 || errno == EPERM else { continue }
        let note = claim["note"] as? String ?? "", by = claim["by"] as? String ?? ""
        claims[udid] = (note.isEmpty ? by : note, claim["since"] as? String ?? "")
    }
    return claims
}

/// The status of each booted simulator (devicectl takes about 0.15 s a device).
func collectSimulatorStatus() -> [SimulatorStatus] {
    guard let devices = try? simulatorDevices().filter(isBooted) else { return [] }
    let claims = simulatorClaims()
    return devices.map { device in
        let id = udid(of: device)
        let integrated = (displays(of: id) ?? []).filter { ($0["type"] as? [String: Any])?["integrated"] != nil }
        let on = integrated.count > 1 ? integrated.first { $0["active"] as? Bool == true } : integrated.first
        let screen = on.map { "\($0["name"] as? String ?? "?") \($0["currentOrientation"] as? String ?? "")" } ?? ""
        let runtime = (device.value(forKey: "runtime") as? NSObject)?.value(forKey: "name") as? String ?? ""
        return SimulatorStatus(name: device.value(forKey: "name") as? String ?? id, udid: id, runtime: runtime,
                               screen: integrated.count > 1 ? "\(screen) (화면 \(integrated.count)개)" : screen,
                               user: claims[id]?.0 ?? "", since: claims[id]?.1 ?? "")
    }.sorted { $0.name < $1.name }
}

/// The latest status, refreshed every 5 seconds in the background so the menu opens at once.
final class SimulatorStatusBoard {
    static let shared = SimulatorStatusBoard()
    private let lock = NSLock()
    private var latest: [SimulatorStatus] = []
    private var updated = Date.distantPast
    private var timer: DispatchSourceTimer?
    var onChange: (() -> Void)?

    var statuses: [SimulatorStatus] { lock.lock(); defer { lock.unlock() }; return latest }
    var updatedAt: Date { lock.lock(); defer { lock.unlock() }; return updated }

    func start() {
        guard timer == nil else { return }
        let timer = DispatchSource.makeTimerSource(queue: DispatchQueue.global(qos: .utility))
        timer.schedule(deadline: .now(), repeating: 5)
        timer.setEventHandler { [weak self] in
            let now = collectSimulatorStatus()
            guard let self else { return }
            self.lock.lock(); self.latest = now; self.updated = Date(); self.lock.unlock()
            DispatchQueue.main.async { self.onChange?() }
        }
        timer.resume()
        self.timer = timer
    }
}

/// A small window that lists the simulators and redraws itself with the board.
final class SimulatorStatusWindow: NSObject {
    static let shared = SimulatorStatusWindow()
    private var panel: NSPanel?
    private var textView: NSTextView?

    func show() {
        if panel == nil {
            let panel = NSPanel(contentRect: NSRect(x: 0, y: 0, width: 560, height: 320),
                                styleMask: [.titled, .closable, .resizable, .utilityWindow], backing: .buffered, defer: false)
            panel.title = "시뮬레이터 상태 (mac-cu)"
            panel.isFloatingPanel = true
            panel.hidesOnDeactivate = false
            let scroll = NSTextView.scrollableTextView()  // wraps to the width and scrolls from the top
            let textView = scroll.documentView as! NSTextView
            textView.isEditable = false
            textView.font = .monospacedSystemFont(ofSize: 12, weight: .regular)
            textView.textContainerInset = NSSize(width: 8, height: 8)
            panel.contentView = scroll
            panel.center()
            self.panel = panel
            self.textView = textView
        }
        panel?.orderFrontRegardless()
        redraw()
    }

    func redraw() {
        guard let panel, panel.isVisible, let textView else { return }  // A hidden window is drawn when it is shown.
        let board = SimulatorStatusBoard.shared
        let time = DateFormatter.localizedString(from: board.updatedAt, dateStyle: .none, timeStyle: .medium)
        let rows = board.statuses.map { status in
            "\(status.name)  \(status.runtime)\n  \(status.screen.isEmpty ? "화면 정보 없음" : "켜진 화면: \(status.screen)")\n  " +
                (status.user.isEmpty ? "사용 기록 없음 (sim-pilot claim으로 기록)" : "사용 중: \(status.user)\(status.since.isEmpty ? "" : " · \(status.since)부터")") +
                "\n  \(status.udid)"
        }
        textView.string = (rows.isEmpty ? "부팅된 시뮬레이터가 없습니다." : rows.joined(separator: "\n\n")) +
            "\n\n\(time)에 읽음 · 5초마다 새로 읽습니다. 다른 세션이 쓰는 기기는 끄거나 접기 전에 그 세션에 물어보세요."
    }
}
