---
description: 'Terse request to look at the uncommitted change: the skill loads and reports findings without changing code.'
tags: [under]
runs: 3
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Bash, Edit, Write, TodoWrite]
expected_outcome: 'fstack skill is invoked; findings reported; no .py file written or edited; no git commit.'
---

변경분 좀 봐주세요.
