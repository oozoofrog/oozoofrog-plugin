---
name: team-coordination
description: Coordinate an enabled leader-and-execution-team workflow with explicit roles, ownership, versioned context acknowledgements, evidence and recovery.
---

The leader owns scope, decisions and acceptance. Execution owners investigate and implement. An independent reviewer checks current artifacts; do not approve your own runtime. Reuse a small team and bounded advisor help. This workflow grants no new permissions.

For managed projects, use one `.codex-team/state.json` through `scripts/harness.py`; legacy ledger CLI refuses managed state. Preserve critical decisions and rationale in role packets. Register real supported IDs with honest provenance, claim canonical write paths, and require current revision/epoch/digest ACKs. Identity registration remains a claim, not OS authentication.

Read the relevant file in `roles/` and `policy.json`. Exact model availability is client/account dependent. The managed adapter initializes, queries model/list, verifies thread model, then rechecks current instructions before dispatch. It defaults to a read-only pilot; explicit handoffs may use the bounded writing scope in session control; direct clients that bypass it retain advisory guidance.

Use trusted Python with site/environment isolation and no bytecode writes. Runtime source is `tools/codex-team-harness/` in the matching reviewed `oozoofrog/oozoofrog-plugin` checkout. Obtain and verify that source before runtime use; a skills-only Plugin does not install the runtime or global guidance. From that verified directory use `python3 -I -S -B run.py harness ...` or `run.py managed-run ...`. For installed scripts, an approved isolated loader must add only this script directory before importing sibling modules. Never use an untrusted environment.

Keep the goal, completion criteria, owner, next action, actual failure cause, alternatives and verification evidence clear. Instruction/contract changes invalidate ACKs. Hold uncertain ownership until supported terminal evidence. Require fresh artifact hashes and genuine independent current-evidence review before acceptance; retain every FAIL. This workflow has no token budget, reservation, synthetic charge, packet-size estimate stop or fixed review-count quota. Actual provider capacity, user constraints and permissions still apply.

For session model/effort inspection, explicit change requests, or an unmanaged session's requested transition to new managed sessions, read [session control](references/session-control.md). Use `run.py session-control` or its long-lived Controller API. Separate requested/accepted/pending/live configured settings from unavailable runtime identity. Keep one authoritative project record, real packet receipts and atomic ownership transfer; exact management-directory claims use the guarded administrative baseline and never expand recipient writing scope; a registration/ACK alone is not migration. Stop the source at an owner checkpoint with actual source-owner ACK evidence, preserve old chat/code, and never silently create a standalone replacement for an unavailable native target.

When context needs a clearer working view or a reset needs portable evidence, read [checkpoints](references/checkpoints.md). Preserve canonical history, key decisions and exact live obligations with hash-pinned snapshots, allowlisted evidence and fresh packet ACKs. Actual provider context capacity is separate. Installation, administrative migration, archive verification and actual work resumption remain separate steps.

For Astra leader/advisor defaults, read [profiles](references/profiles.md). Model, reasoning and requested service mode are separate. Core Sol and support Luna remain unchanged. Desired defaults and configured observations do not attest current provider execution.

For a failed-review correction under the same owner while retaining claims, read [same-owner rework](references/rework.md). Use the explicit CAS/idempotent transition and fresh packet receipt; do not release/reassign merely to reset task state or review counts.

For an existing pre-0.5 project, read [contract migration](references/migration.md). Archive exact old state bytes and retire internal limits through an explicit project-local CAS transition; never reactivate historical accounting or infer account billing from it. Installation does not migrate projects.

For source observation after a retained failed review, read [diagnostics](references/diagnostics.md). Keep the original task, owner and failures. A genuinely changed method may continue after a completed-but-insufficient observation with actual scope/permission, anchored provenance, independent judgment and fresh ACK. Identical attempts are deduplicated; observation authority does not automatically grant correction or product acceptance.

If an observation is closed as known `not_executed` after environment initialization failed, the same reference defines exact-command permission recovery. Append separately reviewed submission authority while preserving the closed result; ordinary command-specific tool authorization still applies and can refuse. Installing this patch does not refresh a project's contract or ACKs.
