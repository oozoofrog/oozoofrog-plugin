#!/usr/bin/env python3
"""Check that spec and domain IDs reach the plan and the tests.

Definitions. Table rows inside fenced code blocks are ignored.
  An ID is defined in the first cell of a Markdown table row:
    AC-<goal>.<n> in spec files, for example "| AC-1.2 | MUST | ... |"
    R<n>          in domain files, for example "| R4 | ... |"
  A row is retired when another of its cells is exactly "Retired", or
  starts with "Retired (YYYY-MM-DD):". A retired ID needs no plan reference
  and no test. A plan that still references it gets a note, not a failure.

Plan references. A plan references an ID only in a table cell that holds
nothing but IDs, separated by commas, semicolons or spaces, for example
"| AC-1.1, AC-1.2, R1 |". Prose such as "Cloudflare R2" is not a reference.
Ranges are not expanded.

Test names, static scan (default). The token of AC-1.2 is ac1_2; the token of
R4 is r4. Text is compared in lower case. Only files with known source
suffixes under the tests folder are searched. Only test declarations count:
  - a definition name: after def, async def, func (Go methods too), fn, fun,
    function or void, a name that is the token, or "test"/"test_" and then
    the token. After the token comes "_", "(", a letter or the end, never a
    digit. For example def test_ac1_2_rejects(, func TestAC1_2Rejects(,
    func testAC1_2Rejects(, public void ac1_2_rejects(. A test class
    "class Test<token>..." also counts.
  - a title: the first string argument of a declaration in TEST_DECLARATIONS,
    when it starts with the token or the literal ID and then the closing
    quote, a space, "_", ":" or "-". For example it("AC-1.2 rejects"),
    it "AC-1.2 rejects" do, test.each(rows)("ac1_2 %s"), t.Run("ac1_2", f),
    @Test("AC-1.2 ..."), @DisplayName("AC-1.2 ..."), @Suite("AC-1.2"),
    @ParameterizedTest(name = "AC-1.2 {0}"), fun `ac1_2 rejects`().
  - in .feature files: "Scenario: AC-1.2 ..." or "Scenario Outline: ...".
Not test names: a variable (ac1_2 = 3), a call site (x = ac1_2_helper(3)), a
string outside a declaration (d['r1'], log('ac1_2 ...')), a longer name
(xac1_2), and AC-1.20 for AC-1.2. Line comments that start with #, // or --
outside quotes are removed first. Limits of this best-effort scan: block
comments and multi-line strings are not removed; quote tracking stops at the
end of a line; a declaration split over two lines is not seen; a helper
defined with a token name (def ac1_2_helper) counts.

Test names, real inventory (--names-from CMD). CMD is split with shlex and
run without a shell in the current directory (run trace.py from the
repository root), with a timeout (--names-timeout, default 120 s). Each
non-empty stdout line is one test name. A token or ID counts when it starts
the name, or starts a segment after "::", "/", ".", a space or "#",
optionally after "test"/"test_", never followed by a digit. This replaces
the static scan. Commands that list test names:
  pytest --collect-only -q    tests/test_x.py::test_ac1_2_rejects
  go test -list .             TestAC1_2Rejects
  swift test list             ItemsTests.ItemsTests/testAC1_2Rejects
"npx jest --listTests" lists test files, not test names, so it does not work.
A command that cannot start, exits non-zero, times out or prints nothing
gives INCONCLUSIVE with its exit code and the first 5 stderr lines.

Fails when: an ID is defined twice; an active ID is in no plan; a plan
references an unknown ID; an active ID has no test name.

Exit codes: 0 PASS, 1 FAIL, 2 INCONCLUSIVE (no IDs; the tests folder is
missing and --no-tests is not set; the names command failed; or a document
is not UTF-8), 3 usage error. Known problems give FAIL even when the test
check is inconclusive; the inconclusive reasons are listed as well.
"""
from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

