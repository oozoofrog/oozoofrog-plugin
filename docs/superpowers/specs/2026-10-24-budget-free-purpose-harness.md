# Budget-free purpose harness 0.5.0

This public design describes removal of the internal budget feature. All examples and fixtures are synthetic; real project state, permissions and adoption records stay private.

## Intended behavior

The harness communicates purpose, completion criteria, roles/ownership, next action, observed failures, alternatives and verification evidence. It does not impose project/task token allowances, per-run reservations, synthetic charges, budget-increase approvals, fixed review-count allowances or a byte/4 packet-size stop. Actual provider context capacity, account quotas/usage/cost, actual user instructions, access permissions and security restrictions remain real facts; this package neither changes nor bypasses them. Unknown usage stays null, not measured zero.

## Minimal active contract

`initial(goal)` and CLI `init --goal` create budget-free state. `begin` and managed/controller CLI require owned task/run/context acknowledgment but no reservation argument. Remove active `budget`, `spent`, `context_limit`, `review_limit`, `budget_changes`, reserve/charge fields, budget operations and all budget/estimated-token usage cancellation paths. Unsupported old budget commands/flags fail as retired interfaces; they never modify or resurrect a historical allowance. No replacement advisory/user-budget engine is introduced.

Keep one current ownership/uncertainty ledger, unique run/operation IDs, actual current model/service configuration guards, canonical path ownership, fresh packet ACKs, in-flight concurrency scheduling and atomic writes. Scheduling reflects the sole execution-owner policy, not a token quota. Report provider usage when actually supplied as `reported_usage`, with provenance and missing/completeness fields; never infer actual billing from text bytes, reserve or old charges.

Packets expose purpose, task completion criteria/context, roles, critical decisions/constraints, next action, unresolved runs, latest failures and evidence/alternatives. They omit every active budget/headroom/reservation target. Existing checkpoint working views still reduce irrelevant context and preserve key obligations; remove the arbitrary 16000 byte/4 stop without claiming any increase in provider context capacity.

## Explicit, atomic legacy migration

Add `contract_migrate` with stable request ID, exact canonical state root/project, current parsed-state digest, current raw-state SHA256, target contract hash, scoped reason and independent leader/reviewer attestations. No new human budget approval is requested. Refuse active/uncertain runs, unresolved operations, stale CAS or changed source bytes. The transaction captures the **exact original state bytes** in an immutable, hash-pinned private historical record before changing the active shape. This preserves obsolete accounting, reservations, measurements, budget-change receipts, old packet limits and full history verbatim. Never replay any of them as active policy.

Retain task identity, owner, canonical claims, original artifacts/FAIL/reviews, terminal outcomes and actual usage claims. Move obsolete per-run packet/reserve/charge/measurement data into the archived original record; preserve active terminal/evidence/run identity and nullable reported usage. Append one migration receipt, update contract/revision and invalidate ACKs. No fake ACK and no business execution occurs. Exact duplicate migration is historical readback; conflicting ID or CAS fails. Pre-rename failure keeps canonical bytes unchanged; post-rename ambiguity requires readback, not another ID.

Expose a pure in-memory migration function taking supplied raw bytes and event. It verifies archived bytes/hash, unchanged product obligations/history and new packet content/size without writing a project. Packet-size reporting is information, not a replacement hard stop. A preview is never real project migration or adoption.

## Failures and changed work

Keep all actual failed reviews and require an actual fresh independent review of current artifacts before product acceptance. Remove fixed two-review quotas. A closed one-cycle diagnostic must not create a permanent ban on legitimate changed observation or later authorized corrective work. Active/uncertain execution still freezes ownership; permission denials remain unresolved until actual permission evidence establishes otherwise.

Add append-only `diagnostic_followup` for a genuinely changed observation after an observed terminal predecessor, including completed-but-insufficient evidence. No `max_reserve`/`reserve_estimate` or fresh human approval for unchanged authorized scope. Exact state/CAS, current contract, same retained ownership/claims, existing source permission, actual fresh ACK before begin, root cause and independent material-method judgment remain necessary.

The method fingerprint binds task/failure, actual collector/spec/input evidence and observation schema, ignoring IDs and cosmetic prose. Exact predecessor descriptor equality is required for prior follow-ups. A first legacy seed is reconstructed from its actual terminal run and explicitly linked retained artifact/manifest evidence, then independently reviewed and stored append-only. It must not require an invented old evidence format. Source-defined inputs may be labeled honestly only when frozen evidence actually covers them; otherwise name the missing owner record/seed step instead of asserting a permanent impossibility. Byte changes alone do not prove semantic improvement; the recorded independent judgment has that explicit limit. Same fingerprint/new ID, conflicting ID, uncertain predecessor, unresolved denial or scope expansion is rejected.

The original diagnostic/grant/result remains historical. Remove the old invariant that the task can never change again after any diagnostic. Preserve the original snapshot and provenance in history; require an explicit same-owner, cause/method-bound transition for new work, retain all FAILs/counts and require current review before acceptance. No silent acceptance, reset or fabricated product pass.

## Minimum preparation and regression

Use synthetic exhausted-accounting fixtures with generic claims, failed reviews and a closed diagnostic with insufficient evidence. Migrate through the real local CLI without any provider/model call. A synthetic Float32 conversion exercises indexed before/after bit patterns and the changed-method follow-up state flow. Fixture governance/ACK/actor records are never actual project permission or acceptance.

Tests cover budget-free creation/CLI/packets, progress after exhausted historical accounting, absent usage-triggered interruption, nullable usage, exact legacy raw-byte archival, stale/conflicting IDs/CAS, fresh ACK, uncertain/access/scope boundaries, same-method dedup, accepted changed observation and preserved product-review truth. No arbitrary context/review-count regression may reintroduce a new hard stop. Actual provider rejections remain rejected/uncertain as appropriate, without automatic retry.

Implementation clarification: validate predecessor methods with their retained original failure binding while binding the new request to the latest actual FAIL. Clear/inactivate correction authority when actor, canonical claims or current external permission change. A pending never-executed method may renew exact authority without contrived byte changes; consumed methods still require a meaningful changed approach. Fresh current review remains necessary for acceptance.
