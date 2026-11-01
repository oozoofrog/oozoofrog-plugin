# Collaboration doctor

Use doctor when collaboration requests unexpected human approval, stalls, reuses an old role packet or has uncertain message/ownership state. A doctor request inspects the existing team; it does not authorize creating diagnostic chats, replacing owners, restarting clients or migrating project contracts. Respect a human instruction to perform the work in the current chat without subagents.

## Diagnose before changing anything

The bundled command is read-only and needs Python 3.11 or later. It reads only the supplied configuration, installed app-tool policy, supported-tool snapshot and optional existing project ledger. It writes no config, task state, approvals or credentials.

```sh
python3 -I -S -B scripts/collaboration_doctor.py --app-policy /absolute/path/to/observed/codex-app-tools/.mcp.json
```

The user config defaults to `CODEX_HOME/config.toml`, or `~/.codex/config.toml`. `--config` selects an explicit file. Obtain the actual installed policy path from supported Plugin metadata or known installed context; do not guess a version or inspect private session/authentication stores. A Plugin installation check can use the official `codex plugin list --json`. The portable runtime also exposes `python3 -I -S -B run.py collaboration-doctor ...`. Its `bootstrap.py doctor` command remains a separate installation-integrity check.

When runtime evidence is needed, collect fresh bounded official `read_thread` and `wait_threads` results for the known team IDs. Preserve requested/returned identity, the actual human delegation reference, decision route, current packet acknowledgement, exact pending action if exposed, message receipts and ownership state. Do not infer a pending command from the last completed tool marker. Store private raw evidence locally, not in public source/release assets.

## Snapshot input

Pass `--snapshot /absolute/path/to/evidence.json`. Schema 1 accepts these fields; omitted sections remain unobserved. This is a **synthetic structure example**, not real team evidence:

```json
{
  "schema": 1,
  "team": {
    "leader_id": "fixture-leader",
    "coordinator_id": "fixture-origin",
    "members": [
      {"thread_id": "fixture-leader", "role": "leader"},
      {"thread_id": "fixture-core", "role": "core", "leader_id": "fixture-leader"}
    ],
    "delegation": {"thread_id": "fixture-origin", "turn_id": "fixture-turn", "message_id": "fixture-human-message"}
  },
  "reads": [],
  "waits": [],
  "deliveries": [],
  "pending_requests": []
}
```

Each `reads` entry contains `source: "codex_app.read_thread"`, `requested_thread_id` and `response` with the actual returned thread/turn data. Each `waits` entry contains `source: "codex_app.wait_threads"` and `response`. Each `deliveries` entry contains `source: "codex_app.send_message_to_thread"`, `requested_thread_id` and the actual `response` receipt. Raw MCP `content` JSON wrappers are accepted. These are operator-supplied observations, not authenticated live queries.

`pending_requests` is only for an exact request actually exposed by supported evidence: `source: "codex_app.read_thread"`, `thread_id`, `tool`, `request_id` and `state: "pending"`. If that evidence is unavailable, leave it empty. A generic `waitingOnApproval` flag does not supply it. Use `--state` only for the existing project's explicit ledger; doctor compares declared claims and uncertain producers without changing them.

## Interpret the report and recover

The JSON report separates configured tool policy, visible policy layers, actual human-message observation, message submission, current evidence and a conditional `recovery_plan`. An observed human message is not a machine decision that every requested action is authorized. The coordinator must evaluate its actual meaning and scope. A send receipt is submission, not recipient acknowledgement. `runtime_verified` remains false because these inputs do not attest loaded policy or absence of native dialogs.

Coverage lists member IDs not observed and whether project state was supplied. Plain final-text approval questions are only candidates for recipient review; quoted examples and internal leader questions must not be reported as proven human prompts. A typed human-input tool call is stronger evidence, and it still needs current task context.

| Finding | Coordinator response |
| --- | --- |
| Tool mode is `prompt` | Under the real delegation, one coordinator applies only the supported tool override and validates the semantic change. Preserve restrictions. |
| Tool mode is already `approve` | Keep it. Do not rewrite the same config as a supposed repair. Inspect the actual request, client adoption and current packet. |
| `APPROVAL_WAIT_UNATTRIBUTED` | Read current official state for the exact action. Continue other authorized work; do not guess, resubmit or treat a completed marker as the pending command. |
| `APPROVED_POLICY_PENDING_REQUEST` | Reconcile that exact existing request through an exposed supported client resolution/reload at a safe boundary. Never synthesize approval or restart an active producer. |
| Legacy packet or direct member question | Verify the current human source and any newer packet acknowledgement. Refresh only stale instructions, route the decision to the leader, then observe actual receipt. |
| Missing/duplicate team ID or mismatched response | Resolve the existing identity through supported metadata. Do not guess by title, clone a chat or send to an unverified destination. |
| Unknown message outcome | Observe/reconcile the same dispatch before another send. Preserve the original failure/receipt. |
| Overlapping owners or uncertain producer | Hold the affected scope. Use actual owner checkpoint and the existing supported release/transfer/reconciliation protocol. Never edit the ledger to hide uncertainty. |
| Model capacity failure | Preserve the requested model and distinguish capacity from permission. Do not silently substitute or create a duplicate producer. |
| Explicit restriction or observed denial | Preserve it and reconcile current authority. Do not change policy to bypass that denied action. |

Doctor is a diagnosis-and-recovery workflow, not a reason to stop at dumping JSON. The current coordinator/leader carries out eligible recovery actions through the existing supported tools under the human delegation, then collects fresh evidence. Members send findings to the leader instead of opening human input dialogs. A verified idle member waiting on an already-authorized textual confirmation can receive one grounded continuation, with exact scope and source. Check the outcome before any further dispatch.

If no supported resolution exposes a native gate or indispensable user-only access remains unavailable, retain that specific limit, defer only dependent work and continue independent work. Consolidate unavoidable user actions in the leader's report. Do not invent a response, loop on the same approval request, widen permissions or create an unrequested monitor.

CLI exit codes: `0` means no blocker found in the supplied observations (or configured policy with runtime unverified); `1` means a confirmed input/policy/ownership blocker; `2` means more evidence or coordination is needed. None means product acceptance or universal prompt suppression. Keep the report, exact commands, conditional actions actually taken and resulting receipts/ACKs in the existing task evidence.
