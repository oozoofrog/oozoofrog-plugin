// The browser tool: web pages through JavaScript in the page.
//
// Three engines:
//   apple_events  The user's own browser (Chrome and other Chromium browsers, Safari), with its
//                 logins. Sends Apple Events; the browser needs "Allow JavaScript from Apple Events".
//   devtools      A separate Chrome with its own profile, through the Chrome DevTools Protocol
//                 (DevTools.swift). Adds network records, response bodies, console, all cookies,
//                 page screenshots and JavaScript with await.
//   extension     The user's own Chrome with its logins, through the mac-cu Chrome extension
//                 (ChromeExtension.swift): the Chrome DevTools Protocol on the user's tab, as devtools.
// The two engines with the protocol click, fill and press keys with real input events.

import AppKit

protocol BrowserEngine: AnyObject {
    /// The app name and process for the state header (focus.py) and window screenshots.
    var appName: String { get }
    var pid: pid_t? { get }
    func tabs() throws -> String
    func open(_ url: String) throws
    func navigate(_ url: String) throws
    func selectTab(_ tab: String) throws
    func closeTab(_ tab: String) throws
    /// back, forward or reload.
    func history(_ step: String) throws
    /// Run a JavaScript expression in the current tab and return its value (JSON types).
    func evaluate(_ expression: String) throws -> Any?
    func screenshot() throws -> String?
    func network(filter: String?, limit: Int) throws -> String
    func responseBody(_ requestID: String) throws -> String
    func console(limit: Int) throws -> String
    func cookies() throws -> String
    func quit() throws
}

func onlyDevTools(_ what: String) -> ToolError {
    ToolError("\(what) needs \"engine\": \"extension\" (the user's Chrome) or \"devtools\" (a separate Chrome that mac-cu starts).")
}

// MARK: - The Chrome DevTools Protocol (devtools and extension engines)

protocol CDPEngine: BrowserEngine {
    /// Sends a protocol command to the current tab and returns its result.
    func cdp(_ method: String, _ params: [String: Any]) throws -> [String: Any]
}

extension CDPEngine {
    func evaluate(_ expression: String) throws -> Any? {
        let result = try cdp("Runtime.evaluate", ["expression": expression, "returnByValue": true, "awaitPromise": true,
                                                  "replMode": true, "userGesture": true])
        if let details = result["exceptionDetails"] as? [String: Any] {
            let exception = details["exception"] as? [String: Any]
            throw ToolError("JavaScript error: \(exception?["description"] ?? details["text"] ?? "")")
        }
        return (result["result"] as? [String: Any])?["value"]
    }

    func screenshot() throws -> String? {
        try cdp("Page.captureScreenshot", ["format": "jpeg", "quality": 70])["data"] as? String
    }

    func responseBody(_ requestID: String) throws -> String {
        let result = try cdp("Network.getResponseBody", ["requestId": requestID])
        let body = result["body"] as? String ?? ""
        if result["base64Encoded"] as? Bool == true { return "Binary body, \(body.count * 3 / 4) bytes." }
        return body.count > 20_000 ? String(body.prefix(20_000)) + "\n… (first 20000 of \(body.count) characters)" : body
    }

    func cookies() throws -> String {
        let cookies = try cdp("Network.getCookies", [:])["cookies"] as? [[String: Any]] ?? []
        let lines = cookies.map { c -> String in
            let value = "\(c["value"] ?? "")"
            let flags = [c["httpOnly"] as? Bool == true ? "HttpOnly" : nil, c["secure"] as? Bool == true ? "Secure" : nil]
                .compactMap { $0 }.joined(separator: " ")
            return "\(c["name"] ?? "")=\(value.count > 60 ? value.prefix(60) + "…" : value) domain=\(c["domain"] ?? "") \(flags)"
        }
        return "Cookies of this tab:\n" + (lines.isEmpty ? "none" : lines.joined(separator: "\n"))
    }

