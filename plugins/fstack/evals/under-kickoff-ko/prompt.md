---
description: 'Vague integration wish with no named target: the skill loads, asks the user-owned questions and writes no code.'
tags: [under]
runs: 3
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Bash, Edit, Write, TodoWrite]
expected_outcome: 'fstack skill is invoked; the reply asks which tool and for what purpose; no .py file written or edited; no git commit.'
---

pager를 다른 도구랑 연동되게 해주세요.
