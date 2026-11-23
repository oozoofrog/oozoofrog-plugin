---
description: 'Explicit fstack name with a bug report.'
tags: [routing]
runs: 3
max_turns: 4
timeout_seconds: 180
allowed_tools: [Read, Glob, Grep, Skill]
expected_outcome: 'fstack skill is invoked.'
---

fstack으로 이 버그 고쳐줘: `paginate(list(range(10)), 1, 3)`이 `[0, 1, 2]`가 아니라 `[3, 4, 5]`를 돌려줘.
