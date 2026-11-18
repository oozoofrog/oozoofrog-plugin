"""Read-only trajectory metrics and cross-run rollback evidence (P7, P12)."""
import pathlib
from datetime import datetime

from . import checks, core, plan, state, store


def _duration(first, last):
    if first is None or last is None:
        return None
    return int((datetime.strptime(last, "%Y-%m-%dT%H:%M:%SZ") -
                datetime.strptime(first, "%Y-%m-%dT%H:%M:%SZ")).total_seconds() * 1000)


def rejection_checks(current, events, verdict):
    """Attribute recorded failures without changing a rejection or its rule."""
    data = verdict["data"]
    nid, reason = data.get("node"), (data.get("rejection") or {}).get("reason", "")
    log = ((data.get("rejection") or {}).get("evidence") or {})
    log = log.get("log") if isinstance(log, dict) else None
    titles = {(n["id"], c["id"]): c.get("title") or c["id"] for n in (current or {}).get("nodes", []) for c in n.get("checks", [])}
    titles.update({("_run", c["id"]): c.get("title") or c["id"] for c in (current or {}).get("integration_checks", []) + (current or {}).get("promoted_checks", [])})
    latest = {}
    for event in events:
        if event["seq"] >= verdict["seq"]:
            break
        item = event["data"]
        if item.get("node") == nid and event["type"] in ("node.start", "gate.verdict"):
            latest = {}
        elif event["type"] == "check.result" and item.get("node") in (nid, "_run") and item.get("phase") == "gate":
            latest[(item["node"], item.get("check"))] = item
    skipped = {entry["check"] for entry in data.get("skipped_checks", [])}
    result = []
    for key, item in latest.items():
        if item.get("result") != "failed" or (key[0] == "_run" and key[1] in skipped):
            continue
        cid = item.get("check")
        if not ((log and item.get("log") == log) or "check %s " % cid in reason
                or item.get("type") in ("scope", "cites") and item["type"] + ":" in reason):
            continue
        result.append(dict(origin="run" if item["node"] == "_run" else "node", check=cid,
                           title=titles.get(key, cid), type=item.get("type"), timed_out=item.get("timed_out", False)))
    if not result and log:
        parts = pathlib.PurePosixPath(log).parts
        if len(parts) >= 4 and parts[0] == "evidence":
            result.append(dict(origin="run" if parts[1] == "_run" else "node", check=parts[2],
                               title=titles.get((parts[1], parts[2]), parts[2])))
    return result


def trace(run_dir):
    current, events, derived = store.snapshot(run_dir)
    summary = {"nodes": 0, "passed": 0, "attempts": 0, "rejections": 0,
               "duration_ms": None}
    result = {"run": summary, "nodes": {}, "human": human_metrics(events, derived),
              "stuck": {"refusals_recorded": False, "refusals_by_code": {},
                        "refusals": "not measurable from records",
                        "superseded_decisions": sum(e["type"] == "decision.superseded" for e in events),
                        "replan": sum(e["type"] == "gate.verdict" and e["data"].get("verdict") == "replan" for e in events),
                        "unverified_at_final": sum(e["type"] == "gate.final" and e["data"].get("result") == "unverified" for e in events)},
              "integrity": derived["run"].get("integrity", [])}
    init = next((e["ts"] for e in events if e["type"] == "run.init"), None)
    if len(events) >= 2:
        summary["duration_ms"] = _duration(init, events[-1]["ts"])
    for node in (current or {}).get("nodes", []):
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
        skipped = sum(len(e["data"].get("skipped_checks", []))
                      for e in recent if e["type"] == "gate.verdict")
        if skipped:
            metrics["checks_skipped"] = skipped
        assignments = [e["data"] for e in events if e["type"] == "node.assign" and e["data"].get("node") == nid]
        assignment = assignments[-1] if assignments else {}
        metrics.update(executor=assignment.get("executor"), model=assignment.get("model"),
                       cmd_checks=command_metrics(node, events, run_dir))
        metrics["rejection_history"] = [dict(attempt=e["data"].get("attempt"), verdict=e["data"].get("verdict"),
            checks=rejection_checks(current, events, e)) for e in recent
            if e["type"] == "gate.verdict" and e["data"].get("rejection")]
        result["nodes"][nid] = metrics
        summary["nodes"] += 1
        summary["passed"] += int(passed)
        for key in ("attempts", "rejections"):
            summary[key] += metrics[key]
    result["run_cmd_checks"] = command_metrics({"id": "_run", "checks":
        (current or {}).get("integration_checks", []) + (current or {}).get("promoted_checks", [])}, events, run_dir)
    result["conformance"] = conformance(current, events, result)
    if any(i["code"] == "plan_tampered" for i in result["integrity"]):
        for principle in ("P1", "P3", "P4", "P5"):
            result["conformance"][principle] = {"measurable": False, "observation": "not measurable from records"}
    if any(i["code"] in ("log_corrupt", "log_sequence") for i in result["integrity"]):
        result["conformance"] = {"P%d" % i: {"measurable": False, "observation": "not measurable from records"} for i in range(1, 13)}
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


