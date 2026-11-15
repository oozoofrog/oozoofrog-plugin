"""Loopback human decision surface (references/dashboard.md)."""
import codecs
import hmac
import json
import os
import pathlib
import re
import secrets
import stat
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from . import core, decisions, graph, learn, state, store, trace

PAGE_PATH = pathlib.Path(__file__).with_name("page.html")
STATIC_TYPES = {name: "text/javascript; charset=utf-8" for name in
                ("page.js", "vendor/three.module.min.js", "vendor/CSS2DRenderer.js")}
STATIC_TYPES.update({"assets/frog-%s.png" % pose: "image/png" for pose in
                     ("wave", "walk-a", "walk-b", "report")})
STATIC_ROOT = pathlib.Path(__file__).parent
MAX_BODY = 64 * 1024
MAX_EVIDENCE = 200 * 1024
RUN_ID = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}")
HUMAN = {"role": "human", "node": None, "session": "dashboard"}


class _HTTPError(Exception):
    def __init__(self, status, code, message):
        self.status, self.code, self.message = status, code, message


def _projects():
    path = core.gf_home() / "registry.json"
    if not path.exists():
        return []
    registry = json.loads(path.read_text(encoding="utf-8"))
    return [entry["root"] for entry in registry["projects"]]


def _runs(root):
    root = pathlib.Path(root)
    if not root.is_dir():
        raise OSError("project directory is missing: %s" % root)
    directory = root / ".graph-flow" / "runs"
    if not directory.exists():
        return []
    return sorted((p for p in directory.iterdir()
                   if RUN_ID.fullmatch(p.name) and p.is_dir()), key=lambda p: p.name)


def _snapshot(run_dir):
    # Read-only transactions take the existing run lock without appending events.
    with store.transaction(run_dir) as tx:
        return tx.plan, tx.events, state.derive(tx.plan, tx.events)


def _run(project, run):
    if not isinstance(project, str) or project not in _projects():
        raise _HTTPError(404, "unknown_project", "project is not registered")
    if not isinstance(run, str) or not RUN_ID.fullmatch(run):
        raise _HTTPError(404, "unknown_run", "unknown run")
    directory = pathlib.Path(project) / ".graph-flow" / "runs"
    target = directory / run
    try:
        target.resolve().relative_to(directory.resolve())
    except ValueError:
        raise _HTTPError(404, "unknown_run", "unknown run")
    if not target.is_dir() or not (target / "events.jsonl").is_file():
        raise _HTTPError(404, "unknown_run", "unknown run")
    return target


def _project_list():
    projects = []
    for root in _projects():
        entry = {"root": root, "name": pathlib.Path(root).name, "runs": []}
        projects.append(entry)
        try:
            for run in _runs(root):
                item = {"id": run.name}
                entry["runs"].append(item)
                try:
                    _, events, derived = _snapshot(run)
                    nodes = derived["nodes"].values()
                    item.update(status=derived["run"]["status"], nodes=len(derived["nodes"]),
                                passed=sum(n["status"] == "passed" for n in nodes),
                                open_decisions=len(decisions.open_decisions(derived)),
                                last_event=events[-1]["ts"] if events else None)
                except Exception as exc:
                    item["error"] = str(exc)
        except Exception as exc:
            entry["error"] = str(exc)
    return {"projects": projects}


def _queue():
    queue = []
    for root in _projects():
        try:
            runs = _runs(root)
        except OSError:
            continue
        for run in runs:
            try:
                _, events, derived = _snapshot(run)
                asked = {e["seq"]: e["ts"] for e in events if e["type"] == "decision.ask"}
                for decision in decisions.open_decisions(derived):
                    node = derived["nodes"].get(decision["node"]) or {}
                    checks = []
                    for check, phases in node.get("checks", {}).items():
                        for phase in ("gate", "loop"):
                            result = phases.get(phase)
                            if result is not None and result.get("attempt") == node["attempts"]:
                                row = {key: result.get(key) for key in
                                       ("result", "exit_code", "command", "log")}
                                checks.append(dict(row, check=check, phase=phase))
                    item = {key: decision[key] for key in
                            ("id", "node", "kind", "purpose", "question", "evidence")}
                    item.update(project=root, run=run.name, asked=asked[decision["seq"]],
                                node_state={key: node.get(key) for key in
                                            ("status", "attempts", "lane", "effective_lane")},
                                checks=checks,
                                changed_files=(node.get("submission") or {}).get("changed_files") or [])
                    queue.append(item)
            except Exception:
                # /api/projects exposes unreadable runs; other projects remain usable.
                continue
    queue.sort(key=lambda item: item["asked"])
    return {"queue": queue}


