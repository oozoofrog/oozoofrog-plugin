// Mac apps through the accessibility API: the numbered tree, actions, and input events that go
// to the app's process, so that the app can stay in the background.

import AppKit
import ApplicationServices

let maxElements = 1500
let maxDepth = 60
// Elements with these roles and no text or action only group other elements: they get no number.
let containerRoles: Set<String> = ["AXGroup", "AXUnknown", "AXSplitGroup", "AXLayoutArea", "AXLayoutItem"]
let quietActions: Set<String> = ["AXShowMenu", "AXScrollToVisible"]

// MARK: - Accessibility

func attribute(_ element: AXUIElement, _ name: String) -> CFTypeRef? {
    var result: CFTypeRef?
    return AXUIElementCopyAttributeValue(element, name as CFString, &result) == .success ? result : nil
}

func string(_ element: AXUIElement, _ name: String) -> String? {
    guard let raw = attribute(element, name) else { return nil }
    let text: String
    if let value = raw as? String { text = value }
    else if CFGetTypeID(raw) == CFNumberGetTypeID() || CFGetTypeID(raw) == CFBooleanGetTypeID() { text = "\(raw)" }
    else { return nil }
    let clean = text.replacingOccurrences(of: "\n", with: " ").trimmingCharacters(in: .whitespaces)
    if clean.isEmpty { return nil }
    return clean.count > 160 ? String(clean.prefix(160)) + "…" : clean
}

func flag(_ element: AXUIElement, _ name: String) -> Bool? {
    (attribute(element, name) as? NSNumber)?.boolValue
}

func element(_ raw: CFTypeRef?) -> AXUIElement? {
    guard let raw, CFGetTypeID(raw) == AXUIElementGetTypeID() else { return nil }
    return (raw as! AXUIElement)
}

func children(_ element: AXUIElement) -> [AXUIElement] {
    attribute(element, kAXChildrenAttribute) as? [AXUIElement] ?? []
}

func actionNames(_ element: AXUIElement) -> [String] {
    var names: CFArray?
    AXUIElementCopyActionNames(element, &names)
    return names as? [String] ?? []
}

/// The short name of an action: "Press" for AXPress, "복사" for an app action "Name:복사\nTarget:…".
func actionLabel(_ action: String) -> String {
    if action.hasPrefix("AX") { return String(action.dropFirst(2)) }
    if action.hasPrefix("Name:") { return String(action.dropFirst(5).prefix { $0 != "\n" }) }
    return action
}

func isSettable(_ element: AXUIElement, _ name: String) -> Bool {
    var settable = DarwinBoolean(false)
    return AXUIElementIsAttributeSettable(element, name as CFString, &settable) == .success && settable.boolValue
}

/// The frame in Window Server coordinates (top left of the main display).
func frame(_ element: AXUIElement) -> CGRect? {
    var origin = CGPoint.zero, size = CGSize.zero
    guard let position = attribute(element, kAXPositionAttribute), let extent = attribute(element, kAXSizeAttribute),
          CFGetTypeID(position) == AXValueGetTypeID(), CFGetTypeID(extent) == AXValueGetTypeID(),
          AXValueGetValue(position as! AXValue, .cgPoint, &origin),
          AXValueGetValue(extent as! AXValue, .cgSize, &size) else { return nil }
    return CGRect(origin: origin, size: size)
}

/// Give a text element the keyboard focus, as a real click does, so that keys go to it. Other
/// elements keep the focus where it is: a focused button takes the keys (Calculator then ignores digits).
func focus(_ element: AXUIElement) {
    let textRoles: Set<String> = ["AXTextField", "AXTextArea", "AXComboBox", "AXSearchField"]
    if textRoles.contains(string(element, kAXRoleAttribute) ?? ""), isSettable(element, kAXFocusedAttribute) {
        AXUIElementSetAttributeValue(element, kAXFocusedAttribute as CFString, kCFBooleanTrue)
    }
}

func check(_ error: AXError, _ what: String) throws {
    if error != .success { throw ToolError("\(what) failed (AXError \(error.rawValue)).") }
}

// MARK: - Apps

final class Session {
    let app: NSRunningApplication
    let root: AXUIElement
    var elements: [AXUIElement] = []
    /// When this server opened the app. A just opened app needs a moment before it shows a window.
    var opened: Date?
    /// Screenshot pixels per window point in the latest screenshot. click_at and drag use it.
    var screenshotScale: CGFloat = 1

    /// The app's process. LaunchServices can list a running app with pid -1 (seen: Xcode 27's Device Hub); then the
    /// process is found by the app's executable.
    let pid: pid_t

    init(app: NSRunningApplication) {
        self.app = app
        pid = resolvedPid(app)
        root = AXUIElementCreateApplication(pid)
        AXUIElementSetMessagingTimeout(root, 3)
        // Chromium and Electron apps expose their web content only when asked.
        AXUIElementSetAttributeValue(root, "AXManualAccessibility" as CFString, kCFBooleanTrue)
    }

    var name: String { app.localizedName ?? app.bundleIdentifier ?? "pid \(app.processIdentifier)" }
}

