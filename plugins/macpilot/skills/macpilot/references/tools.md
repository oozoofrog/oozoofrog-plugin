# 도구 사용법

아래 CLI 예시는 설치되거나 체크아웃된 `macpilot/` 스킬 디렉터리를 현재 디렉터리로 사용한다. Plugin 설치본에서도 해당 스킬 디렉터리의 `scripts/macpilot`를 사용한다. MCP 클라이언트 설정에는 실제 설치 위치 또는 새 설치본을 가리키는 안정된 launcher의 절대 경로를 지정한다. 버전별 캐시 경로를 직접 지정했다면 [설치본 갱신](mcp-recovery.md)의 경로 보존을 확인한다.

## 실행과 빌드

```sh
./scripts/macpilot doctor
./scripts/macpilot tools
./scripts/macpilot connection-check
./scripts/macpilot permission-setup accessibility
./scripts/build.sh
```

빌드에는 Xcode 또는 Swift를 포함한 Apple 개발 도구가 필요하다. SwiftPM의 외부 의존성은 없다. 빌드한 실행 파일은 `bin/MacPilot.app/Contents/MacOS/macpilot`에 있다. 런처는 실행 파일이 없거나 `Package.swift`, `build.sh`, Swift 소스가 설치된 실행 파일보다 새로우면 원자적으로 다시 빌드한다. 릴리스 검증은 타임스탬프 판단에 의존하지 않고 `build.sh`를 직접 실행한다.

CLI는 성공 시 JSON을 stdout에 출력한다. 인수·권한·대상 오류는 JSON 오류와 종료 코드 2를 반환한다. 도움말은 일반 텍스트다. 빌드 로그는 stderr로 출력한다.

`permission-setup [KIND] [TARGET_BUNDLE_ID]`은 macOS 시스템 설정과 옆에 붙는 작은 아이콘 안내 패널을 연다. 기본 KIND는 `all`이며 접근성·화면·Safari Automation을 순서대로 안내한다. 사용자가 직접 드래그하거나 ‘자동으로 추가’를 선택한다. Finder나 큰 설정 대시보드는 열지 않는다. MCP는 `mac_permission operation=setup kind=all`을 사용한다. 지원 항목과 승인·재검사는 [권한 설정](permission-setup.md)을 따른다.

`mac_connection`의 `status`는 현재 프로세스·부모 신원과 호출 경로를 반환한다. `probe`와 CLI `connection-check`는 기존 연결을 변경하지 않고 격리된 MCP 자식을 검사·정리한다. 현재 MCP 호출 실패와 별도 CLI 성공을 구분하는 방법은 [연결 진단과 복구](mcp-recovery.md)를 따른다.

```sh
printf '%s\n' '{}' | ./scripts/macpilot call mac_apps --json -
```

큰 JSON과 사용자 문자열은 파일이나 stdin으로 전달한다. 셸 명령 문자열에 보간하지 않는다. `call TOOL --json /absolute/request.json`도 지원한다. 모든 도구의 정확한 schema는 `tools` 출력으로 확인한다.

## 관찰 예시

`mac_apps`에서 확인한 실제 PID와 `processStartID`, `mac_windows`의 창 ID를 사용한다. 관찰, 앱 상태 변경과 메뉴 실행에는 PID와 같은 행의 `processStartID`를 함께 전달한다. 이 값은 재시작되거나 재사용된 PID로 다른 프로세스를 읽거나 조작하는 일을 차단한다. 아래 숫자와 시작 ID는 요청 형식을 보여주는 예시이며 실제 대상이 아니다.

```json
{"pid":12345,"processStartID":"1770000000.123456","windowID":67890,"screenshot":true,"maxNodes":200,"maxDepth":10}
```

이 JSON을 `mac_observe`에 전달하면 다음 정보가 반환된다.

- `observation.id`: 다음 입력에 사용할 UUID
- `observation.nodes`: 창 내부의 AX 노드, 노드 경로, 역할, 식별자, 지원 동작, 제한된 값
- `observation.coverage`, `diagnostics`: 수집 범위와 잘린 이유
- `observation.screenshot`: 로컬 PNG의 절대 경로
- `observation.windowFrame`: 전역 논리 좌표
- `observation.pixelWidth`, `pixelHeight`: PNG 픽셀 크기
- `foregroundPID`: 실제 전경 앱. 선택한 대상 PID와 다를 수 있다.