    /// A real mouse click at the middle of the element, as a user's click (the page sees isTrusted). A tab
    /// that is not shown can take no mouse events (in the test, after it loaded in the background): there
    /// the element is clicked by script.
    func click(_ index: Int) throws -> String {
        let target = try evaluate(elementScript(index, """
            if (document.visibilityState === 'hidden') { el.focus(); el.click(); return 'hidden'; }
            const r = el.getBoundingClientRect(); const x = r.left + r.width / 2, y = r.top + r.height / 2;
            const hit = document.elementFromPoint(x, y);
            const covered = hit && hit !== el && !el.contains(hit) && !hit.contains(el);
            return {x, y, covered: covered ? hit.tagName.toLowerCase() + ' "' +
              (hit.getAttribute('aria-label') || hit.innerText || '').replace(/\\s+/g, ' ').trim().slice(0, 40) + '"' : null};
            """))
        guard let point = target as? [String: Any], let x = (point["x"] as? NSNumber)?.doubleValue,
              let y = (point["y"] as? NSNumber)?.doubleValue else {
            return target as? String == "hidden" ? "clicked by script: the tab is not shown, so it takes no mouse events" : json(target)
        }
        _ = try cdp("Input.dispatchMouseEvent", ["type": "mouseMoved", "x": x, "y": y])
        for type in ["mousePressed", "mouseReleased"] {
            _ = try cdp("Input.dispatchMouseEvent", ["type": type, "x": x, "y": y, "button": "left", "clickCount": 1])
        }
        let covered = (point["covered"] as? String).map { "; the point shows \($0) in front of the element" } ?? ""
        return "clicked at (\(Int(x)), \(Int(y)))\(covered)"
    }

    /// Selects the text of the element and types the new text as real input. A select element, or an
    /// empty text, is set by script (fillScript).
    func fill(_ index: Int, _ text: String) throws -> String {
        let focused = try evaluate(elementScript(index, """
            if (el.tagName === 'SELECT' || \(text.isEmpty)) return 'script';
            el.focus();
            if (el.isContentEditable) getSelection().selectAllChildren(el); else if (el.select) el.select();
            return 'focused';
            """))
        switch focused as? String {
        case "focused":
            _ = try cdp("Input.insertText", ["text": text])
            return "filled"
        case "script": return json(try evaluate(fillScript(index, text)))
        default: return json(focused)
        }
    }

    /// A key or combination as real key events, for example "Enter", "shift+Tab", "cmd+a".
    func press(_ combination: String) throws -> String {
        var parts = combination.components(separatedBy: "+")
        if combination.hasSuffix("+") { parts = parts.dropLast(2) + ["+"] }  // "+" or "cmd++": the key is "+".
        let name = parts.removeLast()
        var modifiers = 0
        for modifier in parts where !modifier.isEmpty {
            switch modifier.lowercased() {
            case "alt", "option": modifiers |= 1
            case "ctrl", "control": modifiers |= 2
            case "cmd", "command", "meta": modifiers |= 4
            case "shift": modifiers |= 8
            default: throw ToolError("Unknown modifier \"\(modifier)\" in \"\(combination)\". Use cmd, ctrl, alt or shift.")
            }
        }
        let lower = name.lowercased().replacingOccurrences(of: "arrow", with: "")
        var event: [String: Any] = ["modifiers": modifiers]
        if let (key, code, keyCode, text) = cdpKeys[lower] {
            event.merge(["key": key, "code": code, "windowsVirtualKeyCode": keyCode], uniquingKeysWith: { $1 })
            if let text { event["text"] = text }
        } else if name.count == 1 {
            let key = modifiers & 8 != 0 ? name.uppercased() : name
            let upper = name.uppercased()
            event.merge(["key": key, "windowsVirtualKeyCode": Int(upper.unicodeScalars.first!.value)], uniquingKeysWith: { $1 })
            if let letter = upper.first, letter.isLetter, letter.isASCII { event["code"] = "Key\(upper)" }
            if let digit = name.first, digit.isNumber, digit.isASCII { event["code"] = "Digit\(name)" }
            if modifiers & 6 == 0 { event["text"] = key }  // With ctrl or cmd the key types nothing.
        } else {
            throw ToolError("Unknown key \"\(name)\". Use Enter, Tab, Escape, Backspace, Delete, Space, ArrowUp/Down/Left/Right, PageUp, PageDown, Home, End, or one character.")
        }
        // On macOS, Chrome runs editing shortcuts such as cmd+a only as commands.
        if modifiers & 4 != 0, let command = cdpEditCommands[lower] { event["commands"] = [command] }
        var down = event
        down["type"] = event["text"] == nil ? "rawKeyDown" : "keyDown"
        _ = try cdp("Input.dispatchKeyEvent", down)
        event["type"] = "keyUp"
        event["text"] = nil
        _ = try cdp("Input.dispatchKeyEvent", event)
        return "pressed \(combination)"
    }
}

