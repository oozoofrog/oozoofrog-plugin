# oozoofrog-plugin

ChatGPT Chat·Work 상담과 응답 회수를 위한 `gptplease`, Swift 의미론 탐색용 `swift-intelligence`, 로컬 모델 설치·실행용 `local-ai-studio`, macOS·브라우저 제어와 화면·시스템 오디오 녹화용 `macpilot`를 제공합니다.

## GPT Please

`gptwork`를 **gptplease**로 이름 변경하고 Chat·Chat Pro 상담과 목적·복잡도에 따른 모델·사고 수준 선택을 통합했습니다. 기존 `gptpro` Skill·Plugin·전용 Runner/전송 런타임 및 전용 설치 도구는 제거했습니다. 과거 상담 패키지·로그인 프로필을 삭제하거나 새 스킬로 이관하지 않습니다.

```text
$gptplease Chat Pro로 선택한 파일을 검토하고 완료 응답을 여기서 처리해주세요.
$gptplease Work에서 Astra로 이 기획안을 검토하고 답변을 가져와 주세요.
```

- Chat·Work의 실제 선택기에서 목적·복잡도·시간 및 비용 제한에 맞는 모델과 사고 수준을 고릅니다. Work는 실제 제공되는 GPT-6 Luna High·Sol Medium/High·Astra High/Extra High를 작업에 맞춰 선택하고, Chat은 실제 Chat 후보만 사용합니다. 화면별 모델·effort를 일괄 치환하지 않습니다.
- 모델·사고 수준을 명시하면 그대로 지키고 나머지만 자동 선택합니다. `Chat Pro`는 Pro를, `Chat Astra Pro`는 모델까지 요구합니다. 명시한 조합이 없으면 전송을 보류합니다.
- 모드를 생략한 새 요청은 Work를 사용합니다. 자동 선택은 같은 모드의 가용 후보 안에서 조정하며 Ultra·Fast/priority를 자동 활성화하지 않습니다.
- 승인된 파일은 실제 업로드하며, 같은 입력창에서 모드·설정·첨부를 확인한 뒤 한 번 전송합니다.
- 호출 세션이 최종 응답 완료를 기다리고 전체 내용을 읽어 검토·답변·허용된 수정을 이어갑니다.

지원되는 브라우저 제어와 ChatGPT 로그인이 필요합니다. 번들 상담 모듈은 같은 브라우저 도구 세션에서 실행되며, Codex 모델·provider 설정을 바꾸거나 별도 서버를 열지 않습니다. [전송 계약](gptplease/references/transport-contract.md)과 [실제 검증 범위](gptplease/references/runtime-validation.md), [설치·계정 검증 기록](docs/gptplease-transport-validation.md)를 참고하세요. 기존 패키지의 자동 비밀정보 검사·불변 승인·영구 전송 기록·서명 스트림/전용 복구를 제공한다고 주장하지 않습니다. 코드 상담과 응답 회수 용도를 통합한 것이며, 공개 범위와 독립 검증은 호출 세션이 책임집니다. [사용 안내](gptplease/README.md), [모델 선택](gptplease/references/model-selection.md), [입력창 설정](gptplease/references/composer-settings.md), [파일 첨부](gptplease/references/file-attachments.md)를 참고하세요.

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

원본은 [macpilot/](macpilot/), 배포 사본은 [Plugin 스킬](plugins/macpilot/skills/macpilot/SKILL.md)에서 관리합니다. `3.0.0`은 Swift 코어·CLI·MCP, 작업 격리·취소·포커스, 라이브 캡처·오버레이, 파일·Finder 태그·CoreAudio, Chromium 확장과 Safari Apple Events, 로컬 개선 요청 대기열·Codex app-server 전송을 포함합니다. 실제 OS 커서와 키보드 포커스는 공유하며, 모든 앱·모든 브라우저 기능의 성공을 보장하지 않습니다. [작업별 지원 범위](macpilot/references/workflows.md)에 백엔드별 제약을 명시합니다.

macOS 14 이상과 Apple Swift 개발 도구가 필요합니다. `macpilot/scripts/macpilot`는 첫 실행에서 로컬 앱을 빌드·ad-hoc 서명합니다. Python·Node.js는 개발 검증용이며 외부 SwiftPM 패키지는 없습니다. Chromium 확장·사이트 접근과 Safari Automation·JavaScript from Apple Events는 별도 활성화가 필요합니다. 화면·시스템 오디오는 [`mac_record`](macpilot/references/recording.md)로 MP4에 녹화하고 검사합니다(macOS 15+). Safari·Chrome 개발자 설정은 [`mac_browser_developer`](macpilot/references/browser-developer-settings.md)로 조회·준비하고 사용자 승인 후 켤 수 있습니다. Codex 개선 요청 전송에는 명시적 목적지 설정과 로그인·모델 연결이 필요합니다. 일반 로컬 제어는 모델을 요구하지 않습니다.

현재 MCP 도구가 필요한 기능을 제공하면 직접 사용하고, 구버전이면 이 스킬의 CLI를 사용합니다. Plugin은 전역 스킬·MCP 설정·사용자 브라우저 프로필을 자동 교체하지 않습니다. 원격 게시·설치·활성화·새 세션 노출은 별도입니다. [스킬 본문](macpilot/SKILL.md), [CLI·MCP](macpilot/references/tools.md), [개발·검증](macpilot/references/development.md), [설치 안내](docs/plugin-installation.md#macpilot)를 참고하세요.

이후 변경은 원본에서 수행하고 `python3 scripts/sync_skill_mirrors.py --package macpilot --write`로 배포 사본에 반영합니다. 바이너리·빌드 캐시·화면·로그 증거는 Git과 배포 사본에서 제외합니다.

## Swift Intelligence

`swift-intelligence`는 Xcode의 SourceKit-LSP로 Swift 정의, 참조, 구현, 타입, 심볼 및 진단을 읽기 전용으로 조회합니다. MCP 서버가 필요한 Plugin이므로 `plugins/swift-intelligence/`에만 제공합니다. Python 3 외의 Python 패키지나 외부 MCP 바이너리를 추가로 설치하지 않습니다.

## 과거 검증 기록

제거된 스킬의 배포·실행 검증은 당시 기록으로 보존합니다. [모델 정책 검토](docs/model-routing-review.md)와 [검증 기록](docs/model-routing-validation.md)은 현재 제공 기능과 구분해서 읽으세요. `scripts/model_routing_eval.py`는 기존 합성·관측 기록을 검사하는 오프라인 도구입니다.

## 설치

필요한 Plugin만 선택해 설치합니다. 아래 명령은 해당 변경이 원격 marketplace에 반영된 뒤 사용할 수 있습니다.

```bash
codex plugin marketplace add oozoofrog/oozoofrog-plugin --ref main
codex plugin add gptplease@oozoofrog-plugin
codex plugin add swift-intelligence@oozoofrog-plugin
codex plugin add local-ai-studio@oozoofrog-plugin
codex plugin add macpilot@oozoofrog-plugin
```

설치 후 새 대화에서 `$gptplease`를 호출합니다. 이전 `gptwork`/`gptpro` 설치본의 중복 노출을 정리하되 과거 패키지와 계정 프로필은 보존합니다. 다른 Plugin의 요구 사항과 standalone 설치는 [Plugin 설치 안내](docs/plugin-installation.md)를 참고하세요.

## 검증

```bash
python3 -m unittest discover -s scripts/tests -v
python3 scripts/sync_skill_mirrors.py --package gptplease
node --test gptplease/tests/*.test.mjs
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py gptplease
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
