"""Execute checks and record node work (records.md sections 4, 5; developer module contracts)."""
import json as _json
import os as _os
import pathlib as _pathlib
import signal as _signal
import stat as _stat
import subprocess as _subprocess
import time as _time

from . import core as _core, graph as _graph, plan as _plan, state as _state, store as _store

__all__ = ["run_cmd", "run_scope", "run_cites", "record_host", "red", "start",
           "submit", "review_submit"]


def _error(code, message, exit_code=_core.EXIT_STATE):
    return _core.GFError(code, message, exit_code)


def _cwd(run_dir, cwd):
    return _pathlib.Path(cwd if cwd is not None else _store.project_of(run_dir)).resolve()


def _git(cwd, *args):
    try:
        result = _subprocess.run(["git", "-C", str(cwd)] + list(args),
                                 stdout=_subprocess.PIPE, stderr=_subprocess.PIPE)
    except OSError as exc:
        raise _error("io_error", "cannot run git: %s" % exc, _core.EXIT_IO)
    if result.returncode:
        raise _error("git_error", result.stderr.decode("utf-8", "replace").strip())
    return result.stdout


def _paths(cwd, *args):
    return {_os.fsdecode(p) for p in _git(cwd, *args).split(b"\0")
            if p and not p.startswith(b".graph-flow/")}


def _file_state(cwd, path):
    file = cwd / path
    try:
        mode = file.lstat().st_mode
        if _stat.S_ISLNK(mode):
            return "link:" + _os.readlink(file)
        if _stat.S_ISDIR(mode):
            return "dir"
        if not _stat.S_ISREG(mode):
            return "unreadable"
        return "%o:%s" % (_stat.S_IMODE(mode),
                          _git(cwd, "hash-object", "--", path).decode("ascii").strip())
    except FileNotFoundError:
        return "deleted"
    except (OSError, ValueError, _core.GFError):
        return "unreadable"


def _dirty(cwd):
    paths = _paths(cwd, "diff", "--no-renames", "--name-only", "-z", "HEAD")
    paths.update(_paths(cwd, "diff", "--cached", "--no-renames", "--name-only", "-z", "HEAD"))
    paths.update(_paths(cwd, "ls-files", "--others", "--exclude-standard", "-z"))
    return {p: _file_state(cwd, p) for p in sorted(paths)}


def _changed(cwd, base, commit=None):
    args = ["diff", "--no-renames", "--name-only", "-z", base["rev"]]
    if commit is not None:
        return sorted(_paths(cwd, *(args + [commit])))
    paths = _paths(cwd, *args)
    paths.update(_paths(cwd, "ls-files", "--others", "--exclude-standard", "-z"))
    dirty = base.get("dirty") or {}
    paths.update(p for p in dirty if not p.startswith(".graph-flow/"))
    return sorted(p for p in paths if p not in dirty or _file_state(cwd, p) != dirty[p])


def _node(tx, node_id, kind=None, running=False):
    derived = _state.derive(tx.plan, tx.events)
    node = _plan.node_by_id(tx.plan, node_id)
    st = derived["nodes"][node_id]
    if kind is not None and node.get("kind") != kind:
        raise _error("wrong_kind", "%s must be a %s node" % (node_id, kind))
    if running and st["status"] != "running":
        raise _error("wrong_status", "%s must be running" % node_id)
    return node, st


def _token(tx, st, phase):
    token = (tx.revision, st.get("basis", 0), st.get("attempts", 0))
    if phase == "gate":
        token += ((st.get("submission") or {}).get("id"),)
    return token


def _capture(run_dir, node_id, phase, kind=None, check=None, submission=False):
    if phase not in ("loop", "gate"):
        raise _error("bad_phase", "phase must be loop or gate", _core.EXIT_USAGE)
    with _store.transaction(run_dir) as tx:
        if not submission:
            _state.require_plan_approval(_state.derive(tx.plan, tx.events))
        if node_id == "_run" and check is not None:
            _state.derive(tx.plan, tx.events)
            node, st = None, {"attempts": 0}
        else:
            node, st = _node(tx, node_id, kind, running=phase == "loop")
        if check is not None:
            _allowed_cmd(run_dir, tx, node, check)
        st = dict(st)
        st["submission_base"] = next((e["data"]["base"] for e in tx.events
            if e["seq"] > st.get("basis", 0) and e["type"] == "node.start"
            and e["data"].get("node") == node_id and e["data"].get("base")), st.get("base"))
        return node, st, _token(tx, st, phase)


