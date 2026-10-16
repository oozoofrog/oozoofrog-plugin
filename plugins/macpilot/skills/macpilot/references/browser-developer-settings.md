# 브라우저 개발자 설정

`mac_browser_developer`는 실제 브라우저 UI에서 설정을 읽고, 사용자가 네이티브 확인 대화상자의 **허용**을 누르면 선택한 설정 하나를 켠다. `approved=true`나 환경변수로 승인을 대신하는 경로는 없다. 에이전트는 이 대화상자에 AX·키보드·마우스 입력을 보내지 않는다. 다른 도구로 대화상자를 조작할 수 없는 보안 경계를 보장하는 기능은 아니다.

| browser | setting | 변경 범위 |
| --- | --- | --- |
| `safari` | `developer_features` | 현재 macOS 사용자의 Safari 웹 개발자 기능 |
| `safari` | `javascript_apple_events` | Safari에서 Apple Events를 통한 웹페이지 JavaScript 실행 허용 |
| `chrome` | `extension_developer_mode` | 선택한 Chrome 창이 사용하는 프로필의 확장 개발자 모드 |

Safari 개발자 기능과 Apple Events JavaScript 허용은 별도 설정이다. JavaScript 설정의 Developer 탭이 없으면 먼저 `developer_features`를 별도 승인으로 켠다. Chrome의 확장 개발자 모드는 DevTools 열기나 remote debugging 활성화와 다르다.

## 호출

`mac_apps`에서 실제 브라우저의 `pid`와 `processStartID`를 얻는다. Chrome은 `mac_windows`의 정확한 `windowID`도 전달한다. 창 ID로 프로필 범위를 고정하며 프로필 이름은 검증하지 않는다. Safari 설정은 사용자 범위이므로 `windowID`를 전달하지 않는다.

1. `operation=status`는 현재 열린 설정 UI를 읽는다. UI가 없거나 해당 탭이 선택되지 않았으면 `settings_ui_required`를 반환한다. `enabled=false`로 추정하지 않는다.
2. `operation=prepare`는 Safari Settings의 Advanced·Developer 탭 또는 Chrome의 확장 관리 화면을 연다. 토글은 변경하지 않는다. Chrome에서는 선택한 창을 전경으로 올릴 수 있다.
3. `operation=enable`은 준비 후 현재 값이 OFF인 경우에만 승인 대화상자를 표시한다. 대화상자에는 브라우저·PID·시작 ID·창·설정·변경 범위를 표시한다. 기본 버튼은 **취소**다. 승인 대기 시간은 `timeoutMs=5000..120000`이며 기본값은 60000이다.
4. 승인 후 프로세스·설정 창·토글 정체성을 다시 확인한다. AXPress를 한 번 실행한 뒤 새 AX 값을 읽는다. 이미 ON이면 다시 누르거나 승인 대화상자를 표시하지 않는다.

`prepare`·`enable`은 전경 변경이 가능하다. 작업을 지정할 때 `mac_task begin`의 `preserveForeground=false`를 사용한다. `status`는 전경을 바꾸지 않는다. 별도 CLI 호출에서도 같은 도구 이름과 인수를 사용한다.

```sh
./scripts/macpilot call mac_browser_developer --json /absolute/path/browser-settings-request.json
```

요청 파일에는 `operation`, `browser`, `setting`, `pid`, `processStartID`를 넣는다. Chrome 요청에만 `windowID`를 추가한다. PID·창 ID·시작 ID는 현재 조회 결과를 사용하며 예전 실행값을 재사용하지 않는다.

## 결과와 제한

- `settings_status`: 선택한 체크박스의 `enabled`와 `canEnable`을 읽었다.
- `already_enabled`: 현재 값이 이미 ON이다. 새 승인을 받거나 토글을 누르지 않았다.
- `approval_declined`: 취소 또는 승인 시간 초과다. 도구는 설정을 누르지 않았다. 이 결과의 `enabled`는 `null`이며 현재 상태가 필요하면 다시 조회한다.
- `enabled_verified`: 승인 후 선택한 체크박스가 ON임을 다시 확인했다. `approval=native_dialog_accepted`는 로컬 확인 결과이며 서명된 사람 인증 증거가 아니다.
- `settings_target_changed`: 승인 대기 중 대상이 바뀌었다. 설정을 다시 준비하고 새 승인을 받아야 한다.
- `settings_outcome_unconfirmed`·`ax_outcome_uncertain`: 이미 전송한 동작을 반복하지 않는다. 상태를 다시 조회한다. 브라우저가 자체 확인창을 띄우면 사용자가 직접 확인한다.

현재 UI 어댑터는 한국어·영어 메뉴와 라벨을 지원한다. 다른 언어·버전, 기업 관리 정책, 불완전한 AX 트리는 실패로 반환한다. Chrome은 정확한 창의 `chrome://extensions/` AXWebArea 안에서만 개발자 모드를 선택한다. 웹페이지의 유사 체크박스를 누르지 않는다. Safari는 네이티브 설정 pane 안에서만 선택한다.

이 도구는 확장 설치·사이트 접근 허용·native host 등록·Automation TCC 동의·remote debugging·원격 자동화·출처 간 제한·로컬 파일 제한·서명되지 않은 확장을 변경하지 않는다. 설정이 ON이라는 결과와 실제 DOM 자동화 성공은 별도로 확인한다. 승인·취소·시간 초과가 이미 끝난 설정 변경을 되돌리지는 않는다.

## 근거와 검증

- [Apple: 웹 개발자 기능 활성화](https://developer.apple.com/documentation/safari-developer-tools/enabling-developer-features): Settings → Advanced → Show features for web developers.
- [Apple: Developer 설정](https://developer.apple.com/documentation/safari-developer-tools/developer-settings): Apple Events JavaScript와 다른 개발자 설정의 범위.
- [Chrome: unpacked 확장 개발](https://developer.chrome.com/docs/extensions/get-started/tutorial/hello-world#load-unpacked): 확장 관리 화면의 Developer mode.

2026-10-17에 실제 Safari의 이미 켜진 JavaScript 설정 조회와 격리 Chrome의 OFF→ON UI 동작을 검증했다. Chrome의 실제 네이티브 승인 시간 초과와 테스트 내부의 승인 주입을 구분한다. Safari의 OFF→ON과 사람이 허용을 누르는 전체 경로는 별도 실제 검증이 필요하다. 반복 가능한 개발 검증은 `python3 macpilot/scripts/verify_browser_developer.py`이며 개인 프로필은 사용하지 않는다. 이 검증은 전경을 바꾸고 5초 승인 대화상자를 표시한다. 검증 기록은 `evidence/developer-settings-*/`에 남긴다.
