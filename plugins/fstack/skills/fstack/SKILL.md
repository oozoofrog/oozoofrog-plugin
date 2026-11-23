---
name: fstack
description: "Use when the user asks for a disciplined engineering workflow that calibrates pace and documentation to the task: kickoff and open questions, spec, ADR and plan with traceable IDs, one plan task test-first, a reproduced bug fix, a throwaway prototype to settle a design fork, review against the spec, an autonomous run to a checkable exit condition, pending AI decisions, remaining work, or process reflection; also for fstack requests or pstack- or tstack-style requests. 작업 위험도에 맞춰 진행 속도와 문서 수준을 정하는 개발 방식(킥오프, spec·ADR·plan, 테스트 먼저, 자율 실행, 결정 확인)을 요청할 때 사용한다. Not for quick questions, single obvious edits, generic code review, behavior-preserving refactoring, session handoff, or model selection."
---

# fstack

This file is an index. Playbooks, principles, references and the check script live beside it; paths are relative to this skill directory. Read each file in full before you apply it.
Cite only principles that you read in this session, and name the decision each one changed.
Precedence: user instructions > project rules (AGENTS.md, CLAUDE.md, ADR MUSTs) > this skill.

## Frame (right after this skill loads)

- Restate the goal, the problem and the smallest artifact that meets the goal. Read the records that bear on the request (`references/records.md`).
- Choose Pace and Spec tier from the request. Pace is `step` unless the user granted `drive`. Spec is `T1` unless the change creates or alters a contract that others rely on (public API, CLI surface, persisted schema, protocol) or the user asks for spec, ADR or plan; then it is `T2`. Details: `references/dials.md`.
- Send the frame line as visible reply text right after this skill loads, before your next tool call and before any action that changes files. A line only in thinking, in a tool input or in the final report does not count. If a file you read later changes a dial, send a corrected frame line before the next file change. It is one literal line in the user's language. Keep the keys `Pace:` and `Spec:` in every language:
  - `Pace: step · Spec: T1 — internal bug with a clear repro`
  - `Pace: step · Spec: T1 — 재현되는 내부 버그`
- Do not wait for confirmation. This also applies in drive pace: the frame line is not a stop.
- If the evidence contradicts the request, show the evidence and stop.

## Always

- Before a change → write the exit condition as a pass/fail sentence and the verification method.
- A fork that a run can settle → `playbooks/prototype.md`. Do not ask, and do not write a document for it.
- Before you say "done" → `principles/see-it-fail.md` and `principles/real-surface.md`.
- Adding or changing a test → only for T2 tracing, a project rule or the existing suite, or a user request. Otherwise the failing check is a rerunnable repro or a real-surface run (`principles/see-it-fail.md`).
- A decision that no document made → `principles/decide-and-record.md`.
- A project MUST is in the way → `principles/rules-as-written.md`.
- Writing project documents → `references/doc-templates.md`.
- Code shape (comments, structure, naming, data shape, boundaries) → follow the project conventions: its rule files, linters and formatters, and the code around the change.
- Commit → only on a user commit request, or as a local commit under a drive grant. Read `git status` first. Stage explicit paths. Never use `git add -A`. Push is G1.
- Before you ask the user → classify the question: can a run answer it, does an approved decision answer it, or does the user own it? Ask only user-owned questions, in one batch. Give options with the recommended one first and a one-line consequence for each.
- The same correction twice → record it, then run `playbooks/reflect.md`.
- End of every playbook → `playbooks/wrap-up.md`.

## Gates

Gates stop work in any pace. Details: `principles/stop-at-gates.md`.
- **G1** An irreversible or externally visible action: push, deploy, release, data deletion, outgoing messages, secrets, rewriting pushed history, deleting files you did not create.
- **G2** A product or preference call that the user owns and no run can settle.
- **G3** A change to the meaning of an approved document or a project rule.

## Principles

- **See it fail** (`principles/see-it-fail.md`). Writing or keeping a check, or a check is green on its first run. Trust only checks seen failing for the right reason.
- **Real surface** (`principles/real-surface.md`). Before you claim done. Verify where the user meets the behavior; Inconclusive is not a pass.
- **Fix the cause** (`principles/fix-the-cause.md`). Fixing a defect, or a fix failed twice. Write a cause sentence for all symptoms and fix there; test the premise.
- **Label the claim** (`principles/label-the-claim.md`). Any report, memo, record line or number. Label it Verified, Read, Inferred or Question.
- **Decide and record** (`principles/decide-and-record.md`). Tempted to ask about reversible work, or a decision no document made. Decide, then record the source.
- **Stop at gates** (`principles/stop-at-gates.md`). Scope met, a gated action is next, or the next item is visible. Stop at G1–G3, and stop after the scope in step pace.
- **Rules as written** (`principles/rules-as-written.md`). A MUST is costly or was missed. Never narrow it; record the miss.
- **Smallest sufficient change** (`principles/smallest-sufficient-change.md`). "Might as well", sizing a diff, adding an abstraction. Build only what the check requires.
- **Verifiable units** (`principles/verifiable-units.md`). Multi-step work or stacked commits. Known-good → one change → check → next.
- **Trace by ID** (`principles/trace-by-id.md`). T2 documents, ACs, rules or tests. Link them by ID and run the trace.
- **Encode in checks** (`principles/encode-in-checks.md`). The same correction twice, or a rule kept only by care. Climb the ladder: structure > script > test > prose.
- **Evidence before change** (`principles/evidence-before-change.md`). Acting on a review finding, or reviewing again. Act only on a violated contract with trigger, evidence and consequence; a clean result is a success.