/// Key name (lowercased, without "arrow") → key, code, Windows key code, text.
let cdpKeys: [String: (String, String, Int, String?)] = [
    "enter": ("Enter", "Enter", 13, "\r"), "return": ("Enter", "Enter", 13, "\r"), "tab": ("Tab", "Tab", 9, nil),
    "escape": ("Escape", "Escape", 27, nil), "esc": ("Escape", "Escape", 27, nil),
    "backspace": ("Backspace", "Backspace", 8, nil), "delete": ("Delete", "Delete", 46, nil), "space": (" ", "Space", 32, " "),
    "up": ("ArrowUp", "ArrowUp", 38, nil), "down": ("ArrowDown", "ArrowDown", 40, nil),
    "left": ("ArrowLeft", "ArrowLeft", 37, nil), "right": ("ArrowRight", "ArrowRight", 39, nil),
    "pageup": ("PageUp", "PageUp", 33, nil), "pagedown": ("PageDown", "PageDown", 34, nil),
    "home": ("Home", "Home", 36, nil), "end": ("End", "End", 35, nil),
]
let cdpEditCommands = ["a": "selectAll", "c": "copy", "x": "cut", "v": "paste", "z": "undo"]

/// The request records of the devtools and extension engines as lines (request id first).
func requestLines(_ rows: [(id: String, record: [String: Any])], filter: String?, limit: Int) -> String {
    let lines = rows.filter { filter == nil || "\($0.record["url"] ?? "")".localizedCaseInsensitiveContains(filter!) }
        .suffix(limit)
        .map { id, r in
            "\(id) \(r["method"] ?? "") \(r["status"] ?? (r["failed"] != nil ? "failed: \(r["failed"]!)" : "pending")) " +
                "\(r["type"] ?? "") \(r["url"] ?? "")\(r["mime"].map { " (\($0))" } ?? "")"
        }
    return "Requests since mac-cu connected to this tab (request id first; use it with response_body):\n" +
        (lines.isEmpty ? "none" : lines.joined(separator: "\n"))
}

// MARK: - JavaScript run in the page

/// Records console messages from the moment it first runs in a page (apple_events engine).
let consoleHook = """
    if (!window.__mcuLog) { window.__mcuLog = [];
      for (const k of ['log', 'info', 'warn', 'error']) { const o = console[k];
        console[k] = function (...a) { try { window.__mcuLog.push(k + ': ' + a.map(x => typeof x === 'string' ? x : JSON.stringify(x)).join(' '));
          if (window.__mcuLog.length > 300) window.__mcuLog.shift(); } catch (e) {} return o.apply(this, a); }; }
      addEventListener('error', e => window.__mcuLog.push('exception: ' + e.message)); }
    """

