---
type: llm
focus: last_message
---

PASS if the final message states the exit condition (or predicate) for the fix and reports it as met,
citing observed output from a run after the fix (repro output or test results).
FAIL if it reports the condition as unmet or Inconclusive, stops to ask the user whether to continue,
or claims success without any observed output.
Ignore language (Korean or English) and formatting.
