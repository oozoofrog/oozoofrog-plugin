import XCTest
@testable import JevComputerUse

final class SkillInstallationTests: XCTestCase {
    func testTemplateLookupPrefersBundledResourcesThenExecutableAncestors() throws {
        let (root, installer) = try fixture()
        let checkout = root.appendingPathComponent("checkout")
        let template = checkout.appendingPathComponent("skill/jev-native")
        try FileManager.default.createDirectory(at: template, withIntermediateDirectories: true)
        try FileManager.default.copyItem(at: installer.source.appendingPathComponent("SKILL.md"), to: template.appendingPathComponent("SKILL.md"))
        let binary = checkout.appendingPathComponent(".build/arm64-apple-macosx/release/jev-native")
        let elsewhere = root.appendingPathComponent("elsewhere")
        XCTAssertEqual(SkillInstallation.templateSource(resources: installer.source, executable: binary, workingDirectory: elsewhere).path, installer.source.path)
        XCTAssertEqual(SkillInstallation.templateSource(resources: nil, executable: binary, workingDirectory: elsewhere).path, template.path)
        XCTAssertEqual(SkillInstallation.templateSource(resources: root.appendingPathComponent("missing"), executable: binary, workingDirectory: elsewhere).path, template.path)
    }
    func testTemplateLookupFallsBackToExplicitWorkingDirectory() throws {
        let (root, installer) = try fixture()
        let checkout = root.appendingPathComponent("checkout")
        let template = checkout.appendingPathComponent("skill/jev-native")
        try FileManager.default.createDirectory(at: template, withIntermediateDirectories: true)
        try FileManager.default.copyItem(at: installer.source.appendingPathComponent("SKILL.md"), to: template.appendingPathComponent("SKILL.md"))
        XCTAssertEqual(SkillInstallation.templateSource(resources: nil, executable: root.appendingPathComponent("unrelated/bin/jev-native"), workingDirectory: checkout).path, template.path)
    }
    private func fixture() throws -> (URL, SkillInstallation) {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent("jev-install-test-" + UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        addTeardownBlock { try FileManager.default.removeItem(at: root) }
        let source = root.appendingPathComponent("source/jev-native")
        try FileManager.default.createDirectory(at: source, withIntermediateDirectories: true)
        let common = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent().appendingPathComponent("skill/jev-native/SKILL.md")
        try FileManager.default.copyItem(at: common, to: source.appendingPathComponent("SKILL.md"))
        return (root, SkillInstallation(source: source, executable: root.appendingPathComponent("binary with 'quote'/jev-native"), home: root.appendingPathComponent("home")))
    }
    func testBothUserHostsAndRepeatedInstallPreserveExtraFiles() throws {
        let (_, installer) = try fixture()
        let first = try installer.install(hosts: SkillHost.allCases)
        XCTAssertEqual(first.map(\.status), ["installed", "installed"])
        XCTAssertTrue(first[0].path.contains("/.agents/skills/jev-native"))
        XCTAssertTrue(first[1].path.contains("/.claude/skills/jev-native"))
        let extra = URL(fileURLWithPath: first[0].path).appendingPathComponent("my-notes.txt")
        try "user notes".write(to: extra, atomically: true, encoding: .utf8)
        let second = try installer.install(hosts: SkillHost.allCases)
        XCTAssertEqual(second.map(\.status), ["already_installed", "already_installed"])
        XCTAssertEqual(try String(contentsOf: extra, encoding: .utf8), "user notes")
        let claude = try String(contentsOfFile: first[1].path + "/SKILL.md", encoding: .utf8)
        XCTAssertTrue(claude.contains("`/jev-native`"))
        XCTAssertTrue(claude.contains("real Codex CLI subprocess"))
        XCTAssertTrue(claude.contains("Swift and Apple frameworks"))
        XCTAssertTrue(claude.contains("TextEdit background coordinate dragging did not select text"))
        XCTAssertTrue(claude.contains("'\\''"))
        XCTAssertTrue(claude.contains("setup --import-pasteboard"))
    }
    func testProjectScopesAndExplicitDirectory() throws {
        let (root, installer) = try fixture()
        let project = root.appendingPathComponent("project with spaces")
        try FileManager.default.createDirectory(at: project, withIntermediateDirectories: true)
        let installed = try installer.install(hosts: SkillHost.allCases, scope: "project", project: project)
        XCTAssertTrue(installed.allSatisfy { $0.path.hasPrefix(project.path + "/") })
        let custom = root.appendingPathComponent("custom-skills")
        let override = try installer.install(hosts: [.claude], skillsDirectory: custom)
        XCTAssertEqual(override.first?.path, custom.appendingPathComponent("jev-native").path)
        XCTAssertFalse(FileManager.default.fileExists(atPath: installer.home.path))
    }
    func testAllHostConflictPreflightPreservesUserModificationAndUnrelatedSkills() throws {
        let (_, installer) = try fixture()
        let conflicting = installer.home.appendingPathComponent(".claude/skills/jev-native")
        try FileManager.default.createDirectory(at: conflicting, withIntermediateDirectories: true)
        try "user modified instructions".write(to: conflicting.appendingPathComponent("SKILL.md"), atomically: true, encoding: .utf8)
        let unrelated = conflicting.deletingLastPathComponent().appendingPathComponent("other-skill")
        try FileManager.default.createDirectory(at: unrelated, withIntermediateDirectories: true)
        XCTAssertThrowsError(try installer.install(hosts: SkillHost.allCases))
        XCTAssertFalse(FileManager.default.fileExists(atPath: installer.home.appendingPathComponent(".agents").path))
        XCTAssertEqual(try String(contentsOf: conflicting.appendingPathComponent("SKILL.md"), encoding: .utf8), "user modified instructions")
        XCTAssertTrue(FileManager.default.fileExists(atPath: unrelated.path))
    }
    func testExistingCodexSourceSymlinkIsReusedAndNotDuplicated() throws {
        let (_, installer) = try fixture()
        let legacy = installer.home.appendingPathComponent(".codex/skills/jev-native")
        try FileManager.default.createDirectory(at: legacy.deletingLastPathComponent(), withIntermediateDirectories: true)
        try FileManager.default.createSymbolicLink(at: legacy, withDestinationURL: installer.source)
        let result = try installer.install(hosts: [.codex])
        XCTAssertEqual(result.first?.status, "already_installed")
        XCTAssertEqual(result.first?.path, legacy.path)
        XCTAssertEqual(try FileManager.default.destinationOfSymbolicLink(atPath: legacy.path), installer.source.path)
        XCTAssertFalse(FileManager.default.fileExists(atPath: installer.home.appendingPathComponent(".agents").path))
    }
    func testConflictingLegacyInstallIsPreserved() throws {
        let (_, installer) = try fixture()
        let legacy = installer.home.appendingPathComponent(".codex/skills/jev-native")
        try FileManager.default.createDirectory(at: legacy, withIntermediateDirectories: true)
        try "local edits".write(to: legacy.appendingPathComponent("SKILL.md"), atomically: true, encoding: .utf8)
        XCTAssertThrowsError(try installer.install(hosts: SkillHost.allCases))
        XCTAssertFalse(FileManager.default.fileExists(atPath: installer.home.appendingPathComponent(".claude").path))
    }
    func testDanglingSymlinkAndEmptyDirectoryAreConflicts() throws {
        for symlink in [false, true] {
            let (root, installer) = try fixture()
            let base = root.appendingPathComponent("destination")
            try FileManager.default.createDirectory(at: base, withIntermediateDirectories: true)
            let destination = base.appendingPathComponent("jev-native")
            if symlink { try FileManager.default.createSymbolicLink(atPath: destination.path, withDestinationPath: root.appendingPathComponent("absent").path) }
            else { try FileManager.default.createDirectory(at: destination, withIntermediateDirectories: true) }
            XCTAssertThrowsError(try installer.install(hosts: [.claude], skillsDirectory: base))
            XCTAssertEqual(try FileManager.default.contentsOfDirectory(atPath: base.path), ["jev-native"])
        }
    }
    func testInvalidOptionsNeverInstall() throws {
        let (root, installer) = try fixture()
        for arguments in [[], ["--host", "desktop"], ["--host", "codex", "--scope"], ["--host", "codex", "--force", "yes"], ["--host", "codex", "--host", "claude"]] {
            XCTAssertThrowsError(try SkillInstallOptions(arguments: arguments))
        }
        XCTAssertThrowsError(try installer.install(hosts: [.claude], scope: "global"))
        XCTAssertThrowsError(try installer.install(hosts: [.claude], scope: "project"))
        XCTAssertThrowsError(try installer.install(hosts: [.claude], project: root))
        XCTAssertThrowsError(try installer.install(hosts: SkillHost.allCases, skillsDirectory: root))
        XCTAssertFalse(FileManager.default.fileExists(atPath: installer.home.path))
    }
    func testModifiedInstalledDocumentIsNotUpdated() throws {
        let (_, installer) = try fixture()
        let result = try installer.install(hosts: [.claude])
        let document = URL(fileURLWithPath: result[0].path).appendingPathComponent("SKILL.md")
        let data = try Data(contentsOf: document) + Data("\nUser modification\n".utf8)
        try data.write(to: document)
        XCTAssertThrowsError(try installer.install(hosts: [.claude]))
        XCTAssertEqual(try Data(contentsOf: document), data)
    }
}
