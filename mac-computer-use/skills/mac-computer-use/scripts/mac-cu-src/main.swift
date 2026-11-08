// mac-cu: an MCP server (stdio) that reads and operates Mac apps and web pages.
//
// One program, two roles (Daemon.swift): without arguments it is the thin stdio client that the agent starts,
// which hands every line to the menu bar daemon `mac-cu --daemon` (mac-cu.app in ~/Library/Application Support/
// mac-cu, built by setup.py) over daemon.sock and starts it when it does not run. The daemon holds the
// permissions and runs the tools. Socket protocol: three control lines ("mac-cu": hello, quit, permissions),
// every other line is JSON-RPC as below.
//
// Tools:
//   get_app_state  {app, screenshot?, guides?}             The front window of an app as a numbered
//                                                         accessibility tree (Accessibility.swift).
//   act            {app, actions, foreground?, screenshot?, guides?}  Actions on that app, then the new tree.
//   browser        {action, engine?, browser?, verify?, ...}  Web pages through JavaScript (Browser.swift,
//                                                         DevTools.swift, ChromeExtension.swift).
//   simulator      {action, device?, ...}                 A booted iOS Simulator through HID events
//                                                         (Simulator.swift).
//   decide         {questions, app?, source?, text?, model?}  Yes/no, choice and score questions about an app
//                                                         window (picture or tree) and/or a text, answered by
//                                                         OpenAI Decisions (Decide.swift). act takes the same
//                                                         questions in verify.
//                  {app, pick}                            The element that serves a goal (Pick.swift). act
//                                                         with goal displays the action context.
//                  {page, questions | pick}               The same about the current tab of a browser engine.
//
// The first line of a result names the window: `Window: "<title>", App: <name>.` (focus.py reads it).
// Before mac-cu uses an app for the first time in a session, it asks the user in a dialog of its own,
// unless the app is in always-allow.txt (in the skill folder, or in ~/Library/Application Support/mac-cu,
// where "Always Allow" in the dialog adds it).
//
// Public macOS APIs, and two undocumented parts for background mouse events (aim in Accessibility.swift).
// mac-cu.app needs the Accessibility permission, Screen Recording for screenshots, and Automation for the
// browser tool with Apple Events.
//
// Build: python3 ../setup.py (the app bundle; `swiftc -O mac-cu-src/*.swift -o mac-cu` builds the bare program)

import AppKit

/// The version of this build (Info.plist), read now: after a plugin update the running copy keeps its own.
let bundleVersion = Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "0"

struct ToolError: Error {
    let message: String
    init(_ message: String) { self.message = message }
}

/// always-allow.txt of the skill folder, which setup.py copies into the app bundle (Resources).
let bundledAllowList = (Bundle.main.resourceURL ?? URL(fileURLWithPath: CommandLine.arguments[0]).deletingLastPathComponent())
    .appendingPathComponent("always-allow.txt")

// MARK: - Approval of apps

/// Asks the user in a dialog of mac-cu's own, not through the client: some clients (the Claude app)
/// answer an MCP elicitation with "decline" and show nothing. The dialog is a separate process,
/// because the server has no windows. Returns "accept", "always", "decline" or "cancel" (no answer in time).
func askUser(app name: String, bundleID: String?) -> String {
    let dialog = Process()
    dialog.executableURL = URL(fileURLWithPath: Bundle.main.executablePath ?? CommandLine.arguments[0])
    dialog.arguments = ["--approve", name] + (bundleID.map { [$0] } ?? [])
    dialog.standardInput = FileHandle.nullDevice
    dialog.standardOutput = FileHandle.nullDevice
    dialog.standardError = FileHandle.nullDevice
    let done = DispatchSemaphore(value: 0)
    dialog.terminationHandler = { _ in done.signal() }
    guard (try? dialog.run()) != nil else { return "cancel" }
    if done.wait(timeout: .now() + 180) == .timedOut {
        dialog.terminate()
        return "cancel"
    }
    guard dialog.terminationReason == .exit else { return "cancel" }
    return [0: "accept", 1: "decline", 2: "always"][dialog.terminationStatus] ?? "cancel"
}

