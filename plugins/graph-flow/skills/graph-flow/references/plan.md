# Plan contract

`plans/NNNN.json`:

```json
{
  "schema_version": 1,
  "title": "Export your notes",
  "goal": "Export notes to JSON without modifying the source",
  "requirements": [{"id": "R1", "text": "Every note is exported"}],
  "tags": ["python"],
  "integration_checks": [
    {"id": "all-tests", "type": "cmd", "run": "python3 -m unittest -v", "requires_passed": ["export"]}
  ],
  "nodes": [
    {
      "id": "export",
      "kind": "work",
      "title": "Create the export",
      "summary": "Produce a JSON copy of every note for the person requesting the export.",
      "goal": "Implement the JSON export",
      "needs": [],
      "owns": ["notes.py", "tests/test_export.py"],
      "outputs": [],
      "reads": ["README.md"],
      "checks": [
        {"id": "unit", "type": "cmd", "title": "Every note is exported without changing the source", "run": "python3 -m unittest tests.test_export -v", "timeout_s": 600},
        {"id": "scope", "type": "scope"}
      ],
      "lane": 2,
      "grade": "scoped",
      "max_attempts": 3,
      "requirement": "R1"
    },
    {
      "id": "review-export",
      "kind": "review",
      "goal": "Try to refute the export",
      "needs": [{"from": "export", "artifact": "notes.py", "label": "Note exporter"}],
      "target": "export",
      "lens": "data-loss",
      "owns": [],
      "outputs": ["findings"],
      "checks": [{"id": "cites", "type": "cites"}],
      "lane": 1,
      "grade": "daily"
    },
    {
      "id": "publish-ok",
      "kind": "decision",
      "goal": "Approve pushing the branch",
      "needs": [{"from": "export", "artifact": "notes.py"}],
      "decision_kind": "authorization",
      "question": "Push branch notes-export to origin?",
      "context": {"why": "The reviewed export is ready to share", "if_approved": "Publish the branch", "if_rejected": "Keep the work local", "undo": "The published branch can be deleted"},
      "owns": [],
      "outputs": ["approval"],
      "checks": [],
      "lane": 3
    }
  ]
}
```

