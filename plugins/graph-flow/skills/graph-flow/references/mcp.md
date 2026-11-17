# MCP tools

`python3 -B skills/graph-flow/scripts/gf mcp`, run from the plugin root, serves newline-delimited JSON-RPC 2.0 on stdin/stdout. The Claude manifest and Codex `.mcp.json` launch the same entry point. Diagnostics go to stderr. There are no Python dependencies outside the standard library.

The MCP adapter calls `cli.main` in-process with `--json` for every tool (P6). Plans and review findings are written to temporary JSON files and removed after the call. Each result contains `content: [{"type": "text", "text": "<CLI JSON object>"}]` and `isError`. CLI exits 2–5 set `isError: true`; exit 1 is a negative result with `isError: false`, including failed checks, rejected gates, invalid plans, and decision wait timeouts. A failed check still carries the CLI's `ok: true` and `result: "failed"`.

## Identity and visibility (P5)

| Environment variable | Meaning |
| --- | --- |
| `GF_RUN` | Absolute run directory; an optional tool argument `run` overrides it for that call only. |
| `GF_ROLE` | `leader` by default, or `worker`, `reviewer`, `human`. |
| `GF_NODE` | Required bound node for worker and reviewer roles. |
| `GF_SESSION` | Session label recorded in events; the host's chat id is recorded when unset. |
| `GF_HOME` | Optional isolated registry and human-key directory; defaults to `~/.graph-flow`. |

Pass these variables in the MCP host's server environment when starting a session. Tools never accept a `role` or session-identity override. A tool's `node` argument names its target; it does not replace `GF_NODE`. The CLI enforces own-node limits, including a reviewer's access to its target's status. Roles prevent accidental context sharing; they are not a security boundary.

`tools/list` derives visibility from the CLI command registry. `human` sees no tools; the CLI also refuses launching `gf mcp` with that role. Calling an unknown or role-hidden tool returns JSON-RPC error `-32602` before CLI dispatch. Missing or mistyped JSON arguments also return `-32602`; command-level failures retain the CLI result and exit semantics.

## Tool arguments and roles

All tools accept optional `run`. In the table, brackets mark optional arguments, `[]` after a name means an array, and arguments outside brackets are required. `L`, `W`, and `R` mean leader, worker, and reviewer; no tool is exposed to humans. Worker and reviewer access remains limited by the CLI's own-node rules.

| Tool | CLI command | Arguments (besides optional `run`) | Roles |
| --- | --- | --- | --- |
| `run_status` | `status` | `[node]` | L, W, R |
| `plan_validate` | `plan validate` | `plan` JSON object | L, W, R |
| `plan_set` | `plan set` | `plan` JSON object | L |
| `ready_nodes` | `ready` | None | L |
| `route_node` | `route` | `node` | L |
| `assign_node` | `assign` | `node`, `executor`, `model`, `effort`, `provider`, `family`, `isolation` | L |
| `node_brief` | `brief` | `node` or `plan: true`; `[project]` | L |
| `node_start` | `start` | `node`, `[cwd]` | L, W, R |
| `check_red` | `red` | `node`, `[check]`, `[cwd]` | L, W |
| `check_run` | `check run` | `node`, `check`, `[cwd]` | L, W |
| `check_record` | `check record` | `node`, `check`, `result`, `[note]` | L, W |
| `node_submit` | `submit` | `node`, `[commit]`, `[branch]`, `[notes]`, `[low_confidence[]]`, `[cwd]` | L, W |
| `review_submit` | `review submit` | `node`, `verdict`, `findings` JSON array of objects | R |
| `merge_nodes` | `merge` | `nodes[]` | L |
| `gate_node` | `gate` | `node` or `final: true`; `[cwd]` | L |
| `node_reopen` | `reopen` | `node`, `reason` | L |
| `decision_ask` | `decide ask` | `kind`, `question`, `[node]`, `[check]`, `[purpose]`, `[command]`, `[files[]]` | L, W, R |
| `decision_list` | `decide list` | None | L, W, R |
| `decision_wait` | `decide wait` | `id`, `[timeout]` in seconds, default 600 | L, W, R |
| `constraint_list` | `learn list` | `[project]` | L, W, R |
| `constraint_add` | `learn add` | `from_node`, `text`, `review_when`, `[paths[]]`, `[tags[]]`, `[project]` | L |
| `constraint_promote` | `learn promote` | `id`, `run_command`, `[project]` | L |
| `constraint_retire` | `learn retire` | `id`, `reason`, `[project]` | L |
| `run_trace` | `trace` | None | L, W, R |
| `host_set` | `host set` | `capabilities[]` | L |
| `run_init` | `init` | `run_id`, `[project]` | L |

`executor` is `inline`, `subagent`, `workflow`, `t3`, or `background`; `family` is `claude`, `openai`, or `other`; `isolation` is `shared` or `worktree`. `result` is `passed` or `failed`; a review `verdict` is `pass` or `fail`. The CLI validates these values. Optional arrays, when supplied, contain at least one string; `findings` may be empty. The `inputSchema` returned by `tools/list` describes each argument.

Answers to decisions are **not available through MCP (P10)**. Agents can ask, list, and wait; a person answers through the dashboard or the verified human terminal path described in [records.md section 7](records.md#7-decisions). There is no decision-answer, dashboard-start, or MCP-start tool. A host that reaches graph-flow only through MCP asks the person to run `graph-flow open` in their terminal to see the dashboard.

## Example JSON-line session

With `GF_ROLE=leader` and `/work/notes` an existing git repository, send these client messages, one per line. Read the response with the matching id before proceeding to the next request. The initialized notification has no response.

```jsonl
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","clientInfo":{"name":"example","version":"1"},"capabilities":{}}}
{"jsonrpc":"2.0","method":"notifications/initialized"}
{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"run_init","arguments":{"project":"/work/notes","run_id":"notes-export"}}}
```

The first and last server responses have this shape; the intervening `tools/list` response contains the leader's tools and their schemas:

```jsonl
{"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2025-06-18","serverInfo":{"name":"graph-flow","version":"0.3.0"},"capabilities":{"tools":{}}}}
{"jsonrpc":"2.0","id":3,"result":{"content":[{"type":"text","text":"{\"ok\": true, \"run\": \"/work/notes/.graph-flow/runs/notes-export\"}"}],"isError":false}}
```

`ping` returns an empty result. Unknown methods return `-32601`; malformed JSON returns `-32700`. A bad input line does not end the server loop. Initialization echoes the client's protocol version, or uses `2025-06-18` when it is omitted.

`plan_set` always records required plan approval. `ready_nodes`, `assign_node`, work `node_brief`, and `node_start` return `isError: true`, code `plan_not_approved`, until the human signs approval. `run_status`, planning `node_brief` and decision list/wait remain available. Presentation-only changes reuse approval; structural changes ask again. Pre-0.3 records remain unblocked until a new plan is set. Results with `show` tell the leader to ask the person to run `graph-flow open [--decision <id>]` in the terminal; MCP does not expose `--open` or an answer tool. The leader does not restate the plan, waits with `decision_wait`, and ends its turn on timeout because the dashboard cannot wake it.
