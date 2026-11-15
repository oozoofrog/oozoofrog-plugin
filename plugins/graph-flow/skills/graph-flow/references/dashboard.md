# Dashboard HTTP API

This is the contract for `graphflow/server.py`, its `page.html` and `page.js`, and an optional host-side pane. State, readiness, decisions and trace use the formats in [records.md](records.md), sections 5, 7 and 9. The dashboard is the human answer surface described by P10 in [principles.md](principles.md).

## Process and access

A person starts the independent process with `gf serve`. `serve(host="127.0.0.1", port=0)` accepts only `127.0.0.1` and `localhost`; any other host raises `GFError("bad_host", ..., 2)` before binding or creating a key. Both accepted names bind IPv4 `127.0.0.1`; port 0 selects an available port. Startup ensures `human.key`, creates a fresh `secrets.token_urlsafe(32)` token, and publishes `$GF_HOME/server.json` under `$GF_HOME/.lock`, with atomic replacement and mode 0600:

```json
{"url": "http://127.0.0.1:12345/?t=TOKEN", "port": 12345, "token": "TOKEN", "pid": 1234, "started": "2026-11-15T09:30:00Z"}
```

Stdout contains one JSON line, `{"ok": true, "url": "http://127.0.0.1:12345/?t=TOKEN", "port": 12345}`. The process serves until interrupted, closes its listener on shutdown, and removes `server.json` under the same lock only if the record still names its PID. It does not follow an agent session's lifetime. `make_server(port=0)` returns `(httpd, token)` without blocking or publishing a record; its caller owns serving, shutdown and close.

Every route, including the page and unknown routes, requires the Host check below. Only GET `/static/<name>` skips token authentication; all other routes require a token:

- Exactly one `Host` header, either `127.0.0.1:<bound port>` or `localhost:<bound port>`. A missing, duplicate or foreign Host returns HTTP 403, code `bad_host`.
- For GET, `X-GF-Token: <token>` or query parameter `t=<token>`. An existing header takes precedence over the query. The token is checked with `hmac.compare_digest`.
- For POST, the token must be in `X-GF-Token`; a query token does not authorize a write. Missing, wrong or duplicate tokens return HTTP 401, code `unauthorized`.

Authenticate before dispatching (except the public static GET route described below). Authenticated methods other than GET and POST return HTTP 405, code `method_not_allowed`; HEAD has no response body. JSON responses always include `Cache-Control: no-store`. The page and evidence also carry `no-store`. Responses include `Referrer-Policy: no-referrer`, `X-Content-Type-Options: nosniff` and `X-Frame-Options: DENY`; access logging is disabled so it cannot record token URLs. No CORS access is granted.

POST bodies must be UTF-8 JSON objects with one nonnegative `Content-Length`, no `Transfer-Encoding`, and a size of at most 65,536 bytes (64 KB). Over-limit bodies return HTTP 413, code `body_too_large`. Invalid framing, empty bodies, malformed UTF-8/JSON, and JSON values other than objects return HTTP 400, code `bad_body`.

The server uses `http.server.ThreadingHTTPServer`. Files are the source of state: each request reads current records; no decision or state cache is kept. GET never appends events, repairs an incomplete log tail, runs checks or executes recorded commands. POST writes only through `decisions.answer`; the other process writes are startup key creation and the dashboard's own `server.json` and lock handling.

## Who the token stands for

An answer posted with the token is recorded as the person's decision. The token, `server.json` and `human.key` are readable by every process of the same OS user, so roles are a cooperative rule and not a security boundary between a person and an agent on the same account. The rule: the person starts `gf serve` in their own terminal and opens the printed address; an agent session never starts it, never reads `server.json` or `human.key`, and never sends a request to the dashboard. An agent that needs a decision records it with `gf decide ask` and waits.

## GET /

Returns `text/html; charset=utf-8`, loading `page.html` beside `server.py`. If the file is absent, a minimal HTML page says "The page is not installed."

Every response creates a fresh random nonce, replaces every literal `__NONCE__` in the file with that nonce, and sets this Content-Security-Policy (the same nonce for script and style):

```text
default-src 'none'; script-src 'nonce-<nonce>' 'self'; style-src 'nonce-<nonce>'; connect-src 'self'; img-src 'self' data: blob:; base-uri 'none'; form-action 'none'
```

