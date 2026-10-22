import Foundation
import Darwin

enum SkillHost: String, CaseIterable, Codable { case codex, claude }
struct SkillInstallResult: Codable { var host: SkillHost; var path: String; var status: String }

struct SkillInstallOptions {
    var hosts: [SkillHost]; var scope: String; var project: URL?; var skillsDirectory: URL?
    init(arguments: [String]) throws {
        var values: [String:String] = [:], index = 0
        while index < arguments.count {
            let flag = arguments[index]
            guard ["--host", "--scope", "--project", "--skills-dir"].contains(flag), values[flag] == nil,
                  index+1 < arguments.count, !arguments[index+1].hasPrefix("--"), !arguments[index+1].isEmpty else {
                throw Failure("Invalid install-skill arguments. Use --host codex|claude|both [--scope user|project] [--project PATH] [--skills-dir PATH].")
            }
            values[flag] = arguments[index+1]; index += 2
        }
        if values["--host"] == "both" { hosts = SkillHost.allCases }
        else if let host = values["--host"].flatMap(SkillHost.init(rawValue:)) { hosts = [host] }
        else { throw Failure("--host must be codex, claude, or both (Claude Code).") }
        scope = values["--scope"] ?? "user"
        project = values["--project"].map { URL(fileURLWithPath: $0).standardizedFileURL }
        skillsDirectory = values["--skills-dir"].map { URL(fileURLWithPath: $0).standardizedFileURL }
    }
}

