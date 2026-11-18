"""Dependency-free stdio MCP adapter; command rules live in cli (P6)."""
import contextlib
import io
import json
import os
import pathlib
import sys
import tempfile

from . import __version__, cli


def _field(kind, description):
    result = {"type": kind, "description": description}
    if kind == "array":
        result.update(items={"type": "string"}, minItems=1)
    return result


FIELDS = {
    "run": _field("string", "Absolute run directory; overrides GF_RUN for this call."),
    "project": _field("string", "Git project directory; defaults to the CLI's project discovery."),
    "node": _field("string", "Target node id; workers and reviewers remain bound to GF_NODE."),
    "check": _field("string", "Check id declared in the node's plan."),
    "cwd": _field("string", "Working tree directory in which to start, check, submit, or gate."),
    "plan": _field("object", "Complete plan as a JSON object, validated by the CLI. Integration cmd checks may declare "
                   "requires_passed as a non-empty list of distinct producer node IDs, different from the check ID. "
                   "Each producer's own work gate can run the check at any lane once the other producers pass. "
                   "Other work gates run it at effective lane 2 or 3 once all producers pass. The final gate always runs it."),
    "executor": _field("string", "Executor: inline, subagent, workflow, t3, or background."),
    "model": _field("string", "Assigned model name."),
    "effort": _field("string", "Assigned reasoning effort."),
    "provider": _field("string", "Assigned provider name."),
    "family": _field("string", "Model family: claude, openai, or other."),
    "isolation": _field("string", "Isolation: shared or worktree."),
    "result": _field("string", "Observed host check result: passed or failed."),
    "note": _field("string", "Evidence note for an observed host check."),
    "commit": _field("string", "Submission commit descending from the recorded base."),
    "branch": _field("string", "Submission branch name."),
    "notes": _field("string", "Submission notes."),
    "low_confidence": _field("array", "Specific uncertainties reported with the submission."),
    "verdict": _field("string", "Review verdict: pass or fail."),
    "findings": {"type": "array", "description": "Review findings as a JSON array.",
                 "items": {"type": "object"}},
    "nodes": _field("array", "Submitted node ids to merge."),
    "conformance": _field("boolean", "Include measured observations for P1–P12."),
    "final": _field("boolean", "Gate integration checks instead of one node; omit node."),
    "reason": _field("string", "Reason for reopening a node or retiring a constraint."),
    "kind": _field("string", "Decision kind: direction, information, review, or authorization."),
    "question": _field("string", "Question only a person can answer."),
    "options": _field("array", "Concrete answer choices for a free question."),
    "purpose": _field("string", "Decision purpose; defaults to free."),
    "command": _field("string", "Command cited as decision evidence."),
    "files": _field("array", "Project-relative files cited as decision evidence."),
    "id": _field("string", "Decision or constraint id."),
    "timeout": _field("number", "Seconds to wait for an answer; defaults to 600."),
    "from_node": _field("string", "Passed node from which the constraint is derived."),
    "text": _field("string", "Constraint text returned to future planning briefs."),
    "review_when": _field("string", "Condition under which to reconsider the constraint."),
    "paths": _field("array", "Project-relative paths to which the constraint applies."),
    "tags": _field("array", "Plan tags to which the constraint applies."),
    "run_command": _field("string", "Fixed check command promoted from the constraint."),
    "capabilities": _field("array", "Available host executor or tool capabilities."),
    "run_id": _field("string", "New run id, unique within this project."),
}


def _tool(command, description, required=(), positional=(), options=(), properties=None):
    names = list(dict.fromkeys(["run"] + list(required) + list(positional) + list(options)))
    fields = {name: FIELDS[name] for name in names}
    fields.update(properties or {})
    return {"command": tuple(command.split()), "positional": positional, "options": options,
            "description": description,
            "inputSchema": {"type": "object", "properties": fields,
                            "required": list(required), "additionalProperties": False}}