/// `mac-cu --approve <name> [bundle ID]`: the dialog. Exit status 0 is Allow, 1 is Don't Allow, 2 is Always Allow.
func runApprovalDialog(name: String, bundleID: String?) -> Never {
    NSApplication.shared.setActivationPolicy(.accessory)
    let alert = NSAlert()
    alert.messageText = "Allow mac-cu to use “\(name)”?"
    alert.informativeText = """
        The agent (Claude Code or Codex) can read and operate this app until the session ends. \
        Always Allow also allows it in later sessions (remove it from \(savedAllowList.path) to ask again).
        """
    // The dialog takes the focus: a Return typed for another app must not allow. Only a click allows.
    alert.addButton(withTitle: "Allow").keyEquivalent = ""
    alert.addButton(withTitle: "Don’t Allow").keyEquivalent = "\r"
    alert.addButton(withTitle: "Always Allow").keyEquivalent = ""
    if let bundleID, let url = NSWorkspace.shared.urlForApplication(withBundleIdentifier: bundleID) {
        alert.icon = NSWorkspace.shared.icon(forFile: url.path)
    }
    NSApp.activate(ignoringOtherApps: true)
    alert.window.level = .floating
    switch alert.runModal() {
    case .alertFirstButtonReturn: exit(0)
    case .alertThirdButtonReturn: exit(2)
    default: exit(1)
    }
}

/// "Always Allow" writes here: outside the skill folder, so a plugin update keeps it.
let savedAllowList = FileManager.default.homeDirectoryForCurrentUser
    .appendingPathComponent("Library/Application Support/mac-cu/always-allow.txt")

func alwaysAllowed() -> Set<String> {
    let text = [bundledAllowList, savedAllowList]
        .compactMap { try? String(contentsOf: $0, encoding: .utf8) }.joined(separator: "\n")
    return Set(text.split(separator: "\n").map { $0.trimmingCharacters(in: .whitespaces).lowercased() }
        .filter { !$0.isEmpty && !$0.hasPrefix("#") })
}

/// Adds the app to savedAllowList: the bundle ID when there is one, because the app name changes with the language.
func saveAlwaysAllowed(_ name: String, bundleID: String?) {
    let line = (bundleID ?? name) + "\n"
    try? FileManager.default.createDirectory(at: savedAllowList.deletingLastPathComponent(), withIntermediateDirectories: true)
    if let file = try? FileHandle(forWritingTo: savedAllowList) {
        file.seekToEndOfFile()
        file.write(Data(line.utf8))
        try? file.close()
    } else {
        try? line.write(to: savedAllowList, atomically: true, encoding: .utf8)
    }
}

/// Before the first use of an app in this session, the user allows it (once for the session).
func approve(_ name: String, bundleID: String?) throws {
    let keys = [name.lowercased()] + (bundleID.map { [$0.lowercased()] } ?? [])
    let approved = currentSession?.approvedApps ?? []
    if keys.contains(where: approved.contains) || !alwaysAllowed().isDisjoint(with: keys) { return }
    switch askUser(app: name, bundleID: bundleID) {
    case "accept": currentSession?.approvedApps.formUnion(keys)
    case "always":
        currentSession?.approvedApps.formUnion(keys)
        saveAlwaysAllowed(name, bundleID: bundleID)
    case "decline": throw ToolError("The user did not allow mac-cu to use \"\(name)\". Do not try another way to use it.")
    default:
        throw ToolError("""
            The user did not answer the approval request to use "\(name)" in 3 minutes. Do not try another way \
            to use it. Tell the user. To allow the app without a request, the user can choose Always Allow \
            in the dialog, or add "\(name)" to \(savedAllowList.path) (one app name or bundle ID per line).
            """)
    }
}

// MARK: - Tools

