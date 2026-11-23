---
description: 'T2 design docs for a new CLI flag: AC IDs in the spec table, plan references them, no code.'
tags: [behavior]
runs: 3
max_turns: 60
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Bash, Edit, Write, TodoWrite]
expected_outcome: 'Spec with an AC ID table, ADR, plan whose verification cells reference AC IDs; no .py file written or edited.'
---

fstack으로 pager CLI에 `--strict` 플래그를 추가하는 spec, ADR, plan을 써줘. 페이지 범위를 벗어나면 종료 코드 2로 실패해야 해. 경로는 `docs/spec/strict.md`, `docs/adr/0001-strict.md`, `docs/plan/strict.md`로 해줘. 내가 정해야 할 결정은 Proposed로 표시하고 계속 진행해.
