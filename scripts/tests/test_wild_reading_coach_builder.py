import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


NAME = "wild-reading-coach-builder"
BUILDER = Path(__file__).resolve().parents[2] / "plugins" / NAME / "skills" / NAME


class ReadingCoachBuilderTests(unittest.TestCase):
    def test_publish_and_revisit_an_edition(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            source = workspace / "book.md"
            source.write_text("# Observation\nRecord the time of each sighting.\n", encoding="utf-8")
            refs = workspace / "reviewed"
            refs.mkdir()
            index = "[Observation](observation.md)\n"
            (refs / "INDEX.md").write_text(index, encoding="utf-8")
            (refs / "observation.md").write_bytes(source.read_bytes())

            parent = workspace / "coaches"
            target = parent / "observation-coach"
            probe = [
                sys.executable, "-X", "utf8", str(BUILDER / "scripts/make_coach.py"),
                "--source", str(source), "--title", "Observation", "--name", target.name,
                "--parent", str(parent),
            ]
            subprocess.run(probe, cwd=workspace, check=True, capture_output=True)
            self.assertFalse(parent.exists())
            publish = [*probe, "--references", str(refs)]
            subprocess.run(publish, cwd=workspace, check=True, capture_output=True)
            self.assertEqual(index, (target / "references/INDEX.md").read_text(encoding="utf-8"))
            self.assertEqual(source.read_bytes(), (target / "references/observation.md").read_bytes())
            self.assertIn((BUILDER / "assets/coaching.md").read_text(encoding="utf-8"),
                          (target / "SKILL.md").read_text(encoding="utf-8"))
            self.assertIn("$observation-coach", (target / "agents/openai.yaml").read_text(encoding="utf-8"))

            profile = target / "PROFILE.md"
            profile.write_bytes(b"Read section one.\n")
            subprocess.run(publish, cwd=workspace, check=True, capture_output=True)
            source.write_bytes(b"A revised edition.\n")
            result = subprocess.run(publish, cwd=workspace, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(b"another edition", result.stderr)
            self.assertEqual(b"Read section one.\n", profile.read_bytes())