창의 전역 좌표와 PNG 픽셀을 혼용하지 않는다. `space=window`는 창 왼쪽 위 기준 논리 포인트다. `space=screen`은 화면 전역 논리 포인트다. `space=image`는 PNG 왼쪽 위 기준 픽셀이다. `space=normalized`는 각 축의 `[0,1)` 범위다. 음수 전역 좌표가 있는 다중 모니터를 지원한다.

AX 트리는 선택한 창 내부만 수집한다. 메뉴 막대의 전역 트리, 다른 창, 가상화되어 아직 표시되지 않은 목록 항목까지 수집했다는 의미가 아니다. 키보드 단축키로 메뉴를 열거나 화면을 스크롤한 뒤 새 관찰을 얻는다.

## 입력 예시

아래 UUID와 노드 ID는 실제 관찰 값으로 교체한다. 도구는 `OBSERVATION_UUID` 같은 문자열을 유효한 UUID로 인정하지 않는다.

| 도구 | 인수 형식 | 결과의 의미 |
|---|---|---|
| `mac_ax` | `{"observation":"UUID","node":"0.1","operation":"action","action":"AXPress"}` | AX가 요청을 수락함. 후속 관찰 필요 |
| `mac_ax` | `{"observation":"UUID","node":"0.2","operation":"set_value","text":"입력 문자열"}` | 전체 값을 교체하고 문자열 일치 검사 |
| `mac_ax` | `{"observation":"UUID","node":"0.2","operation":"focus"}` | 대상 앱 내부의 AX 포커스 설정 |
| `mac_ax` | `{"observation":"UUID","node":"0.2","operation":"select_range","start":0,"length":3}` | UTF-16 범위 선택 및 재조회 |
| `mac_pointer` | `{"observation":"UUID","x":0.5,"y":0.5,"space":"normalized"}` | 실제 macOS 화면 위의 가상 화살표를 이동. 시스템 입력 없음 |
| `mac_click` | `{"observation":"UUID","x":100,"y":80}` | 기본 accessibility 경로. 좌표를 포함하는 고유한 AXPress 컨트롤 동작 |
| `mac_click` | `{"observation":"UUID","x":100,"y":80,"route":"process"}` | PID 대상 클릭 전송. 앱 수신은 미확인 |
| `mac_drag` | `{"observation":"UUID","x":100,"y":80,"toX":240,"toY":80,"duration":0.35}` | 창 내부 드래그 전송 |
| `mac_scroll` | `{"observation":"UUID","x":100,"y":180,"vertical":-3}` | 해당 지점으로 아래쪽 스크롤 전송 |
| `mac_key` | `{"observation":"UUID","node":"0.2","key":"a","modifiers":["command"]}` | 현재 포커스 노드에 물리 키 조합 전송 |
| `mac_type` | `{"observation":"UUID","node":"0.2","text":"한글 😀"}` | 현재 포커스 노드에 Unicode 이벤트 전송 |
| `mac_find` | `{"observation":"UUID","identifier":"save-button"}` | 관찰에 저장된 제한된 AX 노드를 정확한 조건으로 필터링 |
| `mac_wait` | `{"observation":"UUID","node":"0.2","equals":"완료","timeoutMs":5000}` | 선택한 live AX 텍스트 값의 후조건을 제한 시간 동안 확인 |
| `mac_verify` | `{"observation":"UUID","node":"0.2","equals":"한글 😀"}` | 선택한 AX 문자열만 정확히 검사 |

`mac_key`의 modifier는 `command`, `shift`, `option`, `control`이다. 키 이름은 소문자 영문·숫자·기호와 `return`, `tab`, `space`, `delete`, `forwarddelete`, `escape`, `left`, `right`, `up`, `down`, `home`, `end`, `pageup`, `pagedown`, `f1`부터 `f12`까지 지원한다. 키 코드는 미국식 물리 위치다. IME에서 영문 키 식별이 달라지면 `inputSource=ascii`를 명시한다. 정확한 문자열에는 `set_value`나 `mac_type`을 사용한다.

