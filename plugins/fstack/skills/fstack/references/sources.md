# Sources

This skill adapts ideas from three MIT-licensed works. The text is rewritten in English. Licenses: [NOTICE](../NOTICE.md).

| Source | Pin | Retrieved |
|---|---|---|
| pstack by Lauren Tan, in [cursor/plugins](https://github.com/cursor/plugins) | `cursor/plugins@7a583913eb1b` (pstack 0.15.46) | 2026-11-21 |
| tstack by Toby Lee, [tobyilee/tstack](https://github.com/tobyilee/tstack) | `tobyilee/tstack@868dda2373da` (tstack 0.2.2) | 2026-11-21 |
| dual-brain by Hanmin Kim, [sleeplesshan/dual-brain](https://github.com/sleeplesshan/dual-brain) | v1.7.0 plus the 2026-11-07 documentation update (local copy, no commit) | 2026-11-23 |

## File origins

P = pstack, T = tstack, B = both (pstack and tstack), N = new, D = dual-brain. P and T source paths are relative to the `skills/` folder of each source Plugin, except `tstack/agents/t-reviewer.md`. D paths start with the dual-brain skill folder.

| File | Origin | Source files |
|---|---|---|
| `SKILL.md` | N (structure from B) | P `poteto-mode/SKILL.md`; T `t-mode/SKILL.md` |
| `playbooks/kickoff.md` | T, with a P prototype hook | T `t-mode/playbooks/kickoff.md`; P `poteto-mode/playbooks/prototype.md` |
| `playbooks/design-docs.md` | B | T `t-mode/playbooks/design-docs.md`; P `poteto-mode/playbooks/multi-phase-plan.md` |
| `playbooks/prototype.md` | P | P `poteto-mode/playbooks/prototype.md` |
| `playbooks/build.md` | B | T `t-mode/playbooks/plan-task.md`; P `poteto-mode/playbooks/feature.md` |
| `playbooks/fix.md` | B + D | T `t-mode/playbooks/fix.md`; P `poteto-mode/playbooks/bug-fix.md`; D `dual-brain/SKILL.md` §Evidence before changes |
| `playbooks/review.md` | B + D | T `t-mode/playbooks/review.md`, `t-mode/playbooks/conformance.md`; P `interrogate/SKILL.md`; D `dual-brain/SKILL.md` §Delegate and reconcile |
| `playbooks/drive.md` | P | P `poteto-mode/playbooks/autonomous-run.md`, `figure-it-out/SKILL.md` Phase C |
| `playbooks/checkpoint.md` | T | T `t-mode/playbooks/status.md`, `t-mode/playbooks/decisions.md` |
| `playbooks/figure-it-out.md` | B | T `t-mode/playbooks/figure-it-out.md`; P `figure-it-out/SKILL.md` |
| `playbooks/reflect.md` | B + D | T `t-reflect/SKILL.md`; P `reflect/SKILL.md`; D `dual-brain/SKILL.md` §Evidence before changes |
| `playbooks/wrap-up.md` | T + D | T `t-mode/playbooks/wrap-up.md`; D `dual-brain/SKILL.md` §Evidence before changes |
| `principles/see-it-fail.md` | B | T `t-mode/principles/see-it-fail.md`, `t-mode/principles/assert-the-reason.md`; P `principle-test-behavior-not-implementation` |
| `principles/real-surface.md` | B + D | T `t-mode/principles/real-surface.md`; P `principle-prove-it-works`; D `dual-brain/SKILL.md` §Deliver and retain useful context |
| `principles/fix-the-cause.md` | B | T `t-mode/principles/fix-the-cause.md`; P `principle-fix-root-causes`, `principle-attack-the-premise` |
| `principles/label-the-claim.md` | B | T `t-mode/principles/label-the-claim.md`; P poteto-mode reply labels, `principle-explain-the-number` |
| `principles/decide-and-record.md` | B | T `t-mode/principles/mark-the-source.md`; P `principle-never-block-on-the-human` |
| `principles/stop-at-gates.md` | B + N | T `t-mode/principles/user-drives-the-pace.md`; the Autonomy sections of both routers; N gate model |
| `principles/rules-as-written.md` | T | T `t-mode/principles/rules-as-written.md` |
| `principles/smallest-sufficient-change.md` | B | T `t-mode/principles/scope-of-the-step.md`; P `principle-laziness-protocol`, `principle-subtract-before-you-add` |
| `principles/verifiable-units.md` | P | P `principle-sequence-verifiable-units` |
| `principles/trace-by-id.md` | T | T `t-mode/principles/trace-by-id.md` |
| `principles/evidence-before-change.md` | D + P | D `dual-brain/SKILL.md` §Evidence before changes; P `interrogate/SKILL.md` |
| `principles/encode-in-checks.md` | B | T `t-mode/principles/encode-in-checks.md`; P `principle-encode-lessons-in-structure`, `principle-build-the-lever` |
| `references/dials.md` | N | Resolution of the pace, planning and scale tensions between the two sources |
| `references/report.md` | B + D | T `t-mode/references/report-template.md`; P poteto-mode reply format; the report of the retired evidence-first-engineering Plugin; D `dual-brain/SKILL.md` §Deliver and retain useful context |
| `references/doc-templates.md` | T (rewritten) | T `t-mode/references/doc-templates.md` |
| `references/records.md` | B + D | T `t-mode/references/journal-format.md`, `t-mode/principles/conclusions-and-process.md`; P `show-me-your-work/SKILL.md`, `principle-make-operations-idempotent`; D `dual-brain/references/memory.md` |
| `references/review.md` | B + D | T `tstack/agents/t-reviewer.md`, `t-mode/references/review-memo.md`; P `interrogate/SKILL.md`; D `dual-brain/SKILL.md` §Delegate and reconcile |
| `references/delegation.md` | B + D | T t-mode delegation section; P poteto-mode subagent guidance, `principle-separate-before-serializing-shared-state`, `principle-guard-the-context-window`; D `dual-brain/SKILL.md` §Choose the smallest useful workflow, `dual-brain/references/runtime.md` |
| `references/sources.md` | N | This file |
| `NOTICE.md` | N | The `LICENSE` file of each source Plugin; D `dual-brain/LICENSE` |
| `scripts/trace.py` | T (rewritten) | T `t-mode/scripts/tstack-check.py`, `trace` subcommand |

## Adaptations

- One router replaces two always-on routers with conflicting rules. The request boundary limits authority: `step` pace by default, `drive` only on an explicit grant, gates G1–G3 in any pace.
- Spec weight is a dial (T0–T2) instead of "documents first" or "code is the spec".
- Tests are added when T2 tracing, the project's rules or the user require them. Otherwise a rerunnable repro or a real-surface run proves the change. Every check must be seen failing.
- Code-shape rules are not fixed in this skill, because code style changes over time. The project's rule files, linters and surrounding code decide them. Not adopted as rules: type-system discipline, boundary discipline, domain modeling, foundational thinking, caller migration, reader load and first-principles redesign.
- Experience-first, outcome-oriented execution and design-space exploration are folded into the prototype playbook and the delegation reference.
- Instructions are in English. Replies and project records follow the language of the user or the project. The Korean keyword mapping follows the user's rule, not tstack's `keywords` mapping.
- The journal is optional. trealworld case links are dropped.
- The tstack `keywords`, `journal` and `self` checks are not ported. A repository test replaces `self`.
- The two complementary dual-brain reviewers become an optional two-lens review mode with macro and micro lenses. The default stays one independent reviewer.
- The dual-brain evidence bar for changes becomes the `evidence-before-change` principle.
- dual-brain project memory is absorbed as rules for reading and writing records, not as a new store.
- Agent reuse is limited to the same role, so an author never reviews its own work.

## Exclusions

| Excluded | Reason |
|---|---|
| Cursor-only features: bugbot triage, Cursor `/loop`, cursor-team-kit commands, `~/.cursor/rules/pstack-models.mdc`, hard-coded model slugs, the `poteto-agent` subagent, `AskQuestion` | Not portable to Claude Code and Codex |
| PR babysitting, shipping, opening PRs, autopilot | Externally visible actions belong to the user's own flow (G1) |
| Trace and runtime forensics, visual parity, eval and hillclimb, worktree cleanup, perf issues | Out of scope for a general router |
| pstack Refactoring | Covered by the refactor Plugin |
| pstack Pause safely and Session pickup | Covered by the handoff Plugin |
| The other pstack skills (swarm, tdd, arena and more) | Their useful parts are folded into the playbooks above |
| The dual-brain Hot/Warm/Cold memory store, `.dual-brain/MEMORY.md` and its `refs`/`last_*` metadata | A third store would split the source of truth with ADR, documents and handoff |
| The dual-brain Right Brain and Left Brain role names | Replaced by the macro and micro lenses |
| dual-brain `PORTABLE.md`, its exporter, and the Grok, xAI Grok Bot and Meta Muse setup routes | Product-specific |
| dual-brain benchmarks | Not instructions |
| Host tool names in dual-brain runtime guidance | Hosts differ; use the live tool schema |