| Field | Rule |
| --- | --- |
| Plan `title` | Optional string, at most 80 characters; the flow's human-readable name |
| Node `title`, `summary` | Optional strings on every kind: title at most 60 characters; summary at most 300, one sentence saying what the node produces and for whom |
| `id` | `^[a-z0-9][a-z0-9._-]{0,63}$`, unique in the plan |
| `kind` | `work`, `review`, `decision`. Deterministic steps such as the merge are `gf` commands recorded as events, not plan nodes (P6) |
| `needs` | List of `{"from": <node id>, "artifact": <name>, "label": <optional human artifact name>}`; `label` is a string of at most 60 characters (P3) |
| `owns` | Project-relative paths. A path ending in `/` owns the directory. No absolute paths, no `..`, nothing under `.git` or `.graph-flow` |
| `outputs` | Named non-file outputs (`findings`, `approval`) |
| `checks` | [Check types and grades](records.md#4-checks-and-evidence-grades). Check ids match the node id pattern and are unique within the node |
| `lane` | `1`, `2`, or `3` (P9) |
| `grade` | `bulk`, `scoped`, `daily`, `large`, `security`; used by `gf route`. Not applicable to `decision` |
| `max_attempts` | Integer 1 to 3, default 3, for work/review only (P2) |
| `review` nodes | Need `target` (a `work` node id) and `lens`; own nothing |
| `decision` nodes | Need `decision_kind` and `question`; own nothing; have no checks |
| Check `title` | Optional string on any check type (including integration checks), at most 120 characters, saying what the check confirms in plain words |
| Decision node / `human` check `context` | Optional object with optional string keys `why`, `if_approved`, `if_rejected`, `undo`, each at most 300 characters; no other keys |

All presentation strings above are written in the user's language. When present they must be non-empty (whitespace alone is empty); limits count Unicode characters. Missing presentation fields and empty `context` objects are valid. Unknown execution fields are rejected at every plan load. Node/check ids, requirements, constraints, needs pairs and the combined integration/promoted check ids must be unique. A stored effective lane must agree with normalization.

### Validation

`plan.validate(plan)` returns problems `{"code", "node", "message"}` (`node` is `null` for plan-level problems) and never raises on a malformed plan. It checks the **raw** plan for V1 to V8, then normalizes a copy and checks V9 on it. Any problem makes `gf plan validate` exit 1 and `gf plan set` refuse the plan.

Required top-level fields: `schema_version` (must be `1`), `goal` (non-empty string), `nodes` (non-empty list). Optional: `title`, `requirements`, `tags`, `integration_checks`.

| Code | Rejects | Principle |
| --- | --- | --- |
| `V1` | Missing or mistyped required field, unknown `kind`, bad `schema_version`; a present presentation string with the wrong type, empty text, or length over its limit; decision/human-check `context` with the wrong type or an unknown key | |
| `V2` | Duplicate or malformed node id or check id; duplicate node id in `requires_passed`; more than one `scope` check or more than one `cites` check in a node | |
| `V3` | An unknown node id in `requires_passed`; a `needs` entry whose `from` does not exist, whose `artifact` is empty, or whose `artifact` is neither equal to or under one of the producer's `owns` nor in its `outputs` | P3 |
| `V4` | A dependency cycle or a `requires_passed` entry equal to its own check id | P3 |
| `V5` | A `work` node whose raw `checks` list is empty; a `cmd` check without `run`; a `review` node without `target` and `lens`, whose `target` is not a `work` node, or whose `lane` is not 1; a `decision` node without `question` and a valid `decision_kind`, or with checks; an entry of `integration_checks` that is not a `cmd` check | P1 |
| `V6` | `lane` missing or not 1, 2, 3 | P9 |
| `V7` | Two nodes with overlapping `owns` and no dependency path between them in either direction (they could run at the same time). Two path lists overlap when any pair is equal or one is under the other | P4 |
| `V8` | A path that is absolute, contains `..`, or is under `.git` or `.graph-flow` | |
| `V9` | A `work` node whose `effective_lane` is 2 or 3 and that no `review` node targets | P7, P9 |

### Normalization

`plan.normalize(plan)` returns `(normalized_plan, notices)` without mutating its argument, and is idempotent. Notices have the shape `{"code", "node", "message"}`. `gf plan set` stores the normalized plan.

1. Defaults are filled: `needs`, `owns`, `outputs`, `reads`, `checks` as empty lists; `max_attempts` 3.
2. Every node gets `effective_lane = lane`.
3. A `work` node with no check of type `cmd` gets `effective_lane = min(3, lane + 1)`, and, unless it already has a check of type `human`, an added check `{"id": X, "type": "human"}` where X is the first unused id among `human`, `human_review`, `human_review_2`, `human_review_3`, and so on. Notice code `no_machine_check`.
4. Each node without `title` gets a notice `{"code": "no_title", "node": <id>, "message": "add a title in the user's language for the dashboard"}`. This notice changes neither its effective lane nor its checks and is never a validation problem.

`scope`, `cites`, and `host` do not count as a machine check for rule 3: a node needs a deterministic check of its own behavior (P1). The scope comparison is run by the gate for every `work` node whether or not the plan lists a `scope` check ([gate rules](records.md#6-gate)).

### Revisions

- `gf plan set <file>` validates, normalizes, writes `plans/NNNN.json`, then appends `plan.set`, all in one transaction ([records.md](records.md#transactions)). `store.read_plan` loads the revision named by the last `plan.set` event; a plan file without its event is ignored and its number is never reused (the next revision is the highest existing file number plus one, so numbers may have gaps).
- A plan file is JSON with sorted keys, two-space indent, and a trailing newline; `plan_sha256` is the SHA-256 of exactly those bytes.
- The `plan.set` event itself, and every later event, carries the new `plan_revision`.
- A node's fingerprint is the SHA-256 hex of `json.dumps(node, sort_keys=True, separators=(",", ":"), ensure_ascii=False)` encoded as UTF-8, computed on a copy of the normalized node with presentation fields excluded as specified under [Basis](records.md#basis-what-invalidates-a-node). `plan.set` records every node's fingerprint for inspection, but replay always recomputes it from validated plan files. Logged fingerprints never authorize preservation of work.
- A changed fingerprint invalidates the node and everything that depends on it ([Basis](records.md#basis-what-invalidates-a-node)). A node removed from the plan disappears from the state.

### Plan approval

A new structural `plan set` atomically appends `plan.set` with `plan_identity`, then a `decision.ask` with purpose `plan_approval`, kind `authorization`, no node/submission/check, that identity and a question in the plan language. The identity hashes the normalized plan with nodes represented by a sorted complete list of fingerprints (including each id), without collapsing duplicates; node order is irrelevant. Exactly these fields are excluded: plan `title`/`summary`/`context`; node `title`/`summary`/`context`; `needs[].label`; node `checks[].title`/`context`; and `integration_checks[].title`/`context`. Promoted-check metadata is not excluded. See [later question wording](records.md#wording-and-later-questions). Goals, ownership, dependencies, checks, lane and other structural fields are included.

An identical re-post creates no revision and reuses the current open or verified-approved decision. A wording-only revision retains a currently verified-approved decision and dispatch; it records `wording_only`, `approval_reused` and any `question_wording_changed` nodes in `plan.set`. All other new revisions ask fresh approval; old plan decisions receive `decision.superseded` (`id`, replacement `revision`), retain their answer/text, and are closed and stale. `decide wait` returns superseded immediately. Sending back requires nonempty text on both dashboard and terminal paths. The normal human-role and signature requirements apply; there is no skip flag, environment bypass or agent-answer tool.

Until current approval is answered, verified and approved, `ready`, `assign`, work/review `brief`, `start` (including worker/reviewer starts), `route`, `red`, `check run`, `merge`, every node gate, and the final gate refuse with exit 4, `plan_not_approved`, the decision id and `gf open --decision <id>`. MCP calls the same checks. `status`/dashboard return an empty ready list without failing. Planning briefs, validation, plan set, status, trace, decision list/wait remain usable by their [authorized roles](records.md#2-identity-and-roles).

During re-planning, **new starts wait; existing work continues**. Completed nodes retain accepted submissions, running nodes can submit; checks and gates wait for the new approval. To preserve those contracts safely, `plan set` refuses structural edits/removal of a running, submitted or passed node, or a producer it depends on (`active_plan_change`, exit 4). Add a new node for a changed requirement. Unstarted changed nodes and their dependents still follow the basis invalidation rule. Wording-only edits preserve all accepted work. A check already executing across a revision can still return `stale_result` under the existing race guard; rerun that check, not the worker attempt.

For continuing an older run, see [records.md recoveries](records.md#continuing-an-older-run).

Key and plan-file recovery are in [records.md](records.md#approval-integrity-and-execution-revisions).

If the current plan revision is missing or cannot be verified, `plan set` may replace it: treat the old plan as absent, reset every node and dependent, retain the old events as history, and require fresh approval even for the same structural identity. No original file is needed. Review `lens` is an instruction, is shown with the plan, and is part of its approved identity.

`plan set <file> --open`, `decide ask ... --open`, and `gate [<node>|--final] --open` perform the ordinary mutation and then open the right run/decision with one short output line. Only a waiting decision or successful final gate opens; `GF_NO_OPEN=1` suppresses every browser launch, including explicit `gf open` (which reports suppression), never approval. An opening failure adds `open_error` and retains `show`; the mutation is already recorded. MCP never opens the browser and returns a human-terminal `graph-flow open` instruction. An approved unchanged plan does not reopen the browser.

### Enforced fields and presentation labels

Unknown or inapplicable fields are rejected by name. All kinds accept identifiers, goals, titles, summaries, needs, reads, outputs, lane, requirement and context. `owns` and `checks` must be empty for decisions; reviews also own nothing. `target`/`lens` belong only to reviews, `question`/`decision_kind` only to decisions, and `grade`/`max_attempts` only to work/review. A supplied `effective_lane` must equal the derived value. Decision lane is a risk label; decision acceptance, not lane, controls release. Direction/information decisions cannot have dependents or send-back context.

| Check type | Accepted type-specific fields | Consumer |
| --- | --- | --- |
| `cmd` | `run`, `cwd`, `timeout_s`; provenance labels `from_constraint`, `added` | Command executor, including review gates |
| `scope` | none | Gate compares the frozen submission file list with `owns` |
| `cites` | none | Review gate validates file/line citations |
| `host` | `tool`, `expect` | Recorded host observation; missing evidence blocks, failure holds |
| `human` | `prompt`, `context` | Gate creates a question after submission and requires acceptance |

Every check also accepts `id`, `type`, and the presentation `title`. Work accepts cmd/scope/host/human; review accepts cmd/cites/host/human; decision accepts no checks. Run integration/promoted checks accept cmd only. The full command runs, with cwd and timeout enforced. No other check shows a planned command. Scope is compared against the submitted file list so gate integration output cannot contaminate the next comparison; commands still run in the tested tree, not a sandbox.

An `integration_checks` command may declare `requires_passed`, a non-empty list of distinct existing producer node ids. A reference to the check's own id is invalid. Only integration commands accept this field (V1). A listed producer's work gate runs the command at any effective lane once every other listed producer has passed. Other work gates run it at effective lane 2 or 3 once every listed producer has passed. Omitted declarations preserve the default of running at every effective lane 2 and 3 work gate. The final gate always runs every integration and promoted check. The declaration controls when to collect check evidence and leaves graph readiness to `needs` (P1, P3, P7, P8, P10, P12).

Run fields are schema_version, goal, title, summary, context, requirements, tags, nodes, integration_checks, promoted_checks and constraints. Local promoted checks/constraints are merged by id; a conflicting supplied record is rejected, never silently replaced. The local `.graph-flow/checks.json` is validated by the same command schema, with file and field in errors. Titles, summaries, context, needs labels, reads, outputs, requirement text, constraint text/provenance and check provenance are documented presentation/instruction fields, not machine assertions. `needs`/named outputs enforce graph order; `owns`, checks, lane and attempt limits enforce gate behavior. Constraint scope/tags select inherited instructions; the approved command is the machine enforcement for a promoted constraint.

All binding decisions carry a gate/plan issuer in the signed binding. Agent `decide ask` accepts only free direction/information questions. Gate requests bind the approved node contract, current submission, check/review records with ids and hashes, trajectory and rollback context. The gate recomputes the request and accepts only an identical verified approval. A passed review with a fail verdict therefore creates a new gate-owned hold; an earlier status question cannot override it. Rejected decision nodes stay out of ready and explain how to revise/re-post. Only current plan approval and open decisions participate in project-location mismatch; answered old questions remain history after a move.


Trivially successful cmd checks (`true`, `:`, `exit 0`, or an empty/whitespace-only command) produce `unfalsifiable_check` normalization notices in `plan validate` and `plan set`, without changing validation success or gate verdicts. `plan set` returns the notice count and the full `normalization_notices` list.


### Diagnostic notices

Notices are advisory and leave validation, verdicts and approval requirements unchanged.

- `circular_run_check` flags literal command paths (including `--option=path`, quoted paths and relative `cwd`) owned by a later node that depends directly or transitively on a work node whose gate can run the integration check. The notice names the run check, gate node, later owner and path in `plan validate`, `plan set` and the plan screen. Suppression requires another listed producer whose direct or transitive `needs` require the earlier work node to pass. A review's dependency on its target requires only a submission, even when the target appears in `needs`. The detector reads literal paths. Script defaults such as the first run's implicit `tasks/` input need an explicit `requires_passed` declaration.
- `run_check_failed_after_node_checks_passed` is recorded by the node gate when an undeclared integration check fails and the node's command and scope checks pass. It suggests checking for a missing producer declaration and leaves the verdict unchanged.
- `passes_before_work`: a passing `red` observation, or the first observation of a command check in an attempt, records that no owned-file change from the attempt's Git snapshot was observed before executing it. It is not proof that no thinking or unrecorded external work happened. The node and plan show this notice; `trace --conformance` counts unique node/attempt/check observations as `checks passing before work: N`. Repeated observations of the same check in the same attempt count once. Historical records lacking this observation are not relabelled. With a run selected, validation also displays its recorded notices.