struct SkillInstallation {
    let source: URL
    let executable: URL
    let home: URL
    static func templateSource(resources: URL?, executable: URL, workingDirectory: URL) -> URL {
        var candidates = resources.map { [$0] } ?? []
        var ancestor = executable.deletingLastPathComponent()
        while ancestor.path != "/" {
            candidates.append(ancestor.appendingPathComponent("skill/jev-native"))
            ancestor = ancestor.deletingLastPathComponent()
        }
        let current = workingDirectory.appendingPathComponent("skill/jev-native")
        candidates.append(current)
        return candidates.first { FileManager.default.fileExists(atPath: $0.appendingPathComponent("SKILL.md").path) } ?? current
    }
    static func local() -> Self {
        let resources = Bundle.main.resourceURL?.appendingPathComponent("skills/jev-native")
        let executable = URL(fileURLWithPath: CommandLine.arguments[0]).standardizedFileURL.resolvingSymlinksInPath()
        // Locate resources at runtime; never embed the builder's absolute #filePath in the app.
        return Self(source: templateSource(resources: resources, executable: executable, workingDirectory: URL(fileURLWithPath: FileManager.default.currentDirectoryPath)),
                    executable: executable, home: URL(fileURLWithPath: NSHomeDirectory()))
    }
    func document(for host: SkillHost) throws -> Data {
        var text = try String(contentsOf: source.appendingPathComponent("SKILL.md"), encoding: .utf8)
        guard text.hasPrefix("---\nname: jev-native\n"), text.contains("\ndescription:"), text.contains("# JEV Native\n") else { throw Failure("Companion skill source has invalid frontmatter or title.") }
        let invocation = host == .codex ? "In Codex, invoke `$jev-native` or let the host select this skill for the authorized task." : "In Claude Code, invoke `/jev-native` or let Claude select this skill for the authorized task. This is a local Claude Code skill; it does not install a Claude Desktop, Cowork or cloud integration."
        let hostText = "\n" + invocation + " Original text and image interpretation still use a real Codex CLI subprocess, including when Claude Code invokes this skill. Codex must be installed and authenticated separately. JEV selects typed actions; Swift and Apple frameworks execute and verify them. Do not replace the Codex handoff with an unrecorded host-generated result.\n"
        text = text.replacingOccurrences(of: "# JEV Native\n", with: "# JEV Native\n" + hostText)
        let quoted = "'" + executable.path.replacingOccurrences(of: "'", with: "'\\''") + "'"
        text = text.replacingOccurrences(of: "Use `~/.local/bin/jev-native`.", with: "Use `" + quoted + "`.")
        return Data(text.utf8)
    }
    /// Preflight every host before publishing anything. No overwrite/update mode exists.
    func install(hosts: [SkillHost], scope: String = "user", project: URL? = nil, skillsDirectory: URL? = nil) throws -> [SkillInstallResult] {
        guard ["user", "project"].contains(scope), !hosts.isEmpty else { throw Failure("Use scope user or project and select codex, claude, or both.") }
        guard skillsDirectory == nil || hosts.count == 1 else { throw Failure("--skills-dir requires one host, not both.") }
        guard scope != "project" || project != nil else { throw Failure("Project scope requires --project PATH.") }
        guard project == nil || scope == "project" else { throw Failure("--project requires --scope project.") }
        if let project { var isDirectory: ObjCBool = false; guard FileManager.default.fileExists(atPath: project.path, isDirectory: &isDirectory), isDirectory.boolValue else { throw Failure("Project directory does not exist.") } }
        struct Plan { var host: SkillHost; var path: URL; var data: Data; var existing: Bool }
        var plans: [Plan] = []
        for host in hosts {
            let root = scope == "project" ? project! : home
            let base = skillsDirectory ?? root.appendingPathComponent(host == .codex ? ".agents/skills" : ".claude/skills")
            let path = base.appendingPathComponent("jev-native").standardizedFileURL
            let data = try document(for: host)
            if entryExists(path) {
                guard directoryMatches(path, data: data) else { throw Failure("Skill conflict at \(path.path). Existing installation was preserved; resolve it explicitly before retrying.") }
                plans.append(Plan(host: host, path: path, data: data, existing: true))
                continue
            }
            // Preserve the previously installed Codex source symlink. Do not install a second
            // same-name skill in the newer user location just to migrate an existing setup.
            if host == .codex, scope == "user", skillsDirectory == nil {
                let legacy = home.appendingPathComponent(".codex/skills/jev-native")
                if entryExists(legacy) {
                    let common = try Data(contentsOf: source.appendingPathComponent("SKILL.md"))
                    guard directoryMatches(legacy, data: data) || directoryMatches(legacy, data: common) else {
                        throw Failure("Skill conflict at \(legacy.path). Legacy Codex installation was preserved; no duplicate was installed.")
                    }
                    plans.append(Plan(host: host, path: legacy, data: data, existing: true))
                    continue
                }
            }
            plans.append(Plan(host: host, path: path, data: data, existing: false))
        }
        var results: [SkillInstallResult] = []
        for plan in plans {
            if plan.existing { results.append(.init(host: plan.host, path: plan.path.path, status: "already_installed")); continue }
            let base = plan.path.deletingLastPathComponent()
            try FileManager.default.createDirectory(at: base, withIntermediateDirectories: true)
            let parent = open(base.path, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
            guard parent >= 0 else { throw Failure("Cannot safely open skill destination directory: \(base.path)") }
            defer { close(parent) }
            let staging = ".jev-native-install-" + UUID().uuidString
            guard mkdirat(parent, staging, mode_t(0o700)) == 0 else { throw Failure("Cannot create skill staging directory.") }
            let staged = base.appendingPathComponent(staging)
            defer { try? FileManager.default.removeItem(at: staged) }
            try plan.data.write(to: staged.appendingPathComponent("SKILL.md"), options: .withoutOverwriting)
            // RENAME_EXCL guarantees that even an empty directory or dangling symlink which
            // appeared after preflight is preserved. Use the opened parent for both paths.
            guard renameatx_np(parent, staging, parent, "jev-native", UInt32(RENAME_EXCL)) == 0 else {
                throw Failure("Skill destination appeared or could not be published at \(plan.path.path); nothing there was replaced. Earlier host results, if any, remain installed.")
            }
            results.append(.init(host: plan.host, path: plan.path.path, status: "installed"))
        }
        return results
    }
    private func entryExists(_ url: URL) -> Bool { var info = stat(); return lstat(url.path, &info) == 0 }
    private func directoryMatches(_ url: URL, data: Data) -> Bool {
        var directory: ObjCBool = false
        return FileManager.default.fileExists(atPath: url.path, isDirectory: &directory) && directory.boolValue && (try? Data(contentsOf: url.appendingPathComponent("SKILL.md"))) == data
    }
}
