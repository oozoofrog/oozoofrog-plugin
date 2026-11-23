### Wrap-up
**You own the record of the step.**

1. Read `git status` and `git diff --stat`. Look for foreign files, scratch leftovers and injected defects that were not reverted.
2. If the project keeps a journal, write the entry before any commit. Write other durable records only when something durable changed (`references/records.md`). Otherwise put the decision ledger in the report.
3. Write the report (`references/report.md`) in the user's language.
4. If no commit is allowed, go to step 7. A commit is allowed only on a user commit request, or as a local commit under a drive grant.
5. When a commit is allowed:
   - Stage explicit paths.
   - Ask before you include files you did not create.
   - Keep code commits separate from record commits.
   - Follow the project's message convention.
6. Push only on request (G1). Never rewrite pushed history. Verify the result with `git status -sb`.
7. Stop according to the pace. In step pace, end the report with the next-step line as its last line: `Next step: <candidate>` or `다음 단계: <후보>`. In drive pace, return to the loop unless the predicate is met or a dead end was reached; then stop and report.

**Report:** per `references/report.md`, plus the commits and the excluded files with reasons.