def _text(value, fallback=""):
    return value if isinstance(value, str) and value.strip() else fallback


def _objects(value):
    return [v for v in value if isinstance(v, dict)] if isinstance(value, list) else []


def _mapping(value):
    return value if isinstance(value, dict) else {}


def _strings(value):
    # Older submissions sometimes used a single uncertainty string.
    values = [value] if isinstance(value, str) else value if isinstance(value, list) else []
    return [v for v in values if isinstance(v, str) and v.strip()]


def _finding_text(review):
    return [_text(f.get("text")) for f in _objects(review.get("findings"))
            if _text(f.get("text"))]


def _attempt_results(nid, st, events):
    """All observations used by trajectory_clean, including superseded failures."""
    results = []
    for event in events:
        if event["seq"] <= st.get("basis", 0):
            continue
        data = _mapping(event.get("data"))
        if data.get("node") != nid:
            continue
        if event["type"] == "node.start":
            results = []
        elif (event["type"] == "check.result" and isinstance(data.get("check"), str)
              and data.get("attempt") == st.get("attempts")):
            results.append(data)
    return results


def _trajectory_reasons(st, results):
    reasons = []
    if type(st.get("attempts")) is int and st["attempts"] > 2:
        reasons.append("used_all_attempts")
    if any(r.get("timed_out") is True for r in results):
        reasons.append("timed_out")
    if any(r.get("phase") == "loop" and r.get("type") == "scope"
           and r.get("violations") for r in results):
        reasons.append("left_its_files")
    return reasons


def _history(node, st, events):
    """Present current-basis attempts without copying technical rejection records."""
    laps, returned, results, reviews = [], [], {}, {}
    titles = {c["id"]: _text(c.get("title")) for c in _objects(node.get("checks"))
              if isinstance(c.get("id"), str)}
    for event in events:
        if event["seq"] <= st["basis"]:
            continue
        kind, data = event["type"], _mapping(event.get("data"))
        if (kind == "review.submit" and data.get("target") == node["id"]
                and isinstance(data.get("node"), str)):
            reviews[data["node"]] = data
        if data.get("node") != node["id"]:
            continue
        if kind == "node.start":
            laps.append("current")
            results = {}
        elif (kind == "check.result" and data.get("phase") == "gate"
              and data.get("attempt") == len(laps) and isinstance(data.get("check"), str)):
            results[data["check"]] = data
        elif kind == "gate.verdict":
            verdict, attempt = data.get("verdict"), data.get("attempt", 0)
            if type(attempt) is int and 1 <= attempt <= len(laps):
                if verdict in ("reject", "replan"):
                    laps[attempt - 1] = "returned"
                elif verdict == "pass":
                    laps[attempt - 1] = "passed"
            if verdict in ("reject", "replan"):
                reasons = [titles[cid] for cid, result in results.items()
                           if titles.get(cid) and result.get("result") == "failed"]
                for review in reviews.values():
                    if review.get("target_submission") == data.get("submission"):
                        reasons.extend(_finding_text(review))
                returned.append(list(dict.fromkeys(reasons)))
            results = {}
    if laps and st["submission"] and st["open_decisions"] and laps[-1] == "current":
        laps[-1] = "waiting_for_you"
    return laps, returned


