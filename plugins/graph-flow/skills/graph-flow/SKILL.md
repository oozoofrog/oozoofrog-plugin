---
name: graph-flow
description: Use when a user asks to plan, split, delegate, verify, or track multi-step work with checks that can fail, per-node sub-session assignment, human decision points, or a progress dashboard, or explicitly invokes graph-flow. Exclude simple edits and ordinary questions that need no coordination.
---

# graph-flow

Use bounded work nodes with dependencies, owned files and checks that can fail. Keep decisions, attempts and acceptance in durable records.

## Find the tool and your role

Invoke `python3 <skill-dir>/scripts/gf`; `<skill-dir>` is the directory the host prints when loading this skill. Below, `gf` abbreviates this invocation, not a PATH command. MCP offers the same commands; see [MCP](references/mcp.md).

If the brief sets `GF_ROLE=worker` or `GF_ROLE=reviewer`, read [worker.md](references/worker.md) only and follow the brief. Otherwise read [leader.md](references/leader.md), including first-use setup.

## Run the loop

Follow [leader.md](references/leader.md) for the commands, approval handoff and recoveries.

1. Inspect the project and `gf status`; select an existing `GF_RUN` or `gf init` a new run. Record observed host capabilities.
2. Resolve missing direction through decisions; keep unrelated work moving.
3. Read `gf brief --plan`, write checks before work, split by blast radius, then `gf plan validate` and `gf plan set <file> --open`.
4. Let the person review the dashboard plan. Do not restate the plan in chat. After approval, use `gf ready`, `gf route`, `gf assign` and `gf brief` to dispatch.
5. Within a node: `gf start`, optional `gf red`, produce, `gf check run`, correct, `gf submit`.
6. Merge committed work, receive independent reviews, and gate the review and its target.
7. Return only the rejected scope. Follow leader.md recovery for exhausted attempts, stale decisions or revised contracts. Wording-only revisions retain approval; structural changes require approval.
8. Close with `gf gate --final --open` and `gf trace --conformance`; report evidence and unverified work.
9. Derive, promote and retire a few evidence-based constraints with `gf learn add`, `gf learn promote` and `gf learn retire`.

## Four overriding rules

- A check is something a program can evaluate and that can fail.
- Nothing reaches a person except a decision or an approval, and only a person answers.
- Only gate/plan code creates binding approvals from the contract and current evidence. Agent questions never change verdicts. Unknown or inapplicable plan fields are errors.
- A rejection returns one node with its scope, never the batch.

## Human identity

Never set or change `GF_HOME`, `GF_ROLE=human`, or `GF_HUMAN_TERMINAL`; never run the human answer command (`gf decide answer`). Do not impersonate the person through the dashboard, read or WRITE `human.key`, or edit files under `.graph-flow/runs/**`. These rules prevent accidental impersonation, not a malicious process running as the same OS account.

Execution records are unsigned; file access can falsify them and direct project editing bypasses the tool. Signed approval binds the question, plan and evidence, not execution.

## Reference index

- [Principles](references/principles.md): P1–P12 design rules.
- [Plan](references/plan.md): planner contract and validation.
- [Records](references/records.md): states, events, gates, metrics and recoveries.
- [Leader](references/leader.md): inspect, plan, dispatch, gate and learn.
- [Worker](references/worker.md): execute or review one brief.
- [Executors](references/executors.md): host, model and isolation selection.
- [MCP](references/mcp.md): tool access.
- [Dashboard](references/dashboard.md): recorded progress and human decisions. Open at plan approval, a waiting decision and completion using the creating command's `--open`. `GF_NO_OPEN=1` suppresses browser launch only; on MCP-only hosts relay the returned `graph-flow open` command.
