"""Pure plan validation, normalization and dependency queries."""
import copy
import pathlib
import re

from graphflow import core

_ID = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}")
_GRADES = ("bulk", "scoped", "daily", "large", "security")
_DECISIONS = ("direction", "information", "review", "authorization")


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


def node_by_id(plan, node_id):
    for node in _nodes(plan):
        if node.get("id") == node_id:
            return node
    raise core.GFError("unknown_node", "unknown node: %s" % node_id, core.EXIT_STATE)


def normalize(plan):
    """Copy the plan, fill node defaults and escalate work without a cmd check."""
    result, notices = copy.deepcopy(plan), []
    for node in _nodes(result):
        for field in ("needs", "owns", "outputs", "reads", "checks"):
            node.setdefault(field, [])
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
            check_id = check.get("id")
            if not isinstance(check_id, str) or not _ID.fullmatch(check_id):
                problem("V2", node, "malformed check id: %r" % check_id)
            elif check_id in seen:
                problem("V2", node, "duplicate check id: %s" % check_id)
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
                if not check.get("run"):
                    problem("V5", node, "cmd check requires run")
                field(check, "run", str, node)
                field(check, "cwd", str, node, required=False)
                if isinstance(check.get("cwd"), str):
                    paths([check["cwd"]], node)
                if "timeout_s" in check and (type(check["timeout_s"]) not in (int, float) or check["timeout_s"] <= 0):
                    problem("V1", node, "timeout_s must be a positive number")
            elif kind == "host":
                field(check, "tool", str, node)
                field(check, "expect", str, node)
            elif kind == "human":
                field(check, "prompt", str, node, required=False)
                context(check, node)

    if not isinstance(plan, dict):
        problem("V1", None, "plan must be an object")
        return problems
    if type(plan.get("schema_version")) is not int or plan.get("schema_version") != 1:
        problem("V1", None, "schema_version must be 1")
    field(plan, "goal", str, None)
    text(plan, "title", 80, None)
    field(plan, "nodes", list, None)
    if isinstance(plan.get("goal"), str) and not plan["goal"]:
        problem("V1", None, "goal must be non-empty")
    if isinstance(plan.get("nodes"), list) and not plan["nodes"]:
        problem("V1", None, "nodes must be non-empty")
    for key in ("requirements", "tags", "integration_checks"):
        field(plan, key, list, None, required=False)
    for requirement in _list(plan.get("requirements")):
        if not isinstance(requirement, dict):
            problem("V1", None, "requirement must be an object")
        else:
            field(requirement, "id", str, None)
            field(requirement, "text", str, None)
    if any(not isinstance(tag, str) for tag in _list(plan.get("tags"))):
        problem("V1", None, "tags must contain strings")
    checks(plan.get("integration_checks"), None)
    for check in _list(plan.get("integration_checks")):
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
        kind = node.get("kind")
        if kind not in ("work", "review", "decision"):
            problem("V1", node_id, "unknown node kind: %r" % kind)
        field(node, "goal", str, node_id)
        text(node, "title", 60, node_id)
        text(node, "summary", 300, node_id)
        if type(node.get("lane")) is not int or node.get("lane") not in (1, 2, 3):
            problem("V6", node_id, "lane must be 1, 2 or 3")
        if kind != "decision" or "grade" in node:
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
            if _list(node.get("checks")):
                problem("V5", node_id, "decision node must have no checks")
        if kind in ("review", "decision") and _list(node.get("owns")):
            problem("V1", node_id, "%s node must own nothing" % kind)

        for need in _list(node.get("needs")):
            if not isinstance(need, dict):
                problem("V1", node_id, "needs entry must be an object")
                continue
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
    for node in _nodes(normalized):
        if node.get("kind") == "work" and node.get("effective_lane") in (2, 3):
            node_id = node.get("id")
            if not isinstance(node_id, str) or node_id not in reviewed:
                problem("V9", node_id if isinstance(node_id, str) else None, "work at effective lane 2 or 3 requires a review")
    return problems
