---
name: design-interfaces
description: "인터페이스 설계. Sketch types, signatures, and module structure before code, then stay in the loop while implementation fills in. Use for /design-interfaces, 'architect this', 'design this', or non-trivial work where jumping to code would lock in the wrong shape."
disable-model-invocation: true
---

# Design interfaces

Use the [host profile](../fstack/references/host.md) for tool calls, settings, installed resources and optional capabilities.

Before writing code, trace every system the change touches, then sketch two different shapes for it (types, signatures, module boundaries) and pick the one where each piece of state has one owner, each task has one way to do it, and callers need to know least. Redesign instead of patching if workarounds repeat.

For design alternatives or independent review, select the method using the [design request criteria](../fstack/references/workflows.md#design-requests).
