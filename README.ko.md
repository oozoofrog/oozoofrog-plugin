# oozoofrog-plugin

[리팩토링](plugins/refactor/skills/refactor/SKILL.md) 0.2.0은 동작을 보존하면서 책임·의존 관계·코드 냄새를 정리하는 skills-only Plugin입니다. SwiftLint 빌드 통합 요청도 수행합니다. Xcode·SwiftPM 구조에 맞춰 연결하고 중복 실행·설정·오류 전파를 실제 빌드로 검증합니다. 관련 없는 기능 추가, 버그 수정, 포맷 변경만을 위한 요청에는 적용하지 않습니다. 기존 변경과 저장소 검증 규칙을 보존하며 범위가 불명확할 때만 조사 후 질문합니다. Swift 작업은 분석 전용 요청도 SwiftLint 진단을 필수로 사용합니다. 유효한 진단을 확보하지 못하면 완료로 보고하지 않습니다. 설치는 현재 요청과 저장소·환경 권한을 따릅니다. [설치](docs/plugin-installation.md#refactor) 후 새 대화에서 `$refactor` 또는 `$refactor:refactor`를 사용합니다. [리뷰와 검증 범위](docs/validation/refactor.md)를 확인하세요.

[WinPilot](plugins/winpilot/skills/winpilot/SKILL.md) 0.5.1은 기존 Windows Pilot 제어기를 이 저장소로 이관합니다. `$winpilot` 또는 `windows-pilot` 요청으로 Windows 앱·게임을 WGC·UIA로 관찰하고 화면 안내·중지 기능이 있는 전경 입력을 수행합니다. Windows x64 Plugin은 MCP 설정을 포함하고 첫 연결에서 해시를 검증한 독립 실행형 런타임을 설치합니다. 기존 실행 파일명과 도구명은 유지합니다. [설치](docs/plugin-installation.md#winpilot)와 [검증 범위](docs/validation/winpilot.md)를 확인하세요.

[English](README.md) | 한국어

[High Council Implementation](plugins/high-council-implementation/skills/high-council-implementation/SKILL.md)은 고등 모델 하나 또는 여럿(council)에게 구현 프롬프트를 작성·검토하게 하려는 명시적 요청에 사용합니다. 작성 모델과 검토 모델은 특정 제공자에 고정하지 않고, 지금 호스트 도구가 실제로 받는 고등 모델 중에서 고릅니다. 쓸 수 없는 모델은 다른 모델로 바꾸지 않고 알립니다. 에이전트에게 주는 지시는 사용자가 한국어로 요청했더라도 영어로 옮겨 전달하고, 사용자에게 하는 답은 사용자의 언어로 합니다. 전체 프롬프트를 검토한 뒤 사용자가 구현 모델과 새 세션 시작 여부를 선택합니다. 일반 구현 요청에는 적용하지 않습니다. [작업 절차](plugins/high-council-implementation/skills/high-council-implementation/references/workflow.md)를 확인하세요.

[Interface First Design](plugins/interface-first-design/skills/interface-first-design/SKILL.md) (`interface-first-design` 0.1.0)은 제품 UI를 설계·구현·검토할 때 사용합니다. 설명문이 화면 구조·보이는 조작·상태 피드백을 대신하는 경우에 특히 유용합니다. 기능 이름·사용자 콘텐츠·실제 데이터·오류·동의 안내는 보존합니다. 에이전트의 답변이나 기술 문서에는 적용하지 않습니다. 런타임이나 hooks가 없는 skills-only Plugin이며, 배포 검사와 행동 평가·실제 UI 검증은 구분합니다. [설치 안내](docs/plugin-installation.md#interface-first-design)를 참고하세요. [검증 결과와 한계](docs/validation/interface-first-design.md).

호출 예: `$interface-first-design으로 이 제품 UI의 구조·조작·상태를 설계하거나 검토해 주세요. 필요한 문구와 데이터의 의미는 유지해 주세요.`

[한국어 제품 글쓰기](plugins/korean-product-writing/skills/korean-product-writing/SKILL.md)는 사실·조건·요청한 구성요소를 보존하며 제품 문구를 다듬습니다. skills-only Plugin에는 런타임이나 hooks가 없습니다. 앞선 실패 뒤 같은 6개 입력의 회귀 검사를 통과했으며 [이력과 한계](drafts/korean-product-writing/tests/regression-v4/results.md)를 보존합니다. 설치와 자동 로딩은 시험하지 않았습니다.

설치 후 호출 예: `$korean-product-writing로 이 화면의 제목·설명·버튼을 사실과 조건을 유지해 다듬어 주세요.` 실제 설치나 자동 호출을 시험했다는 뜻은 아닙니다.

`auto-flow`와 `guided-execution`은 폐기했습니다. 여러 단계의 계획·분담·검증 작업에는 [graph-flow](https://github.com/oozoofrog/graph-flow)를 사용하세요. 기존 설치본은 호스트의 Plugin 제거 기능으로 정리하며, Codex에서는 설정과 캐시를 함께 정리합니다. Marketplace 항목 삭제만으로 설치본이 제거되지는 않습니다. [제거 안내](docs/plugin-installation.md#retired-plugins)를 참고하세요.

## Jev Client

[jev-client](plugins/jev-client/skills/jev-client/SKILL.md)는 Swift로 만든 `jev-client` 명령으로 TypeSafe Jev(System One API)에 참/거짓·선택·점수 질문을 보내고, TypeSafe와 OpenAI API 키를 macOS 키체인에 저장합니다. 명령은 `tools/jev-client/Scripts/install.sh`로 빌드해 `~/.local/bin`에 설치합니다.

## OpenAI Decisions

[openai-decisions](plugins/openai-decisions/skills/openai-decisions/SKILL.md)는 텍스트·JSON·이미지의 분류, 참/거짓 확률, 기준표 점수를 OpenAI Decisions API로 구합니다. 기존 MCP/Pi 도구 또는 공통 CLI를 사용하며, 도구가 없을 때는 공식 OpenAI CLI 직접 호출 절차를 제공합니다. skills-only Plugin 설치와 도구 등록·키 보관·API 과금 설정은 별개입니다. [설치와 실행 조건](docs/plugin-installation.md#openai-decisions)을 확인하세요.

## Local AI Studio

`$local-ai-studio`는 Apple Silicon Mac에서 Local AI Studio의 `ai` CLI로 이미지 생성·편집, 음성 합성·전사, 영상·음악 생성, 영어→한국어 번역을 실행하고 결과물을 검증·전달합니다. Local AI Studio 또는 온디바이스 모델 작업을 요청했는데 LocalAIHub나 필요한 모델이 없으면 해당 소스와 요청에 필요한 모델 그룹만 로컬에 설치한 뒤 작업을 이어갑니다. 일반 미디어 요청만으로 대용량 설치를 시작하지 않으며, 사용자가 지정한 도구·모델·저장 위치·형식을 우선합니다.

```text
$local-ai-studio로 이 녹음을 전사해 지정한 폴더에 SRT로 저장하고 결과를 확인해주세요.
$local-ai-studio로 기존 로컬 Whisper 모델을 재사용해 녹음을 전사하고, 추정 타임스탬프와 검토 상태를 알려주세요.
$local-ai-studio로 비상업적 평가용 찻주전자 이미지를 만들고 PNG 파일을 확인해주세요.
$local-ai-studio로 이 영어 문서를 한국어로 번역해 지정한 TXT 파일로 저장해주세요.
```

skills-only Plugin `0.3.0`을 제공합니다. Plugin에 모델·런타임·생성 미디어·인증·실행기 바이너리는 포함하지 않습니다. 설치 시 현재 소스·CLI 기능, 선택한 저장 위치와 용량을 확인하고 필요한 모델만 받습니다. `/Volumes/eyedisk/AI`는 참조 Mac의 발견 후보일 뿐 보편적인 기본값이 아닙니다. Qwen Image 다운로드에는 사용자의 명시적 라이선스 동의가 필요합니다. 24 GB Mac에서는 대형 생성 모델을 한 번에 하나만 실행합니다.

버전 0.3.0에는 별도 `whisper-cli`를 사용하는 로컬 Whisper 음성 인식·전사·추정 타임스탬프 흐름도 있습니다. 검증된 모델은 이동하거나 기본 재다운로드하지 않고 재사용합니다. 이 흐름은 LocalAIHub 설치가 필요하지 않으며, 네이티브 앱의 Whisper 지원을 뜻하지 않습니다. DTW 토큰 시점은 실험적 정렬 추정값입니다. 실제 노래 시작·끝의 검증이나 기존 자막 교체 근거로 단정하지 않습니다. [Whisper 참고](plugins/local-ai-studio/skills/local-ai-studio/references/whisper.md)를 확인하세요.

설치 후 선택한 실행기의 `ai --help` 또는 `whisper-cli --help`로 지원 명령을 확인합니다. 공개 LocalAIHub 소스와 다른 로컬 체크아웃의 기능이 다를 수 있습니다. `READY`·종료 코드·`Output:` 로그만으로 결과 품질을 주장하지 않으며 실제 파일·형식·미리보기/재생/내용 확인 여부를 구분해 전달합니다. [스킬 본문](plugins/local-ai-studio/skills/local-ai-studio/SKILL.md), [LocalAIHub 설치](plugins/local-ai-studio/skills/local-ai-studio/references/setup.md), [명령·출력 규칙](plugins/local-ai-studio/skills/local-ai-studio/references/cli-workflows.md), [Plugin 설치 안내](docs/plugin-installation.md#local-ai-studio)를 참고하세요.

## Swift Intelligence

`swift-intelligence`는 Xcode의 SourceKit-LSP로 Swift 정의, 참조, 구현, 타입, 심볼 및 진단을 읽기 전용으로 조회합니다. MCP 서버가 필요한 Plugin이므로 `plugins/swift-intelligence/`에만 제공합니다. Python 3 외의 Python 패키지나 외부 MCP 바이너리를 추가로 설치하지 않습니다.

## 과거 검증 기록

제거된 스킬의 배포·실행 검증은 당시 기록으로 보존합니다. [GPT Please 검증 기록](docs/gptplease-transport-validation.md)도 현재 제공 기능이 아닙니다. [모델 정책 검토](docs/model-routing-review.md)와 [검증 기록](docs/model-routing-validation.md)은 현재 제공 기능과 구분해서 읽으세요. `scripts/model_routing_eval.py`는 기존 합성·관측 기록을 검사하는 오프라인 도구입니다.

## 인계 문서

[인계 문서](plugins/handoff/skills/handoff/SKILL.md) (`handoff` 0.1.2)는 작업 상태를 프로젝트 안의 `_context/handoff/<브랜치>.md`에 남겨, Claude Code에서 `/clear`나 새 세션 뒤에도 압축에 기대지 않고 이어가게 합니다. `_context/`는 기본으로 Git에 올라가지 않습니다. Claude Code에서는 훅 3개가 함께 등록됩니다: `/clear` 뒤에는 인계 문서 전체를, 새로 시작할 때는 문서 위치와 목표만 넣고, 재개(resume)·fork와 T3 Code 위임 스레드에는 아무것도 넣지 않으며, 압축 요약을 `_context/sessions/`에 보관합니다. 어떤 훅도 인계를 쓰라고 작업을 멈추지 않습니다. 인계 문서는 사용자가 원할 때 씁니다. 14일 넘게 갱신되지 않았거나 커밋이 30개 넘게 지났거나 기록이 갈라졌거나 압축 전에 쓴 문서는 넣지 않고 위치만 알립니다. 끝난 문서와 사라진 브랜치의 문서는 보관 폴더로 옮기고, 오래된 보관본은 지웁니다. Python 3과 Git이 필요하며 MCP 서버는 없습니다. Codex에서는 스킬만 쓸 수 있습니다. [설치](docs/plugin-installation.md#handoff)를 확인하세요.

## 모델 선택

[모델 선택](plugins/model-advisor/skills/model-advisor/SKILL.md) (`model-advisor` 0.1.1)은 작업에 맞는 Claude 모델(Haiku 5.5, Sonnet 5.5, Opus 5.5, Fable 5.2)과 effort를 추천합니다. 넘겨 달라고 하면 이 대화 없이도 시작할 수 있는 지시문을 써서, 그 모델·effort로 서브에이전트를 부르거나 `claude --bg`로 백그라운드 Claude Code 세션을 띄웁니다. 띄운 뒤 `claude logs`에서 실제 모델을 확인하고 `claude attach <id>`로 여는 방법을 알려 줍니다. 현재 세션의 모델은 바꾸지 못하므로 `/compact`, `/model`, `/effort` 순서를 안내합니다. 백그라운드 세션은 `claude` CLI와 신뢰 승인을 마친 프로젝트 폴더가 필요합니다. 모델별 기준과 가격은 2026-11-09 claude.dev 글을 따릅니다. Codex에서는 스킬만 쓸 수 있습니다. [설치](docs/plugin-installation.md#model-advisor)를 확인하세요.

## fstack

[fstack](plugins/fstack/skills/fstack/SKILL.md) (`fstack` 0.1.2)은 작업 위험도에 맞춰 진행 속도와 문서 수준을 정하는 개발 방식입니다. 기본 속도는 `step`입니다. 요청 범위 안의 되돌릴 수 있는 작업은 묻지 않고 끝낸 뒤 멈추고, 다음 단계를 한 줄로 제안합니다. 사용자가 "끝까지", "자율로"처럼 명시적으로 허락하면 확인할 수 있는 종료 조건까지 이어서 진행합니다. 이 허락에 커밋은 포함되지 않습니다. 요청이나 프로젝트 규칙이 커밋하라고 할 때만 커밋하고, 그렇지 않으면 변경을 작업 트리에 남기고 보고서에 그렇게 적습니다. "A를 B와 연동되게"처럼 막연한 요청은 킥오프로 처리합니다. 요청이 가리킬 수 있는 문제 후보를 나열하고, 실무자의 용어로 요청을 다시 쓴 뒤, 코드를 쓰기 전에 질문합니다. 후보 중 하나를 추천하되 목적과 범위는 사용자가 정하므로, 목적부터 번호를 붙여 묻고 답을 기다립니다. 실행해서 가릴 수 있는 "둘 중 어느 쪽이 나은가" 질문에는 버릴 실험 코드로 측정한 결과로 답합니다. 되돌릴 수 없는 작업, 사용자가 정해야 하는 제품 판단, 승인된 문서나 프로젝트 규칙의 의미 변경 앞에서는 속도와 관계없이 멈춥니다. 문서 수준은 T0(목표·종료 조건·검증 방법), T1(실패하는 검사나 재현이 spec), T2(ID가 붙은 spec·ADR·plan) 중에서 고릅니다. AI가 내린 결정은 출처와 함께 기록하고, 확인받지 않은 결정이 5개를 넘으면 확인 단계를 권합니다. 킥오프, 설계 문서, 프로토타입, 구현, 수정, 리뷰, 자율 실행, 현황·결정 확인, 직접 설계, 회고, 마무리 playbook 11개와 원칙 12개를 담았습니다. 실질적인 작업은 독립 에이전트 두 관점이 검토합니다. 설계를 굳히기 전에 거시 관점이 설계를 보고, 동작을 바꾸는 변경을 마친 뒤 미시 관점이 계약과 코드를 확인한 다음 결과를 맞춥니다. 사소한 수정에는 에이전트를 쓰지 않습니다. 에이전트를 시작할 수 없으면 한 에이전트가 두 관점을 차례로 수행하고, 보고서에 단일 에이전트 검토였다고 적습니다. Codex에서 `codex exec --ephemeral`로 시작한 세션은 하위 에이전트를 시작하지 못해 이 방식으로 진행합니다. 이 옵션 없이 실행하면 두 관점 에이전트가 시작됩니다. 수정 제안에는 어긴 계약, 발생 조건, 증거, 결과가 있어야 하며, 고칠 것이 없는 리뷰도 정상 결과입니다. "Review this diff"처럼 일반적인 영어 diff 리뷰 요청은 호스트의 기본 코드 리뷰가 대신 처리할 수 있습니다. 평가 사례에서 fstack은 Claude Code 실행 6회 중 3회에 로드됐고, 나머지는 내장 `code-review` 스킬이 처리했습니다. fstack으로 리뷰하려면 fstack을 이름으로 부르거나, spec 또는 기록된 결정에 비춰 리뷰해 달라고 요청합니다. 지침과 표준 라이브러리만 쓰는 Python 검사 `scripts/trace.py` 하나로 이루어진 skills-only Plugin입니다. 코드 스타일은 프로젝트 관례를 따르고, 동작 보존 리팩토링은 refactor, 세션 인계는 handoff, 여러 단계 작업 관리는 graph-flow, 모델 선택은 model-advisor에 맡깁니다. 기존 코드가 무엇을 하는지 묻는 사실 질문, 한 줄 설명, 오타 같은 명확한 단일 수정에는 쓰지 않습니다. pstack(Lauren Tan, MIT), tstack(Toby Lee, MIT), dual-brain(Hanmin Kim, MIT)의 아이디어를 다시 써서 합쳤습니다. [설치](docs/plugin-installation.md#fstack), [출처](plugins/fstack/skills/fstack/references/sources.md), [라이선스 고지](plugins/fstack/skills/fstack/NOTICE.md)를 참고하세요.

## App Store 리뷰 요청

[Review Moment](plugins/review-moment/skills/review-moment/SKILL.md)는 iPhone·Mac 앱에서 사용자가 핵심 작업을 마치는 지점을 찾고 StoreKit 별점·리뷰 요청을 구현합니다.

## Apple 앱 디자인 점검

[Apple 앱 디자인 점검](plugins/apple-app-design-audit/skills/apple-app-design-audit/SKILL.md) (`apple-app-design-audit` 0.1.0)은 macOS·iOS·iPadOS용 SwiftUI·AppKit 앱의 디자인을 Apple HIG와 Liquid Glass 기준으로 점검하고 고칩니다. 실제 앱을 실행해 화면 모양·접근성 설정·창 크기·콘텐츠 상태별 캡처를 모으고, 결함마다 원인 코드와 근거 문서를 붙여 보고합니다. Apple 문서는 Xcode MCP `DocumentationSearch`와 Xcode에 들어 있는 파일에서 읽으며, 사본을 포함하지 않습니다. 웹 UI, 크로스플랫폼 프레임워크, App Store 스크린샷, 문구만 고치는 작업에는 쓰지 않습니다. 지침만 담은 skills-only Plugin입니다. [설치](docs/plugin-installation.md#apple-app-design-audit)와 [검증 범위](docs/validation/apple-app-design-audit.md)를 참고하세요.

## 야생 학습 독서 코치 만들기

[야생 학습 독서 코치 만들기](plugins/wild-reading-coach-builder/skills/wild-reading-coach-builder/SKILL.md)는 책의 PDF, EPUB, Markdown, 텍스트 또는 발췌문으로 개인 독서 코치를 만듭니다. 코치는 판본별 색인과 본문을 근거로 읽을 곳을 추천하고, 독자가 실제로 읽은 범위를 별도로 기록합니다. 독자가 요청하면 로컬 실험 페이지를 만들어, 독자가 쓴 예측과 나중에 보고한 결과를 나란히 보여 줍니다.

## 설치

필요한 Plugin만 선택해 설치합니다. 아래 명령은 해당 변경이 원격 marketplace에 반영된 뒤 사용할 수 있습니다.

```bash
codex plugin marketplace add oozoofrog/oozoofrog-plugin --ref main
codex plugin add swift-intelligence@oozoofrog-plugin
codex plugin add local-ai-studio@oozoofrog-plugin
```

Claude Code에서는 같은 저장소의 Claude marketplace를 등록하고 같은 `<plugin>@oozoofrog-plugin` 선택자로 설치합니다.

```bash
claude plugin marketplace add oozoofrog/oozoofrog-plugin
claude plugin install swift-intelligence@oozoofrog-plugin
claude plugin marketplace update oozoofrog-plugin
```

Claude Code에서는 스킬이 설명에 따라 로드되거나 `/<plugin>:<skill>`로 호출됩니다. `$<skill>` 호출은 Codex 문법입니다.

다른 Plugin의 요구 사항과 standalone 설치는 [Plugin 설치 안내](docs/plugin-installation.md)를 참고하세요.

## 검증

버전 변경·검증한 커밋·GitHub 게시·선택 설치는 [Plugin 배포 절차](docs/plugin-release.md)를 사용합니다.

```bash
python3 -m unittest discover -s scripts/tests -v
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/local-ai-studio/skills/local-ai-studio
git diff --check
```

Plugin manifest와 marketplace는 저장소 배포 검사로 확인합니다. 실제 원격 등록·설치는 별도 `CODEX_HOME`에서 CLI로 검증하며 기존 설치·인증을 변경하지 않습니다. Swift Intelligence를 수정할 때는 해당 Plugin의 검증 지침을 별도로 따릅니다. 변경 기록은 [CHANGELOG.md](CHANGELOG.md)에 있습니다.

## C4fy

[C4fy](plugins/c4fy/skills/c4fy/SKILL.md)는 소스 근거를 갖춘 C4 시스템 맥락·컨테이너·컴포넌트·코드 구조도를 독립 HTML로 만듭니다. 둥근 카드와 부드러운 색상을 사용하며 C1/C2/C3/C4를 확대 전환합니다. 도메인·유형·역할을 자동 분류해 색상·도형·아이콘에 적용합니다. 추론 근거와 명시적 재정의를 보존하며 노드·소스 상세, SVG·JSON 저장을 지원합니다. 일반 흐름도와 시퀀스 다이어그램은 대상이 아닙니다.

`$c4fy`로 프로젝트의 C1·C2·C3·C4 구조를 요청할 수 있습니다. C4는 컴포넌트 내부의 코드 구조를 설명할 때 선택적으로 추가합니다. 소스 근거가 있는 클래스·인터페이스·함수 등의 관계를 표시하며, 코드 데이터가 없는 기존 C1·C2·C3 모델도 그대로 사용할 수 있습니다. Archify의 제작·검증 흐름만 참고한 독립 구현이며 Archify 설치나 코드에 의존하지 않습니다. 생성에는 Node.js 18 이상이 필요하고 결과 HTML은 오프라인에서 작동합니다. ‘동작 줄이기’를 켜면 즉시 전환합니다. [모델 계약](plugins/c4fy/skills/c4fy/references/model.md)에 계층·근거·출력 범위를 정리했습니다. 이 마켓플레이스를 등록한 뒤 `codex plugin add c4fy@oozoofrog-plugin`으로 설치합니다.

## 별도 Mac 자동화 프로젝트

Mac·iOS 시뮬레이터 자동화는 [Mac Pilot](https://github.com/oozoofrog/mac-pilot)에서 설치·개발·배포합니다. 기존 Keychain·프로필·캡처와 사용자 설정은 유지합니다.