var sessions: [pid_t: Session] = [:]

func resolvedPid(_ app: NSRunningApplication) -> pid_t {
    guard app.processIdentifier <= 0, let path = app.executableURL?.resolvingSymlinksInPath().path else { return app.processIdentifier }
    var pids = [pid_t](repeating: 0, count: 16384)
    let count = Int(proc_listallpids(&pids, Int32(pids.count * MemoryLayout<pid_t>.size)))
    var buffer = [CChar](repeating: 0, count: 4096)
    for pid in pids.prefix(max(count, 0)) where pid > 0 {
        if proc_pidpath(pid, &buffer, UInt32(buffer.count)) > 0, String(cString: buffer) == path { return pid }
    }
    return app.processIdentifier
}

func matches(_ app: NSRunningApplication, _ wanted: String) -> Bool {
    [app.localizedName, app.bundleIdentifier, app.bundleURL?.deletingPathExtension().lastPathComponent]
        .contains { $0?.lowercased() == wanted }
}

func applicationURL(_ wanted: String) -> URL? {
    if let url = NSWorkspace.shared.urlForApplication(withBundleIdentifier: wanted) { return url }
    let folders = ["/Applications", "/Applications/Utilities", "/System/Applications",
                   "/System/Applications/Utilities", NSHomeDirectory() + "/Applications"]
    for folder in folders {
        for item in (try? FileManager.default.contentsOfDirectory(atPath: folder)) ?? [] where item.hasSuffix(".app") {
            let path = folder + "/" + item
            let names = [item, FileManager.default.displayName(atPath: path)].map {
                ($0.hasSuffix(".app") ? String($0.dropLast(4)) : $0).lowercased()
            }
            if names.contains(wanted) { return URL(fileURLWithPath: path) }
        }
    }
    return nil
}

/// The running app with this name or bundle ID. An app that does not run is opened in the background.
func session(for name: String) throws -> Session {
    let wanted = name.trimmingCharacters(in: .whitespaces).lowercased()
    guard !wanted.isEmpty else { throw ToolError("Give the app name, for example \"Calculator\".") }
    // Read on the main thread: from other threads the list keeps missing apps opened after the first read.
    let apps = DispatchQueue.main.sync { NSWorkspace.shared.runningApplications }
    var app = apps.first { $0.activationPolicy == .regular && matches($0, wanted) }
    let running = app != nil
    if let app {
        try approve(app.localizedName ?? name, bundleID: app.bundleIdentifier)
    } else {
        guard let url = applicationURL(wanted) else {
            let names = apps.filter { $0.activationPolicy == .regular }
                .compactMap(\.localizedName).sorted().joined(separator: ", ")
            throw ToolError("No app named \"\(name)\". Running apps: \(names).")
        }
        let displayName = FileManager.default.displayName(atPath: url.path)
        try approve(displayName.hasSuffix(".app") ? String(displayName.dropLast(4)) : displayName,
                    bundleID: Bundle(url: url)?.bundleIdentifier)
        let configuration = NSWorkspace.OpenConfiguration()
        configuration.activates = false
        let done = DispatchSemaphore(value: 0)
        NSWorkspace.shared.openApplication(at: url, configuration: configuration) { opened, _ in
            app = opened
            done.signal()
        }
        _ = done.wait(timeout: .now() + 15)
        guard app != nil else { throw ToolError("Could not open \(url.lastPathComponent).") }
        sessions[resolvedPid(app!)] = nil
    }
    let pid = resolvedPid(app!)
    if let existing = sessions[pid], !existing.app.isTerminated { return existing }
    let session = Session(app: app!)
    if !running { session.opened = Date() }
    sessions[pid] = session
    return session
}

func frontWindow(of session: Session) -> AXUIElement? {
    while true {
        for name in [kAXFocusedWindowAttribute, kAXMainWindowAttribute] {
            if let window = element(attribute(session.root, name)) { return window }
        }
        if let window = (attribute(session.root, kAXWindowsAttribute) as? [AXUIElement])?.first { return window }
        guard let opened = session.opened, Date().timeIntervalSince(opened) < 5 else { return nil }
        usleep(100_000)
    }
}

/// The items of a menu bar, or of the menu that a menu bar item or menu item opens.
func menuItems(_ node: AXUIElement) -> [AXUIElement] {
    children(node).flatMap { string($0, kAXRoleAttribute) == "AXMenu" ? children($0) : [$0] }
}

// MARK: - State