let actionSchema: [String: Any] = [
    "type": "object",
    "properties": [
        "type": ["type": "string",
                 "enum": ["click", "set_value", "type_text", "press_key", "select_text", "scroll", "perform", "menu",
                          "click_at", "drag", "wait"]],
        "element": ["type": "integer", "description": "Element number from the latest tree of this app."],
        "text": ["type": "string", "description": "set_value, type_text, select_text."],
        "key": ["type": "string", "description": "press_key: a key or combination, for example \"Return\", \"cmd+a\", \"shift+Tab\"."],
        "count": ["type": "integer", "description": "click, click_at: 2 for a double click."],
        "button": ["type": "string", "enum": ["left", "right"], "description": "click, click_at: right shows the context menu."],
        "direction": ["type": "string", "enum": ["up", "down", "left", "right"], "description": "scroll."],
        "pages": ["type": "number", "description": "scroll: how far, in visible pages (default 1)."],
        "action": ["type": "string", "description": "perform: an accessibility action shown in the tree, for example \"Increment\"."],
        "path": ["type": "array", "items": ["type": "string"],
                 "description": "menu: menu titles from the menu bar down, for example [\"File\", \"New\"]. Works while the app is in the background."],
        "x": ["type": "number", "description": "click_at, drag: pixels from the left of the latest screenshot of this app."],
        "y": ["type": "number", "description": "click_at, drag: pixels from the top of the latest screenshot of this app."],
        "to_x": ["type": "number", "description": "drag: end point."],
        "to_y": ["type": "number", "description": "drag: end point."],
        "seconds": ["type": "number", "description": "wait: up to 10."],
    ],
    "required": ["type"],
]