def _view(current, derived, events, project):
    current = current or {}
    nodes = {n["id"]: n for n in current.get("nodes", [])}
    opened = decisions.open_decisions(derived)
    view = {"title": _text(current.get("title"), _text(current.get("goal"))), "nodes": [],
            "language": "ko" if re.search(r"[\u1100-\u11ff\u3130-\u318f\uac00-\ud7af]",
                " ".join([_text(current.get("title"))] +
                         [_text(n.get(k)) for n in nodes.values() for k in ("title", "summary")])) else "en",
            "edges": [], "decisions": [], "lessons": [],
            "counts": dict.fromkeys(("done", "doing", "waiting", "needs_you", "returned", "returns_total"), 0),
            "complete": derived["run"]["status"] == "complete"}

    def title(nid):
        return _text(nodes.get(nid, {}).get("title"), nid)

    gates = {}
    for nid, node in nodes.items():
        st = derived["nodes"][nid]
        laps, reasons = _history(node, st, events)
        passed = st["status"] == "passed"
        gates[nid] = ("open" if passed else "returned" if reasons else
                      "waiting_for_you" if st["open_decisions"] else "closed")
        family = _mapping(st["assignment"]).get("family")
        submission = _mapping(st["submission"]).get("id")
        reviewed = any(isinstance(family, str) and isinstance(r.get("family"), str)
                       and family and r["family"] and family != r["family"]
                       and r.get("status") == "passed" and submission is not None
                       and r.get("target_submission") == submission for r in _objects(st["reviews"]))
        view["nodes"].append({"id": nid, "title": title(nid),
                              "summary": _text(node.get("summary"), _text(node.get("goal"))),
                              "kind": node["kind"], "target": node.get("target"), "status": st["status"],
                              "answered": node["kind"] == "decision" and any(
                                  d.get("node") == nid and d.get("status") == "answered" and not d.get("stale")
                                  for d in derived["decisions"].values()),
                              "attempts": st["attempts"], "max_attempts": st["max_attempts"],
                              "lane": st["effective_lane"], "laps": laps,
                              "returned_reasons": reasons, "reviewed_by_other_family": bool(reviewed),
                              "inputs": [], "outputs": []})
        if passed:
            view["counts"]["done"] += 1
        elif not st["open_decisions"]:
            bucket = "doing" if st["status"] in ("running", "submitted", "unverified") else "waiting"
            view["counts"][bucket] += 1
        view["counts"]["returned"] += int(bool(reasons) and not passed)
        view["counts"]["returns_total"] += laps.count("returned")

    for nid, node in nodes.items():
        edges = [(need["from"], _text(need.get("label"), _text(need.get("artifact"))))
                 for need in _objects(node.get("needs"))]
        if node["kind"] == "review":
            edges.append((node["target"], ""))
        for producer, label in edges:
            view["edges"].append({"from": producer, "to": nid, "label": label,
                                  "delivered": gates[producer] == "open", "gate": gates[producer]})

    presented = {n["id"]: n for n in view["nodes"]}
    for edge in view["edges"]:
        presented[edge["to"]]["inputs"].append({"label": edge["label"],
            "other_title": title(edge["from"]), "delivered": edge["delivered"]})
        presented[edge["from"]]["outputs"].append({"label": edge["label"],
            "other_title": title(edge["to"]), "delivered": edge["delivered"]})

    for decision in opened:
        node = nodes.get(decision["node"], {})
        checks = _objects(node.get("checks"))
        context = node.get("context", {}) if node.get("kind") == "decision" else {}
        if node.get("kind") != "decision":
            context = next((c.get("context") for c in checks
                            if c.get("id") == decision["check"] and c.get("type") == "human"), {})
        context = {k: v for k, v in _mapping(context).items()
                   if k in ("why", "if_approved", "if_rejected", "undo") and _text(v)}
        evidence = _mapping(decision.get("evidence"))
        st = derived["nodes"].get(decision["node"]) or {}
        submission = _mapping(st.get("submission"))
        verified, unverified, failed = [], [], []
        observations = _attempt_results(decision["node"], st, events)
        latest = {r["check"]: r for r in observations if r.get("phase") in ("loop", "gate")}
        check_titles = {c["id"]: _text(c.get("title")) for c in checks if isinstance(c.get("id"), str)}
        for result in latest.values():
            wording = check_titles.get(result["check"])
            if result.get("result") == "failed":
                failed.append(wording or "A check without a description did not pass.")
            elif result.get("result") == "passed" and wording:
                verified.append(wording)
        for check in checks:
            if check.get("type") == "human":
                wording = _text(check.get("title"), _text(check.get("prompt")))
                if wording:
                    unverified.append(wording)
        for review in _objects(st.get("reviews")):
            if (submission.get("id") is not None and review.get("target_submission") == submission["id"]
                    and review.get("verdict") == "fail"):
                failed.extend(_finding_text(review))
        unverified.extend(_strings(submission.get("low_confidence")))
        view["decisions"].append({"id": decision["id"], "node": decision["node"],
                                  "node_title": title(decision["node"]),
                                  "question": _text(decision.get("question")), "kind": _text(decision.get("kind")),
                                  "purpose": (_text(decision.get("kind")) if decision.get("purpose") in (None, "node", "free")
                                              else _text(decision.get("purpose"))),
                                  "record_purpose": _text(decision.get("purpose")),
                                  "files": _decision_files(decision, derived, project),
                                  "context": context, "verified": verified, "unverified": unverified,
                                  "failed": failed, "trajectory_reasons": _trajectory_reasons(st, observations),
                                  "worker_note": _text(submission.get("notes"), None),
                                  "has_evidence": any(evidence.get(k) for k in ("command", "files", "checks"))})
    view["counts"]["needs_you"] = len(opened)

    # A malformed learning record must not make the run itself unreadable.
    if (pathlib.Path(project) / ".graph-flow" / "constraints.jsonl").is_file():
        try:
            constraints = learn.all_constraints(project)
        except core.GFError:
            constraints = []
        for constraint in _objects(constraints):
            if constraint.get("status") != "active" or not _text(constraint.get("text")):
                continue
            source = _mapping(constraint.get("derived_from"))
            node_title = None
            if (source.get("run") == derived["run"]["id"]
                    and isinstance(source.get("node"), str) and source["node"] in nodes):
                node_title = title(source["node"])
            view["lessons"].append({"text": constraint["text"], "node_title": node_title})
    return view


