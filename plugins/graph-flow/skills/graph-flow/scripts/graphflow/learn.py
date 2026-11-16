"""Project learning constraints and recoverable fixed checks (records.md section 8)."""
import json
import pathlib
import re

from . import core, plan as planmod, state, store

__all__ = ["add", "all_constraints", "applying", "promote", "retire", "fixed_checks"]


def _nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def _safe_path(value):
    if not _nonempty(value):
        return False
    path = pathlib.PurePosixPath(value)
    return (not path.is_absolute() and ".." not in path.parts
            and not (path.parts and path.parts[0] in (".git", ".graph-flow")))


def _read(path, code):
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except UnicodeError as exc:
        raise core.GFError(code, "invalid UTF-8 in %s: %s" % (path, exc), core.EXIT_IO)
    except OSError as exc:
        raise core.GFError("io_error", "cannot read %s: %s" % (path, exc), core.EXIT_IO)


def _read_constraints(meta):
    text = _read(meta / "constraints.jsonl", "constraints_corrupt")
    constraints = []
    seen = set()
    for number, line in enumerate(text.splitlines() if text is not None else [], 1):
        try:
            item = json.loads(line)
            if (not isinstance(item, dict) or not _nonempty(item.get("id"))
                    or item["id"] in seen
                    or item.get("status") not in ("active", "promoted", "retired")
                    or not all(_nonempty(item.get(k)) for k in ("text", "review_when", "created"))
                    or not isinstance(item.get("scope"), dict)
                    or not isinstance(item.get("derived_from"), dict)):
                raise ValueError("invalid constraint object")
            for key in ("paths", "tags"):
                values = item["scope"].get(key, [])
                if not isinstance(values, list) or not all(isinstance(v, str) for v in values):
                    raise ValueError("invalid scope " + key)
            if not all(_safe_path(p) for p in item["scope"].get("paths", [])):
                raise ValueError("unsafe scope path")
            seen.add(item["id"])
            constraints.append(item)
        except (ValueError, TypeError) as exc:
            raise core.GFError("constraints_corrupt", "invalid constraint line %d: %s" %
                               (number, exc), core.EXIT_IO)
    return constraints


def _read_checks(meta):
    text = _read(meta / "checks.json", "checks_corrupt")
    if text is None:
        return {"schema_version": 1, "checks": []}
    try:
        document = json.loads(text)
        if (not isinstance(document, dict) or type(document.get("schema_version")) is not int
                or document["schema_version"] != 1 or not isinstance(document.get("checks"), list)):
            raise ValueError("expected schema_version 1 and a checks list")
        seen = set()
        for check in document["checks"]:
            if (not isinstance(check, dict) or not _nonempty(check.get("id"))
                    or check["id"] in seen or check.get("type") != "cmd"
                    or not _nonempty(check.get("run"))
                    or ("from_constraint" in check and not isinstance(check["from_constraint"], str))):
                raise ValueError("invalid cmd check")
            seen.add(check["id"])
        return document
    except (ValueError, TypeError) as exc:
        raise core.GFError("checks_corrupt", "invalid checks.json: %s" % exc, core.EXIT_IO)


def _write_checks(meta, document):
    _write(meta / "checks.json", json.dumps(document, ensure_ascii=False, indent=2) + "\n")


def _write_constraints(meta, constraints):
    _write(meta / "constraints.jsonl", "".join(
        json.dumps(c, ensure_ascii=False) + "\n" for c in constraints))


def _write(path, text):
    try:
        store.atomic_write(path, text)
    except OSError as exc:
        raise core.GFError("io_error", "cannot write %s: %s" % (path, exc), core.EXIT_IO)


def _heal(constraints, checks):
    fixed = {(c["id"], c.get("from_constraint")) for c in checks}
    for constraint in constraints:
        cid = constraint["id"]
        if constraint["status"] == "promoted" and ("fx_" + cid, cid) not in fixed:
            constraint["status"] = "active"
    return constraints


def all_constraints(project_root):
    meta = pathlib.Path(project_root) / ".graph-flow"
    with store.locked(meta / ".lock"):
        return _heal(_read_constraints(meta), _read_checks(meta)["checks"])


def applying(project_root, plan):
    normalized, _ = planmod.normalize(plan)
    owns = [p for node in (normalized or {}).get("nodes", []) for p in node["owns"]]
    tags = (normalized or {}).get("tags", [])
    result = []
    for constraint in all_constraints(project_root):
        paths = constraint["scope"].get("paths", [])
        scope_tags = constraint["scope"].get("tags", [])
        if constraint["status"] != "retired" and (
                (not paths and not scope_tags) or planmod.overlaps(paths, owns)
                or any(tag in tags for tag in scope_tags)):
            result.append(constraint)
    return result


