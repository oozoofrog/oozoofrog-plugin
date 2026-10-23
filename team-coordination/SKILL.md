---
name: team-coordination
description: Coordinate an enabled leader-and-execution-team workflow with explicit roles, ownership, versioned context acknowledgements, evidence and recovery.
---

The leader owns scope, decisions and acceptance. Execution owners investigate and implement. An independent reviewer checks current artifacts; do not approve your own runtime. Reuse a small team and bounded advisor help. This workflow grants no new permissions.

For managed projects, use one `.codex-team/state.json` through `scripts/harness.py`; legacy ledger CLI refuses managed state. Preserve critical decisions and rationale in role packets. Register real supported IDs with honest provenance, claim canonical write paths, and require current revision/epoch/digest ACKs. Identity registration remains a claim, not OS authentication.

Read the relevant file in `roles/` and `policy.json`. Exact model availability is client/account dependent. The managed adapter initializes, queries model/list, verifies thread model, then rechecks current instructions before dispatch. It is a read-only pilot; direct clients that bypass it retain advisory guidance.

Use trusted Python with site/environment isolation and no bytecode writes. Runtime source is `tools/codex-team-harness/` in the matching reviewed `oozoofrog/oozoofrog-plugin` checkout. Obtain and verify that source before runtime use; a skills-only Plugin does not install the runtime or global guidance. From that verified directory use `python3 -I -S -B run.py harness ...` or `run.py managed-run ...`. For installed scripts, an approved isolated loader must add only this script directory before importing sibling modules. Never use an untrusted environment.

Instruction/contract changes invalidate ACKs. Guarded policy_refresh refuses active/uncertain runs. Hold uncertain ownership until supported terminal evidence. Reservations are conservative accounting; byte/4 context estimates cover the explicit packet only. Two review passes by default; unresolved material findings require a scoped decision. Handoff artifact hashes and fresh file-backed independent review before acceptance.

For session model/effort inspection, explicit change requests, or an unmanaged session's requested transition to new managed sessions, read [session control](references/session-control.md). Use `run.py session-control` or its long-lived Controller API. Separate requested/accepted/pending/live configured settings from unavailable runtime identity. Keep one authoritative project record, real packet receipts and atomic ownership transfer; a registration/ACK alone is not migration. Stop the source at an owner checkpoint, preserve old chat/code, and never silently create a standalone replacement for an unavailable native target.

When managed packets exceed the unchanged context guard or a reset needs portable evidence, read [checkpoints](references/checkpoints.md). Preserve canonical history; use an owner- and independently reviewed working view with exact live obligations, hash-pinned snapshots, allowlisted evidence and fresh packet ACKs. Installation, administrative policy migration, archive verification and actual work resumption are separate steps.

For Astra leader/advisor defaults, read [profiles](references/profiles.md). Model, reasoning and requested service mode are separate. Core Sol and support Luna remain unchanged. Desired defaults and configured observations do not attest current provider execution.

For a failed-review correction under the same owner while retaining claims, read [same-owner rework](references/rework.md). Use the explicit CAS/idempotent transition and fresh packet receipt; do not release/reassign merely to reset task state or review counts.

For a human-authorized project budget increase, read [budget administration](references/budget.md). Preserve defaults, reviews and accounting; use exact project/CAS approvals and actual fresh packet ACKs.

For human-authorized source instrumentation after a retained failed review, read [bounded diagnostics](references/diagnostics.md). Keep the original task, owner, failed reviews and budget; use one exact approved diagnostic cycle and fresh packet ACK. Stop after its separate evidence result.
