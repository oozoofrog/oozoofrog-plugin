"""Evidence-ordered gates and lane rules (records.md section 6, P7-P10)."""
import copy
import importlib
import hashlib
import json
import pathlib
import subprocess

from . import checks, core, graph, plan as planmod, state as statemod, store

__all__ = ["evaluate", "build_rejection", "render_rejection", "gate", "gate_final", "reopen"]


def _decisions(state, node_id, submission, check, purpose, kind, request):
    return [d for d in state.get("decisions", {}).values()
            if d.get("issuer") == "gate" and not d.get("stale") and d.get("node") == node_id
            and d.get("submission") == submission and d.get("check") == check
            and d.get("purpose") == purpose
            and (kind is None or d.get("kind") == kind)
            and all(d.get(k) == request.get(k)
                    for k in ("question", "evidence", "kind"))]


def _answered(decisions, outcomes):
    return any(d.get("verified") and d.get("status") == "answered"
               and d.get("outcome") in outcomes for d in decisions)


def _ask(node, node_state, purpose, check=None, kind="review", question=None, rollbacks=0):
    submission = node_state.get("submission") or {}
    human = next((c for c in node.get("checks", []) if c.get("id") == check), {})
    context = human.get("context", {}) if purpose == "human_check" else node.get("context", {})
    author_context = copy.deepcopy(context)
    if purpose in ("hold", "trajectory", "lane3"):
        context = {}
    prompt = human.get("prompt") or human.get("title") or node.get("goal", "")
    question = (node.get("question") if purpose == "node" else prompt if purpose == "human_check"
                else question or "Approve %s: %s?" % (purpose, node.get("goal", node["id"])))
    ko = planmod.is_korean(node)
    if purpose in ("hold", "trajectory", "lane3"):
        questions = {
            "hold": ("실패한 검사와 검토 의견을 확인하고도 이 결과를 받아들일까요?", "Accept this result despite the listed failed checks and reviews?"),
            "trajectory": ("수정과 되돌림 기록을 확인하고 이 결과를 받아들일까요?", "Accept this result after reviewing the corrections and rollbacks?"),
            "lane3": ("일을 마쳤어요. 이 결과를 받아들일까요?", "The work is submitted. Accept this result?")}
        question = questions[purpose][0 if ko else 1]
    records = []
    for cid, slots in sorted(node_state.get("checks", {}).items()):
        result = slots.get("loop")
        if result:
            records.append({"type": "check", "id": result.get("id", cid), "value": result})
    for review in node_state.get("reviews", []):
        if review.get("status") == "passed" and review.get("target_submission") == submission.get("id"):
            records.append({"type": "review", "id": review.get("id", review.get("node")), "value": review})
    for record in records:
        record["sha256"] = hashlib.sha256(json.dumps(record["value"], sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return {"issuer": "gate", "node": node["id"], "submission": submission.get("id"),
            "check": check, "purpose": purpose, "kind": kind,
            "question": question,
            "evidence": {
                "command": [c["run"] for c in node.get("checks", []) if c.get("type") == "cmd"],
                "files": list(submission.get("changed_files") or []),
                "checks": {cid: {"loop": copy.deepcopy(slots["loop"])}
                           for cid, slots in node_state.get("checks", {}).items() if slots.get("loop")},
                "context": copy.deepcopy(context),
                "author_context": author_context,
                "contract": planmod.node_contract(node),
                "records": records, "rollbacks": rollbacks,
                "trajectory_clean": node_state.get("trajectory_clean", True)}}


def _approval_rule(state, node, requests, rule):
    """Resolve missing approvals together; never duplicate an outstanding ask."""
    asks = []
    missing = False
    for request in requests:
        decisions = _decisions(state, node["id"], request["submission"], request["check"],
                               request["purpose"], request["kind"], request)
        if _answered(decisions, ("approved",)):
            continue
        if _answered(decisions, ("rejected", "revision_requested")):
            return {"verdict": "hold", "rule": "R4", "failed": [], "asks": [],
                    "message": "The person sent this decision back. Revise and re-post the plan (raise max_attempts or replace the node if attempts are exhausted), then submit corrected work before asking again."}
        missing = True
        bound = _decisions(state, node["id"], request["submission"], request["check"],
                           request["purpose"], None, request)
        if not any(d.get("status") == "open" for d in bound):
            asks.append(request)
    if missing:
        return {"verdict": "needs_approval", "rule": rule, "failed": [], "asks": asks}
    return None


def evaluate(plan, state, node_id, gate_results, integration_results, rollbacks):
    """Pure verdict computation; supplied state already verifies human signatures."""
    node = planmod.node_by_id(plan, node_id)
    st = state["nodes"][node_id]
    submission = (st.get("submission") or {}).get("id")

    def verdict(value, rule, failed=None, asks=None):
        return {"verdict": value, "rule": rule, "failed": failed or [], "asks": asks or []}

    if node["kind"] == "decision":
        request = _ask(node, st, "node", kind=node["decision_kind"])
        decisions = _decisions(state, node_id, None, None, "node", node["decision_kind"], request)
        if _answered(decisions, ("approved",) if node["decision_kind"] in ("review", "authorization") else ("answered",)):
            return verdict("pass", "R7")
        if _answered(decisions, ("rejected", "revision_requested")):
            return dict(verdict("hold", "R4"), message="The person sent this decision back. Revise the question and re-post the plan; dependents remain blocked.")
        asks = [] if any(d.get("status") == "open" for d in decisions) else [
            request]
        return verdict("needs_approval", "R6", asks=asks)

    failed = [r for r in list(gate_results) + list(integration_results)
              if r.get("grade") == 1 and r.get("result") == "failed"]
    if failed:
        if st["attempts"] < st.get("max_attempts", node.get("max_attempts", 3)):
            return verdict("reject", "R1", failed)
        return verdict("replan", "R2", failed)

    host_results = []
    for check in node.get("checks", []):
        if check.get("type") == "host":
            result = (st.get("checks", {}).get(check["id"]) or {}).get("loop")
            if not result or result.get("attempt") != st["attempts"]:
                return verdict("unverified", "R3")
            host_results.append(result)
    reviews = [r for r in st.get("reviews", [])
               if r.get("status") == "passed" and r.get("target_submission") == submission]
    awaited = [n for n in plan.get("nodes", []) if n.get("kind") == "review" and n.get("target") == node_id
               and not any(r.get("node") == n["id"] for r in reviews)]
    if awaited:
        return dict(verdict("unverified", "R3"), message="Awaiting planned review: " +
                    ", ".join("%s (%s)" % (n.get("title") or n.get("goal"), n["id"]) for n in awaited))
    lane = node.get("effective_lane", node["lane"])
    if node["kind"] == "work" and lane >= 2:
        family = (st.get("assignment") or {}).get("family")
        if not any(family and r.get("family") and r["family"] != family for r in reviews):
            return verdict("unverified", "R3")

    observed_failures = [r for r in host_results
                         if r.get("grade") == 2 and r.get("result") == "failed"]
    if observed_failures or any(r.get("verdict") == "fail" for r in reviews):
        result = _approval_rule(state, node, [_ask(node, st, "hold")], "R4")
        if result:
            result.update(verdict="hold", failed=observed_failures)
            return result

    if node["kind"] == "work" and lane == 2 and (not st["trajectory_clean"] or rollbacks > 0):
        result = _approval_rule(state, node, [_ask(node, st, "trajectory", rollbacks=rollbacks)], "R5")
        if result:
            return result

    requests = [_ask(node, st, "human_check", check=c["id"], question=c.get("prompt"))
                for c in node.get("checks", []) if c.get("type") == "human"]
    if lane == 3:
        requests.append(_ask(node, st, "lane3", kind="authorization"))
    result = _approval_rule(state, node, requests, "R6")
    return result or verdict("pass", "R7")


def build_rejection(node, node_state, failed, tails):
    reasons = []
    for result in failed:
        kind = result.get("type")
        if kind == "scope":
            reason = "scope: %s outside owned paths" % ", ".join(result.get("violations") or [])
        elif kind == "cites":
            reason = "cites: %d invalid findings" % len(result.get("violations") or [])
        elif result.get("timed_out"):
            reason = "check %s timed out" % result["check"]
        elif result.get("exit_code") is not None:
            reason = "check %s exited %s" % (result["check"], result["exit_code"])
        else:
            reason = result.get("reason") or "check %s failed" % result.get("check", kind or "unknown")
        reasons.append(reason)
    # Retain the first failure's log and tail, or details for failures without logs.
    log = failed[0].get("log") if failed else None
    rejection = {"unit": node["id"], "attempt": node_state["attempts"],
            "max_attempts": node_state.get("max_attempts", node.get("max_attempts", 3)),
            "verdict": "red", "reason": "; ".join(reasons),
            "evidence": {"log": log, "tail": list(tails.get(log, []))},
            "scope": list(node.get("owns", []))}
    if not log:
        rejection["evidence"]["details"] = [
            ("%s: %s" % (v.get("file") or "finding %s" % v.get("finding", "?"),
                           v.get("reason") or "invalid citation") if isinstance(v, dict) else str(v))
            for result in failed for v in (result.get("violations") or [])]
    paths = [p for result in failed if result.get("type") == "scope"
             for p in result.get("violations") or []]
    if paths:
        rejection["restore_paths"] = paths
    return rejection


def render_rejection(rejection):
    evidence = rejection["evidence"]
    lines = [
        "UNIT      %s (attempt %s of %s)" % (rejection["unit"], rejection["attempt"], rejection["max_attempts"]),
        "VERDICT   %s" % rejection["verdict"],
        "REASON    %s" % rejection["reason"],
        "EVIDENCE  " + ("%s: %s" % (evidence["log"], " | ".join(evidence["tail"]))
                         if evidence.get("log") else
                         "; ".join(evidence.get("details") or []) or rejection["reason"] or "No log recorded"),
        "SCOPE     %s only" % ", ".join(rejection["scope"])]
    if rejection.get("restore_paths"):
        lines.append("RESTORE   Leader restores these paths before reassigning: " +
                     ", ".join(rejection["restore_paths"]))
    return "\n".join(lines)


def _git(cwd, *args):
    try:
        return subprocess.run(["git", "-C", str(cwd)] + list(args),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError as exc:
        raise core.GFError("io_error", "cannot run git: %s" % exc, core.EXIT_IO)


def _head(cwd):
    result = _git(cwd, "rev-parse", "HEAD")
    if result.returncode:
        raise core.GFError("git_error", result.stderr.decode("utf-8", "replace").strip(), core.EXIT_STATE)
    return result.stdout.decode("ascii").strip()


def _optional(module, function, default, *args):
    try:
        imported = importlib.import_module("graphflow." + module)
    except ModuleNotFoundError as exc:
        if exc.name != "graphflow." + module:
            raise
        return default
    return getattr(imported, function)(*args)


def _integration(plan):
    # Only commands frozen into the approved plan can execute.
    return list(plan.get("integration_checks") or []) + list(plan.get("promoted_checks") or [])


def _token(revision, st):
    return (revision, st["basis"], st["attempts"], statemod.submission_binding(st.get("submission")))


def _preconditions(plan, state, node_id):
    node = planmod.node_by_id(plan, node_id)
    st = state["nodes"][node_id]
    statemod.require_plan_approval(state)
    statemod.require_submission_binding(state, node_id, refresh=True)
    if not graph.needs_satisfied(plan, state, node_id):
        raise core.GFError("needs_unsatisfied", "node needs are not satisfied", core.EXIT_STATE)
    if node["kind"] != "decision" and not graph.has_current_submission(st):
        raise core.GFError("no_submission", "node has no current submission", core.EXIT_STATE)
    return node, st


def gate(run_dir, node_id, cwd, actor):
    root = store.project_of(run_dir)
    directory = pathlib.Path(cwd if cwd is not None else root).resolve()
    with store.transaction(run_dir) as tx:
        plan = tx.plan
        derived = statemod.derive(plan, tx.events)
        node, st = _preconditions(plan, derived, node_id)
        token = _token(tx.revision, st)
        started_seq = tx.events[-1]["seq"] if tx.events else 0
    submission = st.get("submission") or {}
    if submission.get("commit"):
        merged = _git(root, "merge-base", "--is-ancestor", submission["commit"], "HEAD")
        if merged.returncode:
            raise core.GFError("not_merged", "submission is not an ancestor of project HEAD; merge it into the project first", core.EXIT_STATE)
    if node["kind"] == "review":
        target = derived["nodes"][node["target"]].get("submission") or {}
        if submission.get("target_submission") != target.get("id"):
            raise core.GFError("review_outdated", "review is for an old submission", core.EXIT_STATE)
    tested_head = _head(directory)
    results, integration_results, skipped_checks = [], [], []
    checked_producers = set()
    if node["kind"] == "work":
        for check in node["checks"]:
            if check["type"] == "cmd":
                results.append(checks.run_cmd(run_dir, node_id, check, "gate", directory, actor))
        results.append(checks.run_scope(run_dir, node_id, "gate", directory, actor))
        lane = node.get("effective_lane", node["lane"])
        for check in _integration(plan):
            producers = check.get("requires_passed", [])
            if lane < 2 and node_id not in producers:
                continue
            other_producers = [nid for nid in producers if nid != node_id]
            pending = [nid for nid in other_producers if derived["nodes"][nid]["status"] != "passed"]
            if pending:
                skipped_checks.append({"check": check["id"], "title": check.get("title") or check["id"],
                                       "pending_nodes": pending})
                continue
            integration_results.append(checks.run_cmd(run_dir, "_run", check, "gate", directory, actor))
            checked_producers.update(other_producers)
    elif node["kind"] == "review":
        for check in node["checks"]:
            if check["type"] == "cmd":
                results.append(checks.run_cmd(run_dir, node_id, check, "gate", directory, actor))
        results.append(checks.run_cites(run_dir, node_id, "gate", directory, actor))
    rollbacks = (_optional("trace", "rollbacks", 0, root, run_dir, node["owns"])
                 if node["kind"] == "work" else 0)
    with store.transaction(run_dir) as tx:
        current = statemod.derive(tx.plan, tx.events)
        statemod.require_plan_approval(current)
        statemod.require_submission_binding(current, node_id, refresh=True)
        current_st = current["nodes"].get(node_id)
        if (current_st is None or _token(tx.revision, current_st) != token or
                (current_st["status"] == "passed" if node["kind"] == "decision"
                 else not graph.has_current_submission(current_st)) or
                any(e["seq"] > started_seq and e["type"] == "gate.verdict"
                    and e["data"].get("node") == node_id for e in tx.events) or
                any(current["nodes"][nid]["status"] != "passed" or
                    current["nodes"][nid]["basis"] != derived["nodes"][nid]["basis"]
                    for nid in checked_producers)):
            raise core.GFError("stale_result", "node, plan or verdict changed during gate", core.EXIT_STATE)
        outcome = evaluate(tx.plan, current, node_id, results, integration_results, rollbacks)
        ask_ids = []
        for request in outcome["asks"]:
            for prior in current["decisions"].values():
                if (prior.get("issuer") == "gate" and prior.get("status") != "superseded"
                        and all(prior.get(k) == request.get(k) for k in ("node", "purpose", "check"))):
                    tx.append("decision.superseded", {"id": prior["id"], "reason": "evidence_changed"},
                              {"role": "tool", "node": node_id, "session": None})
            event = tx.append("decision.ask", request, {"role": "tool", "node": node_id, "session": None})
            request["id"] = "d%d" % event["seq"]
            ask_ids.append(request["id"])
        rejection = None
        if outcome["verdict"] in ("reject", "replan"):
            tails = {}
            for result in outcome["failed"]:
                log = result.get("log")
                if log:
                    try:
                        tails[log] = (pathlib.Path(run_dir) / log).read_text(
                            encoding="utf-8", errors="replace").splitlines()[-5:]
                    except OSError as exc:
                        raise core.GFError("io_error", "cannot read evidence: %s" % exc, core.EXIT_IO)
            rejection = build_rejection(node, current_st, outcome["failed"], tails)
        data = {"node": node_id, "attempt": current_st["attempts"],
                "submission": submission.get("id"), "verdict": outcome["verdict"],
                "rule": outcome["rule"], "message": outcome.get("message"), "rejection": rejection, "tested_head": tested_head,
                "merged_head": _head(root) if submission.get("commit") else None}
        if skipped_checks:
            data["skipped_checks"] = skipped_checks
        if integration_results and all(r["result"] == "passed" for r in results):
            undeclared = {c["id"] for c in plan.get("integration_checks", []) if "requires_passed" not in c}
            notices = [{"code": "run_check_failed_after_node_checks_passed", "node": node_id, "check": r["check"],
                        "message": ("Run check %s failed after this node's command and scope checks passed. "
                                    "If it needs another node's outputs, declare requires_passed." % r["check"])}
                       for r in integration_results if r["result"] == "failed" and r["check"] in undeclared]
            if notices:
                data["notices"] = notices
        tx.append("gate.verdict", data, actor)
    return dict(data, asks=ask_ids)


def gate_final(run_dir, cwd, actor):
    root = store.project_of(run_dir)
    directory = pathlib.Path(cwd if cwd is not None else root).resolve()
    with store.transaction(run_dir) as tx:
        plan, revision = tx.plan, tx.revision
        derived = statemod.derive(plan, tx.events)
        statemod.require_plan_approval(derived)
    for nid, st in derived["nodes"].items():
        commit = (st.get("submission") or {}).get("commit")
        if commit and (not st.get("merged_head") or
                       _git(root, "merge-base", "--is-ancestor", commit, "HEAD").returncode):
            raise core.GFError("not_merged", "%s is not merged into project HEAD" % nid, core.EXIT_STATE)
    tested_head = _head(directory)
    results = [checks.run_cmd(run_dir, "_run", c, "gate", directory, actor)
               for c in _integration(plan or {})]
    failed = [r["check"] for r in results if r["result"] == "failed"]
    data = {"result": "failed" if failed else "passed", "failed_checks": failed,
            "tested_head": tested_head, "project_head": _head(root)}
    with store.transaction(run_dir) as tx:
        if tx.revision != revision:
            raise core.GFError("stale_result", "plan changed during final gate", core.EXIT_STATE)
        current = statemod.derive(tx.plan, tx.events)
        statemod.require_plan_approval(current)
        for nid, st in current["nodes"].items():
            commit = (st.get("submission") or {}).get("commit")
            if commit and (not st.get("merged_head") or
                           _git(root, "merge-base", "--is-ancestor", commit, "HEAD").returncode):
                raise core.GFError("not_merged", "%s is not merged into project HEAD" % nid, core.EXIT_STATE)
        pending = [nid for nid, st in current["nodes"].items() if st["status"] != "passed"]
        if pending and data["result"] == "passed":
            data.update(result="unverified", message="Awaiting planned work, reviews or decisions: " + ", ".join(pending))
        tx.append("gate.final", data, actor)
    return data


def reopen(run_dir, node_id, reason, actor):
    if not isinstance(reason, str) or not reason.strip():
        raise core.GFError("bad_reason", "reopen reason must be non-empty")
    with store.transaction(run_dir) as tx:
        planmod.node_by_id(tx.plan, node_id)
        derived = statemod.derive(tx.plan, tx.events)
        if derived["nodes"][node_id]["status"] != "passed":
            raise core.GFError("wrong_status", "only a passed node can be reopened", core.EXIT_STATE)
        invalidated = [n["id"] for n in tx.plan["nodes"]
                       if n["id"] == node_id or planmod.depends(tx.plan, n["id"], node_id)]
        tx.append("node.reopen", {"node": node_id, "reason": reason}, actor)
    return {"node": node_id, "invalidated": invalidated}