def add(project_root, run_dir, node_id, text, review_when, paths, tags, actor):
    if run_dir is None:
        raise core.GFError("no_run", "adding a constraint requires a run", core.EXIT_STATE)
    for value, code in ((text, "bad_text"), (review_when, "bad_review_when")):
        if not _nonempty(value):
            raise core.GFError(code, code[4:] + " must be non-empty")
    paths = [] if paths is None else paths
    tags = [] if tags is None else tags
    if not isinstance(paths, list) or not all(_safe_path(p) for p in paths):
        raise core.GFError("bad_path", "paths must be safe project-relative paths")
    if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
        raise core.GFError("bad_tags", "tags must be a list of strings")
    meta = pathlib.Path(project_root) / ".graph-flow"
    with store.transaction(run_dir) as tx:
        derived = state.derive(tx.plan, tx.events)
        node = derived["nodes"].get(node_id)
        if node is None or node["status"] != "passed":
            raise core.GFError("not_accepted", "constraint source must be a passed node", core.EXIT_STATE)
        evidence = next((slot["gate"].get("log") for slot in node["checks"].values()
                         if slot.get("gate") and slot["gate"].get("result") == "passed"
                         and slot["gate"].get("attempt") == node["attempts"]), None)
        with store.locked(meta / ".lock"):
            constraints = _read_constraints(meta)
            _read_checks(meta)
            suffixes = [int(m.group(1)) for c in constraints
                        for m in [re.fullmatch(r"c([0-9]+)", c["id"])] if m]
            constraint = {"id": "c%d" % (max(suffixes, default=0) + 1), "text": text,
                          "scope": {"paths": list(paths), "tags": list(tags)},
                          "derived_from": {"run": derived["run"]["id"], "node": node_id,
                                           "attempt": node["attempts"], "evidence": evidence},
                          "review_when": review_when, "status": "active", "created": core.now()}
            _write_constraints(meta, constraints + [constraint])
        tx.append("constraint.add", {"id": constraint["id"]}, actor)
    return constraint


def _find(constraints, constraint_id):
    for constraint in constraints:
        if constraint["id"] == constraint_id:
            return constraint
    raise core.GFError("unknown_constraint", "unknown constraint: %s" % constraint_id, core.EXIT_STATE)


def _event(run_dir, kind, constraint_id, actor):
    if run_dir is not None:
        with store.transaction(run_dir) as tx:
            tx.append(kind, {"id": constraint_id}, actor)


def promote(project_root, constraint_id, command, actor, run_dir=None):
    if not _nonempty(command):
        raise core.GFError("bad_command", "command must be non-empty")
    meta = pathlib.Path(project_root) / ".graph-flow"
    with store.locked(meta / ".lock"):
        constraints, document = _read_constraints(meta), _read_checks(meta)
        constraint = _find(_heal(constraints, document["checks"]), constraint_id)
        if constraint["status"] != "active":
            raise core.GFError("wrong_status", "only active constraints can be promoted", core.EXIT_STATE)
        check = {"id": "fx_" + constraint_id, "type": "cmd", "run": command,
                 "from_constraint": constraint_id, "added": core.now()}
        document["checks"] = [c for c in document["checks"] if c["id"] != check["id"]] + [check]
        # Install the executable half first; an unpromoted check is ignored after a crash.
        _write_checks(meta, document)
        constraint["status"] = "promoted"
        _write_constraints(meta, constraints)
    _event(run_dir, "constraint.promote", constraint_id, actor)
    return {"constraint": constraint, "check": check}


def retire(project_root, constraint_id, reason, actor, run_dir=None):
    if not _nonempty(reason):
        raise core.GFError("bad_reason", "retirement reason must be non-empty")
    meta = pathlib.Path(project_root) / ".graph-flow"
    with store.locked(meta / ".lock"):
        constraints, document = _read_constraints(meta), _read_checks(meta)
        constraint = _find(constraints, constraint_id)
        if constraint["status"] == "retired":
            raise core.GFError("wrong_status", "constraint is already retired", core.EXIT_STATE)
        document["checks"] = [c for c in document["checks"] if c["id"] != "fx_" + constraint_id]
        _write_checks(meta, document)
        constraint["status"], constraint["retired_reason"] = "retired", reason
        _write_constraints(meta, constraints)
    _event(run_dir, "constraint.retire", constraint_id, actor)
    return {"constraint": constraint}


def fixed_checks(project_root):
    meta = pathlib.Path(project_root) / ".graph-flow"
    with store.locked(meta / ".lock"):
        constraints, document = _read_constraints(meta), _read_checks(meta)
        promoted = {c["id"] for c in constraints if c["status"] == "promoted"}
        return [dict(c, type="cmd") for c in document["checks"]
                if c.get("from_constraint") in promoted]
