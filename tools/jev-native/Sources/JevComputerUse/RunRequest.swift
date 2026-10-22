import Foundation

struct RunRequest {
    var spec: TaskSpec
    var chooseApps: Bool
    var allowInteractiveFallback: Bool

    init(arguments: [String]) throws {
        func option(_ key: String) throws -> String? {
            guard let index = arguments.firstIndex(of: key) else { return nil }
            guard arguments.indices.contains(index + 1), !arguments[index + 1].hasPrefix("--") else { throw Failure("Missing value for \(key)") }
            return arguments[index + 1]
        }
        chooseApps = arguments.contains("--simple")
        let auto = arguments.contains("--auto")
        allowInteractiveFallback = !auto
        guard !(chooseApps && auto) else { throw Failure("Use either --auto or --simple, not both.") }
        let explicit = try option("--apps")
        if let path = try option("--task") {
            spec = try JSONDecoder().decode(TaskSpec.self, from: Data(contentsOf: URL(fileURLWithPath: path)))
            // Preserve the existing task-file precedence over CLI --apps.
        } else {
            guard let goal = try option("--goal") else { throw Failure("Missing --goal") }
            let apps = try explicit.map(Self.bundleList) ?? []
            spec = TaskSpec(goal: goal, apps: apps, texts: try option("--text").map { [$0] } ?? [],
                generateText: arguments.contains("--generate-text"), inspectImage: arguments.contains("--inspect-image"),
                maxSteps: Int(try option("--max-steps") ?? "30") ?? 30,
                expectText: try option("--expect-text"), expectApp: try option("--expect-app"))
        }
        guard !(chooseApps || auto) || (explicit == nil && spec.apps.isEmpty) else { throw Failure("Use --apps, --auto, or --simple separately. Task JSON with apps already selects explicit mode.") }
        guard !spec.goal.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty, spec.maxSteps > 0,
              spec.confidence.isFinite, (0...1).contains(spec.confidence), spec.maxRecovery >= 0, spec.settleMS >= 0 else { throw Failure("Invalid goal or task bounds") }
    }

    static func bundleList(_ text: String) throws -> [String] {
        let values = text.split(separator: ",", omittingEmptySubsequences: false).map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
        guard !values.isEmpty, values.allSatisfy({ !$0.isEmpty }) else { throw Failure("--apps requires bundle IDs; omit it for goal-based selection or use --simple.") }
        return values
    }
}
