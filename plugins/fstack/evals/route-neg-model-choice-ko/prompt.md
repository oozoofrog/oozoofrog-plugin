---
description: 'Model choice belongs to the model-advisor skill.'
tags: [routing]
runs: 3
max_turns: 4
timeout_seconds: 180
allowed_tools: [Read, Glob, Grep, Skill]
expected_outcome: 'fstack skill is not invoked.'
---

이 작업 어떤 모델이 좋아? 작은 Python 모듈 하나를 전부 async로 바꾸는 작업이야.