func render(_ node: AXUIElement, indent: Int, depth: Int, lines: inout [String], elements: inout [AXUIElement]) {
    guard depth < maxDepth, elements.count < maxElements else { return }
    let role = string(node, kAXRoleAttribute) ?? "AXUnknown"
    let title = string(node, kAXTitleAttribute)
    let description = string(node, kAXDescriptionAttribute)
    let value = role == "AXScrollBar" ? nil : string(node, kAXValueAttribute)
    let placeholder = string(node, kAXPlaceholderValueAttribute)
    let actions = actionNames(node).filter { !quietActions.contains($0) }
    let labelled = title != nil || description != nil || value != nil || placeholder != nil
    var childIndent = indent
    if labelled || !actions.isEmpty || !containerRoles.contains(role) {
        var parts = ["\(elements.count)", String(role.dropFirst(2))]
        if let subrole = string(node, kAXSubroleAttribute) { parts[1] += "/" + subrole.dropFirst(2) }
        if let title { parts.append("\"\(title)\"") }
        if let description, description != title { parts.append("desc=\"\(description)\"") }
        if let value, value != title { parts.append("value=\"\(value)\"") }
        if let placeholder { parts.append("placeholder=\"\(placeholder)\"") }
        if !actions.isEmpty { parts.append("[" + actions.map(actionLabel).joined(separator: ",") + "]") }
        if flag(node, kAXEnabledAttribute) == false { parts.append("disabled") }
        if flag(node, kAXFocusedAttribute) == true { parts.append("focused") }
        if flag(node, kAXSelectedAttribute) == true { parts.append("selected") }
        if isSettable(node, kAXValueAttribute) { parts.append("editable") }
        lines.append(String(repeating: "  ", count: indent) + parts.joined(separator: " "))
        elements.append(node)
        childIndent += 1
    }
    for child in children(node) {
        render(child, indent: childIndent, depth: depth + 1, lines: &lines, elements: &elements)
    }
}

func state(of session: Session, screenshot: Bool, guides: Bool = false) throws -> [[String: Any]] {
    guard let window = frontWindow(of: session) else {
        session.elements = []
        let menus = element(attribute(session.root, kAXMenuBarAttribute)).map(menuItems) ?? []
        let titles = menus.compactMap { string($0, kAXTitleAttribute) }.map { "\"\($0)\"" }.joined(separator: ", ")
        return [["type": "text", "text": """
            App: \(session.name) has no window. Use a menu action to open one, for example \
            {"type": "menu", "path": ["File", "New"]}. Menus: \(titles).
            """]]
    }
    var lines: [String] = []
    var elements: [AXUIElement] = []
    render(window, indent: 0, depth: 0, lines: &lines, elements: &elements)
    session.elements = elements
    let title = string(window, kAXTitleAttribute) ?? ""
    var header = ["Window: \"\(title)\", App: \(session.name).",
                  "\(elements.count) elements. Use these numbers in act; they change after each call."]
    if elements.count >= maxElements { header.append("The tree was cut at \(maxElements) elements.") }
    // Guides: one list of element frames (Window Server coordinates) for the tree lines, the picture and the user's window.
    let bounds = frame(window) ?? .zero
    let frames: [CGRect?] = guides ? elements.map(frame) : []
    let allBoxes = guideBoxes(frames, within: bounds)
    let boxes = Array(allBoxes.prefix(maxGuideBoxes))
    let jpeg = screenshot ? capture(session: session, window: window, guides: guides ? boxes : nil) : nil
    if guides {
        // Without a picture the numbers are window points: the same as the picture's pixels at scale 1.
        let scale = jpeg == nil ? 1 : session.screenshotScale
        for (index, rect) in frames.enumerated() {
            if let rect { lines[index] += guideSuffix(pixelRect(rect, window: bounds, scale: scale)) }
        }
        if jpeg == nil { header.append("@x,y w×h are window points from the top left.") }
        if allBoxes.count > maxGuideBoxes { header.append("Boxes (on the picture and on the window) for the first \(maxGuideBoxes) elements.") }
        if modes()["show"] != "off" { showGuides(boxes, pid: session.pid) }
    }
    var content: [[String: Any]] = [["type": "text", "text": (header + lines).joined(separator: "\n")]]
    if screenshot {
        if let jpeg {
            content[0]["text"] = (content[0]["text"] as? String ?? "") + """

                Screenshot: x and y for click_at and drag are pixels of this picture, from its top left\
                \(guides ? ", and the @x,y w×h of the tree are its pixels." : ".")
                """
            content.append(["type": "image", "data": jpeg, "mimeType": "image/jpeg"])
        } else {
            content.append(["type": "text", "text": noScreenshot("No screenshot: the window was not found for a picture.")])
        }
    }
    return content
}

/// A JPEG of the window as base64, at most 1280 points wide, or nil. With guides (element frames in Window
/// Server coordinates), the measurement guides are drawn on it.
/// screencapture(1), not SCScreenshotManager: replayd serves one live process per executable file, so a
/// second mac-cu of the same path (another session) waited forever once the first had captured a window.
func capture(session: Session, window: AXUIElement, guides: [GuideBox]? = nil) -> String? {
    guard let bounds = frame(window) else { return nil }
    let pid = session.pid
    func rect(_ window: [String: Any]) -> CGRect? {
        (window[kCGWindowBounds as String] as? NSDictionary).flatMap { CGRect(dictionaryRepresentation: $0) }
    }
    let windows = (CGWindowListCopyWindowInfo(.optionAll, kCGNullWindowID) as? [[String: Any]] ?? []).filter {
        ($0[kCGWindowOwnerPID as String] as? pid_t) == pid && ($0[kCGWindowLayer as String] as? Int) == 0
    }
    guard let target = windows.first(where: { rect($0) == bounds }) ?? windows.first,
          let number = target[kCGWindowNumber as String] as? Int, let frame = rect(target)
    else { return nil }
    let file = FileManager.default.temporaryDirectory.appendingPathComponent("mac-cu-\(getpid())-window.png")
    defer { try? FileManager.default.removeItem(at: file) }
    guard shell("/usr/sbin/screencapture", ["-l", String(number), "-x", "-o", "-t", "png", file.path], timeout: 5).status == 0,
          let image = NSImage(contentsOf: file)?.cgImage(forProposedRect: nil, context: nil, hints: nil)
    else { return nil }
    let scale = min(1, 1280 / max(frame.width, 1))
    session.screenshotScale = scale
    return try? jpegBase64(image, size: CGSize(width: frame.width * scale, height: frame.height * scale),
                           guides: guides?.map { GuideBox(number: $0.number, rect: pixelRect($0.rect, window: bounds, scale: scale)) })
}

