### Build
**You own one unit. Its exit condition is the bar.**

1. Restate the unit and its exit condition. At T2, copy the plan's verification IDs to the checklist. Run the full suite and record the baseline count.
2. Name the data shape before you write logic.
3. Write the outermost failing check first. It is a test only under the test rule in `principles/see-it-fail.md` (T2 tracing, a project rule or the existing suite, or a user request). Otherwise it is a rerunnable repro or a real-surface run. See it fail for the right reason.
4. Work inward with the smallest changes. Record each decision that the documents did not make.
5. Run the full build and suite. Record the counts as before → after.
6. For each check that was green from the start, inject a defect, see the check go red, then revert the defect.
7. Run the change on the real surface. Include inputs that are not in the tests.
8. At T2, from the project root, run `python3 -I -B "<skill-dir>/scripts/trace.py"`; add `--names-from "<list command>"` when the project's runner can list tests. Write the conclusions into the documents. Mark each edit to an approved document "needs confirmation".
9. Run `playbooks/wrap-up.md`.

**Report:** verification table, defect-injection table, real-surface results, AI decisions and rejected alternatives, rules not met, remaining work.
