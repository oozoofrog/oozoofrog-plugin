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

An answer posted with the token is recorded as the person's decision. The token, `server.json` and `human.key` are readable by every process of the same OS user, so roles are a cooperative rule and not a security boundary between a person and an agent on the same account. The rule: opening the dashboard is separate from answering on it. A person may run `gf serve` and open the printed address, or run `gf open`. An agent session may run `gf open` when the person asks to see the dashboard, and `gf open --stop` when the person asks to close it; neither prints an address or a token. An agent session never runs `gf serve`, never reads `server.json` or `human.key`, never sends a request to the dashboard, and never operates the page. An agent that needs a decision records it with `gf decide ask` and waits.

## Opening without the address

`gf open` opens the dashboard in the person's default browser. `open_dashboard()` reads `server.json`; the recorded dashboard counts as running only when its PID exists and GET `/api/projects` with the recorded token returns 200 on the recorded port. Otherwise it starts `gf serve` as a detached process in its own session, with no standard streams, and waits up to 10 seconds for a record that answers. It then passes the recorded URL to `webbrowser.open`.

The result is `{"ok": true, "opened": true, "started": <bool>, "port": <port>, "message": "Dashboard opened in the browser."}`; `started` says whether this call started the process. No output or error message contains the URL or the token. A dashboard that does not answer in time fails with `dashboard_unavailable`, and a browser that does not open with `no_browser`, both exit 5.

A dashboard started this way keeps running after the calling session ends. `gf open --stop` stops the recorded dashboard when it answers: it sends SIGTERM to the recorded PID and removes `server.json` under `$GF_HOME/.lock` if the record still names that PID. The result is `{"ok": true, "stopped": <bool>, "message": ...}`; `stopped` is false when no dashboard answers. Both forms are limited to the leader and human roles and need no run.

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

