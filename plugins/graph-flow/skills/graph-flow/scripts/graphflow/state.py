"""Replay of the event log into state (records.md sections 3, 5, 6, 7).

`derive(plan, events)` reads only its arguments and, through `core.human_sig`,
$GF_HOME/human.key. It never reads the run directory.
"""
import copy
import hashlib
import hmac
import json

from . import core

VERDICT_STATUS = {
    "pass": "passed",
    "reject": "rejected",
    "unverified": "unverified",
    "hold": "held",
    "needs_approval": "awaiting_approval",
    "replan": "replan",
}

ASSIGN_KEYS = ("executor", "model", "effort", "provider", "family", "isolation")
SUBMIT_KEYS = ("attempt", "commit", "branch", "changed_files", "notes", "low_confidence")
REVIEW_KEYS = ("attempt", "target", "target_submission", "verdict", "findings")
REVIEWED_STATUSES = ("submitted", "unverified", "held", "awaiting_approval", "passed")
PHASES = ("loop", "gate")


def fingerprint(node):
    node = copy.deepcopy(node)
    for key in ("title", "summary", "context"):
        node.pop(key, None)
    for need in node.get("needs") or []:
        if isinstance(need, dict):
            need.pop("label", None)
    for check in node.get("checks") or []:
        if isinstance(check, dict):
            check.pop("title", None)
            check.pop("context", None)
    text = json.dumps(node, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def plan_identity(plan):
    """Bind consent to executable structure, using the same presentation exclusions."""
    value = copy.deepcopy(plan)
    for key in ("title", "summary", "context"):
        value.pop(key, None)
    value["nodes"] = {n["id"]: fingerprint(n) for n in value.get("nodes", [])}
    for check in value.get("integration_checks", []):
        check.pop("title", None)
        check.pop("context", None)
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=False).encode("utf-8")).hexdigest()


def plan_approval(derived):
    identity = derived.get("run", {}).get("plan_identity")
    if not derived.get("run", {}).get("approval_required", bool(identity)):
        return None  # Only histories without a marker or identity are legacy.
    if not identity:
        return {}
    matches = [d for d in derived.get("decisions", {}).values()
               if d.get("purpose") == "plan_approval" and d.get("plan_identity") == identity
               and not d.get("stale")]
    return max(matches, key=lambda d: d["seq"]) if matches else {}


def require_plan_approval(derived):
    run = derived.get("run", {})
    if run.get("plan_error"):
        raise core.GFError("plan_tampered", "Plan differs from the recorded structural identity", core.EXIT_STATE)
    if run.get("key_mismatch") and run.get("approval_required"):
        raise core.GFError("human_key_mismatch", "This GF_HOME key differs from the run's recorded human key", core.EXIT_STATE)
    approval = plan_approval(derived)
    if approval is not None and not (approval.get("status") == "answered"
            and approval.get("verified") and approval.get("outcome") == "approved"):
        did = approval.get("id", "missing")
        raise core.GFError("plan_not_approved", "Plan needs human approval (%s); show: gf open --decision %s"
                           % (did, did), core.EXIT_STATE)


def _data(ev):
    d = ev.get("data")
    return d if isinstance(d, dict) else {}


def _closure(nodes):
    """Map node id -> set of node ids it depends on, directly or transitively."""
    direct = {}
    for nid, node in nodes.items():
        d = set()
        for need in node.get("needs") or []:
            if isinstance(need, dict) and need.get("from") in nodes:
                d.add(need["from"])
        if node.get("kind") == "review" and node.get("target") in nodes:
            d.add(node["target"])
        direct[nid] = d
    out = {}
    for nid in nodes:
        seen, todo = set(), list(direct[nid])
        while todo:
            cur = todo.pop()
            if cur not in seen and cur != nid:
                seen.add(cur)
                todo.extend(direct[cur])
        out[nid] = seen
    return out


def _fresh(node, basis):
    checks = {}
    for c in node.get("checks") or []:
        if isinstance(c, dict) and isinstance(c.get("id"), str):
            checks[c["id"]] = {"loop": None, "gate": None}
    return {
        "status": "pending",
        "basis": basis,
        "attempts": 0,
        "assignment": None,
        "base": None,
        "submission": None,
        "checks": checks,
        "red": {},
        "rejections": [],
        "verdict": None,
        "merged_head": None,
        "results": [],  # check.result data of the current attempt
    }


def _sub_id(acc):
    sub = acc["submission"]
    return sub["id"] if sub is not None else None


