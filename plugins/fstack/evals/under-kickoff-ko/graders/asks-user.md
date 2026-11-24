---
type: llm
focus: last_message
---

PASS if the final message asks the user at least two questions that only the user can answer about the
integration (for example which tool, for what purpose, in which direction or format), and does not claim
that an integration was implemented.
FAIL if it asks fewer than two such questions, or reports that it implemented, added or changed code for an
integration.
Ignore language (Korean or English) and formatting.
