#!/usr/bin/env python3
"""Prepare evaluation tasks and grade candidates with external unittest suites.

Strict hidden_tests layout: every .py file except __init__.py must be named
test*.py (with an importable module name), be loaded, and execute at least one
unittest test. Nested directories must be regular packages with __init__.py.
Package markers must not define tests. load_tests hooks and symlinks in hidden
tests or candidates are refused. Hidden suites stay in their source directory.

Standard-library imports take precedence over candidate modules. Tests must use
ordinary unittest TestCase/Suite execution. This is not a sandbox against
deliberately hostile code: monkeypatching the harness, tampering with trusted
files/verdicts, filesystem races, subprocess side effects, and resource exhaustion
are outside its guarantees. Selfcheck proves each hidden file rejects the start
alone for multipart tasks; it cannot infer semantic coverage of the named parts.
"""

import argparse
from collections import Counter
import fnmatch
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tokenize


BASE = Path(__file__).resolve().parent
CATEGORIES = ("single", "chain", "review", "parallel")

# A fresh interpreter prevents candidate imports leaking between task states.
TEST_PROCESS = r'''
import contextlib
import importlib
import io
import json
import os
import sys
import unittest

candidate, tests, result_file, manifest, selected = sys.argv[1:]
expected = json.loads(manifest)
# Preserve stdlib precedence, including modules imported lazily by unittest.
sys.path.append(candidate)
output = io.StringIO()
loaded = set()
executed = dict.fromkeys(expected, 0)

def module_file(module):
    path = getattr(module, "__file__", "")
    if not path:
        return "<unknown>"
    return os.path.relpath(os.path.realpath(path), tests).replace(os.sep, "/")

class Loader(unittest.TestLoader):
    def loadTestsFromModule(self, module, *args, **kwargs):
        name = module_file(module)
        if hasattr(module, "load_tests"):
            raise ValueError(name + ": load_tests hooks are not supported")
        loaded.add(name)
        suite = super().loadTestsFromModule(module, *args, **kwargs)
        if name.endswith("__init__.py") and suite.countTestCases():
            raise ValueError(name + ": package markers must not define tests")
        return suite

class Result(unittest.TextTestResult):
    def startTest(self, test):
        name = module_file(sys.modules.get(type(test).__module__))
        if name in executed:
            executed[name] += 1
        super().startTest(test)

with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
    try:
        loader = Loader()
        if selected:
            sys.path.insert(0, tests)
            module = importlib.import_module(selected[:-3].replace("/", "."))
            suite = loader.loadTestsFromModule(module)
        else:
            suite = loader.discover(tests, top_level_dir=tests)
        result = unittest.TextTestRunner(stream=output, resultclass=Result).run(suite)
        report = dict(tests=result.testsRun,
                      failures=len(result.failures) + len(result.expectedFailures)
                      + len(result.unexpectedSuccesses),
                      errors=len(result.errors), skipped=len(result.skipped))
        if result.expectedFailures:
            report["expected_failures"] = len(result.expectedFailures)
        if result.unexpectedSuccesses:
            report["unexpected_successes"] = len(result.unexpectedSuccesses)
    except BaseException as exc:
        report = dict(tests=0, failures=0, errors=1, skipped=0)
        print(type(exc).__name__ + ": " + str(exc), file=output)
    unloaded = sorted(name for name in expected if name not in loaded or not executed[name])
    if unloaded:
        report["unloaded"] = unloaded
        print("Hidden files not loaded or executing zero tests: " + ", ".join(unloaded), file=output)
    report["passed"] = (report["tests"] > 0 and report["failures"] == 0
                        and report["errors"] == 0 and report["skipped"] == 0
                        and not unloaded)
print(output.getvalue(), file=sys.stderr, end="")
# Stdout is diagnostic output, never a verdict channel.
with open(result_file, "x", encoding="utf-8") as stream:
    json.dump(report, stream)
'''


def task_folders(root):
    if not root.is_dir():
        raise ValueError("tasks directory does not exist: %s" % root)
    return sorted((p for p in root.iterdir() if p.is_dir()), key=lambda p: p.name)


