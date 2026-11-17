# Records and tool contract

This file is the contract between every part of graph-flow: the `gf` tool, the skill text, the MCP server, the dashboard, and the tests. Principle numbers (P1 to P12) refer to [principles.md](principles.md). When code and this file disagree, fix one of them in the same change.

## 1. Runtime and layout

- Python 3.9 or later, standard library only. No third-party imports, no network access except the loopback dashboard.
- Source lives in `scripts/graphflow/` next to this skill; `scripts/gf` is the executable entry (`python3 scripts/gf ...`).
- Tests live in `tests/test_*.py` and insert `scripts/` into `sys.path` themselves. Run one file from the repository root with:
  `python3 -I -S -B -m unittest discover -s plugins/graph-flow/skills/graph-flow/tests -p '<file>' -v`
- Tests never touch the real home directory or a real project: they set `GF_HOME` and use temporary directories and temporary git repositories.

```
<project>/.graph-flow/
  .gitignore                 contains "runs/" and ".lock"
  constraints.jsonl          project constraints (P11), one JSON object per line
  checks.json                fixed checks promoted from constraints
  .lock                      lock file for the two files above
  runs/<run-id>/
    plans/0001.json          immutable plan revisions, zero-padded revision number
    events.jsonl             append-only event log, the only source of state
    .lock                    lock file for this run
    evidence/<node>/<check>/ check output, one file per execution
    brief/<node>.md          briefs handed to sub-sessions
$GF_HOME/                    default ~/.graph-flow
  .lock                      lock file for the files below
  registry.json              {"projects": [{"root": "<abs path>", "added": "<ts>"}]}
  server.json                {"url", "port", "token", "pid", "started"} of a running dashboard
  human.key                  32 random bytes, mode 0600, created by `gf serve` (section 7)
```

`<project>` is the git top level of the working directory unless `--project` is given. A run is always addressed by the absolute path of its directory, so a session working in another git worktree writes to the leader's run. Everything under `.graph-flow/` is tool metadata: no node may own it and scope checks ignore it.

### File update rules

| File | Rule |
| --- | --- |
| `events.jsonl` | Append only, under the run lock (section 5) |
| `plans/NNNN.json` | Written once to a temporary name in the same directory, `fsync`, then `os.replace`. Never modified afterwards |
| `constraints.jsonl`, `checks.json` | Read-modify-write under the project `.lock`; each file is written to a temporary name and installed with `os.replace` |
| `registry.json`, `server.json`, `human.key` | Read-modify-write under `$GF_HOME/.lock`, installed with `os.replace` |

All locks are exclusive `fcntl.flock` locks on the named `.lock` file, blocking with a 30 second timeout (exit code 5, code `lock_timeout`).

## 2. Identity and roles

| Source | Meaning |
| --- | --- |
| `--run` or `GF_RUN` | Absolute path of the run directory |
| `--role` or `GF_ROLE` | `leader` (default), `worker`, `reviewer`, `human` |
| `--node` or `GF_NODE` | The node a worker or reviewer is bound to. Required for those two roles |
| `GF_SESSION` | Free text naming the session (model, thread title); recorded in every event. When unset, `T3CODE_THREAD_ID` is recorded as `t3:<id>`, else `CLAUDE_CODE_SESSION_ID` as `claude:<id>`, else null |

An unset `node` or `session` is JSON `null`. An unknown role raises `GFError("bad_role", ..., EXIT_USAGE)`.

Roles prevent accidents; they are not a security boundary (P5, P10). An agent that deliberately sets another role or reads `human.key` is outside what this tool defends against; the skill text forbids it.

| Command | leader | worker | reviewer | human |
| --- | --- | --- | --- | --- |
| `init`, `plan set`, `host set`, `ready`, `route`, `assign`, `brief`, `merge`, `gate`, `reopen`, `learn add`, `learn promote`, `learn retire` | yes | no | no | no |
| `plan validate`, `learn list`, `trace` | yes | yes | yes | yes |
| `status` | yes | own node only | own node and its target only | yes |
| `submit --commit` | yes | own node | no | no |
| `start` | yes | own node | own node | no |
| `red`, `check run`, `check record`, `submit` | yes | own node | no | no |
| `review submit` | no | no | own node | no |
| `decide ask`, `decide wait`, `decide list` | yes | own node only | own node only | yes |
| `decide answer` | no | no | no | yes, see section 7 |
| `mcp` | yes | yes | yes | no |
| `serve`, `open`, `setup` | yes | no | no | yes |

A leader may also do a node's work itself (`inline`). That is allowed for lane 1 only because lane 2 and 3 nodes require an independent review (section 6).

## 3. Plan

`plans/NNNN.json`:

