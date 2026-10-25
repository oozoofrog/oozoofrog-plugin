# 설치와 개발

WinPilot 0.5.1은 Windows 11 x64용이다. 독립 실행형 ZIP에 .NET 10 Desktop Runtime을 포함한다. 실행에는 SDK·Python·관리자 권한이 필수가 아니다. 대상 앱의 권한은 별도 제약이다. Windows 10은 이번 배포에서 검증하지 않았다.

Plugin은 `winpilot@oozoofrog-plugin`이며 MCP 서버를 함께 등록한다. 0.5.1은 네이티브 UAC 요청을 포함하고 다운로드 진행률 표시의 지연 제거를 유지한다. 첫 연결에서 [설치 스크립트](../scripts/install-runtime.ps1)가 GitHub `winpilot-v0.5.1`의 ZIP SHA-256과 모든 파일 해시를 [manifest](../runtime/distribution.json)와 대조하고 `%LOCALAPPDATA%/WinPilot/0.5.1/`에 설치한다. 다운로드 제한은 120초, MCP 시작 제한은 180초다. 기존 설치의 해시가 다르면 덮어쓰지 않고 중단한다. 인증서 서명·SmartScreen 평판은 제공하지 않는다. 처음 설치할 때 네트워크가 필요하다.

Standalone은 스킬 루트에서 `powershell -NoProfile -File scripts/install-runtime.ps1`로 설치한다. 출력된 절대 실행 파일 경로를 `codex mcp add winpilot -- 실행파일 --stdio`에 지정한다. Plugin MCP와 중복 등록하지 않는다. 현재 대화가 이미 시작됐다면 새 대화에서 도구 노출을 확인한다.

개발에는 .NET 10 SDK와 Python 3이 필요하다. 저장소 루트 기준:

```powershell
powershell -NoProfile -File winpilot/scripts/build.ps1
$env:WINDOWS_PILOT_EXE = "$PWD/winpilot/tool/artifacts/app/windows-pilot.exe"
$env:PYTHONIOENCODING = 'utf-8'
python winpilot/tool/tests/integration.py
python winpilot/tool/tests/foreground.py
python winpilot/tool/tests/verification.py
python winpilot/scripts/package-runtime.py
python scripts/sync_skill_mirrors.py --package winpilot --write
```

GUI 검사는 자체 시험 창에 실제 마우스·키 입력을 보낸다. 검사 중 사용자 입력은 취소를 일으킬 수 있다. `tool/artifacts/`와 `evidence/`는 로컬 기록이며 배포에 포함하지 않는다. 패키징은 검증한 publish 폴더를 사용하고 ZIP 내용과 해시를 다시 검사한다. ZIP 생성 뒤 소스나 바이너리가 바뀌면 관련 검사와 패키징을 다시 수행한다.

이관 출처는 기존 로컬 `windows-pilot` 0.4.0이다. Git 이력이 없는 프로젝트이며 2026-10-18의 게임 검증은 이번 버전의 실기 검증이 아니다. 기존 원본·실험용 native/vendor·개인 캡처·과거 기록은 원래 폴더에 보존한다. 운영 C# 코드와 자체 시험만 이관했다. 게임 전체 캡처 대신 28×28 톱니 표본과 설정 제목 표본만 포함한다.
