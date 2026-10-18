import Foundation
import CryptoKit

struct WorkflowCondition {
    var template: AXCondition
    var parameter: String?
    init(_ raw:[String:Any],parameters:Set<String>) throws {
        var value = raw
        parameter = try raw["textParameter"].map { _ in try Arguments(raw).string("textParameter",limit:64) }
        if let parameter {
            guard parameters.contains(parameter), raw["text"] == nil else { throw ToolFailure("invalid_workflow","Unknown or conflicting condition parameter") }
            value.removeValue(forKey:"textParameter"); value["text"] = ""
        }
        template = try AXCondition(value)
        if parameter != nil, ![AXCondition.Predicate.equals,.contains].contains(template.predicate) {
            throw ToolFailure("invalid_workflow","Only text predicates accept textParameter")
        }
    }
    func resolve(_ values:[String:String]) throws -> AXCondition {
        var object = template.object
        if let parameter { object["text"] = values[parameter]! }
        return try AXCondition(object)
    }
    var object: [String:Any] {
        var value = template.object
        if let parameter { value.removeValue(forKey:"text"); value["textParameter"] = parameter }
        return value
    }
}
struct WorkflowStep {
    var action: String
    var selector: AXSelector?
    var text: String?, parameter: String?, key: String?
    var modifiers: [String] = []
    var route = "process"
    var condition: WorkflowCondition
    var timeoutMs: Int
    @MainActor init(_ raw:[String:Any],parameters:Set<String>) throws {
        let a = Arguments(raw); action = try a.string("action",limit:32)
        let allowed: [String]
        switch action {
        case "set_value": allowed = ["action","selector","text","parameter","postcondition","timeoutMs"]
        case "press": allowed = ["action","selector","postcondition","timeoutMs"]
        case "key": allowed = ["action","selector","key","modifiers","route","postcondition","timeoutMs"]
        case "wait": allowed = ["action","condition","timeoutMs"]
        default: throw ToolFailure("invalid_workflow","Only set_value, press, key and wait steps are supported")
        }
        try a.only(allowed); timeoutMs = try a.integer("timeoutMs",default:5000,range:50...10000)
        if action != "wait" {
            guard let value = raw["selector"] as? [String:Any] else { throw ToolFailure("invalid_workflow","A mutation needs an exact selector") }
            selector = try AXSelector(value)
        }
        if action == "set_value" {
            guard (raw["text"] != nil) != (raw["parameter"] != nil) else { throw ToolFailure("invalid_workflow","set_value needs text or parameter") }
            text = try raw["text"].map { _ in try a.string("text",limit:8192) }
            parameter = try raw["parameter"].map { _ in try a.string("parameter",limit:64) }
            if let parameter, !parameters.contains(parameter) { throw ToolFailure("invalid_workflow","Unknown step parameter") }
        }
        if action == "key" {
            key = try a.string("key",limit:64); modifiers = try a.strings("modifiers"); route = try a.string("route",default:"process",limit:16)
            guard Input.keyCodes[key!.lowercased()] != nil, ["process","global"].contains(route) else { throw ToolFailure("invalid_workflow","Invalid physical key or route") }
            _ = try Input.flags(modifiers)
        }
        let conditionKey = action == "wait" ? "condition" : "postcondition"
        guard let rawCondition = raw[conditionKey] as? [String:Any] else { throw ToolFailure("invalid_workflow","Each mutation needs a postcondition; wait needs a condition") }
        condition = try WorkflowCondition(rawCondition,parameters:parameters)
    }
    var object: [String:Any] {
        var value: [String:Any] = ["action":action,"timeoutMs":timeoutMs]
        if let selector { value["selector"] = selector.object }
        if let text { value["text"] = text }; if let parameter { value["parameter"] = parameter }
        if let key { value["key"] = key; value["modifiers"] = modifiers; value["route"] = route }
        value[action == "wait" ? "condition" : "postcondition"] = condition.object
        return value
    }
}
struct WorkflowDefinition {
    var name: String
    var parameters: [String]
    var steps: [WorkflowStep]
    @MainActor init(_ raw:[String:Any]) throws {
        let a = Arguments(raw); try a.only(["name","parameters","steps"])
        name = try a.string("name",limit:64); _ = try Workflows.name(name)
        parameters = try a.strings("parameters")
        guard Set(parameters).count == parameters.count, parameters.allSatisfy({(try? Workflows.name($0)) != nil}),
              let rawSteps = raw["steps"] as? [[String:Any]], (1...24).contains(rawSteps.count) else { throw ToolFailure("invalid_workflow","A plan needs 1–24 steps and unique short parameter names") }
        let parameterNames = Set(parameters)
        steps = try rawSteps.map { try WorkflowStep($0,parameters:parameterNames) }
    }
    var object: [String:Any] { ["name":name,"parameters":parameters,"steps":steps.map(\.object)] }
}
struct WorkflowReceipt: Codable {
    var schema = "macpilot-workflow-run/1"
    var id: String, name: String, requestDigest: String, createdISO8601: String
    var pid: Int32, processStartID: String, windowID: UInt32
    var status: String, currentStep: Int, stepsCompleted: Int, mutationsDispatched: Int
    var stepStates: [String]
    var reasonCode: String?
}

