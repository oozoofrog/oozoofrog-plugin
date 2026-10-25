"""Packaging contracts only; agent behavior is evaluated separately."""

import json
import unittest
from pathlib import Path

from test_document_links import local_targets
from test_plugin_distribution import tree_files
from test_sync_skill_mirrors import load_module

ROOT = Path(__file__).resolve().parents[2]
NAME = "interface-first-design"


class InterfaceFirstDistributionTests(unittest.TestCase):
    def test_package_is_portable_and_mirror_is_complete(self):
        source = ROOT / NAME
        plugin = ROOT / "plugins" / NAME
        mirror = plugin / "skills" / NAME
        expected = {"SKILL.md", "agents/openai.yaml", "references/examples.md"}
        self.assertEqual(expected, set(tree_files(source)))
        self.assertEqual(tree_files(source), tree_files(mirror))
        self.assertEqual(
            {".codex-plugin/plugin.json"}
            | {f"skills/{NAME}/{path}" for path in expected},
            set(tree_files(plugin)),
        )
        self.assertIn(NAME, load_module().PACKAGES)
        for root in (source, plugin):
            for path in root.rglob("*"):
                self.assertFalse(path.is_symlink(), path)
            for document in root.rglob("*.md"):
                for target in local_targets(document.read_text()):
                    self.assertTrue((document.parent / target).is_file(), (document, target))

    def test_discovery_metadata_and_documentation_agree(self):
        source = ROOT / NAME
        self.assertTrue((source / "SKILL.md").is_file())
        description = (source / "SKILL.md").read_text().split("description: ", 1)[1].splitlines()[0]
        metadata = {}
        lines = (source / "agents/openai.yaml").read_text().splitlines()
        self.assertEqual(["interface:"], [line for line in lines if line and not line.startswith(" ")])
        for line in lines[1:]:
            key, value = line.strip().split(": ", 1)
            metadata[key] = json.loads(value)
        manifest = json.loads((ROOT / "plugins" / NAME / ".codex-plugin/plugin.json").read_text())
        self.assertEqual(NAME, manifest["name"])
        self.assertEqual("0.1.0", manifest["version"])
        self.assertEqual("./skills/", manifest["skills"])
        self.assertEqual(description, manifest["description"])
        self.assertEqual(description, manifest["interface"]["longDescription"])
        self.assertEqual(metadata["display_name"], manifest["interface"]["displayName"])
        self.assertEqual(metadata["short_description"], manifest["interface"]["shortDescription"])
        self.assertTrue(25 <= len(metadata["short_description"]) <= 64)
        self.assertEqual([metadata["default_prompt"]], manifest["interface"]["defaultPrompt"])
        self.assertIn(f"${NAME}", metadata["default_prompt"])
        for key in ("mcpServers", "hooks", "apps"):
            self.assertNotIn(key, manifest)
        self.assertIn(description, (ROOT / "README.md").read_text())
        for path in ("README.ko.md", "docs/plugin-installation.md", "CHANGELOG.md"):
            self.assertIn(NAME, (ROOT / path).read_text())


if __name__ == "__main__":
    unittest.main()
