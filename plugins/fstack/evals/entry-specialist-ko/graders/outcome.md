---
type: llm
focus: last_message
---

PASS if the response supplies a usable Korean prompt that asks for a state diagram and a shortest sequence of events violating a rule, using a model or exhaustive state exploration to check it. It must work without knowing a specialist command name. FAIL if the ready-to-send prompt starts with a specialist command, if the response adds setup instructions or commentary outside the prompt, or if it claims to have performed the actual verification. A code fence around the prompt is acceptable.
