# Independent review

Use one independent reviewer by default. Use two lenses (`## Two-lens review`) only when one target holds both a design question and code.

## Reviewer brief

Send this brief to any generic subagent the host offers. Fill the brackets. Give paths only. Do not include your conclusions.

```text
You did not write this change. Review it against its documents and the user goal.
Target: <commit, diff range, working tree, or document path>
Documents: <spec, ADR, plan and project rule paths>
User goal: <one sentence>
Steps:
1. Scope: list the changed files and flag files that do not belong.
2. Documents: read the requirements and rules that apply.
3. Compare: check each requirement against the code and the tests.
4. Experiment: build and run in a scratch copy, never in the user's tree. Try boundary inputs.
5. Find decisions that the code made and no document records.
6. Keep a finding only if you can name the contract, the trigger, the evidence and the consequence.
If nothing meets that bar, return "no actionable findings" and the scope you checked.
Write the memo table, then three closing lines.
```

## Memo table

| # | Finding (contract, trigger) | Consequence | Label | Evidence | Status |
|---|---|---|---|---|---|
| 1 | <which contract breaks, under which input> | <what goes wrong for whom> | Verified / Read / Inferred / Question | <command and output, or path and line> | Open / Fixed / Rejected / Unresolved |

Fill `Status` on a re-review. A first review leaves it Open.

Map the micro lens claim states to these labels: Confirmed and Contradicted are Verified (name the check), and Unverified is Read, Inferred or Question, by how far the lens got.

Closing lines:
1. Commands run.
2. Checks not run, and why.
3. The memo to read first.

## Two-lens review

- Use it when one target crosses component boundaries, changes a T2 contract, or holds a contested design. Otherwise use one reviewer.
- Run one agent per lens. A lens agent creates no further agents and edits no files.
- The lenses may frame the problem and collect evidence at the same time. When the micro work depends on a design choice, finish the macro lens first.
- Without independent agents, run both lenses yourself and report a single-agent fallback (`references/delegation.md`).

## Macro lens brief

```text
Lens: macro (design). You did not write this change.
Target and documents: <paths>. User goal: <one sentence>.
Question: will this approach solve the user's whole problem, from input to result?
Check the assumptions, the boundaries between parts of the system, the effects one part has
on another, the fit with the current architecture, and the decisions already recorded.
An adequate design stays. Suggest another approach only for a limitation you can show with
evidence, or when the user asked for options.
Return the concerns you can support, or "no actionable findings", with the scope you checked
and your remaining uncertainty. Apply principles/evidence-before-change.md.
Edit no files. Create no agents.
```

## Micro lens brief

```text
Lens: micro (contracts and code). You did not write this change.
Target and documents: <paths>. User goal: <one sentence>.
Check the concrete contracts, the data flow and control flow, the edge cases that matter,
the failure paths and the compatibility with callers. Use the code, the tests and primary
documentation as evidence.
Sort every recorded claim you rely on as Confirmed, Contradicted or Unverified.
For each defect, give the broken contract, the trigger, the consequence and the evidence.
Label each hypothesis you did not test.
Return the state you checked and the findings you can support, or "no actionable findings".
Edit no files. Create no agents.
```

## Reconcile

- Before synthesis, send the micro lens each consequential macro finding that it has not checked. Do not re-verify findings that evidence already covers.
- Allow one focused follow-up for each material conflict. After it, decide by evidence, not by role or by agreement, or report the conflict as Unresolved.
- Either lens may challenge any consequential claim.
- Pass summaries with paths and check results between the lenses, not transcripts.

## Adversarial lenses

For a risky change, add lenses such as security, concurrency or data loss. Use one reviewer per lens. Add a lens only when it is distinct from the others. Keep a finding only if a rerun of its command reproduces it.
