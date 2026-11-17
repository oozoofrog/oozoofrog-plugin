"""Pure plan validation, normalization and dependency queries."""
import copy
import math
import pathlib
import re

from graphflow import core

_ID = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}")
_GRADES = ("bulk", "scoped", "daily", "large", "security")
_DECISIONS = ("direction", "information", "review", "authorization")


def is_korean(plan):
    return bool(re.search(r"[\u1100-\u11ff\u3130-\u318f\uac00-\ud7af]", str(plan)))


def approval_question(plan):
    return "이 계획대로 시작할까요?" if is_korean(plan) else "Start with this plan?"


def _list(value):
    return value if isinstance(value, list) else []


def _nodes(plan):
    if not isinstance(plan, dict):
        return []
    return [n for n in _list(plan.get("nodes")) if isinstance(n, dict)]


def _index(plan):
    return {n["id"]: n for n in _nodes(plan) if isinstance(n.get("id"), str)}


def _edges(plan):
    edges = {}
    for node_id, node in _index(plan).items():
        parents = [need["from"] for need in _list(node.get("needs"))
                   if isinstance(need, dict) and isinstance(need.get("from"), str)]
        if node.get("kind") == "review" and isinstance(node.get("target"), str):
            parents.append(node["target"])
        edges[node_id] = parents
    return edges


def _reaches(edges, a, b):
    pending, seen = list(edges.get(a, [])), set()
    while pending:
        node_id = pending.pop()
        if node_id == b:
            return True
        if node_id not in seen:
            seen.add(node_id)
            pending.extend(edges.get(node_id, []))
    return False


def _under(path, owner):
    return (path.rstrip("/") == owner.rstrip("/") or
            (owner.endswith("/") and path.startswith(owner)))


def overlaps(paths_a, paths_b):
    """Whether two ownership lists share a file or directory."""
    return any(_under(a, b) or _under(b, a)
               for a in paths_a for b in paths_b
               if isinstance(a, str) and isinstance(b, str))


def depends(plan, a, b):
    """Review targets are dependencies, even without an explicit needs edge."""
    return (isinstance(a, str) and isinstance(b, str) and
            a != b and _reaches(_edges(plan), a, b))


def node_index(plan):
    """The single executable node lookup; ambiguity is never resolved by order."""
    result = {}
    for node in _nodes(plan):
        nid = node.get("id")
        if not isinstance(nid, str) or nid in result:
            raise core.GFError("plan_tampered", "Ambiguous node id: %s" % nid, core.EXIT_STATE)
        result[nid] = node
    return result


def node_by_id(plan, node_id):
    node = node_index(plan).get(node_id)
    if node is not None:
        return node
    raise core.GFError("unknown_node", "unknown node: %s" % node_id, core.EXIT_STATE)


def normalize(plan):
    """Copy the plan, fill node defaults and escalate work without a cmd check."""
    result, notices = copy.deepcopy(plan), []
    for node in _nodes(result):
        for field in ("needs", "owns", "outputs", "reads", "checks"):
            node.setdefault(field, [])
        if node.get("kind") != "decision":
            node.setdefault("max_attempts", 3)
        lane = node.get("lane")
        node["effective_lane"] = lane
        checks = [c for c in _list(node["checks"]) if isinstance(c, dict)]
        if node.get("kind") == "work" and not any(c.get("type") == "cmd" for c in checks):
            if type(lane) is int and lane in (1, 2, 3):
                node["effective_lane"] = min(3, lane + 1)
            if isinstance(node["checks"], list) and not any(c.get("type") == "human" for c in checks):
                used_ids = [c.get("id") for c in checks]
                check_id, suffix = "human", 1
                while check_id in used_ids:
                    check_id = "human_review" if suffix == 1 else "human_review_%s" % suffix
                    suffix += 1
                node["checks"].append({"id": check_id, "type": "human"})
            notices.append({"code": "no_machine_check", "node": node.get("id"),
                            "message": "work without a cmd check requires human review"})
        if "title" not in node:
            notices.append({"code": "no_title", "node": node.get("id"),
                            "message": "add a title in the user's language for the dashboard"})
    groups = [(n.get("id"), n.get("checks", [])) for n in _nodes(result)]
    if isinstance(result, dict):
        groups += [("_run", result.get(k, [])) for k in ("integration_checks", "promoted_checks")]
    for nid, checks in groups:
        for check in _list(checks):
            if (isinstance(check, dict) and check.get("type") == "cmd"
                    and isinstance(check.get("run"), str)
                    and check["run"].strip() in ("true", ":", "exit 0", "")):
                notices.append({"code": "unfalsifiable_check", "node": nid, "check": check.get("id"),
                                "message": "command always succeeds; use a check that can fail"})
    return result, notices