PASS, FAIL, INCONCLUSIVE, USAGE = 0, 1, 2, 3
STATUS = {PASS: "PASS", FAIL: "FAIL", INCONCLUSIVE: "INCONCLUSIVE"}
SOURCE_SUFFIXES = {
    ".c", ".cc", ".cpp", ".cs", ".dart", ".ex", ".exs", ".feature", ".go", ".groovy", ".h",
    ".hurl", ".java", ".js", ".jsx", ".kt", ".kts", ".m", ".mjs", ".php", ".py", ".rb", ".rs",
    ".scala", ".sh", ".swift", ".ts", ".tsx",
}
AC_ID = re.compile(r"AC-\d+\.\d+")
RULE_ID = re.compile(r"R\d+")
ID_CELL = re.compile(r"(?:AC-\d+\.\d+|R\d+)(?:[\s,;]+(?:AC-\d+\.\d+|R\d+))*")
FENCE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
RETIRED = re.compile(r"retired(?: \(\d{4}-\d{2}-\d{2}\):.*)?", re.IGNORECASE)
UNREADABLE: list[str] = []
BLANK = r"[ \t]"
TEST_DECLARATIONS = {
    "it, test, describe, context, specify (.only, .skip, .todo, .concurrent, .each)":
        rf"(?<![\w$.])(?:it|test|describe|context|specify)(?:\.(?:only|skip|todo|concurrent))*"
        rf"(?:\.each{BLANK}*(?:\(.*?\)|`[^`]*`))?(?:{BLANK}*\({BLANK}*|{BLANK}+)",
    "t.Run, s.Run": rf"(?<![\w$.])[ts]\.run{BLANK}*\({BLANK}*",
    "@Test, @DisplayName, @Suite": rf"@(?:test|displayname|suite){BLANK}*\({BLANK}*",
    "@ParameterizedTest(name = ...)": rf"@parameterizedtest{BLANK}*\({BLANK}*name{BLANK}*={BLANK}*",
    "Kotlin fun with a backtick name": rf"(?<![\w$.])fun{BLANK}+(?=`)",
}
DEFINITION = rf"(?<![\w$.])(?:def|func|fn|fun|function|void){BLANK}+(?:\([^)\n]*\){BLANK}*)?"
COMMENT_STARTS = ("#", "//", "--")


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        self.exit(USAGE, f"{self.prog}: error: {message}\n")


def markdown_files(folder: Path) -> list[Path]:
    return sorted(path for path in folder.rglob("*.md") if path.is_file()) if folder.is_dir() else []


