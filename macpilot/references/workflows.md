# 작업별 워크플로

CLI JSON은 `scripts/macpilot call TOOL --json -`의 stdin으로 전달한다. 아래 UUID·PID·경로는 형식 예시이며 실제 조회 값으로 바꾼다. 전체 스키마는 `scripts/macpilot tools`가 기준이다.

## 작업·커서·포커스

`mac_task operation=begin`에 `goal`, `expected`, 선택한 `pid`·`processStartID`·`windowID`를 준다. 반환된 `task.id`를 이후 호출의 `taskID`로 사용한다. `preserveForeground`는 기본 true이며 전경 앱이 바뀌면 오류로 반환한다. 사용자의 자발적 전경 전환도 이 오류를 만들 수 있다. 시작한 작업의 창 ID는 `mac_observe`에서 생략해도 적용한다.

각 작업은 관찰·커서·프리뷰 상태를 따로 저장한다. `mac_pointer`의 `cursorID`로 커서를 구분한다. `mac_cursors`의 `list`·`remove`로 조회하거나 제거한다. `hide`·`show`는 실제 데스크톱 화살표와 접근 대상 창 테두리를 숨기거나 표시한다. 관찰하면 대상 창 강조가 시작되고, `mac_pointer`는 macOS 화면 위의 화살표를 이동한다. 커서는 프리뷰·PNG에 합성하지 않는다. 커서 ID는 ASCII 문자·숫자·`-`·`_`로 최대 64바이트다. 기본값은 `primary`다. 내부 ID는 화면 라벨로 쓰지 않는다. `mac_pointer label`에는 `검색어 입력`, `저장 버튼`, `스크롤`처럼 작업 동작·대상을 지정한다. 생략하면 해당 AX 요소의 이름·역할을 사용한다. 목표가 바뀌면 cubic Bézier 경로와 minimum-jerk 시간 함수 `10t³−15t⁴+6t⁵`로 0.18~0.65초 동안 이동한다. 이동 중 목표가 바뀌면 현재 표시 위치에서 다시 시작한다. 커서 이동은 시스템 이벤트를 보내지 않는다.

같은 작업과 PID의 호출은 동시에 실행하지 않는다. 서로 다른 PID·탭은 작업을 나누면 병행할 수 있다. 충돌은 대기 대신 `busy`를 반환한다. 파일 동작과 Safari는 각 백엔드 전체 잠금을 사용한다. MCP 실행 슬롯은 최대 16개이며 이 수가 동시 입력 보장을 뜻하지 않는다.

전경이 필요한 경우 별도 작업에 `preserveForeground=false`를 준다. 새 관찰로 `mac_focus`를 호출하면 최소화 복원, 앱 활성화, 선택 창 올리기와 선택적 `node` 포커스를 연결한다. 실제 전경 PID·AXFocusedWindow·AXFocusedUIElement를 다시 확인한다. 포커스·창 정체성이 바뀌면 다음 입력을 중단한다. 일반 사용자 활동 전체를 감지하거나 사용자 입력을 차단하는 기능은 없다.

`mac_task cancel`은 진행 중인 호출을 취소한다. `finish`는 작업을 끝낸다. 이미 전달한 이벤트·Apple Event·파일 작업은 되돌리지 않으므로 실제 상태를 다시 확인한다. 기본 만료는 1800초이며 `durationSeconds` 범위는 1~28800초다.

## 라이브 프리뷰

새 관찰과 `taskID`로 `mac_preview operation=start`를 호출한다. 프리뷰는 제목 표시줄·창 버튼이 없는 화면 모서리 오버레이다. 드래그로 위치를 옮기고 메뉴 막대에서 크기를 전환할 수 있다. 컨트롤은 마우스를 올릴 때 표시한다. 프리뷰 더블클릭 또는 `창 열기` 버튼은 대상 창을 새로 식별하고 전경·창 포커스를 확인한 뒤 프리뷰만 종료한다. 실패하면 프리뷰를 유지한다. ScreenCaptureKit 스트림에서 선택 창의 새 프레임을 받아 표시한다. `status`는 `frameCount`, `frameSHA256`, 캡처 크기·시간·오류·패널 상태를 반환한다. `preview UUID` CLI도 같은 라이브 프리뷰를 여는 호환 경로다.

