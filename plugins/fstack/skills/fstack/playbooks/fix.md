### Fix
**You own one defect. Every shipped line comes from observed evidence.**

1. Ask only about new decisions. For a review memo, confirm that it meets `principles/evidence-before-change.md`. If it does not, report the memo as unsupported and stop.
2. Reproduce the defect on the surface where it was seen. Record the numbers. Check the sibling paths.
   - If it does not reproduce, synthesize the trigger or add instrumentation.
   - If a live repro is impractical, for example a race, a counterexample test or direct code reasoning with a stated trigger counts as the reproduction. Label it so in the report.
   - If it still does not reproduce, stop without a fix. Ask for the exact command, the environment, the full output and the input.
3. Narrow the cause by bisection with runtime evidence. Write one cause sentence that explains every symptom. If two fixes based on one premise fail, test that premise directly.
4. If the cause is in the documents, work in this order: decision → check → code → other documents.
5. Write a check that fails for the right reason. It is a test only under the test rule in `principles/see-it-fail.md`.
6. Make the smallest fix at the root cause.
7. Run the full suite. Repeat the experiment from step 2. Record a before/after table. For a consequential fix, run the micro lens on the final diff (`references/review.md`) and close each finding.
8. Reinject the defect. Confirm that the new check catches it. Revert the defect.
9. Run `playbooks/wrap-up.md`. If a commit is allowed, commit the fix separately from the records.

**Report:** symptom, cause, fix, before/after table, checks added, rejected alternatives, what was not fixed, wrong first guesses, the memo's closure state (Fixed, Rejected with evidence, Unresolved).
