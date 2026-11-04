# oozoofrog-plugin

Codex Plugins for code navigation, desktop automation, product design, writing, and other focused workflows. Choose the Plugins that fit your work and install them individually.

English | [한국어](README.ko.md)

## Install

Register the remote marketplace, then install a Plugin. This example selects Swift Intelligence; the catalog below lists the other selectors.

```sh
codex plugin marketplace add oozoofrog/oozoofrog-plugin --ref main
codex plugin add swift-intelligence@oozoofrog-plugin
codex plugin list --json
```

For another Plugin, replace `swift-intelligence` with its name: the selector is `<plugin>@oozoofrog-plugin`, where `<plugin>` is the name you choose. To refresh an already registered Git marketplace before installing, run `codex plugin marketplace upgrade oozoofrog-plugin`.

These commands fetch the published remote marketplace, not unpublished changes in this checkout. The catalog below describes the **local checkout**, so a listed Plugin or change may not yet be published remotely. For local checkout registration, platform requirements, existing installations, and standalone options, see [Plugin installation](docs/plugin-installation.md).

A local package, remote publication, installation and enablement, skill exposure in a new chat, and verified behavior are separate states. Check each state relevant to your task; repository tests alone do not establish installation or runtime behavior.

## Choose a Plugin

Each selector ends in `@oozoofrog-plugin`. Links open the skill or its detailed documentation in this checkout.