`hide`·`show`는 스트림과 프로세스를 유지한다. `pause`·`resume`은 캡처를 제어한다. `overlay enabled=true`는 독립 프로세스의 데스크톱 커서·대상 강조를 표시한다. `stop`은 프리뷰 스트림·화면만 종료한다. 커서·대상 강조는 프리뷰의 숨김·일시정지·종료와 별개로 유지되며, `mac_cursors hide` 또는 작업 종료로 숨긴다. 메뉴 막대에서도 숨김·재열기·일시정지·종료를 선택할 수 있다. 캡처 실패, 오래된 프레임, 대상 종료와 작업 취소는 상태로 확인한다. 프리뷰와 데스크톱 화살표·대상 강조는 키보드 포커스를 가져오지 않는다. 강조는 입력 대상 표시이며 실제 OS 포커스 변경이 아니다. 대상 창보다 앞에 있는 창의 영역은 커서·강조에서 제외한다. 완전히 가려진 대상에는 전경 위의 빈 테두리를 표시하지 않는다.

## 파일·시스템

`mac_files`는 `stat`, `list`, `search`, `read`, `write`, `copy`, `move`, `mkdir`, `tags`를 지원한다. 절대 경로를 명시한다. 기존 목적지는 덮어쓰지 않는다. `write overwrite=true`만 기존 일반 파일 교체를 허용한다. 일반 파일의 쓰기·복사·이동은 SHA-256을 확인한다. 디렉터리·심볼릭 링크 복사 결과는 메타데이터 존재만 확인하므로 `unverified`다. 시간 초과된 파일 작업은 계속 실행될 수 있다. 원본·목적지를 확인하기 전에는 반복하지 않는다.

텍스트 읽기·쓰기는 UTF-8, 최대 1 MiB다. 검색은 선택한 디렉터리의 이름을 비교하며 숨김 파일·깊이·결과·순회 개수를 제한한다. `coverage=partial`이면 전체 검색으로 해석하지 않는다. `tags`는 Finder 태그를 설정하고 다시 읽는다. Finder 열기·표시·휴지통은 기존 `mac_open`, `mac_reveal`, `mac_trash`를 사용한다.

`mac_system operation=info`는 실제 디스플레이·저전력·온도 상태를 반환한다. `operation=audio`는 기본 출력 장치의 음량·음소거를 조회한다. `volume` 0~1 또는 `muted`를 명시하면 해당 속성을 설정하고 다시 읽는다. 쓰기를 지원하지 않는 출력 장치는 오류를 반환한다. 마이크나 오디오를 녹음하지 않는다.

## 브라우저

현재 호스트의 브라우저 도구가 사용자 지정 브라우저·기존 로그인 세션에 연결돼 있으면 재사용한다. MacPilot 독립 경로는 Chromium WebExtension + Swift native messaging 또는 Safari Apple Events다. 브라우저 메뉴·주소창·시스템 파일 선택창은 네이티브 도구를 사용한다. synthetic DOM 키 이벤트는 trusted 입력이나 브라우저 단축키가 아니다.

| 백엔드 | 기능 | 조건과 한계 |
|---|---|---|
| Chrome·Edge·Chromium 확장 | 탭 조회·열기·선택·닫기, 이동·history·reload, 프레임, DOM 조회·클릭·입력·선택·스크롤·키·후조건, 업로드·다운로드·상태·화면 | 사용자가 확장 활성화 및 필요한 사이트 접근을 허용해야 함. Chrome 실제 검증, Edge·Chromium 별도 실행 검증 필요 |
| Safari `browser=safari` | 탭 조회·열기·선택·닫기, 이동·history·reload, top DOM 및 같은 출처의 직접 하위 프레임, DOM 동작·후조건·업로드 | Automation 및 Allow JavaScript from Apple Events 필요. 위치 기반 탭 핸들이므로 중복 URL·변경된 URL은 차단. Safari 호출 전체 직렬화 |
| Safari의 교차 출처·깊은 프레임, 다운로드·브라우저 screenshot | 호스트 브라우저 도구 또는 네이티브 캡처·파일 도구로 수행 | 독립 Safari 백엔드는 이 작업을 지원하지 않음. 무인 설치되는 Safari 확장이나 Safari 앱 번들은 포함하지 않음 |

Chromium 설치:

1. 브라우저 확장 관리 화면에서 이 패키지의 `browser/extension/`을 unpacked 확장으로 로드한다. 반환된 확장 ID를 사용한다. 배포 스토어 등록은 별도다.
2. `mac_browser operation=install_host`에 `extensionID`, `browser=chrome|edge|chromium`을 전달한다. 필요한 경우 `manifestDirectory`로 별도 프로필의 `NativeMessagingHosts` 디렉터리를 지정한다. 다른 설치가 만든 host manifest는 교체하지 않는다.
3. 확장 팝업에서 필요한 사이트 접근을 허용한다. `connections`에서 `live=true`인 `id`를 선택해 이후 호출의 `connectionID`로 전달한다. 여러 연결이 있으면 반드시 지정한다. 기존 기본 프로필의 원격 디버깅 설정은 변경하지 않는다.

