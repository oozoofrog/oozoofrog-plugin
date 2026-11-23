# Document templates (T2)

Use the project's own format when it has one. Otherwise use these. Write short declarative sentences, one point per sentence, in the project's language.

## Spec

```markdown
# Spec: <slice>
Status: Proposed | Approved (user, YYYY-MM-DD)

## Goal
<one or two sentences>

## Acceptance criteria
| ID | Keyword | Criterion | Verification |
|---|---|---|---|
| AC-1.1 | MUST | <trigger condition and observable result> | <test name or live check> |
```

## Domain

Write a domain document only for new terms or rules.

```markdown
# Domain: <area>
## Terms
- **<term>**: <definition>

## Rules
| ID | Rule | Source |
|---|---|---|
| R1 | <rule> | <spec ID, ADR or user decision> |
```

## ADR

```markdown
# ADR-<n>: <title>
Status: Proposed (AI) | Approved (user, YYYY-MM-DD)
## Context
## Decision
1. <numbered rule>
## Rationale
## Consequences
```

## Plan

```markdown
# Plan: <slice>
| Unit | Depends on | Files | Change | Verification IDs | Live check | Status |
|---|---|---|---|---|---|---|
| U1 | — | <paths> | <one change> | AC-1.1, R1 | <command or screen> | todo |
```

Status line convention: `todo` → `doing` → `done (YYYY-MM-DD)`. Add `needs confirmation` when an AI edit changed an approved document. Put IDs in a cell that holds only IDs, and list each ID separately; `scripts/trace.py` ignores IDs in prose and does not expand ranges.

To retire a spec or domain ID, write `Retired (YYYY-MM-DD): <reason>` in another cell of its row, or a cell that holds only `Retired`. Keep the row and never reuse the ID. A cell that only starts with the word, such as "Retired accounts are hidden", does not retire the row.

## Requirement keywords

Use RFC 2119 and RFC 8174 keywords when the strength matters. In Korean documents, keep the uppercase keyword next to the Korean wording.

| Keyword | Korean |
|---|---|
| MUST | 반드시 …해야 한다 |
| MUST NOT | …해서는 안 된다 |
| SHOULD | …하기를 권장한다 |
| MAY | …해도 된다 |

Do not map a keyword to "…할 수 있다". That form can mean capability or permission.
