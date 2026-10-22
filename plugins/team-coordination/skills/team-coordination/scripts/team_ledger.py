#!/usr/bin/env python3
"""Recorded coordination invariants, not live-session or OS enforcement."""
import argparse
import copy
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import tempfile


class Invalid(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise Invalid(message)


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def evidence(path):
    p = Path(path).expanduser().resolve(strict=True)
    require(p.is_file(), "Evidence must be a regular file")
    return {"path": str(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "captured_at": now()}


def fresh(item):
    try:
        return evidence(item["path"])["sha256"] == item["sha256"]
    except (OSError, KeyError):
        return False


def canonical(path):
    p = Path(path).expanduser()
    require(p.is_absolute(), "Claim paths must be absolute")
    require(not any(c in str(p) for c in "*?[]"), "Claim paths are literal; glob patterns unsupported")
    return str(p.resolve())


def overlaps(a, b):
    a, b = Path(a).resolve(), Path(b).resolve()
    return a == b or a in b.parents or b in a.parents


def key(leader, agent):
    require(isinstance(leader, str) and leader.strip(), "Actual leader namespace required")
    require(isinstance(agent, str) and agent.strip(), "Actual agent ID required")
    return json.dumps([leader, agent], separators=(",", ":"))


def member_key(event, prefix=""):
    return key(event[prefix + "leader_id"], event[prefix + "agent_id"])


def apply(state, event):
    s = copy.deepcopy(state)
    op = event["op"]
    if op == "init":
        require(not s, "Ledger already initialized")
        return {"version": 1, "members": {}, "tasks": {}, "history": [{"at": now(), "event": event}]}
    require(s.get("version") == 1, "Initialize ledger first")
    tasks, members = s["tasks"], s["members"]
    if op == "register":
        k = member_key(event)
        require(k not in members, "Member already registered in this leader namespace")
        require(event["role"] in ("leader", "executor", "reviewer"), "Unknown role")
        require(bool(event["id_type"]), "ID type required")
        members[k] = {k: event[k] for k in ("leader_id", "agent_id", "role", "id_type")}
        members[k]["provenance"] = evidence(event["provenance"])
        if event.get("agent_thread_id"):
            members[k]["agent_thread_id"] = event["agent_thread_id"]
    elif op == "assign":
        k, task = member_key(event), event["task"]
        require(task not in tasks, "Duplicate task assignment")
        require(k in members and members[k]["role"] == "executor", "Only registered executors own substantive tasks")
        require(fresh(members[k]["provenance"]), "Identity provenance changed or missing")
        require(bool(event["purpose"].strip()), "Bounded task purpose required")
        tasks[task] = {"owner": k, "purpose": event["purpose"], "state": "assigned", "paths": [], "resources": [], "updated_at": now()}
    else:
        require(event["task"] in tasks, "Unknown task")
        task = tasks[event["task"]]
        if op == "claim":
            require(task["state"] in ("assigned", "running"), "Claims require an executable task state")
            paths = sorted(set(canonical(p) for p in event.get("paths", [])))
            resources = sorted(set(event.get("resources", [])))
            require(paths or resources, "Nonempty claim required")
            require(all(isinstance(r, str) and r.strip() for r in resources), "Resource names must be nonempty strings")
            for other_id, other in tasks.items():
                if other_id == event["task"]:
                    continue
                require(not any(overlaps(a, b) for a in paths for b in other["paths"]), "Overlapping write ownership")
                require(not set(resources) & set(other["resources"]), "Shared resource already claimed")
            task["paths"] = sorted(set(task["paths"] + paths))
            task["resources"] = sorted(set(task["resources"] + resources))
        elif op == "release":
            require(event.get("safe_boundary") is True, "Release requires confirmed safe boundary")
            task["paths"], task["resources"] = [], []
        elif op == "status":
            target = event["state"]
            require(target in ("running", "blocked", "denied", "pending", "uncertain"), "Use handoff/review/accept for completion")
            require(task["state"] in ("assigned", "running", "blocked"), "Resolve current state before proceeding")
            task["evidence"] = evidence(event["evidence"])
            if target in ("blocked", "denied", "pending", "uncertain"):
                for field in ("action", "target", "reason", "outcome"):
                    require(bool(str(event.get(field, "")).strip()), field + " required")
                task["block"] = {f: event[f] for f in ("action", "target", "reason", "outcome")}
            task["state"] = target
        elif op == "retry":
            require(task["state"] == "denied", "Pending/uncertain actions must be reconciled, never automatically retried")
            ev = evidence(event["evidence"])
            require(event.get("known_not_executed") is True, "Must establish action did not execute")
            require(bool(event.get("reason", "").strip()), "Material relevance explanation required")
            require(ev["sha256"] != task["evidence"]["sha256"], "Materially new evidence required")
            require(ev["sha256"] not in task.get("retry_evidence", []), "Evidence already used for retry")
            task.setdefault("retry_evidence", []).append(ev["sha256"])
            task["evidence"], task["state"] = ev, "assigned"
        elif op == "reconcile":
            require(task["state"] in ("pending", "uncertain", "blocked"), "Only unresolved outcomes need reconciliation")
            require(event["outcome"] in ("not_executed", "executed", "still_unknown"), "Unknown outcome")
            ev = evidence(event["evidence"])
            require(ev["sha256"] != task["evidence"]["sha256"], "New outcome evidence required")
            task["evidence"] = ev
            task["state"] = {"not_executed": "assigned", "executed": "running", "still_unknown": "uncertain"}[event["outcome"]]
        elif op == "handoff":
            require(task["state"] in ("assigned", "running"), "Resolve blocked action before handoff")
            require(bool(event["artifacts"]), "Artifact evidence required")
            task["artifacts"] = [evidence(p) for p in event["artifacts"]]
            task["state"] = "ready_for_review"
        elif op == "review":
            require(task["state"] == "ready_for_review", "Fresh handoff required")
            k = member_key(event, "reviewer_")
            require(k in members and members[k]["role"] == "reviewer", "Registered reviewer required")
            require(k != task["owner"], "Author cannot independently review")
            author = members[task["owner"]]
            reviewer = members[k]
            require(not (author.get("agent_thread_id") and author.get("agent_thread_id") == reviewer.get("agent_thread_id")), "Same underlying agent cannot independently review")
            require(author["agent_id"] != reviewer["agent_id"] or (author.get("agent_thread_id") and reviewer.get("agent_thread_id") and author["agent_thread_id"] != reviewer["agent_thread_id"]), "Same canonical name across namespaces requires distinct recorded agentThreadId")
            require(fresh(reviewer["provenance"]), "Reviewer identity provenance stale")
            require(all(fresh(a) for a in task["artifacts"]), "Artifact evidence stale")
            require(event["verdict"] in ("pass", "fail"), "Review must pass or fail")
            task["review"] = {"reviewer": k, "verdict": event["verdict"], "report": evidence(event["report"])}
            task["state"] = "reviewed" if event["verdict"] == "pass" else "assigned"
        elif op == "accept":
            require(task["state"] == "reviewed" and task["review"]["verdict"] == "pass", "Passing independent review required")
            require(all(fresh(a) for a in task["artifacts"]) and fresh(task["review"]["report"]), "Evidence stale")
            task["state"] = "accepted"
        else:
            raise Invalid("Unknown operation")
        task["updated_at"] = now()
    s["history"].append({"at": now(), "event": event})
    return s


def audit(state):
    issues = []
    for k, member in state.get("members", {}).items():
        if not fresh(member["provenance"]):
            issues.append("stale identity: " + k)
    tasks = state.get("tasks", {})
    pairs = list(tasks.items())
    for i, (a_id, a) in enumerate(pairs):
        for b_id, b in pairs[i + 1:]:
            if any(overlaps(x, y) for x in a["paths"] for y in b["paths"]):
                issues.append("overlapping paths: " + a_id + "/" + b_id)
            if set(a["resources"]) & set(b["resources"]):
                issues.append("overlapping resources: " + a_id + "/" + b_id)
        for ev in a.get("artifacts", []) + ([a["review"]["report"]] if "review" in a else []):
            if not fresh(ev):
                issues.append("stale evidence: " + a_id)
        if a["state"] in ("blocked", "denied", "pending", "uncertain"):
            issues.append("unresolved outcome: " + a_id + "=" + a["state"])
    return issues


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--ledger", type=Path, required=True)
    sub = p.add_subparsers(dest="command", required=True)
    action = sub.add_parser("apply")
    action.add_argument("--event", type=Path, required=True)
    sub.add_parser("audit")
    args = p.parse_args()
    ledger = args.ledger.expanduser().resolve()
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with open(str(ledger) + ".lock", "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = json.loads(ledger.read_text()) if ledger.exists() else {}
        require("harness" not in state, "Managed project: use harness.py as the single authority; legacy ledger CLI is disabled")
        if args.command == "audit":
            issues = audit(state)
            print(json.dumps({"recorded_state_only": True, "issues": issues}, indent=2))
            return bool(issues)
        state = apply(state, json.loads(args.event.read_text()))
        fd, temporary = tempfile.mkstemp(prefix=".team-", dir=ledger.parent)
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(state, f, indent=2)
                f.write("\n")
                f.flush()
                os.fsync(f.fileno())
            os.replace(temporary, ledger)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        print(json.dumps({"ledger": str(ledger), "operation": args.command, "recorded_state_only": True}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (Invalid, KeyError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": str(exc)}))
        raise SystemExit(2)
