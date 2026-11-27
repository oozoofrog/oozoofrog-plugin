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
| `model-fit-review@oozoofrog-plugin` | [Review your own past sessions to learn which Claude model and effort fit a task](plugins/model-fit-review/skills/model-fit-review/SKILL.md), with case cards, two practice rounds and optional blind replays; see [Model Fit Review](#model-fit-review). |
| `apple-app-design-audit@oozoofrog-plugin` | [Audit and improve a native Apple app's design](plugins/apple-app-design-audit/skills/apple-app-design-audit/SKILL.md) against the HIG and Liquid Glass by running the app; see [Apple App Design Audit](#apple-app-design-audit). |
| `review-moment@oozoofrog-plugin` | [Choose and implement an app-specific StoreKit review request](plugins/review-moment/skills/review-moment/SKILL.md) for iOS or macOS. |
| `wild-reading-coach-builder@oozoofrog-plugin` | [Build a personal reading coach](plugins/wild-reading-coach-builder/skills/wild-reading-coach-builder/SKILL.md) from a book or supplied excerpts. Each edition has a reading index, source references, and a private reading record. On request, the coach writes a local experiment page that shows the reader's prediction beside the result they report. |
| `fstack@oozoofrog-plugin` | [Run engineering playbooks with scoped evidence and verification](plugins/fstack/skills/fstack/SKILL.md); see [fstack](#fstack). |
| `project-wiki@oozoofrog-plugin` | [Keep a per-project Obsidian wiki of episodes, lessons and knowledge](plugins/project-wiki/skills/project-wiki/SKILL.md) that the owner and the agent improve together; see [Project Wiki](#project-wiki). |
| `korean-tech-writing@oozoofrog-plugin` | [Korean developer documents](plugins/korean-tech-writing/skills/korean-tech-writing/SKILL.md) and [PR suggestion reviews](plugins/korean-tech-writing/skills/pr-suggest/SKILL.md): Use when writing or editing Korean developer documents (specs, ADRs, READMEs, runbooks, API references, agent rule files such as CLAUDE.md, AGENTS.md and SKILL.md, code comments, commit messages, PR descriptions and review comments) so that requirement strength follows RFC 2119 and RFC 8174, sentences follow ASD-STE100 clarity principles, and facts and verification levels stay exact. 한국어 개발 문서를 쓰거나 다듬을 때 사용한다. UI 문구는 korean-product-writing을 쓰고, 문학 창작과 법률 계약 원문은 제외한다. The Plugin also includes pr-suggest, which posts an improvement to someone else's pull request as one COMMENT review of GitHub suggestions after checking that they reproduce the edit. 남의 PR에 개선안을 suggestion 묶음 리뷰로 올릴 때도 쓴다. See [installation](docs/plugin-installation.md#korean-tech-writing). |

## Examples

After installing the relevant Plugin, ask for a task within its scope. For example:

```text
Use $swift-intelligence to find the implementations and references of this Swift protocol.
Use $local-ai-studio with my existing local Whisper model to transcribe this recording and report timestamp estimates and their review status.
Use $interface-first-design to review this product screen's actions, states, and recovery paths.
Use $c4fy to map this repository's architecture with source evidence, including code structure for the components that need it.
Use $high-council-implementation to prepare an implementation prompt with the best available high-tier model for my review and choice of implementation model.
Use $apple-app-design-audit to audit this Mac app's design against the HIG and Liquid Glass, with captures.
$fstack 이 변경이 다른 기능에 영향을 주는지 확인해줘.
```

These are requests, not examples of verified results.

## Handoff

지금 작업 상태를 프로젝트 안의 `_context/handoff/<브랜치>.md`에 인계 문서로 남겨, /clear나 새 세션에서 압축 없이 이어가게 한다. "/handoff", "인계 문서 써줘", "세션 넘기기", "/clear 전에 정리", "여기까지 저장"처럼 사용자가 인계를 요청할 때 사용한다. 작업이 끝나 인계가 필요 없어지면 status를 done으로 바꾼다. 코드 커밋이나 PR 설명 작성에는 쓰지 않는다.

The Plugin writes `_context/handoff/<branch>.md` inside the project (ignored by Git by default) and, in Claude Code, registers three hooks: SessionStart injects the handoff after `/clear` and a pointer with the path and goal on a fresh start, and adds nothing on resume, fork or in T3 Code delegated threads; PreCompact and PostCompact keep compaction summaries in `_context/sessions/`. No hook interrupts a session to ask for a handoff; you decide when to write one. Stale context is not injected: a handoff older than 14 days, more than 30 commits behind, on diverged history, or written before a compaction is reduced to a pointer. Finished, detached, and deleted-branch handoffs move to `_context/sessions/`, and old summaries and archives expire. Python 3 and Git are required; there is no MCP server. In Codex only the skill is available. See [installation](docs/plugin-installation.md#handoff).

## Model Advisor

작업 설명을 받아 어떤 Claude 모델(Haiku 5.5, Sonnet 5.5, Opus 5.5, Fable 5.2)과 effort가 어울리는지 판단해 추천하고, 원하면 그 모델·effort로 띄운 서브에이전트나 백그라운드 Claude Code 세션에 지시를 넘긴다. "이 작업은 어떤 모델이 좋을까", "Opus로 충분해?", "Fable이 필요한가", "effort 올릴까?", "Sonnet 세션으로 넘겨줘", "추천 모델로 돌려줘", "이건 Haiku한테 맡겨", 큰 작업을 시작하기 전 모델·effort 선택 상담, 작업 중 결과가 부족해 모델이나 effort를 올릴지 판단할 때, 서브에이전트에 쓸 모델을 고를 때 사용한다. API 파라미터·마이그레이션 질문은 다루지 않는다. 현재 세션의 모델은 바꾸지 못하므로 그 경우 `/model`·`/effort`를 안내한다.

The skill picks a starting model and effort from the task type, applies upgrade and downgrade signals, and states its assumptions. When asked to hand off, it writes a self-contained brief and either calls a subagent with that `model` and `effort`, or starts `claude --bg --model <alias> --effort <level>` in the project folder and checks the model shown by `claude logs`. It cannot change the current session's model; it points to `/compact`, `/model` and `/effort` instead. Background handoff needs the `claude` CLI and a trusted project folder. Model guidance, prices and benchmark figures follow the claude.dev post of 2026-11-09. In Codex only the skill is available. See [installation](docs/plugin-installation.md#model-advisor).

## Model Fit Review

Review your own past Claude Code sessions to learn when Fable 5.2, Opus 5.5, Sonnet 5.5 or Haiku 5.5 (and which effort) fits a task. Builds case cards from your real episodes, runs predict-then-reveal practice rounds, and optionally runs a few blind counterfactual replays judged by another vendor. A learning loop, not a cost audit; creative or deep-analysis work is never downgraded only to save tokens. "모델 적합성 검토", "어떤 모델이 맞았는지 세션 검토", "모델 선택 감각 연습", "지난 세션으로 모델 고르기 연습", "내 작업에 어떤 모델이 맞았는지 돌아보기"에 사용한다. 지금 할 작업 하나의 모델 추천은 model-advisor를 쓴다.

The skill reads Claude Code session logs (`~/.claude/projects/*/*.jsonl`) and, when present, a read-only snapshot of a T3 Code state DB, which adds per-run model, effort and completion time. Without the DB, effort is known only where the log records it, and the report says so. Bundled standard-library Python scripts count only human messages, merge each run's messages into one distinct run, separate the reaction to a result from messages sent while the run was going, exclude session commands, and group runs into episodes. Classifier labels are used as data only after the main agent's hand labels agree at 85 % or more. Counterfactual replays (gate G1) and any change to CLAUDE.md, memory, settings or hooks (gate G2) wait for approval. You choose where the review files and the DB snapshot go; nothing is written to a fixed disk. Choosing subagent models is Claude Code–only; in Codex the scripts, cards, practice rounds and guide work without calibrated Haiku labels. See [installation](docs/plugin-installation.md#model-fit-review).

## Local AI Studio

The skills-only Plugin uses Local AI Studio or selected on-device tools on Apple Silicon. For a requested task, it prepares only missing prerequisites and model groups needed for that task. A general media request alone does not start a large installation. The Plugin does not bundle models or runtimes. Qwen Image setup requires explicit acceptance of the applicable license; check the selected model's terms and any commercial licensing before use. See [setup and license conditions](plugins/local-ai-studio/skills/local-ai-studio/references/setup.md) and [CLI workflows](plugins/local-ai-studio/skills/local-ai-studio/references/cli-workflows.md).

Local Whisper uses a separate `whisper-cli` workflow and can reuse verified weights. It does not imply native app integration. Timestamps, including experimental DTW points, are estimates and do not verify sung boundaries or authorize subtitle replacement. See the [Whisper workflow and limits](plugins/local-ai-studio/skills/local-ai-studio/references/whisper.md).

## High Council Implementation

Use when the user asks a high-tier model or a council of them to prepare an implementation prompt for review and a later user-selected implementation session. Do not use for ordinary implementation requests. The author and any council reviewers are chosen from the high-tier models the host's current tool schemas actually accept, not from a fixed vendor; an unavailable model is reported, never substituted. Agents are briefed in English and the user's instruction is translated before it is passed on; the leader session answers the user in the user's language. The full prompt is presented for review; the user chooses the implementation model and whether to start a new session. Preparing a prompt alone does not authorize implementation or session creation. See the [workflow](plugins/high-council-implementation/skills/high-council-implementation/references/workflow.md).

## fstack

[Command names and upgrade table](plugins/fstack/commands.ko.md)

Use fstack for development requests in plain Korean or English: explain code, refine an idea, compare designs, assess measurements, review changes, implement or verify a fix. 개발 저장소에서 코드 설명, 요청문 다듬기, 사용법 안내, 변경 검토와 구현 검증에 사용한다. “둘 중 뭐가 나아요?”, “이걸로 빨라졌다고 할 수 있어요?”처럼 짧은 구현 비교나 측정 질문도 포함한다.

Install `fstack@oozoofrog-plugin` alone. Describe the outcome, for example “이 변경이 다른 기능에 영향을 주는지 확인해줘.” The [entry point](plugins/fstack/skills/fstack/SKILL.md) selects the bundled procedures. You can still request a particular method. See the [package guide](plugins/fstack/README.md) for host-specific invocation and the [fresh-session evaluation](docs/validation/fstack-korean-entry.md) for known routing limits.

## Apple App Design Audit

Use when auditing or improving the design of a native SwiftUI or AppKit app for macOS, iOS, or iPadOS against Apple's Human Interface Guidelines and Liquid Glass, including toolbars, sidebars, search, empty and error states, Settings, Dark Mode, contrast, text size, and destructive actions. Reads current Apple guidance through Xcode MCP DocumentationSearch and the files bundled in Xcode. Not for web UI, cross-platform frameworks, App Store screenshots, or copy-only edits. The skills-only Plugin contains instructions only and bundles no Apple documents; it reads them from the installed Xcode. Xcode and a way to run and capture the app are required. See the [skill](plugins/apple-app-design-audit/skills/apple-app-design-audit/SKILL.md) and [validation scope](docs/validation/apple-app-design-audit.md).

## Interface First Design

Use when designing, implementing, or reviewing product UI, especially when explanatory prose substitutes for clear structure, visible controls, or state feedback. Applies to product screens and interactions, not agent communication or technical documentation. See the [skill](plugins/interface-first-design/skills/interface-first-design/SKILL.md) and [validation scope](docs/validation/interface-first-design.md).

## Refactor

Use when a user requests behavior-preserving code refactoring, SRP cleanup, clearer responsibilities or dependencies, reducing code smells under repository lint rules, or integrating SwiftLint into project builds. Not for unrelated features, behavior fixes, or formatting alone. Swift work, including analysis-only requests, requires SwiftLint diagnostics using the repository's configuration; valid diagnostics can be reused when inputs, configuration, and tool version match. If diagnostics are unavailable, report the blocker and leave the Swift work incomplete. See [Swift guidance](plugins/refactor/skills/refactor/references/swift.md), [build integration](plugins/refactor/skills/refactor/references/swiftlint-build.md), and [validation](docs/validation/refactor.md).

## C4fy

C4fy creates source-backed C1/C2/C3/C4 architecture maps with optional component-level code structure. Use it for hierarchical C4 explanations, not generic flowcharts or sequence diagrams. Node.js 18 or later generates the standalone HTML viewer. See the [model contract](plugins/c4fy/skills/c4fy/references/model.md) for evidence and scope.

## OpenAI Decisions

Call the OpenAI Decisions API directly to classify text, JSON, or images, estimate predicate probabilities, or score against an ordered rubric. Use for explicit Decisions API requests or bounded semantic judgments that benefit from measured probabilities; not for general chat or free-form extraction.

The skills-only Plugin bundles an `openai-decisions` command (Python 3) that wraps the official OpenAI CLI's `openai decisions create` for both Codex and Claude Code, and documents direct CLI calls as a fallback. Plugin installation does not register tools, provision credentials, or enable API billing. See [CLI prerequisites](plugins/openai-decisions/skills/openai-decisions/references/cli.md) and [installation](docs/plugin-installation.md#openai-decisions).

## Project Wiki

Keep a local Obsidian wiki per project so the owner and the agent both get better at working together. It records each finished request as an episode with an owner-side and an agent-side retrospective, turns repeated corrections into lessons that move from candidate to adopted to encoded, keeps project knowledge, and runs retros. It creates the vault in `_context/wiki`, seeds it from earlier Claude/Codex transcripts, T3 threads, handoff notes, agent memory and git history without reading the same source twice, and lints it. Use for "위키 만들어줘", "프로젝트 위키", "위키에 남겨줘", "이거 교훈으로 남겨줘", "교훈 정리", "위키 회고", "위키 검사", "지시를 어떻게 했어야 했나", lessons learned, an Obsidian project journal, or a retrospective of past agent work. Not for session handoff (use handoff), code or API documentation, or editing notes in an unrelated Obsidian vault.

The skill creates the vault in `_context/wiki` (git-ignored with the rest of `_context/`) with templates, Obsidian Bases dashboards and a usage page, and never overwrites a bundled file you edited. After each request the agent writes an episode note with an owner-side and an agent-side retrospective, or asks in one line whether to; no hook writes to the wiki. The agent records lesson applications and counters; you decide status changes (candidate, adopted, encoded, retired) in a retro or in fstack capture-lessons. `wiki_sources.py` finds earlier Claude Code transcripts (including git and T3 worktrees and former project paths), Codex sessions, handoff notes, agent memory and git history, prints only your own prompts, and keeps a watermark per source so a later seed reads only new material. `wiki_lint.py` checks the frontmatter schema, broken and alias-only links, embedded Bases views, Bases YAML, lesson counters, evidence paths and personal data. `wiki_guides.py` rebuilds the lists in the two guide notes from the adopted and encoded lessons. A retro proposes status changes, one list per kind, and lists the lessons that a new decision by you contradicts. Python 3 is required; Obsidian is needed only to view the vault. Bundled templates are Korean. See [installation](docs/plugin-installation.md#project-wiki).

## More documentation

- [Installation and Plugin-specific requirements](docs/plugin-installation.md)
- [Release procedure](docs/plugin-release.md) and [changelog](CHANGELOG.md)
- [Historical validation](docs/gptplease-transport-validation.md) for removed GPT Please functionality; it is not a current Plugin.

Plugin-specific references and validation records describe their own scope and limits. Historical records do not establish current availability or behavior.

## External Mac automation project

Mac desktop and iOS Simulator automation live in the independent [Mac Pilot repository](https://github.com/oozoofrog/mac-pilot), with their own marketplace and releases.
