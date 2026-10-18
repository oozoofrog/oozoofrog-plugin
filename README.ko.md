# oozoofrog-plugin

[English](README.md) | 한국어

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

`macpilot`는 macOS 앱·창·메뉴·파일·시스템과 브라우저 작업을 관찰·실행·검증합니다. 작업별 멀티 가상 커서, 백그라운드 제어, 라이브 프리뷰, 선택적 private API와 Codex 개선 요청 전송이 필요한 데스크톱 워크플로에 사용합니다.

```text
$macpilot로 macOS·브라우저 작업과 화면·시스템 오디오 녹화를 수행하고 결과를 검증하세요.
```

원본은 [macpilot/](macpilot/), 배포 사본은 [Plugin 스킬](plugins/macpilot/skills/macpilot/SKILL.md)에서 관리합니다. `3.2.1`은 Swift 코어·CLI·MCP, 작업 격리·취소·포커스, 라이브 캡처·오버레이, 파일·Finder 태그·CoreAudio, Chromium 확장과 Safari Apple Events, 로컬 개선 요청 대기열·Codex app-server 전송을 포함합니다. 실제 OS 커서와 키보드 포커스는 공유하며, 모든 앱·모든 브라우저 기능의 성공을 보장하지 않습니다. [작업별 지원 범위](macpilot/references/workflows.md)에 백엔드별 제약을 명시합니다.

macOS 14 이상과 Apple Swift 개발 도구가 필요합니다. `macpilot/scripts/macpilot`는 첫 실행에서 로컬 앱을 빌드·ad-hoc 서명합니다. Python·Node.js는 개발 검증용이며 외부 SwiftPM 패키지는 없습니다. Chromium 확장·사이트 접근과 Safari Automation·JavaScript from Apple Events는 별도 활성화가 필요합니다. 화면·시스템 오디오는 [`mac_record`](macpilot/references/recording.md)로 MP4에 녹화하고 검사합니다(macOS 15+). Safari·Chrome 개발자 설정은 [`mac_browser_developer`](macpilot/references/browser-developer-settings.md)로 조회·준비하고 사용자 승인 후 켤 수 있습니다. Codex 개선 요청 전송에는 명시적 목적지 설정과 로그인·모델 연결이 필요합니다. 일반 로컬 제어는 모델을 요구하지 않습니다.

[`mac_connection`](macpilot/references/mcp-recovery.md)으로 서버·부모 프로세스 신원, 권한과 CLI/MCP 호출 경로를 확인합니다. CLI `connection-check`는 기존 서버·Codex를 재시작하지 않고 격리된 새 MCP를 검사합니다. 별도 검사 성공을 현재 대화의 재연결 성공으로 취급하지 않습니다.

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