def task_metadata(folder):
    try:
        data = json.loads((folder / "task.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError("task.json: %s" % exc) from exc
    if not isinstance(data, dict):
        raise ValueError("task.json must be an object")
    violations = []
    if data.get("id") != folder.name:
        violations.append("id must equal folder name")
    if data.get("category") not in CATEGORIES:
        violations.append("category must be single, chain, review, or parallel")
    for field in ("title", "prompt"):
        if not isinstance(data.get(field), str) or not data[field].strip():
            violations.append("%s must be a non-empty string" % field)
    parts = data.get("parts")
    if not isinstance(parts, list) or not parts or any(
            not isinstance(part, str) or not part.strip() for part in parts):
        violations.append("parts must be a non-empty list of non-empty strings")
    required = ["start", "solution", "hidden_tests"]
    if data.get("category") == "review":
        required.append("tempting")
    for name in required:
        if not (folder / name).is_dir():
            violations.append("missing %s/" % name)
    if violations:
        raise ValueError("; ".join(violations))
    return data


def find_task(root, task_id):
    if task_id in (".", "..") or Path(task_id).name != task_id:
        raise ValueError("invalid task id: %s" % task_id)
    folder = root / task_id
    task_metadata(folder)
    return folder


def overlay(source, destination):
    shutil.copytree(source, destination, dirs_exist_ok=True)


def safe_destination(folder, fixture, destination):
    try:
        resolved = destination.resolve()
    except RuntimeError as exc:
        raise ValueError("destination has unresolvable symlinks: %s" % destination) from exc
    for source in (fixture.resolve(), folder.parent.resolve()):
        if resolved == source or source in resolved.parents:
            raise ValueError("destination must be outside fixture and task directories")


def symlinks(root):
    if root.is_symlink():
        return [root]
    return [p for p in sorted(root.rglob("*")) if p.is_symlink()]


def hidden_files(tests):
    links = symlinks(tests)
    if links:
        raise ValueError("symlinks are not supported: %s" % ", ".join(str(p) for p in links))
    files = sorted(p.relative_to(tests).as_posix() for p in tests.rglob("*.py")
                   if p.is_file() and p.name != "__init__.py")
    problems = []
    for name in files:
        path = Path(name)
        # Python 3.9 can overlook invalid bytes in comments during import.
        try:
            with tokenize.open(str(tests / name)) as stream:
                stream.read()
        except (OSError, SyntaxError, UnicodeError) as exc:
            problems.append("%s: invalid Python source encoding: %s" % (name, exc))
        if not fnmatch.fnmatchcase(path.name, "test*.py") or not path.stem.isidentifier():
            problems.append("%s: test module must match test*.py with an importable name" % name)
        for parent in path.parents:
            if parent == Path("."):
                continue
            if not parent.name.isidentifier() or not (tests / parent / "__init__.py").is_file():
                problems.append("%s: %s requires an importable package with __init__.py" %
                                (name, parent))
    if problems:
        raise ValueError("; ".join(problems))
    return files


def setup(folder, fixture, destination):
    if not fixture.is_dir():
        raise ValueError("fixture directory does not exist: %s" % fixture)
    safe_destination(folder, fixture, destination)
    if destination.is_symlink() or (destination.exists() and (
            not destination.is_dir() or any(destination.iterdir()))):
        raise ValueError("destination must be absent or an empty directory: %s" % destination)
    overlay(fixture, destination)
    overlay(folder / "start", destination)


def run_tests(candidate, tests, only_file=None):
    failure = dict(passed=False, tests=0, failures=0, errors=1, skipped=0)
    try:
        links = symlinks(candidate)
        if links:
            raise ValueError("candidate symlinks are not supported: %s" %
                             ", ".join(str(p) for p in links))
        if tests.is_symlink():
            raise ValueError("hidden test symlinks are not supported: %s" % tests)
        if not candidate.is_dir() or not tests.is_dir():
            return failure, "candidate or test directory does not exist"
        files = hidden_files(tests)
        if only_file is not None:
            if only_file not in files:
                raise ValueError("unknown hidden test file: %s" % only_file)
            files = [only_file]
    except (OSError, ValueError) as exc:
        return dict(failure, unloaded=[str(exc)]), str(exc)
    # Keep the verdict outside the candidate; prints and early exits cannot supply it.
    with tempfile.TemporaryDirectory(prefix="graph-flow-score-") as scratch:
        result_file = Path(scratch) / "result.json"
        try:
            process = subprocess.run(
                [sys.executable, "-I", "-S", "-B", "-c", TEST_PROCESS,
                 str(candidate.resolve()), str(tests.resolve()), str(result_file),
                 json.dumps(files), only_file or ""],
                cwd=str(candidate.resolve()), capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=60)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return failure, str(exc)
        detail = process.stderr + process.stdout
        try:
            if process.returncode:
                raise ValueError("test process exited %d" % process.returncode)
            report = json.loads(result_file.read_text(encoding="utf-8"))
            if not isinstance(report, dict):
                raise ValueError("test process did not return a result")
            if any(type(report.get(key)) is not int or report[key] < 0
                   for key in ("tests", "failures", "errors", "skipped")):
                raise ValueError("invalid test counts")
            if not isinstance(report.get("unloaded", []), list) or any(
                    not isinstance(name, str) for name in report.get("unloaded", [])):
                raise ValueError("invalid hidden file inventory")
            report["passed"] = (report["tests"] > 0 and report["failures"] == 0
                                and report["errors"] == 0 and report["skipped"] == 0
                                and not report.get("unloaded")
                                and report.get("passed") is True)
            return report, detail
        except (OSError, ValueError, TypeError) as exc:
            return failure, "%s\n%s" % (exc, detail)


def category_mix(value):
    counts = {}
    try:
        for item in value.split(","):
            category, count = item.split("=")
            if category not in CATEGORIES or category in counts or int(count) < 0:
                raise ValueError()
            counts[category] = int(count)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "mix must contain unique category=nonnegative-count pairs") from exc
    return counts


def selfcheck(args):
    folders = task_folders(args.tasks)
    violations = [] if folders else ["tasks directory is empty: %s" % args.tasks]
    categories = Counter()
    for folder in folders:
        problems = []
        try:
            metadata = task_metadata(folder)
            categories[metadata["category"]] += 1
            with tempfile.TemporaryDirectory(prefix="graph-flow-selfcheck-") as scratch:
                for state in ("start", "solution", "tempting"):
                    if state == "tempting" and metadata["category"] != "review":
                        continue
                    candidate = Path(scratch) / state
                    setup(folder, args.fixture, candidate)
                    if state != "start":
                        overlay(folder / state, candidate)
                    result, detail = run_tests(candidate, folder / "hidden_tests")
                    detail = detail.strip().replace("\n", " | ")
                    if result["tests"] == 0:
                        problems.append("%s hidden tests ran zero tests: %s" % (state, detail))
                    if state == "solution" and not result["passed"]:
                        problems.append("solution fails hidden tests: %s" % detail)
                    elif state != "solution" and result["passed"]:
                        problems.append("%s wrongly passes hidden tests" % state)
                    if result.get("unloaded"):
                        problems.append("%s hidden test completeness: %s" %
                                        (state, ", ".join(result["unloaded"])))
                    if state != "solution" and (result["skipped"]
                            or result.get("expected_failures") or result.get("unexpected_successes")):
                        problems.append("%s must fail or error without skips or expected failures" % state)
                    if state == "start" and len(metadata["parts"]) > 1:
                        for name in hidden_files(folder / "hidden_tests"):
                            alone, diagnostic = run_tests(candidate, folder / "hidden_tests", name)
                            if (alone["passed"] or alone["tests"] == 0 or alone.get("unloaded")
                                    or alone["skipped"] or alone.get("expected_failures")
                                    or alone.get("unexpected_successes")
                                    or not (alone["failures"] or alone["errors"])):
                                problems.append("start hidden file %s must FAIL or ERROR alone: %s" %
                                                (name, diagnostic.strip().replace("\n", " | ")))
                    if state == "tempting":
                        visible, detail = run_tests(candidate, args.fixture / "tests")
                        if not visible["passed"]:
                            problems.append("tempting fails visible tests: %s" %
                                            detail.strip().replace("\n", " | "))
        except (OSError, ValueError, RuntimeError, shutil.Error) as exc:
            problems.append(str(exc))
        print("%s: %s" % (folder.name, "; ".join(problems) if problems else "OK"))
        violations.extend("%s: %s" % (folder.name, problem) for problem in problems)
    if args.expect is not None and len(folders) != args.expect:
        violations.append("expected %d tasks, found %d" % (args.expect, len(folders)))
    if args.mix is not None:
        for category in CATEGORIES:
            expected = args.mix.get(category, 0)
            if categories[category] != expected:
                violations.append("category %s: expected %d, found %d" % (
                    category, expected, categories[category]))
    for violation in violations:
        print(violation, file=sys.stderr)
    return int(bool(violations))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks", type=Path, default=BASE / "tasks")
    parser.add_argument("--fixture", type=Path, default=BASE / "fixture")
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("list", "setup", "score", "selfcheck"):
        sub = commands.add_parser(command, description=__doc__)
        sub.add_argument("--tasks", type=Path, default=argparse.SUPPRESS)
        sub.add_argument("--fixture", type=Path, default=argparse.SUPPRESS)
        if command in ("setup", "score"):
            sub.add_argument("id")
            sub.add_argument("dest", type=Path)
        if command == "selfcheck":
            sub.add_argument("--expect", type=int)
            sub.add_argument("--mix", type=category_mix)
    args = parser.parse_args(argv)
    try:
        args.tasks = args.tasks.resolve()
        args.fixture = args.fixture.resolve()
        if args.command == "list":
            for folder in task_folders(args.tasks):
                print(folder.name)
            return 0
        if args.command == "selfcheck":
            return selfcheck(args)
        folder = find_task(args.tasks, args.id)
        if args.command == "setup":
            setup(folder, args.fixture, args.dest)
            return 0
        safe_destination(folder, args.fixture, args.dest)
        report, detail = run_tests(args.dest, folder / "hidden_tests")
        print(json.dumps(dict(task=args.id, **report), sort_keys=True))
        if detail:
            print(detail, file=sys.stderr, end="" if detail.endswith("\n") else "\n")
        return 0 if report["passed"] else 1
    except (OSError, ValueError, RuntimeError, shutil.Error) as exc:
        if args.command == "score":
            print(json.dumps(dict(task=args.id, passed=False, tests=0, failures=0, errors=1, skipped=0)))
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