let tools: [[String: Any]] = [
    [
        "name": "get_app_state",
        "description": """
            Read the front window of a Mac app as a numbered accessibility tree, in the background. \
            Opens the app in the background when it does not run. Each line: number, role, "title", \
            desc/value/placeholder, [actions], flags. Use the numbers with act. With screenshot, also \
            returns a picture; click_at and drag use its pixels.
            """,
        "inputSchema": [
            "type": "object",
            "properties": [
                "app": ["type": "string", "description": "App name as shown in the Dock or menu bar (for example \"Calculator\" or \"계산기\"), or a bundle ID."],
                "screenshot": ["type": "boolean", "description": "Also return a picture of the window."],
                "guides": ["type": "boolean", "description": """
                    Measure: add @x,y w×h (screenshot pixels, from the top left; the same as click_at) to each tree \
                    line. With screenshot, also draw rulers, a 100 px grid and a numbered box around each element on \
                    the picture, and show the same boxes on the window for the user. Off by default (tokens).
                    """],
            ],
            "required": ["app"],
        ],
    ],
    [
        "name": "act",
        "description": """
            Run actions on a Mac app, in order, then return its new tree. The app stays in the \
            background unless foreground is true. Element numbers come from the latest get_app_state or \
            act result for that app. click uses the accessibility press action when the element has one, \
            else it selects the row of a list or table, else it sends mouse events. type_text sends key events to the focused element ("\\n" is Return); \
            set_value replaces the whole text of an element. click_at and drag use screenshot pixels. \
            Stops at the first action that fails.
            """,
        "inputSchema": [
            "type": "object",
            "properties": [
                "app": ["type": "string", "description": "Same app name as in get_app_state."],
                "actions": ["type": "array", "items": actionSchema],
                "foreground": ["type": "boolean", "description": """
                    Bring the app to the front for these actions, then put the previous app back in front. \
                    Only after the same actions did nothing in the background: it interrupts the user. \
                    The user's input mode can refuse it (background) or use it for every act (foreground).
                    """],
                "screenshot": ["type": "boolean", "description": "Also return a picture of the window."],
                "guides": ["type": "boolean", "description": """
                    Measure: add @x,y w×h (screenshot pixels, from the top left; the same as click_at) to each tree \
                    line. With screenshot, also draw rulers, a 100 px grid and a numbered box around each element on \
                    the picture, and show the same boxes on the window for the user. Off by default (tokens).
                    """],
                "goal": ["type": "string", "description": """
                    What these actions are for, in a few words (for example "12×12를 계산한다"). Optional. mac-cu \
                    shows it on the window when the user's show mode is steps; it does not change the actions or the result.
                    """],
                "verify": ["type": "object", "description": """
                    Check the result without the tree: {"questions": {...as in decide}, "source": "tree" \
                    (default) or "picture", "text"?: the goal}. The result is "No change" when the window is \
                    the same as before (no model call), else the front element and one line for each answer \
                    of OpenAI Decisions: uncalibrated probabilities requiring inspection. A short tree, an unknown \
                    answer, too many buttons or a failed call give the tree too.
                    """],
            ],
            "required": ["app", "actions"],
        ],
    ],
    [
        "name": "browser",
        "description": """
            Work with web pages through JavaScript in the page. engine apple_events (default): the user's \
            own browser with its logins (Chrome, other Chromium browsers, Safari); the browser must allow \
            JavaScript from Apple Events; JavaScript runs without await. engine extension: the user's own \
            Chrome with its logins, through the mac-cu Chrome extension (installed once); like devtools, \
            and Chrome shows a debugging bar on the tab. engine devtools: a separate Chrome with its own \
            profile that mac-cu starts. extension and devtools add network records, response bodies, \
            console, all cookies, page screenshots, await, and real mouse and key input for click, fill and \
            key. Actions: tabs, open, navigate, select_tab, close_tab, back, forward, reload, page (numbered \
            elements and text), click and fill (numbers from page), key, wait, js, screenshot, network, \
            response_body, console, cookies, quit (devtools only).
            """,
        "inputSchema": [
            "type": "object",
            "properties": [
                "action": ["type": "string",
                           "enum": ["tabs", "open", "navigate", "select_tab", "close_tab", "back", "forward", "reload",
                                    "page", "click", "fill", "key", "wait", "js", "screenshot", "network", "response_body",
                                    "console", "cookies", "quit"]],
                "engine": ["type": "string", "enum": ["apple_events", "extension", "devtools"]],
                "browser": ["type": "string", "description": "apple_events: the browser app (default \"Google Chrome\"), for example \"Safari\"."],
                "url": ["type": "string", "description": "open, navigate."],
                "tab": ["type": "string", "description": "select_tab, close_tab: the id from the tabs action."],
                "element": ["type": "integer", "description": "click, fill: the number from the latest page action."],
                "text": ["type": "string", "description": "fill."],
                "key": ["type": "string", "description": "key (extension, devtools): a key or combination, for example \"Enter\", \"Tab\", \"ArrowDown\", \"shift+Tab\", \"cmd+a\"."],
                "code": ["type": "string", "description": "js: a JavaScript expression; its value is returned as JSON."],
                "selector": ["type": "string", "description": "wait: also wait for this CSS selector."],
                "seconds": ["type": "number", "description": "wait: the longest wait (default 10, up to 30)."],
                "text_limit": ["type": "integer", "description": "page: the most characters of page text (default 4000)."],
                "filter": ["type": "string", "description": "network: only URLs that contain this text."],
                "limit": ["type": "integer", "description": "network, console: the most lines (default 50)."],
                "request_id": ["type": "string", "description": "response_body: the id from the network action (devtools, extension)."],
                "verify": ["type": "object", "description": """
                    open, navigate, select_tab, back, forward, reload, click, fill, key: check the page after the \
                    action without reading it, as act verify: {"questions": {...as in decide}, "source": "tree" \
                    (default: the page's elements and text) or "picture", "text"?: the goal}. "No change" when the \
                    page is the same as before, else one line for each answer of OpenAI Decisions. An unknown answer or a failed call gives the page too.
                    """],
            ],
            "required": ["action"],
        ],
    ],
    [
        "name": "simulator",
        "description": """
            Operate a booted iOS Simulator (Xcode 27 or later) with HID events, in the background: tap, swipe, gesture, \
            type, key, button, paste, screenshot, list, and read its screen: describe gives the front app's \
            accessibility elements (role, label, id, value, center), wait waits for an element to appear, and \
            tap with target taps the element named by a label or id. x and y are points: the pixels of the screenshot \
            action. type sends keys as a hardware keyboard: US characters, or Hangul as two-set keys when \
            the simulator's keyboard is Korean; it refuses text that the current keyboard cannot type. \
            paste puts any text on the pasteboard and uses the native three-finger editing menu when available, otherwise cmd+V; if iOS asks to allow the paste, \
            take a screenshot and tap the Allow Paste button (mac-cu puts the user's Mac pasteboard back after it). \
            hinge folds a foldable device (iPhone Duo) to degrees or a state and reads the angle back (with neither, it \
            only reads); rotate turns the device. Both answer with the screen that is then on. views gives the \
            app's UIView hierarchy with frames, hidden, alpha and Auto Layout constraints, as Xcode's view debugger \
            reads it (lldb attaches and stops the app for about 20 seconds; query narrows it to views whose class, id or label contains it). \
            gesture replays frames of up to three independent fingers as real touchscreen HID reports: each frame has time and touches (id, phase down/move/up, x, y). Use it for multi-tap, long-press drag, pinch, rotation and compound gestures. \
            window opens a borderless live device window with an opaque LCD, drag/status capsule and device menu (focus mode, size, minimize, close), bottom Home/Rotate/Fold/Capture controls and side tools. Preview opacity does not dim it. For the user to watch and use: clicks, drags, keys and scrolling in it reach the simulator. Colored numbered fingers follow sent touches and fade on lift (viewer only). It activates and focuses the window, follows folds and turns; close: true closes it.
            """,
        "inputSchema": [
            "type": "object",
            "properties": [
                "action": ["type": "string",
                           "enum": ["list", "screenshot", "describe", "wait", "tap", "swipe", "gesture", "type", "key", "button", "paste", "hinge", "rotate", "views", "press", "crown", "window"]],
                "frames": ["type": "array", "minItems": 2, "maxItems": 1201, "description": "gesture: up to three independent fingers. Times increase within 0...10 seconds after the call starts. Missing fingers remain held; moves interpolate at 60 Hz. Finish with every finger up. Coordinates are screen points; keep its orientation and hinge unchanged during the gesture.",
                           "items": ["type": "object", "required": ["time", "touches"], "properties": [
                            "time": ["type": "number", "minimum": 0, "maximum": 10],
                            "touches": ["type": "array", "maxItems": 3, "items": [
                                "type": "object", "required": ["id", "phase", "x", "y"], "properties": [
                                    "id": ["type": "integer", "minimum": 1, "maximum": 3],
                                    "phase": ["type": "string", "enum": ["down", "move", "up"]],
                                    "x": ["type": "number"], "y": ["type": "number"],
                                ],
                            ]],
                           ]]],
                "amount": ["type": "number", "description": "crown (Apple Watch): how far to turn the Digital Crown, about points of scrolling; positive scrolls down, negative up (default 60)."],
                "app": ["type": "string", "description": "views: bundle id of the app (default: the front app)."],
                "close": ["type": "boolean", "description": "window: close the window instead of opening it."],
                "degrees": ["type": "number", "description": "hinge: 0 (closed: the cover screen) to 180 (open flat: the inner screen)."],
                "state": ["type": "string", "enum": ["closed", "open"], "description": "hinge: closed is 0°, open is 180°."],
                "orientation": ["type": "string", "enum": ["portrait", "landscape-left", "landscape-right", "upside-down"], "description": "rotate."],
                "device": ["type": "string", "description": "Name or UDID of a booted simulator (from list). Not needed when only one is booted."],
                "query": ["type": "string", "description": "describe: only the elements whose label, id or value is or contains this. views: only the views (and their subviews) whose class, id or label contains this."],
                "target": ["type": "string", "description": "wait, tap, press: a label, id or value of an element (exact first, then contains). tap uses it when x and y are not given; press uses the accessibility press action instead of a touch."],
                "timeout": ["type": "number", "description": "wait (default 10), tap with target (default 5): seconds to wait for the element, at most 60."],
                "x": ["type": "number", "description": "tap, swipe: points from the left (pixels of the screenshot)."],
                "y": ["type": "number", "description": "tap, swipe: points from the top."],
                "to_x": ["type": "number", "description": "swipe: end point."],
                "to_y": ["type": "number", "description": "swipe: end point."],
                "seconds": ["type": "number", "description": "tap, button: how long to hold (long press); swipe: duration (default 0.3)."],
                "text": ["type": "string", "description": "type, paste."],
                "key": ["type": "string", "description": "key: a key or combination, for example \"Return\", \"cmd+a\", \"shift+Tab\", \"cmd+l\"."],
                "button": ["type": "string", "enum": ["home", "lock", "side", "siri"]],
                "guides": ["type": "boolean", "description": """
                    screenshot: Measure. Draw rulers, a 100 px grid and a numbered box around each element of the front \
                    app on the picture, and list those elements with their numbers, centers and sizes (points = pixels). \
                    Off by default (tokens).
                    """],
            ],
            "required": ["action"],
        ],
    ],
    [
        "name": "webinspector",
        "description": """
            The Web Inspector of WKWebView and Safari pages in booted iOS Simulators and USB devices, without \
            Safari: list the pages, then run JavaScript, see console messages, network requests (with the \
            cache source and +KA-TGT), cookies, a picture of the viewport, or send raw WebKit Inspector protocol \
            commands. Select a page with page (a ref from list, or part of its title or URL), and device or app \
            if needed. Token headers, cookie values and token query values are hidden unless asked. On a \
            simulator, a call can wait up to 12 seconds for its Web Inspector to start again.
            """,
        "inputSchema": [
            "type": "object",
            "properties": [
                "action": ["type": "string",
                           "enum": ["list", "eval", "navigate", "reload", "screenshot", "console", "network", "cookies", "watch", "send"]],
                "page": ["type": "string", "description": "All actions except list: a ref from list, or part of the page title or URL."],
                "device": ["type": "string", "description": "Part of the simulator or device name or UDID."],
                "app": ["type": "string", "description": "Part of the app name, bundle ID or PID."],
                "code": ["type": "string", "description": "eval: JavaScript; a string result as it is, others as JSON."],
                "await": ["type": "boolean", "description": "eval: wait for a Promise result."],
                "url": ["type": "string", "description": "navigate: the URL. console, network, watch: go to this URL when the collection starts."],
                "reload": ["type": "boolean", "description": "console, network, watch: reload when the collection starts."],
                "seconds": ["type": "number", "description": "console, network, watch: how long to collect (default 5, up to 60)."],
                "no_cache": ["type": "boolean", "description": "console, network, watch: turn off the web view's resource cache while collecting."],
                "headers": ["type": "boolean", "description": "network: request (>) and response (<) headers."],
                "bodies": ["type": "boolean", "description": "network: the first 500 characters of XHR and Fetch response bodies (can hold personal data)."],
                "name": ["type": "string", "description": "cookies: only cookies whose name contains this."],
                "values": ["type": "boolean", "description": "cookies: show the values."],
                "domain": ["type": "string", "description": "watch: a protocol domain whose events to collect, for example \"DOM\", \"Page\"."],
                "method": ["type": "string", "description": "send: a protocol method, for example \"DOM.getDocument\"."],
                "params": ["type": "object", "description": "send: the parameters of method."],
                "timeout": ["type": "number", "description": "Seconds to wait for each protocol answer (default 15)."],
            ],
            "required": ["action"],
        ],
    ],
    [
        "name": "decide",
        "description": """
            Ask OpenAI Decisions questions about an app's front window, page, or text. Predicate answers \
            provide probabilities; choice and score provide values and confidence. These are uncalibrated \
            and require inspection. Window or page evidence is sent to OpenAI. Use predicate, choice \
            (choices: value and description), or score (levels: label and description).
            """,
        "inputSchema": [
            "type": "object",
            "properties": [
                "questions": ["type": "object", "description": """
                    Questions by an id you choose, for example {"error": {"type": "predicate", "instructions": \
                    "Is an error dialog shown?"}, "screen": {"type": "choice", "instructions": "Which screen?", \
                    "choices": [{"value": "login", "description": "The login form"}, {"value": "home", "description": "The home screen"}]}}.
                    """],
                "app": ["type": "string", "description": "Decide about this app's front window (same name as in get_app_state)."],
                "page": ["type": "string", "enum": ["apple_events", "extension", "devtools"],
                         "description": "Decide about the current tab of this browser engine instead (its elements and text, or a screenshot); also with pick."],
                "browser": ["type": "string", "description": "page apple_events: the browser app (default \"Google Chrome\")."],
                "source": ["type": "string", "enum": ["picture", "tree"], "description": "With app: send the accessibility tree as text without buttons (tree, the default), or a screenshot (picture: for content that the tree does not show, or to check buttons)."],
                "text": ["type": "string", "description": "Text to decide about, or context for the picture."],
                "model": ["type": "string", "description": "Model name (gpt-6-luna)."],
                "pick": ["type": "string", "description": """
                    With app or page, instead of questions: a goal ("저장하지 않고 닫는다"). Returns the element of the \
                    window or page to use next, "none", or "unknown" with the tree or page. Its element numbers are \
                    valid for act (app) or browser click and fill (page).
                    """],
            ],
        ],
    ],
]

