---
name: choice-interview
description: Conduct adaptive user or stakeholder interviews with automatically chosen single-answer, multiple-answer, and free-text UI to identify usability barriers, needs, and product priorities. Use when the user requests an interview, especially with choices; do not use for ordinary implementation clarification or authorization.
---

# Choice Interview

Interview through actual selectable UI, then turn answers into evidence-qualified product decisions. Match the respondent's expertise separately from the intended audience's expertise.

## Start and tools

- Accept the user's requested count, range, maximum, depth, time budget, or interviewing style. The default is a starting plan of about 10 questions, not a fixed cap or mandatory quota. Later user instructions can change that plan.
- If the user requests automatic sizing, estimate the question count from the decisions to resolve, existing evidence, topic breadth, and respondent effort. State a short rationale and an estimated count or range; revise it as answers resolve questions or expose gaps. Do not claim the estimate is an exact calculation.
- If no count or sizing mode is specified, use the default as an initial budget and adapt it to the task. A strict user maximum remains binding unless the user changes it. Do not increase a strict maximum on your own.
- Briefly state the objective and expected count or range. Distinguish an estimate from a user-set limit. Do not front-load a solution before learning the respondent's needs.
- For single-choice rounds, prefer the available `request_user_input_async` tool in Default mode. Use `request_user_input` only when actually available in the active mode. Do not switch modes or use onboarding tools merely to obtain a picker.
- Check the actual tool schema for multiple-choice support. A tool with a list of options may still allow only one selection; never invent a multi-select parameter or label single-select controls as multi-select.
- For rounds requiring multiple-choice UI, use a tool that explicitly supports multiple selections. If none exists and the `visualize` skill is available, read it and use the mixed-form template described below. Keep the whole round in one response surface to avoid conflicting submissions.
- If no true multiple-choice UI can be rendered, disclose the limitation and accept several numbered answers or free text as a fallback. Do not claim that fallback provides checkboxes.

## Automatically choose answer types

- Choose the answer type for each question from the decision it supports; do not make every question single-choice by default or require the user to configure types.
- Use `single` for one primary priority, a mutually exclusive policy, or one best-fitting state. Use native radio buttons and explicitly label it as one choice. If options can reasonably coexist, either use `multiple` or explain why one priority is needed.
- Use `multiple` for needs, barriers, capabilities, or outcomes that can coexist. Use native checkboxes and label it as multiple choices. Do not impose an arbitrary selection maximum; apply one only for an explicit prioritization task or user limit.
- Use `text` for an actual example, short answer, or explanation that cannot be captured without leading the respondent. A free-text alternative or optional note must also be available beside choice questions.
- Mix types within a round when needed. If a respondent selects several answers to a `single` question, preserve all their answers; clarify priority only if the next decision requires it. Do not discard all but the first answer.
- If replacing a pending question only to change its answer type, retain its ID and topic; it is not an additional interview question. Preserve answers already received.

## Mixed response form

- Read [assets/choice-form.html](assets/choice-form.html) only when rendering an inline mixed form. Copy it into a durable, task-owned visualization path and replace its embedded JSON configuration with the current interview's ID and questions. Do not edit the installed template for each interview.
- Question schema: `id`, `type` (`single`, `multiple`, or `text`), `title`, and `options` (stable `id` and `label` for each choice). Optional `maxSelections` is for a justified multiple-choice limit. Give a new round a unique `roundId`; retain it while changing unanswered question types.
- Render with the available `visualize` workflow; this is a working response form, not a product mockup. Use radio buttons, checkboxes, labels, and a text field; preserve theme and keyboard accessibility.
- Use an explicit button click handler for sending. Sandboxed conversation frames can block native form submission even when controls render correctly.
- Validate that single-choice replaces the prior selection, multiple-choice keeps independent selections, unanswered questions remain unanswered, and submitted payloads preserve question IDs, types, all selected options, and free text.
- The template uses `window.openai.sendFollowUpMessage` only from an explicit answer-send button. Draft state saved through `setWidgetState` is not a submitted answer and does not start a turn. Do not infer completion from optimistic state or from opening a host confirmation dialog; use the actual user message as the answer.
- If sending is unavailable or fails, expose the formatted answer text for manual copying. Do not silently discard choices or claim successful delivery.

## Ask and adapt

- Present 1–3 questions per round by default; follow a different user request. Use one decision per question, a concrete context, and a small useful set of short, distinct choices. Match the selection rule to the automatically chosen answer type.
- Keep choices neutral. Do not label opinion choices as recommended unless a tool schema requires it. A preselected option is not an answer. Use the UI's built-in free-text alternative instead of adding an "Other" option.
- Track questions presented, answers received, and unresolved questions. Avoid bundles that hide several questions in one title. Do not repeat unanswered questions or treat silence as a preference.
- Wait for answers before asking dependent questions. With asynchronous tools, do useful independent work if needed, then yield the turn instead of polling or inventing answers.
- Adapt the next round to answers. Prioritize the remaining decision that would most change the product. Skip questions whose answers are already explicit.
- For usability interviews, explore the desired task, first-use expectations, request formation, understanding of execution and results, recovery from failure, and willingness to continue only as relevant to the objective.
- Ask about concrete observed behavior where available. If a stakeholder predicts novice behavior, label it as a hypothesis. Do not present stakeholder preferences as user-test results or assume the respondent lacks the target audience's knowledge.
- Use familiar task language for a novice audience. Avoid asking the respondent to choose an internal architecture or technical component unless that choice is relevant to them.

## Synthesize and stop

- At an explicit user limit, when enough evidence exists, or when the user ends the interview, summarize confirmed answers, observed behavior, hypotheses, and material open questions separately. In default or automatic sizing, adjust the estimate if further questions would materially change the outcome; do not stop only because the initial estimate was reached or pad the interview to fill it.
- Connect each prioritized change to an answer and describe an observable success condition. Suggest a focused usability test for hypotheses that need real target-user evidence.
- Do not claim the product is usable from an interview alone. Do not turn interview answers into permission to implement, publish, install, or message others; follow the user's actual scope and existing authorization.
- Saving an interview record is optional and must follow the user's requested destination and data scope. Do not copy answers into global memory without an explicit request.