def _file_path(project, relative):
    # Validate the recorded spelling as well as the resolved destination.
    path = pathlib.PurePosixPath(relative)
    private = {".git", ".graph-flow"}
    secrets = {"human.key", "server.json", "registry.json"}
    if (not relative or "\x00" in relative or "\\" in relative or path.is_absolute()
            or ".." in path.parts or private.intersection(path.parts) or path.name in secrets):
        raise _HTTPError(403, "forbidden_path", "this file cannot be opened")
    root = pathlib.Path(project).resolve()
    try:
        target = (root / relative).resolve()
        parts = target.relative_to(root).parts
    except (ValueError, OSError, RuntimeError):
        raise _HTTPError(403, "forbidden_path", "this file cannot be opened")
    if private.intersection(parts) or target.name in secrets:
        raise _HTTPError(403, "forbidden_path", "this file cannot be opened")
    return target


def _decision_files(decision, derived, project):
    st = derived["nodes"].get(decision.get("node")) or {}
    paths = _strings(_mapping(st.get("submission")).get("changed_files"))
    paths += _strings(_mapping(decision.get("evidence")).get("files"))
    files = []
    for path in dict.fromkeys(paths):
        try:
            _file_path(project, path)
        except _HTTPError:
            continue
        files.append({"name": pathlib.PurePosixPath(path).name, "path": path})
    return files


def _open_project_file(project, target):
    # Walk the resolved path without following replacements between resolve and open.
    parts = target.relative_to(pathlib.Path(project).resolve()).parts
    directory = os.open(str(project), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory)
            directory = child
        return os.open(parts[-1] if parts else ".", os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW,
                       dir_fd=directory)
    finally:
        os.close(directory)


