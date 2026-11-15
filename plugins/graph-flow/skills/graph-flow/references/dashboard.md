# Dashboard HTTP API

This is the contract for `graphflow/server.py`, its `page.html` and `page.js`, and an optional host-side pane. State, readiness, decisions and trace use the formats in [records.md](records.md), sections 5, 7 and 9. The dashboard is the human answer surface described by P10 in [principles.md](principles.md).

## Process and access

A person starts the independent process with `gf serve`. `serve(host="127.0.0.1", port=0)` accepts only `127.0.0.1` and `localhost`; any other host raises `GFError("bad_host", ..., 2)` before binding or creating a key. Both accepted names bind IPv4 `127.0.0.1`; port 0 selects an available port. Startup ensures `human.key`, creates a fresh `secrets.token_urlsafe(32)` token, and publishes `$GF_HOME/server.json` under `$GF_HOME/.lock`, with atomic replacement and mode 0600:

```json
{"url": "http://127.0.0.1:12345/?t=TOKEN", "port": 12345, "token": "TOKEN", "pid": 1234, "started": "2026-11-15T09:30:00Z"}
```

Stdout contains one JSON line, `{"ok": true, "url": "http://127.0.0.1:12345/?t=TOKEN", "port": 12345}`. The process serves until interrupted, closes its listener on shutdown, and removes `server.json` under the same lock only if the record still names its PID. It does not follow an agent session's lifetime. `make_server(port=0)` returns `(httpd, token)` without blocking or publishing a record; its caller owns serving, shutdown and close.

Every route, including the page and unknown routes, requires the Host check below. Only GET `/static/<name>` skips token authentication. An unauthenticated GET `/` returns the static 401 recovery page described below; all run data and other routes require a token:

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

The page puts `nonce="__NONCE__"` on its `<style>` and its single `<script type="module" src="/static/page.js">`. It stores the startup query token in this tab's `sessionStorage`, under `graph-flow-token:<port>`, removes `t` with `history.replaceState`, and sends `X-GF-Token` on every API request. When `t` is absent it reads the stored token. Storage is scoped by origin and the key by port; another tab does not share this tab's storage. All record text uses `textContent`. There are no external origins, inline style attributes, eval, or unsafe CSP allowances. CSSOM/element.style changes position and scale the DOM cards and SVG routes; markup has no inline style attributes.

Reload recovery briefly puts a token-bearing URL in browser history before `replaceState` removes it, just as opening the printed address does.

An unauthenticated GET `/` returns HTTP 401 with `text/html; charset=utf-8`, `no-store`, and the same referrer, content-type and frame security headers. This small static page contains no token or run data and does not read projects or runs. Its fresh-nonce CSP is `default-src 'none'; script-src 'nonce-<nonce>'; base-uri 'none'; form-action 'none'`. Its only script reads the same session storage key and navigates to `/?t=<encoded token>` if a stored token exists and the URL has no `t`. Otherwise it says to open the address printed by `gf serve` (Korean or English). Checking for an existing `t` prevents an expired token from causing a redirect loop. If storage is unavailable, reopen the printed address. Unauthenticated requests to every other route remain JSON 401 responses; a bad Host still returns 403 before recovery.

## GET /static/<name>

The exact, case-sensitive allowlist is `page.js`, `assets/frog-wave.png`, `assets/frog-walk-a.png`, `assets/frog-walk-b.png`, and `assets/frog-report.png`. JavaScript uses `text/javascript; charset=utf-8`; artwork uses `image/png`. These public page/art files contain no run data. GET requires the same Host check, but no token, because ES module imports cannot attach one. Unknown names, dot segments, percent-encoded names/separators, and traversal under `/static/` return 404 without decoding or normalizing the requested path. Static responses include `no-store` and the usual security headers. POST and other methods retain authentication; no API route is public.

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

## GET /api/file?project=<root>&run=<id>&decision=<decision id>&path=<project-relative path>

Authenticated, Host-checked, read-only text reader for the files a person must review. The decision must exist in the selected run, be open and not stale. Its allowlist is exactly the node's **current** submission `changed_files` plus the decision evidence `files`; neither ownership nor arbitrary project files authorize access. `view.decisions[].files` provides deduplicated `{name, path}` choices. The basename and a small secondary path are visible only in this requested reader.

The path must be relative, contain no `..` component, NUL or backslash, and enter neither `.git` nor `.graph-flow`. After resolving symlinks it must remain inside the project and outside those directories. The resolved path is opened through directory descriptors with no-follow checks on each component, refusing a symlink substituted between validation and opening. `human.key`, `server.json`, `registry.json`, their symlink aliases, and hard links to the current dashboard's private records are refused. Absolute paths and unlisted spellings (even equivalent spellings) return 403 `forbidden_path`. An unknown decision in this run returns 404 `unknown_decision`; answered or stale decisions return 403 `unavailable_decision`.

