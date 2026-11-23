---
description: 'Generic diff review with no spec.'
tags: [routing]
runs: 3
max_turns: 4
timeout_seconds: 180
allowed_tools: [Read, Glob, Grep, Skill]
expected_outcome: 'fstack skill is not invoked.'
---

Review this diff (the uncommitted change in this repo).
