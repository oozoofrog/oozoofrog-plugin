# oozoofrog-plugin

English | [한국어](README.ko.md)

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

The source is maintained in [macpilot/](macpilot/), with a distribution copy in the [Plugin skill](plugins/macpilot/skills/macpilot/SKILL.md). Version `3.5.0` includes the Swift core, CLI and MCP implementation, task isolation, cancellation, focus control, live capture and overlays, file operations, Finder tags, CoreAudio, a Chromium extension, Safari Apple Events, and a local improvement-request queue with Codex app-server delivery. The physical OS cursor and keyboard focus remain shared resources. Support varies by app and browser; see the [workflow and backend limits](macpilot/references/workflows.md).

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