The target must be a regular UTF-8 text file without NUL bytes. Missing, nonregular, binary or malformed UTF-8 files return 404 `unknown_file`. The whole stream is validated, including bytes beyond the display cap. At most 204,800 response bytes are returned, with the evidence route's `\n[truncated]\n` marker included in that limit and no split UTF-8 character. Responses use `text/plain; charset=utf-8`, `nosniff`, and `no-store`; failures use the existing JSON error shape. Reads never execute file content or recorded commands.

The decision view loads each file on demand into a scrollable, paper-coloured plain-text reader using `textContent`. Markdown and HTML remain literal text. A successful file load satisfies the UI reading gate only for hard-to-undo authorizations without failures. When `failed` is non-empty or `purpose` is `hold`, only opening the evidence details disclosure satisfies the gate; reading a worker-chosen file does not. Requests retain the decision session's captured project/run/id, and late results cannot change another session or a later file selection.

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

Errors are JSON objects: `{"ok": false, "code": "<slug>", "message": "<description>"}` with `Cache-Control: no-store`, except the unauthenticated GET `/` recovery page above.

| HTTP status | Codes / meaning |
| --- | --- |
| 400 | `bad_body`, `bad_input`, `bad_outcome`, and other `GFError` input failures |
| 401 | `unauthorized`: token absent or invalid |
| 403 | `bad_host`, `forbidden_path`, `unavailable_decision` |
| 404 | `unknown_project`, `unknown_run`, `unknown_evidence`, `unknown_file`, `unknown_decision`, `not_found` |
| 405 | `method_not_allowed` |
| 409 | `stale_decision`, `already_answered`, `unknown_decision` from answering |
| 413 | `body_too_large` |
| 500 | `internal`: unexpected exception; generic message, no traceback or exception text |

When an answer returns 409, reload the queue and current run before offering another answer. Authentication failures take precedence over route and body errors. Unsupported GET/POST routes return 404 after authorization (POST also validates its JSON body). Methods other than GET/POST are refused after authorization.

## Dashboard and demo

The page defaults to the most recently active readable open run, offers a picker for multiple runs, and polls about every two seconds while visible. The map uses ordinary DOM cards and one SVG edge layer, with a real HTML list as an accessible alternative. There is no GPU renderer or canvas fallback. Korean and English copy follows `view.language`, computed from the plan; browser language is only the no-run fallback. Direction/information decisions use their API-supported `answered` action and require text; review/authorization decisions offer a purpose-specific affirmative action or send back (required reason).

Space supplies type icons and the palette for a flat, labelled ontology graph. Every node is a rounded rectangular card with a 3px dark outline, hard shadow, type icon, untruncated wrapping title, type/status words, one pip per allowed attempt, and a counted comet badge when it has returned. The icons are a star for the goal, a ringed planet for work, a crescent for review, and a satellite beacon for a decision. Status tints and left strips are mint `#8fe6c0` finished, violet `#c3b1ff` in progress, amber `#ffd166` waiting for the person, and dark `#3a2e5a` with `#6a5a8e` outline before starting. Light cards use dark `#1a1330` text; dark cards use paper text. Pips are mint passed, coral returned, violet current, amber waiting for the person, or hollow unused; a finished card also says how many attempts it took. Normal views never display node IDs, commands, exit codes, lanes or model names; legacy technical handoff labels use a plain “Handoff” fallback.

Dependency depth sets the left-to-right layers. Eight alternating barycentre sweeps retain only orders that do not increase crossings (then route length). Reviews occupy the layer immediately after their target and remain full cards with labelled review arrows pointing back to that target. Uniform 232px cards have reserved vertical space; each inter-column corridor contains collision-separated edge labels. Fit shrinks the drawing to no less than 50%. Expanding a card relays out its neighbours. Every SVG route has an arrowhead. Its label is small text on the line: a `hands_over` edge shows only its `<label>` (“넘겨줌” / “hands over” when the label is empty); `reviews` says “검토함” / “reviews”; `waits_for_decision` says “결정을 기다림” / “waits for a decision”. Edges that hand the same label from the same node in the same state share one label and fork after it. The accessible name keeps the full relation and names both ends. Passed/open routes are solid mint, not-yet routes dashed dim, returned routes coral with a comet on the label, and routes awaiting the person thick amber with a label button opening that decision. Open decisions take priority over earlier returns. There are no separate gate arches. Terminal dependency nodes link to a single dim goal card at the far right with unlabelled routes; completion brightens it and adds a waving frog.

The map fits width and height down to its readable minimum scale of 0.8, then scrolls. At phone widths it fits height subject to that same minimum and becomes a horizontal strip with the panel below. Zoom in/out/fit buttons stay outside the scaled graph; background dragging pans it. Selection pans just enough to reveal the expanded card, and an expanded phone map gains height to keep the loop readable. Focus the map or its viewport to use +, −, 0 and arrow keys. Native card-header buttons and amber chips support Enter/Space, visible hover/focus states and accessible names with type, title, status, attempts and return count. Their tab order follows horizontal flow then vertical position. The scaled card headers and amber chips retain at least 40px targets. Reduced motion disables layout transitions.

