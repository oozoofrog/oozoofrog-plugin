# Independent review

Two lenses check substantive work: the macro lens checks the design before it is fixed, and the micro lens checks contracts and code after consequential edits. `## When the lenses run` says which lens runs when. A target with no design question gets one independent reviewer with the reviewer brief or the micro brief.

## When the lenses run

A substantive task has an edit that changes behavior under the exit condition, or a decision that others will rely on. A consequential edit changes behavior under the exit condition or a contract. A trivial edit gets no agents.

| Work | Macro lens | Micro lens |
|---|---|---|
| Trivial edit | none | none |
| T1, one component | none | once, after the consequential edits |
| T1 that crosses components, or a contested design | before the first edit | after the edits |
| T2, or an escalation from T1 to T2 | before a decision is marked Approved and before execution starts | after the real-surface run of each build unit |
| Fix | only when the cause is in the documents, or one premise failed twice | after the before/after run |
| Drive | once, after the split into units | for each kept unit that touches a contract, and when the predicate passes; never for each iteration |
| Review playbook | when the target crosses components, changes a T2 contract or holds a contested design | always |

- An explicit user request for two agents, both lenses or a sequential debate overrides the table when the host supports it. In a debate, the lenses answer each other in turns until the one follow-up for each conflict is used.
- Pace does not change the table. It changes what happens to a finding that hits a gate: stop in step pace, park in drive pace.
- A lens finding is not an approval. A finding that changes an approved document is G3. A finding on a user-owned call is G2.
- A fork that a run can settle goes to `playbooks/prototype.md`, not to the macro lens.
- A request to inspect or explain this skill is not a request to run the lenses.

## Shared brief

Give both lenses the same compact brief: the goal, the acceptance criteria, the constraints, the paths, the recorded claims to verify with their status, and the known uncertainties. The proposed approach is the target. Do not include your verdict on it, full logs, the whole conversation or unrelated records. Send no credentials or sensitive values.

## Reviewer brief

Send this brief to any generic subagent the host offers. Fill the brackets. Give paths, not file contents. Do not include your conclusions.

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

- Run both lenses on one target when `## When the lenses run` asks for both.
- Run one agent per lens. Only the main session creates agents. A lens agent edits no files, with one exception: the main session may assign the micro agent isolated implementation ownership of files that no other agent writes. That agent is then the author of those files, so the main session or the macro lens checks them.
- Do not replace a lens that returned no findings.
- Do not finalize a decision that depends on a lens before its result arrives.
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
Apply principles/evidence-before-change.md.
Create no agents. Edit no files unless the main session assigned you isolated implementation ownership.
```

## Reconcile

- Before synthesis, send the micro lens each consequential macro finding that it has not checked. Do not re-verify findings that evidence already covers.
- Allow one focused follow-up for each material conflict. After it, decide by evidence, not by role or by agreement, or report the conflict as Unresolved.
- Either lens may challenge any consequential claim.
- Pass summaries with paths and check results between the lenses, not transcripts.

## After edits

- Findings from before an edit and tests that passed before it do not certify the changed code. Check the final diff against the acceptance criteria.
- Rerun only the checks that the edit invalidated. Keep the evidence that it did not touch. Never weaken an acceptance check to get a pass.
- Reuse the lens that knows the area when an independent check adds value. Otherwise check locally and report that coverage as it was.
- Match each finding to the file state that the lens checked. A finding on an older state needs a recheck before you act on it.
- A review with findings is not complete work when the user asked for a change. Take each supported finding through `playbooks/fix.md`, then recheck.

## Adversarial lenses

For a risky change, add lenses such as security, concurrency or data loss. Use one reviewer per lens. Add a lens only when it is distinct from the others. Keep a finding only if a rerun of its command reproduces it.
