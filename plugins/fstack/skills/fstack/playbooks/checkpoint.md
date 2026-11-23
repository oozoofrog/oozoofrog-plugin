### Checkpoint
**You own the answer to "where are we". This playbook is read-only, except for recording approvals.**

1. Read the plan, `git log` and `git status`. Check for an upstream with `git rev-parse --abbrev-ref @{u}`. If it exists, read the diff against it. If not, report the local status and write "remote comparison unavailable: no upstream". That is neither an error nor a pass.
2. From the journal, the trail, the documents and the handoff document, collect remaining work, memos, items that need confirmation and unfixed items.
3. If T2 documents exist, run `python3 -I -B "<skill-dir>/scripts/trace.py"` from the project root.
4. Write four lists: plan remaining; uncommitted or unpushed; decisions awaiting confirmation; known unfixed.
5. If the user asked for confirmation, give each decision's location, content, recommendation, reason and validity condition, high impact first. Ask once and wait.
6. Record each answer with its source and the approval method (one by one, or as a batch).
7. Send answers that need code changes to `playbooks/fix.md`.
8. Run `playbooks/wrap-up.md`.

**Report:** the four lists with sources, the decision table, the approval method, and the next-step line from `references/report.md`.
