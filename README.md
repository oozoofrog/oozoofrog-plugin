# oozoofrog-plugin

Codex and Claude Code Plugins for code navigation, desktop automation, product design, writing, and other focused workflows. Choose the Plugins that fit your work and install them individually.

English | [한국어](README.ko.md)

## Install

Register the remote marketplace, then install a Plugin. This example selects Swift Intelligence; the catalog below lists the other selectors.

```sh
codex plugin marketplace add oozoofrog/oozoofrog-plugin --ref main
codex plugin add swift-intelligence@oozoofrog-plugin
codex plugin list --json
```

For another Plugin, replace `swift-intelligence` with its name: the selector is `<plugin>@oozoofrog-plugin`, where `<plugin>` is the name you choose. To refresh an already registered Git marketplace before installing, run `codex plugin marketplace upgrade oozoofrog-plugin`.

### Claude Code

The same Plugins are available from the Claude Code marketplace in this repository, using the same `<plugin>@oozoofrog-plugin` selectors.

```sh
claude plugin marketplace add oozoofrog/oozoofrog-plugin
claude plugin install swift-intelligence@oozoofrog-plugin
claude plugin list
```

To refresh an already registered marketplace, run `claude plugin marketplace update oozoofrog-plugin`. In Claude Code, skills load by their descriptions or as `/<plugin>:<skill>`; the `$<skill>` examples below are Codex syntax. See [Claude Code](docs/plugin-installation.md#claude-code) for MCP differences.

These commands fetch the published remote marketplace, not unpublished changes in this checkout. The catalog below describes the **local checkout**, so a listed Plugin or change may not yet be published remotely. For local checkout registration, platform requirements, existing installations, and standalone options, see [Plugin installation](docs/plugin-installation.md).

A local package, remote publication, installation and enablement, skill exposure in a new chat, and verified behavior are separate states. Check each state relevant to your task; repository tests alone do not establish installation or runtime behavior.

`auto-flow` and `guided-execution` are retired; use [graph-flow](https://github.com/oozoofrog/graph-flow) for multi-step planning, delegation, and verified execution. Remove existing installations through your host's Plugin removal feature; in Codex, this also clears settings and caches. Removing marketplace entries does not uninstall existing copies; see [retirement guidance](docs/plugin-installation.md#retired-plugins).

## Choose a Plugin

Each selector ends in `@oozoofrog-plugin`. Links open the skill or its detailed documentation in this checkout.

| Plugin selector | Use it for |
| --- | --- |
| `swift-intelligence@oozoofrog-plugin` | [Semantic Swift navigation](plugins/swift-intelligence/skills/swift-intelligence/SKILL.md) using SourceKit. macOS, Xcode with Command Line Tools, and Python 3 are required; the Plugin includes MCP configuration. |
| `local-ai-studio@oozoofrog-plugin` | [Requested local AI Studio or on-device model work](plugins/local-ai-studio/skills/local-ai-studio/SKILL.md), including separate Whisper transcription and timestamp estimates on Apple Silicon. See [model setup](#local-ai-studio). |
| `jev-client@oozoofrog-plugin` | [Ask TypeSafe Jev typed questions](plugins/jev-client/skills/jev-client/SKILL.md) with the Swift `jev-client` command, and save TypeSafe or OpenAI API keys in the macOS Keychain. Build the command from [tools/jev-client](tools/jev-client/Scripts/install.sh). |
| `korean-product-writing@oozoofrog-plugin` | [Write or edit Korean product copy and guidance](plugins/korean-product-writing/skills/korean-product-writing/SKILL.md), preserving facts and conditions; excludes literary creation and legal contract texts. |
| `interface-first-design@oozoofrog-plugin` | [Design or review product screens and interactions](plugins/interface-first-design/skills/interface-first-design/SKILL.md); see [scope](#interface-first-design). |
| `winpilot@oozoofrog-plugin` | [WinPilot observes and controls Windows apps and games](plugins/winpilot/skills/winpilot/SKILL.md). The Windows x64 Plugin includes MCP configuration and installs a hash-pinned runtime on first connection. See [installation](docs/plugin-installation.md#winpilot). |
| `c4fy@oozoofrog-plugin` | [Create source-backed C4 architecture maps](plugins/c4fy/skills/c4fy/SKILL.md) as standalone HTML; see [C4fy](#c4fy). |
| `refactor@oozoofrog-plugin` | [Refactor code while preserving behavior](plugins/refactor/skills/refactor/SKILL.md), or integrate SwiftLint into project builds; see [Refactor](#refactor). |
| `high-council-implementation@oozoofrog-plugin` | [Prepare an implementation prompt with an available high-tier model, optionally reviewed by others](plugins/high-council-implementation/skills/high-council-implementation/SKILL.md), before the user chooses whether and how to start an implementation session. See [scope](#high-council-implementation). |
| `openai-decisions@oozoofrog-plugin` | [Call the OpenAI Decisions API](plugins/openai-decisions/skills/openai-decisions/SKILL.md) for text, JSON, image classification, probabilities, and rubric scores; see [scope and prerequisites](#openai-decisions). |
| `handoff@oozoofrog-plugin` | [Keep work state in a project-local handoff document](plugins/handoff/skills/handoff/SKILL.md) so a new Claude Code session continues after `/clear` without relying on compaction; see [Handoff](#handoff). |
| `model-advisor@oozoofrog-plugin` | [Recommend a Claude model and effort for a task](plugins/model-advisor/skills/model-advisor/SKILL.md), and on request hand the task to a subagent or background Claude Code session running that model; see [Model Advisor](#model-advisor). |
| `evidence-first-engineering@oozoofrog-plugin` | [Work as an evidence-first senior engineer](plugins/evidence-first-engineering/skills/evidence-first-engineering/SKILL.md): restate the goal, fix root causes, verify by running the change, and report evidence; see [Evidence-First Engineering](#evidence-first-engineering). |

## Examples

After installing the relevant Plugin, ask for a task within its scope. For example:

```text
Use $swift-intelligence to find the implementations and references of this Swift protocol.
Use $local-ai-studio with my existing local Whisper model to transcribe this recording and report timestamp estimates and their review status.
Use $interface-first-design to review this product screen's actions, states, and recovery paths.
Use $c4fy to map this repository's architecture with source evidence, including code structure for the components that need it.
Use $high-council-implementation to prepare an implementation prompt with the best available high-tier model for my review and choice of implementation model.
Use $evidence-first-engineering to fix this bug at its root cause, verify it by running the app, and report the evidence.
```

These are requests, not examples of verified results.

## Handoff

지금 작업 상태를 프로젝트 안의 `_context/handoff/<브랜치>.md`에 인계 문서로 남겨, /clear나 새 세션에서 압축 없이 이어가게 한다. "/handoff", "인계 문서 써줘", "세션 넘기기", "/clear 전에 정리", "여기까지 저장", 문맥 사용량 경고 훅이 인계를 요청할 때, 큰 작업 단위를 끝냈을 때 사용한다. 작업이 끝나 인계가 필요 없어지면 status를 done으로 바꾼다. 코드 커밋이나 PR 설명 작성에는 쓰지 않는다.

The Plugin writes `_context/handoff/<branch>.md` inside the project (ignored by Git by default) and, in Claude Code, registers four hooks: SessionStart injects the handoff after `/clear` and a short pointer on startup or resume; Stop asks for a handoff once context passes 400,000 tokens (`HANDOFF_TOKENS`), except in unattended T3 Code delegated threads; PreCompact and PostCompact keep compaction summaries in `_context/sessions/`. Stale context is not injected: a handoff older than 14 days, more than 30 commits behind, on diverged history, or written before a compaction is reduced to a pointer. Finished, detached, and deleted-branch handoffs move to `_context/sessions/`, and old summaries and archives expire. Python 3 and Git are required; there is no MCP server. In Codex only the skill is available. See [installation](docs/plugin-installation.md#handoff).

## Model Advisor

작업 설명을 받아 어떤 Claude 모델(Haiku 5.5, Sonnet 5.5, Opus 5.5, Fable 5.2)과 effort가 어울리는지 판단해 추천하고, 원하면 그 모델·effort로 띄운 서브에이전트나 백그라운드 Claude Code 세션에 지시를 넘긴다. "이 작업은 어떤 모델이 좋을까", "Opus로 충분해?", "Fable이 필요한가", "effort 올릴까?", "Sonnet 세션으로 넘겨줘", "추천 모델로 돌려줘", "이건 Haiku한테 맡겨", 큰 작업을 시작하기 전 모델·effort 선택 상담, 작업 중 결과가 부족해 모델이나 effort를 올릴지 판단할 때, 서브에이전트에 쓸 모델을 고를 때 사용한다. API 파라미터·마이그레이션 질문은 다루지 않는다. 현재 세션의 모델은 바꾸지 못하므로 그 경우 `/model`·`/effort`를 안내한다.

The skill picks a starting model and effort from the task type, applies upgrade and downgrade signals, and states its assumptions. When asked to hand off, it writes a self-contained brief and either calls a subagent with that `model` and `effort`, or starts `claude --bg --model <alias> --effort <level>` in the project folder and checks the model shown by `claude logs`. It cannot change the current session's model; it points to `/compact`, `/model` and `/effort` instead. Background handoff needs the `claude` CLI and a trusted project folder. Model guidance, prices and benchmark figures follow the claude.dev post of 2026-11-09. In Codex only the skill is available. See [installation](docs/plugin-installation.md#model-advisor).

## Local AI Studio

The skills-only Plugin uses Local AI Studio or selected on-device tools on Apple Silicon. For a requested task, it prepares only missing prerequisites and model groups needed for that task. A general media request alone does not start a large installation. The Plugin does not bundle models or runtimes. Qwen Image setup requires explicit acceptance of the applicable license; check the selected model's terms and any commercial licensing before use. See [setup and license conditions](plugins/local-ai-studio/skills/local-ai-studio/references/setup.md) and [CLI workflows](plugins/local-ai-studio/skills/local-ai-studio/references/cli-workflows.md).

Local Whisper uses a separate `whisper-cli` workflow and can reuse verified weights. It does not imply native app integration. Timestamps, including experimental DTW points, are estimates and do not verify sung boundaries or authorize subtitle replacement. See the [Whisper workflow and limits](plugins/local-ai-studio/skills/local-ai-studio/references/whisper.md).

## High Council Implementation

Use when the user asks a high-tier model or a council of them to prepare an implementation prompt for review and a later user-selected implementation session. Do not use for ordinary implementation requests. The author and any council reviewers are chosen from the high-tier models the host's current tool schemas actually accept, not from a fixed vendor; an unavailable model is reported, never substituted. Agents are briefed in English and the user's instruction is translated before it is passed on; the leader session answers the user in the user's language. The full prompt is presented for review; the user chooses the implementation model and whether to start a new session. Preparing a prompt alone does not authorize implementation or session creation. See the [workflow](plugins/high-council-implementation/skills/high-council-implementation/references/workflow.md).

## Evidence-First Engineering

Use when the user asks the agent to work as an evidence-first senior engineer on a coding task, such as proving every change by running it, restating the goal before editing, fixing the root cause instead of guarding the symptom, adding no comments or mechanical tests, and reporting goal, changes, evidence and open decisions. 실행 증거 우선, 근본 원인 수정, 주석·기계적 테스트 없는 작업 방식을 요청할 때 사용한다. Not for review-only, behavior-preserving refactoring, or quick questions. The skills-only Plugin contains instructions only. It prefers running the changed software over new tests, adds no comments, and asks before irreversible actions. Project and user instructions take precedence. See the [skill](plugins/evidence-first-engineering/skills/evidence-first-engineering/SKILL.md) and its [source](plugins/evidence-first-engineering/skills/evidence-first-engineering/references/sources.md).

## Interface First Design

Use when designing, implementing, or reviewing product UI, especially when explanatory prose substitutes for clear structure, visible controls, or state feedback. Applies to product screens and interactions, not agent communication or technical documentation. See the [skill](plugins/interface-first-design/skills/interface-first-design/SKILL.md) and [validation scope](docs/validation/interface-first-design.md).

## Refactor

Use when a user requests behavior-preserving code refactoring, SRP cleanup, clearer responsibilities or dependencies, reducing code smells under repository lint rules, or integrating SwiftLint into project builds. Not for unrelated features, behavior fixes, or formatting alone. Swift work, including analysis-only requests, requires SwiftLint diagnostics using the repository's configuration; valid diagnostics can be reused when inputs, configuration, and tool version match. If diagnostics are unavailable, report the blocker and leave the Swift work incomplete. See [Swift guidance](plugins/refactor/skills/refactor/references/swift.md), [build integration](plugins/refactor/skills/refactor/references/swiftlint-build.md), and [validation](docs/validation/refactor.md).

## C4fy

C4fy creates source-backed C1/C2/C3/C4 architecture maps with optional component-level code structure. Use it for hierarchical C4 explanations, not generic flowcharts or sequence diagrams. Node.js 18 or later generates the standalone HTML viewer. See the [model contract](plugins/c4fy/skills/c4fy/references/model.md) for evidence and scope.

## OpenAI Decisions

Call the OpenAI Decisions API directly to classify text, JSON, or images, estimate predicate probabilities, or score against an ordered rubric. Use for explicit Decisions API requests or bounded semantic judgments that benefit from measured probabilities; not for general chat or free-form extraction.

The skills-only Plugin bundles an `openai-decisions` command (Python 3) that wraps the official OpenAI CLI's `openai decisions create` for both Codex and Claude Code, and documents direct CLI calls as a fallback. Plugin installation does not register tools, provision credentials, or enable API billing. See [CLI prerequisites](plugins/openai-decisions/skills/openai-decisions/references/cli.md) and [installation](docs/plugin-installation.md#openai-decisions).

## More documentation

- [Installation and Plugin-specific requirements](docs/plugin-installation.md)
- [Release procedure](docs/plugin-release.md) and [changelog](CHANGELOG.md)
- [Historical validation](docs/gptplease-transport-validation.md) for removed GPT Please functionality; it is not a current Plugin.

Plugin-specific references and validation records describe their own scope and limits. Historical records do not establish current availability or behavior.

## External Mac automation project

Mac desktop and iOS Simulator automation live in the independent [Mac Pilot repository](https://github.com/oozoofrog/mac-pilot), with their own marketplace and releases.
