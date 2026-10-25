# Plugin installation

## WinPilot

Windows x64에서 `codex plugin marketplace upgrade oozoofrog-plugin` 후 `codex plugin add winpilot@oozoofrog-plugin`을 실행합니다. marketplace가 없으면 `codex plugin marketplace add oozoofrog/oozoofrog-plugin --ref main`으로 먼저 등록합니다.

WinPilot 0.5.0은 [스킬](../winpilot/SKILL.md)과 MCP 설정을 함께 제공합니다. 첫 서버 연결에서 GitHub Release의 독립 실행형 ZIP을 내려받아 SHA-256을 검증하고 `%LOCALAPPDATA%/WinPilot/0.5.0/`에 설치합니다. 별도 .NET 설치·Python·SDK는 실행에 필요하지 않습니다. 빌드·시험·오프라인 설치는 [개발 안내](../winpilot/references/development.md)를 따릅니다. unsigned 배포이며 Windows SmartScreen 승인이 필요할 수 있습니다.

기존 `windows-pilot` 실행 파일명과 7개 MCP 도구명은 유지합니다. 기존 standalone 스킬·MCP 설정·개인 캡처·원본 폴더는 자동 삭제하지 않습니다. 동일 서버를 Plugin MCP와 수동 MCP 양쪽에 등록하지 마세요. 설치 상태와 현재 대화의 도구 노출은 별도로 확인하며 새 대화에서 `$winpilot`을 호출할 수 있습니다. [검증 범위](validation/winpilot.md)를 참고하세요.

## 기존 Plugin

Repository marketplace에는 `swift-intelligence`, `local-ai-studio`, `macpilot`가 있습니다. 필요한 Plugin만 선택합니다. 아래 명령은 해당 변경이 원격에 반영된 뒤 사용합니다.

```bash
codex plugin marketplace add oozoofrog/oozoofrog-plugin --ref main
codex plugin add swift-intelligence@oozoofrog-plugin
codex plugin add local-ai-studio@oozoofrog-plugin
codex plugin add macpilot@oozoofrog-plugin
```

2026-10-17에 저장소와 marketplace 이름을 `codex-skills`에서 `oozoofrog-plugin`으로 바꿨습니다. 현재 원격 등록 주소는 `oozoofrog/oozoofrog-plugin`이고 플러그인 선택자는 `<plugin>@oozoofrog-plugin`입니다. 개별 플러그인 이름은 유지합니다. GitHub 저장소의 이름 변경과 Codex의 marketplace·설치 식별자 변경은 별개입니다. 기존 `@codex-skills` 설치·활성화 상태와 사용자 데이터는 자동 이전하거나 삭제하지 않습니다. 새 이름으로 전환할 때는 `codex plugin list --json`의 기존 설치 목록을 확인하고 필요한 플러그인만 선택합니다. 이전 설치본이 있는 상태에서 새 선택자를 추가하면 중복 노출될 수 있습니다.

기존 자동 동기화 launchd label과 daemon lock ID는 설치된 작업의 제어 호환성을 위해 유지합니다. 이 저장소의 원격·카탈로그 이름 변경이 사용자 컴퓨터의 기존 작업을 재설치하거나 다른 checkout을 이동시키지는 않습니다.

이미 등록한 원격 marketplace는 `codex plugin marketplace upgrade oozoofrog-plugin`로 snapshot을 갱신한 뒤 설치합니다. 로컬 checkout marketplace를 사용하는 경우에는 그 source를 확인한 뒤 같은 이름으로 재설치합니다.

설치 성공, 새 로더 노출, 실제 새 작업이 읽은 경로를 구분해 확인합니다. 설치된 Plugin을 제거할 때는 Codex의 제거 기능으로 설정과 캐시를 함께 정리합니다. Marketplace 항목 삭제만으로 설치본이 제거되지는 않습니다.

`gptplease`는 2026-10-17에 제거했습니다. 과거 상담 패키지와 로그인 프로필은 사용자 데이터로 보존하며 삭제·이관하지 않습니다. [이전 검증 기록](gptplease-transport-validation.md)은 당시 상태를 설명합니다.

Swift Intelligence는 macOS, Command Line Tools를 포함한 Xcode, Python 3가 필요합니다. Xcode에 포함된 `sourcekit-lsp`를 실행하며 외부 MCP 바이너리나 Python 패키지를 설치하지 않습니다. Swift Intelligence 설치 후 Codex를 다시 시작하고 새 작업을 열어 Skill과 MCP 도구를 로드하십시오. 자세한 내용은 [Swift Intelligence 설치 및 사용](../plugins/swift-intelligence/docs/installation-and-usage.md)을 참고하세요.

## MacPilot

`mac_analyze`의 읽기 전용 UI 분석과 Baepsae·Simulator 기능의 구분은 [네이티브 UI 분석](../macpilot/references/ui-analysis.md)을 참고하세요.

`macpilot` Plugin `3.5.1`은 macOS·브라우저·Simulator 작업용 스킬, SwiftPM 소스·테스트, Chromium 확장, 빌드 런처와 검증 스크립트를 포함합니다. 새 작업에서 `$macpilot` 또는 `$macpilot:macpilot`로 호출합니다. 현재 MCP에 필요한 기능이 없으면 설치된 스킬의 `scripts/macpilot` CLI를 사용합니다. Plugin은 MCP 서버를 자동 등록하지 않습니다. `mac_record`의 화면·영역·시스템 오디오 MP4 녹화에는 macOS 15 이상이 필요합니다. [녹화 범위와 검증](../macpilot/references/recording.md)을 확인하세요. [CLI·선택적 MCP 설정](../macpilot/references/tools.md)을 참고하세요. MCP가 끊겼으면 [연결 진단과 복구](../macpilot/references/mcp-recovery.md)의 `mac_connection`·`connection-check`를 사용합니다. 기존 연결·Codex 앱을 자동 재시작하지 않습니다.

