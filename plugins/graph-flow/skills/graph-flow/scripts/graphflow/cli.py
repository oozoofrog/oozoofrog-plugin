"""Command dispatch, role checks and output (records.md sections 2 and 10)."""
import argparse
import importlib
import json
import os
import pathlib
import re
import secrets
import shlex
import sys

from . import assign, checks, core, decisions, gate, graph, merge, plan, route, state, store


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
    with store.transaction(args.run, replace_invalid=True) as tx:
        raw = _read_json(args.file)
        problems = plan.validate(raw)
        if problems:
            raise core.GFError("invalid_plan", json.dumps(problems), core.EXIT_NEGATIVE)
        normalized, notices = plan.normalize(raw)
        learn = importlib.import_module("graphflow.learn")
        normalized["promoted_checks"] = learn.fixed_checks(store.project_of(args.run))
        normalized["constraints"] = learn.applying(store.project_of(args.run), normalized)
        problems = plan.validate(normalized)
        if problems:
            raise core.GFError("invalid_plan", json.dumps(problems), core.EXIT_NEGATIVE)
        prior = state.derive(tx.plan, tx.events)
        if not prior["run"].get("run_nonce"):
            tx.append("run.nonce", {"run_nonce": secrets.token_hex(32)}, actor)
        identity = state.plan_identity(normalized)
        approval = state.plan_approval(prior)
        # Never relabel an accepted result or change a running worker's contract.
        if tx.plan:
            old_nodes = plan.node_index(tx.plan)
            new_nodes = plan.node_index(normalized)
            changed = {nid for nid, n in old_nodes.items()
                       if nid not in new_nodes or state.fingerprint(n) != state.fingerprint(new_nodes[nid])}
            deps = state._closure(old_nodes)
            protected = [nid for nid, st in prior["nodes"].items()
                         if st["status"] in ("running", "submitted", "passed")
                         and (nid in changed or deps[nid] & changed)]
            if protected:
                raise core.GFError("active_plan_change", "Keep completed/running contracts; add new work instead: "
                                   + ", ".join(protected), core.EXIT_STATE)
        reuse = (not tx.plan_error and not prior["run"].get("location_mismatch") and approval and normalized == tx.plan and approval.get("plan_identity") == identity
                 and (approval["status"] == "open" or
                      approval["status"] == "answered" and approval.get("verified")
                      and approval["outcome"] == "approved"))
        ids = [c["id"] for c in normalized["constraints"]]
        if reuse:
            result = {"revision": tx.revision, "nodes": len(normalized["nodes"]), "decision": approval["id"],
                      "notices": len(notices), "constraints_applied": ids}
            if approval["status"] == "open":
                _show(args, result, approval["id"])
            return result
        revision, sha = tx.write_plan(normalized)
        tx.append("plan.set", {"revision": revision, "plan_sha256": sha,
                               "plan_identity": identity, "node_counts": plan.node_counts(normalized["nodes"]),
                               "fingerprints": {n["id"]: state.fingerprint(n) for n in normalized["nodes"]},
                               "constraints_applied": ids, "replaced_unverifiable": tx.plan_error}, actor)
        tx.append("constraint.apply", {"ids": ids}, actor)
        if not reuse:
            for previous in prior["decisions"].values():
                if previous.get("purpose") == "plan_approval" and previous["status"] != "superseded":
                    tx.append("decision.superseded", {"id": previous["id"], "revision": revision}, actor)
            wording = " ".join([normalized.get("title", ""), normalized.get("goal", "")] +
                               [n.get("title", "") for n in normalized["nodes"]])
            question = "이 계획대로 시작할까요?" if re.search(r"[\u1100-\u11ff\u3130-\u318f\uac00-\ud7af]", wording) else "Start with this plan?"
            data = {"node": None, "submission": None, "check": None, "purpose": "plan_approval",
                    "kind": "authorization", "question": question, "plan_identity": identity,
                    "evidence": {"command": None, "files": [], "checks": []}}
            event = tx.append("decision.ask", data, actor)
            data["id"] = "d%d" % event["seq"]
            did = data["id"]
        else:
            did = approval["id"]
    result = {"revision": revision, "nodes": len(normalized["nodes"]), "decision": did,
              "notices": len(notices), "constraints_applied": ids}
    if not reuse or approval["status"] == "open":
        _show(args, result, did)
    return result


