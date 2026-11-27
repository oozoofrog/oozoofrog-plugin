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

Use the period agreed in A. `--since` and `--until` are inclusive UTC dates. They apply to the time of a run's first request; a reaction sent after `--until` still resolves. Both scripts refuse an output directory inside a git work tree unless git ignores it. Set `TMPDIR` (and `SQLITE_TMPDIR`, or pass `--tmp` to `extract_t3.py`) to keep temporary files off a small disk.

T3 DB present:

```sh
python3 -I <S>/snapshot_db.py --source <path to statev2.sqlite> --dest <R>/data --yes
python3 -I <S>/extract_t3.py --db <R>/data/t3state.sqlite --out <R>/data --since <YYYY-MM-DD> --until <YYYY-MM-DD> --projects ~/.claude/projects
```

`--yes` is required in a non-interactive shell. An existing snapshot is kept; pass `--force` to replace it. `--projects` adds `max_context_tokens` from the logs (join below).

Log-only:

```sh
python3 -I <S>/extract_logs.py --out <R>/data --since <YYYY-MM-DD> --until <YYYY-MM-DD>
```

To use the logs with the T3 DB as the authority on which prompts are human, add `--t3-db <R>/data/t3state.sqlite`.

Both write `messages.jsonl` (human messages) and `runs.jsonl` (one row per completed Claude run with `initiator`, `follow_state`, `reaction_id`, `next_id`, `superseded_by` and `steer_ids`), and print the same count lines: human messages (all, and attached to Claude runs), Claude runs (human- and agent-initiated), follow states, steer, and effort known over human-initiated runs. Record them.

Check: read the 10 rows that the script writes to `human_check.jsonl` (random, fixed seed) and count the ones a person typed. Record `precision k/10` in the decision log. Below 9/10, find the injected kind, extend the filter (see lessons.md, lesson 1) and rerun.

### Joining T3 threads and logs

`orchestration_v2_projection_provider_threads.payload_json` → `nativeThreadRef.nativeId` equals the Claude Code session file name (`<nativeId>.jsonl`). One T3 thread can map to several session files (a new session after a handoff). Within a mapped pair, a log prompt matches a T3 human message when the times differ by at most 10 minutes and the normalized texts agree: `$skill` (T3) and `/skill` (log) are the same token wherever they stand; attachment markers (`[File: …]`, `[Image #1]`, `[name](t3-context://…)`) and appended context blocks are dropped; then the texts are equal or one contains the other. A log prompt that is only a slash command (its typed text sits in the next meta entry) matches within 30 seconds. `mfrlib.match_prompts` encodes this. Session files that the DB does not know (for example plain CLI sessions) keep the log rules.

Use the T3 runs for timing and human-message origin, the logs for token use per call (`max_context_tokens`) and the full reply text when a card needs it. Effort is in both.

### Reaction states

The timeline of a thread is every completed run: Claude and other providers, human- and agent-initiated. For a Claude run R, `next` is the first human message at or after R completed.

| `follow_state` | Condition | Meaning |
|---|---|---|
| `reaction` | No other run completed between R and `next`; `next` is not attached to a non-Claude run | `next` reacts to R's result. It is the only state that gets a follow-up label. |
| `superseded` | Another run L completed between R and `next` (`superseded_by` = the latest L) | `next` reacts to a later result. If L is a Claude run, `next` is L's reaction. |
| `other_provider` | `next` is attached to a non-Claude run | Never counted as a reaction to a Claude run. |
| `end` | No later human message | — |

Steer: human messages sent after R started and before R completed, except R's own first request and messages attached to a non-Claude run. The user had not seen R's result. Version 0.1.0 called the superseded state `pre_result` and looked only at runs that carried a human message.

Question answers (`creationSource='server'` rows by the user) are counted on their own line and are never a reaction, steer or request; see lessons.md.

## C. Label reactions

**C0 (consent).** Before any classifier runs, tell the user that request text, the end of the agent's reply and the next message go to classifier subagents, with model names masked and no ids. Ask for consent. Without it, hand-label only and report no classifier labels.

```sh
python3 -I <S>/export_items.py --data <R>/data --calib 40 --seed 7
```

Every item has a `kind`: `reaction` or `steer`. `calib.jsonl` is a random sample of reaction items (fixed seed). Model names and ids are masked as `[model]` in all text.

1. Hand-label every item in `calib.jsonl` with the follow-up rubric in [rubrics.md](rubrics.md). Save `{item_id: label}` to `<R>/data/labels_hand.json`.
2. Give Haiku 5.5 subagents the rubric and the items only, in batches of about 200. Use the follow-up rubric for `reaction` items and the steer rubric for `steer` items. Include the calibration items blind among them. Never pass `key.json`; it links items to runs and models.
3. Compare Haiku labels with the hand labels on the calibration items (reactions only). Record exact agreement and fix-vs-not agreement.
4. At ≥ 85 % exact agreement, use Haiku reaction labels as data. Below it, use them only to pick card candidates, report no rates from them, and say so. Steer labels are not calibrated; report steer counts as indicative only.
5. For the task-type rubric, run `export_items.py --data <R>/data --episodes --calib 30` after phase D. It writes `episode_items.jsonl` (first 6 requests of each episode, each cut at 220 characters, and `n_requests`), `episode_calib.jsonl` and `episode_key.json`. The same 85 % gate applies. Long episodes often mix kinds of work; one label per episode is a weak premise, so expect lower agreement.

## D. Episodes and sampling

```sh
python3 -I <S>/episodes.py --data <R>/data --hand <R>/data/labels_hand.json --labels <R>/data/labels_haiku_*.json --exclude-thread <own thread id>
```

Label precedence: a hand label always wins over a classifier label for the same item, whatever the order of the files. Files given with `--hand` are hand labels, and so is any `--labels` file named `labels_hand*.json`. Among classifier files, a later file wins. The printed `unlabeled reactions` counts only items that `export_items.py` exports, so reactions to session-command runs are not in it.

1. Check: a rerun gives identical output. Read 20 random episode boundaries by hand, or all of them if there are fewer than 20, and say which. A classifier sometimes labels a plain go-ahead as `new_topic`, which over-splits; that makes fix counts per episode a lower bound. Record precision.
2. Stratify by model × outcome (`smooth`, `one_fix`, `rough`) × task type. Every stratum with ≥ 3 episodes gets at least one card candidate. Episodes with `delegated: true` (every run agent-initiated, for example a delegated child session) form their own stratum.
3. Exclude the review's own thread and any episode the user already discussed in this review. To find the own thread: in Claude Code, the current session id is the stem of the newest `.jsonl` file in `~/.claude/projects/<working-dir slug>/`, the file that grows while you work; it is the `thread` value on the log path. On the T3 path, look that id up as `nativeThreadRef.nativeId` (join above) to get the T3 thread id. Pass the id to `--exclude-thread`.

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

Check each predicate and give its verdict. Report open items. Offer to delete the DB snapshot and any replay sandboxes; delete only after the user agrees. Delete the snapshot with `python3 -I <S>/snapshot_db.py --delete <R>/data/t3state.sqlite`; it also removes any `-wal`, `-shm` or `-journal` file next to it.
