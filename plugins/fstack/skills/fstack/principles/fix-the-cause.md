# Fix the cause

Write one cause sentence that explains all symptoms, and fix there. After two failed fixes on one premise, test the premise. Add no masking guards.

**Why:** A guard where the symptom shows up hides the defect and gets copied. A premise that is wrong makes every fix built on it fail in a new way.

**How:**
- Reproduce first. When a live repro is impractical, for example a race, a counterexample test or direct code reasoning with a stated trigger counts as the reproduction; label it so. Then narrow the cause with runtime evidence where you can get it, not by reading alone.
- Write the cause sentence. Check that it explains every observed symptom, including the sibling paths.
- Fix at the first place where the system went wrong.
- After a second failed fix, write the shared premise as one sentence and test it directly.
- Do not add retries, swallowed errors, clamped values or null guards that only hide the symptom.

**Stop:** Do not ship a fix without a cause sentence. Do not start a third fix on an untested premise.

**Evidence of use:** the cause sentence in the report; a before/after table; the premise test when a fix failed twice.