def _show(args, result, decision=None):
    """Only open on explicit --open; suppression never changes consent."""
    result["show"] = "gf open" + (" --decision " + decision if decision else "")
    if getattr(args, "open", False) and os.environ.get("GF_NO_OPEN") != "1":
        try:
            target = {"project": str(_project(args)), "run": pathlib.Path(args.run).name,
                      "decision": decision}
            _lazy_import("server").open_dashboard(target=target)
            result["opened"] = True
        except core.GFError as exc:
            # The event is already durable. Do not suggest retrying its mutation.
            result["open_error"] = exc.code
    return result


def _runs(args):
    """Without a run, say which runs this project has so a new session can pick one up."""
    root = store.project_root(args.project)
    found = []
    directory = pathlib.Path(root) / ".graph-flow" / "runs"
    for path in sorted(directory.iterdir()) if directory.is_dir() else []:
        if not (path / "events.jsonl").is_file():
            continue
        entry = {"id": path.name, "run": str(path)}
        try:
            with store.transaction(path) as tx:
                derived = state.derive(tx.plan, tx.events)
            entry.update(status=derived["run"]["status"], last_event=tx.events[-1]["ts"] if tx.events else None,
                         open_decisions=[d["id"] for d in decisions.open_decisions(derived)])
        except core.GFError as exc:
            entry["error"] = exc.message
        found.append(entry)
    return {"project": str(root), "runs": found,
            "message": "Set GF_RUN to one run path, or start a new one with gf init <id>."}


def _status(args, actor):
    if not args.run:
        return _runs(args)
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
    return {"state": derived, "ready": graph.available(current_plan or {"nodes": []}, derived)}


def _host_set(args, actor):
    with store.transaction(args.run) as tx:
        tx.append("host.set", {"capabilities": args.capabilities}, actor)
    return {"capabilities": args.capabilities}


def _snapshot(run_dir):
    with store.transaction(run_dir) as tx:
        return tx.plan, state.derive(tx.plan, tx.events)


def _project(args):
    return store.project_root(args.project) if args.project else (
        store.project_of(args.run) if args.run else store.project_root())


def _lazy_import(name):
    try:
        return importlib.import_module("graphflow." + name)
    except ModuleNotFoundError as exc:
        if exc.name != "graphflow." + name:
            raise
        raise core.GFError("not_implemented", name + " is not implemented yet")


def _mcp(args, actor):
    _lazy_import("mcp").serve(sys.stdin, sys.stdout)
    return 0


def _serve(args, actor):
    _lazy_import("server").serve(port=args.port)
    return {}


def _open(args, actor):
    server = _lazy_import("server")
    if args.stop:
        stopped = server.stop_dashboard()
        return {"stopped": stopped,
                "message": "Dashboard stopped." if stopped else "No dashboard is running."}
    target = None
    if args.run:
        target = {"project": str(_project(args)), "run": pathlib.Path(args.run).name,
                  "decision": args.decision, "node": args.target_node}
    elif args.decision or args.target_node:
        raise core.GFError("run_required", "--run or GF_RUN is required to open a decision or node")
    opened = server.open_dashboard(target=target) if target else server.open_dashboard()
    shown = args.decision or args.target_node
    return dict(opened, message="Browser launch suppressed by GF_NO_OPEN=1." if opened.get("suppressed") else "Dashboard opened in the browser%s." % (" on " + shown if shown else ""))


def _setup(args, actor):
    launcher = _lazy_import("launcher")
    if not args.remove and actor["role"] == "human":
        decisions.ensure_key(actor)
    return launcher.remove(args.bin_dir) if args.remove else launcher.install(args.bin_dir)


def _require_human_terminal(actor, command="decide answer"):
    if actor["role"] != "human":
        raise core.GFError("forbidden", command + " requires role human", core.EXIT_FORBIDDEN)
    if os.environ.get("GF_HUMAN_TERMINAL") != "1":
        raise core.GFError("forbidden", command + " requires GF_HUMAN_TERMINAL=1", core.EXIT_FORBIDDEN)
    if not sys.stdin.isatty():
        raise core.GFError("forbidden", command + " requires stdin to be a TTY", core.EXIT_FORBIDDEN)


