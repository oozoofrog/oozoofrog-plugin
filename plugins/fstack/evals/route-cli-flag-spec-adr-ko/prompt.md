---
description: 'New CLI flag; asks for spec and ADR before implementation (T2 contract).'
tags: [routing]
runs: 3
max_turns: 4
timeout_seconds: 180
allowed_tools: [Read, Glob, Grep, Skill]
expected_outcome: 'fstack skill is invoked.'
---

pager CLI에 페이지 범위를 벗어나면 종료 코드 2로 실패하는 `--strict` 플래그를 새로 추가하려고 해. 구현 전에 spec이랑 ADR부터 써줘.
