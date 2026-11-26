from __future__ import annotations

import json
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
NAME = "fstack"
PLUGIN = REPO_ROOT / "plugins" / NAME
SKILL = PLUGIN / "skills" / NAME
TRACE = SKILL / "scripts" / "trace.py"


def test_token(identifier: str) -> str:
    return "ac" + identifier[3:].replace(".", "_") if identifier.startswith("AC-") else identifier.lower()


def write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def trace(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, "-I", "-B", str(TRACE), "--docs", str(root / "docs"), *args],
                          cwd=root, capture_output=True, text=True, encoding="utf-8")


NAMES_SCRIPT = """import sys, time
mode = sys.argv[1]
if mode == "echo":
    print("\\n".join(sys.argv[2:]))
elif mode == "fail":
    for number in range(7):
        print(f"runner error {number}", file=sys.stderr)
    sys.exit(4)
elif mode == "sleep":
    time.sleep(10)
"""


def names_command(root: Path, mode: str, *arguments: str) -> str:
    script = root / "names_tool.py"
    script.write_text(NAMES_SCRIPT, encoding="utf-8")
    return shlex.join([sys.executable, "-I", "-B", str(script), mode, *arguments])


def consistent_fixture(root: Path) -> None:
    write(root, "docs/spec/a.md", "| ID | Keyword | Criterion | Verification |\n|---|---|---|---|\n"
                                  "| AC-1.1 | MUST | lists items | test |\n| AC-1.2 | MUST | rejects empty | test |\n")
    write(root, "docs/domain/terms.md", "| ID | Rule | Source |\n|---|---|---|\n| R1 | names are unique | AC-1.1 |\n")
    write(root, "docs/plan/p.md", "| Unit | Verification IDs |\n|---|---|\n| U1 | AC-1.1, AC-1.2, R1 |\n")
    write(root, "tests/test_items.py", "def test_ac1_1_lists():\n    pass\n\ndef test_ac1_2_rejects():\n    pass\n\n"
                                       "def test_r1_unique():\n    pass\n")


