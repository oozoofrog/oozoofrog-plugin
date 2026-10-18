import AppKit
import Carbon
import ScreenCaptureKit
import CryptoKit

@MainActor public final class Engine {
    public let store: Store
    public let baseStore: Store
    public let taskRecord: TaskRecord?
    public let cursorID: String
    public let transport: InvocationTransport
    private var inputMonitor: UserInputMonitor?
    public init(store: Store, baseStore: Store? = nil, task: TaskRecord? = nil, cursorID: String = "primary", transport: InvocationTransport = .cli) {
        self.store = store; self.baseStore = baseStore ?? store; self.taskRecord = task; self.cursorID = cursorID
        self.transport = transport
    }
    public func call(_ tool: String, arguments: [String: Any]) async throws -> [String: Any] {
        do { return Outcomes.attach(tool, arguments: arguments, value: try await routeCall(tool, arguments: arguments)) }
        catch let error as ToolFailure {
            if error.outcome != nil { throw error }
            throw ToolFailure(error.code, error.description, improvementRequestID: error.improvementRequestID,
                              outcome: Outcomes.failure(tool, arguments: arguments, beforeDispatch: true))
        }
    }
    private func routeCall(_ tool: String, arguments: [String: Any]) async throws -> [String: Any] {
        // Diagnostics must remain available while a task owns the execution lock.
        if tool == "mac_connection" { return try await ConnectionDiagnostics.call(Arguments(arguments), transport: transport) }
        if tool == "mac_workflow", ["runs","run_status"].contains(arguments["operation"] as? String ?? "") {
            var value = arguments; var selected = store
            if value["taskID"] != nil { selected = try Tasks.state(Arguments(value).string("taskID"),in:baseStore); value.removeValue(forKey:"taskID") }
            return try Workflows.inspect(Arguments(value),store:selected)
        }
        if tool == "mac_task" {
            let lease = try baseStore.lease(".tasks.lock")
            defer { withExtendedLifetime(lease) {} }
            return try Tasks.call(Arguments(arguments), store: baseStore)
        }
        var input = arguments
        let cursor = try Arguments(input).string("cursorID", default: "primary", limit: 64)
        _ = try Store.pointerName(cursor)
        input.removeValue(forKey: "cursorID")
        if input["taskID"] != nil {
            let record = try Tasks.load(Arguments(input).string("taskID"), in: baseStore)
            try Tasks.requireActive(record)
            input.removeValue(forKey: "taskID")
            if let pid = record.pid, let requested = input["pid"] as? NSNumber, requested.int32Value != pid {
                throw ToolFailure("task_target_mismatch", "This task is bound to a different application")
            }
            if let window = record.windowID, let requested = input["windowID"] as? NSNumber, requested.uint32Value != window {
                throw ToolFailure("task_target_mismatch", "This task is bound to a different window")
            }
            if tool == "mac_observe", input["windowID"] == nil, let window = record.windowID { input["windowID"] = window }
            let engine = Engine(store: try Tasks.state(record.id, in: baseStore), baseStore: baseStore, task: record, cursorID: cursor, transport: transport)
            let worker = Task { @MainActor in try await engine.execute(tool, arguments: input) }
            let monitor = Task { @MainActor in
                while !Task.isCancelled {
                    do {
                        let current = try Tasks.load(record.id, in: baseStore)
                        if current.status == "interrupted" { return }
                        try Tasks.requireActive(current)
                        try await Task.sleep(nanoseconds: 80_000_000)
                    } catch {
                        if !Task.isCancelled { worker.cancel() }
                        return
                    }
                }
            }
            defer { monitor.cancel() }
            var result = try await withTaskCancellationHandler(operation: { try await worker.value }, onCancel: { worker.cancel() })
            result["taskID"] = record.id
            return result
        }
        return try await Engine(store: store, baseStore: baseStore, cursorID: cursor, transport: transport).execute(tool, arguments: input)
    }
    private func execute(_ tool: String, arguments: [String: Any], reuseLease:Bool = false) async throws -> [String: Any] {
        let requestedPID = auditPID(arguments)
        var leases: [StateLease] = []
        var enteredDispatch = false
        var trace: TraceScope?, tracePreparationError: String?
        var actionStarted = DispatchTime.now().uptimeNanoseconds
        defer { inputMonitor = nil; withExtendedLifetime(leases) {} }
        do {
            try Task.checkCancellation()
            if !reuseLease { leases.append(try store.lease(".execution.lock")) }
            if let pid = requestedPID {
                if let expected = taskRecord?.pid, expected != pid { throw ToolFailure("task_target_mismatch", "Observation belongs to a different target") }
                // PID-level serialization is conservative across relaunches. The
                // operation validates its full arguments and start identity itself.
                if !reuseLease { leases.append(try baseStore.lease(".target-\(pid).lock")) }
            }
            let foregroundAction = arguments["route"] as? String == "global" || tool == "mac_activate" || tool == "mac_focus"
                || (tool == "mac_workflow" && arguments["allowGlobalInput"] as? Bool == true)
                || tool == "mac_permission"
                || (tool == "mac_browser_developer" && arguments["operation"] as? String != "status")
                || (tool == "mac_app" && arguments["action"] as? String == "activate")
                || ((tool == "mac_launch" || tool == "mac_open") && (arguments["activate"] as? Bool ?? (tool == "mac_open")))
            if taskRecord?.preserveForeground == true,
               foregroundAction || tool == "mac_script" || (tool == "mac_shortcuts" && arguments["operation"] as? String != "list") {
                throw ToolFailure("foreground_required", "Use a task with preserveForeground=false for foreground input, activation or unrestricted scripts")
            }
            if !reuseLease, foregroundAction || tool == "mac_script" || tool == "mac_shortcuts" {
                leases.append(try baseStore.lease(".system-input.lock"))
            }
            try Task.checkCancellation()
            let foreground = NSWorkspace.shared.frontmostApplication?.processIdentifier
            do { trace = try await Tracing.begin(tool:tool,arguments:arguments,engine:self) }
            catch { tracePreparationError = (error as? ToolFailure)?.code ?? "trace_preparation_failed" }
            try Task.checkCancellation()
            actionStarted = DispatchTime.now().uptimeNanoseconds
            enteredDispatch = true
            var result = try await dispatch(tool, Arguments(arguments))
            if let reason = result["reasonCode"] as? String,
               ["user_input_interrupted","input_monitor_lost"].contains(reason), let taskRecord {
                try Tasks.interrupt(taskRecord.id, reason: reason, store: baseStore)
                result["taskStatus"] = "interrupted"
            }
            if taskRecord?.preserveForeground == true, foreground != NSWorkspace.shared.frontmostApplication?.processIdentifier {
                throw ToolFailure("foreground_changed", "Foreground changed during this background operation; reconcile user activity and the target before retrying")
            }
            result["verification"] = result["verification"] ?? "Only the operation-specific status is verified; observe the requested business postcondition"
            result = Outcomes.attach(tool, arguments: arguments, value: result)
            if let trace {
                do {
                    let id = try await Tracing.finish(trace,tool:tool,status:result["status"] as? String ?? "unknown",
                                                      outcome:Outcomes.result(tool,arguments:arguments,value:result),
                                                      elapsedMilliseconds:Int((DispatchTime.now().uptimeNanoseconds-actionStarted)/1_000_000),
                                                      skipAfterCapture:inputMonitor?.reason != nil,engine:self)
                    result["traceID"] = id
                } catch { result["trace"] = ["status":"recording_failed","code":(error as? ToolFailure)?.code ?? "trace_failed","actionMustNotBeRepeated":true] }
            } else if let tracePreparationError { result["trace"] = ["status":"preparation_failed","code":tracePreparationError] }
            let resultPID = (result["pid"] as? NSNumber)?.int32Value
            store.audit(tool: tool, status: result["status"] as? String ?? "ok", pid: resultPID ?? requestedPID)
            return result
        } catch {
            let status = error is CancellationError ? "cancelled" : (error as? ToolFailure)?.code ?? "error"
            store.audit(tool: tool, status: status, pid: requestedPID)
            let requestID = await Improvements.capture(error,tool:tool,task:taskRecord,store:baseStore)
            let failure = error as? ToolFailure
            if let trace {
                _ = try? await Tracing.finish(trace,tool:tool,status:status,
                                              outcome:failure?.outcome ?? Outcomes.failure(tool,arguments:arguments,beforeDispatch:!enteredDispatch),
                                              elapsedMilliseconds:Int((DispatchTime.now().uptimeNanoseconds-actionStarted)/1_000_000),
                                              skipAfterCapture:inputMonitor?.reason != nil,engine:self)
            }
            if let reason = failure?.code, ["user_input_interrupted","input_monitor_lost"].contains(reason), let taskRecord {
                try? Tasks.interrupt(taskRecord.id, reason: reason, store: baseStore)
            }
            if error is CancellationError { throw error }
            throw ToolFailure(failure?.code ?? "native_error", failure?.description ?? error.localizedDescription,
                              improvementRequestID: requestID ?? failure?.improvementRequestID,
                              outcome: failure?.outcome ?? Outcomes.failure(tool, arguments: arguments, beforeDispatch: !enteredDispatch))
        }
    }
    private func auditPID(_ arguments: [String: Any]) -> Int32? {
        if let number = arguments["pid"] as? NSNumber, CFGetTypeID(number) != CFBooleanGetTypeID(), number.int64Value > 0,
           number.int64Value <= Int64(Int32.max) {
            return number.int32Value
        }
        guard let id = arguments["observation"] as? String else { return nil }
        return (try? store.load(id))?.pid
    }
    func checkWorkflowState() throws {
        try Task.checkCancellation(); try inputMonitor?.verify()
        if let taskRecord { try Tasks.requireActive(Tasks.load(taskRecord.id,in:baseStore)) }
    }
    func executeWorkflowStep(_ tool:String,arguments:[String:Any]) async throws -> [String:Any] {
        guard ["mac_ax","mac_key"].contains(tool) else { throw ToolFailure("invalid_workflow","Unsupported nested tool") }
        try checkWorkflowState()
        return try await execute(tool,arguments:arguments,reuseLease:true)
    }
    public func windowRows(pid: Int32? = nil) -> [[String: Any]] {
        (CGWindowListCopyWindowInfo([.optionAll, .excludeDesktopElements], kCGNullWindowID) as? [[String: Any]] ?? []).compactMap { row in
            guard let p = (row[kCGWindowOwnerPID as String] as? NSNumber)?.int32Value,
                  pid == nil || pid == p,
                  let id = (row[kCGWindowNumber as String] as? NSNumber)?.uint32Value,
                  let bounds = row[kCGWindowBounds as String] as? [String: Any],
                  let r = CGRect(dictionaryRepresentation: bounds as CFDictionary), r.width > 1, r.height > 1 else { return nil }
            return ["pid":p, "windowID":id, "layer":row[kCGWindowLayer as String] as? Int ?? 0, "owner":row[kCGWindowOwnerName as String] as? String ?? "",
                    "title":row[kCGWindowName as String] as? String ?? "", "frame":Rect(r).object,
                    "onScreen":row[kCGWindowIsOnscreen as String] as? Bool ?? false]
        }
    }
    public func fresh(_ a: Arguments) throws -> Observation {
        let observation = try store.load(a.string("observation"))
        if let window = taskRecord?.windowID, window != observation.windowID {
            throw ToolFailure("task_target_mismatch", "Observation belongs to a different window")
        }
        try Geometry.validateAge(observation)
        let metadata = try ProcessIdentity.withStableIdentity(pid: observation.pid, expected: observation.processStartID) {
            guard let app = NSRunningApplication(processIdentifier: observation.pid), !app.isTerminated else {
                throw ToolFailure("app_metadata_unavailable", "AppKit metadata is temporarily unavailable for this process identity; reobserve before input")
            }
            return (bundleID: app.bundleIdentifier ?? "", launchTime: app.launchDate?.timeIntervalSince1970 ?? 0)
        }.value
        guard metadata.bundleID == observation.bundleID,
              abs(metadata.launchTime - observation.launchTime) < 0.001,
              let row = windowRows(pid: observation.pid).first(where: { ($0["windowID"] as? UInt32) == observation.windowID }),
              let object = row["frame"] as? [String: Double],
              object == observation.windowFrame.object else { throw ToolFailure("stale_observation", "App identity or window geometry changed") }
        _ = try AX.root(observation)
        return observation
    }
    public func observe(pid: Int32, processStartID: String, windowID: UInt32?, screenshot: Bool, maxNodes: Int, maxDepth: Int,
                        captureTimeoutMilliseconds: Int = 10_000, privateAPI: Bool = false, collectionTimeoutMilliseconds: Int = 5000) async throws -> Observation {
        let metadata = try ProcessIdentity.withStableIdentity(pid: pid, expected: processStartID) {
            guard let app = NSRunningApplication(processIdentifier: pid), !app.isTerminated else {
                throw ToolFailure("app_metadata_unavailable", "AppKit metadata is temporarily unavailable for this process identity; reobserve before input")
            }
            return (bundleID: app.bundleIdentifier ?? "", launchTime: app.launchDate?.timeIntervalSince1970 ?? 0)
        }.value
        let rows = windowRows(pid: pid)
        let windows = try AX.windows(pid)
        let row: [String: Any]?
        if let windowID { row = rows.first { ($0["windowID"] as? UInt32) == windowID } }
        else {
            // WindowServer also lists offscreen menu/utility surfaces at layer zero.
            // Prefer a visible surface that actually corresponds to an AX application window.
            let matching = rows.filter { candidate in
                guard let object = candidate["frame"] as? [String: Double] else { return false }
                return windows.contains { AX.frame($0)?.object == object }
            }
            let focused = AX.element(AX.value(AX.app(pid), kAXFocusedWindowAttribute)).flatMap(AX.frame)
            row = matching.first { ($0["onScreen"] as? Bool == true) && ($0["frame"] as? [String: Double] == focused?.object) }
                ?? matching.first { $0["onScreen"] as? Bool == true } ?? matching.first
        }
        guard let row else { throw ToolFailure("window_unavailable", "No matching AX application window") }
        guard let id = row["windowID"] as? UInt32, let frameObject = row["frame"] as? [String: Double] else { throw ToolFailure("window_unavailable", "Missing window geometry") }
        let cgFrame = Rect(CGRect(x: frameObject["x"]!, y: frameObject["y"]!, width: frameObject["width"]!, height: frameObject["height"]!))
        let matches = try windows.enumerated().filter {
            if privateAPI { return try PrivateAPI.windowID($0.element) == id }
            return AX.frame($0.element) == cgFrame
        }
        guard matches.count == 1, let matched = matches.first else {
            throw ToolFailure("ambiguous_ax_window", "Cannot uniquely match window \(id) frame \(cgFrame.object) to AX frames \(windows.map { AX.frame($0)?.object ?? [:] }); reobserve after the window settles or choose a distinct visible window")
        }
        let (nodes, coverage, diagnostics) = AX.collect(matched.element, maxNodes: maxNodes, maxDepth: maxDepth, timeoutMilliseconds: collectionTimeoutMilliseconds)
        var result = Observation(id: UUID().uuidString.lowercased(), created: Date(), pid: pid, processStartID: processStartID,
            launchTime: metadata.launchTime, bundleID: metadata.bundleID,
            windowID: id, windowFrame: cgFrame, windowTitle: AX.string(matched.element, kAXTitleAttribute), axWindowIndex: matched.offset,
            nodes: nodes, coverage: coverage, diagnostics: diagnostics)
        result.windowIdentityBackend = privateAPI ? "_AXUIElementGetWindow" : "public-frame-match"
        var screenshotData: Data?
        var screenshotURL: URL?
        if screenshot {
            let image = try await Capture.image(windowID: id, timeoutMilliseconds: captureTimeoutMilliseconds)
            let data = try Capture.png(image)
            let url = store.root.appendingPathComponent(result.id + ".png")
            screenshotData = data; screenshotURL = url
            result.pixelWidth = image.width; result.pixelHeight = image.height
            result.screenshotSHA256 = SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined()
        }
        // Capturing can yield while the target changes. Bind both lanes to current geometry.
        try ProcessIdentity.require(pid: pid, expected: processStartID)
        guard let currentWindow = windowRows(pid: pid).first(where: { ($0["windowID"] as? UInt32) == id }),
              currentWindow["frame"] as? [String: Double] == result.windowFrame.object,
              AX.frame(matched.element) == result.windowFrame,
              AX.string(matched.element, kAXTitleAttribute) == result.windowTitle else { throw ToolFailure("stale_observation", "Window changed during observation") }
        if let screenshotData, let screenshotURL {
            try store.write(screenshotData, to: screenshotURL)
            result.screenshot = screenshotURL.path
        }
        result.created = Date()
        try store.save(result)
        return result
    }
    private func pointer(_ a: Arguments, _ observation: Observation, xKey: String = "x", yKey: String = "y") throws -> CGPoint {
        try Geometry.point(x: a.number(xKey), y: a.number(yKey), space: a.string("space", default: "window"), observation: observation)
    }
    private func inputContext(_ a: Arguments, keyboard: Bool) throws -> (Observation, String) {
        let o = try fresh(a); try Input.preflight()
        let route = try a.string("route", default: "process"); try Input.route(route, observation: o)
        if keyboard { _ = try AX.checkFocused(o, nodeID: a.string("node")) }
        if route == "global" { inputMonitor = try UserInputMonitor() }
        return (o, route)
    }
    private func revalidateKeyboardTarget(_ observation: Observation, nodeID: String, route: String) throws {
        try ProcessIdentity.require(pid: observation.pid, expected: observation.processStartID)
        try Input.preflight()
        try inputMonitor?.verify()
        try Input.route(route, observation: observation)
        _ = try AX.checkFocused(observation, nodeID: nodeID, requireStableValue: false)
    }
    private func postCleanupRelease(_ event: CGEvent, route: String, observation: Observation, pointer: Bool) -> String {
        if route == "global" {
            if pointer { event.location = CGEvent(source: nil)?.location ?? event.location }
            Input.post(event, route: route, pid: observation.pid)
            return "best_effort_system_release_posted"
        }
        guard ProcessIdentity.startID(pid: observation.pid) == observation.processStartID else {
            return "release_skipped_after_process_identity_changed"
        }
        Input.post(event, route: route, pid: observation.pid)
        return "best_effort_target_release_posted"
    }
    private func savePointerBestEffort(_ pointer: Pointer) -> String? {
        do {
            var value = pointer
            value.cursorID = cursorID
            if value.label == nil,let data=try? store.read(Store.pointerName(cursorID)),let previous=try? JSONDecoder().decode(Pointer.self,from:data){value.label=previous.label}
            value.processStartID = ProcessIdentity.startID(pid: value.pid)
            if let frame = windowRows(pid: value.pid).first(where: { ($0["windowID"] as? UInt32) == value.windowID })?["frame"] as? [String: Double],
               let x = frame["x"], let y = frame["y"], let width = frame["width"], let height = frame["height"] {
                value.windowFrame = Rect(CGRect(x: x, y: y, width: width, height: height))
            }
            try store.savePointer(value)
            return nil
        } catch {
            return "The UI action was already dispatched, but virtual-pointer state could not be saved; observe the target before any retry"
        }
    }
    private func cursorObject() -> [String: Double] {
        let p = CGEvent(source: nil)?.location ?? .zero
        return ["x":p.x, "y":p.y]
    }
    private func encodedObject<T: Encodable>(_ value: T) throws -> [String: Any] {
        do {
            let data = try JSONEncoder().encode(value)
            guard let object = try JSONSerialization.jsonObject(with: data) as? [String: Any] else {
                throw ToolFailure("encoding_failed", "Typed result did not encode as an object")
            }
            return object
        } catch let failure as ToolFailure {
            throw failure
        } catch {
            throw ToolFailure("encoding_failed", "Cannot encode typed result: \(error.localizedDescription)")
        }
    }
    private func activeDisplayFrame(_ displayID: CGDirectDisplayID) throws -> Rect {
        var ids = [CGDirectDisplayID](repeating: 0, count: 32), count: UInt32 = 0
        guard CGGetActiveDisplayList(UInt32(ids.count), &ids, &count) == .success,
              ids.prefix(Int(count)).contains(displayID) else {
            throw ToolFailure("display_unavailable", "Display is not active; refresh display IDs with mac_doctor")
        }
        let frame = CGDisplayBounds(displayID)
        guard frame.origin.x.isFinite, frame.origin.y.isFinite, frame.width.isFinite, frame.height.isFinite,
              frame.width > 0, frame.height > 0 else {
            throw ToolFailure("display_unavailable", "Display has invalid logical geometry")
        }
        return Rect(frame)
    }
    private func captureDisplay(_ a: Arguments) async throws -> [String: Any] {
        try a.only(["displayID", "maxDimension", "timeoutMs"])
        let displayID = CGDirectDisplayID(try a.integer("displayID", range: 1...Int(UInt32.max)))
        let maxDimension = try a.integer("maxDimension", default: 1600, range: 1...8192)
        let frame = try activeDisplayFrame(displayID)
        let timeout = try a.integer("timeoutMs", default: 10_000, range: 100...60_000)
        let image = try await Capture.image(displayID: displayID, maxDimension: maxDimension, timeoutMilliseconds: timeout)
        guard try activeDisplayFrame(displayID) == frame else {
            throw ToolFailure("display_changed", "Display geometry changed during capture; refresh display IDs and retry")
        }
        let data = try Capture.png(image)
        let url = store.root.appendingPathComponent("display-\(displayID)-\(UUID().uuidString.lowercased()).png")
        try store.write(data, to: url)
        return ["status":"captured", "source":"display", "displayID":displayID, "screenshot":url.path,
                "screenshotSHA256":SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined(),
                "pixelWidth":image.width, "pixelHeight":image.height, "displayFrame":frame.object,
                "cursorIncluded":false,
                "coordinateSystem":"Image pixels use a top-left origin; displayFrame uses global logical points with a top-left origin"]
    }
    private func menu(_ a: Arguments) throws -> [String: Any] {
        let operation = try a.string("operation")
        let allowed: [String]
        switch operation {
        case "list": allowed = ["pid", "operation", "maxItemsPerLevel"]
        case "press": allowed = ["pid", "operation", "processStartID", "titlePath", "maxItemsPerLevel"]
        default: throw ToolFailure("invalid_argument", "operation must be list or press")
        }
        try a.only(allowed)
        let pid = Int32(try a.integer("pid", range: 1...Int(Int32.max)))
        let limit = try a.integer("maxItemsPerLevel", default: 64, range: 1...128)
        let titlePath: [String]?
        let expectedProcessStartID: String?
        if operation == "press" {
            let path = try a.strings("titlePath")
            guard (1...8).contains(path.count), path.allSatisfy({ !$0.isEmpty && $0.utf8.count <= 512 }) else {
                throw ToolFailure("invalid_argument", "Menu title path must contain 1 to 8 nonempty titles of at most 512 bytes")
            }
            titlePath = path
            let expected = try a.string("processStartID", limit: 64)
            try ProcessIdentity.require(pid: pid, expected: expected)
            expectedProcessStartID = expected
        } else {
            titlePath = nil
            expectedProcessStartID = nil
        }
        guard let app = NSRunningApplication(processIdentifier: pid), !app.isTerminated else {
            throw ToolFailure("app_unavailable", "Target PID is not running")
        }
        if operation == "list" {
            let items = try AX.topLevelMenuItems(pid: pid, maxItems: limit)
            return ["status":"listed", "pid":pid, "scope":"complete_top_level_menu_bar",
                    "maxItemsPerLevel":limit, "items":try items.map(encodedObject)]
        }
        let item = try AX.pressMenuItem(pid: pid, processStartID: expectedProcessStartID!,
                                       titlePath: titlePath!, maxItemsPerLevel: limit)
        return ["status":"action_requested", "pid":pid, "item":try encodedObject(item),
                "verification":"Accessibility accepted the menu action; observe and verify the requested application postcondition"]
    }
    private func window(_ a: Arguments) async throws -> [String: Any] {
        let operation = try a.string("operation")
        let allowed: [String]
        switch operation {
        case "state", "raise", "close", "minimize", "unminimize", "toggle_full_screen":
            allowed = ["observation", "operation"]
        case "move":
            allowed = ["observation", "operation", "x", "y"]
        case "resize":
            allowed = ["observation", "operation", "width", "height"]
        default:
            throw ToolFailure("invalid_argument", "Unsupported window operation")
        }
        try a.only(allowed)
        let origin: CGPoint?
        let size: CGSize?
        if operation == "move" {
            origin = CGPoint(x: try a.number("x"), y: try a.number("y"))
            size = nil
        } else if operation == "resize" {
            origin = nil
            size = CGSize(width: try a.number("width", range: Double.leastNonzeroMagnitude...1e7),
                          height: try a.number("height", range: Double.leastNonzeroMagnitude...1e7))
        } else {
            origin = nil
            size = nil
        }
        let observation = try fresh(a)
        if operation == "state" {
            return ["status":"window_state", "operation":operation,
                    "state":try encodedObject(WindowActions.state(observation))]
        }

        try store.consume(observation)
        switch operation {
        case "raise":
            let state = try await WindowActions.raise(observation)
            return ["status":"requested_unverified", "operation":operation, "state":try encodedObject(state),
                    "verification":"AXRaise was accepted; public Accessibility does not expose a reliable window z-order postcondition"]
        case "close":
            let state = try await WindowActions.close(observation), verified = !state.exists
            return ["status":verified ? "closed_verified" : "close_unverified", "operation":operation,
                    "state":try encodedObject(state),
                    "verification":verified ? "Observed window no longer exists" : "Close was accepted but the observed window still exists after the bounded wait"]
        case "minimize", "unminimize":
            let expected = operation == "minimize"
            let state = expected ? try await WindowActions.minimize(observation) : try await WindowActions.unminimize(observation)
            let verified = state.minimized == expected
            return ["status":verified ? (expected ? "minimized_verified" : "unminimized_verified") : "minimize_state_unverified",
                    "operation":operation, "state":try encodedObject(state),
                    "verification":verified ? "Observed AXMinimized matches the requested value" : "AXMinimized did not match after the bounded wait"]
        case "toggle_full_screen":
            let result = try await WindowActions.toggleFullScreen(observation)
            return ["status":result.status, "operation":operation, "state":try encodedObject(result.state),
                    "verification":result.verification]
        case "move":
            let origin = origin!
            let state = try await WindowActions.move(observation, to: origin)
            let verified = state.frame.map { abs($0.x - origin.x) <= 0.5 && abs($0.y - origin.y) <= 0.5 } ?? false
            return ["status":verified ? "moved_verified" : "move_unverified", "operation":operation,
                    "state":try encodedObject(state),
                    "verification":verified ? "Observed window origin matches the requested point" : "Window origin did not match after the bounded wait"]
        case "resize":
            let size = size!
            let state = try await WindowActions.resize(observation, to: size)
            let verified = state.frame.map { abs($0.width - size.width) <= 0.5 && abs($0.height - size.height) <= 0.5 } ?? false
            return ["status":verified ? "resized_verified" : "resize_unverified", "operation":operation,
                    "state":try encodedObject(state),
                    "verification":verified ? "Observed window size matches the requested dimensions" : "Window size did not match after the bounded wait"]
        default:
            preconditionFailure("Window operation was validated before dispatch")
        }
    }
    private func dispatch(_ tool: String, _ a: Arguments) async throws -> [String: Any] {
        switch tool {
        case "mac_workflow": return try await Workflows.call(a,engine:self)
        case "mac_image_search": return try await ImageSearch.call(a,engine:self)
        case "mac_trace": return try Tracing.call(a,store:store)
        case "mac_wait_for": return try await Conditions.call(a, engine: self)
        case "mac_private": return try PrivateAPI.call(a)
        case "mac_improvement": return try await Improvements.call(a,store:baseStore)
        case "mac_browser_developer": return try await BrowserDeveloperSettings.call(a, engine: self)
        case "mac_browser": return try await BrowserBridge.call(a,store:baseStore,preserveForeground:taskRecord?.preserveForeground ?? false)
        case "mac_files": return try await NativeFiles.call(a, resources:baseStore)
        case "mac_system": return try NativeSystem.call(a)
        case "mac_preview":
            let operation = try a.string("operation")
            let o = operation == "start" ? try fresh(a) : nil
            return try await PreviewActions.call(a, store: store, observation: o)
        case "mac_focus":
            try a.only(["observation", "node", "timeoutMs"])
            let timeout = try a.integer("timeoutMs", default: 2000, range: 100...10_000)
            let o = try fresh(a)
            let node = a.values["node"] == nil ? nil : try AX.resolve(o, nodeID: a.string("node"))
            try store.consume(o)
            return try await WindowActions.focus(o, node: node, timeoutMilliseconds: timeout)
        case "mac_doctor":
            try a.only([])
            var ids = [CGDirectDisplayID](repeating: 0, count: 32), count: UInt32 = 0
            CGGetActiveDisplayList(32, &ids, &count)
            return ["status":"ok", "version":MacPilotRuntime.version, "os":ProcessInfo.processInfo.operatingSystemVersionString,
                    "permissions":["accessibility":AXIsProcessTrusted(), "screenCapture":CGPreflightScreenCaptureAccess(),
                        "postEvent":CGPreflightPostEventAccess(), "inputMonitoring":CGPreflightListenEventAccess()],
                    "secureEventInput":IsSecureEventInputEnabled(), "stateDirectory":store.root.path,
                    "systemCursor":cursorObject(), "foregroundPID":NSWorkspace.shared.frontmostApplication?.processIdentifier ?? 0,
                    "displays":ids.prefix(Int(count)).map { ["id":$0, "frame":Rect(CGDisplayBounds($0)).object] as [String: Any] },
                    "runtimeDependencies":["macOS 14+ Apple system frameworks"], "networkRequired":false,
                    "optionalRuntimeDependencies":["imageSearch":"explicit local Python environment and pinned EmbeddingGemma 2 model; disabled by default"],
                    "capabilities":["virtualPointer":"task-scoped named cursors, annotated live preview and click-through overlays; no second OS cursor",
                        "tasks":"isolated state, cancellation, deadlines and target/input leases",
                        "preview":"SCStream live window frames with hide/show/pause/resume/stop",
                        "browser":"Chromium extension/native messaging; Safari Apple Events with site-specific limitations",
                        "files":"explicit paths, UTF-8, copy/move hashes and Finder tags",
                        "audio":"CoreAudio output volume and mute with reread",
                        "recording":"macOS 15+ window/application audio or full-display/system-audio MP4, no microphone; decoded media inspection",
                        "privateAPI":"opt-in _AXUIElementGetWindow; other catalog entries are research-only",
                        "improvements":"local queue; configured Codex app-server delivery requires Codex model connectivity",
                        "processInput":"public CGEvent.postToPid; app compatibility requires verification",
                        "globalInput":"explicit route=global; foreground, visible target and Input Monitoring required; yields on external input",
                        "conditionWaits":"same-process/window AX predicates; notifications plus bounded polling",
                        "traces":"opt-in bounded before/after records; text and screenshots are separate opt-ins",
                        "workflows":"explicit bounded native recipes; declared postconditions and durable runID replay protection",
                        "imageSearch":"optional VisionKit and local EmbeddingGemma 2; ranked candidates, cached vectors, no automatic click",
                        "systemActions":"typed app lifecycle, URL/file open, Finder reveal, and NSWorkspace Trash operations",
                        "clipboard":"explicit bounded plain-text read/write only; never read implicitly",
                        "shortcuts":"fixed /usr/bin/shortcuts executable with bounded time and output",
                        "scripts":"AppleScript or JavaScript through fixed /usr/bin/osascript stdin; no shell interpolation",
                        "displayCapture":"complete selected display through ScreenCaptureKit; cursor excluded; private local PNG",
                        "menus":"bounded exact Accessibility menu list and press; no fuzzy title matching",
                        "windows":"fresh-observation state, raise, close, minimize, full-screen toggle, move, and resize operations",
                        "virtualHID":"not installed; entitlement/driver path is documented in research",
                        "languageModel":"none for base control; optional local EmbeddingGemma 2 for image search"]]
        case "mac_apps":
            try a.only([])
            let applications = NSWorkspace.shared.runningApplications.compactMap { application -> [String: Any]? in
                let pid = application.processIdentifier
                do {
                    let snapshot = try ProcessIdentity.withStableIdentity(pid: pid) {
                        guard application.processIdentifier == pid else {
                            throw ToolFailure("stale_app_identity", "Running-application PID changed during enumeration")
                        }
                        return (policy: application.activationPolicy, name: application.localizedName ?? "",
                                bundleID: application.bundleIdentifier ?? "", active: application.isActive)
                    }
                    guard snapshot.value.policy != .prohibited else { return nil }
                    return ["pid":pid, "processStartID":snapshot.processStartID,
                            "name":snapshot.value.name, "bundleID":snapshot.value.bundleID,
                            "active":snapshot.value.active]
                } catch {
                    // A process that exits or is replaced while the workspace list is
                    // being read is omitted instead of returning mixed-instance data.
                    return nil
                }
            }
            return ["status":"ok", "apps":applications]
        case "mac_windows":
            try a.only(["pid"])
            let pid = try a.values["pid"].map { _ in Int32(try a.integer("pid", range: 1...Int(Int32.max))) }
            return ["status":"ok", "windows":windowRows(pid: pid)]
        case "mac_record":
            if a.values["source"] as? String == "display", taskRecord?.pid != nil || taskRecord?.windowID != nil {
                throw ToolFailure("task_target_mismatch", "A window/application-bound task cannot expand to a full display recording")
            }
            return try await Recording.call(a, store: store)
        case "mac_capture": return try await captureDisplay(a)
        case "mac_menu": return try menu(a)
        case "mac_window": return try await window(a)
        case "mac_launch":
            try a.only(["bundleID", "activate", "timeoutMs"])
            let bundle = try a.string("bundleID", limit: 256)
            guard let url = NSWorkspace.shared.urlForApplication(withBundleIdentifier: bundle) else { throw ToolFailure("app_unavailable", "Installed bundle not found") }
            let config = NSWorkspace.OpenConfiguration(); config.activates = try a.bool("activate")
            let timeout = try a.integer("timeoutMs", default: 10_000, range: 100...60_000)
            let app: NSRunningApplication = try await withCallbackDeadline(
                timeoutMilliseconds: timeout,
                timeoutFailure: ToolFailure("workspace_timeout", "NSWorkspace app launch did not return within \(timeout) ms. The launch may still complete; list apps and reconcile state before retrying.")
            ) { finish in
                NSWorkspace.shared.openApplication(at: url, configuration: config) { application, error in
                    if let application { finish(.success(application)) }
                    else { finish(.failure(error ?? ToolFailure("app_launch_failed", "NSWorkspace returned no launched application"))) }
                }
            }
            let pid = app.processIdentifier
            for _ in 0..<20 {
                if let identity = ProcessIdentity.startID(pid: pid) {
                    let metadata = try ProcessIdentity.withStableIdentity(pid: pid, expected: identity) {
                        guard app.processIdentifier == pid, !app.isTerminated else {
                            throw ToolFailure("app_unavailable", "The launched application terminated before its identity could be returned")
                        }
                        return app.bundleIdentifier ?? ""
                    }
                    guard metadata.value == bundle else {
                        throw ToolFailure("app_launch_failed", "NSWorkspace returned a different application than the requested bundle")
                    }
                    return ["status":"launched", "pid":pid, "processStartID":metadata.processStartID,
                            "bundleID":metadata.value]
                }
                try await Task.sleep(nanoseconds: 25_000_000)
            }
            return ["status":"launched_identity_unavailable", "pid":pid, "bundleID":bundle,
                    "warning":"The app launch was accepted, but its process identity could not be read; list apps before a PID-targeted action"]
        case "mac_app": return try await SystemActions.app(a)
        case "mac_open": return try await SystemActions.open(a)
        case "mac_reveal": return try await SystemActions.reveal(a)
        case "mac_trash": return try await SystemActions.trash(a)
        case "mac_clipboard_read": return try SystemActions.clipboardRead(a)
        case "mac_clipboard_write": return try SystemActions.clipboardWrite(a)
        case "mac_shortcuts": return try await SystemActions.shortcuts(a)
        case "mac_script": return try await SystemActions.script(a)
        case "mac_permission": return try await SystemActions.permission(a)
        case "mac_simulator": return try await simulator(a)
        case "mac_analyze": return try await analyzeUI(a)
        case "mac_observe":
            try a.only(["pid", "processStartID", "windowID", "screenshot", "maxNodes", "maxDepth", "captureTimeoutMs", "privateAPI"])
            let pid = Int32(try a.integer("pid", range: 1...Int(Int32.max)))
            let processStartID = try a.string("processStartID", limit: 64)
            let id = try a.values["windowID"].map { _ in UInt32(try a.integer("windowID", range: 1...Int(UInt32.max))) }
            let o = try await observe(pid: pid, processStartID: processStartID, windowID: id, screenshot: a.bool("screenshot", default: true),
                maxNodes: a.integer("maxNodes", default: 200, range: 1...1000), maxDepth: a.integer("maxDepth", default: 10, range: 1...30),
                captureTimeoutMilliseconds: a.integer("captureTimeoutMs", default: 10_000, range: 100...60_000), privateAPI: a.bool("privateAPI"))
            _ = try await DesktopOverlayActions.ensure(store,observation:o)
            return ["status":"observed", "observation":o.object, "foregroundPID":NSWorkspace.shared.frontmostApplication?.processIdentifier ?? 0,
                    "coordinateSystem":"global logical points, top-left origin; image coordinates use returned pixel dimensions"]
        case "mac_activate":
            try a.only(["observation"]); let o = try fresh(a)
            try store.consume(o)
            let accepted = try ProcessIdentity.withStableIdentity(pid: o.pid, expected: o.processStartID) {
                guard let application = NSRunningApplication(processIdentifier: o.pid), !application.isTerminated else { return false }
                return application.activate(options: [])
            }.value
            return ["status":"activation_requested", "pid":o.pid, "processStartID":o.processStartID,
                    "accepted":accepted, "verification":"Observe foreground state before global input"]
        case "mac_ax":
            let operation = try a.string("operation")
            switch operation {
            case "focus":
                try a.only(["observation", "node", "operation"])
            case "set_value":
                try a.only(["observation", "node", "operation", "text"])
                _ = try a.string("text")
            case "select_range":
                try a.only(["observation", "node", "operation", "start", "length"])
                _ = try a.integer("start"); _ = try a.integer("length")
            case "action":
                try a.only(["observation", "node", "operation", "action"])
                _ = try a.string("action", default: "AXPress", limit: 128)
            default:
                throw ToolFailure("invalid_argument", "operation must be focus, set_value, select_range, or action")
            }
            let o = try fresh(a), nodeID = try a.string("node")
            let element = try AX.resolve(o, nodeID: nodeID)
            switch operation {
            case "focus":
                try ProcessIdentity.require(pid:o.pid,expected:o.processStartID)
                try store.consume(o); try AX.set(element, kAXFocusedAttribute, kCFBooleanTrue)
                return ["status":AX.bool(element, kAXFocusedAttribute) ? "focus_verified" : "focus_requested"]
            case "set_value":
                let text = try a.string("text")
                try ProcessIdentity.require(pid:o.pid,expected:o.processStartID)
                try store.consume(o); try AX.set(element, kAXValueAttribute, text as CFString)
                try await Task.sleep(nanoseconds: 100_000_000)
                let live = AX.boundedString(element, kAXValueAttribute, limit: 65_536)
                let matches = !live.truncated && live.value == text
                return ["status":matches ? "value_verified" : "value_unverified", "equalsRequestedText":matches]
            case "select_range":
                let start = try a.integer("start"), length = try a.integer("length")
                guard let rawValue = AX.value(element, kAXValueAttribute) as? String else {
                    throw ToolFailure("invalid_argument", "Selected node has no complete live text")
                }
                let boundedValue = AX.boundedString(rawValue, limit: 65_536)
                guard !boundedValue.truncated else {
                    throw ToolFailure("oversized_ax_value", "Live text exceeds 65536 UTF-8 bytes; range selection is not safe")
                }
                let valueText = boundedValue.value
                guard start <= valueText.utf16.count, length <= valueText.utf16.count - start else { throw ToolFailure("invalid_argument", "UTF-16 range is outside complete live text") }
                var range = CFRange(location: start, length: length)
                guard let value = AXValueCreate(.cfRange, &range) else { throw ToolFailure("ax_failed", "Cannot create range") }
                try ProcessIdentity.require(pid:o.pid,expected:o.processStartID)
                try store.consume(o); try AX.set(element, kAXSelectedTextRangeAttribute, value)
                var actual = CFRange()
                let raw = AX.value(element, kAXSelectedTextRangeAttribute)
                let matches = raw.map { CFGetTypeID($0) == AXValueGetTypeID() && AXValueGetValue($0 as! AXValue, .cfRange, &actual) && actual.location == start && actual.length == length } ?? false
                return ["status":matches ? "range_verified" : "range_unverified"]
            case "action":
                let action = try a.string("action", default: "AXPress", limit: 128)
                guard AX.actions(element).contains(action) else { throw ToolFailure("unsupported_action", "Action is not exposed by the selected node") }
                try ProcessIdentity.require(pid:o.pid,expected:o.processStartID)
                try store.consume(o)
                let error = AXUIElementPerformAction(element, action as CFString)
                try AX.requireMutationSuccess(error, operation: "performing \(action) on the selected control")
                return ["status":"action_requested", "verification":"Call observe and verify an explicit postcondition"]
            default: throw ToolFailure("invalid_argument", "operation must be focus, set_value, select_range, or action")
            }
        case "mac_pointer":
            try a.only(["observation", "x", "y", "space", "label"])
            let o = try fresh(a), p = try pointer(a, o), before = cursorObject()
            let hit=AX.hits(o,point:p).first
            let fallback=hit?.title.isEmpty == false ? hit!.title : hit?.role == "AXTextField" ? "텍스트 입력" : hit?.role == "AXButton" ? "버튼" : "작업 위치"
            let label=try a.string("label",default:fallback,limit:128)
            try store.savePointer(Pointer(windowID: o.windowID, pid: o.pid, x: p.x, y: p.y,
                                          processStartID: o.processStartID, windowFrame: o.windowFrame, cursorID: cursorID, label:label))
            var result: [String: Any] = ["status":"virtual_pointer_moved", "cursorID":cursorID, "virtualPointer":["x":p.x,"y":p.y], "systemCursorBefore":before, "systemCursorAfter":cursorObject(), "eventsPosted":0]
            result["hitCandidates"] = AX.hits(o, point:p).prefix(8).map { ["node":$0.id,"role":$0.role,"title":$0.title,"actions":$0.actions] as [String:Any] }
            result["desktopOverlay"] = try await DesktopOverlayActions.ensure(store,observation:o)
            return result
        case "mac_cursors":
            try a.only(["operation", "observation"])
            let o = try fresh(a), operation = try a.string("operation")
            if operation == "remove" { try store.remove(Store.pointerName(cursorID)) }
            else if operation == "hide" || operation == "show" {
                _ = try await DesktopOverlayActions.ensure(store,observation:o)
                _ = try await DesktopOverlayActions.control(store,enabled:operation == "show")
            } else if operation != "list" { throw ToolFailure("invalid_argument", "operation must be list, remove, hide or show") }
            return ["status":"cursors", "cursors":try store.pointers(o).map { try encodedObject($0) },"desktopOverlay":DesktopOverlayActions.status(store)]
        case "mac_click", "mac_drag", "mac_scroll":
            let allowed: [String]
            switch tool {
            case "mac_click": allowed = ["observation", "x", "y", "space", "route", "button", "clicks"]
            case "mac_drag": allowed = ["observation", "x", "y", "space", "route", "toX", "toY", "duration"]
            default: allowed = ["observation", "x", "y", "space", "route", "vertical", "horizontal"]
            }
            try a.only(allowed)
            if tool == "mac_click" {
                let route = try a.string("route", default:"accessibility")
                guard ["accessibility","process","global"].contains(route) else {
                    throw ToolFailure("invalid_argument", "route must be accessibility, process, or global")
                }
                let button = try a.string("button",default:"left")
                guard ["left","right"].contains(button) else { throw ToolFailure("invalid_argument", "button must be left or right") }
                let clicks = try a.integer("clicks",default:1,range:1...2)
                if route == "accessibility", button != "left" || clicks != 1 {
                    throw ToolFailure("invalid_argument", "Accessibility coordinate clicks support one left AXPress only")
                }
            } else if tool == "mac_scroll" {
                let vertical = try a.integer("vertical", default: 0, range: -100...100)
                let horizontal = try a.integer("horizontal", default: 0, range: -100...100)
                guard vertical != 0 || horizontal != 0 else {
                    throw ToolFailure("invalid_argument", "At least one scroll delta must be nonzero")
                }
            }
            if tool == "mac_click", try a.string("route", default:"accessibility") == "accessibility" {
                let o = try fresh(a), p = try pointer(a,o), before = cursorObject()
                let candidates = AX.hits(o,point:p).filter { $0.actions.contains(kAXPressAction) }
                guard let chosen = candidates.first else { throw ToolFailure("unsupported_ax_click", "No enabled AXPress control covers this point; inspect nodes or explicitly choose another route") }
                guard candidates.filter({ $0.path.count == chosen.path.count }).count == 1 else { throw ToolFailure("ambiguous_ax_click", "Multiple AXPress controls overlap; select an explicit node with mac_ax") }
                let element = try AX.resolve(o,nodeID:chosen.id)
                try ProcessIdentity.require(pid:o.pid,expected:o.processStartID)
                try store.consume(o)
                let error = AXUIElementPerformAction(element,kAXPressAction as CFString)
                try AX.requireMutationSuccess(error, operation: "coordinate AXPress")
                var result: [String: Any] = ["status":"action_requested","route":"accessibility","node":chosen.id,"eventsPosted":0,
                    "systemCursorBefore":before,"systemCursorAfter":cursorObject(),"verification":"AXPress accepted; observe the requested postcondition"]
                if let warning = savePointerBestEffort(Pointer(windowID:o.windowID,pid:o.pid,x:p.x,y:p.y)) {
                    result["warning"] = warning
                }
                return result
            }
            let (o, route) = try inputContext(a, keyboard: false), p = try pointer(a, o)
            if route == "global" { try Input.globalHitTest(p, observation: o) }
            var events: [CGEvent] = [], duration = 0.0
            if tool == "mac_click" {
                let button = try a.string("button", default: "left"), clicks = try a.integer("clicks", default: 1, range: 1...2)
                guard ["left","right"].contains(button) else { throw ToolFailure("invalid_argument", "button must be left or right") }
                // Blender/GHOST chooses the active UI region from cursor-move
                // events. A button event at a new point alone leaves that stale.
                events.append(try Input.mouseEvent(.mouseMoved, point:p, observation:o))
                for n in 1...clicks {
                    events += try [Input.mouseEvent(button == "left" ? .leftMouseDown : .rightMouseDown, point: p, observation: o, clicks: n),
                                   Input.mouseEvent(button == "left" ? .leftMouseUp : .rightMouseUp, point: p, observation: o, clicks: n)]
                }
            } else if tool == "mac_drag" {
                let end = try pointer(a, o, xKey: "toX", yKey: "toY")
                duration = try a.number("duration", default: 0.35, range: 0.05...2)
                events.append(try Input.mouseEvent(.leftMouseDown, point: p, observation: o))
                for i in 1...20 {
                    let point = CGPoint(x:p.x+(end.x-p.x)*Double(i)/20, y:p.y+(end.y-p.y)*Double(i)/20)
                    if route == "global" { try Input.globalHitTest(point, observation: o) }
                    events.append(try Input.mouseEvent(.leftMouseDragged, point: point, observation: o))
                }
                events.append(try Input.mouseEvent(.leftMouseUp, point: end, observation: o))
            } else {
                let vertical = try a.integer("vertical", default: 0, range: -100...100), horizontal = try a.integer("horizontal", default: 0, range: -100...100)
                guard let event = CGEvent(scrollWheelEvent2Source: CGEventSource(stateID: .privateState), units: .line,
                    wheelCount: 2, wheel1: Int32(vertical), wheel2: Int32(horizontal), wheel3: 0) else { throw ToolFailure("event_failed", "Cannot create scroll event") }
                event.location = p; event.flags = []; Input.address(event, observation: o); events = [event]
            }
            try Task.checkCancellation()
            let activity = route == "global" ? try await InputActivityScope.begin(store: baseStore, kind: "마우스") : nil
            defer { activity?.finish() }
            let before = cursorObject(); try store.consume(o)
            var posted = 0
            var pendingRelease: CGEvent?
            for (index, event) in events.enumerated() {
                do {
                    try Task.checkCancellation()
                    try ProcessIdentity.require(pid: o.pid, expected: o.processStartID)
                    try Input.preflight()
                    try inputMonitor?.verify()
                    try activity?.verify()
                    if route == "global" {
                        guard NSWorkspace.shared.frontmostApplication?.processIdentifier == o.pid else {
                            throw ToolFailure("foreground_changed", "The foreground app changed")
                        }
                        try Input.globalHitTest(event.location, observation: o)
                    }
                } catch {
                    if error is CancellationError {
                        if let release = pendingRelease {
                            _ = postCleanupRelease(release, route:route, observation:o, pointer:true)
                        }
                        throw error
                    }
                    guard posted > 0 else { throw error }
                    let failure = error as? ToolFailure
                    var result: [String:Any] = ["status":"dispatch_interrupted", "route":route, "eventsPosted":posted,
                            "reasonCode":failure?.code ?? "native_error",
                            "reason":failure?.description ?? error.localizedDescription,
                            "verification":"Part of the pointer action may have been dispatched; observe target state before any retry"]
                    if let release = pendingRelease {
                        result["cleanupRelease"] = postCleanupRelease(release, route:route, observation:o, pointer:true)
                    }
                    return result
                }
                event.timestamp = DispatchTime.now().uptimeNanoseconds
                Input.post(event, route: route, pid: o.pid)
                posted += 1
                if [.leftMouseDown,.rightMouseDown].contains(event.type) {
                    pendingRelease = events.dropFirst(index + 1).first {
                        [.leftMouseUp,.rightMouseUp].contains($0.type)
                    }
                } else if [.leftMouseUp,.rightMouseUp].contains(event.type) {
                    pendingRelease = nil
                }
                try? await Task.sleep(nanoseconds: duration > 0 ? UInt64(duration / Double(events.count) * 1e9) : 30_000_000)
            }
            // Quartz dispatch is asynchronous. Keep a one-shot CLI alive through queue delivery.
            try await Task.sleep(nanoseconds: 100_000_000)
            let finalPoint = events.last?.location ?? p
            var result: [String: Any] = ["status":"dispatched_unverified", "route":route, "eventsPosted":events.count,
                    "systemCursorBefore":before, "systemCursorAfter":cursorObject(),
                    "verification":"Event dispatch does not prove app acceptance; observe and verify the requested change"]
            if let warning = savePointerBestEffort(Pointer(windowID: o.windowID, pid: o.pid, x: Double(finalPoint.x), y: Double(finalPoint.y))) {
                result["warning"] = warning
            }
            return result
        case "mac_game_input":
            try a.only(["observation", "node", "route", "keys", "tapKeys", "tapIntervalMs", "durationMs", "inputSource", "eventSource"])
            let nodeID = try a.string("node")
            let keyNames = try a.strings("keys"), tapNames = try a.strings("tapKeys")
            let eventSource = try a.string("eventSource", default: "private")
            guard ["private", "hid"].contains(eventSource) else { throw ToolFailure("invalid_argument", "eventSource must be private or hid") }
            let prepared = try Input.heldKeyEvents(keyNames + tapNames, stateID: eventSource == "hid" ? .hidSystemState : .privateState)
            let keys = Array(prepared.prefix(keyNames.count)), tapKeys = Array(prepared.dropFirst(keyNames.count))
            let tapInterval = try a.integer("tapIntervalMs", default: 250, range: 100...2000)
            let duration = try a.integer("durationMs", range: 20...10_000)
            let sourceMode = try a.string("inputSource", default: "current")
            guard ["current", "ascii"].contains(sourceMode) else {
                throw ToolFailure("invalid_argument", "inputSource must be current or ascii")
            }
            let (o, route) = try inputContext(a, keyboard: true)
            if eventSource == "hid", route != "global" { throw ToolFailure("invalid_argument", "HID system state requires route=global") }
            if sourceMode == "ascii", route != "global" {
                throw ToolFailure("invalid_argument", "Temporary ASCII selection requires route=global")
            }
            try Task.checkCancellation()
            let activity = route == "global" ? try await InputActivityScope.begin(store: baseStore, kind: "키보드") : nil
            defer { activity?.finish() }
            try store.consume(o)
            let sourceScope = sourceMode == "ascii" ? try KeyboardInputSourceScope() : nil
            var pending: [CGEvent] = []
            // Release even on cancellation, foreground loss, or an input-source change.
            defer {
                for event in pending.reversed() {
                    _ = postCleanupRelease(event, route: route, observation: o, pointer: false)
                }
                sourceScope?.restore()
            }
            if sourceScope != nil { try await Task.sleep(nanoseconds: 100_000_000) }
            for key in keys {
                try Task.checkCancellation()
                try sourceScope?.verify()
                try activity?.verify()
                try revalidateKeyboardTarget(o, nodeID: nodeID, route: route)
                key.down.timestamp = DispatchTime.now().uptimeNanoseconds
                pending.append(key.up)
                Input.post(key.down, route: route, pid: o.pid)
            }
            let deadline = DispatchTime.now().uptimeNanoseconds + UInt64(duration) * 1_000_000
            var nextTap: UInt64 = 0, tapReleaseAt: UInt64 = 0, tapActive = false, tapCount = 0
            while DispatchTime.now().uptimeNanoseconds < deadline {
                try Task.checkCancellation()
                try sourceScope?.verify()
                try activity?.verify()
                try revalidateKeyboardTarget(o, nodeID: nodeID, route: route)
                let now = DispatchTime.now().uptimeNanoseconds
                if tapActive, now >= tapReleaseAt {
                    for key in tapKeys.reversed() {
                        _ = postCleanupRelease(key.up, route: route, observation: o, pointer: false)
                        let code = key.up.getIntegerValueField(.keyboardEventKeycode)
                        pending.removeAll { $0.getIntegerValueField(.keyboardEventKeycode) == code }
                    }
                    tapActive = false
                }
                if !tapKeys.isEmpty, !tapActive, now >= nextTap {
                    for key in tapKeys {
                        key.down.timestamp = DispatchTime.now().uptimeNanoseconds
                        pending.append(key.up)
                        Input.post(key.down, route: route, pid: o.pid)
                    }
                    tapActive = true; tapCount += 1
                    tapReleaseAt = now + 50_000_000
                    nextTap = now + UInt64(tapInterval) * 1_000_000
                }
                let remaining = deadline - min(deadline, DispatchTime.now().uptimeNanoseconds)
                try await Task.sleep(nanoseconds: min(50_000_000, remaining))
            }
            for event in pending.reversed() {
                event.timestamp = DispatchTime.now().uptimeNanoseconds
                _ = postCleanupRelease(event, route: route, observation: o, pointer: false)
            }
            pending.removeAll()
            try await Task.sleep(nanoseconds: 100_000_000)
            var result: [String: Any] = ["status": "dispatched_unverified", "route": route,
                "keysHeld": keys.count, "eventSource": eventSource, "tapCount": tapCount, "durationMs": duration, "releaseEventsPosted": keys.count + tapCount * tapKeys.count,
                "verification": "Balanced bounded input was posted; observe the game to verify movement and outcome"]
            if let sourceScope { result["keyboardInputSource"] = sourceScope.restore() }
            return result
        case "mac_key", "mac_type":
            if tool == "mac_key" {
                try a.only(["observation", "node", "route", "key", "modifiers", "inputSource"])
            } else {
                try a.only(["observation", "node", "route", "text", "inputSource"])
            }
            let nodeID = try a.string("node")
            let (o, route) = try inputContext(a, keyboard: true)
            let events = tool == "mac_key" ? try Input.keyEvents(key: a.string("key", limit: 64), modifiers: a.strings("modifiers")) : try Input.textEvents(a.string("text", limit: 8192))
            let sourceMode = try a.string("inputSource", default:"current")
            guard ["current","ascii"].contains(sourceMode) else { throw ToolFailure("invalid_argument","inputSource must be current or ascii") }
            if sourceMode == "ascii", route != "global" {
                throw ToolFailure("invalid_argument","Temporary ASCII selection requires route=global and the selected foreground app")
            }
            try Task.checkCancellation()
            let activity = route == "global" ? try await InputActivityScope.begin(store: baseStore, kind: "키보드") : nil
            defer { activity?.finish() }
            try store.consume(o)
            let sourceScope = sourceMode == "ascii" ? try KeyboardInputSourceScope() : nil
            defer { sourceScope?.restore() }
            if sourceScope != nil { try await Task.sleep(nanoseconds:100_000_000) }
            func restoredResult(_ value:[String:Any]) -> [String:Any] {
                var result = value
                if let sourceScope {
                    let restoration = sourceScope.restore()
                    result["keyboardInputSource"] = restoration
                    if restoration["restored"] as? Bool != true { result["warning"] = "Original input source was not restored; inspect current state before further input" }
                }
                return result
            }
            var posted = 0
            var pendingReleases: [CGEvent] = []
            for (index, event) in events.enumerated() {
                do {
                    try Task.checkCancellation()
                    try sourceScope?.verify()
                    try activity?.verify()
                    try revalidateKeyboardTarget(o, nodeID: nodeID, route: route)
                } catch {
                    if error is CancellationError {
                        for release in pendingReleases.reversed() {
                            _ = postCleanupRelease(release, route:route, observation:o, pointer:false)
                        }
                        throw error
                    }
                    guard posted > 0 else { throw error }
                    let failure = error as? ToolFailure
                    var result: [String:Any] = ["status":"dispatch_interrupted", "route":route, "eventsPosted":posted,
                            "reasonCode":failure?.code ?? "native_error",
                            "reason":failure?.description ?? error.localizedDescription,
                            "verification":"A prefix may have reached the original target; observe its value and focus before any retry"]
                    if !pendingReleases.isEmpty {
                        result["cleanupReleases"] = pendingReleases.reversed().map { postCleanupRelease($0, route:route, observation:o, pointer:false) }
                    }
                    return restoredResult(result)
                }
                event.timestamp = DispatchTime.now().uptimeNanoseconds
                Input.post(event, route: route, pid: o.pid)
                posted += 1
                let code = event.getIntegerValueField(.keyboardEventKeycode)
                if Input.isKeyPress(event) {
                    if let release = events.dropFirst(index + 1).first(where: {
                        $0.getIntegerValueField(.keyboardEventKeycode) == code && !Input.isKeyPress($0)
                    }) { pendingReleases.append(release) }
                } else {
                    pendingReleases.removeAll { $0.getIntegerValueField(.keyboardEventKeycode) == code }
                }
                // Allow the app's event loop to observe down before up, including
                // modifier transitions. Keep revalidation before every event.
                try? await Task.sleep(nanoseconds: 15_000_000)
            }
            try await Task.sleep(nanoseconds: 100_000_000)
            return restoredResult(["status":"dispatched_unverified", "route":route, "eventsPosted":posted, "verification":"Observe the focused value; Unicode events do not emulate IME composition"])
        case "mac_find":
            try a.only(["observation", "role", "title", "identifier", "valueContains", "maxResults"])
            let role = try a.values["role"].map { _ in try a.string("role", limit: 256) }
            let title = try a.values["title"].map { _ in try a.string("title", limit: 4_096) }
            let identifier = try a.values["identifier"].map { _ in try a.string("identifier", limit: 4_096) }
            let valueContains = try a.values["valueContains"].map { _ in try a.string("valueContains", limit: 65_536) }
            guard role != nil || title != nil || identifier != nil || valueContains != nil else {
                throw ToolFailure("invalid_argument", "Supply at least one find predicate: role, title, identifier, or valueContains")
            }
            let limit = try a.integer("maxResults", default: 20, range: 1...100)
            let o = try fresh(a)
            let allMatches = o.nodes.filter { node in
                (role == nil || node.role == role!) &&
                (title == nil || node.title == title!) &&
                (identifier == nil || node.identifier == identifier!) &&
                (valueContains == nil || node.value?.contains(valueContains!) == true)
            }
            return ["status":"searched", "source":"observation_snapshot", "observation":o.id,
                    "coverage":o.coverage, "diagnostics":o.diagnostics, "matchCount":allMatches.count,
                    "truncated":allMatches.count > limit,
                    "valueSearchMayBeIncomplete":valueContains != nil && o.nodes.contains(where: { $0.valueTruncated }),
                    "matches":try allMatches.prefix(limit).map(encodedObject)]
        case "mac_ocr":
            try a.only(["observation", "languages", "timeoutMs"])
            let o = try fresh(a)
            guard o.screenshot != nil else { throw ToolFailure("missing_image", "Observe with screenshot first") }
            let image = try store.image(for: o)
            return ["status":"recognized", "source":"observation_screenshot", "observation":o.id,
                    "text":try await Capture.ocr(image, languages: a.strings("languages"),
                                                 timeoutMilliseconds:a.integer("timeoutMs", default:30_000, range:100...60_000)),
                    "coordinateSystem":"image pixels, top-left origin"]
        case "mac_wait":
            try a.only(["observation", "node", "equals", "contains", "timeoutMs", "pollMs"])
            guard (a.values["equals"] != nil) != (a.values["contains"] != nil) else {
                throw ToolFailure("invalid_argument", "Supply exactly one wait predicate: equals or contains")
            }
            let expectedEquals = try a.values["equals"].map { _ in try a.string("equals") }
            let expectedContains = try a.values["contains"].map { _ in try a.string("contains") }
            let timeout = try a.integer("timeoutMs", default: 5_000, range: 50...10_000)
            let poll = try a.integer("pollMs", default: 100, range: 50...1_000)
            let o = try fresh(a), nodeID = try a.string("node")
            let started = DispatchTime.now().uptimeNanoseconds
            let deadline = started + UInt64(timeout) * 1_000_000
            var attempts = 0
            repeat {
                attempts += 1
                let element = try AX.resolve(o, nodeID: nodeID, requireEnabled: false, requireStableValue: false)
                guard let rawValue = AX.value(element, kAXValueAttribute) as? String else {
                    throw ToolFailure("no_text_value", "Selected node has no plain text value")
                }
                let boundedValue = AX.boundedString(rawValue, limit:65_536)
                guard !boundedValue.truncated else {
                    throw ToolFailure("oversized_ax_value", "Live text exceeds 65536 UTF-8 bytes and cannot be compared safely")
                }
                let value = boundedValue.value
                let matches = expectedEquals.map { value == $0 } ?? value.contains(expectedContains!)
                if matches {
                    return ["status":"predicate_verified", "matches":true, "attempts":attempts,
                            "elapsedMilliseconds":Int((DispatchTime.now().uptimeNanoseconds - started) / 1_000_000),
                            "scope":"Selected live AX text value only"]
                }
                if DispatchTime.now().uptimeNanoseconds >= deadline { break }
                try await Task.sleep(nanoseconds: UInt64(poll) * 1_000_000)
            } while true
            return ["status":"predicate_timeout", "matches":false, "attempts":attempts,
                    "elapsedMilliseconds":timeout, "scope":"Selected live AX text value only"]
        case "mac_verify":
            try a.only(["observation", "node", "equals", "contains"])
            guard (a.values["equals"] != nil) != (a.values["contains"] != nil) else { throw ToolFailure("invalid_argument", "Supply exactly one predicate: equals or contains") }
            if a.values["equals"] != nil { _ = try a.string("equals") }
            else { _ = try a.string("contains") }
            let o = try fresh(a)
            let element = try AX.resolve(o, nodeID: a.string("node"), requireEnabled: false)
            guard let rawValue = AX.value(element, kAXValueAttribute) as? String else {
                throw ToolFailure("no_text_value", "Selected node has no plain text value")
            }
            let boundedValue = AX.boundedString(rawValue, limit:65_536)
            guard !boundedValue.truncated else {
                throw ToolFailure("oversized_ax_value", "Live text exceeds 65536 UTF-8 bytes and cannot be compared safely")
            }
            let value = boundedValue.value
            let matches = try a.values["equals"] != nil ? value == a.string("equals") : value.contains(a.string("contains"))
            return ["status":matches ? "predicate_verified" : "predicate_failed", "matches":matches, "scope":"Selected AX text value only"]
        default: throw ToolFailure("unknown_tool", "Unknown tool: \(tool)")
        }
    }
}