@MainActor enum Workflows {
    static func name(_ raw:String) throws -> String {
        guard !raw.isEmpty, raw.utf8.count <= 64, raw.allSatisfy({$0.isASCII && ($0.isLetter || $0.isNumber || "_-".contains($0))}) else { throw ToolFailure("invalid_workflow","Workflow/parameter names use 1–64 ASCII letters, digits, hyphens or underscores") }
        return raw
    }
    static func definition(_ raw:Any?) throws -> WorkflowDefinition {
        guard let value = raw as? [String:Any] else { throw ToolFailure("invalid_workflow","definition must be an object") }
        return try WorkflowDefinition(value)
    }
    static func load(_ name:String,store:Store) throws -> WorkflowDefinition {
        let data = try store.read("workflow-definition-\(try self.name(name)).json",maximumBytes:131072)
        return try definition(JSONSerialization.jsonObject(with:data))
    }
    static func saveReceipt(_ receipt:WorkflowReceipt,store:Store) throws {
        try store.write(JSONEncoder().encode(receipt),to:store.root.appendingPathComponent("workflow-run-\(try Tasks.id(receipt.id)).json"))
    }
    static func receipt(_ id:String,store:Store) throws -> WorkflowReceipt {
        let key = try Tasks.id(id)
        guard let value = try? JSONDecoder().decode(WorkflowReceipt.self,from:store.read("workflow-run-\(key).json",maximumBytes:65536)), value.id == key else {
            throw ToolFailure("missing_workflow_run","No bounded workflow receipt exists with that UUID")
        }
        return value
    }
    static func inspect(_ a:Arguments,store:Store) throws -> [String:Any] {
        let operation = try a.string("operation")
        if operation == "run_status" {
            try a.only(["operation","runID"])
            return ["status":"workflow_run","run":try Tracing.object(receipt(a.string("runID"),store:store))]
        }
        try a.only(["operation"])
        let rows = try store.names(prefix:"workflow-run-").filter { name in name.hasSuffix(".json") && UUID(uuidString:String(name.dropFirst(13).dropLast(5))) != nil }
        return ["status":"workflow_runs","runs":try rows.suffix(100).map { try Tracing.object(receipt(String($0.dropFirst(13).dropLast(5)),store:store)) }]
    }
    static func call(_ a:Arguments,engine:Engine) async throws -> [String:Any] {
        let operation = try a.string("operation")
        switch operation {
        case "validate", "save":
            try a.only(operation == "save" ? ["operation","definition","overwrite"] : ["operation","definition"])
            let definition = try definition(a.values["definition"])
            if operation == "save" {
                if try engine.store.byteCount("workflow-definition-\(definition.name).json") != nil, try !a.bool("overwrite") {
                    throw ToolFailure("workflow_exists","The saved definition exists; explicit overwrite=true is required")
                }
                let existing = try engine.store.names(prefix:"workflow-definition-").filter{$0.hasSuffix(".json")}
                guard existing.count < 100 || existing.contains("workflow-definition-\(definition.name).json") else { throw ToolFailure("workflow_limit","At most 100 workflow definitions are retained per task") }
                try engine.store.write(jsonData(definition.object),to:engine.store.root.appendingPathComponent("workflow-definition-\(definition.name).json"))
            }
            return ["status":operation == "save" ? "workflow_saved" : "workflow_validated","definition":definition.object,
                    "verification":"The entire bounded plan is structurally valid; no application action was performed"]
        case "list":
            try a.only(["operation"])
            let names = try engine.store.names(prefix:"workflow-definition-").filter{$0.hasSuffix(".json")}.prefix(100)
            return ["status":"workflows","definitions":try names.map { try load(String($0.dropFirst(20).dropLast(5)),store:engine.store).object }]
        case "read", "remove":
            try a.only(["operation","name"])
            let definition = try load(a.string("name",limit:64),store:engine.store)
            if operation == "remove" { try engine.store.remove("workflow-definition-\(definition.name).json") }
            return ["status":operation == "read" ? "workflow" : "workflow_removed","definition":definition.object]
        case "run": return try await run(a,engine:engine)
        case "remove_run":
            try a.only(["operation","runID"])
            let record = try receipt(a.string("runID"),store:engine.store)
            guard record.status != "running" else { throw ToolFailure("workflow_running","An active workflow receipt cannot be removed") }
            try engine.store.remove("workflow-run-\(record.id).json")
            return ["status":"workflow_run_removed","runID":record.id]
        case "runs", "run_status": return try inspect(a,store:engine.store)
        default: throw ToolFailure("invalid_argument","Unsupported workflow operation")
        }
    }
    static func run(_ a:Arguments,engine:Engine) async throws -> [String:Any] {
        try a.only(["operation","definition","name","parameters","pid","processStartID","windowID","runID","allowGlobalInput","timeoutMs","privateAPI"])
        guard (a.values["definition"] != nil) != (a.values["name"] != nil) else { throw ToolFailure("invalid_workflow","Supply one inline definition or saved name") }
        let plan = try a.values["definition"].map { try definition($0) } ?? load(a.string("name",limit:64),store:engine.store)
        let pid = Int32(try a.integer("pid",range:1...Int(Int32.max))), identity = try a.string("processStartID",limit:64)
        let windowID = UInt32(try a.integer("windowID",range:1...Int(UInt32.max))), privateAPI = try a.bool("privateAPI")
        let timeout = try a.integer("timeoutMs",default:60000,range:100...60000), allowGlobal = try a.bool("allowGlobalInput")
        let values = a.values["parameters"] as? [String:Any] ?? [:]
        guard a.values["parameters"] == nil || a.values["parameters"] is [String:Any], Set(values.keys) == Set(plan.parameters) else { throw ToolFailure("invalid_workflow","Provide exactly the declared parameters") }
        var parameters: [String:String] = [:]
        for parameter in plan.parameters { parameters[parameter] = try Arguments(values).string(parameter,limit:8192) }
        guard allowGlobal || !plan.steps.contains(where:{$0.route == "global"}) else { throw ToolFailure("foreground_required","A plan with global keys needs explicit allowGlobalInput=true and a foreground-enabled task") }
        let runID = try a.values["runID"].map { _ in try Tasks.id(a.string("runID")) } ?? UUID().uuidString.lowercased()
        let digest = EmbeddingCache.hash(try jsonData(["definition":plan.object,"parameters":parameters,"pid":pid,"processStartID":identity,"windowID":windowID,"privateAPI":privateAPI]))
        if try engine.store.byteCount("workflow-run-\(runID).json") != nil {
            let existing = try receipt(runID,store:engine.store)
            guard existing.requestDigest == digest else { throw ToolFailure("workflow_run_mismatch","This runID belongs to different arguments; no step was executed") }
            return ["status":"workflow_run_exists","run":try Tracing.object(existing),"verification":"No replay was performed; reconcile the recorded state before deciding on a new run"]
        }
        guard try engine.store.names(prefix:"workflow-run-").filter({$0.hasSuffix(".json")}).count < 256 else {
            throw ToolFailure("workflow_run_limit","Inspect and explicitly remove completed run receipts before starting more runs")
        }
        try ProcessIdentity.require(pid:pid,expected:identity)
        var record = WorkflowReceipt(id:runID,name:plan.name,requestDigest:digest,createdISO8601:ISO8601DateFormatter().string(from:Date()),
                                     pid:pid,processStartID:identity,windowID:windowID,status:"running",currentStep:0,stepsCompleted:0,mutationsDispatched:0,
                                     stepStates:Array(repeating:"not_started",count:plan.steps.count))
        try saveReceipt(record,store:engine.store)
        let started = DispatchTime.now().uptimeNanoseconds, deadline = started + UInt64(timeout)*1_000_000
        var results: [[String:Any]] = []
        do {
            for (index,step) in plan.steps.enumerated() {
                try engine.checkWorkflowState(); try ProcessIdentity.require(pid:pid,expected:identity)
                let now = DispatchTime.now().uptimeNanoseconds
                guard now < deadline else { throw ToolFailure("workflow_timeout","The workflow deadline elapsed; no following step was dispatched") }
                record.currentStep = index
                let condition = try step.condition.resolve(parameters)
                if step.action != "wait" {
                    let observation = try await engine.observe(pid:pid,processStartID:identity,windowID:windowID,screenshot:false,maxNodes:1000,maxDepth:30,privateAPI:privateAPI)
                    let selection = try AXCondition(["selector":step.selector!.object,"predicate":"exists"])
                    guard let node = try selection.selected(in:observation), node.enabled else { throw ToolFailure("workflow_target_unavailable","The step target is missing or disabled") }
                    var args: [String:Any] = ["observation":observation.id,"node":node.id]
                    let already = step.action == "set_value" && node.value == (step.text ?? parameters[step.parameter!])
                    var result: [String:Any]
                    if already { result = ["status":"already_satisfied"] }
                    else {
                        record.stepStates[index] = "dispatching"; try saveReceipt(record,store:engine.store)
                        let tool: String
                        if step.action == "key" { tool = "mac_key"; args["key"] = step.key!; args["modifiers"] = step.modifiers; args["route"] = step.route }
                        else { tool = "mac_ax"; args["operation"] = step.action == "press" ? "action" : "set_value"; if step.action == "set_value" { args["text"] = step.text ?? parameters[step.parameter!]! } }
                        result = try await engine.executeWorkflowStep(tool,arguments:args)
                        record.mutationsDispatched += 1; record.stepStates[index] = "dispatched"; try saveReceipt(record,store:engine.store)
                        if result["status"] as? String == "dispatch_interrupted" {
                            record.status = "interrupted"; record.reasonCode = result["reasonCode"] as? String; try saveReceipt(record,store:engine.store)
                            return ["status":"workflow_interrupted","run":try Tracing.object(record),"reasonCode":record.reasonCode ?? "dispatch_interrupted","steps":results + [result]]
                        }
                    }
                    results.append(result)
                }
                let remaining = Int((deadline - min(deadline,DispatchTime.now().uptimeNanoseconds))/1_000_000)
                guard remaining >= 1 else { throw ToolFailure("workflow_timeout","The workflow deadline elapsed after dispatch; reconcile state before deciding") }
                let verification = try await Conditions.wait(condition,pid:pid,identity:identity,windowID:windowID,timeoutMs:min(step.timeoutMs,remaining),
                                                             maxNodes:1000,maxDepth:30,privateAPI:privateAPI,engine:engine,checkState:{try engine.checkWorkflowState()})
                if let observation = verification["observation"] as? [String:Any], let id = observation["id"] as? String { try? engine.store.remove(id + ".json") }
                guard verification["matches"] as? Bool == true else {
                    record.status = "postcondition_failed"; record.stepStates[index] = "postcondition_failed"; try saveReceipt(record,store:engine.store)
                    return ["status":"workflow_postcondition_failed","run":try Tracing.object(record),"steps":results,"verification":"Only the completed prefix ran. No action was retried and no following step was dispatched"]
                }
                record.stepStates[index] = "verified"; record.stepsCompleted += 1; try saveReceipt(record,store:engine.store)
            }
            record.status = "verified"; try saveReceipt(record,store:engine.store)
            return ["status":"workflow_verified","run":try Tracing.object(record),"steps":results,"verification":"Exactly the declared workflow postconditions were verified; business acceptance remains external"]
        } catch {
            record.status = error is CancellationError || (error as? ToolFailure)?.code == "task_cancelled" ? "cancelled" : "interrupted"
            record.reasonCode = (error as? ToolFailure)?.code ?? (error is CancellationError ? "cancelled" : "native_error")
            try? saveReceipt(record,store:engine.store)
            if error is CancellationError { throw error }
            return ["status":"workflow_interrupted","run":try Tracing.object(record),"reasonCode":record.reasonCode!,"steps":results,
                    "verification":"A prefix may have run. No automatic replay or rollback was attempted; inspect run_status and current app state"]
        }
    }
}
