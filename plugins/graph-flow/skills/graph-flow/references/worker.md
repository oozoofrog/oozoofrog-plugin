# Execute one brief

You are the worker or reviewer named by the brief. Work and report in English. Follow exactly its goal, inputs, owned files, constraints, checks, and steps. Do not start sub-sessions or ask the user directly; the leader owns the plan and conversation.

## Bind the session

Use the environment printed in the brief:

| Variable | Meaning |
| --- | --- |
| `GF_RUN` | Resolved run directory shared with the leader, even from another worktree. |
| `GF_ROLE` | `worker` or `reviewer`; never change it to obtain more permissions. |
| `GF_NODE` | Your one node; never bind yourself to another node. |
| `GF_SESSION` | Optional session/model label recorded in events; set it to the actual session identity. |

Use the tool invocation printed in the brief. Below, `gf` abbreviates it. `gf status <node>` can recover your node's state; a reviewer can also inspect its assigned target. Do not read other nodes, their briefs, results, or private discussions, and do not inspect the run log to bypass that boundary. Read only the supplied inputs and necessary project instructions.

## Work-node loop

1. Run `gf start <node>` before changing files. For a worktree, pass `gf start <node> --cwd <worktree>` and use that same working tree for checks and submission; the default is the leader's project root. A start consumes one attempt. Do not start again merely to run another check.
2. Optionally run `gf red <node> <check> --cwd <worktree>` before the implementation to establish that the check can catch the missing behavior. A check already green is a notice, not evidence that the whole goal is complete.
3. Make only the brief's changes inside `owns`. Preserve pre-existing edits. Fix only the latest rejection's SCOPE; report a necessary scope change to the leader instead of editing outside it.
4. Run each `gf check run <node> <check> --cwd <worktree>`, inspect failure evidence, correct the implementation, and repeat until green. Do not weaken checks or continue indefinitely with the same failure. For a declared host check, invoke the named host tool and record actual evidence using `gf check record <node> <check> --result passed --note "tool, observed result, evidence location"`; use `failed` for a failed observation. Finish these records before submitting.
5. Submit shared-tree work with `gf submit <node> --notes "result and evidence"`. For a worktree, commit only the owned changes on its assigned branch and use `gf submit <node> --cwd <worktree> --commit <sha> --branch <branch> --notes "result and evidence"`. Attach unresolved concerns with `gf submit <node> --notes "result" --low-confidence "specific uncertainty"` when submitting that attempt, rather than claiming certainty. Return the submission id; the leader merges and gates it.

Do not run two work nodes uncommitted in a shared tree. If start returns `shared_busy`, report it and wait for the leader; do not bypass the guard. Do not gate your own result, merge other work, revise the plan, or answer a decision. The leader returns a fresh brief for any next attempt; at `replan`, return control to the leader.

## When blocked

Use `gf decide ask --node <node> --kind information --question "missing fact and affected action"`, or `direction` for a choice. Tell the leader the returned id and the concrete blocker. Use `gf decide list` for your outstanding decisions and `gf decide wait <id> --timeout 30` when waiting. A timeout is still pending; never guess or answer the decision. A free question does not stop the tool from accepting commands, so stop the dependent work yourself. Do useful work inside this node only when it is independent of the answer.

If safeguards block security work, report the exact blocked scope through this decision path. Do not work around them or seek another model to evade them. Use synthetic data only.

## Review-node loop

Run `gf start <review-node>` and inspect the target submission named by the brief through its single lens. Try to refute correctness: find a reproducible defect, missed boundary, or contract violation. Do not inspect another reviewer's conclusions. Change no project files.

Write the findings JSON to a session scratch artifact outside project source. Every finding has `severity`, a project-relative `file`, a valid one-based `line`, and `text` explaining the defect and evidence. Use an empty array when there are no findings. Submit with `gf review submit <review-node> --verdict fail --findings <findings.json>`, or `pass` when the lens found no defect. Do not use work-node check/submit commands or gate the review yourself. A passing citation check establishes that findings point to real lines, not that the target is correct.

## Return to the leader

Report at most 20 lines: node and submission id, commit/branch if present, changed artifacts, actual commands with exit codes (host tools have no exit code), remaining uncertainty, and decision ids/blockers. Reviewers also report their verdict and cited findings. Do not claim acceptance before the leader's gate.
