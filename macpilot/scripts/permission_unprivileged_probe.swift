import AppKit
import ApplicationServices

// Development-only executable. Compiled with the unmodified MacPilotCore files
// into a uniquely identified app. Never injects permission results into the core.
@main struct PermissionUnprivilegedProbe {
    @MainActor static func main() throws {
        let environment = ProcessInfo.processInfo.environment
        guard let directory = environment["MACPILOT_PERMISSION_EVIDENCE_DIR"],
              let bundleID = Bundle.main.bundleIdentifier,
              bundleID.hasPrefix("local.macpilot.permissionprobe."),
              let appURL = Bundle.main.bundleURL as URL?, appURL.pathExtension == "app" else {
            throw ToolFailure("probe_configuration", "Use the isolated permission test app")
        }
        let output = URL(fileURLWithPath: directory)
        let targetID = environment["MACPILOT_PERMISSION_TARGET_ID"] ?? "com.apple.Safari"
        func write(_ name: String, _ value: [String: Any]) {
            do { try jsonData(value, pretty: true).write(to: output.appendingPathComponent(name), options: .atomic) }
            catch { fputs("Probe evidence write failed\n", stderr) }
        }
        NSApplication.shared.setActivationPolicy(.accessory)
        NSApplication.shared.finishLaunching()
        if CommandLine.arguments.contains("target") {
            write("target.json", ["pid": getpid(), "processStartID": ProcessIdentity.startID(pid: getpid()) ?? "", "bundleID": bundleID])
            NSApplication.shared.run()
            return
        }
        func permissions() -> [String: Bool] {
            ["accessibility": AXIsProcessTrusted(), "screenCapture": CGPreflightScreenCaptureAccess(),
             "postEvent": CGPreflightPostEventAccess(), "inputMonitoring": CGPreflightListenEventAccess()]
        }
        write("baseline.json", ["pid": getpid(), "processStartID": ProcessIdentity.startID(pid: getpid()) ?? "", "bundleID": bundleID,
            "applicationPath": appURL.path, "permissions": permissions(), "coreVersion": MacPilotRuntime.version,
            "otherPermissions": ["fullDiskAccess": "not_generically_queryable", "files": "not_requested", "clipboard": "not_read"],
            "permissionResultsInjected": false, "tccResetPerformed": false])
        guard permissions().values.allSatisfy({ !$0 }) else {
            write("failure.json", ["status": "blocked", "reason": "A real OS preflight returned a grant; this is not an unprivileged run", "permissions": permissions()])
            return
        }
        let controller = PermissionSetupController(applicationURL: appURL, plan: try PermissionKind.plan("all"), targetBundleID: targetID)
        func snapshot() -> [String: Any] {
            let menu = controller.makeMenu()
            let auto = menu.items.first { $0.title == "자동으로 추가" }
            let frame = controller.window.frame
            return ["permissions": permissions(), "kind": controller.kind.rawValue,
                "visible": controller.window.isVisible, "windowID": controller.window.windowNumber,
                "frame": ["x":frame.minX, "y":CGDisplayBounds(CGMainDisplayID()).height-frame.maxY, "width":frame.width, "height":frame.height],
                "draggable": controller.drag.isDraggable, "tooltip": controller.drag.toolTip ?? "",
                "autoAddExists": auto != nil, "autoAddEnabled": auto?.isEnabled ?? false,
                "onboarding": controller.onboarding.evidence,
                "menu": menu.items.map { ["title":$0.title,"enabled":$0.isEnabled] }]
        }
        controller.show()
        controller.openSettings()
        Task { @MainActor in
            do {
                let state = try await PermissionCenter.automation(bundleID: targetID, request: false, timeout: 3000)
                write("automation-baseline.json", ["status": state.rawValue, "targetBundleID": targetID, "promptRequested": false])
            } catch { write("automation-baseline.json", ["error": error.localizedDescription, "promptRequested": false]) }
        }
        var seen = Set<String>()
        let timer = Timer.scheduledTimer(withTimeInterval: 0.2, repeats: true) { _ in
            MainActor.assumeIsolated {
                write("current.json", snapshot())
                guard let bytes = try? Data(contentsOf: output.appendingPathComponent("command.json")),
                      let command = try? JSONSerialization.jsonObject(with: bytes) as? [String: String],
                      let id = command["id"], UUID(uuidString: id) != nil, seen.insert(id).inserted,
                      let operation = command["operation"] else { return }
                switch operation {
                case "next": controller.next()
                case "previous": controller.previous()
                case "select":
                    let item = NSMenuItem(); item.representedObject = command["kind"] ?? "accessibility"
                    controller.selectKind(item)
                case "auto_add": controller.autoAdd()
                case "request": controller.request()
                case "replay": controller.replayOnboarding()
                case "quit": controller.closeGuide()
                case "inspect": break
                default: write("response-\(id).json", ["status":"invalid_operation"]); return
                }
                DispatchQueue.main.asyncAfter(deadline: .now() + 1) {
                    write("response-\(id).json", ["operation": operation, "snapshot": snapshot()])
                }
            }
        }
        NSApplication.shared.run()
        timer.invalidate()
        write("final.json", ["permissions": permissions()])
        withExtendedLifetime(controller) {}
    }
}
