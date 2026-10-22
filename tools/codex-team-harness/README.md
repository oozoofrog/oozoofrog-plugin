# Codex team harness

An opt-in coordination policy and read-only managed-run pilot for Codex. A leader assigns bounded work; execution owners hold canonical write claims; independent reviewers inspect current evidence. One project record stores decisions, instruction revisions, acknowledgements, runs and recovery state.

Public release `0.1.1-public.1` is a sanitized portable derivative of a separately tested local0.1.1 package. It has a generic policy/guide and a plan-bound installer. Its bytes and hashes differ from that local package. It contains no machine-specific baselines, personal paths, project data, session logs or authentication. No prior repository history is imported.

## Obtain and verify the migrated source

Canonical source: https://github.com/oozoofrog/oozoofrog-plugin, under `tools/codex-team-harness/`.

This migration is reviewed through a branch/commit before merge. Destination `main` does not contain it until the PR is merged. Select the exact reviewed commit from that PR; do not substitute an unreviewed branch head. No new binary release is required.

Anonymous source download needs no GitHub account. Replace the placeholder with the trusted reviewed commit:

```sh
REF='<reviewed-commit-sha>'
/usr/bin/curl -fL -o oozoofrog-plugin-source.tar.gz "https://github.com/oozoofrog/oozoofrog-plugin/archive/$REF.tar.gz"
mkdir oozoofrog-plugin-source
tar -xzf oozoofrog-plugin-source.tar.gz --strip-components=1 -C oozoofrog-plugin-source
cd oozoofrog-plugin-source/tools/codex-team-harness
```

The source manifest is checked before installer/runner actions. A manifest from an untrusted source cannot authenticate itself; obtain the commit and source archive through a trusted review record. Download does not execute code. After merge, pin a reviewed commit on `main` in the same way.

The former dedicated repository/release is retained as a legacy recovery reference, not the current installation source. Migration provenance and unchanged-runtime scope are documented in [the migration record](../../docs/team-harness-migration.md). Do not delete or overwrite the legacy repository/release as part of this migration.

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

Use JSON events for register/assign/claim/ack/change/boundary/handoff/review/accept, then the managed-run command for an explicitly assigned read-only task. Role files and policy.json define responsibilities, exact model IDs and limits. Defaults are `gpt-6-luna` support, `gpt-6.1-sol` core and `gpt-6-astra` advisor; live model/list and returned thread model must match exactly. There is no silent fallback.

The ACK hash binds policy, role text, schema and implementation. Policy changes require guarded policy_refresh with no active/uncertain runs, fresh packets and real acknowledgements. Preserve key decisions/rationale and relevant changes; do not replicate entire conversations.

## Verification and boundaries

```sh
python3 -I -S -B -m unittest discover -s tests -v
```

Tests use temporary projects and synthetic JSON-RPC fixtures. They cover stale acknowledgements, resume/compaction, conflicting canonical paths, duplicate/uncertain runs, budgets, exact model mismatch, current artifact reviews, installer plans, preservation and rollback. They do not prove all native clients enforce this policy or that a Mac was actually erased.

The managed adapter is read-only. Direct clients that bypass it receive advisory policy only. Registration is a provenance claim; server receipts are observations, not cryptographic model attestation. Reservations are conservative planning controls, not guaranteed within-turn billing caps. The byte/4 estimate covers the explicit packet only; native injected context and exact billing are not measured separately. A tiny response can still consume substantial context tokens. No repeated model comparisons are required for restoration.
