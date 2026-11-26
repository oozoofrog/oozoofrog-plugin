---
name: project-wiki
description: Keep a local Obsidian wiki per project so the owner and the agent both get better at working together. It records each finished request as an episode with an owner-side and an agent-side retrospective, turns repeated corrections into lessons that move from candidate to adopted to encoded, keeps project knowledge, and runs retros. It creates the vault in `_context/wiki`, seeds it from earlier Claude/Codex transcripts, T3 threads, handoff notes, agent memory and git history without reading the same source twice, and lints it. Use for "위키 만들어줘", "프로젝트 위키", "위키에 남겨줘", "이거 교훈으로 남겨줘", "교훈 정리", "위키 회고", "위키 검사", "지시를 어떻게 했어야 했나", lessons learned, an Obsidian project journal, or a retrospective of past agent work. Not for session handoff (use handoff), code or API documentation, or editing notes in an unrelated Obsidian vault.
---

# Project wiki

The vault is a folder of Markdown notes that Obsidian opens. It answers four questions for later work:
what succeeded or failed, how the owner could have instructed better, how the agent should respond, and what is true about the project.
It grows a little after every request instead of in big rewrites.

`<skill-dir>` below is the folder that holds this SKILL.md. Run the scripts with `python3 -I -B`. They need only the Python standard library.

## Where things live

| What | Path |
|---|---|
| Project vault | `<project>/_context/wiki/` (git-ignored; `_context/` is shared with handoff) |
| Vault settings | `<vault>/.wiki/config.json` (folders, language, `former_paths`), `manifest.json` (hashes of bundled files), `state.json` (watermarks), `pending.json` (written by `wiki_sources.py status`, consumed by `mark`) |
| Cross-project lessons | the global vault named in `~/.config/project-wiki/config.json` (`global_vault`) |
| Note schema | `references/schema.md`; machine form `scripts/schema_v1.json` |

Note types: `episode` (one request), `lesson` (one lesson), `knowledge` (one subject), `retro`, `chronicle` (seeded periods only), `home`, `guide`, `inbox`. Frontmatter keys and enum values are English. Note bodies, titles and folder names use the owner's language (bundled: Korean).

## Who decides what

- The agent writes facts without asking: episode notes, new candidate lessons, rows in a lesson's 적용 기록 table, and the `applied`, `worked` and `last_seen` counters.
- The owner decides status changes: candidate → adopted, adopted → encoded, any → retired, and promotion to the global vault. The agent proposes them in a retro or in fstack capture-lessons as Accept / Reject / Defer lists, then applies only what the owner accepts. When an approved encoding is applied, set `encoded_in`.
- A lesson that points to a rule that already exists (agent memory, `CLAUDE.md`, a test, a skill) is written as `encoded` from the start. Link to the rule; do not copy its text.
- No hook writes to the wiki. Records are made at the end of a request (see Capture).
- Never write personal data or secrets: e-mail addresses, locations, share-link tokens, keys. Write "개발자 메일" instead of an address.

## Commands the owner uses

| Owner says | Do |
|---|---|
| "위키 만들어줘" | Init, then offer Seed |
| "위키에 남겨줘", "기록해줘" | Capture the current request |
| "이거 교훈으로 남겨줘" | Write or update one lesson |
| "위키 회고" | Retro |
| "위키 검사" | Lint, report findings |
| "위키 채워줘", "지난 기록 가져와" | Seed (incremental after the first run) |

## Init

1. Run `python3 -I -B "<skill-dir>/scripts/wiki_init.py" --dry-run` in the project. Read `created`, `updated` and `kept`.
2. Run it again without `--dry-run`. It writes only bundled files that are missing or that it wrote before and nobody changed. It keeps every file the owner edited (`kept`) and never touches other notes.
   For each `kept` file, compare it with the bundled version in `<skill-dir>/assets/vault/<lang>/` and tell the owner about changes that matter, such as a new table column in a template. Lint also checks the 적용 기록 header in the lesson template.
3. If `git_ignored` is false, tell the owner the vault is not ignored by git and propose adding `_context/` to `.gitignore`. Do not edit `.gitignore` without that approval.
4. If the project was renamed or moved, ask the owner for its former paths and add them to `former_paths` in `.wiki/config.json`. Old transcripts are filed under the old path.
5. For the global vault (once per machine): `wiki_init.py --global <dir>`. It records the path in the user config.

## Capture (end of a request)

Read `references/capture.md` before the first capture in a session. In short:

1. Decide whether to write.
   - Write without asking when the request changed code, settled a decision, failed, or the owner corrected the agent.
   - Otherwise ask in one line at the end of the report: "위키에 남길까요?" Skip questions, one-line answers and trivial edits.
2. Write one episode note in the episodes folder: the request verbatim, the goal and exit condition, what was done, the outcome, `회고: 지시` (owner side) and `회고: 대응` (agent side), evidence paths. Use the conversation you already have; do not reread files for it.
3. Add or update a knowledge note when the work established a durable fact, and write unresolved observations as inbox lines (`references/capture.md`).
4. Link lessons: for each lesson that was applied, add a 적용 기록 row with `효과` = `있음` / `없음` / `모름`, or `미적용` when an existing lesson was not followed and that caused rework and run `wiki_lint.py --fix-counts`. For a new lesson, check the lessons folder for an existing one first.
5. Run `wiki_lint.py <vault>` and fix the errors you caused.

When fstack runs in a project with a vault, fstack's wrap-up writes this episode as its journal entry and fstack's reflect proposes the status changes. Follow `references/capture.md` for the field mapping.

## Seed (earlier records)

Read `references/seed.md`. The scripts find the sources; agents read and write.

1. `wiki_sources.py status` lists new material per source since the last ingest and writes `.wiki/pending.json`.
2. `wiki_sources.py prompts` prints the owner's own prompts from the new transcript parts, without tool output, delegated briefs or coordination messages.
3. Read T3 thread history with the T3 tools when available; keep messages the user created.
4. Extract with reader agents, then write with writer agents, as `references/seed.md` describes.
5. Lint. Then `wiki_sources.py mark` (and `--t3 <newest updatedAt>`) moves the watermark. Run `mark` only after the notes are written, so a failed seed is read again next time.

## Retro

Read `references/retro.md`. After status changes, `wiki_guides.py <vault>` rebuilds the guides' generated sections. Get the numbers with `wiki_lint.py --summary [--since YYYY-MM-DD] <vault>`; read note bodies only for the lessons you propose to change. Write the retro note, empty the inbox, and present Accept / Reject / Defer. Apply only what the owner accepts.

## Lint

`wiki_lint.py <vault>` checks: frontmatter schema and enums, titles with `/ \ : # ^ | [ ]`, notes split into subfolders by a `/`, broken links, links that match only an alias, embedded Bases views that do not exist, Bases YAML, counters against the 적용 기록 table, episode ↔ lesson backlinks, duplicate episodes (same `date` and `request`), evidence paths, `encoded_in` memory targets, and personal data. Exit 1 means errors. `--json` gives machine output. It writes nothing except with `--fix-counts`.

## Cost

- Capture: one episode and zero to two lesson edits from the current context. Target 2–4k output tokens. No file reads beyond the lesson notes you edit.
- Seed, first run: proportional to the history. Read prompts and summaries, not raw transcripts (`status` reports raw sizes only as an upper bound). Later runs read only what the watermark marks as new.
- Retro: frontmatter numbers by script; bodies only for proposed changes.