def _file(run_dir, decision_id, relative):
    project = store.project_of(run_dir)
    with store.locked(run_dir / ".lock"):
        derived = state.derive(store.read_plan(run_dir), store.events(run_dir))
        decision = derived["decisions"].get(decision_id)
        if decision is None:
            raise _HTTPError(404, "unknown_decision", "this decision is unavailable")
        if decision["status"] != "open" or decision["stale"]:
            raise _HTTPError(403, "unavailable_decision", "this decision is no longer open")
        target = _file_path(project, relative)
        if relative not in [f["path"] for f in _decision_files(decision, derived, project)]:
            raise _HTTPError(403, "forbidden_path", "this file is not part of this decision")
        try:
            fd = _open_project_file(project, target)
            with os.fdopen(fd, "rb") as stream:
                info = os.fstat(stream.fileno())
                if not stat.S_ISREG(info.st_mode):
                    raise _HTTPError(404, "unknown_file", "this is not a readable text file")
                # Also refuse renamed hard links to the dashboard's private records.
                for name in ("human.key", "server.json", "registry.json"):
                    secret = core.gf_home() / name
                    if secret.exists() and os.path.samestat(info, secret.stat()):
                        raise _HTTPError(403, "forbidden_path", "this file cannot be opened")
                decoder = codecs.getincrementaldecoder("utf-8")("strict")
                raw, size = bytearray(), 0
                while True:
                    chunk = stream.read(64 * 1024)
                    if not chunk:
                        decoder.decode(b"", final=True)
                        break
                    if b"\x00" in chunk:
                        raise UnicodeError("binary")
                    decoder.decode(chunk)
                    size += len(chunk)
                    raw.extend(chunk[:max(0, MAX_EVIDENCE - len(raw))])
        except (OSError, UnicodeError):
            raise _HTTPError(404, "unknown_file", "this is not a readable UTF-8 text file")
        if size > MAX_EVIDENCE:
            marker = b"\n[truncated]\n"
            return bytes(raw[:MAX_EVIDENCE - len(marker)]).decode("utf-8", errors="ignore").encode("utf-8") + marker
        return bytes(raw)


