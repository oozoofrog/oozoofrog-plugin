# Plugin installation

## OpenAI Decisions

`openai-decisions@oozoofrog-plugin`은 [스킬](../openai-decisions/SKILL.md)만 제공합니다. 기존 `openai_decide` MCP/Pi 도구나 `openai-decisions` CLI가 있으면 이를 사용하고, 없으면 [공식 CLI 직접 호출](../openai-decisions/references/cli.md)을 따릅니다. Plugin 설치는 MCP 서버·API 키·과금 계정을 자동 등록하지 않습니다. API 키는 기존 비밀 입력·자격증명 저장소로 전달하고 설정 파일이나 대화에 복사하지 않습니다.

`openai-decisions` 0.1.0을 설치하려면 등록한 marketplace를 갱신한 뒤 선택한 Plugin을 추가합니다. marketplace가 없으면 먼저 `codex plugin marketplace add oozoofrog/oozoofrog-plugin --ref main`으로 등록합니다.

```sh
codex plugin marketplace upgrade oozoofrog-plugin
codex plugin add openai-decisions@oozoofrog-plugin
```

기존 standalone 스킬 별칭은 새 소스로 연결할 수 있으며 도구 실행 경로와 인증 설정은 유지합니다.

## WinPilot

Windows x64에서 `codex plugin marketplace upgrade oozoofrog-plugin` 후 `codex plugin add winpilot@oozoofrog-plugin`을 실행합니다. marketplace가 없으면 `codex plugin marketplace add oozoofrog/oozoofrog-plugin --ref main`으로 먼저 등록합니다.

WinPilot 0.5.1은 [스킬](../winpilot/SKILL.md)과 MCP 설정을 함께 제공합니다. 첫 서버 연결에서 GitHub Release의 독립 실행형 ZIP을 내려받아 SHA-256을 검증하고 `%LOCALAPPDATA%/WinPilot/0.5.1/`에 설치합니다. 별도 .NET 설치·Python·SDK는 실행에 필요하지 않습니다. 빌드·시험·오프라인 설치는 [개발 안내](../winpilot/references/development.md)를 따릅니다. unsigned 배포이며 Windows SmartScreen 승인이 필요할 수 있습니다.

기존 `windows-pilot` 실행 파일명과 7개 MCP 도구명은 유지합니다. 기존 standalone 스킬·MCP 설정·개인 캡처·원본 폴더는 자동 삭제하지 않습니다. 동일 서버를 Plugin MCP와 수동 MCP 양쪽에 등록하지 마세요. 설치 상태와 현재 대화의 도구 노출은 별도로 확인하며 새 대화에서 `$winpilot`을 호출할 수 있습니다. [검증 범위](validation/winpilot.md)를 참고하세요.

## Team Coordination

`codex plugin marketplace upgrade oozoofrog-plugin` 후 `codex plugin add team-coordination@oozoofrog-plugin`으로 `0.6.1` Plugin을 설치하거나 갱신합니다. 설치 후 버전·활성화 상태·실제 캐시 경로를 확인합니다.

