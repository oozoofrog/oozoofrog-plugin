"""Assignment and brief contracts against temporary repositories and real logs."""
import os
import pathlib
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock

SCRIPTS = pathlib.Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))
from graphflow import assign, core, plan, state, store

ACTOR = {"role": "leader", "node": None, "session": "assign-test"}


def work(node_id="work", **changes):
    node = {"id": node_id, "kind": "work", "goal": "Implement the unit", "lane": 1,
            "grade": "scoped", "owns": [node_id + ".py"], "reads": ["README.md"],
            "checks": [{"id": "unit", "type": "cmd", "run": "python3 -B unit.py"},
                       {"id": "scope", "type": "scope"},
                       {"id": "ide", "type": "host", "tool": "IDE", "expect": "green"}]}
    node.update(changes)
    return node


class AssignTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = pathlib.Path(temp.name).resolve()
        env = mock.patch.dict(os.environ, GF_HOME=str(self.root / "home"))
        env.start()
        self.addCleanup(env.stop)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        self.run = store.init_run(self.repo, "assign", ACTOR)
        self.set_plan([work()])

    def set_plan(self, nodes):
        raw = {"schema_version": 1, "goal": "plan", "nodes": nodes}
        self.assertEqual(plan.validate(raw), [])
        normalized, _ = plan.normalize(raw)
        with store.transaction(self.run) as tx:
            revision, sha = tx.write_plan(normalized)
            tx.append("plan.set", {"revision": revision, "plan_sha256": sha,
                      "fingerprints": {n["id"]: state.fingerprint(n) for n in normalized["nodes"]}}, ACTOR)

    def append(self, kind, data):
        with store.transaction(self.run) as tx:
            return tx.append(kind, data, ACTOR)

    def current(self):
        return state.derive(store.read_plan(self.run), store.events(self.run))["nodes"]["work"]

    def assign(self, **changes):
        args = dict(executor="subagent", model="test", effort="high", provider="codex",
                    family="openai", isolation="shared", actor=ACTOR)
        args.update(changes)
        return assign.assign(self.run, "work", **args)

    def error(self, code, exit_code, function, *args, **kwargs):
        with self.assertRaises(core.GFError) as cm:
            function(*args, **kwargs)
        self.assertEqual((cm.exception.code, cm.exception.exit_code), (code, exit_code))

    def submit(self):
        self.append("node.start", {"node": "work", "attempt": 1})
        return self.append("node.submit", {"node": "work", "attempt": 1,
                           "commit": "abcdef1234", "changed_files": ["work.py"]})["seq"]

    def verdict(self, verdict, submission=None, rejection=None):
        self.append("gate.verdict", {"node": "work", "attempt": 1, "submission": submission,
                                     "verdict": verdict, "rule": "R1", "rejection": rejection})

    def test_assignment_event_and_reassignment(self):
        data = self.assign()
        self.assertEqual(store.events(self.run)[-1]["data"], data)
        self.assertEqual(set(data), {"node", "executor", "model", "effort", "provider", "family", "isolation"})
        self.assertEqual(self.current()["status"], "assigned")
        self.assign(model="replacement")
        self.assertEqual(self.current()["assignment"]["model"], "replacement")

    def test_valid_enumerations(self):
        for executor in ("inline", "subagent", "workflow", "t3", "background"):
            for family in ("claude", "openai", "other"):
                for isolation in ("shared", "worktree"):
                    self.assign(executor=executor, family=family, isolation=isolation)

    def test_invalid_arguments_append_nothing(self):
        for name in ("executor", "family", "isolation"):
            with self.subTest(name=name):
                before = store.events(self.run)
                self.error("bad_" + name, 2, self.assign, **{name: "invalid"})
                self.assertEqual(store.events(self.run), before)

    def test_reassign_allowed_verdicts_keep_status(self):
        submission = self.submit()
        for verdict, status in (("reject", "rejected"), ("unverified", "unverified"),
                                ("hold", "held"), ("needs_approval", "awaiting_approval")):
            with self.subTest(verdict=verdict):
                self.verdict(verdict, submission)
                self.assign(model=verdict)
                self.assertEqual(self.current()["status"], status)
                self.assertEqual(self.current()["assignment"]["model"], verdict)

    def test_invalid_statuses(self):
        self.append("node.start", {"node": "work", "attempt": 1})
        self.error("wrong_status", 4, self.assign)
        submission = self.append("node.submit", {"node": "work", "attempt": 1})["seq"]
        self.error("wrong_status", 4, self.assign)
        for verdict in ("pass", "replan"):
            self.verdict(verdict, submission)
            self.error("wrong_status", 4, self.assign)

    def test_work_brief_sections_and_atomic_copy(self):
        self.assign()
        text = assign.brief(self.run, "work")
        headings = ["## Environment", "## Goal", "## Inputs", "## Files you own", "## Read",
                    "## Checks", "## Steps", "## If you are blocked", "## Report"]
        self.assertEqual([text.index(h) for h in headings], sorted(text.index(h) for h in headings))
        for value in ("# work: Implement the unit", "export GF_RUN=" + str(self.run),
                      "export GF_ROLE=worker", "export GF_NODE=work", str(SCRIPTS / "gf"),
                      "python3 -B unit.py", "work.py", "IDE", "green", "check run work unit",
                      "check record work ide --result passed|failed --note ...", "red work",
                      "submit work --notes ...", "decide ask --node work", "decide wait <id>"):
            self.assertIn(value, text)
        self.assertNotIn("## Previous rejection", text)
        self.assertNotIn("## Constraints", text)
        self.assertEqual((self.run / "brief" / "work.md").read_text(), text)

    def test_inputs_do_not_leak_producer_context(self):
        self.set_plan([work("producer", goal="SECRET_PRODUCER_GOAL",
                            checks=[{"id": "secret", "type": "cmd", "run": "SECRET_CHECK"}]),
                       work(needs=[{"from": "producer", "artifact": "producer.py"}])])
        text = assign.brief(self.run, "work")
        self.assertIn("producer.py (producer: producer)", text)
        self.assertNotIn("SECRET_PRODUCER_GOAL", text)
        self.assertNotIn("SECRET_CHECK", text)

    def test_review_brief(self):
        self.set_plan([work(goal="SECRET_TARGET_GOAL"),
                       {"id": "review", "kind": "review", "goal": "Inspect changes", "lane": 1,
                        "grade": "daily", "target": "work", "lens": "data loss", "owns": [],
                        "checks": [{"id": "cites", "type": "cites"}]}])
        self.submit()
        text = assign.brief(self.run, "review")
        for value in ("export GF_ROLE=reviewer", "data loss", "abcdef1234", "work.py",
                      "You change no files.", "review submit review --verdict pass|fail --findings <json file>"):
            self.assertIn(value, text)
        self.assertNotIn("SECRET_TARGET_GOAL", text)
        self.append("node.submit", {"node": "work", "attempt": 1, "commit": None, "changed_files": []})
        self.assertIn("uncommitted, in the shared tree", assign.brief(self.run, "review"))

    def test_rejection_only_for_latest_reject(self):
        submission = self.submit()
        rejection = {"unit": "work", "attempt": 1, "max_attempts": 3, "verdict": "red",
                     "reason": "test failed", "evidence": {"log": "evidence/test.log", "tail": ["failure"]},
                     "scope": ["work.py"]}
        self.verdict("reject", submission, rejection)
        text = assign.brief(self.run, "work")
        for label in ("## Previous rejection", "UNIT", "VERDICT", "REASON", "EVIDENCE", "SCOPE",
                      "Fix only what the rejection names; stay inside SCOPE."):
            self.assertIn(label, text)
        self.verdict("hold", submission)
        self.assertNotIn("## Previous rejection", assign.brief(self.run, "work"))

    def test_worktree_submit(self):
        self.assign(isolation="worktree")
        text = assign.brief(self.run, "work")
        self.assertIn("Commit on the worktree branch.", text)
        self.assertIn("submit work --commit <sha> --notes ...", text)

    def test_decision_refused(self):
        self.set_plan([{"id": "work", "kind": "decision", "goal": "Decide", "lane": 3,
                        "question": "Proceed?", "decision_kind": "direction", "owns": [], "checks": []}])
        self.error("wrong_status", 4, self.assign)
        self.error("wrong_status", 4, assign.brief, self.run, "work")
        self.assertFalse((self.run / "brief" / "work.md").exists())

    def test_planning_without_learn_and_with_host(self):
        self.append("host.set", {"capabilities": ["t3_delegate", "ide_build"]})
        with mock.patch.object(assign, "_optional_module", return_value=None):
            text = assign.plan_brief(self.repo)
            self.assertIn("Every work node has a check that can fail", text)
            self.assertNotIn("## Host capabilities", text)
            text = assign.plan_brief(self.repo, self.run)
            self.assertIn("t3_delegate", text)
            self.assertIn("ide_build", text)

    def test_learning_constraints_filtered_and_fixed_checks(self):
        constraints = [{"text": "global", "scope": {}, "status": "active"},
                       {"text": "owned", "scope": {"paths": ["work.py"]}},
                       {"text": "unrelated", "scope": {"paths": ["elsewhere.py"]}}]
        learn = types.SimpleNamespace(applying=lambda *args: constraints,
                                      all_constraints=lambda *args: constraints + [{"text": "retired", "status": "retired"}],
                                      fixed_checks=lambda *args: [{"id": "fixed", "type": "cmd", "run": "fixed-command"}])
        with mock.patch.object(assign, "_optional_module", return_value=learn):
            text = assign.brief(self.run, "work")
            self.assertIn("## Constraints", text)
            self.assertIn("owned", text)
            self.assertIn("global", text)
            self.assertNotIn("unrelated", text)
            text = assign.plan_brief(self.repo)
            self.assertIn("fixed-command", text)
            self.assertNotIn("retired", text)

    def test_optional_import_only_swallows_missing_module(self):
        with mock.patch.object(assign.importlib, "import_module", side_effect=ModuleNotFoundError(name="graphflow.learn")):
            self.assertIsNone(assign._optional_module("learn"))
        with mock.patch.object(assign.importlib, "import_module", side_effect=ModuleNotFoundError(name="dependency")):
            with self.assertRaises(ModuleNotFoundError):
                assign._optional_module("learn")


if __name__ == "__main__":
    unittest.main()
