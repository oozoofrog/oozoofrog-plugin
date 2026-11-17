---
name: graph-flow
description: Use when a user asks to plan, split, delegate, verify, or track multi-step work with checks that can fail, per-node sub-session assignment, human decision points, or a progress dashboard, or explicitly invokes graph-flow. Exclude simple edits and ordinary questions that need no coordination.
---

# graph-flow

Turn multi-step work into bounded nodes with explicit dependencies, owned files, and checks that can fail. Run a produce/check/correct loop inside each node and use gate evidence to choose what runs next. Keep decisions, attempts, and acceptance in durable records so another session can resume the run.

## Find the tool and your role

Invoke `python3 <skill-dir>/scripts/gf`; `<skill-dir>` is the base directory the host prints when it loads this skill. Below, `gf` abbreviates that invocation; it does not require a command on PATH. With MCP available, the same commands exist as tools; see [MCP](references/mcp.md).

As the leader, check `command -v graph-flow` once when you first use this skill for a person. If it finds nothing, tell them in one sentence that `gf setup` puts the commands `graph-flow` and `gf` in `~/.local/bin` so they can run commands such as `graph-flow open` from their own terminal, and ask whether to install it. Many shells already give `gf` another meaning (oh-my-zsh aliases it to `git fetch`), so when you tell the person what to type, write `graph-flow`. Run `gf setup` only after a yes, relay its message, and if it reports that the directory is not on PATH, give them the printed `export` line to add to their shell profile instead of editing the profile yourself. After a no, do not ask again in that session. `gf setup --remove` undoes it. Keep invoking the skill's own copy yourself; the command on PATH is for the person.

If a brief sets `GF_ROLE=worker` or `GF_ROLE=reviewer`, read [worker.md](references/worker.md) only, skip the other references, and follow your brief. Otherwise, this session is the leader: read [leader.md](references/leader.md).

## Run the loop

1. Inspect the project and existing runs: with no run selected, `gf status` lists this project's runs with their status and open decisions. To continue one, set `GF_RUN` to its `run` path and run `gf status` again; initialize a new run with `gf init` only when needed, then record observed capabilities with `gf host set`.
2. Resolve consequential human choices with `gf decide ask --open`; use `gf decide wait` without blocking unrelated nodes.
3. Read `gf brief --plan`; write checks before work, split by blast radius, and use `gf plan validate` followed by `gf plan set <file> --open`. This always asks the person to approve the plan before any dispatch.
4. Do not print or restate the plan in chat. Say one sentence in the person’s language: “계획을 대시보드에 올렸어요. 보시고 시작을 눌러 주세요. (<decision id>)” Then `gf decide wait <id> --timeout 30`. On timeout end the turn; the dashboard cannot wake a session. Resume when the person says they answered. After approval, select `gf ready` nodes, inspect `gf route`, record `gf assign`, and deliver each `gf brief` to its executor.
5. Inside a work node, use `gf start`, optionally `gf red`, then produce, run `gf check run`, correct, and `gf submit`.
6. Integrate committed work with `gf merge`; receive `gf review submit` from independent reviewers and run `gf gate <node> --open` on the review and its target.
7. On rejection, read its scope, use `gf assign` and a fresh `gf brief` for that node only; on `replan`, change the plan with `gf plan set <file> --open`. A structural change needs fresh approval; every new revision needs approval; posting an identical plan creates no revision.
8. Close with `gf gate --final --open` and `gf trace`; report checks, attempts, open decisions, and unverified work.
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
- [Dashboard](references/dashboard.md): show recorded progress and let a person answer decisions. Open without asking at exactly three moments: plan approval (`plan set --open`), a waiting decision (`decide ask --open` or `gate <node> --open`), and completion (`gate --final --open`). Use `GF_NO_OPEN=1` only to suppress the browser in headless use; it never skips approval. On MCP-only hosts, relay the returned `graph-flow open` command.

Never set or change `GF_HOME`, `GF_ROLE=human`, or `GF_HUMAN_TERMINAL`; never run the human answer command (`gf decide answer`). Do not impersonate the person through the dashboard, read or WRITE `human.key`, or edit files under `.graph-flow/runs/**`. These rules prevent accidental impersonation, not a malicious process running as the same OS account.
