"""Real-filesystem contract tests for the record-integrity workspace helper."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "loop_workspace.py"


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / "project"
        self.project.mkdir()
        (self.project / "product.txt").write_text("untouched")
        self.brief = self.root / "input.md"
        self.brief.write_bytes(b"# Request\nKeep scope local.\n")
        self.plan_file = self.root / "input.json"
        self.plan = {
            "schema_version": 1, "goal": "Deliver the change",
            "tasks": [{"id": "build", "title": "Build", "depends_on": [],
                       "reads": ["src/./base.py"], "writes": ["src/new.py"],
                       "checks": [{"id": "unit", "description": "Run unit checks",
                                   "command": "touch SHOULD_NOT_RUN"}]}],
            "context": {"keep": "this"},
        }
        self.workspace = self.project / ".agent-loop" / "run-1"
        self.save_plan()

    def save_plan(self):
        self.plan_file.write_text(json.dumps(self.plan))

    def cli(self, *args, ok=True):
        result = subprocess.run([sys.executable, str(SCRIPT), *map(str, args)],
                                capture_output=True, text=True, cwd=self.root)
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, "")
            return json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertTrue(result.stderr.strip())
        self.assertTrue(result.stderr.startswith("error:"), result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertNotIn("Traceback", result.stderr)
        return result.stderr

    def init(self, **overrides):
        options = dict(project=self.project, run_id="run-1",
                       plan=self.plan_file, brief=self.brief)
        options.update(overrides)
        args = ["init"]
        for key, value in options.items():
            args.extend(["--" + key.replace("_", "-"), value])
        return self.cli(*args)

    def state(self):
        return json.loads((self.workspace / "state.json").read_text())

    def save_state(self, state):
        (self.workspace / "state.json").write_text(json.dumps(state))

    def status(self):
        return self.cli("status", "--workspace", self.workspace)

    def check_error(self):
        return self.cli("check", "--workspace", self.workspace, ok=False)

    def passed(self, state, task="build", revision="revision-a"):
        evidence = self.workspace / "evidence" / (task + ".log")
        evidence.write_bytes(b"Observed test output\n")
        state["tasks"][task].update(
            status="passed", attempts=1, verified_revision=revision,
            evidence=[{"check_id": "unit", "result": "passed",
                       "path": "evidence/" + task + ".log",
                       "sha256": hashlib.sha256(evidence.read_bytes()).hexdigest(),
                       "artifact_version": revision}])

    def add_decision(self):
        self.plan["decisions"] = [{"id": "approve", "kind": "review",
                                   "question": "Accept the preview?",
                                   "artifact_version": "preview-1"}]
        self.plan["tasks"][0]["decision_ids"] = ["approve"]
        self.save_plan()

    def test_bootstrap_normalizes_defaults_and_preserves_context_without_product_writes(self):
        result = self.init()
        self.assertFalse(result["reused"])
        self.assertEqual(result["workspace"], str(self.workspace))
        self.assertEqual(result["verification_scope"], "record_integrity_only")
        self.assertEqual({p.name for p in self.workspace.iterdir()},
                         {"brief.md", "plan.json", "state.json", "decisions.jsonl",
                          "lessons.md", "evidence"})
        normalized = json.loads((self.workspace / "plan.json").read_text())
        self.assertEqual(normalized["context"], {"keep": "this"})
        self.assertEqual(normalized["tasks"][0]["reads"], ["src/base.py"])
        self.assertEqual(normalized["tasks"][0]["max_attempts"], 3)
        self.assertEqual(normalized["tasks"][0]["decision_ids"], [])
        self.assertEqual((self.workspace / "brief.md").read_bytes(), self.brief.read_bytes())
        self.assertIn("scop", (self.workspace / "lessons.md").read_text().lower())
        self.assertEqual(self.state()["plan_sha256"], hashlib.sha256(
            (self.workspace / "plan.json").read_bytes()).hexdigest())
        self.assertEqual(self.status()["ready"], ["build"])
        self.assertFalse(self.status()["complete"])
        self.assertEqual((self.project / "product.txt").read_text(), "untouched")
        self.assertEqual({p.name for p in self.project.iterdir()}, {"product.txt", ".agent-loop"})
        self.assertFalse((self.root / "SHOULD_NOT_RUN").exists())

    def test_reuse_preserves_all_existing_progress_byte_for_byte(self):
        self.init()
        state = self.state()
        state["tasks"]["build"].update(status="failed", attempts=1)
        self.save_state(state)
        (self.workspace / "decisions.jsonl").write_text('{"event":"retained"}\n')
        (self.workspace / "evidence" / "failure.log").write_text("failure")
        before = {str(p.relative_to(self.workspace)): p.read_bytes()
                  for p in self.workspace.rglob("*") if p.is_file()}
        self.assertTrue(self.init()["reused"])
        self.assertEqual(before, {str(p.relative_to(self.workspace)): p.read_bytes()
                                  for p in self.workspace.rglob("*") if p.is_file()})

    def test_reuse_rejects_input_plan_brief_and_identity_mismatches(self):
        self.init()
        original = self.plan_file.read_bytes()
        self.plan["goal"] = "Different goal"
        self.save_plan()
        self.cli("init", "--project", self.project, "--run-id", "run-1",
                 "--plan", self.plan_file, "--brief", self.brief, ok=False)
        self.plan_file.write_bytes(original)
        self.brief.write_text("Different brief")
        self.cli("init", "--project", self.project, "--run-id", "run-1",
                 "--plan", self.plan_file, "--brief", self.brief, ok=False)
        self.brief.write_bytes(b"# Request\nKeep scope local.\n")
        state = self.state()
        state["project_root"] = str(self.root)
        self.save_state(state)
        self.cli("init", "--project", self.project, "--run-id", "run-1",
                 "--plan", self.plan_file, "--brief", self.brief, ok=False)

    def test_unsafe_run_ids_are_rejected_without_creating_workspace(self):
        for run_id in ["../escape", "/absolute", "a/b", r"a\b", ".", "", "a" * 65]:
            with self.subTest(run_id=run_id):
                self.cli("init", "--project", self.project, "--run-id", run_id,
                         "--plan", self.plan_file, "--brief", self.brief, ok=False)
        self.assertFalse((self.project / ".agent-loop").exists())

    def test_missing_project_and_symlink_loop_or_run_destinations_are_rejected(self):
        self.cli("init", "--project", self.root / "missing", "--run-id", "run-1",
                 "--plan", self.plan_file, "--brief", self.brief, ok=False)
        outside = self.root / "outside"
        outside.mkdir()
        loop = self.project / ".agent-loop"
        loop.symlink_to(outside, target_is_directory=True)
        self.cli("init", "--project", self.project, "--run-id", "run-1",
                 "--plan", self.plan_file, "--brief", self.brief, ok=False)
        self.assertEqual(list(outside.iterdir()), [])
        loop.unlink()
        loop.mkdir()
        self.workspace.symlink_to(outside, target_is_directory=True)
        self.cli("init", "--project", self.project, "--run-id", "run-1",
                 "--plan", self.plan_file, "--brief", self.brief, ok=False)
        self.assertEqual(list(outside.iterdir()), [])

    def test_project_alias_resolves_to_real_project(self):
        alias = self.root / "alias"
        alias.symlink_to(self.project, target_is_directory=True)
        self.init(project=alias)
        self.assertEqual(self.state()["project_root"], str(self.project.resolve()))

    def test_failed_init_leaves_no_staging_or_run_and_preserves_other_runs(self):
        loop = self.project / ".agent-loop"
        loop.mkdir()
        existing = loop / "keep"
        existing.write_text("existing")
        self.cli("init", "--project", self.project, "--run-id", "run-1",
                 "--plan", self.plan_file, "--brief", self.root / "missing.md", ok=False)
        self.assertEqual(list(loop.iterdir()), [existing])
        self.assertEqual(existing.read_text(), "existing")

    def test_plan_rejects_missing_self_and_cyclic_dependencies(self):
        for dep in ["missing", "build"]:
            self.plan["tasks"][0]["depends_on"] = [dep]
            self.save_plan()
            self.cli("validate-plan", "--plan", self.plan_file, ok=False)
        second = copy.deepcopy(self.plan["tasks"][0])
        second.update(id="review", depends_on=["build"])
        self.plan["tasks"][0]["depends_on"] = ["review"]
        self.plan["tasks"].append(second)
        self.save_plan()
        self.cli("validate-plan", "--plan", self.plan_file, ok=False)

    def test_plan_rejects_invalid_scope_paths(self):
        for field, path in [("reads", ""), ("reads", "/etc/passwd"),
                            ("reads", "src/../secret"), ("reads", r"src\..\secret"),
                            ("reads", r"C:\secret"), ("reads", "a/*.py"),
                            ("reads", "file?.py"), ("writes", "."),
                            ("writes", ".git/config"), ("writes", "./.agent-loop/run")]:
            with self.subTest(field=field, path=path):
                plan = copy.deepcopy(self.plan)
                plan["tasks"][0][field] = [path]
                self.plan_file.write_text(json.dumps(plan))
                self.cli("validate-plan", "--plan", self.plan_file, ok=False)

    def test_plan_schema_rejects_invalid_types_duplicates_and_decision_references(self):
        mutations = [
            lambda p: p.update(schema_version=True),
            lambda p: p.update(goal=" "), lambda p: p.update(tasks=[]),
            lambda p: p["tasks"].append(copy.deepcopy(p["tasks"][0])),
            lambda p: p["tasks"][0].update(max_attempts=True),
            lambda p: p["tasks"][0].update(max_attempts=0),
            lambda p: p["tasks"][0].update(checks=[]),
            lambda p: p["tasks"][0]["checks"].append(copy.deepcopy(p["tasks"][0]["checks"][0])),
            lambda p: p["tasks"][0].update(decision_ids=["missing"]),
            lambda p: p.update(question_budget={"max_questions": -1, "max_rounds": 2}),
            lambda p: p.update(decisions=[{"id":"d", "kind":"unknown", "question":"?"}]),
        ]
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                plan = copy.deepcopy(self.plan)
                mutate(plan)
                self.plan_file.write_text(json.dumps(plan))
                self.cli("validate-plan", "--plan", self.plan_file, ok=False)

    def test_overlapping_scopes_warn_even_with_dependency_and_read_root(self):
        second = copy.deepcopy(self.plan["tasks"][0])
        second.update(id="review", depends_on=["build"], reads=["."], writes=["src"])
        self.plan["tasks"].append(second)
        self.save_plan()
        result = self.cli("validate-plan", "--plan", self.plan_file)
        self.assertTrue(result["serialization_warnings"])
        self.assertIn("build", json.dumps(result["serialization_warnings"]))
        self.assertIn("review", json.dumps(result["serialization_warnings"]))
        self.assertFalse((self.project / ".agent-loop").exists())

    def test_malformed_state_attempts_status_and_id_sets_fail(self):
        self.init()
        initial = self.state()
        mutations = [
            lambda s: s["tasks"].clear(),
            lambda s: s["decisions"].update(unknown={"status":"pending"}),
            lambda s: s["tasks"]["build"].update(status="invented"),
            lambda s: s["tasks"]["build"].update(attempts=-1),
            lambda s: s["tasks"]["build"].update(attempts=4),
            lambda s: s["tasks"]["build"].update(attempts=True),
            lambda s: s["tasks"]["build"].update(status="running", attempts=0),
            lambda s: s.update(question_usage={"questions":-1,"rounds":0}),
        ]
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                state = copy.deepcopy(initial)
                mutate(state)
                self.save_state(state)
                self.check_error()
        (self.workspace / "state.json").write_text("{broken")
        self.check_error()

    def test_changed_plan_instructs_reconciliation_without_rewriting_state(self):
        self.init()
        before = (self.workspace / "state.json").read_bytes()
        with (self.workspace / "plan.json").open("a") as stream:
            stream.write("\n")
        error = self.check_error().lower()
        self.assertIn("reconcil", error)
        self.assertIn("review", error)
        self.assertEqual((self.workspace / "state.json").read_bytes(), before)

    def test_question_usage_obeys_default_or_explicit_budget_without_counting_decisions(self):
        self.init()
        state = self.state()
        for usage in [{"questions": 4, "rounds": 0}, {"questions": 0, "rounds": 3},
                      {"questions": True, "rounds": 0}, {"questions": 0},
                      {"questions": 1, "rounds": "1"}]:
            with self.subTest(usage=usage):
                state["question_usage"] = usage
                self.save_state(state)
                self.check_error()
        self.add_decision()
        self.plan["decisions"][0]["kind"] = "authorization"
        self.plan["question_budget"] = {"max_questions": 0, "max_rounds": 0}
        self.save_plan()
        self.init(run_id="zero-budget")
        self.workspace = self.project / ".agent-loop" / "zero-budget"
        state = self.state()
        state["decisions"]["approve"].update(status="resolved", answer="Proceed", outcome="approved",
                                             artifact_version="preview-1")
        self.save_state(state)
        self.assertEqual(self.status()["ready"], ["build"])
        state["question_usage"]["questions"] = 1
        self.save_state(state)
        self.check_error()

    def test_pass_requires_revision_and_each_required_passed_evidence(self):
        self.init()
        state = self.state()
        state["tasks"]["build"].update(status="passed", attempts=1)
        self.save_state(state)
        self.check_error()
        state["tasks"]["build"]["verified_revision"] = "revision-a"
        self.save_state(state)
        self.check_error()
        self.passed(state)
        for result in ["failed", "not_run"]:
            state["tasks"]["build"]["evidence"][0]["result"] = result
            self.save_state(state)
            self.check_error()

    def test_missing_edited_empty_and_wrong_revision_evidence_fail(self):
        self.init()
        state = self.state()
        self.passed(state)
        self.save_state(state)
        evidence = self.workspace / "evidence" / "build.log"
        evidence.unlink()
        self.check_error()
        evidence.write_text("changed")
        self.check_error()
        evidence.write_bytes(b"")
        state["tasks"]["build"]["evidence"][0]["sha256"] = hashlib.sha256(b"").hexdigest()
        self.save_state(state)
        self.check_error()
        self.passed(state)
        state["tasks"]["build"]["evidence"][0]["artifact_version"] = "old"
        self.save_state(state)
        self.check_error()

    def test_passed_state_rejects_duplicate_or_contradictory_current_check_records(self):
        self.init()
        state = self.state()
        self.passed(state)
        first = state["tasks"]["build"]["evidence"][0]
        for result in ["passed", "failed", "not_run"]:
            with self.subTest(duplicate_result=result):
                duplicate = dict(first, result=result)
                state["tasks"]["build"]["evidence"] = [first, duplicate]
                self.save_state(state)
                self.check_error()

    def test_evidence_traversal_and_symlink_components_are_rejected(self):
        self.init()
        state = self.state()
        self.passed(state)
        record = state["tasks"]["build"]["evidence"][0]
        for path in ["evidence/../brief.md", "/etc/passwd", "brief.md", r"evidence\..\brief.md"]:
            record["path"] = path
            self.save_state(state)
            self.check_error()
        target = self.workspace / "evidence" / "build.log"
        link = self.workspace / "evidence" / "alias.log"
        link.symlink_to(target)
        record["path"] = "evidence/alias.log"
        self.save_state(state)
        self.check_error()
        directory = self.workspace / "evidence" / "nested"
        directory.symlink_to(self.workspace / "evidence", target_is_directory=True)
        record["path"] = "evidence/nested/build.log"
        self.save_state(state)
        self.check_error()

    def test_symlink_manifests_and_workspace_alias_are_rejected(self):
        self.init()
        for name in ["plan.json", "state.json", "brief.md", "decisions.jsonl", "lessons.md"]:
            manifest = self.workspace / name
            data = manifest.read_bytes()
            source = self.root / name
            source.write_bytes(data)
            manifest.unlink()
            manifest.symlink_to(source)
            self.check_error()
            manifest.unlink()
            manifest.write_bytes(data)
        alias = self.root / "run-alias"
        alias.symlink_to(self.workspace, target_is_directory=True)
        self.cli("check", "--workspace", alias, ok=False)

    def test_decisions_block_ready_and_pass_until_resolved_for_matching_artifact(self):
        self.add_decision()
        self.init()
        self.assertIn("outcome", self.state()["decisions"]["approve"])
        self.assertIsNone(self.state()["decisions"]["approve"]["outcome"])
        self.assertEqual(self.status()["ready"], [])
        self.assertEqual(self.status()["blocked_by_decisions"], ["build"])
        state = self.state()
        self.passed(state)
        self.save_state(state)
        self.check_error()
        state["decisions"]["approve"].update(status="resolved", answer="yes", outcome="approved", artifact_version="old")
        self.save_state(state)
        self.check_error()
        state["decisions"]["approve"]["artifact_version"] = "preview-1"
        state["decisions"]["approve"]["answer"] = " "
        self.save_state(state)
        self.check_error()
        state["decisions"]["approve"]["answer"] = "Accept this preview"
        self.save_state(state)
        self.assertTrue(self.status()["complete"])

    def test_rejected_or_revision_requested_review_and_authorization_never_release_gate(self):
        for kind in ["review", "authorization"]:
            for outcome in ["rejected", "revision_requested"]:
                with self.subTest(kind=kind, outcome=outcome):
                    self.add_decision()
                    self.plan["decisions"][0]["kind"] = kind
                    self.save_plan()
                    run_id = kind + "-" + outcome
                    self.init(run_id=run_id)
                    self.workspace = self.project / ".agent-loop" / run_id
                    state = self.state()
                    state["decisions"]["approve"].update(status="resolved", answer="Do not proceed",
                                                        outcome=outcome, artifact_version="preview-1")
                    self.save_state(state)
                    self.assertEqual(self.status()["ready"], [])
                    self.assertEqual(self.status()["blocked_by_decisions"], ["build"])
                    self.passed(state)
                    self.save_state(state)
                    self.check_error()

    def test_resolved_decisions_require_kind_appropriate_outcomes(self):
        self.add_decision()
        self.init()
        state = self.state()
        decision = state["decisions"]["approve"]
        decision.update(status="resolved", answer="Proceed", artifact_version="preview-1")
        for outcome in [None, "answered", "unknown"]:
            with self.subTest(outcome=outcome):
                decision["outcome"] = outcome
                self.save_state(state)
                self.check_error()
        for kind in ["direction", "information"]:
            self.plan["decisions"][0]["kind"] = kind
            self.save_plan()
            self.init(run_id=kind)
            self.workspace = self.project / ".agent-loop" / kind
            state = self.state()
            decision = state["decisions"]["approve"]
            decision.update(status="resolved", answer="Use this direction", artifact_version="preview-1", outcome="approved")
            self.save_state(state)
            self.check_error()
            decision["outcome"] = "answered"
            self.save_state(state)
            self.assertEqual(self.status()["ready"], ["build"])

    def test_dependencies_gate_ready_and_pass_and_all_passed_is_complete(self):
        second = copy.deepcopy(self.plan["tasks"][0])
        second.update(id="review", depends_on=["build"], reads=["src/new.py"], writes=[])
        self.plan["tasks"].append(second)
        self.save_plan()
        self.init()
        self.assertEqual(self.status()["ready"], ["build"])
        self.assertEqual(self.status()["blocked_by_dependencies"], ["review"])
        state = self.state()
        self.passed(state, "review")
        self.save_state(state)
        self.check_error()
        self.passed(state)
        self.save_state(state)
        status = self.status()
        self.assertTrue(status["complete"])
        self.assertEqual(status["passed"], ["build", "review"])
        self.assertEqual(status["verification_scope"], "record_integrity_only")

    def test_exhausted_stale_running_and_cancelled_status_are_not_complete(self):
        self.init()
        state = self.state()
        for status, attempts, category in [("failed",3,"exhausted"),
                                            ("stale",1,"needs_revalidation"),
                                            ("running",1,"running"),
                                            ("blocked",0,"blocked"),
                                            ("cancelled",0,"cancelled")]:
            with self.subTest(status=status):
                state["tasks"]["build"].update(status=status, attempts=attempts)
                self.save_state(state)
                result = self.status()
                self.assertIn(category, result)
                self.assertEqual(result[category], ["build"])
                self.assertFalse(result["complete"])
                self.assertEqual(result["ready"], ["build"] if status == "stale" else [])

    def test_check_and_status_never_mutate_workspace(self):
        self.init()
        before = {str(p): p.read_bytes() for p in self.workspace.rglob("*") if p.is_file()}
        self.cli("check", "--workspace", self.workspace)
        self.status()
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.workspace.rglob("*") if p.is_file()})

    def test_help_names_record_integrity_limitation(self):
        result = subprocess.run([sys.executable, str(SCRIPT), "--help"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("record", result.stdout.lower())
        self.assertIn("semantic", result.stdout.lower())


if __name__ == "__main__":
    unittest.main()