// MARK: - Input events (sent to the app's process, so the app can stay in the background)

let namedKeys: [String: CGKeyCode] = [
    "return": 36, "enter": 76, "tab": 48, "space": 49, "delete": 51, "backspace": 51, "escape": 53, "esc": 53,
    "forwarddelete": 117, "home": 115, "end": 119, "pageup": 116, "pagedown": 121,
    "left": 123, "right": 124, "down": 125, "up": 126,
    "f1": 122, "f2": 120, "f3": 99, "f4": 118, "f5": 96, "f6": 97, "f7": 98, "f8": 100, "f9": 101, "f10": 109,
    "f11": 103, "f12": 111,
]
// US layout key codes. The typed character is also set on the event, so other layouts work too.
let characterKeys: [Character: CGKeyCode] = [
    "a": 0, "s": 1, "d": 2, "f": 3, "h": 4, "g": 5, "z": 6, "x": 7, "c": 8, "v": 9, "b": 11, "q": 12, "w": 13,
    "e": 14, "r": 15, "y": 16, "t": 17, "1": 18, "2": 19, "3": 20, "4": 21, "6": 22, "5": 23, "=": 24, "9": 25,
    "7": 26, "-": 27, "8": 28, "0": 29, "]": 30, "o": 31, "u": 32, "[": 33, "i": 34, "p": 35, "l": 37, "j": 38,
    "'": 39, "k": 40, ";": 41, "\\": 42, ",": 43, "/": 44, "n": 45, "m": 46, ".": 47, "`": 50,
]
let modifierFlags: [String: CGEventFlags] = [
    "cmd": .maskCommand, "command": .maskCommand, "shift": .maskShift, "alt": .maskAlternate,
    "option": .maskAlternate, "opt": .maskAlternate, "ctrl": .maskControl, "control": .maskControl, "fn": .maskSecondaryFn,
]

/// Background actions send events to the app's process. Foreground actions send them as real input,
/// because some apps ignore events sent to their process.
var sendsRealInput = false

// Not in the public headers. Real input gets the window and the point in it from the window server.
let setWindowLocation = dlsym(dlopen(nil, RTLD_NOW), "CGEventSetWindowLocation")
    .map { unsafeBitCast($0, to: (@convention(c) (CGEvent, CGPoint) -> Void).self) }

/// Name the app's window under the event and the point in that window. Without them, background
/// windows (TextEdit, Chrome) ignore mouse events sent to the process. Field 51 is the window number.
func aim(_ event: CGEvent, pid: pid_t) {
    let point = event.location
    guard let windows = CGWindowListCopyWindowInfo(.optionOnScreenOnly, kCGNullWindowID) as? [[String: Any]],
          let window = windows.first(where: {
              ($0[kCGWindowOwnerPID as String] as? pid_t) == pid
                  && CGRect(dictionaryRepresentation: $0[kCGWindowBounds as String] as! CFDictionary)?.contains(point) == true
          }),
          let number = window[kCGWindowNumber as String] as? Int64,
          let bounds = CGRect(dictionaryRepresentation: window[kCGWindowBounds as String] as! CFDictionary)
    else { return }
    event.setIntegerValueField(CGEventField(rawValue: 51)!, value: number)
    setWindowLocation?(event, CGPoint(x: point.x - bounds.minX, y: point.y - bounds.minY))
}

func deliver(_ event: CGEvent, to pid: pid_t) {
    if sendsRealInput { event.post(tap: .cghidEventTap); return }
    if event.type != .keyDown && event.type != .keyUp { aim(event, pid: pid) }
    event.postToPid(pid)
}

func postKey(_ code: CGKeyCode, character: String?, flags: CGEventFlags, pid: pid_t) {
    for down in [true, false] {
        guard let event = CGEvent(keyboardEventSource: nil, virtualKey: code, keyDown: down) else { continue }
        event.flags = flags
        if let character {
            let units = Array(character.utf16)
            event.keyboardSetUnicodeString(stringLength: units.count, unicodeString: units)
        }
        deliver(event, to: pid)
        usleep(8_000)
    }
}

