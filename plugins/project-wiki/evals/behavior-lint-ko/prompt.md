---
description: 'Lint the vault and report the one broken link.'
tags: [behavior]
runs: 3
max_turns: 10
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill, Bash]
expected_outcome: 'project-wiki is invoked, wiki_lint.py runs, and the reply names the broken link [[없는 교훈]].'
---

위키 검사해줘
