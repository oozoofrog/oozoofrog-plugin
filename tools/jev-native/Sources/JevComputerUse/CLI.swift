import AppKit
import Foundation

@main struct CLI {
    @MainActor static func main() async {
        // LaunchServices/AppKit bundle discovery follows argv[0]. A CLI symlink outside the app
        // must re-exec this same Swift binary with its real path for Dock/menu identity.
        let invoked = URL(fileURLWithPath:CommandLine.arguments[0]).standardizedFileURL
        let canonical = invoked.resolvingSymlinksInPath()
        if invoked.path != canonical.path, canonical.path.contains(".app/Contents/MacOS/") {
            var args = CommandLine.arguments; args[0] = canonical.path
            let pointers = args.map { strdup($0) } + [nil]
            canonical.path.withCString { _ = execv($0,pointers) }
            fputs("jev-native: self-exec failed\n",stderr); exit(1)
        }
        let args = Array(CommandLine.arguments.dropFirst())
        do {
            let mode = startupMode(args)
            if mode != .cli { try GUIContext.current().requireAvailable() }
            if mode == .application { try runApplication(args) }
            else { try await command(args) }
        } catch { fputs("jev-native: \(error)\n", stderr); exit(1) }
    }
    @MainActor private static func runApplication(_ args: [String]) throws {
        let guiOptions = args.first == "--gui" ? try GUIOptions(arguments: args) : nil
        let app = NSApplication.shared; let delegate = AppDelegate(); app.delegate = delegate; app.setActivationPolicy(.accessory)
        if let guiOptions {
            let goal = GoalWindowController(options: guiOptions); AppDelegate.goal = goal; goal.show()
        } else { Task { @MainActor in
            do { try await command(args); if !args.contains("--keep-open") { app.terminate(nil) } }
            catch { fputs("jev-native: \(error)\n", stderr); exit(1) }
        } }
        app.run()
        withExtendedLifetime(delegate) {}
    }
    @MainActor static func command(_ args: [String]) async throws {
        func option(_ name: String) -> String? { guard let i = args.firstIndex(of: name), args.indices.contains(i+1) else { return nil }; return args[i+1] }
        func require(_ name: String) throws -> String { guard let value = option(name) else { throw Failure("Missing \(name)") }; return value }
        func directory() throws -> String { let path = URL(fileURLWithPath: option("--out") ?? FileManager.default.currentDirectoryPath + "/jev-run-" + UUID().uuidString).standardizedFileURL.path; try FileManager.default.createDirectory(atPath: path, withIntermediateDirectories: true, attributes: [.posixPermissions: 0o700]); return path }
        func configuredNative() -> Native {
            let native = Native()
            native.showVirtualPointer = args.contains("--show-virtual-cursor")
            native.sessionApp = option("--app"); native.allowedApps=native.sessionApp.map { [$0] }; native.sessionWindowID = option("--window").flatMap(UInt32.init)
            return native
        }
        switch args.first ?? "help" {
        case "install-skill":
            let install = try SkillInstallOptions(arguments: Array(args.dropFirst()))
            let results = try SkillInstallation.local().install(hosts: install.hosts, scope: install.scope, project: install.project, skillsDirectory: install.skillsDirectory)
            try emit(results)
            fputs("Skill files are installed. Fresh host discovery and invocation have not been verified by this command.\n", stderr)
        case "setup":
            if args.contains("--open-keys") {
                guard CredentialSetupIO.native().openKeys() else { throw Failure("Could not open https://console.typesafe.ai/keys .") }
                fputs("TypeSafe key management opened. After copying the key, run 'jev-native setup'.\n", stderr)
            } else { _ = try setupCredential(importPasteboard: args.contains("--import-pasteboard")) }
        case "doctor":
            let native = configuredNative()
            struct Doctor: Codable { var permissions: [String: Bool]; var credentialAvailable: Bool; var credentialSource: String; var codexPath: String?; var automationBackend: String; var privateWindowEventAnnotation: Bool; var osVersion: String }
            try emit(Doctor(permissions: native.permissions(), credentialAvailable: (try? credential()) != nil, credentialSource: ProcessInfo.processInfo.environment["TYPESAFE_API_KEY"].map { $0.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? "~/.typesafeai" : "environment" } ?? "~/.typesafeai", codexPath: try? Codex().executable, automationBackend: "Apple AppKit/AX/ScreenCaptureKit/CGEvent/Vision; no external automation backend", privateWindowEventAnnotation: native.windowEvents.available, osVersion: ProcessInfo.processInfo.operatingSystemVersionString))
        case "observe":
            let native = configuredNative()
            let dir = try directory(); let obs = try await native.observe(directory: dir, images: !args.contains("--no-image")); try writeJSON(obs, dir + "/observation.json"); try emit(obs)
        case "ax-query":
            let native=configuredNative(); native.sessionApp=try require("--app"); native.allowedApps=[native.sessionApp!]
            let commands=try JSONDecoder().decode([AXCommand].self,from:Data(contentsOf:URL(fileURLWithPath:require("--requests"))))
            try await performAXCommands(commands,native:native,directory:directory())
        case "act":
            let native = configuredNative()
            let priorPath = try require("--observation"), actionPath = try require("--action"), app = try require("--app")
            var actionRebind: Action?
            let prior = try JSONDecoder().decode(Observation.self, from: Data(contentsOf: URL(fileURLWithPath: priorPath))), action = try JSONDecoder().decode(Action.self, from: Data(contentsOf: URL(fileURLWithPath: actionPath)))
            native.sessionApp = prior.target?.bundle ?? app; native.sessionWindowID = prior.selectedWindow?.id
            let dir = try directory(); let fresh = try await native.observe(directory: dir)
            try writeJSON(fresh, dir + "/before.json")
            if !["launch", "activate"].contains(action.kind) { guard Date().timeIntervalSince(prior.timestamp) < 60, stableTargetState(prior, fresh, action: action) else { throw Failure("Observation stale (>60s) or target UI changed; reobserve") } }
            if let id=action.target, let old=prior.nodes.first(where:{$0.id==id}), let current=fresh.nodes.first(where:{($0.locator ?? $0.id)==(old.locator ?? old.id)}) { var rebound=action; rebound.target=current.id; actionRebind=rebound }
            let pointerBefore = native.pointer(); let start = Date(); try await native.execute(actionRebind ?? action, observation: fresh, allowedApps: [app]); let ms = milliseconds(start); try await Task.sleep(nanoseconds: 250_000_000); let pointerAfter = native.pointer()
            let afterDir = dir + "/after"; try FileManager.default.createDirectory(atPath: afterDir, withIntermediateDirectories: true); let after = try await native.observe(directory: afterDir); try writeJSON(after, afterDir + "/observation.json")
            struct Result: Codable { var executionMS: Double; var pointerBefore: Rect; var pointerAfter: Rect; var virtualPointer: VirtualPointer; var after: Observation }; try emit(Result(executionMS: ms, pointerBefore: pointerBefore, pointerAfter: pointerAfter, virtualPointer: native.virtualPointer, after: after))
        case "run":
            let request = try RunRequest(arguments: Array(args.dropFirst()))
            let dir = try directory()
            let runner = TaskRunner(requireCredential: { if (try? credential()) == nil { _ = try setupCredential() } },
                showVirtualPointer: args.contains("--show-virtual-cursor"))
            let report = try await runner.run(request: request, directory: dir, model: option("--codex-model"), control: RunControl(),
                makePreview: { if args.contains("--no-preview") { return nil }; let preview = PreviewController(); AppDelegate.preview = preview; return preview })
            try emit(report)
            if report.status == "error" { throw Failure(report.error ?? "Run failed; see report.json") }
            if let diagnostic = report.error ?? report.appSelection?.diagnostic { fputs(diagnostic + "\n", stderr) }
            if !["verified_complete", "jev_observed_complete"].contains(report.status), !(args.contains("--keep-open") && AppDelegate.preview != nil) { exit(2) }
        case "delegate":
            let dir = try directory(); let start = Date(); let result = try await Codex().invoke(goal: require("--prompt"), image: option("--image"), directory: dir, model: option("--codex-model")); try writeJSON(result, dir + "/handoff.json"); try emit(result); fputs("codex_total_ms=\(milliseconds(start))\n", stderr)
        default:
            print("""
            jev-native — native macOS computer use (Swift / Apple frameworks)
              --gui [--goal TEXT] [--simple] [--no-preview] [--codex-model MODEL]
              doctor
              setup [--import-pasteboard | --open-keys]
              install-skill --host codex|claude|both [--scope user|project]
                  [--project PATH] [--skills-dir PATH (one host only)]
              observe [--out DIR] [--no-image]
              ax-query --app BUNDLE --requests JSON [--window ID] [--out DIR]
              act --observation JSON --action JSON --app BUNDLE [--out DIR]
              run --goal TEXT [--apps BUNDLE[,BUNDLE] | --auto | --simple] [--text LITERAL]
                  [--generate-text] [--inspect-image] [--codex-model MODEL]
                  [--expect-text TEXT] [--expect-app BUNDLE] [--max-steps N] [--out DIR]
              run --task JSON [--auto | --simple (when apps omitted)] [--codex-model MODEL] [--out DIR]
              delegate --prompt TEXT [--image PNG] [--codex-model MODEL] [--out DIR]
            Run writes screenshots, AX snapshots, decisions, usage and measured timings.
            run exits 2 if blocked, recovery exhausted, or step limit reached.
            Without --apps, select apps from goal; ambiguous interactive runs offer a list.
            --auto never prompts for app selection. --simple chooses from a terminal list.
            Resolved app scopes constrain execution. No shell action is supported.
            """)
        }
    }
}
