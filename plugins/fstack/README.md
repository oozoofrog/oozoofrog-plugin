# fstack

The oozoofrog engineering workflow plugin adapts pstack 0.15.48 (Lauren Tan, MIT). Its 59 named skills and principles, 22 playbooks and two worker briefs share one installation across hosts. The existing fstack entry point selects the appropriate workflow. See the [workflow index](skills/poteto-help/SKILL.md), [model setup](skills/setup-pstack/SKILL.md), [host profiles](skills/fstack/references/host.md) and [license](LICENSE).

| Installation | Start | Resources |
| --- | --- | --- |
| Codex marketplace | Install fstack@oozoofrog-plugin and invoke $fstack:fstack | Skills and runtime resources come from the same package. In T3, use its thread, PR and worker operations where available. |
| Claude Code marketplace | Install fstack@oozoofrog-plugin and invoke /fstack:fstack | Named workers use the fstack namespace. |
| Cursor marketplace | Select fstack from this repository's Cursor marketplace, then invoke the fstack skill. | Workers, optional integrations and skills resolve from the installed plugin. |
| Skills-directory host | Retain this entire package and link the desired skill directories into the catalog. | Resolve relative resources from the physical installation path. Copying only a SKILL.md omits its dependencies. |

**Upgrade.** Refresh the configured marketplace, update fstack under its existing ID and open a new session. The former step/drive router is replaced. Existing project wiki records and numbered acceptance-criteria checks remain accessible through [fstack](skills/fstack/SKILL.md). An existing standalone pstack install can coexist. Use the fstack-qualified name to select this version. In a bare skills directory, replace only symlinks you own, never a real directory or a personal skill. Link sibling skills to the same retained checkout.

**Settings.** Setup reads prior role rules for the current host until you save a profile. Saving writes only the fstack profile. Use FSTACK_MODELS for a dedicated settings file, TMPDIR for scratch, and FSTACK_CACHE_DIR for the Bun watcher's dependency cache. Project-specific values need the same environment for setup and later calls. The package itself can be read-only. Provision optional runtimes before offline use. For statechart, provide JAVA and TLA2TOOLS or let mise provision them using its configured cache and data locations.

**Removal and rollback.** Remove fstack through the host that installed it, or remove only its owned directory links. Keep dedicated user settings and project files. To roll back, reinstall the previous package revision from your retained checkout. The prior Cursor and Claude rules still contain their previous choices.

**Benny.** [Benny](automations/benny/README.md) contains dormant setup files for Cursor Automations. Installing fstack does not register routines or provision credentials. Other hosts can use independent skills without this service.

## Architecture decision

The original skills used Cursor terms in executable steps and added a translation table to a separate Claude distribution. fstack retains one physical tree for all hosts so linked skills, role briefs and scripts have the same version. The three manifest formats point to that tree. The host profile owns tool selection and scope; the model reader and worktree inventory enforce rules that must hold outside the conversation. This avoids generated copies and requires every supported host to resolve package-relative resources from the installed source.
