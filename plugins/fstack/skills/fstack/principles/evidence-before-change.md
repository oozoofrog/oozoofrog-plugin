# Evidence before change

Act on a finding only when it names four things: the contract it breaks, the input or event that sets it off, evidence from the code as it is now, and a consequence that matters. A clean result is a success. Reopen a closed finding only on new evidence, a changed requirement or changed code.

**Why:** Pressure to find something produces invented edge cases, generic hardening and churn. Each change without support adds risk and proves no benefit.

**How:**
- Before you propose or apply a fix, check the four parts: contract, trigger, evidence, consequence.
- Evidence can be a test, a counterexample or direct reasoning over the code. Not every defect needs a live repro.
- Label a hypothesis that you did not test Inferred. Run a bounded check when the consequence is large enough.
- Missing evidence means limited confidence. It is not a proven defect, and it is not a clean result.
- An explicit redesign, style or optimization request sets its own acceptance criteria. It does not license changes to unrelated behavior.
- Nothing needs a minimum count: not findings, alternatives, edits, tests or records. Leave optional preferences unapplied.
- Close each material finding as Fixed, Rejected (with evidence) or Unresolved.

**Stop:** Do not change code for a finding without support. Do not open another review round or a backlog only to keep working. A repeated request is not evidence that something is wrong.

**Evidence of use:** memo rows that name contract and consequence; a "no actionable findings" line with the scope checked; closure states in the report.