```json
{
  "schema_version": 1,
  "title": "Export your notes",
  "goal": "Export notes to JSON without modifying the source",
  "requirements": [{"id": "R1", "text": "Every note is exported"}],
  "tags": ["python"],
  "integration_checks": [
    {"id": "all-tests", "type": "cmd", "run": "python3 -m unittest -v"}
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
| `checks` | Section 4. Check ids match the node id pattern and are unique within the node |
| `lane` | `1`, `2`, or `3` (P9) |
| `grade` | `bulk`, `scoped`, `daily`, `large`, `security`; used by `gf route`. Optional for `decision` |
| `max_attempts` | Integer 1 to 3, default 3 (P2) |
| `review` nodes | Need `target` (a `work` node id) and `lens`; own nothing |
| `decision` nodes | Need `decision_kind` and `question`; own nothing; have no checks |
| Check `title` | Optional string on any check type (including integration checks), at most 120 characters, saying what the check confirms in plain words |
| Decision node / `human` check `context` | Optional object with optional string keys `why`, `if_approved`, `if_rejected`, `undo`, each at most 300 characters; no other keys |

All presentation strings above are written in the user's language. When present they must be non-empty (whitespace alone is empty); limits count Unicode characters. Missing presentation fields and empty `context` objects are valid. Unknown fields are preserved and ignored, except unknown keys inside decision-node or human-check `context`.

### Validation

`plan.validate(plan)` returns problems `{"code", "node", "message"}` (`node` is `null` for plan-level problems) and never raises on a malformed plan. It checks the **raw** plan for V1 to V8, then normalizes a copy and checks V9 on it. Any problem makes `gf plan validate` exit 1 and `gf plan set` refuse the plan.

Required top-level fields: `schema_version` (must be `1`), `goal` (non-empty string), `nodes` (non-empty list). Optional: `title`, `requirements`, `tags`, `integration_checks`.

| Code | Rejects | Principle |
| --- | --- | --- |
| `V1` | Missing or mistyped required field, unknown `kind`, bad `schema_version`; a present presentation string with the wrong type, empty text, or length over its limit; decision/human-check `context` with the wrong type or an unknown key | |
| `V2` | Duplicate or malformed node id or check id; more than one `scope` check or more than one `cites` check in a node | |
| `V3` | A `needs` entry whose `from` does not exist, whose `artifact` is empty, or whose `artifact` is neither equal to or under one of the producer's `owns` nor in its `outputs` | P3 |
| `V4` | A dependency cycle | P3 |
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

`scope`, `cites`, and `host` do not count as a machine check for rule 3: a node needs a deterministic check of its own behavior (P1). The scope comparison is run by the gate for every `work` node whether or not the plan lists a `scope` check (section 6).

### Revisions

- `gf plan set <file>` validates, normalizes, writes `plans/NNNN.json`, then appends `plan.set`, all in one transaction (section 5). `store.read_plan` loads the revision named by the last `plan.set` event; a plan file without its event is ignored and its number is never reused (the next revision is the highest existing file number plus one, so numbers may have gaps).
- A plan file is JSON with sorted keys, two-space indent, and a trailing newline; `plan_sha256` is the SHA-256 of exactly those bytes.
- The `plan.set` event itself, and every later event, carries the new `plan_revision`.
- A node's fingerprint is the SHA-256 hex of `json.dumps(node, sort_keys=True, separators=(",", ":"), ensure_ascii=False)` encoded as UTF-8, computed on a copy of the normalized node with presentation fields excluded as specified under "Basis". `plan.set` records every node's fingerprint.
- A changed fingerprint invalidates the node and everything that depends on it (section 5, "Basis"). A node removed from the plan disappears from the state.

### Plan approval (0.3)

`plan set` atomically appends `plan.set` with `plan_identity`, then a `decision.ask` with purpose `plan_approval`, kind `authorization`, no node/submission/check, that identity and a question in the plan language. The identity hashes the normalized plan with nodes represented by id/fingerprint; node order is irrelevant. Plan title/summary/context, node title/summary/context, need labels and check title/context are excluded. Goals, ownership, dependencies, checks, lane and other structural fields are included.

An open or verified-approved decision is reused for the same identity, including wording-only revisions. Otherwise a fresh approval is asked; old plan decisions receive `decision.superseded` (`id`, replacement `revision`), retain their answer/text, and are closed and stale. `decide wait` returns superseded immediately. Sending back requires nonempty text on both dashboard and terminal paths. The normal human-role and signature requirements apply; there is no skip flag, environment bypass or agent-answer tool.

Until current approval is answered, verified and approved, `ready`, `assign`, work/review `brief`, `start` (including worker/reviewer starts), the gate of a decision node, and the final gate refuse with exit 4, `plan_not_approved`, the decision id and `gf open --decision <id>`. MCP calls the same checks. `status`/dashboard return an empty ready list without failing. Planning briefs, validation, plan set, status, trace, decision list/wait remain usable.

During re-planning, **new starts wait; existing work continues**. Completed nodes retain accepted submissions, running nodes can check/submit, and submitted nodes can be gated. To preserve those contracts safely, `plan set` refuses structural edits/removal of a running, submitted or passed node, or a producer it depends on (`active_plan_change`, exit 4). Add a new node for a changed requirement. Unstarted changed nodes and their dependents still follow the basis invalidation rule. Wording-only edits preserve all accepted work. A check already executing across a revision can still return `stale_result` under the existing race guard; rerun that check, not the worker attempt.

**Compatibility:** records with no `plan_identity`/plan-approval event are grandfathered: read/ready/assign/brief/start continue as before. Reading or upgrading never writes a migration. Explicitly setting another plan opts that run into approval, including when its old structure is unchanged. The first such set also preserves existing running/completed contracts.

`plan set <file> --open`, `decide ask ... --open`, and `gate [<node>|--final] --open` perform the ordinary mutation and then open the right run/decision with one short output line. Only a waiting decision or successful final gate opens; `GF_NO_OPEN=1` suppresses opening, never approval. An opening failure adds `open_error` and retains `show`; the mutation is already recorded. MCP never opens the browser and returns a human-terminal `graph-flow open` instruction. An approved unchanged plan does not reopen the browser.

## 4. Checks and evidence grades

| Type | Fields | Judged by | Grade |
| --- | --- | --- | --- |
| `cmd` | `run`, optional `timeout_s` (default 600), optional `cwd` (project-relative) | `gf` runs `/bin/sh -c <run>` and reads the exit code; 0 is passed, anything else or a timeout is failed | 1 |
| `scope` | none | `gf` compares the files the node changed with its `owns`; run for every `work` node | 1 |
| `cites` | none | `gf` verifies every finding of the review has `file` and `line`, the file is a project-relative path that resolves to a regular file inside the tested tree and outside `.git` and `.graph-flow`, and the line number is within the file | 1 |
| `host` | `tool` (free text, e.g. an IDE test tool), `expect` | The agent runs its own tool and submits the outcome with `gf check record` | 2 |
| `human` | optional `prompt` | A person, through a `review` decision bound to this node, attempt, and check | human |
| (review verdict) | | The reviewer's `pass` or `fail` | 4 |

Grade 3 is rollback history (section 9).

### `cmd`

- Only commands written in the plan or in `checks.json` are executed. `gf` records the command in the check result without echoing it to stdout or stderr.
- Working directory: `--cwd` if given (a worktree), else the project root, joined with the check's `cwd`. The resolved directory must stay inside that tree (exit 2, `bad_cwd`); this applies to checks from `checks.json` too.
- Output (stdout and stderr interleaved) goes to `evidence/<node>/<check>/a<attempt>-<8 hex>.log`, created with exclusive open; run-level checks use node `_run`. The 8 hex characters are random.
- The command runs **outside** the run lock. Before running, `gf` notes the node's `basis`, attempt, and the plan revision (and, for gate and merge operations, the submission id); when committing the result it re-checks all of them under the lock and, if any changed, discards the result with exit 4 (code `stale_result`).

### `scope`

`node.submit.changed_files` compares against the base of the node's FIRST attempt after its current basis, using the same snapshot comparison below. Retries with no new edits retain the node's changed files; reverting to that original snapshot removes a file. Scope comparisons continue to use each attempt's own base, so new out-of-scope edits in any attempt are detected. Committed submissions use the first base revision for changed_files and the current attempt base for commit ancestry and scope.

`gf brief` and the planning brief state the absolute project directory near the top and instruct running every command there; their tool invocation uses an absolute entry-script path. Check execution writes command output to evidence logs without echoing commands to stdout or stderr, so `gf --json gate` emits exactly one JSON document.

`gf start` records the base: `git rev-parse HEAD` in the node's working directory, and `dirty`, a map from path to state for every path that is modified, deleted, or untracked at that moment. The state of a path is: `deleted` for a tracked file that is missing; `link:<target>` for a symbolic link (the link text, not followed); `dir` for a directory (for example an untracked nested repository); otherwise `<mode>:<hash>`, the file's permission bits in octal and its `git hash-object` value. Computing the state never fails on an unusual path.

The comparison always asks one question: did this node change a file it does not own?

- **Committed submission** (the submission carries a `commit`): the commit must descend from `base.rev` (`gf submit` refuses it otherwise with `bad_commit`); changed files are `git diff --no-renames --name-only -z <base.rev> <commit>`.
- **Uncommitted submission** (no commit, shared tree): the candidates are `git diff --no-renames --name-only -z <base.rev>`, plus untracked files (`git ls-files --others --exclude-standard -z`), plus **every path in `base.dirty`** (so a file that was dirty at base and has since been restored or deleted is still examined). A candidate listed in `base.dirty` is changed only if its current state (hash, or `deleted` when missing) differs from the recorded one; every other candidate is changed.
- In both cases every changed file must be equal to or under one of the node's `owns`; the others are `violations`. Paths under `.graph-flow/` are excluded. The result is grade 1.

The uncommitted comparison is exact only when one node at a time works in the shared tree. Therefore `gf start` refuses a `work` node whose isolation is `shared` (or unassigned) while another `work` node with shared isolation is `running` or has a current uncommitted submission (exit 4, `shared_busy`). Review nodes change no files, so they neither block nor are blocked. Parallel work requires `worktree` isolation and committed submissions (P4).

### `red`

`gf red <node> [check]` runs the node's `cmd` checks before any work and appends `check.red` with `failed_first`. A check that already passes is reported as notice `red_already_green`; it does not block (P1).

## 5. Events and state

`events.jsonl` holds one JSON object per line.

```json
{"seq": 12, "ts": "2026-11-15T09:30:00Z", "run": "notes_export", "plan_revision": 1, "actor": {"role": "worker", "node": "export", "session": "exec:export sonnet/medium"}, "type": "check.result", "data": {}}
```

### Transactions

Every state-changing command is one transaction: take the run lock, read the log, derive the state, validate the transition against that state, append the event(s), `flush`, `fsync`, release. Validation and append are never separated, so two sessions cannot both start the same attempt. Long work (running a command, merging) happens outside the lock and commits afterwards with re-validation as in section 4.

Incomplete tail: readers ignore a final line that does not end in a newline or does not parse. The next writer, under the lock, truncates that fragment before appending and appends `log.recovered` with the number of bytes dropped.

### Event types

| Type | Data |
| --- | --- |
| `run.init` | `run_id`, `project_root`, `schema_version` |
| `plan.set` | `revision`, `plan_sha256`, `fingerprints` (node id to hash), `constraints_applied` (ids), `plan_identity` (0.3 structural hash) |
| `decision.superseded` | `id`, replacement `revision`; preserves any old answer and closes the decision |
| `host.set` | `capabilities` (list of strings, e.g. `workflow`, `t3_delegate`, `xcode_mcp`) |
| `node.assign` | `node`, `executor` (`inline`, `subagent`, `workflow`, `t3`, `background`), `model`, `effort`, `provider`, `family` (`claude`, `openai`, `other`), `isolation` (`shared`, `worktree`) |
| `node.start` | `node`, `attempt`, `base` `{rev, dirty}`, `cwd` |
| `check.red` | `node`, `check`, `exit_code`, `failed_first`, `log` |
| `check.result` | `node`, `check`, `type`, `grade`, `result` (`passed`, `failed`), `attempt`, `phase` (`loop`, `gate`), `exit_code`, `timed_out`, `command`, `cwd`, `duration_ms`, `log`; scope adds `violations`; host adds `note`; run-level checks use node `_run` and attempt 0 |
| `node.submit` | `node`, `attempt`, `commit` (full SHA or `null`), `branch` (or `null`), `changed_files`, `notes` (string or `null`), `low_confidence` (list of strings) |
| `review.submit` | `node` (the review node), `attempt`, `target`, `target_submission`, `verdict` (`pass`, `fail`), `findings` (list of `{severity, file, line, text}` with optional free-form `evidence`; `text` is one plain sentence a person will read on the dashboard, with paths, commands, ids and exit codes in `evidence`) |
| `merge.result` | `merged` (list of `{node, commit, head}`), `conflicted` (list of `{node, commit, files}`) |
| `gate.verdict` | `node`, `attempt`, `submission` (or `null`), `verdict`, `rule`, `rejection` (or `null`), `tested_head` |
| `gate.final` | `result` (`passed`, `failed`), `failed_checks`, `tested_head` |
| `node.reopen` | `node`, `reason` |
| `decision.ask` | `id`, `node` (or `null`), `submission` (or `null`), `check` (or `null`), `purpose` (`node`, `human_check`, `lane3`, `trajectory`, `hold`, `free`), `kind`, `question`, `evidence` `{command, files, checks}` |
| `decision.answer` | `id`, `outcome`, `answer`, `source` (`dashboard`, `terminal`), `sig` (section 7) |
| `constraint.apply`, `constraint.add`, `constraint.promote`, `constraint.retire` | `ids` or `id` (written only when a run is addressed) |
| `log.recovered` | `dropped_bytes` |

`checks.submit` rejects other notes or low-confidence types with a usage error before writing a submission.

The `seq` of a `node.submit` or `review.submit` event is that submission's **id**. A decision's `id` is `d` followed by the `seq` of its `decision.ask` event.

### Basis: what invalidates a node

Fingerprinting excludes node `title`, `summary`, and `context`; `label` within every `needs` entry; and `title` and `context` within every check. All other fields, including unknown extension fields, retain their existing fingerprint behavior. The plan-level `title` is outside node fingerprints. Adding, editing, or removing only presentation fields in a new revision leaves every node's basis, status, attempts, submission, and evidence untouched, including dependents. A new plan revision still requires a fresh final gate for run completion.

For every node the state keeps `basis`: the `seq` of the latest event that invalidated it, or 0. **Events about a node with `seq <= basis` are ignored for that node**, with one exception: its latest assignment is kept. After an invalidation the node is `pending` (or `assigned`, if it had an assignment) with zero attempts, no submission, no check results, and no verdict. Invalidating events:

1. a `plan.set` that changes the fingerprint of the node, or of any node it depends on directly or transitively (through `needs.from`; a review node also depends on its `target`);
2. a `node.reopen` naming the node or any node it depends on;
3. for a `review` node only: a `node.start` of its `target` (the target is being reworked, so the review must be redone).

A node's own work is kept on disk; invalidation only means it must be started, submitted, and gated again against the new inputs (P8: nothing is rejected in bulk, and a rejection of one node invalidates no other node).

Decisions are bound, not counted: a decision is **stale** when its node's `basis` is greater than or equal to the decision's ask `seq`, or when it carries a `submission` id that is not the node's current submission id. Stale decisions are never used by the gate and cannot be answered.

### Derived state

`state.derive(plan, events)` is deterministic for a given plan, event list, and `human.key`, and returns:

```json
{
  "run": {"id": "notes_export", "plan_revision": 1, "status": "open", "host": ["t3_delegate"], "final": null},
  "nodes": {
    "export": {
      "status": "submitted",
      "kind": "work",
      "lane": 2,
      "effective_lane": 2,
      "basis": 0,
      "attempts": 1,
      "max_attempts": 3,
      "assignment": {"executor": "t3", "model": "claude-sonnet-5-5", "effort": "medium", "provider": "claudeAgent", "family": "claude", "isolation": "worktree"},
      "base": {"rev": "0123abc", "dirty": {}},
      "submission": {"id": 9, "attempt": 1, "commit": "89abcde", "branch": "gf/notes_export/export", "changed_files": ["notes.py"], "notes": "", "low_confidence": []},
      "checks": {"unit": {"loop": {"result": "passed", "exit_code": 0, "attempt": 1}, "gate": null}},
      "red": {"unit": {"failed_first": true}},
      "reviews": [{"node": "review-export", "status": "passed", "target_submission": 9, "verdict": "pass", "family": "openai", "findings": []}],
      "rejections": [],
      "verdict": null,
      "merged_head": null,
      "trajectory_clean": true,
      "open_decisions": ["d14"]
    },
    "review-export": {
      "status": "passed",
      "kind": "review",
      "lane": 1,
      "effective_lane": 1,
      "basis": 0,
      "attempts": 1,
      "max_attempts": 3,
      "assignment": {"executor": "t3", "model": "gpt-6.1-sol", "effort": "high", "provider": "codex", "family": "openai", "isolation": "shared"},
      "base": {"rev": "0123abc", "dirty": {}},
      "submission": {"id": 11, "attempt": 1, "target": "export", "target_submission": 9, "verdict": "pass", "findings": []},
      "checks": {"cites": {"loop": null, "gate": {"result": "passed", "attempt": 1}}},
      "red": {},
      "reviews": [],
      "rejections": [],
      "verdict": {"verdict": "pass", "rule": "R7", "submission": 11, "attempt": 1},
      "merged_head": null,
      "trajectory_clean": true,
      "open_decisions": []
    },
    "publish-ok": {
      "status": "pending",
      "kind": "decision",
      "lane": 3,
      "effective_lane": 3,
      "basis": 0,
      "attempts": 0,
      "max_attempts": 3,
      "assignment": null,
      "base": null,
      "submission": null,
      "checks": {},
      "red": {},
      "reviews": [],
      "rejections": [],
      "verdict": null,
      "merged_head": null,
      "trajectory_clean": true,
      "open_decisions": []
    }
  },
  "decisions": {
    "d14": {"id": "d14", "seq": 14, "node": "export", "submission": 9, "check": null, "purpose": "lane3", "kind": "authorization", "question": "", "evidence": {}, "status": "open", "outcome": null, "answer": null, "source": null, "verified": false, "stale": false}
  }
}
```

- Every node has every key shown; unset values are `null`, `[]`, or `{}` as in the `publish-ok` example.
- `checks[<id>]` has `loop` and `gate`, each the latest `check.result` data of the **current attempt** for that phase, or `null`. `verdict` is the latest `gate.verdict` data for the current submission (for a decision node: since its basis), or `null`. `rejections` lists the rejection objects of this node's `reject` and `replan` verdicts since its basis, in order. `merged_head` is the `head` of the latest `merge.result` entry for the current submission's commit, or `null`; `submission`, `verdict`, and `merged_head` are cleared by `node.start`.
- `reviews` (work nodes only) lists every review node that targets the node and has submitted since its own basis (its status is `submitted`, `unverified`, `held`, `awaiting_approval`, or `passed`), with that review node's `status`, its `target_submission`, verdict, findings, and its assignment `family` (or `null`). The gate, not the list, decides which entries match the current submission.
- `open_decisions` holds the ids of open, non-stale decisions bound to the node. `decisions` holds every decision; `status` is `open`, `answered`, or `superseded`.
- `run.final` is the last `gate.final` data plus its `seq`, or `null`. `run.status` is `complete` only when the plan has at least one node, every node is `passed`, the last `gate.final` has result `passed`, and its `seq` is greater than the `seq` of every `plan.set`, `node.reopen`, and `gate.verdict` event; otherwise `open`.

| Node status | Reached by |
| --- | --- |
| `pending` | No event since the basis |
| `assigned` | `node.assign` |
| `running` | `node.start` |
| `submitted` | `node.submit` or `review.submit` |
| `passed`, `rejected`, `unverified`, `held`, `awaiting_approval`, `replan` | The matching `gate.verdict` (`pass`, `reject`, `unverified`, `hold`, `needs_approval`, `replan`) |

A node **has a current submission** when its status is `submitted`, `unverified`, `held`, or `awaiting_approval`. The `submission` field itself is kept until the next `node.start`, so verdicts and decisions bound to a submission id stay matched to it after the node is `passed` or `rejected`.

A scope violation in an earlier, rejected attempt does not by itself require human approval.

`trajectory_clean` is true when, in the current attempt, no check timed out, no loop-phase scope result has violations, and `attempts <= 2`.

### Starting and readiness

`gf start <node>` is valid for a `work` or `review` node when its status is `pending`, `assigned`, `rejected`, `unverified`, `held`, or `awaiting_approval`; its needs are satisfied; `attempts < max_attempts`; and the shared-tree rule of section 4 allows it. Errors (exit 4): `not_startable`, `needs_unsatisfied`, `shared_busy`, `attempts_exhausted`. Status is checked first: a node that is `running`, `submitted`, or `passed` is `not_startable` even on its last attempt, and nothing is appended for it. `attempts_exhausted` applies only to a node that could otherwise start. On `attempts_exhausted` the tool also appends `gate.verdict` with verdict `replan`, rule `R2`, unless the node is already `replan` (P2: one exhaustion rule for every retry path). `decision` nodes are never started.

Needs are satisfied when every `needs.from` node is `passed`. For a `review` node, its `target` only needs to have a current submission: the review happens before the target is accepted.

Other transitions are validated in the same way (exit 4, `wrong_status`):

- `gf assign` is valid when the node's status is `pending`, `assigned`, `rejected`, `unverified`, `held`, or `awaiting_approval`. In the derived state `node.assign` sets the status to `assigned` only when it was `pending`; otherwise it only replaces `assignment`.
- `gf submit` and `gf review submit` are valid only when the node is `running`; the event carries the attempt of that start.
- `gf check run`, `gf check record`, and `gf red` are valid only when the node is `running`.
- A node that is `passed` changes only through `gf reopen` or a plan change.

`graph.ready(plan, state)` lists, in plan order, the `work` and `review` nodes that `gf start` would accept, and the `decision` nodes whose needs are satisfied and that are not `passed` (P12: a verdict changes this list).

`gf reopen <node> --reason TEXT` (leader) appends `node.reopen`; the node and everything that depends on it become `pending` through the basis rule.

## 6. Gate

`gf gate <node> [--cwd PATH]` is a leader command. It may be run again on the same submission whenever new evidence or an answer has arrived.

Preconditions (exit 4, no event):

- the node's needs are satisfied (`needs_unsatisfied`);
- a `work` or `review` node has a current submission (`no_submission`);
- if the submission has a `commit`, that commit is an ancestor of `HEAD` in the tested tree (`not_merged`);
- for a `review` node, its `target_submission` equals the target's current submission id (`review_outdated`).

Execution, in phase `gate`, recording `tested_head`:

- `work`: every `cmd` check of the node, then the scope comparison (always, under check id `scope` or the id of the plan's scope check); if `effective_lane >= 2`, also the integration checks (the plan's `integration_checks` followed by the project's fixed checks).
- `review`: the `cites` check.
- `host` results are taken from the loop phase of the current attempt.

Evaluation stops at the first rule that fires (P7: all deterministic evidence, then observed evidence, then opinion). Only non-stale, verified decisions count.

| Rule | Condition | Verdict | Status |
| --- | --- | --- | --- |
| R1 | A grade 1 result of this gate run failed (node check, scope, cites, or integration check) and `attempts < max_attempts` | `reject` | `rejected` |
| R2 | The same failure and `attempts == max_attempts` | `replan` | `replan` |
| R3 | Required evidence is missing: a `host` check has no loop result for this attempt; or the node is a `work` node with `effective_lane >= 2` and there is no entry in `reviews` that is `passed`, has `target_submission` equal to this submission's id, and whose `family` and the node's assignment `family` are both known and different | `unverified` | `unverified` |
| R4 | A grade 2 result failed, or a `passed` review whose `target_submission` is this submission has verdict `fail`, and no approved `review` decision with purpose `hold` is bound to this submission | `hold` | `held` |
| R5 | `work` node, `effective_lane == 2`, and `trajectory_clean` is false or the node's `rollbacks` (section 9) is greater than 0, and no approved `review` decision with purpose `trajectory` is bound to this submission | `needs_approval` | `awaiting_approval` |
| R6 | A `human` check has no approved `review` decision with purpose `human_check` bound to this submission and check; or `effective_lane == 3` and no approved `authorization` decision with purpose `lane3` is bound to this submission | `needs_approval` | `awaiting_approval` |
| R7 | Otherwise | `pass` | `passed` |

- For R5 and R6 the gate appends the missing `decision.ask` (with evidence: the commands about to be allowed, the changed files, the check table) unless an open, non-stale one with the same node, submission, check, and purpose exists.
- A decision answered `rejected` or `revision_requested` for R5 or R6 yields `hold` (rule `R4`).
- A review can hold a node; it can never produce `pass` and never outranks a grade 1 failure.
- `decision` nodes have no submission. `gf gate <node>` gives `pass` (R7) when a verified, non-stale answer with outcome `answered` or `approved` exists for a decision with purpose `node` bound to this node; `hold` (R4) when that outcome is `rejected` or `revision_requested`; otherwise `needs_approval` (R6), appending the ask (from the node's `question` and `decision_kind`) if none is open.
- A rejection never changes another node's status (P8).
- The verdict is appended in one transaction that first re-derives the state and discards the result (exit 4, `stale_result`) unless all of these still hold: the plan revision, the node's `basis`, attempt, and submission id are unchanged; the node still has a current submission (for a decision node: it is not `passed`); and no `gate.verdict` for this node was appended since the gate started. Two gates on the same node therefore cannot both record a verdict, and a late gate can never overwrite a `passed` node.

`gf gate --final` runs the plan's integration checks and every fixed check once on the current tree and appends `gate.final`. Because completion requires the final gate to be the latest verdict-like event (section 5), fixed checks run on every completed run, including runs whose nodes are all lane 1 (P11).

Exit code of `gf gate`: 0 for `pass` (or a passed final gate), 1 for every other verdict.

Rejection record (P8), stored in `gate.verdict.data.rejection` and printed as text:

```
UNIT      export (attempt 2 of 3)
VERDICT   red
REASON    check unit exited 1
EVIDENCE  evidence/export/unit/a2-1f3e5a7c.log: last 5 lines of the log
SCOPE     notes.py, tests/test_export.py only
```

```json
{"unit": "export", "attempt": 2, "max_attempts": 3, "verdict": "red", "reason": "check unit exited 1", "evidence": {"log": "evidence/export/unit/a2-1f3e5a7c.log", "tail": ["AssertionError"]}, "scope": ["notes.py", "tests/test_export.py"]}
```

For a scope failure the reason lists the violating files. When several checks failed, the reasons are joined with `; ` and `evidence` holds the log and tail of the first failure. `gate.evaluate` is pure and returns the failed results; `gate.gate` reads the log tails and builds the rejection.

### Merge

`gf merge <node> [<node> ...]` (leader) integrates committed submissions into the current branch of the project root:

- Preconditions (exit 4, nothing appended): every node has a current committed submission (`no_commit`); no merge is already in progress (`merge_in_progress`); the tree has no modified tracked files (`dirty_tree`; untracked files do not block). Work done inline in the shared tree is committed by the leader, and submitted with `gf submit --commit <sha>`, before any merge.
- For each node in the given order: `git merge --no-ff --no-edit <commit>`. On conflict, or on any other failure of the merge command (for example an untracked file that would be overwritten): `git merge --abort` if a merge is in progress, the node is recorded as conflicted (with the conflicting files, or an empty list and the first line of git's error as the reason), and the remaining nodes are still attempted. The merge never stops halfway: every listed node is attempted and exactly one `merge.result` is appended, so git and the log always agree.
- One `merge.result` event is appended. For every conflicted node the merge also appends `gate.verdict` with verdict `reject` (or `replan` at the attempt limit), rule `M1`, and a rejection whose reason names the conflicting files, so the node is restarted like any other rejected node.

When a rejection has no log, EVIDENCE names offending paths or citation details, falling back to its reason (including missing reviews and failed review verdicts), never `None`. Such evidence may carry `details` (a list of strings). Scope rejections also carry `restore_paths` and render `RESTORE   Leader restores these paths before reassigning: <paths>`. The leader preserves other nodes' accepted and in-flight work during restoration.

## 7. Decisions

- `gf decide ask --kind K --question Q [--node N] [--check C] [--purpose P] [--command C] [--files F ...]` appends `decision.ask` and prints the id (`d<seq>`). The tool fills `submission` with the node's current submission id (or `null`). Kinds: `direction`, `information`, `review`, `authorization`. Default purpose: `free`.
- Record purposes are `node`, `human_check`, `lane3`, `trajectory`, `hold`, and `free`. `node` binds a planned decision; `human_check` requests a human look at a result; `lane3` asks permission for work that is hard to undo; `trajectory` asks whether to accept work with an unclean path (all attempts used, timeout, or scope overrun); `hold` concerns held work; `free` is an independently asked decision. IDs repeat across runs: clients must bind answers and drafts to project, run, and decision id together.
- `gf decide wait <id> [--timeout S]` polls the log (1 second interval) until the decision is answered; exit 0 with the answer, exit 1 on timeout.
- `gf decide list` returns open decisions (for worker and reviewer roles: only those bound to their node).
- Valid outcomes: `approved`, `rejected`, `revision_requested` for kinds `review` and `authorization`; `answered` for the other two.
- An answer to a stale decision (section 5, "Basis") is refused (exit 4, `stale_decision`). A decision is answered once: a second answer is refused (exit 4, `already_answered`), and `derive` uses the first answer.

Who can answer (P10):

- The dashboard server, started by a person with `gf serve`, appends `decision.answer` with `source: "dashboard"` and `sig`: HMAC-SHA256, hex, keyed with `human.key`, over the UTF-8 string `<run_id>\n<decision id>\n<outcome>\n<answer>`.
- `gf decide answer` on the command line is refused (exit 3) unless the environment has `GF_HUMAN_TERMINAL=1` and stdin is a TTY. It signs the same way with `source: "terminal"`.
- `decisions.answer` itself refuses any actor whose role is not `human` (exit 3, `forbidden`), so no other entry point (the MCP server, a script) can produce a signed answer for an agent role. The dashboard server and the terminal path call it with a `human` actor.
- `state.derive` sets `verified` by recomputing the signature with `core.human_sig` (constant-time comparison); it is `false` when the key is unreadable or the signature differs. This is the one place where `derive` reads outside its arguments. Gate rules count only verified answers.

## 8. Constraints and fixed checks (P11)

`constraints.jsonl` line:

```json
{"id": "c1", "text": "A test target lists every module it imports directly in its dependencies", "scope": {"paths": ["Package.swift"], "tags": ["swiftpm"]}, "derived_from": {"run": "m7", "node": "pkg", "attempt": 2, "evidence": "evidence/pkg/import/a2-0a1b2c3d.log"}, "review_when": "SwiftPM enables explicit import checking by default", "status": "active", "created": "2026-11-15T09:30:00Z"}
```

- `gf learn add --from <node> --text T --review-when W [--paths ...] [--tags ...]` requires an addressed run in which that node is `passed`; the tool fills `derived_from` with the run, node, attempt, and the log of one passed gate-phase check. A constraint cannot be derived from work that was not accepted.
- `status` is `active`, `promoted`, or `retired`. Retired constraints never apply.
- A non-retired constraint applies to a plan when its scope has neither paths nor tags, or one of its `scope.paths` overlaps (equal, or either is under the other) a path some node owns, or the plan's `tags` intersect `scope.tags`.
- `gf plan set` records the applying ids in `plan.set.data.constraints_applied` and appends `constraint.apply`.
- `gf brief --plan` prints the planning brief for the splitter: the applying constraints' texts, the fixed checks, and the host capabilities.
- `gf learn promote <id> --run "<command>"`: under the project lock, appends `{"id": "fx_<constraint id>", "type": "cmd", "run", "from_constraint", "added"}` to `checks.json` (`{"schema_version": 1, "checks": [...]}`), then sets the constraint's status to `promoted`. `checks.json` is installed first.
- `gf learn retire <id> --reason TEXT`: under the project lock, removes its fixed check, then sets status `retired` with `retired_reason`.
- Recovery after a partial update: `learn.fixed_checks` returns only checks whose constraint has status `promoted`; a `promoted` constraint without a fixed check is treated as `active`.

## 9. Trace (P12)

`trace.trace(run_dir)` returns:

```json
{"run": {"nodes": 3, "passed": 2, "attempts": 4, "rejections": 1, "duration_ms": 512000}, "nodes": {"export": {"attempts": 2, "rejections": 1, "first_start": "2026-11-15T09:30:00Z", "passed_at": "2026-11-15T09:41:00Z", "duration_ms": 660000, "checks_run": 5, "rollbacks": 0}}}
```

`rollbacks` for a node is the number of nodes in **other** runs of the same project that own a path overlapping this node's `owns` and that were `passed` and later reopened, rejected, or replanned. It is grade 3 evidence used by gate rule R5.

## 10. Command line conventions

`python3 scripts/gf [--run PATH] [--project PATH] [--role R] [--node N] [--json] <command> [args]`

- With `--json`, stdout is exactly one JSON object: `{"ok": true, ...}` merged with the dict the module function returned, or `{"ok": false, "code": "<slug>", "message": "..."}`. Without `--json`, short human text.
- Exit codes: `0` success; `1` negative result (a check failed, a verdict other than pass, validation problems, wait timed out); `2` usage error; `3` forbidden for the role; `4` state error (unknown node, attempts exhausted, wrong status, stale); `5` lock timeout or I/O error.
- Every failure inside the library is a `GFError(code, message, exit_code=EXIT_USAGE)`; `cli.main` turns it into the output and exit code above.

## 11. Modules

| Module | Responsibility |
| --- | --- |
| `core.py` | Errors, exit codes, actor, clock, home |
| `store.py` | Files, locking, transactions, plan revisions |
| `state.py` | Replay of the log into state |
| `plan.py` | Validation and normalization |
| `checks.py` | Check execution |
| `gate.py` | Verdict |
| `graph.py` | Readiness |
| `assign.py` | Assignment and briefs |
| `route.py` | Model and executor suggestion |
| `merge.py` | Branch integration |
| `decisions.py` | Decisions and signatures |
| `learn.py` | Constraints and fixed checks |
| `trace.py` | Aggregation |
| `cli.py` | Argument parsing, role checks, output |
| `mcp.py` | stdio MCP server |
| `server.py` | Dashboard server; `page.html` is its single page |
| `launcher.py` | The `graph-flow` and `gf` commands on PATH written by `gf setup` |

Public surface. Other modules may rely only on what is listed here. Functions raise `GFError`; "appends" means inside one transaction. `actor` is the dict from `core.actor_from_env`.

```python
# core.py
class GFError(Exception): ...            # GFError(code, message, exit_code=EXIT_USAGE); attributes code, message, exit_code
EXIT_OK, EXIT_NEGATIVE, EXIT_USAGE, EXIT_FORBIDDEN, EXIT_STATE, EXIT_IO = 0, 1, 2, 3, 4, 5
def actor_from_env(role=None, node=None): ...   # {"role", "node", "session"}; unset node/session are None
def now(): ...                                  # "2026-11-15T09:30:00Z"
def gf_home(): ...                              # pathlib.Path, not created
def human_sig(run_id, decision_id, outcome, answer_text): ...   # HMAC-SHA256 hex with $GF_HOME/human.key (section 7), or None when the key is unreadable

