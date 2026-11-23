---
type: regex
target: trace
pattern: '(?:^|\n)[^\n]*"role"\s*:\s*"assistant"[^\n]*?"type"\s*:\s*"text"\s*,\s*"text"\s*:\s*"(?:[^"\\]|\\.)*?Pace:\s*\W{0,2}drive\b'
match: not_contains
---
