"""Replay of the event log into state (plan.md and records.md sections 5, 6, 7).

`derive(plan, events)` verifies filesystem-bound consent using store.EventLog context.
Recorded fingerprints and recorded filesystem locations are never trusted.
"""
import copy
import hashlib
import hmac
import json
import subprocess

from . import core, plan as planning, store

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


def fingerprint(node, plan=None):
    node = copy.deepcopy(node)
    if plan and node.get("kind") == "decision":
        nodes = planning.node_index(plan)
        node["releases"] = sorted((nid, fingerprint(nodes[nid]))
                                  for nid, deps in _closure(nodes).items() if node["id"] in deps)
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
    value["nodes"] = sorted(fingerprint(n) for n in value.get("nodes", []))
    for check in value.get("integration_checks", []):
        check.pop("title", None)
        check.pop("context", None)
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=False).encode("utf-8")).hexdigest()


def plan_approval(derived):
    identity = derived.get("run", {}).get("plan_identity")
    if not identity:
        return {}
    matches = [d for d in derived.get("decisions", {}).values()
               if d.get("purpose") == "plan_approval" and d.get("issuer") == "plan" and d.get("plan_identity") == identity
               and not d.get("stale")]
    return max(matches, key=lambda d: d["seq"]) if matches else {}


def require_plan_approval(derived):
    run = derived.get("run", {})
    if run.get("plan_error"):
        raise core.GFError("plan_tampered", "Plan differs from the recorded structural identity", core.EXIT_STATE)
    if run.get("location_mismatch"):
        raise core.GFError("project_moved", "Moving or renaming a project directory or run invalidates approvals. "
                           "Re-post this run's plans/NNNN.json with gf plan set, then approve once more.", core.EXIT_STATE)
    if run.get("key_mismatch"):
        raise core.GFError("human_key_mismatch", key_recovery(run), core.EXIT_STATE)
    approval = plan_approval(derived)
    if approval is not None and not (approval.get("status") == "answered"
            and approval.get("verified") and approval.get("outcome") == "approved"):
        if not approval.get("id"):
            raise core.GFError("plan_not_approved", "Set the current plan with gf plan set <file>, then have the person approve it", core.EXIT_STATE)
        if approval.get("verified") and approval.get("outcome") in ("rejected", "revision_requested"):
            raise core.GFError("plan_not_approved", "The person sent the plan back: %s. Revise it and run gf plan set <file>."
                               % approval.get("answer", ""), core.EXIT_STATE)
        did = approval["id"]
        raise core.GFError("plan_not_approved", "Plan needs human approval (%s); show: gf open --decision %s"
                           % (did, did), core.EXIT_STATE)


def key_recovery(run):
    return ("The human key was lost, rotated, or this process uses a different GF_HOME. "
            "Use the original GF_HOME/key, or in your own terminal run: "
            "GF_ROLE=human GF_HUMAN_TERMINAL=1 graph-flow --run <run-path> key repin; "
            "then approve the plan again.")


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


def submission_binding(submission):
    return copy.deepcopy(submission)


def artifact_bytes(run_dir, relative, submission=None, log=False):
    """One byte source for consent hashes and the dashboard. Never dereference a git symlink."""
    import pathlib
    import os
    import stat
    import subprocess
    from . import server
    root = store.project_of(run_dir)
    base = pathlib.Path(run_dir) if log else root
    commit = (submission or {}).get("commit") if not log else None
    target = server._file_path(base, relative, committed=bool(commit))
    if commit:
        if not isinstance(commit, str) or not __import__('re').fullmatch(r"[0-9a-fA-F]{40,64}", commit):
            raise ValueError("invalid commit")
        entry = subprocess.run(["git", "-C", str(root), "ls-tree", "-z", commit, "--", relative],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True).stdout
        if not entry.startswith((b"100644 blob ", b"100755 blob ")):
            raise ValueError("not a regular committed file")
        oid = entry.split(b"\t", 1)[0].split()[-1].decode("ascii")
        size = int(subprocess.check_output(["git", "-C", str(root), "cat-file", "-s", oid]))
        if size > server.MAX_FILE_SCAN:
            raise ValueError("attachment too large")
        return subprocess.check_output(["git", "-C", str(root), "cat-file", "blob", oid])
    fd = server._open_project_file(base, target)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > server.MAX_FILE_SCAN:
            raise ValueError("not a readable attachment")
        for name in ("human.key", "server.json", "registry.json"):
            secret = core.gf_home() / name
            if secret.exists() and os.path.samestat(info, secret.stat()):
                raise server._HTTPError(403, "forbidden_path", "this file cannot be opened")
        raw = stream.read(server.MAX_FILE_SCAN + 1)
        if len(raw) > server.MAX_FILE_SCAN:
            raise ValueError("attachment too large")
        return raw


