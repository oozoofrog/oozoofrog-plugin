---
description: 'Observe only for the skill load: English request to review the uncommitted diff, with shell tools. Findings are reported without changing code.'
tags: [observe]
runs: 3
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Bash, Edit, Write, TodoWrite]
expected_outcome: 'Record whether fstack or the built-in code-review skill handles it (not part of the pass rule); findings reported; no .py file written or edited; no git commit.'
---

Review this diff (the uncommitted change in this repo).
