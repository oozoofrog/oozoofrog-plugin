import AppKit

// LaunchServices gives the test GUI its own permission identity. Direct shell
// execution may inherit the caller's TCC grants and is not admissible evidence.
let manifestURL = URL(fileURLWithPath: CommandLine.arguments[1])
let manifest = try JSONSerialization.jsonObject(with: Data(contentsOf: manifestURL)) as! [String: Any]
let configuration = NSWorkspace.OpenConfiguration()
configuration.createsNewApplicationInstance = true
configuration.activates = false
configuration.environment = [
    "MACPILOT_STATE_DIR": manifest["stateDirectory"] as! String,
    "MACPILOT_PERMISSION_EVIDENCE_DIR": (manifest["liveEvidenceDirectory"] ?? manifest["evidenceDirectory"]) as! String
]
Task { @MainActor in
    do {
        let app = try await NSWorkspace.shared.openApplication(
            at: URL(fileURLWithPath: manifest["applicationPath"] as! String), configuration: configuration)
        print("launched pid=\(app.processIdentifier)")
        exit(0)
    } catch {
        fputs("Native probe launch failed: \(error.localizedDescription)\n", stderr)
        exit(1)
    }
}
RunLoop.main.run()
