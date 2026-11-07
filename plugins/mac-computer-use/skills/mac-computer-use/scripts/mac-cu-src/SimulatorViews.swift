// The view hierarchy of an app in a booted simulator: UIView classes, frames, hidden, alpha and Auto Layout
// constraints, as Xcode's view debugger reads them.
//
// Undocumented parts: Xcode's view debugger asks the app's DebugHierarchyFoundation (DBGTargetHub, in the simulator
// runtime) with a request, a base64 JSON dictionary, after loading the runtime's libViewDebuggerSupport.dylib into the
// app. mac-cu does the same through lldb: attach, run the request on the main thread, write the JSON answer to a file,
// detach. The app is stopped while lldb is attached (about 20 seconds for KakaoTalk, mostly lldb itself).
// Request keys and the property action's fields were found by sending requests and reading the answers
// (plugins/mac-computer-use/docs/development/simulator-deep/README.md, L3-3).

import Foundation

/// NSLayoutAttribute and NSLayoutRelation names, for constraints.
private let layoutAttributes = ["", "left", "right", "top", "bottom", "leading", "trailing", "width", "height", "centerX",
                                "centerY", "lastBaseline", "firstBaseline", "leftMargin", "rightMargin", "topMargin",
                                "bottomMargin", "leadingMargin", "trailingMargin", "centerXWithinMargins", "centerYWithinMargins"]
private let layoutRelations = [-1: "<=", 0: "=", 1: ">="]

