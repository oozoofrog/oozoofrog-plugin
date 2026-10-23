# Requested profiles and configured evidence

Leader/advisor defaults request model `gpt-6-astra`, reasoning `ultra`, and service mode `fast` as separate fields. Core remains `gpt-6.1-sol`; support remains `gpt-6-luna`. Advisor implementation is still prohibited. Do not use `ultrafast` or silently substitute a model, effort or tier.

The official model catalogue advertises tier IDs and labels. The observed Fast label maps to wire ID `priority`; resolve it from current `model/list.serviceTiers`, retaining the requested label, wire ID, catalogue hash and timestamp. Deprecated speed labels alone do not authorize a mapping.

Session control `change --service-tier fast` records a pending request; `apply-change` sends persistent `turn/start` model, effort and serviceTier at an owned idle boundary. The following controlled default turn omits all overrides; `verify` separately checks configured settings. `thread/read` lacks service-tier data. Only supported start/resume responses or exact-thread settings notifications provide configured tier observations. An owned idle resume refresh is explicit, not a native-session discovery mechanism. Missing or substituted tier blocks verification; RPC rejection, capacity and transport uncertainty never trigger fallback or automatic resend. Current provider execution remains unavailable even after configured verification.

The current native app messaging API exposes model/thinking but no tier setter or settings readback. Relayed instructions are requests, not per-session verification. Do not wake completed tasks or replay work to simulate a settings update. Active-turn settings are not changed by next-turn requests.

## Separate requested-default overlay

From a verified bundle use `run.py profile-overlay --codex-home ABS --profile REQUESTED_JSON plan`, then `apply`. The JSON schema is 1, `execution_authorized` is false, and `adoption` is `pending_explicit_owner_safe_boundary`. Leader/advisor role objects contain the three exact fields above; core/support retain their model IDs. Keep catalogue evidence distinct from configured settings.

The overlay appends a discoverable directive outside the existing managed AGENTS block, writes `team-coordination-desired-profiles.json` outside the installed skill, and uses its own `team-coordination-profile-defaults-install.json` journal. It installs future instruction defaults only. Existing project contracts and actual native session configuration remain pending explicit safe owner adoption; completed projects are not rerun. The source runtime 0.4 is separate from a currently installed 0.3 runtime.

Use `profile-overlay ... doctor` for overlay integrity. The original runtime doctor must also pass with its original contract and journal unchanged. Rollback order is mandatory: first guarded `profile-overlay ... rollback`, then the original runtime rollback. Bare legacy rollback refuses while the extra AGENTS directive is present. Concurrent edits are preserved and require reconciliation. No historical journal is rewritten; no credentials, permissions or security configuration are changed.
