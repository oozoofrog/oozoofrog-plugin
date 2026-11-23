# Spec: experiment page for generated reading coaches

Status: Proposed. Decisions D1 to D10 are Approved (user, 2026-11-24, in three batches of multiple-choice questions). All acceptance criteria are Proposed (AI).

Applies to `wild-reading-coach-builder` 0.2.0. The paths in this document are relative to `plugins/wild-reading-coach-builder/skills/wild-reading-coach-builder/` unless they start with another root.

## Goal

A generated reading coach gives the reader an optional local web page. The page and the conversation work together. The page is a workspace for one experiment: the reader writes an action and a prediction, and later sees that prediction beside the result they observed. The conversation stays the place where the coach checks evidence, gives hints, and asks questions.

## Terms

- **Experiment**: one small action that the reader chose in their work or life, the result they predict, and the date when they can see the result. This is the "act, observe, and interpret" move in `assets/coaching.md`.
- **Experiment entry**: the record of one experiment in `PROFILE.md`.
- **Experiment page**: the file `experiment.html` that the coach writes on request.
- **Handoff block**: plain text that the page composes from the reader's input. The reader copies it into the conversation.
- **Coach directory**: the real directory that contains the coach's `SKILL.md` and `PROFILE.md`, after symlinks are resolved.

## Decisions

| # | Decision | Source | Rejected alternative | Valid while |
|---|---|---|---|---|
| D1 | A prediction is about the result of the reader's own action. It is not a guess about the book's content. | Approved (user, 2026-11-24) | Predict what the passage says: easier to write, but it is not the method in `assets/coaching.md`. | The coaching method keeps the act-observe-interpret move. |
| D2 | The page stores nothing. A reload erases text that the reader did not copy. The page says so. | Approved (user, 2026-11-24) | Keep a draft in browser storage: survives a reload, but creates reader state that the coach cannot read. | `PROFILE.md` is the only reader record. |
| D3 | The page shows locators only. It shows no book text and no links to passage files. | Approved (user, 2026-11-24) | Link the Markdown passage files: a browser shows raw Markdown and does not go to the locator. Embed the passage: copies book text into the page. | Passages stay Markdown with HTML-comment locators. |
| D4 | The page is one file, `experiment.html`, in the coach directory. Each generation overwrites it. | AI-proposed. Approved (user, 2026-11-24) | One file for each experiment: keeps a history, but that history duplicates `PROFILE.md`. | The page is a view of the profile only. |
| D5 | An experiment entry has a sequential key and fixed fields. See AC-2.1. | AI-proposed. Approved (user, 2026-11-24) | Free prose: fits the current profile style, but a later session cannot pair a result with its prediction. | The comparison must be rebuilt from the profile. |
| D6 | The coach writes the HTML itself from the rules in `assets/coaching.md`. There is no page template asset. | AI-proposed. Approved (user, 2026-11-24) | A template that the publisher copies: uniform pages, but it needs one more publisher change. | Walkthrough pages meet AC-1.2 to AC-1.6. If they do not, add the template. |
| D7 | The reader moves the handoff block by select and copy. A copy button is optional. | AI-proposed. Approved (user, 2026-11-24) | Clipboard API only: one click, but browsers can refuse it for a local file. | The page is opened as a local file. |
| D8 | The release is version 0.2.0. `scripts/make_coach.py` gains an option that updates the coaching instructions of an existing coach. | Approved (user, 2026-11-24). The user chose this against the AI recommendation of a manual update. | Manual update by the operator: no publisher change, but each coach needs a careful hand edit. New coaches only: safest, but the coach in use cannot run the pilot. | The update touches only `SKILL.md` in the coach directory. |
| D9 | Each criterion has a text-contract test that checks the instruction text, and a walkthrough step that checks coach behavior. | AI-proposed. Approved (user, 2026-11-24) | Walkthrough only: no repeated check that the instruction text stays. | Coach behavior comes from instruction text. |
| D10 | The update runs only with the explicit option `--update-coaching` and the same `--source` file. It keeps the replaced `SKILL.md` as `SKILL.md.previous`. | AI-proposed. Approved (user, 2026-11-24) | Update without the source file: easier for the operator, but the script cannot confirm which coach it rewrites. No backup copy: fewer files, but a hand-edited instruction is lost. | The source marker identifies a coach. |

