# Leader procedure

Use the [record contract](records.md) for field shapes and [executors](executors.md) when starting sessions. In the examples, replace placeholders with observed values; `gf` means the invocation in [SKILL.md](../SKILL.md). Keep the same run through resumed sessions. Let the tool write its events; never edit them to change a verdict.

## 1. Inspect the real project (P1, P6, P12)

Read project instructions, the affected code, existing tests, manifests, branch, and local edits. Identify the requested outcome, acceptance evidence, and existing authorization separately. Inspect existing `.graph-flow/runs/` directories and select the matching run; set `GF_RUN` to its resolved directory, then run `gf status`. Do not create a second run to escape a failure.

For new work, run `gf init <run-id>` from the project and set `GF_RUN` to the returned run path. Global options precede the command; for example, `gf --project <project> init <run-id>` selects a project explicitly. Record only observed capabilities with `gf host set <capability>`, such as `subagent`, `workflow`, `t3_delegate`, or `worktree`; this replaces the previous list. Do not claim an unavailable host tool. Preserve facts and their sources, assumptions, permission scope, project identity, and relevant revisions in the plan's additional `context` field.

On resume, inspect current files and `gf decide list` before reusing evidence. If a passed node's inputs changed outside the plan, use `gf reopen <node> --reason "changed input and evidence"`; this invalidates that node and its dependents. Preserve unrelated accepted work.

## 2. Resolve decisions before splitting (P1, P10)

Ask only for direction, missing information that inspection cannot recover, taste, or authorization. Ask as few consequential questions as possible, preferably before the split. Never ask for confirmation of something a check can decide. At planning, representative-output review, changed requirements, and completion, inspect whether a human decision remains; do not manufacture a question at every boundary.

When a run exists, record a question with `gf decide ask --kind direction --question "Which outcome takes priority?"`; use `information`, `review`, or `authorization` for the other kinds. Include a concrete recommendation and, when available, the reviewable artifact. Preserve earlier answers and their source in context; do not ask again merely to populate the log. Keep design acceptance separate from permission to publish, delete, or access anything. Silence and a wait timeout grant neither. The dashboard is the person's surface: do not start `gf serve`, read its token or key files, or call its HTTP API from an agent session; tell the person the command to run instead.

Use a decision node when downstream work must wait for an answer, giving it a named output such as `approval`. Once it is ready, `gf gate <decision-node>` records the question with the correct binding. A free question does not create a dependency: the leader must keep affected work undispatched until it is resolved. Only a person uses `gf decide answer <id> --outcome answered --answer "choice"` through the human terminal, or answers on the dashboard. Never impersonate that role, set its terminal flag, read its signing key, or translate a chat answer into a signed answer yourself.

## 3. Write the planning brief and graph (P1, P3, P4, P5, P9, P11)

Read `gf brief --plan` and `gf learn list`. Apply only constraints whose evidence, scope, and review condition still fit. Write a plan using the contract's schema; include the user's requirements and integration checks that exercise the assembled result.

Write the plan and node `title`, node `summary`, input `label`, check `title`, and decision-node/human-check `context` in the user's language. Name what the person receives and what a decision changes, using the [presentation field limits](records.md#3-plan). For example, for a Korean request: `{"title":"내보내기 만들기","summary":"사용자에게 모든 메모의 JSON 사본을 제공합니다.","needs":[{"from":"collect","artifact":"notes","label":"모은 메모"}],"checks":[{"id":"review","type":"human","title":"원본 메모가 모두 포함됐는지 확인","context":{"why":"공유 전 결과를 확인합니다.","if_approved":"이 사본을 사용합니다.","if_rejected":"누락된 메모를 보완합니다.","undo":"이전 사본으로 돌아갈 수 있습니다."}}]}`. These fields describe the flow; changing only their wording preserves accepted work.