def _loop(args, actor):
    path, node = args.command_path, getattr(args, "target_node", None)
    if path == ("ready",):
        current_plan, derived = _snapshot(args.run)
        return {"ready": graph.ready(current_plan or {"nodes": []}, derived)}
    if path == ("route",):
        current_plan, derived = _snapshot(args.run)
        state.require_plan_approval(derived)
        definition = plan.node_by_id(current_plan, node)
        current = dict(derived["nodes"][node])
        if definition["kind"] == "review":
            current["target_family"] = (derived["nodes"][definition["target"]].get("assignment") or {}).get("family")
        return route.suggest(definition, current, derived["run"]["host"],
                             route.load_usage(), route.load_routing())
    if path == ("assign",):
        return assign.assign(args.run, node, args.executor, args.model, args.effort,
                             args.provider, args.family, args.isolation, actor)
    if path == ("brief",):
        if args.plan_brief:
            return {"brief": assign.plan_brief(_project(args), args.run)}
        if node is None:
            raise core.GFError("usage", "brief requires a node or --plan")
        text = assign.brief(args.run, node)
        return {"brief": text, "path": str(pathlib.Path(args.run).resolve() / "brief" / (node + ".md"))}
    if path == ("start",):
        return checks.start(args.run, node, args.cwd, actor)
    if path == ("red",):
        return checks.red(args.run, node, args.check, args.cwd, actor)
    if path == ("check", "run"):
        with store.transaction(args.run) as tx:
            definition = plan.node_by_id(tx.plan, node)
            check = next((c for c in definition["checks"] if c["id"] == args.check), None)
            if check is None:
                raise core.GFError("unknown_check", "unknown check: " + args.check, core.EXIT_STATE)
            if check["type"] != "cmd":
                raise core.GFError("wrong_check_type", "check run requires a cmd check", core.EXIT_STATE)
        result = checks.run_cmd(args.run, node, check, "loop", args.cwd, actor)
        return result, core.EXIT_NEGATIVE if result["result"] == "failed" else core.EXIT_OK
    if path == ("check", "record"):
        return checks.record_host(args.run, node, args.check, args.result, args.note, actor)
    if path == ("submit",):
        return checks.submit(args.run, node, args.commit, args.branch, args.notes,
                             args.low_confidence, args.cwd, actor)
    if path == ("review", "submit"):
        findings = _read_json(args.findings)
        if not isinstance(findings, list):
            raise core.GFError("bad_json", "findings must be a JSON list")
        return checks.review_submit(args.run, node, args.verdict, findings, actor)
    if path == ("merge",):
        return merge.merge(args.run, args.nodes, actor)
    if path == ("gate",):
        if args.final:
            result = gate.gate_final(args.run, args.cwd, actor)
            passed = result["result"] == "passed"
        else:
            if node is None:
                raise core.GFError("usage", "gate requires a node or --final")
            result = gate.gate(args.run, node, args.cwd, actor)
            passed = result["verdict"] == "pass"
        _, derived = _snapshot(args.run)
        waiting = decisions.open_decisions(derived)
        if result.get("asks"):
            _show(args, result, result["asks"][0])
        elif waiting:
            result["show"] = "gf open --decision " + waiting[0]["id"]
        elif args.final and passed:
            _show(args, result)
        return result, core.EXIT_OK if passed else core.EXIT_NEGATIVE
    if path == ("reopen",):
        return gate.reopen(args.run, node, args.reason, actor)
    if path == ("decide", "ask"):
        evidence = {"command": args.evidence_command, "files": args.files, "checks": []}
        asked = decisions.ask(args.run, args.kind, args.question, node, args.check,
                              args.purpose, evidence, actor)
        # How to put this question in front of the person (leader.md).
        return _show(args, asked, asked["id"])
    if path == ("decide", "list"):
        _, derived = _snapshot(args.run)
        own = actor["node"] if actor["role"] in ("worker", "reviewer") else None
        return {"decisions": decisions.open_decisions(derived, own)}
    if path == ("decide", "wait"):
        if actor["role"] in ("worker", "reviewer"):
            _, derived = _snapshot(args.run)
            decision = derived["decisions"].get(args.id)
            if decision is not None and decision["node"] != actor["node"]:
                raise core.GFError("forbidden", "decision wait is limited to own node", core.EXIT_FORBIDDEN)
        return decisions.wait(args.run, args.id, args.timeout)
    if path == ("key", "repin"):
        return decisions.repin(args.run, actor)
    if path == ("decide", "answer"):
        return decisions.answer(args.run, args.id, args.outcome, args.answer, "terminal", actor)
    if path[0] == "learn":
        learn = _lazy_import("learn")
        root = _project(args)
        if path[1] == "add":
            return learn.add(root, args.run, args.from_node, args.text, args.review_when,
                             args.paths, args.tags, actor)
        if path[1] == "list":
            return {"constraints": learn.all_constraints(root)}
        if path[1] == "promote":
            return learn.promote(root, args.id, args.run_command, actor, args.run)
        return learn.retire(root, args.id, args.reason, actor, args.run)
    if path == ("trace",):
        return _lazy_import("trace").trace(args.run)


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
_register("decide answer,key repin", "human")
_register("mcp", "leader worker reviewer", needs_run=False)
_register("serve,open,setup", "leader human", needs_run=False)
for _path in ("init", "plan validate", "learn list", "learn promote", "learn retire"):
    COMMANDS[tuple(_path.split())]["needs_run"] = False
