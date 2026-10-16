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
        self.source = self.root / "gptplease"
        self.mirror = self.root / "plugins" / "gptplease" / "skills" / "gptplease"
        self.source.mkdir()
        (self.source / "SKILL.md").write_text("---\nname: gptplease\n---\n", encoding="utf-8")
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

    def test_macpilot_builds_and_observation_evidence_are_not_distributed(self) -> None:
        source = self.root / "macpilot"
        mirror = self.root / "plugins/macpilot/skills/macpilot"
        source.mkdir()
        (source / "SKILL.md").write_text("---\nname: macpilot\n---\n")
        code = source / "tool/Sources/MacPilot/Main.swift"
        code.parent.mkdir(parents=True)
        code.write_text("import AppKit\n")
        for prefix in self.module.GENERATED_PATHS["macpilot"]:
            generated = source / prefix
            generated.mkdir(parents=True)
            (generated / "private-data").write_text("must remain local")
            (generated / "generated-link").symlink_to(code)
        result = self.module.sync_one(source, mirror, write=True)
        self.assertTrue(result["current"])
        self.assertEqual(
            {"SKILL.md", "tool/Sources/MacPilot/Main.swift"},
            set(self.module.package_files(mirror)),
        )
        self.assertEqual(code.read_bytes(), (mirror / code.relative_to(source)).read_bytes())
        for prefix in self.module.GENERATED_PATHS["macpilot"]:
            self.assertFalse((mirror / prefix).exists())
            self.assertTrue((source / prefix / "private-data").is_file())


if __name__ == "__main__":
    unittest.main()