macOS 14 이상에서 실행합니다. CLI 첫 실행은 고정 해시와 서명을 확인한 Universal 배포 앱을 내려받습니다. 일반 macOS 제어에는 Swift·Xcode 설치가 필요 없습니다. 사용하는 기능에 따라 Accessibility·Screen Recording·Automation 권한이 필요합니다. 기본 제어에는 모델·API 키·외부 SwiftPM 패키지·Python·Node.js가 필요하지 않습니다. 선택적 VisionKit·EmbeddingGemma 2 검색만 명시적으로 설정한 로컬 Python 환경과 고정 모델을 사용합니다. 전역 입력 중 다른 입력 출처를 감지하려면 Input Monitoring 권한이 필요합니다. 조건 대기·추적·재사용 작업과 이미지 검색은 [기능 사용법](../macpilot/references/capabilities.md)을 확인하세요. Codex 진단 전송을 사용할 때만 별도 Codex 실행 파일·로그인·모델 연결이 필요합니다.

`mac_simulator`는 UDID·기기·부팅 정체성을 확인하고 앱 생명주기·PNG·동영상·iOSContentGroup 분석을 제공합니다. IndigoHID 입력은 별도 프로세스이며 매 호출의 `privateAPI=true`가 필요합니다. Simulator 기능에만 Xcode와 해당 런타임이 필요합니다. [Simulator 사용법](../macpilot/references/simulator.md)을 참고하세요.

권한을 설정하려면 설치된 스킬의 `scripts/macpilot permission-setup`을 실행합니다. macOS 시스템 설정 옆에 앱 아이콘만 있는 88×88pt 안내 패널을 붙입니다. 짧은 드래그 시연은 최대 두 번 재생하고, 아이콘을 잡으면 멈추며 동작 줄이기를 따릅니다. 사용자가 패널의 앱 아이콘을 권한 목록으로 드래그하거나 아이콘 우클릭 메뉴에서 선택적 자동 추가를 사용할 수 있습니다. Finder나 큰 별도 설정 창은 열지 않습니다. Automation은 대상 앱별 macOS 동의 요청을 사용합니다. 시스템 인증과 최종 승인은 사용자가 직접 진행합니다. [권한 설정](../macpilot/references/permission-setup.md)을 확인하세요.

Chromium은 `browser/extension/`을 로드하고 `mac_browser install_host`로 해당 확장 ID의 Swift native host를 등록합니다. 필요한 사이트 접근은 확장 팝업에서 허용합니다. Safari는 확장 없이 Apple Events를 사용하며 Safari의 Allow JavaScript from Apple Events가 켜져 있어야 DOM 동작을 실행합니다. `mac_browser_developer`로 Safari·Chrome 개발자 설정을 조회·준비하고 사용자의 네이티브 확인 후 선택한 설정을 켤 수 있습니다. [개발자 설정과 승인 범위](../macpilot/references/browser-developer-settings.md)를 확인하세요. Safari의 교차 출처 프레임·다운로드·screenshot은 호스트 브라우저 또는 네이티브 도구가 필요합니다. 설치 조건·전체 지원 범위는 [작업별 워크플로](../macpilot/references/workflows.md)에 있습니다.

작업별 멀티 가상 커서·백그라운드 제어·라이브 프리뷰·통합 포커스, 파일·Finder 태그·CoreAudio, 선택적 private 창 ID 백엔드를 제공합니다. Codex 개선 요청은 목적지·전송 범위를 명시적으로 설정하며 기본은 수동 전송입니다. `automaticSend=true`를 허용하면 이후 오류를 자동 전달합니다. 응답 완료는 수정·설치 완료와 구분합니다.

원본은 `macpilot/`에서 수정하고 `python3 scripts/sync_skill_mirrors.py --package macpilot --write`로 배포 미러를 갱신합니다. Plugin 소스 패키지에는 바이너리·SwiftPM 캐시·실행 증거를 넣지 않습니다. 검증한 Universal 실행 앱은 공식 릴리스의 별도 ZIP으로 제공합니다. [개발과 검증](../macpilot/references/development.md)에서 단위·MCP·실제 앱·브라우저·Codex 전송 검증을 구분합니다.

이 저장소 변경은 기존 `~/.codex/skills/macpilot` 설치본과 MCP 설정을 변경하지 않습니다. Plugin 설치로 전환할 때 기존 경로와 중복 노출을 확인합니다. 원격 게시 전에는 원격 설치 명령에 이번 변경이 포함되지 않습니다. 설치·활성화·새 세션 노출은 별도로 확인해야 합니다.

## Local AI Studio

`local-ai-studio`는 Local AI Studio를 사용한 이미지·음성·영상·음악·영어→한국어 번역 작업을 수행하는 skills-only Plugin `0.2.1`입니다. Local AI Studio 또는 온디바이스 모델 작업을 요청했는데 LocalAIHub나 필요한 모델 그룹이 없으면 현재 소스를 확인해 로컬에 설치한 뒤 결과를 검증·전달합니다. 일반 미디어 요청만으로 설치를 시작하지 않습니다. 새 작업에서 `$local-ai-studio` 또는 `$local-ai-studio:local-ai-studio`로 호출할 수 있으며 사용자가 선택한 도구·모델·출력 위치·형식을 우선합니다.

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
