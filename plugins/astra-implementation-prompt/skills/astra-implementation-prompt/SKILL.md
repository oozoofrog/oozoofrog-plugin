---
name: astra-implementation-prompt
description: Use when the user asks Astra Max to prepare an implementation prompt for review and a later user-selected implementation chat. Do not use for ordinary implementation requests.
---

# Astra Implementation Prompt

Turn the user's task into a self-contained implementation prompt with `gpt-6-astra` / `max`, present it in full, and offer a user-selected Sol or Terra implementation chat. A request for a prompt does not authorize implementation or chat creation.

1. Inspect the task, prior decisions, applicable `AGENTS.md`, and relevant owning files. Verify the target project with `list_projects` for project work. Ask only for missing information that changes the goal or core design.
2. Check the current official invocation schema and model support. Author the prompt through an actual `gpt-6-astra` / `max` call, or directly only if the current session's model and reasoning are verifiable. Distinguish requested settings, tool-confirmed settings, and observed execution. If unavailable or failed, explain the cause; do not present another model's output as Astra's. A writing agent is not the implementation chat.
3. Follow [the workflow](references/workflow.md) for prompt content, presentation, user decision, and post-approval execution. Show the complete copyable prompt, project or location, proposed implementation model, scope and completion criteria before asking. Wait for the user's decision. Do not create an implementation chat or start implementation before approval.
4. After explicit approval, create a user-visible Codex chat with the chosen model and the approved prompt. Verify the returned state using the current tool schema and report only observed progress. Preserve uncertain creation results and reconcile before retrying.
