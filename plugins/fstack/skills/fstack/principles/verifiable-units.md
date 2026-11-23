# Verifiable units

Work as known-good → one change → check → next. The failing check lands before the fix.

**Why:** A batch of changes that fails cannot tell you which change broke it. A check added after the fix cannot show that it would have caught the defect.

**How:**
- Split the work into units that each have their own check.
- Order the units so that the riskiest unknown comes first.
- Confirm a known-good state before each unit.
- Make one change. Run its check. Keep the change or revert it before the next unit.
- In step pace, keep a change in the working tree. Make a local commit only on a user commit request or under a drive grant. Push stays G1.
- When commits stack, keep the failing check in the same or an earlier commit than the fix.

**Stop:** Do not start a unit while the previous one is unverified. Do not batch all checks at the end.

**Evidence of use:** one verification row or trail row per unit; the suite green after each kept unit.
