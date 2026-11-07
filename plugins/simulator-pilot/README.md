# simulator-pilot

iOS 시뮬레이터 작업의 단일 입구입니다. 앱 빌드·설치·실행과 로그, 화면 요소 읽기와 탭·입력, 사진·위치·권한 같은 테스트 데이터, 고친 동작이 앱에서 되는지 확인까지 한 스킬로 처리합니다. CLI 빌드에는 Xcode를 쓰고 화면 조작에는 mac-computer-use Plugin이 필요합니다. Claude Code와 Codex에서 씁니다.

## 설치

```bash
/plugin install simulator-pilot@oozoofrog-plugin
/plugin install mac-computer-use@oozoofrog-plugin   # 화면 조작에 필요 (mac-cu MCP 서버)
```

- `sim-pilot` CLI는 처음 쓸 때 스킬이 `swiftc`로 빌드해 `~/.local/bin/sim-pilot`에 둡니다.
- 화면 조작은 mac-computer-use의 `simulator` 도구를 씁니다. 화면 요소 읽기(`describe`·`wait`·`tap target`)는 mac-computer-use 1.10.0부터 있습니다. 입력 동작은 Xcode 27 이상이 필요합니다.

## 쓰는 예

- "시뮬레이터에서 Sandbox 실행하고 AccountList 로그만 보여 줘"
- "설정 → 일반 → 정보 들어가서 스크린샷"
- "시뮬레이터에 사진 20장 넣어 줘"
- "고친 다크 모드 말풍선이 앱에서 제대로 보이는지 확인해 줘"

## 구성

| 파일 | 내용 |
|---|---|
| `skills/simulator-pilot/SKILL.md` | 준비 확인, 기기 고르기, 요청별 문서 안내 |
| `skills/simulator-pilot/references/drive.md` | 화면 조작 (mac-cu `simulator`) |
| `skills/simulator-pilot/references/launch-and-log.md` | 실행·로그 (`sim-pilot launch`·`logs`·`console`) |
| `skills/simulator-pilot/references/test-data.md` | 사진(`sim-pilot photos`)·위치·권한·푸시 등 |
| `skills/simulator-pilot/references/verify.md` | 변경 확인 흐름 |
| `skills/simulator-pilot/references/fallbacks.md` | 도구가 없을 때 |
| `skills/simulator-pilot/tool/sim-pilot.swift` | Swift CLI (devices, schemes, launch, logs, console, photos) |

## 대체한 플러그인

`axe-simulator`(`/axe`), `simlog`(`/simlog`), `picsum-importer`(`/insert-images-to-sim`)는 이 플러그인으로 옮겼습니다. 외부 `axe` CLI·Node·Go가 더 이상 필요 없습니다.