for _path, _handler in (("init", _init), ("plan validate", _validate),
                        ("plan set", _set_plan), ("status", _status), ("host set", _host_set),
                        ("mcp", _mcp), ("serve", _serve), ("open", _open), ("setup", _setup)):
    COMMANDS[tuple(_path.split())]["handler"] = _handler
for _path, _entry in COMMANDS.items():
    if _entry["handler"] is None and _path not in (("mcp",), ("serve",)):
        _entry["handler"] = _loop


def _parser(authorize_only=False):
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
        if authorize_only:
            sub.add_argument("arguments", nargs=argparse.REMAINDER)
        elif path == ("init",):
            sub.add_argument("run_id")
        elif path in (("plan", "validate"), ("plan", "set")):
            sub.add_argument("file")
        elif path == ("host", "set"):
            sub.add_argument("capabilities", nargs="+")
        elif path == ("status",):
            sub.add_argument("target_node", nargs="?")
        elif path in (("route",), ("assign",), ("start",), ("red",), ("submit",),
                      ("reopen",), ("review", "submit"), ("check", "run"), ("check", "record")):
            sub.add_argument("target_node")
        elif path == ("brief",):
            choice = sub.add_mutually_exclusive_group(required=True)
            choice.add_argument("target_node", nargs="?")
            choice.add_argument("--plan", dest="plan_brief", action="store_true")
        elif path == ("gate",):
            choice = sub.add_mutually_exclusive_group(required=True)
            choice.add_argument("target_node", nargs="?")
            choice.add_argument("--final", action="store_true")
        elif path == ("merge",):
            sub.add_argument("nodes", nargs="+")
        elif path == ("decide", "ask"):
            sub.add_argument("--kind", required=True)
            sub.add_argument("--question", required=True)
            sub.add_argument("--node", dest="target_node")
            sub.add_argument("--check")
            sub.add_argument("--purpose")
            sub.add_argument("--command", dest="evidence_command")
            sub.add_argument("--files", nargs="+", default=[])
        elif path == ("decide", "wait"):
            sub.add_argument("id")
            sub.add_argument("--timeout", type=float, default=600)
        elif path == ("decide", "answer"):
            sub.add_argument("id")
            sub.add_argument("--outcome", required=True)
            sub.add_argument("--answer", default="")
        elif path == ("learn", "add"):
            sub.add_argument("--from", dest="from_node", required=True)
            sub.add_argument("--text", required=True)
            sub.add_argument("--review-when", required=True)
            sub.add_argument("--paths", nargs="+", default=[])
            sub.add_argument("--tags", nargs="+", default=[])
        elif path in (("learn", "promote"), ("learn", "retire")):
            sub.add_argument("id")
            if path[1] == "promote":
                sub.add_argument("--run", dest="run_command", required=True)
            else:
                sub.add_argument("--reason", required=True)
        elif path == ("serve",):
            sub.add_argument("--port", type=int, default=0)
        elif path == ("open",):
            sub.add_argument("--stop", action="store_true")
            sub.add_argument("--decision")
            sub.add_argument("--node", dest="target_node")
        elif path == ("setup",):
            sub.add_argument("--bin-dir")
            sub.add_argument("--remove", action="store_true")
        if authorize_only:
            continue
        if path in (("plan", "set"), ("decide", "ask"), ("gate",)):
            sub.add_argument("--open", action="store_true")
        if path in (("start",), ("red",), ("check", "run"), ("submit",), ("gate",)):
            sub.add_argument("--cwd")
        if path == ("assign",):
            for field in ("executor", "model", "effort", "provider", "family", "isolation"):
                sub.add_argument("--" + field, required=True)
        elif path == ("red",):
            sub.add_argument("check", nargs="?")
        elif path in (("check", "run"), ("check", "record")):
            sub.add_argument("check")
            if path[1] == "record":
                sub.add_argument("--result", choices=("passed", "failed"), required=True)
                sub.add_argument("--note", default="")
        elif path == ("submit",):
            sub.add_argument("--commit")
            sub.add_argument("--branch")
            sub.add_argument("--notes", default="")
            sub.add_argument("--low-confidence", action="extend", nargs="+", default=[])
        elif path == ("review", "submit"):
            sub.add_argument("--verdict", choices=("pass", "fail"), required=True)
            sub.add_argument("--findings", required=True)
        elif path == ("reopen",):
            sub.add_argument("--reason", required=True)
    return parser


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    json_output = "--json" in argv
    try:
        # Authorize the command before requiring its arguments (section 2).
        identity, _ = _parser(authorize_only=True).parse_known_args(argv)
        actor = core.actor_from_env(identity.role, identity.node)
        role = actor["role"]
        if role in ("worker", "reviewer") and not actor["node"]:
            raise core.GFError("node_required", "worker and reviewer roles require a node")
        entry = COMMANDS[identity.command_path]
        if identity.command_path in (("decide", "answer"), ("key", "repin")):
            _require_human_terminal(actor, " ".join(identity.command_path))
        if role not in entry["roles"]:
            raise core.GFError("forbidden", "role %s cannot run %s" % (role, " ".join(identity.command_path)), 3)
        parser = _parser()
        args, unknown = parser.parse_known_args(argv)
        if unknown and entry["handler"] is not None:
            parser.error("unrecognized arguments: %s" % " ".join(unknown))
        target = getattr(args, "target_node", None)
        if args.command_path == ("decide", "ask") and role in ("worker", "reviewer") and target is None:
            args.target_node = target = actor["node"]
        if (entry["own_node_only"] and role in ("worker", "reviewer") and target is not None
                and target != actor["node"] and not (role == "reviewer" and args.command_path == ("status",))):
            raise core.GFError("forbidden", "command is limited to own node", 3)
        if entry["handler"] is None:
            raise core.GFError("not_implemented", "%s is not implemented yet" % " ".join(args.command_path))
        if (entry["needs_run"] and not args.run
                and not (args.command_path == ("brief",) and args.plan_brief)
                and not (args.command_path == ("status",) and role in ("leader", "human"))):
            raise core.GFError("run_required", "--run or GF_RUN is required")
        result = entry["handler"](args, actor)
        if args.command_path == ("mcp",):
            return result
        payload, code = result if isinstance(result, tuple) else (result, 0)
        output = dict(ok=True, **payload)
        if code and args.command_path == ("plan", "validate"):
            output.update(ok=False, code="invalid_plan", message="plan validation failed")
    except core.GFError as exc:
        code = exc.exit_code
        message = exc.message
        if exc.code == "human_key_mismatch":
            message = message.replace("<run-path>", shlex.quote(str(args.run)))
        output = {"ok": False, "code": exc.code, "message": message}
    except SystemExit as exc:
        return exc.code
    except Exception as exc:
        code = core.EXIT_IO
        output = {"ok": False, "code": "internal", "message": str(exc)}
    if json_output:
        print(json.dumps(output, ensure_ascii=False))
    elif "brief" in output:
        print(output["brief"], end="" if output["brief"].endswith("\n") else "\n")
    elif output.get("rejection"):
        print(gate.render_rejection(output["rejection"]))
    else:
        print(output.get("message") or json.dumps(output, ensure_ascii=False))
    return code