합성 키는 down/up을 한 호출에서 짝으로 보낸다. 다음 호출까지 키를 누른 상태로 유지하지 않는다. `mac_type`은 각 Unicode 묶음 전에 프로세스 정체성, 현재 AX 포커스와 Secure Event Input을 다시 확인한다. 전송 중 포커스나 보안 입력 상태가 바뀌면 `dispatch_interrupted`와 전송된 이벤트 수를 반환한다. 일부 접두 문자열은 이미 입력됐을 수 있으므로 값을 관찰한 뒤에만 재시도한다. Unicode 전송은 IME 조합, 받아쓰기, 하드웨어 장치의 모든 기능을 재현하지 않는다. 일부 앱은 합성 입력을 무시한다.

`mac_click`의 기본 `route=accessibility`는 단일 왼쪽 AXPress만 지원한다. 텍스트 caret이나 물리적 마우스 이벤트를 흉내 내지 않는다. 해당 좌표에 컨트롤이 없거나 같은 깊이의 후보가 겹치면 오류를 반환한다. 명시적인 노드 선택이 필요하면 `mac_ax`를 사용한다.

`mac_find`는 새 AX 수집을 하지 않는다. 지정한 관찰 스냅샷 안에서 `role`, `title`, `identifier`, `valueContains` 중 하나 이상을 적용한다. `coverage=partial`, `truncated=true`, `valueSearchMayBeIncomplete=true`이면 검색 결과가 전체 UI의 부재를 증명하지 않는다.

`mac_wait`는 같은 창·노드 정체성과 프레임을 유지하면서 live plain-text 값만 다시 읽는다. `equals` 또는 `contains` 중 하나를 지정한다. 최대 10초까지 기다리며 관찰을 소모하지 않는다. 창, 노드 경로 또는 노드 프레임이 바뀌면 stale 오류를 반환하므로 새로 관찰한다.

`route=process`는 원시 PID 대상 입력이다. 현재 fixture에서 키보드 수신은 확인했고 원시 마우스의 클릭·드래그·스크롤 수신은 확인하지 못했다. 기본 AX 클릭과 별도 기능으로 취급한다.

`route=global`은 사용자와 공유하는 실제 입력 경로다. 전경 앱과 좌표의 가림 여부가 맞을 때만 실행한다. `mac_activate`는 별도 명시 동작이며 관찰 UUID를 소모한다. 전경 변경 후에는 새 관찰을 사용한다.

## 앱·창·메뉴와 시스템 작업

앱, 창, 메뉴, 파일, URL에 타입이 지정된 도구가 있으면 좌표 입력보다 먼저 사용한다. 다음 표의 변경 도구는 호출이 수락된 사실과 실제 업무 결과를 구분한다. 반환값이 `requested`, `accepted` 또는 `unverified`이면 새 관찰이나 대상별 상태로 후조건을 확인한다.