def derive(plan, events):
    events = [ev for ev in (events or []) if isinstance(ev, dict)]
    nodes = {}
    if isinstance(plan, dict):
        for n in plan.get("nodes") or []:
            if isinstance(n, dict) and isinstance(n.get("id"), str):
                nodes[n["id"]] = n

    deps = _closure(nodes)
    acc = {nid: _fresh(n, 0) for nid, n in nodes.items()}
    reviewers = {nid: [] for nid in nodes}  # work node -> review nodes targeting it, plan order
    for nid, n in nodes.items():
        if n.get("kind") == "review" and n.get("target") in reviewers:
            reviewers[n["target"]].append(nid)

    run_id = None
    plan_revision = 0
    current_identity = None
    approval_required = any(
        (e.get("type") == "run.init" and (_data(e).get("approval_required") or _data(e).get("schema_version", 1) >= 2))
        or (e.get("type") == "plan.set" and _data(e).get("plan_identity") is not None) for e in events)
    pinned_key = next((_data(e).get("human_key_sha256") for e in events
                      if e.get("type") in ("run.init", "human.key") and _data(e).get("human_key_sha256")), None)
    key_mismatch = bool(pinned_key and pinned_key != core.key_fingerprint())
    host = []
    final = None
    decisions = {}
    sigs = {}
    prev_fps = None
    ever_seen = set()
    last_reset_seq = 0  # latest plan.set, node.reopen or gate.verdict

    def invalidate(nid, seq):
        # The assignment survives an invalidation: who does the work has not changed.
        kept = acc[nid]["assignment"] if nid in acc else None
        acc[nid] = _fresh(nodes[nid], seq)
        if kept is not None:
            acc[nid]["assignment"] = kept
            acc[nid]["status"] = "assigned"

    def node_acc(nid):
        return acc.get(nid) if isinstance(nid, str) else None

    for i, ev in enumerate(events):
        seq = ev.get("seq") if isinstance(ev.get("seq"), int) else i + 1
        t = ev.get("type")
        d = _data(ev)
        if run_id is None and isinstance(ev.get("run"), str):
            run_id = ev["run"]

        if t == "run.init":
            if d.get("run_id") is not None:
                run_id = d["run_id"]

        elif t == "plan.set":
            current_identity = d.get("plan_identity")
            last_reset_seq = max(last_reset_seq, seq)
            if d.get("revision") is not None:
                plan_revision = d["revision"]
            fps = d.get("fingerprints")
            if not isinstance(fps, dict):
                continue
            changed = set()
            for nid, fp in fps.items():
                if prev_fps is not None and nid in prev_fps:
                    if prev_fps[nid] != fp:
                        changed.add(nid)
                elif nid in ever_seen:  # removed earlier, now re-added
                    changed.add(nid)
            ever_seen.update(fps)
            prev_fps = dict(fps)
            for nid in nodes:
                if nid in changed or deps[nid] & changed:
                    invalidate(nid, seq)

        elif t == "host.set":
            caps = d.get("capabilities")
            host = list(caps) if isinstance(caps, list) else []

        elif t == "gate.final":
            final = copy.deepcopy(d)
            final["seq"] = seq

        elif t == "node.reopen":
            last_reset_seq = max(last_reset_seq, seq)
            target = d.get("node")
            if target not in nodes:
                continue
            for nid in nodes:
                if nid == target or target in deps[nid]:
                    invalidate(nid, seq)

        elif t == "node.assign":
            a = node_acc(d.get("node"))
            if a is not None:
                a["assignment"] = {k: copy.deepcopy(d.get(k)) for k in ASSIGN_KEYS}
                if a["status"] == "pending":
                    a["status"] = "assigned"

        elif t == "node.start":
            nid = d.get("node")
            a = node_acc(nid)
            if a is None:
                continue
            for rid in reviewers.get(nid, ()):
                invalidate(rid, seq)
            a["status"] = "running"
            a["attempts"] += 1
            a["base"] = copy.deepcopy(d.get("base"))
            a["submission"] = None
            a["verdict"] = None
            a["merged_head"] = None
            a["results"] = []
            for slot in a["checks"].values():
                slot["loop"] = slot["gate"] = None

        elif t == "check.red":
            a = node_acc(d.get("node"))
            if a is not None and isinstance(d.get("check"), str):
                a["red"][d["check"]] = copy.deepcopy(d)

        elif t == "check.result":
            a = node_acc(d.get("node"))
            cid = d.get("check")
            if a is None or not isinstance(cid, str) or d.get("attempt") != a["attempts"]:
                continue
            slot = a["checks"].setdefault(cid, {"loop": None, "gate": None})
            if d.get("phase") in PHASES:
                slot[d["phase"]] = copy.deepcopy(d)
            a["results"].append(d)

        elif t in ("node.submit", "review.submit"):
            a = node_acc(d.get("node"))
            if a is None:
                continue
            keys = SUBMIT_KEYS if t == "node.submit" else REVIEW_KEYS
            sub = {"id": seq}
            sub.update({k: copy.deepcopy(d.get(k)) for k in keys})
            a["submission"] = sub
            a["status"] = "submitted"

        elif t == "merge.result":
            for m in d.get("merged") or []:
                if not isinstance(m, dict):
                    continue
                a = node_acc(m.get("node"))
                if a is None or a["submission"] is None:
                    continue
                commit = a["submission"].get("commit")
                if commit is not None and m.get("commit") == commit:
                    a["merged_head"] = m.get("head")

        elif t == "gate.verdict":
            last_reset_seq = max(last_reset_seq, seq)
            nid = d.get("node")
            a = node_acc(nid)
            if a is None:
                continue
            v = d.get("verdict")
            if v in VERDICT_STATUS:
                a["status"] = VERDICT_STATUS[v]
            if v in ("reject", "replan") and d.get("rejection") is not None:
                a["rejections"].append(copy.deepcopy(d["rejection"]))
            if nodes[nid].get("kind") == "decision":
                a["verdict"] = copy.deepcopy(d)
            elif a["submission"] is not None and d.get("submission") == _sub_id(a):
                a["verdict"] = copy.deepcopy(d)

        elif t == "decision.ask":
            did = d.get("id")
            if not isinstance(did, str):
                did = "d%d" % seq
            decisions[did] = {
                "id": did,
                "seq": seq,
                "node": d.get("node"),
                "submission": d.get("submission"),
                "check": d.get("check"),
                "purpose": d.get("purpose"),
                "plan_identity": d.get("plan_identity"),
                "kind": d.get("kind"),
                "question": d.get("question"),
                "evidence": copy.deepcopy(d.get("evidence")),
                "status": "open",
                "outcome": None,
                "answer": None,
                "source": None,
                "verified": False,
                "stale": False,
            }

        elif t == "decision.superseded":
            dec = decisions.get(d.get("id"))
            if dec is not None:
                dec["status"] = "superseded"
                dec["stale"] = True

        elif t == "decision.answer":
            dec = decisions.get(d.get("id"))
            if dec is None or dec["status"] != "open":
                continue  # unknown id, or a later answer: the first one wins
            dec["status"] = "answered"
            dec["outcome"] = d.get("outcome")
            dec["answer"] = d.get("answer")
            dec["source"] = d.get("source")
            sigs[dec["id"]] = d.get("sig")
        # every other type is ignored

    for did, dec in decisions.items():
        if dec.get("purpose") == "plan_approval" and dec.get("plan_identity") != current_identity:
            dec["stale"] = True
        sig = sigs.get(did)
        if dec["status"] == "answered" and isinstance(sig, str):
            modern = sig.startswith("v2:")
            is_plan = dec.get("purpose") == "plan_approval"
            expected = (core.human_sig(run_id, did, dec["outcome"], dec["answer"], dec if modern else None)
                        if not is_plan or modern and pinned_key and not key_mismatch else None)
            if expected is not None:
                dec["verified"] = hmac.compare_digest(
                    expected.encode("utf-8"), sig.encode("utf-8"))
        nid = dec["node"]
        if nid is None:
            continue
        a = node_acc(nid)
        if a is None:
            dec["stale"] = True
        else:
            dec["stale"] = (a["basis"] >= dec["seq"]
                            or (dec["submission"] is not None
                                and dec["submission"] != _sub_id(a)))

    out_nodes = {}
    for nid, node in nodes.items():
        a = acc[nid]
        node_reviews = []
        for rid in reviewers[nid] if node.get("kind") == "work" else ():
            r = acc[rid]
            if r["status"] not in REVIEWED_STATUSES:
                continue
            sub = r["submission"] or {}
            node_reviews.append({
                "node": rid,
                "status": r["status"],
                "target_submission": sub.get("target_submission"),
                "verdict": sub.get("verdict"),
                "family": r["assignment"].get("family") if r["assignment"] else None,
                "findings": copy.deepcopy(sub.get("findings") or []),
            })
        clean = a["attempts"] <= 2
        for res in a["results"]:
            if res.get("timed_out") is True:
                clean = False
            if res.get("phase") == "loop" and res.get("type") == "scope" and res.get("violations"):
                clean = False
        out_nodes[nid] = {
            "status": a["status"],
            "kind": node.get("kind"),
            "lane": node.get("lane"),
            "effective_lane": node.get("effective_lane", node.get("lane")),
            "basis": a["basis"],
            "attempts": a["attempts"],
            "max_attempts": node.get("max_attempts", 3),
            "assignment": a["assignment"],
            "base": a["base"],
            "submission": a["submission"],
            "checks": a["checks"],
            "red": a["red"],
            "reviews": node_reviews,
            "rejections": a["rejections"],
            "verdict": a["verdict"],
            "merged_head": a["merged_head"],
            "trajectory_clean": clean,
            "open_decisions": [
                did for did, dec in decisions.items()
                if dec["node"] == nid and dec["status"] == "open" and not dec["stale"]
            ],
        }

    complete = (
        bool(out_nodes)
        and all(n["status"] == "passed" for n in out_nodes.values())
        and final is not None
        and final.get("result") == "passed"
        and final["seq"] > last_reset_seq
    )
    return {
        "run": {
            "id": run_id,
            "plan_revision": plan_revision,
            "plan_identity": current_identity,
            "approval_required": approval_required,
            "human_key_sha256": pinned_key,
            "key_mismatch": key_mismatch,
            "plan_error": bool(current_identity and plan_identity(plan or {}) != current_identity),
            "status": "complete" if complete else "open",
            "host": host,
            "final": final,
        },
        "nodes": out_nodes,
        "decisions": decisions,
    }
