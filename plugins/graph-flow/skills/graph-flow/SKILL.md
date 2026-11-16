---
name: graph-flow
description: Use when a user asks to plan, split, delegate, verify, or track multi-step work with checks that can fail, per-node sub-session assignment, human decision points, or a progress dashboard, or explicitly invokes graph-flow. Exclude simple edits and ordinary questions that need no coordination.
---

# graph-flow

Turn multi-step work into bounded nodes with explicit dependencies, owned files, and checks that can fail. Run a produce/check/correct loop inside each node and use gate evidence to choose what runs next. Keep decisions, attempts, and acceptance in durable records so another session can resume the run.

## Find the tool and your role

Invoke `python3 <skill-dir>/scripts/gf`; `<skill-dir>` is the base directory the host prints when it loads this skill. Below, `gf` abbreviates that invocation; it does not require a command on PATH. With MCP available, the same commands exist as tools; see [MCP](references/mcp.md).

As the leader, check `command -v gf` once when you first use this skill for a person. If it finds nothing, tell them in one sentence that `gf setup` puts a `gf` command in `~/.local/bin` so they can run commands such as `gf open` from their own terminal, and ask whether to install it. Run `gf setup` only after a yes, relay its message, and if it reports that the directory is not on PATH, give them the printed `export` line to add to their shell profile instead of editing the profile yourself. After a no, do not ask again in that session. `gf setup --remove` undoes it. Keep invoking the skill's own copy yourself; the command on PATH is for the person.

If a brief sets `GF_ROLE=worker` or `GF_ROLE=reviewer`, read [worker.md](references/worker.md) only, skip the other references, and follow your brief. Otherwise, this session is the leader: read [leader.md](references/leader.md).

## Run the loop

1. Inspect the project and existing runs with `gf status`; initialize a new run with `gf init` only when needed, then record observed capabilities with `gf host set`.
2. Resolve consequential human choices with `gf decide ask`; use `gf decide wait` without blocking unrelated nodes.
3. Read `gf brief --plan`; write checks before work, split by blast radius, and use `gf plan validate` followed by `gf plan set`.
4. Select `gf ready` nodes, inspect `gf route`, record `gf assign`, and deliver each `gf brief` to its executor.
5. Inside a work node, use `gf start`, optionally `gf red`, then produce, run `gf check run`, correct, and `gf submit`.
6. Integrate committed work with `gf merge`; receive `gf review submit` from independent reviewers and run `gf gate` on the review and its target.
7. On rejection, read its scope, use `gf assign` and a fresh `gf brief` for that node only; on `replan`, change the plan with `gf plan set`.
8. Close with `gf gate --final` and `gf trace`; report checks, attempts, open decisions, and unverified work.
9. Derive a few constraints with `gf learn add`, promote executable ones with `gf learn promote`, and retire stale ones with `gf learn retire`.

## Three overriding rules

- A check is something a program can evaluate and that can fail.
- Nothing reaches a person except a decision or an approval, and only a person answers.
- A rejection returns one node with its scope, never the batch.

## Read only what the role needs

- [Principles](references/principles.md): resolve a design question by P1–P12.
- [Records](references/records.md): plan fields, role permissions, evidence, and state transitions.
- [Leader](references/leader.md): inspect, plan, dispatch, gate, and learn.
- [Worker](references/worker.md): execute or review one brief.
- [Executors](references/executors.md): choose a host, model, account, and isolation.
- [MCP](references/mcp.md): invoke commands through tool access.
- [Dashboard](references/dashboard.md): show recorded progress and let a person answer decisions. When the person asks to see it, run `gf open`.
