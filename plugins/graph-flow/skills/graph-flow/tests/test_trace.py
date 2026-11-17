"""Trajectory aggregation and real-gate rollback integration."""
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
from graphflow import checks, gate, plan, state, store, trace

from human_support import legacy_run, approve_current_plan

ACTOR = {"role": "leader", "node": None, "session": "trace-test"}


def work(nid, **updates):
    node = {"id": nid, "kind": "work", "goal": nid, "owns": [nid + ".txt"],
            "lane": 1, "grade": "scoped", "checks": [{"id": "unit", "type": "cmd", "run": "true"}]}
    node.update(updates)
    return node


class TraceTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="graphflow-trace-")
        self.addCleanup(temp.cleanup)
        self.root = pathlib.Path(temp.name).resolve()
        env = mock.patch.dict(os.environ, {"GF_HOME": str(self.root / "home")})
        env.start()
        self.addCleanup(env.stop)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.git("init", "-q")
        self.git("config", "user.name", "Trace Test")
        self.git("config", "user.email", "trace@example.invalid")
        (self.repo / "w.txt").write_text("base\n")
        self.git("add", "w.txt")
        self.git("commit", "-qm", "base")
        self.run = self.new_run("current")

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.repo)] + list(args), check=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.decode().strip()

    def new_run(self, name):
        with mock.patch.object(store, "now", return_value="2026-11-15T00:00:00Z"):
            return legacy_run(self.repo, name, ACTOR)

    def append(self, run, kind, node=None, second=0, **data):
        if node is not None:
            data["node"] = node
        with mock.patch.object(store, "now", return_value="2026-11-15T00:00:%02dZ" % second):
            with store.transaction(run) as tx:
                return tx.append(kind, data, ACTOR)

    def set_plan(self, run, nodes):
        current, _ = plan.normalize({"schema_version": 1, "goal": "trace", "nodes": nodes})
        with store.transaction(run) as tx:
            revision, sha = tx.write_plan(current)
            tx.append("plan.set", {"revision": revision, "plan_sha256": sha,
                      "fingerprints": {n["id"]: state.fingerprint(n) for n in current["nodes"]}}, ACTOR)
        approve_current_plan(run)
        return current

    def test_full_shape(self):
        self.set_plan(self.run, [work("w"), work("x")])
        self.append(self.run, "node.start", "w", 1)
        self.append(self.run, "check.result", "w", 2)
        self.append(self.run, "gate.verdict", "w", 3, verdict="reject")
        self.append(self.run, "node.start", "w", 4)
        self.append(self.run, "check.result", "w", 5)
        self.append(self.run, "gate.verdict", "w", 7, verdict="pass")
        self.append(self.run, "node.start", "x", 8)
        self.append(self.run, "gate.verdict", "x", 9, verdict="pass")
        self.assertEqual(trace.trace(self.run), {
            "run": {"nodes": 2, "passed": 2, "attempts": 3, "rejections": 1, "duration_ms": 9000},
            "nodes": {"w": {"attempts": 2, "rejections": 1, "first_start": "2026-11-15T00:00:01Z",
                              "passed_at": "2026-11-15T00:00:07Z", "duration_ms": 6000,
                              "checks_run": 2, "rollbacks": 0},
                      "x": {"attempts": 1, "rejections": 0, "first_start": "2026-11-15T00:00:08Z",
                              "passed_at": "2026-11-15T00:00:09Z", "duration_ms": 1000,
                              "checks_run": 0, "rollbacks": 0}}})

    def test_no_plan_and_reopened_basis(self):
        self.assertEqual(trace.trace(self.run), {"run": {"nodes": 0, "passed": 0, "attempts": 0,
                         "rejections": 0, "duration_ms": None}, "nodes": {}})
        self.set_plan(self.run, [work("w")])
        self.append(self.run, "node.start", "w", 1)
        self.append(self.run, "gate.verdict", "w", 2, verdict="pass")
        self.append(self.run, "node.reopen", "w", 3)
        metrics = trace.trace(self.run)["nodes"]["w"]
        self.assertEqual(metrics, {"attempts": 0, "rejections": 0, "first_start": None,
                         "passed_at": None, "duration_ms": None, "checks_run": 0, "rollbacks": 0})

    def test_rollback_history(self):
        nodes = [work("p"), work("w", needs=[{"from": "p", "artifact": "p.txt"}]),
                 work("changed"), work("never"), work("outside", owns=["elsewhere/"])]
        other = self.new_run("history")
        self.set_plan(other, nodes)
        for nid in ("p", "w", "changed", "outside"):
            self.append(other, "gate.verdict", nid, verdict="pass")
        self.append(other, "node.reopen", "p")
        self.append(other, "node.reopen", "outside")
        self.append(other, "node.reopen", "never")
        nodes[2]["goal"] = "changed fingerprint"
        self.set_plan(other, nodes)
        self.append(other, "gate.verdict", "changed", verdict="reject")
        self.set_plan(self.run, [work("current", owns=["w.txt"])])
        self.append(self.run, "gate.verdict", "current", verdict="pass")
        self.append(self.run, "node.reopen", "current")
        corrupt = self.new_run("corrupt")
        (corrupt / "events.jsonl").write_text("broken\n{}\n")
        self.assertEqual(trace.rollbacks(self.repo, self.run, ["p.txt", "w.txt", "changed.txt", "never.txt"]), 3)
        self.assertEqual(trace.rollbacks(self.repo, self.run, []), 0)
        self.assertEqual(trace.trace(self.run)["nodes"]["current"]["rollbacks"], 1)

    def test_reject_replan_and_dependency_revision(self):
        other = self.new_run("revisions")
        nodes = [work("p"), work("w", needs=[{"from": "p", "artifact": "p.txt"}]),
                 work("rejected"), work("replanned"), work("never")]
        self.set_plan(other, nodes)
        # A failure before acceptance is not a rollback.
        self.append(other, "gate.verdict", "never", verdict="reject")
        for nid in ("w", "rejected", "replanned"):
            self.append(other, "gate.verdict", nid, verdict="pass")
        self.append(other, "gate.verdict", "rejected", verdict="reject")
        self.append(other, "gate.verdict", "replanned", verdict="replan")
        nodes[0]["goal"] = "producer changed"
        self.set_plan(other, nodes)
        self.assertEqual(trace.rollbacks(self.repo, self.run,
                         ["w.txt", "rejected.txt", "replanned.txt", "never.txt"]), 3)

    def test_gate_r5_with_merged_submission_and_independent_review(self):
        reviewer = {"id": "v", "kind": "review", "goal": "review", "target": "w", "lens": "correctness",
                    "owns": [], "lane": 1, "grade": "daily", "checks": [{"id": "cites", "type": "cites"}],
                    "needs": [{"from": "w", "artifact": "w.txt"}]}
        self.set_plan(self.run, [work("w", lane=2), reviewer])
        for nid, family in (("w", "openai"), ("v", "claude")):
            self.append(self.run, "node.assign", nid, family=family, isolation="shared")
        checks.start(self.run, "w", None, ACTOR)
        (self.repo / "w.txt").write_text("updated\n")
        self.git("add", "w.txt")
        self.git("commit", "-qm", "work")
        commit = self.git("rev-parse", "HEAD")
        checks.submit(self.run, "w", commit, None, "", [], None, ACTOR)
        self.append(self.run, "merge.result", merged=[{"node": "w", "commit": commit, "head": commit}])
        checks.start(self.run, "v", None, ACTOR)
        checks.review_submit(self.run, "v", "pass", [], ACTOR)
        self.assertEqual(gate.gate(self.run, "v", None, ACTOR)["verdict"], "pass")
        self.assertEqual(gate.evaluate(store.read_plan(self.run),
                         state.derive(store.read_plan(self.run), store.events(self.run)),
                         "w", [], [], 0)["verdict"], "pass")
        other = self.new_run("history")
        self.set_plan(other, [work("old", owns=["w.txt"])])
        self.append(other, "gate.verdict", "old", verdict="pass")
        self.append(other, "node.reopen", "old")
        outcome = gate.gate(self.run, "w", None, ACTOR)
        self.assertEqual((outcome["verdict"], outcome["rule"]), ("needs_approval", "R5"))


if __name__ == "__main__":
    unittest.main()
