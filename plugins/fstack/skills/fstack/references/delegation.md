# Delegation

- The main session owns the playbook and its checklist (the host's plan or todo tool, or an inline list). Do not hand a whole playbook to a subagent.
- Each brief restates the user goal, gives paths and states the bar for done.
- A subagent report is not evidence. Read the diff and the outputs yourself.
- Default to a lean main session plus one independent reviewer (`references/review.md`).
- Fan out only across disjoint seams, or across competing shapes of a design that has no precedent. Give each worker its own worktree or directory. Separate the work before it touches shared state.
- For more than 3 interdependent units with checks, human decisions or a dashboard, use graph-flow when it is installed. Otherwise write `skip: graph-flow not installed` and use host subagents.
- Use only the models that the host offers. Choose them with model-advisor when it is installed. Put no model IDs in files.
- Send bulk reads to subagents. Keep only summaries in the main session.

## Without independent agents

- With file access but no subagents: run the passes yourself, one after another.
- With access to the conversation only: return a proposed patch or an explanation. Mark every check that you did not run Inconclusive.
- In both cases, write "single-agent fallback" in the report. Never present your own passes as independent reviewers. Never claim writes, test runs or saves that did not happen.
- For a trivial edit, use no extra agents.

## Agent lifecycle

- Reuse a live agent only in the same role, and only while its context still applies. Never make an author the reviewer of its own diff.
- Send a reused agent the current brief and every fact that changed. It does not see new instructions from the user.
- Use at most one agent per role per task.
- When the user changes the goal, send the affected agents the new brief. Name the findings that they must check again.
- Before you take over an agent's files, confirm that the agent has stopped, or agree on files that do not overlap.
- If an agent fails or hits a limit, keep its useful findings, do the missing pass yourself, and report the reduced coverage.
- While agents run, do independent work. Then wait with a bounded wait. Do not poll in a tight loop.
- Keep the session's model and effort for an agent unless the user or model-advisor chooses otherwise. Never write agent handles or runtime IDs into records.