- Split by blast radius: one bounded deliverable per work node. Declare exact `owns` paths, necessary `reads`, inputs, outputs, and a `max_attempts` no greater than three. Combine overlapping work or serialize it through a real artifact dependency.
- For each `needs` edge, name both the producer and the artifact that crosses. The artifact must be under the producer's `owns` or in its named `outputs`. Delete edges that mean only “and then.”
- Write a meaningful `cmd` check for each work node **before** its implementation. Make the check able to refute the requested behavior. Do not substitute a scope comparison, confidence, or a command that always succeeds. If no machine check exists, declare `human` honestly and inspect normalization's raised lane and approval requirement.
- Choose the lane by reversibility and blast radius, separately from model grade:

| Lane | Meaning | Example and gate requirement |
| --- | --- | --- |
| 1 | Reversible and contained | A local parser fix; deterministic checks and scope. |
| 2 | Reversible but wide | A shared API refactor; deterministic and integration checks, clean trajectory, and independent review. |
| 3 | Hard to reverse | A production migration or publication; prepare and verify first, then require a person's authorization for the specific action. |

Add a lane 1 `review` node with one `lens` and the work node as `target` for every effective lane 2 or 3 node. Its reviewer must use another model family. Name the target artifact in `needs`; a review can start once its target is submitted, before that target passes. Use grades `bulk`, `scoped`, `daily`, `large`, and `security` to route difficulty; see the [model table](executors.md).

For consequential actions, separate the reviewable preparation, an authorization decision node, and the action that consumes its approval. A post-submission lane 3 gate does not authorize an earlier external action. Reuse authorization only for the same scope and artifact; material changes require a new decision.

## 4. Validate and save (P1, P3, P4, P7, P9)

Run `gf plan validate <plan.json>`, fix every problem, then `gf plan set <plan.json>`. Read normalization notices before dispatching. A work node without a `cmd` check gets a higher effective lane (capped at 3) and a human check; `no_machine_check` is not a substitute for verification.

| Code | Fix |
| --- | --- |
| V1 | Supply correctly typed required fields, recognized kinds, and schema version 1. |
| V2 | Make node/check ids valid and unique; allow at most one scope or cites check per node. |
| V3 | Name an existing producer and an artifact it owns or declares as an output. |
| V4 | Remove a dependency cycle. |
| V5 | Supply work checks and command bodies, valid review target/lens/lane, valid decision question/kind with no checks, and cmd-only integration checks. |
| V6 | Choose lane 1, 2, or 3. |
| V7 | Remove concurrent ownership overlap or express its real dependency. |
| V8 | Use project-relative paths without parent traversal, Git internals, or graph-flow metadata. |
| V9 | Add a review targeting every effective lane 2 or 3 work node. |

Plan changes invalidate changed nodes and their dependents. Keep the same ids where the deliverable is unchanged; do not rename a node merely to erase its failed attempts.

## 5. Fan out ready nodes (P4, P5, P6, P9, P12)

Run `gf ready`, then `gf route <node>` for each candidate. Check actual host availability and routing's account/usage caveats. Record the actual choice with `gf assign <node> --executor <executor> --model <model> --effort <effort> --provider <provider> --family <family> --isolation <isolation>`. Generate `gf brief <node>` and start exactly one sub-session with that brief using the [executor procedure](executors.md).

Never execute an effective lane 2 or 3 work node inline, even if routing suggests it. If the host cannot supply a suitable worker or another family for review, record the missing capability and leave that node unverified. Uncommitted shared-tree work is serial; parallel writers need worktrees and committed submissions. Dispatch ready decision nodes to their gate, not to an agent. Do unrelated ready work while a decision is pending.

## 6. Receive, merge, gate, and correct (P2, P6, P7, P8, P12)

Read the submission and actual evidence. For committed work, run `gf merge <node>` in the leader's project; it requires a tree without modified tracked files. Preserve other sessions' edits instead of cleaning them away. Gate committed work only after its commit is integrated into the tested tree. Shared uncommitted work needs no merge.

