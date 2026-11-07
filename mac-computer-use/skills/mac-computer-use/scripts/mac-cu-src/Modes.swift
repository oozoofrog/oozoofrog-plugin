// Modes that the user sets with `mac-cu --mode` (the skill runs it when the user asks):
//   input  auto (default): act uses the background, and foreground when the agent asks for it.
//          background: act refuses foreground. foreground: every act runs with the app in front.
//   show   glow (default): focus-overlay shows the glow and the pointer (Claude Code hooks, focus.py).
//          steps: also the goal of act and its current step on the target window.
//          off: no glow, pointer or preview.
// mac-cu reads the file on each call, so a change works without a restart.

import AppKit

let modesFile = savedAllowList.deletingLastPathComponent().appendingPathComponent("modes.json")
/// The first choice is the default.
let modeChoices: [(name: String, values: [String])] = [("input", ["auto", "background", "foreground"]),
                                                       ("show", ["glow", "steps", "off"])]

func modes() -> [String: String] {
    let saved = (try? Data(contentsOf: modesFile)).flatMap { try? JSONSerialization.jsonObject(with: $0) } as? [String: String] ?? [:]
    var result: [String: String] = [:]
    for choice in modeChoices {
        result[choice.name] = saved[choice.name].flatMap { choice.values.contains($0) ? $0 : nil } ?? choice.values[0]
    }
    return result
}

/// `mac-cu --mode [input=…] [show=…]`: set the given modes, then print all of them. Exit 2 on a wrong setting.
func runModeCommand(_ settings: [String]) -> Never {
    var current = modes()
    for setting in settings {
        let parts = setting.split(separator: "=", maxSplits: 1).map(String.init)
        guard parts.count == 2, let choice = modeChoices.first(where: { $0.name == parts[0] }), choice.values.contains(parts[1]) else {
            print("Unknown setting \(setting). Use " + modeChoices.map { "\($0.name)=\($0.values.joined(separator: "|"))" }.joined(separator: " ") + ".")
            exit(2)
        }
        current[parts[0]] = parts[1]
    }
    if !settings.isEmpty, !saveModes(current) {
        print("Could not write \(modesFile.path).")
        exit(1)
    }
    print(modeChoices.map { "\($0.name)=\(current[$0.name]!)" }.joined(separator: " "))
    exit(0)
}

/// Writes the modes (also the menu of the daemon). False when the file could not be written.
func saveModes(_ modes: [String: String]) -> Bool {
    try? FileManager.default.createDirectory(at: modesFile.deletingLastPathComponent(), withIntermediateDirectories: true)
    guard let data = try? JSONSerialization.data(withJSONObject: modes, options: [.sortedKeys]) else { return false }
    return (try? data.write(to: modesFile)) != nil
}

/// Write a record with the time for focus-overlay to $TMPDIR/<folder>/<pid>.json. The overlay of that app's
/// window reads it about five times a second and shows it for a few seconds after the time.
func tellOverlay(_ folder: String, pid: pid_t, _ record: [String: Any]) {
    let path = NSTemporaryDirectory() + folder
    try? FileManager.default.createDirectory(atPath: path, withIntermediateDirectories: true)
    if let data = try? JSONSerialization.data(withJSONObject: record.merging(["time": Date().timeIntervalSince1970]) { $1 }) {
        FileManager.default.createFile(atPath: "\(path)/\(pid).json", contents: data)
    }
}

/// With show=steps, tell focus-overlay what act does now in the app: the goal and the step.
func showStep(_ step: String, goal: String?, pid: pid_t) {
    tellOverlay("mac-cu-status", pid: pid, ["goal": goal ?? "", "step": step])
}

/// With guides, tell focus-overlay the element boxes (Window Server coordinates, the numbers of the tree), so
/// that it shows them with rulers on the window for 8 seconds. Not with show=off.
func showGuides(_ boxes: [GuideBox], pid: pid_t) {
    tellOverlay("mac-cu-guides", pid: pid, ["boxes": boxes.map {
        ["n": $0.number, "x": $0.rect.minX, "y": $0.rect.minY, "w": $0.rect.width, "h": $0.rect.height]
    }])
}

/// A short Korean line for an act action, for the user. Typed text shows only its length (it can be a password).
func stepText(_ action: [String: Any], session: Session) -> String {
    var name = ""
    if let index = action["element"] as? Int, session.elements.indices.contains(index) {
        let node = session.elements[index]
        let label = [kAXTitleAttribute, kAXDescriptionAttribute].lazy.compactMap { string(node, $0) }.first { !$0.isEmpty }
        name = " · " + (label.map { String($0.prefix(30)) } ?? "요소 \(index)")
    }
    let length = (action["text"] as? String).map { " (\($0.count)자)" } ?? ""
    switch action["type"] as? String ?? "" {
    case "click":
        let kind = action["button"] as? String == "right" ? "오른쪽 클릭" : (action["count"] as? Int ?? 1) > 1 ? "더블 클릭" : "클릭"
        return kind + name
    case "set_value": return "값 넣기" + name + length
    case "type_text": return "입력" + length
    case "press_key": return "키 · " + (action["key"] as? String ?? "")
    case "select_text": return "텍스트 선택" + name
    case "scroll": return "스크롤 " + (action["direction"] as? String ?? "down") + name
    case "perform": return "동작 " + (action["action"] as? String ?? "") + name
    case "menu": return "메뉴 · " + (action["path"] as? [String] ?? []).joined(separator: " > ")
    case "click_at": return "클릭 (화면 위치)"
    case "drag": return "드래그"
    case "wait": return "기다림"
    case let other: return other
    }
}
