# Encode in checks

Use the enforcement ladder: structure > script > test > prose. Build the tool that proves the work. Check names cite the rule source.

**Why:** A rule that people keep only by care fails on the first busy day. More prose does not stop a repeated mistake; a check does.

**How:**
- When the same correction arrives twice, propose a guard on the highest rung that fits: a type or file layout, then a script or architecture test, then a test, then prose.
- For repetitive work, write the smallest script that performs the work or proves it. Do the first item by hand, then confirm that the script gives the same result.
- Give the check a name that cites its rule, such as an ID or a document section.
- See the new check fail before you rely on it (`principles/see-it-fail.md`).

**Stop:** Do not add another paragraph for a rule that was already ignored. Do not build a framework when one script is enough.

**Evidence of use:** the new check, its source citation and its first red run.
