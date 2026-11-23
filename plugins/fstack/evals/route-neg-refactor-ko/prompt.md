---
description: 'Behavior-preserving refactoring belongs to the refactor skill.'
tags: [routing]
runs: 3
max_turns: 4
timeout_seconds: 180
allowed_tools: [Read, Glob, Grep, Skill]
expected_outcome: 'fstack skill is not invoked.'
---

동작 바꾸지 말고 `report.py`의 `ReportBuilder` 클래스 쪼개줘
