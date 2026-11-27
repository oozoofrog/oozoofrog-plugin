# Counterfactual replays and the blind judge

A replay runs a past request again on other models, so a card's reference can rest on evidence instead of inference. Replays cost the most tokens of the review. Run them only after G1.

## Pick cases

- Pick 2–4 boundary cards whose reference is `inferred`.
- Only tasks whose inputs live inside one repository. A task that read home config, other project folders, the network or a device cannot be isolated.
- Prefer read-and-judge tasks (design decision, review, analysis). Code-change replays work too but need a build or test to judge.

## Isolate

1. Find the commit just before the episode: the last commit before the episode's first request, or the T3 checkpoint ref recorded for that thread.
2. Make a local clone (not a worktree; a worktree changes the original repo's worktree list): `git clone --no-hardlinks <repo> <sandbox>/<project-like-name>` then `git -C <clone> checkout <commit>` and `git -C <clone> remote remove origin`. No remote means no push.
3. Check what else the original episode could read and whether it still exists today in a later state: home config, memory or skill files, sibling folders. A folder or skill that the original episode itself created leaks the original answer. If anything outside the repo matters and cannot be pinned, drop the case or mark its result INCONCLUSIVE.
4. Put sandboxes under `<R>` or another location the user chose. Never under a system temp folder that may be cleared.

## Prompt

- Use the user's original request, lightly cleaned. Organic wording only: no "eval", "test", "judge", "experiment", "rubric", "score", "compare", "benchmark", "candidate".
- The same prompt for every model.
- If the original delegated or changed code and you need a judgment only, add one sentence such as "Decide here; do not delegate or change files." Record it as a known difference.
- Ask for the answer in a file with a random name (for example `notes/note-k3.md`). Keep the mapping from file to model in `<R>/replay/mapping.json`, which the judge never sees.
- Do not tell a candidate that other candidates exist.

## Candidates

Default set: Sonnet 5.5 high, Opus 5.5 medium, Fable 5.2 medium, one subagent each, each in its own clone. Add Haiku 5.5 only for volume-type cases. Estimate tokens before G1 from the original runs' `max_context_tokens` and output size, per candidate and in total, and say that it is an estimate.

## G1 contents

Show: cases (card id and one line each), models and effort, estimated tokens per case and in total, the isolation setup (commit, clone path, what was checked outside the repo), and the judge. Wait for approval.

## Judge

1. Prefer a judge from a different vendor (for example a Codex model through T3 Code). If none is available, the main agent judges, and the report MUST say that no independent verdict exists.
2. Copy the answers to anonymous labels per case (`A.md`, `B.md`, `C.md`), shuffled per case.
3. Brief: the user request, 3–5 criteria scored 1–5, and a rank. One pass per case, all answers on one scale. Ties only when no meaningful difference exists.
4. The judge MUST check key factual claims against the source: for a review, open the cited files and lines for every high-severity finding and a sample of the rest, and mark each `confirmed`, `partly` or `false`. No build, run or file change.
5. Example criteria for a review case: correctness (false high findings cost more than missed low ones), coverage, severity calibration, actionable fixes, honest scope. For a planning case: problem fit, grounding in real facts, concrete proposal, decisions surfaced with consequences, clarity.

## After the verdict

1. Read every candidate answer yourself, end to end.
2. Re-check the judge's decisive claims in the source yourself (the two or three facts that decide the ranking).
3. Update the card: `evidence: replay` and the reference set, or keep `inferred` and record why (leak, judge error, tie).

## Cost comparison

Compare token use only at equal context. A long thread re-reads its whole context on every call, so an original run deep in a thread can show far more cache-read tokens than a fresh replay of the same step. That gap is about context length, not the model. Use `max_context_tokens` from the log extractor to show the original's context size, and say which gap is due to context.
