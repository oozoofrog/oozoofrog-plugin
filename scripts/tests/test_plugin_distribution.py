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
    def test_marketplace_points_to_available_plugins(self) -> None:
        marketplace = json.loads(
            (REPO_ROOT / ".agents" / "plugins" / "marketplace.json").read_text(encoding="utf-8")
        )
        self.assertEqual("oozoofrog-plugin", marketplace["name"])
        self.assertEqual("oozoofrog-plugin", marketplace["interface"]["displayName"])
        self.assertEqual(
            ['swift-intelligence', 'local-ai-studio', 'jev-native', 'korean-product-writing', 'interface-first-design', 'winpilot', 'c4fy', 'refactor', 'astra-implementation-prompt', 'openai-decisions', 'guided-execution', 'handoff', 'model-advisor'],
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

    def test_claude_marketplace_mirrors_codex_marketplace(self) -> None:
        codex = json.loads((REPO_ROOT / ".agents/plugins/marketplace.json").read_text(encoding="utf-8"))
        claude = json.loads((REPO_ROOT / ".claude-plugin/marketplace.json").read_text(encoding="utf-8"))
        self.assertEqual(codex["name"], claude["name"])
        self.assertEqual("oozoofrog", claude["owner"]["name"])
        self.assertEqual([p["name"] for p in codex["plugins"]], [p["name"] for p in claude["plugins"]])
        for entry in claude["plugins"]:
            with self.subTest(plugin=entry["name"]):
                self.assertEqual(f"./plugins/{entry['name']}", entry["source"])
                plugin_root = REPO_ROOT / entry["source"]
                codex_manifest = json.loads((plugin_root / ".codex-plugin/plugin.json").read_text(encoding="utf-8"))
                manifest = json.loads((plugin_root / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))
                for key in ("name", "version", "description"):
                    self.assertEqual(codex_manifest[key], manifest[key])
                self.assertEqual(codex_manifest["description"], entry["description"])
                self.assertEqual("https://github.com/oozoofrog/oozoofrog-plugin", manifest["repository"])
                self.assertNotIn("interface", manifest)
                self.assertNotIn("skills", manifest)
                self.assertTrue((plugin_root / "skills" / entry["name"] / "SKILL.md").is_file())
                codex_mcp_path = plugin_root / ".mcp.json"
                if not codex_mcp_path.is_file():
                    self.assertNotIn("mcpServers", manifest)
                    continue
                codex_servers = json.loads(codex_mcp_path.read_text(encoding="utf-8"))["mcpServers"]
                self.assertEqual(set(codex_servers), set(manifest["mcpServers"]))
                for name, server in manifest["mcpServers"].items():
                    codex_server = codex_servers[name]
                    self.assertEqual(codex_server["command"], server["command"])
                    self.assertEqual("${CLAUDE_PLUGIN_ROOT}", server["cwd"])
                    expected_args = [
                        "${CLAUDE_PLUGIN_ROOT}/" + arg[2:] if arg.startswith("./") else arg
                        for arg in codex_server["args"]
                    ]
                    self.assertEqual(expected_args, server["args"])

    def test_guided_execution_distribution(self) -> None:
        from test_sync_skill_mirrors import load_module
        source = REPO_ROOT / "guided-execution"
        plugin = REPO_ROOT / "plugins/guided-execution"
        mirror = plugin / "skills/guided-execution"
        expected = {
            "SKILL.md", "agents/openai.yaml", "assets/icon.svg",
            "references/questions.md", "references/execution.md", "references/workspace.md",
            "scripts/loop_workspace.py", "tests/test_loop_workspace.py",
            "references/environment.md", "scripts/loop_control.py", "scripts/render_report.py",
            "tests/test_loop_control.py", "tests/test_render_report.py", "tests/test_project_scenario.py",
            "scripts/serve_dashboard.py", "tests/test_serve_dashboard.py",
        }
        claude_mod = {
            "claude-mod/hooks.json", "claude-mod/register.tsx", "claude-mod/board.test.tsx",
            "claude-mod/types/index.d.ts",
        }
        self.assertEqual(expected, set(tree_files(source)))
        self.assertEqual(tree_files(source), tree_files(mirror))
        self.assertEqual(
            {".codex-plugin/plugin.json", ".claude-plugin/plugin.json"} | claude_mod
            | {f"skills/guided-execution/{path}" for path in expected},
            set(tree_files(plugin)),
        )
        self.assertIn("guided-execution", load_module().PACKAGES)
        manifest = json.loads((plugin / ".codex-plugin/plugin.json").read_text(encoding="utf-8"))
        self.assertEqual("0.5.0", manifest["version"])
        self.assertEqual("./skills/", manifest["skills"])
        for key in ("mcpServers", "apps", "hooks"):
            self.assertNotIn(key, manifest)
        # Codex discovers hooks/hooks.json; the Claude mod lives elsewhere and only the Claude manifest names it.
        self.assertFalse((plugin / "hooks").exists())
        claude = json.loads((plugin / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))
        self.assertEqual("0.5.0", claude["version"])
        self.assertEqual("./claude-mod/hooks.json", claude["hooks"])
        self.assertEqual("./claude-mod/types/index.d.ts", claude["types"])
        self.assertEqual({"modules": ["./register.tsx"]},
                         json.loads((plugin / "claude-mod/hooks.json").read_text(encoding="utf-8")))
        description = (source / "SKILL.md").read_text(encoding="utf-8").split("description: ", 1)[1].splitlines()[0]
        self.assertEqual(description, manifest["description"])
        self.assertEqual(description, manifest["interface"]["longDescription"])
        self.assertIn(description, (REPO_ROOT / "README.md").read_text(encoding="utf-8"))
        metadata = {}
        for line in (source / "agents/openai.yaml").read_text(encoding="utf-8").splitlines():
            if line.startswith("  ") and ": " in line and not line.strip().startswith("allow_"):
                key, value = line.strip().split(": ", 1)
                metadata[key] = json.loads(value)
        self.assertEqual(metadata["short_description"], manifest["interface"]["shortDescription"])
        self.assertEqual([metadata["default_prompt"]], manifest["interface"]["defaultPrompt"])

    def test_openai_decisions_distribution(self) -> None:
        from test_document_links import local_targets
        source = REPO_ROOT / "openai-decisions"
        plugin = REPO_ROOT / "plugins/openai-decisions"
        manifest = json.loads((plugin / ".codex-plugin/plugin.json").read_text())
        metadata = {}
        for line in (source / "agents/openai.yaml").read_text().splitlines():
            if line.startswith("  ") and ": " in line:
                key, value = line.strip().split(": ", 1)
                metadata[key] = json.loads(value)
        self.assertEqual(metadata["display_name"], manifest["interface"]["displayName"])
        self.assertEqual(metadata["short_description"], manifest["interface"]["shortDescription"])
        self.assertEqual([metadata["default_prompt"]], manifest["interface"]["defaultPrompt"])
        self.assertIn(manifest["description"], (REPO_ROOT / "README.md").read_text())
        for root in (source, plugin):
            for path in root.rglob("*"):
                self.assertFalse(path.is_symlink(), path)
            for document in root.rglob("*.md"):
                self.assertNotIn("/Users/oozoofrog", document.read_text())
                for target in local_targets(document.read_text()):
                    self.assertTrue((document.parent / target).is_file(), (document, target))

    def test_refactor_distribution(self) -> None:
        from test_sync_skill_mirrors import load_module
        from test_document_links import local_targets
        source = REPO_ROOT / "refactor"
        plugin = REPO_ROOT / "plugins/refactor"
        mirror = plugin / "skills/refactor"
        expected = {"SKILL.md", "agents/openai.yaml", "references/swift.md", "references/swiftlint-build.md"}
        self.assertEqual(expected, set(tree_files(source)))
        self.assertEqual(tree_files(source), tree_files(mirror))
        self.assertEqual({".codex-plugin/plugin.json", ".claude-plugin/plugin.json"} | {f"skills/refactor/{p}" for p in expected}, set(tree_files(plugin)))
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

    def test_handoff_distribution(self) -> None:
        from test_sync_skill_mirrors import load_module
        source = REPO_ROOT / "handoff"
        plugin = REPO_ROOT / "plugins/handoff"
        expected = {"SKILL.md", "agents/openai.yaml", "scripts/ctx.py", "scripts/ctx_hook.py",
                    "scripts/ctxlib.py", "tests/test_ctx.py"}
        self.assertEqual(expected, set(tree_files(source)))
        self.assertEqual(tree_files(source), tree_files(plugin / "skills/handoff"))
        self.assertEqual({".codex-plugin/plugin.json", ".claude-plugin/plugin.json", "claude-hooks/hooks.json"}
                         | {f"skills/handoff/{path}" for path in expected}, set(tree_files(plugin)))
        self.assertIn("handoff", load_module().PACKAGES)
        codex = json.loads((plugin / ".codex-plugin/plugin.json").read_text(encoding="utf-8"))
        claude = json.loads((plugin / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))
        # Hooks are Claude Code only: Codex discovers hooks/hooks.json, so they live in claude-hooks/.
        for key in ("mcpServers", "apps", "hooks"):
            self.assertNotIn(key, codex)
        self.assertFalse((plugin / "hooks").exists())
        self.assertEqual("./claude-hooks/hooks.json", claude["hooks"])
        hooks = json.loads((plugin / "claude-hooks/hooks.json").read_text(encoding="utf-8"))["hooks"]
        events = {"SessionStart": "session-start", "Stop": "stop", "PreCompact": "pre-compact", "PostCompact": "post-compact"}
        self.assertEqual(set(events), set(hooks))
        for event, arg in events.items():
            (entry,) = hooks[event]
            (hook,) = entry["hooks"]
            self.assertEqual(
                f'python3 -I -B "${{CLAUDE_PLUGIN_ROOT}}/skills/handoff/scripts/ctx_hook.py" {arg}', hook["command"])
            self.assertLessEqual(hook["timeout"], 5)
        self.assertTrue((plugin / "skills/handoff/scripts/ctx_hook.py").is_file())
        description = (source / "SKILL.md").read_text(encoding="utf-8").split("description: ", 1)[1].splitlines()[0]
        self.assertEqual(description, codex["description"])
        self.assertEqual(description, codex["interface"]["longDescription"])
        self.assertIn(description, (REPO_ROOT / "README.md").read_text(encoding="utf-8"))
        metadata = {}
        for line in (source / "agents/openai.yaml").read_text(encoding="utf-8").splitlines():
            if line.startswith("  ") and ": " in line:
                key, value = line.strip().split(": ", 1)
                metadata[key] = json.loads(value)
        for yaml_key, json_key in (("display_name", "displayName"), ("short_description", "shortDescription")):
            self.assertEqual(metadata[yaml_key], codex["interface"][json_key])
        self.assertEqual([metadata["default_prompt"]], codex["interface"]["defaultPrompt"])
        self.assertIn("$handoff", metadata["default_prompt"])
        self.assertLessEqual(len(metadata["default_prompt"]), 128)

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


    def test_mac_automation_packages_are_external(self) -> None:
        from test_sync_skill_mirrors import load_module
        module = load_module()
        for name in ("mac-computer-use", "simulator-pilot"):
            self.assertNotIn(name, module.PACKAGES)
            self.assertFalse((REPO_ROOT / name).exists())
            self.assertFalse((REPO_ROOT / "plugins" / name).exists())
        self.assertIn("https://github.com/oozoofrog/mac-pilot", (REPO_ROOT / "README.md").read_text())


    def test_retired_packages_are_not_distributed(self) -> None:
        for name in ("gptplease", "gptpro", "gptwork", "astra-orchestrator", "jev-start", "jev-blender-use", "jev-computer-use",
                     "astra-team-building", "figma-computer-use", "session-continuity",
                     "ponytail-beck-tdd", "unreal-agent",
                     "team-coordination", "audit", "outcome-brief", "verify-work",
                     "choice-interview", "obsidian-projects", "korean-travel-guidebook"):
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
            {".codex-plugin/plugin.json", ".claude-plugin/plugin.json"}
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
