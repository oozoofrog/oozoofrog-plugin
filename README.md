# oozoofrog-plugin

[WinPilot](winpilot/SKILL.md) 0.5.1 migrates the existing Windows Pilot controller into this repository. Use `$winpilot` (formerly `windows-pilot`) to observe Windows apps and games with WGC/UIA and perform foreground input with a visible stop control. The Windows x64 Plugin includes MCP configuration and installs a hash-pinned self-contained runtime on first connection. Existing executable and tool names remain compatible. See [installation](docs/plugin-installation.md#winpilot) and [validation](docs/validation/winpilot.md).

[Team harness `0.5.6`](https://github.com/oozoofrog/oozoofrog-plugin/releases/tag/team-harness-v0.5.6) fixes recipient creation config merging and adds explicit same-ID paused-recipient settings repair plus versioned stale-packet refresh. Exact identity, permission, owner-evidence and canonical-byte checks remain required. Installation and project adoption are separate; no automatic load, recovery or model turn is added. See the [Korean explanation and update procedure](README.ko.md#팀-하네스-056).

Team harness `0.5.5` adds no-follow symlink inventory to the management-aware handoff baseline while retaining cross-tool handoff, strict product baselines and bounded recipient writing. It includes the locally reviewed `0.5.0`–`0.5.4` changes in one public release after `0.4.1`. Installation and project adoption remain separate operations.

The [team-harness `0.5.5` release](https://github.com/oozoofrog/oozoofrog-plugin/releases/tag/team-harness-v0.5.5) includes [exact-command permission recovery](team-coordination/references/diagnostics.md) for known-not-executed environment initialization failures. It preserves the closed result and requires ordinary command-specific tool authorization, current independent review and a fresh ACK. Installation does not refresh existing project contracts. See the [Korean explanation and update procedure](README.ko.md#팀-하네스-055).

English | [한국어](README.ko.md)

[Interface First Design](interface-first-design/SKILL.md) (`interface-first-design` 0.1.0) is a skills-only Plugin. Use when designing, implementing, or reviewing product UI, especially when explanatory prose substitutes for clear structure, visible controls, or state feedback. Applies to product screens and interactions, not agent communication or technical documentation. It preserves essential text and data while making actions and recovery visible. Distribution checks cover packaging; behavioral evaluation and live UI verification are separate. See [installation](docs/plugin-installation.md#interface-first-design). [Validation method, results and limits](docs/validation/interface-first-design.md).

Invocation: `Use $interface-first-design to design or review this product UI with visible actions, clear states, and preserved meaning.`

[Korean Product Writing](korean-product-writing/SKILL.md) edits Korean product copy while preserving facts, conditions and requested components. Its skills-only Plugin is opt-in guidance without runtime/hooks. One reused six-case regression passed after earlier failures; [validation history and limits](drafts/korean-product-writing/tests/regression-v4/results.md) remain public. Installation and automatic loading were not tested.

After installation, invoke explicitly: `Use $korean-product-writing to edit this screen’s title, description and button while preserving facts and conditions.` This is an invocation example, not a completed installation or automatic-loading test.

[Audit](audit/SKILL.md) reviews skill, repository and task instructions within the requested scope. [Choice Interview](choice-interview/SKILL.md) conducts adaptive interviews with single, multiple and text responses; its mixed-form template is included. Both are available as matching skills-only Plugins, without hooks or runtime installation.

## JEV Native stable source

The [stable native controller source](tools/jev-native/README.md) and [companion skill](jev-native/SKILL.md) are included from a pinned public commit. No binary or installed runtime is replaced. [Provenance and deferred newer revisions](docs/jev-native-source.md) distinguish source/unit verification from live desktop behavior.

## Portable personal workflows

Skills-only packages now include [Korean Travel Guidebook](korean-travel-guidebook/SKILL.md), [Obsidian Projects](obsidian-projects/SKILL.md), [Outcome Brief](outcome-brief/SKILL.md) and [Verify Work](verify-work/SKILL.md). They preserve user-selected scope and project-owned verification. The travel package includes an OFL-licensed unmodified Nanum Gothic font and fictional example; no real trip data is bundled. Machine-specific agreements and project state are omitted from the portable copies.

The [user-skill inventory](docs/user-skill-inventory.md) distinguishes current packages, external dependencies and unresolved source revisions. [The historical Korean-writing draft](drafts/korean-product-writing/STATUS.md) preserves failed trials separately from the current canonical skill.

## Team harness migration

The opt-in [team-coordination skill](team-coordination/SKILL.md) and skills-only Plugin use the public payload. The installer, managed runtime and tests live in [tools/codex-team-harness](tools/codex-team-harness/README.md). [Version 0.5.5](https://github.com/oozoofrog/oozoofrog-plugin/releases/tag/team-harness-v0.5.5) removes internal token allowances, reservations and arbitrary review/context-count stops while preserving actual permissions, provider errors, ownership, failure evidence and fresh independent review. Pre-0.5 contracts need explicit [exact-byte contract migration](tools/codex-team-harness/payload/team-coordination/references/migration.md). Existing 0.5+ schema-2 projects need quiescent `policy_refresh`, fresh packets and real ACKs only when the effective contract differs; a matching contract needs no repeat migration; the 0.5.5 runtime changes the effective contract; [changed observations/corrections](tools/codex-team-harness/payload/team-coordination/references/diagnostics.md) retain prior results and require applicable scope. Requested Normal defaults, Astra/Sol high and Luna medium reasoning, and [session model control](tools/codex-team-harness/payload/team-coordination/references/session-control.md) remain; actual availability and execution are separate evidence. Plugin installation does not install global guidance/runtime or migrate projects. See the [Korean explanation and update procedure](README.ko.md#팀-하네스-055).

Codex plugins for Swift code navigation (`swift-intelligence`), local model setup and execution (`local-ai-studio`), and macOS and browser automation with screen and system audio recording (`macpilot`).

## Local AI Studio

Use `$local-ai-studio` on an Apple Silicon Mac to generate and edit images, synthesize and transcribe speech, generate video and music, and translate English into Korean through Local AI Studio's `ai` CLI. The skill verifies and delivers the saved results. When a requested Local AI Studio or on-device model task needs LocalAIHub or a missing model, it prepares the source and only the required model group before continuing. A generic media request does not start a large installation. User-selected tools, models, storage locations, and formats take precedence.

```text
Use $local-ai-studio to transcribe this recording, save an SRT file in the specified folder, and verify the result.
Use $local-ai-studio to generate a teapot image for non-commercial evaluation and verify the PNG file.
Use $local-ai-studio to translate this English document into Korean and save it as the specified TXT file.
```

Available as a standalone skill in `local-ai-studio/` and a skills-only Plugin, version `0.2.1`, with a byte-identical skill copy. The Plugin does not bundle models, runtimes, generated media, credentials, or runner binaries. Setup checks the current source and CLI capabilities, the selected storage location, and available space before downloading only the required models. `/Volumes/eyedisk/AI` is a discovery candidate on the reference Mac, not a universal default. Qwen Image downloads require explicit user acceptance of its license. On a 24 GB Mac, run only one large generator at a time.

After setup, inspect supported commands with `ai --help`. Public LocalAIHub source and other local checkouts may expose different capabilities. `READY`, an exit code, or an `Output:` log alone does not establish output quality. Report actual file and format checks separately from preview, playback, and content review. See the [skill](local-ai-studio/SKILL.md), [LocalAIHub setup](local-ai-studio/references/setup.md), [CLI and output contracts](local-ai-studio/references/cli-workflows.md), and [Plugin installation](docs/plugin-installation.md#local-ai-studio).

## MacPilot

Use `macpilot` to observe, execute, and verify macOS app, window, menu, file, system, browser, and iOS Simulator tasks. It supports bounded simultaneous game-key holds and repeated taps, visible screen edges and a small notice during system keyboard/mouse input, per-task virtual cursors, background control, live previews, optional private APIs, and sending authorized improvement requests to Codex.

```text
Use $macpilot to perform the macOS and browser tasks, record the screen and system audio, and verify the results.
```

The source is maintained in [macpilot/](macpilot/), with a distribution copy in the [Plugin skill](plugins/macpilot/skills/macpilot/SKILL.md). Version `3.5.1` includes the Swift core, CLI and MCP implementation, task isolation, cancellation, focus control, live capture and overlays, file operations, Finder tags, CoreAudio, a Chromium extension, Safari Apple Events, and a local improvement-request queue with Codex app-server delivery. The physical OS cursor and keyboard focus remain shared resources. Support varies by app and browser; see the [workflow and backend limits](macpilot/references/workflows.md).

Version 3.5 adds `mac_analyze` for read-only native AX summaries, literal search, attribute/action metadata, UTF-16 text ranges, and app-scoped hit tests. It also reads native text bounds and line ranges. `mac_simulator` adds exact-UDID app lifecycle, PNG/video, iOSContentGroup analysis, and opt-in IndigoHID touch/gesture/button/key input through an isolated driver. Only Simulator features require Xcode and a matching runtime; see [Simulator requirements](macpilot/references/simulator.md). It does not activate or click during AX analysis. See [UI analysis and the Baepsae comparison](macpilot/references/ui-analysis.md).

Version 3.4 adds AX condition waits, scoped operation outcomes, yield on external input, opt-in action traces, and explicit reusable recipes with postconditions and replay protection. Optional image search is disabled by default; it uses VisionKit and local EmbeddingGemma 2, caches vectors, and abstains on weak or ambiguous matches. See [capability usage and limits](macpilot/references/capabilities.md).

Requires macOS 14 or later. First use downloads the pinned Universal release app and verifies executable hashes and its ad-hoc signature. Ordinary macOS control needs no Swift or Xcode installation. Explicit source development uses `scripts/build.sh`. The base controller has no Python/Node.js runtime or external SwiftPM dependencies. Optional VisionKit + EmbeddingGemma 2 image search uses an explicitly configured local Python environment and model. The Chromium extension and site access, Safari Automation, and Safari JavaScript from Apple Events require separate enablement. Use [`mac_record`](macpilot/references/recording.md) to record and inspect MP4 screen and system audio captures on macOS 15 or later. Use [`mac_browser_developer`](macpilot/references/browser-developer-settings.md) to inspect and prepare Safari or Chrome developer settings, then enable a selected setting after user approval. Sending improvement requests to Codex requires an explicitly configured destination, login, and model connection. Ordinary local control does not require a model.

Use [`mac_connection`](macpilot/references/mcp-recovery.md) to inspect server and parent process identities, permissions, and the CLI/MCP execution scope. CLI `connection-check` verifies a separate isolated MCP session without restarting existing servers or Codex. A passing probe does not establish that the current chat reconnected.

For permission setup, use `mac_permission operation=setup` with `kind=all` or CLI `permission-setup`. MacPilot opens native macOS System Settings with an 88×88pt icon-only attached guide. Drag the guide’s app icon into the permission list, or use optional auto-add from the icon’s context menu. Finder and a separate settings dashboard are not opened. The guide follows the Settings window, hides when another app becomes active, and supports per-app Automation requests. A short icon-and-hand animation demonstrates the user’s drag; it stops when the user grabs the icon and respects Reduce Motion. The user completes native authentication and final approval. See [permission setup](macpilot/references/permission-setup.md).

Use current MCP tools directly when they expose the required feature; otherwise use the skill's CLI. The Plugin does not automatically replace global skills, MCP configuration, or browser profiles. Remote publication, installation, enablement, and availability in a new session are separate checks. See the [skill](macpilot/SKILL.md), [CLI and MCP setup](macpilot/references/tools.md), [development and validation](macpilot/references/development.md), and [installation guide](docs/plugin-installation.md#macpilot).

Make changes in the source directory, then update the distribution copy with `python3 scripts/sync_skill_mirrors.py --package macpilot --write`. Binaries, build caches, screenshots, and logs are excluded from Git and the distribution copy.

## Swift Intelligence

`swift-intelligence` uses Xcode's SourceKit-LSP for read-only lookup of Swift definitions, references, implementations, types, symbols, and diagnostics. It is provided only in `plugins/swift-intelligence/` because it requires an MCP server. It does not install Python packages beyond Python 3 itself or add an external MCP binary.

## Historical validation records

Validation records for removed skills describe their state at the time. The [GPT Please validation record](docs/gptplease-transport-validation.md) does not describe a currently available feature. Read the [model policy review](docs/model-routing-review.md) and [validation record](docs/model-routing-validation.md) separately from current capabilities. `scripts/model_routing_eval.py` is an offline tool for checking existing synthetic and observed records.

## Installation

Install only the Plugins you need. These commands use the changes published in the remote marketplace.

```bash
codex plugin marketplace add oozoofrog/oozoofrog-plugin --ref main
codex plugin add swift-intelligence@oozoofrog-plugin
codex plugin add local-ai-studio@oozoofrog-plugin
codex plugin add macpilot@oozoofrog-plugin
```

See [Plugin installation](docs/plugin-installation.md) for requirements and standalone installation options.

## Validation

For versioning, verified commits, GitHub releases, and selective installation, use the [Plugin release procedure](docs/plugin-release.md).

```bash
python3 -m unittest discover -s scripts/tests -v
python3 scripts/sync_skill_mirrors.py --package local-ai-studio
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py local-ai-studio
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/local-ai-studio/skills/local-ai-studio
python3 scripts/sync_skill_mirrors.py --package macpilot
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py macpilot
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/macpilot/skills/macpilot
xcrun swift test --package-path macpilot/tool
python3 macpilot/scripts/verify_mcp.py
git diff --check
```

Repository distribution tests check Plugin manifests and the marketplace catalog. Validate remote registration and installation separately through the CLI with a separate `CODEX_HOME`, without changing existing installations or credentials. Follow the Plugin-specific validation guidance when changing Swift Intelligence. See [CHANGELOG.md](CHANGELOG.md) for the change history.