class TraceScriptTests(unittest.TestCase):
    def test_consistent_fixture_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            consistent_fixture(root)
            result = trace(root, "--tests", str(root / "tests"))
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertTrue(result.stdout.startswith("trace: PASS — "), result.stdout)

    def test_inconsistencies_fail(self) -> None:
        cases = {
            "missing plan reference": ("docs/plan/p.md", "| Unit | Verification IDs |\n|---|---|\n| U1 | AC-1.1, R1 |\n",
                                       "not in any plan: AC-1.2"),
            "missing test token": ("tests/test_items.py", "def test_ac1_1_lists():\n    pass\n\n"
                                   "def test_ac1_20_other():\n    pass\n\ndef test_r1_unique():\n    pass\n",
                                   "no test name starts with `ac1_2`: AC-1.2"),
            "duplicate ID": ("docs/spec/b.md", "| AC-1.1 | MUST | listed again | test |\n", "defined twice: AC-1.1"),
            "unknown plan reference": ("docs/plan/q.md", "| U2 | AC-9.9 |\n", "plan references unknown ID: AC-9.9"),
        }
        for name, (relative, text, problem) in cases.items():
            with self.subTest(case=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                consistent_fixture(root)
                write(root, relative, text)
                result = trace(root, "--tests", str(root / "tests"))
                self.assertEqual(1, result.returncode, result.stdout + result.stderr)
                self.assertTrue(result.stdout.startswith("trace: FAIL — "), result.stdout)
                self.assertIn(problem, result.stdout.splitlines())

    def test_missing_ids_or_tests_are_inconclusive(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write(root, "docs/spec/a.md", "No table here.\n")
            result = trace(root, "--no-tests")
            self.assertEqual(2, result.returncode, result.stdout + result.stderr)
            self.assertTrue(result.stdout.startswith("trace: INCONCLUSIVE — "), result.stdout)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            consistent_fixture(root)
            result = trace(root, "--tests", str(root / "absent"))
            self.assertEqual(2, result.returncode, result.stdout + result.stderr)

    def test_no_tests_skips_the_test_scan(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            consistent_fixture(root)
            write(root, "tests/test_items.py", "")
            self.assertEqual(1, trace(root, "--tests", str(root / "tests")).returncode)
            result = trace(root, "--no-tests", "--json")
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual("PASS", report["status"])
            self.assertEqual({"criteria": 2, "rules": 1, "retired": 0}, report["counts"])
            self.assertEqual([], report["notes"])

    def run_case(self, files: dict[str, str]) -> subprocess.CompletedProcess[str]:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        consistent_fixture(root)
        for relative, text in files.items():
            write(root, relative, text)
        return trace(root, "--tests", str(root / "tests"))

    def assert_fails_with(self, result: subprocess.CompletedProcess[str], problem: str) -> None:
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertIn(problem, result.stdout.splitlines())

    def test_only_test_name_positions_count(self) -> None:
        tests = ("def test_ac1_1_lists():\n    r1 = 3\n    assert r1\n\n"
                 "def test_ac1_2_rejects():\n    pass\n")
        self.assert_fails_with(self.run_case({"tests/test_items.py": tests}), "no test name starts with `r1`: R1")
        accepted = {
            "tests/a.test.ts": "it('ac1_1 lists', () => {})\nit(\"ac1_2: rejects\", () => {})\nit(`r1 unique`, () => {})\n",
            "tests/ItemsTest.go": "func TestAC1_1Lists(t *testing.T) {}\nfunc TestAC1_2_Rejects(t *testing.T) {}\nfunc TestR1_Unique(t *testing.T) {}\n",
        }
        for relative, text in accepted.items():
            with self.subTest(style=relative):
                result = self.run_case({"tests/test_items.py": "", relative: text})
                self.assertIn(result.returncode, (0, 1))
                missing = [line for line in result.stdout.splitlines() if line.startswith("no test name")]
                self.assertEqual([], missing)

    def test_each_accepted_test_name_style_covers_the_id(self) -> None:
        base = "def test_ac1_1_lists():\n    pass\n\ndef test_r1_unique():\n    pass\n"
        styles = {
            "Go camelCase": ("tests/items_test.go", "func TestAC1_2Rejects(t *testing.T) {}\n"),
            "XCTest camelCase": ("tests/ItemsTests.swift", "func testAC1_2Rejects() {}\n"),
            "it title with ID": ("tests/items.test.ts", 'it("AC-1.2 rejects empty", () => {})\n'),
            "Swift Testing title": ("tests/Items.swift", '@Test("AC-1.2 rejects empty") func rejects() {}\n'),
            "JUnit DisplayName": ("tests/ItemsTest.java", '@DisplayName("AC-1.2 rejects empty")\nvoid rejects() {}\n'),
            "describe with ID only": ("tests/items.spec.js", "describe('AC-1.2', () => {})\n"),
            "exact token string": ("tests/sub_test.go", 't.Run("ac1_2", func(t *testing.T) {})\n'),
            "suite Run": ("tests/suite_test.go", 's.Run("AC-1.2 rejects", func() {})\n'),
            "it.only": ("tests/a.test.ts", "it.only('ac1_2 rejects', () => {})\n"),
            "test.skip": ("tests/b.test.ts", "test.skip(\"AC-1.2: rejects\", () => {})\n"),
            "describe.each with rows": ("tests/c.test.ts", "describe.each([[1, 2]])('ac1_2 %i', () => {})\n"),
            "test.each with a template": ("tests/d.test.ts", "test.each`a | b`('AC-1.2 $a', () => {})\n"),
            "context": ("tests/e.spec.js", "context('AC-1.2 when empty', () => {})\n"),
            "specify": ("tests/f.spec.js", "specify(`ac1_2 rejects`, () => {})\n"),
            "RSpec without parentheses": ("tests/items_spec.rb", 'it "AC-1.2 rejects empty" do\nend\n'),
            "Swift Testing suite": ("tests/Suite.swift", '@Suite("AC-1.2") struct Rejects {}\n'),
            "JUnit ParameterizedTest name": ("tests/P.java", '@ParameterizedTest(name = "AC-1.2 {0}")\nvoid rejects(int n) {}\n'),
            "Kotlin backtick fun": ("tests/ItemsTest.kt", "@Test fun `ac1_2 rejects empty`() {}\n"),
            "Gherkin Scenario": ("tests/items.feature", "Feature: items\n  Scenario: AC-1.2 rejects empty\n"),
            "Gherkin Scenario Outline": ("tests/outline.feature", "  Scenario Outline: ac1_2 rejects <value>\n"),
            "async def": ("tests/test_async.py", "async def test_ac1_2_rejects():\n    pass\n"),
            "Go method": ("tests/method_test.go", "func (s *ItemsSuite) TestAC1_2Rejects() {}\n"),
            "Rust fn": ("tests/items.rs", "#[test]\nfn ac1_2_rejects_empty() {}\n"),
            "JS function": ("tests/g.test.js", "function ac1_2RejectsEmpty() {}\n"),
            "Java public void": ("tests/ItemsTest.java", "@Test\npublic void ac1_2_rejects() {}\n"),
            "test class": ("tests/test_class.py", "class TestAC1_2Rejects(unittest.TestCase):\n    pass\n"),
            "comment marker inside a string": ("tests/h.test.ts", 'const url = "http://x"; it("ac1_2 rejects", () => {})\n'),
        }
        for style, (relative, text) in styles.items():
            with self.subTest(style=style):
                result = self.run_case({"tests/test_items.py": base, relative: text})
                self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_each_rejected_test_name_style_leaves_the_id_uncovered(self) -> None:
        base = "def test_ac1_1_lists():\n    pass\n\ndef test_r1_unique():\n    pass\n"
        styles = {
            "local variable": "def test_other():\n    ac1_2 = 3\n",
            "longer name": "def test_xac1_2_rejects():\n    pass\n",
            "longer ID in a function name": "def test_ac1_20_rejects():\n    pass\n",
            "longer ID in a title": 'it("AC-1.20 rejects", () => {})\n',
            "token inside a title": 'it("rejects ac1_2", () => {})\n',
        }
        for style, text in styles.items():
            with self.subTest(style=style):
                result = self.run_case({"tests/test_items.py": base, "tests/extra.ts": text})
                self.assert_fails_with(result, "no test name starts with `ac1_2`: AC-1.2")

    def test_static_scan_ignores_strings_calls_and_comments_outside_declarations(self) -> None:
        cases = {
            "string equal to the token": ("R1", "tests/test_dict.py", "def test_other():\n    assert d['r1']\n"),
            "string in a log call": ("AC-1.2", "tests/test_log.py", "def test_other():\n    log('ac1_2 something')\n"),
            "hash comment": ("AC-1.2", "tests/test_comment.py", "# def test_ac1_2_rejects():\n"),
            "slash comment": ("AC-1.2", "tests/c_test.go", "// func TestAC1_2Rejects(t *testing.T) {}\n"),
            "trailing slash comment": ("AC-1.2", "tests/x.test.ts", "const a = 1 // it('ac1_2 rejects', () => {})\n"),
            "dash comment": ("AC-1.2", "tests/notes.kt", "-- fun ac1_2_rejects() {}\n"),
            "call site": ("AC-1.2", "tests/test_call.py", "def test_other():\n    x = ac1_2_helper(3)\n"),
            "keyword inside a longer word": ("AC-1.2", "tests/items_spec.rb", "undef test_ac1_2_rejects\n"),
            "method on another object": ("AC-1.2", "tests/y.test.ts", "page.it('ac1_2 rejects')\n"),
        }
        others = {"AC-1.1": "def test_ac1_1_lists():\n    pass\n", "AC-1.2": "def test_ac1_2_rejects():\n    pass\n",
                  "R1": "def test_r1_unique():\n    pass\n"}
        for case, (identifier, relative, text) in cases.items():
            with self.subTest(case=case):
                base = "\n".join(body for key, body in others.items() if key != identifier)
                result = self.run_case({"tests/test_items.py": base, relative: text})
                self.assert_fails_with(result, f"no test name starts with `{test_token(identifier)}`: {identifier}")

    def test_prose_starting_with_retired_does_not_retire_a_row(self) -> None:
        spec = ("| ID | Keyword | Criterion | Verification |\n|---|---|---|---|\n"
                "| AC-1.1 | MUST | lists items | test |\n| AC-1.2 | MUST | Retired accounts are hidden | test |\n")
        domain = "| ID | Rule | Source |\n|---|---|---|\n| R1 | Retired employees keep read access | ADR-2 |\n"
        plan = "| Unit | Verification IDs |\n|---|---|\n| U1 | AC-1.1 |\n"
        result = self.run_case({"docs/spec/a.md": spec, "docs/domain/terms.md": domain, "docs/plan/p.md": plan})
        self.assert_fails_with(result, "not in any plan: AC-1.2")
        self.assertIn("not in any plan: R1", result.stdout.splitlines())
        self.assertIn("0 retired", result.stdout)

    def test_bare_retired_cell_retires_and_plan_reference_gets_a_note(self) -> None:
        domain = "| ID | Rule | Source |\n|---|---|---|\n| R1 | names are unique | Retired |\n"
        plan = "| Unit | Verification IDs |\n|---|---|\n| U1 | AC-1.1, AC-1.2, R1 |\n"
        tests = "def test_ac1_1_lists():\n    pass\n\ndef test_ac1_2_rejects():\n    pass\n"
        result = self.run_case({"docs/domain/terms.md": domain, "docs/plan/p.md": plan, "tests/test_items.py": tests})
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("note: plan still references retired ID: R1", result.stdout.splitlines())

    def test_token_inside_a_longer_name_does_not_count(self) -> None:
        tests = "def test_ac1_1_lists():\n    pass\n\ndef test_xac1_2_rejects():\n    pass\n\ndef test_r1_unique():\n    pass\n"
        self.assert_fails_with(self.run_case({"tests/test_items.py": tests}), "no test name starts with `ac1_2`: AC-1.2")

    def test_only_source_files_are_searched(self) -> None:
        tests = "def test_ac1_1_lists():\n    pass\n\ndef test_r1_unique():\n    pass\n"
        result = self.run_case({"tests/test_items.py": tests, "tests/notes.md": "def test_ac1_2_rejects():\n"})
        self.assert_fails_with(result, "no test name starts with `ac1_2`: AC-1.2")

    def test_plan_prose_and_longer_ids_are_not_confused(self) -> None:
        plan = ("| Unit | Verification IDs | Notes |\n|---|---|---|\n| U1 | AC-1.1, AC-1.2, R1 | Cloudflare R2 bucket |\n\n"
                "Store uploads in Cloudflare R2 behind Route R53. See AC-7.7 for later.\n")
        result = self.run_case({"docs/plan/p.md": plan})
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        result = self.run_case({"docs/plan/p.md": "| U1 | AC-1.10, AC-1.2, R1 |\n"})
        self.assert_fails_with(result, "not in any plan: AC-1.1")
        self.assertIn("plan references unknown ID: AC-1.10", result.stdout.splitlines())

    def test_retired_ids_need_no_plan_or_test(self) -> None:
        spec = ("| ID | Keyword | Criterion | Verification |\n|---|---|---|---|\n| AC-1.1 | MUST | lists items | test |\n"
                "| AC-1.2 | Retired (2026-11-23): merged into AC-1.1 | rejects empty | — |\n")
        plan = "| Unit | Verification IDs |\n|---|---|\n| U1 | AC-1.1, R1 |\n"
        tests = "def test_ac1_1_lists():\n    pass\n\ndef test_r1_unique():\n    pass\n"
        result = self.run_case({"docs/spec/a.md": spec, "docs/plan/p.md": plan, "tests/test_items.py": tests})
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("1 retired", result.stdout)

    def test_duplicates_are_reported_once_and_fenced_rows_are_ignored(self) -> None:
        row = "| AC-1.1 | MUST | listed again | test |\n"
        result = self.run_case({"docs/spec/b.md": row * 2})
        self.assertEqual(1, result.stdout.splitlines().count("defined twice: AC-1.1"), result.stdout)
        fenced = "Example:\n\n```markdown\n| AC-1.1 | MUST | example | test |\n| AC-3.1 | MUST | example | test |\n```\n"
        result = self.run_case({"docs/spec/example.md": fenced, "docs/plan/example.md": "```\n| U9 | AC-9.9 |\n```\n"})
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_unreadable_document_and_usage_error_have_clear_exits(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            consistent_fixture(root)
            (root / "docs/spec/latin1.md").write_bytes("| AC-2.1 | MUST | caf\xe9 | test |\n".encode("latin-1"))
            result = trace(root, "--tests", str(root / "tests"))
            self.assertEqual(2, result.returncode, result.stdout + result.stderr)
            self.assertTrue(result.stdout.startswith("trace: INCONCLUSIVE — "), result.stdout)
            self.assertIn("1 unreadable", result.stdout.splitlines()[0])
            self.assertTrue(any(line.startswith("cannot read document: ") and "latin1.md" in line
                                for line in result.stdout.splitlines()), result.stdout)
            self.assertNotIn("Traceback", result.stderr)
            write(root, "docs/spec/b.md", "| AC-1.1 | MUST | listed again | test |\n")
            result = trace(root, "--tests", str(root / "tests"))
            self.assertEqual(1, result.returncode, result.stdout + result.stderr)
            self.assertIn("defined twice: AC-1.1", result.stdout.splitlines())
            self.assertTrue(any(line.startswith("cannot read document: ") for line in result.stdout.splitlines()))
            result = trace(root, "--unknown-flag")
            self.assertEqual(3, result.returncode, result.stdout + result.stderr)
            self.assertIn("usage:", result.stderr)


class NamesFromTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        consistent_fixture(self.root)

    def run_names(self, mode: str, *arguments: str, extra: tuple[str, ...] = ()) -> subprocess.CompletedProcess[str]:
        return trace(self.root, "--names-from", names_command(self.root, mode, *arguments), *extra)

    def test_listed_names_replace_the_static_scan(self) -> None:
        result = self.run_names("echo", "tests/test_items.py::test_ac1_1_lists",
                                "ItemsTests.ItemsTests/testAC1_2Rejects", "TestR1Unique")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("3/3 active IDs in 3 listed test names", result.stdout)
        result = self.run_names("echo", "tests/test_items.py::test_ac1_1_lists", "TestR1Unique")
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertIn("no test name starts with `ac1_2`: AC-1.2", result.stdout.splitlines())

    def test_listed_names_that_only_resemble_the_id_miss(self) -> None:
        result = self.run_names("echo", "test_ac1_1_lists", "test_r1_unique", "tests/test_x.py::test_ac1_20_other",
                                "suite/xac1_2_rejects", "helper_ac1_2", "AC-1.20 rejects")
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertIn("no test name starts with `ac1_2`: AC-1.2", result.stdout.splitlines())
        result = self.run_names("echo", "test_ac1_1_lists", "test_r1_unique", "Items #AC-1.2 rejects")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_failing_command_is_inconclusive_with_exit_code_and_stderr(self) -> None:
        result = self.run_names("fail")
        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        lines = result.stdout.splitlines()
        self.assertTrue(lines[0].startswith("trace: INCONCLUSIVE — "), lines[0])
        self.assertTrue(any(line.startswith("names command exited 4: ") for line in lines), lines)
        self.assertEqual([f"stderr: runner error {number}" for number in range(5)],
                         [line for line in lines if line.startswith("stderr: ")])

    def test_empty_output_is_inconclusive(self) -> None:
        result = self.run_names("echo")
        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        self.assertTrue(any(line.startswith("names command printed no test names (exit 0): ")
                            for line in result.stdout.splitlines()), result.stdout)

    def test_timeout_is_inconclusive(self) -> None:
        result = self.run_names("sleep", extra=("--names-timeout", "0.5"))
        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        self.assertTrue(any(line.startswith("names command timed out after 0.5 s (exit: none): ")
                            for line in result.stdout.splitlines()), result.stdout)

    def test_missing_command_is_inconclusive(self) -> None:
        result = trace(self.root, "--names-from", "fstack-no-such-command-for-trace")
        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        self.assertTrue(any(line.startswith("names command could not start (exit: none): ")
                            for line in result.stdout.splitlines()), result.stdout)

    def test_quoted_argument_stays_one_name(self) -> None:
        result = self.run_names("echo", "test_ac1_1_lists", "test_r1_unique", "test_ac1_2 rejects empty input")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_shell_syntax_is_not_interpreted(self) -> None:
        marker = shlex.quote(str(self.root / "shell-ran"))
        command = names_command(self.root, "echo", "test_ac1_1_lists", "test_ac1_2_rejects", "test_r1_unique")
        hostile = f" ; touch {marker} && touch {marker} | touch {marker} $(touch {marker}) `touch {marker}`"
        result = trace(self.root, "--names-from", command + hostile)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertFalse((self.root / "shell-ran").exists())

    def test_usage_errors(self) -> None:
        for arguments in (("--names-from", ""), ("--names-from", "x", "--no-tests"),
                          ("--names-from", "x", "--names-timeout", "0"), ("--names-from", "'unclosed")):
            with self.subTest(arguments=arguments):
                result = trace(self.root, *arguments)
                self.assertEqual(3, result.returncode, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
