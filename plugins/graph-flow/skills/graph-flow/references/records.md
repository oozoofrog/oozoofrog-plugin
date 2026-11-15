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
| `GF_SESSION` | Free text naming the session (model, thread title); recorded in every event |

An unset `node` or `session` is JSON `null`. An unknown role raises `GFError("bad_role", ..., EXIT_USAGE)`.

Roles prevent accidents; they are not a security boundary (P5, P10). An agent that deliberately sets another role or reads `human.key` is outside what this tool defends against; the skill text forbids it.

| Command | leader | worker | reviewer | human |
| --- | --- | --- | --- | --- |
| `init`, `plan set`, `host set`, `ready`, `route`, `assign`, `brief`, `merge`, `gate`, `reopen`, `learn add`, `learn promote`, `learn retire` | yes | no | no | no |
| `plan validate`, `learn list`, `trace` | yes | yes | yes | yes |
| `status` | yes | own node only | own node and its target only | yes |
| `start`, `red`, `check run`, `check record`, `submit` | yes | own node | no | no |
| `review submit` | no | no | own node | no |
| `decide ask`, `decide wait`, `decide list` | yes | own node only | own node only | yes |
| `decide answer` | no | no | no | yes, see section 7 |
| `mcp` | yes | yes | yes | no |
| `serve` | yes | no | no | yes |

A leader may also do a node's work itself (`inline`). That is allowed for lane 1 only because lane 2 and 3 nodes require an independent review (section 6).

## 3. Plan

`plans/NNNN.json`:

