# Codex team harness

An opt-in coordination policy and managed-run pilot for Codex, read-only by default with explicitly bounded handoff writing. A leader assigns bounded work; execution owners hold canonical write claims; independent reviewers inspect current evidence. One project record stores decisions, instruction revisions, acknowledgements, runs and recovery state.

Runtime `0.5.6` preserves exact requested reasoning together with bounded sandbox config during recipient creation. Explicit paused-recipient repair and versioned stale-packet refresh require verified same-ID configuration and fresh owner evidence; installation performs neither transition. Runtime `0.5.5` added no-follow descendant symlink metadata, race-checked normal file/directory inventory and a pure full-claim compatibility preflight to exact management-directory ownership baselines and locked state/history consistency checks to the existing cross-tool handoff. Management ownership does not grant recipient write access. It retains the Standard request correction. It retains [exact-command permission-recovery submission](payload/team-coordination/references/diagnostics.md) for known-not-executed environment initialization failures. It includes the budget-free `0.5.0` changes. Native tool authorization, fresh independent review and ACK remain required; installing it does not refresh project contracts.

Versions `0.5.0`–`0.5.4` were reviewed locally without individual public releases. Their changes are included in `0.5.5`, the public release after `0.4.1`. Previous releases and assets remain available for recovery.

## Obtain and verify the source

Canonical source: https://github.com/oozoofrog/oozoofrog-plugin, under `tools/codex-team-harness/`.