# store.py
def project_root(path=None): ...                # git top level of path or cwd; GFError if not a repository
def init_run(project_root, run_id, actor): ...  # run_id matches the node id pattern ("bad_run_id"); creates dirs, .gitignore, registry entry; appends run.init; returns run_dir Path; GFError("run_exists", exit_code=EXIT_STATE) if present
def locked(lock_path, timeout_s=30): ...        # context manager, exclusive flock
def events(run_dir): ...                        # list of event dicts; ignores an incomplete or unparseable last line; a damaged earlier line raises GFError("log_corrupt", exit_code=EXIT_IO)
def read_plan(run_dir): ...                     # the stored plan of the last plan.set (stored plans are already normalized), or None
def project_of(run_dir): ...                    # project root Path (run_dir/../../..)
def transaction(run_dir, timeout_s=30): ...     # context manager yielding tx; appends are buffered and written only on clean exit
#   tx.events -> list (includes events appended earlier in this tx), tx.plan -> dict or None, tx.revision -> int
#   tx.append(type, data, actor) -> event dict (seq, ts, plan_revision filled in)
#   tx.write_plan(plan) -> (revision, sha256): writes plans/NNNN.json; the caller appends plan.set in the same tx, and tx.plan / tx.revision advance when that event is appended
def evidence_path(run_dir, node, check, attempt): ...   # creates and returns a new unique log Path (exclusive)
def atomic_write(path, data): ...               # str or bytes; temp file + fsync + os.replace
def register_project(root): ...                 # locked update of registry.json

