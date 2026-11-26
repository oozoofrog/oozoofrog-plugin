---
name: review-code-comments
description: "코드 주석 검토. Review comments in the requested files or diff and report supported findings. Apply corrections when the user requests edits."
disable-model-invocation: true
---

# Review code comments

Review the files or diff named by the user. Otherwise inspect the working tree and branch changes against the base branch. Follow the [review criteria](../../agents/comment-sicko.md). When an independent review is requested and available, give the reviewer this same read-only scope. Disclose any unavailable requested review.

Trace each candidate to its symbol, caller, public contract or external constraint. Report the location, evidence and proposed action. Keep uncertain constraints visible. Use source inspection when it settles the finding. For an executable check, prevent cache and build output in the reviewed tree (for example, use Python’s -B option), or run it in a scratch copy. Compare the final worktree status with its initial state, including untracked files. A review ends with the findings.

When the user requests edits, apply only supported corrections within the requested scope. Removing a comment must preserve its constraint. For a suppression, verify the affected check before removing it. Report any application-code fix outside the requested scope as a separate finding. Verify edited files with the relevant checks.
