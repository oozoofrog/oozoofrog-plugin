# Note schema (v1)

`scripts/schema_v1.json` is the machine form; `wiki_lint.py` enforces it. A vault MAY override it with `<vault>/.wiki/schema.json`. Keys and enum values are English; everything else is in the owner's language.

## Note types

| `type` | Folder (ko) | Required | Other fields |
|---|---|---|---|
| `episode` | `10 작업 기록` | `date`, `request`, `outcome`, `mode` | `session`, `lessons` (wikilinks), `evidence` (paths), `tags`, free extras such as `build` |
| `lesson` | `20 교훈` | `audience`, `kind`, `status`, `basis`, `first_seen`, `last_seen`, `applied`, `worked` | `missed`, `encoded_in`, `episodes` (wikilinks), `aliases`, `projects` (global vault) |
| `knowledge` | `50 지식` | `area`, `verified` | `sources` (paths) |
| `retro` | `60 회고` | `date`, `period` | |
| `chronicle` | `10 작업 기록` | | A table of every owner request in a period, linking to episodes |
| `home`, `guide`, `inbox` | root, `30`, `40` | | |

## Enums

- episode `outcome`: `success` · `partial` · `failure` · `in-progress`
- episode `mode`: `main-session` · `delegated` · `mixed`
- lesson `audience`: `user` · `agent` · `both`
- lesson `kind`: `instruction` · `response` · `technical` · `process`
- lesson `status`: `candidate` · `adopted` · `encoded` · `retired`
- lesson `basis`: `success` · `failure` · `mixed`
- knowledge `area`: `product` · `architecture` · `sync` · `reader` · `performance` · `verification` · `release` · `decisions` · `issues` · `glossary`

Dates are `YYYY-MM-DD` in the owner's local time zone.

## Lesson application log

The last section of a lesson is `## 적용 기록` with this table:

```
| 날짜 | 작업 기록 | 효과 | 내용 |
|---|---|---|---|
| 2026-11-26 | [[2026-11-26 실기기 병목 4건 수정]] | 있음 | 결함 3건을 테스트가 잡음 |
```

- `효과` is one of:
  - `있음`: the lesson was applied and helped.
  - `없음`: the lesson was applied and did not help.
  - `모름`: the lesson was applied and the outcome is not known yet. Change it later.
  - `미적용`: the lesson was not followed, and that caused a failure or rework. This is a missed application, not a failed one.
- `applied` = rows except `미적용`. `worked` = rows with `있음`. `missed` = rows with `미적용`; the field is optional and appears when the first such row is added. `wiki_lint.py --fix-counts` sets all three.
- `missed` ≥ 2 is strong evidence that the lesson needs enforcement (`encoded`), not more prose. The retro lists those lessons under `missed_often`.
- A lesson becomes eligible for adoption at `worked` ≥ 2. Eligible is not adopted: the owner adopts.

## `encoded_in`

Name where the lesson now lives, comma-separated: `메모리: <memory file name>`, `CLAUDE.md`, `AGENTS.md`, `skill: <name>`, `test: <path>`, `script: <path>`. Lint checks that a `메모리:` target exists in the project's agent memory folder.

## Titles and links

- Titles MUST NOT contain `/ \ : # ^ | [ ]`. A `/` makes a folder.
- Link by title, never by alias. Write `[[Title|shown text]]`.
- Frontmatter links are quoted: `- "[[Title]]"`.
- Embed a dashboard view by its exact view name: `![[교훈.base#후보]]`. Renaming a view breaks the embed; lint reports it.