Dispatch and gate required review nodes before gating their targets: `gf gate <review-node>`, then `gf gate <work-node>`. A review gate validates citations; its pass does not erase a reviewer's fail verdict. Let deterministic results outrank observations, trajectory/history, and opinion.

On `reject`, read all five fields: UNIT, VERDICT, REASON, EVIDENCE, SCOPE. Read the named log. Reassign **only** that node and regenerate its brief so the rejection travels with the task. Preserve every unrelated accepted node. The target's next start makes its old review stale, so review the new submission again.

On the second attempt, escalate once: raise effort for an incomplete or defective implementation; raise the model when the approach was wrong. Use `gf route <node>` again and record the actual choice with `gf assign`. Routing recognizes an `approach:` rejection prefix, but the CLI has no failure-classification command; if the evidence proves an approach failure, choose the higher model explicitly in the assignment and explain it in the report. Do not edit rejection records or escalate repeatedly without new evidence.

`replan` means the bounded attempt budget is exhausted, not permission for a fourth attempt. Diagnose the scope, inputs, or check and change the plan with `gf plan validate` and `gf plan set`. Preserve the history and explain the substantive plan change; never reset a node just to repeat the same work.

## 7. Handle the other verdicts (P1, P7, P9, P10)

| Verdict | Next action |
| --- | --- |
| `unverified` | Bring the missing evidence, then gate again. For a missing independent review, dispatch and gate that review on the current submission. Host evidence can be recorded only while running: a missing host result requires another start, check, and submission, consuming an attempt. |
| `hold` | Turn a concrete objection into a failing cmd check and revise the plan, or ask a person to decide the unresolved judgment. Use `gf decide ask --node <node> --kind review --purpose hold --question "Accept this specific objection?" --files <artifact>` when appropriate; a refused authorization stays blocked. |
| `needs_approval` | Inspect `gf decide list`, present the exact artifact/action, and use `gf decide wait <id> --timeout 30`. Continue unrelated nodes meanwhile; gate the affected node again only after the required answer arrives. |

Do not convert `hold` or `unverified` into pass by rewriting evidence. A timeout leaves a decision pending. Keep existing submissions when only review evidence or an approval is missing; starting again consumes an attempt and changes the submission binding.

## 8. Close and report (P7, P10, P12)

After every required node passes, run `gf gate --final`, then `gf status` and `gf trace`. The final gate runs integration and fixed checks; verify that status actually says complete. Do not call a partially verified run finished.

Report in the user's language: the delivered outcome; per-node model/provider and attempts; a check table with actual commands, exit codes, and evidence; open decisions; and what was not verified. Obtain command/exit details from status and recorded evidence, not from trace totals alone. For host checks, report the tool's observed result and “no exit code.” Provide concise visible progress during execution from recorded state, without asking the user to supervise checks.

## 9. Add the learning edge (P11, P12)

After acceptance, derive at most a few constraints from observed failures and fixes. Use `gf learn add --from <node> --text "constraint" --review-when "condition that invalidates it" --paths <path> --tags <tag>`. Scope them to the project and evidence; do not turn a one-off preference into a global rule. Promote machine-checkable constraints with `gf learn promote <id> --run "check command"`. Review `gf learn list` on later runs and use `gf learn retire <id> --reason "obsolete evidence or condition"` when a constraint is stale.

## 10. Apply security scope throughout (P4, P9, P10)

Use the `security` grade when the purpose is defensive vulnerability discovery, threat modeling, or attack-scenario testing on systems the user owns. Give workers relevant code and synthetic test data only; never pass real credentials, tokens, payment data, or personal records. If a worker's safeguards block the task, have it report the blocked scope as a decision for a person. Stop that action; do not bypass safeguards, disguise the request, or switch models to evade the block.

## 11. Keep session communication scoped (P5, P10)

Brief sub-sessions in English and require English reports, preserving original code, paths, and user-facing strings. Sub-sessions never start other sessions and never ask the user directly. Only the leader talks to the user, in the user's language. Human-facing requests are decisions or approvals; implementation checks remain inside the loop.
