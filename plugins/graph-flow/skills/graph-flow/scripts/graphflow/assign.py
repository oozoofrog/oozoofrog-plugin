"""Assignment and isolated session briefs (records.md sections 5 and 8)."""
import importlib
import pathlib
import shlex

from . import core, plan, state, store


def _optional_module(name):
    try:
        return importlib.import_module("graphflow." + name)
    except ModuleNotFoundError as exc:
        if exc.name != "graphflow." + name:
            raise
        return None


def assign(run_dir, node_id, executor, model, effort, provider, family, isolation, actor):
    with store.transaction(run_dir) as tx:
        node = plan.node_by_id(tx.plan, node_id)
        current = state.derive(tx.plan, tx.events)["nodes"][node_id]
        if node["kind"] == "decision" or current["status"] not in (
                "pending", "assigned", "rejected", "unverified", "held", "awaiting_approval"):
            raise core.GFError("wrong_status", "node cannot be assigned: " + node_id, core.EXIT_STATE)
        for name, value, choices in (
                ("executor", executor, ("inline", "subagent", "workflow", "t3", "background")),
                ("family", family, ("claude", "openai", "other")),
                ("isolation", isolation, ("shared", "worktree"))):
            if value not in choices:
                raise core.GFError("bad_" + name, "invalid %s: %s" % (name, value))
        data = {"node": node_id, "executor": executor, "model": model, "effort": effort,
                "provider": provider, "family": family, "isolation": isolation}
        tx.append("node.assign", data, actor)
    return data


def _rejection_text(rejection):
    gate = _optional_module("gate")
    if gate is not None and hasattr(gate, "render_rejection"):
        return gate.render_rejection(rejection)
    evidence = rejection.get("evidence") or {}
    return "\n".join([
        "UNIT      %s (attempt %s of %s)" % (rejection.get("unit"), rejection.get("attempt"), rejection.get("max_attempts")),
        "VERDICT   " + str(rejection.get("verdict", "red")),
        "REASON    " + str(rejection.get("reason", "")),
        "EVIDENCE  " + (("%s: %s" % (evidence["log"], " | ".join(evidence.get("tail") or [])))
                         if evidence.get("log") else
                         "; ".join(evidence.get("details") or []) or rejection.get("reason") or "No log recorded"),
        "SCOPE     " + ", ".join(rejection.get("scope") or []) + " only"])