TOOLS = {
    "run_status": _tool("status", "Read run or own-node state with role-limited context (P5).",
                        positional=("node",)),
    "plan_validate": _tool("plan validate", "Validate a plan's checks, scope, and dependencies (P1, P3, P4).",
                           required=("plan",), positional=("plan",)),
    "plan_set": _tool("plan set", "Validate and record an immutable plan revision (P3, P4).",
                      required=("plan",), positional=("plan",)),
    "ready_nodes": _tool("ready", "Compute nodes ready to run from accepted dependency artifacts (P3)."),
    "route_node": _tool("route", "Suggest an executor and model for a node using deterministic routing (P6).",
                        required=("node",), positional=("node",)),
    "assign_node": _tool("assign", "Record one node's executor, model, and isolation (P4, P5).",
                         required=("node", "executor", "model", "effort", "provider", "family", "isolation"),
                         positional=("node",), options=("executor", "model", "effort", "provider", "family", "isolation")),
    "node_brief": _tool("brief", "Build a node's own context or a planning brief with constraints (P5, P11).",
                        positional=("node",), options=("plan", "project"),
                        properties={"plan": _field("boolean", "Return the planning brief; omit node.")}),
    "node_start": _tool("start", "Begin a bounded work or review attempt and record its base (P2).",
                        required=("node",), positional=("node",), options=("cwd",)),
    "check_red": _tool("red", "Run planned command checks before work and record failing-first evidence (P1).",
                       required=("node",), positional=("node", "check"), options=("cwd",)),
    "check_run": _tool("check run", "Execute a planned command check and record deterministic evidence (P1).",
                       required=("node", "check"), positional=("node", "check"), options=("cwd",)),
    "check_record": _tool("check record", "Record observed host-tool evidence with its explicit grade (P7).",
                          required=("node", "check", "result"), positional=("node", "check"), options=("result", "note")),
    "node_submit": _tool("submit", "Submit a node's work and uncertainties for evidence-based gating (P7).",
                         required=("node",), positional=("node",),
                         options=("commit", "branch", "notes", "low_confidence", "cwd")),
    "review_submit": _tool("review submit", "Submit an independent review verdict and cited findings (P5, P7).",
                           required=("node", "verdict", "findings"), positional=("node",), options=("verdict", "findings")),
    "merge_nodes": _tool("merge", "Merge submitted node commits with deterministic conflict reporting (P6).",
                         required=("nodes",), positional=("nodes",)),
    "gate_node": _tool("gate", "Gate one node or final integration from evidence in grade order (P7, P8, P9).",
                       positional=("node",), options=("final", "cwd")),
    "node_reopen": _tool("reopen", "Return one accepted unit and its dependents for correction (P8).",
                         required=("node", "reason"), positional=("node",), options=("reason",)),
    "decision_ask": _tool("decide ask", "Ask a free direction/information question; only the gate creates binding approvals (P10).",
                          required=("kind", "question"), options=("kind", "question", "node", "check", "purpose", "command", "files", "options")),
    "decision_list": _tool("decide list", "List open decisions within the caller's node context (P5, P10)."),
    "decision_wait": _tool("decide wait", "Wait for a person's decision without answering on their behalf (P10).",
                           required=("id",), positional=("id",), options=("timeout",)),
    "constraint_list": _tool("learn list", "Read constraints returned from accepted work to planning (P11).", options=("project",)),
    "constraint_add": _tool("learn add", "Derive a reusable constraint from accepted node evidence (P11).",
                            required=("from_node", "text", "review_when"), options=("from_node", "text", "review_when", "paths", "tags", "project")),
    "constraint_promote": _tool("learn promote", "Promote a learned constraint into a fixed machine check (P1, P11).",
                                required=("id", "run_command"), positional=("id",), options=("run_command", "project")),
    "constraint_retire": _tool("learn retire", "Retire a constraint and its fixed check with a reason (P11).",
                               required=("id", "reason"), positional=("id",), options=("reason", "project")),
    "run_trace": _tool("trace", "Measure work, human answers and waits, and P1–P12 observations from records.", options=("conformance",)),
    "host_set": _tool("host set", "Record available host capabilities for deterministic executor routing (P6).",
                      required=("capabilities",), positional=("capabilities",)),
    "run_init": _tool("init", "Initialize a run with an append-only record of its identity (P12).",
                      required=("run_id",), positional=("run_id",), options=("project",)),
}


def _visible_tools():
    role = os.environ.get("GF_ROLE") or "leader"
    return {name: tool for name, tool in TOOLS.items()
            if role != "human" and role in cli.COMMANDS[tool["command"]]["roles"]}


class InvalidParams(ValueError):
    pass


