# Leader procedure

Use the [plan contract](plan.md) for field shapes and [executors](executors.md) when starting sessions. In the examples, replace placeholders with observed values; `gf` means the invocation in [SKILL.md](../SKILL.md). Keep the same run through resumed sessions. Let the tool write its events; never edit them to change a verdict.

## 1. Inspect the real project (P1, P6, P12)

As the leader, check `command -v graph-flow` once when you first use this skill for a person. If it finds nothing, tell them in one sentence that `gf setup` puts the commands `graph-flow` and `gf` in `~/.local/bin` so they can run commands such as `graph-flow open` from their own terminal, and ask whether to install it. Many shells already give `gf` another meaning (oh-my-zsh aliases it to `git fetch`), so when you tell the person what to type, write `graph-flow`. Run `gf setup` only after a yes, relay its message, and if it reports that the directory is not on PATH, give them the printed `export` line to add to their shell profile instead of editing the profile yourself. After a no, do not ask again in that session. `gf setup --remove` undoes it. Keep invoking the skill's own copy yourself; the command on PATH is for the person.

Read project instructions, the affected code, existing tests, manifests, branch, and local edits. Identify the requested outcome, acceptance evidence, and existing authorization separately. Run `gf status` with no run selected to list this project's runs, their status and their open decisions; select the matching run, set `GF_RUN` to its `run` path, then run `gf status` again. Do not create a second run to escape a failure.

For new work, run `gf init <run-id>` from the project and set `GF_RUN` to the returned run path. Global options precede the command; for example, `gf --project <project> init <run-id>` selects a project explicitly. Record only observed capabilities with `gf host set <capability>`, such as `subagent`, `workflow`, `t3_delegate`, or `worktree`; this replaces the previous list. Do not claim an unavailable host tool. Preserve facts and their sources, assumptions, permission scope, project identity, and relevant revisions in the plan's `context` fields (`why`, `if_approved`, `if_rejected`, `undo`).

On resume, inspect current files and `gf decide list` before reusing evidence. If a passed node's inputs changed outside the plan, use `gf reopen <node> --reason "changed input and evidence"`; this invalidates that node and its dependents. Preserve unrelated accepted work.

## 2. Resolve decisions before splitting (P1, P10)

Ask only for direction, missing information that inspection cannot recover, taste, or authorization. Ask as few consequential questions as possible, preferably before the split. Never ask for confirmation of something a check can decide. At planning, representative-output review, changed requirements, and completion, inspect whether a human decision remains; do not manufacture a question at every boundary.

When a run exists, record a question with `gf decide ask --open --kind direction --question "Which outcome takes priority?"`; use `information` for missing facts. Agent-authored `decide ask` questions are always free and non-binding; they cannot create holds, human checks, trajectory, lane-3, decision-node or plan approvals. Include a concrete recommendation and, when available, the reviewable artifact. Preserve earlier answers and their source in context; do not ask again merely to populate the log. Keep design acceptance separate from permission to publish, delete, or access anything. Silence and a wait timeout grant neither. The dashboard is the person's surface: do not start `gf serve`, read its token or key files, or call its HTTP API from an agent session; tell the person the command to run instead.

Use an `authorization` or `review` decision node when downstream work must wait, giving it a named output such as `approval`. Only acceptance releases dependents; send-back keeps them blocked until the plan is revised. Direction/information nodes cannot have dependents. Once it is ready, `gf gate <decision-node> --open` records the question with the correct binding. A free question does not create a dependency: the leader must keep affected work undispatched until it is resolved. Open the browser without asking at plan approval, a waiting decision, and run completion. Use the creating command’s `--open`; it prints no address. An explicit request to see the dashboard can also use `gf open`.

When you tell the person that something waits for them, never give an id alone. A decision asking the person to accept a result must name the file(s) to read so the dashboard can show them; ask a question with nothing attached as a direction or information question instead. Quote the question in full, name the node by its title, add the decision id in parentheses, and use `--open` on the creating ask/gate command so their browser opens on that decision (use the returned `show` command only if it was not opened); `gf decide ask` returns this command as `show`. Point at a node the same way with `gf open --node <node>`. The dashboard shows the same decision id and node id beside each title and has a find box that accepts either, so a person can also get from your message to the page by typing the id. Set `GF_SESSION` to the name the person sees for this session (the thread or tab title); without it only the host's chat id is recorded, which the person cannot match to a tab by eye. Pass each worker's session name in its brief environment as well. The dashboard shows these names as who asked and who is working. Run `gf open --stop` when they ask to close it. Do not run `gf serve`, send requests to the dashboard, or operate its page.

