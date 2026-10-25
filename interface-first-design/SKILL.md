---
name: interface-first-design
description: Use when designing, implementing, or reviewing product UI, especially when explanatory prose substitutes for clear structure, visible controls, or state feedback. Applies to product screens and interactions, not agent communication or technical documentation.
---

# Interface First Design

Make the interface convey what users can do, what they are acting on, and what happened through structure, state, and interaction. Concise text is part of that interface. Optimize for successful use, not fewer words.

## Map the task

Inspect the supplied screen, source, and behavior. For each core operation, map **user goal → object → current state → visible control → result/recovery**. Separate observed facts from proposals and unknowns.

Preserve functional visible labels, headings, accessible names, user content, actual data, errors, consent, and safety disclosures. Keep counts, units, statuses, relationships, and conditions semantically intact. An absent value remains unknown; a pending count is not a completed count. If meaning is ambiguous, retain it and resolve it from available evidence before rewriting it. For unavailable meanings, specify a safe usable fallback using confirmed capabilities; for example, keep an unfiltered list with supported opening/creation available while unresolved filters remain unavailable. Proposed control behavior must not invent stored facts or successful operations.

## Build the visible path

Use hierarchy, grouping, proximity, selection, and persistent controls to expose operations. Put actions beside objects; make mode and selection explicit. Prefer recognizable, labeled controls to cryptic icons, hidden gestures, hover-only actions, or tooltip-only guidance. Gestures and shortcuts can supplement a discoverable path. An accessible name alone does not make an unfamiliar icon visually understandable.

For explanatory prose, identify its job and provide structure, controls, or feedback that performs it. Then shorten or remove the redundant passage. Retain concise guidance at a real decision or unfamiliar requirement. Evaluate meaning and use, not word blacklists or blind deletion. See [examples](references/examples.md) when preservation or replacement is uncertain.

## Complete the states

For each core operation, cover applicable states:

| State | Visible path |
| --- | --- |
| First use / empty | Expose the first supported action, such as creation/addition when supported. Distinguish no data from no filter matches. |
| Loading / pending | Show what is in progress; preserve context and input. Confirm success only from a confirmed result. |
| Success / changed | Show the result and current state near the affected object. |
| Error / interrupted | Identify the failed operation; retain work and offer recovery or retry without duplication. |
| Destructive / consent | Name the target and consequence; expose an explicit choice and safe cancellation. |

## Verify and report

Specify concrete interaction routes in proposals: keyboard sequence and activation, dialog focus entry/return, touch access, and the noncolor cue for each selection/status/difference (such as a checkmark or patterned outline). Naming an accessibility check alone leaves the design unresolved.

Use available UI tools and project checks to exercise core operations and applicable states, including first-use/empty supported actions, loading, feedback, and recovery. Compare rendered data and content with the source. Summarize coverage by operation/state with observed evidence or an explicit unverified acceptance check; include keyboard/focus, narrow/touch, accessible names/announcements, and noncolor cues. A screenshot establishes appearance, not unexercised behavior. Claim human testing only when it occurred.

For a review, return **issue → visible remedy → verification**, tied to the object/state. For implementation, deliver the working UI and concise coverage results with remaining unknowns.