| 도구 | 핵심 인수 | 동작과 검증 범위 |
|---|---|---|
| `mac_launch` | `bundleID`, `activate?` | 설치된 앱을 실행하고 PID와 `processStartID`를 반환한다. 프로세스 시작 식별자를 즉시 읽지 못하면 앱을 다시 실행하지 않고 `launched_identity_unavailable`을 반환하므로 `mac_apps`로 조정한다. |
| `mac_app` | `pid`, `processStartID`, `action`, `timeoutMs?` | `mac_apps`에서 함께 받은 프로세스 시작 ID를 확인한 뒤 실행 중인 앱을 `activate`, `hide`, `unhide`, `terminate`, `force_terminate`한다. 제한 시간 안에 앱 상태를 다시 읽어 검증한다. |
| `mac_open` | `url`, `bundleID?`, `activate?` | 기존 로컬 `file:` URL 또는 `http`/`https` URL을 NSWorkspace로 연다. 반환값은 열기 요청 수락이며 문서 내용이나 웹 로드 완료가 아니다. |
| `mac_reveal` | `paths` | 1~16개의 기존 절대 경로를 Finder에 표시한다. 셸 확장과 glob은 사용하지 않는다. |
| `mac_trash` | `paths`, `timeoutMs?` | 1~16개의 기존 절대 경로를 NSWorkspace로 휴지통에 이동한다. 루트, 중복, 상대 경로를 거부한다. 부분 완료는 확인된 원본→휴지통 경로와 불확실한 원본을 함께 반환한다. 제한 시간 초과 뒤에도 시스템 작업이 끝날 수 있으므로 상태를 조정하기 전에는 재시도하지 않는다. |
| `mac_window` | `observation`, `operation`, 동작별 좌표·크기 | 새 관찰에 묶인 창의 상태 조회, 올리기, 닫기, 최소화·복원, 전체 화면 토글, 이동, 크기 변경을 수행한다. |
| `mac_menu` | `pid`, `operation`, `processStartID?`, `titlePath?` | 최상위 메뉴를 제한된 개수로 읽는다. 메뉴 실행에는 `mac_apps`의 `processStartID`와 최대 8단계의 정확하고 고유한 제목 경로가 필요하다. |
| `mac_capture` | `displayID`, `maxDimension?` | 선택한 전체 디스플레이를 한 프레임 캡처하고 로컬 PNG 경로, 해시, 픽셀 크기와 논리 좌표를 반환한다. 시스템 커서는 제외한다. |
| `mac_clipboard_read` | `maxBytes?` | 명시적으로 일반 클립보드의 plain text만 읽는다. UTF-8 경계를 보존하며 최대 1 MiB로 제한한다. |
| `mac_clipboard_write` | `text` | 명시적인 plain text로 일반 클립보드를 교체하고 같은 값을 다시 읽어 확인한다. 최대 1 MiB다. |
| `mac_shortcuts` | `operation`과 동작별 이름·경로 | 고정된 `/usr/bin/shortcuts`로 `list`, `run`, `view`를 실행한다. 제한 시간과 출력 크기를 적용한다. |
| `mac_script` | `language`, `source`, 제한 시간·출력 크기 | 고정된 `/usr/bin/osascript`에 AppleScript 또는 JavaScript for Automation 소스를 stdin으로 전달한다. 셸을 실행하거나 소스를 감사 로그에 남기지 않는다. |

`mac_window`의 `operation`은 `state`, `raise`, `close`, `minimize`, `unminimize`, `toggle_full_screen`, `move`, `resize`다. `move`는 전역 논리 좌표 `x`, `y`를 받는다. `resize`는 양수인 논리 크기 `width`, `height`를 받는다. 창 동작은 최신 관찰의 앱·창 정체성과 프레임을 다시 확인한다. `close`, `minimize`, `unminimize`, `move`, `resize`는 실행 뒤 AX 상태를 다시 읽는다. 공개 AX가 안정적인 완료 속성을 제공하지 않는 `raise`와 전체 화면 토글은 요청 결과를 별도 관찰로 확인한다.

```json
{"observation":"UUID","operation":"move","x":220,"y":160}
```

`mac_menu`의 `operation=list`는 최상위 항목만 반환한다. `operation=press`는 같은 PID 행의 `processStartID`와 각 단계에서 정확히 하나와 일치하는 `titlePath`가 필요하다. 비활성 항목, 중복 제목, 바뀐 프로세스 정체성, 노출되지 않은 action은 오류다.

```json
{"pid":12345,"processStartID":"1770000000.123456","operation":"press","titlePath":["File","Save"],"maxItemsPerLevel":64}
```

`mac_capture`의 `displayID`는 `mac_doctor.displays`에서 선택한다. 전체 디스플레이 PNG에는 다른 앱과 사용자 데이터가 포함될 수 있다. 작업에 전체 화면이 필요할 때만 캡처한다. 창 하나만 필요하면 `mac_observe`의 창 캡처를 사용한다.

```json
{"displayID":1,"maxDimension":1600}
```

클립보드 읽기·쓰기, Shortcuts 실행과 스크립트 실행은 사용자가 요청한 경우에만 호출한다. 일반 타이핑에 클립보드를 사용하지 않는다. Shortcuts와 스크립트의 stdout 또는 종료 성공은 대상 앱·파일·네트워크 상태의 완료 증거가 아니다. 제한 시간 초과는 `/usr/bin/shortcuts` 또는 `/usr/bin/osascript` 래퍼 프로세스만 종료한다. 이미 전달된 Apple Event나 Shortcuts 서비스 작업은 계속될 수 있으므로 대상 상태를 확인한 뒤에만 재시도한다.