## Acceptance criteria

The verification column names a test in `scripts/tests/test_wild_reading_coach_builder.py` and a step in the walkthrough below. A text-contract test proves that the instruction is in `assets/coaching.md` or `SKILL.md`. It does not prove coach behavior. Only the walkthrough proves behavior.

### Goal 1: the page

| ID | Keyword | Criterion | Verification |
|---|---|---|---|
| AC-1.1 | MUST | When the reader asks for the page, the coach writes one file named `experiment.html` in the coach directory and tells the reader its full path. The file is not in `references/`. A later generation overwrites the same file. | `test_ac1_1`, W2 |
| AC-1.2 | MUST | The file is self-contained. It loads nothing from the network or from other files. It does not use `localStorage`, `sessionStorage`, IndexedDB, or cookies. | `test_ac1_2`, W2 |
| AC-1.3 | MUST NOT | The page does not show book text, figures, or links to passage files. It does not show a completion percentage, time spent, a streak, or a count of items read. | `test_ac1_3`, W2 |
| AC-1.4 | MUST | The new-experiment view shows the two or three entry points that the coach verified for this reader, each with its locator and a one-line reason. The reader selects one. The view has three fields: the action, the predicted result, and the date to check. The date field may stay empty. | `test_ac1_4`, W2 |
| AC-1.5 | MUST | The page composes a handoff block from the selected locator and the three fields. The reader can select and copy the block without a script permission. | `test_ac1_5`, W3 |
| AC-1.6 | MUST | The page states, in the reader's language, that it saves nothing and that a reload erases text that was not copied. | `test_ac1_6`, W3 |
| AC-1.7 | MUST | When an experiment entry has a result, the regenerated page shows the prediction and the result side by side, each with its date, in the reader's exact words. Neither is in an input field. Reader text is escaped so that it shows as text. | `test_ac1_7`, W5 |
| AC-1.8 | MUST | The coach creates the page only when the reader asks. All coaching works when the reader never asks. The coach accepts the same experiment typed directly in the conversation. | `test_ac1_8`, W1 |
| AC-1.9 | MUST NOT | The coach does not publish, host, or upload the page or its content. | `test_ac1_9`, W2 |

### Goal 2: the record

| ID | Keyword | Criterion | Verification |
|---|---|---|---|
| AC-2.1 | MUST | When the reader gives an experiment, by a handoff block or in their own message, the coach appends an experiment entry to `PROFILE.md`. The entry has a key `E<n>` that is one more than the last key, the date, the locator, the action, the prediction in the reader's exact words, and the date to check when given. | `test_ac2_1`, W4 |
| AC-2.2 | MUST | When the reader reports what happened, the coach adds the date and the result, in the reader's exact words, to the entry of that experiment. If more than one entry has no result and the reader does not say which, the coach asks. | `test_ac2_2`, W5 |
| AC-2.3 | MUST NOT | The coach does not change the recorded wording of a prediction or a result. When the reader corrects one, the coach adds a dated correction line to the entry and keeps the original. The page shows both. | `test_ac2_3`, W6 |
| AC-2.4 | MUST NOT | The coach does not record confirmed reading from the page, from the selected entry point, or from a handoff block. Confirmed reading enters the profile only when the reader states what they read. | `test_ac2_4`, W4 |
| AC-2.5 | MUST | In a new session, with `experiment.html` deleted, the coach rebuilds the same comparison from `PROFILE.md` alone. | `test_ac2_5`, W7 |
| AC-2.6 | MUST | When the reader reports a result and the profile has no prediction for it, the coach records the result alone. The coach does not write a prediction for the reader. | `test_ac2_6`, W8 |
| AC-2.7 | MUST | After the reader reports a result, the coach's next question in the conversation quotes the prediction and the result and asks what the reader wants to try next. This happens with or without the page. | `test_ac2_7`, W5 |

### Goal 3: distribution

