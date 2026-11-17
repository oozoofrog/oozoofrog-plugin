"""Human decisions and signatures (records.md sections 5 and 7)."""
import hmac
import math
import secrets
import time

from . import core, plan, state, store

POLL_INTERVAL_S = 1.0


def ask(run_dir, kind, question, node, check, purpose, evidence, actor):
    if kind not in ("direction", "information", "review", "authorization"):
        raise core.GFError("bad_kind", "unknown decision kind: %s" % kind)
    purpose = "free" if purpose is None else purpose
    if purpose != "free":
        raise core.GFError("bad_purpose", "decide ask creates only free questions; gate owns purpose: %s" % purpose)
    if kind not in ("direction", "information"):
        raise core.GFError("bad_kind", "free questions must be direction or information; approval questions belong to the gate")
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


def answer(run_dir, decision_id, outcome, answer_text, source, actor, displayed=None):
    """Sign a human answer; the CLI also enforces terminal checks."""
    if actor.get("role") != "human":
        raise core.GFError("forbidden", "only a human can answer decisions", core.EXIT_FORBIDDEN)
    ensure_key(actor)
    with store.transaction(run_dir) as tx:
        derived = state.derive(tx.plan, tx.events)
        decision = derived["decisions"].get(decision_id)
        if decision is None:
            raise core.GFError("unknown_decision", "unknown decision: %s" % decision_id, core.EXIT_STATE)
        if displayed is not None and displayed != state.decision_identity(decision):
            raise core.GFError("stale_decision", "The displayed question or evidence changed. Read the current decision again.", core.EXIT_STATE)
        if decision.get("legacy_binding"):
            raise core.GFError("legacy_decision", "This question predates signed bindings. Ask the leader to request a fresh question.", core.EXIT_STATE)
        if decision.get("recorded_location") != store.location(run_dir):
            raise core.GFError("project_moved", "Moving or renaming a project directory or run invalidates approvals. Re-post the plan and approve once more.", core.EXIT_STATE)
        if decision.get("binding_changed"):
            raise core.GFError("approval_changed", "Submission or evidence changed; submit again before approval.", core.EXIT_STATE)
        if decision["stale"]:
            raise core.GFError("stale_decision", "decision is stale: %s" % decision_id, core.EXIT_STATE)
        if decision["status"] == "answered":
            raise core.GFError("already_answered", "decision already answered: %s" % decision_id, core.EXIT_STATE)
        outcomes = (("approved", "rejected", "revision_requested")
                    if decision["kind"] in ("review", "authorization") else ("answered",))
        if outcome not in outcomes:
            raise core.GFError("bad_outcome", "invalid outcome: %s" % outcome)
        if (decision.get("purpose") == "plan_approval" and outcome != "approved"
                and (not isinstance(answer_text, str) or not answer_text.strip())):
            raise core.GFError("answer_required", "describe what to change before sending the plan back")
        if source not in ("dashboard", "terminal"):
            raise core.GFError("bad_source", "invalid answer source: %s" % source)
        if derived["run"].get("key_mismatch"):
            raise core.GFError("human_key_mismatch", state.key_recovery(derived["run"]), core.EXIT_STATE)
        if not derived["run"].get("run_nonce"):
            tx.append("run.nonce", {"run_nonce": secrets.token_hex(32)}, actor)
        if not derived["run"].get("human_key_sha256"):
            tx.append("human.key", {"human_key_sha256": core.key_fingerprint()}, actor)
        decision = state.derive(tx.plan, tx.events)["decisions"][decision_id]
        data = {"id": decision_id, "outcome": outcome, "answer": answer_text,
                "source": source, "sig": core.human_sig(derived["run"]["id"], decision_id, outcome, answer_text, decision)}
        tx.append("decision.answer", data, actor)
    return data


