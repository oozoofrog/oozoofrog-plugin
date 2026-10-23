# Same-owner rework (0.3.1 patch source)

A task in `ready_for_review` retains its claimed paths, so neither `begin` (assigned/running only) nor `reassign` (released claims only) can safely reopen it. Use the additive `rework` event only to address the latest canonical failed review under the same owner and original scope. It is not reassignment, acceptance, a review-limit reset or an execution grant.

A registered leader with a fresh file-backed identity claim requests the transition. Provide a nonempty reason and fresh decision-evidence file. These are auditable claims, not native caller authentication. The task must be exactly `ready_for_review`, its latest actual stored review must be `fail` with an unchanged report, and a review allowance must remain. Each failed-review index/digest can authorize only one rework. All project runs must be terminal; pending/uncertain controls and in-flight handoffs block the revision change.

Save the following JSON event, substituting actual values:

```json
{"op":"rework","request_id":"unique-correction-id","task":"task-id","member":"unchanged-owner","requester":"registered-leader","source_sha256":"FULL_STATE_CANONICAL_DIGEST","reason":"Address the failed finding within the approved scope","evidence":"ABSOLUTE_DECISION_EVIDENCE_FILE"}
```

`source_sha256` is `harness.digest(parsed_state)`: SHA-256 over Python `json.dumps(state, sort_keys=True, ensure_ascii=False).encode()` with default separators. It is not the raw JSON-file SHA. Capture the complete current state, including history and nonrevision mutations. Submit through `run.py harness --state STATE apply --event EVENT` or installed `harness.transaction`; do not edit state JSON manually.

The locked transaction preserves every task field except state (`assigned`), existing claims/resources, all artifacts/reviews/failure counts, runs, reservations/accounting and full prior history. It adds a request receipt, auditable history/change and revision boundary, and removes the owner's old ACK. Read the fresh packet and record an actual revision/epoch/digest receipt before any new `begin`; never generate another participant's ACK. A new completion still needs handoff and independent review. Remaining review allowance is unchanged.

Exact duplicate request ID and payload return the current state without saving, appending history or charging again—even after later activity. CLI output distinguishes the original committed transition from current observed owner/state/revision; it never reports a later task as newly assigned. A conflicting payload or a fresh request with stale full-state digest is refused. A fresh ID cannot reuse the consumed old failed review.

Before atomic file replacement, storage failure leaves original state bytes intact. Failure after replacement (such as directory fsync failure) can mean a full transition committed with durability uncertain. Read the authoritative state and request receipt before retrying. The same exact request permits idempotent readback; never guess a new ID or reset accounting. Fault-injection tests do not prove real power-cut durability.

## Adoption and current installed overlay

This is source0.3.1, separate from staged0.4 Astra/Fast work. It is not installed automatically. Active project contracts must remain unchanged until actual owner safe holds and a reviewed preserving installer are ready. The public generic installer is not a private-overlay migration recipe.

An installed requested-default Astra overlay changes global AGENTS outside the managed block and has its own journal. A future preserving runtime migration must first back up and remove that overlay using its reviewed helper; preserve exact private guidance and old journals; apply/doctor the reviewed runtime patch; then recreate the overlay against the new baseline and verify both doctors/ordered rollback. Do not rewrite historical journals. That complete private migration is not proven by this patch and must be separately staged/tested before installation. Project policy migration/checkpoint and real fresh member ACKs follow installation; no project operation or resumption is automatic.
