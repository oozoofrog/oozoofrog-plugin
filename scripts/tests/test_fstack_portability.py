import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from test_document_links import local_targets

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "plugins/fstack"
SKILLS = PACKAGE / "skills"


class PortableWorkflows(unittest.TestCase):
    def test_packages_and_local_routes(self):
        sources = list(SKILLS.glob("*/SKILL.md"))
        self.assertEqual(len(sources), 60)
        self.assertEqual(len(list(SKILLS.glob("principle-*/SKILL.md"))), 24)
        self.assertEqual(len(list((SKILLS / "poteto-mode/playbooks").glob("*.md"))), 22)
        self.assertEqual(len(list((PACKAGE / "agents").glob("*.md"))), 2)
        for source in sources:
            self.assertIn("name: " + source.parent.name + "\n", source.read_text())
        for path in [PACKAGE / "README.md", *SKILLS.rglob("*.md"), *(PACKAGE / "automations").rglob("*.md")]:
            for target in local_targets(path.read_text()):
                with self.subTest(path=path, target=target):
                    self.assertTrue((path.parent / target).exists())
        catalog = json.loads((ROOT / ".cursor-plugin/marketplace.json").read_text())
        entry = next(x for x in catalog["plugins"] if x["name"] == "fstack")
        self.assertEqual(ROOT / entry["source"], PACKAGE)
        for host in ("claude", "codex", "cursor"):
            manifest = json.loads((PACKAGE / f".{host}-plugin/plugin.json").read_text())
            self.assertEqual(manifest["version"], "1.0.0")
            self.assertIn(manifest["description"], (SKILLS / "fstack/SKILL.md").read_text())

    def test_settings_import_round_trip_and_profile_isolation(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            env = dict(os.environ, HOME=d, USERPROFILE=d, XDG_CONFIG_HOME=str(root / "config"))
            env.pop("FSTACK_MODELS", None)
            rule = root / ".cursor/rules/pstack-models.mdc"
            rule.parent.mkdir(parents=True)
            original = "# budget: medium (high)\narena runners: first high, inherit-parent\n"
            rule.write_text(original)
            def models(host, *args, data=None, check=True):
                return subprocess.run([sys.executable, str(SKILLS / "setup-pstack/scripts/models.py"),
                                       "--host", host, *args], env=env, input=data,
                                      capture_output=True, text=True, check=check)
            previous = models("cursor", "show").stdout
            self.assertEqual(json.loads(previous)["roles"]["arena runners"], ["first high", "inherit-parent"])
            for _ in range(2):
                models("cursor", "save", data=previous)
            self.assertEqual(json.loads(models("cursor", "role", "arena runners").stdout)["budget"], "medium")
            self.assertEqual(models("cursor", "show").stdout, previous)
            self.assertNotEqual(models("cursor", "save", data='{"budget":"oops"}', check=False).returncode, 0)
            self.assertEqual(models("cursor", "show").stdout, previous)
            self.assertEqual(rule.read_text(), original)
            self.assertEqual(json.loads(models("other", "role", "swarm workers").stdout)["choices"], ["inherit-parent"])

    def test_worktree_activity_and_reused_branch(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            repo = root / "source repo"
            wt = root / "test tree"
            def git(where, *args):
                subprocess.run(["git", "-C", str(where), "-c", "user.name=Fixture",
                                "-c", "user.email=test@example.invalid", "-c", "commit.gpgsign=false",
                                *args], check=True, capture_output=True)
            repo.mkdir()
            git(repo, "init", "-b", "main")
            git(repo, "commit", "--allow-empty", "-m", "base")
            git(repo, "worktree", "add", "-b", "again", str(wt))
            evidence = root / "activity.tsv"
            def audit(state=None, env=None):
                args = []
                if state:
                    evidence.write_text(f"{wt}\t{state}\n")
                    args = ["--activity", str(evidence)]
                r = subprocess.run([sys.executable, str(SKILLS / "poteto-mode/scripts/worktree_audit.py"),
                                    "-b", "main", *args, str(repo)], check=True, env=env, capture_output=True, text=True)
                return r.stdout.splitlines()[-1].split("\t")[-2]
            self.assertEqual(audit(), "review")
            self.assertEqual(audit("active"), "verify-recent-chat")
            self.assertEqual(audit("inactive"), "safe")
            git(repo, "worktree", "lock", str(wt))
            self.assertEqual(audit("inactive"), "hold-locked")
            git(repo, "worktree", "unlock", str(wt))
            git(wt, "commit", "--allow-empty", "-m", "new unpushed work")
            git(repo, "remote", "add", "origin", str(root / "unused remote"))
            if os.name == "posix":
                # A forge may return a historical merge that reused this branch name.
                for cli in ("origin", "gh"):
                    script = root / cli
                    payload = [{"number": 5, "status": "merged", "state": "MERGED",
                                "headRef": "again", "headRefName": "again"}]
                    script.write_text("#!/bin/sh\necho '" + json.dumps(payload) + "'\n")
                    script.chmod(0o755)
                env = dict(os.environ, PATH=str(root) + os.pathsep + os.environ["PATH"])
                self.assertEqual(audit("inactive", env), "review")