/// Press a key or a combination such as "Return", "cmd+a" or "shift+Tab".
func pressKey(_ combination: String, pid: pid_t) throws {
    var parts = combination.split(separator: "+").map { $0.trimmingCharacters(in: .whitespaces) }
    if combination.hasSuffix("++") || combination == "+" { parts = parts.filter { !$0.isEmpty } + ["+"] }
    guard let key = parts.popLast(), !key.isEmpty else { throw ToolError("No key in \"\(combination)\".") }
    var flags = CGEventFlags()
    for name in parts {
        guard let modifier = modifierFlags[name.lowercased()] else { throw ToolError("Unknown modifier \"\(name)\".") }
        flags.insert(modifier)
    }
    if let code = namedKeys[key.lowercased()] {
        postKey(code, character: nil, flags: flags, pid: pid)
    } else if key.count == 1, let character = key.lowercased().first {
        postKey(characterKeys[character] ?? 0, character: key, flags: flags, pid: pid)
    } else {
        throw ToolError("Unknown key \"\(key)\". Use a character or one of: \(namedKeys.keys.sorted().joined(separator: ", ")).")
    }
}

/// Type text as key events to the focused element of the app, as a person types. A line break is
/// a Return key. (Text put in through the accessibility API can skip the app's own input handling:
/// Chrome's address field then shows the text but does not open it on Return.)
func typeText(_ text: String, pid: pid_t) {
    for character in text {
        if character == "\n" {
            postKey(36, character: nil, flags: [], pid: pid)
        } else {
            postKey(characterKeys[Character(character.lowercased())] ?? 0, character: String(character),
                    flags: character.isUppercase ? .maskShift : [], pid: pid)
        }
    }
}

/// The app in front now. NSWorkspace.frontmostApplication can be out of date in this process, so it is
/// only the fallback: some apps in front (Claude, an Electron app) make the accessibility query fail.
func frontmostPID() -> pid_t? {
    var pid: pid_t = 0
    if let app = element(attribute(AXUIElementCreateSystemWide(), kAXFocusedApplicationAttribute)),
       AXUIElementGetPid(app, &pid) == .success { return pid }
    return NSWorkspace.shared.frontmostApplication?.processIdentifier
}

/// Tell focus-overlay where mac-cu acts, so that it can show a pointer there (Window Server coordinates).
func showCursor(at point: CGPoint, pid: pid_t) {
    tellOverlay("mac-cu-cursor", pid: pid, ["x": point.x, "y": point.y])
}

func showCursor(on node: AXUIElement, pid: pid_t) {
    if let bounds = frame(node) { showCursor(at: CGPoint(x: bounds.midX, y: bounds.midY), pid: pid) }
}

func postDrag(from start: CGPoint, to end: CGPoint, pid: pid_t) {
    func post(_ type: CGEventType, _ point: CGPoint) {
        if let event = CGEvent(mouseEventSource: nil, mouseType: type, mouseCursorPosition: point, mouseButton: .left) {
            deliver(event, to: pid)
        }
        usleep(15_000)
    }
    post(.leftMouseDown, start)
    for step in 1...10 {
        let t = CGFloat(step) / 10
        post(.leftMouseDragged, CGPoint(x: start.x + (end.x - start.x) * t, y: start.y + (end.y - start.y) * t))
    }
    post(.leftMouseUp, end)
}

/// The element, or one of its near parents, when it is a row that can be selected.
func selectableRow(_ node: AXUIElement) -> AXUIElement? {
    var current: AXUIElement? = node
    for _ in 0..<4 {
        guard let candidate = current else { return nil }
        if string(candidate, kAXRoleAttribute) == "AXRow" {
            return isSettable(candidate, kAXSelectedAttribute) ? candidate : nil
        }
        current = element(attribute(candidate, kAXParentAttribute))
    }
    return nil
}

func postClick(at point: CGPoint, count: Int, right: Bool, pid: pid_t) {
    let (down, up): (CGEventType, CGEventType) = right ? (.rightMouseDown, .rightMouseUp) : (.leftMouseDown, .leftMouseUp)
    for click in 1...max(count, 1) {
        for type in [down, up] {
            guard let event = CGEvent(mouseEventSource: nil, mouseType: type, mouseCursorPosition: point,
                                      mouseButton: right ? .right : .left) else { continue }
            event.setIntegerValueField(.mouseEventClickState, value: Int64(click))
            deliver(event, to: pid)
            usleep(15_000)
        }
    }
}

// MARK: - Actions

