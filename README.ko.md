# oozoofrog-plugin

[WinPilot](winpilot/SKILL.md) 0.5.1은 기존 Windows Pilot 제어기를 이 저장소로 이관합니다. `$winpilot` 또는 `windows-pilot` 요청으로 Windows 앱·게임을 WGC·UIA로 관찰하고 화면 안내·중지 기능이 있는 전경 입력을 수행합니다. Windows x64 Plugin은 MCP 설정을 포함하고 첫 연결에서 해시를 검증한 독립 실행형 런타임을 설치합니다. 기존 실행 파일명과 도구명은 유지합니다. [설치](docs/plugin-installation.md#winpilot)와 [검증 범위](docs/validation/winpilot.md)를 확인하세요.

팀 하네스 [`0.5.6`](https://github.com/oozoofrog/oozoofrog-plugin/releases/tag/team-harness-v0.5.6)은 수신 세션을 만들 때 추론·샌드박스 설정을 함께 보존합니다. 같은 수신자의 일시 중지 상태 복구와 오래된 인계 패킷 갱신을 명시적으로 수행할 수 있습니다. 세션 식별자·권한·담당자 근거·원본 상태 바이트를 검증해야 하며, 설치만으로 복구나 프로젝트 계약 반영이 실행되지는 않습니다.

팀 하네스 `0.5.5`는 관리 디렉터리 인계 기준선에 심볼릭 링크를 따라가지 않는 메타데이터 기록과 전체 소유 경로의 읽기 전용 사전 점검을 추가합니다. 제품 파일 기준선과 새 세션의 제한된 쓰기 범위, Standard 명시 요청 수정은 유지합니다. 로컬에서 검토한 `0.5.0`~`0.5.4`의 변경을 `0.4.1` 다음 공개 릴리스에 함께 담았습니다. 설치와 프로젝트 계약 반영은 각각 진행해야 합니다.

팀 하네스 [`0.5.5` 릴리스](https://github.com/oozoofrog/oozoofrog-plugin/releases/tag/team-harness-v0.5.5)는 환경 초기화 실패로 실행되지 않은 관찰에 [동일 명령의 권한 검토 제출](team-coordination/references/diagnostics.md)을 허용합니다. 기존 종료·실패 기록과 담당 범위를 유지하며, 일반 도구의 명령별 권한 검토와 최신 독립 검토·ACK가 필요합니다. 설치만으로 기존 프로젝트 계약을 갱신하지 않습니다.

[English](README.md) | 한국어

[Interface First Design](interface-first-design/SKILL.md) (`interface-first-design` 0.1.0)은 제품 UI를 설계·구현·검토할 때 사용합니다. 설명문이 화면 구조·보이는 조작·상태 피드백을 대신하는 경우에 특히 유용합니다. 기능 이름·사용자 콘텐츠·실제 데이터·오류·동의 안내는 보존합니다. 에이전트의 답변이나 기술 문서에는 적용하지 않습니다. 런타임이나 hooks가 없는 skills-only Plugin이며, 배포 검사와 행동 평가·실제 UI 검증은 구분합니다. [설치 안내](docs/plugin-installation.md#interface-first-design)를 참고하세요. [검증 결과와 한계](docs/validation/interface-first-design.md).

호출 예: `$interface-first-design으로 이 제품 UI의 구조·조작·상태를 설계하거나 검토해 주세요. 필요한 문구와 데이터의 의미는 유지해 주세요.`

[한국어 제품 글쓰기](korean-product-writing/SKILL.md)는 사실·조건·요청한 구성요소를 보존하며 제품 문구를 다듬습니다. skills-only Plugin에는 런타임이나 hooks가 없습니다. 앞선 실패 뒤 같은 6개 입력의 회귀 검사를 통과했으며 [이력과 한계](drafts/korean-product-writing/tests/regression-v4/results.md)를 보존합니다. 설치와 자동 로딩은 시험하지 않았습니다.

설치 후 호출 예: `$korean-product-writing로 이 화면의 제목·설명·버튼을 사실과 조건을 유지해 다듬어 주세요.` 실제 설치나 자동 호출을 시험했다는 뜻은 아닙니다.

[Audit](audit/SKILL.md)은 요청한 범위의 스킬·저장소·작업 지침을 감사합니다. [Choice Interview](choice-interview/SKILL.md)는 단일·복수·직접 응답을 구성하는 인터뷰를 진행하며 혼합형 응답 폼을 포함합니다. 두 스킬은 hooks나 런타임 설치 없이 skills-only Plugin으로도 제공합니다.

## JEV Native 고정 소스

공개 commit으로 고정한 [네이티브 제어기 소스](tools/jev-native/README.md)와 [동반 스킬](jev-native/SKILL.md)을 포함합니다. 바이너리·기존 설치본은 교체하지 않습니다. [출처와 보류한 최신 변경](docs/jev-native-source.md)에서 소스·단위 검사와 실제 데스크톱 동작을 구분합니다.

## 재사용 가능한 개인 작업 스킬

Skills-only 패키지로 [한국어 여행 가이드북](korean-travel-guidebook/SKILL.md), [Obsidian 프로젝트 기록](obsidian-projects/SKILL.md), [Outcome Brief](outcome-brief/SKILL.md), [Verify Work](verify-work/SKILL.md)를 제공합니다. 사용자가 선택한 범위와 프로젝트 검증을 유지합니다. 여행 패키지의 예시는 가상이며 수정하지 않은 나눔고딕과 OFL 원문을 보존합니다. 기기별 합의·개인 프로젝트 상태는 공개본에서 제외했습니다.

[전체 후보 목록](docs/user-skill-inventory.md)은 현재 패키지·외부 의존성·미확인 소스를 구분합니다. [한국어 글쓰기의 과거 초안](drafts/korean-product-writing/STATUS.md)은 이전 실패 이력을 최신 원본과 구별해 보존합니다.

## 팀 하네스 0.5.6

수신 세션을 만들 때 지정한 모델·추론 수준과 승인된 샌드박스 설정을 함께 보존합니다. 충돌하는 모델이나 추론 설정은 생성 전에 거부합니다. 권한·네트워크·승인 범위를 넓히지 않습니다.

`recover-paused`는 패킷을 전달하기 전에 실패한 수신자의 설정을 같은 세션 ID에서 확인하고 복구합니다. 원래 생성 기록·실패·담당자·권한과 일시 중지 상태를 보존합니다. 이미 로드되어 있고 작업이 진행되지 않는 세션만 다룹니다. 별도의 세션을 만들거나 자동으로 로드하거나 모델 작업을 시작하지 않습니다. 세션을 다시 로드하려면 같은 공식 백엔드에서 대기 입력과 활성 목표가 없음을 확인하고, 새 입력을 보내는 주체가 중지된 상태를 유지해야 합니다. 조회를 지원하지 않거나 결과가 불명확하면 중단합니다.

`refresh-packet`은 계약을 명시적으로 반영한 뒤 아직 전달하지 않은 오래된 패킷을 갱신합니다. 이전 패킷·해시·실패와 작업 내용·담당 범위를 보존하고 최신 실제 담당자의 중지 근거를 요구합니다. 새 패킷의 실제 수신과 새 ACK가 있어야 인계를 이어갈 수 있습니다. 설치 성공이나 합성 검사 결과로 실제 인계가 완료되었다고 판단하지 않습니다. [세부 조건과 명령](team-coordination/references/session-control.md)을 확인하세요.

[0.5.6 릴리스](https://github.com/oozoofrog/oozoofrog-plugin/releases/tag/team-harness-v0.5.6)에서 소스와 체크섬을 받으세요. 아래 설치 절차의 파일명·새 설치 계획에는 `0.5.6`을 사용합니다. 기존 설치는 해당 버전의 소스·저널과 사용자 지침을 보존한 채 오버레이를 먼저 복원하고 런타임을 나중에 복원하는 순서를 검토해야 합니다. 0.5.6의 유효 계약 해시도 바뀌므로 기존 프로젝트 반영은 안전한 중단 지점에서 별도로 진행합니다. Normal/default와 역할별 추론 수준은 요청값이며 실제 제공자의 실행 모델·등급을 증명하지 않습니다. 이전 0.5.5와 이전 릴리스는 복구용으로 남습니다.

## 팀 하네스 0.5.5

실제 담당자의 중지 ACK와 공식 앱 조회 근거가 있어야 교차 도구 인계를 준비할 수 있습니다. 대기 상태만으로 중지를 추정하지 않습니다. 디렉터리 소유권과 기존 실패·검토·채팅을 보존하며, 새 구현 세션은 승인된 경로와 일반 권한 심사 설정이 공식 응답에서 일치해야 합니다. 실제 패킷 수신·원자적 소유권 이전·이전 후 담당자 ACK·최신 문맥 ACK가 필요합니다. 설치만으로 기존 실제 프로젝트를 이전하지 않습니다. [인계 절차와 제한](team-coordination/references/session-control.md#cross-tool-source-and-bounded-writing)을 확인하세요.

0.5.0~0.5.4는 개별 공개 릴리스로 게시하지 않았습니다. 해당 변경과 Standard 명시 요청 수정을 0.5.5에 포함했습니다. 이전 0.4.1 릴리스와 자산은 그대로 보존합니다.

[team-coordination](team-coordination/SKILL.md)은 팀이 목적과 완료 조건을 공유하고, 담당자가 작업을 수행하며, 독립 검토자가 현재 결과와 근거를 확인하도록 돕는 선택형 하네스입니다. 리더는 다음 행동과 실패 원인·대안을 정리하고, 실행 담당자는 소유한 범위의 일을 완료까지 이어갑니다.

[0.5.5 릴리스](https://github.com/oozoofrog/oozoofrog-plugin/releases/tag/team-harness-v0.5.5)는 내부 토큰 예산·예약·가상 차감·예산 증액 승인과 임의의 패킷 크기·검토 횟수 제한을 제거한 0.5.0 변경을 포함합니다. 과거에 계산한 한도를 소진했다는 이유만으로 의미 있는 작업을 중단하지 않습니다. 새로운 관찰이나 허용된 수정은 원인과 방법을 기록하고 이어갈 수 있습니다. 0.5.5에서는 수집기 초기화 전에 환경 문제로 실행되지 않았음이 확인된 명령만 같은 명령·환경·입력에 묶어 일반 도구의 권한 검토에 제출할 수 있습니다. 명시적 거부나 실행 여부가 불확실한 결과에는 이 절차를 적용하지 않습니다. 기존 실패 기록, 담당 범위, 최신 지침 확인, 실제 접근 권한과 독립 검토는 유지합니다. 통과하지 않은 결과를 통과로 바꾸지 않습니다.

실제 제공자의 용량·계정 한도·오류와 사용자의 지시는 계속 적용됩니다. 사용량이 제공되지 않으면 미확인으로 남기며 비용을 추정하지 않습니다. 역할 기본값은 Normal, Astra/Sol은 high, Luna는 medium을 **요청**합니다. 현재 계정의 모델 사용 가능 여부, 실제 실행 모델·서비스 등급이나 모든 외부 클라이언트의 강제 준수는 보장하지 않습니다.

설치·업데이트는 다음 순서로 진행합니다.

1. 릴리스에서 `codex-team-harness-0.5.6.tar.gz`와 `.sha256` 파일을 함께 받아 SHA-256을 비교한 뒤 압축을 풉니다. 공식 소스를 신뢰할 수 있는 Python 3.9 이상으로 실행합니다. [소스 다운로드·검증 안내](tools/codex-team-harness/README.md#obtain-and-verify-the-source)를 참고하세요.
2. 새 설치는 압축을 푼 디렉터리에서 아래 명령으로 변경 계획을 확인한 뒤 적용하고 검사합니다. 기존 지침과 원본 바이트는 로컬 저널에 보존합니다. 계획·저널·프로젝트 기록은 공개하지 않습니다.

```sh
python3 -I -S -B bootstrap.py --codex-home "$HOME/.codex" --save-plan plan.json dry-run
python3 -I -S -B bootstrap.py --codex-home "$HOME/.codex" --plan plan.json apply
python3 -I -S -B bootstrap.py --codex-home "$HOME/.codex" doctor
```

기존 설치의 업데이트는 덮어쓰기 방식으로 지원하지 않습니다. 이전 버전의 저널이나 관리 외 파일이 있으면 설치를 중단합니다. 기존 버전에 맞는 소스·저널로 [프로필 오버레이를 먼저 복원하고 런타임을 나중에 복원하는 순서](tools/codex-team-harness/payload/team-coordination/references/profiles.md)를 검토하거나, 원본 바이트와 사용자 지침을 보존하는 별도의 버전별 이전을 검토해야 합니다. 복원이 확인된 뒤 0.5.6에서 새 계획을 생성합니다. 저널이나 알 수 없는 파일을 지워 설치를 강행하지 마세요.

Plugin만 설치하면 스킬 안내만 추가됩니다. 전역 지침·런타임 설치나 기존 프로젝트 이전은 자동으로 일어나지 않습니다. 0.5 이전 계약의 프로젝트는 담당자가 안전한 중단 지점에서 원본 상태 바이트를 비공개로 보존하고, 리더와 독립 검토자의 확인을 거쳐 [명시적 계약 이전(`contract_migrate`)](tools/codex-team-harness/payload/team-coordination/references/migration.md)을 실행해야 합니다. 이미 0.5 이상인 schema-2 프로젝트는 유효 계약 해시가 달라질 때만 안전한 중단 지점에서 `policy_refresh`를 수행하고, 현재 패킷을 실제로 읽은 참여자의 새 ACK를 받아야 합니다. 계약 해시가 이미 일치하면 반복 이전은 필요하지 않습니다. 0.5.5 런타임 변경은 유효 계약 해시를 바꿉니다. 설치 성공이나 합성 검사 ACK는 실제 프로젝트 이전·승인을 대신하지 않습니다.

[실행·복구 도구](tools/codex-team-harness/README.md), [변경된 관찰·수정 절차](tools/codex-team-harness/payload/team-coordination/references/diagnostics.md), [소스 이전 이력](docs/team-harness-migration.md)을 함께 제공합니다. 이전 `0.4.1`과 `0.1.1-public.1` 릴리스는 복구 참조로 보존합니다.

Swift 의미론 탐색용 `swift-intelligence`, 로컬 모델 설치·실행용 `local-ai-studio`, macOS·브라우저 제어와 화면·시스템 오디오 녹화용 `macpilot`를 제공합니다.

## Local AI Studio

`$local-ai-studio`는 Apple Silicon Mac에서 Local AI Studio의 `ai` CLI로 이미지 생성·편집, 음성 합성·전사, 영상·음악 생성, 영어→한국어 번역을 실행하고 결과물을 검증·전달합니다. Local AI Studio 또는 온디바이스 모델 작업을 요청했는데 LocalAIHub나 필요한 모델이 없으면 해당 소스와 요청에 필요한 모델 그룹만 로컬에 설치한 뒤 작업을 이어갑니다. 일반 미디어 요청만으로 대용량 설치를 시작하지 않으며, 사용자가 지정한 도구·모델·저장 위치·형식을 우선합니다.

```text
$local-ai-studio로 이 녹음을 전사해 지정한 폴더에 SRT로 저장하고 결과를 확인해주세요.
$local-ai-studio로 비상업적 평가용 찻주전자 이미지를 만들고 PNG 파일을 확인해주세요.
$local-ai-studio로 이 영어 문서를 한국어로 번역해 지정한 TXT 파일로 저장해주세요.
```

Standalone `local-ai-studio/`와 byte-identical skills-only Plugin `0.2.1`을 제공합니다. Plugin에 모델·런타임·생성 미디어·인증·실행기 바이너리는 포함하지 않습니다. 설치 시 현재 소스·CLI 기능, 선택한 저장 위치와 용량을 확인하고 필요한 모델만 받습니다. `/Volumes/eyedisk/AI`는 참조 Mac의 발견 후보일 뿐 보편적인 기본값이 아닙니다. Qwen Image 다운로드에는 사용자의 명시적 라이선스 동의가 필요합니다. 24 GB Mac에서는 대형 생성 모델을 한 번에 하나만 실행합니다.

설치 후 `ai --help`로 지원 명령을 확인합니다. 공개 LocalAIHub 소스와 다른 로컬 체크아웃의 기능이 다를 수 있습니다. `READY`·종료 코드·`Output:` 로그만으로 결과 품질을 주장하지 않으며 실제 파일·형식·미리보기/재생/내용 확인 여부를 구분해 전달합니다. [스킬 본문](local-ai-studio/SKILL.md), [LocalAIHub 설치](local-ai-studio/references/setup.md), [명령·출력 규칙](local-ai-studio/references/cli-workflows.md), [Plugin 설치 안내](docs/plugin-installation.md#local-ai-studio)를 참고하세요.

## MacPilot

`macpilot`는 macOS 앱·창·메뉴·파일·시스템과 브라우저·iOS Simulator 작업을 관찰·실행·검증합니다. 제한 시간 동안 게임 키를 동시에 유지하거나 반복해서 누르며, 전역 키보드·마우스 입력 중 화면 가장자리 효과와 작은 조작 중 안내를 표시합니다. 작업별 멀티 가상 커서, 백그라운드 제어, 라이브 프리뷰, 선택적 private API와 Codex 개선 요청 전송이 필요한 데스크톱 워크플로에 사용합니다.

```text
$macpilot로 macOS·브라우저 작업과 화면·시스템 오디오 녹화를 수행하고 결과를 검증하세요.
```

원본은 [macpilot/](macpilot/), 배포 사본은 [Plugin 스킬](plugins/macpilot/skills/macpilot/SKILL.md)에서 관리합니다. `3.5.1`은 Swift 코어·CLI·MCP, 작업 격리·취소·포커스, 라이브 캡처·오버레이, 파일·Finder 태그·CoreAudio, Chromium 확장과 Safari Apple Events, 로컬 개선 요청 대기열·Codex app-server 전송을 포함합니다. 실제 OS 커서와 키보드 포커스는 공유하며, 모든 앱·모든 브라우저 기능의 성공을 보장하지 않습니다. [작업별 지원 범위](macpilot/references/workflows.md)에 백엔드별 제약을 명시합니다.

3.5는 읽기 전용 `mac_analyze`로 AX 계층 요약·문자열 검색·속성/액션 열거·UTF-16 텍스트 범위·앱 범위 hit test를 제공합니다. 창을 활성화하거나 클릭하지 않으며 외부 AX 라이브러리를 사용하지 않습니다. [UI 분석과 Baepsae 비교](macpilot/references/ui-analysis.md)를 참고하세요.

3.4는 AX 조건 대기, 범위를 명시한 공통 결과, 다른 입력 출처 감지 시 중단, 선택적 동작 추적, 후조건과 재실행 차단이 있는 명시적 재사용 작업을 추가합니다. 이미지 검색은 기본 비활성이며 VisionKit과 로컬 EmbeddingGemma 2를 사용합니다. 후보 벡터를 재사용하고 낮은 점수나 중복 후보는 선택하지 않습니다. [사용법과 검증 범위](macpilot/references/capabilities.md)를 확인하세요.

macOS 14 이상에서 실행합니다. 첫 실행은 고정 해시와 서명을 확인한 Universal 배포 앱을 내려받습니다. 일반 macOS 제어에는 Swift·Xcode 설치가 필요 없습니다. 기본 제어에는 Python·Node.js 런타임과 외부 SwiftPM 패키지가 없습니다. 선택적 VisionKit·EmbeddingGemma 2 검색은 별도로 설정한 로컬 Python 환경과 모델을 사용합니다. Chromium 확장·사이트 접근과 Safari Automation·JavaScript from Apple Events는 별도 활성화가 필요합니다. 화면·시스템 오디오는 [`mac_record`](macpilot/references/recording.md)로 MP4에 녹화하고 검사합니다(macOS 15+). Safari·Chrome 개발자 설정은 [`mac_browser_developer`](macpilot/references/browser-developer-settings.md)로 조회·준비하고 사용자 승인 후 켤 수 있습니다. Codex 개선 요청 전송에는 명시적 목적지 설정과 로그인·모델 연결이 필요합니다. 일반 로컬 제어는 모델을 요구하지 않습니다.

[`mac_connection`](macpilot/references/mcp-recovery.md)으로 서버·부모 프로세스 신원, 권한과 CLI/MCP 호출 경로를 확인합니다. CLI `connection-check`는 기존 서버·Codex를 재시작하지 않고 격리된 새 MCP를 검사합니다. 별도 검사 성공을 현재 대화의 재연결 성공으로 취급하지 않습니다.

`mac_simulator`는 UDID·기기·부팅 정체성을 확인하고 앱 생명주기·PNG·동영상·iOSContentGroup 분석을 제공합니다. IndigoHID 입력은 별도 프로세스이며 매 호출의 `privateAPI=true`가 필요합니다. Simulator 기능에만 Xcode와 해당 런타임이 필요합니다. [Simulator 사용법](macpilot/references/simulator.md)을 참고하세요.

권한 설정은 `mac_permission operation=setup kind=all` 또는 CLI `permission-setup`으로 진행합니다. macOS 시스템 설정 옆에 앱 아이콘만 있는 88×88pt 안내 패널을 붙입니다. 사용자가 패널의 아이콘을 권한 목록으로 끌어 넣거나 아이콘 우클릭 메뉴에서 ‘자동으로 추가’를 선택할 수 있습니다. Finder나 큰 별도 설정 창은 열지 않습니다. 패널은 설정 창 이동을 따라가고 다른 앱이 활성화되면 숨습니다. 아이콘과 잡는 손 모양의 짧은 시연이 직접 드래그를 안내합니다. 사용자가 아이콘을 잡으면 시연을 멈추며 동작 줄이기를 따릅니다. Automation은 앱별 macOS 동의 요청을 사용하며, 시스템 인증과 최종 승인은 사용자가 직접 진행합니다. [권한 설정](macpilot/references/permission-setup.md)을 참고하세요.

현재 MCP 도구가 필요한 기능을 제공하면 직접 사용하고, 구버전이면 이 스킬의 CLI를 사용합니다. Plugin은 전역 스킬·MCP 설정·사용자 브라우저 프로필을 자동 교체하지 않습니다. 원격 게시·설치·활성화·새 세션 노출은 별도입니다. [스킬 본문](macpilot/SKILL.md), [CLI·MCP](macpilot/references/tools.md), [개발·검증](macpilot/references/development.md), [설치 안내](docs/plugin-installation.md#macpilot)를 참고하세요.

이후 변경은 원본에서 수행하고 `python3 scripts/sync_skill_mirrors.py --package macpilot --write`로 배포 사본에 반영합니다. 바이너리·빌드 캐시·화면·로그 증거는 Git과 배포 사본에서 제외합니다.

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
codex plugin add macpilot@oozoofrog-plugin
```

다른 Plugin의 요구 사항과 standalone 설치는 [Plugin 설치 안내](docs/plugin-installation.md)를 참고하세요.

## 검증

버전 변경·검증한 커밋·GitHub 게시·선택 설치는 [Plugin 배포 절차](docs/plugin-release.md)를 사용합니다.

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

Plugin manifest와 marketplace는 저장소 배포 검사로 확인합니다. 실제 원격 등록·설치는 별도 `CODEX_HOME`에서 CLI로 검증하며 기존 설치·인증을 변경하지 않습니다. Swift Intelligence를 수정할 때는 해당 Plugin의 검증 지침을 별도로 따릅니다. 변경 기록은 [CHANGELOG.md](CHANGELOG.md)에 있습니다.

## C4fy

[C4fy](c4fy/SKILL.md)는 소스 근거를 갖춘 C4 시스템 맥락·컨테이너·컴포넌트 구조도를 독립 HTML로 만듭니다. 둥근 카드와 부드러운 색상을 사용하며 C1/C2/C3를 확대 전환합니다. 노드·소스 상세, SVG·JSON 저장을 지원합니다. 일반 흐름도·시퀀스·C4 코드 수준 구조도는 대상이 아닙니다.

`$c4fy`로 프로젝트의 C1·C2·C3 구조를 요청할 수 있습니다. Archify의 제작·검증 흐름만 참고한 독립 구현이며 Archify 설치나 코드에 의존하지 않습니다. 생성에는 Node.js 18 이상이 필요하고 결과 HTML은 오프라인에서 작동합니다. ‘동작 줄이기’를 켜면 즉시 전환합니다. [모델 계약](c4fy/references/model.md)에 계층·근거·출력 범위를 정리했습니다. 이 마켓플레이스를 등록한 뒤 `codex plugin add c4fy@oozoofrog-plugin`으로 설치합니다.