/// Numbers the visible interactive elements (attribute data-mcu) and returns them with the page text.
/// With mark false it sets no numbers, so that the numbers the agent saw stay valid.
func pageScript(textLimit: Int, mark: Bool = true) -> String {
    """
    (() => { const mark = \(mark);
      const sel = 'a[href],button,input,select,textarea,summary,[role=button],[role=link],[role=checkbox],[role=radio],' +
        '[role=tab],[role=menuitem],[role=option],[role=switch],[role=textbox],[contenteditable=""],[contenteditable=true],[onclick]';
      if (mark) document.querySelectorAll('[data-mcu]').forEach(e => e.removeAttribute('data-mcu'));
      const out = []; let n = 0;
      for (const el of document.querySelectorAll(sel)) {
        const r = el.getBoundingClientRect(); const st = getComputedStyle(el);
        if (r.width === 0 || r.height === 0 || st.visibility === 'hidden' || st.display === 'none') continue;
        if (n >= 500) break;
        if (mark) el.setAttribute('data-mcu', n);
        // The text of a field goes in value= (never the text of a password field), apart from its label.
        const field = el.matches('textarea,select') || (el.tagName === 'INPUT' && !/^(submit|button|reset|image|checkbox|radio)$/.test(el.type));
        const clean = s => String(s || '').replace(/\\s+/g, ' ').trim().slice(0, 80);
        const label = clean(el.getAttribute('aria-label') || (field ? '' : el.innerText || el.value) || el.title || el.alt);
        const value = el.tagName === 'SELECT' ? el.selectedOptions[0]?.text : el.value;
        let line = n + ' ' + el.tagName.toLowerCase();
        if (el.type && el.tagName !== 'BUTTON') line += '[' + el.type + ']';
        if (el.getAttribute('role')) line += ' role=' + el.getAttribute('role');
        if (label) line += ' "' + label + '"';
        if (field && value) line += el.type === 'password' ? ' value=(hidden)' : ' value="' + clean(value) + '"';
        if (el.placeholder) line += ' placeholder="' + clean(el.placeholder) + '"';
        if (el.href) line += ' href=' + String(el.href).slice(0, 120);
        if (el.checked) line += ' checked';
        if (el.disabled) line += ' disabled';
        if (r.bottom < 0 || r.top > innerHeight) line += ' offscreen';
        out.push(line); n++;
      }
      const text = (document.body ? document.body.innerText : '').replace(/\\n{3,}/g, '\\n\\n');
      return {title: document.title, url: location.href, ready: document.readyState, elements: out,
              text: text.slice(0, \(textLimit)), textLength: text.length};
    })()
    """
}

func jsString(_ text: String) -> String {
    let data = try! JSONSerialization.data(withJSONObject: [text], options: [.fragmentsAllowed])
    return String(String(data: data, encoding: .utf8)!.dropFirst().dropLast())
}

func elementScript(_ index: Int, _ body: String) -> String {
    """
    (() => { const el = document.querySelector('[data-mcu="\(index)"]');
      if (!el) return 'No element \(index). Read the page again with the page action.';
      el.scrollIntoView({block: 'center', behavior: 'instant'}); \(body) })()
    """
}

func clickScript(_ index: Int) -> String {
    elementScript(index, "el.focus(); el.click(); return 'clicked';")
}

/// Sets the value as typing does, so that frameworks such as React see the change.
func fillScript(_ index: Int, _ text: String) -> String {
    elementScript(index, """
        el.focus(); const v = \(jsString(text));
        if (el.isContentEditable) { el.textContent = v; }
        else { const d = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(el), 'value');
          if (d && d.set) d.set.call(el, v); else el.value = v; }
        el.dispatchEvent(new Event('input', {bubbles: true})); el.dispatchEvent(new Event('change', {bubbles: true}));
        return 'filled';
        """)
}

func json(_ value: Any?) -> String {
    guard let value, !(value is NSNull) else { return "null" }
    if let text = value as? String { return text }
    guard let data = try? JSONSerialization.data(withJSONObject: value, options: [.fragmentsAllowed, .prettyPrinted, .withoutEscapingSlashes]),
          let text = String(data: data, encoding: .utf8) else { return "\(value)" }
    return text
}

/// Wait until the page has loaded (and has the selector, when one is given).
func waitForPage(_ engine: BrowserEngine, selector: String?, seconds: Double) throws -> String {
    let check = selector.map { "document.readyState === 'complete' && !!document.querySelector(\(jsString($0)))" }
        ?? "document.readyState === 'complete'"
    let end = Date().addingTimeInterval(min(max(seconds, 0.5), 30))
    usleep(300_000)  // A navigation that just started still shows the old page.
    while Date() < end {
        do {
            if try engine.evaluate(check) as? Bool == true { return "ready" }
        } catch let error as ToolError where error.message.contains("does not allow JavaScript") {
            return "done; mac-cu cannot check the page because \(engine.appName) does not allow JavaScript from Apple Events"
        } catch {}  // While a page loads, the old page can be gone.
        usleep(250_000)
    }
    throw ToolError("The page was not ready after \(Int(seconds)) seconds" + (selector.map { " (selector \($0))" } ?? "") + ".")
}

// MARK: - apple_events engine

final class AppleEventsBrowser: BrowserEngine {
    let appName: String
    let bundleID: String
    let safari: Bool
    var pid: pid_t? { NSRunningApplication.runningApplications(withBundleIdentifier: bundleID).first?.processIdentifier }