`$team-coordination:team-coordination`은 현재 채팅의 직접 작업과 기존 담당자 재사용을 우선합니다. 새 채팅은 명시적인 생성 요청과 구체적인 이점이 있을 때만 만들며, 별도 Astra 분석 채팅은 선택 사항입니다. 스킬 호출을 해당 작업의 협업 위임으로 전달하고, 팀원의 승인·확인·선택 요청은 리더에게 모읍니다. 협업 도구의 `prompt` 정책은 별도이므로 조정 담당자가 [공식 도구별 설정](../team-coordination/references/team-decisions.md#official-tool-policy)을 확인·적용합니다. 사용자 전체에 적용되는 6개 도구만 변경하며 실제 작업 권한은 넓히지 않습니다. 설명 질문이나 설치만으로 채팅을 만들지 않습니다. [시작 절차](../team-coordination/references/sidebar-startup.md)를 참고하세요.

Plugin 설치는 기존 `~/.codex/skills/team-coordination` standalone 런타임·설치 저널·프로필 오버레이와 활성 프로젝트 계약을 이전하지 않습니다. 기존 저널을 삭제하거나 설치 경로를 직접 덮어쓰지 않습니다. 새 채팅의 스킬 노출과 실제 실행 모델·등급은 설치 파일 검사와 구분합니다.

설정이 이미 적용돼 있는데도 승인을 요청하거나 협업이 정체되면 `$team-coordination:team-coordination`에 `doctor`를 요청합니다. [협업 Doctor](../team-coordination/references/doctor.md)는 기존 팀과 공식 조회 근거를 진단한 뒤 조정 담당자가 가능한 복구를 이어가도록 합니다. 선택 명령은 Python 3.11 이상이 필요하며, 진단 스크립트가 사용자 설정·원장·승인 응답을 직접 쓰지는 않습니다.

## 기존 Plugin


```bash
codex plugin marketplace add oozoofrog/oozoofrog-plugin --ref main
codex plugin add swift-intelligence@oozoofrog-plugin
codex plugin add local-ai-studio@oozoofrog-plugin
```

2026-10-17에 저장소와 marketplace 이름을 `codex-skills`에서 `oozoofrog-plugin`으로 바꿨습니다. 현재 원격 등록 주소는 `oozoofrog/oozoofrog-plugin`이고 플러그인 선택자는 `<plugin>@oozoofrog-plugin`입니다. 개별 플러그인 이름은 유지합니다. GitHub 저장소의 이름 변경과 Codex의 marketplace·설치 식별자 변경은 별개입니다. 기존 `@codex-skills` 설치·활성화 상태와 사용자 데이터는 자동 이전하거나 삭제하지 않습니다. 새 이름으로 전환할 때는 `codex plugin list --json`의 기존 설치 목록을 확인하고 필요한 플러그인만 선택합니다. 이전 설치본이 있는 상태에서 새 선택자를 추가하면 중복 노출될 수 있습니다.

기존 자동 동기화 launchd label과 daemon lock ID는 설치된 작업의 제어 호환성을 위해 유지합니다. 이 저장소의 원격·카탈로그 이름 변경이 사용자 컴퓨터의 기존 작업을 재설치하거나 다른 checkout을 이동시키지는 않습니다.

이미 등록한 원격 marketplace는 `codex plugin marketplace upgrade oozoofrog-plugin`로 snapshot을 갱신한 뒤 설치합니다. 로컬 checkout marketplace를 사용하는 경우에는 그 source를 확인한 뒤 같은 이름으로 재설치합니다.

설치 성공, 새 로더 노출, 실제 새 작업이 읽은 경로를 구분해 확인합니다. 설치된 Plugin을 제거할 때는 Codex의 제거 기능으로 설정과 캐시를 함께 정리합니다. Marketplace 항목 삭제만으로 설치본이 제거되지는 않습니다.

`gptplease`는 2026-10-17에 제거했습니다. 과거 상담 패키지와 로그인 프로필은 사용자 데이터로 보존하며 삭제·이관하지 않습니다. [이전 검증 기록](gptplease-transport-validation.md)은 당시 상태를 설명합니다.

Swift Intelligence는 macOS, Command Line Tools를 포함한 Xcode, Python 3가 필요합니다. Xcode에 포함된 `sourcekit-lsp`를 실행하며 외부 MCP 바이너리나 Python 패키지를 설치하지 않습니다. Swift Intelligence 설치 후 Codex를 다시 시작하고 새 작업을 열어 Skill과 MCP 도구를 로드하십시오. 자세한 내용은 [Swift Intelligence 설치 및 사용](../plugins/swift-intelligence/docs/installation-and-usage.md)을 참고하세요.

## Local AI Studio

버전 0.3.0은 별도 `whisper-cli`를 사용하는 [Whisper 전사·추정 타임스탬프 흐름](../local-ai-studio/references/whisper.md)도 제공합니다. 기존 모델 재사용, crop 오프셋, DTW 실패와 정확도 한계를 구분합니다. 별도 CLI 지침이며 네이티브 앱 통합을 뜻하지 않습니다.

`local-ai-studio`는 Local AI Studio를 사용한 이미지·음성·영상·음악·영어→한국어 번역 작업을 수행하는 skills-only Plugin `0.3.0`입니다. Local AI Studio 또는 온디바이스 모델 작업을 요청했는데 LocalAIHub나 필요한 모델 그룹이 없으면 현재 소스를 확인해 로컬에 설치한 뒤 결과를 검증·전달합니다. 일반 미디어 요청만으로 설치를 시작하지 않습니다. 새 작업에서 `$local-ai-studio` 또는 `$local-ai-studio:local-ai-studio`로 호출할 수 있으며 사용자가 선택한 도구·모델·출력 위치·형식을 우선합니다.

아직 푸시하지 않은 checkout을 시험하려면 저장소 루트에서 `codex plugin marketplace add "$PWD"`로 등록한 뒤 `codex plugin add local-ai-studio@oozoofrog-plugin`를 사용하세요. 기존 `oozoofrog-plugin` marketplace가 있으면 source가 원격인지 해당 checkout인지 먼저 확인합니다. Standalone을 선택하면 `local-ai-studio/`를 skill-installer로 설치하되 Plugin과 중복 설치하지 않고 기존 전역 스킬을 임의로 덮어쓰지 않습니다.

Plugin 설치 자체는 LocalAIHub나 모델을 설치하지 않습니다. 스킬을 호출해 로컬 작업을 요청하면 Apple Silicon/macOS와 저장 공간을 확인하고 [LocalAIHub 설치 절차](../local-ai-studio/references/setup.md)로 필요한 소스·앱·모델 그룹을 준비할 수 있습니다. 이미 설치된 경우 `ai --help`, `ai status`, `ai models`와 선택 root/`AIHUB_ROOT`를 확인해 재다운로드를 피합니다. 참조 Mac의 `/Volumes/eyedisk/AI/bin/ai`와 `/Volumes/eyedisk/AI/LocalAIHub/README.md`는 발견 후보일 뿐 타 기기의 기본 경로가 아닙니다. 모델·생성 미디어·인증·runner·MCP·app·hook을 Plugin에 번들하지 않으며 marketplace `ON_INSTALL`도 모델 라이선스 동의나 인증을 대신하지 않습니다.

Qwen Image 2.1 설치 플래그는 사용자의 명시적 라이선스 동의 후에만 사용합니다. 24 GB Mac에서는 다른 app/UI 작업도 포함해 대형 생성 모델을 직렬로 실행합니다. TTS 출력 디렉터리·전사 stem·그 외 파일 경로의 차이와 `music --prompt`/bare `music`의 동작을 [명령 참고](../local-ai-studio/references/cli-workflows.md)에 정리했습니다.

Plugin 설치 성공, 새 세션에서 읽은 스킬 경로, 모델 readiness, 실제 추론 완료, 결과의 파일·형식·품질 확인은 별도 단계입니다. 배포 검사만으로 실제 생성·재생 품질이나 설치 후 노출을 주장하지 않습니다.

## Interface First Design

`interface-first-design` 0.1.0은 제품 화면·상호작용을 설계·구현·검토하는 skills-only Plugin입니다. 설명문 대신 구조·보이는 조작·상태 피드백으로 사용 흐름을 드러내며, 기능 이름·실제 데이터·사용자 콘텐츠·오류·동의 안내를 보존합니다. 에이전트 답변이나 기술 문서에는 적용하지 않습니다. 별도 런타임·MCP·hooks·인증 정보를 포함하지 않습니다.

원격에 반영된 뒤 다음 명령으로 설치합니다. 기존 marketplace가 있으면 먼저 `codex plugin marketplace upgrade oozoofrog-plugin`로 snapshot을 갱신하세요.

```sh
codex plugin marketplace add oozoofrog/oozoofrog-plugin --ref main
codex plugin add interface-first-design@oozoofrog-plugin
```

게시 전 checkout 검증에는 저장소 루트에서 `codex plugin marketplace add "$PWD"`를 사용하고 source가 그 checkout인지 확인합니다. Standalone 설치는 `interface-first-design/`을 skill-installer로 설치하며 기존 설치본을 임의로 덮어쓰거나 Plugin과 중복 설치하지 않습니다.

새 작업에서 `$interface-first-design` 또는 `$interface-first-design:interface-first-design`으로 호출합니다. [스킬](../interface-first-design/SKILL.md)과 [가상 예시](../interface-first-design/references/examples.md)를 참고하세요. 패키지 검사 통과, 원격 카탈로그 반영, 설치 성공, 새 세션 노출, 실제 제품 UI 동작 검증은 각각 확인해야 합니다.

## Refactor

`refactor` 0.2.0은 동작 보존 리팩토링과 요청한 SwiftLint 빌드 통합을 수행하는 skills-only Plugin입니다. 통합 시 [빌드 통합 지침](../refactor/references/swiftlint-build.md)에 따라 프로젝트 구조에 맞춰 빌드 파일을 수정하고 실제 실행을 검증합니다. 별도 런타임·MCP·hooks를 설치하지 않습니다. Swift 작업은 분석 전용 요청에서도 SwiftLint 진단을 반드시 사용합니다. 도구가 없으면 요청 권한과 저장소·환경 제약에 따라 설치합니다. 진단을 확보하지 못하면 원인과 필요한 조치를 보고하고 작업을 미완료로 남깁니다.

```sh
# marketplace가 없는 경우 먼저 등록합니다.
codex plugin marketplace add oozoofrog/oozoofrog-plugin --ref main
# 기존 marketplace는 snapshot을 갱신합니다.
codex plugin marketplace upgrade oozoofrog-plugin
codex plugin add refactor@oozoofrog-plugin
codex plugin list --marketplace oozoofrog-plugin --json
```

새 대화에서 `$refactor` 또는 `$refactor:refactor`로 호출합니다. 기존 개인 `refactor` 스킬이 있다면 원본을 스킬 검색 경로 밖에 백업하고, Plugin 설치 경로와 내용 일치를 확인한 뒤 개인 사본을 제거합니다. 설치·활성화와 새 대화의 스킬 노출은 별도로 확인합니다. [리뷰와 검증 범위](validation/refactor.md)를 참고하세요.

## 별도 Mac 자동화 프로젝트

Mac·iOS 시뮬레이터 자동화는 [Mac Pilot](https://github.com/oozoofrog/mac-pilot)에서 설치·개발·배포합니다. 기존 Keychain·프로필·캡처와 사용자 설정은 유지합니다.