func run(_ action: [String: Any], session: Session) throws -> String {
    guard let type = action["type"] as? String else { throw ToolError("Each action needs a \"type\".") }
    let pid = session.pid
    func target() throws -> (Int, AXUIElement) {
        guard let index = action["element"] as? Int else { throw ToolError("\(type) needs \"element\".") }
        guard session.elements.indices.contains(index) else {
            throw ToolError("No element \(index) in the latest tree of \(session.name). Call get_app_state.")
        }
        return (index, session.elements[index])
    }
    func text() throws -> String {
        guard let text = action["text"] as? String else { throw ToolError("\(type) needs \"text\".") }
        return text
    }
    /// A point in the latest screenshot (pixels from its top left) in Window Server coordinates.
    func screenPoint(_ xKey: String, _ yKey: String) throws -> CGPoint {
        guard let x = (action[xKey] as? NSNumber)?.doubleValue, let y = (action[yKey] as? NSNumber)?.doubleValue else {
            throw ToolError("\(type) needs \"\(xKey)\" and \"\(yKey)\".")
        }
        guard let window = frontWindow(of: session), let bounds = frame(window) else {
            throw ToolError("\(session.name) has no window.")
        }
        let point = CGPoint(x: bounds.minX + x / session.screenshotScale, y: bounds.minY + y / session.screenshotScale)
        guard bounds.contains(point) else { throw ToolError("(\(Int(x)), \(Int(y))) is outside the window.") }
        return point
    }

    switch type {
    case "click":
        let (index, node) = try target()
        let count = action["count"] as? Int ?? 1
        let right = action["button"] as? String == "right"
        let available = actionNames(node)
        showCursor(on: node, pid: pid)
        if !right { focus(node) }
        if count == 1 && !right {
            for name in ["AXPress", "AXConfirm", "AXPick", "AXOpen"] where available.contains(name) {
                if AXUIElementPerformAction(node, name as CFString) == .success { return "click \(index): \(name)" }
            }
        }
        if right, available.contains("AXShowMenu"), AXUIElementPerformAction(node, "AXShowMenu" as CFString) == .success {
            return "click \(index): AXShowMenu"
        }
        // Lists and tables (for example a sidebar) select a row with AXSelected. Inactive apps
        // ignore the mouse events below, so this keeps row selection in the background.
        if count == 1 && !right && !isSettable(node, kAXValueAttribute), let row = selectableRow(node),
           AXUIElementSetAttributeValue(row, kAXSelectedAttribute as CFString, kCFBooleanTrue) == .success {
            return "click \(index): AXSelected on its row"
        }
        guard let bounds = frame(node) else { throw ToolError("Element \(index) has no position to click.") }
        let point = CGPoint(x: bounds.midX, y: bounds.midY)
        postClick(at: point, count: count, right: right, pid: pid)
        return "click \(index): mouse events at (\(Int(point.x)), \(Int(point.y)))"
    case "set_value":
        let (index, node) = try target()
        showCursor(on: node, pid: pid)
        focus(node)
        try check(AXUIElementSetAttributeValue(node, kAXValueAttribute as CFString, try text() as CFString), "set_value \(index)")
        return "set_value \(index)"
    case "type_text":
        typeText(try text(), pid: pid)
        return "type_text"
    case "press_key":
        guard let key = action["key"] as? String else { throw ToolError("press_key needs \"key\".") }
        try pressKey(key, pid: pid)
        return "press_key \(key)"
    case "select_text":
        let (index, node) = try target()
        let wanted = try text()
        guard let whole = attribute(node, kAXValueAttribute) as? String, let found = whole.range(of: wanted) else {
            throw ToolError("Element \(index) does not contain \"\(wanted)\".")
        }
        var range = CFRange(location: whole.utf16.distance(from: whole.startIndex, to: found.lowerBound),
                            length: wanted.utf16.count)
        focus(node)
        try check(AXUIElementSetAttributeValue(node, kAXSelectedTextRangeAttribute as CFString,
                                               AXValueCreate(.cfRange, &range)!), "select_text \(index)")
        return "select_text \(index)"
    case "scroll":
        let (index, node) = try target()
        showCursor(on: node, pid: pid)
        let direction = (action["direction"] as? String ?? "down").lowercased()
        let pages = max(action["pages"] as? Double ?? 1, 0.1)
        return "scroll \(index): " + (try scroll(node, direction: direction, pages: pages, pid: pid))
    case "perform":
        let (index, node) = try target()
        guard let name = action["action"] as? String else { throw ToolError("perform needs \"action\".") }
        let full = actionNames(node).first { $0 == name || actionLabel($0) == name } ?? name
        showCursor(on: node, pid: pid)
        try check(AXUIElementPerformAction(node, full as CFString), "\(full) on \(index)")
        return "perform \(index): \(full)"
    case "menu":
        guard let path = action["path"] as? [String], !path.isEmpty else { throw ToolError("menu needs \"path\".") }
        guard var node = element(attribute(session.root, kAXMenuBarAttribute)) else {
            throw ToolError("\(session.name) has no menu bar.")
        }
        for title in path {
            let items = menuItems(node)
            guard let item = items.first(where: { string($0, kAXTitleAttribute)?.lowercased() == title.lowercased() }) else {
                let titles = items.compactMap { string($0, kAXTitleAttribute) }.map { "\"\($0)\"" }.joined(separator: ", ")
                throw ToolError("No menu item \"\(title)\". Items here: \(titles).")
            }
            node = item
        }
        try check(AXUIElementPerformAction(node, kAXPressAction as CFString), "menu \(path.joined(separator: " > "))")
        return "menu " + path.joined(separator: " > ")
    case "click_at":
        let point = try screenPoint("x", "y")
        showCursor(at: point, pid: pid)
        postClick(at: point, count: action["count"] as? Int ?? 1, right: action["button"] as? String == "right", pid: pid)
        return "click_at (\(Int(point.x)), \(Int(point.y))) on screen"
    case "drag":
        let start = try screenPoint("x", "y"), end = try screenPoint("to_x", "to_y")
        showCursor(at: end, pid: pid)
        postDrag(from: start, to: end, pid: pid)
        return "drag (\(Int(start.x)), \(Int(start.y))) -> (\(Int(end.x)), \(Int(end.y))) on screen"
    case "wait":
        let seconds = min(max(action["seconds"] as? Double ?? 1, 0), 10)
        usleep(useconds_t(seconds * 1_000_000))
        return "wait \(seconds)s"
    default:
        throw ToolError("Unknown action type \"\(type)\".")
    }
}

