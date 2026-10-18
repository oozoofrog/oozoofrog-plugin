import Foundation
import CryptoKit

struct TraceSettings: Codable {
    var enabled = false
    var captureText = false
    var captureScreenshots = false
    var maxEntries = 50
    var maxBytes = 32 * 1024 * 1024
}
struct TraceNode: Codable {
    var id: String, role: String, identifier: String
    var enabled: Bool, focused: Bool
    var frame: Rect?
    var title: String?, value: String?
}
struct TraceSnapshot: Codable {
    var observationID: String, coverage: String
    var nodes: [TraceNode]
    var screenshot: String?, screenshotSHA256: String?
}
struct TraceRecord: Codable {
    var schema = "macpilot-trace/1"
    var id: String, createdISO8601: String, tool: String, status: String
    var pid: Int32?, processStartID: String?, windowID: UInt32?
    var elapsedMilliseconds: Int
    var outcome: OperationOutcome
    var before: TraceSnapshot?, after: TraceSnapshot?
    var changedNodeIDs: [String]
    var captureErrors: [String]
}
struct TraceScope {
    var id: String
    var settings: TraceSettings
    var target: Observation?
    var before: Observation?
    var errors: [String]
}

@MainActor enum Tracing {
    static func settings(_ store: Store) throws -> TraceSettings {
        guard try store.names(prefix:"trace-settings").contains("trace-settings.json") else { return TraceSettings() }
        guard let value = try? JSONDecoder().decode(TraceSettings.self, from:store.read("trace-settings.json",maximumBytes:4096)),
              (1...200).contains(value.maxEntries), (1_048_576...67_108_864).contains(value.maxBytes) else {
            throw ToolFailure("invalid_trace_configuration", "Trace settings are invalid; explicitly configure tracing again")
        }
        return value
    }
    static func snapshot(_ observation: Observation, settings: TraceSettings) -> TraceSnapshot {
        TraceSnapshot(observationID:observation.id, coverage:observation.coverage,
                      nodes:observation.nodes.map { node in
            TraceNode(id:node.id, role:node.role, identifier:node.secure ? "" : node.identifier,
                      enabled:node.enabled, focused:node.focused, frame:node.frame,
                      title:settings.captureText && !node.secure ? String(node.title.prefix(256)) : nil,
                      value:settings.captureText && !node.secure ? node.value.map { String($0.prefix(512)) } : nil)
        }, screenshot:settings.captureScreenshots ? observation.screenshot.map { URL(fileURLWithPath:$0).lastPathComponent } : nil,
                      screenshotSHA256:settings.captureScreenshots ? observation.screenshotSHA256 : nil)
    }
    static func begin(tool: String, arguments: [String:Any], engine: Engine) async throws -> TraceScope? {
        let settings = try settings(engine.store)
        guard settings.enabled, tool != "mac_trace", !["mac_task","mac_connection"].contains(tool),
              !Outcomes.isRead(tool,arguments:arguments) || ["mac_wait","mac_wait_for","mac_verify"].contains(tool) else { return nil }
        let id = UUID().uuidString.lowercased()
        var target: Observation?, errors: [String] = []
        if let reference = arguments["observation"] as? String { target = try engine.store.load(reference) }
        else if let parsed = try? Arguments(arguments).integer("pid",range:1...Int(Int32.max)),
                let identity = arguments["processStartID"] as? String,
                let parsedWindow = try? Arguments(arguments).integer("windowID",range:1...Int(UInt32.max)) {
            let pid = Int32(parsed), windowID = UInt32(parsedWindow)
            target = try? await engine.observe(pid:pid,processStartID:identity,windowID:windowID,screenshot:false,maxNodes:200,maxDepth:10)
            if let target { try? engine.store.remove(target.id + ".json") }
        }
        var before: Observation?
        if let target {
            do { before = try await capture(target,settings:settings,traceID:id,phase:"before",engine:engine) }
            catch { errors.append((error as? ToolFailure)?.code ?? "before_capture_failed") }
        }
        return TraceScope(id:id,settings:settings,target:target,before:before,errors:errors)
    }
    static func capture(_ target: Observation, settings: TraceSettings, traceID:String, phase:String, engine: Engine) async throws -> Observation {
        var value = try await engine.observe(pid:target.pid,processStartID:target.processStartID,windowID:target.windowID,
                                 screenshot:settings.captureScreenshots,maxNodes:200,maxDepth:10,captureTimeoutMilliseconds:3000,
                                 privateAPI:target.windowIdentityBackend == "_AXUIElementGetWindow",collectionTimeoutMilliseconds:1000)
        defer { try? engine.store.remove(value.id + ".json"); try? engine.store.remove(value.id + ".png") }
        if settings.captureScreenshots, value.screenshot != nil {
            let image = try engine.store.image(for:value), data = try Capture.png(image)
            let url = engine.store.root.appendingPathComponent("trace-frame-\(traceID)-\(phase).png")
            try engine.store.write(data,to:url); value.screenshot = url.path
            value.screenshotSHA256 = SHA256.hash(data:data).map{String(format:"%02x",$0)}.joined()
        }
        return value
    }
    static func finish(_ scope: TraceScope, tool: String, status: String, outcome: OperationOutcome,
                       elapsedMilliseconds: Int, skipAfterCapture:Bool = false, engine: Engine) async throws -> String {
        var errors = scope.errors, after: Observation?
        if skipAfterCapture { errors.append("after_capture_skipped_user_input") }
        else if let target = scope.target {
            do { after = try await capture(target,settings:scope.settings,traceID:scope.id,phase:"after",engine:engine) }
            catch { errors.append((error as? ToolFailure)?.code ?? "after_capture_failed") }
        }
        // Compare transient values in memory; default persisted records omit text and value hashes.
        let old = Dictionary(uniqueKeysWithValues:(scope.before?.nodes ?? []).map { ($0.id,$0) })
        let changed = (after?.nodes ?? []).filter { node in
            guard !node.secure else { return false }
            guard let previous = old[node.id] else { return true }
            return previous.role != node.role || previous.identifier != node.identifier || previous.value != node.value
                || previous.frame != node.frame || previous.enabled != node.enabled || previous.focused != node.focused
        }.map(\.id)
        let formatter = ISO8601DateFormatter(); formatter.formatOptions = [.withInternetDateTime,.withFractionalSeconds]
        let record = TraceRecord(id:scope.id,createdISO8601:formatter.string(from:Date()),tool:tool,status:status,
                                 pid:scope.target?.pid,processStartID:scope.target?.processStartID,windowID:scope.target?.windowID,
                                 elapsedMilliseconds:elapsedMilliseconds,outcome:outcome,
                                 before:scope.before.map { snapshot($0,settings:scope.settings) },
                                 after:after.map { snapshot($0,settings:scope.settings) },changedNodeIDs:Array(changed.prefix(200)),captureErrors:errors)
        do { try save(record,store:engine.store,settings:scope.settings) }
        catch { try? remove(record,store:engine.store); throw error }
        return record.id
    }
    static func recordNames(_ store: Store) throws -> [String] {
        try store.names(prefix:"trace-").filter { name in
            name.hasSuffix(".json") && UUID(uuidString:String(name.dropFirst(6).dropLast(5))) != nil
        }
    }
    static func load(_ id: String, store: Store) throws -> TraceRecord {
        let key = try Tasks.id(id)
        guard let record = try? JSONDecoder().decode(TraceRecord.self,from:store.read("trace-\(key).json",maximumBytes:2_097_152)), record.id == key else {
            throw ToolFailure("missing_trace", "No bounded trace record with that UUID exists in this task")
        }
        return record
    }
    static func remove(_ record: TraceRecord, store: Store) throws {
        for phase in ["before","after"] { try store.remove("trace-frame-\(try Tasks.id(record.id))-\(phase).png") }
        try store.remove("trace-\(try Tasks.id(record.id)).json")
        try store.remove("trace-view-\(try Tasks.id(record.id)).html")
    }
    static func save(_ record: TraceRecord, store: Store, settings: TraceSettings) throws {
        let data = try JSONEncoder().encode(record)
        guard data.count <= 2_097_152 else { throw ToolFailure("trace_too_large", "Trace record exceeds its bounded size") }
        try store.write(data,to:store.root.appendingPathComponent("trace-\(try Tasks.id(record.id)).json"))
        var rows: [TraceRecord] = []
        for name in try recordNames(store) { rows.append(try load(String(name.dropFirst(6).dropLast(5)),store:store)) }
        rows.sort { left,right in
            if left.createdISO8601 == right.createdISO8601 { return left.id < right.id }
            return left.createdISO8601 < right.createdISO8601
        }
        func size(_ record: TraceRecord) -> Int {
            var names: [String] = ["trace-\(record.id).json", "trace-view-\(record.id).html"]
            if let before = record.before?.screenshot { names.append(before) }
            if let after = record.after?.screenshot { names.append(after) }
            return names.reduce(0) { total,name in total + ((try? store.byteCount(name)) ?? 0) }
        }
        var bytes = rows.reduce(0) {$0 + size($1)}
        while rows.count > settings.maxEntries || bytes > settings.maxBytes {
            let oldest = rows.removeFirst(); bytes -= size(oldest); try remove(oldest,store:store)
        }
        guard rows.contains(where:{$0.id == record.id}) else { throw ToolFailure("trace_budget_exceeded","Trace could not be retained within the configured storage budget") }
    }
    static func object<T:Encodable>(_ value: T) throws -> [String:Any] {
        try JSONSerialization.jsonObject(with:JSONEncoder().encode(value)) as! [String:Any]
    }
    static func escaped(_ value: String) -> String {
        value.replacingOccurrences(of:"&",with:"&amp;").replacingOccurrences(of:"<",with:"&lt;")
            .replacingOccurrences(of:">",with:"&gt;").replacingOccurrences(of:"\"",with:"&quot;")
    }
    static func call(_ a: Arguments, store: Store) throws -> [String:Any] {
        let operation = try a.string("operation")
        switch operation {
        case "configure":
            try a.only(["operation","enabled","captureText","captureScreenshots","maxEntries","maxBytes"])
            var value = (try? settings(store)) ?? TraceSettings()
            value.enabled = try a.bool("enabled",default:value.enabled)
            value.captureText = try a.bool("captureText",default:value.captureText)
            value.captureScreenshots = try a.bool("captureScreenshots",default:value.captureScreenshots)
            value.maxEntries = try a.integer("maxEntries",default:value.maxEntries,range:1...200)
            value.maxBytes = try a.integer("maxBytes",default:value.maxBytes,range:1_048_576...67_108_864)
            try store.write(JSONEncoder().encode(value),to:store.root.appendingPathComponent("trace-settings.json"))
            return ["status":"trace_configured","settings":try object(value),"scope":"This task's private state directory"]
        case "status", "list":
            try a.only(["operation"])
            let rows = try recordNames(store).map { try load(String($0.dropFirst(6).dropLast(5)),store:store) }
            return ["status":"traces","settings":try object(settings(store)),"count":rows.count,
                    "entries":rows.sorted{$0.createdISO8601 < $1.createdISO8601}.map { ["id":$0.id,"createdISO8601":$0.createdISO8601,"tool":$0.tool,"status":$0.status,"outcome":$0.outcome.object] }]
        case "read", "export":
            try a.only(["operation","traceID"])
            let record = try load(a.string("traceID"),store:store)
            if operation == "read" { return ["status":"trace","trace":try object(record)] }
            let pictures = [record.before,record.after].enumerated().compactMap { index,snapshot -> String? in
                guard let snapshot, let name = snapshot.screenshot,
                      name == "trace-frame-\(record.id)-\(index == 0 ? "before" : "after").png" else { return nil }
                return "<figure><img src=\"\(escaped(name))\"><figcaption>\(index == 0 ? "Before" : "After")</figcaption></figure>"
            }.joined()
            let body = "<!doctype html><meta charset=\"utf-8\"><title>MacPilot trace</title><style>body{font:16px system-ui;margin:24px;background:#17191e;color:#eee}section{display:flex;gap:16px}figure{width:48%;margin:0}img{width:100%}pre{white-space:pre-wrap}</style><h1>\(escaped(record.tool))</h1><p>\(escaped(record.status)) · \(record.elapsedMilliseconds) ms</p><section>\(pictures)</section><pre>\(escaped(jsonString(try object(record))))</pre>"
            let url = store.root.appendingPathComponent("trace-view-\(record.id).html")
            try store.write(Data(body.utf8),to:url)
            try save(record,store:store,settings:settings(store))
            return ["status":"trace_exported","path":url.path,"traceID":record.id]
        case "clear":
            try a.only(["operation"])
            let names = try recordNames(store)
            for name in names { try remove(load(String(name.dropFirst(6).dropLast(5)),store:store),store:store) }
            return ["status":"traces_cleared","count":names.count]
        default: throw ToolFailure("invalid_argument","operation must be configure, status, list, read, export or clear")
        }
    }
}
