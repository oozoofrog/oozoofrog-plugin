---
name: compare-solutions
description: "여러 해법 비교·통합. Spawn N parallel candidates at the same task, pick a base, graft the strongest parts of the losers into it. Use for /compare-solutions, 'arena this', 'throw it in the arena', or when one attempt at a non-trivial artifact would lock in the wrong shape."
disable-model-invocation: true
---

# Compare solutions

Use the [host profile](../fstack/references/host.md) for tool calls, settings, installed resources and optional capabilities.

Open a todolist with one entry per phase (Frame, Fan out, Cross-judge, Pick, Graft, Verify) before launching anything.

## Phase A: Frame

Every candidate gets the same prompt, so the prompt is the contract.

1. State the artifact each candidate is producing.
2. Derive the rubric, 3-6 concrete gradeable criteria for what success looks like on *this* task. It is the picker's tool in Phase D. Candidates only see the task.
3. Read the ordered `arena runners` role using configure-models. Use the requested model for each arm when available. Record missing arms. When no count or list was supplied, select available distinct models where possible and disclose the actual panel.
4. Use one host-managed worktree or one directory under the permitted scratch root for each candidate.

## Phase B: Fan out

Start the candidates through the host. Send each the same task and grounding, its own output location and the request for an artifact and short rationale.

If a candidate produces no output, proceed with N-1 and note the dropout.

## Phase C: Cross-judge

After candidates finish, read `arena cross-judge pool`. Select the first available read-only judge whose resolved vendor differs from the parent's. When none qualifies or the vendor is unknown, record the missing independent verdict and continue to Phase D. Give the judge anonymized candidates and the rubric.

## Phase D: Pick a base

Read every candidate end to end before picking. Score each against the rubric criterion by criterion, not on holistic feel, and compare with the cross-judge when Phase C ran one. Agreement on the base confirms the pick. Disagreement means one of you is biased or the rubric was ambiguous. Read both rationales before deciding.

Pick the base a future maintainer can extend most easily without breaking invariants. When two feel tied, prefer the cleaner boundary or smaller API, per the Laziness Protocol.

## Phase E: Graft

Walk each losing candidate once more for what is worth porting into the base, usually one or two things per candidate, not most of it. Fold each graft in by hand, per the **principle-rethink-design** principle skill, so the result stays coherent under one mental model. Don't paste mechanically.

If the candidates converge on one shape, that is strong agreement. Note it and ship the consensus shape. No graft is needed. If they wildly diverge, Phase A was under-specified. Reframe and re-run rather than averaging the divergence.

## Phase F: Verify

Verify the synthesized artifact like any other output, per the **principle-verify-real-behavior** principle skill. If verification finds a problem the arena missed, either Phase A was wrong (re-frame and re-run) or a candidate caught it and you missed the graft (go back to Phase E). Don't paper over it.

## Outputs

One synthesized artifact, with a short synthesis note alongside naming the base and why, the cross-judge's verdict or that Phase C skipped the judge, each graft with its source candidate, what was rejected and why, any convergence or dropouts, and the verification result.