def _validate(value, schema, name="arguments"):
    kind = schema.get("type")
    valid = {"object": isinstance(value, dict), "array": isinstance(value, list),
             "string": isinstance(value, str), "boolean": isinstance(value, bool),
             "number": isinstance(value, (float, int)) and not isinstance(value, bool)}
    if kind and not valid[kind]:
        raise InvalidParams(name + " must be a JSON " + kind)
    if kind == "object" and "properties" in schema:
        for key in schema["required"]:
            if key not in value:
                raise InvalidParams("missing argument: " + key)
        for key, item in value.items():
            if key not in schema["properties"]:
                raise InvalidParams("unknown argument: " + key)
            _validate(item, schema["properties"][key], key)
    if kind == "array":
        if len(value) < schema.get("minItems", 0):
            raise InvalidParams(name + " must not be empty")
        for item in value:
            _validate(item, schema["items"], name + " item")


def _call(tool, arguments):
    _validate(arguments, tool["inputSchema"])
    argv = ["--json"]
    for key in ("run", "project"):
        if key in arguments:
            argv.append("--" + key + "=" + arguments[key])
    argv.extend(tool["command"])
    with tempfile.TemporaryDirectory(prefix="graph-flow-mcp-") as directory:
        values = dict(arguments)
        for key in ("plan", "findings"):
            if key in values and not isinstance(values[key], bool):
                filename = pathlib.Path(directory) / (key + ".json")
                filename.write_text(json.dumps(values[key], ensure_ascii=False), encoding="utf-8")
                values[key] = str(filename)
        for key in tool["positional"]:
            if key in values:
                value = values[key]
                argv.extend(value if isinstance(value, list) else [value])
        for key in tool["options"]:
            if key == "project" or key not in values:
                continue
            value = values[key]
            flag = "--" + {"from_node": "from", "run_command": "run"}.get(key, key.replace("_", "-"))
            if isinstance(value, bool):
                if value:
                    argv.append(flag)
            elif key == "options":
                argv.extend("--option=" + text for text in value)
            elif isinstance(value, list):
                argv.extend([flag] + value)
            else:
                # Equals keeps option-like strings (including --help) as values.
                argv.append(flag + "=" + str(value))
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = cli.main(argv)
    payload = json.loads(output.getvalue())
    if payload.get("show"):
        payload["show"] = payload["show"].replace("gf open", "graph-flow open", 1)
        payload["message"] = "Ask the person to run `%s` in their terminal; this MCP host cannot open their browser." % payload["show"]
    return {"content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False)}],
            "isError": code in (2, 3, 4, 5)}


def _handle(request):
    if not isinstance(request, dict) or request.get("jsonrpc") != "2.0" or not isinstance(request.get("method"), str):
        return {"error": {"code": -32600, "message": "Invalid JSON-RPC request"}, "id": None}
    if "id" not in request or request["method"] == "notifications/initialized":
        return None
    method, params = request["method"], request.get("params", {})
    if not isinstance(params, dict):
        raise InvalidParams("params must be a JSON object")
    if method == "initialize":
        result = {"protocolVersion": params.get("protocolVersion", "2025-06-18"),
                  "serverInfo": {"name": "graph-flow", "version": __version__}, "capabilities": {"tools": {}}}
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": [{"name": name, "description": tool["description"], "inputSchema": tool["inputSchema"]}
                            for name, tool in _visible_tools().items()]}
    elif method == "tools/call":
        name = params.get("name")
        if not isinstance(name, str):
            raise InvalidParams("tool name must be a string")
        tool = _visible_tools().get(name)
        if tool is None:
            raise InvalidParams("unknown or unavailable tool")
        result = _call(tool, params.get("arguments", {}))
    else:
        return {"id": request["id"], "error": {"code": -32601, "message": "Method not found: " + method}}
    return {"id": request["id"], "result": result}


def serve(stdin, stdout):
    """Read JSON-RPC lines until EOF; stdout contains protocol messages only."""
    for line in stdin:
        if not line.strip():
            continue
        request = None
        try:
            request = json.loads(line)
        except (ValueError, RecursionError):
            response = {"id": None, "error": {"code": -32700, "message": "Parse error"}}
        else:
            try:
                response = _handle(request)
            except Exception as exc:
                code = -32602 if isinstance(exc, InvalidParams) else -32603
                if code == -32603:
                    print("graph-flow MCP: " + str(exc), file=sys.stderr)
                if isinstance(request, dict) and "id" not in request:
                    continue
                response = {"id": request.get("id") if isinstance(request, dict) else None,
                            "error": {"code": code, "message": str(exc)}}
        if response is not None:
            response["jsonrpc"] = "2.0"
            stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            stdout.flush()
