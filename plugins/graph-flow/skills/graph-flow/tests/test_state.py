import copy
import hashlib
import json
import os
import pathlib
import sys
import tempfile
import unittest

SCRIPTS = pathlib.Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

from graphflow import core, plan as planmod, state  # noqa: E402

RUN = "r1"
ALL_KEYS = {"status", "kind", "lane", "effective_lane", "basis", "attempts", "max_attempts",
            "assignment", "base", "submission", "checks", "red", "reviews", "rejections",
            "verdict", "merged_head", "trajectory_clean", "open_decisions"}
DECISION_KEYS = {"plan_identity", "id", "seq", "node", "submission", "check", "purpose", "kind", "question",
                 "evidence", "status", "outcome", "answer", "source", "verified", "stale"}


class EnvCase(unittest.TestCase):
    KEYS = ("GF_ROLE", "GF_NODE", "GF_SESSION", "GF_HOME", "T3CODE_THREAD_ID", "CLAUDE_CODE_SESSION_ID")

    def setUp(self):
        self._saved = {k: os.environ.pop(k, None) for k in self.KEYS}
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["GF_HOME"] = self._tmp.name

    def tearDown(self):
        for k, v in self._saved.items():
            os.environ.pop(k, None)
            if v is not None:
                os.environ[k] = v
        self._tmp.cleanup()

    def write_key(self):
        (pathlib.Path(self._tmp.name) / "human.key").write_bytes(b"k" * 32)


# --- normalized plan fixtures -------------------------------------------------

def work(nid, needs=(), lane=1, checks=None, **extra):
    n = {
        "id": nid, "kind": "work", "goal": "g " + nid,
        "needs": [{"from": f, "artifact": "a"} for f in needs],
        "owns": [nid + ".py"], "outputs": [], "reads": [],
        "checks": checks if checks is not None else [
            {"id": "unit", "type": "cmd", "run": "true"}, {"id": "scope", "type": "scope"}],
        "lane": lane, "effective_lane": lane, "grade": "scoped", "max_attempts": 3,
    }
    n.update(extra)
    return n


def review(nid, target):
    return {
        "id": nid, "kind": "review", "goal": "refute", "target": target, "lens": "bugs",
        "needs": [{"from": target, "artifact": "a"}], "owns": [], "outputs": ["findings"],
        "reads": [], "checks": [{"id": "cites", "type": "cites"}],
        "lane": 1, "effective_lane": 1, "grade": "daily", "max_attempts": 3,
    }


def decision(nid, needs=()):
    return {
        "id": nid, "kind": "decision", "goal": "approve", "decision_kind": "authorization",
        "question": "ok?", "needs": [{"from": f, "artifact": "a"} for f in needs],
        "owns": [], "outputs": ["approval"], "reads": [], "checks": [],
        "lane": 3, "effective_lane": 3, "max_attempts": 3,
    }


def plan_of(*nodes):
    return {"schema_version": 1, "goal": "x", "requirements": [], "tags": [],
            "integration_checks": [], "nodes": list(nodes)}


class Log:
    """Fabricates events with increasing seq, a ts, plan_revision and actor.

    Every helper returns the seq of the event it appended."""

    def __init__(self, run=RUN, init=True):
        self.run = run
        self.events = []
        self.rev = 0
        if init:
            self.add("run.init", {"run_id": run, "project_root": "/p", "schema_version": 1})

    def add(self, type_, data, role="leader", node=None):
        seq = len(self.events) + 1
        ev = {"seq": seq, "ts": "2026-11-15T09:%02d:%02dZ" % divmod(seq % 3600, 60),
              "run": self.run, "plan_revision": self.rev,
              "actor": {"role": role, "node": node, "session": None},
              "type": type_, "data": data}
        self.events.append(ev)
        return seq

    def plan_set(self, plan):
        self.rev += 1
        fps = {n["id"]: state.fingerprint(n) for n in plan["nodes"]}
        self.add("plan.set", {"revision": self.rev, "plan_sha256": "0" * 64,
                              "fingerprints": fps, "constraints_applied": []})
        return plan

    def assign(self, node, family="claude", isolation="worktree"):
        return self.add("node.assign", {"node": node, "executor": "t3", "model": "m",
                                        "effort": "medium", "provider": "p", "family": family,
                                        "isolation": isolation})

    def start(self, node, attempt, rev="base0"):
        return self.add("node.start", {"node": node, "attempt": attempt,
                                       "base": {"rev": rev, "dirty": {}}, "cwd": "/w"},
                        "worker", node)

    def result(self, node, check, attempt, phase="loop", result="passed", type_="cmd", **extra):
        d = {"node": node, "check": check, "type": type_, "grade": 1, "result": result,
             "attempt": attempt, "phase": phase, "exit_code": 0 if result == "passed" else 1,
             "timed_out": False, "command": "true", "cwd": "/w", "duration_ms": 5, "log": "l"}
        d.update(extra)
        self.add("check.result", d)
        return d

    def submit(self, node, attempt, commit="c1"):
        return self.add("node.submit", {"node": node, "attempt": attempt, "commit": commit,
                                        "branch": "b", "changed_files": [node + ".py"],
                                        "notes": "", "low_confidence": []}, "worker", node)

    def review(self, node, attempt, target, target_submission, verdict="pass", findings=()):
        return self.add("review.submit", {"node": node, "attempt": attempt, "target": target,
                                          "target_submission": target_submission,
                                          "verdict": verdict, "findings": list(findings)},
                        "reviewer", node)

    def verdict(self, node, attempt, verdict, submission=None, rejection=None, rule="R1"):
        return self.add("gate.verdict", {"node": node, "attempt": attempt,
                                         "submission": submission, "verdict": verdict,
                                         "rule": rule, "rejection": rejection,
                                         "tested_head": "h"})

    def merge(self, merged=(), conflicted=()):
        return self.add("merge.result", {"merged": list(merged), "conflicted": list(conflicted)})

    def final(self, result="passed"):
        return self.add("gate.final", {"result": result, "failed_checks": [], "tested_head": "h"})

    def reopen(self, node):
        return self.add("node.reopen", {"node": node, "reason": "why"})

    def ask(self, node=None, submission=None, purpose="free", kind="review", check=None,
            did=None):
        d = {"node": node, "submission": submission, "check": check, "purpose": purpose,
             "kind": kind, "question": "q?",
             "evidence": {"command": None, "files": [], "checks": []}}
        if did is not None:
            d["id"] = did
        seq = len(self.events) + 1
        if "id" not in d:
            d["id"] = "d%d" % seq
        self.add("decision.ask", d)
        return seq

    def answer(self, did, outcome="approved", answer="ok", sig=None, run=None):
        if sig is None:
            sig = core.human_sig(run or self.run, did, outcome, answer) or "x"
        return self.add("decision.answer", {"id": did, "outcome": outcome, "answer": answer,
                                            "source": "dashboard", "sig": sig}, "human")


