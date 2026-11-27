# Procedure

`<R>` is the review directory the user chose. `<S>` is this skill's `scripts/` directory. Analysis steps are reversible and proceed without asking. Only G1 and G2 wait for the user. Keep a decision log at `<R>/decisions.tsv` (columns: `ts`, `phase`, `decision`, `why`, `evidence`, `result`), one row per decision or failure found.

Verdict words: VERIFIED (checked on the artifact), NOT VERIFIED (checked and failed), INCONCLUSIVE (cannot be decided from the data). Report strata with fewer than 10 runs as INCONCLUSIVE, not as rates.

## A. Frame

1. State the goal: the user picks a model and effort by trained judgment, backed by their own cases.
2. Agree a falsifiable done predicate with the user. A default that has worked:
   - P1: in round 2, the user makes fewer over-picks (a model above the reference set) than in round 1.
   - P2: every reference answer names its evidence kind; at least 3 boundary cards are `replay` if replays are run.
   - P3: a one-page guide exists and every rule cites at least one card.
   Do not use a fixed pass mark (for example "most cards right") that the baseline may already meet; with few cards a gain cannot be shown from a high start. If round 1 shows this, propose a new predicate and record the change.
3. Agree the period (for example the last 2–4 weeks) and the card count (default 16: 8 per round).

## B. Extract

T3 DB present:

```sh
python3 -I <S>/snapshot_db.py --source <path to statev2.sqlite> --dest <R>/data
python3 -I <S>/extract_t3.py --db <R>/data/t3state.sqlite --out <R>/data
```

Log-only:

```sh
python3 -I <S>/extract_logs.py --out <R>/data --since <YYYY-MM-DD>
```

Both write `messages.jsonl` (human messages) and `runs.jsonl` (one row per distinct run, with `reaction_id`, `steer_ids`, `follow_state`). Check: the printed counts are plausible, and 10 random rows of `messages.jsonl` are text a person typed. Record the effort coverage line.

When both sources are available, use the T3 runs for model, effort and timing, and use logs for token use per call (`max_context_tokens`) and for the full reply text when a card needs it.

## C. Label reactions

```sh
python3 -I <S>/export_items.py --data <R>/data --calib 40
```

1. Hand-label every item in `calib.jsonl` with the follow-up rubric in [rubrics.md](rubrics.md). Save `{item_id: label}` to `<R>/data/labels_hand.json`.
2. Give Haiku 5.5 subagents the rubric and the items only, in batches of about 200. Include the calibration items blind among them. Never pass `key.json`; it links items to runs and models.
3. Compare Haiku labels with the hand labels on the calibration items. Record exact agreement and fix-vs-not agreement.
4. At ≥ 85 % exact agreement, use Haiku labels as data. Below it, use them only to pick card candidates, report no rates from them, and say so.
5. Run the task-type rubric the same way on episodes (after phase D) if you need it for sampling. The same 85 % gate applies. Long episodes often mix kinds of work; one label per episode is a weak premise, so expect lower agreement.

## D. Episodes and sampling

```sh
python3 -I <S>/episodes.py --data <R>/data --labels <R>/data/labels_hand.json <R>/data/labels_haiku_*.json
```

1. Check: a rerun gives identical output. Read 20 random episode boundaries by hand. A classifier sometimes labels a plain go-ahead as `new_topic`, which over-splits; that makes fix counts per episode a lower bound. Record precision.
2. Stratify by model × outcome (`smooth`, `one_fix`, `rough`) × task type. Every stratum with ≥ 3 episodes gets at least one card candidate.
3. Exclude the review's own thread and any episode the user already discussed in this review.

## E. Cards

Write cards per [cards.md](cards.md). Read every run of a chosen episode by hand, fix wrong boundaries there, and record the run ids. Put the cards that will get replay evidence in round 2, so their references are final when round 2 is scored.

## F. Round 1 (baseline)

Ask one card per AskUserQuestion question, options Haiku 5.5 / Sonnet 5.5 / Opus 5.5 / Fable 5.2. Show the card's question text only (no actual model, outcome or reference). Store picks in `<R>/cards/round1_picks.json` before showing anything else. Then reveal each card's actual model, outcome, reference and lesson, and score:

```sh
python3 -I <S>/score_practice.py --cards <R>/cards/cards.json --picks <R>/cards/round1_picks.json --round 1
```

## G. Counterfactual replays (optional, G1)

Follow [replay-and-judge.md](replay-and-judge.md). Pick boundary cards whose reference is only `inferred`. Wait for G1 approval.

## H. Guide

Write one page (`<R>/cards/guide.md`) from round-1 cards and replay results only. Every rule cites at least one card id. Citing a round-2 card would reveal a held-out answer. Useful rule shapes: "what is hard in this task" → starting model; checks before upgrading ("is the fix the model's fault?", "is effort already excessive?", "is a long thread inflating the cost?"); and one sentence on the user's own pick habit from round 1.

## I. Round 2 (held-out)

Same as round 1 with the round-2 cards, after the user has read the guide. Score with `--round 2`. Report right, over and under picks per round and per evidence kind. If misses fall only on `inferred` cards, the data cannot tell "user over-picks" from "references too low": report INCONCLUSIVE for that side.

## J. Recurring method corrections (G2)

1. Collect reactions labelled `method`. Cluster them (Haiku first pass, then a hand check). Each cluster lists its item ids and thread count.
2. For clusters that repeat in ≥ 3 threads, check existing rules: CLAUDE.md, memory files, skills. Note the date each rule appeared, and count corrections before and after that date. Status per cluster: `missing rule`, `rule exists and works`, `rule exists but not followed`, `rule conflicts with the user`, or `one-off`. If a file's dates are unreliable, say "not checked by date".
3. A rule that exists but keeps being corrected needs a check or hook, not more text. Propose the smallest mechanism and dry-run it on real data first, for example with `sample_final_messages.py` for a Stop-hook check: report catches and false alarms against hand labels.
4. Any change to global instructions, memory, settings or hooks is G2: show the exact diff and evidence, back up the file, and wait for approval per change. A check must not fight another standing instruction (exempt lines that another rule requires).

## Hand back

Check each predicate and give its verdict. Report open items. Offer to delete the DB snapshot and any replay sandboxes; delete only after the user agrees.
