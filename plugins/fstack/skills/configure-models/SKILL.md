---
name: configure-models
description: "모델 설정. Configure the worker models, panel order and reasoning budget for fstack workflows on the current host."
---
# Configure models

Identify the active [host profile](../fstack/references/host.md). Run `python3 <this-skill>/scripts/models.py --host <cursor|claude|codex|t3|other> show`. All worker workflows use the same reader. To load one role use `role 'swarm workers'` in place of `show`. Output lists are ordered. An absent setting inherits the parent. For an arena or review panel, use the requested number of available independent candidates. An inherited model cannot supply a different-vendor verdict.

Enumerate the models and reasoning levels actually offered to the session's worker tool. If enumeration is unavailable, preserve the parent default or obtain the user's available choices. Present the current budget and roles. For a selected budget, choose a supported reasoning level per role (small targets medium, medium targets high, large targets the highest supported up to xhigh); preserve explicit per-role overrides. Map an inherited alias by omitting the model field. Map explicit model and effort values to the active schema. Legacy values retain their original spelling until confirmed. Show any unavailable choices.

On confirmation, edit the JSON returned by show and pipe the complete document to `python3 <this-skill>/scripts/models.py --host <profile> save`. Use the project’s permitted scratch directory if a file is needed. Read it back. Profile-specific defaults and previous Cursor/Claude files are read only. To use project-scoped settings, set FSTACK_MODELS to an explicit project file for setup and all readers. Never alter a general host instruction file. For app proof, route to create-app-check-skill or create-model-checker-skill when requested.

Available roles are `feature, refactoring` (one role), `bug-fix`, `perf-issue`, `hillclimb`, `judgment and prose`, `swarm workers`, `arena runners`, `arena cross-judge pool` and `interrogate reviewers`. The last three accept ordered lists. Each other role accepts one choice. Merge changes into the current document. For example, on a fresh host this config explicitly inherits the parent for swarm:

```json
{"budget": "medium", "roles": {"swarm workers": ["inherit-parent"]}}
```
