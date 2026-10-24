# TDD plan: remove harness budget feature

This public implementation checklist uses synthetic fixtures only. Project state, local installation evidence, participant acknowledgements and approvals stay private.

- [x] Review the design and remove the superseded resource-policy implementation rather than retain a second control engine.
- [x] RED: budget-free initial state, CLI begin without reserve, packets without budget/headroom/estimated token targets, no synthetic charge, reported usage unknown=null; verify old budget interface cannot reactivate history.
- [x] GREEN: remove budget/reservation/charge/increase paths from harness, adapter/controller, schema and policy. Keep ownership, current ACK/model, actual permissions, run identity and uncertain holds. Use one reporting helper for actual supplied usage, not a new resource guard.
- [x] RED: exact raw-byte archival migration with synthetic exhausted-accounting fixtures; preserve failures/claims/artifacts/history. Reject stale raw/parsed CAS, conflicting IDs and active/uncertain runs. Verify pre-rename atomic failure.
- [x] GREEN: pure migration plus exact-bound `contract_migrate` transaction; archive obsolete contract/run fields as private immutable history; fresh revision/ACK required.
- [x] RED: adapter/controller synthetic transports continue after formerly exceeded reserve/ledger references, retain null usage, and honor actual provider/security errors. Remove arbitrary byte/4 packet and review-count stops without weakening fresh review or actual provider capacity.
- [x] GREEN: delete obsolete quota branches; keep checkpoint projections and actual failure evidence. No repeat unchanged broad baseline suite.
- [x] RED: local CLI migration and synthetic Float32 pre/post conversion, insufficient-evidence predecessor, exact retained method seed, changed observation, dedup, CAS, missing ACK, uncertainty, denial and scope guards. Preserve original product FAIL and require actual current independent review for acceptance.
- [x] GREEN: append-only method-bound follow-up without reservations/count quotas. Permit legitimate same-owner changed work through explicit reviewed transitions; preserve all original records.
- [x] Update runtime/plugin guidance mirrors, schema, README/changelog and manifests to 0.5.0. Remove active budget documentation/flags.
- [x] Run affected complete harness suite, distribution/mirror/integrity checks and final diff using synthetic projects and isolated temporary homes.
- [x] Freeze source for independent review. Address findings with regression first; report actual checks and limits.

Synthetic tests and fixture acknowledgements do not establish actual project adoption, product acceptance, native runtime identity or permission to execute a real project.
