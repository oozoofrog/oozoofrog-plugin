# Cards and guide

## Card format

Store all cards in `<R>/cards/cards.json` as a list. Write the user-facing fields in the user's language.

```json
{
  "id": "1-3",
  "round": 1,
  "episode": "e0042",
  "question": "Decide whether the app's export module should become its own package, then draft an ADR. 3 requests.",
  "actual": "Opus 5.5 · high",
  "outcome": "smooth",
  "result_fixes": 0,
  "method_corrections": 1,
  "reference": ["Sonnet", "Opus"],
  "evidence": "replay",
  "confidence": "medium",
  "lesson": "The evidence lives in the repository; a Sonnet 5.5 high replay reached the same decision.",
  "run_ids": ["<run id>", "<run id>"]
}
```

The example is synthetic. Field rules:

- `question`: what the user asked and how many requests, in plain terms. No actual model, effort, outcome or hint at the answer. Remove names the user would not want on a card.
- `actual`: model and effort used. Write `effort unknown` when no source records it.
- `outcome`: `smooth` (no result fix), `one_fix`, or `rough` (≥ 2 result fixes).
- `result_fixes` and `method_corrections`: count them separately. A `fix` reaction is a result fix only when the model got it wrong. Move these to `method_corrections` or leave them out, and say why in `lesson`:
  - the user's own mistaken facts in the request;
  - taste iteration (design rounds that converge on a preference);
  - results the user could not see (for example a page not deployed yet);
  - process rules (how to ask, where to work, whom to delegate to).
- `reference`: one or two acceptable model families. Two when either is reasonable.
- `evidence`: `replay` (a counterfactual run was judged), `observed` (the log outcome shows it, for example a smaller model succeeded smoothly on this task), or `inferred` (reasoning only). Combine with `+` when both apply, and score by the strongest kind.
- `confidence`: low, medium or high.
- `run_ids`: every run the card's facts come from. Each fact must trace to one of them.

Cards whose references will come from replays belong in round 2. Mark them `pending replay` until the verdict is in.

## Practice questions

One AskUserQuestion question per card. Header: the card id. Question: the card's `question`. Options in this order: Haiku 5.5, Sonnet 5.5, Opus 5.5, Fable 5.2, each with a one-line description of what that model is for. Do not mark a recommended option. Do not reveal anything until all cards of the round are answered and the picks are saved.

## Reveal

Per card: the pick, the reference set, the actual model and effort, the outcome, the evidence kind, and the lesson. Then the round summary from `score_practice.py`: right, over-picks, under-picks, and right picks per evidence kind. State that the score is only as good as the reference answers.

## Guide

One page. Each rule cites at least one round-1 card id (and replay ids if any). No round-2 card before round 2 is scored. A guide addition written after round 2 may cite round-2 cards. Suggested sections:

1. What is hard in this task → starting model (table with the card ids).
2. Before upgrading: is the fix the model's fault; would a check or procedure prevent the failure better than a bigger model; is effort already more than the task needs; is a long thread inflating cost.
3. The user's habit: one sentence from round 1 (for example "both misses were one level above the reference"), and a self-check ("say in one sentence what fails without this model; if you cannot, pick one level lower").

Never write a rule that downgrades creative or deep-analysis work only because it is cheaper.
