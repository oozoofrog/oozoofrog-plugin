# See it fail

Trust only checks that you saw fail for the right reason. Keep checks that fail when behavior breaks and pass when only internals change.

**Why:** A check that was green from its first run proves nothing yet. A "must not" rule and a test written after the code are usually green from the start. A check that pins internals breaks on harmless refactors and still misses real regressions.

**How:**
- Choose the kind of check. Add or change a test only in three cases: T2 tracing needs it, the project's rules or the existing suite for that area require it, or the user asks. Otherwise the failing check is a rerunnable repro or a real-surface run.
- Write the check first. Make it fail on an assertion, not on a missing symbol. A compile error only says that the code does not exist.
- For a check that is green from the start, inject a violation. Confirm that only this check goes red. Revert the violation.
- Read the failure message. Confirm that it names the behavior you meant, not an unrelated error.
- Add a control case: an allowed input that the check must not flag.
- Assert on observable behavior (output, response, stored state). Do not assert on private calls or call order.
- At the end of a unit, inject defects one at a time and record which check caught each one.

**Stop:** Do not cite a check that you never saw red as verification. Do not edit a check to make it pass. Do not add a test that the three cases above do not call for.

**Evidence of use:** a table "injected defect → check that caught it" in the report or the record; no injected defect left in `git diff`.