def _evidence(run_dir, relative):
    if "\x00" in relative:
        raise _HTTPError(404, "unknown_evidence", "evidence file is unavailable")
    path = pathlib.Path(relative)
    evidence = (run_dir / "evidence").resolve()
    target = (run_dir / path).resolve()
    try:
        evidence.relative_to(run_dir.resolve())
        target.relative_to(evidence)
    except ValueError:
        raise _HTTPError(403, "forbidden_path", "path must stay inside this run's evidence directory")
    if path.is_absolute():
        raise _HTTPError(403, "forbidden_path", "path must be relative to the run")
    try:
        fd = os.open(str(target), os.O_RDONLY | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise _HTTPError(404, "unknown_evidence", "evidence is not a regular file")
            raw = stream.read(MAX_EVIDENCE + 1)
    except OSError:
        raise _HTTPError(404, "unknown_evidence", "evidence file is unavailable")
    text = raw.decode("utf-8", errors="replace").encode("utf-8")
    if len(raw) > MAX_EVIDENCE or len(text) > MAX_EVIDENCE:
        marker = b"\n[truncated]\n"
        text = text[:MAX_EVIDENCE - len(marker)].decode("utf-8", errors="ignore").encode("utf-8") + marker
    return text


def _handler(token):
    class Handler(BaseHTTPRequestHandler):
        server_version = "graph-flow"
        sys_version = ""
        timeout = 30  # an unfinished request must not hold a thread forever

        def log_message(self, *args):
            pass  # URLs can contain the token.

        def _send(self, status, body, content_type, nonce=None, recovery=False):
            data = body.encode("utf-8") if isinstance(body, str) else body
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            if nonce is not None:
                self.send_header("Content-Security-Policy",
                                 ("default-src 'none'; script-src 'nonce-%s'; base-uri 'none'; form-action 'none'" % nonce)
                                 if recovery else
                                 "default-src 'none'; script-src 'nonce-%s' 'self'; style-src 'nonce-%s'; "
                                 "connect-src 'self'; img-src 'self' data: blob:; base-uri 'none'; form-action 'none'"
                                 % (nonce, nonce))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(data)

        def _json(self, status, value):
            self._send(status, json.dumps(value), "application/json; charset=utf-8")

        def _error(self, status, code, message):
            self._json(status, {"ok": False, "code": code, "message": message})

        def _reload_page(self):
            nonce = secrets.token_urlsafe(24)
            page = '''<!doctype html><html lang="en"><meta charset="utf-8">
<title>Graph flow</title><p id="message">Open the address printed by gf serve.</p>
<script nonce="__NONCE__">
if (navigator.language.toLowerCase().startsWith('ko')) {
  document.getElementById('message').textContent = 'gf serve를 켤 때 나온 주소를 열어 주세요.';
}
try {
  const token = sessionStorage.getItem('graph-flow-token:' + location.port);
  if (token && !new URL(location.href).searchParams.has('t')) location.replace('/?t=' + encodeURIComponent(token));
} catch { /* The printed address also works when storage is unavailable. */ }
</script></html>'''
            return self._send(401, page.replace("__NONCE__", nonce), "text/html; charset=utf-8", nonce, recovery=True)

        def send_error(self, code, message=None, explain=None):
            self._error(code, "bad_request", message or "invalid HTTP request")

        def _authorize(self):
            port = self.server.server_address[1]
            hosts = self.headers.get_all("Host", [])
            if len(hosts) != 1 or hosts[0] not in ("127.0.0.1:%s" % port, "localhost:%s" % port):
                raise _HTTPError(403, "bad_host", "Host must name this loopback server")
            parsed = urlsplit(self.path)
            query = parse_qs(parsed.query, keep_blank_values=True)
            if self.command == "GET" and parsed.path.startswith("/static/"):
                return parsed.path, query
            supplied = self.headers.get_all("X-GF-Token", [])
            if not supplied and self.command == "GET":
                supplied = query.get("t", [])
            if len(supplied) != 1 or not hmac.compare_digest(
                    supplied[0].encode("utf-8"), token.encode("ascii")):
                raise _HTTPError(401, "unauthorized", "a valid X-GF-Token is required")
            return parsed.path, query

        def _body(self):
            lengths = self.headers.get_all("Content-Length", [])
            if self.headers.get("Transfer-Encoding") or len(lengths) != 1:
                raise _HTTPError(400, "bad_body", "one Content-Length is required")
            try:
                length = int(lengths[0])
            except ValueError:
                raise _HTTPError(400, "bad_body", "invalid Content-Length")
            if length > MAX_BODY:
                raise _HTTPError(413, "body_too_large", "JSON body exceeds 64 KB")
            if length <= 0:
                raise _HTTPError(400, "bad_body", "a JSON body is required")
            try:
                body = json.loads(self.rfile.read(length).decode("utf-8"))
            except (ValueError, UnicodeError):
                raise _HTTPError(400, "bad_body", "body must be UTF-8 JSON")
            if not isinstance(body, dict):
                raise _HTTPError(400, "bad_body", "body must be a JSON object")
            return body

        def _dispatch(self):
            path, query = self._authorize()
            if self.command not in ("GET", "POST"):
                raise _HTTPError(405, "method_not_allowed", "only GET and POST are supported")
            if self.command == "POST":
                body = self._body()
                if path != "/api/answer":
                    raise _HTTPError(404, "not_found", "unknown route")
                for key in ("project", "run", "id", "outcome", "answer"):
                    if not isinstance(body.get(key), str):
                        raise _HTTPError(400, "bad_input", "%s must be a string" % key)
                    try:
                        body[key].encode("utf-8")
                    except UnicodeError:
                        raise _HTTPError(400, "bad_input", "%s must be valid Unicode" % key)
                run = _run(body["project"], body["run"])
                answer = decisions.answer(run, body["id"], body["outcome"], body["answer"], "dashboard", HUMAN)
                return self._json(200, {"ok": True, "decision": answer})
            if path.startswith("/static/"):
                name = path[len("/static/"):]
                if name not in STATIC_TYPES:
                    raise _HTTPError(404, "not_found", "unknown static file")
                try:
                    content = (STATIC_ROOT / name).read_bytes()
                except OSError:
                    raise _HTTPError(404, "not_found", "static file is unavailable")
                return self._send(200, content, STATIC_TYPES[name])
            if path == "/":
                nonce = secrets.token_urlsafe(24)
                try:
                    page = PAGE_PATH.read_text(encoding="utf-8")
                except FileNotFoundError:
                    page = "<!doctype html><html lang=\"en\"><title>Graph flow</title><p>The page is not installed.</p></html>"
                return self._send(200, page.replace("__NONCE__", nonce), "text/html; charset=utf-8", nonce)
            if path == "/api/projects":
                return self._json(200, _project_list())
            if path == "/api/queue":
                return self._json(200, _queue())
            if path in ("/api/run", "/api/evidence", "/api/file"):
                run = _run(query.get("project", [None])[0], query.get("run", [None])[0])
                if path == "/api/file":
                    return self._send(200, _file(run, query.get("decision", [""])[0],
                                      query.get("path", [""])[0]), "text/plain; charset=utf-8")
                if path == "/api/evidence":
                    return self._send(200, _evidence(run, query.get("path", [""])[0]), "text/plain; charset=utf-8")
                with store.locked(run / ".lock"):
                    current = store.read_plan(run)
                    events = store.events(run)
                    derived = state.derive(current, events)
                    result = {"plan": current, "state": derived,
                              "ready": graph.ready(current or {}, derived), "trace": trace.trace(run),
                              "view": _view(current, derived, events, store.project_of(run))}
                return self._json(200, result)
            raise _HTTPError(404, "not_found", "unknown route")

        def _handle(self):
            try:
                self._dispatch()
            except _HTTPError as exc:
                if exc.status == 401 and self.command == "GET" and urlsplit(self.path).path == "/":
                    self._reload_page()
                else:
                    self._error(exc.status, exc.code, exc.message)
            except core.GFError as exc:
                status = 409 if exc.code in ("stale_decision", "already_answered", "unknown_decision") else 400
                self._error(status, exc.code, exc.message)
            except Exception:
                self._error(500, "internal", "internal server error")

        do_GET = do_POST = _handle

        def __getattr__(self, name):
            if name.startswith("do_"):
                return self._handle
            raise AttributeError(name)

    return Handler


def make_server(port=0):
    """Bind loopback without blocking or publishing server.json; caller closes it."""
    token = secrets.token_urlsafe(32)
    httpd = ThreadingHTTPServer(("127.0.0.1", port), _handler(token))
    httpd.daemon_threads = True
    return httpd, token


def serve(host="127.0.0.1", port=0):
    """Publish a person-started dashboard and serve until interrupted."""
    if host not in ("127.0.0.1", "localhost"):
        raise core.GFError("bad_host", "dashboard must bind 127.0.0.1 or localhost", core.EXIT_USAGE)
    decisions.ensure_key()
    httpd, token = make_server(port)
    home = core.gf_home()
    path = home / "server.json"
    pid = os.getpid()
    port = httpd.server_address[1]
    url = "http://127.0.0.1:%s/?t=%s" % (port, token)
    try:
        with store.locked(home / ".lock"):
            store.atomic_write(path, json.dumps({"url": url, "port": port, "token": token,
                                                "pid": pid, "started": core.now()}) + "\n")
        print(json.dumps({"ok": True, "url": url, "port": port}), flush=True)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
    finally:
        httpd.server_close()
        with store.locked(home / ".lock"):
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                record = None
            if isinstance(record, dict) and record.get("pid") == pid:
                path.unlink()
