# Implementation contracts

These module signatures and dashboard view shapes are for plugin maintainers.

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
def human_sig(run_id, decision_id, outcome, answer_text, decision=None): ...   # HMAC-SHA256 hex with $GF_HOME/human.key (section 7), or None when the key is unreadable

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
def verify(run_id, decision_id, answer_data, decision=None): ...   # bool; compares answer_data["sig"] with core.human_sig
def ensure_key(actor=None, fresh=False): ...    # human-only; fresh always replaces the key (mode 0600)

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

The MCP tool list and the dashboard's HTTP API are specified by the units that own `mcp.py` and `server.py`, in `skills/graph-flow/references/mcp.md` and `skills/graph-flow/references/dashboard.md`; both call only the functions above.

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

The dashboard HTTP contract and fixed public static allowlist are in [dashboard.md](../skills/graph-flow/references/dashboard.md#get-staticname). Only those GET static requests skip token authentication; every request still needs the loopback Host check, and all APIs still require the token.

The dashboard view also exposes `plan_approval` (id/status/outcome/answer/verified/question/plan_identity; null values when no approval has been posted), `plan_counts` (work nodes, declared checks including integration, scheduled human questions excluding this approval), and node `planned_checks`/`deliverables`. Planned question counts exclude unforeseen free questions and retry approvals. The timeline includes plan set, approval asked, answer text and superseded events.

This protects against mistakes and drift, not against an agent that deliberately forges on the same OS account. Such an agent can impersonate the human terminal or rewrite the log and key fingerprint; a genuine security boundary requires a separate identity or external signing authority.


## Reader and trace additions

`store.snapshot(run_dir)` returns `(plan_or_none, events, derived)` for reader commands, attaching `derived.run.integrity` recovery entries when the plan or log is unavailable. It uses the existing transaction/invalidation path without changing refusal persistence. The dashboard view exposes this list as `integrity`; `trace` remains available on `/api/run` even when the plan cannot be verified.

A `planned` timeline row also carries `wording_only` and `question_wording_changed` (node/title/fields entries). The log renderer uses those entries for the wording-revision message. `run_trace` accepts optional `conformance`; its JSON always includes the observations documented in the [record contract](../skills/graph-flow/references/records.md#9-trace-p12).