```json
{
  "schema_version": 1,
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
      "goal": "Implement the JSON export",
      "needs": [],
      "owns": ["notes.py", "tests/test_export.py"],
      "outputs": [],
      "reads": ["README.md"],
      "checks": [
        {"id": "unit", "type": "cmd", "run": "python3 -m unittest tests.test_export -v", "timeout_s": 600},
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
      "needs": [{"from": "export", "artifact": "notes.py"}],
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
| `id` | `^[a-z0-9][a-z0-9._-]{0,63}$`, unique in the plan |
| `kind` | `work`, `review`, `decision`. Deterministic steps such as the merge are `gf` commands recorded as events, not plan nodes (P6) |
| `needs` | List of `{"from": <node id>, "artifact": <name>}` (P3) |
| `owns` | Project-relative paths. A path ending in `/` owns the directory. No absolute paths, no `..`, nothing under `.git` or `.graph-flow` |
| `outputs` | Named non-file outputs (`findings`, `approval`) |
| `checks` | Section 4. Check ids match the node id pattern and are unique within the node |
| `lane` | `1`, `2`, or `3` (P9) |
| `grade` | `bulk`, `scoped`, `daily`, `large`, `security`; used by `gf route`. Optional for `decision` |
| `max_attempts` | Integer 1 to 3, default 3 (P2) |
| `review` nodes | Need `target` (a `work` node id) and `lens`; own nothing |
| `decision` nodes | Need `decision_kind` and `question`; own nothing; have no checks |

Unknown fields are preserved and ignored.

### Validation

`plan.validate(plan)` returns problems `{"code", "node", "message"}` (`node` is `null` for plan-level problems). Any problem makes `gf plan validate` exit 1 and `gf plan set` refuse the plan.

| Code | Rejects | Principle |
| --- | --- | --- |
| `V1` | Missing or mistyped required field, unknown `kind`, bad `schema_version` | |
| `V2` | Duplicate or malformed node id or check id | |
| `V3` | A `needs` entry whose `from` does not exist, whose `artifact` is empty, or whose `artifact` is neither equal to or under one of the producer's `owns` nor in its `outputs` | P3 |
| `V4` | A dependency cycle | P3 |
| `V5` | A `work` node with no check; a `cmd` check without `run`; a `review` node without `target` and `lens`, or whose `target` is not a `work` node; a `decision` node without `question` and a valid `decision_kind` | P1 |
| `V6` | `lane` missing or not 1, 2, 3 | P9 |
| `V7` | Two nodes with overlapping `owns` and no dependency path between them in either direction (they could run at the same time). Two path lists overlap when any pair is equal or one is under the other | P4 |
| `V8` | A path that is absolute, contains `..`, or is under `.git` or `.graph-flow` | |
| `V9` | A `work` node whose `effective_lane` is 2 or 3 and that no `review` node targets | P7, P9 |

### Normalization

`plan.normalize(plan)` returns `(normalized_plan, notices)` without mutating its argument, and is idempotent. `gf plan set` stores the normalized plan.

1. Every node gets `effective_lane = lane`.
2. A `work` node with no check of type `cmd` gets `effective_lane = min(3, lane + 1)`, and, unless it already has a check of type `human`, a check `{"id": "human", "type": "human"}` (if the id `human` is taken by a non-human check, the id `human_review` is used). Notice code `no_machine_check`.
3. Defaults are filled: `needs`, `owns`, `outputs`, `reads`, `checks` as empty lists; `max_attempts` 3.

`scope` and `cites` do not count as a machine check for rule 2: a node needs a check of its own behavior (P1). `V9` is evaluated on the normalized plan.

### Revisions

- `gf plan set <file>` validates, normalizes, writes `plans/NNNN.json`, then appends `plan.set` in one transaction (section 5). `store.read_plan` always loads the revision named by the last `plan.set` event; a plan file without its event is ignored.
- Each node has a fingerprint: SHA-256 of its normalized JSON with sorted keys. `plan.set` records every node's fingerprint.
- A node's **epoch** starts at the first revision containing it and restarts at every revision that changes its fingerprint. Only events of the current epoch count for that node, so a changed node starts again at `pending` with zero attempts; unchanged nodes keep their state. A node removed from the plan disappears from the state.

## 4. Checks and evidence grades

| Type | Fields | Judged by | Grade |
| --- | --- | --- | --- |
| `cmd` | `run`, optional `timeout_s` (default 600), optional `cwd` (project-relative) | `gf` runs `/bin/sh -c <run>` and reads the exit code; 0 is passed, anything else or a timeout is failed | 1 |
| `scope` | none | `gf` compares changed files with `owns` | 1 in isolated mode, 2 in shared mode |
| `cites` | none | `gf` verifies every finding of the review has `file` and `line`, the file exists in the tested tree, and the line number is within the file | 1 |
| `host` | `tool` (free text, e.g. an IDE test tool), `expect` | The agent runs its own tool and submits the outcome with `gf check record` | 2 |
| `human` | optional `prompt` | A person, through a `review` decision bound to this node, attempt, and check | human |
| (review verdict) | | The reviewer's `pass` or `fail` | 4 |

Grade 3 is rollback history (section 9).

### `cmd`

- Only commands written in the plan or in `checks.json` are executed. `gf` prints the command line to stderr before running it.
- Working directory: `--cwd` if given (a worktree), else the project root, joined with the check's `cwd`.
- Output (stdout and stderr interleaved) goes to `evidence/<node>/<check>/a<attempt>-<8 hex>.log`, created with exclusive open; run-level checks use node `_run`. The 8 hex characters are random.
- The command runs **outside** the run lock. Before running, `gf` notes the node's attempt and the plan revision; when committing the result it re-checks both under the lock and, if either changed, discards the result with exit 4 (code `stale_result`).

### `scope`

`gf start` records the base: `git rev-parse HEAD`, and for every file that is modified or untracked at that moment its `git hash-object` value (`dirty`: map of path to hash).

- **Isolated mode** (the submission carries a `commit`): changed files are `git diff --no-renames --name-only -z <base.rev> <commit>`. Every changed file must be equal to or under one of the node's `owns`. Grade 1, `"attribution": true`.
- **Shared mode** (no commit): changed files are `git diff --no-renames --name-only -z <base.rev>` plus untracked files (`git ls-files --others --exclude-standard -z`), keeping a base-dirty file only if its current hash differs from the recorded one. A file is a violation when it is under no node's `owns` in the plan. Grade 2, `"attribution": false`, because changes in a shared tree cannot be attributed to one node. A shared-mode result never satisfies a lane 2 or 3 node (section 6, R3).
- Paths under `.graph-flow/` are excluded in both modes.

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
| `plan.set` | `revision`, `plan_sha256`, `fingerprints` (node id to hash), `constraints_applied` (ids) |
| `host.set` | `capabilities` (list of strings, e.g. `workflow`, `t3_delegate`, `xcode_mcp`) |
| `node.assign` | `node`, `executor` (`inline`, `subagent`, `workflow`, `t3`, `background`), `model`, `effort`, `provider`, `family` (`claude`, `openai`, `other`), `isolation` (`shared`, `worktree`) |
| `node.start` | `node`, `attempt`, `base` `{rev, dirty}`, `cwd` |
| `check.red` | `node`, `check`, `exit_code`, `failed_first`, `log` |
| `check.result` | `node`, `check`, `type`, `grade`, `result` (`passed`, `failed`), `attempt`, `phase` (`loop`, `gate`), `exit_code`, `timed_out`, `command`, `cwd`, `duration_ms`, `log`; scope adds `mode`, `attribution`, `violations`; host adds `note`; run-level checks use node `_run` and attempt 0 |
| `node.submit` | `node`, `attempt`, `commit` (full SHA or `null`), `branch` (or `null`), `changed_files`, `notes`, `low_confidence` |
| `review.submit` | `node` (the review node), `target`, `target_attempt`, `target_commit`, `verdict` (`pass`, `fail`), `findings` (list of `{severity, file, line, text}`) |
| `merge.result` | `merged` (list of `{node, commit, head}`), `conflicted` (list of `{node, commit, files}`) |
| `gate.verdict` | `node`, `attempt`, `verdict`, `rule`, `rejection` (or `null`), `tested_head` |
| `gate.final` | `result` (`passed`, `failed`), `failed_checks` |
| `node.reopen` | `node`, `reason` |
| `decision.ask` | `id`, `node` (or `null`), `attempt` (or `null`), `check` (or `null`), `purpose` (`node`, `human_check`, `lane3`, `trajectory`, `hold`, `free`), `kind`, `question`, `evidence` `{command, files, checks}` |
| `decision.answer` | `id`, `outcome`, `answer`, `source` (`dashboard`, `terminal`), `sig` (section 7) |
| `constraint.apply`, `constraint.add`, `constraint.promote`, `constraint.retire` | `ids` or `id` (written only when a run is addressed) |
| `log.recovered` | `dropped_bytes` |

### Derived state

`state.derive(plan, events)` is pure and returns:

```json
{
  "run": {"id": "notes_export", "plan_revision": 1, "status": "open", "host": ["t3_delegate"], "final": null},
  "nodes": {
    "export": {
      "status": "submitted",
      "kind": "work",
      "lane": 2,
      "effective_lane": 2,
      "attempts": 1,
      "max_attempts": 3,
      "assignment": {"executor": "t3", "model": "claude-sonnet-5-5", "effort": "medium", "provider": "claudeAgent", "family": "claude", "isolation": "worktree"},
      "base": {"rev": "0123abc", "dirty": {}},
      "submission": {"attempt": 1, "commit": "89abcde", "branch": "gf/notes_export/export", "changed_files": ["notes.py"], "notes": "", "low_confidence": []},
      "checks": {"unit": {"loop": {"result": "passed", "exit_code": 0, "attempt": 1}, "gate": null}},
      "red": {"unit": {"failed_first": true}},
      "reviews": [{"node": "review-export", "target_attempt": 1, "verdict": "pass", "family": "openai", "findings": []}],
      "rejections": [],
      "verdict": null,
      "merged_head": null,
      "trajectory_clean": true,
      "open_decisions": []
    }
  },
  "decisions": {
    "d3": {"id": "d3", "node": "export", "attempt": 1, "check": null, "purpose": "lane3", "kind": "authorization", "question": "", "evidence": {}, "status": "open", "outcome": null, "answer": null, "source": null, "verified": false, "stale": false}
  }
}
```

In `checks`, each phase holds the latest `check.result` data of the current attempt, or `null`. `reviews` lists only reviews whose `target_attempt` equals the node's current attempt; `family` comes from the review node's assignment. `run.status` is `complete` only when every node is `passed` and the last `gate.final` passed (section 6); otherwise `open`.

| Node status | Reached by |
| --- | --- |
| `pending` | No event in the current epoch |
| `assigned` | `node.assign` |
| `running` | `node.start` |
| `submitted` | `node.submit` or `review.submit` |
| `passed`, `rejected`, `unverified`, `held`, `awaiting_approval`, `replan` | The matching `gate.verdict` |
| `stale` | `node.reopen` on this node, or on a node it depends on directly or transitively, after it had started |

`trajectory_clean` is true when, in the current attempt, no check timed out, no loop-phase scope result has violations, and `attempts <= 2`.

A decision is `stale` when it is bound to a node attempt that is no longer the node's current attempt, or was asked in an earlier epoch of its node.

### Starting and readiness

`gf start <node>` is valid when the node's status is `pending`, `assigned`, `rejected`, `held`, `unverified`, or `stale`; its needs are satisfied; and `attempts < max_attempts`. Otherwise exit 4 (`not_startable`, `needs_unsatisfied`, or `attempts_exhausted`). `decision` nodes are never started.

Needs are satisfied when every `needs.from` node is `passed`; for a `review` node its `target` only needs to be `submitted` (the review happens before the target is accepted).

`graph.ready(plan, state)` lists nodes that are startable as above and that own no path overlapping the `owns` of a node currently `running` or `submitted`. A `decision` node is ready when its needs are satisfied and it is not `passed` (P12: a verdict changes this list).

`gf reopen <node> --reason TEXT` (leader) marks a passed node and everything that depends on it `stale` without rejecting them: their work is kept, they must be started and gated again.

## 6. Gate

`gf gate <node> [--cwd PATH]` is a leader command.

Preconditions (exit 4, no event): the node's needs are satisfied; a `work` or `review` node is `submitted`; if the submission has a `commit`, that commit is an ancestor of `HEAD` in the tested tree (`not_merged` otherwise). The gate records `tested_head`.

Execution: the gate runs, in phase `gate`, every `cmd`, `scope`, and `cites` check of the node; if `effective_lane >= 2` it also runs the integration checks (the plan's `integration_checks` followed by the project's fixed checks). `host` results are taken from the loop phase of the current attempt.

Evaluation stops at the first rule that fires (P7: all deterministic evidence before observed evidence before opinion):

| Rule | Condition | Verdict | Status |
| --- | --- | --- | --- |
| R1 | A grade 1 result of this gate run failed (node check or integration check) and `attempts < max_attempts` | `reject` | `rejected` |
| R2 | The same failure and `attempts == max_attempts` | `replan` | `replan` |
| R3 | Required evidence is missing for this attempt: a `host` check has no loop result; or `effective_lane >= 2` and the scope result is not isolated (`attribution` false); or `effective_lane >= 2` and no review targeting the node has submitted for this attempt; or such a review's `family` equals the node's assignment `family` | `unverified` | `unverified` |
| R4 | A grade 2 result failed, or a review of this attempt has verdict `fail`, and no verified approved `review` decision with purpose `hold` exists for this attempt | `hold` | `held` |
| R5 | `effective_lane == 2`, and `trajectory_clean` is false or the node's `rollbacks` (section 9) is greater than 0, and no verified approved `review` decision with purpose `trajectory` exists for this attempt | `needs_approval` | `awaiting_approval` |
| R6 | A `human` check has no verified approved `review` decision bound to this node, attempt, and check; or `effective_lane == 3` and no verified approved `authorization` decision with purpose `lane3` is bound to this node and attempt | `needs_approval` | `awaiting_approval` |
| R7 | Otherwise | `pass` | `passed` |

- For R5 and R6 the gate appends the missing `decision.ask` (with evidence: the commands about to be allowed, the changed files, the check table) unless an open, non-stale one with the same binding exists.
- A decision answered `rejected` or `revision_requested` for R5 or R6 yields `hold`.
- A review verdict can hold a node; it can never produce `pass` and never outranks a grade 1 failure.
- `decision` nodes: `gf gate <node>` passes (R7) when a verified answer with outcome `answered` or `approved` exists for a decision with purpose `node` bound to this node in its current epoch; `hold` (R4) when the outcome is `rejected` or `revision_requested`; otherwise `needs_approval` (R6) and the ask is appended.
- A rejection never changes another node's status (P8).

`gf gate --final` runs the plan's integration checks and every fixed check once on the current tree and appends `gate.final`. A run is `complete` only after a passed final gate, so fixed checks run on every run even when all nodes are lane 1 (P11).

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

For a scope failure the reason lists the violating files.

### Merge

`gf merge <node> [<node> ...]` (leader) integrates submitted commits into the current branch of the project root:

- Precondition: the tree has no modified tracked files (exit 4, `dirty_tree`).
- For each node in the given order: `git merge --no-ff --no-edit <commit>`. On conflict: `git merge --abort`, the node goes to `conflicted` with the conflicting files, and the remaining nodes are still attempted.
- One `merge.result` event is appended. A conflicted node is not rejected by the merge; the leader gates it (which fails the `not_merged` precondition) or restarts it.

## 7. Decisions

- `gf decide ask --kind K --question Q [--node N] [--check C] [--purpose P] [--command C] [--files F ...]` appends `decision.ask` and prints the id (`d<seq>`). The tool fills `attempt` from the node's current attempt. Kinds: `direction`, `information`, `review`, `authorization`. Default purpose: `free`.
- `gf decide wait <id> [--timeout S]` polls the log (1 second interval) until the decision is answered; exit 0 with the answer, exit 1 on timeout.
- `gf decide list` returns open decisions (for worker and reviewer roles: only those bound to their node).
- Valid outcomes: `approved`, `rejected`, `revision_requested` for kinds `review` and `authorization`; `answered` for the other two.
- An answer to a stale decision is refused (exit 4, `stale_decision`).

Who can answer (P10):

- The dashboard server, started by a person with `gf serve`, appends `decision.answer` with `source: "dashboard"` and `sig`: HMAC-SHA256, hex, keyed with `human.key`, over the UTF-8 string `<run_id>\n<decision id>\n<outcome>\n<answer>`.
- `gf decide answer` on the command line is refused (exit 3) unless the environment has `GF_HUMAN_TERMINAL=1` and stdin is a TTY. It signs the same way with `source: "terminal"`.
- `state.derive` sets `verified` by recomputing the signature with `core.human_sig` (constant-time comparison), and `false` when the key is unreadable or the signature differs. Gate rules count only verified answers.

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
def init_run(project_root, run_id, actor): ...  # creates dirs, .gitignore, registry entry; appends run.init; returns run_dir Path; GFError("run_exists") if present
def locked(lock_path, timeout_s=30): ...        # context manager, exclusive flock
def events(run_dir): ...                        # list of event dicts; ignores an incomplete tail
def read_plan(run_dir): ...                     # normalized plan of the last plan.set, or None
def project_of(run_dir): ...                    # project root Path (run_dir/../../..)
def transaction(run_dir): ...                   # context manager yielding tx
#   tx.events -> list, tx.plan -> dict or None, tx.revision -> int
#   tx.append(type, data, actor) -> event dict (seq, ts, plan_revision filled in)
#   tx.write_plan(plan) -> (revision, sha256): writes plans/NNNN.json; caller appends plan.set in the same tx
def evidence_path(run_dir, node, check, attempt): ...   # creates and returns a new unique log Path (exclusive)
def atomic_write(path, text): ...               # temp file + fsync + os.replace
def register_project(root): ...                 # locked update of registry.json

# state.py
def derive(plan, events): ...                   # section 5 shape; plan may be None (then nodes is {})
def fingerprint(node): ...                      # sha256 hex of normalized node JSON, sorted keys

# plan.py
def validate(plan): ...                         # list of {"code", "node", "message"}; validates the normalized form
def normalize(plan): ...                        # (new_plan, notices); pure and idempotent
def overlaps(paths_a, paths_b): ...             # bool
def depends(plan, a, b): ...                    # True if a depends on b directly or transitively
def node_by_id(plan, node_id): ...              # node dict; GFError("unknown_node", exit_code=EXIT_STATE)

# checks.py   (each appends its event and returns that event's data dict)
def run_cmd(run_dir, node_id, check, phase, cwd, actor): ...     # check is the check dict; node_id "_run" for run-level
def run_scope(run_dir, node_id, phase, cwd, actor): ...
def run_cites(run_dir, node_id, phase, cwd, actor): ...
def record_host(run_dir, node_id, check_id, result, note, actor): ...   # result "passed" | "failed"
def red(run_dir, node_id, check_id, cwd, actor): ...             # check_id None runs every cmd check; returns {"results": [...], "notices": [...]}
def start(run_dir, node_id, cwd, actor): ...                     # appends node.start; returns its data
def submit(run_dir, node_id, commit, branch, notes, low_confidence, actor): ...   # computes changed_files; appends node.submit
def review_submit(run_dir, node_id, verdict, findings, actor): ...                 # appends review.submit

# gate.py
def evaluate(plan, state, node_id, gate_results, integration_results, rollbacks): ...
#   pure. gate_results / integration_results: lists of check.result data from this gate run.
#   returns {"verdict", "rule", "rejection" or None, "asks": [decision.ask data to append]}
def gate(run_dir, node_id, cwd, actor): ...     # preconditions, runs checks, appends asks and gate.verdict; returns the verdict data
def gate_final(run_dir, cwd, actor): ...        # appends gate.final; returns its data
def reopen(run_dir, node_id, reason, actor): ...  # appends node.reopen; returns {"node", "stale": [ids]}

# graph.py
def needs_satisfied(plan, state, node_id): ...  # bool
def ready(plan, state): ...                     # list of node ids in plan order

# assign.py
def assign(run_dir, node_id, executor, model, effort, provider, family, isolation, actor): ...   # appends node.assign
def brief(run_dir, node_id): ...                # English brief text for a sub-session; also written to brief/<node>.md
def plan_brief(project_root, run_dir=None): ... # planning brief for the splitter (section 8)

# route.py
def suggest(node, node_state, host, usage, routing): ...   # {"executor", "model", "effort", "provider", "family", "isolation", "why"}
def load_routing(path=None): ...                # routing.json next to the skill
def load_usage(cache_dir=None): ...             # provider usage from the host's cache files, {} when absent

# merge.py
def merge(run_dir, node_ids, actor): ...        # appends merge.result; returns its data

# decisions.py
def ask(run_dir, kind, question, node, check, purpose, evidence, actor): ...   # returns {"id", ...ask data}
def answer(run_dir, decision_id, outcome, answer_text, source, actor): ...     # signs; GFError on stale or invalid outcome
def wait(run_dir, decision_id, timeout_s): ...  # decision dict, or GFError(exit_code=EXIT_NEGATIVE) on timeout
def open_decisions(state, node_id=None): ...    # list
def verify(run_id, decision_id, answer_data): ...   # bool; compares answer_data["sig"] with core.human_sig
def ensure_key(): ...                           # creates human.key (mode 0600) if absent; called by `gf serve` and the terminal answer path

# learn.py
def add(project_root, run_dir, node_id, text, review_when, paths, tags, actor): ...
def all_constraints(project_root): ...          # list, statuses healed as in section 8
def applying(project_root, plan): ...           # list of constraint dicts
def promote(project_root, constraint_id, command, actor, run_dir=None): ...
def retire(project_root, constraint_id, reason, actor, run_dir=None): ...
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
```

The MCP tool list and the dashboard's HTTP API are specified by the units that own `mcp.py` and `server.py`, in `references/mcp.md` and `references/dashboard.md`; both call only the functions above.