def _recheck(tx, node_id, phase, token, kind=None, running=False):
    derived = _state.derive(tx.plan, tx.events)
    st = {"attempts": 0} if node_id == "_run" else derived["nodes"].get(node_id)
    if st is None or _token(tx, st, phase) != token:
        raise _error("stale_result", "node or plan changed while collecting evidence")
    if node_id != "_run":
        return _node(tx, node_id, kind, running=running or phase == "loop")
    return None, st


def _check(node, check_id, kind):
    check = next((c for c in node.get("checks", []) if c["id"] == check_id), None)
    if check is None:
        raise _error("unknown_check", "unknown check: %s" % check_id)
    if check.get("type") != kind:
        raise _error("wrong_check_type", "%s must be a %s check" % (check_id, kind))
    return check


def _allowed_cmd(run_dir, tx, node, check):
    allowed = list((tx.plan or {}).get("integration_checks") or [])
    allowed.extend((tx.plan or {}).get("promoted_checks") or [])
    if node is not None:
        allowed.extend(node.get("checks") or [])
    if check.get("type") == "cmd" and check in allowed:
        return
    if check.get("type") != "cmd" or check not in allowed:
        raise _error("unknown_check", "command must be a plan or fixed check")


def _result(node_id, check_id, kind, attempt, phase, cwd):
    return {"node": node_id, "check": check_id, "type": kind, "grade": 1,
            "result": "passed", "attempt": attempt, "phase": phase,
            "exit_code": None, "timed_out": False, "command": None,
            "cwd": str(cwd) if cwd is not None else None, "duration_ms": 0, "log": None}


def _execute(run_dir, node_id, check, attempt, phase, cwd):
    inputs = _plan.check_inputs(check)
    try:
        directory = (cwd / inputs["cwd"]).resolve()
        directory.relative_to(cwd)
    except (OSError, ValueError, RuntimeError):
        raise _error("bad_cwd", "check working directory must stay inside the tested tree",
                     _core.EXIT_USAGE)
    data = _result(node_id, check["id"], "cmd", attempt, phase, directory)
    data["command"] = inputs["run"]
    started = _time.monotonic()
    try:
        log = _store.evidence_path(run_dir, node_id, check["id"], attempt)
        with log.open("wb") as output:
            proc = _subprocess.Popen([inputs["shell"], "-c", inputs["run"]], cwd=str(directory),
                                     stdout=output, stderr=_subprocess.STDOUT,
                                     start_new_session=True)
            try:
                data["exit_code"] = proc.wait(timeout=inputs["timeout_s"])
            except _subprocess.TimeoutExpired:
                data["timed_out"] = True
                try:
                    _os.killpg(proc.pid, _signal.SIGKILL)
                except ProcessLookupError:
                    pass
                proc.wait()
        data["log"] = str(log.relative_to(_pathlib.Path(run_dir)))
    except OSError as exc:
        raise _error("io_error", "cannot execute check: %s" % exc, _core.EXIT_IO)
    data["duration_ms"] = int((_time.monotonic() - started) * 1000)
    data["result"] = "passed" if data["exit_code"] == 0 and not data["timed_out"] else "failed"
    return data


def run_cmd(run_dir, node_id, check, phase, cwd, actor):
    _, st, token = _capture(run_dir, node_id, phase, check=check)
    data = _execute(run_dir, node_id, check, st["attempts"], phase, _cwd(run_dir, cwd))
    with _store.transaction(run_dir) as tx:
        _recheck(tx, node_id, phase, token)
        if data["result"] == "passed":
            data["failed_before"] = failure_observed(tx.events, node_id, check["run"], run_dir)
        tx.append("check.result", data, actor)
    return data


