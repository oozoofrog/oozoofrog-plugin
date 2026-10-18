import Foundation

/// Additive transport contract. A verified local predicate is never task acceptance.
public struct OperationOutcome: Codable, Equatable, Sendable {
    public var dispatch: String
    public var effect: String
    public var retry: String
    public var scope: String
    public init(dispatch: String, effect: String, retry: String, scope: String = "operation") {
        self.dispatch = dispatch; self.effect = effect; self.retry = retry; self.scope = scope
    }
    public var object: [String: Any] {
        ["schema":"macpilot-outcome/1", "dispatch":dispatch, "effect":effect, "retry":retry, "scope":scope]
    }
}

public enum Outcomes {
    static let predicateTools: Set<String> = ["mac_wait", "mac_wait_for", "mac_verify"]
    public static func isRead(_ tool: String, arguments: [String: Any]) -> Bool {
        let operation = arguments["operation"] as? String ?? ""
        switch tool {
        case "mac_browser": return ["connections", "receipt", "tabs", "frames", "observe", "verify", "wait", "download_status", "screenshot"].contains(operation)
        case "mac_simulator": return ["list","status","screenshot","observe","probe_input"].contains(operation)
        case "mac_files": return ["stat", "list", "search", "read"].contains(operation)
        case "mac_system": return operation == "info" || (operation == "audio" && arguments["volume"] == nil && arguments["muted"] == nil)
        case "mac_ax": return operation == "read"
        case "mac_window": return operation == "state"
        case "mac_menu": return operation == "list"
        case "mac_record": return ["status", "list", "inspect"].contains(operation)
        case "mac_trace": return ["status", "list", "read", "export"].contains(operation)
        case "mac_image_search": return ["status", "search"].contains(operation)
        case "mac_workflow": return ["list", "read", "validate", "runs", "run_status"].contains(operation)
        case "mac_task": return ["list", "status"].contains(operation)
        default:
            return (ToolCatalog.tools.first(where: { $0["name"] as? String == tool })?["annotations"] as? [String: Any])?["readOnlyHint"] as? Bool == true
        }
    }
    public static func result(_ tool: String, arguments: [String: Any], value: [String: Any]) -> OperationOutcome {
        let status = value["status"] as? String ?? "unknown"
        let read = isRead(tool, arguments: arguments)
        let predicate = predicateTools.contains(tool) || (tool == "mac_browser" && ["verify","wait"].contains(arguments["operation"] as? String ?? ""))
        if status == "already_satisfied" {
            return OperationOutcome(dispatch:"not_needed", effect:"already_satisfied", retry:"not_needed", scope:"operation_postcondition")
        }
        if status == "dispatch_interrupted" || status == "workflow_interrupted" || status == "partial" || status == "partial_completion" {
            return OperationOutcome(dispatch:"partial_or_unknown", effect:"unverified", retry:"observe_before_deciding")
        }
        if predicate {
            let matches = value["matches"] as? Bool == true
            return OperationOutcome(dispatch:"not_applicable", effect:matches ? "predicate_verified" : "predicate_not_met",
                                    retry:matches ? "not_needed" : "read_again", scope:"selected_predicate")
        }
        if status == "workflow_verified" {
            return OperationOutcome(dispatch:"sent", effect:"postconditions_verified", retry:"not_needed", scope:"declared_workflow_postconditions")
        }
        if status == "workflow_postcondition_failed" {
            return OperationOutcome(dispatch:"partial_or_unknown", effect:"predicate_not_met", retry:"observe_before_deciding", scope:"declared_workflow_postconditions")
        }
        if read { return OperationOutcome(dispatch:"not_applicable", effect:"read_completed", retry:"read_again") }
        if status.hasSuffix("_verified") {
            return OperationOutcome(dispatch:"sent", effect:"postcondition_verified", retry:"not_needed", scope:"operation_postcondition")
        }
        if ["task_started", "task_finished", "task_cancelled", "task_resumed", "trace_configured", "image_search_configured", "workflow_saved", "workflow_removed"].contains(status) {
            return OperationOutcome(dispatch:"not_applicable", effect:"state_recorded", retry:"not_needed", scope:"controller_state")
        }
        return OperationOutcome(dispatch:"sent_or_unknown", effect:"unverified", retry:"observe_before_deciding")
    }
    public static func attach(_ tool: String, arguments: [String: Any], value: [String: Any]) -> [String: Any] {
        var result = value
        if result["outcome"] == nil { result["outcome"] = self.result(tool, arguments: arguments, value: value).object }
        return result
    }
    public static func failure(_ tool: String, arguments: [String: Any], beforeDispatch: Bool) -> OperationOutcome {
        if isRead(tool, arguments: arguments) {
            return OperationOutcome(dispatch:"not_applicable", effect:"read_failed", retry:"read_again")
        }
        if beforeDispatch {
            return OperationOutcome(dispatch:"not_sent", effect:"not_checked", retry:"correct_precondition")
        }
        return OperationOutcome(dispatch:"partial_or_unknown", effect:"unverified", retry:"observe_before_deciding")
    }
}
