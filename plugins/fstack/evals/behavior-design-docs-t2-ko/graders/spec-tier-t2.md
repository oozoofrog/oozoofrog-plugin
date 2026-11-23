---
type: regex
target: trace
pattern: '"name"\s*:\s*"Skill"\s*,\s*"input"\s*:\s*\{\s*"skill"\s*:\s*"(?:[\w-]+:)?fstack"[^\n]*(?:\n(?![^\n]*(?:"name"\s*:\s*"(?:Edit|MultiEdit|Write|NotebookEdit)"|"name"\s*:\s*"Bash"\s*,\s*"input"\s*:\s*\{\s*"command"\s*:\s*"(?:[^"\\]|\\.)*?(?:\bsed\s+-i|\btee\b|[^0-9&>]>>?\s*[^&\s]|\b(?:rm|mv|cp|touch|mkdir|patch)\s|\bgit\s+(?:commit|apply|checkout|restore|reset|add|stash|merge|rebase)\b|write_text|open\([^)]*\\"[wa]\+?\\")))[^\n]*)*?\n[^\n]*"role"\s*:\s*"assistant"[^\n]*?"type"\s*:\s*"text"\s*,\s*"text"\s*:\s*"(?:[^"\\]|\\.)*?Pace:\s*\W{0,2}(?:step|drive)\b(?:[^"\\]|\\[^n])*?Spec:\s*\W{0,2}T2\b'
---
