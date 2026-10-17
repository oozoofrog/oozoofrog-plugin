# 권한이 없는 앱의 실제 검증

검증은 기존 설치본의 권한을 초기화하지 않고 별도 bundle ID의 앱으로 수행한다. `verify_permissions_none.py`는 현재 `MacPilotCore` 소스를 그대로 컴파일하고 파일별 SHA256을 기록한다. 검증용 진입점이 같은 권한 안내 컨트롤러를 실행한다. 배포 바이너리의 동일 ID·서명이나 모든 OS를 검증했다는 뜻은 아니다.

## 시작

```sh
python3 macpilot/scripts/verify_permissions_none.py
```

출력에 표시된 `evidenceDirectory`가 해당 실행의 근거 폴더다. 실행기는 다음을 검사하고 검증 앱을 열어 둔다.

- 접근성·화면 캡처·이벤트 전송·입력 모니터링의 실제 사전 검사 결과가 모두 `false`다. 하나라도 허용이면 무권한 실행으로 인정하지 않는다.
- Safari Automation의 사전 검사 결과를 별도로 기록한다. 이 단계에서는 동의를 요청하지 않는다.
- 자동 추가 메뉴가 비활성화된다. 해당 동작을 직접 호출해도 실제 입력 전에 `event_post_denied`로 차단된다.
- 권한 항목 8개의 시연 대상·직접 드래그 가능 여부와 기본 이전·다음 순서가 맞는다.
- 전환 후에도 실제 사전 검사 결과가 계속 `false`다.

전체 디스크 접근은 일반 사전 검사 API가 없다. 파일·붙여넣기 권한도 시스템 전체 허용 여부로 환산하지 않는다. 검증 앱은 개인 파일이나 일반 클립보드를 읽지 않으며, 해당 항목을 `not_generically_queryable`·`not_requested`·`not_read`로 기록한다.

## 실시간 동작과 종료

```sh
python3 macpilot/scripts/permission_probe_control.py /absolute/evidenceDirectory inspect
python3 macpilot/scripts/permission_probe_control.py /absolute/evidenceDirectory replay
python3 macpilot/scripts/permission_probe_control.py /absolute/evidenceDirectory select --kind screenCapture
python3 macpilot/scripts/permission_probe_control.py /absolute/evidenceDirectory quit
```

`request`는 검증 앱의 실제 macOS 요청을 한 번 실행한다. 새 보안 권한을 부여하지 않으며 동의 버튼은 사용자가 직접 선택한다. 이 명령은 기본 자동 검사에 포함하지 않는다. 종료는 해당 검증 앱만 대상으로 한다. 다른 앱·MCP·호스트를 재시작하지 않는다.

실제 파일 URL 드래그는 `verify_permission_drag.swift`로 소유한 테스트 창에만 전송한다. PID·시작 ID·창 ID·관찰한 좌표·실제 앱 경로를 사용하고, 검증 앱의 정확한 bundle ID를 마지막 선택 인수로 준다. 기본값은 `local.macpilot`다. 시스템 설정의 권한 목록이나 허용 버튼에는 입력을 보내지 않는다.

시연 중 드래그를 시작한 경우에는 `onboarding.playing → userInteracted=true, playing=false` 전환과 받은 URL을 함께 기록한다. 영상은 별도 권한이 있는 관찰 프로세스가 캡처한다. 녹화 성공을 검증 앱의 화면 캡처 권한으로 해석하지 않는다.

## 격리 조건

앱과 실시간 로그·명령·상태는 내부 임시 경로에 둔다. 기존 호스트가 근거를 저장소로 복사한다. 검증 앱이 외장 볼륨에 로그를 쓰면 제거 가능한 볼륨의 동의를 요구하여 실험을 오염시킬 수 있다.

직접 셸 자식으로 앱 실행 파일을 실행하면 호스트의 권한을 물려받을 수 있다. `permission_probe_launcher.swift`의 `NSWorkspace` 앱 실행과 실제 사전 검사 결과를 함께 사용한다. 허용 결과를 가짜 `false`로 바꾸지 않는다. 앱이 준비되기 전에 실패하거나 요청 UI에 막힌 실행은 성공으로 처리하지 않는다.

`baseline.json`, `automation-baseline.json`, `automatic-report.json`, `response-*.json`, `final.json`과 원시 빌드·실행 로그를 보존한다. 검증용 ID의 실제 승인과 기존 설치본의 승인은 별도다. 사용자 동의·인증·재실행과 최종 설치 여부도 별도로 보고한다.
