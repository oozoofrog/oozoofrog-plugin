# States, evidence and recovery

Execution records (check results, submissions and merge results) are unsigned and can be falsified by anything with file access. Editing the project directly bypasses the tool. Signed approval protects the particular question, context, approved plan, submission and evidence hashes within the recorded project/run location; it does not prove execution or prevent direct edits.

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
  human.key                  32 random bytes, mode 0600, created only by a human dashboard/terminal answer, human-role setup, or human key re-pin (section 7)
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

Roles prevent accidents; they are not a security boundary (P5, P10). An agent that deliberately sets another role or reads or WRITES `human.key` is outside what this tool defends against; the skill text forbids it.

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
| `decide answer`, `key repin` | no | no | no | yes, see section 7 |
| `mcp` | yes | yes | yes | no |
| `serve`, `open`, `setup` | yes | no | no | yes |

A leader may also do a node's work itself (`inline`). That is allowed for lane 1 only because lane 2 and 3 nodes require an independent review (section 6).

Plan fields and validation live in [plan.md](plan.md).

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

`node.submit.changed_files` compares against the base of the node's FIRST attempt after its current basis, using the same snapshot comparison below. Retries with no new edits retain the node's changed files; reverting to that original snapshot removes a file. Loop scope comparisons use each attempt's own base, so new out-of-scope edits in any attempt are detected. Gate scope compares this frozen submission file list with the approved owns paths; later integration-check output does not enter that comparison. Committed submissions use the first base revision for changed_files and the current attempt base for commit ancestry.

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
| `plan.set` | `revision`, `plan_sha256`, `fingerprints` (node id to hash), `constraints_applied` (ids), `plan_identity` (structural hash), `wording_only`, `approval_reused` (decision id or null), `question_wording_changed` (node/title/fields entries) |
| `decision.superseded` | `id`, replacement `revision`; preserves any old answer and closes the decision |
| `host.set` | `capabilities` (list of strings, e.g. `workflow`, `t3_delegate`, `xcode_mcp`) |
| `node.assign` | `node`, `executor` (`inline`, `subagent`, `workflow`, `t3`, `background`), `model`, `effort`, `provider`, `family` (`claude`, `openai`, `other`), `isolation` (`shared`, `worktree`) |
| `node.start` | `node`, `attempt`, `base` `{rev, dirty}`, `cwd` |
| `check.red` | `node`, `check`, `exit_code`, `failed_first`, `command`, `log` |
| `check.result` | `node`, `check`, `type`, `grade`, `result` (`passed`, `failed`), `attempt`, `phase` (`loop`, `gate`), `exit_code`, `timed_out`, `command`, `cwd`, `duration_ms`, `log`; passing cmd results add `failed_before`; scope adds `violations`; host adds `note`; run-level checks use node `_run` and attempt 0 |
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

Fingerprinting excludes node `title`, `summary`, and `context`; `label` within every `needs` entry; and `title` and `context` within every check. All other allowed fields affect the fingerprint; unknown execution fields are invalid. The plan-level `title` is outside node fingerprints. Adding, editing, or removing only presentation fields in a new revision leaves every node's basis, status, attempts, submission, and evidence untouched, including dependents. A new plan revision still requires a fresh final gate for run completion.

For every node the state keeps `basis`: the `seq` of the latest event that invalidated it, or 0. **Events about a node with `seq <= basis` are ignored for that node**, with one exception: its latest assignment is kept. After an invalidation the node is `pending` (or `assigned`, if it had an assignment) with zero attempts, no submission, no check results, and no verdict. Invalidating events:

1. a `plan.set` that changes the fingerprint of the node, or of any node it depends on directly or transitively (through `needs.from`; a review node also depends on its `target`);
2. a `node.reopen` naming the node or any node it depends on;
3. for a `review` node only: a `node.start` of its `target` (the target is being reworked, so the review must be redone).

A node's own work is kept on disk; invalidation only means it must be started, submitted, and gated again against the new inputs (P8: nothing is rejected in bulk, and a rejection of one node invalidates no other node).

Decisions are bound, not counted: a decision is **stale** when its node's `basis` is greater than or equal to the decision's ask `seq`, or when it carries a `submission` id that is not the node's current submission id. Stale decisions are never used by the gate and cannot be answered.

### Derived state

