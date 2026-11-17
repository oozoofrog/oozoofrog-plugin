"""Learning-edge contract tests; repositories, runs and GF_HOME are temporary."""
import copy
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
from graphflow import assign, core, gate, learn, plan, state, store

from human_support import legacy_run, approve_current_plan, refresh_contract

ACTOR = {"role": "leader", "node": None, "session": "learn-test"}


def concurrent_add(root, run, barrier, results):
    try:
        barrier.wait(timeout=10)
        constraint = learn.add(root, run, "work", "Concurrent lesson", "When obsolete",
                               [], [], ACTOR)
        results.put(constraint["id"])
    except BaseException as exc:
        results.put("error: " + repr(exc))
        raise


class LearnTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name).resolve()
        env = mock.patch.dict(os.environ, {"GF_HOME": str(self.root / "home")})
        env.start()
        self.addCleanup(env.stop)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.git("init", "-q")
        self.git("config", "user.name", "Learn Test")
        self.git("config", "user.email", "test@example.invalid")
        self.git("commit", "-q", "--allow-empty", "-m", "fixture")
        self.run = legacy_run(self.repo, "learning", ACTOR)
        self.meta = self.repo / ".graph-flow"
        self.constraints_path = self.meta / "constraints.jsonl"
        self.checks_path = self.meta / "checks.json"
        self.set_plan()
        self.accept()

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.repo)] + list(args), check=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.decode().strip()

    def set_plan(self, owns=None, tags=None):
        self.plan, _ = plan.normalize({
            "schema_version": 1, "goal": "Learn from accepted work", "tags": tags or [],
            "nodes": [{"id": "work", "kind": "work", "goal": "Implement", "lane": 1,
                       "grade": "scoped", "owns": owns if owns is not None else ["src/"],
                       "checks": [{"id": "unit", "type": "cmd", "run": "true"}]}]})
        self.assertEqual(plan.validate(self.plan), [])
        with store.transaction(self.run) as tx:
            revision, sha = tx.write_plan(self.plan)
            tx.append("plan.set", {"revision": revision, "plan_sha256": sha,
                      "fingerprints": {n["id"]: state.fingerprint(n) for n in self.plan["nodes"]},
                      "constraints_applied": []}, ACTOR)

        approve_current_plan(self.run)
    def append(self, kind, data):
        with store.transaction(self.run) as tx:
            return tx.append(kind, data, ACTOR)

    def accept(self, evidence=True):
        with store.transaction(self.run) as tx:
            attempt = state.derive(tx.plan, tx.events)["nodes"]["work"]["attempts"] + 1
            tx.append("node.start", {"node": "work", "attempt": attempt,
                      "base": {"rev": self.git("rev-parse", "HEAD"), "dirty": {}},
                      "cwd": str(self.repo)}, ACTOR)
            submission = tx.append("node.submit", {"node": "work", "attempt": attempt,
                                   "commit": None, "branch": None, "changed_files": [],
                                   "notes": "", "low_confidence": []}, ACTOR)
            log = None
            if evidence:
                path = store.evidence_path(self.run, "work", "unit", attempt)
                path.write_text("accepted\n", encoding="utf-8")
                log = path.relative_to(self.run).as_posix()
                tx.append("check.result", {"node": "work", "check": "unit", "type": "cmd",
                          "grade": 1, "result": "passed", "attempt": attempt, "phase": "gate",
                          "exit_code": 0, "timed_out": False, "command": "true",
                          "cwd": str(self.repo), "duration_ms": 0, "log": log}, ACTOR)
            tx.append("gate.verdict", {"node": "work", "attempt": attempt,
                      "submission": submission["seq"], "verdict": "pass", "rule": "R7",
                      "rejection": None, "tested_head": self.git("rev-parse", "HEAD")}, ACTOR)
        return log

    def add(self, text="Keep the accepted invariant", review_when="When the format changes",
            paths=None, tags=None, node="work", run=None):
        return learn.add(self.repo, run if run is not None else self.run, node, text,
                         review_when, paths or [], tags or [], ACTOR)

    def error(self, code, exit_code, function, *args, **kwargs):
        with self.assertRaises(core.GFError) as caught:
            function(*args, **kwargs)
        self.assertEqual((caught.exception.code, caught.exception.exit_code), (code, exit_code))
        return caught.exception

    def events(self, kind):
        return [e for e in store.events(self.run) if e["type"] == kind]

    def raw_constraints(self):
        return [json.loads(line) for line in self.constraints_path.read_text().splitlines()]

    def raw_checks(self):
        return json.loads(self.checks_path.read_text())

    def test_missing_files_are_empty_and_reads_do_not_write(self):
        with mock.patch.object(store, "atomic_write") as write:
            self.assertEqual(learn.all_constraints(self.repo), [])
            self.assertEqual(learn.applying(self.repo, self.plan), [])
            self.assertEqual(learn.fixed_checks(self.repo), [])
        write.assert_not_called()
        self.assertFalse(self.constraints_path.exists())
        self.assertFalse(self.checks_path.exists())

    def test_add_shape_provenance_timestamp_and_event(self):
        paths, tags = ["src/config.py"], ["python"]
        with mock.patch.object(core, "now", return_value="2026-11-15T09:30:00Z"):
            c = self.add(text="Preserve ünicode", paths=paths, tags=tags)
        self.assertEqual(c, {
            "id": "c1", "text": "Preserve ünicode", "review_when": "When the format changes",
            "scope": {"paths": paths, "tags": tags}, "status": "active",
            "created": "2026-11-15T09:30:00Z",
            "derived_from": {"run": "learning", "node": "work", "attempt": 1,
                             "evidence": self.events("check.result")[-1]["data"]["log"]}})
        paths.append("other/")
        tags.append("other")
        self.assertEqual(c["scope"], {"paths": ["src/config.py"], "tags": ["python"]})
        self.assertEqual(self.raw_constraints(), [c])
        event = self.events("constraint.add")[-1]
        self.assertEqual(event["data"], {"id": "c1"})
        self.assertEqual(event["actor"], ACTOR)
        self.assertEqual(event["plan_revision"], 1)

    def test_requires_addressed_run(self):
        self.error("no_run", core.EXIT_STATE, learn.add, self.repo, None, "work", "T", "W",
                   [], [], ACTOR)
        self.error("no_run", core.EXIT_STATE, learn.add, self.repo, self.root / "missing",
                   "work", "T", "W", [], [], ACTOR)
        self.assertFalse(self.constraints_path.exists())

    def test_only_accepted_nodes_can_be_sources(self):
        for status, event in (("unknown", None), ("pending", "node.reopen"),
                              ("running", "node.start"), ("submitted", "node.submit"),
                              ("rejected", "gate.verdict")):
            with self.subTest(status=status):
                if event:
                    data = {"node": "work", "attempt": 1}
                    if event == "gate.verdict":
                        data.update(verdict="reject", submission=None)
                    self.append(event, data)
                self.error("not_accepted", core.EXIT_STATE, self.add,
                           node="missing" if status == "unknown" else "work")
        self.assertFalse(self.constraints_path.exists())
        self.assertEqual(self.events("constraint.add"), [])

    def test_text_and_review_when_validation(self):
        for value in ("", " \n", None, 7):
            with self.subTest(value=value):
                self.error("bad_text", 2, self.add, text=value)
                self.error("bad_review_when", 2, self.add, review_when=value)
        self.assertFalse(self.constraints_path.exists())

    def test_invalid_paths(self):
        for path in ("/src/x", "../x", "src/../x", ".git", ".git/HEAD", ".graph-flow",
                     ".graph-flow/checks.json", "./.git/HEAD", "", None, 42):
            with self.subTest(path=path):
                self.error("bad_path", 2, learn.add, self.repo, self.run, "work", "T", "W",
                           [path], [], ACTOR)
        self.error("bad_path", 2, learn.add, self.repo, self.run, "work", "T", "W", "src/", [], ACTOR)
        self.assertFalse(self.constraints_path.exists())

    def test_valid_relative_paths_and_optional_scope(self):
        paths = ["src/", "src/config.py", "space name/file", ".github/workflows/ci.yml", "src/.git/file"]
        self.assertEqual(self.add(paths=paths)["scope"]["paths"], paths)
        c = learn.add(self.repo, self.run, "work", "T", "W", None, None, ACTOR)
        self.assertEqual(c["scope"], {"paths": [], "tags": []})

    def test_evidence_is_current_attempt_gate_pass_or_null(self):
        self.accept(evidence=False)
        for check, phase, result, attempt in (("loop", "loop", "passed", 2),
                                               ("old", "gate", "passed", 1),
                                               ("failed", "gate", "failed", 2)):
            self.append("check.result", {"node": "work", "check": check, "phase": phase,
                        "result": result, "attempt": attempt, "log": "wrong.log"})
        c = self.add()
        self.assertEqual(c["derived_from"]["attempt"], 2)
        self.assertIsNone(c["derived_from"]["evidence"])
        log = self.accept()
        c = self.add()
        self.assertEqual(c["derived_from"]["attempt"], 3)
        self.assertEqual(c["derived_from"]["evidence"], log)

    def test_ids_use_highest_suffix_and_preserve_line_order(self):
        first = self.add()
        first["id"] = "c12"
        earlier = dict(first, id="c4", text="Earlier")
        with store.locked(self.meta / ".lock"):
            learn._write_constraints(self.meta, [first, earlier])
        last = self.add(text="Last")
        self.assertEqual(last["id"], "c13")
        self.assertEqual([c["id"] for c in learn.all_constraints(self.repo)], ["c12", "c4", "c13"])
        self.assertEqual(len(self.constraints_path.read_text().splitlines()), 3)

    def test_all_applicability_routes_and_negative_cases(self):
        global_c = self.add(text="Global")
        path_c = self.add(text="Path", paths=["src/config.py"])
        tag_c = self.add(text="Tag", tags=["python"])
        both_c = self.add(text="Either route", paths=["other/"], tags=["python"])
        self.add(text="Neither", paths=["docs/"], tags=["rust"])
        self.add(text="Prefix is not containment", paths=["src-other/"])
        candidate = copy.deepcopy(self.plan)
        candidate["tags"] = ["python"]
        before = copy.deepcopy(candidate)
        self.assertEqual(learn.applying(self.repo, candidate), [global_c, path_c, tag_c, both_c])
        self.assertEqual(candidate, before)
        candidate["tags"] = ["rust-unrelated"]
        self.assertEqual(learn.applying(self.repo, candidate), [global_c, path_c])
        candidate["nodes"][0]["owns"] = ["unrelated/"]
        self.assertEqual(learn.applying(self.repo, candidate), [global_c])

    def test_overlap_in_both_containment_directions_and_equal(self):
        for owns, scope in ((["src/"], ["src/config.py"]),
                            (["src/config.py"], ["src/"]),
                            (["src/config.py"], ["src/config.py"])):
            with self.subTest(owns=owns, scope=scope):
                c = self.add(paths=scope)
                candidate = copy.deepcopy(self.plan)
                candidate["nodes"][0]["owns"] = owns
                self.assertIn(c, learn.applying(self.repo, candidate))

    def test_paths_owned_by_any_node_apply(self):
        c = self.add(paths=["elsewhere/file"])
        candidate = copy.deepcopy(self.plan)
        candidate["nodes"].append(dict(candidate["nodes"][0], id="second", owns=["elsewhere/"]))
        self.assertEqual(learn.applying(self.repo, candidate), [c])

    def test_promote_still_applies_retired_never_applies(self):
        c = self.add(paths=["src/"], tags=["python"])
        promoted = learn.promote(self.repo, c["id"], "true", ACTOR)["constraint"]
        self.assertEqual(learn.applying(self.repo, self.plan), [promoted])
        retired = learn.retire(self.repo, c["id"], "Obsolete", ACTOR)["constraint"]
        self.assertEqual(learn.applying(self.repo, self.plan), [])
        self.assertEqual(learn.all_constraints(self.repo), [retired])

    def test_promote_shape_event_and_fixed_check_extra_fields(self):
        c = self.add()
        with mock.patch.object(core, "now", return_value="2026-11-15T10:00:00Z"):
            result = learn.promote(self.repo, c["id"], "true", ACTOR, self.run)
        check = {"id": "fx_c1", "type": "cmd", "run": "true", "from_constraint": "c1",
                 "added": "2026-11-15T10:00:00Z"}
        self.assertEqual(result, {"constraint": dict(c, status="promoted"), "check": check})
        self.assertEqual(self.raw_checks(), {"schema_version": 1, "checks": [check]})
        self.assertEqual(self.raw_constraints(), [result["constraint"]])
        self.assertEqual(self.events("constraint.promote")[-1]["data"], {"id": "c1"})
        document = self.raw_checks()
        document["checks"][0].update(timeout_s=12, cwd="src", custom={"keep": True})
        with store.locked(self.meta / ".lock"):
            learn._write_checks(self.meta, document)
        self.assertEqual(learn.fixed_checks(self.repo), document["checks"])

    def test_promote_validation_and_status(self):
        c = self.add()
        for command in ("", " \n", None, 3):
            self.error("bad_command", 2, learn.promote, self.repo, c["id"], command, ACTOR)
        self.error("unknown_constraint", 4, learn.promote, self.repo, "c404", "true", ACTOR)
        learn.promote(self.repo, c["id"], "true", ACTOR)
        self.error("wrong_status", 4, learn.promote, self.repo, c["id"], "false", ACTOR)
        learn.retire(self.repo, c["id"], "Done", ACTOR)
        self.error("wrong_status", 4, learn.promote, self.repo, c["id"], "true", ACTOR)
        self.assertEqual(self.events("constraint.promote"), [])

    def test_retire_active_and_promoted_preserves_all_lines_and_other_checks(self):
        first, second = self.add(), self.add(text="Second")
        learn.promote(self.repo, second["id"], "true", ACTOR)
        first_retired = learn.retire(self.repo, first["id"], "No longer needed", ACTOR, self.run)
        self.assertEqual(first_retired, {"constraint": dict(first, status="retired", retired_reason="No longer needed")})
        self.assertEqual([c["id"] for c in learn.fixed_checks(self.repo)], ["fx_c2"])
        second_retired = learn.retire(self.repo, second["id"], "Replaced", ACTOR)
        self.assertEqual(second_retired["constraint"]["status"], "retired")
        self.assertEqual(learn.fixed_checks(self.repo), [])
        self.assertEqual(self.raw_checks()["checks"], [])
        self.assertEqual([c["id"] for c in self.raw_constraints()], ["c1", "c2"])
        self.assertEqual([e["data"] for e in self.events("constraint.retire")], [{"id": "c1"}])

    def test_retire_validation(self):
        c = self.add()
        for reason in ("", " \n", None, 7):
            self.error("bad_reason", 2, learn.retire, self.repo, c["id"], reason, ACTOR)
        self.error("unknown_constraint", 4, learn.retire, self.repo, "c404", "Why", ACTOR)
        learn.retire(self.repo, c["id"], "Done", ACTOR)
        self.error("wrong_status", 4, learn.retire, self.repo, c["id"], "Again", ACTOR)

    def test_healed_read_does_not_rewrite_and_can_be_promoted_again(self):
        c = self.add()
        learn.promote(self.repo, c["id"], "false", ACTOR)
        self.checks_path.unlink()
        before = self.constraints_path.read_bytes()
        self.assertEqual(learn.all_constraints(self.repo), [c])
        self.assertEqual(learn.applying(self.repo, self.plan), [c])
        self.assertEqual(self.constraints_path.read_bytes(), before)
        self.assertEqual(learn.fixed_checks(self.repo), [])
        self.assertEqual(learn.promote(self.repo, c["id"], "true", ACTOR)["constraint"]["status"], "promoted")

    def test_orphan_active_retired_and_unlinked_checks_are_ignored(self):
        active, retired, promoted = self.add(), self.add(), self.add()
        learn.retire(self.repo, retired["id"], "Done", ACTOR)
        kept = learn.promote(self.repo, promoted["id"], "true", ACTOR)["check"]
        document = {"schema_version": 1, "checks": [
            dict(kept, id="fx_c404", from_constraint="c404"),
            dict(kept, id="fx_c1", from_constraint=active["id"]),
            dict(kept, id="fx_c2", from_constraint=retired["id"]),
            {"id": "manual", "type": "cmd", "run": "true"}, kept]}
        with store.locked(self.meta / ".lock"):
            learn._write_checks(self.meta, document)
        self.assertEqual(learn.fixed_checks(self.repo), [kept])
        self.constraints_path.unlink()
        self.assertEqual(learn.fixed_checks(self.repo), [])

    def test_fixed_checks_keep_file_order(self):
        first, second = self.add(), self.add()
        second_check = learn.promote(self.repo, second["id"], "true", ACTOR)["check"]
        first_check = learn.promote(self.repo, first["id"], "true", ACTOR)["check"]
        self.assertEqual(learn.fixed_checks(self.repo), [second_check, first_check])

    def test_partial_promotion_private_steps_and_replacement(self):
        c = self.add()
        check = {"id": "fx_c1", "type": "cmd", "run": "false", "from_constraint": "c1",
                 "added": core.now()}
        with store.locked(self.meta / ".lock"):
            learn._write_checks(self.meta, {"schema_version": 1, "checks": [check]})
        self.assertEqual(learn.all_constraints(self.repo), [c])
        self.assertEqual(learn.fixed_checks(self.repo), [])
        promoted = dict(c, status="promoted")
        with store.locked(self.meta / ".lock"):
            learn._write_constraints(self.meta, [promoted])
        self.assertEqual(learn.fixed_checks(self.repo), [check])
        with store.locked(self.meta / ".lock"):
            learn._write_constraints(self.meta, [c])
        result = learn.promote(self.repo, c["id"], "true", ACTOR)
        self.assertEqual(self.raw_checks()["checks"], [result["check"]])

    def test_promotion_crash_after_checks_install_is_recoverable(self):
        c = self.add()
        before = self.constraints_path.read_bytes()
        with mock.patch.object(learn, "_write_constraints", side_effect=RuntimeError("crash")):
            with self.assertRaisesRegex(RuntimeError, "crash"):
                learn.promote(self.repo, c["id"], "false", ACTOR, self.run)
        self.assertEqual(self.constraints_path.read_bytes(), before)
        self.assertEqual(self.raw_checks()["checks"][0]["id"], "fx_c1")
        self.assertEqual(learn.fixed_checks(self.repo), [])
        self.assertEqual(learn.all_constraints(self.repo), [c])
        self.assertEqual(self.events("constraint.promote"), [])
        learn.promote(self.repo, c["id"], "true", ACTOR)
        self.assertEqual(len(learn.fixed_checks(self.repo)), 1)

    def test_retirement_crash_after_check_removal_heals_to_active(self):
        c = self.add()
        learn.promote(self.repo, c["id"], "false", ACTOR)
        with mock.patch.object(learn, "_write_constraints", side_effect=RuntimeError("crash")):
            with self.assertRaisesRegex(RuntimeError, "crash"):
                learn.retire(self.repo, c["id"], "Obsolete", ACTOR, self.run)
        self.assertEqual(self.raw_constraints()[0]["status"], "promoted")
        self.assertEqual(learn.all_constraints(self.repo), [c])
        self.assertEqual(learn.applying(self.repo, self.plan), [c])
        self.assertEqual(learn.fixed_checks(self.repo), [])
        self.assertEqual(self.events("constraint.retire"), [])
        learn.retire(self.repo, c["id"], "Obsolete", ACTOR)
        self.assertEqual(learn.all_constraints(self.repo)[0]["status"], "retired")

    def test_writes_are_atomic_under_project_lock_in_required_order(self):
        writes = []
        atomic_write = store.atomic_write

        def checked_write(path, data):
            self.error("lock_timeout", core.EXIT_IO, self.acquire_project_lock)
            writes.append(pathlib.Path(path).name)
            return atomic_write(path, data)

        with mock.patch.object(store, "atomic_write", side_effect=checked_write):
            c = self.add()
            learn.promote(self.repo, c["id"], "true", ACTOR)
            learn.retire(self.repo, c["id"], "Done", ACTOR)
        self.assertEqual(writes, ["constraints.jsonl", "checks.json", "constraints.jsonl",
                                  "checks.json", "constraints.jsonl"])

    def acquire_project_lock(self):
        with store.locked(self.meta / ".lock", timeout_s=0.001):
            pass

    def test_six_processes_add_distinct_ids_without_lost_lines(self):
        context = multiprocessing.get_context("fork")
        barrier, results = context.Barrier(6), context.Queue()
        processes = [context.Process(target=concurrent_add,
                     args=(self.repo, self.run, barrier, results)) for _ in range(6)]
        try:
            for process in processes:
                process.start()
            for process in processes:
                process.join(15)
                self.assertEqual(process.exitcode, 0)
            self.assertCountEqual([results.get(timeout=2) for _ in processes],
                                  ["c%d" % n for n in range(1, 7)])
            self.assertEqual(len(self.raw_constraints()), 6)
            self.assertEqual(len(self.events("constraint.add")), 6)
        finally:
            for process in processes:
                if process.is_alive():
                    process.terminate()
                    process.join()
            results.close()
            results.join_thread()

    def assert_corrupt_readers_and_writers(self, code):
        for function, args in ((learn.all_constraints, (self.repo,)),
                               (learn.applying, (self.repo, self.plan)),
                               (learn.fixed_checks, (self.repo,)),
                               (self.add, ()),
                               (learn.promote, (self.repo, "c1", "true", ACTOR)),
                               (learn.retire, (self.repo, "c1", "Done", ACTOR))):
            with self.subTest(function=function.__name__):
                self.error(code, core.EXIT_IO, function, *args)

    def test_corrupt_constraint_lines_raise_without_rewriting(self):
        c = self.add()
        valid = json.dumps(c) + "\n"
        for suffix in ("{bad}\n", "{unfinished", "[]\n", "null\n", "\n", "{}\n",
                       json.dumps(dict(c, scope={"paths": [42]})) + "\n",
                       json.dumps(dict(c, status="unknown")) + "\n", valid):
            with self.subTest(suffix=suffix):
                self.constraints_path.write_text(valid + suffix, encoding="utf-8")
                before = self.constraints_path.read_bytes()
                self.assert_corrupt_readers_and_writers("constraints_corrupt")
                self.assertEqual(self.constraints_path.read_bytes(), before)
        self.constraints_path.write_bytes(b"\xff\n")
        self.assert_corrupt_readers_and_writers("constraints_corrupt")

    def test_corrupt_checks_raise_without_rewriting(self):
        self.add()
        for text in ("{bad}", "", "[]", "null", "{}", '{"checks": []}',
                     '{"schema_version": 2, "checks": []}',
                     '{"schema_version": true, "checks": []}',
                     '{"schema_version": 1, "checks": {}}',
                     '{"schema_version": 1, "checks": [null]}',
                     '{"schema_version": 1, "checks": [{"id": "x", "type": "cmd"}]}'):
            with self.subTest(text=text):
                self.checks_path.write_text(text, encoding="utf-8")
                self.assert_corrupt_readers_and_writers("checks_corrupt")
                self.assertEqual(self.checks_path.read_text(), text)
        self.checks_path.write_bytes(b"\xff")
        self.assert_corrupt_readers_and_writers("checks_corrupt")

    def test_write_io_failure_is_gferror_and_add_has_no_event(self):
        with mock.patch.object(store, "atomic_write", side_effect=OSError("disk full")):
            self.error("io_error", core.EXIT_IO, self.add)
        self.assertFalse(self.constraints_path.exists())
        self.assertEqual(self.events("constraint.add"), [])

    def test_fixed_checks_run_only_after_next_approved_plan(self):
        c = self.add()
        promoted = learn.promote(self.repo, c["id"], "false", ACTOR)
        self.assertEqual(gate.gate_final(self.run, None, ACTOR)["result"], "passed")
        refresh_contract(self.run)
        result = gate.gate_final(self.run, None, ACTOR)
        self.assertEqual(result["failed_checks"], [promoted["check"]["id"]])
        learn.retire(self.repo, c["id"], "Replace failing fixture", ACTOR)
        self.assertEqual(gate.gate_final(self.run, None, ACTOR)["result"], "failed")
        refresh_contract(self.run)
        self.assertEqual(gate.gate_final(self.run, None, ACTOR)["result"], "passed")

    def test_assign_briefs_include_scoped_learning_and_fixed_checks(self):
        c = self.add(text="Keep the config backwards compatible", paths=["src/config.py"])
        other = self.add(text="Unrelated documentation lesson", paths=["docs/"])
        refresh_contract(self.run)
        text = assign.brief(self.run, "work")
        self.assertIn(c["text"], text)
        self.assertNotIn(other["text"], text)
        self.assertEqual((self.run / "brief" / "work.md").read_text(), text)
        learn.promote(self.repo, c["id"], "true", ACTOR)
        text = assign.plan_brief(self.repo, self.run)
        self.assertIn(c["text"], text)
        self.assertIn("fx_c1", text)
        self.assertIn("true", text)
        learn.retire(self.repo, c["id"], "No longer relevant", ACTOR)
        self.assertIn(c["text"], assign.brief(self.run, "work"))
        refresh_contract(self.run)
        self.assertNotIn(c["text"], assign.brief(self.run, "work"))


if __name__ == "__main__":
    unittest.main()
