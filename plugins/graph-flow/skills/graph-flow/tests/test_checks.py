"""Checks contract tests; every git tree and GF_HOME is temporary."""
import io
import json
import multiprocessing
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SCRIPTS = pathlib.Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))
from graphflow import checks, core, plan, state, store

from human_support import legacy_run

ACTOR = {"role": "leader", "node": None, "session": "checks-test"}
CMD = {"id": "unit", "type": "cmd", "run": "printf 'out\\n'; printf 'err\\n' >&2"}


def work(node_id="work", **updates):
    node = {"id": node_id, "kind": "work", "goal": "work", "lane": 1,
            "grade": "scoped", "owns": ["owned.txt", "owned/"],
            "checks": [dict(CMD), {"id": "bounds", "type": "scope"},
                       {"id": "ide", "type": "host", "tool": "IDE", "expect": "green"}]}
    node.update(updates)
    return node


def review():
    return {"id": "review", "kind": "review", "goal": "review", "lane": 1,
            "grade": "daily", "target": "work", "lens": "correctness", "owns": [],
            "checks": [{"id": "citations", "type": "cites"}]}


def race_start(run_dir, barrier, results):
    dirty = checks._dirty

    def snapshot(cwd):
        result = dirty(cwd)
        barrier.wait()
        return result

    try:
        with mock.patch.object(checks, "_dirty", snapshot):
            checks.start(run_dir, "work", None, ACTOR)
        results.put("started")
    except core.GFError as exc:
        results.put(exc.code)


class ChecksCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name).resolve()
        self.env = mock.patch.dict(os.environ, {"GF_HOME": str(self.root / "home")})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.git("init", "-q")
        self.git("config", "user.name", "Checks Test")
        self.git("config", "user.email", "test@example.invalid")
        for file in ("owned.txt", "other.txt", "deleted.txt", "owned/child.txt"):
            self.write(file, "first\nsecond\n")
        self.commit()
        self.run = legacy_run(self.repo, "checks", ACTOR)
        self.set_plan([work()])

    def git(self, *args):
        result = subprocess.run(["git", "-C", str(self.repo)] + list(args),
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return result.stdout.decode().strip()

    def write(self, file, text):
        path = self.repo / file
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def commit(self):
        self.git("add", "--all", "--", ":(exclude).graph-flow")
        self.git("commit", "-q", "-m", "fixture")
        return self.git("rev-parse", "HEAD")

    def set_plan(self, nodes, integration=None):
        self.plan, _ = plan.normalize({"schema_version": 1, "goal": "checks", "nodes": nodes,
                                       "integration_checks": integration or []})
        self.assertEqual(plan.validate(self.plan), [])
        with store.transaction(self.run) as tx:
            rev, sha = tx.write_plan(self.plan)
            tx.append("plan.set", {"revision": rev, "plan_sha256": sha,
                      "fingerprints": {n["id"]: state.fingerprint(n) for n in self.plan["nodes"]},
                      "constraints_applied": []}, ACTOR)

    def append(self, event_type, data):
        with store.transaction(self.run) as tx:
            return tx.append(event_type, data, ACTOR)

    def status(self, node="work"):
        return state.derive(store.read_plan(self.run), store.events(self.run))["nodes"][node]

    def start(self, node="work"):
        return checks.start(self.run, node, None, ACTOR)

    def submit(self, commit=None):
        return checks.submit(self.run, "work", commit, "branch", "notes", [], None, ACTOR)

    def scope(self, phase="loop"):
        return checks.run_scope(self.run, "work", phase, None, ACTOR)

    def error(self, code, func, *args):
        with self.assertRaises(core.GFError) as cm:
            func(*args)
        self.assertEqual(cm.exception.code, code)
        return cm.exception

    def run_cmd(self, check=CMD, phase="loop", node="work", cwd=None):
        return checks.run_cmd(self.run, node, check, phase, cwd, ACTOR)

    def results(self, event_type="check.result"):
        return [e for e in store.events(self.run) if e["type"] == event_type]


class StartTests(ChecksCase):
    def test_first_attempt_records_all_dirty_states(self):
        self.write("other.txt", "modified\n")
        self.write("new space\nfile.txt", "untracked\n")
        (self.repo / "deleted.txt").unlink()
        self.write(".graph-flow/ignored", "metadata")
        before = self.git("rev-parse", "HEAD")
        data = self.start()
        self.assertEqual(data["attempt"], 1)
        self.assertEqual(data["cwd"], str(self.repo))
        self.assertEqual(data["base"]["rev"], before)
        self.assertEqual(data["base"]["dirty"], {
            "other.txt": "644:" + self.git("hash-object", "--", "other.txt"),
            "new space\nfile.txt": "644:" + self.git("hash-object", "--", "new space\nfile.txt"),
            "deleted.txt": "deleted"})

    def test_start_while_running_refused(self):
        self.start()
        self.error("not_startable", self.start)
        self.assertEqual(len(self.results("node.start")), 1)

    def test_last_attempt_live_status_not_startable(self):
        for attempt in (1, 2):
            self.start()
            sub = self.submit()
            self.append("gate.verdict", {"node": "work", "attempt": attempt,
                        "submission": sub["id"], "verdict": "reject", "rule": "R1"})
        self.start()
        self.assertEqual((self.status()["status"], self.status()["attempts"]), ("running", 3))
        for status in ("running", "submitted", "passed"):
            if status == "submitted":
                sub = self.submit()
            elif status == "passed":
                self.append("gate.verdict", {"node": "work", "attempt": 3,
                            "submission": sub["id"], "verdict": "pass", "rule": "R7"})
            with self.subTest(status=status):
                before = store.events(self.run)
                self.error("not_startable", self.start)
                self.assertEqual(self.status()["status"], status)
                self.assertEqual(store.events(self.run), before)

    def test_start_with_untracked_nested_repository(self):
        self.write("nested/file.txt", "nested")
        self.git("init", "-q", "nested")
        data = self.start()
        self.assertEqual(data["base"]["dirty"], {"nested/": "dir"})
        self.assertEqual(self.status()["status"], "running")

    def test_start_with_directory_symlink(self):
        (self.repo / "directory-link").symlink_to("owned", target_is_directory=True)
        data = self.start()
        self.assertEqual(data["base"]["dirty"], {"directory-link": "link:owned"})

    def test_start_with_dangling_symlink(self):
        (self.repo / "dangling").symlink_to("missing")
        data = self.start()
        self.assertEqual(data["base"]["dirty"], {"dangling": "link:missing"})

    def test_unusual_file_state_is_unreadable(self):
        os.mkfifo(self.repo / "pipe")
        with mock.patch.object(checks, "_git", side_effect=core.GFError("git_error", "unreadable")):
            self.assertEqual(checks._file_state(self.repo, "pipe"), "unreadable")
            self.assertEqual(checks._file_state(self.repo, "owned.txt"), "unreadable")

    def test_four_concurrent_starts(self):
        context = multiprocessing.get_context("fork")
        barrier = context.Barrier(4, timeout=10)
        results = context.Queue()
        processes = [context.Process(target=race_start, args=(self.run, barrier, results))
                     for _ in range(4)]
        try:
            for process in processes:
                process.start()
            for process in processes:
                process.join(15)
                self.assertEqual(process.exitcode, 0)
            self.assertCountEqual([results.get(timeout=2) for _ in processes],
                                  ["started"] + ["not_startable"] * 3)
            self.assertEqual(len(self.results("node.start")), 1)
        finally:
            for process in processes:
                if process.is_alive():
                    process.terminate()
                    process.join()
            results.close()
            results.join_thread()

    def test_staged_dirty_with_working_copy_matching_head(self):
        self.write("other.txt", "staged change")
        self.git("add", "other.txt")
        self.write("other.txt", "first\nsecond\n")
        data = self.start()
        self.assertEqual(data["base"]["dirty"]["other.txt"],
                         "644:" + self.git("hash-object", "--", "other.txt"))

    def test_unsatisfied_needs(self):
        self.set_plan([work("producer"), work("consumer", owns=["consumer.txt"],
                       needs=[{"from": "producer", "artifact": "owned.txt"}])])
        self.error("needs_unsatisfied", self.start, "consumer")

    def test_shared_busy(self):
        self.set_plan([work(), work("second", owns=["second.txt"])])
        self.start()
        self.error("shared_busy", self.start, "second")

    def test_shared_busy_after_uncommitted_submission(self):
        self.set_plan([work(), work("second", owns=["second.txt"])])
        self.start()
        self.submit()
        self.error("shared_busy", self.start, "second")

    def test_attempts_exhausted_records_r2_once(self):
        self.set_plan([work(max_attempts=1)])
        self.start()
        sub = self.submit()
        self.append("gate.verdict", {"node": "work", "attempt": 1, "submission": sub["id"],
                                    "verdict": "reject", "rule": "R1", "rejection": None})
        exc = self.error("attempts_exhausted", self.start)
        self.assertEqual(exc.exit_code, core.EXIT_STATE)
        expected = {"node": "work", "attempt": 1, "submission": None, "verdict": "replan",
                    "rule": "R2", "rejection": None, "tested_head": None}
        self.assertEqual(self.results("gate.verdict")[-1]["data"], expected)
        self.assertEqual(self.status()["status"], "replan")
        count = len(store.events(self.run))
        self.error("attempts_exhausted", self.start)
        self.assertEqual(len(store.events(self.run)), count)

    def test_git_queries_outside_lock(self):
        original = checks._git

        def unlocked(*args):
            with store.locked(self.run / ".lock", timeout_s=0.05):
                pass
            return original(*args)

        with mock.patch.object(checks, "_git", unlocked):
            self.start()
            self.write("owned.txt", "changed")
            self.scope()
            self.submit()


class CmdTests(ChecksCase):
    def test_success_log_and_event_fields(self):
        self.start()
        with mock.patch("sys.stderr", new_callable=io.StringIO) as stderr:
            data = self.run_cmd()
        self.assertEqual(stderr.getvalue(), "")
        self.assertEqual(data["result"], "passed")
        self.assertEqual(data["exit_code"], 0)
        self.assertFalse(data["timed_out"])
        self.assertEqual((self.run / data["log"]).read_text(), "out\nerr\n")
        self.assertEqual(set(data), {"node", "check", "type", "grade", "result", "attempt",
                         "phase", "exit_code", "timed_out", "command", "cwd", "duration_ms", "log"})
        self.assertEqual((data["grade"], data["attempt"], data["phase"]), (1, 1, "loop"))
        self.assertEqual(self.results()[-1]["data"], data)
        self.assertGreaterEqual(data["duration_ms"], 0)
        again = self.run_cmd()
        self.assertNotEqual(again["log"], data["log"])

    def test_nonzero(self):
        check = dict(CMD, run="exit 7")
        self.set_plan([work(checks=[check])])
        self.start()
        data = self.run_cmd(check)
        self.assertEqual((data["result"], data["exit_code"]), ("failed", 7))

    def test_timeout_kills_process_group(self):
        check = dict(CMD, run="sleep 5; printf survived > escaped", timeout_s=1)
        self.set_plan([work(checks=[check])])
        self.start()
        data = self.run_cmd(check)
        self.assertEqual(data["result"], "failed")
        self.assertIsNone(data["exit_code"])
        self.assertTrue(data["timed_out"])
        self.assertLess(data["duration_ms"], 4000)
        self.assertFalse((self.repo / "escaped").exists())

    def test_check_cwd(self):
        check = dict(CMD, run="pwd; cat child.txt", cwd="owned")
        self.set_plan([work(checks=[check])])
        self.start()
        data = self.run_cmd(check, cwd=self.repo)
        self.assertEqual(data["cwd"], str(self.repo / "owned"))
        self.assertEqual((self.run / data["log"]).read_text(), str(self.repo / "owned") + "\nfirst\nsecond\n")

    def test_wrong_status(self):
        exc = self.error("wrong_status", self.run_cmd)
        self.assertEqual(exc.exit_code, core.EXIT_STATE)
        self.assertEqual(self.results(), [])

    def test_unplanned_command_refused(self):
        self.start()
        self.error("unknown_check", self.run_cmd, dict(CMD, run="exit 99"))
        self.assertEqual(self.results(), [])

    def test_run_level_attempt_zero(self):
        self.set_plan([work()], [CMD])
        data = self.run_cmd(node="_run", phase="gate")
        self.assertEqual((data["attempt"], data["node"]), (0, "_run"))

    def test_fixed_command_allowed(self):
        fixed = dict(CMD, id="fixed", run="true")
        (self.repo / ".graph-flow" / "checks.json").write_text(
            json.dumps({"checks": [fixed]}))
        data = self.run_cmd(fixed, node="_run", phase="gate")
        self.assertEqual(data["result"], "passed")

    def test_fixed_command_cwd_cannot_escape_tree(self):
        (self.repo / "escape").symlink_to(self.root, target_is_directory=True)
        marker = self.root / "executed"
        for cwd in ("../..", "/", "escape"):
            with self.subTest(cwd=cwd):
                fixed = dict(CMD, id="fixed", run="touch '%s'" % marker, cwd=cwd)
                (self.repo / ".graph-flow" / "checks.json").write_text(
                    json.dumps({"checks": [fixed]}))
                exc = self.error("bad_cwd", self.run_cmd, fixed, "gate", "_run")
                self.assertEqual(exc.exit_code, core.EXIT_USAGE)
                self.assertFalse(marker.exists())
                self.assertEqual(self.results(), [])
                self.assertEqual(list((self.run / "evidence").rglob("*.log")), [])

    def test_stale_result_after_restart(self):
        self.start()
        execute = checks._execute

        def restart(*args):
            result = execute(*args)
            self.append("node.reopen", {"node": "work", "reason": "restart during check"})
            self.start()
            return result

        with mock.patch.object(checks, "_execute", restart):
            exc = self.error("stale_result", self.run_cmd)
        self.assertEqual(exc.exit_code, core.EXIT_STATE)
        self.assertEqual(self.results(), [])

    def test_stale_result_after_plan_revision(self):
        self.start()
        execute = checks._execute

        def revise(*args):
            result = execute(*args)
            self.set_plan([work()])
            return result

        with mock.patch.object(checks, "_execute", revise):
            self.error("stale_result", self.run_cmd)
        self.assertEqual(self.results(), [])

    def test_gate_stale_result_after_submission_changes(self):
        self.start()
        self.submit()
        execute = checks._execute

        def resubmit(*args):
            result = execute(*args)
            self.append("node.submit", {"node": "work", "attempt": 1, "commit": None})
            return result

        with mock.patch.object(checks, "_execute", resubmit):
            self.error("stale_result", self.run_cmd, CMD, "gate")
        self.assertEqual(self.results(), [])


class ScopeTests(ChecksCase):
    def test_dirty_symlink_retargeted_to_identical_content_fails(self):
        link = self.repo / "unowned-link"
        link.symlink_to("owned.txt")
        self.start()
        link.unlink()
        link.symlink_to("other.txt")
        self.assertEqual(self.scope()["violations"], ["unowned-link"])

    def test_dirty_file_mode_changed_fails(self):
        self.write("other.txt", "dirty")
        (self.repo / "other.txt").chmod(0o644)
        self.start()
        (self.repo / "other.txt").chmod(0o755)
        self.assertEqual(self.scope()["violations"], ["other.txt"])

    def test_owned_changed_passes(self):
        self.start()
        self.write("owned.txt", "changed")
        result = self.scope()
        self.assertEqual(result["result"], "passed")
        self.assertEqual(result["check"], "bounds")
        self.assertEqual(result["violations"], [])

    def test_unowned_tracked_changed_fails(self):
        self.start()
        self.write("other.txt", "changed")
        self.assertEqual(self.scope()["violations"], ["other.txt"])

    def test_unowned_untracked_fails(self):
        self.start()
        self.write("new space\nfile.txt", "new")
        self.assertEqual(self.scope()["violations"], ["new space\nfile.txt"])

    def test_dirty_at_base_untouched_passes(self):
        self.write("other.txt", "dirty")
        self.start()
        self.assertEqual(self.scope()["result"], "passed")

    def test_dirty_at_base_changed_again_fails(self):
        self.write("other.txt", "dirty")
        self.start()
        self.write("other.txt", "different")
        self.assertEqual(self.scope()["violations"], ["other.txt"])

    def test_dirty_at_base_restored_to_head_fails(self):
        self.write("other.txt", "dirty")
        self.start()
        self.git("restore", "other.txt")
        self.assertEqual(self.scope()["violations"], ["other.txt"])

    def test_untracked_at_base_deleted_fails(self):
        self.write("new.txt", "new")
        self.start()
        (self.repo / "new.txt").unlink()
        self.assertEqual(self.scope()["violations"], ["new.txt"])

    def test_directory_ownership_trailing_slash(self):
        self.start()
        self.write("owned/child.txt", "changed")
        self.write("owned/deep/new.txt", "new")
        self.assertEqual(self.scope()["result"], "passed")
        self.write("owned-other.txt", "outside")
        self.assertEqual(self.scope()["violations"], ["owned-other.txt"])

    def test_metadata_ignored(self):
        self.start()
        self.write(".graph-flow/file", "metadata")
        self.assertEqual(self.scope()["result"], "passed")

    def test_committed_submission_ignores_later_tree_changes(self):
        self.start()
        self.write("owned.txt", "changed")
        commit = self.commit()
        self.submit(commit)
        self.write("other.txt", "later change")
        self.assertEqual(self.scope("gate")["result"], "passed")

    def test_rename_unowned_to_owned_fails(self):
        self.start()
        self.git("mv", "other.txt", "owned/moved.txt")
        commit = self.commit()
        self.submit(commit)
        self.assertEqual(self.scope("gate")["violations"], ["other.txt"])

    def test_scope_default_check_id(self):
        self.set_plan([work(checks=[CMD])])
        self.start()
        self.assertEqual(self.scope()["check"], "scope")

    def test_deleted_at_base_restored_fails(self):
        (self.repo / "deleted.txt").unlink()
        self.start()
        self.assertEqual(self.scope()["result"], "passed")
        self.git("restore", "deleted.txt")
        self.assertEqual(self.scope()["violations"], ["deleted.txt"])

    def test_stale_scope_not_recorded(self):
        self.start()
        changed = checks._changed

        def reopen(*args):
            result = changed(*args)
            self.append("node.reopen", {"node": "work", "reason": "changed"})
            return result

        with mock.patch.object(checks, "_changed", reopen):
            self.error("stale_result", self.scope)
        self.assertEqual(self.results(), [])


class CitesTests(ChecksCase):
    def prepare(self, findings):
        self.set_plan([work(), review()])
        self.start()
        self.submit()
        self.start("review")
        checks.review_submit(self.run, "review", "pass", findings, ACTOR)

    def cites(self):
        return checks.run_cites(self.run, "review", "gate", None, ACTOR)

    def test_missing_file(self):
        self.prepare([{"file": "missing.txt", "line": 1}])
        self.assertEqual(self.cites()["result"], "failed")

    def test_citations_confined_to_project_files(self):
        outside = self.root / "outside.txt"
        outside.write_text("outside\n")
        (self.repo / "outside-link").symlink_to(outside)
        (self.repo / "metadata-link").symlink_to(".git/HEAD")
        self.write(".graph-flow/metadata.txt", "metadata\n")
        self.prepare([{"file": file, "line": 1} for file in (
            str(self.repo / "owned.txt"), "../outside.txt", "owned/../owned.txt",
            ".git/HEAD", ".graph-flow/metadata.txt", "outside-link", "metadata-link",
            "owned", "owned/child.txt")])
        data = self.cites()
        self.assertEqual(data["result"], "failed")
        self.assertEqual([v["finding"] for v in data["violations"]], list(range(1, 9)))

    def test_line_out_of_range(self):
        self.prepare([{"file": "owned.txt", "line": 3}])
        self.assertEqual(self.cites()["result"], "failed")

    def test_missing_line(self):
        self.prepare([{"file": "owned.txt"}])
        self.assertEqual(self.cites()["result"], "failed")

    def test_invalid_lines(self):
        self.prepare([{"file": "owned.txt", "line": line} for line in (0, -1, True, "1", 1.0)])
        self.assertEqual(len(self.cites()["violations"]), 5)

    def test_missing_file_field(self):
        self.prepare([{"line": 1}])
        self.assertEqual(self.cites()["result"], "failed")

    def test_valid_findings(self):
        self.prepare([{"file": "owned.txt", "line": 2, "severity": "high", "text": "reason"}])
        data = self.cites()
        self.assertEqual(data["result"], "passed")
        self.assertEqual(data["check"], "citations")
        self.assertEqual(data["grade"], 1)
        self.assertEqual(self.results()[-1]["data"], data)

    def test_zero_findings(self):
        self.prepare([])
        self.assertEqual(self.cites()["result"], "passed")


class HostRedSubmitTests(ChecksCase):
    def test_host_result(self):
        self.start()
        data = checks.record_host(self.run, "work", "ide", "passed", "green", ACTOR)
        self.assertEqual((data["type"], data["grade"], data["phase"], data["note"]),
                         ("host", 2, "loop", "green"))
        self.assertIsNone(data["exit_code"])
        self.assertEqual(self.results()[-1]["data"], data)

    def test_host_wrong_status(self):
        self.error("wrong_status", checks.record_host, self.run, "work", "ide", "passed", "", ACTOR)

    def test_host_wrong_check(self):
        self.start()
        self.error("unknown_check", checks.record_host, self.run, "work", "missing", "passed", "", ACTOR)
        self.error("wrong_check_type", checks.record_host, self.run, "work", "unit", "passed", "", ACTOR)
        self.error("bad_result", checks.record_host, self.run, "work", "ide", "yes", "", ACTOR)
        self.assertEqual(self.results(), [])

    def test_red_records_failures_and_green_notice(self):
        failing = dict(CMD, id="fail", run="exit 1")
        self.set_plan([work(checks=[CMD, failing])])
        self.start()
        data = checks.red(self.run, "work", None, None, ACTOR)
        self.assertEqual([r["failed_first"] for r in data["results"]], [False, True])
        self.assertEqual(data["notices"][0]["code"], "red_already_green")
        self.assertEqual(data["notices"][0]["node"], "work")
        self.assertEqual([e["data"] for e in self.results("check.red")], data["results"])
        self.assertEqual(self.results(), [])
        for result in data["results"]:
            self.assertTrue((self.run / result["log"]).is_file())

    def test_red_selected_check(self):
        self.start()
        data = checks.red(self.run, "work", "unit", None, ACTOR)
        self.assertEqual(len(data["results"]), 1)
        self.assertEqual(data["results"][0]["check"], "unit")

    def test_red_wrong_status(self):
        self.error("wrong_status", checks.red, self.run, "work", None, None, ACTOR)

    def test_submit_uncommitted(self):
        self.write("other.txt", "base dirty")
        self.start()
        self.write("owned.txt", "work")
        data = self.submit()
        self.assertEqual(data["changed_files"], ["owned.txt"])
        self.assertIsNone(data["commit"])
        self.assertEqual((data["branch"], data["notes"], data["low_confidence"]), ("branch", "notes", []))
        event = self.results("node.submit")[-1]
        self.assertEqual(data["id"], event["seq"])
        self.assertNotIn("id", event["data"])
        self.assertEqual(self.status()["status"], "submitted")

    def test_submit_validates_presentation_types_before_writing(self):
        self.start()
        for notes in (5, {}, [], False):
            with self.subTest(notes=notes):
                exc = self.error("bad_notes", checks.submit, self.run, "work", None, None,
                                 notes, [], None, ACTOR)
                self.assertEqual(exc.exit_code, core.EXIT_USAGE)
        for low_confidence in (5, {}, "legacy string", None, ["text", 7], [None]):
            with self.subTest(low_confidence=low_confidence):
                exc = self.error("bad_low_confidence", checks.submit, self.run, "work", None, None,
                                 None, low_confidence, None, ACTOR)
                self.assertEqual(exc.exit_code, core.EXIT_USAGE)
        self.assertEqual(self.results("node.submit"), [])
        self.assertEqual(self.status()["status"], "running")
        data = checks.submit(self.run, "work", None, None, None, ["Needs another look"], None, ACTOR)
        self.assertIsNone(data["notes"])
        self.assertEqual(data["low_confidence"], ["Needs another look"])

    def test_submit_committed_resolves_full_sha(self):
        self.start()
        self.write("owned.txt", "committed work")
        commit = self.commit()
        self.write("other.txt", "later")
        data = self.submit(commit[:10])
        self.assertEqual(data["commit"], commit)
        self.assertEqual(data["changed_files"], ["owned.txt"])

    def retry(self):
        sub = self.submit()
        self.append("gate.verdict", {"node": "work", "attempt": 1,
                    "submission": sub["id"], "verdict": "reject", "rule": "R1"})
        self.start()

    def test_retry_keeps_first_attempt_files(self):
        self.start()
        self.write("owned.txt", "work")
        self.retry()
        self.assertEqual(self.submit()["changed_files"], ["owned.txt"])

    def test_retry_revert_drops_file(self):
        self.start()
        self.write("owned.txt", "work")
        self.retry()
        self.git("restore", "owned.txt")
        self.assertEqual(self.submit()["changed_files"], [])

    def test_retry_scope_detects_new_outside_edit(self):
        self.start()
        self.write("owned.txt", "work")
        self.retry()
        self.write("other.txt", "stray")
        self.assertEqual(self.scope()["violations"], ["other.txt"])

    def test_retry_committed_submission(self):
        self.start()
        self.write("owned.txt", "work")
        commit = self.commit()
        sub = self.submit(commit)
        self.append("gate.verdict", {"node": "work", "attempt": 1,
                    "submission": sub["id"], "verdict": "reject", "rule": "R1"})
        self.start()
        self.assertEqual(self.submit(commit)["changed_files"], ["owned.txt"])

    def test_json_gate_subprocess_is_silent(self):
        self.set_plan([work(checks=[CMD])])
        self.start()
        self.write("owned.txt", "work")
        self.submit()
        result = subprocess.run([sys.executable, "-I", "-S", "-B", str(SCRIPTS / "gf"),
                                 "--json", "--run", str(self.run), "gate", "work"],
                                cwd=self.repo, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(json.loads(result.stdout)["verdict"], "pass")
        self.assertEqual(result.stderr, "")

    def test_submit_bad_sha(self):
        self.start()
        self.error("bad_commit", self.submit, "does-not-resolve")
        self.assertEqual(self.results("node.submit"), [])
        self.assertEqual(self.status()["status"], "running")

    def test_submit_commit_must_descend_from_base(self):
        self.write("owned.txt", "second commit")
        self.commit()
        self.start()
        exc = self.error("bad_commit", self.submit, "HEAD~1")
        self.assertEqual(exc.exit_code, core.EXIT_USAGE)
        self.assertEqual(self.results("node.submit"), [])
        self.assertEqual(self.status()["status"], "running")

    def test_submit_wrong_status(self):
        self.error("wrong_status", self.submit)

    def test_review_submit_target_id(self):
        self.set_plan([work(), review()])
        self.start()
        target = self.submit()
        self.start("review")
        findings = [{"severity": "high", "file": "owned.txt", "line": 1, "text": "The result loses data.",
                     "evidence": {"command": "reader", "exit_code": 1}}]
        data = checks.review_submit(self.run, "review", "fail", findings, ACTOR)
        self.assertEqual((data["target"], data["target_submission"]), ("work", target["id"]))
        self.assertEqual(data["findings"], findings)
        self.assertEqual(data["id"], self.results("review.submit")[-1]["seq"])

    def test_review_submit_target_without_submission_refused(self):
        self.set_plan([work(), review()])
        # Simulate an invalid/outdated reviewer start to exercise the submit guard.
        self.append("node.start", {"node": "review", "attempt": 1, "base": {"rev": "x", "dirty": {}}})
        self.error("wrong_status", checks.review_submit, self.run, "review", "pass", [], ACTOR)
        self.assertEqual(self.results("review.submit"), [])

    def test_review_submit_wrong_status_and_verdict(self):
        self.set_plan([work(), review()])
        self.error("wrong_status", checks.review_submit, self.run, "review", "pass", [], ACTOR)
        self.start()
        self.submit()
        self.start("review")
        self.error("bad_verdict", checks.review_submit, self.run, "review", "maybe", [], ACTOR)
        for bad in ("text", ["bare text"], [{"text": "ok"}, None]):
            self.error("bad_findings", checks.review_submit, self.run, "review", "fail", bad, ACTOR)


if __name__ == "__main__":
    unittest.main()
