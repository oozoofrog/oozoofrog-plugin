# project-wiki evals

Purpose: measure whether the `project-wiki` skill fires on the requests it claims, stays out of the ones it disclaims, and runs the lint script for "위키 검사".

Format: `claude plugin eval` (https://code.claude.com/docs/en/plugin-evals.md). One directory per case: `prompt.md`, `graders/*.md`, `case.yaml` and `scaffold.sh`. `_fixtures/wiki-repo.sh` builds a tiny local git repository (`pager.py`, `README.md`, `.gitignore` with `_context/`; no remote, no network). `--with-vault` creates the vault with the skill's own `wiki_init.py` and adds one episode and one lesson. `--broken-link` makes the episode link to a note that does not exist.

## Cases

| Layer | Cases | Graders |
|---|---|---|
| Routing, should fire | `route-init-ko`, `route-capture-ko`, `route-lesson-ko`, `route-retro-ko`, `route-instruction-ko`, `route-capture-en` | `tool_used: Skill` matching `project-wiki` |
| Routing, must not fire | `route-neg-handoff-ko`, `route-neg-api-docs-ko`, `route-neg-question-ko` (in a project with a vault) | `tool_used: Skill`, `min: 0`, `max: 0`, `arm: both` |
| Behavior | `behavior-lint-ko` ("위키 검사해줘" with one broken link) | `project-wiki-fired`, `lint-ran` (a `Bash` call with `wiki_lint.py`), `reports-broken-link` (`regex` on the last message: `없는 교훈`) |

Routing cases stop at `max_turns: 4`; "Reached maximum number of turns" in a routing run is expected and does not fail it.

Each run loads only this plugin. The negative cases test the skill's own "Not for …" clause, not a competition with `handoff` or `fstack`.

## Results

2026-11-26, `project-wiki` 0.1.0, `--ablation none`, 3 runs per case: 30 of 30 runs passed, $4.37 list price, 127 s with `-j 4`.

## Run

Run from `plugins/project-wiki`. Keep results outside the package tree.

```sh
OUT="${TMPDIR:-/tmp}/project-wiki-evals/$(date +%Y%m%dT%H%M%S)"
mkdir -p "$(dirname "$OUT")"
claude plugin eval . --scaffold --allow-tools Bash --trust-plugin --ablation none -j 4 --threshold 0 \
  --max-cost-usd 15 --no-publish --output-dir "$OUT" --json "$OUT.json"
```

`--scaffold` runs the case scaffold scripts. Without it, the cases run in an empty workspace.
