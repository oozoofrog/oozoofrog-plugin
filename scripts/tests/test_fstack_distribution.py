from __future__ import annotations

import hashlib
import json
import re
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from test_document_links import local_targets

REPO_ROOT = Path(__file__).resolve().parents[2]
NAME = "fstack"
PLUGIN = REPO_ROOT / "plugins" / NAME
SKILL = PLUGIN / "skills" / NAME
TRACE = SKILL / "scripts" / "trace.py"
PLAYBOOKS = {"kickoff", "design-docs", "prototype", "build", "fix", "review", "drive", "checkpoint",
             "figure-it-out", "reflect", "wrap-up"}
PRINCIPLES = {"see-it-fail", "real-surface", "fix-the-cause", "label-the-claim", "decide-and-record",
              "stop-at-gates", "rules-as-written", "smallest-sufficient-change", "verifiable-units",
              "trace-by-id", "encode-in-checks", "evidence-before-change"}
REFERENCES = {"dials", "report", "doc-templates", "records", "review", "delegation", "sources"}
PACKAGE_PATH = re.compile(r"`((?:playbooks|principles|references|scripts)/[^`\s]+)`")
MODEL_ID = re.compile(r"claude-(?:opus|sonnet|haiku|fable)-\d|gemini-\d|gpt-\d")
CURSOR_ONLY = ("bugbot", ".cursor/", "/loop", "AskQuestion", "poteto-agent", "pstack-models")
TRIGGER_SHA256 = "04e53b288ae1abdbb7a83fee2d0cb530d2236498ce8526c307950d24f0edeb1a"
MIT_TEMPLATE = """MIT License

Copyright (c) 2026 {holder}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE."""
DUAL_BRAIN_TERMS = ("dual-brain", "Right Brain", "Left Brain", "MEMORY.md", "Hot Memory")
CREDIT_FILES = {"sources.md", "NOTICE.md"}


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def package_files() -> set[str]:
    return {path.relative_to(PLUGIN).as_posix() for path in PLUGIN.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts and path.name != ".DS_Store"}


def assert_executable(case: unittest.TestCase, path: Path) -> None:
    mode = subprocess.run(["git", "ls-files", "-s", str(path.relative_to(REPO_ROOT))], cwd=REPO_ROOT,
                          capture_output=True, text=True, check=True).stdout.split(" ")[0]
    if mode:
        case.assertEqual("100755", mode, path)
    else:
        case.assertTrue(path.stat().st_mode & 0o111, path)


def skill_description() -> str:
    line = read(SKILL / "SKILL.md").split("\n")[2]
    prefix = "description: "
    assert line.startswith(prefix), line
    return json.loads(line[len(prefix):])


def section(text: str, heading: str) -> str:
    return text.split(f"\n{heading}\n", 1)[1].split("\n## ", 1)[0]


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


