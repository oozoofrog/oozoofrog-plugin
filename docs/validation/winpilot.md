# WinPilot 검증

## 0.5.1 네이티브 UAC와 실제 게임 검증

2026-10-25, 실제 실행 중인 마비노기 모바일 PID 4808의 던전 완료 화면에서 검사했다. WGC 1444×1728 캡처와 좌표 매핑은 정상이며 UIA 요소 조회는 worker_error였다.

- 일반 권한의 골드 아이콘 클릭은 `elevation_required`로 입력 전에 거부됐다.
- 기존 PowerShell helper는 한글 UTF-8 JSON을 ANSI로 읽다가 UAC 요청 전에 실패했다. `Start-Process`의 경로 오류도 별도로 기록했다. 이를 Windows UAC 승인 거부로 해석하지 않았다.
- UAC를 실행 파일의 `--elevate-game-click`/`--elevate-game`으로 옮겼다. `ShellExecuteExW(runas)`와 STA COM 초기화를 사용한다. 승인 전후 파일 SHA-256·창 신원·2분 수명·버튼 픽셀을 확인하고 사용자 취소와 Win32 실패 코드를 구분한다. PowerShell은 선택적인 호환 wrapper이며 JSON을 읽거나 runas를 실행하지 않는다.
- 개발 빌드의 네이티브 요청으로 생성된 helper PID 16368의 실제 권한 수준은 High(12288)였다. 골드 아이콘의 단일 클릭과 해제가 전달됐다. 후 화면에 골드·재화·250·구하는 방법·확인 버튼이 나타나 상세 창 열기를 시각적으로 확인했다.
- 원본 보고서는 `dispatched_unverified`, `verified=false` 그대로 보존했다. 별도의 시각 검토 기록에 성공 근거와 원본 JSON·전후 PNG 해시를 기록했다. 관리자 프로세스 생성만으로 게임 효과 성공을 판정하지 않았다.
- 닫기 계획을 만들고 최신 이미지를 확인했을 때 상세 창이 이미 닫혀 있었다. 같은 위치가 재도전 버튼으로 바뀌었으므로 닫기 클릭은 실행하지 않았다. 게임 옵션·보상 사용·재도전 조작을 수행하지 않았다.

최종 0.5.1 빌드는 `build.ps1`의 자체 검사 43개와 `python -X utf8 winpilot/tool/tests/elevation.py`의 손상·한글 만료 계획·승인 전후 변조 거부 3개를 통과했다. 실제 게임 성공 기록은 네이티브 경로 개발 빌드에서 얻었으며, 이후 버전 표기와 공통 launch 함수 분리 뒤 같은 게임 입력을 반복하지 않았다. 기존 0.5.0의 전체 GUI 회귀 결과를 0.5.1의 재실행 결과로 표시하지 않는다.

로컬 근거: `winpilot/evidence/game-20261025/`, `winpilot/tool/artifacts/verification/20261025-080638-ca617f05/`. 개인 화면은 게시하지 않는다. UAC 보안 데스크톱의 승인 UI 자체는 캡처하지 않았으며, 확인한 것은 네이티브 runas 요청 성공과 생성 프로세스의 High 권한이다. 물리 장치 중단·독점 전체 화면·모든 DPI 조합·강제 종료 후 입력 해제는 미검증이다.

