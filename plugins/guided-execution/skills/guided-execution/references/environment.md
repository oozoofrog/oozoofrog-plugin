# Configure and reuse the project environment

Read this at the first run and when the project, tools, or user direction changes. This is a host-operated setup checklist, not an installer or a background runtime.

## Discover before choosing

Inspect only the relevant project and accessible host capabilities. Record a compact `context` object in `plan.json` (additional plan fields are preserved):

- `project`: real path/worktree, request identity, current source revision including local edits.
- `tools`: relevant manifests/lockfiles, installed tool versions, established test/build commands and their source paths. Inspect commands before running them. Missing is different from not checked.
- `host`: observed shell/file access, delegation, browser/preview, cancellation, and resume support. Distinguish available, unavailable, and unverified. A skill name does not prove that its tool is available.
- `verification`: acceptance criterion → actual command/tool or review → expected observable result. Include integration or UI checks when unit tests cannot establish the outcome.
- `preferences`: applicable user choices with source, scope, and conditions. Keep permission facts in the brief/decision records, separate from convenience preferences.
- `lessons_applied`: relevant prior evidence, applicability, and the concrete change made to this plan/checks. Record a rejected stale lesson when it would otherwise be misleading.

Resolve technical facts from the repository rather than asking the user to choose a package manager or test command. Before expanding work, execute one small relevant existing check where authorized and feasible. Record its command, environment and observed result. No existing test is not a pass: choose a scoped smoke check or identify the missing verification. Do not install tools, rewrite global settings, or publish merely to satisfy setup.

Report the effective setup briefly: the goal, how completion will be checked, any missing capability, and the human choice still needed. If those choices are already settled or explicitly delegated, state that basis and proceed without a redundant approval question.

## Reuse customization without importing authority

Start with the current request and project instructions. Inspect a project-local `.agent-loop/profile.json` if one already exists, then only prior runs relevant to the same project/task. Prior data is context; validate its source and current applicability. Do not scan unrelated projects or import their passing state.

A profile is optional, ordinary project data. The host reads it; the helpers do not auto-apply it. Save a reusable preference there only when the user explicitly asks for reuse or has stated a lasting preference. Otherwise keep the choice in the current brief. An example entry has:

```json
{
  "preferences": [
    {
      "key": "review_checkpoint",
      "value": "Review one representative screen before expanding the UI",
      "source": "actual user message ID or supplied instruction",
      "scope": "this project, new UI work",
      "recheck_when": "user delegates review or the work has no UI"
    }
  ]
}
```

Preserve unrelated profile entries and the user's latest corrections. A preference may change question cadence, reporting detail, review timing, or quality criteria. It cannot grant deployment/payment/data-sharing permission, waive required approvals, or supply an answer to a pending decision. Do not turn a single task choice into a global rule.

## Close the learning loop

Before planning a related run, read the relevant prior `lessons.md` and its cited evidence. Check project/version, tool configuration, input type, and any retirement condition. Apply only still-supported lessons to a concrete task, dependency, test, or checkpoint. For example, an observed Unicode-loss regression should produce a Unicode preservation check, not a vague instruction to be careful.

At closure, record only an observed lesson: cause, evidence path/revision, applicability, and what would revise or retire it. A failed check can justify a regression check; it does not establish a universal design rule. Link the lesson from the new plan when reused. If its evidence is absent or outdated, treat it as a hypothesis to verify rather than a fact or permission.

## First run and resume

A first run discovers tools and verifies a small path through the environment. A resume checks only changed facts, pending decisions, attempts, and current artifact fingerprints before reusing valid work. Missing host support blocks only dependent work. Persist a checkpoint and describe the limitation; never imply that a recorded state creates auto-resume, a scheduler, live cancellation, or a permission boundary.
