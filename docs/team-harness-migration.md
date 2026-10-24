# Team harness migration

Canonical destination: `oozoofrog/oozoofrog-plugin`, `tools/codex-team-harness/`. This document records the original source relocation and subsequent changes. Release 0.5.5 includes the locally reviewed 0.5.0–0.5.4 preparations after public 0.4.1; previous releases remain preserved. For installation, updates and explicit project-contract adoption, use [the 0.5.5 source guide](../tools/codex-team-harness/README.md) and [Korean explanation](../README.ko.md#팀-하네스-055). The installer and runner resolve their manifest/payload relative to their own directory, so extraction under a larger repository does not change target resolution.

## Source provenance and license boundary

The source derives only from the final sanitized public `0.1.1-public.1` handoff, accepted at a safe ownership boundary. Upstream commit: `9a8f24e2b8e529e6f3dfdaac85e7e23b7a076af3`. Legacy archive SHA-256: `b983f644fa2039f3fc9ec5ab239eb470429a8770dddf4bbfe93317fea0eb41dc`.

Legacy source: https://github.com/oozoofrog/codex-team-harness

Legacy release (retained, not overwritten): https://github.com/oozoofrog/codex-team-harness/releases/tag/v0.1.1-public.1

This is the user-authorized relocation of the accepted public handoff; it supplies no new rights warranty. No new license grant is invented: neither the accepted upstream payload nor destination root selected an open-source license. Python runtime code uses the standard library; no vendored third-party code/dependency was found in this payload. Python and Codex are installed separately from their official distributors. This does not redistribute authentication, runtime binaries, personal policy variants or project state.

The original relocation changed source-routing documentation, matching public skill instructions, distribution metadata/mirrors and the integrity manifest, without changing state-machine, managed-run or installer behavior. Extra standalone/Plugin UI metadata is distribution-only. That relocation created no new release; later versioned releases have their own reviewed source and checksums. The old accepted archive checksum must not be reused for relocated or updated source.

## Installation and recovery

Follow [the source README](../tools/codex-team-harness/README.md) for anonymous commit-archive download, dry-run plan, explicit apply, doctor, idempotent reapply and journal rollback. Installation remains a separate authorized action. The skills-only Plugin exposes guidance only, with no hooks, MCP server, automatic global AGENTS modification or runtime installation.

Preserve unmanaged instructions and exact original bytes. Keep plans/journals local. To restore after rollback, make a fresh plan from the same verified source, apply, and run doctor. Concurrent edits, unknown files and symlinks are refused. Migration verification must use a temporary Codex home, never an existing personal home.

Fresh tests and isolated installation/recovery results are reported in the PR. After push, anonymous public destination-commit archive verification is required before claiming premerge downloadable restoration. No merge, clean-Mac erase, automatic loading or universal native enforcement is implied. The legacy URL's future archival/deletion requires a separate decision after migration is proven.

## 0.2.0 followup

The separately reviewed followup adds session model/effort control and explicit project handoff. Its [procedure](../tools/codex-team-harness/payload/team-coordination/references/session-control.md) distinguishes requested, accepted, pending, live/persisted configuration and unavailable execution telemetry. Source/mirror/manifest changes belong to this followup; the original public release remains unchanged. Global installation and existing-project adoption remain separate, checkpointed operations.

## 0.3.0 compact checkpoints

The additive checkpoint API preserves canonical history, ownership, reviews and reservation accounting while selecting an owner- and independently reviewed compact working view. Its proposal pins both the whole source-state canonical digest and target effective contract. Quiescent administrative activation can atomically migrate the policy without requiring an oversized old-packet ACK; new execution still requires fresh real packet receipts. Required evidence and ancestor approvals are copied as portable content-addressed objects. Archive verification/root restoration does not rebind old absolute task claims, establish native runtime identity, or resume work. See [the checkpoint contract](../tools/codex-team-harness/payload/team-coordination/references/checkpoints.md). Existing private overlays require a separately reviewed preservation migration; do not replace them with the generic public installer.
