---
description: 'Standalone "which of two approaches is better" question: the skill loads and the answer comes from a measured run, with report.py unchanged.'
tags: [under]
runs: 3
max_turns: 60
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Bash, Edit, Write, TodoWrite]
expected_outcome: 'fstack skill is invoked; both variants are run and measured; the answer cites the numbers; report.py and pager.py are not edited; no git commit.'
---

report.py 통째로 읽는 거랑 한 줄씩 중에 뭐가 나아요?
