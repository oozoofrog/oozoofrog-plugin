# Review instructions

This repository is a Claude Code and Codex plugin marketplace. Each skill has one source: `plugins/<plugin>/skills/<skill>/`. Tools live in `tools/`.

When reviewing a pull request, report only defects with a concrete trigger and consequence. Skip style preferences and generic hardening.

Check in particular:

- **Secrets:** API keys never appear in command arguments, logs, error output, test fixtures with real values, or committed files. Keychain writes go through stdin.
- **Billing:** network calls to paid APIs are never retried silently. A timeout or failure is reported, not turned into a negative answer.
- **Command contract** (`jev-client`, `openai-decisions`): exit codes `2` bad request and `3` not ready send nothing; `4` means the call failed and may have been billed. The raw response stays the default output, and `--summary` keeps the same shape in both tools.
- **Distribution consistency:** a changed skill keeps its trigger wording aligned across `SKILL.md`, both Plugin manifests (`.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`), `agents/openai.yaml` and `README.md`. Adding, renaming or removing a Plugin updates both marketplace files and `scripts/tests/test_plugin_distribution.py`.
- **Changelog:** user-visible changes have a `CHANGELOG.md` entry under `Unreleased`, and version bumps match in both manifests.
- **Paths:** no machine-specific absolute paths (for example `/Users/<name>`) or symlinks inside a skill folder; local links resolve.
- **Executables:** scripts that are run directly keep mode `100755` in the Git index.