The page puts `nonce="__NONCE__"` on its `<style>` and its single `<script type="module" src="/static/page.js">`. It reads the startup query token, removes `t` with `history.replaceState`, and sends `X-GF-Token` on every API request. All record text uses `textContent`. There are no external origins, inline style attributes, eval, or unsafe CSP allowances. CSSOM/element.style changes support three.js and CSS2DRenderer.

## GET /static/<name>

The exact, case-sensitive allowlist is `page.js`, `vendor/three.module.min.js`, `vendor/CSS2DRenderer.js`, `assets/frog-wave.png`, `assets/frog-walk-a.png`, `assets/frog-walk-b.png`, and `assets/frog-report.png`. JavaScript uses `text/javascript; charset=utf-8`; artwork uses `image/png`. These public library/art files contain no run data. GET requires the same Host check, but no token, because ES module imports cannot attach one. Unknown names, dot segments, percent-encoded names/separators, and traversal under `/static/` return 404 without decoding or normalizing the requested path. Static responses include `no-store` and the usual security headers. POST and other methods retain authentication; no API route is public.

## GET /api/projects

Enumerates every project root in `$GF_HOME/registry.json`. Project order follows the registry; runs are sorted by ID. An absent registry yields an empty list.

```json
{"projects": [{"root": "/absolute/project", "name": "project", "runs": [{"id": "export", "status": "open", "nodes": 2, "passed": 1, "open_decisions": 1, "last_event": "2026-11-15T09:30:00Z"}]}]}
```

`status` is derived `run.status`; `nodes` and `passed` count current plan nodes; `open_decisions` counts open, non-stale decisions. `last_event` is the last readable event's timestamp, or null for an empty log. A run with no plan has zero nodes. A deleted or unreadable project gets an `error` string on its project entry; an unreadable run gets an `error` on its run entry (retaining its `id`). These conditions never turn the whole response into a 500 or discard other projects.

## GET /api/queue

Returns every open, non-stale decision from every readable run of every registered project, oldest `decision.ask` timestamp first. Equal timestamps retain project/run enumeration and decision sequence order. Deleted projects and unreadable runs are skipped; `/api/projects` reports their errors.

```json
{"queue": [{"project": "/absolute/project", "run": "export", "id": "d14", "node": "build", "kind": "authorization", "purpose": "lane3", "question": "Approve lane3 for build?", "asked": "2026-11-15T09:30:00Z", "evidence": {"command": ["python3 -B test.py"], "files": ["app.py"], "checks": {}}, "node_state": {"status": "awaiting_approval", "attempts": 1, "lane": 3, "effective_lane": 3}, "checks": [{"check": "unit", "phase": "gate", "result": "passed", "exit_code": 0, "command": "python3 -B test.py", "log": "evidence/build/unit/a1-1234abcd.log"}], "changed_files": ["app.py"]}]}
```

`evidence` is the decision's evidence snapshot; `node_state`, `checks` and `changed_files` come from current derived node state. `checks` contains the latest gate-phase and loop-phase result for each check in the node's current attempt, in check order with gate before loop. Each row has all six keys shown; unavailable values such as a scope check's command or log are null. `changed_files` comes from the node's current submission, or is empty when there is none. A decision with `node: null` has null values for all four `node_state` fields and empty `checks` and `changed_files`. Answered and stale decisions are excluded on the next request, without restarting the process. This evidence is what the person reads before approving.

## GET /api/run?project=<root>&run=<id>