def wait(run_dir, decision_id, timeout_s):
    if type(timeout_s) not in (int, float) or not math.isfinite(timeout_s) or timeout_s < 0:
        raise core.GFError("bad_timeout", "timeout must be a finite non-negative number")
    deadline = time.monotonic() + timeout_s
    while True:
        with store.transaction(run_dir) as tx:
            decision = state.derive(tx.plan, tx.events)["decisions"].get(decision_id)
        if decision is None:
            raise core.GFError("unknown_decision", "unknown decision: %s" % decision_id, core.EXIT_STATE)
        if decision["status"] in ("answered", "superseded"):
            return decision
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise core.GFError("wait_timeout", "timed out waiting for %s" % decision_id, core.EXIT_NEGATIVE)
        time.sleep(min(POLL_INTERVAL_S, remaining))


def open_decisions(state, node_id=None):
    return sorted((d for d in state["decisions"].values()
                   if d["status"] == "open" and not d["stale"]
                   and (node_id is None or d["node"] == node_id)), key=lambda d: d["seq"])


def verify(run_id, decision_id, answer_data, decision=None):
    try:
        modern = answer_data["sig"].startswith("v3:")
        if not modern or not decision or not decision.get("run_nonce"):
            return False
        expected = core.human_sig(run_id, decision_id, answer_data["outcome"], answer_data["answer"], decision if modern else None)
        return expected is not None and hmac.compare_digest(
            expected.encode("utf-8"), answer_data["sig"].encode("utf-8"))
    except Exception:
        return False


def recovery_identity(derived):
    run = derived["run"]
    return {"nonce": run.get("run_nonce"),
            "pinned_key": run.get("human_key_sha256"), "current_key": core.key_fingerprint(),
            "location": run.get("location"), "plan": run.get("plan_identity"),
            "repin_seq": run.get("repin_seq", 0)}


def repin(run_dir, actor, displayed=None):
    """Called by the guarded human terminal or confirmed dashboard recovery."""
    if actor.get("role") != "human":
        raise core.GFError("forbidden", "only a human can re-pin a key", core.EXIT_FORBIDDEN)
    with store.transaction(run_dir) as tx:
        derived = state.derive(tx.plan, tx.events)
        if displayed is not None and displayed != recovery_identity(derived):
            raise core.GFError("stale_decision", "Read the current recovery request again.", core.EXIT_STATE)
        ensure_key(actor, fresh=True)
        data = {"run_nonce": secrets.token_hex(32), "human_key_sha256": core.key_fingerprint(),
                "location": store.location(run_dir)}
        data["sig"] = core.human_sig(tx.run_id, "human.repin", "repinned", "", data)
        tx.append("human.repin", data, actor)
        for decision in derived["decisions"].values():
            if decision["status"] == "open" or decision.get("purpose") == "plan_approval":
                tx.append("decision.superseded", {"id": decision["id"], "reason": "key_repinned"}, actor)
        identity = derived["run"].get("plan_identity")
        if tx.plan and identity:
            ask = {"node": None, "submission": None, "check": None, "purpose": "plan_approval",
                   "kind": "authorization", "question": plan.approval_question(tx.plan), "issuer": "plan", "reason": "key_repinned",
                   "plan_identity": identity, "evidence": {"command": None, "files": [], "checks": []}}
            event = tx.append("decision.ask", ask, {"role": "tool", "node": None, "session": None})
            ask["id"] = "d%d" % event["seq"]
    return {"repinned": True, "message": "Key re-pinned. Approve the plan again before continuing."}


def ensure_key(actor=None, fresh=False):
    actor = actor or core.actor_from_env()
    if actor.get("role") != "human":
        raise core.GFError("forbidden", "only a human entry point creates the signing key", core.EXIT_FORBIDDEN)
    path = core.gf_home() / "human.key"
    with store.locked(path.parent / ".lock"):
        if fresh or not path.exists():
            # atomic_write uses mkstemp, whose mode is 0600 before installation.
            store.atomic_write(path, secrets.token_bytes(32))
    return path
