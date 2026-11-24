---
type: llm
focus: last_message
---

PASS if the final message reviews the uncommitted change in this repository: it names the changed file or
function and states at least one concrete finding about that change, or states that it found nothing to fix
and says what it checked.
FAIL if it only describes the repository in general, asks which change to review without reviewing the
uncommitted one, or reports that it modified the code.
Ignore language (Korean or English) and formatting.
