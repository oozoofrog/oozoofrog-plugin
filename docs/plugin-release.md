# Plugin 배포

MacPilot 전용 릴리스 스크립트·프로필과 그 검사는 제거했습니다. 새 패키지는 이전 런타임의 바이너리 고정·서명·실행 보고서 계약을 사용하지 않습니다.
이 문서는 로컬 배포 준비 절차이며 커밋·푸시·릴리스 게시·사용자 설치는 요청한 권한 범위에서 별도로 수행합니다.

## mac-computer-use와 simulator-pilot

원본 사용자 제공 패키지 구조를 유지합니다. `mac-computer-use/`와 `simulator-pilot/`에서 수정하고 아래 명령으로 전체 Plugin 미러를 갱신합니다.
두 manifest(`.codex-plugin/plugin.json`, `.claude-plugin/plugin.json`)의 버전·설명을 맞추고 스킬·UI metadata·README·CHANGELOG를 함께 갱신합니다.
긴 운영 지침은 `references/`에 둡니다. 미러는 개발 증거, 캐시, 생성 바이너리, 개인 프로필·허용 목록을 제외합니다. 원본의 해당 자료는 보존합니다.

```sh
python3 scripts/sync_skill_mirrors.py --package mac-computer-use --package simulator-pilot --write
python3 -m unittest discover -s scripts/tests -v
python3 scripts/sync_skill_mirrors.py --package mac-computer-use --package simulator-pilot
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py mac-computer-use/skills/mac-computer-use
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/mac-computer-use/skills/mac-computer-use
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py simulator-pilot/skills/simulator-pilot
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/simulator-pilot/skills/simulator-pilot
git diff --check
```

통과한 배포 검사는 파일·메타데이터·로컬 링크의 일관성을 확인합니다. mac-cu setup 실행, 사용자 권한 설정, MCP 연결, 앱 UI 및 Simulator 동작은 증명하지 않습니다.
전경 desktop 시험은 잠금 해제된 대화형 desktop에서 직렬 실행하고 입력 보호 조건을 유지합니다. LCD 창은 [격리 네이티브 검증](mac-cu-device-window-validation.md)에 따라 별도 bundle의 앱으로 확인하며, 사용자 전역 앱·설치 캐시를 교체하지 않습니다.
게시가 요청되면 해당 변경만 검토해 커밋·푸시한 뒤 원격 `.agents/plugins/marketplace.json`과 manifest를 확인합니다.
설치가 요청되면 선택 marketplace source와 설치본 경로·파일을 확인하고 새 세션 노출·실제 동작을 별도로 검증합니다.
[설치와 전환](plugin-installation.md#mac-computer-use-and-simulator-pilot)을 따릅니다.

## 다른 Plugin

WinPilot은 [Windows 개발·배포 절차](../winpilot/references/development.md)를 따릅니다.
각 Plugin의 실제 런타임·패키징 요구 사항은 그 패키지의 지침을 사용하며 새 패키지에 일반화하지 않습니다.

## Native decision and toolbar checks

```sh
swiftc mac-computer-use/skills/mac-computer-use/scripts/mac-cu-src/DecisionService.swift mac-computer-use/tests/decision-service-selfcheck.swift -o /tmp/mac-cu-decision-check
/tmp/mac-cu-decision-check
python3 mac-computer-use/tests/check-decision-answer.py
swiftc -parse-as-library mac-computer-use/skills/mac-computer-use/scripts/mac-cu-src/DecisionService.swift mac-computer-use/skills/mac-computer-use/scripts/mac-cu-src/DecisionSettingsWindow.swift mac-computer-use/tests/decision-settings-selfcheck.swift -o /tmp/mac-cu-decision-settings-check
/tmp/mac-cu-decision-settings-check
bash mac-computer-use/tests/check-simulator-gestures.sh
```

These checks use synthetic data and isolated preferences. They do not establish real API credentials or physical pointer/keyboard behavior. Follow the [native window validation procedure](mac-cu-device-window-validation.md) for an isolated app and serialized desktop checks.
