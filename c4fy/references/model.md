# C4fy model v1

An original JSON model feeds the independent renderer. Reference semantics: [C4 context](https://c4model.com/diagrams/system-context), [containers](https://c4model.com/diagrams/container), [components](https://c4model.com/diagrams/component). The [Archify project](https://github.com/tt-a1i/archify) informed the validate/deliver/evidence separation only; no Archify code, assets or package are embedded.

## Required shape

```json
{
  "version": 1,
  "title": "Notes",
  "locale": "en",
  "elements": [
    {"id":"reader","kind":"person","name":"Reader","description":"Reads notes"},
    {"id":"notes","kind":"system","name":"Notes","description":"Keeps personal notes"}
  ],
  "relationships": [
    {"id":"read","source":"reader","target":"notes","description":"Reads notes"}
  ],
  "views": [
    {"id":"context","level":1,"scope":"notes","title":"Notes in context","nodes":["reader","notes"],"relationships":["read"],"positions":{"reader":[0,0],"notes":[1,0]}}
  ]
}
```

This miniature example is fictional. The bundled MacPilot example is pinned to real source.

## Fields

Unknown fields, XML-invalid control characters and lone UTF-16 surrogates are rejected. IDs are strings matching `[a-z][a-z0-9_-]{0,63}` and are unique per collection. Maximums: 300 elements, 300 relationships, 30 views; 40 nodes/view. These are input bounds, not authoring targets.

- Model: `version:1`, `title` (1–120 chars), optional `description` (1–500), `locale` (`ko|en`, English default), optional `repository:{url,revision}`, and the three arrays above.
- Repository: credential-free HTTPS URL with no query/fragment, full lowercase 40-character commit SHA. `--repo-root` checks the origin, committed regular-file modes and line bounds against that revision. It does not prove entailment or current installed behavior. GitHub source links use that immutable revision; other repository references remain text.
- Element: `id`, `kind` (`person|system|container|component`), `name` (1–80), `description` (1–500). `container` requires a system `parent`; `component` requires a container `parent`. Both require `technology` (1–100). Person/system cannot have a parent. `external:true` applies only to systems. Optional `sources`.
- Relationship: `id`, `source`, `target`, `description` (1–160), optional `technology` (1–100), `optional` boolean, `sources`. Self edges are not supported. Optional means a source-backed opt-in or conditional path, not uncertainty.
- Source: `{path,line,endLine?}`. Safe repository-relative POSIX path; positive line range, inclusive end, at most 12 per element/relationship. Do not include secrets or personal paths. Sources live on relationships as well as elements so an actual caller/write site can support each edge.
- View: `id`, `level` (`1|2|3`), internal `scope`, `title` (1–120), optional `description` (1–500), unique visible `nodes`, unique `relationships`, optional `positions:{nodeID:[column,row]}` with integers `0..12`. Every selected relationship endpoint must be visible. The renderer does not synthesize cross-level relationships.

C1 contains people/systems and includes its scoped system. C2 contains the scoped system's containers, plus directly connected people/other systems. C3 contains its scoped container's components, plus people, other systems and sibling containers. Expanded views need at least one child. A scope boundary must not enclose supporting nodes. Each stable system/container can be expanded through the details button, double-click or Alt+Down; multiple same-level views also have a selector.

## Layout and text

Unpositioned nodes fill available cells in row-major order. Positioning is deliberately small and transparent; it is not a global graph solver. Use two or three columns for readable laptop diagrams. Each cell has a 244×158 card with generous route space. The rectilinear router searches four-side ports and clear lanes around nodes, with a penalty for crossings and shared segments. Inspect the receipt's per-view diagnostics; a passing model/layout is not a claim that every crossing is resolved.

Long card descriptions and names are shortened visually, with complete text in accessible names and the details panel. Edges use complete labels when space permits; otherwise a numbered badge links to the expanded relationship list. Details retain protocol and optional conditions. SVG is a static light-color view with card summaries and compact-edge key; use JSON for full descriptions and all views. SVG is not pixel-identical to the interactive HTML.

## Evidence

`output.html.receipt.json` binds source specification and output SHA-256/byte counts, model/layout checks, source-range results and explicit `browserEvidence: not-run`, `visualReview: not-run`. A separate browser receipt binds the HTML hash, records viewports/navigation/motion/download checks and leaves visual review pending. A human/image review must be recorded separately with the same artifact hash and observed scope. Retain earlier receipts when regenerating an artifact if they support a historical claim.

CLI validates before writing and rejects an input specification that aliases either the HTML or receipt destination. It stages HTML and receipt together, replaces both, and restores prior bytes on a handled failure. Failed rollback preserves its recovery directory and reports the path. This is ordinary filesystem atomic replacement with rollback, not a signed audit log or power-loss transaction guarantee.