Safari는 확장이 필요 없다. `mac_browser` 호출에 `browser=safari`를 지정한다. `tabs` 또는 `open`의 `tabID`를 사용한다. 이동·redirect 후에는 `tabs`를 다시 조회한다. `frames`에서 `accessible=true`인 `frameID`만 선택한다. 직접 하위 프레임 목록이며 전체 프레임 트리로 해석하지 않는다.

개발 기능이 꺼져 있으면 `mac_browser_developer status|prepare|enable`을 사용한다. Safari 웹 개발자 기능·Apple Events JavaScript와 Chrome 확장 개발자 모드를 각각 선택한다. `enable`은 실제 사용자 확인을 받은 뒤 토글 하나만 켠다. [범위·승인·결과 코드](browser-developer-settings.md)를 먼저 확인한다. 에이전트가 승인 대화상자를 누르지 않는다.

DOM 변경에는 `tabID`, 필요 시 `frameID`, `observation`, `node`가 필요하다. 관찰은 30초·단일 변경에 유효하며 암호 값은 반환하거나 입력하지 않는다. `verify`·`wait`는 `equals`와 `contains` 중 정확히 하나를 받는다. 후조건 대기는 최대 30초이며 네이티브에서 폴링한다. `upload`는 `path`의 일반 파일을 최대 32 MiB까지 청크·해시로 전달한다. `files_assigned`는 파일 입력 할당이며 서버 업로드 완료는 별도 후조건으로 확인한다.

Chromium `download`는 브라우저의 다운로드 디렉터리 안에서 상대 `filename`만 허용한다. `download_status`로 완료·실패·경로를 확인하고 필요한 경우 원본과 비교한다. 브라우저 명령의 `requestID`는 `receipt`로 조회한다. 응답이 불확실한 변경 명령은 상태 확인 없이 반복하지 않는다.

## Codex 개선 요청

사용자의 개선 요청 전송 지시가 있을 때 목적지를 설정한다. `mac_improvement configure`에 명시적인 `codexPath`, 진단할 `cwd`, 필요한 `threadID`, 선택적 `model`·`effort`를 준다. 기본은 수동 전송이며 모델·effort를 생략하면 Codex 설정을 따른다. 별도 app-server 대화가 데스크톱 사이드바에 보이는지는 보장하지 않는다.

실행 오류는 원래 인수를 제외한 도구명·오류 코드, 호출 호스트가 준 작업 목표·기대 결과로 로컬 요청을 만든다. 정상 상태로 반환됐지만 업무 후조건이 틀리면 `report`에 `title`, `goal`, `expected`, `actual`을 준다. `evidencePaths`는 명시적으로 선택한 로컬 경로 목록이다. 파일 첨부나 화면 자동 수집이 아니다. 보고문·목표에 비밀·쿠키·인증 정보·불필요한 사용자 원문을 넣지 않는다.

`send requestID=...`는 Codex app-server의 initialize → thread start/resume → turn start를 실행한다. 요청 ID·thread ID·turn ID·응답·오류를 로컬에 저장한다. `automaticSend=true`는 이후 해당 범위의 오류를 자동 전송한다. 연결 실패는 요청을 보존한다. 모델을 포함한 실제 네트워크 호출은 별도 Codex 프로세스가 수행한다. 설정만 저장했다고 전송 완료로 보고하지 않는다.

`completed`는 진단 응답 완료다. 코드 수정·빌드·설치가 아니다. `unconfirmed`는 `reconcile`로 기존 turn을 조회하며 새 turn을 보내지 않는다. 완료·불확실한 요청은 중복 전송하지 않는다. 같은 도구·코드·목표·기대 결과는 같은 요청에 발생 횟수를 합친다.

진단에는 read-only sandbox, approval never, 작업 도구의 networkAccess=false를 요청한다. 이 sandbox가 파일 읽기를 `cwd`와 선택 증거로 OS 수준에서 제한하지는 않는다. 읽기 범위는 진단 지시이며 강제 파일 접근 격리가 아니다. 민감한 라이브러리는 진단 workspace로 선택하지 않는다. 진단 결과는 제안으로 검토하고 사용자가 허용한 수정 범위에만 적용한다.

## 영상 녹화와 분석

`mac_record record`로 선택한 창 또는 디스플레이·영역을 MP4에 기록한다. 전체 Mac 소리가 필요하면 디스플레이·영역 모드를 선택한다. 독립 창의 앱 귀속 오디오와 시스템 오디오를 구분한다. 완료 후 트랙·PCM 신호·추출 프레임을 읽고 실제 내용을 확인한다. 범위·권한·실행 예시는 [녹화 지침](recording.md)을 따른다.
