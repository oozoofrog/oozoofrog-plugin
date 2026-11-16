"""Read-only trajectory metrics and cross-run rollback evidence (P7, P12)."""
import pathlib
from datetime import datetime

from . import core, plan, state, store


def _duration(first, last):
    if first is None or last is None:
        return None
    return int((datetime.strptime(last, "%Y-%m-%dT%H:%M:%SZ") -
                datetime.strptime(first, "%Y-%m-%dT%H:%M:%SZ")).total_seconds() * 1000)


def trace(run_dir):
    current = store.read_plan(run_dir)
    events = store.events(run_dir)
    summary = {"nodes": 0, "passed": 0, "attempts": 0, "rejections": 0,
               "duration_ms": None}
    result = {"run": summary, "nodes": {}}
    if current is None:
        return result
    derived = state.derive(current, events)
    init = next((e["ts"] for e in events if e["type"] == "run.init"), None)
    if len(events) >= 2:
        summary["duration_ms"] = _duration(init, events[-1]["ts"])
    for node in current["nodes"]:
        nid = node["id"]
        st = derived["nodes"][nid]
        recent = [e for e in events if e["seq"] > st["basis"]
                  and e.get("data", {}).get("node") == nid]
        starts = [e["ts"] for e in recent if e["type"] == "node.start"]
        passes = [e["ts"] for e in recent if e["type"] == "gate.verdict"
                  and e["data"].get("verdict") == "pass"]
        first = starts[0] if starts else None
        passed = st["status"] == "passed"
        last = passes[-1] if passed and passes else None
        metrics = {"attempts": st["attempts"],
                   "rejections": sum(e["type"] == "gate.verdict" and
                                     e["data"].get("verdict") in ("reject", "replan")
                                     for e in recent),
                   "first_start": first, "passed_at": last,
                   "duration_ms": _duration(first, last),
                   "checks_run": sum(e["type"] == "check.result" for e in recent),
                   "rollbacks": rollbacks(store.project_of(run_dir), run_dir, node["owns"])}
        result["nodes"][nid] = metrics
        summary["nodes"] += 1
        summary["passed"] += int(passed)
        for key in ("attempts", "rejections"):
            summary[key] += metrics[key]
    return result


def _rolled_back(current, events, owns):
    candidates = {n["id"] for n in current["nodes"] if plan.overlaps(n["owns"], owns)}
    passed, rolled, seen = set(), set(), set()
    previous = None
    for event in events:
        kind, data = event["type"], event["data"]
        nid = data.get("node")
        if kind == "gate.verdict":
            if data.get("verdict") == "pass" and nid in candidates:
                passed.add(nid)
            elif data.get("verdict") in ("reject", "replan") and nid in passed:
                rolled.add(nid)
        elif kind == "node.reopen":
            rolled.update(n for n in passed if n == nid or plan.depends(current, n, nid))
        elif kind == "plan.set":
            fps = data["fingerprints"]
            changed = {n for n, fp in fps.items()
                       if (previous is not None and n in previous and previous[n] != fp)
                       or (n not in (previous or {}) and n in seen)}
            rolled.update(n for n in passed if n in changed or
                          any(plan.depends(current, n, producer) for producer in changed))
            previous = fps
            seen.update(fps)
    return len(rolled)


def rollbacks(project_root, run_dir, owns):
    """Count overlapping current nodes accepted then invalidated in other runs."""
    if not owns:
        return 0
    runs = pathlib.Path(project_root) / ".graph-flow" / "runs"
    try:
        directories = list(runs.iterdir())
    except OSError:
        return 0
    total = 0
    for other in directories:
        try:
            if other.resolve() == pathlib.Path(run_dir).resolve() or not other.is_dir():
                continue
            current = store.read_plan(other)
            if current is not None:
                total += _rolled_back(current, store.events(other), owns)
        except (core.GFError, OSError, ValueError, TypeError, KeyError, AttributeError):
            # Historical damage must not prevent the current run from being gated.
            continue
    return total