| Plugin selector | Use it for |
| --- | --- |
| `swift-intelligence@oozoofrog-plugin` | [Semantic Swift navigation](plugins/swift-intelligence/skills/swift-intelligence/SKILL.md) using SourceKit. macOS, Xcode with Command Line Tools, and Python 3 are required; the Plugin includes MCP configuration. |
| `local-ai-studio@oozoofrog-plugin` | [Requested local AI Studio or on-device model work](local-ai-studio/SKILL.md), including separate Whisper transcription and timestamp estimates on Apple Silicon. See [model setup](#local-ai-studio). |
| `macpilot@oozoofrog-plugin` | [macOS, browser, and iOS Simulator workflows](macpilot/SKILL.md), including desktop control and recording. The Plugin does not automatically register MCP; see [MacPilot](#macpilot). |
| `team-coordination@oozoofrog-plugin` | [Explicitly requested team coordination](team-coordination/SKILL.md), including tailored sidebar teams, ownership, and evidence. See [team coordination](#team-coordination). |
| `korean-travel-guidebook@oozoofrog-plugin` | [Korean HTML travel guides](korean-travel-guidebook/SKILL.md) with itinerary, accessibility, and practical travel information. |
| `obsidian-projects@oozoofrog-plugin` | [Maintain project records and links](obsidian-projects/SKILL.md) when asked to organize an Obsidian vault. |
| `outcome-brief@oozoofrog-plugin` | [Develop task briefs and completion criteria](outcome-brief/SKILL.md) when instruction coaching or a reusable brief is requested. |
| `verify-work@oozoofrog-plugin` | [Apply a project-owned evidence workflow](verify-work/SKILL.md) to repeated failures or a requested verification contract. |
| `jev-native@oozoofrog-plugin` | [Native macOS app workflows](jev-native/SKILL.md) with a virtual cursor and target preview. Its runtime and credentials are separate from the skills-only Plugin. |
| `audit@oozoofrog-plugin` | [Audit skills, AGENTS.md, and task instructions](audit/SKILL.md) for conflicting scope or unclear completion criteria. |
| `choice-interview@oozoofrog-plugin` | [Conduct an adaptive user or stakeholder interview](choice-interview/SKILL.md) when an interview is requested. |
| `korean-product-writing@oozoofrog-plugin` | [Write or edit Korean product copy and guidance](korean-product-writing/SKILL.md), preserving facts and conditions; excludes literary creation and legal contract texts. |
| `interface-first-design@oozoofrog-plugin` | [Design or review product screens and interactions](interface-first-design/SKILL.md); see [scope](#interface-first-design). |
| `winpilot@oozoofrog-plugin` | [WinPilot observes and controls Windows apps and games](winpilot/SKILL.md). The Windows x64 Plugin includes MCP configuration and installs a hash-pinned runtime on first connection. See [installation](docs/plugin-installation.md#winpilot). |
| `c4fy@oozoofrog-plugin` | [Create source-backed C4 architecture maps](c4fy/SKILL.md) as standalone HTML; see [C4fy](#c4fy). |
| `refactor@oozoofrog-plugin` | [Refactor code while preserving behavior](refactor/SKILL.md), or integrate SwiftLint into project builds; see [Refactor](#refactor). |
| `astra-implementation-prompt@oozoofrog-plugin` | [Prepare an implementation prompt with Astra Max for review](astra-implementation-prompt/SKILL.md), before the user chooses whether and how to start an implementation chat. See [scope](#astra-implementation-prompt). |

## Examples

After installing the relevant Plugin, ask for a task within its scope. For example:

```text
Use $swift-intelligence to find the implementations and references of this Swift protocol.
Use $local-ai-studio with my existing local Whisper model to transcribe this recording and report timestamp estimates and their review status.
Use $interface-first-design to review this product screen's actions, states, and recovery paths.
Use $c4fy to map this repository's architecture with source evidence, including code structure for the components that need it.
Use $astra-implementation-prompt to prepare an implementation prompt with Astra Max for my review and choice of implementation model.
```

These are requests, not examples of verified results.

## Local AI Studio

The skills-only Plugin uses Local AI Studio or selected on-device tools on Apple Silicon. For a requested task, it prepares only missing prerequisites and model groups needed for that task. A general media request alone does not start a large installation. The Plugin does not bundle models or runtimes. Qwen Image setup requires explicit acceptance of the applicable license; check the selected model's terms and any commercial licensing before use. See [setup and license conditions](local-ai-studio/references/setup.md) and [CLI workflows](local-ai-studio/references/cli-workflows.md).

Local Whisper uses a separate `whisper-cli` workflow and can reuse verified weights. It does not imply native app integration. Timestamps, including experimental DTW points, are estimates and do not verify sung boundaries or authorize subtitle replacement. See the [Whisper workflow and limits](local-ai-studio/references/whisper.md).

## MacPilot

This checkout's Plugin manifest and pinned Apple silicon-only runtime asset specify version `3.7.0`. MacPilot requires an Apple silicon Mac with macOS 14 or later; screen and system audio recording requires macOS 15 or later, and Simulator workflows require Xcode and a matching runtime. The Plugin includes CLI and MCP implementations but does not automatically register an MCP server. See [installation](docs/plugin-installation.md#macpilot), [CLI and MCP setup](macpilot/references/tools.md), and [workflow limits](macpilot/references/workflows.md).

During global keyboard or mouse input, MacPilot displays screen-edge effects and a small notice. Input Monitoring detects other input sources; user input or loss of monitoring interrupts the task. Resume requires an explicit request and a fresh observation. See [capabilities](macpilot/references/capabilities.md). Unknown or uncertain action delivery does not authorize automatic replay; see the [delivery contract](macpilot/references/delivery-contract.md).

## Team coordination

Team coordination is opt-in. It prefers direct work and reuse of an existing team; new sidebar chats require an explicit request and a concrete benefit. A separate Astra bootstrap is optional. Installing the Plugin does not create chats, install the global harness, or adopt existing project contracts. See [sidebar startup](team-coordination/references/sidebar-startup.md).

Version 0.6.1 adds [adaptive collaboration](team-coordination/references/adaptive-collaboration.md) guidance based on observed outcomes; it does not automatically route models or establish adoption by an active team. For stalls, use [collaboration doctor](team-coordination/references/doctor.md). See the [team harness guide](tools/codex-team-harness/README.md) and [Korean update procedures](README.ko.md#팀-하네스-055) for setup, migration, and recovery.

## Astra Implementation Prompt

Use when the user asks Astra Max to prepare an implementation prompt for review and a later user-selected implementation chat. Do not use for ordinary implementation requests. The full prompt is presented for review; the user chooses the implementation model and whether to start a new chat. Preparing a prompt alone does not authorize implementation or chat creation. See the [workflow](astra-implementation-prompt/references/workflow.md).

## Interface First Design

Use when designing, implementing, or reviewing product UI, especially when explanatory prose substitutes for clear structure, visible controls, or state feedback. Applies to product screens and interactions, not agent communication or technical documentation. See the [skill](interface-first-design/SKILL.md) and [validation scope](docs/validation/interface-first-design.md).

## Refactor

Use when a user requests behavior-preserving code refactoring, SRP cleanup, clearer responsibilities or dependencies, reducing code smells under repository lint rules, or integrating SwiftLint into project builds. Not for unrelated features, behavior fixes, or formatting alone. Swift work, including analysis-only requests, requires SwiftLint diagnostics using the repository's configuration; valid diagnostics can be reused when inputs, configuration, and tool version match. If diagnostics are unavailable, report the blocker and leave the Swift work incomplete. See [Swift guidance](refactor/references/swift.md), [build integration](refactor/references/swiftlint-build.md), and [validation](docs/validation/refactor.md).

## C4fy

C4fy creates source-backed C1/C2/C3/C4 architecture maps with optional component-level code structure. Use it for hierarchical C4 explanations, not generic flowcharts or sequence diagrams. Node.js 18 or later generates the standalone HTML viewer. See the [model contract](c4fy/references/model.md) for evidence and scope.

## More documentation

- [Installation and Plugin-specific requirements](docs/plugin-installation.md)
- [Release procedure](docs/plugin-release.md) and [changelog](CHANGELOG.md)
- [Team harness installation and recovery](tools/codex-team-harness/README.md)
- [JEV Native source and provenance](docs/jev-native-source.md)
- [Historical validation](docs/gptplease-transport-validation.md) for removed GPT Please functionality; it is not a current Plugin.

Plugin-specific references and validation records describe their own scope and limits. Historical records do not establish current availability or behavior.