    init(name: String) throws {
        let browser = try session(for: name)  // Approval, and opens the browser in the background.
        guard let bundleID = browser.app.bundleIdentifier else { throw ToolError("\(name) has no bundle ID.") }
        if bundleID.hasPrefix("org.mozilla.") {
            throw ToolError("Firefox cannot run JavaScript through Apple Events. Use \"engine\": \"devtools\", or get_app_state and act.")
        }
        appName = browser.name
        self.bundleID = bundleID
        safari = bundleID.hasPrefix("com.apple.Safari")
    }

    func script(_ body: String) throws -> String {
        let source = "tell application id \"\(bundleID)\"\n\(body)\nend tell"
        var output: String?
        var failure: (String, Int)?
        DispatchQueue.main.sync {
            var error: NSDictionary?
            let result = NSAppleScript(source: source)?.executeAndReturnError(&error)
            if let error {
                failure = (error[NSAppleScript.errorMessage] as? String ?? "\(error)", error[NSAppleScript.errorNumber] as? Int ?? 0)
            } else {
                output = result?.stringValue ?? ""
            }
        }
        if let (message, number) = failure {
            if number == -1743 {
                throw ToolError("""
                    macOS did not allow Apple Events to \(appName). In System Settings > Privacy & Security > Automation, \
                    the user turns on \(appName) under mac-cu.
                    """)
            }
            if message.contains("JavaScript") || number == 12 {
                throw ToolError("""
                    \(appName) does not allow JavaScript from Apple Events. The user turns it on: \
                    \(safari ? "Safari > Settings > Advanced > Show features for web developers, then Develop > Allow JavaScript from Apple Events" : "View > Developer > Allow JavaScript from Apple Events"). \
                    Ask the user first; it is a browser setting. Or use "engine": "devtools". (\(message))
                    """)
            }
            throw ToolError("\(appName): \(message) (\(number))")
        }
        return output ?? ""
    }

    func quoted(_ text: String) -> String {
        "\"" + text.replacingOccurrences(of: "\\", with: "\\\\").replacingOccurrences(of: "\"", with: "\\\"") + "\""
    }

    func windowAndTab(_ tab: String) throws -> (Int, Int) {
        let parts = tab.split(separator: ".").compactMap { Int($0) }
        guard parts.count == 2 else { throw ToolError("tab is \"window.tab\" from the tabs action, for example \"1.2\".") }
        return (parts[0], parts[1])
    }

    var currentTab: String { safari ? "current tab of front window" : "active tab of front window" }

    func tabs() throws -> String {
        let active = safari ? "index of current tab of window w" : "active tab index of window w"
        let title = safari ? "name" : "title"
        let raw = try script("""
            set out to ""
            repeat with w from 1 to count of windows
              try
                set a to \(active)
                repeat with t from 1 to count of tabs of window w
                  set out to out & (w as text) & "." & (t as text) & tab & ((t = a) as text) & tab & (\(title) of tab t of window w) & tab & (URL of tab t of window w) & linefeed
                end repeat
              end try
            end repeat
            out
            """)
        let lines = raw.split(separator: "\n").map { line -> String in
            let f = line.split(separator: "\t", omittingEmptySubsequences: false).map(String.init)
            guard f.count >= 4 else { return String(line) }
            return "\(f[0])\(f[1] == "true" ? " *" : "") \(f[2]) — \(f[3])"
        }
        return lines.isEmpty ? "No open tabs." : "Tabs (window.tab, * = shown in its window; window 1 is the front window):\n" + lines.joined(separator: "\n")
    }

    func open(_ url: String) throws {
        _ = try script(safari ? """
            if (count of documents) = 0 then make new document
            tell front window to set current tab to (make new tab with properties {URL:\(quoted(url))})
            """ : """
            if (count of windows) = 0 then make new window
            tell front window to make new tab with properties {URL:\(quoted(url))}
            """)
    }

    func navigate(_ url: String) throws {
        _ = try script("set URL of \(currentTab) to \(quoted(url))")
    }

    func selectTab(_ tab: String) throws {
        let (w, t) = try windowAndTab(tab)
        _ = try script((safari ? "set current tab of window \(w) to tab \(t) of window \(w)" : "set active tab index of window \(w) to \(t)")
                       + "\nset index of window \(w) to 1")
    }

    func closeTab(_ tab: String) throws {
        let (w, t) = try windowAndTab(tab)
        _ = try script("close tab \(t) of window \(w)")
    }