## 3. Write the planning brief and graph (P1, P3, P4, P5, P9, P11)

Read `gf brief --plan` and `gf learn list`. Apply only constraints whose evidence, scope, and review condition still fit. Write a plan using the contract's schema; include the user's requirements and integration checks that exercise the assembled result.

Write the plan and node `title`, node `summary`, input `label`, check `title`, and decision-node/human-check `context` in the user's language. Name what the person receives and what a decision changes, using the [presentation field limits](plan.md#plan-contract). For example, for a Korean request: `{"title":"내보내기 만들기","summary":"사용자에게 모든 메모의 JSON 사본을 제공합니다.","needs":[{"from":"collect","artifact":"notes","label":"모은 메모"}],"checks":[{"id":"review","type":"human","title":"원본 메모가 모두 포함됐는지 확인","context":{"why":"공유 전 결과를 확인합니다.","if_approved":"이 사본을 사용합니다.","if_rejected":"누락된 메모를 보완합니다.","undo":"이전 사본으로 돌아갈 수 있습니다."}}]}`. Presentation-only fields preserve accepted work; see plan.md for the exact wording exclusions.

- Split by blast radius: one bounded deliverable per work node. Declare exact `owns` paths, necessary `reads`, inputs, outputs, and a `max_attempts` no greater than three. Combine overlapping work or serialize it through a real artifact dependency.
- For each `needs` edge, name both the producer and the artifact that crosses. The artifact must be under the producer's `owns` or in its named `outputs`. Delete edges that mean only “and then.”
- Add `requires_passed` to an integration check that needs particular nodes' outputs, including inputs a script chooses by default. List the producer ids. Each listed producer's work gate runs the check at any lane once the other listed producers have passed. Other work gates run it at effective lane 2 or 3 once all listed producers have passed. The final gate always runs the check.
- Write a meaningful `cmd` check for each work node **before** its implementation. Make the check able to refute the requested behavior. Do not substitute a scope comparison, confidence, or a command that always succeeds. If no machine check exists, declare `human` honestly and inspect normalization's raised lane and approval requirement.
- Choose the lane by reversibility and blast radius, separately from model grade:

| Lane | Meaning | Example and gate requirement |
| --- | --- | --- |
| 1 | Reversible and contained | A local parser fix; deterministic checks and scope. |
| 2 | Reversible but wide | A shared API refactor; deterministic and integration checks, clean trajectory, and independent review. |
| 3 | Hard to reverse | A production migration or publication; prepare and verify first, then require a person's authorization for the specific action. |

Add a lane 1 `review` node with one `lens` and the work node as `target` for every effective lane 2 or 3 node. Its reviewer must use another model family. Name the target artifact in `needs`; a review can start once its target is submitted, before that target passes. Use grades `bulk`, `scoped`, `daily`, `large`, and `security` to route difficulty; see the [model table](executors.md).

For consequential actions, separate the reviewable preparation, an authorization decision node, and the action that consumes its approval. A post-submission lane 3 gate does not authorize an earlier external action. Reuse authorization only for the same scope and artifact; material changes require a new decision.

A check title states exactly what will be checked, without claiming success before execution. For `grep -q 안내 guide.txt`, write “'안내'라는 낱말이 있는지”. The screen prefixes planned titles with “확인할 것” and labels executed results separately. Plan approval is separate from later gate answers: the person must read the goal, owned files, inputs, outputs and commands. A newly promoted check takes effect only after the next plan is set and approved.

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

Plan changes invalidate changed, unstarted nodes and their dependents. Completed/running/submitted contracts and their inputs cannot be rewritten; add new work for new requirements. Keep the same ids where the deliverable is unchanged; do not rename a node merely to erase its failed attempts.

### Required plan approval

Set the validated plan with `gf plan set <file> --open`. The one-line result contains the revision, node count, approval decision id, notice count and `show` only while approval is open; do not print the file or restate its nodes in chat. Say exactly one sentence in the person’s language, for example: “계획을 대시보드에 올렸어요. 보시고 시작을 눌러 주세요. (d4)” Then run `gf decide wait <id> --timeout 30`. On timeout end your turn and resume when the person says they answered: the dashboard cannot wake a session. A chat reply is not a signed approval.

