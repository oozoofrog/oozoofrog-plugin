"""Human decisions and signatures (records.md sections 5 and 7)."""
import hmac
import secrets
import time

from . import core, plan, state, store

POLL_INTERVAL_S = 1.0


def ask(run_dir, kind, question, node, check, purpose, evidence, actor):
    if kind not in ("direction", "information", "review", "authorization"):
        raise core.GFError("bad_kind", "unknown decision kind: %s" % kind)
    purpose = "free" if purpose is None else purpose
    if purpose not in ("node", "human_check", "lane3", "trajectory", "hold", "free"):
        raise core.GFError("bad_purpose", "unknown decision purpose: %s" % purpose)
    if not isinstance(question, str) or not question.strip():
        raise core.GFError("bad_question", "question must be non-empty")
    with store.transaction(run_dir) as tx:
        derived = state.derive(tx.plan, tx.events)
        submission = None
        if node is not None:
            plan.node_by_id(tx.plan, node)
            sub = derived["nodes"][node]["submission"]
            submission = sub["id"] if sub is not None else None
        data = {"node": node, "submission": submission, "check": check,
                "purpose": purpose, "kind": kind, "question": question,
                "evidence": evidence if evidence is not None else
                {"command": None, "files": [], "checks": []}}
        event = tx.append("decision.ask", data, actor)
        data["id"] = "d%d" % event["seq"]
    return data


def answer(run_dir, decision_id, outcome, answer_text, source, actor):
    """Sign an answer; CLI and dashboard enforce caller roles and terminal checks."""
    ensure_key()
    with store.transaction(run_dir) as tx:
        derived = state.derive(tx.plan, tx.events)
        decision = derived["decisions"].get(decision_id)
        if decision is None:
            raise core.GFError("unknown_decision", "unknown decision: %s" % decision_id, core.EXIT_STATE)
        if decision["stale"]:
            raise core.GFError("stale_decision", "decision is stale: %s" % decision_id, core.EXIT_STATE)
        if decision["status"] == "answered":
            raise core.GFError("already_answered", "decision already answered: %s" % decision_id, core.EXIT_STATE)
        outcomes = (("approved", "rejected", "revision_requested")
                    if decision["kind"] in ("review", "authorization") else ("answered",))
        if outcome not in outcomes:
            raise core.GFError("bad_outcome", "invalid outcome: %s" % outcome)
        if source not in ("dashboard", "terminal"):
            raise core.GFError("bad_source", "invalid answer source: %s" % source)
        data = {"id": decision_id, "outcome": outcome, "answer": answer_text,
                "source": source, "sig": core.human_sig(derived["run"]["id"], decision_id, outcome, answer_text)}
        tx.append("decision.answer", data, actor)
    return data


def wait(run_dir, decision_id, timeout_s):
    deadline = time.monotonic() + timeout_s
    while True:
        with store.transaction(run_dir) as tx:
            decision = state.derive(tx.plan, tx.events)["decisions"].get(decision_id)
        if decision is None:
            raise core.GFError("unknown_decision", "unknown decision: %s" % decision_id, core.EXIT_STATE)
        if decision["status"] == "answered":
            return decision
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise core.GFError("wait_timeout", "timed out waiting for %s" % decision_id, core.EXIT_NEGATIVE)
        time.sleep(min(POLL_INTERVAL_S, remaining))


def open_decisions(state, node_id=None):
    return sorted((d for d in state["decisions"].values()
                   if d["status"] == "open" and not d["stale"]
                   and (node_id is None or d["node"] == node_id)), key=lambda d: d["seq"])


def verify(run_id, decision_id, answer_data):
    try:
        expected = core.human_sig(run_id, decision_id, answer_data["outcome"], answer_data["answer"])
        return expected is not None and hmac.compare_digest(
            expected.encode("utf-8"), answer_data["sig"].encode("utf-8"))
    except Exception:
        return False


def ensure_key():
    path = core.gf_home() / "human.key"
    with store.locked(path.parent / ".lock"):
        if not path.exists():
            # atomic_write uses mkstemp, whose mode is 0600 before installation.
            store.atomic_write(path, secrets.token_bytes(32))
    return path
