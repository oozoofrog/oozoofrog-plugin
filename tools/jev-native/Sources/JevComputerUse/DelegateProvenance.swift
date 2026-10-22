import Foundation

struct DelegateProvenance: Codable {
    var kind: String
    var sourceObservation: String
    var requestedModel: String?
    var reportedModel: String? = nil
    var usage: [String:Int] = [:]
    var status: String
    var eventsFile = "codex-events.jsonl"
    var outputFile = "codex-result.json"
    var textUTF16 = 0
    var source: DocumentSourceEvidence? = nil

    static func completed(kind: String, observation: String, model: String?, directory: String, handoff: Handoff, source: DocumentSourceEvidence?) -> Self {
        var trace = Self(kind:kind,sourceObservation:observation,requestedModel:model,status:"completed",textUTF16:handoff.text.utf16.count,source:source)
        if let events = try? String(contentsOfFile:directory + "/codex-events.jsonl",encoding:.utf8) {
            for line in events.split(separator:"\n") {
                guard let event = (try? JSONSerialization.jsonObject(with:Data(line.utf8))) as? [String:Any] else { continue }
                if let model = event["model"] as? String { trace.reportedModel = model }
                if let usage = event["usage"] as? [String:Int] { trace.usage = usage }
            }
        }
        // A host default is not an observed model identifier; leave reportedModel nil when unavailable.
        return trace
    }
}