Only a verified `approved` answer releases dispatch. For `revision_requested` or `rejected`, read the answer text and revise with `plan set --open`; that supersedes the old question and creates a fresh approval. Wording-only revisions retain current plan approval and completed work; an identical re-post creates no revision. Structural changes require fresh approval. See [the field exclusions](plan.md#revisions) and [older-run recovery](records.md#continuing-an-older-run).

Use `GF_NO_OPEN=1` for headless runs/tests; this suppresses only the browser. With MCP-only access, tell the person to run the result’s `graph-flow open` command. Ordinary commands without a new waiting decision do not open it. `webbrowser.open` requests reuse of the current browser window where supported; it cannot guarantee reuse of a particular existing tab.

## 5. Fan out ready nodes (P4, P5, P6, P9, P12)

Run `gf ready`, then `gf route <node>` for each candidate. Check actual host availability and routing's account/usage caveats. Record the actual choice with `gf assign <node> --executor <executor> --model <model> --effort <effort> --provider <provider> --family <family> --isolation <isolation>`. Generate `gf brief <node>` and start exactly one sub-session with that brief using the [executor procedure](executors.md).

Never execute an effective lane 2 or 3 work node inline, even if routing suggests it. If the host cannot supply a suitable worker or another family for review, record the missing capability and leave that node unverified. Uncommitted shared-tree work is serial; parallel writers need worktrees and committed submissions. Dispatch ready decision nodes to their gate, not to an agent. Do unrelated ready work while a decision is pending.

## 6. Receive, merge, gate, and correct (P2, P6, P7, P8, P12)

Read the submission and actual evidence. For committed work, run `gf merge <node>` in the leader's project; it requires a tree without modified tracked files. Preserve other sessions' edits instead of cleaning them away. Gate committed work only after its commit is integrated into the project root. Shared uncommitted work needs no merge.

Dispatch and gate required review nodes before gating their targets: `gf gate <review-node> --open`, then `gf gate <work-node> --open`. A review gate executes its command checks and validates citations; its pass does not erase a reviewer's fail verdict. Let deterministic results outrank observations, trajectory/history, and opinion.

On `reject`, read all five fields: UNIT, VERDICT, REASON, EVIDENCE, SCOPE. Read the named log when present. After a scope rejection, the leader restores the out-of-scope paths before reassigning, never by discarding another node's accepted or in-flight work; coordinate recovery of only the offending edits. Reassign **only** that node and regenerate its brief so the rejection travels with the task. Preserve every unrelated accepted node. The target's next start makes its old review stale, so review the new submission again.

When the verdict includes `run_check_failed_after_node_checks_passed`, read the failing check's log first. If it shows a missing producer output, revise the plan by adding `requires_passed` or moving the check to the producing node. Get the revised plan approved before spending another attempt.

On the second attempt, escalate once: raise effort for an incomplete or defective implementation; raise the model when the approach was wrong. Use `gf route <node>` again and record the actual choice with `gf assign`. Routing recognizes an `approach:` rejection prefix, but the CLI has no failure-classification command; if the evidence proves an approach failure, choose the higher model explicitly in the assignment and explain it in the report. Do not edit rejection records or escalate repeatedly without new evidence.

`replan` means the bounded attempt budget is exhausted, not permission for a fourth attempt. Diagnose the scope, inputs, or check and change the plan with `gf plan validate` and `gf plan set`. Preserve the history and explain the substantive plan change; never reset a node just to repeat the same work.

Gate scope checks compare the frozen file list of the submission, before any integration commands. Integration commands may create files in the tested tree; those outputs do not become worker changes at the next gate. Inspect new edits explicitly and submit again when the submitted work changes. Planned lane-3 and human-check questions are asked after submission, before acceptance; they never authorize work that has already happened.

## 7. Handle the other verdicts (P1, P7, P9, P10)

| Verdict | Next action |
| --- | --- |
| `unverified` | Bring the missing evidence, then gate again. For a missing independent review, dispatch and gate that review on the current submission. Host evidence can be recorded only while running: a missing host result requires another start, check, and submission, consuming an attempt. |
| `hold` | The gate itself creates the question from the approved plan and the current failed host checks/reviews, identifying each evidence record by id and hash. Present that question with `gf gate <node> --open`, then wait for its answer. Do not author an override question with `decide ask`. An earlier answer or an answer about different evidence never counts; changed evidence requires the gate to ask again. Refusal keeps the node blocked; correct the work or revise and re-post the plan. |
| `needs_approval` | Inspect `gf decide list`, present the exact artifact/action, and use `gf decide wait <id> --timeout 30`. Continue unrelated nodes meanwhile; gate the affected node again only after the required answer arrives. When nothing else can proceed, tell the person exactly what waits for them, say that you will continue when they tell you they have answered, and end your turn: the dashboard cannot wake a session. When they return, run `gf decide list` and gate again. |

Do not convert `hold` or `unverified` into pass by rewriting evidence. A timeout leaves a decision pending. Keep existing submissions when only review evidence or an approval is missing; starting again consumes an attempt and changes the submission binding.

### Recover without losing the current submission

A refusal from `start` changes nothing. If a rejected human check or declined hold uses the last attempt, revise the contract and raise `max_attempts` (or replace the node) with `plan set`, obtain fresh plan approval, then start the revised work. After send-back on a decision node, revise its question and re-post the plan. Rejections do not freeze nodes.

For changed submitted bytes, run `gate` again; it asks about the current evidence without spending an attempt. Staleness is recorded as `decision.superseded` and cannot be reversed by moving the project back or restoring a file. When `decide wait` returns stale, follow its recovery instead of waiting for a hidden question. After a move, re-post the current plan and obtain approval; an earlier key recovery remains valid for pinning.

For `active_plan_change` on an approved decision node, gate it, use `gf reopen <decision> --reason <reason>`, then revise and re-post. Otherwise preserve running/completed contracts and add a new node. Only a verified approval still in force protects a waiting node; an answer alone does not. Old submitted files shown during upgrade are informational after plan approval; later edits still require any gate acceptance specified by the contract.

If a completed review prevents revising rejected work, follow `active_plan_change`: reopen the review with `gf reopen <review> --reason <reason>`, then re-post the target’s revised plan.


For lost/rotated keys and continuing old runs, use [records.md recoveries](records.md#continuing-an-older-run); re-post the run’s own `plans/NNNN.json` when instructed there.

## 8. Close and report (P7, P10, P12)

After every required node passes, run `gf gate --final --open`, then `gf status` and `gf trace --conformance`. The final gate runs integration and fixed checks; verify that status actually says complete. Do not call a partially verified run finished. Trace reports planned/unplanned human answers, wait times, and observed failing checks alongside P1–P12 measurements; use `gf --json trace --conformance` for the same stable numbers.

Report in the user's language: the delivered outcome; per-node model/provider and attempts; a check table with actual commands, exit codes, and evidence; open decisions; and what was not verified. Obtain command/exit details from status and recorded evidence, not from trace totals alone. For host checks, report the tool's observed result and “no exit code.” Provide concise visible progress during execution from recorded state, without asking the user to supervise checks.

## 9. Add the learning edge (P11, P12)

After acceptance, derive at most a few constraints from observed failures and fixes. Use `gf learn add --from <node> --text "constraint" --review-when "condition that invalidates it" --paths <path> --tags <tag>`. Scope them to the project and evidence; do not turn a one-off preference into a global rule. Promote machine-checkable constraints with `gf learn promote <id> --run "check command"`. Review `gf learn list` on later runs and use `gf learn retire <id> --reason "obsolete evidence or condition"` when a constraint is stale.

## 10. Apply security scope throughout (P4, P9, P10)

Use the `security` grade when the purpose is defensive vulnerability discovery, threat modeling, or attack-scenario testing on systems the user owns. Give workers relevant code and synthetic test data only; never pass real credentials, tokens, payment data, or personal records. If a worker's safeguards block the task, have it report the blocked scope as a decision for a person. Stop that action; do not bypass safeguards, disguise the request, or switch models to evade the block.

## 11. Keep session communication scoped (P5, P10)

Brief sub-sessions in English and require English reports, preserving original code, paths, and user-facing strings. Sub-sessions never start other sessions and never ask the user directly. Only the leader talks to the user, in the user's language. Human-facing requests are decisions or approvals; implementation checks remain inside the loop.

Follow the [human identity rule](../SKILL.md#human-identity).


For free questions, give concrete alternatives in the person's terms with repeated `--option` arguments to `gf decide ask`. The dashboard displays those choices and their consequences; do not mark one as recommended. Existing questions without alternatives keep their answer-text path behind an explicit choice. Binding questions are still created only by plan/gate code.


A re-brief includes “Review findings on your previous submission” for the last submission's latest failed reviews, with severity, file:line, text and evidence. Read these alongside the gate rejection; a run-level check failure may have hidden the review failure at the gate.

Current recovery behavior: a submitted work node cannot start another attempt and `reopen` accepts only passed nodes. If command/scope checks pass but an accepted independent review says fail, gating creates the existing R4 hold question. A held node with attempts remaining may then start another attempt without answering that question. This documents current behavior; it adds no required answer or rule.
