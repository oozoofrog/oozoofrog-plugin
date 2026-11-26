"""Distribution and suggestion-script checks for the korean-tech-writing Plugin."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from test_document_links import local_targets

REPO_ROOT = Path(__file__).resolve().parents[2]
PLUGIN = REPO_ROOT / "plugins/korean-tech-writing"
SCRIPT = PLUGIN / "skills/pr-suggest/scripts/suggest.py"
T3_ARGS = {"gh": (), "t3": ("--repository", "o/r", "--number", "7")}


def read_metadata(path: Path) -> dict[str, str]:
    metadata = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("  ") and ": " in line:
            key, value = line.strip().split(": ", 1)
            metadata[key] = json.loads(value)
    return metadata


class DistributionTests(unittest.TestCase):
    def test_manifests_metadata_and_links(self) -> None:
        source = PLUGIN / "skills/korean-tech-writing"
        manifest = json.loads((PLUGIN / ".codex-plugin/plugin.json").read_text(encoding="utf-8"))
        claude = json.loads((PLUGIN / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))
        description = (source / "SKILL.md").read_text(encoding="utf-8").split("description: ", 1)[1].splitlines()[0]
        self.assertTrue(manifest["description"].startswith(description))
        self.assertIn("pr-suggest", manifest["description"])
        self.assertEqual(manifest["description"], claude["description"])
        self.assertEqual(manifest["description"], manifest["interface"]["longDescription"])
        self.assertIn(manifest["description"], (REPO_ROOT / "README.md").read_text(encoding="utf-8"))
        self.assertEqual("./skills/", manifest["skills"])
        for key in ("mcpServers", "apps", "hooks"):
            self.assertNotIn(key, manifest)
        metadata = read_metadata(source / "agents/openai.yaml")
        self.assertEqual(metadata["display_name"], manifest["interface"]["displayName"])
        self.assertEqual(metadata["short_description"], manifest["interface"]["shortDescription"])
        suggest = read_metadata(PLUGIN / "skills/pr-suggest/agents/openai.yaml")
        self.assertEqual([metadata["default_prompt"], suggest["default_prompt"]], manifest["interface"]["defaultPrompt"])
        self.assertIn("$korean-tech-writing", metadata["default_prompt"])
        self.assertIn("$pr-suggest", suggest["default_prompt"])
        for path in PLUGIN.rglob("*"):
            self.assertFalse(path.is_symlink(), path)
        for document in PLUGIN.rglob("*.md"):
            text = document.read_text(encoding="utf-8")
            self.assertNotIn("/Users/", text, document)
            for target in local_targets(text):
                self.assertTrue((document.parent / target).is_file(), (document, target))
        mode = subprocess.run(["git", "ls-files", "-s", str(SCRIPT.relative_to(REPO_ROOT))], cwd=REPO_ROOT,
                              capture_output=True, text=True).stdout.split(" ", 1)[0]
        if mode:
            self.assertEqual("100755", mode)


class SuggestScriptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.git("init", "-q")
        (self.repo / "README").write_text("readme\n")
        self.commit("base")
        self.base = self.git("rev-parse", "HEAD").strip()
        (self.repo / "src").mkdir()
        (self.repo / "src/a.txt").write_text("".join(f"line{i}\n" for i in range(1, 21)))
        (self.repo / "b.md").write_text("title\nbody\n")
        self.commit("head")
        self.head = self.git("rev-parse", "HEAD").strip()
        self.proposed = self.root / "proposed"
        (self.proposed / "src").mkdir(parents=True)
        (self.root / "body.md").write_text("본문\n")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def commit(self, message: str) -> None:
        self.git("add", ".")
        self.git("-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-qm", message)

    def git(self, *args: str) -> str:
        return subprocess.run(["git", "-C", str(self.repo), *args], check=True, capture_output=True, text=True).stdout

    def run_script(self, *extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, "-I", str(SCRIPT), "--repo", str(self.repo), "--base", self.base, "--head", self.head,
                               "--proposed", str(self.proposed), "--body", str(self.root / "body.md"), *extra],
                              capture_output=True, text=True)

    def apply(self, base: list[str], comments: list[dict], start_key: str, side: str) -> list[str]:
        result = list(base)
        for comment in sorted(comments, key=lambda c: c["line"], reverse=True):
            self.assertEqual(side, comment["side"])
            start = comment.get(start_key, comment["line"])
            rows = comment["body"].split("\n")
            opening = next(i for i, row in enumerate(rows) if row.endswith("suggestion"))
            lines = rows[opening + 1:-1]
            result[start - 1:comment["line"]] = lines
        return result

    def test_suggestions_reproduce_the_edit(self) -> None:
        base = [f"line{i}" for i in range(1, 21)]
        new = ["inserted at top"] + base[:3] + ["CHANGED4"] + base[4:9] + base[10:] + ["appended"]
        (self.proposed / "src/a.txt").write_text("\n".join(new) + "\n")
        for fmt, start_key, side in (("gh", "start_line", "RIGHT"), ("t3", "startLine", "new")):
            with self.subTest(fmt=fmt):
                result = self.run_script("--format", fmt, *T3_ARGS[fmt])
                self.assertEqual(0, result.returncode, result.stderr)
                review = json.loads(result.stdout)
                self.assertEqual(new, self.apply(base, review["comments"], start_key, side))
                self.assertIn("1 files", result.stderr)
        gh = json.loads(self.run_script("--format", "gh").stdout)
        self.assertEqual(("COMMENT", self.head, "본문"), (gh["event"], gh["commit_id"], gh["body"]))
        t3 = json.loads(self.run_script("--format", "t3", *T3_ARGS["t3"]).stdout)
        self.assertEqual(("o/r", 7, "comment", self.head),
                         (t3["repository"], t3["number"], t3["verdict"], t3["expectedHeadSha"]))
        self.assertNotEqual(0, self.run_script("--format", "t3").returncode)

    def test_notes_and_fence(self) -> None:
        (self.proposed / "b.md").write_text("title\n```code```\n")
        (self.root / "notes.json").write_text(json.dumps({"b.md:2-2": "이유 한 문장."}))
        result = self.run_script("--notes", str(self.root / "notes.json"))
        self.assertEqual(0, result.returncode, result.stderr)
        body = json.loads(result.stdout)["comments"][0]["body"]
        self.assertTrue(body.startswith("이유 한 문장.\n\n````suggestion\n```code```\n````"), body)

    def test_rejects_what_a_suggestion_cannot_express(self) -> None:
        cases = {
            "new file": ("new.txt", "x\n"),
            "final newline": ("b.md", "title\nbody"),
            "no change": ("b.md", "title\nbody\n"),
        }
        for name, (path, text) in cases.items():
            with self.subTest(name):
                for old in self.proposed.rglob("*"):
                    if old.is_file():
                        old.unlink()
                (self.proposed / path).write_text(text)
                self.assertNotEqual(0, self.run_script().returncode)
        (self.proposed / "b.md").write_text("title\nBODY\n")
        (self.root / "notes.json").write_text(json.dumps({"b.md:9-9": "x"}))
        self.assertNotEqual(0, self.run_script("--notes", str(self.root / "notes.json")).returncode)

    def test_github_line_model(self) -> None:
        (self.repo / "c.txt").write_text("l1\n\x0cl2\nl3\nl4\n")
        self.commit("form feed")
        self.head = self.git("rev-parse", "HEAD").strip()
        (self.proposed / "c.txt").write_text("l1\n\x0cl2\nl3\nX\n")
        result = self.run_script()
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(4, json.loads(result.stdout)["comments"][0]["line"])
        (self.proposed / "c.txt").unlink()
        (self.proposed / "b.md").write_bytes(b"title\r\nbody\r\n")
        self.assertNotEqual(0, self.run_script().returncode)

    def test_rejects_overlap_and_lines_outside_the_pr_diff(self) -> None:
        (self.proposed / "b.md").write_text("I0\ntitle\nI1\nbody\n")
        self.assertNotEqual(0, self.run_script("--gap", "0").returncode)
        self.assertEqual(0, self.run_script("--gap", "1").returncode)
        (self.proposed / "b.md").unlink()
        (self.repo / "src/a.txt").write_text("".join(f"line{i}\n" for i in range(1, 21)).replace("line2\n", "LINE2\n"))
        self.commit("later")
        self.base, self.head = self.head, self.git("rev-parse", "HEAD").strip()
        lines = [f"line{i}" for i in range(1, 21)]
        lines[1] = "LINE2"
        lines[3] = "inside"
        (self.proposed / "src/a.txt").write_text("\n".join(lines) + "\n")
        self.assertEqual(0, self.run_script().returncode)
        lines[17] = "outside"
        (self.proposed / "src/a.txt").write_text("\n".join(lines) + "\n")
        result = self.run_script()
        self.assertNotEqual(0, result.returncode)
        self.assertIn("src/a.txt:18-18", result.stderr)

    def test_hunks_follow_renames_and_ignore_user_diff_settings(self) -> None:
        lines = [f"row{i}" for i in range(1, 31)]
        (self.repo / "old.txt").write_text("\n".join(lines) + "\n")
        self.commit("add old")
        self.base = self.git("rev-parse", "HEAD").strip()
        self.git("mv", "old.txt", "new.txt")
        lines[4], lines[19] = "ROW5", "ROW20"
        (self.repo / "new.txt").write_text("\n".join(lines) + "\n")
        self.git("config", "diff.interHunkContext", "10")
        self.commit("rename and edit")
        self.head = self.git("rev-parse", "HEAD").strip()
        for line, ok in ((3, True), (12, False), (22, True)):
            with self.subTest(line=line):
                edited = list(lines)
                edited[line - 1] = "suggested"
                (self.proposed / "new.txt").write_text("\n".join(edited) + "\n")
                self.assertEqual(ok, self.run_script().returncode == 0)


if __name__ == "__main__":
    unittest.main()
