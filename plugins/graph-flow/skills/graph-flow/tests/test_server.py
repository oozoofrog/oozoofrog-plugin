"""Dashboard contract against real runs, checks, gates and signed human answers."""
import contextlib
import hashlib
import http.client
import io
import json
import os
import pathlib
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest import mock
from urllib.parse import urlencode

SCRIPTS = pathlib.Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
from graphflow import assign, checks, core, decisions, gate, learn, plan, server, state, store

from human_support import recorded_question, legacy_run, approve_current_plan

ACTOR = {"role": "leader", "node": None, "session": "server-test"}
REVIEWER = {"role": "reviewer", "node": "review", "session": "review-test"}
CMD = {"id": "unit", "type": "cmd", "run": "printf checked"}


class ServerTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = pathlib.Path(temporary.name).resolve()
        self.home = self.root / "home"
        env = mock.patch.dict(os.environ, {"GF_HOME": str(self.home)})
        env.start()
        self.addCleanup(env.stop)
        decisions.ensure_key({'role': 'human'})
        self.projects, self.runs, self.asks = [], [], []
        for index in range(2):
            root = self.root / ("project%d" % index)
            root.mkdir()
            self.git(root, "init", "-q")
            self.git(root, "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                     "-c", "commit.gpgsign=false", "commit", "-q", "--allow-empty", "-m", "initial")
            run = legacy_run(root, "run%d" % index, ACTOR)
            raw = {"schema_version": 1, "goal": "server test", "nodes": [
                {"id": "build", "kind": "work", "goal": "build", "owns": ["built.txt"],
                 "lane": 3, "grade": "scoped", "checks": [dict(CMD)]},
                {"id": "review", "kind": "review", "goal": "review", "target": "build",
                 "lens": "correctness", "lane": 1, "grade": "daily", "owns": [],
                 "needs": [{"from": "build", "artifact": "built.txt"}],
                 "checks": [{"id": "cites", "type": "cites"}]}]}
            self.assertEqual(plan.validate(raw), [])
            normalized, _ = plan.normalize(raw)
            with store.transaction(run) as tx:
                revision, sha = tx.write_plan(normalized)
                tx.append("plan.set", {"revision": revision, "plan_sha256": sha,
                          "fingerprints": {n["id"]: state.fingerprint(n) for n in normalized["nodes"]},
                          "constraints_applied": []}, ACTOR)
            approve_current_plan(run)
            assign.assign(run, "build", "subagent", "test", "high", "test", "openai", "shared", ACTOR)
            assign.assign(run, "review", "subagent", "test", "high", "test", "claude", "shared", ACTOR)
            with contextlib.redirect_stderr(io.StringIO()):
                checks.start(run, "build", None, ACTOR)
                (root / "built.txt").write_text("built\n", encoding="utf-8")
                checks.run_cmd(run, "build", CMD, "loop", None, ACTOR)
                checks.submit(run, "build", None, None, "done", [], None, ACTOR)
                checks.start(run, "review", None, REVIEWER)
                checks.review_submit(run, "review", "pass", [], REVIEWER)
                self.assertEqual(gate.gate(run, "review", None, ACTOR)["verdict"], "pass")
                # Deliberately reverse chronological order across the registry's projects.
                with mock.patch.object(store, "now", return_value="2026-01-0%dT00:00:00Z" % (2 - index)):
                    outcome = gate.gate(run, "build", None, ACTOR)
            self.assertEqual(outcome["verdict"], "needs_approval")
            self.projects.append(root)
            self.runs.append(run)
            self.asks.append(outcome["asks"][0])
        self.httpd, self.token = server.make_server()
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever,
                                       kwargs={"poll_interval": 0.01}, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_server)

    def stop_server(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(5)
        self.assertFalse(self.thread.is_alive())

    def git(self, root, *args):
        return subprocess.run(["git", "-C", str(root)] + list(args), check=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def request(self, method, path, body=None, headers=None, token=True):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        merged = {"X-GF-Token": self.token} if token else {}
        merged.update(headers or {})
        if body is not None and not isinstance(body, bytes):
            body = json.dumps(body).encode("utf-8")
        try:
            connection.request(method, path, body=body, headers=merged)
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def api(self, route, index=0, **query):
        return route + "?" + urlencode(dict(project=str(self.projects[index]),
                                           run=self.runs[index].name, **query))

    def answer_body(self, index=0, **changes):
        body = {"project": str(self.projects[index]), "run": self.runs[index].name,
                "id": self.asks[index], "outcome": "approved", "answer": "Yes ✓"}
        body.update(changes)
        d=state.derive(store.read_plan(self.runs[index]),store.events(self.runs[index]))["decisions"].get(body["id"]) if isinstance(body["id"],str) else None
        body["displayed"]=state.decision_identity(d) if d else {}
        return body

    def json_request(self, method, path, **kwargs):
        status, headers, payload = self.request(method, path, **kwargs)
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertTrue(headers["Content-Type"].startswith("application/json"))
        return status, json.loads(payload)

    def assert_error(self, status, code, method, path, **kwargs):
        actual, body = self.json_request(method, path, **kwargs)
        self.assertEqual(actual, status, body)
        self.assertEqual(set(body), {"ok", "code", "message"})
        self.assertEqual((body["ok"], body["code"]), (False, code))

    def test_host_and_token_for_every_route(self):
        routes = ["/", "/api/projects", "/api/queue", self.api("/api/run"),
                  self.api("/api/evidence", path="evidence/missing"),
                  self.api("/api/file", decision=self.asks[0], path="built.txt"), "/not-found"]
        for path in routes:
            for method in ("GET", "POST"):
                with self.subTest(path=path, method=method):
                    kw = {"body": self.answer_body()} if method == "POST" else {}
                    if path == "/" and method == "GET":
                        self.assertEqual(self.request(method, path, token=False)[0], 401)
                        self.assertEqual(self.request(method, path, headers={"X-GF-Token": "wrong"})[0], 401)
                    else:
                        self.assert_error(401, "unauthorized", method, path, token=False, **kw)
                        self.assert_error(401, "unauthorized", method, path,
                                          headers={"X-GF-Token": "wrong"}, **kw)
                    self.assert_error(403, "bad_host", method, path,
                                      headers={"Host": "foreign.example:%s" % self.port}, **kw)
        for kw in ({"token": False}, {"headers": {"X-GF-Token": "wrong"}},
                   {"token": False, "path_suffix": "?t=" + self.token}):
            suffix = kw.pop("path_suffix", "")
            self.assert_error(401, "unauthorized", "POST", "/api/answer" + suffix,
                              body=self.answer_body(), **kw)
        self.assert_error(403, "bad_host", "POST", "/api/answer", body=self.answer_body(),
                          headers={"Host": "example.invalid"})
        self.assertEqual(self.request("GET", "/?t=" + self.token, token=False)[0], 200)
        self.assertEqual(self.request("GET", "/api/projects",
                                     headers={"Host": "localhost:%s" % self.port})[0], 200)
        for host in ("0.0.0.0", "::1", "example.invalid", "127.0.0.2", None):
            with self.subTest(host=host), self.assertRaises(core.GFError) as caught:
                server.serve(host=host)
            self.assertEqual((caught.exception.code, caught.exception.exit_code), ("bad_host", 2))
        self.assertEqual(self.httpd.server_address[0], "127.0.0.1")

    def test_static_allowlist_and_host_without_token(self):
        self.assertEqual(set(server.STATIC_TYPES), {"page.js", *("assets/frog-%s.png" % p for p in ("wave", "walk-a", "walk-b", "report"))})
        for name, content_type in server.STATIC_TYPES.items():
            status, headers, body = self.request("GET", "/static/" + name, token=False)
            self.assertEqual(status, 200, name)
            self.assertEqual(headers["Content-Type"], content_type)
            self.assertEqual(body, (server.STATIC_ROOT / name).read_bytes())
            self.assertEqual(headers["Cache-Control"], "no-store")
            self.assert_error(403, "bad_host", "GET", "/static/" + name, token=False,
                              headers={"Host": "foreign.example"})
        for path in ("vendor/three.module.min.js", "vendor/CSS2DRenderer.js", "vendor/LICENSE", "vendor/VERSIONS.txt", "missing", "server.py", "../server.py", "vendor/../page.js",
                     "vendor%2fthree.module.min.js", "vendor%2Fthree.module.min.js",
                     "%70age.js", "%2e%2e/page.js", "./page.js", "assets//frog-wave.png",
                     "vendor/%2e%2e/page.js", "%252e%252e/page.js", "page.js/", ""):
            self.assert_error(404, "not_found", "GET", "/static/" + path, token=False)
        self.assert_error(401, "unauthorized", "POST", "/static/page.js", token=False, body={})
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            connection.putrequest("GET", "/static/page.js", skip_host=True)
            connection.endheaders()
            self.assertEqual(connection.getresponse().status, 403)
        finally:
            connection.close()
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            connection.putrequest("GET", "/static/page.js")
            connection.putheader("Host", "localhost:%s" % self.port)
            connection.endheaders()
            self.assertEqual(connection.getresponse().status, 403)
        finally:
            connection.close()

    def test_authentication_regressions(self):
        status, headers, body = self.request("HEAD", "/static/page.js", token=False)
        self.assertEqual(status, 401)
        self.assertEqual(body, b"")
        self.assertTrue(headers["Content-Type"].startswith("application/json"))
        self.assertEqual(headers["Cache-Control"], "no-store")
        for path in ("/?t=" + self.token, "/api/projects?t=" + self.token):
            status, _, body = self.request("GET", path, headers={"X-GF-Token": "wrong"})
            self.assertEqual(status, 401, 'header must take precedence over query token')
            if path.startswith("/api/"):
                self.assertEqual(json.loads(body)["code"], "unauthorized")
        self.assert_error(401, "unauthorized", "GET", "http://evil.example/api/projects", token=False,
                          headers={"Host": "127.0.0.1:%s" % self.port})

    def test_unauthenticated_root_has_only_static_token_recovery(self):
        with mock.patch.object(server, "_project_list", side_effect=AssertionError('must not read runs')), \
                mock.patch.object(server, "_snapshot", side_effect=AssertionError('must not read runs')):
            status, headers, body = self.request("GET", "/", token=False)
        self.assertEqual(status, 401)
        self.assertEqual(headers["Content-Type"], "text/html; charset=utf-8")
        for name, value in (("Cache-Control", "no-store"), ("Referrer-Policy", "no-referrer"),
                            ("X-Content-Type-Options", "nosniff"), ("X-Frame-Options", "DENY")):
            self.assertEqual(headers[name], value)
        csp = headers["Content-Security-Policy"]
        nonce = csp.split("'nonce-")[1].split("'")[0]
        self.assertEqual(csp, "default-src 'none'; script-src 'nonce-%s'; base-uri 'none'; form-action 'none'" % nonce)
        self.assertIn(('script nonce="%s"' % nonce).encode(), body)
        self.assertEqual(body.count(b'<script'), 1)
        self.assertNotIn(b'__NONCE__', body)
        self.assertIn(b'sessionStorage.getItem', body)
        self.assertIn(b"'graph-flow-token:' + location.port", body)
        self.assertIn(b"location.replace('/?t=' + encodeURIComponent(token))", body)
        self.assertIn(b"searchParams.has('t')", body)  # expired tokens must not loop
        self.assertIn(b'Run graph-flow open, or ask your agent session', body)
        for secret in (self.token, str(self.home), 'server test', 'built.txt', 'api/projects',
                       *map(str, self.projects), *map(str, self.runs), *self.asks):
            self.assertNotIn(secret.encode(), body)
        second = self.request("GET", "/", token=False)
        self.assertNotEqual(second[1]["Content-Security-Policy"], csp)

    def test_demo_view_additions_and_current_attempt_only(self):
        from test_page import build_demo_run
        project = self.root / "demo-project"
        run = build_demo_run(self.home, project)
        status, data = self.json_request("GET", "/api/run?" + urlencode({"project": str(project.resolve()), "run": run.name}))
        self.assertEqual(status, 200)
        decision = data["view"]["decisions"][0]
        self.assertEqual(decision["purpose"], "human_check")
        self.assertEqual(decision["verified"], ["약속한 결과가 빠짐없이 있어요", "scope"])
        self.assertEqual(len(decision["unverified"]), 1)
        self.assertTrue(decision["worker_note"])
        current, events, derived = server._snapshot(run)
        # Untitled commands and implicit scope checks still count; questions are not findings.
        guide = next(n for n in current["nodes"] if n["id"] == "guide")
        guide["checks"][0].pop("title")
        guide["checks"][1].pop("title")
        presentation = server._view(current, derived, events, project)
        self.assertEqual(presentation["decisions"][0]["verified"], ["printf checked", "scope"])
        self.assertNotIn("사용 설명서를 통과시킬까요?", presentation["decisions"][0]["unverified"])
        guide["checks"][0]["title"] = "Readable check"
        derived["nodes"]["guide"]["attempts"] += 1
        presentation = server._view(current, derived, events, project)
        self.assertEqual(presentation["decisions"][0]["verified"], [])
        self.assertEqual(data["view"]["nodes"][3]["inputs"],
                         [{"label": "기록 사용법", "other_title": "기록 저장", "delivered": True}])
        self.assertEqual(data["view"]["nodes"][3]["outputs"],
                         [{"label": "읽기 쉬운 설명", "other_title": "현황판 화면", "delivered": False}])

    def test_decisions_show_latest_failures_and_bound_review_findings_for_every_purpose(self):
        run, project = self.runs[0], self.projects[0]
        current, _, derived = server._snapshot(run)
        submission = derived["nodes"]["build"]["submission"]["id"]
        current["nodes"][0]["checks"][0]["title"] = "The result is complete"
        with store.transaction(run) as tx:
            def result(check, outcome, **extra):
                tx.append("check.result", dict(node="build", check=check, type="cmd", phase="loop",
                          attempt=1, result=outcome, **extra), ACTOR)
            result("unit", "failed", timed_out=True)
            result("unnamed", "failed")
            result("old", "failed")
            result("old", "passed")
            tx.append("check.result", {"node": "build", "check": "scope", "type": "scope",
                      "phase": "loop", "attempt": 1, "result": "passed", "violations": ["outside"]}, ACTOR)
            tx.append("review.submit", {"node": "review", "target": "build", "attempt": 1,
                      "target_submission": submission, "verdict": "fail",
                      "findings": [{"text": "A case is missing"}, {"text": {}}, 7]}, ACTOR)
        for purpose in ("hold", "trajectory", "human_check"):
            with store.transaction(run) as tx:
                st=state.derive(tx.plan,tx.events)["nodes"]["build"]
                tx.append("decision.ask",gate._ask(plan.node_by_id(tx.plan,"build"),st,purpose),ACTOR)
        events = store.events(run)
        derived = state.derive(current, events)
        view = server._view(current, derived, events, project)
        for decision in view["decisions"]:
            self.assertEqual(decision["failed"], ["The result is complete",
                "A check without a description did not pass.", "A case is missing (review · correctness)"])
            self.assertEqual(decision["verified"], ["scope"])
            self.assertEqual(decision["trajectory_reasons"], ["timed_out", "left_its_files"])
        # A later successful result replaces that failure, but not the timeout fact.
        with store.transaction(run) as tx:
            tx.append("check.result", {"node": "build", "check": "unit", "type": "cmd",
                      "phase": "loop", "attempt": 1, "result": "passed"}, ACTOR)
        events = store.events(run); derived = state.derive(current, events)
        view = server._view(current, derived, events, project)
        self.assertEqual(view["decisions"][0]["verified"], ["The result is complete", "scope"])
        self.assertEqual(view["decisions"][0]["failed"], [
            "A check without a description did not pass.", "A case is missing (review · correctness)"])
        derived["nodes"]["build"]["reviews"][0]["target_submission"] = -1
        self.assertNotIn("A case is missing", server._view(current, derived, events, project)["decisions"][0]["failed"])

    def test_run_tolerates_legacy_submission_evidence_and_finding_shapes(self):
        run = self.runs[0]
        for uncertainty in (5, {}, None, "Legacy note", ["Readable note", 4, None, {"text": "bad"}]):
            for findings in (5, {}, [None, {"text": {}}, {"text": "Readable finding"}]):
                with self.subTest(uncertainty=uncertainty, findings=findings):
                    with store.transaction(run) as tx:
                        event = tx.append("node.submit", {"node": "build", "attempt": 1,
                            "notes": {"bad": "shape"}, "low_confidence": uncertainty}, ACTOR)
                        tx.append("review.submit", {"node": "review", "attempt": 1, "target": "build",
                            "target_submission": event["seq"], "verdict": "fail", "findings": findings}, ACTOR)
                    recorded_question(run, "review", "Read this", "build", None, "hold", 5, ACTOR)
                    status, body = self.json_request("GET", self.api("/api/run"))
                    self.assertEqual(status, 200, body)
                    d = body["view"]["decisions"][0]
                    self.assertIsNone(d["worker_note"])
                    expected = [uncertainty] if isinstance(uncertainty, str) else ["Readable note"] if isinstance(uncertainty, list) else []
                    self.assertEqual(d["unverified"], [])  # Free questions never inherit gate evidence.
                    self.assertEqual(d["failed"], [])
                    with store.transaction(run) as tx:
                        tx.append("gate.verdict", {"node": "build", "attempt": "bad", "submission": event["seq"],
                                  "verdict": "reject"}, ACTOR)
                    self.assertEqual(self.json_request("GET", self.api("/api/run"))[0], 200)

    def test_view_filters_malformed_presentation_and_constraint_source_values(self):
        current, events, derived = server._snapshot(self.runs[0])
        current["title"] = {}; current["nodes"][0].update(title=[], summary={})
        check = current["nodes"][0]["checks"][0]
        check.update(title={})
        current["nodes"][0]["checks"].append({"id": "human", "type": "human", "title": [], "prompt": 5})
        derived["decisions"][self.asks[0]]["check"] = "human"
        for context in (5, [], {"why": {}, "undo": ["bad"], "if_approved": "Readable effect"}):
            current["nodes"][0]["checks"][-1]["context"] = context
            view = server._view(current, derived, events, self.projects[0])
            self.assertEqual(view["title"], "server test")
            self.assertEqual(view["nodes"][0]["title"], "build")
            self.assertEqual(view["nodes"][0]["summary"], "build")
            self.assertEqual(view["decisions"][0]["unverified"], [])
            self.assertEqual(view["decisions"][0]["context"], {})
        constraint_path = self.projects[0] / ".graph-flow/constraints.jsonl"
        constraint_path.write_text("{}\n")
        self.assertEqual(self.json_request("GET", self.api("/api/run"))[0], 200)
        with mock.patch.object(learn, "all_constraints", return_value=[
                {"status": "active", "text": {}, "derived_from": {}},
                {"status": "active", "text": "Readable lesson", "derived_from": {"run": derived["run"]["id"], "node": []}},
                {"status": "active", "text": "Another lesson", "derived_from": 5}]):
            lessons = server._view(current, derived, events, self.projects[0])["lessons"]
        self.assertEqual(lessons, [{"text": "Readable lesson", "node_title": None}, {"text": "Another lesson", "node_title": None}])

    def test_unsupported_methods(self):
        for method in ("PUT", "DELETE", "PATCH", "OPTIONS", "HEAD", "TRACE", "BREW"):
            with self.subTest(method=method):
                status, headers, body = self.request(method, "/api/projects")
                self.assertEqual(status, 405)
                self.assertEqual(headers["Cache-Control"], "no-store")
                if method != "HEAD":
                    self.assertEqual(json.loads(body)["code"], "method_not_allowed")

    def test_body_limit_and_malformed_input(self):
        self.assert_error(413, "body_too_large", "POST", "/api/answer", body=b" " * (64 * 1024 + 1))
        for raw in (b"{", b"\xff", b"[]", b"null", b""):
            self.assert_error(400, "bad_body", "POST", "/api/answer", body=raw)
        self.assert_error(400, "bad_body", "POST", "/api/answer", body=b"{}",
                          headers={"Content-Length": "-1"})
        self.assert_error(400, "bad_body", "POST", "/api/answer", body=b"{}",
                          headers={"Content-Length": "nonsense"})
        self.assert_error(400, "bad_body", "POST", "/api/answer", body=b"{}",
                          headers={"Transfer-Encoding": "chunked"})
        for key in ("project", "run", "id", "outcome", "answer"):
            self.assert_error(400, "bad_input", "POST", "/api/answer",
                              body=self.answer_body(**{key: []}))
            self.assert_error(400, "bad_input", "POST", "/api/answer",
                              body=self.answer_body(**{key: "\ud800"}))
        # The limit is inclusive; a small JSON object followed by whitespace still parses.
        body = json.dumps(self.answer_body(outcome="bad")).encode()
        self.assert_error(400, "bad_outcome", "POST", "/api/answer",
                          body=body + b" " * (64 * 1024 - len(body)))

    def test_projects_missing_project_and_unreadable_run(self):
        status, data = self.json_request("GET", "/api/projects")
        self.assertEqual(status, 200)
        self.assertEqual([p["root"] for p in data["projects"]], list(map(str, self.projects)))
        for index, project in enumerate(data["projects"]):
            self.assertEqual(project["name"], self.projects[index].name)
            run = project["runs"][0]
            self.assertEqual(set(run), {"id", "title", "status", "nodes", "passed", "open_decisions", "last_event", "plan_error"})
            self.assertEqual((run["id"], run["status"], run["nodes"], run["passed"], run["open_decisions"]),
                             (self.runs[index].name, "open", 2, 1, 1))
            self.assertEqual(run["last_event"], store.events(self.runs[index])[-1]["ts"])
        shutil.rmtree(str(self.projects[1]))
        (self.runs[0] / "plans" / "0001.json").write_text("broken", encoding="utf-8")
        status, data = self.json_request("GET", "/api/projects")
        self.assertEqual(status, 200)
        self.assertIn("error", data["projects"][1])
        self.assertTrue(data["projects"][0]["runs"][0]["plan_error"])
        self.assertEqual(self.json_request("GET", "/api/queue"), (200, {"queue": []}))

    def test_queue_evidence_checks_files_order_and_freshness(self):
        status, data = self.json_request("GET", "/api/queue")
        self.assertEqual(status, 200)
        queue = data["queue"]
        self.assertEqual([item["project"] for item in queue], list(map(str, reversed(self.projects))))
        for item in queue:
            self.assertEqual(set(item), {"project", "run", "id", "node", "kind", "purpose", "question",
                                         "asked", "evidence", "node_state", "checks", "changed_files"})
            self.assertEqual((item["node"], item["purpose"], item["kind"]),
                             ("build", "lane3", "authorization"))
            self.assertEqual(item["evidence"]["command"], [CMD["run"]])
            self.assertEqual(item["changed_files"], ["built.txt"])
            self.assertEqual(item["node_state"], {"status": "awaiting_approval", "attempts": 1,
                                                  "lane": 3, "effective_lane": 3})
            rows = {(row["check"], row["phase"]): row for row in item["checks"]}
            self.assertEqual(set(rows), {("unit", "gate"), ("unit", "loop"), ("scope", "gate")})
            for phase in ("gate", "loop"):
                row = rows[("unit", phase)]
                self.assertEqual(set(row), {"check", "phase", "result", "exit_code", "command", "log"})
                self.assertEqual((row["result"], row["exit_code"], row["command"]), ("passed", 0, CMD["run"]))
                index = self.projects.index(pathlib.Path(item["project"]))
                self.assertEqual((self.runs[index] / row["log"]).read_text(), "checked")
        self.assertEqual(self.json_request("POST", "/api/answer", body=self.answer_body())[0], 200)
        # A restart gives the old submission's decision a stale binding.
        checks.start(self.runs[1], "build", None, ACTOR)
        self.assertEqual(self.json_request("GET", "/api/queue"), (200, {"queue": []}))
        fresh = recorded_question(self.runs[1], "information", "Which direction?", None, None, "free", None, ACTOR)
        item = self.json_request("GET", "/api/queue")[1]["queue"][0]
        self.assertEqual(item["id"], fresh["id"])
        self.assertEqual(item["node_state"], dict.fromkeys(("status", "attempts", "lane", "effective_lane")))
        self.assertEqual((item["checks"], item["changed_files"]), ([], []))

    def test_queue_uses_only_current_attempt(self):
        run = self.runs[0]
        checks.start(run, "build", None, ACTOR)
        checks.submit(run, "build", None, None, "again", [], None, ACTOR)
        fresh = recorded_question(run, "review", "Second attempt?", "build", None, "free", None, ACTOR)
        queue = self.json_request("GET", "/api/queue")[1]["queue"]
        item = next(item for item in queue if item["project"] == str(self.projects[0]))
        self.assertEqual(item["id"], fresh["id"])
        self.assertEqual(item["node_state"]["attempts"], 2)
        self.assertEqual(item["checks"], [])

    def test_run_shape_and_unknown_id_validation(self):
        status, data = self.json_request("GET", self.api("/api/run"))
        self.assertEqual(status, 200)
        self.assertEqual(set(data), {"plan", "state", "ready", "trace", "view"})
        self.assertEqual(data["plan"], store.read_plan(self.runs[0]))
        self.assertEqual(data["state"], state.derive(data["plan"], store.events(self.runs[0])))
        self.assertEqual(data["ready"], ["build"])
        self.assertEqual(data["trace"]["run"]["nodes"], 2)
        self.assertEqual(data["trace"]["run"]["attempts"], 2)
        self.assertEqual(data["view"]["title"], "server test")
        build, review = data["view"]["nodes"]
        self.assertEqual((build["title"], build["summary"], build["lane"]), ("build", "build", 3))
        self.assertEqual(build["laps"], ["waiting_for_you"])
        self.assertTrue(build["reviewed_by_other_family"])
        self.assertEqual(review["laps"], ["passed"])
        self.assertFalse(review["reviewed_by_other_family"])
        self.assertTrue(data["view"]["decisions"][0]["has_evidence"])
        self.assertEqual(data["view"]["decisions"][0]["purpose"], "lane3")
        self.assertEqual(data["view"]["decisions"][0]["context"], {})
        for route in ("/api/run", "/api/evidence"):
            self.assert_error(404, "unknown_project", "GET", route + "?" + urlencode(
                {"project": str(self.root / "foreign"), "run": self.runs[0].name}))
            for bad in ("missing", "../run0", "/tmp", "Bad", "run0\n", "", "."):
                self.assert_error(404, "unknown_run", "GET", route + "?" + urlencode(
                    {"project": str(self.projects[0]), "run": bad}))
        self.assert_error(404, "unknown_project", "POST", "/api/answer",
                          body=self.answer_body(project=str(self.root)))
        self.assert_error(404, "unknown_run", "POST", "/api/answer", body=self.answer_body(run="../run0"))
        self.assert_error(404, "not_found", "GET", "/missing")
        self.assert_error(404, "not_found", "POST", "/missing", body={})

    def test_timeline_keeps_order_reason_and_survives_odd_events(self):
        def event(seq, kind, **data):
            return {"seq": seq, "ts": "2026-11-15T14:00:%02dZ" % seq, "type": kind, "data": data,
                    "actor": {"role": "worker", "node": data.get("node"), "session": "t3:abc"}}
        nodes = {"a": {"id": "a", "title": "Make A", "checks": [{"id": "unit", "title": "A works"}]},
                 "r": {"id": "r", "title": "Review A", "checks": []}}
        events = [event(1, "node.start", node="a", attempt=1),
                  event(2, "node.start", node="r", attempt=1),
                  event(3, "check.result", node="a", check="unit", result="failed", phase="gate", command="run"),
                  event(4, "gate.verdict", node="a", attempt=1, verdict="reject", rejection={"reason": "unit failed"}),
                  event(5, "review.submit", node="r", target="a", verdict="fail", findings=[{"text": "Too slow"}]),
                  event(6, "gate.verdict", node="a", attempt=1, verdict="replan", rejection=None),
                  event(7, "constraint.add", id=["not", "a", "string"]),
                  event(8, "constraint.add", id="c1"),
                  event(9, "check.result", node="missing", check="unit", result="passed")]
        rows = server._timeline(nodes, events, {"c1": "Keep it small"})
        self.assertEqual([(r["id"], r["seq"], r["kind"]) for r in rows],
                         [("e2", 5, "attempt"), ("e1", 6, "attempt"), ("e8", 8, "learned")])
        review, attempt, learned = rows
        self.assertEqual((review["state"], review["findings"]), ("submitted", ["Too slow"]))
        self.assertEqual((attempt["state"], attempt["reason"]), ("replan", "unit failed"))
        self.assertEqual(attempt["checks"][0]["title"], "A works")
        self.assertEqual(attempt["by"], {"role": "worker", "session": "t3:abc"})
        self.assertEqual(learned["text"], "Keep it small")

    def test_run_without_plan(self):
        run = legacy_run(self.projects[0], "empty", ACTOR)
        status, data = self.json_request("GET", "/api/run?" + urlencode(
            {"project": str(self.projects[0]), "run": run.name}))
        self.assertEqual(status, 200)
        self.assertIsNone(data["plan"])
        self.assertEqual(data["ready"], [])
        self.assertEqual([r["kind"] for r in data["view"].pop("timeline")], ["started"])
        self.assertEqual(data["view"].pop("project"), pathlib.Path(self.projects[0]).name)
        self.assertIn("key repin", data["view"].pop("key_recovery"))
        self.assertTrue(data["view"].pop("legacy"))
        self.assertFalse(data["view"].pop("replaced_unverifiable"))
        self.assertTrue(all(v is None for v in data["view"].pop("plan_approval").values()))
        data["view"].pop("recovery_identity")
        self.assertEqual(data["view"].pop("run_contract"), {})
        self.assertEqual(data["view"].pop("integrity"), [])
        self.assertEqual(data["view"], {"title": "", "summary": "", "context": {}, "requirements": [], "language": "en", "nodes": [], "edges": [], "decisions": [], "answered": [],
                                      "lessons": [], "stale_decisions": [], "complete": False, "run": "empty",
                                      "plan_counts": {"work": 0, "review": 0, "decision": 0, "checks": 0, "decisions": 0},
                                  "plan_error": False, "key_mismatch": False, "location_mismatch":False, "has_work":False, "goal": "", "planned_questions": [],
                                  "integration_checks": [], "promoted_checks": [], "superseded": [], "constraints": [],
                                      "counts": {"done": 0, "doing": 0, "waiting": 0,
                                                 "needs_you": 0, "returned": 0, "returns_total": 0}})

    def test_view_mixed_flow_history_context_edges_and_lessons(self):
        project = self.projects[0]
        run = legacy_run(project, "presentation", ACTOR)
        context = {"why": "Choose the wording", "if_approved": "Use this wording",
                   "if_rejected": "Revise the wording", "undo": "Restore the earlier wording"}
        raw = {"schema_version": 1, "title": "A flow for people", "goal": "Assemble the result", "nodes": []}
        for nid in ("done", "retry", "human", "waiting"):
            raw["nodes"].append({"id": nid, "kind": "work", "goal": "Produce " + nid,
                                 "title": nid.capitalize(), "summary": "A result for the reader",
                                 "owns": [nid + ".txt"], "lane": 1, "grade": "scoped",
                                 "checks": [dict(CMD, title="The result meets the requirement")]})
        raw["nodes"][2]["checks"].append({"id": "wording", "type": "human", "title": "The wording fits",
                                                 "context": context})
        raw["nodes"][3]["needs"] = [{"from": "retry", "artifact": "retry.txt", "label": "Draft"},
                                           {"from": "human", "artifact": "human.txt", "label": "Chosen wording"},
                                           {"from": "done", "artifact": "done.txt", "label": "Finished result"}]
        raw["nodes"].append({"id": "review-retry", "kind": "review", "goal": "Refute the draft",
                             "target": "retry", "lens": "correctness", "lane": 1, "grade": "daily",
                             "checks": [{"id": "cites", "type": "cites"}]})
        self.assertEqual(plan.validate(raw), [])
        current, _ = plan.normalize(raw)
        with store.transaction(run) as tx:
            revision, sha = tx.write_plan(current)
            tx.append("plan.set", {"revision": revision, "plan_sha256": sha,
                      "fingerprints": {n["id"]: state.fingerprint(n) for n in current["nodes"]},
                      "constraints_applied": []}, ACTOR)
            def append(event_type, **data):
                return tx.append(event_type, data, ACTOR)["seq"]
            for nid in ("done", "retry", "human"):
                append("node.start", node=nid, attempt=1)
                sid = append("node.submit", node=nid, attempt=1)
                if nid == "done":
                    append("gate.verdict", node=nid, attempt=1, submission=sid, verdict="pass")
                elif nid == "retry":
                    append("check.result", node=nid, attempt=1, check="unit", phase="gate", result="failed",
                           command="SECRET_COMMAND", exit_code=123, log="SECRET_PATH")
                    append("check.result", node=nid, attempt=1, check="scope", phase="gate", result="failed")
                    append("node.start", node="review-retry", attempt=1)
                    rsid = append("review.submit", node="review-retry", attempt=1, target=nid,
                                  target_submission=sid, verdict="fail",
                                  findings=[{"file": "SECRET_PATH", "line": 12,
                                             "severity": "high", "text": "A required case is missing"}])
                    append("gate.verdict", node="review-retry", attempt=1, submission=rsid, verdict="pass")
                    append("gate.verdict", node=nid, attempt=1, submission=sid, verdict="reject",
                           rejection={"reason": "SECRET_COMMAND exited 123", "evidence": "SECRET_PATH"})
                    append("node.start", node=nid, attempt=2)
                else:
                    append("decision.ask", node=nid, submission=sid + 999, kind="review",
                           question="Stale?", purpose="human_check", check="wording")
                    ask = append("decision.ask", issuer="gate", node=nid, submission=sid, kind="review",
                                 question="Does this wording fit?", purpose="human_check", check="wording",
                                 evidence={"command": None, "files": [], "checks": []})
                    append("gate.verdict", node=nid, attempt=1, submission=sid, verdict="needs_approval")
        approve_current_plan(run)
        active = learn.add(project, run, "done", "Keep the reader's wording", "When requirements change", [], [], ACTOR)
        promoted = learn.add(project, run, "done", "A fixed check", "When checks change", [], [], ACTOR)
        retired = learn.add(project, run, "done", "Old advice", "When scope changes", [], [], ACTOR)
        learn.promote(project, promoted["id"], "true", ACTOR)
        learn.retire(project, retired["id"], "No longer applies", ACTOR)
        # Sources from another run cannot safely be named from this plan, even with a reused id.
        unknown = dict(active, id="c99", text="Advice from another run",
                       derived_from={"run": "elsewhere", "node": "done"})
        with (project / ".graph-flow" / "constraints.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(unknown) + "\n")
        before = store.events(run)
        status, data = self.json_request("GET", "/api/run?" + urlencode({"project": str(project.resolve()), "run": run.name}))
        self.assertEqual(status, 200)
        view = data["view"]
        self.assertEqual(set(view), {"title", "summary", "context", "requirements", "language", "nodes", "edges", "decisions", "answered", "lessons", "counts", "complete",
                                     "run", "project", "timeline", "plan_approval", "plan_counts", "plan_error", "key_mismatch", "location_mismatch", "has_work",
                                 "goal", "planned_questions", "integration_checks", "promoted_checks", "superseded", "constraints", "key_recovery", "legacy", "replaced_unverifiable", "stale_decisions", "recovery_identity", "run_contract", "integrity"})
        self.assertEqual(view["title"], raw["title"])
        self.assertFalse(view["complete"])
        self.assertEqual([n["id"] for n in view["nodes"]], [n["id"] for n in current["nodes"]])
        done, retry, human, waiting, review = view["nodes"]
        self.assertEqual(done["laps"], ["passed"])
        self.assertEqual(retry["laps"], ["returned", "current"])
        self.assertEqual(retry["returned_reasons"], [["The result meets the requirement",
                                                      "A required case is missing"]])
        self.assertEqual((retry["status"], retry["attempts"], retry["max_attempts"]), ("running", 2, 3))
        self.assertEqual(human["laps"], ["waiting_for_you"])
        self.assertEqual(waiting["laps"], [])
        self.assertEqual(review["laps"], [])
        self.assertEqual(view["edges"], [
            {"from": "retry", "to": "waiting", "label": "Draft", "relation": "hands_over", "delivered": False, "gate": "returned"},
            {"from": "human", "to": "waiting", "label": "Chosen wording", "relation": "hands_over", "delivered": False, "gate": "waiting_for_you"},
            {"from": "done", "to": "waiting", "label": "Finished result", "relation": "hands_over", "delivered": True, "gate": "open"},
            {"from": "review-retry", "to": "retry", "label": "", "relation": "reviews", "delivered": False, "gate": "closed"}])
        asked = view["decisions"][0].pop("asked")
        self.assertRegex(asked, r"^\d{4}-\d\d-\d\dT")
        self.assertEqual(view["decisions"][0].pop("asked_by")["role"], "leader")
        self.assertEqual([d["outcome"] for d in view["answered"]], ["approved"])
        for node in view["nodes"]:
            self.assertEqual(set(node) >= {"worker", "session", "started"}, True)
        self.assertIn("identity",view["decisions"][0]);view["decisions"][0].pop("identity")
        view["decisions"][0].pop("contract")
        self.assertEqual(view["decisions"], [{"id": "d%d" % ask, "node": "human", "node_title": "Human",
                                            "question": "Does this wording fit?", "kind": "review",
                                        "purpose": "human_check", "commit": None, "artifact_hashes": {},
                                            "context": {}, "has_evidence": False,
                                            "verified": [], "unverified": [], "worker_note": None,
                                        "record_purpose": "human_check", "files": [], "failed": [], "failed_reviews": 0, "free": False, "replaces_refused": None, "author_context": context, "trajectory_reasons": []}])
        self.assertEqual(view["lessons"], [{"text": active["text"], "node_title": "Done"},
                                         {"text": unknown["text"], "node_title": None}])
        self.assertEqual(view["counts"], {"done": 1, "doing": 1, "waiting": 2, "needs_you": 1, "returned": 1, "returns_total": 1})
        # Commands, log paths and rejection text are shown only in the record of what happened.
        self.assertNotIn("SECRET_", json.dumps({k: v for k, v in view.items() if k != "timeline"}))
        attempts = [r for r in view["timeline"] if r["kind"] == "attempt"]
        self.assertIn("SECRET_COMMAND", {c["command"] for r in attempts for c in r["checks"]})
        self.assertIn("SECRET_COMMAND exited 123", {r["reason"] for r in attempts})
        self.assertEqual(store.events(run), before)
        revised = json.loads(json.dumps(current))
        revised["nodes"][1]["goal"] = "Produce a different draft"
        with store.transaction(run) as tx:
            revision, sha = tx.write_plan(revised)
            tx.append("plan.set", {"revision": revision, "plan_sha256": sha,
                      "fingerprints": {n["id"]: state.fingerprint(n) for n in revised["nodes"]},
                      "constraints_applied": []}, ACTOR)
        approve_current_plan(run)
        _, data = self.json_request("GET", "/api/run?" + urlencode({"project": str(project.resolve()), "run": run.name}))
        self.assertEqual(data["view"]["nodes"][1]["laps"], [])
        self.assertEqual(data["view"]["nodes"][1]["returned_reasons"], [])
        self.assertEqual(data["view"]["edges"][0]["gate"], "closed")
        self.assertEqual(data["view"]["counts"]["returned"], 0)

    def test_view_edge_relations_follow_plan_types(self):
        raw = {"schema_version": 1, "goal": "Choose and review", "nodes": [
            {"id": "choice", "kind": "decision", "goal": "Choose", "lane": 1,
             "question": "Proceed?", "decision_kind": "authorization", "outputs": ["choice"]},
            {"id": "work", "kind": "work", "goal": "Make", "lane": 1, "grade": "scoped",
             "owns": ["result.txt"], "checks": [dict(CMD)],
             "needs": [{"from": "choice", "artifact": "choice", "label": "Permission"}]},
            {"id": "review", "kind": "review", "target": "work", "goal": "Review", "lens": "correctness",
             "lane": 1, "grade": "daily", "checks": [{"id": "cites", "type": "cites"}],
             "needs": [{"from": "work", "artifact": "result.txt", "label": "Result"}]}]}
        self.assertEqual(plan.validate(raw), [])
        current, _ = plan.normalize(raw)
        view = server._view(current, state.derive(current, []), [], self.projects[0])
        self.assertEqual([(e["from"], e["to"], e["relation"]) for e in view["edges"]],
                         [("choice", "work", "waits_for_decision"), ("work", "review", "hands_over"),
                          ("review", "work", "reviews")])

    def test_view_decision_node_context_free_decisions_and_completion(self):
        raw = {"schema_version": 1, "goal": "Choose a direction", "nodes": [
            {"id": "choice", "kind": "decision", "goal": "Pick the direction", "lane": 1,
             "question": "Proceed?", "decision_kind": "direction", "context": {"why": "The direction matters"}}]}
        current, _ = plan.normalize(raw)
        events = [{"seq": 1, "type": "decision.ask", "data": {
            "issuer": "gate", "node": "choice", "kind": "direction", "question": "Proceed?", "purpose": "node"}},
                  {"seq": 2, "type": "decision.ask", "data": {
                      "node": None, "kind": "information", "question": "Which audience?", "purpose": "free"}},
                  {"seq": 3, "type": "decision.answer", "data": {"id": "d2"}}]
        derived = state.derive(current, events)
        view = server._view(current, derived, events, self.projects[0])
        self.assertEqual(view["decisions"][0]["author_context"], raw["nodes"][0]["context"])
        self.assertEqual(view["decisions"][0]["node_title"], "choice")
        self.assertEqual(view["decisions"][0]["purpose"], "direction")
        self.assertEqual(view["nodes"][0]["laps"], [])
        self.assertFalse(view["nodes"][0]["answered"])
        answered_events = events + [{"seq": 4, "type": "decision.answer", "data": {"id": "d1"}}]
        self.assertFalse(server._view(current, state.derive(current, answered_events), answered_events,
                                    self.projects[0])["nodes"][0]["answered"])
        self.assertEqual(view["counts"]["needs_you"], 1)
        free_events = events[:2]
        free_view = server._view(current, state.derive(current, free_events), free_events, self.projects[0])
        self.assertEqual(free_view["decisions"][1]["context"], {})
        self.assertIsNone(free_view["decisions"][1]["node_title"])
        self.assertEqual(free_view["decisions"][1]["purpose"], "information")
        for purpose, kind, expected in (("trajectory", "review", "trajectory"),
                                        ("hold", "review", "hold"),
                                        ("free", "authorization", "authorization"),
                                        ("node", "review", "review"),
                                        ("future-purpose", "review", "future-purpose")):
            derived["decisions"]["d1"].update(purpose=purpose, kind=kind)
            self.assertEqual(server._view(current, derived, events, self.projects[0])["decisions"][0]["purpose"], expected)
        complete = [{"seq": 1, "type": "gate.verdict", "data": {"node": "choice", "verdict": "pass"}},
                    {"seq": 2, "type": "gate.final", "data": {"result": "passed"}}]
        view = server._view(current, state.derive(current, complete), complete, self.projects[0])
        self.assertTrue(view["complete"])
        self.assertEqual(view["counts"], {"done": 1, "doing": 0, "waiting": 0, "needs_you": 0, "returned": 0, "returns_total": 0})

    def file_decision(self, paths):
        # A gate-owned reader includes the submitted files; free questions only list explicit attachments.
        with store.transaction(self.runs[0]) as tx:
            sub = state.derive(tx.plan, tx.events)["nodes"]["build"]["submission"]
            event = tx.append("decision.ask", {"issuer": "gate", "kind": "review",
                "question": "Read the files", "node": "build", "submission": sub["id"],
                "purpose": "human_check", "evidence": {"files": paths}}, ACTOR)
        return "d%d" % event["seq"]

    def test_file_reader_happy_path_and_view_list(self):
        project, run = self.projects[0], self.runs[0]
        (project / "guide.md").write_text("# Read me\n안녕하세요 <script>plain text</script>\n", encoding="utf-8")
        # A current submission and evidence contribute to the same allowlist.
        with store.transaction(run) as tx:
            sub = dict(state.derive(tx.plan, tx.events)["nodes"]["build"]["submission"])
            sub.pop("id", None)
            sub["changed_files"] = ["built.txt"]
            tx.append("node.submit", sub, ACTOR)
        did = self.file_decision(["guide.md", "guide.md", ".graph-flow/secret", "../secret", "human.key"])
        status, headers, body = self.request("GET", self.api("/api/file", decision=did, path="guide.md"))
        self.assertEqual((status, body.decode()), (200, (project / "guide.md").read_text()))
        self.assertEqual(headers["Content-Type"], "text/plain; charset=utf-8")
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(headers["Cache-Control"], "no-store")
        _, payload = self.json_request("GET", self.api("/api/run"))
        d = next(d for d in payload["view"]["decisions"] if d["id"] == did)
        self.assertEqual(d["files"], [{"name": "built.txt", "path": "built.txt"},
                                     {"name": "guide.md", "path": "guide.md"}])
        self.assertEqual(self.request("GET", self.api("/api/file", decision=did, path="built.txt"))[0], 200)

    def test_file_reader_host_internal_symlink_and_replacement(self):
        project = self.projects[0]
        (project / "docs").mkdir()
        (project / "docs" / "guide.txt").write_text("Read inside the project", encoding="utf-8")
        (project / "guide-link.txt").symlink_to(project / "docs" / "guide.txt")
        did = self.file_decision(["guide-link.txt"])
        route = self.api("/api/file", decision=did, path="guide-link.txt")
        self.assertEqual(self.request("GET", route)[2], b"Read inside the project")
        self.assert_error(403, "bad_host", "GET", route, headers={"Host": "evil.example"})
        # The resolved directory can be swapped after validation; open must refuse it.
        outside = self.root / "outside"
        outside.mkdir()
        (outside / "guide.txt").write_text("Outside secret", encoding="utf-8")
        original_open = server._open_project_file
        def replace_directory(project_root, target):
            (project / "docs").rename(project / "old-docs")
            (project / "docs").symlink_to(outside, target_is_directory=True)
            return original_open(project_root, target)
        with mock.patch.object(server, "_open_project_file", side_effect=replace_directory):
            self.assert_error(409, "evidence_changed", "GET", route)

    def test_file_reader_refuses_unsafe_paths_even_when_listed(self):
        project = self.projects[0]
        outside = self.root / "outside.txt"
        outside.write_text("private")
        (project / "escape.txt").symlink_to(outside)
        (project / "private-alias").symlink_to(project / ".graph-flow" / "runs")
        os.link(self.home / "human.key", project / "renamed-key")
        bad = ["../outside.txt", "docs/../built.txt", str(project / "built.txt"), "bad\x00name", "docs\\file",
               ".git/config", ".graph-flow/runs/run0/events.jsonl", "nested/.graph-flow/secret",
               "human.key", "server.json", "registry.json", "escape.txt", "private-alias/run0/events.jsonl", "renamed-key"]
        did = self.file_decision(bad)
        for path in bad:
            with self.subTest(path=path):
                self.assert_error(403, "forbidden_path", "GET", self.api("/api/file", decision=did, path=path))
        (project / "not-listed.txt").write_text("unlisted")
        self.assert_error(403, "forbidden_path", "GET", self.api("/api/file", decision=did, path="not-listed.txt"))
        # Exact spelling matters; equivalent spellings are not authorized.
        did = self.file_decision(["built.txt"])
        self.assert_error(403, "forbidden_path", "GET", self.api("/api/file", decision=did, path="./built.txt"))

    def test_file_reader_refuses_case_variants_of_private_directories(self):
        project = self.projects[0]
        (project / ".git").mkdir(exist_ok=True)
        (project / ".git" / "config").write_text("[remote]\nurl = secret", encoding="utf-8")
        (project / "caselink").symlink_to(project / ".git")
        variants = [".GIT/config", ".Git/config", ".Graph-Flow/runs/run0/events.jsonl", "HUMAN.KEY", "caselink/config"]
        did = self.file_decision(variants)
        _, payload = self.json_request("GET", self.api("/api/run"))
        listed = [f["path"] for d in payload["view"]["decisions"] if d["id"] == did for f in d["files"]]
        for path in variants:
            with self.subTest(path=path):
                self.assertNotEqual(self.request("GET", self.api("/api/file", decision=did, path=path))[0], 200)
                if path != "caselink/config":
                    self.assertNotIn(path, listed)
        # Identity check: an alias directory is refused even though its spelling is harmless.
        self.assert_error(403, "forbidden_path", "GET", self.api("/api/file", decision=did, path="caselink/config"))

    def test_file_reader_lists_only_the_nodes_own_changed_files_and_caps_the_scan(self):
        project, run = self.projects[0], self.runs[0]
        (project / "other.txt").write_text("another node's uncommitted file", encoding="utf-8")
        with store.transaction(run) as tx:
            sub = dict(state.derive(tx.plan, tx.events)["nodes"]["build"]["submission"])
            sub.pop("id", None)
            sub["changed_files"] = ["built.txt", "other.txt"]
            tx.append("node.submit", sub, ACTOR)
        did = self.file_decision([])
        _, payload = self.json_request("GET", self.api("/api/run"))
        d = next(d for d in payload["view"]["decisions"] if d["id"] == did)
        self.assertEqual([f["path"] for f in d["files"]], ["built.txt"])
        self.assert_error(403, "forbidden_path", "GET", self.api("/api/file", decision=did, path="other.txt"))
        with mock.patch.object(server, "MAX_FILE_SCAN", 4):
            self.assert_error(409, "evidence_changed", "GET", self.api("/api/file", decision=did, path="built.txt"))

    def test_file_reader_requires_current_open_decision_in_selected_run(self):
        did = self.file_decision(["built.txt"])
        self.assert_error(401, "unauthorized", "GET", self.api("/api/file", decision=did, path="built.txt"), token=False)
        self.assert_error(404, "unknown_decision", "GET", self.api("/api/file", decision="d99999", path="built.txt"))
        self.assert_error(404, "unknown_decision", "GET", self.api("/api/file", index=1, decision=did, path="built.txt"))
        decisions.answer(self.runs[0], did, "approved", "Read", "dashboard", server.HUMAN)
        self.assert_error(403, "unavailable_decision", "GET", self.api("/api/file", decision=did, path="built.txt"))
        stale = self.file_decision(["built.txt"])
        checks.start(self.runs[0], "build", None, ACTOR)
        self.assert_error(403, "unavailable_decision", "GET", self.api("/api/file", decision=stale, path="built.txt"))

    def test_file_reader_regular_utf8_and_bounded_output(self):
        project = self.projects[0]
        (project / "directory").mkdir()
        os.mkfifo(project / "fifo")
        did = self.file_decision(["built.txt", "missing", "directory", "fifo"])
        for path in ("missing", "directory", "fifo"):
            self.assert_error(409, "evidence_changed", "GET", self.api("/api/file", decision=did, path=path))
        for raw in (b"\xffbinary", b"text\x00binary", b"x" * (server.MAX_EVIDENCE + 30) + b"\x00", b"x" * server.MAX_EVIDENCE + b"\xff"):
            (project / "built.txt").write_bytes(raw)
            self.assert_error(409, "evidence_changed", "GET", self.api("/api/file", decision=did, path="built.txt"))
        (project / "built.txt").write_text("한" * server.MAX_EVIDENCE, encoding="utf-8")
        did=self.file_decision(["built.txt"])
        status, _, body = self.request("GET", self.api("/api/file", decision=did, path="built.txt"))
        self.assertEqual(status, 200)
        self.assertLessEqual(len(body), server.MAX_EVIDENCE)
        self.assertTrue(body.endswith(b"\n[truncated]\n"))
        body.decode("utf-8")
        (project / "built.txt").write_bytes(b"x" * server.MAX_EVIDENCE)
        did=self.file_decision(["built.txt"])
        self.assertEqual(self.request("GET", self.api("/api/file", decision=did, path="built.txt"))[2], b"x" * server.MAX_EVIDENCE)

    def test_view_language_and_total_returns_survive_later_passes(self):
        current = {"title": "English", "nodes": [{"id": "work", "kind": "work", "title": "Task", "summary": "Summary", "checks": []},
                    {"id": "other", "kind": "work", "title": "Other", "summary": "Summary", "checks": []}]}
        events = []
        for nid in ("work", "other"):
            for attempt, verdict in ((1, "reject"), (2, "pass")):
                events.append({"seq":len(events)+1,"type":"node.start","data":{"node":nid,"attempt":attempt}})
                events.append({"seq":len(events)+1,"type":"gate.verdict","data":{"node":nid,"attempt":attempt,"verdict":verdict}})
        normalized, _ = plan.normalize(dict(current, schema_version=1, goal="English"))
        derived = state.derive(normalized, events)
        def view():
            return server._view(normalized, derived, events, self.projects[0])
        self.assertEqual(view()["counts"]["returns_total"], 2)
        self.assertEqual(view()["counts"]["returned"], 0)
        self.assertEqual(view()["language"], "en")
        for container, key in ((normalized,"title"),(normalized["nodes"][0],"title"),(normalized["nodes"][1],"summary")):
            original = container[key]
            container[key] = "한국어"
            self.assertEqual(view()["language"], "ko")
            container[key] = original

    def test_evidence_confinement_text_and_truncation(self):
        run = self.runs[0]
        path = run / "evidence" / "note.log"
        path.write_text("evidence ✓", encoding="utf-8")
        status, headers, body = self.request("GET", self.api("/api/evidence", path="evidence/note.log"))
        self.assertEqual((status, body.decode()), (200, "evidence ✓"))
        self.assertEqual(headers["Content-Type"], "text/plain; charset=utf-8")
        outside = self.root / "secret.log"
        outside.write_text("secret", encoding="utf-8")
        (run / "evidence" / "escape").symlink_to(outside)
        for bad in ("../secret.log", str(path), "evidence/escape", "events.jsonl"):
            self.assert_error(403, "forbidden_path", "GET", self.api("/api/evidence", path=bad))
        for bad in ("evidence", "evidence/missing", "evidence/a\x00b"):
            self.assert_error(404, "unknown_evidence", "GET", self.api("/api/evidence", path=bad))
        fifo = run / "evidence" / "fifo"
        os.mkfifo(str(fifo))
        self.assert_error(404, "unknown_evidence", "GET", self.api("/api/evidence", path="evidence/fifo"))
        for raw in (b"x" * (server.MAX_EVIDENCE + 100), b"\xff" * server.MAX_EVIDENCE):
            path.write_bytes(raw)
            status, _, body = self.request("GET", self.api("/api/evidence", path="evidence/note.log"))
            self.assertEqual(status, 200)
            self.assertLessEqual(len(body), server.MAX_EVIDENCE)
            self.assertTrue(body.endswith(b"\n[truncated]\n"))
            body.decode("utf-8")
        path.write_bytes(b"x" * server.MAX_EVIDENCE)
        body = self.request("GET", self.api("/api/evidence", path="evidence/note.log"))[2]
        self.assertEqual(body, b"x" * server.MAX_EVIDENCE)

    def test_evidence_directory_symlink_outside_run_is_refused(self):
        run = self.runs[0]
        outside = self.root / "outside-evidence"
        outside.mkdir()
        (outside / "secret.log").write_text("outside run secret", encoding="utf-8")
        shutil.rmtree(run / "evidence")
        (run / "evidence").symlink_to(outside, target_is_directory=True)
        self.assert_error(403, "forbidden_path", "GET",
                          self.api("/api/evidence", path="evidence/secret.log"))

    def test_answer_is_verified_and_next_lane3_gate_passes(self):
        status, data = self.json_request("POST", "/api/answer", body=self.answer_body())
        self.assertEqual(status, 200)
        self.assertTrue(data["ok"])
        event = store.events(self.runs[0])[-1]
        self.assertEqual(event["type"], "decision.answer")
        self.assertEqual(event["actor"], {"role": "human", "node": None, "session": "dashboard"})
        self.assertEqual(event["data"], data["decision"])
        self.assertEqual(event["data"]["source"], "dashboard")
        derived = state.derive(store.read_plan(self.runs[0]), store.events(self.runs[0]))
        self.assertTrue(derived["decisions"][self.asks[0]]["verified"])
        self.assertEqual(derived["nodes"]["build"]["status"], "awaiting_approval")
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(gate.gate(self.runs[0], "build", None, ACTOR)["verdict"], "pass")
        self.assert_error(409, "already_answered", "POST", "/api/answer", body=self.answer_body())

    def test_answer_state_errors_and_bad_outcome(self):
        self.assert_error(400, "bad_outcome", "POST", "/api/answer", body=self.answer_body(outcome="answered"))
        self.assert_error(409, "unknown_decision", "POST", "/api/answer", body=self.answer_body(id="d999999"))
        checks.start(self.runs[0], "build", None, ACTOR)
        self.assert_error(409, "stale_decision", "POST", "/api/answer", body=self.answer_body())

    def test_concurrent_answers_only_one_wins(self):
        barrier = threading.Barrier(2)
        results = []
        def answer():
            barrier.wait(5)
            results.append(self.json_request("POST", "/api/answer", body=self.answer_body()))
        threads = [threading.Thread(target=answer) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(10)
            self.assertFalse(thread.is_alive())
        self.assertEqual(sorted(code for code, _ in results), [200, 409])
        self.assertEqual(sum(e["type"] == "decision.answer" and e["data"]["id"] == self.answer_body()["id"] for e in store.events(self.runs[0])), 1)

    def test_reads_do_not_write_or_recover_logs(self):
        with (self.runs[0] / "events.jsonl").open("ab") as stream:
            stream.write(b'{"partial":')
        def digest():
            return {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                    for root in (self.home,) + tuple(self.projects)
                    for p in root.rglob("*") if p.is_file()}
        before = digest()
        for route in ("/api/projects", "/api/queue", self.api("/api/run"),
                      self.api("/api/file", decision=self.asks[0], path="built.txt")):
            self.assertEqual(self.request("GET", route)[0], 200)
        self.assertEqual(digest(), before)
        self.assertFalse((self.home / "server.json").exists())

    def test_page_placeholder_and_nonce_replacement(self):
        path = self.root / "patched-module" / "page.html"
        with mock.patch.object(server, "PAGE_PATH", path):
            status, headers, body = self.request("GET", "/")
            self.assertEqual(status, 200)
            self.assertIn(b"page is not installed", body)
            csp = headers["Content-Security-Policy"]
            nonce = csp.split("'nonce-")[1].split("'")[0]
            self.assertEqual(csp, "default-src 'none'; script-src 'nonce-%s' 'self'; style-src 'nonce-%s'; "
                             "connect-src 'self'; img-src 'self' data: blob:; base-uri 'none'; form-action 'none'" % (nonce, nonce))
            path.parent.mkdir()
            path.write_text('<style nonce="__NONCE__"></style><script nonce="__NONCE__"></script>', encoding="utf-8")
            status, headers, body = self.request("GET", "/")
            self.assertEqual(status, 200)
            second_nonce = headers["Content-Security-Policy"].split("'nonce-")[1].split("'")[0]
            self.assertNotEqual(nonce, second_nonce)
            self.assertNotIn(b"__NONCE__", body)
            self.assertEqual(body.decode().count('nonce="%s"' % second_nonce), 2)

    def test_internal_error_does_not_leak_exception(self):
        with mock.patch.object(server, "_project_list", side_effect=RuntimeError("SECRET traceback")):
            self.assert_error(500, "internal", "GET", "/api/projects")
            body = self.request("GET", "/api/projects")[2]
            self.assertNotIn(b"SECRET", body)
            self.assertNotIn(b"Traceback", body)

    def test_serve_publishes_private_record_and_removes_it_on_shutdown(self):
        for host in ("127.0.0.1", "localhost"):
            out = io.StringIO()
            captured = {}
            def interrupt(httpd):
                record = json.loads((self.home / "server.json").read_text())
                self.assertEqual(set(record), {"url", "port", "token", "pid", "started"})
                self.assertEqual(stat.S_IMODE((self.home / "server.json").stat().st_mode), 0o600)
                self.assertEqual(record["pid"], os.getpid())
                self.assertEqual(record["port"], httpd.server_address[1])
                self.assertEqual(record["url"], "http://127.0.0.1:%s/?t=%s" % (record["port"], record["token"]))
                captured.update(record)
                raise KeyboardInterrupt
            with mock.patch.object(server.ThreadingHTTPServer, "serve_forever", interrupt), \
                    contextlib.redirect_stdout(out):
                server.serve(host=host)
            lines = out.getvalue().splitlines()
            self.assertEqual(len(lines), 1)
            self.assertEqual(json.loads(lines[0]), {"ok": True, "url": captured["url"], "port": captured["port"]})
            self.assertFalse((self.home / "server.json").exists())
            self.assertEqual(stat.S_IMODE((self.home / "human.key").stat().st_mode), 0o600)

    def test_shutdown_preserves_record_for_another_pid(self):
        def replace(httpd):
            with store.locked(self.home / ".lock"):
                store.atomic_write(self.home / "server.json", json.dumps({"pid": os.getpid() + 1}))
            raise KeyboardInterrupt
        with mock.patch.object(server.ThreadingHTTPServer, "serve_forever", replace), \
                contextlib.redirect_stdout(io.StringIO()):
            server.serve()
        self.assertEqual(json.loads((self.home / "server.json").read_text()), {"pid": os.getpid() + 1})

    def running(self, pid=None):
        """Serve in this process and publish the record `gf serve` would write."""
        httpd, token = server.make_server()
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        def close():
            httpd.shutdown()
            httpd.server_close()
            thread.join()
        self.addCleanup(close)
        port = httpd.server_address[1]
        record = {"url": "http://127.0.0.1:%s/?t=%s" % (port, token), "port": port, "token": token,
                  "pid": os.getpid() if pid is None else pid, "started": core.now()}
        store.atomic_write(self.home / "server.json", json.dumps(record) + "\n")
        return record

    @mock.patch.dict(os.environ, GF_NO_OPEN="0")
    def test_open_reuses_a_running_dashboard_without_revealing_the_address(self):
        record, seen = self.running(), []
        result = server.open_dashboard(launch=lambda: self.fail("must not start another"),
                                       browse=lambda url: seen.append(url) or True)
        self.assertEqual(result, {"opened": True, "started": False, "port": record["port"]})
        self.assertEqual(seen, [record["url"]])
        self.assertNotIn(record["token"], json.dumps(result))
        server.open_dashboard(browse=lambda url: seen.append(url) or True,
                              target={"project": "/p q", "run": "r1", "decision": "d4", "node": None})
        self.assertEqual(seen[-1], record["url"] + "#project=%2Fp+q&run=r1&decision=d4")

    @mock.patch.dict(os.environ, GF_NO_OPEN="0")
    def test_open_starts_a_dashboard_when_the_record_is_absent_or_stale(self):
        stale = [None, {"pid": os.getpid(), "port": 1, "token": "x", "url": "http://127.0.0.1:1/?t=x"},
                 "wrong-token"]
        for case in stale:
            with self.subTest(case=case):
                path = self.home / "server.json"
                if case is None:
                    self.assertFalse(path.exists())
                elif case == "wrong-token":
                    record = self.running()
                    store.atomic_write(path, json.dumps(dict(record, token="wrong")) + "\n")
                else:
                    store.atomic_write(path, json.dumps(case) + "\n")
                launched, seen = [], []
                def launch():
                    launched.append(self.running())
                result = server.open_dashboard(launch=launch, browse=lambda url: seen.append(url) or True)
                self.assertEqual(len(launched), 1)
                self.assertEqual(result, {"opened": True, "started": True, "port": launched[0]["port"]})
                self.assertEqual(seen, [launched[0]["url"]])

    @mock.patch.dict(os.environ, GF_NO_OPEN="0")
    def test_open_reports_a_dashboard_that_never_starts_and_a_missing_browser(self):
        with self.assertRaises(core.GFError) as caught:
            server.open_dashboard(launch=lambda: None, browse=lambda url: True, timeout=0.2)
        self.assertEqual((caught.exception.code, caught.exception.exit_code),
                         ("dashboard_unavailable", core.EXIT_IO))
        self.running()
        with self.assertRaises(core.GFError) as caught:
            server.open_dashboard(browse=lambda url: False)
        self.assertEqual(caught.exception.code, "no_browser")
        self.assertNotIn("?t=", caught.exception.message)

    def test_stop_signals_only_a_dashboard_that_answers(self):
        self.assertFalse(server.stop_dashboard())
        store.atomic_write(self.home / "server.json", json.dumps(
            {"pid": os.getpid(), "port": 1, "token": "x", "url": "u"}) + "\n")
        with mock.patch.object(server.os, "kill") as kill:
            self.assertFalse(server.stop_dashboard())
            self.assertNotIn(server.signal.SIGTERM, [call.args[1] for call in kill.call_args_list])
        record = self.running(pid=424242)
        with mock.patch.object(server.os, "kill") as kill:
            self.assertTrue(server.stop_dashboard())
            kill.assert_called_with(record["pid"], server.signal.SIGTERM)
        self.assertFalse((self.home / "server.json").exists())

    @mock.patch.dict(os.environ, GF_NO_OPEN="0")
    def test_open_and_stop_with_a_real_detached_process(self):
        result = server.open_dashboard(browse=lambda url: True)
        record = json.loads((self.home / "server.json").read_text())
        self.addCleanup(lambda: subprocess.run(["kill", str(record["pid"])], capture_output=True))
        self.assertTrue(result["started"])
        self.assertNotEqual(record["pid"], os.getpid())
        self.assertEqual(server.open_dashboard(launch=lambda: self.fail("already running"),
                                               browse=lambda url: True)["started"], False)
        self.assertTrue(server.stop_dashboard())
        self.assertFalse((self.home / "server.json").exists())
        for _ in range(50):
            if not server._alive(record):
                break
            threading.Event().wait(0.1)
        self.assertFalse(server._alive(record))


class ReviewRegressionTest(unittest.TestCase):
    """Defects found by the cross-family review of the server."""

    def test_history_ignores_findings_that_are_not_objects(self):
        node = {"id": "work", "checks": []}
        state = {"basis": 0, "submission": None, "open_decisions": []}
        events = [
            {"seq": 1, "type": "node.start", "data": {"node": "work"}},
            {"seq": 2, "type": "review.submit",
             "data": {"node": "review", "target": "work", "target_submission": 5,
                      "findings": ["bare text", 7, None, {"text": "A case is missing"}, {"text": 3}]}},
            {"seq": 3, "type": "gate.verdict",
             "data": {"node": "work", "verdict": "reject", "attempt": 1, "submission": 5}},
        ]
        laps, returned = server._history(node, state, events)[:2]
        self.assertEqual(laps, ["returned"])
        self.assertEqual(returned, [["A case is missing"]])

    def test_trajectory_reasons_follow_derive_current_attempt_facts(self):
        raw = {"schema_version": 1, "goal": "flow", "nodes": [{"id": "work", "kind": "work",
               "goal": "work", "lane": 1, "owns": [], "checks": [CMD]}]}
        current, _ = plan.normalize(raw)
        events = []
        def append(kind, **data):
            events.append({"seq": len(events) + 1, "type": kind, "data": data, "plan_revision": 1})
        def reasons():
            st = state.derive(current, events)["nodes"]["work"]
            actual = server._trajectory_reasons(st, server._attempt_results("work", st, events))
            self.assertEqual(bool(actual), not st["trajectory_clean"])
            return actual
        append("node.start", node="work", attempt=1)
        self.assertEqual(reasons(), [])
        append("check.result", node="work", check="unit", attempt=1, phase="loop", timed_out=True)
        append("check.result", node="work", check="unit", attempt=1, phase="loop", timed_out=False)
        self.assertEqual(reasons(), ["timed_out"])
        append("check.result", node="work", check="scope", type="scope", attempt=1, phase="loop", violations=["outside"])
        self.assertEqual(reasons(), ["timed_out", "left_its_files"])
        append("node.start", node="work", attempt=2)
        self.assertEqual(reasons(), [])
        append("check.result", node="work", check="old", attempt=1, phase="loop", timed_out=True)
        append("check.result", node="work", check="scope", type="scope", attempt=2, phase="gate", violations=["outside"])
        self.assertEqual(reasons(), [])
        append("node.start", node="work", attempt=3)
        self.assertEqual(reasons(), ["used_all_attempts"])

    def test_history_tolerates_non_iterable_findings_and_non_string_titles(self):
        node = {"id": "work", "checks": [{"id": "unit", "title": {"bad": "shape"}}]}
        st = {"basis": 0, "submission": None, "open_decisions": []}
        for findings in (5, {}, "text", [{"text": []}, {"text": "Readable finding"}]):
            events = [
                {"seq": 1, "type": "node.start", "data": {"node": "work"}},
                {"seq": 2, "type": "review.submit", "data": {"node": "review", "target": "work", "target_submission": 5, "findings": findings}},
                {"seq": 3, "type": "check.result", "data": {"node": "work", "check": "unit", "phase": "gate", "attempt": 1, "result": "failed"}},
                {"seq": 4, "type": "gate.verdict", "data": {"node": "work", "verdict": "reject", "attempt": {}, "submission": 5}}]
            _, returned = server._history(node, st, events)
            self.assertEqual(returned, [["Readable finding"]] if isinstance(findings, list) else [[]])

    def test_requests_have_a_socket_timeout(self):
        httpd, token = server.make_server()
        try:
            self.assertEqual(httpd.RequestHandlerClass.timeout, 30)
        finally:
            httpd.server_close()


if __name__ == "__main__":
    unittest.main()
