import Foundation

public enum ToolCatalog {
    private static func str(_ description: String, choices: [String]? = nil) -> [String: Any] {
        var p: [String: Any] = ["type":"string", "description":description]
        if let choices { p["enum"] = choices }; return p
    }
    private static func int(_ description: String, min: Int = 0, max: Int = Int(Int32.max)) -> [String: Any] {
        ["type":"integer", "description":description, "minimum":min, "maximum":max]
    }
    private static let observation = str("Fresh observation UUID from mac_observe. Expires after 30 seconds and one target mutation.")
    private static let node = str("Node ID from this observation's AX tree.")
    private static let processStartID = str("Exact process start identity returned with this PID by mac_apps.")
    private static let route = str("process targets only PID and is app-dependent; global uses the shared system cursor/keyboard and requires foreground.", choices:["process","global"])
    private static let x: [String: Any] = ["type":"number", "minimum":-1e7, "maximum":1e7]
    private static let space = str("Coordinate units. Default window. All origins top-left.", choices:["screen","window","image","normalized"])
    private static let strings: [String: Any] = ["type":"array", "items":["type":"string"], "maxItems":8]
    private static func stringArray(_ description: String, maxItems: Int = 16) -> [String: Any] {
        ["type":"array", "description":description, "items":["type":"string"], "minItems":1, "maxItems":maxItems]
    }
    private static func spec(_ name: String, _ description: String, _ properties: [String: Any], _ required: [String],
                             read: Bool = false, destructive: Bool? = nil, idempotent: Bool? = nil, openWorld: Bool = false,
                             variants: [[String: Any]]? = nil, anyOf: [[String: Any]]? = nil) -> [String: Any] {
        var allProperties = properties
        if name != "mac_task" && name != "mac_connection" { allProperties["taskID"] = str("Optional active MacPilot task UUID. Isolates state, cursor, cancellation and deadline.") }
        if ["mac_pointer", "mac_click", "mac_drag", "mac_scroll", "mac_cursors"].contains(name) {
            allProperties["cursorID"] = str("Independent virtual cursor ID within this task; default primary. ASCII letters, digits, hyphens or underscores; at most 64 bytes.")
        }
        var schema: [String: Any] = ["type":"object", "properties":allProperties, "required":required, "additionalProperties":false]
        // Some MCP hosts render a union from each oneOf/anyOf branch and do not
        // carry the enclosing object's properties or required keys into that
        // generated signature. Make every branch a complete object schema while
        // retaining the root constraints for ordinary JSON Schema validators.
        func complete(_ alternatives: [[String: Any]]) -> [[String: Any]] {
            alternatives.map { alternative in
                var result = alternative
                var mergedProperties = allProperties
                if let specialized = alternative["properties"] as? [String: Any] {
                    for (key, value) in specialized { mergedProperties[key] = value }
                }
                var mergedRequired = required
                for key in alternative["required"] as? [String] ?? [] where !mergedRequired.contains(key) {
                    mergedRequired.append(key)
                }
                result["type"] = "object"
                result["properties"] = mergedProperties
                result["required"] = mergedRequired
                result["additionalProperties"] = false
                return result
            }
        }
        if let variants { schema["oneOf"] = complete(variants) }
        if let anyOf { schema["anyOf"] = complete(anyOf) }
        return ["name":name, "description":description, "inputSchema":schema,
                "annotations":["readOnlyHint":read, "destructiveHint":destructive ?? !read,
                               "idempotentHint":idempotent ?? read, "openWorldHint":openWorld]]
    }
    public static var tools: [[String: Any]] {
        let coords: [String: Any] = ["observation":observation, "x":x, "y":x, "space":space]
        var click = coords; click["route"] = str("Default accessibility invokes one AXPress control at this point without cursor movement. process/global send raw events.",choices:["accessibility","process","global"]); click["button"] = str("Default left; accessibility route supports only left", choices:["left","right"]); click["clicks"] = int("Single or double click; accessibility route supports only single", min:1,max:2)
        var drag = coords; drag["route"] = route; drag["toX"] = x; drag["toY"] = x
        drag["duration"] = ["type":"number", "minimum":0.05, "maximum":2]
        var scroll = coords; scroll["route"] = route
        scroll["vertical"] = int("Lines; positive up, negative down",min:-100,max:100)
        scroll["horizontal"] = int("Horizontal lines",min:-100,max:100)
        return [
            spec("mac_connection", "Diagnose this server's process identity, parent, permissions and CLI/MCP scope, or probe a separate isolated MCP. Never kills existing servers, reloads the host or retries mutations. Probe success is not host reconnection.",
                 ["operation":str("status reads this process; probe starts and cleans up one owned MCP subprocess",choices:["status","probe"]),
                  "previousServerPID":int("Previous server PID; requires previousServerStartID",min:1),
                  "previousServerStartID":str("Previous server processStartID from connection status"),
                  "previousParentPID":int("Previous parent PID; requires previousParentStartID",min:1),
                  "previousParentStartID":str("Previous parent processStartID from connection status"),
                  "timeoutMs":int("Probe-only deadline; default 10000, plus bounded child cleanup",min:500,max:30000)], ["operation"],read:true),
            spec("mac_task", "Begin, inspect, cancel or finish isolated MacPilot work. Background preservation is the default. Cancellation interrupts active task calls.",
                 ["operation":str("Task operation", choices:["begin","list","status","cancel","finish"]),
                  "taskID":str("Task UUID for status, cancel and finish"), "goal":str("Explicit task intent; up to 4096 UTF-8 bytes"),
                  "expected":str("Explicit expected postcondition; up to 4096 UTF-8 bytes"), "pid":int("Optional bound PID",min:1),
                  "processStartID":processStartID, "windowID":int("Optional bound window",min:1,max:Int(UInt32.max)),
                  "preserveForeground":["type":"boolean","default":true],
                  "durationSeconds":int("Deadline from creation; default 1800 seconds",min:1,max:28800)], ["operation"]),
            spec("mac_cursors", "List/remove virtual cursors or hide/show desktop arrows and target highlight. Independent of preview visibility; no system events.",
                 ["operation":str("Cursor operation",choices:["list","remove","hide","show"]), "observation":observation], ["operation","observation"]),
            spec("mac_private", "Inspect private SPI exports or explicitly map AX windows to WindowServer IDs. Exported research symbols are not called.",
                 ["operation":str("Private API operation",choices:["catalog","window_ids"]), "enabled":["type":"boolean","default":false],
                  "pid":int("Owner PID",min:1), "processStartID":processStartID], ["operation"],read:true),
            spec("mac_preview", "Control this task's non-activating live window preview, independent cursors and click-through desktop overlays.",
                 ["operation":str("Preview operation",choices:["start","status","hide","show","pause","resume","stop","overlay"]),
                  "observation":observation, "enabled":["type":"boolean"], "timeoutMs":int("Acknowledgement deadline; default 10000",min:100,max:20000)], ["operation"]),
            spec("mac_files", "Inspect/search selected directories, read/write UTF-8, copy/move, create directories or set Finder tags. Destinations are never silently overwritten.",
                 ["operation":str("File operation",choices:["stat","list","search","read","write","copy","move","mkdir","tags"]),
                  "path":str("Explicit absolute selected path"),"destination":str("Explicit new copy/move destination"),
                  "text":str("Explicit UTF-8 content; up to 1 MiB"),"overwrite":["type":"boolean","default":false],
                  "tags":strings,"query":str("Literal filename query"),"limit":int("Result limit; default 100",min:1,max:1000),
                  "maxDepth":int("Search depth; default 8",min:1,max:32),"maxBytes":int("Text read limit; default 65536",min:1,max:1048576),
                  "includeHidden":["type":"boolean"],"timeoutMs":int("Deadline; external filesystem work may continue after timeout",min:100,max:60000)], ["operation","path"]),
            spec("mac_system", "Read system display/power state or explicitly read/write output audio volume and mute through CoreAudio.",
                 ["operation":str("System operation",choices:["info","audio"]),"volume":["type":"number","minimum":0,"maximum":1],"muted":["type":"boolean"]], ["operation"]),
            spec("mac_improvement", "Queue and deduplicate sanitized failures, configure an explicit Codex destination, send requests through app-server, and reconcile durable thread/turn receipts. Diagnosis does not deploy a fix.",
                 ["operation":str("Improvement operation",choices:["configure","report","list","status","send","reconcile"]),"requestID":str("Existing improvement UUID"),
                  "title":str("Explicit report title"),"tool":str("Failing tool"),"code":str("Failure category"),"goal":str("Explicit task intent"),"expected":str("Expected postcondition"),"actual":str("Observed failure"),
                  "evidencePaths":strings,"codexPath":str("Explicit installed Codex executable"),"cwd":str("Explicit diagnostic workspace"),
                  "automaticSend":["type":"boolean","default":false],"ephemeral":["type":"boolean","default":false],"threadID":str("Optional dedicated Codex thread UUID"),
                  "model":str("Optional explicit model; omitted preserves configuration"),"effort":str("Optional explicit effort; omitted preserves configuration"),
                  "timeoutMs":int("Send or reconciliation deadline",min:1000,max:300000)], ["operation"],openWorld:true),
            spec("mac_browser_developer", "Inspect or prepare Safari/Chrome developer settings. Enable shows a native user confirmation; the agent must never click that dialog. No approval flag bypass. Prepare/enable require a foreground task.",
                 ["operation":str("status reads currently open UI; prepare opens settings without changing toggles; enable asks the user before one change",choices:["status","prepare","enable"]),
                  "browser":str("Exact running browser",choices:["safari","chrome"]),
                  "setting":str("Safari developer_features/javascript_apple_events; Chrome extension_developer_mode",choices:["developer_features","javascript_apple_events","extension_developer_mode"]),
                  "pid":int("Browser PID from mac_apps",min:1),"processStartID":processStartID,
                  "windowID":int("Required exact Chrome window ID; selects that window's profile",min:1,max:Int(UInt32.max)),
                  "timeoutMs":int("Native approval deadline; default 60000",min:5000,max:120000)], ["operation","browser","setting","pid","processStartID"],openWorld:true),
            spec("mac_browser", "Control an explicitly connected browser through a local native-messaging extension. DOM snapshots expire and mutations consume them. No cookie or credential access.",
                 ["operation":str("Browser operation",choices:["connections","install_host","receipt","tabs","open","select","close","navigate","back","forward","reload","frames","observe","click","fill","select_option","scroll","key","verify","wait","upload","download","download_status","screenshot"]),
                  "connectionID":str("Connected browser UUID"),"requestID":str("Existing command receipt UUID"),"tabID":int("Exact tab ID from tabs",min:1),"frameID":int("Frame ID from frames"),
                  "observation":observation,"node":node,"url":str("Explicit http, https or local file URL; about:blank is also supported"),"activate":["type":"boolean","default":false],
                  "text":str("Explicit text or option value"),"equals":str("Exact text predicate"),"contains":str("Literal text predicate"),
                  "x":x,"y":x,"key":str("DOM key; native shortcuts use mac_key"),"maxNodes":int("Snapshot node limit",min:1,max:500),
                  "path":str("Explicit upload file; at most 32 MiB"),"mime":str("Explicit upload MIME type"),"filename":str("Relative download filename"),"downloadID":int("Download ID"),
                  "extensionID":str("Installed Chromium extension ID"),"browser":str("Browser backend; Safari uses explicit Apple Events and requires its JavaScript permission for DOM actions",choices:["chrome","edge","chromium","safari"]),
                  "manifestDirectory":str("Optional explicit native-host manifest directory; default is the selected browser's user directory"),
                  "timeoutMs":int("Response deadline; reconcile timed-out mutations with receipt",min:100,max:60000)], ["operation"],openWorld:true),
            spec("mac_doctor", "Read local permissions, displays, secure-input state and backend limitations. Does not request permissions.", [:], [], read:true),
            spec("mac_apps", "List running native GUI apps and PIDs.", [:], [], read:true),
            spec("mac_windows", "List native windows with owner PID, windowID and global logical frame.", ["pid":int("Optional owner PID",min:1)], [], read:true),
            spec("mac_record", "Record an explicitly selected window or display and system audio to a private local MP4 (macOS 15+). No microphone. Inspect local movie tracks, decoded audio energy and sampled frames.",
                 ["operation":str("Bounded recording or saved-movie inspection",choices:["record","inspect"]),
                  "source":str("Capture scope; window audio includes its owning application",choices:["window","display"]),
                  "pid":int("Window owner PID from mac_apps",min:1),"processStartID":processStartID,
                  "windowID":int("Exact selected window ID",min:1,max:Int(UInt32.max)),"displayID":int("Exact display ID from mac_doctor",min:1,max:Int(UInt32.max)),
                  "region":["type":"object","description":"Optional source=display crop in display-relative logical points. Includes visible composited pixels and all system audio; not an independent window.","properties":["x":["type":"number","minimum":0],"y":["type":"number","minimum":0],"width":["type":"number","minimum":1],"height":["type":"number","minimum":1]],"required":["x","y","width","height"],"additionalProperties":false],
                  "durationSeconds":["type":"number","minimum":1,"maximum":120,"default":10],
                  "maxDimension":int("Maximum encoded dimension; default 1920",min:320,max:3840),"fps":int("Maximum frame rate; default 30",min:1,max:60),
                  "systemAudio":["type":"boolean","default":true],"showsCursor":["type":"boolean","default":false],
                  "path":str("Explicit existing local movie for inspect; <=1 GiB, <=600 seconds"),"frames":int("inspect sampled PNG count; default 3",min:0,max:6)], ["operation"]),
            spec("mac_capture", "Capture the complete selected display without the cursor to a private local PNG. Use a display ID returned by mac_doctor.",
                 ["displayID":int("Active display ID from mac_doctor",min:1,max:Int(UInt32.max)),
                  "maxDimension":int("Maximum output pixel width or height; default 1600. A 16777216-pixel safety cap also applies.",min:1,max:8192),
                  "timeoutMs":int("Total ScreenCaptureKit discovery and capture timeout; default 10000",min:100,max:60000)], ["displayID"], read:true),
            spec("mac_menu", "List one app's complete bounded top-level menu bar or press one exact unique title path through Accessibility.",
                 ["pid":int("Running application PID",min:1), "operation":str("Menu operation",choices:["list","press"]),
                  "processStartID":processStartID,
                  "titlePath":["type":"array", "description":"Exact menu title path for press only", "items":["type":"string","description":"Nonempty title, at most 512 UTF-8 bytes","minLength":1,"maxLength":512], "minItems":1, "maxItems":8],
                  "maxItemsPerLevel":int("Traversal limit for each menu level; default 64",min:1,max:128)], ["pid","operation"],
                 destructive:true, idempotent:false,
                 variants:[
                    ["properties":["operation":["const":"list"]],
                     "not":["anyOf":[["required":["titlePath"]],["required":["processStartID"]]]]],
                    ["properties":["operation":["const":"press"]], "required":["titlePath","processStartID"]]
                 ]),
            spec("mac_window", "Read or change the window bound to one fresh observation. Mutations consume the observation; full-screen remains explicitly unverified.",
                 ["observation":observation,
                  "operation":str("Window operation",choices:["state","raise","close","minimize","unminimize","toggle_full_screen","move","resize"]),
                  "x":["type":"number","description":"Global logical x coordinate for move","minimum":-1e7,"maximum":1e7],
                  "y":["type":"number","description":"Global logical y coordinate for move","minimum":-1e7,"maximum":1e7],
                  "width":["type":"number","description":"Positive logical width for resize","exclusiveMinimum":0,"maximum":1e7],
                  "height":["type":"number","description":"Positive logical height for resize","exclusiveMinimum":0,"maximum":1e7]], ["observation","operation"],
                 destructive:true, idempotent:false,
                 variants:[
                    ["properties":["operation":["enum":["state","raise","close","minimize","unminimize","toggle_full_screen"]]],
                     "not":["anyOf":[["required":["x"]],["required":["y"]],["required":["width"]],["required":["height"]]]]],
                    ["properties":["operation":["const":"move"]], "required":["x","y"],
                     "not":["anyOf":[["required":["width"]],["required":["height"]]]]],
                    ["properties":["operation":["const":"resize"]], "required":["width","height"],
                     "not":["anyOf":[["required":["x"]],["required":["y"]]]]]
                 ]),
            spec("mac_launch", "Launch an installed app by bundle ID and return its PID plus processStartID. Activation defaults false.",
                 ["bundleID":str("Installed app bundle ID"), "activate":["type":"boolean"],
                  "timeoutMs":int("NSWorkspace response timeout; default 10000. A timed-out launch may still complete.",min:100,max:60000)], ["bundleID"]),
            spec("mac_app", "Change one running app's lifecycle state and verify the bounded postcondition.",
                 ["pid":int("Running application PID",min:1), "processStartID":processStartID,
                  "action":str("Lifecycle action",choices:["activate","hide","unhide","terminate","force_terminate"]),
                  "timeoutMs":int("Verification timeout in milliseconds; default 3000",min:100,max:10000)], ["pid","processStartID","action"]),
            spec("mac_open", "Open one existing local file URL or http/https URL, optionally with an installed bundle ID.",
                 ["url":str("Absolute file, http, or https URL; maximum 8192 UTF-8 bytes"), "bundleID":str("Optional installed application bundle ID"),
                  "activate":["type":"boolean", "default":true],
                  "timeoutMs":int("NSWorkspace response timeout; default 10000. A timed-out open may still complete.",min:100,max:60000)], ["url"], destructive:false, idempotent:false, openWorld:true),
            spec("mac_reveal", "Reveal 1 to 16 explicit existing absolute paths in Finder.",
                 ["paths":stringArray("Existing absolute paths; no glob or shell expansion"),
                  "timeoutMs":int("Finder request timeout; default 10000. A timed-out reveal may still complete.",min:100,max:60000)], ["paths"], destructive:false, idempotent:true),
            spec("mac_trash", "Move 1 to 16 explicit existing absolute paths to Trash through NSWorkspace.recycle.",
                 ["paths":stringArray("Existing absolute paths; no glob or shell expansion"),
                  "timeoutMs":int("Completion timeout in milliseconds; default 30000",min:100,max:60000)], ["paths"]),
            spec("mac_clipboard_read", "Read an explicitly requested bounded plain-text value from the general clipboard.",
                 ["maxBytes":int("Maximum returned UTF-8 bytes; default 65536",min:1,max:1048576)], [], read:true, idempotent:false),
            spec("mac_clipboard_write", "Replace the general clipboard with explicit plain text and verify the round trip.",
                 ["text":str("Plain text; maximum 1048576 UTF-8 bytes")], ["text"]),
            spec("mac_shortcuts", "List, run, or view Apple Shortcuts through the fixed /usr/bin/shortcuts executable with bounded time and output.",
                 ["operation":str("Shortcuts operation",choices:["list","run","view"]), "name":str("Shortcut name or identifier for run/view"),
                  "folder":str("Optional folder for list"), "folders":["type":"boolean"], "showIdentifiers":["type":"boolean"],
                  "inputPaths":stringArray("Existing absolute run input paths"), "outputPath":str("Absolute run output path"),
                  "outputType":str("Run output UTI"), "timeoutMs":int("Timeout in milliseconds; default 30000",min:100,max:60000),
                  "maxOutputBytes":int("Maximum bytes retained for each output stream; default 65536",min:1,max:1048576)],
                 ["operation"], destructive:true, idempotent:false, openWorld:true,
                 variants:[
                    ["properties":["operation":["const":"list"]],
                     "not":["anyOf":[["required":["name"]],["required":["inputPaths"]],["required":["outputPath"]],["required":["outputType"]],
                                        ["properties":["folders":["const":true]],"required":["folder","folders"]]]]],
                    ["properties":["operation":["const":"run"]], "required":["name"],
                     "not":["anyOf":[["required":["folder"]],["required":["folders"]],["required":["showIdentifiers"]]]]],
                    ["properties":["operation":["const":"view"]], "required":["name"],
                     "not":["anyOf":[["required":["folder"]],["required":["folders"]],["required":["showIdentifiers"]],
                                        ["required":["inputPaths"]],["required":["outputPath"]],["required":["outputType"]]]]]
                 ]),
            spec("mac_script", "Run explicit AppleScript or JavaScript source through fixed /usr/bin/osascript stdin with bounded time and output; no shell interpolation.",
                 ["language":str("OSA language",choices:["applescript","javascript"]), "source":str("Source text; maximum 131072 UTF-8 bytes"),
                  "timeoutMs":int("Timeout in milliseconds; default 10000",min:100,max:60000),
                  "maxOutputBytes":int("Maximum bytes retained for each output stream; default 65536",min:1,max:1048576)],
                 ["language","source"], destructive:true, idempotent:false, openWorld:true),
            spec("mac_permission", "Request a macOS permission, or open native System Settings with a small attached icon guide. User drag is the default; the guide offers optional auto-add. Requires a foreground-capable task and the shared input lease. User approval in System Settings is required.",
                 ["kind":str("Permission",choices:["all","accessibility","screenCapture","postEvent","inputMonitoring","automation","fullDiskAccess","files","clipboard"]),
                  "operation":str("Default request shows the OS prompt for the four system permissions; setup opens native System Settings with an attached drag icon. all guides through required lists and Safari Automation",choices:["request","setup"]),
                  "targetBundleID":str("Automation target for setup; default com.apple.Safari"),
                  "timeoutMs":int("Native setup/request timeout; default 10000. A timed-out request may still complete.",min:100,max:60000)], ["kind"]),
            spec("mac_observe", "Capture one app window and a bounded AX tree. Returns short-lived node IDs and a local PNG. Partial coverage never proves absence.",
                 ["pid":int("Running owner PID",min:1), "processStartID":processStartID,
                  "windowID":int("Optional exact window ID",min:1,max:Int(UInt32.max)),
                  "screenshot":["type":"boolean", "default":true], "maxNodes":int("Default 200",min:1,max:1000), "maxDepth":int("Default 10",min:1,max:30),
                  "privateAPI":["type":"boolean","default":false,"description":"Explicitly use private _AXUIElementGetWindow to disambiguate overlapping windows."],
                  "captureTimeoutMs":int("ScreenCaptureKit discovery and window-capture timeout; default 10000",min:100,max:60000)], ["pid","processStartID"], read:true),
            spec("mac_activate", "Explicitly bring the observed app to foreground. Consumes observation.", ["observation":observation], ["observation"]),
            spec("mac_focus", "Activate one observed app, restore and select its exact window and optional input node; verify all three focus states. Consumes observation.",
                 ["observation":observation, "node":node, "timeoutMs":int("Focus verification deadline; default 2000",min:100,max:10000)], ["observation"]),
            spec("mac_ax", "Act on one fresh AX node: focus, set literal value, select UTF-16 range, or perform an exposed action. Consumes observation.",
                 ["observation":observation,"node":node,"operation":str("Operation",choices:["focus","set_value","select_range","action"]),
                  "action":str("Exposed action name, default AXPress"),"text":str("Literal replacement text"),"start":int("UTF-16 start"),"length":int("UTF-16 length")], ["observation","node","operation"],
                 variants:[
                    ["properties":["operation":["const":"focus"]],
                     "not":["anyOf":[["required":["action"]],["required":["text"]],["required":["start"]],["required":["length"]]]]],
                    ["properties":["operation":["const":"set_value"]], "required":["text"],
                     "not":["anyOf":[["required":["action"]],["required":["start"]],["required":["length"]]]]],
                    ["properties":["operation":["const":"select_range"]], "required":["start","length"],
                     "not":["anyOf":[["required":["action"]],["required":["text"]]]]],
                    ["properties":["operation":["const":"action"]],
                     "not":["anyOf":[["required":["text"]],["required":["start"]],["required":["length"]]]]]
                 ]),
            spec("mac_pointer", "Move and display a virtual arrow on the actual macOS desktop. label describes the action or target; cursorID stays internal. No system events.",coords.merging(["label":str("Meaningful action or target, e.g. Search input or Save button; at most 128 UTF-8 bytes")]) { _,new in new },["observation","x","y"]),
            spec("mac_click", "Default: press one enabled AXPress control covering the virtual coordinate. Raw PID/global events require an explicit route. Always verify the postcondition.",click,["observation","x","y"],
                 variants:[
                    ["properties":["route":["const":"accessibility"],"button":["const":"left"],"clicks":["const":1]]],
                    ["properties":["route":["enum":["process","global"]]],"required":["route"]]
                 ]),
            spec("mac_drag", "Send bounded left-button drag with balanced release. Default PID route; background acceptance is app-specific.",drag,["observation","x","y","toX","toY"]),
            spec("mac_scroll", "Send nonzero scroll lines at an observed window point. Default PID route; verify actual scroll result.",scroll,["observation","x","y"],
                 anyOf:[
                    ["properties":["vertical":["type":"integer","minimum":-100,"maximum":-1]],"required":["vertical"]],
                    ["properties":["vertical":["type":"integer","minimum":1,"maximum":100]],"required":["vertical"]],
                    ["properties":["horizontal":["type":"integer","minimum":-100,"maximum":-1]],"required":["horizontal"]],
                    ["properties":["horizontal":["type":"integer","minimum":1,"maximum":100]],"required":["horizontal"]]
                 ]),
            spec("mac_key", "Send one physical key shortcut with balanced down/up to a currently focused observed AX node. No persistent held keys.",
                 ["observation":observation,"node":node,"route":route,"key":str("US physical key name: a, return, left, f1, etc."),"modifiers":strings],["observation","node","key"]),
            spec("mac_type", "Send literal Unicode without clipboard access or IME composition. Requires the current focused AX node. Prefer mac_ax set_value where supported.",
                 ["observation":observation,"node":node,"route":route,"text":str("Literal text, maximum 8192 UTF-8 bytes")],["observation","node","text"]),
            spec("mac_find", "Filter the bounded nodes already stored in one fresh observation snapshot. Partial observation coverage still applies.",
                 ["observation":observation, "role":str("Exact AX role"), "title":str("Exact title"),
                  "identifier":str("Exact accessibility identifier"), "valueContains":str("Literal substring in the captured nonsecure value"),
                  "maxResults":int("Maximum returned matches; default 20",min:1,max:100)], ["observation"], read:true,
                 anyOf:[["required":["role"]],["required":["title"]],["required":["identifier"]],["required":["valueContains"]]]),
            spec("mac_ocr", "Run Apple's local Vision OCR on the observation PNG; returns top-left image-pixel boxes. No model download or network.",
                 ["observation":observation,"languages":strings,
                  "timeoutMs":int("Vision OCR timeout; default 30000",min:100,max:60000)],["observation"],read:true),
            spec("mac_wait", "Wait a bounded time for one observed AX node's live plain-text value to equal or contain a literal string. Does not consume the observation.",
                 ["observation":observation,"node":node,"equals":str("Exact expected text"),"contains":str("Expected substring"),
                  "timeoutMs":int("Wait timeout in milliseconds; default 5000",min:50,max:10000),
                  "pollMs":int("Polling interval in milliseconds; default 100",min:50,max:1000)], ["observation","node"], read:true,
                 variants:[["required":["equals"],"not":["required":["contains"]]],
                           ["required":["contains"],"not":["required":["equals"]]]]),
            spec("mac_verify", "Check exactly one equals/contains predicate against the observed AX node's live text value. Reports only that predicate.",
                 ["observation":observation,"node":node,"equals":str("Exact expected text"),"contains":str("Expected substring")],["observation","node"],read:true,
                 variants:[["required":["equals"],"not":["required":["contains"]]],
                           ["required":["contains"],"not":["required":["equals"]]]])
        ]
    }
}

public enum RPC {
    public static func success(id: Any, result: Any) -> [String: Any] { ["jsonrpc":"2.0", "id":id, "result":result] }
    public static func failure(id: Any, code: Int, message: String) -> [String: Any] { ["jsonrpc":"2.0", "id":id, "error":["code":code,"message":message]] }
    public static func initialize(_ parameters: [String: Any]) -> [String: Any] {
        let supported = ["2024-11-05","2025-03-26","2025-06-18","2025-11-25"]
        let requested = parameters["protocolVersion"] as? String ?? ""
        return ["protocolVersion":supported.contains(requested) ? requested : "2025-11-25",
                "serverInfo":["name":"macpilot","version":MacPilotRuntime.version], "capabilities":["tools":["listChanged":false]],
                "instructions":"Local macOS tools use Apple frameworks and fixed system executables. No language model or shell interpolation. Open URLs, Shortcuts, and OSA scripts can invoke apps or external resources. Reobserve after UI mutations and verify the requested postcondition."]
    }
}
