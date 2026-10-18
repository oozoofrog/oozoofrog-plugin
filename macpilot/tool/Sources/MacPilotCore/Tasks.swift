import AppKit
import Darwin

public final class StateLease {
    private let descriptor: Int32
    init(_ descriptor: Int32) { self.descriptor = descriptor }
    deinit { flock(descriptor, LOCK_UN); Darwin.close(descriptor) }
}

public struct TaskRecord: Codable {
    public var id: String
    public var goal: String
    public var expected: String
    public var pid: Int32?
    public var processStartID: String?
    public var windowID: UInt32?
    public var preserveForeground: Bool
    public var status: String
    public var created: Date
    public var deadline: Date
    public var interruptionReason: String? = nil
    public var object: [String: Any] {
        (try? JSONSerialization.jsonObject(with: JSONEncoder().encode(self))) as? [String: Any] ?? [:]
    }
}

public enum Tasks {
    public static func id(_ raw: String) throws -> String {
        guard let uuid = UUID(uuidString: raw) else { throw ToolFailure("invalid_argument", "taskID must be a UUID") }
        return uuid.uuidString.lowercased()
    }
    public static func load(_ raw: String, in store: Store) throws -> TaskRecord {
        let key = try id(raw)
        guard let record = try? JSONDecoder().decode(TaskRecord.self, from: store.read("task-\(key).json")), record.id == key else {
            throw ToolFailure("missing_task", "Task does not exist in this MacPilot state directory")
        }
        return record
    }
    public static func save(_ record: TaskRecord, in store: Store) throws {
        try store.write(JSONEncoder().encode(record), to: store.root.appendingPathComponent("task-\(id(record.id)).json"))
    }
    public static func state(_ raw: String, in store: Store) throws -> Store {
        _ = try load(raw, in: store)
        return try Store(root: store.root.appendingPathComponent("task-\(id(raw))", isDirectory: true))
    }
    public static func requireActive(_ record: TaskRecord) throws {
        guard record.status == "active" else { throw ToolFailure("task_\(record.status)", "Task is \(record.status)") }
        guard record.deadline > Date() else { throw ToolFailure("task_expired", "Task deadline elapsed") }
        if let pid = record.pid, let identity = record.processStartID { try ProcessIdentity.require(pid: pid, expected: identity) }
    }
    public static func interrupt(_ id: String, reason: String, store: Store) throws {
        let lease = try store.lease(".tasks.lock"); defer { withExtendedLifetime(lease) {} }
        var record = try load(id, in: store)
        guard record.status == "active" else { return }
        record.status = "interrupted"; record.interruptionReason = reason; try save(record, in: store)
    }
    @MainActor public static func call(_ a: Arguments, store: Store) throws -> [String: Any] {
        let operation = try a.string("operation")
        switch operation {
        case "begin":
            try a.only(["operation", "goal", "expected", "pid", "processStartID", "windowID", "preserveForeground", "durationSeconds"])
            let pid = a.values["pid"] == nil ? nil : Int32(try a.integer("pid", range: 1...Int(Int32.max)))
            let identity = a.values["processStartID"] == nil ? nil : try a.string("processStartID", limit: 64)
            guard (pid == nil) == (identity == nil), a.values["windowID"] == nil || pid != nil else {
                throw ToolFailure("invalid_argument", "Specify pid and processStartID together; windowID requires both")
            }
            if let pid, let identity { try ProcessIdentity.require(pid: pid, expected: identity) }
            let duration = try a.integer("durationSeconds", default: 1800, range: 1...28_800)
            let record = TaskRecord(id: UUID().uuidString.lowercased(), goal: try a.string("goal", default: "", limit: 4096),
                                    expected: try a.string("expected", default: "", limit: 4096), pid: pid, processStartID: identity,
                                    windowID: a.values["windowID"] == nil ? nil : UInt32(try a.integer("windowID", range: 1...Int(UInt32.max))),
                                    preserveForeground: try a.bool("preserveForeground", default: true), status: "active",
                                    created: Date(), deadline: Date().addingTimeInterval(Double(duration)))
            try save(record, in: store)
            let state = try state(record.id, in: store)
            return ["status": "task_started", "task": record.object, "stateDirectory": state.root.path]
        case "list":
            try a.only(["operation"])
            let records = try store.names(prefix: "task-").filter { $0.hasSuffix(".json") }.compactMap { name in
                try? JSONDecoder().decode(TaskRecord.self, from: store.read(name)).object
            }
            return ["status": "tasks", "tasks": records]
        case "status", "cancel", "finish", "resume":
            try a.only(["operation", "taskID"])
            var record = try load(a.string("taskID"), in: store)
            if operation == "resume" {
                guard record.status == "interrupted" else { throw ToolFailure("task_not_interrupted", "Only an interrupted task can be explicitly resumed") }
                guard record.deadline > Date() else { throw ToolFailure("task_expired", "Task deadline elapsed") }
                if let pid = record.pid, let identity = record.processStartID { try ProcessIdentity.require(pid: pid, expected: identity) }
                let state = try state(record.id,in:store)
                // User activity can change focus and meaning without changing a
                // node's bytes. Never revive pre-interruption input evidence.
                for name in try state.names(prefix:"") where name.hasSuffix(".json") {
                    let reference = String(name.dropLast(5))
                    if UUID(uuidString:reference) != nil {
                        try state.remove(name); try state.remove(reference + ".png")
                    }
                }
                record.status = "active"; record.interruptionReason = nil; try save(record, in: store)
                return ["status":"task_resumed", "task":record.object, "verification":"Controller state resumed; make a fresh observation before input"]
            }
            if operation != "status" {
                guard ["active","interrupted"].contains(record.status) else { return ["status": "task_\(record.status)", "task": record.object] }
                record.status = operation == "cancel" ? "cancelled" : "finished"
                try save(record, in: store)
            }
            return ["status": "task_\(record.status)", "task": record.object]
        default: throw ToolFailure("invalid_argument", "operation must be begin, list, status, cancel, finish or resume")
        }
    }
}
