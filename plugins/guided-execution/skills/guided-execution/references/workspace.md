# Project loop workspace contract

## Contents

- [Capabilities](#capabilities)
- [Initialize](#initialize)
- [Plan example](#plan-example)
- [State and evidence](#state-and-evidence)
- [Changes and resume](#changes-and-resume)
- [Check and status](#check-and-status)
- [Explicit transitions](#explicit-transitions)
- [Read-only report](#read-only-report)
- [Live board](#live-board)

## Capabilities

`scripts/loop_workspace.py` uses Python 3 standard library. It creates a filesystem workspace and validates its records. It does not execute product commands, spawn agents, enforce tool permissions, or provide unattended scheduling. The host agent operates the loop. Use one writer; do not share a run's mutable files across independent sessions.

The helper outputs `verification_scope: record_integrity_only`. Valid evidence metadata does not prove semantic correctness or that a command was really run. Observe actual checks and current artifacts before recording a pass.

## Initialize

Prepare a brief and JSON plan from the actual project after initial human alignment is answered or legitimately skipped under questions.md. Record the answer or concrete exception in the brief. Use a stable, locally unique run ID: lowercase letters, digits, hyphens, or underscores; begin with a letter or digit; maximum 64 characters. The project directory must exist.

Run through the interpreter:

```sh
python3 <skill-dir>/scripts/loop_workspace.py init \
  --project <project-path> --run-id notes-export \
  --plan <prepared-plan.json> --brief <prepared-brief.md>
```

The result includes the real workspace path and whether the run was reused. It creates:

| Artifact | Purpose |
| --- | --- |
| brief.md | Outcome, constraints, acceptance, facts, assumptions, authorized scope |
| plan.json | Work units, prerequisites, file scopes, checks, decision definitions |
| state.json | Project/run identity, plan hash, current status, attempts, evidence references, question usage, decision resolutions |
| decisions.jsonl | Append-only history of actual user decisions and controller rulings |
| evidence/ | Actual tool/test results, review observations, and verification metadata |
| lessons.md | Scoped, evidence-backed lessons with revision/removal conditions |

Existing identical input reuses the run without resetting it. Different brief/plan/identity at the same run ID is an error. Resume by reading the existing workspace rather than calling init with newly invented inputs. Do not use `--force`, delete another run, or reset progress to make initialization pass; no such reset operation is provided.

## Plan example

This example assumes the user already chose a local JSON copy of all notes, preservation of the input, and no overwrite, with no remaining material workflow decision. Those explicit choices permit skipping an initial question; technical clarity alone would not. Replace names and checks with observed project details, and record the user choices in the brief.

```json
{
  "schema_version": 1,
  "goal": "Export existing notes to a new local JSON file without modifying the source",
  "question_budget": {"max_questions": 3, "max_rounds": 2},
  "decisions": [],
  "tasks": [
    {
      "id": "export",
      "title": "Implement the JSON export and verify data preservation",
      "depends_on": [],
      "reads": ["notes.py", "test_notes.py"],
      "writes": ["notes.py", "test_notes.py"],
      "checks": [
        {"id": "behavior", "description": "Roundtrip content, original preservation, and existing-output protection pass", "command": "python3 -m unittest -v"}
      ],
      "max_attempts": 3,
      "decision_ids": []
    },
    {
      "id": "usage",
      "title": "Document and exercise the actual export command",
      "depends_on": ["export"],
      "reads": ["notes.py", "README.md"],
      "writes": ["README.md"],
      "checks": [
        {"id": "example", "description": "The documented command produces a readable copy and leaves the input intact"}
      ],
      "max_attempts": 3,
      "decision_ids": []
    }
  ]
}
```

Every task needs an ID, title, dependencies, reads/writes, and nonempty checks. Paths are literal project-relative file/directory scopes, not globs; no parent traversal, absolute paths, `.git` writes, or `.agent-loop` writes. The controller maintains the workspace outside task product scopes. Task IDs use the run-ID character rules. Decision IDs and check IDs are nonempty strings; decision IDs are unique globally and check IDs are unique per task. Dependencies must exist and be acyclic. Commands are descriptions for the host to inspect/run, never automatically executed by the helper.

Optional `requirements` is an array of `{"id": "export", "text": "Export every note to one JSON file"}`: what the user asked for, in their words. IDs are unique nonempty strings; text is nonempty. Runs without it remain valid.

Optional decisions have `id`, `kind` (`direction`, `information`, `review`, or `authorization`), `question`, and optionally `artifact_version`. A task names the applicable decision IDs. Put a decision only on work that actually depends on it; independent tasks remain eligible.

## State and evidence

The helper initializes `state.json`. Prefer `loop_control.py` for supported transitions; it atomically replaces state.json and stores transition snapshots in its optional `history` array. The coordinating agent preserves actual decision/replan context in decisions.jsonl. Older schema-1 workspaces remain readable. Tasks have `status`, `attempts`, `verified_revision`, and `evidence`. Status is one of pending/running/passed/failed/blocked/stale/cancelled. Running, failed, and passed tasks require at least one recorded attempt. Attempts cannot exceed the task limit.

Optional `todos` is an ordered array of `{id, title, task_id, requirement_id, status, reason?}` added and changed only through `loop_control.py todo-add` / `todo-set`, so adding one leaves the plan digest unchanged. `task_id` names a plan task; `requirement_id` names a plan requirement or is null. Status is pending/in_progress/completed/dropped; a dropped todo keeps its reason. A todo's status never satisfies a task check.

Question usage is `question_usage.questions` and `question_usage.rounds`. Record actual usage before yielding to the user, including relevant earlier questions in the same request. Init starts these counters at zero because it cannot observe earlier conversation; the coordinator must transfer existing usage immediately, not reset the budget at bootstrap/resume.

Decision state uses `status` pending/resolved, `answer`, `artifact_version`, and `outcome`. A resolved direction/information decision uses outcome `answered`. A resolved review/authorization uses `approved`, `rejected`, or `revision_requested`. Only `answered` or the applicable `approved` outcome satisfies a task's gate. A refusal is a recorded decision but does not release execution. If the plan pins an artifact version, the resolution must match it. These fields record actual user input; inventing an approval is not permitted.

Before running checks, identify the relevant artifact/input/environment revision, including dirty working-tree changes. Capture real output in a nonempty regular file under evidence/. Use a new evidence file per attempt/check rather than overwriting earlier evidence. Record its SHA-256 and the revision actually checked. A passed task requires exactly one current passed record for each declared check, with no contradictory or duplicate current records. Older logs remain on disk and are linked from the decision history. A current record has this shape:

```json
{
  "check_id": "behavior",
  "result": "passed",
  "path": "evidence/export-attempt-1-behavior.log",
  "sha256": "<actual SHA-256 of the evidence bytes>",
  "artifact_version": "<the exact verified_revision>"
}
```

Possible results are passed/failed/not_run. A pending test never becomes passed because a reviewer is optimistic. Keep the actual command/tool, environment, timestamp, exit/result, and relevant output in the log. For a qualitative review, store the inspected artifact version, acceptance criteria, observations, and verdict.

The helper checks file containment, nonempty evidence bytes, SHA-256 agreement, required checks, and declared revision agreement. It cannot infer the current product revision from that string. The coordinator must compare real artifacts to the recorded fingerprints before reusing success.

## Changes and resume

Preserve original evidence. When requirements, inputs, outputs, checks, or review scope change, mark affected tasks and dependent tasks stale; keep unaffected verified units. Reconcile additions/removals in both plan and state, retain attempt lineage and question usage, reset only materially affected decision resolutions, and log why.

After reconciliation, set `plan_sha256` to SHA-256 of the exact current plan.json bytes, then run check. Updating only the hash is not reconciliation. Review actual changed dependencies and evidence first. Do not auto-grant permission or lower acceptance criteria while reconciling.

Resume in the recorded real project and worktree. The helper rejects mismatched workspace identity, but the coordinator still checks that the user request and current code match the run. Distinct worktrees/versions use separate run state. No match means explicit revalidation, not reuse of a similarly named result.

## Check and status

```sh
python3 <skill-dir>/scripts/loop_workspace.py validate-plan --plan <plan.json>
python3 <skill-dir>/scripts/loop_workspace.py check --workspace <project>/.agent-loop/<run-id>
python3 <skill-dir>/scripts/loop_workspace.py status --workspace <project>/.agent-loop/<run-id>
```

All produce JSON; errors are nonzero. Check/status are read-only. Serialization warnings report potential overlapping reads/writes; the controller also considers shared services, approvals, and resource quotas.

Status reports ready work, unmet dependencies/decisions, explicitly blocked work, exhausted attempts, running/passed/stale/cancelled work. Categories may overlap. Put a concrete block_reason on host-blocked task state so the handoff explains the missing resource or decision. Structural `complete: true` requires every task passed; the coordinator additionally verifies the overall user outcome and current evidence. A valid but blocked/exhausted run is not complete.

## Explicit transitions

`loop_control.py` is a standard-library companion, not a command executor. Every operation requires `--workspace`. Run each subcommand with `--help` for flags. Existing `loop_workspace.py` commands and schema 1 remain supported.

| Command | Preconditions and recorded effect |
| --- | --- |
| `start --task ID --revision HASH` | Requires ready dependencies/decisions and remaining attempts; increments attempts, sets running, archives prior state and clears current check records. |
| `set-revision --task ID --revision HASH --reason TEXT` | After production, records the measured post-edit snapshot for a running attempt with no recorded checks; does not consume another attempt. |
| `record-check --task ID --check CHECK --path evidence/NEW.log --result passed\|failed\|not_run --revision HASH` | Requires a running attempt and a new existing nonempty log under evidence/. Computes its hash, rejects reused log paths and repeated current check IDs; never runs a command. |
| `finish --task ID --result passed\|failed --revision HASH --reason TEXT` | Requires the running revision. A pass requires exactly one current passed record per check; a failed attempt retains observations for repair. |
| `resolve-decision --decision ID --answer TEXT --source SOURCE --outcome answered\|approved\|rejected\|revision_requested [--revision VERSION]` | Records actual input for a pending decision; matches decision kind and pinned artifact version. Rejection does not open the gate. |
| `todo-add --todo ID --task ID [--requirement ID] --title TEXT` | Appends a pending todo under an existing task and, if given, an existing requirement. Rejects duplicate IDs. |
| `todo-set --todo ID --status pending\|in_progress\|completed\|dropped [--reason TEXT]` | in_progress/completed require the todo's task to be running or passed; dropped requires a reason. Records the previous todo in history. Never changes a task or check. |
| `invalidate --task ID --reason TEXT` | Marks the task and its descendants stale, preserving unrelated work, attempts, and logs. |
| `block` / `cancel --task ID --reason TEXT` | Records the task's block/cancellation and invalidates descendants. Does not stop external tools or workers. |

The revision passed to `start` identifies the starting snapshot. After implementation changes it, use `set-revision` with the measured post-edit fingerprint before running checks. Retargeting is rejected once evidence exists; finish the attempt and use an allowed next attempt instead. Capture the same snapshot before/after checks. Never pass an obsolete pre-edit fingerprint as the tested version.

Independent ready tasks may be started together only when their declared file scopes do not conflict. Shared services, undeclared mutable state and resource limits still need host coordination; file-scope checks do not establish full independence.

The coordinating host checks actual authorization before calling these commands. A source string is traceability, not authentication; a recorded approval cannot create permission. Capture the user's real question/answer, version, scope and actual question usage before yielding. This helper does not send questions or update question counters.

A `.control.lock` prevents cooperating writers from racing. If it remains after interruption, inspect whether its writer or external work is still running before removing it; do not auto-steal it. Manual writers must not edit concurrently. A successful state write and its history event are one atomic replacement; history is not a tamper-proof audit log.

For materially changed decisions, plans/checks, blocked-task reopening, cancelled work, or legacy running tasks without `running_revision`, stop affected work and reconcile the plan/state with real evidence before continuing. Preserve prior snapshots, attempts, question usage, and logs. The control helper never silently resets or grants a changed decision.

## Read-only report

```sh
python3 <skill-dir>/scripts/render_report.py \
  --workspace <project>/.agent-loop/<run-id> \
  --output <new-path-outside-run>/report.html
```

Stop the coordinating writer while generating a snapshot. The output directory must already exist. The report is self-contained HTML centered on a typed ontology graph: tasks, available agent records, verification checks and decision gates have distinct shapes. Directed edges show dependencies, planned relationships, recorded results and history-backed retries. Desktop and mobile use separate horizontal/vertical layouts; detailed states, history and evidence metadata are collapsed below the graph. It does not include raw evidence log contents or execute plan commands; it has no network dependencies, approval controls, or live refresh. Existing files, symlinks and output inside the source run are rejected.

Typed surfaces, directional beam/packet decoration and local node-neighborhood focus help explain the graph. Motion is presentation only, not live execution or historical playback. Node states and graph facts do not change during animation. The visual-only motion switch and system `prefers-reduced-motion` preference stop effects without hiding records or base relationships. No animation timing establishes actual chronology, duration, permission or observed worker activity.

Optional agent metadata is presentation context, not a new permission or execution guarantee. Define `plan.agents` as an array of `{"id": "maker", "label": "제작"}`. A task's `agent_id` is a planned assignment. A task state's `agent_id` plus a nonempty `agent_source` is a recorded assignment whose source the host must verify. Only explicitly defined matching IDs become agent nodes; absent or malformed metadata must not manufacture workers. The visual legend distinguishes planned relationships from recorded results. Retry/rework arrows require retained failed-attempt history, not merely `max_attempts`.

The report leaves workspace bytes unchanged. It labels `record_integrity_only` prominently and avoids showing absolute project paths. Free-text fields can still contain sensitive information: inspect the output and recipients before sharing. A green record is not proof that its source code remains current or that its checks were adequate.

## Live board

The Claude Code Plugin adds a read-only mod (`claude-mod/`, Claude manifest only). It polls the newest `.agent-loop/<run>/plan.json` and `state.json` under the session's project root every 2 seconds:

- Side pane `guided-board` (`/guided-board`): list view (task → checks, attempts, readiness, pending decisions, block reasons, then live lines: calls in flight, the latest calls, elapsed time, call and error counts, the last recorded transition) and relation view (prerequisites, decision gates, checks, recorded retries, call counts). It opens by itself once per incomplete run when the terminal is wide enough.
- Third view `요구사항 할 일` (key 3): each requirement with its todos, their status, task and drop reason, then todos with no requirement; a run without todos says so.
- One line above the prompt while work remains, with the tool call in flight and todo progress.
- A mismatched plan/state read keeps the last good board and shows a read-mismatch line until the next poll succeeds.

### Session activity

While a run is incomplete, the mod observes every tool call through a pass-through `tool.call` hook (the call runs unchanged) and keeps its tool, a short target, outcome and time. It attributes each call, in order: an explicit `loop_control.py … --task <id>` command for this run; a subagent tied to a task when it was spawned (one running task, or a prompt naming exactly one running task); the only running task; a file path inside exactly one running task's write, then read scope. Everything else goes to the session node. This is observed activity, not a record: it never changes a status, check or attempt, and it is lost on reload.

### Web dashboard

The pane's web dashboard button runs:

```sh
python3 <skill-dir>/scripts/serve_dashboard.py --workspace <project>/.agent-loop/<run-id>
```

It binds `127.0.0.1` on a free port, prints one JSON line with the tokenized URL, and requires the token plus a loopback `Host` on every request. It re-reads and validates the run on each request (`/api/records`, `/report`) and never writes the run or runs plan commands. `/api/records` adds per-task start time, scopes, revision, evidence paths and a recorded transition timeline. The mod posts activity to `/api/activity` (header token only); the server keeps at most 120 calls in memory, drops unknown fields, and maps unknown task IDs to the session node.

The page has two tabs. `세션 작업` is the session work view below. `요구사항 할 일` (`#view=todos`) lists each requirement with its todos (status glyph, title, drop reason) and a chip for the owning task that opens it in the session view; overall and per-requirement progress count completed over non-dropped todos. `/api/records` carries `requirements` and `todos`.

The session work view is a dark ontology graph polled every second: a session hub, decision gates (diamonds) and task nodes (circles whose ring segments are check results), with typed links (prerequisite, gate, activity) whose labels appear on selection. A running node spins, counts up its elapsed time, shows the call in flight and a call/error badge; a new call travels from the session hub to its node and a failed call pulses. The left rail leads with what needs the person, then object/status filters, search and the full task list; a 10-minute activity lane per task sits under the graph. Selecting a node (click, Enter or Space, the lists or the lanes) opens a plain-language panel: what is happening now, the latest calls as verbs (파일 수정, 명령 실행, 코드 찾기), check results by description, waiting decisions by question, tasks before and after, and a collapsed history of attempts. Revisions, scopes and evidence paths stay in `/api/records` and the static report. Every status carries a glyph besides its color; colors come only from records. Motion is decoration with a motion-off switch and reduced-motion fallback. The server exits when its launching process goes away; `--no-parent-watch` keeps it running for manual use.

### Quick view, command explanations and Claude questions

The mod also sends the absolute path of file-tool calls (Read, Edit, MultiEdit, Write, NotebookEdit) and the full Bash command (600 characters). In the task panel a file call has a 보기 button: `/api/file?path=` returns the file's current text only when that exact path is in the received activity, it is a regular non-symlink file, it does not look secret (`.env*`, keys, certificates, `.ssh`, `.aws`, credentials files), and it is not binary; at most 200KB is shown with line numbers. A command call shows its command and a Korean explanation on hover or focus. The page asks `/api/explain` only for commands present in the activity; the mod picks pending requests on its 2-second tick, asks Haiku in one batch (at most six), and posts the texts back. The tooltip shows a waiting state until then; with AI off the mod answers that explanations are off. Explanations are cached in memory.

When Claude calls AskUserQuestion while the dashboard runs, the mod posts the questions to `/api/question` and the page shows them first in the left rail with their options, a free-text field and a send button. The terminal dialog opens as usual. An answer sent from the dashboard answers the tool call and withdraws the pending dialog; an answer in the terminal closes the card. Either way the card then shows where it was answered and the answer.

While the dashboard runs and AI summary is on, the mod sends Haiku the run's task records and a digest of the last 30 session messages (message text clipped, tool names and targets; no tool output) at most every 20 seconds after new activity, then posts the reply to `/api/session`. The server keeps only headline, activity sentence, stage labels/kinds/notes, stage order and references to existing task IDs. Unknown IDs and any status field are dropped. The page labels this layer "AI 요약 · 참고용" with its time and token count. Turn it off in the pane. After a mod reload the pane forgets the running server: reopen the dashboard from the pane; the previous server process stays idle until the Claude Code process exits. A remote surface cannot open the loopback link.
