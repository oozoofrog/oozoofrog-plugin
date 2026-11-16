"""Graph Flow package contracts; no live marketplace installation claims."""

import json
import re
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

from test_document_links import local_targets
from test_plugin_distribution import tree_files

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "plugins/graph-flow"
SKILL = PLUGIN / "skills/graph-flow"


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)


class GraphFlowDistributionTests(unittest.TestCase):
    def test_manifests_and_discovery_metadata_agree(self):
        claude = json.loads((PLUGIN / ".claude-plugin/plugin.json").read_text())
        codex = json.loads((PLUGIN / ".codex-plugin/plugin.json").read_text())
        description = (SKILL / "SKILL.md").read_text().split("description: ", 1)[1].splitlines()[0]
        self.assertIn("name: graph-flow\n", (SKILL / "SKILL.md").read_text())
        self.assertEqual("graph-flow", codex["name"])
        self.assertRegex(codex["version"], r"^\d+\.\d+\.\d+$")
        for key in ("name", "version", "description"):
            self.assertEqual(claude[key], codex[key], key)
        self.assertEqual(description, codex["description"])
        self.assertEqual(description, codex["interface"]["longDescription"])
        self.assertEqual("./skills/", codex["skills"])
        metadata = dict(line.strip().split(": ", 1) for line in
                        (SKILL / "agents/openai.yaml").read_text().splitlines()[1:])
        metadata = {key: json.loads(value) for key, value in metadata.items()}
        for yaml_key, json_key in (("display_name", "displayName"),
                                  ("short_description", "shortDescription")):
            self.assertEqual(metadata[yaml_key], codex["interface"][json_key])
        self.assertTrue(25 <= len(metadata["short_description"]) <= 64)
        self.assertEqual([metadata["default_prompt"]], codex["interface"]["defaultPrompt"])
        self.assertIn("$graph-flow", metadata["default_prompt"])
        for name in ("README.md", "README.ko.md"):
            text = (ROOT / name).read_text()
            for expected in ("graph-flow@oozoofrog-plugin", "$graph-flow",
                             "/graph-flow:graph-flow", "graph-flow serve",
                             "docs/plugin-installation.md#graph-flow"):
                self.assertIn(expected, text, name)
        self.assertIn(description, (ROOT / "README.md").read_text())
        self.assertIn("graph-flow", (ROOT / "CHANGELOG.md").read_text())

    def test_mcp_configurations_resolve_to_the_same_launcher(self):
        claude = json.loads((PLUGIN / ".claude-plugin/plugin.json").read_text())
        codex = json.loads((PLUGIN / ".codex-plugin/plugin.json").read_text())
        # Match winpilot/swift-intelligence: Codex names a config file;
        # Claude uses an inline server rooted at its installed Plugin directory.
        self.assertEqual("./.mcp.json", codex["mcpServers"])
        config = json.loads((PLUGIN / codex["mcpServers"]).read_text())
        self.assertEqual({"graph-flow"}, set(config["mcpServers"]))
        self.assertEqual({"graph-flow"}, set(claude["mcpServers"]))
        local = config["mcpServers"]["graph-flow"]
        installed = claude["mcpServers"]["graph-flow"]
        self.assertEqual("python3", local["command"])
        self.assertEqual(local["command"], installed["command"])
        self.assertEqual(["./skills/graph-flow/scripts/gf", "mcp"], local["args"])
        self.assertEqual(local["args"], [arg.replace("${CLAUDE_PLUGIN_ROOT}", ".")
                                       for arg in installed["args"]])
        self.assertEqual(".", local["cwd"])
        self.assertEqual(local["cwd"], installed["cwd"].replace("${CLAUDE_PLUGIN_ROOT}", "."))
        self.assertTrue(local["enabled"])

    def test_launcher_is_executable_in_git_index(self):
        launcher = SKILL / "scripts/gf"
        self.assertTrue(launcher.is_file())
        result = subprocess.run(
            ["git", "ls-files", "--stage", "--", str(launcher.relative_to(ROOT))],
            cwd=ROOT, check=True, capture_output=True, text=True)
        self.assertEqual(["100755"], [line.split()[0] for line in result.stdout.splitlines()])

    def test_referenced_package_files_exist(self):
        for manifest in (PLUGIN / ".claude-plugin/plugin.json",
                         PLUGIN / ".codex-plugin/plugin.json", PLUGIN / ".mcp.json"):
            for value in strings(json.loads(manifest.read_text())):
                if value.startswith(("./", "${CLAUDE_PLUGIN_ROOT}")):
                    target = value.replace("${CLAUDE_PLUGIN_ROOT}", ".")
                    self.assertTrue((PLUGIN / target).exists(), (manifest, target))
        documents = [SKILL / "SKILL.md", *SKILL.glob("references/*.md"), *PLUGIN.glob("agents/*.md")]
        for document in documents:
            text = document.read_text()
            for target in local_targets(text):
                self.assertTrue((document.parent / target).is_file(), (document, target))
            for target in re.findall(r"<skill-dir>/([^\s`]+)", text):
                self.assertTrue((SKILL / target).is_file(), (document, target))
        self.assertTrue((SKILL / "workflow.js").is_file())
        self.assertTrue((SKILL / "routing.json").is_file())

    def test_dashboard_assets_and_runtime_have_no_vendor_references(self):
        with mock.patch.object(sys, "path", [str(SKILL / "scripts"), *sys.path]):
            from graphflow import server
        assets = [server.PAGE_PATH, *(server.STATIC_ROOT / name for name in server.STATIC_TYPES)]
        for path in assets:
            self.assertTrue(path.is_file(), path)
            self.assertGreater(path.stat().st_size, 0, path)
        for source in (server.PAGE_PATH, server.STATIC_ROOT / "page.js"):
            for target in re.findall(r'/static/([^\s\"\'`<>]+)', source.read_text()):
                self.assertIn(target, server.STATIC_TYPES, (source, target))
        for relative, (_, content) in tree_files(PLUGIN).items():
            self.assertNotIn("vendor", Path(relative).parts, relative)
            # Server tests retain negative fixtures that prove old vendor URLs return 404.
            if "tests" not in Path(relative).parts and Path(relative).suffix in {".md", ".json", ".yaml", ".py", ".js", ".html"}:
                self.assertNotIn("vendor/", content.decode("utf-8"), relative)


if __name__ == "__main__":
    unittest.main()
