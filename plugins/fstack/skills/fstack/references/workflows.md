## Specialist index

The table maps requested outcomes to resources within this package. Direct invocations remain available. Model and budget setup is optional.

| The user wants to | Skill |
|---|---|
| Do any non-trivial task with rigor | [`/run-engineering-workflow`](../../run-engineering-workflow/SKILL.md) |
| Check that the agent understood their goal and the problem before it starts | [`/confirm-goal`](../../confirm-goal/SKILL.md) |
| Get a prompt rewritten deeper, not bigger, before sending it: what a top professional would add, their raw material and methods, and an outside check. It returns the prompt and doesn't do the task | [`/refine-request`](../../refine-request/SKILL.md) |
| Learn the expert words for what they're building, including words borrowed from neighboring fields, with every cited source checked, and get their description rewritten with them | [`/clarify-terminology`](../../clarify-terminology/SKILL.md) |
| Know how code works now, or where new code should live | [`/explain-code`](../../explain-code/SKILL.md) |
| Know why code is shaped this way, or where a number came from | [`/explain-design-decisions`](../../explain-design-decisions/SKILL.md) |
| Understand a change or subsystem, explained plainly | [`/explain-completed-work`](../../explain-completed-work/SKILL.md) |
| Catch up on their own recent work on a topic | [`/recover-work-context`](../../recover-work-context/SKILL.md) |
| Catch up on what changed in this chat since their last message, in plain words and small visuals, with every item waiting on them listed and decidable from the reply alone | [`/summarize-progress`](../../summarize-progress/SKILL.md) |
| Catch up like `/summarize-progress`, in a short subtitled video of slides, with the waiting calls as text under it | [`/summarize-progress-on-video`](../../summarize-progress-on-video/SKILL.md) |
| Know what a small diff could break outside itself | [`/assess-change-impact`](../../assess-change-impact/SKILL.md) |
| Settle types and module shape before code that crosses a function boundary | [`/design-interfaces`](../../design-interfaces/SKILL.md) |
| Get several attempts at one brief, merged into the best one | [`/compare-solutions`](../../compare-solutions/SKILL.md) |
| Run parallel checks over slices, or race workers, with available workers | [`/coordinate-workers`](../../coordinate-workers/SKILL.md) |
| Challenge an existing design or diff with independent reviewers | [`/review-with-multiple-models`](../../review-with-multiple-models/SKILL.md) |
| Fix a bug test-first when a cheap local test exists | [`/develop-test-first`](../../develop-test-first/SKILL.md) |
| Apply TypeScript rules to `.ts` or `.tsx` work | [`/write-typescript`](../../write-typescript/SKILL.md) |
| Review comments and receive findings | [`/review-code-comments`](../../review-code-comments/SKILL.md) |
| Clean AI tells out of prose | [`/edit-prose`](../../edit-prose/SKILL.md) |
| Write docs, an RFC, a README, a PR description, or a commit message to a standard | [`/write-technical-docs`](../../write-technical-docs/SKILL.md) |
| Hear the last reply again in plain words | [`/explain-simply`](../../explain-simply/SKILL.md) |
| Give agents a scripted way to drive the app and prove behavior | [`/create-app-check-skill`](../../create-app-check-skill/SKILL.md) |
| Bring a verification skill and its feature map back in line with the app | [`/update-app-check-skill`](../../update-app-check-skill/SKILL.md) |
| Formally verify a race, invariant, or other property that tests rarely reach | [`/create-model-checker-skill`](../../create-model-checker-skill/SKILL.md) |
| Bring a formal verification back in line after the code it covers changed, and learn whether a failure is drift or a bug | [`/update-model-checker-skill`](../../update-model-checker-skill/SKILL.md) |
| Show a PM or designer what the user sees as a chart checked by a TLA+ model, with the shortest path to each state that breaks a rule | [`/verify-state-transitions`](../../verify-state-transitions/SKILL.md) |
| Vet a performance number before reporting or acting on it | [`/verify-benchmark`](../../verify-benchmark/SKILL.md) |
| Run a large or cross-cutting change, or one to review after stepping away | [`/design-workflow`](../../design-workflow/SKILL.md) |
| Keep a decision log during a run, and review it afterward | [`/record-decisions`](../../record-decisions/SKILL.md) |
| Pick a model for each role and a reasoning budget | [`/configure-models`](../../configure-models/SKILL.md) |
| Turn their own working habits into a personal mode skill | [`/create-personal-workflow`](../../create-personal-workflow/SKILL.md) |
| Turn what a finished task taught into skill edits | [`/capture-lessons`](../../capture-lessons/SKILL.md) |
| Stop agents from repeating the same mistakes in this repo | [`/prevent-repeated-mistakes`](../../prevent-repeated-mistakes/SKILL.md) |
| Build a page whose buttons wake a Grok Bot over a webhook | [`/build-webhook-ui`](../../build-webhook-ui/SKILL.md) |
| Find a workflow or direct command | [find-workflows](../../find-workflows/SKILL.md) |

For the general entry point use [fstack](../SKILL.md). The `principle-*` directories are listed in the [engineering workflow](../../run-engineering-workflow/SKILL.md#principles).

Close calls:

- `/explain-code` explains what the code does. `/explain-design-decisions` explains the reasons. `/explain-completed-work` runs one or both and explains the result plainly.
- `/compare-solutions` gives every worker the same brief and merges the best parts. `/coordinate-workers` splits work into slices or a race and returns one report.
- `/review-with-multiple-models` challenges a named proposal or diff. `/assess-change-impact` looks for breakage outside the diff and proves the one fact that makes the change safe.
- `/recover-work-context` rebuilds context across recent chats. `/summarize-progress` covers only this chat since the user's last message. Resuming one specific chat or branch is the Session pickup playbook.
- `/design-workflow` designs one rigorous run. The Autonomous run playbook drives one task to a finish condition.


## Design requests

Sketch types and ownership with [design-interfaces](../../design-interfaces/SKILL.md). When the requested result is competing solutions and a selected design, use [compare-solutions](../../compare-solutions/SKILL.md). When a proposal already exists and the requested result is evidence of defects, use [review-with-multiple-models](../../review-with-multiple-models/SKILL.md). For a measurable choice between runnable implementations, run the [prototype playbook](../../run-engineering-workflow/playbooks/prototype.md).
