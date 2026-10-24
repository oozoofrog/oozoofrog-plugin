# Same-owner evidence-based rework

Use `rework` to correct a genuinely failed deliverable without losing ownership, original artifacts, FAILs or history. Ordinary first rework requires exact full-state CAS, registered leader requester, original ready-for-review task/member, latest actual fresh FAIL, explicit reason and fresh decision evidence. All runs/controls/handoffs must be resolved. Its receipt is idempotent; new work requires an actual fresh packet ACK and current permissions.

An unchanged failure is not permission for meaningless repeated attempts. For materially changed further work, or correction following a diagnostic-only phase, use the cause/method/authority-bound rework form described in [diagnostics](diagnostics.md). There is no fixed review-count or total-attempt quota. Preserve every prior receipt and require genuine current-artifact independent review before acceptance. A previous PASS does not override a later FAIL or stale artifact.

Source/skill installation, contract migration, native configuration and real work are separate. None is automatic and this workflow grants no new access.

## Additional claims while awaiting review

When a drained original task remains `ready_for_review` and needs additional integration files, use `claim_expand` before preparing separately authorized correction. The existing `claim` operation still accepts only assigned/running tasks. Expansion preserves the owner, state, purpose, context, kind, resources, artifacts, FAILs, diagnostic snapshots, retained authority records and all historical entries. It appends the sorted union of old and additional claims, advances the revision, removes the current task authority mapping and invalidates every packet ACK. Existing scope requirements remain intact.

Supply an event with these fields:

```json
{
  "op": "claim_expand",
  "request_id": "stable-integration-claims-id",
  "project": "exact current project goal",
  "project_root": "/absolute/canonical/state-directory",
  "task": "original-task-id",
  "member": "current-execution-owner-id",
  "source_sha256": "harness.digest(parsed current state)",
  "source_raw_sha256": "sha256(exact current state file bytes)",
  "policy_hash": "current effective contract digest",
  "additional_paths": ["/absolute/canonical/additional-file"],
  "reason": "Concrete reason the original task needs these claims"
}
```

Use `run.py harness --state state.json apply --event event.json`. The state directory and every path must already be canonical; aliases, relative paths, duplicates, stale owner identity, stale contracts/CAS and other-task overlaps are refused. Existing claims cannot have changed through symlinks. Same-task parent/child claims remain explicit and usable; different tasks conflict even when their owner is the same. Shared resources are preserved and must not conflict. Drain all project runs, uncertain outcomes, unresolved controls and in-flight handoffs first. Pending diagnostic grants for this task must be legitimately resolved before expansion; this operation cannot cancel them or rewrite their immutable snapshots. A current checkpoint must still verify.

Keep the request ID and exact event after uncertain output. Identical committed-ID readback is read-only even after later state changes, and returns the historical transition plus current observation. A conflicting event with the same ID is refused. An uncommitted stale-CAS event must be rebuilt from a fresh read, without silently broadening its paths.

Expansion records ownership only. It grants no native permission, correction, execution, or acceptance authority and requires no new human approval for this administrative step. After expansion, use the existing applicable correction authorization and evidence workflow, obtain a fresh packet ACK, and begin separately. Existing failed-review and artifact freshness checks still apply to correction/review; expansion preserves their original truth without inventing a new FAIL or PASS.
