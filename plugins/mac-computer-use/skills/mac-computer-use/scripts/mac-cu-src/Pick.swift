// Pick an interactive element using OpenAI Decisions.

import AppKit

/// Candidates in one question, besides "none".
let pickLimit = 31
/// An element the pick question can choose: its label in the question, its number in the tree, its line.
struct PickCandidate {
    let key: String
    let number: Int
    let line: String
}

/// Korean names for roles and window buttons.
private let pickRoleNames = [
    "Button": "버튼", "CheckBox": "체크 상자", "RadioButton": "라디오 버튼", "PopUpButton": "팝업 메뉴",
    "MenuButton": "메뉴 버튼", "ComboBox": "콤보 상자", "TextField": "입력 칸", "TextArea": "글 입력 영역",
    "Slider": "슬라이더", "DisclosureTriangle": "펼치기 삼각형", "Cell": "셀", "Row": "행", "Link": "링크",
    "Tab": "탭", "Incrementor": "증감 버튼", "SearchField": "검색 칸", "MenuItem": "메뉴 항목",
]
private let pickWindowButtons = ["CloseButton": "창 닫기", "MinimizeButton": "창 최소화",
                                 "FullScreenButton": "전체 화면", "ZoomButton": "창 확대"]

private let pickSkippedRoles: Set<String> = ["ScrollArea", "ScrollBar", "Ruler", "RulerMarker", "StaticText", "Image",
                                             "Toolbar", "Group", "Splitter", "LayoutArea"]

/// The text after `name="` up to the next quote, or the leading quoted title when name is nil.
private func quotedField(_ text: String, _ name: String?) -> String? {
    let start: String.Index
    if let name {
        guard let range = text.range(of: "\(name)=\"") else { return nil }
        start = range.upperBound
    } else {
        guard text.hasPrefix("\"") else { return nil }
        start = text.index(after: text.startIndex)
    }
    guard let end = text[start...].firstIndex(of: "\"") else { return nil }
    let value = String(text[start..<end]).trimmingCharacters(in: .whitespaces)
    return value.isEmpty ? nil : value
}

/// An element before ranking: its label, the Korean name of its role, its number, and its line.
typealias PickItem = (label: String, roleName: String, number: Int, line: String)

/// Keys for the items (role name and label, unique), those sharing more of the goal first, up to pickLimit.
func rankPicks(_ items: [PickItem], goal: String) -> [PickCandidate] {
    let lowerGoal = goal.lowercased()
    var used: [String: Int] = [:]
    var scored: [(candidate: PickCandidate, score: Int, order: Int)] = []
    for (order, item) in items.enumerated() {
        var key = String((item.label.isEmpty ? item.roleName : "\(item.roleName) \(item.label)").prefix(48))
        used[key, default: 0] += 1
        if used[key]! > 1 { key += " #\(used[key]!)" }
        // Shared characters pairs: Korean words carry particles ("볼드체를"), so whole words seldom match.
        let lowerLabel = item.label.lowercased()
        let pairs = zip(lowerLabel, lowerLabel.dropFirst()).map { String([$0, $1]) }
        let score = (lowerGoal.contains(lowerLabel) ? 2 : 0) + pairs.filter { lowerGoal.contains($0) }.count
        scored.append((PickCandidate(key: key, number: item.number, line: item.line), score, order))
    }
    return scored.sorted { ($0.score, -$0.order) > ($1.score, -$1.order) }.prefix(pickLimit).map(\.candidate)
}

/// The enabled elements of a tree that take an action or text, those sharing more of the goal first.
func pickCandidates(tree: String, goal: String) -> [PickCandidate] {
    let marks = "[\u{200E}\u{200F}\u{202A}-\u{202E}]"
    var items: [PickItem] = []
    for raw in tree.split(separator: "\n") {
        let line = raw.trimmingCharacters(in: .whitespaces)
            .replacingOccurrences(of: marks, with: "", options: .regularExpression)
        let parts = line.split(separator: " ", maxSplits: 2).map(String.init)
        guard parts.count >= 2, let number = Int(parts[0]) else { continue }
        let role = parts[1], rest = parts.count > 2 ? parts[2] : ""
        let roles = role.split(separator: "/").map(String.init)
        guard let base = roles.first, !pickSkippedRoles.contains(base), base != "Window", base != "Sheet",
              !rest.contains(" disabled"), !rest.hasSuffix("disabled"), rest.contains("[") || rest.contains("editable")
        else { continue }
        let roleName = pickRoleNames[base] ?? base
        let named = quotedField(rest, nil) ?? quotedField(rest, "desc") ?? quotedField(rest, "value")
        let label = roles.dropFirst().compactMap { pickWindowButtons[$0] }.first ?? named ?? ""
        items.append((label, roleName, number, "\(role) \(rest)"))
    }
    return rankPicks(items, goal: goal)
}

/// The request body of a pick, and the candidates it names. place is where the elements are ("창", "페이지").
func pickRequest(candidates: [PickCandidate], goal: String, intro: String, content: String,
                 place: String = "창", elsewhere: String = "다른 앱이나 다른 창") -> (body: [String: Any], candidates: [PickCandidate]) {
    var criteria: [String: Any] = [:]
    for candidate in candidates { criteria[candidate.key] = candidate.line }
    criteria["none"] = "이 \(place)의 어떤 요소도 목표와 관계없다. 목표는 \(elsewhere)의 일이다."
    let question: [String: Any] = [
        "type": "choice",
        "instructions": "목표를 이루려면 이 \(place)에서 다음에 누르거나 입력할 요소 하나를 고른다. 목표와 가장 직접 관련된 요소를 고르고, "
            + "이 \(place)의 어떤 요소도 목표와 관계없을 때만 none을 고른다. " + evidenceRule,
        "choices": criteria.keys.sorted().map { ["value": $0, "description": criteria[$0] as! String] },
    ]
    let state = ["목표: " + goal, intro, content].joined(separator: "\n\n")
    return (["input": state, "questions": ["pick": question]], candidates)
}

