# C4fy model v1

An original JSON model feeds the independent renderer. Reference semantics: [C4 context](https://c4model.com/diagrams/system-context), [containers](https://c4model.com/diagrams/container), [components](https://c4model.com/diagrams/component), [code](https://c4model.com/diagrams/code). The [Archify project](https://github.com/tt-a1i/archify) informed the validate/deliver/evidence separation only; no Archify code, assets or package are embedded.

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

Unknown fields, XML-invalid control characters and lone UTF-16 surrogates are rejected. IDs are strings matching `[a-z][a-z0-9_-]{0,63}` and are unique per collection. Maximums: 300 elements, 300 relationships, 30 views; 40 nodes/view; 4 MiB CLI input. These fixed input bounds are independent of browser viewport size, and are not authoring targets. If source-relevant content exceeds a bound, divide it into meaningful related views or artifacts and state the coverage; do not silently truncate it to fit either the bound or the screen.

- Model: `version:1`, `title` (1–120 chars), optional `description` (1–500), `locale` (`ko|en`, English default), optional `repository:{url,revision}`, and the three arrays above.
- Repository: credential-free HTTPS URL with no query/fragment, full lowercase 40-character commit SHA. `--repo-root` checks the origin, committed regular-file modes and line bounds against that revision. It does not prove entailment or current installed behavior. GitHub source links use that immutable revision; other repository references remain text.
- Element: `id`, `kind` (`person|system|container|component|code`), `name` (1–80), `description` (1–500). `container` requires a system `parent`; `component` requires a container `parent`. Both require `technology` (1–100). `code` requires a component `parent`, a `codeType` and at least one source reference. Person/system cannot have a parent. `external:true` applies only to systems. Optional `sources`, `roleLabel` (1–48 characters, project-defined display role), and `icon` (catalog key). `kind` remains the C4 classification. Missing roleLabel falls back to the localized C4 type (code nodes use their codeType); missing icon falls back to the kind icon. Icon keys: `person`, `system`, `container`, `component`, `app`, `server`, `storage`, `database`, `queue`, `browser`, `extension`, `bridge`, `device`, `keyboard`, `code`. Raw SVG, URLs and unknown identifiers are rejected. Labels render as escaped text. Use source-backed role names consistently within each project; never derive them automatically from names.
- Relationship: `id`, `source`, `target`, `description` (1–160), optional `technology` (1–100), `optional` boolean, `sources`. Any edge with a code endpoint requires at least one source reference, including caller, declaration, conformance or type-use evidence as applicable. Self edges are not supported. Optional means a source-backed opt-in or conditional path, not uncertainty.
- Source: `{path,line,endLine?}`. Safe repository-relative POSIX path; positive line range, inclusive end, at most 12 per element/relationship. Do not include secrets or personal paths. Sources live on relationships as well as elements so an actual caller/write site can support each edge.
- View: `id`, `level` (`1|2|3|4`), internal `scope`, `title` (1–120), optional `description` (1–500), unique visible `nodes`, unique `relationships`, optional `positions:{nodeID:[column,row]}` with integers `0..12`. Every selected relationship endpoint must be visible. The renderer does not synthesize cross-level relationships.

C1 contains people/systems and includes its scoped system. C2 contains the scoped system's containers, plus directly connected people/other systems. C3 contains its scoped container's components, plus people, other systems and sibling containers. C4 contains code entities owned by its scoped component, plus supporting sibling components, sibling containers of the containing system, people and other systems. Code from another component and ancestor scope cards are not admitted as model nodes. Expanded views need at least one child. A scope boundary must not enclose supporting nodes. Each stable system/container/component with an authored child view can be expanded through the details button, double-click or Alt+Down; multiple same-level views also have a selector.

## Optional code structure

Existing v1 C1–C3 models require no migration. Add `kind:"code"` elements and a `level:4` view only when a component needs this detail. The scope must be a component, not a container or file. Files alone do not establish architectural components.

`codeType` is required only on code nodes: `class|interface|struct|enum|protocol|function|method|type|module|object|table`. It classifies a source symbol or data structure, independently of project-defined `roleLabel` and `icon`. The detail panel retains both the C4 kind and codeType; cards/SVG use the roleLabel or localized codeType, with the generic code icon by default. Code technology is optional because the owning component already declares technology.

Keep code parents flat at the architectural component. Express symbol membership, calls, implementation/conformance, inheritance and type use as explicit, source-backed relationships with precise descriptions. A method node may therefore share a component parent with its declaring class, with a separate “declares” relationship. This avoids inventing runtime or ownership hierarchy from names. Raw source bodies are not embedded; immutable source links open the evidence.

Select code entities by component scope, explanatory relevance and evidence. Do not omit source-relevant nodes or relationships merely to avoid canvas zoom, pan or scrolling. This does not require every symbol in a component or the entire repository: record the view's chosen concern and material omissions. The bundled five-node BrowserBridge view explains selected declaration, call and type-use relationships; it is a focused example, not a graph-size recommendation or a claim to show the entire component.

For example, these additions to a fictional Editor component named `editor-core` describe a contract and implementation:

```json
{
  "elements": [
    {"id":"document","kind":"code","codeType":"interface","parent":"editor-core","name":"Document","description":"Editable document contract","sources":[{"path":"src/document.ts","line":1,"endLine":8}]},
    {"id":"editor","kind":"code","codeType":"class","parent":"editor-core","name":"Editor","description":"Implements the document contract","sources":[{"path":"src/editor.ts","line":4,"endLine":20}]}
  ],
  "relationships": [{"id":"implements","source":"editor","target":"document","description":"Implements Document","sources":[{"path":"src/editor.ts","line":4}]}],
  "views": [{"id":"editor-code","level":4,"scope":"editor-core","title":"Editor code","nodes":["document","editor"],"relationships":["implements"]}]
}
```

This is an excerpt to merge into a complete model, not a standalone input. The bundled MacPilot example shows selected `BrowserBridge` methods and `BrowserConnection` at its pinned commit; omitted branches remain explicit. No child view means no drill action. Level tabs follow the current scope lineage, and the same-level selector switches authored alternatives. Code views reuse the complete-view fit, bottom pagination, node focus, morph-return, reduced motion, source links and SVG/JSON exports.

## Layout and text

Unpositioned nodes fill available cells in row-major order. Positioning is deliberately small and transparent; it is not a global graph solver. Two or three columns can suit laptop diagrams, but the canvas may grow in both dimensions within the input bounds. Each cell has a 244×158 card with generous route space. The rectilinear router searches four-side ports and clear lanes around nodes, with a penalty for crossings and shared segments. Inspect the receipt's per-view diagnostics; a passing model/layout is not a claim that every crossing is resolved.

Avoid outer-document scrolling. Initial Fit is a camera state for an overview, not a completeness criterion or a reason to remove nodes. The internal diagram uses its full layout coordinates and supports zoom in/out, two-axis scrolling and background-drag panning; its content need not fit the viewport at reading scale. The current zoom buttons use 0.6–2.8 times the initial fit scale; Fit restores the overview. Keep the compact paginated detail panel while using the canvas for larger graphs. A small-screen overview can have small text; zoom/pan and the selected node's details provide the reading path. These controls do not remove or synthesize graph elements.

Long card descriptions and names are shortened visually, with complete text in accessible names and the details panel. Edges use complete labels when space permits; otherwise a numbered badge links to the expanded relationship list. Details retain protocol and optional conditions. SVG is a static light-color view with card summaries and compact-edge key; use JSON for full descriptions and all views. SVG is not pixel-identical to the interactive HTML.

## Evidence

`output.html.receipt.json` binds source specification and output SHA-256/byte counts, model/layout checks, source-range results and explicit `browserEvidence: not-run`, `visualReview: not-run`. A separate browser receipt binds the HTML hash, records viewports/navigation/motion/download checks and leaves visual review pending. A human/image review must be recorded separately with the same artifact hash and observed scope. Retain earlier receipts when regenerating an artifact if they support a historical claim.

CLI validates before writing and rejects an input specification that aliases either the HTML or receipt destination. It stages HTML and receipt together, replaces both, and restores prior bytes on a handled failure. Failed rollback preserves its recovery directory and reports the path. This is ordinary filesystem atomic replacement with rollback, not a signed audit log or power-loss transaction guarantee.