    func history(_ step: String) throws {
        if safari {
            _ = try evaluate(step == "reload" ? "location.reload()" : "history.\(step)()")
        } else {
            _ = try script("tell \(currentTab) to \(step == "back" ? "go back" : step == "forward" ? "go forward" : "reload")")
        }
    }

    /// Apple Events return text, so the value goes back as JSON. A promise is not awaited.
    func evaluate(_ expression: String) throws -> Any? {
        let wrapped = """
            (() => { \(consoleHook)
              try { const v = eval(\(jsString(expression))); return JSON.stringify({v: v === undefined ? null : v}); }
              catch (e) { return JSON.stringify({error: String(e)}); } })()
            """
        let command = safari ? "do JavaScript \(quoted(wrapped)) in \(currentTab)" : "execute \(currentTab) javascript \(quoted(wrapped))"
        let raw = try script(command)
        guard let data = raw.data(using: .utf8),
              let result = try? JSONSerialization.jsonObject(with: data, options: [.fragmentsAllowed]) as? [String: Any] else {
            throw ToolError("No result from the page (\(raw.isEmpty ? "empty" : raw)). Pages such as chrome:// do not run JavaScript.")
        }
        if let error = result["error"] as? String { throw ToolError("JavaScript error: \(error)") }
        return result["v"]
    }

    func screenshot() throws -> String? {
        let browser = try session(for: appName)
        guard let window = frontWindow(of: browser) else { return nil }
        return capture(session: browser, window: window)
    }

    func network(filter: String?, limit: Int) throws -> String {
        let entries = try evaluate("""
            performance.getEntries().filter(e => e.entryType === 'navigation' || e.entryType === 'resource')
              .map(e => [e.entryType === 'navigation' ? 'document' : e.initiatorType, e.responseStatus || '', Math.round(e.duration), e.transferSize, e.name])
            """) as? [[Any]] ?? []
        let lines = entries.map { $0.map { "\($0)" } }
            .filter { filter == nil || $0.last!.localizedCaseInsensitiveContains(filter!) }
            .suffix(limit)
            .map { "\($0[0]) status=\($0[1].isEmpty ? "?" : $0[1]) \($0[2])ms \($0[3])B \($0[4])" }
        return "Requests of this page from the browser's performance records (no headers or bodies; " +
            "use engine devtools for those):\n" + (lines.isEmpty ? "none" : lines.joined(separator: "\n"))
    }

    func responseBody(_ requestID: String) throws -> String { throw onlyDevTools("response_body") }

    func console(limit: Int) throws -> String {
        let lines = try evaluate("window.__mcuLog || []") as? [String] ?? []
        return "Console messages since mac-cu first ran JavaScript in this page:\n" +
            (lines.isEmpty ? "none" : lines.suffix(limit).joined(separator: "\n"))
    }

    func cookies() throws -> String {
        let text = try evaluate("document.cookie") as? String ?? ""
        return "Cookies that the page can read (not HttpOnly; use engine devtools for all):\n" +
            (text.isEmpty ? "none" : text.split(separator: ";").map { $0.trimmingCharacters(in: .whitespaces) }.joined(separator: "\n"))
    }

    func quit() throws { throw ToolError("quit is for the devtools engine. mac-cu does not close the user's browser.") }
}

// MARK: - The browser tool

func browserEngine(_ name: String?, browser: String?) throws -> BrowserEngine {
    switch name ?? "apple_events" {
    case "apple_events": return try AppleEventsBrowser(name: browser ?? "Google Chrome")
    case "devtools": return try DevTools.connect()
    case "extension": return try ChromeExtension()
    default: throw ToolError("engine is \"apple_events\", \"extension\" or \"devtools\".")
    }
}

/// The page as the page action shows it, and its element lines.
func readPage(_ engine: BrowserEngine, textLimit: Int = 4000, mark: Bool = true) throws -> (text: String, elements: [String]) {
    let page = try engine.evaluate(pageScript(textLimit: textLimit, mark: mark)) as? [String: Any] ?? [:]
    let elements = page["elements"] as? [String] ?? []
    let length = page["textLength"] as? Int ?? 0
    let shown = (page["text"] as? String ?? "")
    return ("""
        Tab: \(page["title"] ?? "") — \(page["url"] ?? "") (\(page["ready"] ?? ""))
        \(elements.count) elements. Use these numbers with click and fill; read the page again after it changes.
        \(elements.joined(separator: "\n"))

        Text\(length > shown.count ? " (first \(shown.count) of \(length) characters; set text_limit for more)" : ""):
        \(shown)
        """, elements)
}

