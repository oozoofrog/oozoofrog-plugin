# Capture

Capture turns the request that just finished into an episode note and lesson updates. It runs at the end of a request, from what is already in the conversation.

## When

| Situation | Action |
|---|---|
| Code changed, a decision was settled, the work failed or partly failed, or the owner corrected the agent | Write without asking |
| The owner said "위키에 남겨줘" or similar | Write |
| Substantial investigation with no change | Ask in one line at the end of the report: "위키에 남길까요?" |
| A question, a one-line answer, a typo, coordination between sessions | Do not write |
| A delegated child thread | Do not write. Return findings; the main session writes |

The main session writes. Two writers in parallel duplicate lessons.

## Episode note

File: `<episodes folder>/YYYY-MM-DD <짧은 제목>.md`, from the template `90 템플릿/작업 기록 템플릿.md`. One note per request or work unit. Fold small follow-up requests into the same note's 요청 원문. If an episode for this request already exists (for example an `in-progress` note written mid-task), update that note and its `outcome`; do not write a second note under a new title. Lint warns when two episodes have the same `date` and `request`.

Fill every section:

1. **요청 원문**: the owner's words, verbatim, including follow-ups during the work. Verbatim has one exception: replace share or auth tokens (for example `?a=<token>`), e-mail addresses and other personal data with `…`.
2. **목표와 완료 기준**: a pass/fail sentence.
3. **한 일** and **결과**: numbers with their conditions (build, device, configuration), commits, test counts before → after.
4. **잘된 점**, **아쉬운 점**.
5. **회고: 지시** (owner side): how the request could have been phrased to finish faster or with less rework. Label guesses "추정". When the instruction was good, say what made it good; that is a lesson too.
6. **회고: 대응** (agent side): what the agent should have done differently and what worked.
7. **근거**: commit IDs, report paths, the owner's reactions quoted.

Set `outcome` to match 결과 and `mode` to `delegated` when T3 or Codex children did the main work.

## Lessons

1. For each lesson that the work applied, add one 적용 기록 row (`효과` = `있음` / `없음` / `모름`) and update `last_seen`. For a lesson that existed but was not followed, and the miss caused a failure or rework, add a row with `미적용`. Then run `wiki_lint.py --fix-counts <vault>`.
2. For a new lesson, list the lessons folder first and reuse a lesson that says the same thing. One lesson per note. Title it as an action sentence in the owner's language.
3. Add the lesson to the episode's `lessons` and the episode to the lesson's `episodes`. Lint warns when one side is missing.
4. Write a lesson for the owner side (`audience: user`) when the instruction itself mattered: a terse request that worked because of context, a policy change that was never stated as a lasting rule, a compact numbered decision.
5. Never change `status` here. Status changes go to a retro or to fstack reflect.
6. When the owner states a lasting rule or policy during the work, note it in the episode and add an inbox line "정책 변경: … → 회고에서 상충 교훈 확인". A decision can contradict an existing lesson, and the retro checks that.

## Knowledge and inbox

- If the work established a fact that later work needs (architecture, the behavior of an external site, a tool or a platform, a measured number), add or update one knowledge note in the knowledge folder, set `verified` to today, and list the evidence in `sources`. Link it from the episode.
- Write each observation that the request raised but did not resolve as one inbox line with a link to the episode: `- YYYY-MM-DD 에이전트: <observation> → [[<episode>]]`. The retro empties the inbox.
- Do not append to `chronicle` notes. Chronicles exist only for seeded periods; the episode dashboard covers new work.

## With fstack

When the project has a vault, it is the project journal for fstack's `references/records.md`.

| fstack journal field | Episode section |
|---|---|
| Request; Question (AI) with options | 요청 원문 (+ the question and the options) |
| Answer (user) | 요청 원문 follow-ups; owner decisions in 결과 |
| Work done, test counts | 한 일 |
| Verification table, defect-injection table | 결과 |
| Decisions (user, AI, rejected alternatives) | 결과 → a "결정" list |
| Rules not met, remaining work | 아쉬운 점 |
| Observations: learned, AI mistakes, user corrections | 회고: 대응 and 회고: 지시 |

fstack's wrap-up writes the episode before any commit. fstack's reflect reads the lessons as signals, applies the two-occurrence rule to `worked`, and lists the status changes as Accept / Reject / Defer.

## Check

Run `wiki_lint.py <vault>`. Fix the errors in notes you wrote. Report other errors without fixing notes that another writer may be editing.
