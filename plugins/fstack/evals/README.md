# fstack evals

Purpose: measure whether the `fstack` skill fires on the requests it claims (and stays out of the ones it disclaims), and whether, once it fires, it follows its own dials, gates and report contract.

Format: `claude plugin eval` (https://code.claude.com/docs/en/plugin-evals.md). One directory per case: `prompt.md` (frontmatter: run limits, tools, tags, `runs: 3`), `graders/*.md`, and for fixture cases `case.yaml` + `scaffold.sh`. `_fixtures/pager-repo.sh` builds a tiny local git repo (Python `pager.py` with one real off-by-one bug, `report.py`, a passing `tests/test_pages.py`, a README typo; no remote, no network). Options: `--with-plan` adds `docs/plan` and pending decisions; `--with-diff` leaves one uncommitted change.

## Layers

| Layer | Cases | Tag | Graders |
|---|---|---|---|
| 1 Routing, should fire | `route-fix-explicit-name-ko`, `route-cli-flag-spec-adr-ko`, `route-fix-drive-grant-ko`, `route-remaining-work-ko`, `route-dry-run-spec-adr-en` | `routing` | `tool_used: Skill` matching `fstack` (the skill is invoked as `fstack:fstack`) |
| 1 Routing, must not fire | `route-neg-quick-question-ko`, `route-neg-readme-typo-ko`, `route-neg-refactor-ko`, `route-neg-handoff-ko`, `route-neg-model-choice-ko`, `route-neg-fact-question-ko` | `routing` | `tool_used: Skill`, `min: 0`, `max: 0`, `arm: both` |
| 1 Observe only | `observe-evidence-first-overlap-ko`, `observe-review-diff-en` | `observe` | `fstack-fired` indicator (`arm: with-only`); the skill load is not part of the pass rule. `observe-review-diff-en` also carries the outcome graders `reports-findings` (`llm`), `no-commit`, `no-python-written`, `no-python-edited`, which are scored |
| 1+2 Under-specified | `under-fix-ko`, `under-review-ko`, `under-kickoff-ko`, `under-prototype-ko` | `under` | `fstack-fired` plus outcome graders: `bug-fixed`; `reports-findings` (`llm`); `asks-user` (`llm`) and `pager-unchanged`; `ran-experiment`, `reports-measurement` (`llm`), `source-not-edited` and `source-not-written`; `no-commit` and, where no code may change, `no-python-written` / `no-python-edited` |
| 2 Behavior | `behavior-fix-step-pace-ko`, `behavior-fix-drive-grant-ko`, `behavior-design-docs-t2-ko`, `behavior-fix-wiki-journal-ko` | `behavior` | deterministic `regex` / `tool_used` / `tool_order` / `file_exists`; one `llm` grader in each fix case; `lens-agents` in the design-docs case |

Behavior prompts name fstack explicitly so routing noise does not mask behavior.

Under-specified prompts are terse requests that name neither fstack nor a workflow ("1페이지가 이상하게 나와요. 봐주세요.", "변경분 좀 봐주세요.", "pager를 다른 도구랑 연동되게 해주세요.", "report.py 통째로 읽는 거랑 한 줄씩 중에 뭐가 나아요?"). They measure routing and behavior together, with write tools allowed, because that is how the 0.1.1 trigger text failed: the skill did not load in 5 of 8 such requests. In these cases a red `fstack-fired` is the finding, not noise. `under-kickoff-ko` passes only when the reply asks the user at least two questions and no `.py` file changes. With the first 0.1.2 kickoff text ("Pick the most likely one and say why") the replies asked, but folded purpose, target and format into one "which candidate" question; `asks-user` failed in 1 of 2 Claude Code runs and 2 of 2 Codex runs. The grader was kept. Kickoff now recommends a candidate without deciding, asks the purpose first and each remaining build-changing choice as its own numbered question, and ends the report with the questions when no answer is in the turn. With that text `asks-user` passed in 3 of 3 Claude Code runs (judge votes 9 of 9) and 2 of 2 Codex runs (Inferred; three questions each).

`observe-review-diff-en` ("Review this diff (the uncommitted change in this repo).") is observe-only for the skill load. Until 0.1.2 the prompt was the negative case `route-neg-generic-review-en`. With the read-only tool set `[Read, Glob, Grep, Skill]` no tool could show the diff: the model called the built-in `code-review` skill, which reported "I couldn't run `git diff` (no shell tool here)" and reviewed the whole file. The case therefore runs with shell tools. With them, on 2026-11-24 and the final 0.1.2 text, fstack loaded in 3 of 6 runs; a kept trace of a run without fstack shows a call to the built-in `code-review` skill. The outcome graders passed in 6 of 6 runs: every run reported findings, changed no file and made no commit. An earlier batch on the same day loaded fstack in 4 of 4 runs, so the rate varies by batch. For a generic English diff-review request either skill is an acceptable handler, so the skill load is recorded and not scored. A request that names fstack, or asks for a review against the spec or the recorded decisions, selects fstack. The Korean request `under-review-ko` loaded fstack in 3 of 3 runs and stays scored.

`under-prototype-ko` is a standalone "which of two approaches is better" question. With the first 0.1.2 wording ("choose between two approaches (measure with a throwaway prototype)" and "Not for quick factual questions about the code") it loaded the skill in 0 of 4 runs; the model read `report.py` and answered from the code, with no skill call. The trigger text now names the question form ("a 'which of two approaches is better?' question (answer it by measuring a throwaway prototype, not from opinion)", "'A랑 B 중 뭐가 나아요?' 같은 방식 선택 질문(실행해 측정)") and narrows the exclusion to "factual questions about what existing code does or returns". With that text the skill loaded in 4 of 4 runs, each run measured the variants in a temporary directory and left `report.py` unchanged, and `route-neg-fact-question-ko` stayed out in 3 of 3 runs. `source-not-edited` and `source-not-written` match `Edit` and `Write` calls on `report.py` or `pager.py` in the run workspace; throwaway files elsewhere are allowed. `ran-experiment` requires one `Bash` call that runs Python.

`no-commit` (`behavior-fix-drive-grant-ko` and the under-specified cases) allows no `git commit` call in Bash. The drive prompt grants autonomy and no commit, so a commit there breaks the rule that a drive grant alone does not permit one. The grader reads Bash commands only; it does not inspect the fixture's history.

Frame graders (`pace-step`, `pace-drive`, `spec-tier-t2`) are one `regex` over `trace`. `tool_order` compares tool calls only, so it cannot place a message. The pattern requires, in this order:

1. The `Skill` call for `fstack`.
2. Then, before any file-changing line, an assistant `text` block with `Pace: <step|drive>` and `Spec: <T0|T1|T2>` on one line of that text.

A file-changing line is an `Edit`, `MultiEdit`, `Write` or `NotebookEdit` call, or a `Bash` command that matches a write heuristic: `sed -i`, `tee`, a `>`/`>>` redirect other than `2>&1`, `rm`/`mv`/`cp`/`touch`/`mkdir`/`patch`, a state-changing `git` subcommand, `write_text`, or `open(..., "w"|"a")`.

Limitations:
- The heuristic can miss other writes, for example a Python script that writes through a helper.
- It counts `> /dev/null` or a `>` comparison inside `python3 -c` as a write. A frame that comes after such a call fails.
- Tool results and the injected skill text never match, because the pattern requires an assistant `text` block.

`lens-agents` (`behavior-design-docs-t2-ko`, `arm: with-only`) requires at least two `Agent` calls: one agent for each lens. It counts calls and does not read the briefs. The fix cases do not allow the `Agent` tool, so a lens there can only be a single-agent fallback that the report discloses.

`pace-not-drive` rejects a `Pace: drive` frame in any assistant text. `next-step-line` accepts only `Next step: <candidate>` or `다음 단계: <후보>` as the last non-empty line of the final message.

## Isolation limits

- Each run loads only this plugin. Your other installed plugins, user `CLAUDE.md`, hooks and MCP servers are not loaded. A case cannot load sibling plugins (`plugins:` outside `plugins/fstack` is rejected by the containment check). Negative cases therefore test fstack's own "Not for …" clause, not a competition with `refactor`, `handoff` or `model-advisor`.
- Runs use your own credentials and plan usage. `--max-cost-usd` caps the list-price estimate, not plan usage.
- Bash runs inside the OS sandbox. The fixture has no remote, so a `git push` attempt fails; the `no-push` grader still records the attempt.

## Run commands

Run from `plugins/fstack`. Put the target `.` before list options. Keep results outside the package tree: results inside `plugins/fstack` break `scripts/tests/test_fstack_distribution.py`.

```sh
OUT="${TMPDIR:-/tmp}/fstack-evals/$(date +%Y%m%dT%H%M%S)"
mkdir -p "$(dirname "$OUT")"

# Routing only (11 cases x 3 runs x 2 arms = 66 runs)
claude plugin eval . --tag routing --scaffold --trust-plugin -j 4 --threshold 0.66 \
  --max-cost-usd 20 --no-publish --output-dir "$OUT" --json "$OUT.json"

# One routing case by glob
claude plugin eval . --case 'route-neg-*' --scaffold --trust-plugin -j 4 --max-cost-usd 10 --no-publish --output-dir "$OUT"

# Behavior (3 cases x 3 runs x 2 arms = 18 runs)
claude plugin eval . --tag behavior --scaffold --allow-tools Bash Edit Write Agent --trust-plugin -j 3 \
  --max-cost-usd 60 --no-publish --output-dir "$OUT" --json "$OUT.json"

# Under-specified requests (4 cases x 3 runs x 2 arms = 24 runs)
claude plugin eval . --tag under --scaffold --allow-tools Bash Edit Write --trust-plugin -j 3 \
  --max-cost-usd 30 --no-publish --output-dir "$OUT" --json "$OUT.json"

# All, including the observe cases (20 cases x 3 runs x 2 arms = 120 runs)
claude plugin eval . --scaffold --allow-tools Bash Edit Write Agent --trust-plugin -j 4 \
  --max-cost-usd 80 --no-publish --output-dir "$OUT" --json "$OUT.json"

# Parse-only check: loads every case, starts no run (exits 2, partial)
claude plugin eval . --scaffold --allow-tools Bash Edit Write Agent --trust-plugin --max-cost-usd 0 --no-publish --output-dir "$OUT"
```

- `--scaffold` runs the case scaffold scripts. Without it, fixture cases run in an empty workspace.
- `--allow-tools Bash Edit Write Agent` is needed only by behavior and under-specified cases and by `observe-review-diff-en`, which needs `Bash` to read the diff. `Agent` is used only by `behavior-design-docs-t2-ko`, where it starts the lens agents. Routing cases use the read-only set `[Read, Glob, Grep, Skill]`.
- `--trust-plugin` is only for this local plugin.
- `runs: 3` is set per case; `--runs 1 --ablation none` gives one cheap iteration run.
- Do not use `--keep-temp` casually: on macOS, kept run directories go to `/tmp` (not `$TMPDIR`) with sealed subdirectories.
- `_fixtures/pager-repo.sh` refuses (exit 65) unless the current directory is empty and outside any git work tree. The only allowed work tree is the empty sentinel repository that `claude plugin eval` places at `<run>/home/.git` around the scaffold directory `<run>/home/cwd`. All of its git calls disable hooks, fsmonitor and signing.

## Reading results

- `WITH`, `W/OUT`, `Δ`: score with fstack, without any plugin, and the difference. Positive routing cases have only the Skill grader, so it is scored and `Δ` shows what the trigger adds. Negative cases score in both arms (`arm: both`); `W/OUT` is always 1.0, so `Δ` is 0 when fstack stays out and negative when it fires.
- Skill-fired indicator: in two-arm runs, the `fstack-fired` grader in behavior cases carries `withOnly: true`, `scored: false` in JSON and a `plugin-fired indicator` badge in the report. A behavior run with the indicator red did not run fstack; read its other graders as invalid. A case whose only graders are Skill graders (positive routing, observe) scores them normally.
- JSON: `cases[].arms.with[].score`, `.graders[].passed`, `.graders[].explanation`, `.tracePath`.

## Pass rule

A case passes when at least 2 of its 3 with-arm runs score 1.0. For routing cases a run scores 0 or 1, so `--threshold 0.66` gives the same verdict in the exit code. For behavior cases count runs:

```sh
jq -r '.cases[] | "\(.name)\t\([.arms.with[] | select(.score == 1)] | length)/\(.arms.with | length)"' "$OUT.json"
```

The observe cases have no pass rule for the skill load. Record how many of their runs fired fstack. For `observe-review-diff-en`, also check that the outcome graders pass.

### Result snapshot (2026-11-24, Claude Code 2.1.328, fstack 0.1.2 working tree, new cases)

With-arm only (`--ablation none`, so `fstack-fired` is scored), 3 runs per case, flags as in the run commands above. The English diff review ran under its earlier name `under-review-en`, with `fstack-fired` scored.

| Case | Runs at 1.0 | Verdict | Failed graders |
|---|---|---|---|
| `under-fix-ko` | 3/3 | pass | none |
| `under-review-ko` | 3/3 | pass | none |
| `under-kickoff-ko` | 3/3 | pass | none |
| `under-prototype-ko` | 3/3 | pass | none |
| `route-neg-fact-question-ko` | 3/3 | pass | none |
| `observe-review-diff-en` (then `under-review-en`) | 1/3, then 2/3 in a second batch | observe-only after these runs | `fstack-fired` in 3 of 6 runs; outcome graders passed in 6 of 6 |

The second batch was not taken as a pass. The case was moved to the observe layer for the reason given under Layers. After the move the case was not run again.

## Codex

`claude plugin eval` covers Claude Code only. Codex routing and behavior are checked separately with the same `prompt.md` files and scaffolds. Whoever runs that check documents its runner and results.

### Method used on 2026-11-23

- CLI: `codex-cli 0.171.0`, `codex -a never exec --ephemeral --json`, one fixed model at `model_reasoning_effort="high"`, `web_search="disabled"`. Final message via `-o final.md`; prompt on stdin.
- Isolation:
  - Point `CODEX_HOME` at an isolated home that you prepared. The "with" home installs the plugin from the local marketplace: `codex plugin marketplace add <repo root>`, then `codex plugin add fstack@oozoofrog-plugin`. The baseline home has no plugin.
  - Set `[features] apps = false` in that home's `config.toml`.
  - Set `HOME` to an empty directory and pass `--enable skip_host_skill_discovery`. In pilot runs, personal skills leaked in through the real `HOME`.
  - Set `shell_environment_policy.inherit="none"` with an explicit environment (`GIT_CONFIG_GLOBAL=/dev/null`, `GIT_CONFIG_NOSYSTEM=1`, `HOME=<workspace>`).
- Sandbox:
  - Routing cases use `-s read-only`.
  - Behavior cases use `-s workspace-write` with `network_access=false`, `exclude_tmpdir_env_var=true` and `exclude_slash_tmp=true`.
  - An exec-policy rules file in `CODEX_HOME/rules/` forbids `git push` and `git remote add|set-url|rename`.
- Scaffolds: each run gets a new empty workspace outside any git work tree, and `bash <case>/scaffold.sh` runs there before Codex starts.
- Runs: 3 per case with the plugin, plus 1 baseline run per behavior case.
- Lens agents: drop `--ephemeral` for a case that must start agents (`behavior-design-docs-t2-ko`). An ephemeral session has no stored rollout, and every agent start then fails with `collab spawn failed: ... no rollout found for thread id <id>` on stderr; the run falls back to a single-agent review. Without the flag, sessions are stored under `<CODEX_HOME>/sessions/`. `--json` prints no event for an agent start. Count the stored rollout files whose first line has `source.subagent.thread_spawn` (one per started agent), or the `spawn_agent` calls in the parent rollout.

Event mapping (Codex has no `Skill` or `Edit` tool names):

| Grader concept | Codex `--json` event |
|---|---|
| Skill fired | an `item.completed` `command_execution` with `exit_code` 0 that read the installed `<CODEX_HOME>/plugins/cache/oozoofrog-plugin/fstack/<version>/skills/fstack/SKILL.md` (its output contains `name: fstack`) |
| Edit / Write | `file_change` items, plus shell writes found by the same heuristic as above |
| Bash call | `command_execution` items (`command`, `exit_code`, `aggregated_output`) |
| Assistant text | `agent_message` items; the final message is `final.md` |
| `llm` graders | judged outside the runner and labeled Inferred |

The runner and grader are not vendored here. They hard-code machine paths, the model, the case count and a copy of every grader name. They would drift from `graders/*.md` with each grader change, for example the frame and next-step graders above. The two `llm` graders were judged outside the runner, so the grader is not self-contained. Porting them needs a separate reviewed change.

### Result snapshot (2026-11-23, Codex, fstack 0.1.1, before the frame and next-step grader changes)

This snapshot predates 0.1.2. It does not cover the under-specified cases, `route-neg-fact-question-ko` or the `no-commit` grader. The English diff review was then the negative case `route-neg-generic-review-en`.


- Scored cases: 13 of 14 passed. Scored runs: 39 of 42.
- All 11 routing cases passed in 3 of 3 runs.
- The observe case fired fstack in 3 of 3 runs.
- `behavior-fix-step-pace-ko` failed `next-step-line` in all 3 runs. The final report ended with prose such as "다음 단계 후보는 … 커밋하는 것입니다." instead of a `다음 단계:` line.
- No run attempted `git push` or `git remote add`, and no run changed git history.
- Of the 9 behavior runs with the plugin, the literal frame line was in the first assistant message in 0 runs. It was in the first assistant message after the skill loaded in 8 runs; `behavior-design-docs-t2-ko` run 2 was the exception.

### Result snapshot (2026-11-24, Codex, fstack 0.1.2 working tree)

Method as above, with these differences: one fixed model at `high` (this file names no model ID); 1 run per case unless stated; no baseline home; behavior and under-specified cases only, no routing cases. The plugin was installed from the working tree into a new isolated home, and the installed `SKILL.md` carried the 0.1.2 trigger text. `llm` graders were judged by reading `final.md` and are labeled Inferred.

| Case | Runs | Skill loaded | Frame line after the skill, before any write | Outcome checks |
|---|---|---|---|---|
| `behavior-fix-step-pace-ko` | 1 | 1/1 | 1/1 (`step`, `T1`) | fixed, tests run, no commit, no push; last line `다음 단계: 없음` |
| `behavior-fix-drive-grant-ko`, prompt before the rewording | 3 | 3/3 | 3/3 (`drive`) | fixed 1/3; no commit 3/3; no push 3/3 |
| `behavior-fix-drive-grant-ko`, reworded prompt | 2 | 2/2 | 2/2 (`drive`, `T1`) | fixed 2/2; tests run 2/2; no commit 2/2; no push 2/2 |
| `behavior-design-docs-t2-ko` | 1 | 1/1 | 1/1 (`step`, `T2`) | three documents written, no `.py` change, `trace.py` run; `lens-agents` failed: no agent call, and the report says the review agents could not be started |
| `under-fix-ko` | 1 | 1/1 | 1/1 | fixed, no commit, no push |
| `under-review-ko` | 1 | 1/1 | 1/1 | findings reported (Inferred), no file change, no commit |
| `under-review-en` (now `observe-review-diff-en`) | 1 | 1/1 | 1/1 | findings reported (Inferred), no file change, no commit |
| `under-kickoff-ko` | 2 | 2/2 | 2/2 | no file change 2/2, no commit 2/2; `asks-user` failed 2/2 (Inferred): each reply asked one question, which integration target, where the grader requires two |
| `under-prototype-ko` | 1 | 1/1 | 1/1 | Python benchmark run, measured time and memory in the answer (Inferred), `report.py` unchanged, no commit |

- The skill loaded in 13 of 13 runs. The frame line was never in the first assistant message, because Codex sends a preamble before it reads `SKILL.md`; it was always after the skill load and before the first write.
- No run called `git commit` or `git push`, and `HEAD` was unchanged in every workspace.
- Drive prompt: the earlier sentence ended in "`[3, 4, 5]`를 돌려줘", which also reads as "return `[3, 4, 5]`". In 2 of 3 runs Codex took that reading, found that the code already returned `[3, 4, 5]` and changed nothing. The prompt now ends in "돌려주고 있어", which states the symptom only. With it Codex fixed the bug in 2 of 2 runs, and one Claude Code run scored 1.0.
- Resolved after this table (same day, same method):
  - `under-kickoff-ko`: with the kickoff text that asks each choice as its own question, 2 of 2 runs asked three questions (purpose, target tool, output format), changed no file and made no commit.
  - `behavior-design-docs-t2-ko`: the table row came from an `--ephemeral` run. Its stderr shows two agent start attempts that failed with `collab spawn failed: ... no rollout found for thread id`, and the report disclosed the fallback. The cause was the runner flag, not the skill text. One run without `--ephemeral`, with the skill text unchanged, started two agents (`macro`, `micro`; two stored child rollouts), wrote the three documents and changed no `.py` file.

`behavior-fix-wiki-journal-ko` (2026-11-26) runs the pager fixture with `--with-wiki`: a git-ignored vault with one candidate lesson. Before Frame checked for `_context/wiki/.wiki/config.json`, 1 of 2 runs wrote no episode; the vault does not show in `git status`. After the check, 3 of 3 runs wrote an episode with both retrospectives, added a 적용 기록 row and kept the lesson's status. One earlier run wrote `outcome: done`; the episode template now lists the allowed values in comments, and `episode-outcome-enum` checks them. `behavior-fix-step-pace-ko` passed 2 of 2 runs, including `no-wiki-without-vault`.
