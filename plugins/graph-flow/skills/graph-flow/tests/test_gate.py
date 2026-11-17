"""Gate contract tests: pure rules and isolated, signed event-log scenarios."""
import copy
import os
import pathlib
import shlex
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock

SCRIPTS = pathlib.Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))
from graphflow import checks, core, decisions, gate, graph, plan, state, store

from human_support import legacy_run

ACTOR = {"role": "leader", "node": None, "session": "gate-test"}
HUMAN = {"role": "human", "node": None, "session": None}
CMD = {"id": "unit", "type": "cmd", "run": "true"}
HOST = {"id": "ide", "type": "host", "tool": "IDE", "expect": "green"}


def work(node_id="w", **updates):
    node = {"id": node_id, "kind": "work", "goal": "implement " + node_id,
            "owns": [node_id + ".txt"], "lane": 1, "grade": "scoped", "checks": [dict(CMD)]}
    node.update(updates)
    return node


def review(**updates):
    node = {"id": "v", "kind": "review", "goal": "review W", "target": "w",
            "lens": "correctness", "owns": [], "lane": 1, "grade": "daily",
            "checks": [{"id": "citations", "type": "cites"}],
            "needs": [{"from": "w", "artifact": "w.txt"}]}
    node.update(updates)
    return node


def decision(**updates):
    node = {"id": "d", "kind": "decision", "goal": "authorize", "owns": [],
            "lane": 3, "checks": [], "question": "Publish?", "decision_kind": "authorization"}
    node.update(updates)
    return node


def result(kind="cmd", failed=False, **updates):
    data = {"check": "unit", "type": kind, "grade": 2 if kind == "host" else 1,
            "attempt": 1, "result": "failed" if failed else "passed", "exit_code": 1 if failed else 0,
            "timed_out": False, "log": "evidence/w/unit/a1-test.log"}
    data.update(updates)
    return data


