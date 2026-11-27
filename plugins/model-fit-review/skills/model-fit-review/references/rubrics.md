# Rubrics

Give a classifier the rubric and the items only. Do not tell it which model produced a reply, and do not pass ids that reveal the model.

## Follow-up rubric (reaction to a result)

Each item is one agent run. It has three fields:
- `request`: what the user asked.
- `assistant_reply_end`: the end of the agent's final reply (may be cut at the start).
- `next_user_message`: the next message the user sent in the same conversation.

Classify how `next_user_message` reacts to the agent's result. Choose exactly one label.

| label | Use when the next message... |
|---|---|
| accept | accepts the result or moves on to the next step in the same work. Includes short approvals ("yes", "go ahead", "진행"), answers to a question the agent asked, and reports that the user did what the agent asked. |
| new_topic | starts an unrelated topic and says nothing about the result. Includes slash commands such as `/init`. |
| extend | accepts the result and adds scope: a new feature, an extra requirement, a further improvement. |
| fix | says the result itself is wrong, broken, incomplete, missed something, or misunderstood the request. Includes "doesn't work", "not visible", disagreement with the agent's conclusion, and restating the request because the agent got it wrong. |
| method | corrects HOW the agent works, not the result: which tool to use, delegate to other agents, ask questions as multiple choice, do it yourself instead of asking the user, skip a loop, verify a different way, do not delete test data. |
| clarify | asks a question to understand the result or its status ("is CI done?", "what does X mean?"). |
| unclear | cannot be judged from the text (attachment only, "Retry", error text). |

Tie-breakers:
1. A message that points out a defect and adds a request → `fix`.
2. A question that implies the agent missed something ("Did you also check the remote one?") → `fix`.
3. A pure question about status or meaning → `clarify`.
4. Work on a different feature, project or subject that does not mention the result → `new_topic`, not `extend`. Use `extend` only when the new work builds on the result just delivered.

Output: a JSON object `{item_id: label}`.

## Task-type rubric (per episode)

Each item is one episode: the user's requests in order (first 6 shown, each cut at 220 characters) and `n_requests`.

| label | Use when most of the work is... |
|---|---|
| capability | judgment that a stronger model does better: architecture or design decisions, product planning, research and synthesis, finding the cause of an unknown bug, creative work (games, stories, visual design), a non-trivial new feature or tool. |
| volume | well-scoped, mechanical work with a clear spec: bulk edits, registering many issues, translating, renaming, updating text as told, extracting or classifying many items. |
| operate | driving tools and checking state: install, build to a device, merge, push, deploy, open an app, clean files, check resource use, find something, set up a tool or key. |
| coordinate | relaying between sessions: delegating work, passing context to another thread, collecting delegated results, telling workers to continue. |

Tie-breakers:
1. The user asks the agent to delegate the main work and later requests are mostly relays or approvals → `coordinate`.
2. The first request is a design or research question and later requests build on it → `capability`, even if a delegation request appears later.
3. Short approvals do not decide the label. Judge from the substantive requests.

## Question check (for a proposed Stop hook, phase J)

Use this only as a starting rubric for a dry run; adapt it to the user's own rule.

> You check the final message of an assistant turn. The user's rule: every question to the user goes through the interactive question tool, never as text at the end of a message. A numbered or lettered list in the message text does NOT satisfy the rule. Return ok=false if the message asks the user to decide, choose, confirm, or provide information in its text (for example "Shall I …?", "Which …?", or a list of options for the user to pick). Return ok=true if the message only reports, or if its only question is rhetorical, inside code or a quote, or a generic closing such as "let me know if you get stuck". If stop_hook_active is true, return ok=true.

Measure catches and false alarms against hand labels on about 50 real turn endings. A regex-only variant (strip code blocks and lines another rule requires, look at the last ~600 characters) can reach zero false alarms at lower recall and needs no model call; let the user choose the trade-off.