API 계약: [Microsoft ShellExecuteExW](https://learn.microsoft.com/en-us/windows/win32/api/shellapi/nf-shellapi-shellexecuteexw), [SHELLEXECUTEINFOW](https://learn.microsoft.com/en-us/windows/win32/api/shellapi/ns-shellapi-shellexecuteinfow).

## 0.5.0 배포 검증 이력

기준: 2026-10-25, Windows x64. 기존 로컬 Windows Pilot 0.4.0에서 운영 소스와 자체 시험을 이관했다. 기존 폴더·개인 화면 캡처·실험 코드는 보존하고 배포에 포함하지 않는다.

## 현재 변경

- 개인 전체 화면 이미지 의존성을 28×28 톱니 표본으로 교체했다. 표본 위치를 바꾼 합성 화면으로 기존 탐색·중복 후보 거부 검사를 유지했다.
- SDK 없는 실행을 위한 self-contained .NET 10 x64 ZIP과 고정 SHA-256 설치기를 추가했다. 정상 설치, 손상 ZIP 거부, 변조 설치 거부, 재설치 시 파일 보존을 검사한다.
- helper의 실행 경로를 `WINDOWS_PILOT_EXE`로 선택할 수 있다. 설치 경로에서도 검증 결과를 찾도록 시험을 수정했다.
- MCP JSON 문서를 즉시 해제하고 전경 활성화 실패에 창 가림·좌표 진단을 추가했다. 입력 방어 조건을 완화하지 않았다.

## 이번 실행 결과

- Release self-contained publish 성공. 입력 없는 자체 검사 43개 통과.
- 사용자가 데스크톱 사용을 멈춘 최종 순차 실행에서 MCP 회귀 15개, 전경 입력 4개, 자동 실행·준비 중 중단 2개가 모두 통과했다. 키 취소 검사는 입력란을 실제 클릭해 전경 상태를 확인한 뒤 키 누름과 해제를 검사한다.
- 자체 캔버스 전경 검사 4개 통과: 실제 선 생성, 중지 버튼, 표식 없는 합성 마우스·키 입력 감지, 버튼 해제와 알림 제거.
- 오프라인 설치 검사 통과: 손상 ZIP 거부·staging 정리, 정상 설치, 설치본 자체 검사 43개, MCP 7개 도구·창 목록, 동일 설치 보존, 변조된 설치 거부.
- 최초 GUI 회귀에서는 `foreground_denied`로 입력 전에 중단됐다. 이후 진단 빌드에서 캔버스 검사가 통과했지만 최초 실패의 외부 전경 상태 원인은 확정하지 않았다. 해당 실패를 성공으로 덮어쓰지 않는다.
- 최초 sandbox 빌드는 NuGet DNS 접근 제한으로 실패했다. 네트워크 접근이 허용된 실행에서는 restore와 publish가 성공했다.
- 저장소 배포 검사 8개, 문서 링크 검사 2개, 미러 동기화 검사 3개와 standalone/Plugin 스킬 검사가 통과했다. Windows에서는 Python UTF-8 모드와 Git 실행 비트 검사를 사용한다.
- 전체 MCP 회귀 재실행은 입력 없는 구간의 외부 커서 이동, 이후 `blocked_desktop`으로 중단된 기록이 있다. 보호된 데스크톱을 우회하지 않았다.

실행 명령: `powershell -NoProfile -File winpilot/scripts/build.ps1`, `python -X utf8 winpilot/tool/tests/integration.py`, `foreground.py`, `verification.py`, `distribution.py` (같은 tests 폴더), `python -X utf8 winpilot/scripts/package-runtime.py`, `python -X utf8 scripts/sync_skill_mirrors.py --package winpilot --write`, `python -X utf8 -m unittest discover -s scripts/tests -p test_plugin_distribution.py`, `test_document_links.py`, `test_sync_skill_mirrors.py` (같은 discover 옵션), skill-creator `quick_validate.py` (정본·미러), Python `compileall`, PowerShell 구문 분석, `git diff --check`.

최종 runtime ZIP SHA-256: `b6151e1047f395e49fa2e833a16b6fe2d5bab891f29d6e73b658556d00378a2d`. ZIP 476개 파일을 해시 manifest와 대조했다. 로컬 상세 기록은 `winpilot/tool/artifacts/`에 보존하며 개인 화면이 포함될 수 있어 게시하지 않는다.

## 공개·설치 확인

소스 커밋 `51d522f57a90c9287703fd5d385e769309df43b1`을 원격 main에 반영하고 annotated tag `winpilot-v0.5.0`을 게시했다. [GitHub Release](https://github.com/oozoofrog/oozoofrog-plugin/releases/tag/winpilot-v0.5.0)의 ZIP과 SHA256SUMS.txt를 다시 내려받아 업로드 전 원본과 바이트 단위로 비교한 뒤 공개했다.

`codex plugin marketplace upgrade oozoofrog-plugin --json`과 `codex plugin add winpilot@oozoofrog-plugin --json`으로 원격 배포본을 설치했다. 설치 경로는 `%USERPROFILE%/.codex/plugins/cache/oozoofrog-plugin/winpilot/0.5.0`이다. 설치 파일 36개의 Git blob을 위 커밋과 대조했다. `codex plugin list --marketplace oozoofrog-plugin --json`에서 설치·활성화를 확인했고 기존 Plugin의 버전·활성화 상태를 전후 비교했다.

실제 설치된 `.mcp.json`의 PowerShell 진입점을 실행해 버전 0.5.0, 도구 7개, 창 목록 조회를 확인했다. runtime은 `%LOCALAPPDATA%/WinPilot/0.5.0`에 설치했다. 기존 standalone 스킬은 중복 선택을 피하도록 `%USERPROFILE%/.codex/skills-archive/windows-pilot-0.4.0-before-winpilot-0.5.0`으로 옮기고 두 파일의 해시를 확인했다. 기존 개발 프로젝트와 개인 기록은 변경하지 않았다.

현재 대화의 재연결과 새 대화에서의 자동 스킬 선택은 검증하지 않았다. 위 검사는 설치된 서버의 별도 stdio 연결 검사다.

공개 URL에서 비어 있는 경로로 설치하는 최초 검사는 약 2분 걸렸다. Windows PowerShell의 진행률 표시를 끈 Plugin build `0.5.0+codex.20261025.1`은 같은 공개 ZIP의 새 경로 다운로드·전체 파일 검증·설치를 7.05초에 완료했다. 다운로드는 120초로 제한하고 MCP 시작 제한은 180초로 설정했다. 바이너리·ZIP·runtime manifest 해시는 변경하지 않았다.

## 범위와 제한

자체 시험 창의 결과는 실제 게임 검증을 대신하지 않는다. 2026-10-18의 게임 실행·설정 화면 기록은 이전 버전의 이력이다. 이번 버전에서 실제 게임, UAC, 물리 장치로 발생시킨 중단, 독점 전체 화면, 모든 DPI 조합과 강제 worker 종료 후 입력 해제를 검증하지 않았다. 배포 실행 파일은 인증서 서명되지 않았다.

Plugin 설치·활성화, 원격 카탈로그 반영, 실제 런타임 동작과 새 대화의 도구 노출은 별도 증거다. 현재 대화의 도구 목록이 갱신됐다고 간주하지 않는다.
