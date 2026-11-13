---
name: high-council-implementation
description: Use when the user asks a high-tier model or a council of them to prepare an implementation prompt for review and a later user-selected implementation session. Do not use for ordinary implementation requests.
---

# High Council Implementation

Turn the user's task into a self-contained implementation prompt written by a high-tier model the host actually offers, optionally reviewed by other high-tier models (the council), present it in full, and offer a user-selected implementation session. A request for a prompt does not authorize implementation or session creation.

The session that received the request is the leader. Everything except what the leader says to the user is in English: briefs to agents, their replies, the implementation prompt, and the first message of the implementation session. Translate the user's instruction into English before passing it on, even when the user wrote in another language. The leader talks to the user in the user's language.

1. Inspect the task, prior decisions, applicable `AGENTS.md`, and relevant owning files. Verify the target project with the host's project listing when one exists. Ask only for missing information that changes the goal or core design.
2. Read the host's current agent, delegation, and session tool schemas and list the high-tier models they actually accept. Choose the author and any council reviewers as [the workflow](references/workflow.md#choose-the-council) describes. Never assume a model from memory or from a vendor name; if the user named a model the host does not offer, say so and stop instead of substituting.
3. Follow [the workflow](references/workflow.md) for prompt content, council review, presentation, user decision, and post-approval execution. Show the complete copyable prompt, project or location, the models that wrote and reviewed it, proposed implementation model, scope and completion criteria before asking. Wait for the user's decision. Do not create an implementation session or start implementation before approval.
4. After explicit approval, create a user-visible implementation session with the chosen model and the approved prompt. Verify the returned state using the current tool schema and report only observed progress. Preserve uncertain creation results and reconcile before retrying.