# state.py
def derive(plan, events): ...                   # section 5 shape; plan may be None (then nodes is {}); reads human.key through core.human_sig
def fingerprint(node): ...                      # section 3 "Revisions"

# plan.py
def validate(plan): ...                         # list of {"code", "node", "message"}; raw plan for V1-V8, normalized copy for V9; never raises
def normalize(plan): ...                        # (new_plan, notices); pure and idempotent
def overlaps(paths_a, paths_b): ...             # bool
def depends(plan, a, b): ...                    # True if a depends on b directly or transitively
def node_by_id(plan, node_id): ...              # node dict; GFError("unknown_node", exit_code=EXIT_STATE)

# checks.py   (each appends its event and returns that event's data dict)
def run_cmd(run_dir, node_id, check, phase, cwd, actor): ...     # check is the check dict; node_id "_run" for run-level
def run_scope(run_dir, node_id, phase, cwd, actor): ...   # the one scope comparison of a work node
def run_cites(run_dir, node_id, phase, cwd, actor): ...   # the one cites check of a review node
def record_host(run_dir, node_id, check_id, result, note, actor): ...   # result "passed" | "failed"
def red(run_dir, node_id, check_id, cwd, actor): ...             # check_id None runs every cmd check; returns {"results": [...], "notices": [...]}
def start(run_dir, node_id, cwd, actor): ...                     # validates per section 5 in one transaction; appends node.start; returns its data
def submit(run_dir, node_id, commit, branch, notes, low_confidence, cwd, actor): ...   # computes changed_files; appends node.submit; returns its data plus "id"
def review_submit(run_dir, node_id, verdict, findings, actor): ...   # fills target and target_submission; appends review.submit; returns its data plus "id"

