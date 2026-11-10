#!/usr/bin/env python3
"""Bootstrap and inspect a single-writer project loop using record integrity only.

This helper never runs project commands. Records cannot establish semantic
correctness, prove a command ran, or prove a revision matches current product code.
The coordinator owns authorization, product scope checks, and reconciliation.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import shutil
import sys
import tempfile


ID = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}\Z")
STATUSES = {"pending", "running", "passed", "failed", "blocked", "stale", "cancelled"}
SCOPE = "record_integrity_only"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def integer(value, minimum=0):
    return type(value) is int and value >= minimum


def mapping(value, label):
    require(isinstance(value, dict), label + " must be an object")
    return value


def array(value, label):
    require(isinstance(value, list), label + " must be an array")
    return value


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def decode(data):
    return json.loads(data, parse_constant=lambda value: reject_constant(value))


def reject_constant(value):
    raise ValueError("invalid JSON constant: " + value)


def scope_path(value, write=False):
    require(nonempty(value) and "\x00" not in value and "\\" not in value,
            "scope path must be a nonempty portable relative path")
    require(not PureWindowsPath(value).drive and not value.startswith("/")
            and ".." not in value.split("/") and not any(c in value for c in "*?[]"),
            "absolute, parent traversal, and glob scope paths are forbidden: " + value)
    normalized = str(PurePosixPath(value))
    require(not write or (normalized != "." and normalized.split("/")[0]
                           not in {".git", ".agent-loop"}), "unsafe write scope: " + value)
    return normalized


def records(items, label, task_ids=False):
    result = {}
    for item in array(items, label):
        mapping(item, label + " entry")
        name = item.get("id")
        require(nonempty(name) and (not task_ids or ID.fullmatch(name)), "invalid " + label + " id")
        require(name not in result, "duplicate " + label + " id: " + name)
        result[name] = item
    return result


def validate_plan(plan):
    mapping(plan, "plan")
    require(type(plan.get("schema_version")) is int and plan["schema_version"] == 1,
            "plan schema_version must be 1")
    require(nonempty(plan.get("goal")), "plan goal must be nonempty")
    tasks = records(plan.get("tasks"), "task", task_ids=True)
    require(tasks, "plan tasks must not be empty")
    decisions = records(plan.get("decisions", []), "decision")
    for decision in decisions.values():
        require(decision.get("kind") in {"direction", "information", "review", "authorization"}
                and nonempty(decision.get("question")), "invalid decision kind or question")
        require("artifact_version" not in decision or isinstance(decision["artifact_version"], str),
                "decision artifact_version must be a string")
    budget = mapping(plan.get("question_budget", {"max_questions": 3, "max_rounds": 2}), "question_budget")
    require(all(integer(budget.get(key)) for key in ("max_questions", "max_rounds")),
            "question budget must contain nonnegative integer limits")
    for name, task in tasks.items():
        require(nonempty(task.get("title")), "task title must be nonempty")
        deps = array(task.get("depends_on"), "depends_on")
        require(all(isinstance(dep, str) and dep in tasks and dep != name for dep in deps),
                "missing or self dependency: " + name)
        for key in ("reads", "writes"):
            task[key] = [scope_path(path, write=key == "writes") for path in array(task.get(key), key)]
        checks = records(task.get("checks"), "check")
        require(checks, "task checks must not be empty")
        require(all(nonempty(check.get("description")) and
                    ("command" not in check or isinstance(check["command"], str))
                    for check in checks.values()), "invalid check description or command")
        task.setdefault("max_attempts", 3)
        require(integer(task["max_attempts"], 1), "max_attempts must be a positive integer")
        task.setdefault("decision_ids", [])
        require(all(isinstance(item, str) and item in decisions
                    for item in array(task["decision_ids"], "decision_ids")), "unknown task decision")
    remaining = set(tasks)
    while remaining:
        ready = {name for name in remaining if not (set(tasks[name]["depends_on"]) & remaining)}
        require(ready, "cyclic task dependencies")
        remaining -= ready
    warnings = []
    task_list = list(tasks.values())
    for index, left in enumerate(task_list):
        for right in task_list[index + 1:]:
            for a, b in (("writes", "writes"), ("writes", "reads"), ("reads", "writes")):
                overlaps = [[x, y] for x in left[a] for y in right[b]
                            if x == "." or y == "." or x == y
                            or x.startswith(y + "/") or y.startswith(x + "/")]
                if overlaps:
                    warnings.append({"tasks": [left["id"], right["id"]],
                                     "kind": a + "/" + b, "scopes": overlaps})
    return tasks, decisions, warnings


def regular_file(path):
    require(not path.is_symlink() and path.is_file(), "expected nonsymlink regular file: " + str(path))
    return path.read_bytes()


def validate_evidence(workspace, task, record, checks):
    mapping(record, "evidence record")
    require(isinstance(record.get("check_id"), str) and record["check_id"] in checks
            and record.get("result") in {"passed", "failed", "not_run"}, "invalid evidence check or result")
    relative = scope_path(record.get("path"))
    parts = PurePosixPath(relative).parts
    require(len(parts) > 1 and parts[0] == "evidence", "evidence must be strictly inside evidence/")
    target = workspace
    for part in parts:
        target = target / part
        require(not target.is_symlink(), "symlink evidence component: " + str(target))
    data = regular_file(target)
    require(data and record.get("sha256") == digest(data), "empty evidence or evidence digest mismatch")
    require(nonempty(record.get("artifact_version")), "evidence needs an artifact_version")
    if task["status"] == "passed":
        require(record["artifact_version"] == task["verified_revision"], "evidence artifact_version mismatch")


def decision_satisfied(state):
    return state["status"] == "resolved" and state["outcome"] in {"answered", "approved"}


def load_workspace(location, *, state_override=None):
    workspace = Path(os.path.abspath(location))
    require(workspace.parent.name == ".agent-loop" and ID.fullmatch(workspace.name),
            "workspace must be .agent-loop/<safe-run-id>")
    require(not workspace.is_symlink() and not workspace.parent.is_symlink()
            and workspace.is_dir(), "workspace and .agent-loop must be nonsymlink directories")
    files = {name: regular_file(workspace / name) for name in
             ("plan.json", "state.json", "brief.md", "decisions.jsonl", "lessons.md")}
    evidence = workspace / "evidence"
    require(not evidence.is_symlink() and evidence.is_dir(), "evidence must be a nonsymlink directory")
    state = mapping(decode(files["state.json"]) if state_override is None else state_override, "state")
    root = state.get("project_root")
    require(nonempty(root) and Path(root).is_dir() and str(Path(root).resolve()) == root
            and workspace.resolve().parent.parent == Path(root) and state.get("run_id") == workspace.name,
            "workspace project_root/run_id identity mismatch")
    require(type(state.get("schema_version")) is int and state["schema_version"] == 1,
            "state schema_version must be 1")
    require(state.get("plan_sha256") == digest(files["plan.json"]),
            "plan digest changed; coordinator must reconcile affected task states and update the digest only after review")
    plan = decode(files["plan.json"])
    tasks, decisions, warnings = validate_plan(plan)
    task_states = mapping(state.get("tasks"), "task states")
    decision_states = mapping(state.get("decisions"), "decision states")
    require(set(task_states) == set(tasks) and set(decision_states) == set(decisions),
            "state task/decision ID sets must exactly match the plan")
    usage = mapping(state.get("question_usage"), "question_usage")
    require(all(integer(usage.get(key)) for key in ("questions", "rounds")), "invalid question usage")
    budget = plan.get("question_budget", {"max_questions": 3, "max_rounds": 2})
    require(usage["questions"] <= budget["max_questions"] and usage["rounds"] <= budget["max_rounds"],
            "discretionary question usage exceeds the plan budget")
    for name, decision in decision_states.items():
        mapping(decision, "decision state")
        require(decision.get("status") in {"pending", "resolved"}, "unknown decision status")
        if decision["status"] == "resolved":
            require(nonempty(decision.get("answer")), "resolved decision requires a nonempty answer")
            outcomes = {"answered"} if decisions[name]["kind"] in {"direction", "information"} else {
                "approved", "rejected", "revision_requested"}
            require(decision.get("outcome") in outcomes, "resolved decision requires a kind-appropriate outcome")
            if "artifact_version" in decisions[name]:
                require(decision.get("artifact_version") == decisions[name]["artifact_version"],
                        "resolved decision artifact_version mismatch")
    for name, task in task_states.items():
        mapping(task, "task state")
        require(task.get("status") in STATUSES, "unknown task status")
        attempts = task.get("attempts")
        require(integer(attempts) and attempts <= tasks[name]["max_attempts"], "invalid task attempts")
        require(task["status"] not in {"running", "passed", "failed"} or attempts >= 1,
                "running/passed/failed tasks require at least one attempt")
        checks = {check["id"] for check in tasks[name]["checks"]}
        entries = array(task.get("evidence"), "task evidence")
        for entry in entries:
            validate_evidence(workspace, task, entry, checks)
        if task["status"] == "passed":
            require(nonempty(task.get("verified_revision")), "passed task requires verified_revision")
            require(len(entries) == len(checks) and
                    checks == {e["check_id"] for e in entries if e["result"] == "passed"},
                    "passed task needs exactly one current passed record per required check")
    for name, task in task_states.items():
        if task["status"] == "passed":
            require(all(task_states[dep]["status"] == "passed" for dep in tasks[name]["depends_on"]),
                    "passed task has unpassed dependencies")
            require(all(decision_satisfied(decision_states[dep]) for dep in tasks[name]["decision_ids"]),
                    "passed task has unresolved or unsatisfied decisions")
    return workspace, files, plan, state, warnings


def init(project, run_id, plan_file, brief_file):
    require(ID.fullmatch(run_id), "unsafe run ID")
    root = Path(project).resolve(strict=True)
    require(root.is_dir(), "project must already be a directory")
    plan = decode(Path(plan_file).read_bytes())
    tasks, decisions, warnings = validate_plan(plan)
    plan_bytes, brief_bytes = encode(plan), Path(brief_file).read_bytes()
    parent = root / ".agent-loop"
    require(not parent.is_symlink(), "symlink .agent-loop parent is forbidden")
    parent.mkdir(exist_ok=True)
    require(parent.is_dir(), ".agent-loop must be a directory")
    destination = parent / run_id
    require(not destination.is_symlink(), "symlink run is forbidden")
    if destination.exists():
        workspace, files, _, _, _ = load_workspace(destination)
        require(files["plan.json"] == plan_bytes and files["brief.md"] == brief_bytes,
                "existing run plan or brief input mismatch")
        return {"workspace": str(workspace), "reused": True, "serialization_warnings": warnings}
    stage = Path(tempfile.mkdtemp(prefix=".staging-", dir=parent))
    try:
        state = {"schema_version": 1, "project_root": str(root), "run_id": run_id,
                 "plan_sha256": digest(plan_bytes), "question_usage": {"questions": 0, "rounds": 0},
                 "decisions": {name: {"status": "pending", "answer": None, "outcome": None, "artifact_version": None}
                               for name in decisions},
                 "tasks": {name: {"status": "pending", "attempts": 0, "verified_revision": None,
                                  "evidence": []} for name in tasks}}
        for name, data in {"brief.md": brief_bytes, "plan.json": plan_bytes, "state.json": encode(state),
                           "decisions.jsonl": b"", "lessons.md": b"# Scoped learning\n\nRecord project, revision, and applicability for each lesson.\n"}.items():
            (stage / name).write_bytes(data)
        (stage / "evidence").mkdir()
        require(not os.path.lexists(destination), "run appeared during staging; refusing overwrite")
        stage.rename(destination)  # Single coordinating writer; never replace a known existing run.
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    return {"workspace": str(destination), "reused": False, "serialization_warnings": warnings}


def status(plan, state, warnings):
    result = {key: [] for key in ("ready", "blocked_by_dependencies", "blocked_by_decisions",
                                 "exhausted", "running", "passed", "needs_revalidation", "cancelled", "blocked")}
    for task in plan["tasks"]:
        name = task["id"]
        item = state["tasks"][name]
        current = item["status"]
        if current in {"running", "passed", "cancelled"}:
            result[current].append(name)
            continue
        if current == "stale":
            result["needs_revalidation"].append(name)
        if current == "blocked":
            result["blocked"].append(name)
        deps = all(state["tasks"][dep]["status"] == "passed" for dep in task["depends_on"])
        decisions = all(decision_satisfied(state["decisions"][dep]) for dep in task["decision_ids"])
        if not deps:
            result["blocked_by_dependencies"].append(name)
        if not decisions:
            result["blocked_by_decisions"].append(name)
        if item["attempts"] >= task["max_attempts"]:
            result["exhausted"].append(name)
        elif current in {"pending", "failed", "stale"} and deps and decisions:
            result["ready"].append(name)
    result.update(complete=all(task["status"] == "passed" for task in state["tasks"].values()),
                  serialization_warnings=warnings)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    bootstrap = commands.add_parser("init", help="create or reuse a matching project run")
    for flag in ("project", "run-id", "plan", "brief"):
        bootstrap.add_argument("--" + flag, required=True)
    for command in ("check", "status"):
        commands.add_parser(command, help="inspect record integrity only").add_argument("--workspace", required=True)
    commands.add_parser("validate-plan", help="validate plan shape and scopes").add_argument("--plan", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            result = init(args.project, args.run_id, args.plan, args.brief)
        elif args.command == "validate-plan":
            _, _, warnings = validate_plan(decode(Path(args.plan).read_bytes()))
            result = {"valid": True, "serialization_warnings": warnings}
        else:
            _, _, plan, state, warnings = load_workspace(args.workspace)
            result = status(plan, state, warnings) if args.command == "status" else {
                "valid": True, "serialization_warnings": warnings}
        result["verification_scope"] = SCOPE
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (ValueError, OSError, TypeError, KeyError, RecursionError) as error:
        print("error: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
