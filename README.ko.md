# oozoofrog-plugin

[리팩토링](refactor/SKILL.md) 0.2.0은 동작을 보존하면서 책임·의존 관계·코드 냄새를 정리하는 skills-only Plugin입니다. SwiftLint 빌드 통합 요청도 수행합니다. Xcode·SwiftPM 구조에 맞춰 연결하고 중복 실행·설정·오류 전파를 실제 빌드로 검증합니다. 관련 없는 기능 추가, 버그 수정, 포맷 변경만을 위한 요청에는 적용하지 않습니다. 기존 변경과 저장소 검증 규칙을 보존하며 범위가 불명확할 때만 조사 후 질문합니다. Swift 작업은 분석 전용 요청도 SwiftLint 진단을 필수로 사용합니다. 유효한 진단을 확보하지 못하면 완료로 보고하지 않습니다. 설치는 현재 요청과 저장소·환경 권한을 따릅니다. [설치](docs/plugin-installation.md#refactor) 후 새 대화에서 `$refactor` 또는 `$refactor:refactor`를 사용합니다. [리뷰와 검증 범위](docs/validation/refactor.md)를 확인하세요.

[WinPilot](winpilot/SKILL.md) 0.5.1은 기존 Windows Pilot 제어기를 이 저장소로 이관합니다. `$winpilot` 또는 `windows-pilot` 요청으로 Windows 앱·게임을 WGC·UIA로 관찰하고 화면 안내·중지 기능이 있는 전경 입력을 수행합니다. Windows x64 Plugin은 MCP 설정을 포함하고 첫 연결에서 해시를 검증한 독립 실행형 런타임을 설치합니다. 기존 실행 파일명과 도구명은 유지합니다. [설치](docs/plugin-installation.md#winpilot)와 [검증 범위](docs/validation/winpilot.md)를 확인하세요.

[English](README.md) | 한국어

[Astra Implementation Prompt](astra-implementation-prompt/SKILL.md)는 Astra Max로 구현 프롬프트를 작성해 검토하려는 명시적 요청에 사용합니다. 전체 프롬프트를 검토한 뒤 사용자가 구현 모델과 새 채팅 시작 여부를 선택합니다. 일반 구현 요청에는 적용하지 않습니다. [작업 절차](astra-implementation-prompt/references/workflow.md)를 확인하세요.

[Interface First Design](interface-first-design/SKILL.md) (`interface-first-design` 0.1.0)은 제품 UI를 설계·구현·검토할 때 사용합니다. 설명문이 화면 구조·보이는 조작·상태 피드백을 대신하는 경우에 특히 유용합니다. 기능 이름·사용자 콘텐츠·실제 데이터·오류·동의 안내는 보존합니다. 에이전트의 답변이나 기술 문서에는 적용하지 않습니다. 런타임이나 hooks가 없는 skills-only Plugin이며, 배포 검사와 행동 평가·실제 UI 검증은 구분합니다. [설치 안내](docs/plugin-installation.md#interface-first-design)를 참고하세요. [검증 결과와 한계](docs/validation/interface-first-design.md).

호출 예: `$interface-first-design으로 이 제품 UI의 구조·조작·상태를 설계하거나 검토해 주세요. 필요한 문구와 데이터의 의미는 유지해 주세요.`

[한국어 제품 글쓰기](korean-product-writing/SKILL.md)는 사실·조건·요청한 구성요소를 보존하며 제품 문구를 다듬습니다. skills-only Plugin에는 런타임이나 hooks가 없습니다. 앞선 실패 뒤 같은 6개 입력의 회귀 검사를 통과했으며 [이력과 한계](drafts/korean-product-writing/tests/regression-v4/results.md)를 보존합니다. 설치와 자동 로딩은 시험하지 않았습니다.

설치 후 호출 예: `$korean-product-writing로 이 화면의 제목·설명·버튼을 사실과 조건을 유지해 다듬어 주세요.` 실제 설치나 자동 호출을 시험했다는 뜻은 아닙니다.

## 협업 실행

[협업 실행](guided-execution/SKILL.md) (`guided-execution` 0.2.3)은 여러 단계의 프로젝트 구현·재개에서 프로젝트 분석, 최소 질문, 실제 검증과 사람의 판단을 연결하는 skills-only Plugin입니다. 일반 정보 답변, 학습 지도, 단독 리뷰, 프로젝트 조율이 필요 없는 작은 수정은 적용 대상에서 제외합니다.

새로운 여러 단계의 작업은 프로젝트 자료와 기존 결정을 먼저 확인한 뒤, 아직 정해지지 않은 중요한 우선순위·사용 흐름·범위·품질 기준에 관해 질문 1개를 먼저 합니다. 확인한 맥락과 추천안을 제시하고, 답변을 받은 뒤 해당 판단에 의존하는 구현을 시작합니다. 구현할 수 있다는 판단이나 쉽게 되돌릴 수 있다는 이유만으로 사람의 의견을 생략하지 않습니다.

관련 판단이 현재 요청이나 이전 답변에 이미 명시됐거나, 사용자가 해당 선택을 명시적으로 위임하거나 질문을 원하지 않는다고 했거나, 판단이 정해진 범위 그대로 작업을 재개할 때만 초기 질문을 생략하고 근거를 기록합니다. 초기 질문을 포함해 요청 전체에서 독립적인 선택·선호 결정은 최대 3개, 질문을 주고받는 차례는 최대 2회입니다. 실행 중의 선호·품질 검토 질문도 이 한도에 합산합니다.

기존 답변과 권한을 유지하고, 초기 판단과 목표·제약·완료 기준·허용 범위가 정해지면 `.agent-loop/<run-id>/`를 만들어 구현·검증·수정을 이어갑니다. 이미 요청한 실행에 대해 다시 시작 허락을 묻지 않습니다. 답변을 기다리는 동안에는 그 판단과 무관하고 이미 허용된 조사·준비만 계속합니다. 피드백이 바꾸는 작업과 후속 결과를 다시 검증하고, 유효한 나머지 작업은 보존합니다.

```text
$guided-execution 프로젝트와 도구·기존 선호를 확인하고, 미결정된 중요한 판단은 질문한 뒤 제 답변을 기다려주세요. 실제 검사와 상태 기록을 남기며 진행해주세요.
```

프로젝트의 실제 도구·검사와 적용 가능한 선호·교훈을 확인하고 다음 실행에 반영합니다. Python 표준 라이브러리 도구로 작업 시작, 검사 근거, 사용자 결정, 관련 작업 재검증을 기록하며 문자를 최소화한 읽기 전용 온톨로지 그래프 파이프라인을 만듭니다. 작업·에이전트 기록·검증·결정을 다른 도형으로 구분하고 계획·기록·수정 경로를 표시하며, 모바일은 세로로 배치합니다. 상세 근거는 접힌 영역에 남깁니다. 온톨로지·지식그래프 사례를 반영한 적극적인 CSS 모션과 주변 관계 강조는 연출임을 표시하고 모션 끄기와 시스템 동작 줄이기를 지원하며, 실제 상태나 실행 기록을 바꾸지 않습니다. 기존 기록 검사 명령과 schema 1은 유지합니다. 실제 작업과 권한 확인은 호스트 에이전트가 수행하며, 보고서는 실시간 제어 화면이 아닙니다. 별도 백그라운드 실행기는 포함하지 않습니다. [환경 구성과 재사용](guided-execution/references/environment.md)을 참고하세요. [설치 안내](docs/plugin-installation.md#guided-execution), [작업 환경 규약](guided-execution/references/workspace.md), [검증 범위](docs/validation/guided-execution.md)를 확인하세요.

## JEV Native 고정 소스

공개 commit으로 고정한 [네이티브 제어기 소스](tools/jev-native/README.md)와 [동반 스킬](jev-native/SKILL.md)을 포함합니다. 바이너리·기존 설치본은 교체하지 않습니다. [출처와 보류한 최신 변경](docs/jev-native-source.md)에서 소스·단위 검사와 실제 데스크톱 동작을 구분합니다.

## OpenAI Decisions

[openai-decisions](openai-decisions/SKILL.md)는 텍스트·JSON·이미지의 분류, 참/거짓 확률, 기준표 점수를 OpenAI Decisions API로 구합니다. 기존 MCP/Pi 도구 또는 공통 CLI를 사용하며, 도구가 없을 때는 공식 OpenAI CLI 직접 호출 절차를 제공합니다. skills-only Plugin 설치와 도구 등록·키 보관·API 과금 설정은 별개입니다. [설치와 실행 조건](docs/plugin-installation.md#openai-decisions)을 확인하세요.

## Local AI Studio

`$local-ai-studio`는 Apple Silicon Mac에서 Local AI Studio의 `ai` CLI로 이미지 생성·편집, 음성 합성·전사, 영상·음악 생성, 영어→한국어 번역을 실행하고 결과물을 검증·전달합니다. Local AI Studio 또는 온디바이스 모델 작업을 요청했는데 LocalAIHub나 필요한 모델이 없으면 해당 소스와 요청에 필요한 모델 그룹만 로컬에 설치한 뒤 작업을 이어갑니다. 일반 미디어 요청만으로 대용량 설치를 시작하지 않으며, 사용자가 지정한 도구·모델·저장 위치·형식을 우선합니다.

```text
$local-ai-studio로 이 녹음을 전사해 지정한 폴더에 SRT로 저장하고 결과를 확인해주세요.
$local-ai-studio로 기존 로컬 Whisper 모델을 재사용해 녹음을 전사하고, 추정 타임스탬프와 검토 상태를 알려주세요.
$local-ai-studio로 비상업적 평가용 찻주전자 이미지를 만들고 PNG 파일을 확인해주세요.
$local-ai-studio로 이 영어 문서를 한국어로 번역해 지정한 TXT 파일로 저장해주세요.
```

Standalone `local-ai-studio/`와 byte-identical skills-only Plugin `0.3.0`을 제공합니다. Plugin에 모델·런타임·생성 미디어·인증·실행기 바이너리는 포함하지 않습니다. 설치 시 현재 소스·CLI 기능, 선택한 저장 위치와 용량을 확인하고 필요한 모델만 받습니다. `/Volumes/eyedisk/AI`는 참조 Mac의 발견 후보일 뿐 보편적인 기본값이 아닙니다. Qwen Image 다운로드에는 사용자의 명시적 라이선스 동의가 필요합니다. 24 GB Mac에서는 대형 생성 모델을 한 번에 하나만 실행합니다.

버전 0.3.0에는 별도 `whisper-cli`를 사용하는 로컬 Whisper 음성 인식·전사·추정 타임스탬프 흐름도 있습니다. 검증된 모델은 이동하거나 기본 재다운로드하지 않고 재사용합니다. 이 흐름은 LocalAIHub 설치가 필요하지 않으며, 네이티브 앱의 Whisper 지원을 뜻하지 않습니다. DTW 토큰 시점은 실험적 정렬 추정값입니다. 실제 노래 시작·끝의 검증이나 기존 자막 교체 근거로 단정하지 않습니다. [Whisper 참고](local-ai-studio/references/whisper.md)를 확인하세요.

설치 후 선택한 실행기의 `ai --help` 또는 `whisper-cli --help`로 지원 명령을 확인합니다. 공개 LocalAIHub 소스와 다른 로컬 체크아웃의 기능이 다를 수 있습니다. `READY`·종료 코드·`Output:` 로그만으로 결과 품질을 주장하지 않으며 실제 파일·형식·미리보기/재생/내용 확인 여부를 구분해 전달합니다. [스킬 본문](local-ai-studio/SKILL.md), [LocalAIHub 설치](local-ai-studio/references/setup.md), [명령·출력 규칙](local-ai-studio/references/cli-workflows.md), [Plugin 설치 안내](docs/plugin-installation.md#local-ai-studio)를 참고하세요.

## Swift Intelligence

`swift-intelligence`는 Xcode의 SourceKit-LSP로 Swift 정의, 참조, 구현, 타입, 심볼 및 진단을 읽기 전용으로 조회합니다. MCP 서버가 필요한 Plugin이므로 `plugins/swift-intelligence/`에만 제공합니다. Python 3 외의 Python 패키지나 외부 MCP 바이너리를 추가로 설치하지 않습니다.

## 과거 검증 기록

제거된 스킬의 배포·실행 검증은 당시 기록으로 보존합니다. [GPT Please 검증 기록](docs/gptplease-transport-validation.md)도 현재 제공 기능이 아닙니다. [모델 정책 검토](docs/model-routing-review.md)와 [검증 기록](docs/model-routing-validation.md)은 현재 제공 기능과 구분해서 읽으세요. `scripts/model_routing_eval.py`는 기존 합성·관측 기록을 검사하는 오프라인 도구입니다.

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
python3 scripts/sync_skill_mirrors.py --package local-ai-studio
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py local-ai-studio
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/local-ai-studio/skills/local-ai-studio
git diff --check
```

Plugin manifest와 marketplace는 저장소 배포 검사로 확인합니다. 실제 원격 등록·설치는 별도 `CODEX_HOME`에서 CLI로 검증하며 기존 설치·인증을 변경하지 않습니다. Swift Intelligence를 수정할 때는 해당 Plugin의 검증 지침을 별도로 따릅니다. 변경 기록은 [CHANGELOG.md](CHANGELOG.md)에 있습니다.

## C4fy

[C4fy](c4fy/SKILL.md)는 소스 근거를 갖춘 C4 시스템 맥락·컨테이너·컴포넌트·코드 구조도를 독립 HTML로 만듭니다. 둥근 카드와 부드러운 색상을 사용하며 C1/C2/C3/C4를 확대 전환합니다. 도메인·유형·역할을 자동 분류해 색상·도형·아이콘에 적용합니다. 추론 근거와 명시적 재정의를 보존하며 노드·소스 상세, SVG·JSON 저장을 지원합니다. 일반 흐름도와 시퀀스 다이어그램은 대상이 아닙니다.

`$c4fy`로 프로젝트의 C1·C2·C3·C4 구조를 요청할 수 있습니다. C4는 컴포넌트 내부의 코드 구조를 설명할 때 선택적으로 추가합니다. 소스 근거가 있는 클래스·인터페이스·함수 등의 관계를 표시하며, 코드 데이터가 없는 기존 C1·C2·C3 모델도 그대로 사용할 수 있습니다. Archify의 제작·검증 흐름만 참고한 독립 구현이며 Archify 설치나 코드에 의존하지 않습니다. 생성에는 Node.js 18 이상이 필요하고 결과 HTML은 오프라인에서 작동합니다. ‘동작 줄이기’를 켜면 즉시 전환합니다. [모델 계약](c4fy/references/model.md)에 계층·근거·출력 범위를 정리했습니다. 이 마켓플레이스를 등록한 뒤 `codex plugin add c4fy@oozoofrog-plugin`으로 설치합니다.

## 별도 Mac 자동화 프로젝트

Mac·iOS 시뮬레이터 자동화는 [Mac Pilot](https://github.com/oozoofrog/mac-pilot)에서 설치·개발·배포합니다. 기존 Keychain·프로필·캡처와 사용자 설정은 유지합니다.