# gate.py
def evaluate(plan, state, node_id, gate_results, integration_results, rollbacks): ...
#   pure. gate_results / integration_results: lists of check.result data from this gate run.
#   returns {"verdict", "rule", "failed": [the failing results], "asks": [decision.ask data without "id"]}
def build_rejection(node, node_state, failed, tails): ...   # tails: map of log path to list of last lines; returns the rejection object
def gate(run_dir, node_id, cwd, actor): ...     # preconditions, runs checks, appends asks and gate.verdict; returns the verdict data
def gate_final(run_dir, cwd, actor): ...        # appends gate.final; returns its data
def reopen(run_dir, node_id, reason, actor): ...  # node must be passed; appends node.reopen; returns {"node", "invalidated": [ids in plan order]}
def render_rejection(rejection): ...            # UNIT/VERDICT/REASON/EVIDENCE/SCOPE, plus RESTORE for scope violations

# graph.py
def has_current_submission(node_state): ...     # bool
def needs_satisfied(plan, state, node_id): ...  # bool
def shared_busy(plan, state, node_id): ...      # bool
def start_problem(plan, state, node_id): ...    # None, or "not_startable" | "attempts_exhausted" | "needs_unsatisfied" | "shared_busy"
def check_start(plan, state, node_id): ...      # raises GFError(code, exit_code=EXIT_STATE) when start_problem is not None
def ready(plan, state): ...                     # list of node ids in plan order