Selecting a work or review card expands it in place. Only one expands at a time; Escape or its header collapses it. Inside, make → check → outgoing handoff and check → fix → make arrows show the loop, with a highlighted current state. A 48px walking frog stands at make for the first running attempt, fix for later running attempts, or check for submitted work. Finished work shows an exit check mark; work awaiting the person shows a report frog at the exit. One row per earlier returned attempt uses a comet and plain checks that did not pass. The overview has only one 44px report frog and speech bubble beside each card awaiting the person, plus the waving frog when complete. Decision cards and amber chips open the existing decision reading view.

The side panel orders decisions before counts and a five-line legend, followed by the selected node's now, checks that did not pass, receives, hands over and person-action details. Return counts use `returns_total` and say “times”. History uses the same node cards in plan order (the records cannot interleave all attempts in global time order); earlier returns remain readable in their own section. Lessons remain a constellation of stars joined by lines with readable lesson cards.

`page.js` exports DOM-free `viewLanguage`, `attemptPips`, `innerLoopState`, `edgeRelationLabel`, `fitScale`, `MIN_FIT_SCALE`, `cometCount`, `failedBadgeCount`, `crossingCount` and `layeredLayout`. Layout returns dependency layers, card positions/depths/rectangles, flow order, routes and chip rectangles, goal/terminal positions and bounds. Tests cover the real demo, a twelve-node layered graph, review direction/layers, crossing reduction, rectangle separation including expansion, the minimum fit scale, both languages' relation labels, pips and loop states.

An open decision captures `(project, run, decision id)` and every answer and evidence request uses that target. Each draft belongs to that captured target. Any run change, including automatic replacement when a run disappears, closes the decision and discards its draft. A refresh that removes the decision does the same. While an answer POST is in flight, the run picker is disabled and refreshes and navigation cannot close that decision; the real response is always reported. Late results cannot re-render a different run. A plain notice explains the closure, and callbacks from an earlier view cannot act on a new or reopened decision.

Every decision card, reading view and HTML list entry shows the node title and a plain description of its `purpose` (allowed values and normalization are in [records.md section 12](records.md#12-dashboard-presentation-view)). Only a question exactly matching the gate-generated form for its recorded purpose and node is replaced by that description; authored questions are preserved. Unknown purposes use neutral wording and a neutral decision action. When `has_evidence` is true, the reading view shows a visible reminder and a button opening the details. The reading view, panel card and HTML list show a coral “Did not pass” block for current failed checks and matching failed-review findings. The reading block comes before the verified list. Trajectory decisions list only recorded causes in plain words. Held work and any decision with failures use “그래도 받아들이기” / “Accept anyway”. These decisions and authorizations (`lane3` or `authorization` purpose, or `authorization` kind) disable the affirmative action until the reading gate is satisfied. With any failures or `hold` purpose, only opening that decision's evidence details disclosure unlocks it. For authorizations without failures, either opening evidence details or successfully loading a listed file counts. Neither executes commands. This UI reading gate supplements the signed-answer API; it is not an additional server authorization rule.

`page.js` exports `createDecisionController`, which owns each bound target, draft, evidence-details-open state, successful-file-open state and busy state, and exposes open, close, refresh, openDetails, openFile, canSubmit, buildRequest and onResult. All map, panel and list entry points use it. Importing the module without a DOM does not start the UI. `tests/test_page.py` drives the controller with Node when available and reports a clear skip when Node is absent; the existing static scans remain in place. Refresh updates the surrounding decision content in place without replacing the textarea or action buttons, preserving focus, caret and composition.

From the repository root, this one line creates a fresh isolated demo project and starts its server (choose fresh paths if these already exist):

```sh
python3 -B -c 'import sys; sys.path.insert(0,"plugins/graph-flow/skills/graph-flow/tests"); from test_page import build_demo_run; build_demo_run("/tmp/gf-demo-home", "/tmp/gf-demo-project"); from graphflow.server import serve; serve()'
```

Open the printed URL. `build_demo_run(gf_home, project_dir)` is importable from `tests/test_page.py`, returns the run directory, and sets `GF_HOME` for the current process. It initializes git only in the supplied fresh demo project; the plugin checkout is untouched. It uses real library calls for two passed nodes, one returned and running on its second attempt, one submitted with a contextual human question and uncertainty, two not started, Korean presentation fields, a readable submitted `guide.txt`, and a recorded lesson. To restart that existing demo without recreating it:

```sh
GF_HOME=/tmp/gf-demo-home python3 -B plugins/graph-flow/skills/graph-flow/scripts/gf serve
```
