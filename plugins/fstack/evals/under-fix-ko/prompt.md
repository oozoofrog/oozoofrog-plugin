---
description: 'Terse bug report that names neither fstack nor a workflow: the skill loads and the defect is fixed.'
tags: [under]
runs: 3
max_turns: 60
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Bash, Edit, Write, TodoWrite]
expected_outcome: 'fstack skill is invoked; pager.py fixed; no git commit or push.'
---

1페이지가 이상하게 나와요. 봐주세요.
