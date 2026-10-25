---
name: c4fy
description: Create source-backed C4 context, container, and component diagrams as standalone HTML with a soft rounded UI, animated C1/C2/C3 drill-down, source details, and SVG/JSON export. Use for C4 architecture maps and hierarchical system explanations; not for generic flowcharts, sequence diagrams, or C4 code-level diagrams.
---

# C4fy

Build C1/C2/C3 from one semantic model. C4fy is an original renderer; Archify inspired the artifact/validation workflow but is not a code or runtime dependency. Requires Node.js 18+; the delivered HTML has no network dependencies.

## Author from the owning source

Read [model contract](references/model.md) and the matching parts of [the MacPilot example](examples/macpilot.c4.json). For repository work, inspect manifests, executable entry points, actual calls and persistence operations. Pin the credential-free repository URL and commit; use committed source ranges, and disclose relevant uncommitted changes. A valid source range does not establish that its text supports the claim.

- C1: people and systems around one internal system.
- C2: applications/process roles and data stores inside one system. A container is not necessarily Docker. Do not promote a source file or module to an independently executing container.
- C3: components within one selected container; supporting people, systems and sibling containers can remain visible.
- Keep stable entity IDs across views. A system/container should lead to a view whose `scope` is that entity. The viewer morphs the selected card bounds into the child scope boundary through a clipped transition layer. Child cards translate at constant text scale, the title moves to the boundary heading, and connection endpoints follow the actual moving card ports on every animation frame, including links to external cards. Relationship labels move with the routes. Return reverses the same keyframes over 520ms. Shared external cards move independently. Reduced-motion users receive immediate transitions.
- Put meaningful actions/protocols and optional conditions on relationships. Keep unresolved boundaries explicit in descriptions. Do not invent a runtime, database, provider or metric from a name alone.

Keep view names, descriptions and surrounding prose in the user's language. Use `locale: "ko"` or `"en"` for the built-in UI; disclose other-language UI fallback rather than claiming translation. UI copy should explain architecture and the next action, not the diagram's production process.

## Generate and verify

Place the model and output in a task-specific artifact folder, outside this Skill package. Use the installed package's absolute path for the CLI:

```sh
node /path/to/c4fy/bin/c4fy.mjs validate model.json --repo-root /path/to/repo
node /path/to/c4fy/bin/c4fy.mjs render model.json output.html --repo-root /path/to/repo
```

Omit `--repo-root` only for a non-repository model or unavailable source, and state the evidence limit. `render` includes model/layout validation and stages the HTML and receipt, then replaces them with rollback on a handled failure. A failure must not be reported as delivery. The receipt records exact input/output hashes and source-range verification separately from browser and visual review.

Layouts use view-specific grid cells. Cluster scoped children in a rectangle and keep supporting systems/containers outside it. Automatic routing avoids opaque nodes and reports crossings/shared corridors. Fix nonzero crossings/corridors before calling a diagram visually clean. A compact numeric edge badge refers to the visible relationship list, which retains the full action and protocol. Do not delete relationships to silence layout errors. Fix the named layout neighborhood, then rerender.

A faded parent-scope card inside C2/C3 returns to the parent view on single click or keyboard activation, folding the outgoing structure into its parent-view card (instant with reduced motion); reserve space so it never overlaps model nodes or edges. The default viewer fits the complete C4 view above a compact bottom detail panel. Responsibility, technology, source evidence and relationships are paginated without expanding the page. Explicit zoom can pan inside the diagram on narrow screens. The viewer includes C1/C2/C3 navigation, scope expansion, theme, search, node/source details, keyboard navigation, fit/zoom and SVG/JSON download. Click a node to show its incoming/outgoing relationships and connected cards; unrelated cards fade and the relationship list filters to that node. Click the canvas background or press Escape to clear this focus. These relationships describe structure, not an inferred execution sequence. Double-click a node, use Alt+Down, or choose its details button to expand it. Selected relationships animate along their source-to-target direction until focus is cleared. With reduced motion, only static emphasis remains. There is no automatic motion before selection. Mobile diagrams preserve readable card size with internal panning; the page itself must not overflow horizontally.

For development verification, optional Playwright can exercise the exact HTML:

```sh
node /path/to/c4fy/tests/browser.mjs output.html evidence-directory
```

Install/use Playwright only in the development environment; it is not a runtime dependency. `C4FY_PLAYWRIGHT_PATH` may point to its `index.mjs`; `C4FY_CHROME` can name a Chrome executable. The browser probe targets a C1/C2/C3 fixture with a scoped system visible in C1, not every possible custom model. For other models adapt checks to the requested views, and do not claim this fixture probe as universal validation.

Inspect rendered light/dark screenshots and animated transitions. Confirm readable labels, correct scope boundaries, no route/node collisions and usable narrow screens. Browser automation is not perceptual approval. Exported SVG is a static view; the JSON preserves the complete model. Neither export is a runtime or deployment test of the depicted system.

## Delivery

Lead with the HTML link and the most useful architectural finding. State material omissions and evidence limits. Include changed paths and executed validations when required by the project. Preserve the distinction between created, tested, locally installed, published and newly discovered Skills. Do not publish, change unrelated Skills or install global configuration based on this workflow alone.
