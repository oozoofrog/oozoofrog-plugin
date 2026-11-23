---
description: 'Bug fix with an explicit drive grant.'
tags: [routing]
runs: 3
max_turns: 4
timeout_seconds: 180
allowed_tools: [Read, Glob, Grep, Skill]
expected_outcome: 'fstack skill is invoked.'
---

이 버그 재현하고 끝까지 고쳐: 마지막 페이지가 비어 나와. `paginate(list(range(10)), 4, 3)`이 `[9]`가 아니라 `[]`야.