def run_scope(run_dir, node_id, phase, cwd, actor):
    node, st, token = _capture(run_dir, node_id, phase, "work")
    directory = _cwd(run_dir, cwd)
    check_id = next((c["id"] for c in node["checks"] if c["type"] == "scope"), "scope")
    data = _result(node_id, check_id, "scope", st["attempts"], phase, directory)
    started = _time.monotonic()
    commit = (st.get("submission") or {}).get("commit") if phase == "gate" else None
    changed = (list((st.get("submission") or {}).get("changed_files") or [])
               if phase == "gate" else _changed(directory, st["base"], commit))
    data["violations"] = [p for p in changed if not any(
        p == owner.rstrip("/") or (owner.endswith("/") and p.startswith(owner))
        for owner in node["owns"])]
    data["result"] = "failed" if data["violations"] else "passed"
    data["duration_ms"] = int((_time.monotonic() - started) * 1000)
    with _store.transaction(run_dir) as tx:
        _recheck(tx, node_id, phase, token, "work")
        tx.append("check.result", data, actor)
    return data


def run_cites(run_dir, node_id, phase, cwd, actor):
    node, st, token = _capture(run_dir, node_id, phase, "review")
    if not _graph.has_current_submission(st):
        raise _error("wrong_status", "review must have a current submission")
    directory = _cwd(run_dir, cwd)
    check_id = next((c["id"] for c in node["checks"] if c["type"] == "cites"), "cites")
    data = _result(node_id, check_id, "cites", st["attempts"], phase, directory)
    violations = []
    started = _time.monotonic()
    for index, finding in enumerate(st["submission"].get("findings") or [], 1):
        finding = finding if isinstance(finding, dict) else {}
        file, line = finding.get("file"), finding.get("line")
        reason = None
        if not isinstance(file, str) or not file:
            reason = "missing file"
        elif type(line) is not int or line < 1:
            reason = "line must be an integer >= 1"
        else:
            try:
                path = _pathlib.Path(file)
                if path.is_absolute() or ".." in path.parts:
                    raise ValueError("file must be project-relative without '..'")
                resolved = (directory / path).resolve()
                relative = resolved.relative_to(directory)
                if any(part in (".git", ".graph-flow") for part in path.parts + relative.parts):
                    raise ValueError("file must be outside .git and .graph-flow")
                if not resolved.is_file():
                    raise ValueError("file must resolve to a regular file")
                count = len(resolved.read_bytes().splitlines())
            except (ValueError, RuntimeError) as exc:
                reason = str(exc)
            except OSError:
                reason = "file does not exist or cannot be read"
            else:
                if line > count:
                    reason = "line exceeds file line count"
        if reason:
            violations.append({"finding": index, "file": file, "line": line, "reason": reason})
    data["violations"] = violations
    data["result"] = "failed" if violations else "passed"
    data["duration_ms"] = int((_time.monotonic() - started) * 1000)
    with _store.transaction(run_dir) as tx:
        _recheck(tx, node_id, phase, token, "review")
        tx.append("check.result", data, actor)
    return data


def record_host(run_dir, node_id, check_id, result, note, actor):
    with _store.transaction(run_dir) as tx:
        _state.require_plan_approval(_state.derive(tx.plan, tx.events))
        node, st = _node(tx, node_id, running=True)
        _check(node, check_id, "host")
        if result not in ("passed", "failed"):
            raise _error("bad_result", "result must be passed or failed", _core.EXIT_USAGE)
        data = _result(node_id, check_id, "host", st["attempts"], "loop", None)
        data.update(grade=2, result=result, note=note)
        tx.append("check.result", data, actor)
    return data


def red(run_dir, node_id, check_id, cwd, actor):
    node, st, token = _capture(run_dir, node_id, "loop")
    selected = ([_check(node, check_id, "cmd")] if check_id is not None else
                [c for c in node["checks"] if c["type"] == "cmd"])
    results, notices = [], []
    for check in selected:
        outcome = _execute(run_dir, node_id, check, st["attempts"], "loop", _cwd(run_dir, cwd))
        data = {"node": node_id, "check": check["id"], "exit_code": outcome["exit_code"],
                "failed_first": outcome["result"] == "failed", "log": outcome["log"],
                "command": check["run"]}
        results.append(data)
        if not data["failed_first"]:
            notices.append({"code": "red_already_green", "node": node_id,
                            "message": "check %s already passes" % check["id"]})
    with _store.transaction(run_dir) as tx:
        _recheck(tx, node_id, "loop", token)
        for data in results:
            tx.append("check.red", data, actor)
    return {"results": results, "notices": notices}


