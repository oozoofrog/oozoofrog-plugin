"""Integrate committed submissions into the project branch (records.md section 6)."""
import os
import subprocess

from . import core, graph, plan, state, store


def _git(project, *args, check=True):
    try:
        result = subprocess.run(["git", "-C", str(project)] + list(args),
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError as exc:
        raise core.GFError("io_error", "cannot run git: %s" % exc, core.EXIT_IO)
    if check and result.returncode:
        raise core.GFError("git_error", result.stderr.decode("utf-8", "replace").strip(),
                           core.EXIT_STATE)
    return result


def _token(st):
    return (st["basis"], st["attempts"], state.submission_binding(st["submission"]))


def _identity(project):
    options = []
    for key, fallback in (("user.name", "gf"), ("user.email", "gf@localhost")):
        result = _git(project, "config", "--get", key, check=False)
        if result.returncode not in (0, 1):
            raise core.GFError("git_error", "cannot read git identity: %s" % key,
                               core.EXIT_STATE)
        if not result.stdout.strip():
            options.extend(["-c", "%s=%s" % (key, fallback)])
    return options


def _before_commit(run_dir):
    """Hook for exercising state changes after git work and before the transaction."""


def merge(run_dir, node_ids, actor):
    node_ids = list(node_ids)
    with store.transaction(run_dir) as tx:
        derived = state.derive(tx.plan, tx.events)
        state.require_plan_approval(derived)
        nodes = {nid: plan.node_by_id(tx.plan, nid) for nid in node_ids}
        captured = {}
        for nid in node_ids:
            state.require_submission_binding(derived, nid)
            st = derived["nodes"][nid]
            if not graph.has_current_submission(st) or not (st["submission"] or {}).get("commit"):
                raise core.GFError("no_commit", "%s has no current committed submission" % nid,
                                   core.EXIT_STATE)
            captured[nid] = st
        revision = tx.revision

    project = store.project_of(run_dir)
    if _git(project, "rev-parse", "-q", "--verify", "MERGE_HEAD", check=False).returncode == 0:
        raise core.GFError("merge_in_progress", "a merge is already in progress", core.EXIT_STATE)
    # Check index and worktree separately: staged changes may be restored in the worktree.
    if (_git(project, "diff", "--name-only", "-z", "HEAD").stdout or
            _git(project, "diff", "--cached", "--name-only", "-z", "HEAD").stdout):
        raise core.GFError("dirty_tree", "project has modified tracked files", core.EXIT_STATE)

    data = {"merged": [], "conflicted": []}
    tested_heads = {}
    for nid in node_ids:
        commit = captured[nid]["submission"]["commit"]
        ancestor = _git(project, "merge-base", "--is-ancestor", commit, "HEAD", check=False)
        if ancestor.returncode not in (0, 1):
            raise core.GFError("git_error", ancestor.stderr.decode("utf-8", "replace").strip(),
                               core.EXIT_STATE)
        if ancestor.returncode == 1:
            result = _git(project, *(_identity(project) + ["merge", "--no-ff", "--no-edit",
                          "-m", "gf: merge %s" % nid, commit]), check=False)
            if result.returncode:
                files = [os.fsdecode(p) for p in _git(
                    project, "diff", "--name-only", "--diff-filter=U", "-z").stdout.split(b"\0") if p]
                in_progress = _git(project, "rev-parse", "-q", "--verify", "MERGE_HEAD",
                                   check=False).returncode == 0
                if in_progress:
                    _git(project, "merge", "--abort")
                conflict = {"node": nid, "commit": commit, "files": files}
                if not files:
                    error = (result.stderr or result.stdout).decode("utf-8", "replace").strip().splitlines()
                    conflict["reason"] = error[0] if error else "git merge exited %d" % result.returncode
                data["conflicted"].append(conflict)
                tested_heads[nid] = _git(project, "rev-parse", "HEAD").stdout.decode("ascii").strip()
                continue
        head = _git(project, "rev-parse", "HEAD").stdout.decode("ascii").strip()
        data["merged"].append({"node": nid, "commit": commit, "head": head})

    _before_commit(run_dir)
    with store.transaction(run_dir) as tx:
        current_state = state.derive(tx.plan, tx.events)
        state.require_plan_approval(current_state)
        for nid in node_ids:
            state.require_submission_binding(current_state, nid)
        current = current_state["nodes"]
        for nid in node_ids:
            if (tx.revision != revision or nid not in current or
                    _token(current[nid]) != _token(captured[nid])):
                raise core.GFError("stale_result", "node or plan changed during merge; "
                                   "git merges already made remain in the project branch",
                                   core.EXIT_STATE)
        tx.append("merge.result", data, actor)
        for conflict in data["conflicted"]:
            nid, files = conflict["node"], conflict["files"]
            st = current[nid]
            verdict = "replan" if st["attempts"] == st["max_attempts"] else "reject"
            rejection = {"unit": nid, "attempt": st["attempts"],
                         "max_attempts": st["max_attempts"], "verdict": "red",
                         "reason": ("merge conflict in %s" % ", ".join(files) if files else
                                    "merge failed: %s" % conflict["reason"]),
                         "evidence": {"log": None, "tail": files}, "scope": nodes[nid]["owns"]}
            tx.append("gate.verdict", {"node": nid, "attempt": st["attempts"],
                      "submission": st["submission"]["id"], "verdict": verdict, "rule": "M1",
                      "rejection": rejection, "tested_head": tested_heads[nid]}, actor)
    return data