Returns `{"plan": <stored normalized plan or null>, "state": <derived state>, "ready": [<node IDs>], "trace": <trace result>, "view": <presentation view>}` for one run. The `view` shape is defined in [records.md section 12](records.md#12-dashboard-presentation-view). It includes readable decision `verified`/`unverified` lists and `worker_note`, and node `inputs`/`outputs` derived from edges. The normal page uses only `view`; raw records/evidence appear only in the manually opened details disclosure. The state, readiness, trace and view are read under that run's lock. Readiness uses `graph.ready`; trace uses `trace.trace`.

The `project` string must exactly match a registered absolute root (HTTP 404, `unknown_project`, otherwise). The run ID must fully match `[a-z0-9][a-z0-9._-]{0,63}`, resolve inside the project's runs directory and exist with an event log (HTTP 404, `unknown_run`, otherwise). These addressing rules also apply to evidence and answer endpoints. URL-encode query values, especially roots and log paths.

## GET /api/evidence?project=<root>&run=<id>&path=<relative path>

Returns one evidence log as `text/plain; charset=utf-8`. `path` is relative to the **run directory**, matching recorded check logs, for example `evidence/build/unit/a1-1234abcd.log`.

Absolute paths, paths resolving outside this run's `evidence/`, and symlinks escaping that directory return HTTP 403, `forbidden_path`. An evidence directory that itself resolves outside the run is also forbidden. The target must be a regular file; missing files, directories and other nonregular files return HTTP 404, `unknown_evidence`.

At most 204,800 response bytes (200 KB) are returned. Content is decoded as UTF-8 with replacement for malformed sequences. Oversized responses end with `\n[truncated]\n`, included in the byte limit, and never split a UTF-8 character. This route serves only regular files reached through the run's `evidence/` directory; a path that resolves outside it is refused. A hard link placed inside `evidence/` is served like any other file there, so the guarantee is only as strong as who can write to that directory.

## POST /api/answer

All five fields are required strings containing valid Unicode (HTTP 400, `bad_input`, otherwise):

```json
{"project": "/absolute/project", "run": "export", "id": "d14", "outcome": "approved", "answer": "Publish this version."}
```

After resolving the registered run, the server calls:

```python
decisions.answer(run_dir, id, outcome, answer, "dashboard",
                 {"role": "human", "node": None, "session": "dashboard"})
```

Success is HTTP 200: `{"ok": true, "decision": <answer data>}`. The answer data contains `id`, `outcome`, `answer`, `source: "dashboard"`, and `sig`. The event is signed with `human.key` and derived state verifies the signature. Answering does not run a gate, start a node, or accept a submission: the leader's next gate consumes the answer and changes readiness according to the normal rules.

Kinds `review` and `authorization` accept `approved`, `rejected`, `revision_requested`; kinds `direction` and `information` accept only `answered`. Empty answer text is allowed. Unknown fields are ignored. The decision layer serializes concurrent answers, validates current bindings and refuses a second answer.

## Errors

Errors are JSON objects: `{"ok": false, "code": "<slug>", "message": "<description>"}` with `Cache-Control: no-store`.

| HTTP status | Codes / meaning |
| --- | --- |
| 400 | `bad_body`, `bad_input`, `bad_outcome`, and other `GFError` input failures |
| 401 | `unauthorized`: token absent or invalid |
| 403 | `bad_host`, `forbidden_path` |
| 404 | `unknown_project`, `unknown_run`, `unknown_evidence`, `not_found` |
| 405 | `method_not_allowed` |
| 409 | `stale_decision`, `already_answered`, `unknown_decision` from answering |
| 413 | `body_too_large` |
| 500 | `internal`: unexpected exception; generic message, no traceback or exception text |

When an answer returns 409, reload the queue and current run before offering another answer. Authentication failures take precedence over route and body errors. Unsupported GET/POST routes return 404 after authorization (POST also validates its JSON body). Methods other than GET/POST are refused after authorization.

## Dashboard and demo

The page defaults to the most recently active readable open run, offers a picker for multiple runs, and polls about every two seconds while visible. Flow and selected-node views share the same orthographic three.js scene. A real HTML list remains available, and becomes the primary view if WebGL is unavailable. Reduced motion disables walking and camera animation. Korean and English copy is selected from `navigator.language`. History uses plan order because `view` does not contain enough information to interleave different nodes' attempts in global time order. Direction/information decisions use their API-supported `answered` action and require text; review/authorization decisions offer approve or send back (required reason).

From the repository root, this one line creates a fresh isolated demo project and starts its server (choose fresh paths if these already exist):

```sh
python3 -B -c 'import sys; sys.path.insert(0,"plugins/graph-flow/skills/graph-flow/tests"); from test_page import build_demo_run; build_demo_run("/tmp/gf-demo-home", "/tmp/gf-demo-project"); from graphflow.server import serve; serve()'
```

Open the printed URL. `build_demo_run(gf_home, project_dir)` is importable from `tests/test_page.py`, returns the run directory, and sets `GF_HOME` for the current process. It initializes git only in the supplied fresh demo project; the plugin checkout is untouched. It uses real library calls for two passed nodes, one returned and running on its second attempt, one submitted with a contextual human question and uncertainty, two not started, Korean presentation fields, and a recorded lesson. To restart that existing demo without recreating it:

```sh
GF_HOME=/tmp/gf-demo-home python3 -B plugins/graph-flow/skills/graph-flow/scripts/gf serve
```