/// Scroll the element or the nearest scroll area around it by pages.
func scroll(_ node: AXUIElement, direction: String, pages: Double, pid: pid_t) throws -> String {
    let vertical = direction == "up" || direction == "down"
    guard vertical || direction == "left" || direction == "right" else {
        throw ToolError("direction must be up, down, left or right.")
    }
    let forward = direction == "down" || direction == "right"
    var area: AXUIElement? = node
    for _ in 0..<8 where area.map({ string($0, kAXRoleAttribute) != "AXScrollArea" }) ?? false {
        area = element(attribute(area!, kAXParentAttribute))
    }
    if let area, string(area, kAXRoleAttribute) == "AXScrollArea",
       let bar = element(attribute(area, vertical ? kAXVerticalScrollBarAttribute : kAXHorizontalScrollBarAttribute)),
       let current = (attribute(bar, kAXValueAttribute) as? NSNumber)?.doubleValue,
       let visible = frame(area),
       let content = children(area).first(where: { string($0, kAXRoleAttribute) != "AXScrollBar" }).flatMap(frame) {
        let hidden = vertical ? content.height - visible.height : content.width - visible.width
        guard hidden > 1 else { return "nothing to scroll" }
        let step = (vertical ? visible.height : visible.width) / hidden * pages
        let next = min(max(current + (forward ? step : -step), 0), 1)
        try check(AXUIElementSetAttributeValue(bar, kAXValueAttribute as CFString, next as CFNumber), "scroll")
        return String(format: "scroll bar %.2f -> %.2f", current, next)
    }
    guard let bounds = frame(node) else { throw ToolError("No scroll area and no position to scroll at.") }
    let distance = Int32(((vertical ? bounds.height : bounds.width) * 0.9 * pages).rounded())
    let amount = forward ? -distance : distance
    guard let event = CGEvent(scrollWheelEvent2Source: nil, units: .pixel, wheelCount: 2,
                              wheel1: vertical ? amount : 0, wheel2: vertical ? 0 : amount, wheel3: 0) else {
        throw ToolError("Could not make a scroll event.")
    }
    event.location = CGPoint(x: bounds.midX, y: bounds.midY)
    deliver(event, to: pid)
    return "scroll wheel event"
}

// MARK: - act

/// Bring the app and its front window to the front, and wait until it is in front.
func bringToFront(_ session: Session) {
    if let window = frontWindow(of: session) { AXUIElementPerformAction(window, kAXRaiseAction as CFString) }
    AXUIElementSetAttributeValue(session.root, kAXFrontmostAttribute as CFString, kCFBooleanTrue)
    session.app.activate()
    for _ in 0..<20 where frontmostPID() != session.pid { usleep(50_000) }
    usleep(300_000)  // The window takes keys only after it becomes the key window.
}