/// The view hierarchy of the app with pid, as text: one line for each view (class, frame in its superview,
/// hidden, alpha, accessibility id or label, text), its constraints under it. query keeps the subtrees of views
/// whose class, id or label contains it.
func simulatorViews(pid: Int32, query: String, maxLines: Int = 400) throws -> String {
    let request: [String: Any] = [
        "DBGHierarchyRequestIdentifier": UUID().uuidString,
        "DBGHierarchyRequestInitiatorVersionKey": 4,
        "DBGHierarchyRequestPriority": 0,
        "DBGHierarchyRequestTransportCompression": false,
        "DBGHierarchyObjectDiscovery": 1,
        // visibility 1: public properties. propertyNamesAreExclusive true means all but these names (and some of the
        // others throw in KakaoTalk), so false: only these.
        "DBGHierarchyRequestActions": [[
            "actionClass": "DebugHierarchyPropertyAction", "visibility": 1, "propertyNamesAreExclusive": false,
            "propertyNames": ["frame", "hidden", "alpha", "accessibilityIdentifier", "accessibilityLabel", "text",
                              "firstItem", "firstAttribute", "relation", "secondItem", "secondAttribute", "multiplier",
                              "constant", "priority", "active", "identifier"],
        ]],
    ]
    let base64 = try JSONSerialization.data(withJSONObject: request).base64EncodedString()
    let folder = FileManager.default.temporaryDirectory.appendingPathComponent("mac-cu-views-\(UUID().uuidString)")
    try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
    defer { try? FileManager.default.removeItem(at: folder) }
    let answer = folder.appendingPathComponent("answer.json"), script = folder.appendingPathComponent("views.lldb")
    try """
        settings set target.preload-symbols false
        settings set symbols.load-on-demand true
        process attach --pid \(pid)
        thread select 1
        expr -l objc -- (void*)dlopen("/usr/lib/libViewDebuggerSupport.dylib", 2)
        expr -l objc -- (BOOL)[[[(id)NSClassFromString(@"DBGTargetHub") sharedHub] performRequestWithRequestInBase64:@"\(base64)"] writeToFile:@"\(answer.path)" atomically:YES]
        detach
        """.write(to: script, atomically: true, encoding: .utf8)
    let started = Date()
    let result = shell("/usr/bin/xcrun", ["lldb", "--batch", "-s", script.path], timeout: 180)
    let seconds = Int(Date().timeIntervalSince(started).rounded())
    guard let data = try? Data(contentsOf: answer),
          let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
          let groups = json["topLevelGroups"] as? [String: Any]
    else {
        let lines = result.output.split(separator: "\n").filter { $0.contains("error") || $0.contains("detached") }
        throw ToolError("lldb did not get the view hierarchy of pid \(pid) (\(seconds) s): \(lines.suffix(4).joined(separator: " | "))")
    }

    func value(_ object: [String: Any], _ name: String) -> Any? {
        (object["properties"] as? [[String: Any]])?.first { $0["propertyName"] as? String == name }?["propertyValue"]
    }
    func number(_ any: Any?) -> Double? { (any as? String).flatMap { Double($0) } }  // hex floats, "0x1.d2p+8"
    func short(_ n: Double) -> String { n == n.rounded() ? String(Int(n)) : String(format: "%.1f", n) }

    // Constraints by the address of their first item.
    var constraintsOf: [String: [String]] = [:]
    var names: [String: String] = [:]
    func collect(_ any: Any?) {
        if let list = any as? [Any] { list.forEach(collect); return }
        guard let object = any as? [String: Any] else { return }
        if let id = object["objectID"] as? String, let cls = object["className"] as? String { names[id] = cls }
        object.values.forEach { if $0 is [Any] || $0 is [String: Any] { collect($0) } }
    }
    collect(groups)
    for case let constraint as [String: Any] in ((groups["com.apple.UIKit.NSLayoutConstraint"] as? [String: Any])?["debugHierarchyObjects"] as? [Any] ?? []) {
        guard value(constraint, "active") as? String != "0", let first = value(constraint, "firstItem") as? [String: Any],
              let firstAddress = first["memoryAddress"] as? String else { continue }
        func attribute(_ key: String) -> String {
            let n = Int(value(constraint, key) as? String ?? "") ?? 0
            return layoutAttributes[safe: n].flatMap { $0.isEmpty ? nil : $0 } ?? "attribute(\(n))"
        }
        var line = "\(attribute("firstAttribute")) \(layoutRelations[Int(value(constraint, "relation") as? String ?? "0") ?? 0] ?? "?") "
        if let second = value(constraint, "secondItem") as? [String: Any], let address = second["memoryAddress"] as? String {
            let other = address == firstAddress ? "self" : "\((second["className"] as? String ?? "?").split(separator: ".").last ?? "")(\(address))"
            line += "\(other).\(attribute("secondAttribute"))"
            if let m = number(value(constraint, "multiplier")), m != 1 { line += " × \(short(m))" }
            if let c = number(value(constraint, "constant")), c != 0 { line += c > 0 ? " + \(short(c))" : " − \(short(-c))" }
        } else {
            line += short(number(value(constraint, "constant")) ?? 0)
        }
        if let p = number(value(constraint, "priority")), p != 1000 { line += " @\(short(p))" }
        if let id = value(constraint, "identifier") as? String, !id.isEmpty { line += " id=\(id)" }
        constraintsOf[firstAddress, default: []].append(line)
    }

    // The views, from the windows down.
    var lines: [String] = []
    let wanted = query.lowercased()
    func describe(_ view: [String: Any], depth: Int, inMatch: Bool) {
        let id = view["objectID"] as? String ?? "?", cls = view["className"] as? String ?? "?"
        let identifier = value(view, "accessibilityIdentifier") as? String ?? "", label = value(view, "accessibilityLabel") as? String ?? ""
        let matches = inMatch || wanted.isEmpty || [cls, identifier, label].contains { $0.lowercased().contains(wanted) }
        if matches {
            guard lines.count < maxLines else { return }
            var line = String(repeating: "  ", count: depth) + cls + " (\(id))"
            if let f = (value(view, "frame") as? [Any])?.compactMap(number), f.count == 4 {
                line += " \(short(f[0])),\(short(f[1])) \(short(f[2]))×\(short(f[3]))"
            }
            if value(view, "hidden") as? String == "1" { line += " hidden" }
            if let a = number(value(view, "alpha")), a < 1 { line += " alpha=\(short(a))" }
            if !identifier.isEmpty { line += " id=\(identifier)" }
            if !label.isEmpty { line += " \"\(label.prefix(60))\"" }
            if let text = value(view, "text") as? String, !text.isEmpty { line += " text=\"\(text.prefix(60))\"" }
            lines.append(line)
            for c in constraintsOf[id] ?? [] where lines.count < maxLines { lines.append(String(repeating: "  ", count: depth + 1) + "| " + c) }
        }
        let children = ((view["childGroup"] as? [String: Any])?["debugHierarchyObjects"] as? [Any]) ?? []
        for case let child as [String: Any] in children { describe(child, depth: matches ? depth + 1 : depth, inMatch: matches && !wanted.isEmpty) }
    }
    for case let window as [String: Any] in ((groups["com.apple.UIKit.UIWindow"] as? [String: Any])?["debugHierarchyObjects"] as? [Any] ?? []) {
        describe(window, depth: 0, inMatch: false)
    }
    let header = """
        Views of pid \(pid) (\(names.count) objects; the app was stopped for \(seconds) s while lldb read them). \
        Each line: class (address) x,y width×height in its superview, then hidden, alpha, id, label, text. \
        Lines with | are the view's active constraints (first item is the view; self is the view).
        """
    if lines.isEmpty { return header + "\n" + (wanted.isEmpty ? "No window." : "No view matches \"\(query)\".") }
    return header + "\n" + lines.joined(separator: "\n") + (lines.count >= maxLines ? "\n… more views: use query to narrow." : "")
}

private extension Array {
    subscript(safe index: Int) -> Element? { indices.contains(index) ? self[index] : nil }
}