`state.derive(plan, events)` uses the trusted `store.EventLog` filesystem context, validated revision files, current attachment bytes, and `human.key`, and returns:

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
      "assignment": {"executor": "t3", "model": "gpt-6.2-sol", "effort": "high", "provider": "codex", "family": "openai", "isolation": "shared"},
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
- if the submission has a `commit`, that commit is an ancestor of `HEAD` in the project root (`not_merged`);
- for a `review` node, its `target_submission` equals the target's current submission id (`review_outdated`).

Execution, in phase `gate`, recording `tested_head`:

- `work`: every `cmd` check of the node, then the scope comparison (always, under check id `scope` or the id of the plan's scope check); if `effective_lane >= 2`, also the integration checks (the plan's `integration_checks` followed by the approved plan's frozen `promoted_checks`).
- `review`: all declared `cmd` checks, then the `cites` check.
- `host` results are taken from the loop phase of the current attempt.

Evaluation stops at the first rule that fires (P7: all deterministic evidence, then observed evidence, then opinion). Only non-stale, verified gate-issued decisions matching the recomputed current question, context and evidence ids/hashes count.

| Rule | Condition | Verdict | Status |
| --- | --- | --- | --- |
| R1 | A grade 1 result of this gate run failed (node check, scope, cites, or integration check) and `attempts < max_attempts` | `reject` | `rejected` |
| R2 | The same failure and `attempts == max_attempts` | `replan` | `replan` |
| R3 | Required evidence is missing: a `host` check has no loop result for this attempt; or the node is a `work` node with `effective_lane >= 2` and there is no entry in `reviews` that is `passed`, has `target_submission` equal to this submission's id, and whose `family` and the node's assignment `family` are both known and different | `unverified` | `unverified` |
| R4 | A grade 2 result failed, or a `passed` review whose `target_submission` is this submission has verdict `fail`, and no approved `review` decision with purpose `hold` is bound to this submission | `hold` | `held` |
| R5 | `work` node, `effective_lane == 2`, and `trajectory_clean` is false or the node's `rollbacks` (section 9) is greater than 0, and no approved `review` decision with purpose `trajectory` is bound to this submission | `needs_approval` | `awaiting_approval` |
| R6 | A `human` check has no approved `review` decision with purpose `human_check` bound to this submission and check; or `effective_lane == 3` and no approved `authorization` decision with purpose `lane3` is bound to this submission | `needs_approval` | `awaiting_approval` |
| R7 | Otherwise | `pass` | `passed` |

- For R4, R5 and R6 the gate appends the missing `decision.ask` (with evidence: the commands about to be allowed, the changed files, the check table) unless an open, non-stale gate-issued request matches the same node, submission, check, purpose, kind, generated question and current evidence. Obsolete open requests for that purpose are superseded.
- A decision answered `rejected` or `revision_requested` for R5 or R6 yields `hold` (rule `R4`).
- A review can hold a node; it can never produce `pass` and never outranks a grade 1 failure.
- `decision` nodes have no submission. `gf gate <node>` gives `pass` (R7) when a verified, non-stale answer with outcome `approved` (review/authorization) or `answered` (direction/information) exists for the exact gate-issued current request with purpose `node`; `hold` (R4) when that outcome is `rejected` or `revision_requested`; otherwise `needs_approval` (R6), appending the ask (from the node's `question` and `decision_kind`) if none is open.
- A rejection never changes another node's status (P8).
- The verdict is appended in one transaction that first re-derives the state and discards the result (exit 4, `stale_result`) unless all of these still hold: the plan revision, the node's `basis`, attempt, and submission id are unchanged; the node still has a current submission (for a decision node: it is not `passed`); and no `gate.verdict` for this node was appended since the gate started. Two gates on the same node therefore cannot both record a verdict, and a late gate can never overwrite a `passed` node.

`gf gate --final` runs the plan's integration checks and frozen promoted checks once on the current tree and appends `gate.final`. Because completion requires the final gate to be the latest verdict-like event (section 5), fixed checks run on every completed run, including runs whose nodes are all lane 1 (P11).

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

- `gf decide ask --kind K --question Q [--node N] [--check C] [--purpose P] [--command C] [--files F ...]` appends `decision.ask` and prints the id (`d<seq>`). The tool fills `submission` with the node's current submission id (or `null`). Kinds for this command: `direction`, `information`. Purpose is always `free`. Every other purpose is rejected with `bad_purpose`; review/authorization kinds require a planned gate-created question. The gate generates and rechecks the exact plan question, context and evidence before accepting a gate-owned answer.
- Record purposes are `node`, `human_check`, `lane3`, `trajectory`, `hold`, and `free`. `node` binds a planned decision; `human_check` requests a human look at a result; `lane3` asks whether to accept submitted lane-3 work after it is done; `trajectory` asks whether to accept work with an unclean path (all attempts used, timeout, or scope overrun); `hold` concerns held work; `free` is an independently asked decision. IDs repeat across runs: clients must bind answers and drafts to project, run, and decision id together.
- `gf decide wait <id> [--timeout S]` polls the log (1 second interval) until the decision is answered; exit 0 with the answer, exit 1 on timeout.
- `gf decide list` returns open decisions (for worker and reviewer roles: only those bound to their node).
- Valid outcomes: `approved`, `rejected`, `revision_requested` for kinds `review` and `authorization`; `answered` for the other two.
- An answer to a stale decision (section 5, "Basis") is refused (exit 4, `stale_decision`). A decision is answered once: a second answer is refused (exit 4, `already_answered`), and `derive` uses the first answer.

Who can answer (P10):

- The dashboard server, started by a person with `gf serve`, appends `decision.answer` with `source: "dashboard"` and `sig`: HMAC-SHA256, hex, keyed with `human.key`, over canonical JSON `[3, run_id, decision_id, outcome, answer, binding]`, prefixed `v3:`. Binding includes issuer, kind, purpose, plan_identity, node, submission, check, question, evidence, the per-run nonce, pinned key fingerprint, filesystem location, full submission binding and attachment/evidence hashes. Old unprefixed/v2 answers never authorize new execution.
- `gf decide answer` on the command line is refused (exit 3) unless the environment has `GF_HUMAN_TERMINAL=1` and stdin is a TTY. It signs the same way with `source: "terminal"`.
- `decisions.answer` itself refuses any actor whose role is not `human` (exit 3, `forbidden`), so no other entry point (the MCP server, a script) can produce a signed answer for an agent role. The dashboard server and the terminal path call it with a `human` actor.
- `state.derive` sets `verified` by recomputing the signature with `core.human_sig` (constant-time comparison); it is `false` when the key is unreadable or the signature differs. Verification recomputes the resolved project root and run directory name from the filesystem context, never from the log; signatures without that context cannot authorize work. Gate rules count only verified answers.

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

`gf trace` and MCP `run_trace` return the existing `run` and `nodes` metrics plus `human`, `stuck`, `integrity` and `conformance`. `gf trace --conformance` prints one measured observation per P1–P12; `gf --json trace --conformance` carries those same numbers under stable principle keys. These are observations of records, not a compliance verdict.

- `human.answers` contains `total`, `planned`, `unplanned`, and `by_kind`. Planned kinds are the first `plan_approval`, `decision_node`, `lane3`, and declared `human_check`; unplanned kinds are `hold`, `trajectory`, `evidence_reask`, `plan_reapproval`, other `reask`, and `free`. Repeated plan asks include re-planning, moved-project and key recovery approvals; repeated gate slots after `evidence_changed` are evidence re-asks. Counts describe recorded human activity, including answers later superseded; they do not re-authorize historical answers or authenticate unsigned execution history.
- `human.wait.decisions` records each decision's id, category, ask and answer timestamps, and `wait_ms` (null until answered). `total_ms` sums completed waits, `longest_ms` is their maximum, and `open` lists currently open, non-stale decisions. Concurrent waits are summed, not deduplicated into wall-clock elapsed time; unanswered and superseded-without-answer waits do not add to the completed total.
- `stuck` counts recorded `superseded_decisions`, gate `replan` verdicts and `unverified_at_final`. Refused commands are not logged: `refusals_recorded` is false, `refusals_by_code` is empty, and `refusals` says "not measurable from records". No refusal recording is added.
- Run-level integration/promoted commands appear under `run_cmd_checks` with the same per-command fields. Each node adds its last declared `executor` and `model` and `cmd_checks`, keyed by current check id. Each command entry reports `red_recorded`, `failure_observed`, `passed` and individual passes' `failed_before`. Failure history matches the same node and exact command across attempts; an old red record without `command` is resolved through its recorded plan revision. Missing or unverifiable historical evidence is not a failure. Passing cmd results also record `failed_before`; this never changes a gate verdict.
- P1 reports work-node cmd coverage and checks never observed failing; P2 reports the highest recorded attempt number (not the sum across reopened budgets) and replan; P3–P7 report recorded dependencies, scope declarations, assignments/reviews, deterministic results/merges and gate counts. P8/P9 report "not measurable from records": the log lacks the historical state snapshots needed to measure cross-node rejection effects or independently verify approval at each historical lane-3 pass. P10 reports answers and waits; P11 constraints; P12 trajectory and stuck counts. Corrupt event logs produce unavailable conformance observations, not a zero-activity conclusion.

`rollbacks` for a node is the number of nodes in **other** runs of the same project that own a path overlapping this node's `owns` and that were `passed` and later reopened, rejected, or replanned. It is grade 3 evidence used by gate rule R5.

## 10. Command line conventions

`python3 scripts/gf [--run PATH] [--project PATH] [--role R] [--node N] [--json] <command> [args]`

- With `--json`, stdout is exactly one JSON object: `{"ok": true, ...}` merged with the dict the module function returned, or `{"ok": false, "code": "<slug>", "message": "..."}`. Without `--json`, short human text.
- Exit codes: `0` success; `1` negative result (a check failed, a verdict other than pass, validation problems, wait timed out); `2` usage error; `3` forbidden for the role; `4` state error (unknown node, attempts exhausted, wrong status, stale); `5` lock timeout or I/O error.
- Every failure inside the library is a `GFError(code, message, exit_code=EXIT_USAGE)`; `cli.main` turns it into the output and exit code above.

### Approval integrity and execution revisions

New `run.init` records use schema version 2, `approval_required: true` (informational only), and a random `run_nonce`. Plan documents remain schema 1. All runs pin the person’s key on the first signed answer. Approval is required regardless of version or markers. The signed human-terminal recovery and upgrade rules are under [Continuing an older run](#continuing-an-older-run).

Every disk plan load verifies its bytes against the corresponding `plan.set.plan_sha256` and its structural identity against `plan_identity`. A mismatch, unreadable or missing revision refuses with `plan_tampered` (exit 4); the dashboard shows an unavailable plan with no actionable graph. Dispatch also checks the derived structural identity. Hashes are integrity checks against accidental drift, not a protected append-only store against a malicious account owner.

During a structural re-plan, running work can continue editing and submit its result, and finished results remain accepted. Checks, routing, worker briefs, merge and all gates refuse with `plan_not_approved` until the new plan is approved. They never combine preserved work with unapproved integration commands. Replanning cannot rewrite running/submitted/passed node contracts or their inputs.

`plan set` snapshots the project's promoted checks into `promoted_checks` and applicable constraints into `constraints` before computing identity. Worker briefs use that frozen constraint snapshot; planning briefs can inspect newer constraints. Promotions and retirements affect the next approved plan only; existing approvals keep their exact snapshot. The dashboard lists these commands alongside integration checks. `brief --plan` may show pending promotions for planning, but does not dispatch or execute them. Legacy runs cannot execute before re-posting their plan; that revision freezes fixed checks and constraints too.

An answered but unverified approval stays blocked and is shown separately from a sent-back plan. Return to the original key/home if it differs; ask the coordinator to re-post the plan and answer its new question. `plan set` returns `show` (and MCP's open instruction) only when that approval is open. SIGTERM and SIGHUP close the dashboard and remove only its own `server.json`.

New `plan.set` events also record `node_counts` from `plan.node_counts`, the same function used by dashboard totals. Historical events without those counts show a neutral total item count. Plan approval answers in the timeline say that the plan was authorized, rather than describing them as acceptance of a completed result.

### Approval integrity and same-account limits

Every executable plan load validates the full schema, uniqueness, dependencies and effective lanes before any CLI, brief, check, gate, MCP or dashboard use. Invalid plans fail with `plan_tampered`; the dashboard shows a warning and no executable cards. All executable node lookups share `plan.node_index` / `node_by_id`. Run-level integration checks, promoted checks and constraints are included in the structural identity.

Answer signatures bind the resolved project root path and run directory name computed at verification time. Re-pin signatures verify their recorded location for key pinning only. Moving or renaming a project directory invalidates approvals permanently when observed, even after moving back; the person approves once more after the leader re-posts the run's current plan. Copying the log and plan to another project or run cannot transfer consent. The CLI reports `project_moved`; the dashboard explains the same recovery.

For human-check, lane-3, trajectory and hold decisions, the signed question includes the complete submission (including commit) and SHA-256 hashes of the files and check evidence shown to the person. Gate and merge recheck those bindings. Changed file bytes supersede the answer and the gate re-asks on the same submission; merge refuses `approval_changed` until fresh approval. Altered signed records still refuse `approval_changed`. With worktree isolation, the recorded commit is the commit that can be merged under that approval. **Shared-tree mode cannot bind file contents beyond the recorded evidence hashes.** Unattached files, commands reading the environment, and changes after a check are not made immutable by an approval. File hashes are not a filesystem snapshot or a defense against a concurrent malicious writer.

Only the latest current plan question may authorize execution. A later structural `plan.set` revision or later send-back prevents reuse even if `decision.superseded` lines are removed. A recorded wording-only revision explicitly reuses the current approval without changing the structural identity; a revision without that reuse marker still requires approval. An identical re-post does not append `plan.set`. Log truncation or rollback of the entire run to an older, genuinely approved state is still possible: there is no external monotonic counter or tamper-proof audit log. A writer without a forged signature can delete history, falsify unsigned work/check/gate events, alter display-only wording, deny service, change unbound files, or roll back to an earlier approved contract at the same location. They cannot obtain a verified approval for a different executable contract, moved run, or changed bound submission merely by editing its logged hash, identity or fingerprint. Deleting bound questions/answers removes that binding history; unsigned work events and direct Git or shell commands are not a security boundary. Merge integrates submitted work before its final gate, so it is not proof that every result has passed human review. An adversarial file writer can also replace the program itself.

Follow the [human identity rule](../SKILL.md#human-identity). First-use pinning cannot be made safe on a shared account; a key planted before the first human answer is an accepted same-account limit. `key repin` repairs that case by generating new random bytes, which also invalidates approvals in other runs pinned to the prior global key. `setup` under an agent role and dashboard startup do not create the key. The key is created at the human answer entry point or by an explicitly human setup/re-pin.

### Display and execution consistency

`decide ask` accepts only free direction/information questions for every role; binding hold questions come from the gate. The gate alone creates `node`, `human_check`, `lane3` and `trajectory` questions from the approved plan and compares their question, context and evidence contract before using an answer. Command checks show their command, relative working directory (default `.`), finite positive timeout (default 600 seconds), `/bin/sh` shell and inherited process environment. The approved node contract also exposes dependencies, ownership, reads, outputs, lane, grade, review target/lens, maximum attempts and the shared/worktree assignment policy. Committed work always requires a project merge; assignment chooses the allowed isolation, it does not amend checks.

`--cwd` selects the tree in which checks execute (and the worker tree for start/submit). A check’s `cwd` is relative to that tree. It never changes which project must contain a submitted commit: gate ancestry and final completion always use the project owning the run. Committed attachments are read and hashed from Git blobs at the submitted commit; shared-tree attachments are read from the project and rejected if their bytes differ from the recorded hash. A final result requires each submitted commit to be merged into project HEAD and a recorded `merged_head`.

Every log reader requires each `seq` to equal its one-based line number and reports `log_sequence` with that line on mismatch. Every successful project command registers its canonical filesystem location so moved projects reappear. Dashboard answers include the displayed decision id, question/contract hash and evidence hashes; a mismatch is `stale_decision`. A structurally changed plan stays disabled until the person acknowledges the change; approved wording-only revisions retain approval.


### Permanent invalidation and recovery

A stale answer never revives. At the first transaction that observes a project move or changed evidence, append `decision.superseded` with `reason: project_moved` or `evidence_changed`. This observation is durable even when the requested action is refused; it does not change a node or discard its submission. Moving back or restoring old bytes cannot undo it. A gate re-ask supersedes every earlier open or answered decision for that node, check and purpose, across submissions. Only the latest question for a purpose can count. `decide wait` returns stale questions immediately, with the reason and a working recovery: ask a fresh free question, run the gate again, or re-post the plan.

Re-plan protection also covers a signature-verified, approving, not-superseded gate answer that still binds the node's current submission and contract. Merely answered is insufficient: rejection, send-back, declined hold and unusable approvals do not protect the node. Revise the question or contract and re-post the plan for fresh approval. When attempts are exhausted, raise `max_attempts` with a substantive revised plan or replace the node, then approve that plan. A refused `start` leaves status, submission, pending questions and the attempt count unchanged.

An approving decision node protects its entire transitive release set. To change that set, gate the approved decision, then `gf reopen <decision> --reason <reason>` and re-post the revised plan; otherwise keep running/completed contracts and add a new node. The decision card names the same transitive release set.

For an edited uncommitted file awaiting acceptance, run the gate again: it asks about current bytes on the same submission, without another attempt. Merge stays blocked until fresh consent. Altered signed records must be restored intact before proceeding. A key recovery is verified at its recorded location for pinning purposes; a later move still requires fresh plan approval but does not require another key recovery.



If a completed review protects a rejected target, reopen that review with `gf reopen <review> --reason <reason>` before re-posting the revised target plan.


### Continuing an older run

**Upgrade from 0.2.x (behaviour change): approval is always required.** No unsigned version/approval marker grants an exemption. Status, trace and dashboard remain readable, including old answers exactly as recorded. An unfinished old run refuses new dispatch/start/check/merge/gate with `plan_not_approved`. Gates for already-submitted work also wait, because they execute checks. The leader re-posts the run's own `plans/NNNN.json` with `gf plan set <run-path>/plans/NNNN.json`; one human plan approval then resumes the run, preserving unchanged running/submitted/completed work. This records a random `run.nonce` for old runs; its value is covered by the new answer signature. Reads never migrate legacy records, but observing a moved project or changed approval evidence records permanent supersession. Old unprefixed or v2 answers remain visible as unverified history and never authorize new execution; a gate that needs human consent must obtain a fresh bound answer. Questions and answers lacking the new bindings are automatically stale (`legacy_decision`), not a moved-project or connection error. After the one-time plan approval, the gate asks again for unchanged submissions without restarting a node or spending another attempt. No key re-pin is required for this upgrade.

New `run.init` events contain a random 256-bit `run_nonce` and never create or pin a human key. The first verified human answer pins the person’s key with `human.key`. A missing/rotated key or a different GF_HOME yields `human_key_mismatch` and a recovery command in CLI/dashboard. Use the original environment/key, or from the person’s own terminal run `GF_ROLE=human GF_HUMAN_TERMINAL=1 graph-flow --run <run-path> key repin`. This TTY-only command always generates a fresh random key itself (never adopts existing bytes), appends a signed `human.repin` event with a new nonce and key fingerprint, supersedes open decisions and earlier plan approvals, and asks for plan approval again. No execution resumes until that fresh approval. For an old run with no posted approval, use `plan set` first.

### Wording and later questions

A human-check `title` without a `prompt`, and human-check/decision-node `context`, can feed a question asked later; those fields remain excluded from plan identity. This is acceptable because the person sees the question and context when asked and the signed answer binds exactly that displayed text; plan approval never substitutes for the gate answer. A wording-only re-post records affected nodes/fields in `plan.set.question_wording_changed` and shows “질문에 쓰일 문구가 바뀌었어요” with the node in the dashboard revision log; already open or answered questions retain their recorded text, and the next gate uses the existing supersede-and-re-ask path (`evidence_changed`) when its request differs.

### Readable integrity failures

`status` (including the project run list), `trace`, `decide list`, their MCP equivalents, and dashboard run/project/queue reads show available records plus `integrity` entries with a code and recovery. A missing, invalid or hash/identity-mismatched plan reports `plan_tampered`: re-post the plan with `gf plan set <file>` for approval; dispatch/gates still refuse. `log_sequence` and `log_corrupt` return an unavailable snapshot with recovery to restore an intact event log from backup; conformance observations are explicitly not measurable. Existing project-move/key checks remain unchanged, with their existing recovery advice included in reads.


Dashboard question facts (attempt histories, previous review findings, current reviews, release/block lists and plan differences) are display data recomputed from records. The signed binding format is unchanged. Free-question evidence may contain `options` (`label`, `answer`), supplied by repeated `decide ask --option`; answering uses the existing `answered` outcome and never releases work by itself.


Trace nodes include `rejection_history[].checks` with `origin: run|node`, check id and title, derived from the failed gate observations and the existing rejection evidence. Dashboard attempt history uses the same attribution. R5 is unchanged: for a work node with effective lane 2, after R1–R4 are satisfied, it asks for trajectory approval when `trajectory_clean` is false or recorded cross-run rollbacks are positive. Clean means at most two attempts, no timeout in the current attempt and no loop-phase scope violation in the current attempt. Two attempts alone do not trigger R5; three do, even with a passing independent review and checks. A valid current trajectory approval satisfies that request.

The P10 text observation includes nonzero unplanned categories (for example, `unplanned 2: plan_reapproval 1, trajectory 1`), matching the existing JSON `by_kind` counts.


`check.red` and `check.result` may carry `passes_before_work: true`; new red records also include the attempt number. This is diagnostic display data and does not affect red/green results, grade, retry limits, `trajectory_clean`, approval identity or signatures.