var askedForAccessibility = false

/// Asks macOS once for each process: macOS adds mac-cu.app (the daemon) to Privacy & Security > Accessibility.
/// Then the guide opens that page and shows the app's icon to drag into the list.
func requestAccessibility() -> Bool {
    if AXIsProcessTrusted() { return true }
    if !askedForAccessibility {
        askedForAccessibility = true
        _ = AXIsProcessTrustedWithOptions([kAXTrustedCheckOptionPrompt.takeUnretainedValue(): true] as CFDictionary)
        showPermissionGuide(.accessibility)
    }
    return false
}

let accessibilityHelp = """
    The accessibility API is not allowed. System Settings opened at Privacy & Security > Accessibility, \
    with a panel below it that shows mac-cu. Tell the user to drag that icon into the list (or turn mac-cu \
    on if it is in the list already), then try again. If it is still not allowed, the user quits mac-cu in \
    the menu bar (the next call starts it again) and tries again.
    """

var askedForScreenRecording = false

/// The same for Screen Recording (window screenshots), once for each process. False when it is not allowed.
func requestScreenRecording() -> Bool {
    if CGPreflightScreenCaptureAccess() { return true }
    if !askedForScreenRecording {
        askedForScreenRecording = true
        _ = CGRequestScreenCaptureAccess()
        showPermissionGuide(.screenRecording)
    }
    return false
}