/// Actions after which verify reads the page.
let pageChangingActions: Set = ["open", "navigate", "select_tab", "back", "forward", "reload", "click", "fill", "key"]

func browserTool(_ arguments: [String: Any]) throws -> [String: Any] {
    guard let action = arguments["action"] as? String else { throw ToolError("browser needs \"action\".") }
    let engine = try browserEngine(arguments["engine"] as? String, browser: arguments["browser"] as? String)
    let verify = pageChangingActions.contains(action) ? arguments["verify"] as? [String: Any] : nil
    let before = verify == nil ? nil : try? readPage(engine, mark: false).text
    func required(_ key: String) throws -> String {
        if let value = arguments[key] as? String, !value.isEmpty { return value }
        if let value = arguments[key] as? NSNumber { return value.stringValue }
        throw ToolError("\(action) needs \"\(key)\".")
    }
    func index() throws -> Int {
        guard let value = arguments["element"] as? Int else { throw ToolError("\(action) needs \"element\" from the page action.") }
        return value
    }
    let limit = arguments["limit"] as? Int ?? 50
    var text: String
    var image: String?
    switch action {
    case "tabs": text = try engine.tabs()
    case "open":
        try engine.open(try required("url"))
        text = "Opened a new tab: " + (try waitForPage(engine, selector: nil, seconds: 15))
    case "navigate":
        try engine.navigate(try required("url"))
        text = "Navigated: " + (try waitForPage(engine, selector: nil, seconds: 15))
    case "select_tab": try engine.selectTab(try required("tab")); text = "Selected tab \(try required("tab"))."
    case "close_tab": try engine.closeTab(try required("tab")); text = "Closed tab \(try required("tab"))."
    case "back", "forward", "reload":
        try engine.history(action)
        text = "\(action): " + (try waitForPage(engine, selector: nil, seconds: 15))
    case "js": text = json(try engine.evaluate(try required("code")))
    case "page": text = try readPage(engine, textLimit: arguments["text_limit"] as? Int ?? 4000).text
    case "click":
        text = try (engine as? CDPEngine)?.click(try index()) ?? json(try engine.evaluate(clickScript(try index())))
    case "fill":
        let value = arguments["text"] as? String ?? ""
        text = try (engine as? CDPEngine)?.fill(try index(), value) ?? json(try engine.evaluate(fillScript(try index(), value)))
    case "key":
        guard let cdp = engine as? CDPEngine else {
            throw ToolError("key needs engine extension or devtools. With apple_events, use act press_key on the browser window.")
        }
        text = try cdp.press(try required("key"))
    case "wait":
        text = try waitForPage(engine, selector: arguments["selector"] as? String, seconds: arguments["seconds"] as? Double ?? 10)
    case "screenshot":
        guard let jpeg = try engine.screenshot() else { throw ToolError(noScreenshot("No screenshot of the browser window.")) }
        image = jpeg
        text = "Screenshot of the \(engine is CDPEngine ? "page" : "browser window")."
    case "network": text = try engine.network(filter: arguments["filter"] as? String, limit: limit)
    case "response_body": text = try engine.responseBody(try required("request_id"))
    case "console": text = try engine.console(limit: limit)
    case "cookies": text = try engine.cookies()
    case "quit": try engine.quit(); text = "Closed the devtools Chrome."
    default: throw ToolError("Unknown browser action \"\(action)\".")
    }
    if let verify { text += "\n\n" + verifyPage(engine, verify, before: before) }
    // The first line names the window, so that focus.py shows the glow around it.
    if action != "quit", let pid = engine.pid, let app = NSRunningApplication(processIdentifier: pid) {
        let session = sessions[pid] ?? Session(app: app)
        sessions[pid] = session
        if let window = frontWindow(of: session) {
            text = "Window: \"\(string(window, kAXTitleAttribute) ?? "")\", App: \(session.name).\n" + text
        }
    }
    var content: [[String: Any]] = [["type": "text", "text": text]]
    if let image { content.append(["type": "image", "data": image, "mimeType": "image/jpeg"]) }
    return ["content": content]
}

