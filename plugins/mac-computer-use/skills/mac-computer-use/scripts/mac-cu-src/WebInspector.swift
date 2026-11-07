// The webinspector tool: the Web Inspector of WKWebView pages in iOS Simulator and USB device apps, without
// Safari. It lists the pages, runs JavaScript, and shows console, network, cookies and a picture of a page.
// Each call connects again (see Discovery.connect for the wait on a simulator). Ported from the iwi CLI.

import AppKit

let sensitiveHeaders: Set<String> = ["ka-tgt", "authorization", "proxy-authorization", "cbt-token", "x-ka-auth", "set-cookie"]

/// Only the length of a token header, and only the names of a Cookie header.
func redactHeader(_ name: String, _ value: Any) -> String {
    let v = "\(value)"
    let n = name.lowercased()
    if n == "cookie" {
        return "<" + v.split(separator: ";").map { $0.split(separator: "=").first?.trimmingCharacters(in: .whitespaces) ?? "" }.joined(separator: ", ") + ">"
    }
    return sensitiveHeaders.contains(n) ? "<\(v.count) characters hidden>" : v
}

func redactURL(_ url: Any?) -> String {
    "\(url ?? "")".replacing(#/(?i)([?&](?:token|tgt|ka_tgt|access_token|refresh_token|code|ticket)=)[^&#]+/#) { "\($0.1)<hidden>" }
}

func pageLabel(_ c: Candidate) -> String {
    "\(c.ref)  \(c.page.type.replacingOccurrences(of: "WIRType", with: ""))  \"\(c.page.title)\"  \(redactURL(c.page.url))"
}

func webInspectorEndpoints(device: String?) -> [Endpoint] {
    (Discovery.simulators() + Discovery.devices()).filter { ep in
        guard let d = device, ep.kind == "simulator" else { return true }   // A device has its name only after the connection.
        return ep.id.lowercased().contains(d) || ep.name.lowercased().contains(d)
    }
}

func webInspectorList(_ conns: [Connection]) -> String {
    if conns.isEmpty { return "No simulator or device to inspect: boot a simulator, or connect a trusted device with USB." }
    var lines: [String] = []
    for c in conns {
        lines.append("[\(c.kind)] \(c.name) \(c.version.isEmpty ? "" : "(iOS \(c.version)) ")\(c.id)")
        if let e = c.error { lines.append("  error: \(e)"); continue }
        let shown = c.apps.filter { !($0.pages ?? []).isEmpty }
        if shown.isEmpty { lines.append("  (no page to inspect)") }
        for a in shown {
            lines.append("  \(a.name) \(a.bundleID) \(a.id)\(a.isActive ? "" : "  [background: its pages can stop answering]")")
            for p in a.pages ?? [] {
                lines.append("    \(pageLabel(Candidate(conn: c, app: a, page: p)))\(p.inUse ? "  [another inspector uses it]" : "")")
            }
        }
    }
    return lines.joined(separator: "\n")
}

/// Opens a session to the one page that the arguments select, runs body, and closes all connections.
func withWebPage<T>(_ arguments: [String: Any], _ body: (PageSession, Candidate) throws -> T) throws -> T {
    let device = (arguments["device"] as? String)?.lowercased()
    let app = (arguments["app"] as? String)?.lowercased()
    let page = arguments["page"] as? String
    let conns = Discovery.connect(webInspectorEndpoints(device: device))
    defer { conns.forEach { $0.client?.close() } }
    var c = conns.candidates
    if let d = device { c = c.filter { $0.conn.id.lowercased().contains(d) || $0.conn.name.lowercased().contains(d) } }
    if let a = app { c = c.filter { [$0.app.name, $0.app.bundleID, $0.app.id].contains { $0.lowercased().contains(a) } } }
    if let p = page {
        let exact = c.filter { $0.ref == p }
        c = exact.isEmpty ? c.filter { $0.page.title.localizedCaseInsensitiveContains(p) || $0.page.url.localizedCaseInsensitiveContains(p) } : exact
    }
    guard let pick = c.first else {
        let errors = conns.compactMap { $0.error }
        throw ToolError("No page matches. \(errors.isEmpty ? "Use the list action to see the pages." : "Connection errors: " + errors.joined(separator: "; "))")
    }
    guard c.count == 1 else {
        throw ToolError("\(c.count) pages match. Give one ref from this list in page:\n" + c.map { "  " + pageLabel($0) }.joined(separator: "\n"))
    }
    try approve(pick.app.name, bundleID: pick.app.bundleID.isEmpty ? nil : pick.app.bundleID)
    let session = PageSession(client: pick.conn.client!, appID: pick.app.id, pageID: pick.page.id)
    session.open()
    defer {
        session.close()
        Thread.sleep(forTimeInterval: 0.1)   // Time to send forwardDidClose.
    }
    return try body(session, pick)
}

func evaluate(_ s: PageSession, _ expression: String, byValue: Bool = true, timeout: TimeInterval?) throws -> [String: Any] {
    try s.command("Runtime.evaluate", ["expression": expression, "returnByValue": byValue, "includeCommandLineAPI": true], timeout: timeout)
}

/// The value of a Runtime.evaluate result: a string as it is, other values as JSON.
func evaluationText(_ r: [String: Any]) throws -> String {
    let res = r["result"] as? [String: Any] ?? [:]
    if r["wasThrown"] as? Bool == true { throw ToolError("The JavaScript threw: \(res["description"] ?? res["value"] ?? "")") }
    if let v = res["value"] { return json(v) }
    if res["type"] as? String == "undefined" { return "undefined" }
    return "\(res["description"] ?? json(res))"
}

/// Enables the domain, collects the lines that format makes from its events for `seconds`, and returns them.
func collectEvents(_ s: PageSession, domain: String, _ arguments: [String: Any], timeout: TimeInterval?,
                   format: @escaping (String, [String: Any]) -> String?) throws -> [String] {
    let lock = NSLock()
    var lines: [String] = []
    s.onEvent = { method, params in
        guard let line = format(method, params) else { return }
        lock.lock(); lines.append(line); lock.unlock()
    }
    let noCache = arguments["no_cache"] as? Bool ?? false
    try s.command("\(domain).enable", timeout: timeout)
    if noCache {
        if domain != "Network" { try s.command("Network.enable", timeout: timeout) }
        try s.command("Network.setResourceCachingDisabled", ["disabled": true], timeout: timeout)
    }
    if let url = arguments["url"] as? String { _ = try evaluate(s, "window.location.href = \(jsString(url))", timeout: timeout) }
    else if arguments["reload"] as? Bool == true { try s.command("Page.reload", timeout: timeout) }
    Thread.sleep(forTimeInterval: min(max((arguments["seconds"] as? NSNumber)?.doubleValue ?? 5, 0.5), 60))
    if noCache { _ = try? s.command("Network.setResourceCachingDisabled", ["disabled": false], timeout: 3) }
    s.onEvent = nil
    lock.lock(); defer { lock.unlock() }
    return lines
}

func webInspectorTool(_ arguments: [String: Any]) throws -> [String: Any] {
    let action = arguments["action"] as? String ?? ""
    func text(_ value: String) -> [String: Any] {
        let limit = 40_000
        return ["content": [["type": "text", "text": value.count > limit ? String(value.prefix(limit)) + "\n… (\(value.count - limit) more characters)" : value]]]
    }
    let timeout = (arguments["timeout"] as? NSNumber)?.doubleValue
    switch action {
    case "list":
        let conns = Discovery.connect(webInspectorEndpoints(device: (arguments["device"] as? String)?.lowercased()))
        defer { conns.forEach { $0.client?.close() } }
        return text(webInspectorList(conns))

    case "eval":
        guard let code = arguments["code"] as? String, !code.isEmpty else { throw ToolError("eval needs code.") }
        return text(try withWebPage(arguments) { s, _ in
            var r = try evaluate(s, code, byValue: arguments["await"] as? Bool != true, timeout: timeout)
            if arguments["await"] as? Bool == true, let res = r["result"] as? [String: Any], res["className"] as? String == "Promise",
               let oid = res["objectId"] as? String {
                r = try s.command("Runtime.awaitPromise", ["promiseObjectId": oid, "returnByValue": true], timeout: max(timeout ?? 60, 60))
            }
            return try evaluationText(r)
        })

    case "navigate":
        guard let url = arguments["url"] as? String, !url.isEmpty else { throw ToolError("navigate needs url.") }
        return text(try withWebPage(arguments) { s, c in
            _ = try evaluate(s, "window.location.href = \(jsString(url))", timeout: timeout)
            return "Went from \(redactURL(c.page.url)) to \(redactURL(url))."
        })

    case "reload":
        return text(try withWebPage(arguments) { s, c in
            try s.command("Page.reload", timeout: timeout)
            return "Reloaded \(redactURL(c.page.url))."
        })

    case "screenshot":
        return try withWebPage(arguments) { s, c in
            let dims = (try evaluate(s, "[innerWidth, innerHeight]", timeout: timeout)["result"] as? [String: Any])?["value"] as? [Double] ?? [0, 0]
            let r = try s.command("Page.snapshotRect", ["x": 0, "y": 0, "width": dims[0], "height": dims[1], "coordinateSystem": "Viewport"], timeout: timeout)
            guard let url = r["dataURL"] as? String, let comma = url.firstIndex(of: ","),
                  let data = Data(base64Encoded: String(url[url.index(after: comma)...])),
                  let image = NSImage(data: data)?.cgImage(forProposedRect: nil, context: nil, hints: nil), dims[0] > 0, dims[1] > 0
            else { throw ToolError("The page gave no picture.") }
            return ["content": [
                ["type": "text", "text": "Viewport of \"\(c.page.title)\": \(Int(dims[0]))×\(Int(dims[1])) CSS pixels, one pixel of the picture each."],
                ["type": "image", "data": try jpegBase64(image, size: CGSize(width: dims[0], height: dims[1])), "mimeType": "image/jpeg"],
            ]]
        }

    case "console":
        return text(try withWebPage(arguments) { s, _ in
            let lines = try collectEvents(s, domain: "Console", arguments, timeout: timeout) { method, p in
                guard method == "Console.messageAdded", let m = p["message"] as? [String: Any] else { return nil }
                let place = (m["url"] as? String).map { "  (\(redactURL($0)):\(m["line"] ?? 0))" } ?? ""
                return "[\(m["level"] ?? "log")] \(m["text"] ?? "")\(place)"
            }
            return lines.isEmpty ? "(no console message)" : lines.joined(separator: "\n")
        })

    case "network":
        let wantHeaders = arguments["headers"] as? Bool ?? false
        let wantBodies = arguments["bodies"] as? Bool ?? false
        return text(try withWebPage(arguments) { s, _ in
            let lock = NSLock()
            var urls: [String: String] = [:]
            var bodyIDs: [String] = []
            func headers(_ mark: String, _ h: Any?) -> String {
                guard wantHeaders, let h = h as? [String: Any] else { return "" }
                return h.keys.sorted().map { "\n    \(mark) \($0): \(redactHeader($0, h[$0]!))" }.joined()
            }
            var lines = try collectEvents(s, domain: "Network", arguments, timeout: timeout) { method, p in
                let rid = p["requestId"] as? String ?? ""
                switch method {
                case "Network.requestWillBeSent":
                    let r = p["request"] as? [String: Any] ?? [:]
                    var out = ""
                    if let rr = p["redirectResponse"] as? [String: Any] {
                        let location = (rr["headers"] as? [String: Any])?.first { $0.key.lowercased() == "location" }?.value
                        out = "↪ \(rr["status"] ?? "") \(redactURL(rr["url"])) → \(redactURL(location))\(headers("<", rr["headers"]))\n"
                    }
                    lock.lock(); urls[rid] = r["url"] as? String ?? ""; lock.unlock()
                    let tgt = (r["headers"] as? [String: Any])?.keys.contains { $0.lowercased() == "ka-tgt" } == true
                    return out + "→ \(r["method"] ?? "") \(redactURL(r["url"])) [\(p["type"] ?? "")]\(tgt ? " +KA-TGT" : "")\(headers(">", r["headers"]))"
                case "Network.responseReceived":
                    let r = p["response"] as? [String: Any] ?? [:]
                    if wantBodies, ["XHR", "Fetch"].contains(p["type"] as? String ?? "") { lock.lock(); bodyIDs.append(rid); lock.unlock() }
                    return "← \(r["status"] ?? "") \(redactURL(r["url"])) [\(r["mimeType"] ?? ""), \(r["source"] ?? "?")]\(headers("<", r["headers"]))"
                case "Network.loadingFailed":
                    lock.lock(); let u = urls[rid] ?? rid; lock.unlock()
                    return "✗ \(p["errorText"] ?? "") \(redactURL(u))"
                default: return nil
                }
            }
            lock.lock(); let ids = bodyIDs; let known = urls; lock.unlock()
            for id in ids {
                guard let r = try? s.command("Network.getResponseBody", ["requestId": id], timeout: 5), let body = r["body"] as? String else { continue }
                let shown = r["base64Encoded"] as? Bool == true ? "<base64, \(body.count) characters>" : String(body.prefix(500)).replacingOccurrences(of: "\n", with: " ")
                lines.append("body \(redactURL(known[id] ?? id))\n    \(shown)")
            }
            return lines.isEmpty ? "(no request)" : lines.joined(separator: "\n")
        })

    case "cookies":
        let filter = (arguments["name"] as? String)?.lowercased()
        let wantValues = arguments["values"] as? Bool ?? false
        return text(try withWebPage(arguments) { s, _ in
            let all = try s.command("Page.getCookies", timeout: timeout)["cookies"] as? [[String: Any]] ?? []
            let list = all.filter { c in filter.map { (c["name"] as? String ?? "").lowercased().contains($0) } ?? true }
                .sorted { "\($0["domain"] ?? "") \($0["name"] ?? "")" < "\($1["domain"] ?? "") \($1["name"] ?? "")" }
            let format = DateFormatter()
            format.dateFormat = "yyyy-MM-dd HH:mm:ss"
            let lines = list.map { c -> String in
                let flags = [c["httpOnly"] as? Bool == true ? "HttpOnly" : nil, c["secure"] as? Bool == true ? "Secure" : nil,
                             (c["sameSite"] as? String).flatMap { $0 == "None" ? nil : "SameSite=\($0)" }].compactMap { $0 }
                // WebKit gives expires in milliseconds.
                let expires = c["session"] as? Bool == true ? "session" : (c["expires"] as? Double).map { format.string(from: Date(timeIntervalSince1970: $0 / 1000)) } ?? "?"
                let value = c["value"] as? String ?? ""
                return "\(c["name"] ?? "")  \(c["domain"] ?? "")\(c["path"] ?? "")  \(flags.isEmpty ? "-" : flags.joined(separator: ","))  expires=\(expires)  value=\(wantValues ? value : "<\(value.count) characters>")"
            }
            return lines.isEmpty ? "(no cookie)" : lines.joined(separator: "\n")
        })

    case "watch":
        guard let domain = arguments["domain"] as? String, !domain.isEmpty else { throw ToolError("watch needs domain, for example \"DOM\" or \"Page\".") }
        return text(try withWebPage(arguments) { s, _ in
            let lines = try collectEvents(s, domain: domain, arguments, timeout: timeout) { method, p in
                String(decoding: (try? JSONSerialization.data(withJSONObject: ["method": method, "params": p], options: [.withoutEscapingSlashes])) ?? Data(), as: UTF8.self)
            }
            return lines.isEmpty ? "(no \(domain) event)" : lines.joined(separator: "\n")
        })

    case "send":
        guard let method = arguments["method"] as? String, !method.isEmpty else { throw ToolError("send needs method, for example \"DOM.getDocument\".") }
        let params = arguments["params"] as? [String: Any] ?? [:]
        return text(try withWebPage(arguments) { s, _ in json(try s.command(method, params, timeout: timeout)) })

    default:
        throw ToolError("Unknown webinspector action \"\(action)\".")
    }
}
