### Review
**You own the findings. You do not own fixes or decisions.**

1. Set the target: a commit, a diff, the working tree, a design or plan document, or a whole document (conformance mode).
2. Read `git show --stat` or `git diff --stat`. Flag files that do not belong to the change.
3. If the target is not the working tree, export it to scratch with `git archive` and build it there.
4. In conformance mode, sort each MUST into four groups: enforced, held but unenforced, violated, not yet built.
5. Run boundary experiments. Record the numbers.
6. Choose the review mode in `references/review.md`: one independent reviewer (default), or two lenses (macro and micro) when the target crosses components, changes a contract or holds a contested design. Give paths only, not your conclusions. Add adversarial lenses only when each lens is distinct.
7. Reconcile per `references/review.md`: send consequential macro findings to the micro lens before synthesis, allow one focused follow-up for each material conflict, and after it decide by evidence or mark the conflict Unresolved. Keep a finding only if it meets `principles/evidence-before-change.md` and a rerun reproduces it.
8. Write the memo table. Label every row. If no finding survives, write "no actionable findings" with the scope checked. That is a successful result.
9. Run `playbooks/wrap-up.md`.

**Report:** memos, review mode (independent, two-lens, or single-agent fallback, with any reduced coverage), experiments, conformance table, what the reviewers found that you missed, and one question on how to handle the memos.