// MARK: - decide on pages

let pageIntro = "A web page: its visible interactive elements (number, tag[type], role=, \"label\", href=, flags), then its text."

private let pageRoles = ["a": "Link", "button": "Button", "textarea": "TextArea", "select": "PopUpButton", "summary": "DisclosureTriangle"]
private let inputRoles = ["text": "TextField", "search": "SearchField", "email": "TextField", "password": "TextField",
                          "number": "TextField", "tel": "TextField", "url": "TextField", "checkbox": "CheckBox",
                          "radio": "RadioButton", "submit": "Button", "button": "Button", "reset": "Button"]

/// The page as decide reads it: element lines with the role names of an app tree, and the placeholder of a
/// field without a label in the place of the title. In the test the model read the value of a field only
/// in this form (docs/development/decide-verify/README.md, web pages).
func pageForDecide(_ page: String) -> String {
    guard let textStart = page.range(of: "\n\nText") else { return page }
    let lines = page[..<textStart.lowerBound].split(separator: "\n", omittingEmptySubsequences: false).map { line -> String in
        let parts = line.split(separator: " ", maxSplits: 2).map(String.init)
        guard parts.count >= 2, Int(parts[0]) != nil else { return String(line) }
        let tagAndType = parts[1].split(separator: "[").map(String.init)
        let type = tagAndType.count > 1 ? String(tagAndType[1].dropLast()) : ""
        guard let role = pageRoles[tagAndType[0]] ?? (tagAndType[0] == "input" ? inputRoles[type] : nil) else { return String(line) }
        var rest = parts.count > 2 ? " " + parts[2] : ""
        if !rest.hasPrefix(" \""), !rest.hasPrefix(" role="),
           let range = rest.range(of: #" placeholder="[^"]*""#, options: .regularExpression) {
            let placeholder = rest[range].dropFirst(" placeholder=".count)
            rest.removeSubrange(range)
            rest = " " + placeholder + rest
        }
        return "\(parts[0]) \(role)\(rest)"
    }
    return lines.joined(separator: "\n") + page[textStart.lowerBound...]
}

/// The answers of OpenAI Decisions about a page (source tree: its elements and text; picture: a screenshot).
func decidePage(_ engine: BrowserEngine, page: String, questions: Any?, source: String?, text: String?, model: String?) throws -> [DecideAnswer] {
    let input = try windowState(source: source ?? "tree", intro: pageIntro, slim: false, tree: { pageForDecide(page) },
                                picture: { try engine.screenshot() }, text: text)
    return try askDecide(questions: try decideQuestions(questions), state: input.state, zone: input.zone, lossy: input.lossy, model: model)
}

/// After a page action with verify: "No change" when the page is the same as before (no model call), else
/// the answers. An unsure answer or a failed call gives the page too.
func verifyPage(_ engine: BrowserEngine, _ verify: [String: Any], before: String?) -> String {
    _ = try? waitForPage(engine, selector: nil, seconds: 10)  // A click can start a navigation.
    guard var after = try? readPage(engine).text else { return "Verify failed: mac-cu could not read the page." }
    // A page can change some time after the action (a fetch, a tab that is not shown).
    let end = Date().addingTimeInterval(2)
    while after == before, Date() < end {
        usleep(250_000)
        after = (try? readPage(engine).text) ?? after
    }
    if after == before { return "No change: the page is the same as before this action (checked without a decision model)." }
    do {
        let answers = try decidePage(engine, page: after, questions: verify["questions"], source: verify["source"] as? String,
                                     text: verify["text"] as? String, model: verify["model"] as? String)
        let lines = answers.map(\.line).joined(separator: "\n")
        return answers.allSatisfy(\.sure)
            ? "Verify:\n\(lines)\nThe page is not shown. Use the page action before you use element numbers."
            : "Verify:\n\(lines)\nNot sure: the page follows.\n\n" + after
    } catch let error as ToolError {
        return "Verify failed: \(error.message)\n\n" + after
    } catch {
        let reason = (error as? DecisionServiceError)?.message ?? "The decision request could not be completed."
        return "Verify failed: \(reason)\n\n" + after
    }
}