| ID | Keyword | Criterion | Verification | Status |
|---|---|---|---|---|
| AC-3.1 | MUST | `assets/coaching.md` states that the page is optional and that routine coaching needs only the local Markdown files and their linked images. | `test_ac3_1` | |
| AC-3.2 | MUST | The check paragraph in `SKILL.md` adds the page loop to the walk-through that the builder runs against scratch state before delivery. | `test_ac3_2` | |
| AC-3.3 | MUST | Both plugin manifests have version 0.2.0. `CHANGELOG.md`, `README.md`, and `README.ko.md` describe the page. The trigger descriptions do not change. | `test_ac3_3`, `python3 -m unittest discover -s scripts/tests` | |
| AC-3.4 | MUST | `scripts/make_coach.py` is unchanged, and a coach published by it contains the page instructions. | `test_ac3_4` | Retired (2026-11-24): D8 changes the publisher. AC-3.6 replaces it. |
| AC-3.5 | SHOULD | `SKILL.md` tells the operator how to give an existing coach the new instructions: replace the text after the source marker in that coach's `SKILL.md` with the current `assets/coaching.md`, and keep the front matter, title, marker, `references/`, and `PROFILE.md`. | `test_ac3_5`, W9 | Retired (2026-11-24): D8 replaces the manual step. AC-3.7 to AC-3.10 replace it. |
| AC-3.6 | MUST | A coach that `scripts/make_coach.py` publishes contains the page instructions from `assets/coaching.md`. | `test_ac3_6` | |
| AC-3.7 | MUST | With `--update-coaching`, when the destination is an existing coach for the same source, the script replaces the text after the source marker in that coach's `SKILL.md` with the current `assets/coaching.md`. The front matter, the title, the marker, `references/`, `PROFILE.md`, and every other file stay byte-identical. | `test_ac3_7`, W9 | |
| AC-3.8 | MUST | Before it replaces the text, the script saves the earlier `SKILL.md` as `SKILL.md.previous` in the coach directory. When the text is already current, the script writes nothing and says so. | `test_ac3_8` | |
| AC-3.9 | MUST | Without `--update-coaching`, the script writes nothing to an existing coach. With it, the script exits with an error and writes nothing when the destination does not exist or belongs to another source. | `test_ac3_9` | |
| AC-3.10 | MUST | `SKILL.md` gives the operator the update command for an existing coach. | `test_ac3_10` | |

## Walkthrough

Run the walkthrough in a scratch directory under `/Volumes/eyedisk/tmp`, with a coach published from a synthetic book. Run it once in Claude Code and once in Codex. Each step passes or fails on the stated observation.

| Step | Action | Pass when |
|---|---|---|
| W1 | Start a session. Give an experiment in a message. Do not ask for the page. | No `experiment.html` exists. `PROFILE.md` has entry `E1`. |
| W2 | Ask for the page. | The file is in the coach directory. `grep -Ei 'https?://|localStorage|sessionStorage|indexedDB|document\.cookie|<img|\.md' experiment.html` prints no match other than fixed instruction text. The page shows two or three locators and three fields. |
| W3 | Open the file with the network off. Type in the three fields. Select and copy the handoff block. Reload. | The block holds the locator and the three texts. After the reload the fields are empty, and the notice was visible before the reload. |
| W4 | Paste the block into the conversation. | `PROFILE.md` gains entry `E2` with the pasted wording. The confirmed-reading log is byte-identical to its state before the paste. |
| W5 | In the same session, report a result for `E2`. Ask for the page. | The reply quotes the prediction and the result. The entry has the result and its date. The page shows both as text, and a prediction that contains `<b>` shows the characters `<b>`. |
| W6 | Correct the prediction of `E2`. Ask for the page. | The entry has the original wording and a dated correction line. The page shows both. |
| W7 | Delete `experiment.html`. Start a new session. Ask for the page. | The page shows the same comparison as W6. |
| W8 | Report a result that matches no entry. | The profile has the result with no prediction. No prediction text was added. |
| W9 | Publish a second scratch coach with the 0.1.0 instructions and give it a profile. Run the script with `--update-coaching`. Repeat W1. | `PROFILE.md` and `references/` are byte-identical before and after the update. `SKILL.md.previous` holds the earlier text. W1 passes. |

## Out of scope

- A five-problem worksheet page.
- A whole-book reading map.
- A local server.
- A hosted page, for example Claude Artifacts.
- An update of existing coaches that runs without an operator command.

## Decision after the pilot

The release unit in the plan starts only after one reader uses the loop with a real book. Continue if the reader returns to the page and uses the comparison to choose the next action. If the page mainly adds copying and reloading, keep the comparison in the conversation and do not release the page. The user owns this decision.