```json
{"language":"applescript","source":"return 6 * 7","timeoutMs":5000,"maxOutputBytes":4096}
```

## 로컬 OCR과 패널

```json
{"observation":"UUID","languages":["ko-KR","en-US"]}
```

`mac_ocr`는 해당 관찰의 PNG를 Apple Vision으로 읽는다. 반환된 `imageRect`는 왼쪽 위 기준 PNG 픽셀이다. 결과에는 인식 confidence가 있으며 원문·문서 구조가 정확하다는 보장은 없다.

```sh
./scripts/macpilot preview REAL_UUID
```

이 명령도 테두리 없는 라이브 프리뷰를 여는 호환 경로다. 작업별 프리뷰·숨김·재열기는 `mac_preview`를 사용한다. [작업별 워크플로](workflows.md#라이브-프리뷰)에 인수와 상태를 설명한다.

## MCP

서버는 실행 파일의 `mcp` 명령이다. stdout에는 JSON-RPC 메시지만 쓴다. 별도 Node.js, Python, MCP SDK, 웹 서버를 사용하지 않는다. 로컬 stdio 전송을 사용한다. 네트워크 포트는 열지 않는다.

일반 MCP 클라이언트 설정의 예시:

```json
{
  "mcpServers": {
    "macpilot": {
      "command": "/absolute/path/to/macpilot/scripts/macpilot",
      "args": ["mcp"]
    }
  }
}
```

`initialize`, `notifications/initialized`, `ping`, `tools/list`, `tools/call`을 지원한다. JSON 줄 단위 stdio를 사용한다. 지원 protocol version은 `2024-11-05`, `2025-03-26`, `2025-06-18`, `2025-11-25`다. 취소 notification은 해당 request의 Task를 취소한다. 최대 16개의 호출 슬롯을 제공한다. 작업별 상태와 같은 PID·탭·시스템 입력 잠금은 별도로 적용한다. 동일 자원 충돌과 슬롯 초과는 구조화된 `busy` 도구 오류를 즉시 반환한다. 작업 계획·무한 반복 실행 기능은 없다. 조회는 노드 수·깊이·시간 예산으로 제한한다. OS 프레임워크의 응답 지연은 별도 장애로 보고한다.

MCP `mac_observe`는 결과 JSON과 최대 3 MB의 PNG를 반환한다. 어느 AI나 클라이언트에 이 데이터를 제공할지는 MCP 호스트의 설정에 따른다. 일반 로컬 도구, 명시적 브라우저·스크립트 네트워크 작업, 설정한 Codex 진단 전송과 MCP 호스트의 데이터 전송 정책을 구분한다.

## 확장 도구

`mac_task`, `mac_cursors`, `mac_focus`, `mac_preview`, `mac_files`, `mac_system`, `mac_browser`, `mac_private`, `mac_improvement`의 사용 조건과 예시는 [작업별 워크플로](workflows.md)에 있다. `mac_browser_developer`의 상태 조회·설정 화면 준비·사용자 승인 후 활성화는 [브라우저 개발자 설정](browser-developer-settings.md)에 있다. 공개 API 외의 창 정체성 선택은 [비공개 API 범위](private-api.md)를 읽는다.

## 검증

```sh
xcrun swift test --package-path ./tool
python3 ./scripts/verify_mcp.py
```

`tool/Sources/MacPilotFixture`는 사용자 데이터 없이 AX·키·포인터 수신을 검증하는 전용 앱이다. `bin/`, `tool/.build/`, `tool/.swiftpm/`, `evidence/`는 로컬 생성물이며 Git과 Plugin 미러에서 제외한다. 기존 설치본의 화면·로그·검증 증거는 배포하지 않는다. 실제 실행 결과는 해당 실행의 로그와 생성된 `evidence/`에서 확인한다. 단위 테스트와 MCP 회귀 검사는 모든 앱, Intel Mac, macOS 14 또는 App Store 배포를 검증하지 않는다.

[개발과 검증](development.md)에 단계별 실행과 증거 범위를 설명한다. 개발 검증용 `scripts/verify_runtime.py`는 먼저 현재 소스의 release 앱을 다시 빌드·설치·ad-hoc 서명하고 strict 서명을 확인한다. 그 정확한 설치 바이너리를 Apple 개발 도구의 Python 표준 라이브러리와 전용 앱으로 검사한다. 이 스크립트는 CLI·MCP의 실행 의존성이 아니다. 입력 테스트 중에는 전용 앱을 활성화하고 명시적 global 경로의 포인터를 이동한다. 테스트 앱은 종료하며 사용자 커서를 과거 위치로 되돌리지 않는다.

`mac_record`의 창·디스플레이·영역 및 오디오 범위, 완료·무음·취소 결과와 파일 검사는 [화면과 시스템 오디오 녹화](recording.md)에 있다.

### Blender 등 IME에 민감한 저장 입력

`mac_key`·`mac_type`의 기본 `inputSource=current`는 현재 입력 소스를 유지한다. 한글 IME에서 문자 key down이 소비되는 앱에는 `route=global, inputSource=ascii`를 명시할 수 있다. 이미 존재하는 ASCII 키보드 레이아웃만 호출 중 선택하고, 완료·중단·취소 때 원래 소스로 복구한다. 응답의 `keyboardInputSource.restored`를 확인한다. 입력 중 사용자가 다른 소스를 선택했으면 이를 덮어쓰지 않고 중단한다. 입력 소스 설치·영구 설정·클립보드 사용은 하지 않는다.

단일 창 관찰은 macOS 14.2 이상에서 `includeChildWindows=false`로 창 픽셀과 메타데이터 범위를 일치시킨다. Blender File View가 새 창이면 새 windowID로 관찰한다. 파일명 클릭 전 mouse-move를 보내 UI 영역을 갱신한다. 좌표는 `screen|window|normalized|image` 중 명시하며, 화면 전체 캡처와 작은 창 이미지를 혼용하지 않는다.

저장은 고유 새 경로에만 시도한다. 이름 입력 후 새 화면에서 정확한 전체 파일명과 Save As 버튼을 확인하고 저장한다. 입력 수신·파일 생성·Blender filepath/dirty와 파일 크기/mtime/SHA는 서로 다른 검증이다. 전송이 불확실하면 실제 창과 파일을 재조회하며 입력이나 저장을 바로 반복하지 않는다.


## 게임 키 유지

`mac_game_input`은 관찰한 focused AX 노드에 `keys`를 동시에 유지하고 `tapKeys`를 50ms씩 반복해서 누른 뒤 `durationMs` 20–10000ms 후 역순으로 해제한다. 두 목록을 합쳐 서로 다른 키 1–8개만 허용한다. 반복 간격은 `tapIntervalMs` 100–2000ms이며 기본값은 250ms다. 예: `keys=["left","up"]`, `durationMs=1500`, `route="global"`, `node="root"`. 게임의 AX 창 자체가 실제 포커스인 경우 root를 쓴다. 매 50ms에 프로세스 정체성·전경·AX 포커스·Secure Event Input을 재검사한다. 취소·오류에도 해제를 시도한다. 사용자와 같은 전역 키보드를 공유하므로 사용자 조작과의 완전한 격리는 없다. 물리 HID 장치나 커널 드라이버를 생성하지 않는다.

`eventSource="hid"`는 공개 Quartz의 HID 시스템 상태를 사용한다. 기본값은 `private`이며 `hid`는 global 전경에서만 허용한다. 가상 HID 장치를 생성하는 옵션이 아니며, 물리 장치를 조회하는 게임에서 수신을 보장하지 않는다.

문자 키가 IME에 소비되면 명시적으로 `inputSource="ascii"`를 선택한다. 이 모드는 global 전경에서만 허용하며 원래 입력 소스를 복구한다. 이벤트 전송과 실제 이동·게임 결과를 별도로 검증한다. 각 동작 후 새 관찰을 사용한다.


전역 키보드·마우스 입력에는 모든 디스플레이의 3pt 가장자리 효과와 ‘MacPilot 조작 중 · 키보드/마우스’ 안내가 표시된다. 안내는 포커스나 클릭을 받지 않는다. 동작 줄이기 설정에서는 가장자리 효과를 고정한다. 완료·취소·오류·소유 프로세스 종료 시 숨기며, 안내 호스트가 사라지면 추가 입력을 중단하고 눌린 키를 해제한다. process 경로와 AX 작업에는 이 전역 입력 안내를 표시하지 않는다.
