# Prompts worth copying

Swap in the real paths, skills, and done checks. Informal wording works.

## Understand

- `/run-engineering-workflow read <thread>. restate the underlying issue in your own words, in plain english.`
- `/confirm-goal <long or messy ask>`
- `/refine-request <the prompt you're about to send>`
- `/run-engineering-workflow investigate why <symptom>. give me what we know, what data you used, and your best hypotheses. don't change any code yet.`
- `use /explain-code to understand <subsystem>. then use /explain-design-decisions to find out why it broke recently.`
- `/recover-work-context my work on <topic> from last week, then read <issue>.`
- `/explain-completed-work me why you implemented it this way and not <other way>. what did you trade off?`
- `/run-engineering-workflow take over this branch. read the decision log, find what's done, and continue. don't redo finished work.`

## Build

- Bug: `/run-engineering-workflow <symptom>. repro first, then fix and verify.`
- Bug in an app: `/run-engineering-workflow repro this with /verify-<app>. if it repros on main, fix it and show me a video as proof.`
- Bug with a cheap test: `/run-engineering-workflow repro <bug> first. if there's a cheap test path, /develop-test-first it. then fix and rerun.`
- Feature: `/run-engineering-workflow add <behavior>. <current output> stays byte-identical. verify both.`
- Refactor: `/run-engineering-workflow move <code> into one module, zero behavior change. record the current output first and prove it's unchanged after.`
- Perf: `/run-engineering-workflow <operation> takes <time> on <fixture>. trace it, fix the measured cause, show me before and after.`

## Design and plan

- `/run-engineering-workflow prototype a few options for <feature>. take screenshots or videos for me to compare.`
- `/run-engineering-workflow we need <feature>. /design-interfaces it first, and answer open questions with prototypes. let me review before proceeding.`
- `/run-engineering-workflow write a tutorial for how i would use <new package> first. then /explain-completed-work me why it beats the current one.`
- `ask /compare-solutions for a second opinion on this thread and our approach.`
- `/run-engineering-workflow turn this design into a plan. small verifiable PRs, each with its own verification steps.`
- `/run-engineering-workflow plan the migration of <library> to <target>. small verifiable PRs. the result must match the original exactly, bugs included.`

## Review and ship

- `/review-with-multiple-models the whole branch, but skeptically. don't change anything yet. no nitpicks unless it's a real bug or regression.` Read the Dropped list too.
- `/create-model-checker-skill prove <property> holds in <module>, even when <steps> interleave or retry.` After merges or refactors in that code: `/update-model-checker-skill`.
- `/coordinate-workers check every package under <dir> against its check script. one worker per package. one report.`
- `/run-engineering-workflow open the pr. small ordered commits, evidence in the description.`
- `/run-engineering-workflow babysit this pr. get it green.` For status only: `/run-engineering-workflow check on pr <number>. anything outstanding?`
- `/run-engineering-workflow land the stack.`

## Away and back

- `/run-engineering-workflow im going to bed. <goal> in a fresh worktree off <base>. done means <checks>. keep a decision log. don't ask me before committing. continue until the checks pass. if you're truly stuck after a few hours, stop and write up why.`
- `/record-decisions catch me up on what you did last night.` Read its Attention section first.
- `/summarize-progress` catches you up on this chat since your last message and lists every call that waits on you.
- `/run-engineering-workflow full autopilot on this queue. each item is independent.`
- `/run-engineering-workflow autopilot these changes, but don't merge. i'll land them.`
- `/capture-lessons capture what we learned so the next run doesn't repeat it.` Approve only edits that change a future decision.
- `/explain-simply` restates the last reply in plain words.
