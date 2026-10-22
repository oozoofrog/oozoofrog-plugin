# Team harness migration

Canonical destination: `oozoofrog/oozoofrog-plugin`, `tools/codex-team-harness/`. This change is reviewed on a branch; main becomes the installation source only after merge. Before merge, use the exact reviewed commit archive and enter that subtree. The installer and runner resolve their manifest/payload relative to their own directory, so extraction under a larger repository does not change target resolution.

## Source provenance and license boundary

The source derives only from the final sanitized public `0.1.1-public.1` handoff, accepted at a safe ownership boundary. Upstream commit: `9a8f24e2b8e529e6f3dfdaac85e7e23b7a076af3`. Legacy archive SHA-256: `b983f644fa2039f3fc9ec5ab239eb470429a8770dddf4bbfe93317fea0eb41dc`.

Legacy source: https://github.com/oozoofrog/codex-team-harness

Legacy release (retained, not overwritten): https://github.com/oozoofrog/codex-team-harness/releases/tag/v0.1.1-public.1

This is the user-authorized relocation of the accepted public handoff; it supplies no new rights warranty. No new license grant is invented: neither the accepted upstream payload nor destination root selected an open-source license. Python runtime code uses the standard library; no vendored third-party code/dependency was found in this payload. Python and Codex are installed separately from their official distributors. This does not redistribute authentication, runtime binaries, personal policy variants or project state.

Migration changes are source-routing documentation, matching public skill instructions, distribution metadata/mirrors and refreshed integrity manifest. State-machine, managed-run and installer behavior are unchanged. Extra standalone/Plugin UI metadata is distribution-only; the installer retains its verified public payload. No new release is created, and the old accepted archive checksum must not be reused for the relocated source.

## Installation and recovery

Follow [the source README](../tools/codex-team-harness/README.md) for anonymous commit-archive download, dry-run plan, explicit apply, doctor, idempotent reapply and journal rollback. Installation remains a separate authorized action. The skills-only Plugin exposes guidance only, with no hooks, MCP server, automatic global AGENTS modification or runtime installation.

Preserve unmanaged instructions and exact original bytes. Keep plans/journals local. To restore after rollback, make a fresh plan from the same verified source, apply, and run doctor. Concurrent edits, unknown files and symlinks are refused. Migration verification must use a temporary Codex home, never an existing personal home.

Fresh tests and isolated installation/recovery results are reported in the PR. After push, anonymous public destination-commit archive verification is required before claiming premerge downloadable restoration. No merge, clean-Mac erase, automatic loading or universal native enforcement is implied. The legacy URL's future archival/deletion requires a separate decision after migration is proven.
