"""Readiness: which nodes can start now (records.md section 5, P12)."""
from .core import EXIT_STATE, GFError
from . import plan as planmod
from .state import require_plan_approval

STARTABLE = ("pending", "assigned", "rejected", "unverified", "held", "awaiting_approval")
WITH_SUBMISSION = ("submitted", "unverified", "held", "awaiting_approval")


def has_current_submission(node_state):
    return bool(node_state) and node_state.get("status") in WITH_SUBMISSION


def needs_satisfied(plan, state, node_id):
    node = planmod.node_by_id(plan, node_id)
    nodes = state.get("nodes", {})
    target = node.get("target") if node.get("kind") == "review" else None
    for need in node.get("needs") or []:
        producer = need.get("from")
        if producer == target:
            continue
        if nodes.get(producer, {}).get("status") != "passed":
            return False
    if target is not None:
        # A review happens before its target is accepted.
        if not has_current_submission(nodes.get(target)):
            return False
    return True


def _shared(node_state):
    assignment = (node_state or {}).get("assignment") or {}
    return assignment.get("isolation") in (None, "shared")


def shared_busy(plan, state, node_id):
    """True when another work node occupies the shared tree with uncommitted work."""
    node = planmod.node_by_id(plan, node_id)
    nodes = state.get("nodes", {})
    if node.get("kind") != "work" or not _shared(nodes.get(node_id)):
        return False
    for other in plan.get("nodes") or []:
        oid = other.get("id")
        if oid == node_id or other.get("kind") != "work":
            continue
        ost = nodes.get(oid) or {}
        if not _shared(ost):
            continue
        if ost.get("status") == "running":
            return True
        if has_current_submission(ost) and not (ost.get("submission") or {}).get("commit"):
            return True
    return False


def start_problem(plan, state, node_id):
    """None when `gf start` would accept the node, else the error code."""
    require_plan_approval(state)
    node = planmod.node_by_id(plan, node_id)
    st = state.get("nodes", {}).get(node_id) or {}
    if node.get("kind") == "decision":
        return "not_startable"
    status = st.get("status")
    if status == "replan":
        return "attempts_exhausted"
    # Status first: a node that is running, submitted or passed is simply not startable,
    # even on its last attempt. Exhaustion only applies to a node that could otherwise start.
    if status not in STARTABLE:
        return "not_startable"
    if st.get("attempts", 0) >= st.get("max_attempts", 3):
        return "attempts_exhausted"
    if not needs_satisfied(plan, state, node_id):
        return "needs_unsatisfied"
    if shared_busy(plan, state, node_id):
        return "shared_busy"
    return None


def check_start(plan, state, node_id):
    require_plan_approval(state)
    code = start_problem(plan, state, node_id)
    if code:
        raise GFError(code, "node %s cannot start: %s" % (node_id, code), EXIT_STATE)


def ready(plan, state):
    require_plan_approval(state)
    out = []
    nodes = state.get("nodes", {})
    for node in plan.get("nodes") or []:
        nid = node.get("id")
        if node.get("kind") == "decision":
            if nodes.get(nid, {}).get("status") != "passed" and needs_satisfied(plan, state, nid):
                out.append(nid)
        elif start_problem(plan, state, nid) is None:
            out.append(nid)
    return out


def available(plan, state):
    """Read-only status surfaces stay available while dispatch is blocked."""
    try:
        return ready(plan, state)
    except GFError as exc:
        if exc.code not in ("plan_not_approved", "human_key_mismatch", "plan_tampered"):
            raise
        return []