Returns `{"plan": <stored normalized plan or null>, "state": <derived state>, "ready": [<node IDs>], "trace": <trace result>, "view": <presentation view>}` for one run. The `view` shape is defined in [records.md section 12](records.md#12-dashboard-presentation-view). It includes readable decision `verified`/`unverified` lists and `worker_note`, and node `inputs`/`outputs` derived from edges. The page draws from `view`. Check logs are fetched from `/api/evidence` only when the person presses a log button or opens a decision's details disclosure. The state, readiness, trace and view are read under that run's lock. Readiness uses `graph.ready`; trace uses `trace.trace`.

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

The page defaults to the most recently active readable open run, offers a picker for multiple runs (each option names the project and run id, and how many answers it waits for), and polls about every two seconds while visible. Korean and English copy follows `view.language`, computed from the plan; browser language is only the no-run fallback. Direction/information decisions use their API-supported `answered` action and require text; review/authorization decisions offer a purpose-specific affirmative action or send back (required reason).

The page has two views and the decision reading view. “그래프” / “Graph”, the node map described below, is what opens. The other, “할 일과 기록” / “To do and log”, is one tab away. The header names the project and run id, the plan title, and one line of counts: answers needed, work in progress, and finished out of total. Counts appear nowhere else.

The to-do and log view reads top to bottom:

1. **Your turn.** One card per open decision, with its id, who asked, when, the node title, the purpose in plain words, the question, and the button that opens the reading view. With no open decision it says so.
2. **In progress now.** One line per node that has started and is neither finished nor waiting for the person: title, node id, status, attempt, worker model, session and start time. A running node has the walking frog. The section is omitted when the run is complete, or when nothing is in progress and the person has decisions to answer.
3. **What happened.** `view.timeline`, newest first. Each attempt is one entry that moves to the time of its latest event; questions, answers, reopenings, the final check and recorded lessons are entries of their own. An attempt entry opens to its real checks: title, passed or failed, who ran it (worker or the leader's gate), the command, exit code and duration, files touched outside the node's own, and a button that loads the check's log through `/api/evidence`. It also shows why it came back when no failed check says so, review findings, the worker's note, low-confidence items and changed files. A returned attempt is open without a click. Three filters narrow the list: all, the person's decisions, and what came back.
4. **Tasks as a table**, closed by default: task and id, status, worker, attempts used, and what it still waits for. A task's name shows only that task's entries in the record.
5. **Lessons**, closed by default and present only when some are recorded.

A coloured strip on each entry repeats what its words say: mint passed, coral came back, amber the person's, violet in progress. The view needs no legend. It is one column and has no horizontal scroll at phone width; only the task table scrolls sideways inside its own box.

The graph uses ordinary DOM cards and one SVG edge layer, with a real HTML list as an accessible alternative shown under it. There is no GPU renderer or canvas fallback.

Space supplies type icons and the palette for a flat, labelled ontology graph. Every node is a rounded rectangular card with a 3px dark outline, hard shadow, type icon, untruncated wrapping title, type/status words, the attempt count as words (“시도 2/3”, or how many attempts a finished card took), and its node id with the worker's model. A card that came back and has not yet passed carries a coral strip that says how many times and names the checks that did not pass in the latest return. A card with an open decision carries a paper strip with the question and a button, “<id> 읽고 답하기”, that opens the reading view. The icons are a star for the goal, a ringed planet for work, a crescent for review, and a satellite beacon for a decision. Status tints and left strips are mint `#8fe6c0` finished, violet `#c3b1ff` in progress, amber `#ffd166` waiting for the person, and dark `#3a2e5a` with `#6a5a8e` outline before starting. Light cards use dark `#1a1330` text; dark cards use paper text. Lanes are never displayed; legacy technical handoff labels use a plain “Handoff” fallback.

Dependency depth sets the left-to-right layers. Eight alternating barycentre sweeps retain only orders that do not increase crossings (then route length). Reviews occupy the layer immediately after their target and remain full cards with dotted review arrows pointing back to that target. Uniform 232px cards have reserved vertical space; each inter-column corridor contains collision-separated edge labels. Fit shrinks the drawing to no less than 75%, the scale at which card text stays readable. Every SVG route has an arrowhead. Text on a line has one meaning, the name of what is handed over: a `hands_over` edge shows its `<label>` and nothing when the label is empty; `reviews`, `waits_for_decision` and goal lines carry no text. Edges that hand the same label from the same node in the same state share one label and fork after it. The accessible name keeps the full relation and names both ends. Passed/open routes are solid mint, not-yet routes dashed dim, returned routes coral, routes awaiting the person thick amber, and review routes dotted. Open decisions take priority over earlier returns. There are no separate gate arches. Terminal dependency nodes link to a single dim goal card at the far right with unlabelled routes; completion brightens it and adds a waving frog.

The map fits width and height down to its minimum scale of 0.75, then scrolls. When a run is first drawn and the graph is wider than the map, it scrolls to the leftmost card that has not passed, so the person sees where the work is. At phone widths it fits height subject to that same minimum and becomes a horizontal strip with the panel below. Zoom in/out/fit buttons stay outside the scaled graph; background dragging pans it. Selection pans just enough to reveal the selected card. Focus the map or its viewport to use +, −, 0 and arrow keys. Native card-header buttons and the decision buttons on cards support Enter/Space, visible hover/focus states and accessible names with type, title, status, attempts and return count. Their tab order follows horizontal flow then vertical position. The scaled card headers retain at least 40px targets. Reduced motion disables layout transitions.

Motion marks work in progress and changes seen while the page is open; it never carries information that the words, colours and counts do not. A running card has a walking frog that alternates `frog-walk-a.png` and `frog-walk-b.png` every quarter second, and a violet glow that breathes over two seconds. Open routes into a running card are dashed and flow toward it once per second. When a refresh shows a card newly in progress or newly finished it pops once; when its return count rose it shakes once; the goal card pops once when the run completes. A card first drawn on page load does not pop or shake. The completion frog waves. Looping animations on elements rebuilt at each refresh start at the phase given by the page clock, so polling does not restart them. Under `prefers-reduced-motion: reduce` every animation and transition is off; the first walking frame stays visible and states remain readable from text and colour.

The decision view shows only what was recorded. The worker note, the effects of each choice, the reason the person is asked, verified and unverified items, and the file reader each appear only when the decision carries them; when none do, one line says that only the question was recorded. An empty field is never drawn as a filled section. While a direction or information answer is empty, its send button is disabled and the status line says to write an answer first. The button beside it leaves the decision unanswered and says so. In the record, a returned attempt names the checks that did not pass, so a check title is not read as a statement that it holds.

Every reference an agent session can say is visible on the page, and every entry says where it came from. Decision ids and node ids are shown as small bordered chips on decision cards, record entries, in-progress lines, the task table and graph cards. Pressing a chip copies `<id> · <title>` to paste into the chat. Entries show the actor's role and session. The session is `GF_SESSION` when the person or leader set it; otherwise `gf` records the host's own chat id, `t3:<thread id>` from `T3CODE_THREAD_ID` or `claude:<session id>` from `CLAUDE_CODE_SESSION_ID`, shown as “T3 스레드 <first eight characters>” or “Claude 세션 <first eight characters>”. Times show the date when it is not today. The find box takes a decision id, a node id or part of a node title: an open decision opens its reading view, an answered decision scrolls to and outlines its answer in the record, and a node is selected in the graph with its attempts in the side panel. It searches the current run and says so when nothing matches.

`gf open --decision <id>` and `gf open --node <id>` add a fragment, `#project=<root>&run=<id>&decision=<id>&node=<id>`, to the address they open. The fragment is not sent to the server. The page reads it on load and on `hashchange`, removes it from the address, switches to that run, waits for the run's view, and then acts as the find box does. Both options need `--run` or `GF_RUN`; with a run and neither option the page only switches to that run. The view carries `answered` (id, node, node title, question, outcome, answer, stale) for closed decisions, `asked` and `asked_by` on each open decision, `worker`, `session` and `started` on each node, and `run`, `project` and `timeline` for the header and the record.

Selecting a work or review card in the graph outlines it and shows it in the side panel; selecting it again or pressing Escape clears the selection. The panel shows the node title, id, worker, status and attempts, its summary, the node's attempts from `view.timeline` with the same real checks as the record, what it receives and hands over, and a button that shows the node's entries in the to-do and log view. With nothing selected the panel says to select a task and shows the legend. The legend covers every mark on the map: the four type icons, the four card colours, the five line styles (handed over, not yet, waiting for the person, from work that came back, review) and the meaning of text on a line.

The graph does not list counts. A decision is answered from the button on its card, and leaving the reading view returns to the view it was opened from. Lessons are listed in the to-do and log view.

`page.js` exports DOM-free `viewLanguage`, `edgeRelationLabel`, `edgeChipText`, `fitScale`, `MIN_FIT_SCALE`, `cometCount`, `crossingCount` and `layeredLayout`. Layout returns dependency layers, card positions/depths/rectangles, flow order, routes and chip rectangles, goal/terminal positions and bounds. Tests cover the real demo, a twelve-node layered graph, review direction/layers, crossing reduction, rectangle separation, the minimum fit scale, both languages' relation labels and the one meaning of line text.

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
