---
name: model-fit-review
description: Review your own past Claude Code sessions to learn when Fable 5.2, Opus 5.5, Sonnet 5.5 or Haiku 5.5 (and which effort) fits a task. Builds case cards from your real episodes, runs predict-then-reveal practice rounds, and optionally runs a few blind counterfactual replays judged by another vendor. A learning loop, not a cost audit; creative or deep-analysis work is never downgraded only to save tokens. "모델 적합성 검토", "어떤 모델이 맞았는지 세션 검토", "모델 선택 감각 연습", "지난 세션으로 모델 고르기 연습", "내 작업에 어떤 모델이 맞았는지 돌아보기"에 사용한다. 지금 할 작업 하나의 모델 추천은 model-advisor를 쓴다.
---

# Model-fit review

Help the user build their own judgment for choosing a Claude model and effort, using cases from their own session history. The output is case cards, two practice rounds, a one-page decision guide, and (optional) proposals for recurring method corrections.

This is a learning loop. Do not frame results as savings. Never recommend a smaller model for creative work or deep analysis only because it costs fewer tokens.

## Before you start

1. Ask once (AskUserQuestion) where to keep the review files. Suggest `<project working dir>/_model-fit-review/`. Never assume a secondary disk or any fixed path. All later outputs go there.
2. Find the inputs:
   - Required: Claude Code session logs, by default `~/.claude/projects/*/*.jsonl`.
   - Optional: a T3 Code state DB (`statev2.sqlite`). It adds per-run model and effort and the run completion time.
3. If the T3 DB exists, tell the user the copy can be several GB, then run `scripts/snapshot_db.py --source <db> --dest <review dir>/data`. It opens the source read-only, checks free space and copies with `sqlite3 "file:...?mode=ro" ".backup <dest>"`. Never read the live DB for analysis.
4. If there is no T3 DB, use the log-only path. Effort is then known only where the log records it. State the coverage in the report.

## Phases

Follow [references/procedure.md](references/procedure.md) for every step, its check and its output file. Summary:

| Phase | Do | Gate or check |
|---|---|---|
| A. Frame | Agree the goal, the done predicate and the period | Predicate is falsifiable |
| B. Extract | `extract_t3.py` or `extract_logs.py` → messages and distinct runs | Counts printed; human filter applied |
| C. Label | Hand-label 30–40 items, then calibrated Haiku labels with [references/rubrics.md](references/rubrics.md) | ≥ 85 % agreement, or labels used only for sampling |
| D. Episodes | `episodes.py` groups runs; sample by model × outcome × task type | 20 boundaries read by hand |
| E. Cards | Write cards per [references/cards.md](references/cards.md) | Each fact traces to a run id |
| F. Round 1 | Practice via AskUserQuestion, one card per question | Baseline stored before any guide |
| G. Replays (optional) | [references/replay-and-judge.md](references/replay-and-judge.md) | **G1** approval first |
| H. Guide | One page, every rule cites round-1 cards only | Each rule has a card id |
| I. Round 2 | Held-out cards, then `score_practice.py` | Over- and under-picks reported |
| J. Method corrections | Cluster and check against existing rules | **G2** approval per change |

## Gates

- **G1** — before any replay: show cases, models and effort, estimated tokens, and the isolation setup. Wait for approval.
- **G2** — before any change to CLAUDE.md, memory, settings or hooks: show the exact change and its evidence. Wait for approval for each change separately.

## Rules that are easy to get wrong

Read [references/lessons.md](references/lessons.md) before Phase B. The short form:

- Count only human messages, and count distinct runs. The reaction to a run is the first human message after it completed; earlier messages are steer.
- Session commands (`/compact`, `/clear`, `/reload-*`, `/mcp`, `/output-style`) are not tasks. A slash-invoked skill with text is a task.
- Keep model names out of every item given to a classifier or judge.
- A "fix" reaction is not always a model failure. Cards separate result fixes from method corrections.
- Compare token cost only at equal context length.
- Scores are only as good as the reference answers. Say which references are `replay`, `observed` or `inferred`.

## Report

End with: inputs used (logs only, or logs + T3 DB) and effort coverage; what was VERIFIED, NOT VERIFIED or INCONCLUSIVE; round scores with over- and under-picks; the guide; open G2 proposals; and the location of the snapshot copy with an offer to delete it.

## Host notes

Claude Code is the reference host. Choosing a subagent model (Haiku classifiers, replay candidates) is Claude Code–only. In Codex, the extraction scripts, cards, practice rounds and guide work; skip the calibrated Haiku labels (hand-label a smaller sample and say so) and run replays only if the host can start sessions on the named Claude models.