def derive(log, plan):
    return state.derive(plan, log.events)


def rejection(unit, attempt):
    return {"unit": unit, "attempt": attempt, "max_attempts": 3, "verdict": "red",
            "reason": "check unit exited 1", "evidence": {"log": "l", "tail": []},
            "scope": [unit + ".py"]}


class FingerprintTests(unittest.TestCase):
    def test_matches_section_3(self):
        n = work("a", goal="ünï")
        text = json.dumps(n, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        self.assertEqual(state.fingerprint(n), hashlib.sha256(text.encode("utf-8")).hexdigest())
        self.assertEqual(state.fingerprint(dict(reversed(list(n.items())))),
                         state.fingerprint(n))

    def revision_fixture(self, p=None):
        p, _ = planmod.normalize(p or plan_of(work("a", outputs=["a"]), work("b", ["a"], checks=[
            {"id": "unit", "type": "cmd", "run": "true"}, {"id": "human", "type": "human"}]),
                                            work("x"), review("v", "a"), decision("d", ["a"])))
        log = Log()
        log.plan_set(p)
        for nid in ("a", "b", "x", "v"):
            log.assign(nid)
            log.start(nid, 1)
            if nid == "x":
                continue
            sid = log.submit(nid, 1)
            if nid == "a":
                log.verdict("a", 1, "pass", submission=sid)
        return log, p

    def test_presentation_revisions_preserve_every_node_state_in_both_directions(self):
        _, bare = self.revision_fixture()
        presented = copy.deepcopy(bare)
        presented["title"] = "사람이 읽는 작업 흐름"
        for node in presented["nodes"]:
            node.update(title="작업 제목", summary="사용자를 위한 결과를 만듭니다",
                        context={"why": "결정이 필요한 이유"})
            for need in node["needs"]:
                need["label"] = "전달할 결과"
            for check in node["checks"]:
                check.update(title="결과가 요구를 충족하는지 확인",
                             context={"undo": "다시 검토할 수 있습니다"})
        for first, second in ((bare, presented), (presented, bare)):
            with self.subTest(add_fields=first is bare):
                # Use normalized revisions and the exact per-node hash map used by cli.py.
                log, _ = self.revision_fixture(first)
                before = state.derive(first, log.events)["nodes"]
                original = copy.deepcopy(second)
                log.plan_set(planmod.normalize(second)[0])
                self.assertEqual(before, state.derive(second, log.events)["nodes"])
                self.assertEqual(second, original)

    def test_behavioral_revisions_still_invalidate_node_and_dependents(self):
        for field in ("goal", "run", "artifact", "check_extension", "need_extension", "extension"):
            with self.subTest(field=field):
                log, first = self.revision_fixture()
                second = copy.deepcopy(first)
                node = second["nodes"][0]
                if field == "run":
                    node["checks"][0]["run"] = "false"
                elif field == "check_extension":
                    node["checks"][0]["extension"] = {"title": "behavior"}
                elif field in ("artifact", "need_extension"):
                    node = second["nodes"][1]
                    node["needs"][0][field if field == "artifact" else "extension"] = "changed"
                else:
                    node[field] = "changed"
                before = state.derive(first, log.events)["nodes"]
                log.plan_set(planmod.normalize(second)[0])
                after = state.derive(second, log.events)["nodes"]
                changed = {"b"} if field in ("artifact", "need_extension") else {"a", "b", "v", "d"}
                for nid in after:
                    if nid in changed:
                        self.assertEqual(after[nid]["basis"], log.events[-1]["seq"])
                        self.assertIsNone(after[nid]["submission"])
                        self.assertEqual(after[nid]["attempts"], 0)
                    else:
                        self.assertEqual(before[nid], after[nid])


class ShapeTests(EnvCase):
    def test_plan_none(self):
        log = Log()
        log.add("host.set", {"capabilities": ["t3_delegate"]})
        s = state.derive(None, log.events)
        self.assertEqual(s["nodes"], {})
        self.assertEqual(s["decisions"], {})
        self.assertEqual(s["run"], {"id": RUN, "plan_revision": 0, "plan_identity": None, "status": "open", "approval_required": False,
                                 "human_key_sha256": None, "key_mismatch": False, "plan_error": False,
                                    "host": ["t3_delegate"], "final": None})

    def test_empty_events(self):
        s = state.derive(None, [])
        self.assertEqual(s, {"run": {"id": None, "plan_revision": 0, "plan_identity": None, "status": "open", "approval_required": False,
                                 "human_key_sha256": None, "key_mismatch": False, "plan_error": False,
                                     "host": [], "final": None},
                             "nodes": {}, "decisions": {}})

    def test_defaults_for_all_three_kinds(self):
        log = Log()
        p = log.plan_set(plan_of(work("a", lane=2), review("v", "a"), decision("d", ["a"])))
        s = derive(log, p)
        self.assertEqual(s["run"]["plan_revision"], 1)
        common = {"status": "pending", "basis": 0, "attempts": 0, "max_attempts": 3,
                  "assignment": None, "base": None, "submission": None, "red": {},
                  "reviews": [], "rejections": [], "verdict": None, "merged_head": None,
                  "trajectory_clean": True, "open_decisions": []}
        self.assertEqual(s["nodes"]["a"], dict(
            common, kind="work", lane=2, effective_lane=2,
            checks={"unit": {"loop": None, "gate": None}, "scope": {"loop": None, "gate": None}}))
        self.assertEqual(s["nodes"]["v"], dict(
            common, kind="review", lane=1, effective_lane=1,
            checks={"cites": {"loop": None, "gate": None}}))
        self.assertEqual(s["nodes"]["d"], dict(
            common, kind="decision", lane=3, effective_lane=3, checks={}))
        for n in s["nodes"].values():
            self.assertEqual(set(n), ALL_KEYS)

    def test_every_key_after_activity(self):
        log = Log()
        p = log.plan_set(plan_of(work("a", lane=2), review("v", "a"), decision("d", ["a"])))
        log.assign("a")
        log.start("a", 1)
        log.submit("a", 1)
        log.verdict("d", 0, "needs_approval")
        s = derive(log, p)
        for n in s["nodes"].values():
            self.assertEqual(set(n), ALL_KEYS)

    def test_effective_lane_and_max_attempts_defaults(self):
        n = work("a", lane=2)
        del n["effective_lane"]
        del n["max_attempts"]
        log = Log()
        p = log.plan_set(plan_of(n))
        a = derive(log, p)["nodes"]["a"]
        self.assertEqual((a["effective_lane"], a["max_attempts"]), (2, 3))

    def test_nodes_in_plan_order(self):
        log = Log()
        p = log.plan_set(plan_of(work("b"), work("a"), decision("z", ["a"])))
        self.assertEqual(list(derive(log, p)["nodes"]), ["b", "a", "z"])

    def test_inputs_not_mutated_and_output_not_aliased(self):
        log = Log()
        p = log.plan_set(plan_of(work("a")))
        log.start("a", 1)
        log.result("a", "unit", 1)
        sid = log.submit("a", 1)
        log.verdict("a", 1, "reject", submission=sid, rejection=rejection("a", 1))
        log.ask("a", sid)
        log.final("failed")
        before_p, before_e = copy.deepcopy(p), copy.deepcopy(log.events)
        s = derive(log, p)
        self.assertEqual(p, before_p)
        self.assertEqual(log.events, before_e)
        a = s["nodes"]["a"]
        a["checks"]["unit"]["loop"]["result"] = "failed"
        a["submission"]["changed_files"].append("x")
        a["base"]["dirty"]["x"] = "y"
        a["verdict"]["rule"] = "zz"
        a["rejections"][0]["reason"] = "zz"
        s["run"]["final"]["result"] = "zz"
        next(iter(s["decisions"].values()))["evidence"]["files"].append("x")
        self.assertEqual(log.events, before_e)
        self.assertEqual(derive(log, p), state.derive(p, before_e))

    def test_deterministic(self):
        log = Log()
        p = log.plan_set(plan_of(work("a"), review("v", "a")))
        log.start("a", 1)
        log.submit("a", 1)
        self.assertEqual(derive(log, p), derive(log, p))


class StatusTests(EnvCase):
    """Points 1, 5, 6, 8: statuses and how each event sets them."""

    def test_status_table(self):
        for verdict, status in [("pass", "passed"), ("reject", "rejected"),
                                ("unverified", "unverified"), ("hold", "held"),
                                ("needs_approval", "awaiting_approval"), ("replan", "replan")]:
            with self.subTest(verdict=verdict):
                log = Log()
                p = log.plan_set(plan_of(work("a")))
                log.start("a", 1)
                sid = log.submit("a", 1)
                log.verdict("a", 1, verdict, submission=sid)
                self.assertEqual(derive(log, p)["nodes"]["a"]["status"], status)

    def test_lifecycle_never_stale(self):
        log = Log()
        p = log.plan_set(plan_of(work("a"), work("b", ["a"])))
        seen = []

        def snap():
            seen.append(derive(log, p)["nodes"]["a"]["status"])

        snap()
        log.assign("a")
        snap()
        log.start("a", 1)
        snap()
        sid = log.submit("a", 1)
        snap()
        log.verdict("a", 1, "pass", submission=sid)
        snap()
        log.reopen("a")
        snap()
        self.assertEqual(seen, ["pending", "assigned", "running", "submitted", "passed",
                                "assigned"])
        allowed = {"pending", "assigned", "running", "submitted", "passed", "rejected",
                   "unverified", "held", "awaiting_approval", "replan"}
        for n in derive(log, p)["nodes"].values():
            self.assertIn(n["status"], allowed)

    def test_assign_only_from_pending_changes_status(self):
        log = Log()
        p = log.plan_set(plan_of(work("a")))
        log.assign("a", family="claude")
        log.start("a", 1)
        sid = log.submit("a", 1)
        log.verdict("a", 1, "reject", submission=sid)
        log.assign("a", family="openai", isolation="shared")
        a = derive(log, p)["nodes"]["a"]
        self.assertEqual(a["status"], "rejected")
        self.assertEqual(a["assignment"], {"executor": "t3", "model": "m", "effort": "medium",
                                           "provider": "p", "family": "openai",
                                           "isolation": "shared"})

    def test_assign_while_assigned_replaces_assignment(self):
        log = Log()
        p = log.plan_set(plan_of(work("a")))
        log.assign("a", family="claude")
        log.assign("a", family="other")
        a = derive(log, p)["nodes"]["a"]
        self.assertEqual((a["status"], a["assignment"]["family"]), ("assigned", "other"))

    def test_start_sets_running_and_clears(self):
        log = Log()
        p = log.plan_set(plan_of(work("a")))
        log.start("a", 1, rev="r1")
        sid = log.submit("a", 1, commit="c1")
        log.merge([{"node": "a", "commit": "c1", "head": "h1"}])
        log.verdict("a", 1, "reject", submission=sid, rejection=rejection("a", 1))
        before = derive(log, p)["nodes"]["a"]
        self.assertEqual(before["merged_head"], "h1")
        self.assertIsNotNone(before["verdict"])
        log.start("a", 2, rev="r2")
        a = derive(log, p)["nodes"]["a"]
        self.assertEqual(a["status"], "running")
        self.assertEqual(a["attempts"], 2)
        self.assertEqual(a["base"], {"rev": "r2", "dirty": {}})
        self.assertIsNone(a["submission"])
        self.assertIsNone(a["verdict"])
        self.assertIsNone(a["merged_head"])
        self.assertEqual(len(a["rejections"]), 1)


class SubmissionTests(EnvCase):
    """Point 3: submission ids and shapes."""

    def test_node_submit_id_is_seq(self):
        log = Log()
        p = log.plan_set(plan_of(work("a")))
        log.start("a", 1)
        sid = log.submit("a", 1, commit="abc")
        self.assertEqual(derive(log, p)["nodes"]["a"]["submission"], {
            "id": sid, "attempt": 1, "commit": "abc", "branch": "b",
            "changed_files": ["a.py"], "notes": "", "low_confidence": []})

    def test_review_submit_shape(self):
        log = Log()
        p = log.plan_set(plan_of(work("a", lane=2), review("v", "a")))
        log.start("a", 1)
        ws = log.submit("a", 1)
        log.start("v", 1)
        f = [{"severity": "low", "file": "a.py", "line": 1, "text": "t"}]
        vs = log.review("v", 1, "a", ws, verdict="fail", findings=f)
        v = derive(log, p)["nodes"]["v"]
        self.assertEqual(v["status"], "submitted")
        self.assertEqual(v["submission"], {"id": vs, "attempt": 1, "target": "a",
                                           "target_submission": ws, "verdict": "fail",
                                           "findings": f})


class ChecksTests(EnvCase):
    """Point 7."""

    def test_latest_per_phase_of_current_attempt(self):
        log = Log()
        p = log.plan_set(plan_of(work("a")))
        log.start("a", 1)
        log.result("a", "unit", 1, result="failed")
        log.start("a", 2)
        self.assertEqual(derive(log, p)["nodes"]["a"]["checks"]["unit"],
                         {"loop": None, "gate": None})
        log.result("a", "unit", 1, result="passed")  # late result of attempt 1: ignored
        log.result("a", "unit", 2, result="failed")
        last = log.result("a", "unit", 2, result="passed")
        gate = log.result("a", "unit", 2, phase="gate")
        c = derive(log, p)["nodes"]["a"]["checks"]
        self.assertEqual(c["unit"], {"loop": last, "gate": gate})
        self.assertEqual(c["scope"], {"loop": None, "gate": None})

    def test_result_only_check_id_included(self):
        log = Log()
        p = log.plan_set(plan_of(work("a")))
        log.start("a", 1)
        r = log.result("a", "all-tests", 1, phase="gate")
        self.assertEqual(derive(log, p)["nodes"]["a"]["checks"]["all-tests"],
                         {"loop": None, "gate": r})

    def test_red_kept(self):
        log = Log()
        p = log.plan_set(plan_of(work("a")))
        log.start("a", 1)
        log.add("check.red", {"node": "a", "check": "unit", "exit_code": 1,
                              "failed_first": True, "log": "l"})
        self.assertTrue(derive(log, p)["nodes"]["a"]["red"]["unit"]["failed_first"])


class VerdictTests(EnvCase):
    """Point 8."""

    def test_verdict_bound_to_current_submission(self):
        log = Log()
        p = log.plan_set(plan_of(work("a")))
        log.start("a", 1)
        sid = log.submit("a", 1)
        log.verdict("a", 1, "unverified", submission=sid, rule="R3")
        v = derive(log, p)["nodes"]["a"]["verdict"]
        self.assertEqual((v["verdict"], v["submission"]), ("unverified", sid))
        log.verdict("a", 1, "hold", submission=sid + 999, rule="R4")
        a = derive(log, p)["nodes"]["a"]
        self.assertEqual(a["status"], "held")
        self.assertEqual(a["verdict"]["verdict"], "unverified")

    def test_no_verdict_without_submission(self):
        log = Log()
        p = log.plan_set(plan_of(work("a")))
        log.start("a", 1)
        log.verdict("a", 1, "replan", submission=None, rule="R2")
        a = derive(log, p)["nodes"]["a"]
        self.assertEqual((a["status"], a["verdict"]), ("replan", None))

    def test_rejections_reject_and_replan_non_null_in_order(self):
        log = Log()
        p = log.plan_set(plan_of(work("a")))
        log.start("a", 1)
        s1 = log.submit("a", 1)
        log.verdict("a", 1, "reject", submission=s1, rejection=rejection("a", 1))
        log.start("a", 2)
        s2 = log.submit("a", 2)
        log.verdict("a", 2, "hold", submission=s2, rejection={"unit": "ignored"})
        log.verdict("a", 2, "reject", submission=s2, rejection=None, rule="M1")
        log.verdict("a", 2, "replan", submission=s2, rejection=rejection("a", 2), rule="R2")
        self.assertEqual(derive(log, p)["nodes"]["a"]["rejections"],
                         [rejection("a", 1), rejection("a", 2)])

    def test_rejections_since_basis(self):
        log = Log()
        p = log.plan_set(plan_of(work("a")))
        log.start("a", 1)
        s1 = log.submit("a", 1)
        log.verdict("a", 1, "reject", submission=s1, rejection=rejection("a", 1))
        log.reopen("a")
        self.assertEqual(derive(log, p)["nodes"]["a"]["rejections"], [])

    def test_decision_node_verdict_since_basis(self):
        log = Log()
        p = log.plan_set(plan_of(work("a"), decision("d", ["a"])))
        log.verdict("d", 0, "needs_approval", rule="R6")
        log.verdict("d", 0, "pass", rule="R7")
        d = derive(log, p)["nodes"]["d"]
        self.assertEqual((d["status"], d["verdict"]["verdict"]), ("passed", "pass"))
        log.reopen("a")
        d = derive(log, p)["nodes"]["d"]
        self.assertEqual((d["status"], d["verdict"]), ("pending", None))


class MergeTests(EnvCase):
    """Point 9."""

    def test_merged_head_for_current_commit(self):
        log = Log()
        p = log.plan_set(plan_of(work("a"), work("b")))
        log.start("a", 1)
        log.submit("a", 1, commit="c1")
        log.merge([{"node": "a", "commit": "c1", "head": "h1"},
                   {"node": "b", "commit": "c1", "head": "hb"}])
        log.merge([{"node": "a", "commit": "other", "head": "h2"}])
        s = derive(log, p)
        self.assertEqual(s["nodes"]["a"]["merged_head"], "h1")
        self.assertIsNone(s["nodes"]["b"]["merged_head"])
        log.merge([{"node": "a", "commit": "c1", "head": "h3"}])
        self.assertEqual(derive(log, p)["nodes"]["a"]["merged_head"], "h3")

    def test_uncommitted_submission_never_merged(self):
        log = Log()
        p = log.plan_set(plan_of(work("a")))
        log.start("a", 1)
        log.submit("a", 1, commit=None)
        log.merge([{"node": "a", "commit": None, "head": "h1"}])
        self.assertIsNone(derive(log, p)["nodes"]["a"]["merged_head"])


class ReviewsTests(EnvCase):
    """Point 10."""

    def plan(self):
        return plan_of(work("a", lane=2), review("v1", "a"), review("v2", "a"),
                       review("v3", "a"), decision("d", ["a"]))

    def test_listed_statuses_and_fields(self):
        log = Log()
        p = log.plan_set(self.plan())
        log.start("a", 1)
        log.assign("v1", family="openai")  # after the target's start (point 2c)
        s1 = log.submit("a", 1)
        log.start("v1", 1)
        r1 = log.review("v1", 1, "a", s1, verdict="fail",
                        findings=[{"severity": "high", "file": "a.py", "line": 2, "text": "x"}])
        log.start("v2", 1)
        log.review("v2", 1, "a", s1 + 1000)  # not filtered by target_submission
        log.start("v3", 1)  # running: not listed
        s = derive(log, p)
        self.assertEqual(s["nodes"]["a"]["reviews"], [
            {"node": "v1", "status": "submitted", "target_submission": s1, "verdict": "fail",
             "findings": [{"severity": "high", "file": "a.py", "line": 2, "text": "x"}],
             "family": "openai"},
            {"node": "v2", "status": "submitted", "target_submission": s1 + 1000,
             "verdict": "pass", "findings": [], "family": None},
        ])
        for nid in ("v1", "v2", "v3", "d"):
            self.assertEqual(s["nodes"][nid]["reviews"], [])
        self.assertEqual(r1, s["nodes"]["v1"]["submission"]["id"])

    def test_each_listed_status(self):
        for verdict, status in [("unverified", "unverified"), ("hold", "held"),
                                ("needs_approval", "awaiting_approval"), ("pass", "passed")]:
            with self.subTest(verdict=verdict):
                log = Log()
                p = log.plan_set(self.plan())
                log.start("a", 1)
                s1 = log.submit("a", 1)
                log.start("v1", 1)
                vs = log.review("v1", 1, "a", s1)
                log.verdict("v1", 1, verdict, submission=vs)
                self.assertEqual([r["status"] for r in derive(log, p)["nodes"]["a"]["reviews"]],
                                 [status])

    def test_rejected_and_replan_reviews_not_listed(self):
        for verdict in ("reject", "replan"):
            with self.subTest(verdict=verdict):
                log = Log()
                p = log.plan_set(self.plan())
                log.start("a", 1)
                s1 = log.submit("a", 1)
                log.start("v1", 1)
                vs = log.review("v1", 1, "a", s1)
                log.verdict("v1", 1, verdict, submission=vs)
                self.assertEqual(derive(log, p)["nodes"]["a"]["reviews"], [])


class DecisionTests(EnvCase):
    """Point 11."""

    def test_record_shape_and_id(self):
        log = Log()
        p = log.plan_set(plan_of(work("a")))
        seq = log.ask("a", None, purpose="node", kind="direction", check="unit")
        s = derive(log, p)
        did = "d%d" % seq
        self.assertEqual(s["decisions"], {did: {
            "id": did, "seq": seq, "node": "a", "submission": None, "check": "unit",
            "purpose": "node", "plan_identity": None, "kind": "direction", "question": "q?",
            "evidence": {"command": None, "files": [], "checks": []}, "status": "open",
            "outcome": None, "answer": None, "source": None, "verified": False,
            "stale": False}})
        self.assertEqual(set(s["decisions"][did]), DECISION_KEYS)
        self.assertEqual(s["nodes"]["a"]["open_decisions"], [did])

    def test_id_from_seq_when_data_has_none(self):
        log = Log()
        p = log.plan_set(plan_of(work("a")))
        seq = log.add("decision.ask", {"node": None, "submission": None, "check": None,
                                       "purpose": "free", "kind": "information",
                                       "question": "q", "evidence": {}})
        self.assertIn("d%d" % seq, derive(log, p)["decisions"])

    def test_data_id_used_when_present(self):
        log = Log()
        p = log.plan_set(plan_of(work("a")))
        log.ask(None, did="d77")
        self.assertEqual(list(derive(log, p)["decisions"]), ["d77"])

    def test_first_answer_wins_and_verified(self):
        self.write_key()
        log = Log()
        p = log.plan_set(plan_of(work("a")))
        did = "d%d" % log.ask("a")
        log.answer(did, outcome="approved", answer="yes")
        log.answer(did, outcome="rejected", answer="no")
        dec = derive(log, p)["decisions"][did]
        self.assertEqual((dec["status"], dec["outcome"], dec["answer"], dec["source"],
                          dec["verified"]), ("answered", "approved", "yes", "dashboard", True))
        self.assertEqual(derive(log, p)["nodes"]["a"]["open_decisions"], [])

    def test_first_answer_wins_even_if_unverified(self):
        self.write_key()
        log = Log()
        p = log.plan_set(plan_of(work("a")))
        did = "d%d" % log.ask("a")
        log.answer(did, sig="forged")
        log.answer(did)
        self.assertFalse(derive(log, p)["decisions"][did]["verified"])

    def test_unverified_cases(self):
        log = Log()
        p = log.plan_set(plan_of(work("a")))
        no_key = "d%d" % log.ask("a")
        log.answer(no_key, sig="x")
        self.assertFalse(derive(log, p)["decisions"][no_key]["verified"])
        self.write_key()
        other_run = "d%d" % log.ask("a")
        log.answer(other_run, run="other")
        bad = "d%d" % log.ask("a")
        log.answer(bad, sig="0" * 64)
        none_sig = "d%d" % log.ask("a")
        log.add("decision.answer", {"id": none_sig, "outcome": "approved", "answer": "ok",
                                    "source": "terminal", "sig": None})
        good = "d%d" % log.ask("a")
        log.answer(good)
        dec = derive(log, p)["decisions"]
        self.assertFalse(dec[no_key]["verified"])
        self.assertFalse(dec[other_run]["verified"])
        self.assertFalse(dec[bad]["verified"])
        self.assertFalse(dec[none_sig]["verified"])
        self.assertTrue(dec[good]["verified"])

    def test_answer_to_unknown_id_ignored(self):
        log = Log()
        p = log.plan_set(plan_of(work("a")))
        log.answer("d999")
        self.assertEqual(derive(log, p)["decisions"], {})

    def test_stale_when_basis_reaches_ask(self):
        log = Log()
        p = log.plan_set(plan_of(work("a"), work("b", ["a"])))
        did = "d%d" % log.ask("b")
        log.reopen("a")
        later = "d%d" % log.ask("b")
        s = derive(log, p)
        self.assertTrue(s["decisions"][did]["stale"])
        self.assertFalse(s["decisions"][later]["stale"])
        self.assertEqual(s["nodes"]["b"]["open_decisions"], [later])

    def test_stale_when_submission_not_current(self):
        log = Log()
        p = log.plan_set(plan_of(work("a")))
        log.start("a", 1)
        s1 = log.submit("a", 1)
        bound = "d%d" % log.ask("a", s1)
        wrong = "d%d" % log.ask("a", s1 + 500)
        s = derive(log, p)
        self.assertFalse(s["decisions"][bound]["stale"])
        self.assertTrue(s["decisions"][wrong]["stale"])
        log.verdict("a", 1, "reject", submission=s1)
        self.assertFalse(derive(log, p)["decisions"][bound]["stale"])
        log.start("a", 2)  # no current submission: id is null
        self.assertTrue(derive(log, p)["decisions"][bound]["stale"])
        s2 = log.submit("a", 2)
        self.assertTrue(derive(log, p)["decisions"][bound]["stale"])
        self.assertNotEqual(s1, s2)

    def test_node_outside_plan_kept_and_stale(self):
        log = Log()
        p = log.plan_set(plan_of(work("a")))
        did = "d%d" % log.ask("ghost")
        free = "d%d" % log.ask(None)
        s = derive(log, p)
        self.assertTrue(s["decisions"][did]["stale"])
        self.assertFalse(s["decisions"][free]["stale"])
        self.assertTrue(state.derive(None, log.events)["decisions"][did]["stale"])

    def test_open_decisions_only_open_non_stale_bound(self):
        self.write_key()
        log = Log()
        p = log.plan_set(plan_of(work("a"), work("b")))
        log.start("a", 1)
        s1 = log.submit("a", 1)
        open_ = "d%d" % log.ask("a", s1)
        answered = "d%d" % log.ask("a", s1)
        log.answer(answered)
        log.ask("a", s1 + 1)  # stale
        log.ask("b")
        log.ask(None)
        self.assertEqual(derive(log, p)["nodes"]["a"]["open_decisions"], [open_])


class TrajectoryTests(EnvCase):
    """Point 12."""

    def test_clean_by_default_and_through_attempt_two(self):
        log = Log()
        p = log.plan_set(plan_of(work("a")))
        log.start("a", 1)
        log.start("a", 2)
        self.assertTrue(derive(log, p)["nodes"]["a"]["trajectory_clean"])
        log.start("a", 3)
        self.assertFalse(derive(log, p)["nodes"]["a"]["trajectory_clean"])

    def test_timeout_in_current_attempt(self):
        log = Log()
        p = log.plan_set(plan_of(work("a")))
        log.start("a", 1)
        log.result("a", "unit", 1, phase="gate", result="failed", timed_out=True)
        self.assertFalse(derive(log, p)["nodes"]["a"]["trajectory_clean"])
        log.start("a", 2)
        self.assertTrue(derive(log, p)["nodes"]["a"]["trajectory_clean"])

    def test_loop_scope_violations(self):
        log = Log()
        p = log.plan_set(plan_of(work("a")))
        log.start("a", 1)
        log.result("a", "scope", 1, phase="gate", type_="scope", result="failed",
                   violations=["x.py"])
        self.assertTrue(derive(log, p)["nodes"]["a"]["trajectory_clean"])
        log.result("a", "scope", 1, phase="loop", type_="scope", violations=[])
        self.assertTrue(derive(log, p)["nodes"]["a"]["trajectory_clean"])
        log.result("a", "scope", 1, phase="loop", type_="scope", result="failed",
                   violations=["x.py"])
        self.assertFalse(derive(log, p)["nodes"]["a"]["trajectory_clean"])


class RunTests(EnvCase):
    """Point 13."""

    def passed_run(self):
        log = Log()
        p = log.plan_set(plan_of(work("a")))
        log.start("a", 1)
        sid = log.submit("a", 1)
        log.verdict("a", 1, "pass", submission=sid, rule="R7")
        return log, p

    def test_plan_revision_and_host(self):
        log = Log()
        p = log.plan_set(plan_of(work("a")))
        log.plan_set(p)
        log.add("host.set", {"capabilities": ["workflow"]})
        log.add("host.set", {"capabilities": ["xcode_mcp"]})
        r = derive(log, p)["run"]
        self.assertEqual((r["plan_revision"], r["host"]), (2, ["xcode_mcp"]))

    def test_run_id_from_event_without_run_init(self):
        log = Log(run="other", init=False)
        log.add("host.set", {"capabilities": []})
        self.assertEqual(state.derive(None, log.events)["run"]["id"], "other")

    def test_complete(self):
        log, p = self.passed_run()
        log.final("failed")
        fseq = log.final("passed")
        r = derive(log, p)["run"]
        self.assertEqual(r["status"], "complete")
        self.assertEqual(r["final"], {"result": "passed", "failed_checks": [],
                                      "tested_head": "h", "seq": fseq})

    def test_open_when_last_final_failed(self):
        log, p = self.passed_run()
        log.final("passed")
        log.final("failed")
        self.assertEqual(derive(log, p)["run"]["status"], "open")

    def test_open_without_final(self):
        log, p = self.passed_run()
        self.assertEqual(derive(log, p)["run"]["status"], "open")

    def test_open_when_verdict_like_event_after_final(self):
        for later in ("verdict", "reopen_other", "plan_set"):
            with self.subTest(later=later):
                log, p = self.passed_run()
                log.final("passed")
                if later == "verdict":
                    sid = derive(log, p)["nodes"]["a"]["submission"]["id"]
                    log.verdict("a", 1, "pass", submission=sid, rule="R7")
                elif later == "reopen_other":
                    log.reopen("ghost")
                else:
                    log.plan_set(p)
                s = derive(log, p)
                self.assertEqual(s["nodes"]["a"]["status"], "passed")
                self.assertEqual(s["run"]["status"], "open")

    def test_open_when_a_node_not_passed(self):
        log = Log()
        p = log.plan_set(plan_of(work("a"), work("b")))
        log.start("a", 1)
        sid = log.submit("a", 1)
        log.verdict("a", 1, "pass", submission=sid)
        log.final("passed")
        self.assertEqual(derive(log, p)["run"]["status"], "open")

    def test_open_with_empty_plan(self):
        log = Log()
        p = log.plan_set({"schema_version": 1, "goal": "x", "nodes": []})
        log.final("passed")
        self.assertEqual(derive(log, p)["run"]["status"], "open")
        self.assertEqual(state.derive(None, log.events)["run"]["status"], "open")


class BasisTests(EnvCase):
    """Point 2."""

    def test_plan_set_change_invalidates_node_and_dependents(self):
        a, b, c, x = work("a"), work("b", ["a"]), work("c", ["b"]), work("x")
        log = Log()
        log.plan_set(plan_of(a, b, c, x))
        for nid in ("a", "b", "c", "x"):
            log.assign(nid)
            log.start(nid, 1)
        b2 = work("b", ["a"], goal="changed")
        p2 = log.plan_set(plan_of(a, b2, c, x))
        seq = log.events[-1]["seq"]
        s = derive(log, p2)["nodes"]
        self.assertEqual({n: (s[n]["status"], s[n]["basis"], s[n]["attempts"])
                          for n in s},
                         {"a": ("running", 0, 1), "b": ("assigned", seq, 0),
                          "c": ("assigned", seq, 0), "x": ("running", 0, 1)})
        self.assertIsNotNone(s["b"]["assignment"])
        self.assertIsNone(s["b"]["base"])

    def test_unchanged_plan_set_invalidates_nothing(self):
        log = Log()
        p = log.plan_set(plan_of(work("a")))
        log.start("a", 1)
        log.plan_set(p)
        a = derive(log, p)["nodes"]["a"]
        self.assertEqual((a["status"], a["basis"]), ("running", 0))

    def test_first_appearance_is_not_invalidation(self):
        log = Log()
        log.plan_set(plan_of(work("a")))
        log.start("a", 1)
        p2 = log.plan_set(plan_of(work("a"), work("n", ["a"])))
        s = derive(log, p2)["nodes"]
        self.assertEqual((s["a"]["basis"], s["n"]["basis"]), (0, 0))
        self.assertEqual(s["a"]["status"], "running")

    def test_removed_and_readded_is_invalidated(self):
        log = Log()
        p1 = log.plan_set(plan_of(work("a"), work("n")))
        log.start("n", 1)
        log.plan_set(plan_of(work("a")))
        log.plan_set(p1)
        seq = log.events[-1]["seq"]
        n = derive(log, p1)["nodes"]["n"]
        self.assertEqual((n["status"], n["basis"], n["attempts"]), ("pending", seq, 0))
        self.assertEqual(derive(log, p1)["nodes"]["a"]["basis"], 0)

    def test_removed_node_disappears(self):
        log = Log()
        log.plan_set(plan_of(work("a"), work("n")))
        p2 = log.plan_set(plan_of(work("a")))
        self.assertEqual(list(derive(log, p2)["nodes"]), ["a"])

    def test_dependencies_from_current_plan(self):
        # Only a's fingerprint changes; whether b is invalidated depends on the
        # needs in the plan handed to derive.
        log = Log()
        log.plan_set(plan_of(work("a"), work("b")))
        log.start("b", 1)
        log.plan_set(plan_of(work("a", goal="new"), work("b")))
        seq = log.events[-1]["seq"]
        dep = plan_of(work("a", goal="new"), work("b", ["a"]))
        nodep = plan_of(work("a", goal="new"), work("b"))
        self.assertEqual(derive(log, dep)["nodes"]["b"]["basis"], seq)
        self.assertEqual(derive(log, nodep)["nodes"]["b"]["basis"], 0)
        self.assertEqual(derive(log, nodep)["nodes"]["b"]["status"], "running")

    def test_review_depends_on_target_without_needs(self):
        v = review("v", "a")
        v["needs"] = []
        log = Log()
        log.plan_set(plan_of(work("a"), v))
        log.start("v", 1)
        p2 = log.plan_set(plan_of(work("a", goal="new"), v))
        self.assertEqual(derive(log, p2)["nodes"]["v"]["status"], "pending")

    def test_reopen_invalidates_node_and_dependents_only(self):
        log = Log()
        p = log.plan_set(plan_of(work("a"), work("b", ["a"]), work("x")))
        for nid in ("a", "b", "x"):
            log.start(nid, 1)
        seq = log.reopen("b")
        s = derive(log, p)["nodes"]
        self.assertEqual((s["a"]["basis"], s["b"]["basis"], s["x"]["basis"]), (0, seq, 0))
        self.assertEqual(s["b"]["status"], "pending")

    def test_events_at_or_before_basis_ignored(self):
        log = Log()
        p = log.plan_set(plan_of(work("a")))
        log.assign("a")
        log.add("check.red", {"node": "a", "check": "unit", "exit_code": 1,
                              "failed_first": True, "log": "l"})
        log.start("a", 1)
        log.result("a", "unit", 1)
        sid = log.submit("a", 1)
        log.verdict("a", 1, "pass", submission=sid)
        log.reopen("a")
        a = derive(log, p)["nodes"]["a"]
        self.assertEqual(
            {k: a[k] for k in ("status", "attempts", "base", "submission",
                               "red", "verdict", "rejections")},
            {"status": "assigned" if a["assignment"] else "pending", "attempts": 0, "base": None,
             "submission": None, "red": {}, "verdict": None, "rejections": []})
        self.assertEqual(a["checks"]["unit"], {"loop": None, "gate": None})
        log.start("a", 1)
        a = derive(log, p)["nodes"]["a"]
        self.assertEqual((a["status"], a["attempts"]), ("running", 1))

    def test_target_start_invalidates_review_only(self):
        log = Log()
        p = log.plan_set(plan_of(work("a", lane=2), review("v", "a"), decision("d", ["v"])))
        log.start("a", 1)
        s1 = log.submit("a", 1)
        log.start("v", 1)
        vs = log.review("v", 1, "a", s1)
        log.verdict("v", 1, "pass", submission=vs)
        log.verdict("d", 0, "pass", rule="R7")
        seq = log.start("a", 2)
        s = derive(log, p)["nodes"]
        self.assertEqual((s["v"]["status"], s["v"]["basis"], s["v"]["attempts"]),
                         ("pending", seq, 0))
        self.assertEqual((s["d"]["status"], s["d"]["basis"]), ("passed", 0))
        self.assertEqual(s["a"]["basis"], 0)

    def test_target_start_keeps_earlier_review_assignment(self):
        log = Log()
        p = log.plan_set(plan_of(work("a", lane=2), review("v", "a")))
        log.assign("v", family="openai")
        start_seq = log.start("a", 1)
        v = derive(log, p)["nodes"]["v"]
        self.assertEqual(
            (v["status"], v["assignment"]["family"], v["attempts"], v["basis"]),
            ("assigned", "openai", 0, start_seq))

    def test_review_start_does_not_invalidate_target(self):
        log = Log()
        p = log.plan_set(plan_of(work("a", lane=2), review("v", "a")))
        log.start("a", 1)
        log.submit("a", 1)
        log.start("v", 1)
        a = derive(log, p)["nodes"]["a"]
        self.assertEqual((a["status"], a["basis"]), ("submitted", 0))


class IgnoredEventsTests(EnvCase):
    """Point 14."""

    def test_unknown_types_and_outside_nodes(self):
        log = Log()
        p = log.plan_set(plan_of(work("a")))
        log.add("something.new", {"node": "a"})
        log.add("log.recovered", {"dropped_bytes": 3})
        log.add("constraint.apply", {"ids": ["c1"]})
        log.assign("ghost")
        log.start("ghost", 1)
        log.result("ghost", "unit", 1)
        log.result("_run", "all-tests", 0, phase="gate")
        log.submit("ghost", 1)
        log.review("ghost", 1, "a", 1)
        log.merge([{"node": "ghost", "commit": "c1", "head": "h"}, "junk"])
        log.verdict("ghost", 1, "pass", submission=1)
        log.reopen("ghost")
        log.add("check.red", {"node": "ghost", "check": "unit"})
        s = derive(log, p)
        self.assertEqual(list(s["nodes"]), ["a"])
        self.assertEqual(s["nodes"]["a"]["status"], "pending")
        self.assertEqual(s["nodes"]["a"]["basis"], 0)

    def test_malformed_events_tolerated(self):
        log = Log()
        p = log.plan_set(plan_of(work("a")))
        events = log.events + ["junk", None, {"type": "node.start"},
                               {"seq": 99, "type": "node.assign", "data": "x"},
                               {"seq": 100, "type": "plan.set", "data": {"fingerprints": 3}}]
        s = state.derive(p, events)
        self.assertEqual(s["nodes"]["a"]["status"], "pending")


class ScenarioTests(EnvCase):
    """S1 to S4: whole event sequences."""

    def s1(self):
        log = Log()
        p = log.plan_set(plan_of(work("W", lane=2), review("V", "W")))
        log.assign("W", family="claude")
        log.start("W", 1)
        log.assign("V", family="openai")  # after the target's start (point 2c)
        s1 = log.submit("W", 1)
        log.start("V", 1)
        vs = log.review("V", 1, "W", s1)
        log.verdict("V", 1, "pass", submission=vs, rule="R7")
        return log, p, s1

    def test_s1_review_passed(self):
        log, p, s1 = self.s1()
        s = derive(log, p)["nodes"]
        self.assertEqual(s["V"]["status"], "passed")
        self.assertEqual(s["W"]["status"], "submitted")
        self.assertEqual(s["W"]["reviews"], [
            {"node": "V", "status": "passed", "target_submission": s1, "verdict": "pass",
             "findings": [], "family": "openai"}])

    def test_s2_reject_and_restart(self):
        log, p, s1 = self.s1()
        bound = "d%d" % log.ask("W", s1, purpose="trajectory")
        unbound = "d%d" % log.ask("W", None, purpose="free", kind="direction")
        log.verdict("W", 1, "reject", submission=s1, rejection=rejection("W", 1))
        self.assertEqual(derive(log, p)["nodes"]["W"]["status"], "rejected")
        restart = log.start("W", 2)
        s = derive(log, p)
        v, w = s["nodes"]["V"], s["nodes"]["W"]
        self.assertEqual((v["status"], v["attempts"], v["basis"]),
                         ("assigned" if v["assignment"] else "pending", 0, restart))
        self.assertIsNone(v["submission"])
        self.assertEqual(w["reviews"], [])
        self.assertEqual((w["status"], w["attempts"], w["basis"]), ("running", 2, 0))
        self.assertEqual(w["rejections"], [rejection("W", 1)])
        self.assertTrue(s["decisions"][bound]["stale"])
        self.assertFalse(s["decisions"][unbound]["stale"])
        self.assertEqual(w["open_decisions"], [unbound])

    def build_pwvd(self):
        self.write_key()
        log = Log()
        p = log.plan_set(plan_of(work("P"), work("W", ["P"], lane=2), review("V", "W"),
                                 decision("D", ["W"])))
        log.assign("P")
        log.start("P", 1)
        sp = log.submit("P", 1)
        log.verdict("P", 1, "pass", submission=sp, rule="R7")
        log.assign("W", family="claude")
        log.start("W", 1)
        log.assign("V", family="openai")
        sw = log.submit("W", 1)
        log.start("V", 1)
        sv = log.review("V", 1, "W", sw)
        log.verdict("V", 1, "pass", submission=sv, rule="R7")
        log.verdict("W", 1, "pass", submission=sw, rule="R7")
        did = "d%d" % log.ask("D", None, purpose="node", kind="authorization")
        log.answer(did, outcome="approved")
        log.verdict("D", 0, "pass", rule="R7")
        s = derive(log, p)
        self.assertEqual({n: s["nodes"][n]["status"] for n in "PWVD"},
                         {n: "passed" for n in "PWVD"})
        self.assertTrue(s["decisions"][did]["verified"])
        self.assertFalse(s["decisions"][did]["stale"])
        return log, p, did

    def test_s3_reopen_root(self):
        log, p, did = self.build_pwvd()
        log.final("passed")
        self.assertEqual(derive(log, p)["run"]["status"], "complete")
        seq = log.reopen("P")
        s = derive(log, p)
        for nid in "PWVD":
            n = s["nodes"][nid]
            self.assertEqual((n["status"], n["basis"], n["attempts"]),
                             ("assigned" if n["assignment"] else "pending", seq, 0), nid)
            self.assertLess(n["attempts"], n["max_attempts"])
            self.assertIsNone(n["verdict"])
        self.assertTrue(s["decisions"][did]["stale"])
        self.assertEqual(s["run"]["status"], "open")
        log.start("P", 1)
        self.assertEqual(derive(log, p)["nodes"]["P"]["attempts"], 1)

    def test_s4_plan_change_of_one_node(self):
        log, p, did = self.build_pwvd()
        nodes = copy.deepcopy(p["nodes"])
        nodes[1]["goal"] = "rework W"
        p2 = log.plan_set(plan_of(*nodes))
        seq = log.events[-1]["seq"]
        s = derive(log, p2)
        self.assertEqual((s["nodes"]["P"]["status"], s["nodes"]["P"]["basis"]), ("passed", 0))
        for nid in "WVD":
            n = s["nodes"][nid]
            self.assertEqual((n["status"], n["basis"], n["attempts"]),
                             ("assigned" if n["assignment"] else "pending", seq, 0), nid)
        self.assertTrue(s["decisions"][did]["stale"])
        self.assertEqual(s["run"]["plan_revision"], 2)


if __name__ == "__main__":
    unittest.main()
