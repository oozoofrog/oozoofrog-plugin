"""Command dispatch, role checks and output (records.md sections 2 and 10)."""
import argparse
import importlib
import json
import os
import pathlib
import sys

from . import core, graph, plan, state, store


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise core.GFError("usage", message, core.EXIT_USAGE)


def _read_json(filename):
    try:
        return json.loads(pathlib.Path(filename).read_text(encoding="utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise core.GFError("bad_json", str(exc))
    except OSError as exc:
        raise core.GFError("io_error", str(exc), core.EXIT_IO)


def _init(args, actor):
    return {"run": str(store.init_run(store.project_root(args.project), args.run_id, actor))}


def _validate(args, actor):
    raw = _read_json(args.file)
    problems = plan.validate(raw)
    _, notices = plan.normalize(raw)
    return {"problems": problems, "notices": notices}, 1 if problems else 0


def _set_plan(args, actor):
    with store.transaction(args.run) as tx:
        raw = _read_json(args.file)
        problems = plan.validate(raw)
        if problems:
            raise core.GFError("invalid_plan", json.dumps(problems), core.EXIT_NEGATIVE)
        normalized, notices = plan.normalize(raw)
        try:
            learn = importlib.import_module("graphflow.learn")
        except ModuleNotFoundError as exc:
            if exc.name != "graphflow.learn":
                raise
            ids = []
        else:
            ids = [c["id"] for c in learn.applying(store.project_of(args.run), normalized)]
        revision, sha = tx.write_plan(normalized)
        tx.append("plan.set", {"revision": revision, "plan_sha256": sha,
                               "fingerprints": {n["id"]: state.fingerprint(n) for n in normalized["nodes"]},
                               "constraints_applied": ids}, actor)
        tx.append("constraint.apply", {"ids": ids}, actor)
    return {"revision": revision, "plan_sha256": sha, "notices": notices,
            "constraints_applied": ids}


def _status(args, actor):
    with store.transaction(args.run) as tx:
        current_plan = tx.plan
        derived = state.derive(current_plan, tx.events)
    role, own = actor["role"], actor["node"]
    if role in ("worker", "reviewer"):
        plan.node_by_id(current_plan, own)
        if role == "worker":
            return {"id": own, "node": derived["nodes"][own]}
        target = plan.node_by_id(current_plan, own).get("target")
        allowed = {own, target}
        if args.target_node and args.target_node not in allowed:
            raise core.GFError("forbidden", "status is limited to own node and target", 3)
        if args.target_node:
            return {"id": args.target_node, "node": derived["nodes"][args.target_node]}
        return {"state": {"nodes": {n: derived["nodes"][n] for n in allowed if n in derived["nodes"]}}}
    if args.target_node:
        plan.node_by_id(current_plan, args.target_node)
        return {"id": args.target_node, "node": derived["nodes"][args.target_node]}
    return {"state": derived, "ready": graph.ready(current_plan or {"nodes": []}, derived)}


def _host_set(args, actor):
    with store.transaction(args.run) as tx:
        tx.append("host.set", {"capabilities": args.capabilities}, actor)
    return {"capabilities": args.capabilities}


# Extensions add an entry here and argument declarations in _parser.
COMMANDS = {}


def _register(paths, roles, needs_run=True, own_node_only=False):
    for path in paths.split(","):
        COMMANDS[tuple(path.strip().split())] = {
            "handler": None, "roles": tuple(roles.split()),
            "needs_run": needs_run, "own_node_only": own_node_only}


_register("init,plan set,host set,ready,route,assign,brief,merge,gate,reopen,learn add,learn promote,learn retire", "leader")
_register("plan validate,learn list,trace", "leader worker reviewer human")
_register("status", "leader worker reviewer human", own_node_only=True)
_register("start", "leader worker reviewer", own_node_only=True)
_register("red,check run,check record,submit", "leader worker", own_node_only=True)
_register("review submit", "reviewer", own_node_only=True)
_register("decide ask,decide wait,decide list", "leader worker reviewer human", own_node_only=True)
_register("decide answer", "human")
_register("mcp", "leader worker reviewer", needs_run=False)
_register("serve", "leader human", needs_run=False)
for _path in ("init", "plan validate", "learn list", "learn promote", "learn retire"):
    COMMANDS[tuple(_path.split())]["needs_run"] = False
for _path, _handler in (("init", _init), ("plan validate", _validate),
                        ("plan set", _set_plan), ("status", _status), ("host set", _host_set)):
    COMMANDS[tuple(_path.split())]["handler"] = _handler


def _parser():
    parser = Parser(prog="gf", allow_abbrev=False)
    for name in ("run", "project", "role", "node"):
        parser.add_argument("--" + name, default=os.environ.get("GF_" + name.upper()) if name != "project" else None)
    parser.add_argument("--json", action="store_true")
    commands = parser.add_subparsers(dest="command", required=True)
    groups = {}
    for path, entry in COMMANDS.items():
        if len(path) == 2:
            if path[0] not in groups:
                group = commands.add_parser(path[0], allow_abbrev=False)
                groups[path[0]] = group.add_subparsers(dest="subcommand", required=True)
            sub = groups[path[0]].add_parser(path[1], allow_abbrev=False)
        else:
            sub = commands.add_parser(path[0], allow_abbrev=False)
        sub.set_defaults(command_path=path)
        if path == ("init",):
            sub.add_argument("run_id")
        elif path in (("plan", "validate"), ("plan", "set")):
            sub.add_argument("file")
        elif path == ("host", "set"):
            sub.add_argument("capabilities", nargs="+")
        elif path == ("status",):
            sub.add_argument("target_node", nargs="?")
        else:
            # Placeholder commands accept their future syntax; authorization still runs.
            sub.add_argument("arguments", nargs=argparse.REMAINDER)
    return parser


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    json_output = "--json" in argv
    try:
        parser = _parser()
        args, unknown = parser.parse_known_args(argv)
        if unknown and COMMANDS[args.command_path]["handler"] is not None:
            parser.error("unrecognized arguments: %s" % " ".join(unknown))
        actor = core.actor_from_env(args.role, args.node)
        role = actor["role"]
        if role in ("worker", "reviewer") and not actor["node"]:
            raise core.GFError("node_required", "worker and reviewer roles require a node")
        entry = COMMANDS[args.command_path]
        if role not in entry["roles"]:
            raise core.GFError("forbidden", "role %s cannot run %s" % (role, " ".join(args.command_path)), 3)
        target = getattr(args, "target_node", None)
        arguments = getattr(args, "arguments", [])
        if (not target and args.command_path in (("start",), ("red",), ("check", "run"),
                                                ("check", "record"), ("submit",), ("review", "submit"))
                and arguments and not arguments[0].startswith("-")):
            target = arguments[0]
        if (entry["own_node_only"] and role in ("worker", "reviewer") and target
                and target != actor["node"] and not (role == "reviewer" and args.command_path == ("status",))):
            raise core.GFError("forbidden", "command is limited to own node", 3)
        if entry["handler"] is None:
            raise core.GFError("not_implemented", "%s is not implemented yet" % " ".join(args.command_path))
        if entry["needs_run"] and not args.run:
            raise core.GFError("run_required", "--run or GF_RUN is required")
        result = entry["handler"](args, actor)
        payload, code = result if isinstance(result, tuple) else (result, 0)
        output = dict(payload, ok=(code == 0))
        if code:
            output.update(code="invalid_plan", message="plan validation failed")
    except core.GFError as exc:
        code = exc.exit_code
        output = {"ok": False, "code": exc.code, "message": exc.message}
    except SystemExit as exc:
        return exc.code
    except Exception as exc:
        code = core.EXIT_IO
        output = {"ok": False, "code": "internal", "message": str(exc)}
    print(json.dumps(output, ensure_ascii=False) if json_output else
          (output.get("message") or json.dumps(payload, ensure_ascii=False)))
    return code
