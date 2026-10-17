# 권한 요청과 앱 드래그 설정

사용자가 권한 설정을 요청하면 `mac_doctor`로 현재 MCP의 권한을 확인한다. `mac_permission`의 기본 동작은 시스템 요청 창을 띄운다. 요청 수락은 권한 부여가 아니다. `granted=false`이면 같은 요청을 반복하지 말고 드래그 설정 창을 사용한다.

`mac_permission`은 전경을 사용할 수 있는 작업에서 실행하며, 작업을 분리했다면 `preserveForeground=false`가 필요하다. 다른 작업의 시스템 입력 잠금이 사용 중이면 실행 전에 `busy`로 중단한다. `mac_doctor`의 읽기 검사는 백그라운드 유지 작업에서도 사용할 수 있다.

```json
{"kind":"accessibility","operation":"setup"}
```

현재 MCP에 `operation=setup`이 없으면 설치된 스킬 폴더에서 CLI를 실행한다.

```sh
./scripts/macpilot permission-setup accessibility
./scripts/macpilot permission-setup screenCapture
```

`MacPilot.app`을 Finder에서 열어도 같은 창이 열린다. 창은 실행한 앱 번들의 실제 파일 URL을 드래그 항목으로 제공한다. 화면 왼쪽에 안내 창을 표시하고 선택한 개인정보 보호 설정을 연다. 사용자는 앱을 설정 목록으로 드래그한 뒤 스위치를 켠다. 드롭이 지원되지 않으면 설정 목록의 ＋와 창의 `Finder에서 보기`를 사용한다. macOS가 호스트 앱을 요청하면 해당 앱도 사용자가 허용한다.

`setup`의 `kind`는 `accessibility`와 `screenCapture`만 지원한다. `postEvent`는 기존 `request` 동작을 사용한다. 기본 `operation=request`와 기존 인수는 유지한다. `timeoutMs`는 요청 또는 안내 앱 실행을 기다리는 시간이며 사용자 승인 기한이 아니다. 실행 시간 초과 뒤에도 창이 열릴 수 있으므로 재실행 전에 확인한다.

MCP의 `permission_setup_launch_accepted`는 앱 실행 요청 수락이다. 창의 `허용됨` 표시는 **안내 창 프로세스**의 사전 검사 결과다. 드롭 수락·안내 창 권한·호출한 MCP 권한을 구분하고, 사용자가 허용한 뒤 현재 MCP의 `mac_doctor`를 다시 호출한다. macOS가 재시작을 요구하면 해당 앱을 재실행한다. 다른 대화나 전체 호스트를 진단 때문에 임의 종료하지 않는다.

파일 URL은 전용 드래그 pasteboard에만 전달한다. 일반 클립보드·TCC 데이터베이스·권한 스위치는 수정하지 않는다. 승인 대화상자는 사용자가 직접 승인한다. raw SwiftPM 실행 파일은 앱 드래그 대상으로 사용하지 않으며 서명된 `bin/MacPilot.app`을 먼저 빌드한다.