# assign.py
def assign(run_dir, node_id, executor, model, effort, provider, family, isolation, actor): ...   # appends node.assign; returns its data
def brief(run_dir, node_id): ...                # English brief text for a sub-session; also written to brief/<node>.md
def plan_brief(project_root, run_dir=None): ... # planning brief for the splitter (section 8)

# route.py
def suggest(node, node_state, host, usage, routing): ...   # {"executor", "model", "effort", "provider", "family", "isolation", "why"}
def load_routing(path=None): ...                # routing.json next to the skill
def load_usage(cache_dir=None): ...             # provider usage from the host's cache files, {} when absent

# merge.py
def merge(run_dir, node_ids, actor): ...        # appends merge.result and the M1 verdicts; returns the merge.result data

# decisions.py
def ask(run_dir, kind, question, node, check, purpose, evidence, actor): ...   # returns the ask data including "id"
def answer(run_dir, decision_id, outcome, answer_text, source, actor): ...     # actor role must be human; signs; returns the answer data; GFError on stale or invalid outcome
def wait(run_dir, decision_id, timeout_s): ...  # decision dict, or GFError(exit_code=EXIT_NEGATIVE) on timeout
def open_decisions(state, node_id=None): ...    # list
def verify(run_id, decision_id, answer_data): ...   # bool; compares answer_data["sig"] with core.human_sig
def ensure_key(): ...                           # creates human.key (mode 0600) if absent; called by `gf serve` and the terminal answer path

