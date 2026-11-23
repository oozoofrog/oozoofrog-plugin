# Trace by ID

Use the IDs `AC-<goal>.<n>` and `R<n>`, and number ADR rules. Never renumber. Test names start with the ID token. Run the trace script.

**Why:** "Every requirement has a test" is only checkable when requirements and tests share a key. Renumbered IDs break every old reference without notice.

**How:**
- Define an AC ID in the first cell of a spec table row, such as `| AC-1.2 | MUST | … |`. Define a rule ID in the first cell of a domain table row, such as `| R4 | … |`.
- Retire an ID by writing `Retired (YYYY-MM-DD): <reason>` in another cell of its row, or a cell that holds only `Retired`. Prose that only starts with the word, such as "Retired accounts are hidden", does not retire the row. Keep the row. A retired ID needs no plan reference and no test; the script notes a plan that still references it. Never reuse or renumber it.
- In the plan, put IDs in a table cell that holds only IDs, such as `| AC-1.1, R4 |`. Name each ID; the script does not expand ranges. Prose is not a reference.
- Start each test name with the ID token: `AC-1.2` → `ac1_2`, `R4` → `r4`. Only test declarations count. A defined name may put `test` or `test_` first; after the token comes `_`, `(` or a letter, never a digit (`def test_ac1_2_rejects_empty`, `func TestAC1_2Rejects`). A title counts as the first string of a test declaration (`it("AC-1.2 rejects empty")`, `@DisplayName("AC-1.2 …")`, `t.Run("ac1_2", …)`, `Scenario: AC-1.2 …`). Variables, call sites, comments and other strings do not count. The script's `--help` lists every declaration form and the scan's limits.
- Run it from the project root: `python3 -I -B "<skill-dir>/scripts/trace.py"` (add `--no-tests` before tests exist). `<skill-dir>` is the absolute directory of the skill's `SKILL.md`. A relative `scripts/trace.py` does not exist in the project, and a run from the skill directory finds no project documents.
- When the project's runner can list its tests, prefer `--names-from "<list command>"`, such as `pytest --collect-only -q`, `go test -list .` or `swift test list`. It checks the real test inventory instead of the static scan. `npx jest --listTests` lists files, not test names, so it does not work. A failing, silent or slow command gives INCONCLUSIVE, never PASS.

**Stop:** Do not change IDs, tests or the script to make the trace pass.

**Evidence of use:** the `trace:` line and its counts in the report.