def brief(run_dir, node_id):
    run_dir = pathlib.Path(run_dir).resolve()
    with store.transaction(run_dir) as tx:
        node = plan.node_by_id(tx.plan, node_id)
        if node["kind"] == "decision":
            raise core.GFError("wrong_status", "decision nodes have no brief", core.EXIT_STATE)
        current_plan = tx.plan
        derived = state.derive(current_plan, tx.events)
    current = derived["nodes"][node_id]
    reviewer = node["kind"] == "review"
    gf = pathlib.Path(__file__).resolve().parent.parent / "gf"
    invocation = "python3 %s --json " % shlex.quote(str(gf))
    lines = ["# %s: %s" % (node_id, node["goal"]), "",
             "Project directory: `%s`. Run every command from this directory." % store.project_of(run_dir).resolve(), "",
             "You are a sub-session. The leader owns the plan and the user conversation. "
             "Work and report in English. Do not start sub-sessions. Do not ask the user anything.", "",
             "## Environment", "", "```sh",
             "export GF_RUN=" + shlex.quote(str(run_dir)),
             "export GF_ROLE=" + ("reviewer" if reviewer else "worker"),
             "export GF_NODE=" + shlex.quote(node_id), invocation + "<command>", "```", "",
             "## Goal", "", node["goal"]]
    if reviewer:
        lines += ["Lens: " + node["lens"],
                  "Try to refute the target; report only defects that can be pointed to by file and line."]
    lines += ["", "## Inputs", ""]
    lines += ["- %s (producer: %s)" % (n["artifact"], n["from"]) for n in node["needs"]]
    if reviewer:
        target = derived["nodes"][node["target"]].get("submission") or {}
        lines += ["Target submission: " + (target.get("commit") or "uncommitted, in the shared tree"),
                  "Changed files: " + ", ".join(target.get("changed_files") or [])]
    lines += ["", "## Files you own", ""]
    if reviewer:
        lines += ["You change no files."]
    else:
        lines += ["- " + p for p in node["owns"]]
        lines += ["Nothing else may be edited."]
    if node["reads"]:
        lines += ["", "## Read", ""] + ["- " + p for p in node["reads"]]
    lines += ["", "## Checks", ""]
    for check in node["checks"]:
        lines += ["- %s (%s)" % (check["id"], check["type"])]
        if check["type"] == "cmd":
            lines += ["```sh", check["run"], "```"]
        elif check["type"] == "host":
            lines += ["Tool: %s. Record passed|failed and a note with observed evidence for: %s" %
                      (check["tool"], check["expect"])]
    lines += ["The scope is always compared at the gate."]
    learn = _optional_module("learn")
    if learn is not None:
        constraints = [c["text"] for c in learn.applying(store.project_of(run_dir), current_plan)
                       if not c.get("scope", {}).get("paths") or
                       plan.overlaps(c["scope"]["paths"], node["owns"])]
        if constraints:
            lines += ["", "## Constraints", ""] + ["- " + text for text in constraints]
    if (current.get("verdict") or {}).get("verdict") == "reject" and current["rejections"]:
        lines += ["", "## Previous rejection", "", "```text",
                  _rejection_text(current["rejections"][-1]), "```",
                  "Fix only what the rejection names; stay inside SCOPE."]
    lines += ["", "## Steps", "", "```sh", invocation + "start " + node_id]
    if reviewer:
        lines += ["```", "Read the target's changes.", "```sh",
                  invocation + "review submit " + node_id + " --verdict pass|fail --findings <json file>",
                  "```", "Each finding is {severity, file, line, text}, with optional free-form evidence. "
                  "The text is one plain sentence a person will read on the dashboard; "
                  "put paths, commands, ids and exit codes in the separate evidence field."]
    else:
        lines += ["# Optional, before any work:", invocation + "red " + node_id, "```",
                  "Do the work. Run each command check until it passes.", "```sh"]
        for check in node["checks"]:
            if check["type"] == "cmd":
                lines += [invocation + "check run %s %s" % (node_id, check["id"])]
            elif check["type"] == "host":
                lines += [invocation + "check record %s %s --result passed|failed --note ..." % (node_id, check["id"])]
        if (current.get("assignment") or {}).get("isolation") == "worktree":
            lines += ["```", "Commit on the worktree branch.", "```sh",
                      invocation + "submit " + node_id + " --commit <sha> --notes ..."]
        else:
            lines += [invocation + "submit " + node_id + " --notes ..."]
        lines += ["```"]
    lines += ["", "## If you are blocked", "", "```sh",
              invocation + "decide ask --node " + node_id + " --kind direction|information --question ...",
              invocation + "decide wait <id>", "```",
              "Never guess a decision that belongs to a person; never answer a decision.", "",
              "## Report", "",
              "Return at most 20 lines to the leader: commands run with exit codes, submission id, and anything uncertain.", ""]
    text = "\n".join(lines)
    try:
        store.atomic_write(run_dir / "brief" / (node_id + ".md"), text)
    except OSError as exc:
        raise core.GFError("io_error", str(exc), core.EXIT_IO)
    return text


def plan_brief(project_root, run_dir=None):
    project_root = (store.project_of(run_dir) if run_dir is not None else pathlib.Path(project_root)).resolve()
    lines = ["# Planning brief", "",
             "Project directory: `%s`. Run every command from this directory." % project_root, "",
             "## Principles", "",
             "- Every work node has a check that can fail.",
             "- Every edge names the artifact that crosses.",
             "- Split by blast radius with owns and lane.",
             "- Lane 2/3 work needs a review node from another family.",
             "- Parallel nodes must not own overlapping paths."]
    derived = None
    if run_dir is not None:
        with store.transaction(run_dir) as tx:
            derived = state.derive(tx.plan, tx.events)
            current_plan = tx.plan
    learn = _optional_module("learn")
    if learn is not None:
        constraints = (learn.all_constraints(project_root) if run_dir is None else
                       learn.applying(project_root, current_plan))
        lines += ["", "## Constraints", ""]
        lines += ["- " + c["text"] for c in constraints if c.get("status") != "retired"]
        lines += ["", "## Fixed checks", ""]
        for check in learn.fixed_checks(project_root):
            lines += ["- %s (%s)" % (check["id"], check["type"]), "```sh", check["run"], "```"]
    if derived is not None:
        lines += ["", "## Host capabilities", ""]
        lines += ["- " + capability for capability in derived["run"]["host"]]
    return "\n".join(lines) + "\n"