class FstackDistributionTests(unittest.TestCase):
    def test_trigger_text_and_metadata_match_on_every_surface(self) -> None:
        description = skill_description()
        self.assertEqual(TRIGGER_SHA256, hashlib.sha256(description.encode("utf-8")).hexdigest(),
                         "The trigger text changed; update every surface and this pin together, on purpose.")
        codex = json.loads(read(PLUGIN / ".codex-plugin/plugin.json"))
        claude = json.loads(read(PLUGIN / ".claude-plugin/plugin.json"))
        sibling = json.loads(read(REPO_ROOT / "plugins/refactor/.codex-plugin/plugin.json"))
        marketplace = json.loads(read(REPO_ROOT / ".claude-plugin/marketplace.json"))
        (entry,) = [plugin for plugin in marketplace["plugins"] if plugin["name"] == NAME]
        for value in (codex["description"], codex["interface"]["longDescription"], claude["description"],
                      entry["description"]):
            self.assertEqual(description, value)
        self.assertIn(description, section(read(REPO_ROOT / "README.md"), "## fstack"))
        self.assertNotIn("disable-model-invocation", read(SKILL / "SKILL.md"))
        for manifest in (codex, claude):
            self.assertEqual(NAME, manifest["name"])
            self.assertEqual("0.1.0", manifest["version"])
            self.assertEqual("https://github.com/oozoofrog/oozoofrog-plugin", manifest["repository"])
            self.assertEqual(sibling["author"], manifest["author"])
        for key in ("hooks", "mcpServers", "apps"):
            self.assertNotIn(key, codex)
        self.assertEqual("productivity", entry["category"])
        interface = codex["interface"]
        self.assertEqual("fstack", interface["displayName"])
        self.assertEqual("Match pace and spec depth to risk; prove each step", interface["shortDescription"])
        self.assertEqual(["Read", "Write"], interface["capabilities"])
        metadata = {}
        for line in read(SKILL / "agents/openai.yaml").splitlines():
            if line.startswith("  "):
                key, value = line.strip().split(": ", 1)
                metadata[key] = json.loads(value)
        self.assertEqual({"display_name", "short_description", "default_prompt"}, set(metadata))
        self.assertEqual(metadata["display_name"], interface["displayName"])
        self.assertEqual(metadata["short_description"], interface["shortDescription"])
        self.assertEqual([metadata["default_prompt"]], interface["defaultPrompt"])
        self.assertIn("$" + NAME, metadata["default_prompt"])
        self.assertLessEqual(len(metadata["default_prompt"]), 128)

    def test_package_contains_exactly_the_designed_files(self) -> None:
        expected = {".claude-plugin/plugin.json", ".codex-plugin/plugin.json"} | {
            f"skills/{NAME}/{path}" for path in (
                {"SKILL.md", "NOTICE.md", "agents/openai.yaml", "scripts/trace.py"}
                | {f"playbooks/{name}.md" for name in PLAYBOOKS}
                | {f"principles/{name}.md" for name in PRINCIPLES}
                | {f"references/{name}.md" for name in REFERENCES})}
        self.assertEqual(expected, {path for path in package_files() if not path.startswith("evals/")})
        assert_executable(self, TRACE)
        for path in PLUGIN.rglob("*"):
            self.assertFalse(path.is_symlink(), path)

    def test_evals_have_the_case_layout(self) -> None:
        evals = PLUGIN / "evals"
        self.assertTrue((evals / "README.md").is_file())
        self.assertIn("results/", read(evals / ".gitignore").split())
        self.assertEqual([], [path for path in PLUGIN.rglob("results") if path.is_dir()])
        fixtures = sorted((evals / "_fixtures").iterdir())
        self.assertTrue(fixtures)
        for path in fixtures:
            with self.subTest(fixture=path.name):
                self.assertTrue(path.is_file() and path.suffix == ".sh", path)
                assert_executable(self, path)
        cases = [path for path in sorted(evals.iterdir()) if path.name not in {"README.md", ".gitignore", "_fixtures"}]
        self.assertTrue(cases)
        for case in cases:
            with self.subTest(case=case.name):
                self.assertTrue(case.is_dir(), case)
                names = {path.name for path in case.iterdir()}
                self.assertLessEqual({"prompt.md", "graders"}, names)
                self.assertLessEqual(names, {"prompt.md", "graders", "case.yaml", "scaffold.sh"})
                self.assertTrue((case / "prompt.md").is_file())
                graders = sorted((case / "graders").iterdir())
                self.assertTrue(graders)
                for grader in graders:
                    self.assertTrue(grader.is_file() and grader.suffix == ".md", grader)

    def test_router_is_a_short_index_that_maps_one_to_one(self) -> None:
        router = read(SKILL / "SKILL.md")
        self.assertLessEqual(len(router.splitlines()), 120)
        for heading, folder, names in (("## Playbooks", "playbooks", PLAYBOOKS),
                                       ("## Principles", "principles", PRINCIPLES)):
            with self.subTest(index=folder):
                bullets = [line for line in section(router, heading).splitlines() if line.startswith("- **")]
                listed = [re.search(rf"\(`{folder}/([a-z-]+)\.md`\)", line).group(1) for line in bullets]
                self.assertEqual(sorted(names), sorted(listed))
                self.assertEqual(names, {path.stem for path in (SKILL / folder).glob("*.md")})

    def test_every_package_path_and_link_exists(self) -> None:
        for document in SKILL.rglob("*.md"):
            text = read(document)
            for target in PACKAGE_PATH.findall(text):
                with self.subTest(document=document.name, target=target):
                    self.assertTrue((SKILL / target).is_file())
            for target in local_targets(text):
                with self.subTest(document=document.name, link=target):
                    self.assertTrue((document.parent / target).is_file())

    def test_playbooks_follow_the_shape(self) -> None:
        for path in sorted((SKILL / "playbooks").glob("*.md")):
            with self.subTest(playbook=path.stem):
                lines = read(path).splitlines()
                content = [line for line in lines if line.strip()]
                self.assertRegex(lines[0], r"^### \S")
                self.assertTrue(lines[1].startswith("**You own "), lines[1])
                steps = [line for line in lines if re.match(r"^\d+\. ", line)]
                self.assertGreaterEqual(len(steps), 3)
                self.assertLessEqual(len(content), 25)
                self.assertTrue(content[-1].startswith("**Report:** "), content[-1])
                if path.stem != "wrap-up":
                    self.assertTrue(any("playbooks/wrap-up.md" in step for step in steps))

    def test_principles_follow_the_shape(self) -> None:
        for path in sorted((SKILL / "principles").glob("*.md")):
            with self.subTest(principle=path.stem):
                text = read(path)
                lines = text.splitlines()
                self.assertRegex(lines[0], r"^# \S")
                self.assertTrue(lines[2].strip())
                for label in ("**Why:**", "**How:**", "**Stop:**", "**Evidence of use:**"):
                    self.assertIn("\n" + label, text)
                how = text.split("**How:**", 1)[1].split("**Stop:**", 1)[0]
                self.assertIn("\n- ", how)
                self.assertLessEqual(len([line for line in lines if line.strip()]), 20)
                self.assertNotIn("trealworld", text)

    def test_no_model_ids_or_cursor_only_features(self) -> None:
        for path in PLUGIN.rglob("*"):
            if not path.is_file() or path.suffix == ".pyc":
                continue
            text = read(path)
            with self.subTest(file=path.relative_to(PLUGIN).as_posix()):
                self.assertIsNone(MODEL_ID.search(text))
                if path.name not in CREDIT_FILES:
                    for term in CURSOR_ONLY:
                        self.assertNotIn(term, text)

    def test_notice_and_sources_cover_licenses_and_files(self) -> None:
        notice = read(SKILL / "NOTICE.md")
        self.assertEqual(3, notice.count("MIT License"))
        blocks = re.findall(r"```text\n(.*?)\n```", notice, re.DOTALL)
        self.assertEqual([MIT_TEMPLATE.format(holder=holder) for holder in ("Lauren Tan", "Toby Lee", "Hanmin Kim")],
                         blocks)
        for name in ("Copyright (c) 2026 Lauren Tan", "Copyright (c) 2026 Toby Lee", "Copyright (c) 2026 Hanmin Kim",
                     "https://github.com/cursor/plugins", "https://github.com/tobyilee/tstack",
                     "https://github.com/sleeplesshan/dual-brain", "references/sources.md"):
            self.assertIn(name, notice)
        sources = read(SKILL / "references/sources.md")
        for folder, names in (("playbooks", PLAYBOOKS), ("principles", PRINCIPLES), ("references", REFERENCES)):
            for name in names:
                self.assertIn(f"`{folder}/{name}.md`", sources)
        for pin in ("cursor/plugins@7a583913eb1b", "tobyilee/tstack@868dda2373da", "sleeplesshan/dual-brain", "v1.7.0"):
            self.assertIn(pin, sources)
        rows = {line.split(" | ")[0].strip("| `"): line for line in sources.splitlines() if line.startswith("| `")}
        for changed in ("principles/evidence-before-change.md", "playbooks/review.md", "playbooks/fix.md",
                        "playbooks/reflect.md", "playbooks/wrap-up.md", "principles/real-surface.md",
                        "references/review.md", "references/delegation.md", "references/records.md",
                        "references/report.md", "NOTICE.md"):
            self.assertIn(" D `", rows[changed])

    def test_frame_and_next_step_lines_are_literal_templates(self) -> None:
        for relative in ("SKILL.md", "references/dials.md"):
            text = read(SKILL / relative)
            with self.subTest(document=relative):
                self.assertIn("visible reply text right after", text)
                self.assertIn("before your next tool call and before any action that changes files", text)
                self.assertIn("`Pace: step · Spec: T1 — internal bug with a clear repro`", text)
                self.assertIn("`Pace: step · Spec: T1 — 재현되는 내부 버그`", text)
        for path in SKILL.rglob("*.md"):
            with self.subTest(document=path.name):
                self.assertNotRegex(read(path), r"\bfirst message\b(?! after)")
        self.assertIn("the last line of the report is the next-step line", read(SKILL / "references/report.md"))
        for relative in ("references/report.md", "SKILL.md", "playbooks/wrap-up.md"):
            text = read(SKILL / relative)
            for template in ("`Next step: <candidate>`", "`다음 단계: <후보>`"):
                with self.subTest(document=relative, template=template):
                    self.assertIn(template, text)

    def test_trace_runs_from_the_project_root_with_an_absolute_script_path(self) -> None:
        form = 'python3 -I -B "<skill-dir>/scripts/trace.py"'
        for relative in ("SKILL.md", "playbooks/design-docs.md", "playbooks/build.md", "playbooks/checkpoint.md",
                         "principles/trace-by-id.md"):
            text = read(SKILL / relative)
            with self.subTest(document=relative):
                self.assertIn(form, text)
                self.assertIn("project root", text)
        self.assertIn("`<skill-dir>` is the absolute directory of this `SKILL.md`", read(SKILL / "SKILL.md"))
        for path in SKILL.rglob("*.md"):
            text = read(path)
            with self.subTest(document=path.name):
                self.assertNotRegex(text, r"(?i)\brun `scripts/trace\.py")
                self.assertEqual(text.count('"<skill-dir>/scripts/trace.py"'), text.count("<skill-dir>/scripts/trace.py"))

    def test_checkpoint_handles_a_branch_without_upstream(self) -> None:
        text = read(SKILL / "playbooks/checkpoint.md")
        self.assertIn("`git rev-parse --abbrev-ref @{u}`", text)
        self.assertIn('"remote comparison unavailable: no upstream"', text)
        self.assertIn("neither an error nor a pass", text)
        self.assertNotIn("the diff against the remote", text)

    def test_skill_text_names_no_host_specific_tools(self) -> None:
        banned = ("TodoWrite", "Task tool", "subagent_type", "Skill tool", "AskUserQuestion", "Bash tool", "Edit tool",
                  "todo list")
        for path in SKILL.rglob("*"):
            if not path.is_file() or path.name in CREDIT_FILES or path.suffix == ".pyc":
                continue
            text = read(path)
            for term in banned:
                with self.subTest(file=path.relative_to(SKILL).as_posix(), term=term):
                    self.assertNotIn(term, text)
        self.assertIn("host's skill catalog", section(read(SKILL / "SKILL.md"), "## Related skills"))

    def test_dual_brain_absorbed_not_delegated(self) -> None:
        for path in PLUGIN.rglob("*"):
            if not path.is_file() or path.suffix == ".pyc" or path.name in CREDIT_FILES:
                continue
            text = read(path)
            for term in DUAL_BRAIN_TERMS:
                with self.subTest(file=path.relative_to(PLUGIN).as_posix(), term=term):
                    self.assertNotIn(term, text)
        related = section(read(SKILL / "SKILL.md"), "## Related skills")
        self.assertNotIn("dual-brain", related)

    def test_review_delegation_and_records_carry_the_absorbed_rules(self) -> None:
        review = read(SKILL / "references/review.md")
        for heading in ("## Two-lens review", "## Macro lens brief", "## Micro lens brief", "## Reconcile"):
            self.assertIn("\n" + heading + "\n", review)
        playbook = read(SKILL / "playbooks/review.md")
        for phrase in ("one independent reviewer (default)", "two lenses (macro and micro)",
                       "one focused follow-up for each material conflict", "no actionable findings"):
            self.assertIn(phrase, playbook)
        delegation = read(SKILL / "references/delegation.md")
        for heading in ("## Without independent agents", "## Agent lifecycle"):
            self.assertIn("\n" + heading + "\n", delegation)
        records = read(SKILL / "references/records.md")
        for heading in ("## Reading records", "## Writing durable records"):
            self.assertIn("\n" + heading + "\n", records)
        self.assertIn("Do not create a new memory store.", records)

    def test_test_and_commit_rules_are_stated_where_they_apply(self) -> None:
        for relative in ("SKILL.md", "principles/see-it-fail.md", "playbooks/build.md"):
            self.assertIn("T2 tracing", read(SKILL / relative), relative)
        for relative in ("SKILL.md", "playbooks/wrap-up.md", "playbooks/drive.md", "principles/verifiable-units.md"):
            self.assertIn("drive grant", read(SKILL / relative), relative)
        self.assertNotIn("Commit or revert before the next unit", read(SKILL / "principles/verifiable-units.md"))
        self.assertIn("unless the predicate is met or a dead end was reached", read(SKILL / "playbooks/wrap-up.md"))
        g1 = "push, deploy, release, data deletion, outgoing messages, secrets, rewriting pushed history, deleting files you did not create"
        for relative in ("SKILL.md", "principles/stop-at-gates.md"):
            self.assertIn(g1, read(SKILL / relative), relative)

    def test_repository_documents_list_the_plugin(self) -> None:
        readme = read(REPO_ROOT / "README.md")
        self.assertIn(f"| `{NAME}@oozoofrog-plugin` | [Calibrate pace and spec depth to the task, prove each step, "
                      f"and record decisions](plugins/{NAME}/skills/{NAME}/SKILL.md)", readme)
        self.assertIn("Use $fstack to fix this bug: reproduce it, prove the fix, and report "
                      "decisions and evidence.", readme)
        readme_section = section(readme, "## fstack")
        self.assertIn("dual-brain (Hanmin Kim, MIT)", readme_section)
        for target in ("SKILL.md", "references/sources.md", "NOTICE.md"):
            self.assertIn(f"plugins/{NAME}/skills/{NAME}/{target}", readme_section)
        korean = section(read(REPO_ROOT / "README.ko.md"), "## fstack")
        self.assertIn(f"plugins/{NAME}/skills/{NAME}/SKILL.md", korean)
        self.assertIn("dual-brain(Hanmin Kim, MIT)", korean)
        self.assertIn("playbook 11개와 원칙 12개", korean)
        named = korean.split(" playbook 11개", 1)[0].rsplit(". ", 1)[1]
        self.assertEqual(11, len(named.split(", ")), named)
        install = section(read(REPO_ROOT / "docs/plugin-installation.md"), "## fstack")
        for command in (f"claude plugin install {NAME}@oozoofrog-plugin", f"codex plugin add {NAME}@oozoofrog-plugin"):
            self.assertIn(command, install)
        unreleased = read(REPO_ROOT / "CHANGELOG.md").split("## Unreleased\n", 1)[1].split("\n## ", 1)[0]
        first = unreleased.strip().splitlines()[0]
        for phrase in (f"Add `{NAME}` 0.1.0", "dual-brain (Hanmin Kim, MIT)", "12 principles"):
            self.assertIn(phrase, first)


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
