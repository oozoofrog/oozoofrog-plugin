---
name: graph-flow
description: Use when a user asks to plan, split, delegate, verify, or track multi-step work with checks that can fail, per-node sub-session assignment, human decision points, or a progress dashboard, or explicitly invokes graph-flow. Exclude simple edits and ordinary questions that need no coordination.
---

# graph-flow

graph-flow turns multi-step work into a graph of nodes. Each node has an owner, checks that can fail, and a gate verdict. Progress is derived from an append-only event log, and decisions that need a person are recorded as decision nodes.

The `gf` tool (`scripts/gf`) reads and writes these records; the skill text decides when to use it.

## References

- [references/principles.md](references/principles.md): the principles (P1 to P12) behind the design.
- [references/records.md](references/records.md): file layout, roles, `plan.json`, events, gate rules, command line, and module contract.

The step-by-step procedure is not written yet.
