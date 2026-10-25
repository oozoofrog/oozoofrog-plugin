# AGENTS.md

## Collaboration Rules
- Use the `skill-creator` workflow when creating or materially updating skills.
- Keep trigger language aligned across the standalone Skill, Plugin mirror, UI metadata, and `README.md`.
- Prefer `references/` for long guidance and keep top-level instructions lean.
- Skills intended for marketplace delivery need a Plugin manifest and marketplace entry; placing a skill in `.agents/skills/` only makes it repository-scoped. Verify the published catalog and installed skill path before reporting marketplace availability.

## Output Contract
- List changed files or directories.
- List validation commands actually executed.
- State any remaining manual follow-up or risk.

## Review Rules
- Apply checks to the changed skill/package and affected distribution surfaces. Run relevant checks once; repeat only after related changes, failures, or new evidence.
- When adding, renaming, or removing a Plugin, update the expected marketplace inventory in `scripts/tests/test_plugin_distribution.py` and run the repository distribution tests. Preserve unrelated in-progress entries and files.
- Check trigger wording consistency between both `SKILL.md` copies, both UI metadata files, and `README.md`.
- Check local links and path references for breakage, and user-visible additions against `CHANGELOG.md`.
- If a rule was missing and caused rework, update the relevant context document instead of fixing code only.
- For file-delivery validation, distinguish actual attachment from path/text delivery; correlate the final assistant turn and compare original/retrieved files when a supported read provides them.
- Keep live UI evidence, server-internal model claims, installed/enabled state, and fresh-session skill exposure separate. Do not claim the removed runtime's scan, approval, signed-stream, or receipt guarantees.
- Retired consultation packages and login profiles are user data. Do not migrate, resend, or delete them when renaming or removing a skill.
- On Windows, run Python validation with `-X utf8`; verify Unix executable bits through the Git index because Windows filesystem modes do not retain them.
- Run foreground desktop tests serially on an unlocked interactive desktop. Preserve external-input and protected-desktop failures as environmental evidence; do not weaken input guards to make a test pass.