def _start_problem(tx, node_id, actor):
    derived = _state.derive(tx.plan, tx.events)
    code = _graph.start_problem(tx.plan, derived, node_id)
    if code is not None:
        recovery = (" Re-post a revised plan with more max_attempts or a replacement node." if code == "attempts_exhausted" else "")
        return _error(code, "node %s cannot start: %s.%s" % (node_id, code, recovery))
    return None


def start(run_dir, node_id, cwd, actor):
    directory = _cwd(run_dir, cwd)
    base = {"rev": _git(directory, "rev-parse", "HEAD").decode("ascii").strip(),
            "dirty": _dirty(directory)}
    with _store.transaction(run_dir) as tx:
        problem = _start_problem(tx, node_id, actor)
        if problem is None:
            _, st = _node(tx, node_id)
            data = {"node": node_id, "attempt": st["attempts"] + 1,
                    "base": base, "cwd": str(directory)}
            tx.append("node.start", data, actor)
    if problem is not None:
        raise problem
    return data


def submit(run_dir, node_id, commit, branch, notes, low_confidence, cwd, actor):
    if notes is not None and not isinstance(notes, str):
        raise _error("bad_notes", "notes must be a string or null", _core.EXIT_USAGE)
    if not isinstance(low_confidence, list) or any(not isinstance(v, str) for v in low_confidence):
        raise _error("bad_low_confidence", "low_confidence must be a list of strings", _core.EXIT_USAGE)
    _, st, token = _capture(run_dir, node_id, "loop", "work", submission=True)
    directory = _cwd(run_dir, cwd)
    if commit is not None:
        try:
            commit = _git(directory, "rev-parse", "--verify", "--end-of-options",
                          "%s^{commit}" % commit).decode("ascii").strip()
        except _core.GFError as exc:
            if exc.code != "git_error":
                raise
            raise _error("bad_commit", "commit does not resolve: %s" % commit, _core.EXIT_USAGE)
        try:
            _git(directory, "merge-base", "--is-ancestor", st["base"]["rev"], commit)
        except _core.GFError as exc:
            if exc.code != "git_error":
                raise
            raise _error("bad_commit", "commit must descend from base.rev", _core.EXIT_USAGE)
    data = {"node": node_id, "attempt": st["attempts"], "commit": commit,
            "branch": branch, "changed_files": _changed(directory, st["submission_base"], commit),
            "notes": notes, "low_confidence": low_confidence}
    with _store.transaction(run_dir) as tx:
        _recheck(tx, node_id, "loop", token, "work")
        event = tx.append("node.submit", data, actor)
    return dict(data, id=event["seq"])


def review_submit(run_dir, node_id, verdict, findings, actor):
    with _store.transaction(run_dir) as tx:
        node, st = _node(tx, node_id, "review", running=True)
        if verdict not in ("pass", "fail"):
            raise _error("bad_verdict", "verdict must be pass or fail", _core.EXIT_USAGE)
        if not isinstance(findings, list):
            raise _error("bad_findings", "findings must be a list", _core.EXIT_USAGE)
        if any(not isinstance(finding, dict) for finding in findings):
            raise _error("bad_findings", "each finding must be an object", _core.EXIT_USAGE)
        _, target = _node(tx, node["target"], "work")
        if not _graph.has_current_submission(target):
            raise _error("wrong_status", "target must have a current submission")
        data = {"node": node_id, "attempt": st["attempts"], "target": node["target"],
                "target_submission": target["submission"]["id"], "verdict": verdict,
                "findings": findings}
        event = tx.append("review.submit", data, actor)
    return dict(data, id=event["seq"])


def recorded_command(event, run_dir):
    """Older red records carry a revision/check id instead of the command."""
    data = event.get("data", {})
    if data.get("command") is not None:
        return data["command"]
    if event.get("type") != "check.red":
        return None
    try:
        current = _store._load_plan(run_dir, event["plan_revision"])
        node = _plan.node_by_id(current, data["node"])
        return next(c["run"] for c in node["checks"] if c["id"] == data["check"] and c["type"] == "cmd")
    except (_core.GFError, KeyError, StopIteration):
        return None


def failure_observed(events, node, command, run_dir):
    return any(e.get("data", {}).get("node") == node
        and (e["type"] == "check.red" and e["data"].get("failed_first") is True
             or e["type"] == "check.result" and e["data"].get("result") == "failed")
        and recorded_command(e, run_dir) == command for e in events)
