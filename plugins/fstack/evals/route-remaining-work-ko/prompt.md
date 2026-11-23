---
description: 'Checkpoint request in a repository that keeps docs/plan and pending decisions.'
tags: [routing]
runs: 3
max_turns: 4
timeout_seconds: 180
allowed_tools: [Read, Glob, Grep, Skill]
expected_outcome: 'fstack skill is invoked (checkpoint playbook).'
---

남은 작업이랑 내가 확인할 결정 정리해줘