def _bad_path(path):
    parts = pathlib.PurePosixPath(path).parts
    return (pathlib.PurePosixPath(path).is_absolute() or ".." in parts or
            bool(parts and parts[0] in (".git", ".graph-flow")))


def validate(plan):
    """Collect structural and semantic problems; use a normalized copy for V9."""
    problems = []

    def problem(code, node, message):
        problems.append({"code": code, "node": node, "message": message})

    def known(obj, allowed, node):
        for key in obj:
            if key not in allowed.split():
                problem("V1", node, "unknown field: %s" % key)

    def field(obj, key, expected, node, required=True):
        if key not in obj and not required:
            return
        if not isinstance(obj.get(key), expected):
            problem("V1", node, "%s must be %s" % (key, expected.__name__))

    def paths(values, node):
        for path in _list(values):
            if isinstance(path, str) and _bad_path(path):
                problem("V8", node, "unsafe project-relative path: %s" % path)

    def text(obj, key, limit, node):
        if key in obj and (not isinstance(obj[key], str) or not obj[key].strip()
                           or len(obj[key]) > limit):
            problem("V1", node, "%s must be a non-empty string of at most %d characters" % (key, limit))

    def context(obj, node):
        if "context" not in obj:
            return
        value = obj["context"]
        if not isinstance(value, dict):
            problem("V1", node, "context must be an object")
            return
        for key in value:
            if key not in ("why", "if_approved", "if_rejected", "undo"):
                problem("V1", node, "unknown context key: %s" % (key,))
            else:
                text(value, key, 300, node)

    def checks(values, node):
        seen = set()
        singleton_types = set()
        for check in _list(values):
            if not isinstance(check, dict):
                problem("V1", node, "check must be an object")
                continue
            kind = check.get("type")
            type_fields = {"cmd": "run cwd timeout_s from_constraint added", "scope": "", "cites": "",
                           "host": "tool expect", "human": "prompt context"}
            known(check, "id type title " + (type_fields.get(kind, "") if isinstance(kind,str) else ""), node)
            check_id = check.get("id")
            if not isinstance(check_id, str) or not _ID.fullmatch(check_id):
                problem("V2", node, "malformed check id: %r" % check_id)
            elif check_id in seen:
                problem("V2", node, "duplicate check id: %s (check integration_checks and .graph-flow/checks.json; use distinct ids)" % check_id)
            if isinstance(check_id, str):
                seen.add(check_id)
            kind = check.get("type")
            text(check, "title", 120, node)
            if kind not in ("cmd", "scope", "cites", "host", "human"):
                problem("V1", node, "unknown check type: %r" % kind)
            if node is not None and kind in ("scope", "cites"):
                if kind in singleton_types:
                    problem("V2", node, "more than one %s check" % kind)
                singleton_types.add(kind)
            if kind == "cmd":
                if "run" not in check:
                    problem("V5", node, "cmd check requires run")
                field(check, "run", str, node)
                field(check, "cwd", str, node, required=False)
                for label in ("from_constraint", "added"):
                    text(check, label, 300, node)
                if isinstance(check.get("cwd"), str):
                    if _bad_path(check["cwd"]):
                        problem("V8", node, "unsafe cwd field: %s" % check["cwd"])
                if "timeout_s" in check and (type(check["timeout_s"]) not in (int, float) or not math.isfinite(check["timeout_s"]) or check["timeout_s"] <= 0):
                    problem("V1", node, "timeout_s must be a finite positive number")
            elif kind == "host":
                field(check, "tool", str, node)
                field(check, "expect", str, node)
            elif kind == "human":
                field(check, "prompt", str, node, required=False)
                context(check, node)

    if not isinstance(plan, dict):
        problem("V1", None, "plan must be an object")
        return problems
    def finite(value):
        if isinstance(value, float) and not math.isfinite(value):
            problem("V1", None, "numbers must be finite")
        elif isinstance(value, dict):
            for item in value.values(): finite(item)
        elif isinstance(value, list):
            for item in value: finite(item)
    finite(plan)
    known(plan, "schema_version goal title summary context requirements tags integration_checks promoted_checks constraints nodes", None)
    if type(plan.get("schema_version")) is not int or plan.get("schema_version") != 1:
        problem("V1", None, "schema_version must be 1")
    field(plan, "goal", str, None)
    text(plan, "title", 80, None)
    text(plan, "summary", 300, None)
    context(plan, None)
    field(plan, "nodes", list, None)
    if isinstance(plan.get("goal"), str) and not plan["goal"]:
        problem("V1", None, "goal must be non-empty")
    if isinstance(plan.get("nodes"), list) and not plan["nodes"]:
        problem("V1", None, "nodes must be non-empty")
    for key in ("requirements", "tags", "integration_checks", "promoted_checks", "constraints"):
        field(plan, key, list, None, required=False)
    for requirement in _list(plan.get("requirements")):
        if not isinstance(requirement, dict):
            problem("V1", None, "requirement must be an object")
        else:
            field(requirement, "id", str, None)
            field(requirement, "text", str, None)
    if any(not isinstance(tag, str) for tag in _list(plan.get("tags"))):
        problem("V1", None, "tags must contain strings")
    run_checks = _list(plan.get("integration_checks")) + _list(plan.get("promoted_checks"))
    checks(run_checks, None)
    for field_name in ("requirements", "constraints"):
        ids = set()
        for item in _list(plan.get(field_name)):
            if not isinstance(item, dict) or not isinstance(item.get("id"), str):
                problem("V2", None, "%s needs unique string ids" % field_name)
                continue
            if item["id"] in ids:
                problem("V2", None, "duplicate %s id: %s" % (field_name, item["id"]))
            ids.add(item["id"])
            known(item, "id text" if field_name == "requirements" else
                  "id text status scope derived_from review_when created", None)
            field(item, "text", str, None)
            if field_name == "constraints" and "status" in item and item["status"] not in ("active", "promoted"):
                problem("V1", None, "plan constraints must be active or promoted; remove retired constraints")
            if field_name == "constraints" and "scope" in item:
                scope = item["scope"]
                field(item, "scope", dict, None)
                if isinstance(scope, dict):
                    known(scope, "paths tags", None)
                    for key in ("paths", "tags"):
                        field(scope, key, list, None, required=False)
                        if any(not isinstance(v, str) for v in _list(scope.get(key))):
                            problem("V1", None, "constraint scope %s must contain strings" % key)
                    paths(scope.get("paths"), None)
    for check in run_checks:
        # The gate executes integration checks itself, so only cmd checks make sense here.
        if isinstance(check, dict) and check.get("type") != "cmd":
            problem("V5", None, "integration checks must be cmd checks")

    seen = set()
    indexed = _index(plan)
    for node in _list(plan.get("nodes")):
        if not isinstance(node, dict):
            problem("V1", None, "node must be an object")
            continue
        node_id = node.get("id") if isinstance(node.get("id"), str) else None
        if node_id is None or not _ID.fullmatch(node_id):
            problem("V2", node_id, "malformed node id: %r" % node.get("id"))
        elif node_id in seen:
            problem("V2", node_id, "duplicate node id: %s" % node_id)
        seen.add(node_id)
        kind_fields = {"work": "context grade max_attempts", "review": "target lens context grade max_attempts", "decision": "question decision_kind context"}
        known(node, "id kind goal title summary needs owns outputs reads checks lane effective_lane requirement " + kind_fields.get(str(node.get("kind")), ""), node_id)
        kind = node.get("kind")
        if kind not in ("work", "review", "decision"):
            problem("V1", node_id, "unknown node kind: %r" % kind)
        field(node, "goal", str, node_id)
        text(node, "title", 60, node_id)
        text(node, "summary", 300, node_id)
        if type(node.get("lane")) is not int or node.get("lane") not in (1, 2, 3):
            problem("V6", node_id, "lane must be 1, 2 or 3")
        if kind != "decision":
            if node.get("grade") not in _GRADES:
                problem("V1", node_id, "grade must be one of %s" % (", ".join(_GRADES)))
        if "max_attempts" in node and (type(node["max_attempts"]) is not int or node["max_attempts"] not in (1, 2, 3)):
            problem("V1", node_id, "max_attempts must be an integer from 1 to 3")
        for key in ("needs", "owns", "outputs", "reads", "checks"):
            field(node, key, list, node_id, required=False)
        for key in ("owns", "outputs", "reads"):
            if any(not isinstance(value, str) for value in _list(node.get(key))):
                problem("V1", node_id, "%s must contain strings" % key)
        paths(node.get("owns"), node_id)
        paths(node.get("reads"), node_id)
        checks(node.get("checks"), node_id)
        allowed_checks = {"work": ("cmd", "scope", "host", "human"),
                          "review": ("cmd", "cites", "host", "human"), "decision": ()}
        for check in _list(node.get("checks")):
            if isinstance(check, dict) and check.get("type") not in allowed_checks.get(str(kind), ()):
                problem("V5", node_id, "checks type %s is not enforced on %s nodes" % (check.get("type"), kind))
        field(node, "requirement", str, node_id, required=False)
        if "context" in node:
            context(node, node_id)
        if kind == "work" and not _list(node.get("checks")):
            # Check the supplied list: normalization must not conceal missing checks.
            problem("V5", node_id, "work node requires a check")
        if kind == "review":
            if type(node.get("lane")) is not int or node.get("lane") != 1:
                problem("V5", node_id, "review node lane must be 1")
            for key in ("target", "lens"):
                if not node.get(key):
                    problem("V5", node_id, "review node requires %s" % key)
                field(node, key, str, node_id)
            target = node.get("target")
            if not isinstance(target, str) or indexed.get(target, {}).get("kind") != "work":
                problem("V5", node_id, "review target must be a work node")
        if kind == "decision":
            context(node, node_id)
            if not node.get("question") or node.get("decision_kind") not in _DECISIONS:
                problem("V5", node_id, "decision requires question and a valid decision_kind")
            field(node, "question", str, node_id)
            if node.get("decision_kind") in ("direction", "information"):
                if any(depends(plan, other, node_id) for other in indexed):
                    problem("V5", node_id, "decision_kind must be review or authorization when other nodes depend on this decision")
                if "if_rejected" in (node.get("context") or {}):
                    problem("V1", node_id, "context.if_rejected is inapplicable to direction/information")
            if _list(node.get("checks")):
                problem("V5", node_id, "decision node must have no checks")
        if kind in ("review", "decision") and _list(node.get("owns")):
            problem("V1", node_id, "%s node must own nothing" % kind)

        need_ids = set()
        for need in _list(node.get("needs")):
            if not isinstance(need, dict):
                problem("V1", node_id, "needs entry must be an object")
                continue
            known(need, "from artifact label", node_id)
            pair = (need.get("from"), need.get("artifact"))
            if all(isinstance(v, str) for v in pair):
                if pair in need_ids:
                    problem("V2", node_id, "duplicate need: %s/%s" % pair)
                need_ids.add(pair)
            field(need, "from", str, node_id)
            field(need, "artifact", str, node_id)
            text(need, "label", 60, node_id)
            producer_id, artifact = need.get("from"), need.get("artifact")
            producer = indexed.get(producer_id) if isinstance(producer_id, str) else None
            if producer is None:
                problem("V3", node_id, "needs producer does not exist: %r" % producer_id)
            if not isinstance(artifact, str) or not artifact:
                problem("V3", node_id, "needs artifact must be nonempty")
            elif producer is not None:
                outputs = _list(producer.get("outputs"))
                if artifact not in outputs:
                    paths([artifact], node_id)
                    if not any(_under(artifact, owner) for owner in _list(producer.get("owns")) if isinstance(owner, str)):
                        problem("V3", node_id, "artifact is not owned or output by producer: %s" % artifact)

    edges = _edges(plan)
    for node_id in indexed:
        if _reaches(edges, node_id, node_id):
            problem("V4", node_id, "dependency cycle includes %s" % node_id)
    nodes = _nodes(plan)
    for i, node in enumerate(nodes):
        for other in nodes[:i]:
            if (overlaps(_list(node.get("owns")), _list(other.get("owns"))) and
                    not (depends(plan, node.get("id"), other.get("id")) or depends(plan, other.get("id"), node.get("id")))):
                problem("V7", node.get("id") if isinstance(node.get("id"), str) else None,
                        "ownership overlaps with %s without a dependency" % other.get("id"))

    normalized, _ = normalize(plan)
    reviewed = {n["target"] for n in nodes if n.get("kind") == "review" and isinstance(n.get("target"), str)}
    for original, node in zip(_nodes(plan), _nodes(normalized)):
        if "effective_lane" in original and original["effective_lane"] != node["effective_lane"]:
            problem("V6", node.get("id"), "effective_lane differs from normalized lane")
        if node.get("kind") == "work" and node.get("effective_lane") in (2, 3):
            node_id = node.get("id")
            if not isinstance(node_id, str) or node_id not in reviewed:
                problem("V9", node_id if isinstance(node_id, str) else None, "work at effective lane 2 or 3 requires a review")
    normalized, _ = normalize(plan)
    for raw, computed in zip(_nodes(plan), _nodes(normalized)):
        if "effective_lane" in raw and raw["effective_lane"] != computed.get("effective_lane"):
            problem("V1", raw.get("id"), "effective_lane must match the lane derived from checks")
    return problems


def node_counts(nodes):
    """The same work/review/decision totals for plan records and every view."""
    return {kind: sum(n.get("kind") == kind for n in nodes)
            for kind in ("work", "review", "decision")}


def check_inputs(check):
    """The entire command execution contract. Environment is inherited, never plan-overridden."""
    return {"run": check["run"], "cwd": check.get("cwd", "."),
            "timeout_s": check.get("timeout_s", 600), "shell": "/bin/sh",
            "environment": "inherited"}


def check_contract(check):
    return dict(check, **check_inputs(check)) if check.get("type") == "cmd" else dict(check)


def node_contract(node):
    contract = copy.deepcopy(node)
    contract["checks"] = [check_contract(c) for c in node.get("checks", [])]
    if node.get("kind") != "decision":
        contract["max_attempts"] = node.get("max_attempts", 3)
    contract["effective_lane"] = node.get("effective_lane", node.get("lane"))
    if node.get("kind") != "decision":
        contract["isolation"] = "shared or worktree, selected at assignment"
        contract["merge"] = "committed submissions must be merged into project HEAD; merge --no-ff"
    return contract