class EvaluateTests(unittest.TestCase):
    def setUp(self):
        self.plan, _ = plan.normalize({"nodes": [work()]})
        self.st = {"status": "submitted", "attempts": 1, "max_attempts": 3, "basis": 0,
                   "submission": {"id": 10, "changed_files": ["w.txt"]},
                   "assignment": {"family": "openai"}, "checks": {},
                   "reviews": [], "trajectory_clean": True}
        self.state = {"nodes": {"w": self.st}, "decisions": {}}

    @property
    def node(self):
        return self.plan["nodes"][0]

    def evaluate(self, results=None, integration=None, rollbacks=0):
        return gate.evaluate(self.plan, self.state, "w", results or [], integration or [], rollbacks)

    def assert_verdict(self, expected, rule, **kwargs):
        data = self.evaluate(**kwargs)
        self.assertEqual((data["verdict"], data["rule"]), (expected, rule))
        return data

    def lane(self, lane):
        self.node["effective_lane"] = lane
        self.st["reviews"] = [{"node": "v", "status": "passed", "target_submission": 10,
                               "family": "claude", "verdict": "pass"}]

    def answer(self, purpose, outcome="approved", check=None, kind="review", **updates):
        data = {"node": "w", "submission": 10, "check": check, "purpose": purpose,
                "kind": kind, "status": "answered", "outcome": outcome, "verified": True, "stale": False}
        data.update(updates)
        self.state["decisions"]["d1"] = data
        return data

    def test_r1_positive_and_negative(self):
        failure = result(failed=True)
        self.assertEqual(self.assert_verdict("reject", "R1", results=[failure])["failed"], [failure])
        self.assert_verdict("pass", "R7", results=[result()])

    def test_r2_positive_and_negative(self):
        self.st["attempts"] = 3
        self.assert_verdict("replan", "R2", integration=[result(failed=True)])
        self.st["attempts"] = 2
        self.assert_verdict("reject", "R1", integration=[result(failed=True)])

    def test_r3_host_positive_negative_and_wrong_attempt(self):
        self.node["checks"].append(HOST)
        self.assert_verdict("unverified", "R3")
        self.st["checks"]["ide"] = {"loop": result("host", attempt=0)}
        self.assert_verdict("unverified", "R3")
        self.st["checks"]["ide"]["loop"]["attempt"] = 1
        self.assert_verdict("pass", "R7")

    def test_r3_review_family_and_submission_rules(self):
        self.lane(2)
        for family, reviewer, expected in [("openai", "claude", "pass"),
                                            ("openai", "openai", "unverified"),
                                            (None, "claude", "unverified"),
                                            ("openai", None, "unverified"), (None, None, "unverified")]:
            with self.subTest(worker=family, reviewer=reviewer):
                self.st["assignment"]["family"] = family
                self.st["reviews"][0]["family"] = reviewer
                self.assertEqual(self.evaluate()["verdict"], expected)
        self.st["assignment"]["family"] = "openai"
        self.st["reviews"][0].update(family="claude", target_submission=9)
        self.assert_verdict("unverified", "R3")
        self.st["reviews"][0].update(target_submission=10, status="submitted")
        self.assert_verdict("unverified", "R3")
        self.st["reviews"] = []
        self.assert_verdict("unverified", "R3")

    def test_r4_host_positive_and_hold_approval(self):
        self.node["checks"].append(HOST)
        failed = result("host", failed=True)
        self.st["checks"]["ide"] = {"loop": failed}
        self.assertEqual(self.assert_verdict("hold", "R4")["failed"], [failed])
        self.answer("hold")
        self.assert_verdict("pass", "R7")

    def test_r4_review_positive_and_negative(self):
        self.lane(2)
        self.st["reviews"][0]["verdict"] = "fail"
        self.assert_verdict("hold", "R4")
        self.st["reviews"][0]["verdict"] = "pass"
        self.assert_verdict("pass", "R7")
        self.st["reviews"].append({"status": "submitted", "target_submission": 10, "verdict": "fail"})
        self.assert_verdict("pass", "R7")
        self.st["reviews"].append({"status": "passed", "target_submission": 9, "verdict": "fail"})
        self.assert_verdict("pass", "R7")

    def test_r5_positive_negative_approval_and_decline(self):
        self.lane(2)
        self.assert_verdict("pass", "R7")
        self.st["trajectory_clean"] = False
        data = self.assert_verdict("needs_approval", "R5")
        self.assertEqual(data["asks"][0]["purpose"], "trajectory")
        self.answer("trajectory")
        self.assert_verdict("pass", "R7")
        for outcome in ("rejected", "revision_requested"):
            self.answer("trajectory", outcome)
            self.assert_verdict("hold", "R4")
        self.state["decisions"] = {}
        self.st["trajectory_clean"] = True
        self.assert_verdict("needs_approval", "R5", rollbacks=1)
        self.node["effective_lane"] = 1
        self.assert_verdict("pass", "R7", rollbacks=1)

    def test_r6_lane3_positive_negative_and_decline(self):
        self.lane(3)
        data = self.assert_verdict("needs_approval", "R6")
        self.assertEqual(data["asks"][0]["kind"], "authorization")
        self.answer("lane3", kind="authorization")
        self.assert_verdict("pass", "R7")
        for outcome in ("rejected", "revision_requested"):
            self.answer("lane3", outcome, kind="authorization")
            self.assert_verdict("hold", "R4")

    def test_r6_human_check_bound_to_check_kind_and_submission(self):
        self.node["checks"].append({"id": "taste", "type": "human", "prompt": "Readable?"})
        self.assert_verdict("needs_approval", "R6")
        self.answer("human_check", check="other")
        self.assert_verdict("needs_approval", "R6")
        self.answer("human_check", check="taste", kind="authorization")
        self.assert_verdict("needs_approval", "R6")
        self.answer("human_check", check="taste", submission=9)
        self.assert_verdict("needs_approval", "R6")
        self.answer("human_check", check="taste")
        self.assert_verdict("pass", "R7")
        self.answer("human_check", "rejected", check="taste")
        self.assert_verdict("hold", "R4")

    def test_r7_pass_and_negative(self):
        self.assertEqual(self.evaluate(), {"verdict": "pass", "rule": "R7", "failed": [], "asks": []})
        self.assert_verdict("reject", "R1", results=[result(failed=True)])

    def test_grade_one_outranks_review_and_host_failures(self):
        self.lane(2)
        self.st["reviews"][0]["verdict"] = "fail"
        self.node["checks"].append(HOST)
        self.st["checks"]["ide"] = {"loop": result("host", failed=True)}
        for kind in ("cmd", "scope", "cites"):
            with self.subTest(kind=kind):
                failed = result(kind, failed=True)
                data = self.assert_verdict("reject", "R1", results=[failed])
                self.assertEqual(data["failed"], [failed])

    def test_unverified_or_stale_approvals_never_count(self):
        self.lane(3)
        for updates in ({"verified": False}, {"stale": True}):
            with self.subTest(**updates):
                self.answer("lane3", kind="authorization", **updates)
                self.assert_verdict("needs_approval", "R6")

    def test_ask_deduplication_exact_binding_for_r5_and_r6(self):
        for lane, purpose, kind, rule in [(2, "trajectory", "review", "R5"),
                                          (3, "lane3", "authorization", "R6")]:
            with self.subTest(lane=lane):
                self.lane(lane)
                self.st["trajectory_clean"] = False
                self.answer(purpose, kind=kind, status="open", verified=False)
                self.assertEqual(self.assert_verdict("needs_approval", rule)["asks"], [])
                self.state["decisions"]["d1"]["kind"] = "information"
                self.assertEqual(self.evaluate()["asks"], [], "open-ask identity excludes kind")
                for changed in ({"stale": True}, {"submission": 9}, {"node": "other"},
                                {"check": "other"}, {"purpose": "free"}):
                    self.answer(purpose, kind=kind, status="open", verified=False).update(changed)
                    self.assertEqual(len(self.evaluate()["asks"]), 1)
                self.state["decisions"] = {}

    def test_unverified_or_stale_declines_do_not_hold(self):
        self.lane(3)
        for updates in ({"verified": False}, {"stale": True}):
            self.answer("lane3", "rejected", kind="authorization", **updates)
            self.assert_verdict("needs_approval", "R6")

    def test_multiple_missing_human_checks_and_lane3(self):
        self.lane(3)
        self.node["checks"].extend([{"id": "a", "type": "human"}, {"id": "b", "type": "human"}])
        self.assertEqual([a["purpose"] for a in self.evaluate()["asks"]],
                         ["human_check", "human_check", "lane3"])

    def test_decision_node_pass_hold_and_missing_rules(self):
        self.plan["nodes"] = [decision(id="w")]
        self.st["submission"] = None
        data = self.assert_verdict("needs_approval", "R6")
        self.assertEqual((data["asks"][0]["question"], data["asks"][0]["kind"]),
                         ("Publish?", "authorization"))
        self.answer("node", status="open", verified=False, submission=None)
        self.assertEqual(self.evaluate()["asks"], [])
        for outcome in ("answered", "approved"):
            self.answer("node", outcome, submission=None)
            self.assert_verdict("pass", "R7")
        for outcome in ("rejected", "revision_requested"):
            self.answer("node", outcome, submission=None)
            self.assert_verdict("hold", "R4")
        for updates in ({"verified": False}, {"stale": True}, {"purpose": "free"}, {"submission": 10}):
            self.answer("node", submission=None)
            self.state["decisions"]["d1"].update(updates)
            self.assert_verdict("needs_approval", "R6")

    def test_evaluate_is_pure(self):
        self.lane(3)
        before = copy.deepcopy((self.plan, self.state))
        with mock.patch("builtins.open", side_effect=AssertionError("file access")), \
                mock.patch.object(pathlib.Path, "read_bytes", side_effect=AssertionError("file access")), \
                mock.patch.object(subprocess, "run", side_effect=AssertionError("git access")), \
                mock.patch.object(core, "now", side_effect=AssertionError("clock access")), \
                mock.patch.object(core, "human_sig", side_effect=AssertionError("signature access")):
            data = self.evaluate()
        data["asks"][0]["evidence"]["checks"]["new"] = "changed"
        self.assertEqual((self.plan, self.state), before)