func pickRequest(tree: String, goal: String) -> (body: [String: Any], candidates: [PickCandidate]) {
    pickRequest(candidates: pickCandidates(tree: tree, goal: goal), goal: goal, intro: appTreeIntro, content: slimTree(tree).0)
}

/// Korean names for page elements, by role, input type or tag.
private let pagePickNames = [
    "a": "링크", "link": "링크", "button": "버튼", "submit": "버튼", "reset": "버튼", "checkbox": "체크 상자",
    "radio": "라디오 버튼", "select": "팝업 메뉴", "textarea": "글 입력 영역", "input": "입력 칸", "text": "입력 칸",
    "textbox": "입력 칸", "email": "입력 칸", "password": "입력 칸", "number": "입력 칸", "search": "검색 칸",
    "tab": "탭", "menuitem": "메뉴 항목", "option": "선택 항목", "switch": "스위치", "summary": "펼치기",
]

/// A pick over the elements of a page (lines of pageScript: number, tag[type], role=, "label", href=, flags).
func pageRequest(page: (text: String, elements: [String]), goal: String) -> (body: [String: Any], candidates: [PickCandidate]) {
    let items: [PickItem] = page.elements.compactMap { line in
        let parts = line.split(separator: " ", maxSplits: 2).map(String.init)
        guard parts.count >= 2, let number = Int(parts[0]), !line.hasSuffix(" disabled"), !line.contains(" disabled ") else { return nil }
        let rest = parts.count > 2 ? parts[2] : ""
        let tag = parts[1].split(separator: "[").first.map(String.init) ?? parts[1]
        let type = parts[1].contains("[") ? String(parts[1].split(separator: "[")[1].dropLast()) : nil
        let role = rest.range(of: #"(?<=^role=)\S+"#, options: .regularExpression).map { String(rest[$0]) }
        let afterRole = rest.replacingOccurrences(of: #"^role=\S+ ?"#, with: "", options: .regularExpression)
        let label = quotedField(afterRole, nil) ?? quotedField(rest, "placeholder") ?? quotedField(rest, "value") ?? ""
        let roleName = [role, type, tag].compactMap { $0.flatMap { pagePickNames[$0] } }.first ?? tag
        return (label, roleName, number, String(parts.dropFirst().joined(separator: " ")))
    }
    return pickRequest(candidates: rankPicks(items, goal: goal), goal: goal, intro: pageIntro, content: page.text,
                       place: "페이지", elsewhere: "다른 페이지나 다른 탭")
}

/// The pick for a tree: its line for the agent, whether it is sure, and the chosen candidate.
func askPick(tree: String, goal: String, model: String?) throws -> (line: String, sure: Bool, choice: PickCandidate?) {
    try askPick(request: pickRequest(tree: tree, goal: goal), model: model)
}

func askPick(request: (body: [String: Any], candidates: [PickCandidate]), model: String?) throws -> (line: String, sure: Bool, choice: PickCandidate?) {
    let (body, candidates) = request
    guard !candidates.isEmpty else { return ("pick: none (no element in this window takes an action)", true, nil) }
    let answer = try askChoice(body: body, model: model)
    let label = answer["choice"] as? String ?? ""
    let confidence = (answer["confidence"] as? NSNumber)?.doubleValue ?? 0
    let next = (answer["probabilities"] as? [String: Any] ?? [:])
        .filter { $0.key != label }.max { ($0.value as? Double ?? 0) < ($1.value as? Double ?? 0) }
        .map { "; next: \($0.key) \(String(format: "%.2f", ($0.value as? NSNumber)?.doubleValue ?? 0))" } ?? ""
    let chosen = candidates.first { $0.key == label }
    let what = label == "none" ? "none" : chosen.map { "\($0.key) → element \($0.number)" } ?? "?"
    return ("pick: unknown: \(what) (\(String(format: "%.2f", confidence))\(next))", false, chosen)
}

/// Posts a request with one question named "pick" and returns its answer.
func askChoice(body: [String: Any], model: String?) throws -> [String: Any] {
    var body = body
    if let model, !model.isEmpty { body["model"] = model }
    return try postDecide(body)["pick"] ?? [:]
}

/// `mac-cu --pick-request <tree file> <goal>`: the request body and candidate numbers as JSON, for the test.
func printPickRequest(treeFile: String, goal: String) -> Never {
    let tree = (try? String(contentsOfFile: treeFile, encoding: .utf8)) ?? ""
    let (body, candidates) = pickRequest(tree: tree, goal: goal)
    let numbers = Dictionary(candidates.map { ($0.key, $0.number) }, uniquingKeysWith: { first, _ in first })
    let data = (try? JSONSerialization.data(withJSONObject: ["body": body, "numbers": numbers], options: [.sortedKeys, .withoutEscapingSlashes])) ?? Data()
    FileHandle.standardOutput.write(data)
    exit(0)
}
