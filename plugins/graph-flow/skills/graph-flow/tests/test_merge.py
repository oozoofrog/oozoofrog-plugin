"""Real-git merge tests; repositories and GF_HOME are always temporary."""
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SCRIPTS = pathlib.Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))
from graphflow import checks, core, merge, plan, state, store

from human_support import legacy_run

ACTOR = {"role": "leader", "node": None, "session": "merge-test"}


class MergeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name).resolve()
        environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        environment.update(GF_HOME=str(self.root / "home"), GIT_CONFIG_NOSYSTEM="1",
                           GIT_CONFIG_GLOBAL=os.devnull)
        self.env = mock.patch.dict(os.environ, environment, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.git("init", "-q", "--template=")
        self.git("symbolic-ref", "HEAD", "refs/heads/main")
        self.git("config", "user.name", "Merge Test")
        self.git("config", "user.email", "merge@example.invalid")
        self.write("alpha.txt", "base alpha\n")
        self.write("beta.txt", "base beta\n")
        self.base = self.commit()
        self.run = legacy_run(self.repo, "merge", ACTOR)
        self.set_plan()

    def git(self, *args):
        result = subprocess.run(["git", "-C", str(self.repo)] + list(args),
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return result.stdout.decode().strip()

    def write(self, file, text):
        (self.repo / file).write_text(text, encoding="utf-8")

    def commit(self):
        self.git("add", "--all", "--", ":(exclude).graph-flow")
        self.git("commit", "-q", "-m", "fixture")
        return self.git("rev-parse", "HEAD")

    def set_plan(self, alpha_file="alpha.txt"):
        nodes = [{"id": nid, "kind": "work", "goal": "implement %s" % nid, "lane": 1,
                  "grade": "scoped", "owns": [file], "max_attempts": 3,
                  "checks": [{"id": "unit", "type": "cmd", "run": "true"}]}
                 for nid, file in (("alpha", alpha_file), ("beta", "beta.txt"))]
        normalized, _ = plan.normalize({"schema_version": 1, "goal": "merge", "nodes": nodes})
        self.assertEqual(plan.validate(normalized), [])
        with store.transaction(self.run) as tx:
            revision, sha = tx.write_plan(normalized)
            tx.append("plan.set", {"revision": revision, "plan_sha256": sha,
                      "fingerprints": {n["id"]: state.fingerprint(n) for n in normalized["nodes"]},
                      "constraints_applied": []}, ACTOR)

    def append(self, kind, data):
        with store.transaction(self.run) as tx:
            return tx.append(kind, data, ACTOR)

    def status(self, node):
        return state.derive(store.read_plan(self.run), store.events(self.run))["nodes"][node]

    def events(self, kind):
        return [e for e in store.events(self.run) if e["type"] == kind]

    def submission(self, node="alpha", file=None, attempt=1):
        file = file or "%s.txt" % node
        self.git("checkout", "-q", "-b", "work-%s" % node, self.base)
        for number in range(1, attempt + 1):
            checks.start(self.run, node, None, ACTOR)
            if number < attempt:
                self.append("gate.verdict", {"node": node, "attempt": number,
                            "submission": None, "verdict": "reject", "rule": "R1",
                            "rejection": None, "tested_head": None})
        self.write(file, "submitted %s\n" % node)
        commit = self.commit()
        result = checks.submit(self.run, node, commit, "work-%s" % node, "", [], None, ACTOR)
        self.git("checkout", "-q", "main")
        return result

    def integrate(self, *nodes):
        return merge.merge(self.run, nodes or ("alpha",), ACTOR)

    def error(self, code, *nodes):
        with self.assertRaises(core.GFError) as cm:
            self.integrate(*nodes)
        self.assertEqual((cm.exception.code, cm.exception.exit_code), (code, core.EXIT_STATE))
        return cm.exception

    def assert_ancestor(self, commit, head="HEAD"):
        self.git("merge-base", "--is-ancestor", commit, head)

    def assert_clean(self):
        self.assertEqual(self.git("diff", "HEAD", "--"), "")
        self.assertFalse((self.repo / ".git" / "MERGE_HEAD").exists())

    def conflict(self, attempt=1, file="alpha.txt"):
        if file != "alpha.txt":
            self.write(file, "base\n")
            self.base = self.commit()
            self.set_plan(alpha_file=file)
        sub = self.submission(file=file, attempt=attempt)
        self.write(file, "leader change\n")
        self.commit()
        return sub

    def test_two_branches_merge_in_given_order_and_record_heads(self):
        alpha, beta = self.submission(), self.submission("beta")
        data = self.integrate("beta", "alpha")
        self.assertEqual(data["conflicted"], [])
        self.assertEqual([entry["node"] for entry in data["merged"]], ["beta", "alpha"])
        first, second = data["merged"]
        self.assertEqual([first["commit"], second["commit"]], [beta["commit"], alpha["commit"]])
        self.assertEqual(self.git("rev-parse", first["head"] + "^1"), self.base)
        self.assertEqual(self.git("rev-parse", second["head"] + "^1"), first["head"])
        self.assertEqual(second["head"], self.git("rev-parse", "HEAD"))
        for entry in data["merged"]:
            self.assert_ancestor(entry["commit"])
            self.assertEqual(self.git("show", "-s", "--format=%s", entry["head"]),
                             "gf: merge %s" % entry["node"])
            self.assertEqual(self.status(entry["node"])["merged_head"], entry["head"])
        self.assertEqual(self.events("merge.result")[0]["data"], data)
        self.assertEqual(len(self.events("merge.result")), 1)
        self.assertEqual(self.events("gate.verdict"), [])
        self.assertEqual(self.git("branch", "--show-current"), "main")

    def test_already_merged_records_current_head_without_git_merge(self):
        sub = self.submission()
        self.integrate()
        before = self.git("rev-parse", "HEAD")
        original = merge._git
        with mock.patch.object(merge, "_git", wraps=original) as git:
            data = self.integrate()
        self.assertFalse(any("merge" in call.args[1:] for call in git.call_args_list))
        self.assertEqual(data, {"merged": [{"node": "alpha", "commit": sub["commit"],
                                         "head": before}], "conflicted": []})
        self.assertEqual(self.git("rev-parse", "HEAD"), before)

    def test_conflict_aborts_continues_and_rejects_only_conflicting_node(self):
        sub = self.conflict()
        beta = self.submission("beta")
        before = self.git("rev-parse", "HEAD")
        data = self.integrate("alpha", "beta")
        self.assertEqual(data["conflicted"], [{"node": "alpha", "commit": sub["commit"],
                                              "files": ["alpha.txt"]}])
        self.assertEqual(data["merged"][0]["commit"], beta["commit"])
        self.assert_ancestor(beta["commit"])
        self.assert_clean()
        rejection = {"unit": "alpha", "attempt": 1, "max_attempts": 3, "verdict": "red",
                     "reason": "merge conflict in alpha.txt",
                     "evidence": {"log": None, "tail": ["alpha.txt"]}, "scope": ["alpha.txt"]}
        self.assertEqual(self.status("alpha")["status"], "rejected")
        self.assertEqual(self.status("alpha")["rejections"], [rejection])
        self.assertEqual(self.status("beta")["status"], "submitted")
        self.assertEqual(self.status("beta")["rejections"], [])
        self.assertEqual(self.events("gate.verdict")[0]["data"], {
            "node": "alpha", "attempt": 1, "submission": sub["id"], "verdict": "reject",
            "rule": "M1", "rejection": rejection, "tested_head": before})
        self.assertEqual([e["type"] for e in store.events(self.run)[-2:]],
                         ["merge.result", "gate.verdict"])

    def test_conflict_at_attempt_limit_replans(self):
        self.conflict(attempt=3)
        self.integrate()
        st = self.status("alpha")
        self.assertEqual((st["status"], st["verdict"]["verdict"], st["verdict"]["rule"]),
                         ("replan", "replan", "M1"))
        self.assertEqual(st["rejections"][0]["attempt"], 3)
        self.assert_clean()

    def test_conflicting_paths_are_nul_delimited(self):
        file = "space and\nnewline.txt"
        self.conflict(file=file)
        data = self.integrate()
        self.assertEqual(data["conflicted"][0]["files"], [file])
        self.assertEqual(self.status("alpha")["rejections"][0]["evidence"]["tail"], [file])
        self.assert_clean()

    def test_dirty_tracked_worktree_appends_nothing(self):
        self.submission()
        self.write("beta.txt", "dirty\n")
        before = (self.run / "events.jsonl").read_bytes()
        head = self.git("rev-parse", "HEAD")
        self.error("dirty_tree")
        self.assertEqual((self.run / "events.jsonl").read_bytes(), before)
        self.assertEqual(self.git("rev-parse", "HEAD"), head)

    def test_staged_change_with_worktree_restored_is_dirty(self):
        self.submission()
        self.write("beta.txt", "staged\n")
        self.git("add", "beta.txt")
        self.write("beta.txt", "base beta\n")
        before = store.events(self.run)
        self.error("dirty_tree")
        self.assertEqual(store.events(self.run), before)

    def test_untracked_files_do_not_block(self):
        self.submission()
        self.write("untracked.txt", "keep\n")
        self.assertEqual(len(self.integrate()["merged"]), 1)
        self.assertEqual((self.repo / "untracked.txt").read_text(), "keep\n")

    def _untracked_collision(self, order):
        alpha = self.submission()
        self.git("checkout", "-q", "-b", "work-beta", self.base)
        checks.start(self.run, "beta", None, ACTOR)
        self.write("beta.txt", "submitted beta\n")
        self.write("new.txt", "submitted new file\n")
        commit = self.commit()
        beta = checks.submit(self.run, "beta", commit, "work-beta", "", [], None, ACTOR)
        self.git("checkout", "-q", "main")
        self.write("new.txt", "keep untracked file\n")
        original = merge._git
        errors = []

        def capture(*args, **kwargs):
            result = original(*args, **kwargs)
            if "merge" in args[1:] and result.returncode:
                errors.append(result.stderr.decode("utf-8", "replace").strip().splitlines()[0])
            return result

        with mock.patch.object(merge, "_git", capture):
            data = self.integrate(*order)
        self.assertEqual([entry["node"] for entry in data["merged"]], ["alpha"])
        self.assertEqual(len(data["conflicted"]), 1)
        conflict = data["conflicted"][0]
        self.assertEqual((conflict["node"], conflict["commit"], conflict["files"]),
                         ("beta", beta["commit"], []))
        self.assertEqual(conflict["reason"], errors[0])
        self.assert_ancestor(alpha["commit"])
        self.assertEqual((self.repo / "new.txt").read_text(), "keep untracked file\n")
        self.assertEqual(self.git("ls-files", "--", "new.txt"), "")
        self.assert_clean()
        self.assertEqual(len(self.events("merge.result")), 1)
        self.assertEqual(self.events("merge.result")[0]["data"], data)
        self.assertEqual(len(self.events("gate.verdict")), 1)
        verdict = self.events("gate.verdict")[0]["data"]
        self.assertEqual((verdict["node"], verdict["rule"], verdict["verdict"]),
                         ("beta", "M1", "reject"))
        self.assertEqual(verdict["rejection"]["reason"], "merge failed: " + errors[0])
        self.assertEqual(self.status("beta")["status"], "rejected")
        self.assertEqual(self.status("alpha")["status"], "submitted")

    def test_untracked_collision_records_earlier_merge_and_rejects(self):
        self._untracked_collision(("alpha", "beta"))

    def test_untracked_collision_continues_with_remaining_node(self):
        self._untracked_collision(("beta", "alpha"))

    def test_no_commit_and_unknown_node_preconditions_precede_git(self):
        self.submission()
        for code, nodes in (("unknown_node", ("alpha", "unknown")),
                            ("no_commit", ("alpha", "beta"))):
            with self.subTest(code=code):
                before = (self.run / "events.jsonl").read_bytes()
                with mock.patch.object(merge, "_git") as git:
                    self.error(code, *nodes)
                git.assert_not_called()
                self.assertEqual((self.run / "events.jsonl").read_bytes(), before)

    def test_uncommitted_submission_is_no_commit(self):
        checks.start(self.run, "alpha", None, ACTOR)
        checks.submit(self.run, "alpha", None, None, "", [], None, ACTOR)
        before = store.events(self.run)
        self.error("no_commit")
        self.assertEqual(store.events(self.run), before)

    def test_retained_rejected_submission_is_not_current(self):
        sub = self.submission()
        self.append("gate.verdict", {"node": "alpha", "attempt": 1, "submission": sub["id"],
                    "verdict": "reject", "rule": "R1", "rejection": None, "tested_head": None})
        before = store.events(self.run)
        self.error("no_commit")
        self.assertEqual(store.events(self.run), before)

    def test_existing_merge_is_not_aborted(self):
        sub = self.conflict()
        result = subprocess.run(["git", "-C", str(self.repo), "merge", "--no-ff", "--no-edit",
                                 sub["commit"]], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertNotEqual(result.returncode, 0)
        before = store.events(self.run)
        self.error("merge_in_progress")
        self.assertTrue((self.repo / ".git" / "MERGE_HEAD").exists())
        self.assertEqual(store.events(self.run), before)
        self.git("merge", "--abort")

    def test_all_git_runs_outside_run_lock(self):
        self.submission()
        original = merge._git

        def unlocked(*args, **kwargs):
            with store.locked(self.run / ".lock", timeout_s=0.05):
                pass
            return original(*args, **kwargs)

        with mock.patch.object(merge, "_git", unlocked):
            self.integrate()

    def test_restart_after_git_work_is_stale_and_keeps_git_merges(self):
        alpha, beta = self.submission(), self.submission("beta")

        def restart(run_dir):
            self.append("node.reopen", {"node": "beta", "reason": "restart during merge"})
            checks.start(run_dir, "beta", None, ACTOR)

        with mock.patch.object(merge, "_before_commit", restart):
            exc = self.error("stale_result", "alpha", "beta")
        self.assertIn("git merges already made remain", exc.message)
        self.assertEqual(self.events("merge.result"), [])
        self.assertEqual(self.events("gate.verdict"), [])
        self.assert_ancestor(alpha["commit"])
        self.assert_ancestor(beta["commit"])
        self.assert_clean()

    def test_new_submission_after_git_work_is_stale(self):
        sub = self.submission()

        def resubmit(run_dir):
            self.append("node.submit", {key: value for key, value in sub.items() if key != "id"})

        with mock.patch.object(merge, "_before_commit", resubmit):
            self.error("stale_result")
        self.assertEqual(self.events("merge.result"), [])

    def test_plan_revision_after_git_work_is_stale(self):
        self.submission()
        with mock.patch.object(merge, "_before_commit", lambda run_dir: self.set_plan()):
            self.error("stale_result")
        self.assertEqual(self.events("merge.result"), [])

    def test_stale_conflict_appends_no_merge_or_m1_verdict(self):
        self.conflict()
        with mock.patch.object(merge, "_before_commit", lambda run_dir: self.append(
                "node.reopen", {"node": "alpha", "reason": "restart"})):
            self.error("stale_result")
        self.assertEqual(self.events("merge.result"), [])
        self.assertEqual(self.events("gate.verdict"), [])
        self.assert_clean()

    def test_missing_identity_uses_fallback_without_changing_config(self):
        self.submission()
        self.git("config", "--unset", "user.name")
        self.git("config", "--unset", "user.email")
        before = self.git("config", "--local", "--list")
        self.integrate()
        self.assertEqual(self.git("show", "-s", "--format=%an <%ae>|%cn <%ce>", "HEAD"),
                         "gf <gf@localhost>|gf <gf@localhost>")
        self.assertEqual(self.git("config", "--local", "--list"), before)

    def test_configured_identity_is_preserved(self):
        self.submission()
        self.integrate()
        self.assertEqual(self.git("show", "-s", "--format=%an <%ae>|%cn <%ce>", "HEAD"),
                         "Merge Test <merge@example.invalid>|Merge Test <merge@example.invalid>")

    def test_non_conflict_git_failure_is_not_a_rejection(self):
        self.submission()
        self.git("update-ref", "-d", "refs/heads/work-alpha")
        self.append("node.submit", {"node": "alpha", "attempt": 1, "commit": "0" * 40})
        before = store.events(self.run)
        self.error("git_error")
        self.assertEqual(store.events(self.run), before)
        self.assert_clean()


if __name__ == "__main__":
    unittest.main()