let screenRecordingHelp = """
    No screenshot: Screen Recording is not allowed. System Settings opened at Privacy & Security > Screen & \
    System Audio Recording, with a panel below it that shows mac-cu. Tell the user to drag that icon into \
    the list (or turn mac-cu on if it is in the list already). macOS can ask to quit and reopen mac-cu: then \
    the user quits it in the menu bar (the next call starts it again) and asks again.
    """

/// The text when a window screenshot fails: the Screen Recording guide when that is the cause.
func noScreenshot(_ other: String) -> String { requestScreenRecording() ? other : screenRecordingHelp }

func callTool(_ name: String, _ arguments: [String: Any]) -> [String: Any] {
    // The simulator tool sends HID events to the simulator, and webinspector uses Web Inspector sockets:
    // they need no Accessibility permission.
    if name == "simulator" || name == "webinspector" {
        do { return try name == "simulator" ? simulatorTool(arguments) : webInspectorTool(arguments) } catch let error as ToolError {
            return ["content": [["type": "text", "text": error.message]], "isError": true]
        } catch {
            return ["content": [["type": "text", "text": "\(error)"]], "isError": true]
        }
    }
    guard requestAccessibility() else {
        return ["content": [["type": "text", "text": accessibilityHelp]], "isError": true]
    }
    do {
        let screenshot = arguments["screenshot"] as? Bool ?? false
        let guides = arguments["guides"] as? Bool ?? false
        switch name {
        case "get_app_state":
            return ["content": try state(of: try session(for: arguments["app"] as? String ?? ""), screenshot: screenshot, guides: guides)]
        case "act":
            guard let actions = arguments["actions"] as? [[String: Any]], !actions.isEmpty else {
                throw ToolError("act needs a list of actions.")
            }
            return try act(actions, session: try session(for: arguments["app"] as? String ?? ""),
                           foreground: arguments["foreground"] as? Bool ?? false, screenshot: screenshot, guides: guides,
                           verify: arguments["verify"] as? [String: Any], goal: arguments["goal"] as? String)
        case "browser":
            return try browserTool(arguments)
        case "decide":
            return try decideTool(arguments)
        default:
            throw ToolError("Unknown tool \(name).")
        }
    } catch let error as ToolError {
        return ["content": [["type": "text", "text": error.message]], "isError": true]
    } catch {
        return ["content": [["type": "text", "text": "\(error)"]], "isError": true]
    }
}

