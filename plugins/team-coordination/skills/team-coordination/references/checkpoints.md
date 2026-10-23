# Checkpoints and compact continuation

A checkpoint gives a project a compact, reviewable working view while preserving its canonical history for audit and recovery. It does not rewrite or delete the source state. Each proposal binds to the complete current-state digest and the target effective policy/role/schema/runtime contract; a revision number alone is not a sufficient concurrency check. The source digest is the harness canonical-JSON digest (`sort_keys=True`, `ensure_ascii=False`, default JSON separators), not the raw state-file byte hash. Snapshot and copied object-file hashes are recorded separately. Do not substitute a raw state-file hash for a source digest unless the harness has verified and reported it.

## Prepare and review

Create a view JSON containing the compact facts and explicit treatment of history omitted from that view. The required fields are `constraint_indices`, `decision_indices`, `historical_constraints`, `historical_decisions`, `historical_summary`, `remaining_work`, and `task_contexts`. Each excluded historical constraint or decision must have an indexed entry with an explicit reviewed reason. Keep every task context nonempty and include unresolved blockers and recovery status in `remaining_work`.

Prepare the immutable snapshot and proposal with:

```sh
python3 -I -S -B run.py harness --state /absolute/project/.codex-team/state.json checkpoint-prepare --id cp-001 --view /absolute/project/checkpoint-view.json --evidence /absolute/allowlisted-evidence.json
```

Repeat `--evidence` for each exact allowlisted evidence file to include. Preparation writes `.stateparent/checkpoints/ID/snapshot.json`, content-addressed objects under `objects/SHA`, and `proposal.json`. Review the proposal against the current obligations and referenced evidence before approval. The owner and an independent reviewer must each approve the same proposal, source digest, and `target_policy_hash`, attest a safe boundary, and confirm that all current obligations remain represented. Commit requires the current effective contract to still match the reviewed target. If policy, roles, schema, or runtime changes after preparation, prepare a new proposal and obtain new owner and independent approvals; do not reuse approvals for the previous target.

The approvals JSON passed to commit has this shape:

```json
{
  "leader": {
    "member": "leader-key",
    "proposal_sha256": "<proposal digest>",
    "source_sha256": "<source-state digest>",
    "target_policy_hash": "<target effective contract hash>",
    "approved": true,
    "safe_boundary": true,
    "all_current_obligations_retained": true
  },
  "reviewer": {
    "member": "reviewer-key",
    "proposal_sha256": "<same proposal digest>",
    "source_sha256": "<same source-state digest>",
    "target_policy_hash": "<same target effective contract hash>",
    "approved": true,
    "safe_boundary": true,
    "all_current_obligations_retained": true
  }
}
```

Commit by applying a checkpoint event that names the prepared proposal and approval file:

```sh
python3 -I -S -B run.py harness --state /absolute/project/.codex-team/state.json apply --event /absolute/project/checkpoint-commit-event.json
```

The event uses `op: "checkpoint_commit"`, `candidate` set to the prepared `proposal.json` path, and `approvals` set to the JSON file above. `policy_refresh: true` also requires a nonempty `reason`. A committed checkpoint creates a smaller working packet. Obtain and record real current-context ACKs for that packet before starting work from it; a checkpoint file or approval receipt is not an ACK.

## Verify and restore

Verify a checkpoint read-only. Compare the returned canonical proposal digest with the separately approved pin; self-consistent bytes alone do not establish approval:

```sh
python3 -I -S -B run.py harness --state /absolute/project/.codex-team/state.json checkpoint-verify --directory /absolute/project/.codex-team/checkpoints/cp-001
```

The `checkpoint_restore` event verifies the archive and its permitted root location. It does not restore or rebind the original task, claims, or absolute evidence paths, and it does not resume execution. Use `directory` beneath the project root, the `leader` member key, and `safe_boundary: true`:

```sh
python3 -I -S -B run.py harness --state /absolute/project/.codex-team/state.json apply --event /absolute/project/checkpoint-restore-event.json
```

After restart, verify source-state and archive digests and checkpoint lineage before relying on the compact view. A successor checkpoint carries a verified portable closure of its ancestor proposal, snapshot, approvals, and referenced evidence, so verification does not depend on the former archive location. If a copied ancestor object is missing or corrupt, stop verification and report the blocker. A missing archive, digest mismatch, malformed data, or path escaping the permitted root is an integrity failure: preserve the evidence, stop the restore, and report the blocker. Do not silently recreate or discard history. Do not retry uncertain work because its outcome is absent from a compact view; reconcile the original operation first.

A digest proves byte identity only. It does not prove summary completeness, that an approval is genuine, or that an event occurred. Approval JSON is a recorded claim, not cryptographic identity attestation. Keep those limits explicit in review notes.

Checkpoints are for project state only. Never put credentials, authentication files, private transcripts, unrelated personal data, or machine-specific paths in a portable fixture or public checkpoint. Use synthetic identifiers and evidence in examples.

Filesystem publication uses fsync plus atomic canonical-state replacement. An fsync error is an uncertain durability outcome: read and verify the canonical pointer before any retry. Fault-injection tests simulate process boundaries; they do not prove behavior during an actual power cut or a complete Mac reset. Historical inspection never re-executes archived business commands.