def artifact_hashes(run_dir, evidence, submission=None):
    if run_dir is None:
        return {}
    evidence = evidence if isinstance(evidence, dict) else {}
    files = [p for values in (evidence.get("files"), (submission or {}).get("changed_files"))
             if isinstance(values, list) for p in values if isinstance(p, str)]
    paths = [("file:" + p, p, False) for p in files]
    for slots in (evidence.get("checks") or {}).values() if isinstance(evidence.get("checks"), dict) else []:
        for result in (slots or {}).values():
            if isinstance(result, dict) and isinstance(result.get("log"), str):
                paths.append(("log:" + result["log"], result["log"], True))
    hashes = {}
    for name, relative, log in paths:
        try:
            hashes[name] = hashlib.sha256(artifact_bytes(run_dir, relative, submission, log)).hexdigest()
        except Exception:
            hashes[name] = None
    return hashes


def decision_identity(decision):
    """What the person saw, returned unchanged with an answer (also for plan banners)."""
    content = {k: decision.get(k) for k in ("question", "evidence", "plan_identity", "submission_binding", "location")}
    return {"id": decision["id"], "question_hash": hashlib.sha256(json.dumps(content,
            sort_keys=True, ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest(),
            "artifact_hashes": decision.get("artifact_hashes") or {}}


def require_submission_binding(derived, node_id, refresh=False):
    sub = (derived["nodes"].get(node_id) or {}).get("submission") or {}
    for dec in derived["decisions"].values():
        if (dec.get("issuer") == "gate" and (not dec.get("stale") or dec.get("stale_reason") == "evidence_changed") and dec.get("outcome") is not None and dec.get("node") == node_id and dec.get("submission") == sub.get("id")
                and dec.get("purpose") in ("human_check", "lane3", "trajectory", "hold")
                and (dec.get("stale_reason") == "evidence_changed" or dec.get("binding_changed") or dec.get("status") == "answered" and not dec.get("verified"))):
            if refresh and dec.get("stale_reason") == "evidence_changed":
                continue
            newer = any(d.get("node") == node_id and d.get("purpose") == dec.get("purpose")
                        and d.get("check") == dec.get("check") and d["seq"] > dec["seq"]
                        and d.get("verified") and not d.get("stale") and d.get("outcome") == "approved"
                        for d in derived["decisions"].values())
            if not newer:
                raise core.GFError("approval_changed", "The submission or evidence differs from the human approval. Run the gate again to request current evidence approval; if the signed record was altered, restore the intact record first.", core.EXIT_STATE)


def derive(plan, events):
    run_dir = getattr(events, "run_dir", None)
    actual_location = store.location(run_dir) if run_dir is not None else None
    events = [ev for ev in (events or []) if isinstance(ev, dict)]
    nodes = planning.node_index(plan)

    deps = _closure(nodes)
    acc = {nid: _fresh(n, 0) for nid, n in nodes.items()}
    reviewers = {nid: [] for nid in nodes}  # work node -> review nodes targeting it, plan order
    for nid, n in nodes.items():
        if n.get("kind") == "review" and n.get("target") in reviewers:
            reviewers[n["target"]].append(nid)

    run_id = None
    plan_revision = 0
    current_identity = None
    approval_required = True
    run_nonce = next((_data(e).get("run_nonce") for e in events
                      if e.get("type") in ("run.init", "run.nonce") and _data(e).get("run_nonce")), None)
    legacy = not any(e.get("type") == "run.init" and _data(e).get("run_nonce") for e in events)
    repin_seq = 0
    repins = []
    for e in events:
        d = _data(e)
        if e.get("type") == "human.repin" and d.get("run_nonce") and d.get("human_key_sha256") == core.key_fingerprint():
            expected = core.human_sig(e.get("run"), "human.repin", "repinned", "", d) if d.get("location") else None
            if expected and hmac.compare_digest(expected, str(d.get("sig", ""))):
                repins.append(e)
    pinned_key = next((_data(e).get("human_key_sha256") for e in events
                      if e.get("type") in ("run.init", "human.key") and _data(e).get("human_key_sha256")), None)
    if repins:
        repin = repins[-1]
        pinned_key, run_nonce, repin_seq = (_data(repin)["human_key_sha256"], _data(repin)["run_nonce"], repin["seq"])
    key_mismatch = bool(pinned_key and pinned_key != core.key_fingerprint())
    host = []
    final = None
    decisions = {}
    sigs = {}
    prev_fps = None
    ever_seen = set()
    identity_revision_seq = 0
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
            if not d.get("approval_reused") or d.get("plan_identity") != current_identity:
                identity_revision_seq = seq
            current_identity = d.get("plan_identity")
            last_reset_seq = max(last_reset_seq, seq)
            if d.get("revision") is not None:
                plan_revision = d["revision"]
            if run_dir is not None:
                try:
                    revision_plan = store._load_plan(run_dir, int(d["revision"]), d)
                    fps = {nid: fingerprint(n, revision_plan) for nid, n in planning.node_index(revision_plan).items()}
                except (core.GFError, KeyError, ValueError, TypeError):
                    fps = {}
                    for nid in nodes:
                        invalidate(nid, seq)
            else:
                # Pure replay has no file authority: it cannot preserve work across a revision.
                fps = {nid: fingerprint(n) for nid, n in nodes.items()}
                if prev_fps is not None:
                    for nid in nodes:
                        invalidate(nid, seq)
            changed = set(nodes) if d.get("replaced_unverifiable") else set()
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
                slot[d["phase"]] = dict(copy.deepcopy(d), id=seq)
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
            if d.get("merged_head"):
                a["merged_head"] = d["merged_head"]
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
                "issuer": d.get("issuer"),
                "reason": d.get("reason"),
                "plan_identity": d.get("plan_identity"),
                "location": actual_location,
                "recorded_location": copy.deepcopy(d.get("location")),
                "submission_binding": copy.deepcopy(d.get("submission_binding")),
                "artifact_hashes": copy.deepcopy(d.get("artifact_hashes")),
                "binding_changed": False,
                "legacy_binding": run_dir is not None and not all(k in d for k in ("location", "submission_binding", "artifact_hashes")),
                "run_nonce": run_nonce,
                "human_key_sha256": pinned_key,
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
                if d.get("reason"):
                    dec["stale_reason"] = d["reason"]

        elif t == "decision.answer":
            dec = decisions.get(d.get("id"))
            if dec is None or dec["status"] != "open":
                continue  # unknown id, or a later answer: the first one wins
            dec["status"] = "answered"
            dec["outcome"] = d.get("outcome")
            dec["answer"] = d.get("answer")
            dec["source"] = d.get("source")
            sigs[dec["id"]] = d.get("sig")
            dec["answer_seq"] = seq
        # every other type is ignored

    for did, dec in decisions.items():
        if dec["legacy_binding"]:
            dec["stale"] = True
            dec["stale_reason"] = "legacy_decision"
        if dec["seq"] < repin_seq or dec.get("purpose") == "plan_approval" and dec["seq"] < identity_revision_seq or dec.get("purpose") == "plan_approval" and dec.get("plan_identity") != current_identity:
            dec["stale"] = True
        sig = sigs.get(did)
        if dec.get("answer_seq") is not None and isinstance(sig, str):
            # Old signatures are history only, never authorization for new execution.
            modern = sig.startswith("v3:")
            expected = (core.human_sig(run_id, did, dec["outcome"], dec["answer"], dec)
                        if modern and actual_location and run_nonce and pinned_key and not key_mismatch and dec["seq"] > repin_seq else None)
            if expected is not None:
                dec["verified"] = hmac.compare_digest(
                    expected.encode("utf-8"), sig.encode("utf-8"))
        nid = dec["node"]
        if nid is None:
            if not (dec.get("purpose") == "plan_approval" and dec["status"] == "answered") and run_dir is not None and not dec["legacy_binding"] and dec.get("artifact_hashes") != artifact_hashes(run_dir, dec.get("evidence")):
                dec["binding_changed"] = True
                if dec["status"] == "open" or dec["verified"]:
                    dec["stale"] = True
                    dec["stale_reason"] = "evidence_changed"
                dec["verified"] = False
            continue
        a = node_acc(nid)
        if a is None:
            dec["stale"] = True
        else:
            sub = a.get("submission")
            if run_dir is not None and not dec["legacy_binding"] and dec.get("submission") == _sub_id(a):
                dec["binding_changed"] = (dec.get("submission_binding") != submission_binding(sub)
                    or dec.get("artifact_hashes") != artifact_hashes(run_dir, dec.get("evidence"), sub))
                if dec["binding_changed"]:
                    if (dec["status"] == "open" or dec["verified"]) and dec.get("submission_binding") == submission_binding(sub):
                        dec["stale"] = True
                        dec["stale_reason"] = "evidence_changed"
                    dec["verified"] = False
            dec["stale"] = dec["stale"] or (a["basis"] >= dec["seq"]
                            or (dec["submission"] is not None
                                and dec["submission"] != _sub_id(a)))

    for dec in decisions.values():
        if actual_location and dec.get("recorded_location") and dec["recorded_location"] != actual_location:
            dec["stale"] = True
            dec["stale_reason"] = "project_moved"

    # Supersession remains derivable if a writer deletes the convenience events.
    plan_decisions = [d for d in decisions.values() if d.get("purpose") == "plan_approval"]
    if plan_decisions:
        latest = max(plan_decisions, key=lambda d: d["seq"])
        for dec in plan_decisions:
            if dec is not latest:
                dec["stale"] = True
                dec["status"] = "superseded"
    latest_gate = {}
    for dec in decisions.values():
        if dec.get("issuer") == "gate":
            key = (dec.get("node"), dec.get("purpose"), dec.get("check"))
            previous = latest_gate.get(key)
            if previous:
                previous["stale"] = True
                previous["status"] = "superseded"
            latest_gate[key] = dec

    location_mismatch = bool(actual_location and any(
        d.get("recorded_location") and d["recorded_location"] != actual_location
        and d.get("purpose") == "plan_approval" and d is latest
        for d in decisions.values()))

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
                "id": sub.get("id"),
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
        and all(n["status"] == "passed" and (not (n.get("submission") or {}).get("commit")
                or n.get("merged_head")) for n in out_nodes.values())
        and final is not None
        and final.get("result") == "passed"
        and final["seq"] > last_reset_seq
    )
    if complete and run_dir is not None:
        for node in out_nodes.values():
            commit = (node.get("submission") or {}).get("commit")
            if commit and subprocess.run(["git", "-C", str(store.project_of(run_dir)),
                    "merge-base", "--is-ancestor", commit, "HEAD"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode:
                complete = False
                break
    return {
        "run": {
            "id": run_id,
            "plan_revision": plan_revision,
            "plan_identity": current_identity,
            "approval_required": approval_required,
            "run_nonce": run_nonce,
            "legacy": legacy,
            "repin_seq": repin_seq,
            "human_key_sha256": pinned_key,
            "key_mismatch": key_mismatch,
            "location_mismatch": location_mismatch,
            "location": actual_location,
            "plan_error": bool(current_identity and plan_identity(plan or {}) != current_identity),
            "status": "complete" if complete else "open",
            "host": host,
            "final": final,
        },
        "nodes": out_nodes,
        "decisions": decisions,
    }