class RejectionTests(unittest.TestCase):
    def test_cmd_record_and_five_line_renderer(self):
        failed = result(failed=True)
        rejection = gate.build_rejection(work(), {"attempts": 2, "max_attempts": 3}, [failed],
                                         {failed["log"]: ["AssertionError"]})
        self.assertEqual(rejection, {"unit": "w", "attempt": 2, "max_attempts": 3,
                         "verdict": "red", "reason": "check unit exited 1",
                         "evidence": {"log": failed["log"], "tail": ["AssertionError"]}, "scope": ["w.txt"]})
        self.assertEqual(gate.render_rejection(rejection).splitlines(), [
            "UNIT      w (attempt 2 of 3)", "VERDICT   red", "REASON    check unit exited 1",
            "EVIDENCE  evidence/w/unit/a1-test.log: AssertionError", "SCOPE     w.txt only"])

    def test_scope_without_log_names_paths_and_leader_recovery(self):
        rejection = gate.build_rejection(work(), {"attempts": 1},
            [result("scope", failed=True, violations=["stray.txt"], log=None)], {})
        self.assertEqual(gate.render_rejection(rejection),
            "UNIT      w (attempt 1 of 3)\nVERDICT   red\n"
            "REASON    scope: stray.txt outside owned paths\n"
            "EVIDENCE  stray.txt\nSCOPE     w.txt only\n"
            "RESTORE   Leader restores these paths before reassigning: stray.txt")

    def test_logless_citations_and_review_reasons_never_render_none(self):
        rejection = gate.build_rejection(work(), {"attempts": 1},
            [result("cites", failed=True, violations=[{"file": "bad.txt", "reason": "missing"},
                                                       {"file": None, "finding": 2}],
                    log=None)], {})
        self.assertIn("bad.txt", gate.render_rejection(rejection))
        self.assertNotIn("None", gate.render_rejection(rejection))
        for reason in ("missing review", "review verdict fail"):
            rejection["reason"] = reason
            rejection["evidence"] = {"log": None, "tail": []}
            rendered = gate.render_rejection(rejection)
            self.assertIn("EVIDENCE  " + reason, rendered)
            self.assertNotIn("None", rendered)

    def test_all_failure_reasons_are_joined(self):
        failed = [result(failed=True, timed_out=True),
                  result("scope", failed=True, violations=["x.txt", "y.txt"], log=None),
                  result("cites", failed=True, violations=[{}, {}], log=None)]
        rejection = gate.build_rejection(work(), {"attempts": 3}, failed, {})
        self.assertEqual(rejection["reason"], "check unit timed out; scope: x.txt, y.txt outside owned paths; "
                         "cites: 2 invalid findings")
        self.assertEqual(rejection["evidence"]["tail"], [])


class GateCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="graphflow-gate-")
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name).resolve()
        home = self.root / "home"
        home.mkdir()
        (home / "human.key").write_bytes(b"test-human-key-32-bytes-long!!!!!")
        (home / "human.key").chmod(0o600)
        env = mock.patch.dict(os.environ, {"GF_HOME": str(home)})
        env.start()
        self.addCleanup(env.stop)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.git("init", "-q")
        self.git("config", "user.name", "Gate Test")
        self.git("config", "user.email", "gate@example.invalid")
        for name in ("p.txt", "w.txt", "x.txt"):
            self.write(name, "good\n")
        self.commit()
        self.main = self.git("symbolic-ref", "--short", "HEAD")
        self.run = legacy_run(self.repo, "gate-test", ACTOR)
        self.set_plan([work()])

    def git(self, *args):
        completed = subprocess.run(["git", "-C", str(self.repo)] + list(args),
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return completed.stdout.decode().strip()

    def write(self, name, value):
        path = self.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value)

    def commit(self):
        self.git("add", "--all", "--", ":(exclude).graph-flow")
        self.git("commit", "-q", "-m", "test fixture")
        return self.git("rev-parse", "HEAD")

    def set_plan(self, nodes, integration=None):
        self.plan, _ = plan.normalize({"schema_version": 1, "goal": "gate tests", "nodes": nodes,
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

    def derived(self):
        return state.derive(store.read_plan(self.run), store.events(self.run))

    def status(self, node="w"):
        return self.derived()["nodes"][node]

    def assign(self, node, family):
        self.append("node.assign", {"node": node, "executor": "subagent", "model": "fixture",
                    "effort": "high", "provider": family, "family": family, "isolation": "shared"})

    def start(self, node="w"):
        return checks.start(self.run, node, None, ACTOR)

    def submit(self, node="w", commit=None):
        return checks.submit(self.run, node, commit, None, "fixture", [], None, ACTOR)

    def gate(self, node="w"):
        return gate.gate(self.run, node, None, ACTOR)

    def answer(self, decision_id, outcome="approved"):
        data = decisions.answer(self.run, decision_id, outcome, "human answer", "dashboard", HUMAN)
        self.assertTrue(self.derived()["decisions"][decision_id]["verified"])
        return data

    def events(self, event_type):
        return [e for e in store.events(self.run) if e["type"] == event_type]

    def error(self, code, func, *args):
        with self.assertRaises(core.GFError) as caught:
            func(*args)
        self.assertEqual(caught.exception.code, code)
        self.assertEqual(caught.exception.exit_code, core.EXIT_STATE)
        return caught.exception

    def redo_review(self):
        self.start("v")
        checks.review_submit(self.run, "v", "pass", [], ACTOR)
        self.assertEqual(self.gate("v")["verdict"], "pass")

    def lane_plan(self, lane=2, check=None):
        self.set_plan([work(lane=lane, checks=[check or dict(CMD)]), review()])
        self.assign("w", "openai")
        self.assign("v", "claude")

    def side_submission(self, text="good\n", branch="worker"):
        self.start()
        self.git("checkout", "-q", "-b", branch)
        self.write("w.txt", text + "worker change\n")
        commit = self.commit()
        self.submit(commit=commit)
        self.git("checkout", "-q", self.main)
        return commit

    def chain_passed(self):
        self.set_plan([work("p"), work(lane=2, needs=[{"from": "p", "artifact": "p.txt"}]),
                       review(), decision(needs=[{"from": "w", "artifact": "w.txt"}])])
        self.assign("w", "openai")
        self.assign("v", "claude")
        self.start("p")
        self.submit("p")
        self.assertEqual(self.gate("p")["verdict"], "pass")
        self.start()
        self.submit()
        self.redo_review()
        self.assertEqual(self.gate()["verdict"], "pass")
        asked = self.gate("d")["asks"][0]
        self.answer(asked)
        self.assertEqual(self.gate("d")["verdict"], "pass")
        return asked


class ScenarioTests(GateCase):
    def test_A1_lane2_merged_work_and_independent_review_pass(self):
        self.lane_plan()
        commit = self.side_submission()
        self.git("merge", "--no-ff", "--no-edit", commit)
        self.redo_review()
        data = self.gate()
        self.assertEqual((data["verdict"], data["rule"]), ("pass", "R7"))
        self.assertEqual(data["tested_head"], self.git("rev-parse", "HEAD"))
        self.assertEqual(self.events("check.result")[0]["data"]["type"], "cites")

    def test_A2_reject_restart_redo_review_and_stale_old_decision(self):
        command = dict(CMD, run="head -n 1 w.txt | /usr/bin/grep -qx good")
        self.lane_plan(check=command)
        commit = self.side_submission(text="bad\n")
        self.git("merge", "--no-ff", "--no-edit", commit)
        self.redo_review()
        asked = decisions.ask(self.run, "review", "Approve trajectory?", "w", None,
                              "trajectory", None, ACTOR)["id"]
        rejected = self.gate()
        self.assertEqual(rejected["verdict"], "reject")
        rejection = rejected["rejection"]
        self.assertTrue({"unit", "verdict", "reason", "evidence", "scope"}.issubset(rejection))
        self.assertEqual(len(gate.render_rejection(rejection).splitlines()), 5)
        self.assertEqual(self.status("v")["status"], "passed", "rejection changes only W")
        self.start()
        self.assertNotEqual(self.status("v")["status"], "passed")
        self.write("w.txt", "good\nfixed\n")
        self.submit(commit=self.commit())
        self.assertIn("v", graph.ready(self.plan, self.derived()))
        self.assertTrue(self.derived()["decisions"][asked]["stale"])
        self.error("stale_decision", self.answer, asked)
        self.redo_review()
        self.assertEqual(self.gate()["verdict"], "pass")

    def test_A3_lane3_deduplicates_then_approved_passes_or_rejected_holds(self):
        self.lane_plan(3)
        self.start()
        self.submit()
        self.redo_review()
        first = self.gate()
        self.assertEqual((first["verdict"], len(first["asks"])), ("needs_approval", 1))
        self.assertEqual(self.gate()["asks"], [])
        self.assertEqual(len(self.events("decision.ask")), 1)
        self.answer(first["asks"][0])
        self.assertEqual(self.gate()["verdict"], "pass")
        gate.reopen(self.run, "w", "new authorization", ACTOR)
        self.start()
        self.submit()
        self.redo_review()
        asked = self.gate()["asks"][0]
        self.answer(asked, "rejected")
        held = self.gate()
        self.assertEqual((held["verdict"], held["rule"], held["asks"]), ("hold", "R4", []))

    def test_A4_reopen_invalidates_transitive_nodes_reviews_and_answers(self):
        old = self.chain_passed()
        reopened = gate.reopen(self.run, "p", "new input", ACTOR)
        self.assertEqual(reopened, {"node": "p", "invalidated": ["p", "w", "v", "d"]})
        self.assertTrue(all(n["status"] != "passed" for n in self.derived()["nodes"].values()))
        self.assertTrue(self.derived()["decisions"][old]["stale"])
        self.start("p")
        self.submit("p")
        self.assertEqual(self.gate("p")["verdict"], "pass")
        self.start()
        self.submit()
        self.assertEqual(self.gate()["verdict"], "unverified")
        self.redo_review()
        self.assertEqual(self.gate()["verdict"], "pass")
        new = self.gate("d")
        self.assertEqual(new["verdict"], "needs_approval")
        self.assertNotEqual(new["asks"][0], old)

    def test_A5_plan_checks_change_resets_only_work_and_dependents(self):
        old = self.chain_passed()
        nodes = copy.deepcopy(self.plan["nodes"])
        nodes[1]["checks"][0]["run"] = ":"
        self.set_plan(nodes)
        self.assertEqual(self.status("p")["status"], "passed")
        self.assertTrue(all(self.status(n)["status"] != "passed" for n in ("w", "v", "d")))
        self.assertTrue(self.derived()["decisions"][old]["stale"])
        self.assertEqual([self.status(n)["attempts"] for n in ("w", "v", "d")], [0, 0, 0])

    def test_A6_third_failure_replans_but_third_hold_is_regatable(self):
        self.set_plan([work(checks=[dict(CMD, run="false")]),
                       work("x", checks=[dict(CMD), dict(HOST)])])
        for attempt in range(1, 4):
            self.start()
            self.submit()
            data = self.gate()
            self.assertEqual((data["verdict"], data["rule"]),
                             ("replan", "R2") if attempt == 3 else ("reject", "R1"))
        self.error("attempts_exhausted", self.start)
        for attempt in range(1, 4):
            self.start("x")
            checks.record_host(self.run, "x", "ide", "failed", "red", ACTOR)
            self.submit("x")
            self.assertEqual(self.gate("x")["verdict"], "hold")
        self.assertEqual(self.gate("x")["verdict"], "hold")
        self.assertEqual(self.status("x")["attempts"], 3)
        self.error("attempts_exhausted", self.start, "x")

    def test_A7_shared_uncommitted_work_serializes_and_restores_or_deletes_fail_scope(self):
        self.set_plan([work(), work("x")])
        self.start()
        self.write("w.txt", "first node's uncommitted work\n")
        self.submit()
        self.error("shared_busy", self.start, "x")
        self.assertEqual(self.gate()["verdict"], "pass")
        self.start("x")
        self.git("restore", "w.txt")
        self.submit("x")
        rejected = self.gate("x")
        self.assertEqual(rejected["verdict"], "reject")
        self.assertEqual(rejected["rejection"]["reason"], "scope: w.txt outside owned paths")
        self.assertEqual(self.status()["status"], "passed")
        self.write("w.txt", "first node's uncommitted work\n")
        self.start("x")
        (self.repo / "w.txt").unlink()
        self.submit("x")
        self.assertEqual(self.gate("x")["rejection"]["reason"], "scope: w.txt outside owned paths")

    def test_A8_final_gate_required_again_after_reopen(self):
        self.set_plan([work(), work("x")])
        for node in ("w", "x"):
            self.start(node)
            self.submit(node)
            self.assertEqual(self.gate(node)["verdict"], "pass")
        self.assertEqual(gate.gate_final(self.run, None, ACTOR)["result"], "passed")
        self.assertEqual(self.derived()["run"]["status"], "complete")
        gate.reopen(self.run, "w", "recheck", ACTOR)
        self.assertEqual(self.derived()["run"]["status"], "open")
        self.start()
        self.submit()
        self.assertEqual(self.gate()["verdict"], "pass")
        self.assertEqual(self.derived()["run"]["status"], "open")
        gate.gate_final(self.run, None, ACTOR)
        self.assertEqual(self.derived()["run"]["status"], "complete")

    def test_A9_unmerged_commit_is_refused_without_any_event(self):
        self.side_submission()
        before = store.events(self.run)
        self.error("not_merged", self.gate)
        self.assertEqual(store.events(self.run), before)


class ExecutionTests(GateCase):
    def _competing_gate(self, first_passes):
        ok = self.root / "ok"
        if not first_passes:
            ok.touch()
        self.set_plan([work(checks=[dict(CMD, run="test -f %s" % shlex.quote(str(ok)))]),
                       work("x", needs=[{"from": "w", "artifact": "w.txt"}])])
        self.start()
        self.submit()
        original = checks.run_scope
        recorded = []

        def finish_first(*args):
            outcome = original(*args)
            if first_passes:
                ok.touch()
            else:
                ok.unlink()
            with mock.patch.object(checks, "run_scope", original):
                self.assertEqual(self.gate()["verdict"], "pass" if first_passes else "reject")
            if first_passes:
                self.start("x")
            recorded.extend(store.events(self.run))
            return outcome

        with mock.patch.object(checks, "run_scope", finish_first):
            self.error("stale_result", self.gate)
        self.assertEqual(store.events(self.run), recorded)
        self.assertEqual(len(self.events("gate.verdict")), 1)
        self.assertEqual(self.status()["status"], "passed" if first_passes else "rejected")
        self.assertEqual(self.status("x")["status"], "running" if first_passes else "pending")

    def test_late_rejection_cannot_overwrite_pass_with_dependent_running(self):
        self._competing_gate(first_passes=True)

    def test_late_pass_cannot_overwrite_rejection(self):
        self._competing_gate(first_passes=False)

    def test_competing_decision_gate_discards_late_asks_and_verdict(self):
        self.set_plan([decision()])
        original = gate._head
        recorded = []

        def finish_first(*args):
            head = original(*args)
            with mock.patch.object(gate, "_head", original):
                self.assertEqual(self.gate("d")["verdict"], "needs_approval")
            recorded.extend(store.events(self.run))
            return head

        with mock.patch.object(gate, "_head", finish_first):
            self.error("stale_result", self.gate, "d")
        self.assertEqual(store.events(self.run), recorded)
        self.assertEqual(len(self.events("decision.ask")), 1)
        self.assertEqual(len(self.events("gate.verdict")), 1)

    def test_passed_decision_cannot_record_another_verdict(self):
        self.set_plan([decision()])
        asked = self.gate("d")["asks"][0]
        self.answer(asked)
        self.assertEqual(self.gate("d")["verdict"], "pass")
        before = store.events(self.run)
        self.error("stale_result", self.gate, "d")
        self.assertEqual(store.events(self.run), before)

    def test_final_gate_allows_concurrent_node_verdict(self):
        self.set_plan([work()], [dict(CMD, id="integration")])
        self.start()
        self.submit()
        original = checks.run_cmd

        def finish_node(*args):
            outcome = original(*args)
            with mock.patch.object(checks, "run_cmd", original):
                self.assertEqual(self.gate()["verdict"], "pass")
            return outcome

        with mock.patch.object(checks, "run_cmd", finish_node):
            self.assertEqual(gate.gate_final(self.run, None, ACTOR)["result"], "passed")
        self.assertEqual([e["type"] for e in store.events(self.run)[-2:]],
                         ["gate.verdict", "gate.final"])
        self.assertEqual(self.derived()["run"]["status"], "complete")

    def test_normalized_human_check_asks_then_signed_review_approval_passes(self):
        self.set_plan([work(checks=[{"id": "scope", "type": "scope"}]), review()])
        self.assign("w", "openai")
        self.assign("v", "claude")
        self.start()
        self.submit()
        self.redo_review()
        first = self.gate()
        self.assertEqual(first["verdict"], "needs_approval")
        ask = self.derived()["decisions"][first["asks"][0]]
        self.assertEqual((ask["kind"], ask["purpose"], ask["check"]), ("review", "human_check", "human"))
        self.answer(ask["id"])
        self.assertEqual(self.gate()["verdict"], "pass")

    def test_stale_result_after_restart_before_gate_verdict_transaction(self):
        self.start()
        self.submit()
        original = checks.run_scope

        def restart(*args):
            outcome = original(*args)
            # A submitted node cannot start: put it on the authorized retry path first.
            sub = self.status()["submission"]["id"]
            self.append("gate.verdict", {"node": "w", "attempt": 1, "submission": sub,
                        "verdict": "hold", "rule": "R4", "rejection": None, "tested_head": None})
            self.start()
            return outcome

        with mock.patch.object(checks, "run_scope", restart):
            self.error("stale_result", self.gate)
        self.assertEqual(len(self.events("gate.verdict")), 1)
        self.assertEqual(self.status()["status"], "running")

    def test_preconditions_needs_submission_and_outdated_review_no_events(self):
        before = store.events(self.run)
        self.error("no_submission", self.gate)
        self.assertEqual(before, store.events(self.run))
        self.set_plan([work("p"), work(needs=[{"from": "p", "artifact": "p.txt"}])])
        before = store.events(self.run)
        self.error("needs_unsatisfied", self.gate)
        self.assertEqual(before, store.events(self.run))
        self.set_plan([work(), review()])
        self.start()
        self.submit()
        self.start("v")
        checks.review_submit(self.run, "v", "pass", [], ACTOR)
        self.append("review.submit", {"node": "v", "attempt": 1, "target": "w",
                    "target_submission": 0, "verdict": "pass", "findings": []})
        before = store.events(self.run)
        self.error("review_outdated", self.gate, "v")
        self.assertEqual(before, store.events(self.run))

    def test_reopen_requires_passed_node_and_nonempty_reason(self):
        before = store.events(self.run)
        self.error("wrong_status", gate.reopen, self.run, "w", "retry", ACTOR)
        self.assertEqual(store.events(self.run), before)
        with self.assertRaises(core.GFError) as caught:
            gate.reopen(self.run, "w", "  ", ACTOR)
        self.assertEqual(caught.exception.code, "bad_reason")
        self.assertEqual(store.events(self.run), before)

    def test_log_tail_has_last_five_lines(self):
        command = dict(CMD, run="printf '1\\n2\\n3\\n4\\n5\\n6\\n7\\n'; exit 8")
        self.set_plan([work(checks=[command])])
        self.start()
        self.submit()
        data = self.gate()
        self.assertEqual(data["rejection"]["evidence"]["tail"], ["3", "4", "5", "6", "7"])
        self.assertEqual(data["rejection"]["reason"], "check unit exited 8")

    def test_lane2_integration_then_fixed_checks_and_final_runs_each_once(self):
        integration = dict(CMD, id="integration")
        fixed = dict(CMD, id="fixed")
        self.set_plan([work(lane=2), review()], [integration])
        self.assign("w", "openai")
        self.assign("v", "claude")
        self.start()
        self.submit()
        self.redo_review()
        # The optional learning module is not part of this unit; exercise its public hook.
        import json
        self.write(".graph-flow/checks.json", json.dumps({"checks": [fixed]}))
        learn = types.ModuleType("graphflow.learn")
        learn.fixed_checks = mock.Mock(return_value=[fixed])
        trace = types.ModuleType("graphflow.trace")
        trace.rollbacks = mock.Mock(return_value=0)
        with mock.patch.dict(sys.modules, {"graphflow.learn": learn, "graphflow.trace": trace}):
            self.assertEqual(self.gate()["verdict"], "pass")
            data = gate.gate_final(self.run, None, ACTOR)
        self.assertEqual(data["result"], "passed")
        run_results = [e["data"] for e in self.events("check.result") if e["data"]["node"] == "_run"]
        self.assertEqual([r["check"] for r in run_results], ["integration", "fixed", "integration", "fixed"])
        self.assertEqual([e["data"]["check"] for e in self.events("check.result")],
                         ["citations", "unit", "scope", "integration", "fixed", "integration", "fixed"])
        self.assertTrue(all(r["attempt"] == 0 and r["phase"] == "gate" for r in run_results))
        trace.rollbacks.assert_called_once_with(self.repo, self.run, ["w.txt"])
        self.assertEqual(learn.fixed_checks.call_count, 2)

    def test_rollback_history_requests_signed_trajectory_review(self):
        self.lane_plan()
        self.start()
        self.submit()
        self.redo_review()
        trace = types.ModuleType("graphflow.trace")
        trace.rollbacks = mock.Mock(return_value=1)
        with mock.patch.dict(sys.modules, {"graphflow.trace": trace}):
            first = self.gate()
            self.assertEqual((first["verdict"], first["rule"]), ("needs_approval", "R5"))
            self.assertEqual(self.gate()["asks"], [])
            self.answer(first["asks"][0])
            self.assertEqual(self.gate()["verdict"], "pass")

    def test_non_command_integration_check_is_rejected_by_plan_validation(self):
        # The gate executes integration checks as commands, so the plan refuses anything else (V5).
        document = {"schema_version": 1, "goal": "g", "nodes": [work()],
                    "integration_checks": [{"id": "not-cmd", "type": "scope"}]}
        self.assertIn(("V5", None), [(p["code"], p["node"]) for p in plan.validate(document)])

    def test_final_failed_checks_and_tested_tree(self):
        self.set_plan([work()], [dict(CMD, id="bad", run="false"), dict(CMD, id="good")])
        data = gate.gate_final(self.run, self.repo, ACTOR)
        self.assertEqual(data, {"result": "failed", "failed_checks": ["bad"],
                               "tested_head": self.git("rev-parse", "HEAD")})
        self.assertEqual(self.events("gate.final")[-1]["data"], data)

    def test_decision_gate_executes_no_checks(self):
        self.set_plan([decision(decision_kind="information")])
        with mock.patch.object(checks, "run_cmd", side_effect=AssertionError("executed")), \
                mock.patch.object(checks, "run_scope", side_effect=AssertionError("executed")), \
                mock.patch.object(checks, "run_cites", side_effect=AssertionError("executed")):
            data = self.gate("d")
            self.answer(data["asks"][0], "answered")
            self.assertEqual(self.gate("d")["verdict"], "pass")
        self.assertEqual(self.events("check.result"), [])

    def test_asks_and_verdict_share_one_transaction_and_correct_ids(self):
        self.set_plan([decision()])
        original = store.transaction
        appended = []
        import contextlib

        @contextlib.contextmanager
        def transaction(*args, **kwargs):
            with original(*args, **kwargs) as tx:
                events = []
                append = tx.append

                def record(event_type, data, actor):
                    events.append(event_type)
                    return append(event_type, data, actor)

                tx.append = record
                yield tx
                appended.append(events)

        with mock.patch.object(store, "transaction", transaction):
            data = self.gate("d")
        self.assertIn(["decision.ask", "gate.verdict"], appended)
        event = self.events("decision.ask")[-1]
        self.assertEqual(event["data"]["id"], "d%d" % event["seq"])
        self.assertEqual(data["asks"], [event["data"]["id"]])


if __name__ == "__main__":
    unittest.main()