def read_document(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        UNREADABLE.append(f"cannot read document: {path} is not UTF-8 (byte {error.start})")
        return ""


def table_rows(path: Path) -> list[list[str]]:
    rows = []
    fence = None
    for line in read_document(path).splitlines():
        marker = FENCE.match(line)
        if marker:
            value = marker.group(1)
            if fence is None:
                fence = value
            elif value[0] == fence[0] and len(value) >= len(fence):
                fence = None
            continue
        if fence is None and line.strip().startswith("|"):
            rows.append([cell.strip() for cell in line.strip().strip("|").split("|")])
    return rows


def defined_ids(folder: Path, pattern: re.Pattern[str]) -> tuple[list[str], list[str], set[str]]:
    ids: list[str] = []
    duplicates: list[str] = []
    retired: set[str] = set()
    for path in markdown_files(folder):
        for cells in table_rows(path):
            if not pattern.fullmatch(cells[0]):
                continue
            identifier = cells[0]
            if identifier in ids:
                if identifier not in duplicates:
                    duplicates.append(identifier)
            else:
                ids.append(identifier)
            if any(RETIRED.fullmatch(cell) for cell in cells[1:]):
                retired.add(identifier)
    return ids, duplicates, retired


def plan_references(path: Path) -> set[str]:
    found: set[str] = set()
    for cells in table_rows(path):
        for cell in cells:
            if ID_CELL.fullmatch(cell):
                found |= set(AC_ID.findall(cell)) | set(RULE_ID.findall(cell))
    return found


def test_token(identifier: str) -> str:
    if identifier.startswith("AC-"):
        return "ac" + identifier[3:].replace(".", "_")
    return identifier.lower()


def strip_line_comment(line: str) -> str:
    quote = None
    index = 0
    while index < len(line):
        character = line[index]
        if quote:
            if character == "\\":
                index += 2
                continue
            if character == quote:
                quote = None
        elif character in "\"'`":
            quote = character
        elif line.startswith(COMMENT_STARTS, index):
            return line[:index]
        index += 1
    return line


def source_text(path: Path) -> str:
    lines = path.read_text(encoding="utf-8", errors="replace").lower().splitlines()
    return "\n".join(strip_line_comment(line) for line in lines)


def declaration_patterns(identifier: str) -> tuple[re.Pattern[str], re.Pattern[str]]:
    token = re.escape(test_token(identifier))
    literal = re.escape(identifier.lower())
    name = rf"(?:test_?)?{token}(?![0-9])"
    title = rf"[\"'`](?:{token}|{literal})(?=[\"'`\s_:\-])"
    declarations = "|".join(f"(?:{opener})" for opener in TEST_DECLARATIONS.values())
    code = rf"{DEFINITION}{name}|(?<![\w$.])class{BLANK}+test_?{token}(?![0-9])|(?:{declarations}){title}"
    scenario = rf"(?m)^{BLANK}*scenario(?:{BLANK}+outline)?{BLANK}*:{BLANK}*(?:{token}|{literal})(?=[\s_:\-]|$)"
    return re.compile(code), re.compile(scenario)


def inventory_pattern(identifier: str) -> re.Pattern[str]:
    token = re.escape(test_token(identifier))
    literal = re.escape(identifier.lower())
    return re.compile(rf"(?:^|::|[/.\s#])(?:test_?)?(?:{token}|{literal})(?![0-9])")


def stderr_lines(stderr: str | bytes | None) -> list[str]:
    if isinstance(stderr, bytes):
        stderr = stderr.decode("utf-8", errors="replace")
    return [f"stderr: {line}" for line in (stderr or "").splitlines() if line.strip()][:5]


def list_test_names(command: str, timeout: float) -> tuple[list[str], list[str]]:
    argv = shlex.split(command)
    try:
        result = subprocess.run(argv, cwd=Path.cwd(), capture_output=True, text=True, encoding="utf-8",
                                errors="replace", timeout=timeout, check=False)
    except subprocess.TimeoutExpired as error:
        return [], [f"names command timed out after {timeout:g} s (exit: none): {argv[0]}"] + stderr_lines(error.stderr)
    except OSError as error:
        return [], [f"names command could not start (exit: none): {argv[0]}: {error.strerror or error}"]
    names = [line.strip().lower() for line in result.stdout.splitlines() if line.strip()]
    if result.returncode != 0:
        return [], [f"names command exited {result.returncode}: {argv[0]}"] + stderr_lines(result.stderr)
    if not names:
        return [], [f"names command printed no test names (exit 0): {argv[0]}"] + stderr_lines(result.stderr)
    return names, []


def run(args: argparse.Namespace) -> tuple[int, str, list[str], dict[str, int]]:
    docs = Path(args.docs)
    spec = Path(args.spec) if args.spec else docs / "spec"
    domain = Path(args.domain) if args.domain else docs / "domain"
    plan = Path(args.plan) if args.plan else docs / "plan"
    criteria, duplicate_criteria, retired_criteria = defined_ids(spec, AC_ID)
    rules, duplicate_rules, retired_rules = defined_ids(domain, RULE_ID)
    ids = criteria + rules
    retired = retired_criteria | retired_rules
    active = [identifier for identifier in ids if identifier not in retired]
    counts = {"criteria": len(criteria), "rules": len(rules), "retired": len(retired)}
    if not ids:
        return INCONCLUSIVE, f"no IDs defined in {spec} or {domain}", list(UNREADABLE), counts

    problems = [f"defined twice: {identifier}" for identifier in duplicate_criteria + duplicate_rules]
    plan_files = markdown_files(plan)
    if not plan_files:
        problems.append(f"no plan files in {plan}")
    planned: set[str] = set()
    for path in plan_files:
        planned |= plan_references(path)
    problems += [f"not in any plan: {identifier}" for identifier in active if identifier not in planned]
    problems += [f"plan references unknown ID: {identifier}" for identifier in sorted(planned - set(ids))]
    notes = [f"note: plan still references retired ID: {identifier}" for identifier in ids
             if identifier in retired and identifier in planned]

    reasons: list[str] = []
    missing: list[str] | None = None
    if args.no_tests:
        tests_summary = "tests not scanned (--no-tests)"
    elif args.names_from is not None:
        names, reasons = list_test_names(args.names_from, args.names_timeout)
        tests_summary = "test names not listed"
        if names:
            missing = [identifier for identifier in active
                       if not any(inventory_pattern(identifier).search(name) for name in names)]
            tests_summary = f"{len(active) - len(missing)}/{len(active)} active IDs in {len(names)} listed test names"
    else:
        tests = Path(args.tests)
        tests_summary = "tests not scanned"
        if not tests.is_dir():
            reasons = [f"tests directory missing: {tests} (use --no-tests to check documents only)"]
        else:
            files = [path for path in sorted(tests.rglob("*"))
                     if path.is_file() and path.suffix.lower() in SOURCE_SUFFIXES]
            code_text = "\n".join(source_text(path) for path in files if path.suffix.lower() != ".feature")
            feature_text = "\n".join(source_text(path) for path in files if path.suffix.lower() == ".feature")
            missing = []
            for identifier in active:
                code, scenario = declaration_patterns(identifier)
                if not (code.search(code_text) or scenario.search(feature_text)):
                    missing.append(identifier)
            tests_summary = f"{len(active) - len(missing)}/{len(active)} active IDs have tests"
    if missing is not None:
        problems += [f"no test name starts with `{test_token(identifier)}`: {identifier}" for identifier in missing]
        counts["tested"] = len(active) - len(missing)
    if UNREADABLE:
        tests_summary += f", {len(UNREADABLE)} unreadable"
    if problems:
        code = FAIL
    elif reasons or UNREADABLE:
        code = INCONCLUSIVE
    else:
        code = PASS
    return code, summary(counts, tests_summary), problems + UNREADABLE + reasons + notes, counts


def summary(counts: dict[str, int], tests_summary: str) -> str:
    return (f"{counts['criteria']} acceptance criteria, {counts['rules']} rules, "
            f"{counts['retired']} retired, {tests_summary}")


def main() -> int:
    parser = Parser(prog="trace.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--docs", default="docs", help="documents root (default: docs)")
    parser.add_argument("--spec", help="spec folder (default: <docs>/spec)")
    parser.add_argument("--domain", help="domain folder (default: <docs>/domain)")
    parser.add_argument("--plan", help="plan folder (default: <docs>/plan)")
    parser.add_argument("--tests", default="tests", help="tests folder to scan for test names (default: tests)")
    test_source = parser.add_mutually_exclusive_group()
    test_source.add_argument("--no-tests", action="store_true", help="check the documents only; skip the test check")
    test_source.add_argument("--names-from", metavar="CMD",
                             help="list real test names with CMD (split with shlex, no shell) instead of the static scan")
    parser.add_argument("--names-timeout", type=float, default=120.0, metavar="SECONDS",
                        help="timeout for --names-from (default: 120)")
    parser.add_argument("--json", action="store_true", help="print one JSON object instead of text")
    args = parser.parse_args()
    if args.names_from is not None:
        try:
            if not shlex.split(args.names_from):
                parser.error("--names-from needs a command")
        except ValueError as error:
            parser.error(f"--names-from: {error}")
    if args.names_timeout <= 0:
        parser.error("--names-timeout must be positive")
    code, text, problems, counts = run(args)
    if args.json:
        notes = [line for line in problems if line.startswith("note: ")]
        problems = [line for line in problems if not line.startswith("note: ")]
        print(json.dumps({"status": STATUS[code], "summary": text, "problems": problems, "notes": notes,
                          "counts": counts}))
    else:
        print(f"trace: {STATUS[code]} — {text}")
        for problem in problems:
            print(problem)
    return code


if __name__ == "__main__":
    sys.exit(main())
