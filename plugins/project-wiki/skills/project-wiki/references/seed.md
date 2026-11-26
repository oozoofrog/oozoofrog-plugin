# Seed

Seed builds episodes, lessons and knowledge from records that already exist. The first run is large; later runs read only what is new.

## 1. Find the sources

Run in the project:

```bash
python3 -I -B "<skill-dir>/scripts/wiki_sources.py" status
```

| Source key | What | Watermark |
|---|---|---|
| `claude` | Claude Code transcripts in `~/.claude/projects/<encoded path>*`, including git worktrees, T3 worktrees (`-t3-worktrees-<name>-`) and `former_paths` | byte offset per file |
| `codex` | Codex sessions whose `cwd` is in the project. Sessions started by T3 Code are skipped; read their T3 threads instead. `--include-t3-codex` adds them | byte offset per file |
| `handoff` | `_context/sessions/*.md`, `_context/handoff/*.md` | size + mtime |
| `memory` | agent memory files `~/.claude/projects/<p>/memory/*.md`, one per file name: worktree and former-path folders hold copies, so the current project's copy wins, then the newest | size + mtime |
| `git` | commits since the last ingest | commit ID |
| `t3` | T3 thread history (read by the agent, see 3) | newest `updatedAt` |

`new_bytes` and `est_tokens_raw` are raw sizes, an upper bound. Raw transcripts are never read whole.

If `first_ingest` is true and the project was renamed, ask the owner for the former paths and put them in `former_paths` in `.wiki/config.json` before going on.

## 2. Owner prompts

```bash
python3 -I -B "<skill-dir>/scripts/wiki_sources.py" prompts > <scratch>/prompts.txt
```

One line per prompt: UTC time, source and session prefix, text. Tool output, system reminders, compaction summaries, delegated briefs and coordination messages are removed. Lines that remain from agents (a brief that starts with an unknown phrase) are judged by the readers.

## 3. T3 threads

When T3 tools are available, search the threads of this project (`t3_thread_search` or `t3_thread_list` by project) updated after the `t3` watermark. Read them with `t3_thread_read` and keep the items with `createdBy: "user"` as owner prompts, plus the final assistant message of each run as the outcome. Delegated child threads hold briefs and reports, which are evidence, not owner prompts.

## 4. Readers (parallel, read-only)

Use one reader per period or per source group so that each reads about 300 KB or less. Give each the same brief:

> Extract material for a project wiki. You only extract; you do not write the wiki. Read completely: <files>. Also read the owner's prompts for the same dates in <prompts.txt>.
> Write <extract-N.md> in English with these sections:
> 1. Episodes: one entry per owner request or work unit, in date order: date, session prefix, the request verbatim, what the agent did, outcome (success / partial / failure) with evidence (commit, path, owner reaction quoted), time or rework worth noting.
> 2. Failures and incidents: what went wrong, the root cause if stated, how it was found, the fix, whether it became a rule, memory or check.
> 3. Owner corrections and instruction lessons: quote the correction, the agent behavior that caused it, and the instruction or default that would have avoided it (mark it "Inferred").
> 4. Agent response patterns: what worked and what did not, with evidence. Include delegation versus main-session work, review, measurement before change, verification on the real surface.
> 5. Technical knowledge and gotchas: the concrete fact and its source.
> 6. Decisions: owner and agent decisions with rationale.
> Rules: a source path for every item; quote exactly; never invent dates, numbers, commits or reactions; mark inferences "Inferred"; record contradictions as both; keep failures and corrections even when shortening. Reply with a summary under 200 words and the output path. Edit no other file.

A knowledge reader reads project rules, specs, ADRs, plans and evidence reports and writes: product overview, architecture, decisions, performance numbers with method, methods that worked with commands, known issues, glossary.

## 5. Writers (one period at a time)

Writers for different periods MUST run one after another, oldest first. Parallel writers duplicate lessons. The knowledge writer MAY run in parallel with one period writer, because it writes only the knowledge folder.

Each writer reads `위키 사용법.md`, the templates, two existing episodes and two existing lessons, and lists the lessons folder before it writes. It reuses an existing lesson by adding an 적용 기록 row instead of writing a duplicate. It writes:

1. Episodes for the period, as in `references/capture.md`.
2. One `chronicle` note for the period: every owner request with local time, verbatim text and a link to the covering episode.
3. Lessons, one per note, with `status: candidate`, or `encoded` with `encoded_in` when the rule already exists. A writer MUST NOT set `adopted`; it lists lessons with `worked` ≥ 2 as adoption proposals in its reply. Put this rule and the 4-column 적용 기록 format (`| 날짜 | 작업 기록 | 효과 | 내용 |`, 효과 ∈ 있음 · 없음 · 모름 · 미적용) into every writer brief. Writers leave `applied`, `worked` and `missed` to `wiki_lint.py --fix-counts`.

Writing rules: the owner's language; code, commands, paths, identifiers, numbers and quotes kept exact; "추정" for inferences; no invented data; no personal data; titles without `/ \ : # ^ | [ ]`; links only to notes that exist or that the writer creates.

## 6. Finish

1. `wiki_lint.py --fix-counts <vault>`, then `wiki_lint.py <vault>`; fix what the writers broke.
2. `wiki_sources.py mark` and, if T3 threads were read, `wiki_sources.py mark --t3 <newest updatedAt>`.
3. Report to the owner: notes written per type, lint result, proposals for adoption, sources skipped.

## Cost (measured on one project, 2026-11-26)

- 10 days of work, 300 KB of session summaries, 157 owner prompts: three readers, then three writers.
- Each extract was 1,000–1,300 lines. A writer took about 10 minutes and about 250k tokens.
- `status` takes under 0.2 s; `prompts` reads only new transcript bytes.
