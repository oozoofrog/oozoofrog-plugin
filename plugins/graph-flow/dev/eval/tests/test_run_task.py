"""Exercise the public CLI using disposable candidates and trusted suites."""

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
RUNNER = HERE.parent / "run_task.py"
SAMPLES = HERE / "samples"


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="graph-flow-runner-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.tasks = self.root / "tasks"
        shutil.copytree(SAMPLES / "tasks", self.tasks)
        self.fixture = SAMPLES / "fixture"
        self.dest = self.root / "candidate"

    def cli(self, *args, expected=0):
        result = subprocess.run(
            [sys.executable, "-I", "-S", "-B", str(RUNNER),
             "--tasks", str(self.tasks), "--fixture", str(self.fixture)]
            + [str(arg) for arg in args],
            capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def select(self, *names):
        for task in self.tasks.iterdir():
            if task.name not in names:
                shutil.rmtree(task)

    def setup_candidate(self):
        self.cli("setup", "sound", self.dest)

    def solve(self):
        shutil.copyfile(self.tasks / "sound/solution/mathkit.py", self.dest / "mathkit.py")

    def test_list_is_sorted_and_paths_work_after_command(self):
        result = self.cli("list", "--tasks", SAMPLES / "tasks", "--fixture", self.fixture)
        self.assertEqual(result.stdout.splitlines(), sorted(p.name for p in self.tasks.iterdir()))

    def test_setup_copies_fixture_then_start_and_refuses_nonempty(self):
        self.dest.mkdir()
        self.cli("setup", "bad-start", self.dest)
        self.assertEqual((self.dest / "mathkit.py").read_text(),
                         (self.tasks / "bad-start/start/mathkit.py").read_text())
        self.assertTrue((self.dest / "tests/test_visible.py").is_file())
        before = (self.dest / "mathkit.py").read_bytes()
        result = self.cli("setup", "sound", self.dest, expected=1)
        self.assertIn("absent or an empty directory", result.stderr)
        self.assertEqual((self.dest / "mathkit.py").read_bytes(), before)
        self.assertFalse((self.dest / "hidden_tests").exists())
        self.assertFalse((self.dest / "task.json").exists())

    def test_setup_rejects_file_symlink_and_source_destination(self):
        self.dest.write_text("keep")
        self.cli("setup", "sound", self.dest, expected=1)
        self.assertEqual(self.dest.read_text(), "keep")
        self.dest.unlink()
        target = self.root / "empty"
        target.mkdir()
        self.dest.symlink_to(target, target_is_directory=True)
        self.cli("setup", "sound", self.dest, expected=1)
        self.assertEqual(list(target.iterdir()), [])
        self.cli("setup", "sound", self.fixture / "nested", expected=1)

    def test_score_runs_hidden_suite_and_returns_exact_json_contract(self):
        self.setup_candidate()
        result = self.cli("score", "sound", self.dest, expected=1)
        score = json.loads(result.stdout)
        self.assertEqual(score, dict(task="sound", passed=False, tests=2, failures=2, errors=0, skipped=0))
        self.solve()
        before = sorted(str(p.relative_to(self.dest)) for p in self.dest.rglob("*"))
        score = json.loads(self.cli("score", "sound", self.dest).stdout)
        self.assertEqual(score, dict(task="sound", passed=True, tests=2, failures=0, errors=0, skipped=0))
        self.assertEqual(before, sorted(str(p.relative_to(self.dest)) for p in self.dest.rglob("*")))
        self.assertFalse(list(self.root.rglob("__pycache__")))

    def test_deleting_or_editing_visible_tests_cannot_change_score(self):
        self.setup_candidate()
        (self.dest / "tests/test_visible.py").write_text("raise RuntimeError('edited')")
        report = json.loads(self.cli("score", "sound", self.dest, expected=1).stdout)
        self.assertEqual(report["failures"], 2)
        shutil.rmtree(self.dest / "tests")
        (self.dest / "test_hidden.py").write_text("# impostor empty test suite")
        report = json.loads(self.cli("score", "sound", self.dest, expected=1).stdout)
        self.assertEqual(report["tests"], 2)
        self.solve()
        self.assertTrue(json.loads(self.cli("score", "sound", self.dest).stdout)["passed"])

    def test_visible_test_tampering_by_candidate_cannot_pass(self):
        self.setup_candidate()
        for action in ("Path('tests/test_visible.py').write_text('# removed assertions')",
                       "shutil.rmtree('tests')"):
            with self.subTest(action=action):
                shutil.copytree(self.fixture / "tests", self.dest / "tests", dirs_exist_ok=True)
                (self.dest / "mathkit.py").write_text(
                    "from pathlib import Path\nimport shutil\n" + action + "\n"
                    "def bump(value): return value\n")
                score = json.loads(self.cli("score", "sound", self.dest, expected=1).stdout)
                self.assertFalse(score["passed"])
                self.assertEqual(score["tests"], 2)
                self.assertEqual(score["failures"], 2)
                self.assertEqual(score["errors"], 0)
                self.assertEqual(score["skipped"], 0)
                if action.startswith("Path"):
                    self.assertEqual((self.dest / "tests/test_visible.py").read_text(),
                                     "# removed assertions")
                else:
                    self.assertFalse((self.dest / "tests").exists())

    def test_hidden_import_error_is_an_error(self):
        self.setup_candidate()
        self.solve()
        (self.tasks / "sound/hidden_tests/test_hidden.py").write_text("import absent_hidden_dependency")
        score = json.loads(self.cli("score", "sound", self.dest, expected=1).stdout)
        self.assertFalse(score["passed"])
        self.assertEqual(score["errors"], 1)
        self.assertEqual(score["failures"], 0)

    def test_zero_tests_never_pass(self):
        self.setup_candidate()
        (self.tasks / "sound/hidden_tests/test_hidden.py").write_text("# no tests")
        score = json.loads(self.cli("score", "sound", self.dest, expected=1).stdout)
        self.assertFalse(score["passed"])
        self.assertEqual(score["tests"], 0)
        self.select("sound")
        result = self.cli("selfcheck", expected=1)
        self.assertIn("zero tests", result.stdout)

    def test_candidate_prints_do_not_corrupt_json(self):
        self.setup_candidate()
        self.solve()
        with (self.dest / "mathkit.py").open("a") as stream:
            stream.write("\nprint('candidate output')\n")
        result = self.cli("score", "sound", self.dest)
        self.assertTrue(json.loads(result.stdout)["passed"])
        self.assertIn("candidate output", result.stderr)

    def test_module_skip_never_passes(self):
        self.setup_candidate()
        (self.dest / "mathkit.py").write_text(
            "import unittest\nraise unittest.SkipTest('candidate skipped')\n")
        score = json.loads(self.cli("score", "sound", self.dest, expected=1).stdout)
        self.assertFalse(score["passed"])
        self.assertEqual(score["skipped"], 1)
        self.assertIn("test_hidden.py", score["unloaded"])

    def test_skipped_tests_never_pass(self):
        self.setup_candidate()
        self.solve()
        cases = {
            "method": ("    @unittest.skip('skip')\n"
                       "    def test_skip(self): pass\n", 1),
            "mixed": ("    def test_pass(self): self.assertEqual(bump(2), 3)\n"
                      "    @unittest.skip('skip')\n"
                      "    def test_skip(self): pass\n", 2),
            "class_setup": ("    @classmethod\n"
                            "    def setUpClass(cls): raise unittest.SkipTest('skip')\n"
                            "    def test_skip(self): pass\n", 0),
            "subtest": ("    def test_subtests(self):\n"
                        "        with self.subTest(value=2): self.assertEqual(bump(2), 3)\n"
                        "        with self.subTest(value=7): self.skipTest('skip')\n", 1),
        }
        for name, (body, count) in cases.items():
            with self.subTest(outcome=name):
                (self.tasks / "sound/hidden_tests/test_hidden.py").write_text(
                    "import unittest\nfrom mathkit import bump\n"
                    "class Hidden(unittest.TestCase):\n" + body)
                score = json.loads(self.cli("score", "sound", self.dest, expected=1).stdout)
                self.assertFalse(score["passed"])
                self.assertEqual(score["tests"], count)
                self.assertEqual(score["skipped"], 1)
                self.assertEqual(score["failures"], 0)
                self.assertEqual(score["errors"], 0)

    def test_expected_failure_and_unexpected_success_never_pass(self):
        self.setup_candidate()
        self.solve()
        for assertion in ("self.fail('expected failure')", "self.assertEqual(bump(2), 3)"):
            for other_pass in (False, True):
                with self.subTest(assertion=assertion, other_pass=other_pass):
                    source = ("import unittest\nfrom mathkit import bump\n"
                              "class Hidden(unittest.TestCase):\n"
                              "    @unittest.expectedFailure\n"
                              "    def test_expected(self): " + assertion + "\n")
                    if other_pass:
                        source += "    def test_pass(self): self.assertEqual(bump(2), 3)\n"
                    (self.tasks / "sound/hidden_tests/test_hidden.py").write_text(source)
                    score = json.loads(self.cli("score", "sound", self.dest, expected=1).stdout)
                    self.assertFalse(score["passed"])
                    self.assertEqual(score["tests"], 2 if other_pass else 1)
                    self.assertEqual(score["failures"], 1)
                    self.assertEqual(score["errors"], 0)
                    self.assertEqual(score["skipped"], 0)

    def test_fake_stdout_and_early_exit_never_pass(self):
        self.setup_candidate()
        fake = json.dumps(dict(tests=5, failures=0, errors=0, skipped=0, passed=True))
        for exit_code in (0, 7):
            with self.subTest(exit_code=exit_code):
                (self.dest / "mathkit.py").write_text(
                    "import os\nos.write(1, %r)\nos._exit(%d)\n" %
                    (fake.encode("utf-8"), exit_code))
                result = self.cli("score", "sound", self.dest, expected=1)
                score = json.loads(result.stdout)
                self.assertFalse(score["passed"])
                self.assertEqual(score["tests"], 0)
                self.assertEqual(score["errors"], 1)
                self.assertEqual(score["skipped"], 0)
                self.assertIn(fake, result.stderr)

    def test_raw_stdout_is_diagnostic_only(self):
        self.setup_candidate()
        self.solve()
        fake = json.dumps(dict(tests=500, failures=0, errors=0, skipped=0, passed=True))
        with (self.dest / "mathkit.py").open("a") as stream:
            stream.write("\nimport os\nos.write(1, %r)\n" % fake.encode("utf-8"))
        result = self.cli("score", "sound", self.dest)
        score = json.loads(result.stdout)
        self.assertTrue(score["passed"])
        self.assertEqual(score["tests"], 2)
        self.assertIn(fake, result.stderr)
        (self.dest / "mathkit.py").write_text(
            (self.fixture / "mathkit.py").read_text()
            + "\nimport os\nos.write(1, %r)\n" % fake.encode("utf-8"))
        score = json.loads(self.cli("score", "sound", self.dest, expected=1).stdout)
        self.assertFalse(score["passed"])
        self.assertEqual(score["failures"], 2)

    def test_candidate_exit_and_crash_without_report_never_pass(self):
        self.setup_candidate()
        for action in ("os._exit(0)", "os._exit(7)", "os.kill(os.getpid(), signal.SIGKILL)"):
            with self.subTest(action=action):
                (self.dest / "mathkit.py").write_text("import os, signal\n" + action + "\n")
                score = json.loads(self.cli("score", "sound", self.dest, expected=1).stdout)
                self.assertFalse(score["passed"])
                self.assertEqual(score["errors"], 1)
                self.assertEqual(score["skipped"], 0)

    def test_nonzero_exit_rejects_even_a_completed_passing_report(self):
        self.setup_candidate()
        self.solve()
        with (self.dest / "mathkit.py").open("a") as stream:
            stream.write("\nimport atexit, os\natexit.register(lambda: os._exit(7))\n")
        score = json.loads(self.cli("score", "sound", self.dest, expected=1).stdout)
        self.assertFalse(score["passed"])
        self.assertEqual(score["errors"], 1)

    def test_selfcheck_rejects_skip_only_solution(self):
        self.select("bad-skip-solution")
        result = self.cli("selfcheck", "--expect", 1, "--mix", "single=1", expected=1)
        self.assertIn("bad-skip-solution: solution fails hidden tests", result.stdout)
        self.assertIn("skipped=1", result.stdout)
        self.assertNotIn("bad-skip-solution: OK", result.stdout)

    def test_missing_candidate_or_unknown_task_returns_json_error(self):
        for task in ("sound", "missing", "../sound"):
            with self.subTest(task=task):
                score = json.loads(self.cli("score", task, self.dest, expected=1).stdout)
                self.assertFalse(score["passed"])
                self.assertEqual(score["errors"], 1)

    def test_selfcheck_reports_every_unsound_sample(self):
        self.select("sound", "sound-review", "bad-start", "bad-solution", "bad-review", "bad-skip-solution")
        result = self.cli("selfcheck", expected=1)
        self.assertIn("sound: OK", result.stdout)
        self.assertIn("sound-review: OK", result.stdout)
        self.assertIn("bad-start: start wrongly passes hidden tests", result.stdout)
        self.assertIn("bad-solution: solution fails hidden tests", result.stdout)
        self.assertIn("bad-review: tempting wrongly passes hidden tests", result.stdout)
        self.assertIn("bad-skip-solution: solution fails hidden tests", result.stdout)
        self.assertEqual(len(result.stdout.splitlines()), 6)

    def test_sound_samples_count_and_category_mix(self):
        self.select("sound", "sound-review")
        self.cli("selfcheck", "--expect", 2,
                 "--mix", "single=1,chain=0,review=1,parallel=0")
        result = self.cli("selfcheck", "--expect", 10,
                          "--mix", "single=2,chain=1,review=0,parallel=1", expected=1)
        for message in ("expected 10 tasks, found 2", "category single", "category chain",
                        "category review", "category parallel"):
            self.assertIn(message, result.stderr)

    def test_empty_and_missing_tasks_do_not_meet_expected_count(self):
        result = self.cli("selfcheck", "--tasks", HERE / "empty-tasks", "--expect", 10, expected=1)
        self.assertIn("expected 10 tasks, found 0", result.stderr)
        self.cli("selfcheck", "--tasks", self.root / "missing", "--expect", 10, expected=1)

    def test_invalid_metadata_is_reported_for_every_task(self):
        self.select("sound", "bad-start")
        metadata = self.tasks / "sound/task.json"
        data = json.loads(metadata.read_text())
        data.update(id="wrong", category="other", title="", prompt=12, parts=[""])
        metadata.write_text(json.dumps(data))
        (self.tasks / "bad-start/task.json").write_text("[]")
        result = self.cli("selfcheck", expected=1)
        for text in ("sound:", "bad-start:", "id must equal", "category must be", "title must",
                     "prompt must", "parts must", "must be an object"):
            self.assertIn(text, result.stdout)

    def test_required_directories_and_bad_json_are_reported(self):
        self.select("sound", "sound-review", "bad-start")
        shutil.rmtree(self.tasks / "sound/solution")
        shutil.rmtree(self.tasks / "sound-review/tempting")
        (self.tasks / "bad-start/task.json").write_text("{")
        result = self.cli("selfcheck", expected=1)
        for text in ("missing solution/", "missing tempting/", "bad-start: task.json:"):
            self.assertIn(text, result.stdout)

    def test_review_visible_tests_are_trusted_fixture_tests(self):
        self.select("sound-review")
        tempting = self.tasks / "sound-review/tempting"
        (tempting / "mathkit.py").write_text("def bump(value):\n    return -1\n")
        (tempting / "tests").mkdir()
        (tempting / "tests/test_visible.py").write_text("# disable visible tests")
        result = self.cli("selfcheck", expected=1)
        self.assertIn("tempting fails visible tests", result.stdout)

    def test_invalid_mix_is_rejected(self):
        for mix in ("nope=1", "single=-1", "single=1,single=2", "single", "single=x"):
            with self.subTest(mix=mix):
                self.cli("selfcheck", "--mix", mix, expected=2)


    def test_uncollected_file_samples_fail_selfcheck_and_score(self):
        cases = {
            "bad-unpackaged": "alpha/test_part.py",
            "bad-pattern": "bump_test.py",
            "bad-empty-module": "test_empty.py",
        }
        self.select(*cases)
        result = self.cli("selfcheck", expected=1)
        for task, file in cases.items():
            with self.subTest(task=task):
                self.assertIn(task + ":", result.stdout)
                self.assertIn(file, result.stdout)
                self.assertNotIn(task + ": OK", result.stdout)
                candidate = self.root / task
                self.cli("setup", task, candidate)
                shutil.copyfile(self.tasks / task / "solution/mathkit.py", candidate / "mathkit.py")
                scored = self.cli("score", task, candidate, expected=1)
                score = json.loads(scored.stdout)
                self.assertFalse(score["passed"])
                self.assertTrue(any(file in name for name in score["unloaded"]))
                self.assertIn(file, scored.stderr)

    def test_parallel_packages_duplicate_names_and_partial_candidate(self):
        self.select("sound-parallel")
        self.cli("selfcheck", "--expect", 1, "--mix", "parallel=1")
        self.cli("setup", "sound-parallel", self.dest)
        partial = (self.dest / "mathkit.py").read_text().replace(
            "def bump(value): return value", "def bump(value): return value + 1 if value else 0")
        (self.dest / "mathkit.py").write_text(partial)
        score = json.loads(self.cli("score", "sound-parallel", self.dest, expected=1).stdout)
        self.assertEqual(score["tests"], 3)
        self.assertEqual(score["failures"], 2)
        shutil.copyfile(self.tasks / "sound-parallel/solution/mathkit.py", self.dest / "mathkit.py")
        self.assertTrue(json.loads(self.cli("score", "sound-parallel", self.dest).stdout)["passed"])

    def test_multipart_each_hidden_file_must_fail_start_alone(self):
        self.select("bad-irrelevant-part")
        result = self.cli("selfcheck", expected=1)
        self.assertIn("alpha/test_part.py must FAIL or ERROR alone", result.stdout)
        self.assertNotIn("bad-irrelevant-part: OK", result.stdout)

    def test_each_file_check_uses_an_isolated_interpreter(self):
        self.select("bad-irrelevant-part")
        hidden = self.tasks / "bad-irrelevant-part/hidden_tests/test_bump.py"
        hidden.write_text(hidden.read_text() + "\nimport mathkit\n"
                          "if mathkit.bump(2) == 2: mathkit.twice = lambda value: value\n")
        # All files fail in a shared suite, but twice already works when taken alone.
        result = self.cli("selfcheck", expected=1)
        self.assertIn("alpha/test_part.py must FAIL or ERROR alone", result.stdout)

    def test_empty_tasks_are_an_error_even_without_expect_or_with_expect_zero(self):
        self.select()
        for options in ((), ("--expect", 0)):
            with self.subTest(options=options):
                result = self.cli("selfcheck", *options, expected=1)
                self.assertIn("tasks directory is empty", result.stderr)

    def test_score_refuses_fixture_or_any_task_destination(self):
        aliases = self.root / "alias"
        aliases.symlink_to(self.tasks / "sound/solution", target_is_directory=True)
        for destination in (self.fixture, self.fixture / "tests", self.tasks,
                            self.tasks / "sound/solution", self.tasks / "bad-start/start", aliases):
            with self.subTest(destination=destination):
                result = self.cli("score", "sound", destination, expected=1)
                self.assertFalse(json.loads(result.stdout)["passed"])
                self.assertIn("destination must be outside fixture and task directories", result.stderr)

    def test_load_tests_hooks_cannot_replace_or_hide_hidden_tests(self):
        self.select("sound")
        self.setup_candidate()
        self.solve()
        hidden = self.tasks / "sound/hidden_tests"
        original = (hidden / "test_hidden.py").read_text()
        hooks = (
            "def load_tests(loader, tests, pattern): return unittest.TestSuite()\n",
            "def load_tests(loader, tests, pattern): return unittest.TestSuite([Hidden('test_two')])\n",
        )
        for hook in hooks:
            with self.subTest(hook=hook):
                (hidden / "test_hidden.py").write_text(original + "\n" + hook)
                result = self.cli("score", "sound", self.dest, expected=1)
                self.assertIn("load_tests hooks are not supported", result.stderr)
                self.assertIn("test_hidden.py", json.loads(result.stdout)["unloaded"])
                self.assertIn("load_tests hooks are not supported", self.cli("selfcheck", expected=1).stdout)
        (hidden / "test_hidden.py").write_text(original)
        package = hidden / "nested"
        package.mkdir()
        (package / "__init__.py").write_text("import unittest\n" + hooks[0])
        (package / "test_nested.py").write_text(original)
        result = self.cli("score", "sound", self.dest, expected=1)
        self.assertIn("nested/__init__.py: load_tests", result.stderr)
        self.assertIn("nested/test_nested.py", json.loads(result.stdout)["unloaded"])

    def test_extra_file_with_no_testcase_never_scores_a_subset(self):
        self.select("sound")
        self.setup_candidate()
        self.solve()
        empty = self.tasks / "sound/hidden_tests/test_empty.py"
        for source in ("def test_function(): assert False\n",
                       "import unittest\nclass Empty(unittest.TestCase):\n    def helper(self): pass\n"):
            with self.subTest(source=source):
                empty.write_text(source)
                score = json.loads(self.cli("score", "sound", self.dest, expected=1).stdout)
                self.assertEqual(score["tests"], 2)
                self.assertEqual(score["unloaded"], ["test_empty.py"])
                result = self.cli("selfcheck", expected=1)
                self.assertIn("test_empty.py", result.stdout)
                self.assertNotIn("sound: OK", result.stdout)

    def test_extra_file_with_all_skips_or_expected_failures_never_passes(self):
        self.select("sound")
        self.setup_candidate()
        self.solve()
        extra = self.tasks / "sound/hidden_tests/test_extra.py"
        sources = (
            "@unittest.skip('skip')\nclass Extra(unittest.TestCase):\n    def test_x(self): pass\n",
            "class Extra(unittest.TestCase):\n    @unittest.expectedFailure\n"
            "    def test_x(self): self.fail('expected')\n",
        )
        for source in sources:
            with self.subTest(source=source):
                extra.write_text("import unittest\n" + source)
                score = json.loads(self.cli("score", "sound", self.dest, expected=1).stdout)
                self.assertFalse(score["passed"])
                self.assertEqual(score["tests"], 3)
                self.assertIn("solution fails hidden tests", self.cli("selfcheck", expected=1).stdout)

    def test_start_skip_does_not_prove_task_is_unsolved(self):
        self.select("sound")
        (self.tasks / "sound/start/mathkit.py").write_text(
            "import unittest\nraise unittest.SkipTest('no assertions executed')\n")
        result = self.cli("selfcheck", expected=1)
        self.assertNotIn("sound: OK", result.stdout)
        self.assertIn("start must fail or error without skips", result.stdout)

    def test_syntax_error_and_invalid_encoding_files_fail_closed(self):
        self.select("sound")
        self.setup_candidate()
        self.solve()
        extra = self.tasks / "sound/hidden_tests/test_broken.py"
        for source in (b"def broken(:\n", b"# invalid utf8: \xff\n"):
            with self.subTest(source=source):
                extra.write_bytes(source)
                result = self.cli("score", "sound", self.dest, expected=1)
                score = json.loads(result.stdout)
                self.assertEqual(score["errors"], 1)
                self.assertTrue(any("test_broken.py" in name for name in score["unloaded"]))
                self.assertIn("test_broken.py", result.stderr)
                self.assertNotIn("sound: OK", self.cli("selfcheck", expected=1).stdout)
        extra.write_bytes(("# coding: latin-1\n# café\nimport unittest\nfrom mathkit import bump\n"
                           "class Extra(unittest.TestCase):\n"
                           "    def test_x(self): self.assertEqual(bump(2), 3)\n").encode("latin-1"))
        self.assertTrue(json.loads(self.cli("score", "sound", self.dest).stdout)["passed"])
        self.cli("selfcheck")

    def test_hidden_symlinks_are_refused_without_following_them(self):
        self.select("sound")
        self.setup_candidate()
        self.solve()
        hidden = self.tasks / "sound/hidden_tests"
        for target in (self.root / "absent", self.dest / "mathkit.py", self.dest):
            with self.subTest(target=target):
                link = hidden / "linked"
                link.symlink_to(target, target_is_directory=target.is_dir())
                result = self.cli("score", "sound", self.dest, expected=1)
                self.assertIn("symlinks are not supported", result.stderr)
                self.assertTrue(json.loads(result.stdout)["unloaded"])
                self.assertNotIn("sound: OK", self.cli("selfcheck", expected=1).stdout)
                link.unlink()
        saved = self.root / "saved-hidden"
        hidden.rename(saved)
        hidden.symlink_to(saved, target_is_directory=True)
        self.assertIn("symlinks", self.cli("score", "sound", self.dest, expected=1).stderr)

    def test_candidate_symlinks_are_refused(self):
        self.setup_candidate()
        self.solve()
        for target in (self.root / "absent", self.dest / "mathkit.py", self.dest):
            with self.subTest(target=target):
                link = self.dest / "linked"
                link.symlink_to(target, target_is_directory=target.is_dir())
                result = self.cli("score", "sound", self.dest, expected=1)
                self.assertIn("candidate symlinks", result.stderr)
                self.assertFalse(json.loads(result.stdout)["passed"])
                link.unlink()
        alias = self.root / "alias"
        alias.symlink_to(self.dest, target_is_directory=True)
        self.assertIn("candidate symlinks", self.cli("score", "sound", alias, expected=1).stderr)

    def test_stdlib_shadow_cannot_forge_assertion_results(self):
        self.select("sound")
        self.setup_candidate()
        hidden = self.tasks / "sound/hidden_tests/test_hidden.py"
        hidden.write_text("import unittest\nfrom fractions import Fraction\nfrom mathkit import bump\n"
                          "class Hidden(unittest.TestCase):\n"
                          "    def test_x(self): self.assertEqual(Fraction(bump(2)), Fraction(3))\n")
        fake = ("class Fraction:\n    def __init__(self, value): pass\n"
                "    def __eq__(self, other): return True\n")
        (self.dest / "fractions.py").write_text(fake)
        score = json.loads(self.cli("score", "sound", self.dest, expected=1).stdout)
        self.assertEqual(score["failures"], 1)
        # The same attempted bypass cannot certify a wrong reference solution.
        solution = self.tasks / "sound/solution"
        shutil.copyfile(self.fixture / "mathkit.py", solution / "mathkit.py")
        (solution / "fractions.py").write_text(fake)
        self.assertIn("solution fails hidden tests", self.cli("selfcheck", expected=1).stdout)

    def test_help_documents_strict_layout_for_task_authors(self):
        for args in (("--help",), ("selfcheck", "--help"), ("score", "--help")):
            with self.subTest(args=args):
                help_text = self.cli(*args).stdout
                for term in ("test*.py", "__init__.py", "load_tests", "symlinks"):
                    self.assertIn(term, help_text)


    def test_deep_packages_execute_every_file(self):
        self.select("sound-parallel")
        alpha = self.tasks / "sound-parallel/hidden_tests/alpha"
        (alpha / "deep").mkdir()
        (alpha / "deep/__init__.py").write_text("")
        (alpha / "test_part.py").rename(alpha / "deep/test_part.py")
        self.cli("selfcheck")
        self.cli("setup", "sound-parallel", self.dest)
        shutil.copyfile(self.tasks / "sound-parallel/solution/mathkit.py", self.dest / "mathkit.py")
        self.assertEqual(json.loads(self.cli("score", "sound-parallel", self.dest).stdout)["tests"], 3)
        # A missing package marker at any depth must name the affected module.
        (alpha / "deep/__init__.py").unlink()
        result = self.cli("score", "sound-parallel", self.dest, expected=1)
        self.assertIn("alpha/deep/test_part.py", result.stderr)
        self.assertIn("alpha/deep/test_part.py", self.cli("selfcheck", expected=1).stdout)

    def test_package_markers_cannot_contribute_ignored_tests(self):
        self.setup_candidate()
        self.solve()
        nested = self.tasks / "sound/hidden_tests/nested"
        nested.mkdir()
        (nested / "__init__.py").write_text(
            "import unittest\nclass Extra(unittest.TestCase):\n    def test_pass(self): pass\n")
        result = self.cli("score", "sound", self.dest, expected=1)
        self.assertIn("package markers must not define tests", result.stderr)
        self.assertFalse(json.loads(result.stdout)["passed"])

    def test_symlink_loop_destination_returns_json(self):
        self.dest.symlink_to(self.dest)
        result = self.cli("score", "sound", self.dest, expected=1)
        self.assertFalse(json.loads(result.stdout)["passed"])
        self.assertIn("symlink", result.stderr.lower())

    def test_invalid_utf8_candidate_output_remains_diagnostic(self):
        self.setup_candidate()
        self.solve()
        with (self.dest / "mathkit.py").open("a") as stream:
            stream.write("\nimport os\nos.write(1, b'\\xff')\n")
        self.assertTrue(json.loads(self.cli("score", "sound", self.dest).stdout)["passed"])


if __name__ == "__main__":
    unittest.main()