/// Run the actions in order and return the new state with a line for each action.
/// With foreground, the app is in front while the actions run (for apps that ignore background input).
/// With verify, the result has short answers in place of the tree: "No change" when the tree is the same as
/// before the actions (no model call), else the answers of OpenAI Decisions (Decide.swift). A short tree, an
/// "unknown" answer or a failed call gives the tree too.
func act(_ actions: [[String: Any]], session: Session, foreground asked: Bool, screenshot: Bool, guides: Bool = false,
         verify: [String: Any]? = nil, goal: String? = nil) throws -> [String: Any] {
    // AppKit answers accessibility actions on mac-cu's own windows inside this process, on this (not the main) thread;
    // raising or pressing them there stopped the daemon (EXC_BREAKPOINT in NSWindow ordering).
    guard session.pid != getpid() else {
        throw ToolError("""
            act does not operate mac-cu's own windows (it would stop mac-cu). The simulator window is for the user to use; \
            operate the simulator with the simulator tool.
            """)
    }
    let mode = modes()
    if asked && mode["input"] == "background" {
        throw ToolError("""
            The user set mac-cu to the background only (`mac-cu --mode input=background`), so act does not use \
            foreground. Tell the user what did not work in the background; the user can change the mode.
            """)
    }
    let foreground = asked || mode["input"] == "foreground"
    let steps = mode["show"] == "steps"
    let pid = session.pid
    let front = frontmostPID()
    var log: [String] = []
    var failed: String?
    let pointer = CGEvent(source: nil)?.location
    var before: String?
    if verify != nil {
        // Keep the element numbers of the tree the agent saw: the actions use them.
        let seen = session.elements
        before = try? state(of: session, screenshot: false)[0]["text"] as? String
        session.elements = seen
    }
    if foreground {
        if front != pid { bringToFront(session) }
        sendsRealInput = true
        log.append("\(session.name) is in front for these actions; they use real input"
                   + (asked ? "." : " (the user's input mode is foreground)."))
    }
    defer {
        if foreground {
            sendsRealInput = false
            if let pointer { CGWarpMouseCursorPosition(pointer) }  // The user's pointer goes back.
        }
    }
    // Waits are not steps for the user: the step before a wait stays shown, and the count leaves waits out.
    let shown = actions.filter { $0["type"] as? String != "wait" }
    var number = 0
    for action in actions {
        if steps && action["type"] as? String != "wait" {
            number += 1
            showStep("\(number)/\(shown.count) " + stepText(action, session: session), goal: goal, pid: pid)
        }
        do {
            log.append(try run(action, session: session))
            // Text fields (for example Chrome's address field) need time to take a new text.
            let changesText = ["set_value", "type_text", "select_text"].contains(action["type"] as? String ?? "")
            usleep(changesText ? 250_000 : 60_000)
        } catch let error as ToolError {
            failed = error.message
            break
        }
    }
    if steps { showStep(failed == nil ? "끝 · 동작 \(shown.count)개" : "멈춤 · 동작이 실패함", goal: goal, pid: pid) }
    usleep(250_000)  // Let the app update its window.
    // The app that was in front goes back to the front: after foreground actions, and when the app
    // came to the front by itself (for example Chrome when it opens a window).
    if let front, front != pid, frontmostPID() == pid, let previous = NSRunningApplication(processIdentifier: front) {
        // activate() alone does nothing from mac-cu (a background process): set it front as bringToFront does.
        AXUIElementSetAttributeValue(AXUIElementCreateApplication(front), kAXFrontmostAttribute as CFString, kCFBooleanTrue)
        previous.activate()
        for _ in 0..<20 where frontmostPID() != front { usleep(50_000) }
        if frontmostPID() != front, let url = previous.bundleURL {
            // Some apps (Electron, for example Claude) ignore both: Launch Services activates them, as `open -a` does.
            let configuration = NSWorkspace.OpenConfiguration()
            configuration.activates = true
            NSWorkspace.shared.openApplication(at: url, configuration: configuration)
            for _ in 0..<40 where frontmostPID() != front { usleep(50_000) }
        }
        if frontmostPID() != front { log.append("\(previous.localizedName ?? "The previous app") did not come back to the front.") }
        if !foreground {
            log.append("\(session.name) came to the front by itself; \(previous.localizedName ?? "the previous app") is in front again.")
        }
    }
    var content = try state(of: session, screenshot: screenshot, guides: guides)
    if let verify, failed == nil, let window = frontWindow(of: session) {
        let tree = content[0]["text"] as? String ?? ""
        let header = "Window: \"\(string(window, kAXTitleAttribute) ?? "")\", App: \(session.name)."
        var plain = tree
        if screenshot || guides {
            // The screenshot and guides add to the text: compare a plain read, as before is; keep content's numbers.
            let seen = session.elements
            plain = (try? state(of: session, screenshot: false)[0]["text"] as? String) ?? tree
            session.elements = seen
        }
        if plain == before {
            content[0]["text"] = """
                \(header)
                No change: the window is the same as before these actions (checked without a decision model).
                """
        } else if tree.count < shortTree {
            content[0]["text"] = "Verify skipped: the tree is short.\n\n" + tree
        } else {
            do {
                let input = try windowState(source: verify["source"] as? String ?? "tree", tree: { tree },
                                            picture: { capture(session: session, window: window) }, text: verify["text"] as? String)
                let answers = try askDecide(questions: try decideQuestions(verify["questions"]), state: input.state,
                                            zone: input.zone, lossy: input.lossy, model: verify["model"] as? String)
                let lines = answers.map(\.line).joined(separator: "\n")
                // The front element's line says in code whether a dialog or sheet is in front (the model did not).
                let front = tree.split(separator: "\n").first { $0.hasPrefix("0 ") }.map { "Front: \($0)\n" } ?? ""
                content[0]["text"] = answers.allSatisfy(\.sure)
                    ? "\(header)\n\(front)Verify:\n\(lines)\nThe tree is not shown. Call get_app_state before you use element numbers."
                    : "Verify:\n\(lines)\nNot sure: the tree follows.\n\n" + tree
            } catch {
                // Verification happens after the actions. A provider/auth/network failure must
                // preserve their result and the current tree so the client does not repeat them.
                let reason = (error as? ToolError)?.message
                    ?? (error as? DecisionServiceError)?.message ?? "The decision request could not be completed."
                content[0]["text"] = "Verify failed: \(reason)\n\n" + tree
            }
        }
    }
    let summary = (log + (failed.map { ["Stopped: \($0)"] } ?? [])).joined(separator: "\n")
    content[0]["text"] = summary + "\n\n" + (content[0]["text"] as? String ?? "")
    return failed == nil ? ["content": content] : ["content": content, "isError": true]
}
