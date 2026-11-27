---
name: model-fit-review
description: Review your own past Claude Code sessions to learn when Fable 5.2, Opus 5.5, Sonnet 5.5 or Haiku 5.5 (and which effort) fits a task. Builds case cards from your real episodes, runs predict-then-reveal practice rounds, and optionally runs a few blind counterfactual replays judged by another vendor. A learning loop, not a cost audit; creative or deep-analysis work is never downgraded only to save tokens. "모델 적합성 검토", "어떤 모델이 맞았는지 세션 검토", "모델 선택 감각 연습", "지난 세션으로 모델 고르기 연습", "내 작업에 어떤 모델이 맞았는지 돌아보기"에 사용한다. 지금 할 작업 하나의 모델 추천은 model-advisor를 쓴다.
---

# Model-fit review

Help the user build their own judgment for choosing a Claude model and effort, using cases from their own session history. The output is case cards, two practice rounds, a one-page decision guide, and (optional) proposals for recurring method corrections.

This is a learning loop. Do not frame results as savings. Never recommend a smaller model for creative work or deep analysis only because it costs fewer tokens.

## Before you start

1. Ask once (AskUserQuestion) where to keep the review files. Suggest a directory outside every git repository, for example `~/model-fit-review/`. The files hold message text, so a directory inside a git work tree must be git-ignored; the scripts refuse any other directory inside a work tree (override: `--allow-repo`). Never assume a secondary disk or any fixed path. All later outputs go there.
2. Find the inputs:
   - Required: Claude Code session logs, by default `~/.claude/projects/*/*.jsonl`. They record model and token use per call, and effort on most assistant entries.
   - Optional: a T3 Code state DB (`statev2.sqlite`). It adds which user rows a person typed (human-message origin), run completion times, and the runs other agents started. It does not add effort.
3. If the T3 DB exists, tell the user the copy can be several GB, then run `scripts/snapshot_db.py --source <db> --dest <review dir>/data --yes`. An agent's shell has no terminal, so `--yes` is required there; without it the script asks and stops. It opens the source read-only, checks free space, copies with the SQLite backup API and switches the copy to `journal_mode=DELETE`, so no `-wal` or `-shm` files appear. Never read the live DB for analysis.
4. If there is no T3 DB, use the log-only path. State the effort coverage and the human-filter precision in the report.
5. Set `TMPDIR` (and `SQLITE_TMPDIR`) when the default temporary directory is on a small disk; every script honors them.

## Phases

Follow [references/procedure.md](references/procedure.md) for every step, its check and its output file. Summary:

| Phase | Do | Gate or check |
|---|---|---|
| A. Frame | Agree the goal, the done predicate and the period | Predicate is falsifiable |
| B. Extract | `extract_t3.py` or `extract_logs.py` with `--since`/`--until` → messages and distinct runs | Counts printed; 10 random human messages read, precision recorded |
| C. Label | **C0** consent, then hand-label 30–40 reaction items and run calibrated Haiku labels with [references/rubrics.md](references/rubrics.md) | ≥ 85 % agreement on reactions, or labels used only for sampling |
| D. Episodes | `episodes.py` groups runs; sample by model × outcome × task type | 20 boundaries (all if fewer) read by hand |
| E. Cards | Write cards per [references/cards.md](references/cards.md) | Each fact traces to a run id |
| F. Round 1 | Practice via AskUserQuestion, one card per question | Baseline stored before any guide |
| G. Replays (optional) | [references/replay-and-judge.md](references/replay-and-judge.md) | **G1** approval first |
| H. Guide | One page, every rule cites round-1 cards only | Each rule has a card id |
| I. Round 2 | Held-out cards, then `score_practice.py` | Over- and under-picks reported |
| J. Method corrections | Cluster and check against existing rules | **G2** approval per change |

## Gates

- **C0** — before Phase C: tell the user that request and reply text (with model names masked) goes to classifier subagents, and ask for consent. Without consent, hand-label a smaller sample and say so.
- **G1** — before any replay: show cases, models and effort, estimated tokens, and the isolation setup. Wait for approval.
- **G2** — before any change to CLAUDE.md, memory, settings or hooks: show the exact change and its evidence. Wait for approval for each change separately.

## Rules that are easy to get wrong

Read [references/lessons.md](references/lessons.md) before Phase B. The short form:

- Count only human messages, and count distinct runs. The reaction to a run is the first human message after it completed, and only if no other run of the thread (any provider, including runs that a delegation result started) completed first; otherwise the run is `superseded`. Messages sent while it ran are steer.
- Session commands (`/compact`, `/clear`, `/reload-*`, `/mcp`, `/output-style`) are not tasks. A slash-invoked skill with text is a task.
- Keep model names out of every item given to a classifier or judge.
- A "fix" reaction is not always a model failure. Cards separate result fixes from method corrections.
- Compare token cost only at equal context length.
- Scores are only as good as the reference answers. Say which references are `replay`, `observed` or `inferred`.

## Report

End with: inputs used (logs only, or logs + T3 DB), the period, effort coverage and human-filter precision; what was VERIFIED, NOT VERIFIED or INCONCLUSIVE; round scores with over- and under-picks; the guide; open G2 proposals; and the location of the snapshot copy with an offer to delete it (`snapshot_db.py --delete <snapshot>` also removes `-wal`/`-shm` files).

## Host notes

Claude Code is the reference host. Choosing a subagent model (Haiku classifiers, replay candidates) is Claude Code–only. In Codex, the extraction scripts, cards, practice rounds and guide work; skip the calibrated Haiku labels (hand-label a smaller sample and say so) and run replays only if the host can start sessions on the named Claude models.