# learn.py
def add(project_root, run_dir, node_id, text, review_when, paths, tags, actor): ...   # returns the constraint dict
def all_constraints(project_root): ...          # list, statuses healed as in section 8
def applying(project_root, plan): ...           # list of constraint dicts
def promote(project_root, constraint_id, command, actor, run_dir=None): ...   # returns {"constraint", "check"}
def retire(project_root, constraint_id, reason, actor, run_dir=None): ...     # returns {"constraint"}
def fixed_checks(project_root): ...             # list of cmd check dicts

# trace.py
def trace(run_dir): ...                         # section 9 shape
def rollbacks(project_root, run_dir, owns): ... # int

# cli.py
def main(argv): ...                             # returns the exit code

# mcp.py
def serve(stdin, stdout): ...                   # newline-delimited JSON-RPC; tools filtered by GF_ROLE

# server.py
def serve(host="127.0.0.1", port=0): ...        # writes server.json; blocks
def open_dashboard(): ...                       # starts a detached `gf serve` when none answers; opens the browser; returns no address
def stop_dashboard(): ...                       # SIGTERM to the recorded dashboard; False when none answers

# launcher.py
def install(bin_dir=None, script=None): ...     # writes <bin_dir>/graph-flow and <bin_dir>/gf (default ~/.local/bin); refuses a foreign graph-flow, skips a foreign gf
def remove(bin_dir=None): ...                   # removes the ones it wrote
```

The MCP tool list and the dashboard's HTTP API are specified by the units that own `mcp.py` and `server.py`, in `references/mcp.md` and `references/dashboard.md`; both call only the functions above.

## 12. Dashboard presentation view

`GET /api/run` retains `plan`, `state`, `ready`, and `trace` and adds `view`. Build the view from the same current plan, events, and derived state loaded under the run lock, plus the learning store; no new events are written. Nodes, edges and decisions carry readable wording only; commands, exit codes, log paths and rejection reasons appear only in `timeline`, the record of what happened. Decision and node IDs are shown, because agent sessions say them. Shape (arrays below show one representative entry):

```json
{
  "title": "Export your notes", "language": "en", "run": "export-1", "project": "notes",
  "timeline": [{"id": "e6", "seq": 12, "ts": "2026-11-15T14:16:55Z", "kind": "attempt", "by": {"role": "leader", "session": "t3:6f0c"},
    "node": "export", "node_title": "Create the export", "attempt": 1, "state": "returned",
    "worker": {"executor": "t3", "model": "claude-sonnet-5-5", "effort": "medium", "provider": "claudeAgent"},
    "checks": [{"id": "unit", "title": "Every note is exported", "result": "failed", "phase": "gate", "command": "python3 -m unittest",
      "exit_code": 1, "timed_out": false, "duration_ms": 93, "log": "evidence/export/unit/a1-a8b952fc.log", "violations": []}],
    "notes": "Two notes still fail", "files": ["export.py"], "unsure": [], "reason": "check unit exited 1", "findings": []}],
  "nodes": [{
    "id": "export", "title": "Create the export",
    "summary": "Produce a JSON copy of every note for the person requesting the export.",
    "kind": "work", "target": null, "answered": false, "status": "running", "attempts": 2, "max_attempts": 3,
    "lane": 2, "laps": ["returned", "current"],
    "returned_reasons": [["Every note is exported", "An empty note was omitted"]],
    "reviewed_by_other_family": false,
    "inputs": [],
    "outputs": [{"label": "Note exporter", "other_title": "Review the export", "delivered": false}]
  }],
  "edges": [{"from": "export", "to": "review-export", "label": "Note exporter", "relation": "hands_over", "delivered": false, "gate": "returned"}],
  "decisions": [{
    "id": "d14", "node": "publish-ok", "node_title": "Approve publication",
    "question": "Publish the reviewed export?", "kind": "authorization", "purpose": "authorization",
    "record_purpose": "node",
    "context": {"why": "The export is ready to share"}, "has_evidence": true,
    "verified": ["Every note is exported"],
    "failed": [], "trajectory_reasons": [],
    "unverified": ["A new reader can follow the instructions", "Installation order needs a second look"],
    "worker_note": "Please read the installation section.",
    "files": [{"name": "guide.md", "path": "docs/guide.md"}]
  }],
  "lessons": [{"text": "Keep the original notes unchanged", "node_title": "Create the export"}],
  "counts": {"done": 0, "doing": 1, "waiting": 0, "needs_you": 1, "returned": 1, "returns_total": 1},
  "complete": false
}
```

- `run` is the run id and `project` the project directory's name, for the header.
- `timeline` lists what happened in event order, built from every event of the run. Each row has `id` (`e` plus the `seq` of the event that created it, stable for the row's life), `seq` and `ts` of its latest event, `kind`, and `by` (`role` and `session` of the actor of the event that created the row; for an attempt, whoever started it). Kinds: `started` (`run.init`); `planned` (`plan.set`, with `revision` and node `count`); `attempt` (one per `node.start`); `reopened` (`node.reopen`, with `node`, `node_title`, `reason`); `asked` (`decision.ask`, with `decision`, `node`, `node_title`, `question`); `answered` (`decision.answer`, with `decision`, the asked `node`, `node_title`, `question`, and `outcome`, `answer`); `final` (`gate.final`, with `result` and `failed` check ids); `learned` (`constraint.add`, with the constraint `text`; omitted when the text cannot be read). An `attempt` row gathers that attempt's later `check.result`, `node.submit`, `review.submit` and `gate.verdict` events and moves to the position of the latest one. Its `state` is `running`, `submitted`, or from the gate verdict `passed` (pass), `returned` (reject), `replan`, `needs_you` (needs_approval) or `held` (hold). `checks` holds the latest result per check id, a gate-phase run replacing the worker's loop-phase run, each with `id`, plan `title` (empty when the plan gives none), `result`, `phase`, `command`, `exit_code`, `timed_out`, `duration_ms`, `log` (a path for `/api/evidence`, or null) and scope `violations`. `worker` is the latest `node.assign` before the start; `notes`, `files` and `unsure` come from `node.submit`; `reason` is the rejection's reason; `findings` are the finding texts of a `review.submit` by this review node, which also makes the row `submitted`. The dashboard also uses these attempt rows in the decision reading view, with the recorded checks, notes and files visible before an answer. A current open decision takes precedence over running/submitted words in presentation; it does not rewrite an attempt row or earlier outcomes. Failed check titles are expectations and must be explicitly labelled as not met. A verdict without a rejection keeps an earlier reason. `learned` uses the constraint's text whatever its current status. `node.assign`, `host.set`, `constraint.apply` and `check.red` create no row.
- `title` falls back to the plan's `goal` (empty string without a plan). `nodes` follows plan order; each title falls back to its id and each summary to its goal. Node `kind`, `status`, `attempts`, and `max_attempts` come from the plan/state; `lane` is the effective lane.
- `language` is `"ko"` when the plan title or any node title/summary contains Hangul (Jamo, compatibility Jamo or syllables), else `"en"`. This is independent of browser language; the page uses the browser only when there is no run.
- Node `target` is the recorded review target id for review nodes, otherwise `null`. It binds a full review card to its target; it is never display copy. Review cards occupy the dependency layer immediately after their target, with a `reviews` arrow from the review card back to its target. They participate in the graph and the HTML list.
- Node `answered` is true only for a decision node with a current, non-stale answered decision in derived state. Its card can receive the finished treatment immediately after an answer, before a later gate accepts it. Work and review styles otherwise reflect their own status; an open decision gives its bound node an amber border and explicit waiting words. It is false on work and review nodes.
- Decision `files` is the deduplicated list of `{name, path}` from the node’s current submission `changed_files`, then decision evidence `files`, preserving order. `name` is the basename, `path` the exact project-relative request parameter. Unsafe paths and destinations escaping the project or entering `.git`/`.graph-flow` or private dashboard records are omitted. File existence and UTF-8 readability are checked when opened through `/api/file`; a listed file may have disappeared. Only this explicitly requested reader shows filenames and a small secondary path.
- `laps` has one entry for every `node.start` after the node's current basis. A rejection (`reject` or budget-exhausted `replan`) makes that attempt `returned`; a pass makes it `passed`; otherwise it is `current`. A current submitted attempt with an open, non-stale decision is `waiting_for_you`. Decision nodes normally have no attempts and an empty list.
- `returned_reasons` has one list per rejection after the current basis, in event order, including earlier attempts while a retry runs. Strings come only from failed gate-phase node checks' current plan titles (untitled checks are omitted) and matching reviewer finding `text` for the rejected submission. It never copies a rejection's technical reason, command, exit code, log, file or line. Duplicate strings within one rejection are collapsed. When no such human-readable evidence is recorded (for example a merge rejection), that rejection's list is empty. Run-level `_run` check results have no rejecting-node/submission binding, so the view does not attribute them to a particular rejection.
- Node `inputs` and `outputs` contain `{label, other_title, delivered}` entries copied from incoming/outgoing `edges`, in edge order. `other_title` is the title (legacy fallback: id) of the producer/receiver respectively. No matching edges means `[]`; labels follow the edge fallback below, and implicit review-edge labels remain empty.
- `reviewed_by_other_family` is true only when a passed review is bound to the node's current submission and both assignment families are known and different. A review's fail verdict still counts as review evidence; it does not mean the work passed.
- `edges` contains each node's `needs` entries in order, then its implicit review-target edge if any. Needs edges point from producer to receiver; the implicit review edge points from the review node to its target. Every edge has `relation`: `"waits_for_decision"` for a needs entry whose producer has kind `decision`, `"reviews"` for an implicit review-target entry, and `"hands_over"` for other needs entries. Recorded handoff labels are visible on the map in the presentation language; review and decision relations remain in accessible descriptions rather than adding label chips. A needs label falls back to `artifact`; an implicit review-target edge has no recorded artifact or label, so its label is the empty string. These are separate entries even when they have the same endpoints. `delivered` means the producer is passed. `gate` is `open` for a passed producer, else `returned` if it has any current-basis rejection, else `waiting_for_you` if it has an open, non-stale decision, else `closed`.
- `decisions` contains only open, non-stale decisions in ask order. A decision node supplies its `context`; a decision bound to a human check uses that check's context; otherwise context is `{}`. `has_evidence` means at least one recorded `command`, `files`, or `checks` evidence slot is non-empty; evidence contents are not copied. An unbound decision has `node: null`, `node_title: null`, and empty context.
- Decision `purpose` preserves a specific record purpose (`human_check`, `lane3`, `trajectory`, `hold`). For record purpose `node`, `free`, or absent, the view uses the decision's kind (`direction`, `information`, `review`, `authorization`). These eight values are the normal presentation purposes; unknown record values are preserved for forward compatibility and must receive neutral wording, never an assumed approval request. Korean/English meanings are: `human_check`/`review`: “사람이 직접 살펴봐야 하는 결과를 받아들일지 정해 주세요.” / “Decide whether to accept a result that needs a human look.”; `lane3`/`authorization`: “되돌리기 어려운 일을 허락할지 정해 주세요.” / “Decide whether to allow work that is hard to undo.”; `trajectory`: “평소와 다르게 진행된 일을 받아들일지 정해 주세요.” / “Decide whether to accept work with an unclean path.”; `hold`: “멈춰 둔 일을 어떻게 이어 갈지 정해 주세요.” / “Decide how to continue work that was put on hold.”; `direction`: “다음에 어느 방향으로 갈지 알려 주세요.” / “Tell us which direction to take next.”; `information`: “계속하는 데 필요한 정보를 알려 주세요.” / “Provide the information needed to continue.” The fallback is “내용을 읽고 어떻게 할지 정해 주세요.” / “Read the details and decide what to do.”
- Each decision also has `verified`: titles of non-human checks whose latest current-attempt result passed (event order across loop and gate phases; omit untitled checks). `unverified` lists human check titles, falling back to their prompts and omitting checks with neither, followed by the current submission’s nonempty low-confidence strings. Human checks remain in this list because no machine confirmed them. `worker_note` is the current submission’s notes text or `null` when absent. An unbound decision has `verified: []`, `unverified: []`, and `worker_note: null`. These are derived read-only from the same records; no outcomes are guessed.
- Decision `failed` is always a list of plain strings: one title for every node check whose latest current-attempt result failed, across loop and gate phases (including implicitly added checks), then every string finding `text` from a fail review bound to the current submission. A failed check with no readable title contributes `"A check without a description did not pass."`, translated by the page; ids and commands are never substituted. Findings need not wait for a rejection. Every decision purpose gets this information.
- Decision `trajectory_reasons` is always a list containing only `"used_all_attempts"`, `"timed_out"`, `"left_its_files"`, in that order when applicable. These follow `state.derive` exactly: more than two attempts, any current-attempt observation with `timed_out is True`, and any current-attempt loop scope observation with nonempty violations, respectively. Superseded observations still affect trajectory; older attempts and events at or before basis do not. With no derivable cause the list is empty, including when only rollback history prompted approval. The page lists only these actual causes in plain words for trajectory decisions.
- Decision `record_purpose` is the original record purpose as a string (empty when absent); `purpose` remains the normalized presentation purpose. The page suppresses a question only when it exactly equals `Approve <record_purpose> for <node id>?`, the default form generated by the gate for that record. Other authored questions are shown unchanged.
- Presentation readers discard non-string notes, titles, prompts, context values and finding text. Legacy low-confidence lists keep only strings; a single legacy string is retained as one note, other shapes are ignored. Malformed finding collections are ignored. A corrupt learning store yields no lessons rather than hiding the run.
- `lessons` contains all project learning constraints whose healed status is `active`, in store order (not promoted or retired constraints). Each entry has `text` and `node_title`. A source recorded in `derived_from` gets its current title (fallback: id) only when its source run matches this run and its node exists in this plan. No title snapshot is stored for other runs or removed nodes: their `node_title` is `null`. No learning store means `[]`.
- `counts.done` counts passed nodes. Among non-passed nodes without open decisions, `doing` counts running, submitted, or unverified nodes and `waiting` counts the rest. `needs_you` counts open, non-stale decisions, including unbound questions. `returned` counts non-passed nodes with at least one current-basis rejection, including retries; it can overlap `doing` or `waiting`. `returns_total` sums the number of `"returned"` laps across all current-plan nodes, including nodes that subsequently passed (current-basis history, like `laps`). The UI uses this total and says “times”; the existing `returned` key retains its meaning. These counters are integers, not an exclusive partition. `complete` is exactly whether derived `run.status` is `complete`.
- Without a plan, `nodes` and `edges` are empty and node counters are zero; unbound decisions and project lessons can still be present. Existing fallback ids and artifact names may themselves be technical, so leaders should provide presentation fields for person-facing flows.

The dashboard HTTP contract and fixed public static allowlist are in [dashboard.md](dashboard.md#get-staticname). Only those GET static requests skip token authentication; every request still needs the loopback Host check, and all APIs still require the token.

The dashboard view also exposes `plan_approval` (null for legacy runs; id/status/outcome/answer/verified/question/plan_identity otherwise), `plan_counts` (work nodes, declared checks including integration, scheduled human questions including this approval), and node `planned_checks`/`deliverables`. Planned question counts exclude unforeseen free questions and retry approvals. The timeline includes plan set, approval asked, answer text and superseded events.
