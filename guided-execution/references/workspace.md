# Project loop workspace contract

## Contents

- [Capabilities](#capabilities)
- [Initialize](#initialize)
- [Plan example](#plan-example)
- [State and evidence](#state-and-evidence)
- [Changes and resume](#changes-and-resume)
- [Check and status](#check-and-status)

## Capabilities

`scripts/loop_workspace.py` uses Python 3 standard library. It creates a filesystem workspace and validates its records. It does not execute product commands, spawn agents, enforce tool permissions, or provide unattended scheduling. The host agent operates the loop. Use one writer; do not share a run's mutable files across independent sessions.

The helper outputs `verification_scope: record_integrity_only`. Valid evidence metadata does not prove semantic correctness or that a command was really run. Observe actual checks and current artifacts before recording a pass.

## Initialize

Prepare a brief and JSON plan from the actual project. Use a stable, locally unique run ID: lowercase letters, digits, hyphens, or underscores; begin with a letter or digit; maximum 64 characters. The project directory must exist.

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

This example assumes the user requested a local JSON export, preserving the input and avoiding overwrite. Replace names and checks with observed project details. No human gate is needed when that scope is already clear and authorized.

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

Optional decisions have `id`, `kind` (`direction`, `information`, `review`, or `authorization`), `question`, and optionally `artifact_version`. A task names the applicable decision IDs. Put a decision only on work that actually depends on it; independent tasks remain eligible.

## State and evidence

The helper initializes `state.json`. The coordinating agent updates it using atomic replacement and preserves history in decisions.jsonl. Tasks have `status`, `attempts`, `verified_revision`, and `evidence`. Status is one of pending/running/passed/failed/blocked/stale/cancelled. Running, failed, and passed tasks require at least one recorded attempt. Attempts cannot exceed the task limit.

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
