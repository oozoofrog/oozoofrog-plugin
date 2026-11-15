"""Loopback human decision surface (references/dashboard.md)."""
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


def _history(node, st, events):
    """Present current-basis attempts without copying technical rejection records."""
    laps, returned, results, reviews = [], [], {}, {}
    titles = {c["id"]: c.get("title", c["id"]) for c in node["checks"]}
    for event in events:
        if event["seq"] <= st["basis"]:
            continue
        kind, data = event["type"], event["data"]
        if kind == "review.submit" and data.get("target") == node["id"]:
            reviews[data["node"]] = data
        if data.get("node") != node["id"]:
            continue
        if kind == "node.start":
            laps.append("current")
            results = {}
        elif (kind == "check.result" and data.get("phase") == "gate"
              and data.get("attempt") == len(laps)):
            results[data["check"]] = data
        elif kind == "gate.verdict":
            verdict, attempt = data.get("verdict"), data.get("attempt", 0)
            if 1 <= attempt <= len(laps):
                if verdict in ("reject", "replan"):
                    laps[attempt - 1] = "returned"
                elif verdict == "pass":
                    laps[attempt - 1] = "passed"
            if verdict in ("reject", "replan"):
                reasons = [titles.get(cid, cid) for cid, result in results.items()
                           if result.get("result") == "failed"]
                for review in reviews.values():
                    if review.get("target_submission") == data.get("submission"):
                        reasons.extend(f["text"] for f in review.get("findings") or []
                                       if isinstance(f.get("text"), str))
                returned.append(list(dict.fromkeys(reasons)))
            results = {}
    if laps and st["submission"] and st["open_decisions"] and laps[-1] == "current":
        laps[-1] = "waiting_for_you"
    return laps, returned


def _view(current, derived, events, project):
    current = current or {}
    nodes = {n["id"]: n for n in current.get("nodes", [])}
    opened = decisions.open_decisions(derived)
    view = {"title": current.get("title", current.get("goal", "")), "nodes": [],
            "edges": [], "decisions": [], "lessons": [],
            "counts": dict.fromkeys(("done", "doing", "waiting", "needs_you", "returned"), 0),
            "complete": derived["run"]["status"] == "complete"}

    def title(nid):
        return nodes.get(nid, {}).get("title", nid)

    gates = {}
    for nid, node in nodes.items():
        st = derived["nodes"][nid]
        laps, reasons = _history(node, st, events)
        passed = st["status"] == "passed"
        gates[nid] = ("open" if passed else "returned" if reasons else
                      "waiting_for_you" if st["open_decisions"] else "closed")
        family = (st["assignment"] or {}).get("family")
        submission = (st["submission"] or {}).get("id")
        reviewed = any(family and r["family"] and family != r["family"]
                       and r["status"] == "passed" and submission is not None
                       and r["target_submission"] == submission for r in st["reviews"])
        view["nodes"].append({"id": nid, "title": title(nid),
                              "summary": node.get("summary", node["goal"]),
                              "kind": node["kind"], "status": st["status"],
                              "attempts": st["attempts"], "max_attempts": st["max_attempts"],
                              "lane": st["effective_lane"], "laps": laps,
                              "returned_reasons": reasons, "reviewed_by_other_family": reviewed})
        if passed:
            view["counts"]["done"] += 1
        elif not st["open_decisions"]:
            bucket = "doing" if st["status"] in ("running", "submitted", "unverified") else "waiting"
            view["counts"][bucket] += 1
        view["counts"]["returned"] += int(bool(reasons) and not passed)

    for nid, node in nodes.items():
        edges = [(need["from"], need.get("label", need["artifact"])) for need in node["needs"]]
        if node["kind"] == "review":
            edges.append((node["target"], ""))
        for producer, label in edges:
            view["edges"].append({"from": producer, "to": nid, "label": label,
                                  "delivered": gates[producer] == "open", "gate": gates[producer]})

    for decision in opened:
        node = nodes.get(decision["node"], {})
        context = node.get("context", {}) if node.get("kind") == "decision" else {}
        if node.get("kind") != "decision":
            context = next((c.get("context", {}) for c in node.get("checks", [])
                            if c["id"] == decision["check"] and c["type"] == "human"), {})
        evidence = decision.get("evidence") or {}
        view["decisions"].append({"id": decision["id"], "node": decision["node"],
                                  "node_title": title(decision["node"]),
                                  "question": decision["question"], "kind": decision["kind"],
                                  "context": context,
                                  "has_evidence": any(evidence.get(k) for k in ("command", "files", "checks"))})
    view["counts"]["needs_you"] = len(opened)

    # Absent learning files mean no lessons, without creating a project lock on GET.
    if (pathlib.Path(project) / ".graph-flow" / "constraints.jsonl").is_file():
        for constraint in learn.all_constraints(project):
            if constraint["status"] != "active":
                continue
            source = constraint["derived_from"]
            node_title = None
            if source.get("run") == derived["run"]["id"] and source.get("node") in nodes:
                node_title = title(source["node"])
            view["lessons"].append({"text": constraint["text"], "node_title": node_title})
    return view


def _evidence(run_dir, relative):
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

        def log_message(self, *args):
            pass  # URLs can contain the token.

        def _send(self, status, body, content_type, nonce=None):
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
                                 "default-src 'none'; script-src 'nonce-%s'; style-src 'nonce-%s'; "
                                 "connect-src 'self'; img-src data:; base-uri 'none'; form-action 'none'"
                                 % (nonce, nonce))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(data)

        def _json(self, status, value):
            self._send(status, json.dumps(value), "application/json; charset=utf-8")

        def _error(self, status, code, message):
            self._json(status, {"ok": False, "code": code, "message": message})

        def send_error(self, code, message=None, explain=None):
            self._error(code, "bad_request", message or "invalid HTTP request")

        def _authorize(self):
            port = self.server.server_address[1]
            hosts = self.headers.get_all("Host", [])
            if len(hosts) != 1 or hosts[0] not in ("127.0.0.1:%s" % port, "localhost:%s" % port):
                raise _HTTPError(403, "bad_host", "Host must name this loopback server")
            parsed = urlsplit(self.path)
            query = parse_qs(parsed.query, keep_blank_values=True)
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
            if path in ("/api/run", "/api/evidence"):
                run = _run(query.get("project", [None])[0], query.get("run", [None])[0])
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