/// The reply to a JSON-RPC request; nil for a notification.
func handle(_ request: [String: Any]) -> [String: Any]? {
    guard let method = request["method"] as? String, let id = request["id"] else { return nil }
    let params = request["params"] as? [String: Any] ?? [:]
    var reply: [String: Any] = ["jsonrpc": "2.0", "id": id]
    switch method {
    case "initialize":
        reply["result"] = [
            "protocolVersion": params["protocolVersion"] as? String ?? "2025-06-18",
            "capabilities": ["tools": [:]],
            "serverInfo": ["name": "mac-cu", "version": bundleVersion],
        ]
    case "tools/list":
        reply["result"] = ["tools": tools]
    case "tools/call":
        reply["result"] = callTool(params["name"] as? String ?? "", params["arguments"] as? [String: Any] ?? [:])
    case "ping":
        reply["result"] = [String: Any]()
    default:
        reply["error"] = ["code": -32601, "message": "Method not found: \(method)"]
    }
    return reply
}

// Chrome starts mac-cu as the native messaging host of the mac-cu extension, with the extension's origin.
if CommandLine.arguments.dropFirst().first?.hasPrefix("chrome-extension://") == true { runNativeHost() }

// `mac-cu --mode [input=…] [show=…]` (Modes.swift): set and print the user's modes.
if let index = CommandLine.arguments.firstIndex(of: "--mode") {
    runModeCommand(Array(CommandLine.arguments.dropFirst(index + 1)))
}
// `mac-cu --request-accessibility` (setup.py): check the permission and ask for it, then exit.
if CommandLine.arguments.contains("--request-accessibility") {
    print(requestAccessibility() ? "The accessibility API is allowed." : accessibilityHelp)
    exit(0)
}
// `mac-cu --request-screen-recording` (setup.py) does the same for Screen Recording.
if CommandLine.arguments.contains("--request-screen-recording") {
    print(requestScreenRecording() ? "Screen Recording is allowed." : screenRecordingHelp)
    exit(0)
}
// The guide's check, in a new process each time. Exit 0: allowed.
if CommandLine.arguments.contains("--check-screen-recording") { exit(CGPreflightScreenCaptureAccess() ? 0 : 1) }
if let index = CommandLine.arguments.firstIndex(of: "--pick-request"), index + 2 < CommandLine.arguments.count {
    printPickRequest(treeFile: CommandLine.arguments[index + 1], goal: CommandLine.arguments[index + 2])
}
if let index = CommandLine.arguments.firstIndex(of: "--approve"), index + 1 < CommandLine.arguments.count {
    runApprovalDialog(name: CommandLine.arguments[index + 1], bundleID: CommandLine.arguments.dropFirst(index + 2).first)
}
for permission in [Permission.accessibility, .screenRecording] {
    if let index = CommandLine.arguments.firstIndex(of: permission.rawValue) {
        let paths = CommandLine.arguments.dropFirst(index + 1).map { URL(fileURLWithPath: $0) }
        runPermissionGuide(permission, app: paths.first, iconApp: paths.dropFirst().first)
    }
}

// `mac-cu --daemon` (from mac-cu.app): the menu bar daemon that runs the tools. NSApp.run keeps the main run
// loop going: NSWorkspace.runningApplications and NSRunningApplication change only then. Started by launchd
// (`open -a`, Finder), the app is the daemon too.
if CommandLine.arguments.contains("--daemon") || (getppid() == 1 && Bundle.main.bundleIdentifier == daemonBundleID) { runDaemon() }
// `mac-cu --quit-daemon` (setup.py) and `mac-cu --update` (the menu).
if CommandLine.arguments.contains("--quit-daemon") { runQuitDaemonCommand() }
if CommandLine.arguments.contains("--update") { runUpdateCommand() }
// No arguments: the MCP stdio client of one agent session.
runClient()