## Delegation

- The main session owns the playbook and its checklist. Details: `references/delegation.md`.
- A substantive task gets two lenses from independent agents: macro before the design is fixed, micro after consequential edits. `references/review.md` says when each runs. A trivial edit gets none.
- Each brief restates the goal, gives paths and states the bar. Give a reviewer the target and the claims to verify, never your conclusions.
- A subagent report is not evidence. Read the diff and the outputs yourself.
- Fan out only across disjoint seams or competing shapes. Use only models that the host offers.
- If no independent agent is available, run the passes yourself and say so. Never present your own passes as independent review.

## Report

- Read `references/report.md` before you write the report. Every report, also for a one-line fix, uses its five headings in this order: Goal, Changes, Verification, Basis, Remaining (Korean: 목표, 변경, 검증, 근거, 남은 일). Write "none" under an empty heading.
- State the review mode under Verification: independent, two-lens, or single-agent fallback. A skipped lens and its reason also go there.
- Label each claim. A check that you did not run is "Inconclusive", not a pass.
- In step pace, the last line is `Next step: <candidate>` or, in Korean, `다음 단계: <후보>`, on its own line. Do not start it.

## Playbooks

Pick one playbook. Copy its steps to a checklist: the host's plan or todo tool, or an inline list. Mark each skipped step `skip: <reason>`. If no playbook fits, use `playbooks/figure-it-out.md`.

- **Kickoff** (`playbooks/kickoff.md`). Extract intent and close open questions for a new project or slice. No code. ("kickoff", "brainstorm", "open questions", "킥오프", "브레인스토밍")
- **Design docs** (`playbooks/design-docs.md`). Write or rewrite spec, domain, ADR and plan with IDs. ("write the spec", "ADR", "make a plan", "spec 써줘", "plan 만들어")
- **Prototype** (`playbooks/prototype.md`). Settle a design fork with throwaway variants. ("prototype", "try both", "which layout", "프로토타입", "비교해 봐")
- **Build** (`playbooks/build.md`). Implement one unit or plan task, test-first. ("do task 3", "next task", "implement", "작업 3 해", "다음 작업")
- **Fix** (`playbooks/fix.md`). Reproduce and fix one defect or one review memo. ("fix this bug", "fix memo 1", "버그 고쳐", "메모 1 고쳐")
- **Review** (`playbooks/review.md`). Explain and review a change, a design or a whole document, with one or two lenses. Findings only; a requested fix continues in Fix. ("review this commit", "explain the diff", "does every AC have a test", "macro and micro review", "리뷰", "문서 대조", "설계·코드 교차 검토")
- **Drive** (`playbooks/drive.md`). Run autonomously to a checkable exit predicate after an explicit grant. ("run until done", "don't stop", "끝까지 해", "자율로")
- **Checkpoint** (`playbooks/checkpoint.md`). Report remaining work and confirm pending AI decisions. Read-only. ("what's left", "where are we", "approve the proposals", "남은 작업", "결정 확인")
- **Figure it out** (`playbooks/figure-it-out.md`). Design the steps when no playbook fits, then execute. ("figure it out", "알아서 방법 찾아")
- **Reflect** (`playbooks/reflect.md`). Turn repeated corrections into rules or checks. ("reflect", "retro", "회고", "같은 실수 막아")
- **Wrap-up** (`playbooks/wrap-up.md`). End of every playbook: records, report, commit when allowed. ("commit", "wrap up", "커밋", "마무리")

## Check script

- `scripts/trace.py` checks that spec and domain IDs reach the plan and the tests. Run it from the project root: `python3 -I -B "<skill-dir>/scripts/trace.py" [--no-tests | --names-from "<list command>"]`. `<skill-dir>` is the absolute directory of this `SKILL.md`. Add `--help` for the rules.
- When the project's runner can list its tests, prefer `--names-from "<list command>"` over the static scan (`principles/trace-by-id.md`).
- Never change the script, the IDs or the exit condition to make the check pass.

## Related skills

Find each skill by name in the host's skill catalog. If a named skill is missing, write `skip: <skill> not installed` and use the fallback.
- refactor: behavior-preserving refactoring. Fallback: tell the user that it is out of scope here.
- handoff: pause, `/clear` and session pickup. Fallback: a resume note in the report.
- graph-flow: more than 3 interdependent units with checks, decisions or a dashboard. Fallback: host subagents.
- model-advisor: model and effort for subagents. Fallback: the host's default model.