Use the reviewed commit referenced by the [0.5.6 release](https://github.com/oozoofrog/oozoofrog-plugin/releases/tag/team-harness-v0.5.6); do not substitute an unreviewed branch head. The portable release is a source archive, with no bundled model runtime or credentials.

The release assets are `codex-team-harness-0.5.6.tar.gz` and its `.sha256` file. Download both without signing in, compare the checksum before extraction, and retain the trusted release commit and digest. A checksum authenticates bytes only when obtained through a trusted release record. Existing versioned assets must not be overwritten. Read the [Korean explanation and update procedure](https://github.com/oozoofrog/oozoofrog-plugin/blob/team-harness-v0.5.6/README.ko.md#팀-하네스-056).

```sh
/usr/bin/curl -fLO https://github.com/oozoofrog/oozoofrog-plugin/releases/download/team-harness-v0.5.6/codex-team-harness-0.5.6.tar.gz
/usr/bin/curl -fLO https://github.com/oozoofrog/oozoofrog-plugin/releases/download/team-harness-v0.5.6/codex-team-harness-0.5.6.tar.gz.sha256
shasum -a 256 -c codex-team-harness-0.5.6.tar.gz.sha256
tar -xzf codex-team-harness-0.5.6.tar.gz
cd codex-team-harness-0.5.6
```

Anonymous source download needs no GitHub account. Replace the placeholder with the trusted reviewed commit:

```sh
REF='<reviewed-commit-sha>'
/usr/bin/curl -fL -o oozoofrog-plugin-source.tar.gz "https://github.com/oozoofrog/oozoofrog-plugin/archive/$REF.tar.gz"
mkdir oozoofrog-plugin-source
tar -xzf oozoofrog-plugin-source.tar.gz --strip-components=1 -C oozoofrog-plugin-source
cd oozoofrog-plugin-source/tools/codex-team-harness
```

The source manifest is checked before installer/runner actions. A manifest from an untrusted source cannot authenticate itself; obtain the commit and source archive through a trusted review record. Download does not execute code.

The former dedicated repository/release is retained as a legacy recovery reference, not the current installation source. Migration provenance is documented in [the migration record](../../docs/team-harness-migration.md). Do not delete or overwrite the legacy repository/release as part of this migration.

## Restore on a new Mac

Use a trusted Python3.9+ interpreter from a verified vendor distribution, isolated from site packages and environment hooks. The commands below use `python3` as a placeholder for that explicitly selected interpreter. Do not use a suspect environment. Bootstrap uses only the standard library and never installs dependencies, credentials, daemons, hooks, MCP settings or security changes.

Obtain a trusted interpreter from the [official Python macOS distribution](https://www.python.org/downloads/macos/) when needed. Install the CLI through [official Codex CLI instructions](https://developers.openai.com/codex/cli), then sign in through its official login flow. Public package download itself requires no account sign-in. Never restore authentication files from another machine. Model availability depends on the current account/client. This package does not bundle an authenticated runtime or promise an exact future runtime download.

```sh
python3 -I -S -B bootstrap.py --codex-home "$HOME/.codex" --save-plan plan.json dry-run
# Review exact target paths and before/after hashes in plan.json.
python3 -I -S -B bootstrap.py --codex-home "$HOME/.codex" --plan plan.json apply
python3 -I -S -B bootstrap.py --codex-home "$HOME/.codex" doctor
```

The installer preserves unmanaged global instructions. Apply requires the fresh exact plan, rejects symlinks, unknown installed files and concurrent baseline changes, and journals original bytes before writes. For idempotence, generate a fresh plan and apply it again; changed must be0. It does not infer permission to overwrite another existing installation. Keep plan and original-byte journal local; never publish them.

```sh
python3 -I -S -B bootstrap.py --codex-home "$HOME/.codex" rollback
```

Rollback compares all affected current bytes before restoring originals; unexpected concurrent edits stop it. To restore afterward, generate a fresh plan, apply and run doctor again. Unknown generated caches are refused, not silently ignored or deleted. No native instruction hot reload is implied; verify discovery in a fresh process and obtain real current-context acknowledgements before managed work.

## Managed sample

From this verified `tools/codex-team-harness/` source directory:

```sh
python3 -I -S -B run.py harness --state /absolute/sample/.codex-team/state.json init --goal 'Inspect this sample'
python3 -I -S -B run.py harness --state /absolute/sample/.codex-team/state.json status
```

Use JSON events for register/assign/claim/ack/change/boundary/handoff/review/accept, then the managed-run command for an explicitly assigned read-only task. Role files and policy.json define responsibilities, exact model IDs, permissions and concurrency scheduling. They impose no internal token budget or fixed review-count limit. Defaults are `gpt-6-luna` support, `gpt-6.1-sol` core and `gpt-6-astra` advisor; live model/list and returned thread model must match exactly. There is no silent fallback.

The ACK hash binds policy, role text, schema and implementation. Policy changes require guarded policy_refresh with no active/uncertain runs, fresh packets and real acknowledgements. Preserve key decisions/rationale and relevant changes; do not replicate entire conversations.

## Verification and boundaries

```sh
python3 -I -S -B -m unittest discover -s tests -v
```

Tests use temporary projects and synthetic JSON-RPC fixtures. They cover stale acknowledgements, resume/compaction, conflicting canonical paths, duplicate/uncertain runs, budget-free legacy migration, exact model mismatch, current artifact reviews, installer plans, preservation and rollback. They do not prove all native clients enforce this policy or that a Mac was actually erased.

The managed-run command stays read-only; session-control handoffs can explicitly configure bounded workspace writing after exact official permission readback. Direct clients that bypass it receive advisory policy only. Registration is a provenance claim; server receipts are observations, not cryptographic model attestation. The harness has no internal budget, reservation, synthetic charge, estimated packet-size stop or fixed review-count quota. Supplied provider/client usage remains provisional, missing usage stays null, and billing is not inferred. Actual provider capacity, access restrictions and explicit user instructions remain applicable. A tiny response can still consume substantial context tokens. No repeated model comparisons are required for restoration.

## Session model control and requested handoff

Use `python3 -I -S -B run.py session-control --help` and the [session-control procedure](payload/team-coordination/references/session-control.md) for exact live model/effort inspection, explicit pending changes and next-turn verification, or a user-requested unmanaged-to-managed handoff. New recipient creation, actual packet receipt, atomic ownership transfer, source dispatch disabling and committed-revision owner ACK are separate states. The native proxy requires an authorized supplied endpoint; current native-app availability is not inferred. Runtime/provider identity remains unverified, and outside clients are not intercepted. No global installation or existing project migration occurs automatically.

For oversized packet recovery and portable checkpoint archives, see [checkpoint governance](payload/team-coordination/references/checkpoints.md). The archive is project-private and must not be committed to public source.

Requested defaults are Astra `high` for leader/design/advisor, Sol 6.1 `high` for core/reviewer and Luna 6 `medium` for support, with `normal` service mode for every role. Read [profiles](payload/team-coordination/references/profiles.md) for catalogue translation, configuration limits and the independently reversible requested-default overlay. Normal uses the selected current client protocol contract and explicitly sends `serviceTierForTurn: "default"` on each new owned idle turn, omitting persistent `serviceTier`. Priority-only or empty additional tiers do not block Standard; an unknown protocol or rejected field does. Acceptance never proves persistent tier or provider execution. Existing active contracts and native sessions are not automatically replaced or verified.

Patch0.3.1 adds [same-owner failed-review rework](payload/team-coordination/references/rework.md) without releasing claims or resetting reviews/accounting. No installed runtime or active project is automatically migrated.

## 0.5.5: purpose and completion

The harness clarifies the goal, completion criteria, owner, next action, failure cause, alternatives and verification evidence. It no longer allocates tokens or stops meaningful work because a synthetic budget, packet estimate, review count or single diagnostic cycle was exhausted.

Projects with pre-0.5 contracts need an explicit [contract migration (`contract_migrate`)](payload/team-coordination/references/migration.md), retaining exact original state bytes privately while retiring old live limits. For schema-2 projects already on 0.5 or later, use quiescent `policy_refresh` and fresh packets with real participant ACKs only when the effective contract hash differs. A project whose contract already matches needs no repeat migration. The 0.5.5 runtime change alters the effective contract; adoption remains a separate quiescent owner operation. Changed observations and properly authorized corrections use [method-bound continuation](payload/team-coordination/references/diagnostics.md), preserving every actual failure and requiring genuine current independent review before product acceptance. Fresh installation follows the plan/apply/doctor procedure above. Existing installations require a separately reviewed versioned migration or guarded rollback using the matching prior release; [roll back any profile overlay before its runtime](payload/team-coordination/references/profiles.md). Preserve user guidance, journals and unknown files; do not delete them to force installation. Generate a fresh 0.5.6 plan only after reconciliation. Installation does not migrate a project or create actual participant ACKs. Previous releases remain available for recovery.