HUMAN_KINDS = ("plan_approval", "decision_node", "lane3", "human_check",
               "hold", "trajectory", "evidence_reask", "plan_reapproval", "reask", "free")


def human_metrics(events, derived):
    by_kind = dict.fromkeys(HUMAN_KINDS, 0)
    decisions, slots, superseded = {}, {}, {}
    for event in events:
        data, kind = event["data"], event["type"]
        if kind == "decision.superseded":
            superseded[data.get("id")] = data.get("reason")
        elif kind == "decision.ask":
            did = data.get("id", "d%d" % event["seq"])
            purpose = data.get("purpose")
            slot = (data.get("issuer"), purpose, data.get("node"), data.get("check"))
            prior = slots.get(slot)
            category = "free"
            if data.get("issuer") == "plan" and purpose == "plan_approval":
                category = "plan_reapproval" if prior else "plan_approval"
            elif data.get("issuer") == "gate":
                category = {"node": "decision_node", "human_check": "human_check",
                            "lane3": "lane3", "hold": "hold", "trajectory": "trajectory"}.get(purpose, "free")
                if prior:
                    category = "evidence_reask" if superseded.get(prior) == "evidence_changed" else "reask"
            planned = category in ("plan_approval", "decision_node", "lane3", "human_check")
            decisions[did] = {"id": did, "kind": category, "planned": planned,
                              "asked_at": event["ts"], "answered_at": None, "wait_ms": None}
            slots[slot] = did
        elif kind == "decision.answer":
            decision = decisions.get(data.get("id"))
            # Count recorded human activity, not a fresh authorization of historical evidence.
            if decision and not decision["answered_at"] and data.get("id") not in superseded and (event.get("actor") or {}).get("role") == "human":
                decision["answered_at"] = event["ts"]
                decision["wait_ms"] = _duration(decision["asked_at"], event["ts"])
                by_kind[decision["kind"]] += 1
    answered = [d for d in decisions.values() if d["answered_at"]]
    planned = sum(d["planned"] for d in answered)
    return {"answers": {"total": len(answered), "planned": planned, "unplanned": len(answered) - planned,
                        "by_kind": by_kind},
            "wait": {"total_ms": sum(d["wait_ms"] for d in answered),
                     "longest_ms": max([d["wait_ms"] for d in answered] or [0]),
                     "decisions": list(decisions.values()),
                     "open": [d["id"] for d in derived["decisions"].values()
                              if d["status"] == "open" and not d.get("stale")]}}


def command_metrics(node, events, run_dir):
    result = {}
    for check in node.get("checks", []):
        if check["type"] != "cmd":
            continue
        records = [e for e in events if e["type"] in ("check.red", "check.result")
                   and e["data"].get("node") == node["id"]
                   and ("requires_passed" not in check or e["data"].get("check") == check["id"])
                   and checks.recorded_command(e, run_dir) == check["run"]]
        failures = [e["seq"] for e in records if e["data"].get("failed_first") is True
                    or e["data"].get("result") == "failed"]
        passes = [e for e in records if e["type"] == "check.result" and e["data"].get("result") == "passed"]
        result[check["id"]] = {"command": check["run"],
            "red_recorded": any(e["type"] == "check.red" and e["data"].get("failed_first") is True for e in records),
            "failure_observed": bool(failures), "passed": bool(passes),
            "passes": [{"seq": e["seq"], "failed_before": any(seq < e["seq"] for seq in failures)} for e in passes]}
    return result


def before_work_notices(current, events):
    nodes = plan.node_index(current or {})
    notices, seen = [], set()
    for event in events:
        data = event["data"]
        if event["type"] not in ("check.red", "check.result") or not data.get("passes_before_work"):
            continue
        key = (data.get("node"), data.get("attempt"), data.get("check"))
        if key in seen:
            continue
        seen.add(key)
        node = nodes.get(data.get("node"), {})
        check = next((c for c in node.get("checks", []) if c.get("id") == data.get("check")), {})
        notices.append(dict(code="passes_before_work", node=data.get("node"), check=data.get("check"),
                            attempt=data.get("attempt"), title=check.get("title") or data.get("check"),
                            node_title=node.get("title") or data.get("node")))
    return notices


