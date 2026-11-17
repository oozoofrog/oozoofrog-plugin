"""Evidence-ordered gates and lane rules (records.md section 6, P7-P10)."""
import copy
import importlib
import pathlib
import subprocess

from . import checks, core, graph, plan as planmod, state as statemod, store

__all__ = ["evaluate", "build_rejection", "render_rejection", "gate", "gate_final", "reopen"]


def _decisions(state, node_id, submission, check, purpose, kind, request=None):
    return [d for d in state.get("decisions", {}).values()
            if not d.get("stale") and d.get("node") == node_id
            and d.get("submission") == submission and d.get("check") == check
            and d.get("purpose") == purpose
            and (kind is None or d.get("kind") == kind)
            and (request is None or all(d.get(k) == request.get(k)
                 for k in ("question", "evidence", "kind")))]


def _answered(decisions, outcomes):
    return any(d.get("verified") and d.get("status") == "answered"
               and d.get("outcome") in outcomes for d in decisions)


def _ask(node, node_state, purpose, check=None, kind="review", question=None):
    submission = node_state.get("submission") or {}
    human = next((c for c in node.get("checks", []) if c.get("id") == check), {})
    context = human.get("context", {}) if purpose == "human_check" else node.get("context", {})
    prompt = human.get("prompt") or human.get("title") or node.get("goal", "")
    question = (node.get("question") if purpose == "node" else prompt if purpose == "human_check"
                else question or "Approve %s: %s?" % (purpose, node.get("goal", node["id"])))
    return {"node": node["id"], "submission": submission.get("id"),
            "check": check, "purpose": purpose, "kind": kind,
            "question": question,
            "evidence": {
                "command": [c["run"] for c in node.get("checks", []) if c.get("type") == "cmd"],
                "files": list(submission.get("changed_files") or []),
                "checks": {cid: {"loop": copy.deepcopy(slots["loop"])}
                           for cid, slots in node_state.get("checks", {}).items() if slots.get("loop")},
                "context": copy.deepcopy(context),
                "contract": planmod.node_contract(node)}}


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
            return {"verdict": "hold", "rule": "R4", "failed": [], "asks": []}
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
        if _answered(decisions, ("answered", "approved")):
            return verdict("pass", "R7")
        if _answered(decisions, ("rejected", "revision_requested")):
            return verdict("hold", "R4")
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
    lane = node.get("effective_lane", node["lane"])
    if node["kind"] == "work" and lane >= 2:
        family = (st.get("assignment") or {}).get("family")
        if not any(family and r.get("family") and r["family"] != family for r in reviews):
            return verdict("unverified", "R3")

    observed_failures = [r for r in host_results
                         if r.get("grade") == 2 and r.get("result") == "failed"]
    if observed_failures or any(r.get("verdict") == "fail" for r in reviews):
        holds = _decisions(state, node_id, submission, None, "hold", "review")
        if not _answered(holds, ("approved",)):
            return verdict("hold", "R4", observed_failures)

    if node["kind"] == "work" and lane == 2 and (not st["trajectory_clean"] or rollbacks > 0):
        result = _approval_rule(state, node, [_ask(node, st, "trajectory")], "R5")
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


def _integration(plan, root, derived):
    # Only commands frozen into the approved plan can execute.
    return list(plan.get("integration_checks") or []) + list(plan.get("promoted_checks") or [])


def _token(revision, st):
    return (revision, st["basis"], st["attempts"], statemod.submission_binding(st.get("submission")))


def _preconditions(plan, state, node_id):
    node = planmod.node_by_id(plan, node_id)
    st = state["nodes"][node_id]
    statemod.require_plan_approval(state)
    statemod.require_submission_binding(state, node_id)
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
    results, integration_results = [], []
    if node["kind"] == "work":
        for check in node["checks"]:
            if check["type"] == "cmd":
                results.append(checks.run_cmd(run_dir, node_id, check, "gate", directory, actor))
        results.append(checks.run_scope(run_dir, node_id, "gate", directory, actor))
        if node.get("effective_lane", node["lane"]) >= 2:
            integration_results = [checks.run_cmd(run_dir, "_run", c, "gate", directory, actor)
                                   for c in _integration(plan, root, derived)]
    elif node["kind"] == "review":
        results.append(checks.run_cites(run_dir, node_id, "gate", directory, actor))
    rollbacks = (_optional("trace", "rollbacks", 0, root, run_dir, node["owns"])
                 if node["kind"] == "work" else 0)
    with store.transaction(run_dir) as tx:
        current = statemod.derive(tx.plan, tx.events)
        statemod.require_plan_approval(current)
        statemod.require_submission_binding(current, node_id)
        current_st = current["nodes"].get(node_id)
        if (current_st is None or _token(tx.revision, current_st) != token or
                (current_st["status"] == "passed" if node["kind"] == "decision"
                 else not graph.has_current_submission(current_st)) or
                any(e["seq"] > started_seq and e["type"] == "gate.verdict"
                    and e["data"].get("node") == node_id for e in tx.events)):
            raise core.GFError("stale_result", "node, plan or verdict changed during gate", core.EXIT_STATE)
        outcome = evaluate(tx.plan, current, node_id, results, integration_results, rollbacks)
        ask_ids = []
        for request in outcome["asks"]:
            event = tx.append("decision.ask", request, actor)
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
                "rule": outcome["rule"], "rejection": rejection, "tested_head": tested_head,
                "merged_head": _head(root) if submission.get("commit") else None}
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
               for c in _integration(plan or {}, root, derived)]
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
