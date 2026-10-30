from __future__ import annotations

import json
import os
import re
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SWIFT_PLUGIN_ROOT = REPO_ROOT / "plugins" / "swift-intelligence"
SWIFT_PLUGIN_SKILL = SWIFT_PLUGIN_ROOT / "skills" / "swift-intelligence"
IGNORED_NAMES = {".DS_Store", "__pycache__"}
IGNORED_SUFFIXES = {".pyc", ".pyo"}

def tree_files(root: Path) -> dict[str, tuple[int, bytes]]:
    files: dict[str, tuple[int, bytes]] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(part in IGNORED_NAMES or " 2." in part for part in relative.parts):
            continue
        if path.is_file() and path.suffix not in IGNORED_SUFFIXES:
            files[relative.as_posix()] = (path.stat().st_mode & 0o777, path.read_bytes())
    return files

class PluginDistributionTests(unittest.TestCase):
    def test_team_runtime_plugin_policy_and_portable_versions_are_consistent(self):
        runtime = REPO_ROOT / "tools/codex-team-harness"
        version = json.loads((runtime / "manifest.json").read_text())["version"]
        plugin = json.loads((REPO_ROOT / "plugins/team-coordination/.codex-plugin/plugin.json").read_text())
        self.assertEqual(version, plugin["version"])
        for path in (runtime / "payload/team-coordination/policy.json", REPO_ROOT / "team-coordination/policy.json", REPO_ROOT / "plugins/team-coordination/skills/team-coordination/policy.json"):
            self.assertEqual(version, json.loads(path.read_text())["version"])

    def test_marketplace_points_to_available_plugins(self) -> None:
        marketplace = json.loads(
            (REPO_ROOT / ".agents" / "plugins" / "marketplace.json").read_text(encoding="utf-8")
        )
        self.assertEqual("oozoofrog-plugin", marketplace["name"])
        self.assertEqual("oozoofrog-plugin", marketplace["interface"]["displayName"])
        self.assertEqual(
            ["swift-intelligence", "local-ai-studio", "macpilot", "team-coordination", "korean-travel-guidebook", "obsidian-projects", "outcome-brief", "verify-work", "jev-native", "audit", "choice-interview", "korean-product-writing", "interface-first-design", "winpilot", "c4fy", "refactor"],
            [plugin["name"] for plugin in marketplace["plugins"]],
        )
        for entry in marketplace["plugins"]:
            with self.subTest(plugin=entry["name"]):
                self.assertEqual(
                    {"source": "local", "path": f"./plugins/{entry['name']}"},
                    entry["source"],
                )
                self.assertEqual("AVAILABLE", entry["policy"]["installation"])
                self.assertEqual("ON_INSTALL", entry["policy"]["authentication"])
                self.assertEqual("Productivity", entry["category"])
                plugin_root = REPO_ROOT / entry["source"]["path"]
                manifest = json.loads(
                    (plugin_root / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
                )
                self.assertEqual(entry["name"], manifest["name"])
                if "repository" in manifest:
                    self.assertEqual("https://github.com/oozoofrog/oozoofrog-plugin", manifest["repository"])
                skill_root = plugin_root / manifest["skills"] / entry["name"]
                self.assertTrue((skill_root / "SKILL.md").is_file())

    def test_refactor_distribution(self) -> None:
        from test_sync_skill_mirrors import load_module
        from test_document_links import local_targets
        source = REPO_ROOT / "refactor"
        plugin = REPO_ROOT / "plugins/refactor"
        mirror = plugin / "skills/refactor"
        expected = {"SKILL.md", "agents/openai.yaml", "references/swift.md", "references/swiftlint-build.md"}
        self.assertEqual(expected, set(tree_files(source)))
        self.assertEqual(tree_files(source), tree_files(mirror))
        self.assertEqual({".codex-plugin/plugin.json"} | {f"skills/refactor/{p}" for p in expected}, set(tree_files(plugin)))
        self.assertIn("refactor", load_module().PACKAGES)
        refactor_manifest = json.loads((plugin / ".codex-plugin/plugin.json").read_text())
        self.assertEqual("refactor", refactor_manifest["name"])
        self.assertEqual("0.2.0", refactor_manifest["version"])
        self.assertEqual("./skills/", refactor_manifest["skills"])
        for key in ("mcpServers", "apps", "hooks"):
            self.assertNotIn(key, refactor_manifest)
        description = (source / "SKILL.md").read_text().split("description: ", 1)[1].splitlines()[0]
        self.assertEqual(description, refactor_manifest["description"])
        self.assertEqual(description, refactor_manifest["interface"]["longDescription"])
        self.assertIn(description, (REPO_ROOT / "README.md").read_text())
        metadata = {}
        for line in (source / "agents/openai.yaml").read_text().splitlines():
            if line.startswith("  ") and ": " in line:
                key, value = line.strip().split(": ", 1)
                metadata[key] = json.loads(value)
        for yaml_key, json_key in (("display_name", "displayName"), ("short_description", "shortDescription")):
            self.assertEqual(metadata[yaml_key], refactor_manifest["interface"][json_key])
        self.assertEqual([metadata["default_prompt"]], refactor_manifest["interface"]["defaultPrompt"])
        self.assertIn("$refactor", metadata["default_prompt"])
        self.assertLessEqual(len(metadata["default_prompt"]), 128)
        for root in (source, plugin):
            for path in root.rglob("*"):
                self.assertFalse(path.is_symlink(), path)
            for document in root.rglob("*.md"):
                for target in local_targets(document.read_text()):
                    self.assertTrue((document.parent / target).is_file(), (document, target))

    def test_c4fy_distribution(self) -> None:
        source = REPO_ROOT / "c4fy"
        mirror = REPO_ROOT / "plugins/c4fy/skills/c4fy"
        from test_sync_skill_mirrors import load_module
        module = load_module()
        self.assertIn("c4fy", module.PACKAGES)
        self.assertEqual(module.package_files(source), module.package_files(mirror))
        manifest = json.loads((REPO_ROOT / "plugins/c4fy/.codex-plugin/plugin.json").read_text())
        self.assertEqual(manifest["version"], json.loads((source / "package.json").read_text())["version"])
        self.assertIn("description: " + manifest["description"], (source / "SKILL.md").read_text())
        self.assertEqual(manifest["description"], manifest["interface"]["longDescription"])
        self.assertIn("$c4fy", (source / "agents/openai.yaml").read_text())
        self.assertIn("C1/C2/C3/C4", (REPO_ROOT / "README.md").read_text())
        self.assertIn("C1·C2·C3·C4", (source / "agents/openai.yaml").read_text())
        self.assertIn("code", (source / "references/model.md").read_text())
        for name in ("bin/c4fy.mjs", "lib/model.mjs", "lib/layout.mjs", "lib/render.mjs",
                     "assets/viewer.js", "assets/viewer.css", "references/model.md", "LICENSE"):
            self.assertTrue((mirror / name).is_file(), name)
        self.assertTrue((mirror / "bin/c4fy.mjs").stat().st_mode & 0o111)
        self.assertNotIn("dependencies", json.loads((source / "package.json").read_text()))

    def test_c4fy_documented_scope_matches_ui_levels(self) -> None:
        metadata = (REPO_ROOT / "c4fy/agents/openai.yaml").read_text(encoding="utf-8")
        short = next(line.split(": ", 1)[1] for line in metadata.splitlines()
                     if line.strip().startswith("short_description:"))
        levels = re.findall(r"\bC[1-4]\b", json.loads(short))
        self.assertEqual(["C1", "C2", "C3", "C4"], levels)
        for name, code_scope in (("README.md", "optional component-level code structure"),
                                 ("README.ko.md", "컴포넌트 내부의 코드")):
            with self.subTest(document=name):
                section = (REPO_ROOT / name).read_text(encoding="utf-8").split("## C4fy\n", 1)[1].split("\n## ", 1)[0]
                self.assertIn("/".join(levels), section)
                self.assertIn(code_scope, section)
                self.assertNotRegex(section, r"C4 코드[^.\n]*(?:대상이 아닙니다|제외)")

    def test_winpilot_distribution(self) -> None:
        from test_sync_skill_mirrors import load_module
        from test_document_links import local_targets
        source = REPO_ROOT / "winpilot"
        plugin = REPO_ROOT / "plugins/winpilot"
        mirror = plugin / "skills/winpilot"
        module = load_module()
        self.assertEqual(module.package_files(source), module.package_files(mirror))
        manifest = json.loads((plugin / ".codex-plugin/plugin.json").read_text(encoding="utf-8"))
        runtime = json.loads((source / "runtime/distribution.json").read_text())
        self.assertEqual(manifest["version"].split("+")[0], runtime["version"])
        self.assertIn("windows-pilot.exe", runtime["files"])
        self.assertRegex(runtime["sha256"], r"^[a-f0-9]{64}$")
        self.assertIn("<Version>" + runtime["version"] + "</Version>", (source / "tool/WindowsPilot.csproj").read_text())
        config = json.loads((plugin / ".mcp.json").read_text())["mcpServers"]["winpilot"]
        self.assertTrue((plugin / config["args"][2]).is_file())
        self.assertEqual("-Stdio", config["args"][3])
        metadata = dict(line.strip().split(": ", 1) for line in (source / "agents/openai.yaml").read_text(encoding="utf-8").splitlines() if line.startswith("  "))
        self.assertEqual(json.loads(metadata["display_name"]), manifest["interface"]["displayName"])
        self.assertEqual(json.loads(metadata["short_description"]), manifest["interface"]["shortDescription"])
        self.assertIn(json.loads(metadata["default_prompt"]), manifest["interface"]["defaultPrompt"])
        self.assertIn("WinPilot", (REPO_ROOT / "README.md").read_text(encoding="utf-8"))
        self.assertIn("WinPilot", (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8"))
        for root in (source, mirror):
            for document in root.rglob("*.md"):
                if any(part in {"evidence", "bin", "obj", "artifacts"} for part in document.relative_to(root).parts):
                    continue
                for target in local_targets(document.read_text(encoding="utf-8")):
                    self.assertTrue((document.parent / target).exists(), (document, target))
        files = module.package_files(source)
        self.assertFalse(any(part in {"bin", "obj", "artifacts", "evidence"} for name in files for part in Path(name).parts))
        self.assertNotIn("game-start-reference.png", runtime["files"])

    def test_macpilot_distribution(self) -> None:
        source = REPO_ROOT / "macpilot"
        plugin = REPO_ROOT / "plugins" / source.name
        mirror = plugin / "skills" / source.name
        from test_sync_skill_mirrors import load_module
        module = load_module()
        self.assertIn(source.name, module.PACKAGES)
        self.assertEqual(module.package_files(source), module.package_files(mirror))
        for relative in ("assets/app-icon.png", "assets/README.md",
                         "tool/Package.swift", "tool/Sources/MacPilot/Main.swift",
                         "tool/Sources/MacPilotCore/Engine.swift",
                         "tool/Sources/MacPilotFixture/main.swift",
                         "tool/Tests/MacPilotCoreTests/CoreTests.swift",
                         "scripts/verify_mcp.py", "scripts/verify_connection.py", "scripts/verify_runtime.py", "scripts/verify_features.py",
                         "scripts/verify_browser.mjs", "scripts/verify_safari.py", "scripts/verify_preview_drag.swift", "browser/extension/manifest.json",
                         "browser/extension/background.js", "browser/extension/content.js", "browser/extension/popup.html",
                         "browser/extension/popup.js", "references/workflows.md", "references/private-api.md", "references/development.md",
                         "tool/Sources/MacPilotCore/Tasks.swift", "tool/Sources/MacPilotCore/ConnectionDiagnostics.swift",
                         "tool/Tests/MacPilotCoreTests/ConnectionTests.swift", "references/mcp-recovery.md",
                         "tool/Sources/MacPilotCore/PermissionSetup.swift", "tool/Sources/MacPilotCore/PermissionCenter.swift",
                         "tool/Sources/MacPilotCore/PermissionGuide.swift",
                         "tool/Sources/MacPilotCore/PermissionDragOnboarding.swift",
                         "scripts/verify_permissions_none.py", "scripts/verify_input.py",
                         "scripts/permission_unprivileged_probe.swift",
                         "scripts/permission_probe_launcher.swift", "scripts/permission_probe_control.py",
                         "references/permission-validation.md",
                         "tool/Tests/MacPilotCoreTests/PermissionSetupTests.swift",
                         "references/permission-setup.md", "scripts/verify_permission_drag.swift", "tool/Sources/MacPilotCore/BrowserBridge.swift",
                         "tool/Sources/MacPilotCore/SafariBridge.swift", "tool/Sources/MacPilotCore/Improvements.swift",
                         "tool/Sources/MacPilotCore/BrowserDeveloperSettings.swift",
                         "tool/Tests/MacPilotCoreTests/BrowserDeveloperTests.swift",
                         "scripts/verify_browser_developer.py", "references/browser-developer-settings.md",
                         "tool/Sources/MacPilotCore/Recording.swift", "tool/Tests/MacPilotCoreTests/RecordingTests.swift",
                         "scripts/verify_recording_chrome.mjs", "scripts/verify_recording_lifecycle.py", "references/recording.md",
                         "references/capabilities.md", "scripts/verify_capabilities.py",
                         "references/ui-analysis.md", "scripts/verify_analysis.py",
                         "references/simulator.md", "scripts/verify_simulator.py", "scripts/verify_bootstrap.py", "scripts/install-runtime.sh", "runtime/distribution.json",
                         "tool/Sources/MacPilotCore/Simulator.swift", "tool/Sources/MacPilotSimulatorHID/main.m", "tool/Fixtures/SimulatorFixture.m",
                         "tool/Tests/MacPilotCoreTests/SimulatorTests.swift",
                         "tool/Sources/MacPilotCore/UIAnalysis.swift", "tool/Tests/MacPilotCoreTests/UIAnalysisTests.swift",
                         "runtime/image_search_worker.py", "runtime/embeddinggemma2-manifest.json", "runtime/requirements-image-search.txt",
                         "tool/Sources/MacPilotCapabilityFixture/main.swift",
                         "tool/Sources/MacPilotCore/Conditions.swift", "tool/Sources/MacPilotCore/OperationOutcome.swift",
                         "tool/Sources/MacPilotCore/UserInputMonitor.swift", "tool/Sources/MacPilotCore/Tracing.swift",
                         "tool/Sources/MacPilotCore/ImageSearch.swift", "tool/Sources/MacPilotCore/ImageSearchPipeline.swift",
                         "tool/Sources/MacPilotCore/Workflows.swift"):
            self.assertTrue((mirror / relative).is_file(), relative)
        for relative in ("scripts/macpilot", "scripts/build.sh", "scripts/install-runtime.sh", "scripts/verify_simulator.py"):
            if os.name == "nt":
                mode = subprocess.check_output(["git", "ls-files", "--stage", "--", (mirror / relative).relative_to(REPO_ROOT).as_posix()], cwd=REPO_ROOT, text=True).split()[0]
                self.assertEqual("100755", mode, relative)
            else:
                self.assertTrue((mirror / relative).stat().st_mode & 0o111, relative)
        for relative in module.GENERATED_PATHS[source.name]:
            self.assertFalse((mirror / relative).exists(), relative)
        manifest = json.loads((plugin / ".codex-plugin/plugin.json").read_text())
        self.assertEqual(source.name, manifest["name"])
        self.assertEqual("3.5.1", manifest["version"])
        self.assertEqual(manifest["version"], json.loads((source / "browser/extension/manifest.json").read_text())["version"])
        frontmatter = (source / "SKILL.md").read_text().split("---", 2)[1]
        self.assertEqual({"name", "description"}, {line.split(":", 1)[0] for line in frontmatter.splitlines() if ":" in line})
        self.assertIn("description: " + manifest["description"], frontmatter)

        self.assertEqual("./skills/", manifest["skills"])
        for key in ("mcpServers", "apps", "hooks"):
            self.assertNotIn(key, manifest)
        for relative in (".mcp.json", ".app.json", "hooks"):
            self.assertFalse((plugin / relative).exists(), relative)
        metadata = {}
        for line in (source / "agents/openai.yaml").read_text().splitlines():
            if line.startswith("  ") and ": " in line:
                key, value = line.strip().split(": ", 1)
                metadata[key] = json.loads(value)
        self.assertEqual(metadata["display_name"], manifest["interface"]["displayName"])
        self.assertEqual(metadata["short_description"], manifest["interface"]["shortDescription"])
        prompts = manifest["interface"]["defaultPrompt"]
        self.assertIn(metadata["default_prompt"], prompts)
        self.assertTrue(1 <= len(prompts) <= 3)
        for prompt in prompts:
            self.assertIn("$macpilot", prompt)
            self.assertLessEqual(len(prompt), 128)
        from test_document_links import local_targets
        for document in source.rglob("*.md"):
            for target in local_targets(document.read_text(encoding="utf-8")):
                self.assertTrue((document.parent / target).exists(), (document, target))

    def test_retired_packages_are_not_distributed(self) -> None:
        for name in ("gptplease", "gptpro", "gptwork", "astra-orchestrator", "jev-start", "jev-blender-use", "jev-computer-use",
                     "astra-team-building", "figma-computer-use", "session-continuity",
                     "ponytail-beck-tdd", "unreal-agent"):
            self.assertFalse((REPO_ROOT / name / "SKILL.md").exists())
            self.assertFalse((REPO_ROOT / "plugins" / name / ".codex-plugin" / "plugin.json").exists())

    def test_local_ai_studio_distribution(self) -> None:
        source = REPO_ROOT / "local-ai-studio"
        plugin = REPO_ROOT / "plugins" / source.name
        mirror = plugin / "skills" / source.name
        skill_files = {"SKILL.md", "agents/openai.yaml", "references/cli-workflows.md", "references/setup.md", "references/whisper.md"}
        self.assertEqual(skill_files, set(tree_files(source)))
        self.assertEqual(tree_files(source), tree_files(mirror))
        # Exact allowlist excludes weights, generated media, credentials and binaries.
        self.assertEqual(
            {".codex-plugin/plugin.json"}
            | {f"skills/{source.name}/{relative}" for relative in skill_files},
            set(tree_files(plugin)),
        )
        for root in (source, plugin):
            for path in root.rglob("*"):
                self.assertFalse(path.is_symlink(), path)
        manifest = json.loads((plugin / ".codex-plugin" / "plugin.json").read_text())
        self.assertEqual(source.name, manifest["name"])
        self.assertEqual("0.3.0", manifest["version"].split("+")[0])
        self.assertEqual("./skills/", manifest["skills"])
        for key in ("mcpServers", "apps", "hooks"):
            self.assertNotIn(key, manifest)
        prompts = manifest["interface"]["defaultPrompt"]
        self.assertIsInstance(prompts, list)
        self.assertTrue(1 <= len(prompts) <= 3)
        for prompt in prompts:
            self.assertIsInstance(prompt, str)
            self.assertIn("$local-ai-studio", prompt)
            self.assertLessEqual(len(prompt), 128)
        from test_sync_skill_mirrors import load_module
        self.assertIn(source.name, load_module().PACKAGES)
        from test_document_links import local_targets
        for root in (source, mirror):
            for document in root.rglob("*.md"):
                for target in local_targets(document.read_text(encoding="utf-8")):
                    self.assertTrue((document.parent / target).exists(), (document, target))

    def test_local_ai_studio_discovery_metadata(self) -> None:
        source = REPO_ROOT / "local-ai-studio"
        # This package uses only JSON-compatible quoted YAML scalars, no dependencies
        # or explicit-only policy: normal automatic skill discovery remains enabled.
        lines = (source / "agents" / "openai.yaml").read_text().splitlines()
        self.assertEqual(["interface:"], [line for line in lines if line and not line.startswith(" ")])
        scalars = {}
        for line in lines:
            if line.startswith("  "):
                key, value = line.strip().split(": ", 1)
                scalars[key] = json.loads(value)
        self.assertEqual({"display_name", "short_description", "default_prompt"}, set(scalars))
        manifest = json.loads(
            (REPO_ROOT / "plugins" / source.name / ".codex-plugin" / "plugin.json").read_text()
        )
        self.assertEqual(manifest["interface"]["displayName"], scalars["display_name"])
        self.assertEqual(manifest["interface"]["shortDescription"], scalars["short_description"])
        self.assertTrue(25 <= len(scalars["short_description"]) <= 64)
        self.assertIn(scalars["default_prompt"], manifest["interface"]["defaultPrompt"])

    def test_swift_intelligence_plugin_loads_skill_and_mcp_server(self) -> None:
        manifest = json.loads(
            (SWIFT_PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        self.assertEqual("swift-intelligence", manifest["name"])
        self.assertEqual("0.1.0+codex.20260904035318", manifest["version"])
        self.assertEqual("./skills/", manifest["skills"])
        self.assertEqual("./.mcp.json", manifest["mcpServers"])
        self.assertTrue((SWIFT_PLUGIN_SKILL / "SKILL.md").is_file())

        mcp_config = json.loads((SWIFT_PLUGIN_ROOT / ".mcp.json").read_text(encoding="utf-8"))
        server = mcp_config["mcpServers"]["swift-intelligence"]
        self.assertEqual("python3", server["command"])
        self.assertEqual(["./scripts/swift_intelligence_mcp.py"], server["args"])
        self.assertEqual(".", server["cwd"])
        self.assertTrue(server["enabled"])
        self.assertTrue((SWIFT_PLUGIN_ROOT / "scripts" / "swift_intelligence_mcp.py").is_file())

if __name__ == "__main__":
    unittest.main()