def conformance(current, events, metrics):
    nodes = (current or {}).get("nodes", [])
    work = [n for n in nodes if n["kind"] == "work"]
    cmd = [c for n in metrics["nodes"].values() for c in n["cmd_checks"].values()] + list(metrics["run_cmd_checks"].values())
    starts = {}
    max_attempts = 0
    for event in events:
        if event["type"] == "node.start":
            nid = event["data"].get("node")
            starts[nid] = starts.get(nid, 0) + 1
            max_attempts = max(max_attempts, event["data"].get("attempt", starts[nid]))
    counts = {"work_nodes": len(work), "work_nodes_with_cmd": sum(any(c["type"] == "cmd" for c in n["checks"]) for n in work),
              "checks_never_observed_failing": sum(not c["failure_observed"] for c in cmd),
              "checks_passing_before_work": len(before_work_notices(current, events)),
              "passed_checks_never_observed_failing": sum(c["passed"] and not c["failure_observed"] for c in cmd)}
    applied = {cid for e in events if e["type"] == "constraint.apply" for cid in e["data"].get("ids", [])}
    unknown = {"measurable": False, "observation": "not measurable from records"}
    observations = {
        "P1": dict(counts, observation="work nodes with a cmd check: %(work_nodes_with_cmd)d/%(work_nodes)d; checks never observed failing: %(checks_never_observed_failing)d; passed checks never observed failing: %(passed_checks_never_observed_failing)d; checks passing before work: %(checks_passing_before_work)d" % counts),
        "P2": {"max_attempts": max_attempts, "replan": metrics["stuck"]["replan"]},
        "P3": {"edges": sum(len(n.get("needs", [])) for n in nodes),
               "edges_with_named_artifact": sum(bool(e.get("artifact")) for n in nodes for e in n.get("needs", []))},
        "P4": {"nodes": len(nodes), "nodes_with_owns": sum(bool(n.get("owns")) for n in nodes)},
        "P5": {"assignments": sum(e["type"] == "node.assign" for e in events),
               "reviews": sum(n["kind"] == "review" for n in nodes)},
        "P6": {"command_results": sum(e["type"] == "check.result" and e["data"].get("type") == "cmd" for e in events),
               "merges": sum(e["type"] == "merge.result" for e in events)},
        "P7": {"gate_verdicts": sum(e["type"] == "gate.verdict" for e in events)},
        "P8": dict(unknown),
        "P9": dict(unknown),
        "P10": {"answers": metrics["human"]["answers"], "wait_total_ms": metrics["human"]["wait"]["total_ms"],
                "wait_longest_ms": metrics["human"]["wait"]["longest_ms"], "open_decisions": len(metrics["human"]["wait"]["open"])},
        "P11": {"constraints_applied": len(applied), "constraints_added": sum(e["type"] == "constraint.add" for e in events)},
        "P12": {"refusals": "not measurable from records", "attempts": sum(starts.values()), "rejections": sum(e["type"] == "gate.verdict" and e["data"].get("verdict") == "reject" for e in events),
                "superseded_decisions": metrics["stuck"]["superseded_decisions"], "unverified_at_final": metrics["stuck"]["unverified_at_final"]}}
    skipped = sum(len(e["data"].get("skipped_checks", []))
                  for e in events if e["type"] == "gate.verdict")
    if skipped:
        observations["P12"]["run_checks_skipped"] = skipped
    for principle, observation in observations.items():
        if "observation" not in observation:
            if principle == "P10":
                answers = observation["answers"]
                kinds = ", ".join("%s %d" % (kind, count) for kind, count in sorted(answers["by_kind"].items())
                                  if count and kind not in ("plan_approval", "decision_node", "lane3", "human_check"))
                observation["observation"] = "human answers %d (planned %d, unplanned %d%s); waited %s; longest %s; open %d" % (answers["total"], answers["planned"], answers["unplanned"], ": " + kinds if kinds else "", _elapsed(observation["wait_total_ms"]), _elapsed(observation["wait_longest_ms"]), observation["open_decisions"])
            else:
                observation["observation"] = "; ".join("%s %s" % (k.replace("_", " "), v) for k, v in observation.items())
    return observations


def _elapsed(ms):
    seconds = ms // 1000
    return "%dm%02ds" % (seconds // 60, seconds % 60)


def render_conformance(result):
    lines = ["%s %s" % (p, result["conformance"][p]["observation"]) for p in ("P%d" % i for i in range(1, 13))]
    lines.extend("%s: %s" % (item["code"], item["recovery"]) for item in result.get("integrity", []))
    return "\n".join(lines)
