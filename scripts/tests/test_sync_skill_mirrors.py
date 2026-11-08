from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "sync_skill_mirrors.py"


def load_module():
    name = f"sync_skill_mirrors_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class SyncSkillMirrorsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="skill-mirror-test-")
        self.root = Path(self.temporary.name)
        self.source = self.root / "fixture-skill"
        self.mirror = self.root / "plugins" / "fixture-skill" / "skills" / "fixture-skill"
        self.source.mkdir()
        (self.source / "SKILL.md").write_text("---\nname: fixture-skill\n---\n", encoding="utf-8")
        (self.source / "README.md").write_text("source\n", encoding="utf-8")
        self.module = load_module()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_check_then_atomic_write_and_recheck(self) -> None:
        before = self.module.sync_one(self.source, self.mirror, write=False)
        self.assertFalse(before["current"])
        self.assertFalse(before["write_performed"])
        written = self.module.sync_one(self.source, self.mirror, write=True)
        self.assertTrue(written["current"])
        self.assertTrue(written["write_performed"])
        self.assertEqual(
            self.module.package_files(self.source), self.module.package_files(self.mirror)
        )
        current = self.module.sync_one(self.source, self.mirror, write=False)
        self.assertTrue(current["current"])
        self.assertFalse(current["write_performed"])

    def test_source_symlink_is_rejected(self) -> None:
        outside = self.root / "outside.txt"
        outside.write_text("outside\n", encoding="utf-8")
        (self.source / "linked.txt").symlink_to(outside)
        with self.assertRaises(self.module.SyncError):
            self.module.sync_one(self.source, self.mirror, write=True)

    def test_plugin_source_layout_and_local_data_exclusions(self) -> None:
        source = self.root / "fixture-plugin"
        mirror = self.root / "plugins/fixture-plugin"
        skill = source / "skills/fixture-plugin"
        self.module.PLUGIN_PACKAGES.add(source.name)
        self.module.GENERATED_PATHS[source.name] = ("development", "skills/fixture-plugin/runtime", "skills/fixture-plugin/profile")
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text("---\nname: fixture-plugin\n---\n")
        manifest = source / ".claude-plugin/plugin.json"
        manifest.parent.mkdir()
        manifest.write_text('{"version":"1.26.1"}')
        for prefix in self.module.GENERATED_PATHS[source.name]:
            generated = source / prefix
            generated.parent.mkdir(parents=True, exist_ok=True)
            generated.write_text("must remain local")
        result = self.module.sync_one(source, mirror, write=True)
        self.assertTrue(result["current"])
        self.assertEqual({"skills/fixture-plugin/SKILL.md", ".claude-plugin/plugin.json"},
                         set(self.module.package_files(mirror)))
        for prefix in self.module.GENERATED_PATHS[source.name]:
            self.assertFalse((mirror / prefix).exists())
            self.assertTrue((source / prefix).is_file())



if __name__ == "__main__":
    unittest.main()
