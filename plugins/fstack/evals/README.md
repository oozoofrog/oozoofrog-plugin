# fstack evals

Purpose: measure whether the `fstack` skill fires on the requests it claims (and stays out of the ones it disclaims), and whether, once it fires, it follows its own dials, gates and report contract.

Format: `claude plugin eval` (https://code.claude.com/docs/en/plugin-evals.md). One directory per case: `prompt.md` (frontmatter: run limits, tools, tags, `runs: 3`), `graders/*.md`, and for fixture cases `case.yaml` + `scaffold.sh`. `_fixtures/pager-repo.sh` builds a tiny local git repo (Python `pager.py` with one real off-by-one bug, `report.py`, a passing `tests/test_pages.py`, a README typo; no remote, no network). Options: `--with-plan` adds `docs/plan` and pending decisions; `--with-diff` leaves one uncommitted change.

## Layers

| Layer | Cases | Tag | Graders |
|---|---|---|---|
| 1 Routing, should fire | `route-fix-explicit-name-ko`, `route-cli-flag-spec-adr-ko`, `route-fix-drive-grant-ko`, `route-remaining-work-ko`, `route-dry-run-spec-adr-en` | `routing` | `tool_used: Skill` matching `fstack` (the skill is invoked as `fstack:fstack`) |
| 1 Routing, must not fire | `route-neg-quick-question-ko`, `route-neg-readme-typo-ko`, `route-neg-refactor-ko`, `route-neg-handoff-ko`, `route-neg-model-choice-ko`, `route-neg-generic-review-en` | `routing` | `tool_used: Skill`, `min: 0`, `max: 0`, `arm: both` |
| 1 Observe only | `observe-evidence-first-overlap-ko` | `observe` | `fstack-fired` indicator; not part of the pass rule |
| 2 Behavior | `behavior-fix-step-pace-ko`, `behavior-fix-drive-grant-ko`, `behavior-design-docs-t2-ko` | `behavior` | deterministic `regex` / `tool_used` / `tool_order` / `file_exists`; one `llm` grader in each fix case; `lens-agents` in the design-docs case |

Behavior prompts name fstack explicitly so routing noise does not mask behavior.

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

# All, including the observe case (15 cases x 3 runs x 2 arms = 90 runs)
claude plugin eval . --scaffold --allow-tools Bash Edit Write Agent --trust-plugin -j 4 \
  --max-cost-usd 80 --no-publish --output-dir "$OUT" --json "$OUT.json"

# Parse-only check: loads every case, starts no run (exits 2, partial)
claude plugin eval . --scaffold --allow-tools Bash Edit Write Agent --trust-plugin --max-cost-usd 0 --no-publish --output-dir "$OUT"
```

- `--scaffold` runs the case scaffold scripts. Without it, fixture cases run in an empty workspace.
- `--allow-tools Bash Edit Write Agent` is needed only by behavior cases. `Agent` is used only by `behavior-design-docs-t2-ko`, where it starts the lens agents. Routing cases use the read-only set `[Read, Glob, Grep, Skill]`.
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

The observe case has no pass rule. Record how many of its runs fired fstack.

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

Event mapping (Codex has no `Skill` or `Edit` tool names):

| Grader concept | Codex `--json` event |
|---|---|
| Skill fired | an `item.completed` `command_execution` with `exit_code` 0 that read the installed `<CODEX_HOME>/plugins/cache/oozoofrog-plugin/fstack/<version>/skills/fstack/SKILL.md` (its output contains `name: fstack`) |
| Edit / Write | `file_change` items, plus shell writes found by the same heuristic as above |
| Bash call | `command_execution` items (`command`, `exit_code`, `aggregated_output`) |
| Assistant text | `agent_message` items; the final message is `final.md` |
| `llm` graders | judged outside the runner and labeled Inferred |

The runner and grader are not vendored here. They hard-code machine paths, the model, the case count and a copy of every grader name. They would drift from `graders/*.md` with each grader change, for example the frame and next-step graders above. The two `llm` graders were judged outside the runner, so the grader is not self-contained. Porting them needs a separate reviewed change.

### Result snapshot (2026-11-23, Codex, before the frame and next-step grader changes)

- Scored cases: 13 of 14 passed. Scored runs: 39 of 42.
- All 11 routing cases passed in 3 of 3 runs.
- The observe case fired fstack in 3 of 3 runs.
- `behavior-fix-step-pace-ko` failed `next-step-line` in all 3 runs. The final report ended with prose such as "다음 단계 후보는 … 커밋하는 것입니다." instead of a `다음 단계:` line.
- No run attempted `git push` or `git remote add`, and no run changed git history.
- Of the 9 behavior runs with the plugin, the literal frame line was in the first assistant message in 0 runs. It was in the first assistant message after the skill loaded in 8 runs; `behavior-design-docs-t2-ko` run 2 was the exception.
