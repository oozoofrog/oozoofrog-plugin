# Smallest sufficient change

Build only what the unit's check requires. Subtract first. Write deferred items down instead of building them. Defects outside the scope become memos.

**Why:** Extra code needs review, tests and maintenance that nobody asked for. A "might as well" change mixes unrelated risk into the unit and hides it in the diff.

**How:**
- Before adding, look for code to remove: dead paths, needless layers, duplicate decisions.
- Size the diff against the exit condition. Each changed line serves the check or the cause.
- Add an abstraction only when a second real caller exists.
- Put ideas for later in the remaining-work list, not in the code.
- Record defects outside the scope as memos with evidence. Do not fix them in this unit.

**Stop:** Do not widen the scope without the user's request. A small diff does not justify a patch at the wrong place.

**Evidence of use:** a "Remaining" list with deferred items and memos; a diff limited to the unit.
