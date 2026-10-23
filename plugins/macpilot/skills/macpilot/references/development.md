# 개발과 검증

실행 코어·CLI·MCP·AX·캡처·CoreAudio·Codex app-server 연결은 Swift다. 선택적 SimulatorKit 입력 helper는 Objective-C이며 private ABI 실패를 별도 프로세스로 격리한다. 일반 실행은 Universal 배포 앱을 사용하며 Swift 설치가 필요 없다. 브라우저 확장은 JavaScript다. 기본 제어에서 Python과 Node.js는 개발 검증용이다. 선택적 이미지 검색만 명시적으로 설정한 로컬 Python 모델 worker를 사용한다. 패키지는 외부 SwiftPM 의존성이 없다.

## 검증 명령

저장소 루트에서 실행한다.

```sh
xcrun swift test --package-path macpilot/tool
MACPILOT_UNIVERSAL=1 macpilot/scripts/build.sh
python3 macpilot/scripts/verify_mcp.py
python3 macpilot/scripts/verify_connection.py --binary macpilot/bin/MacPilot.app/Contents/MacOS/macpilot
python3 macpilot/scripts/verify_startup.py --binary macpilot/bin/MacPilot.app/Contents/MacOS/macpilot
python3 macpilot/scripts/verify_browser_developer.py
python3 macpilot/scripts/verify_features.py --stage all
python3 macpilot/scripts/verify_runtime.py
python3 scripts/sync_skill_mirrors.py --package macpilot --write
python3 -m unittest discover -s scripts/tests -v
```

`PermissionSetupTests`는 한글·공백 경로의 앱 파일 URL, 88×88pt 패널의 아이콘 단일 계층·우클릭 메뉴, 네이티브 설정 창 옆 배치·이동 계산, 최소 권한 계획, 전경·입력 잠금, Automation 상태와 인증·재실행 안내 분류, 화면·오디오 주 목록 선택을 검사한다. `MACPILOT_PERMISSION_TEST_EVIDENCE=/absolute/guide.png`는 아이콘 패널 렌더링을 남긴다. `xcrun swift macpilot/scripts/verify_permission_drag.swift PID WINDOW_ID X Y /absolute/MacPilot.app START_ID`는 실제 부착 패널에서 소유한 테스트 창으로 파일 URL을 드래그한다. 시스템 설정의 권한이나 인증 버튼에는 입력을 보내지 않는다. 실제 창 추적·다른 앱 전환 시 숨김·직접 드래그와 자동 추가는 별도 런타임 근거로 남긴다.

`verify_features.py --stage tasks|preview|files|browser|safari|codex`로 해당 단계만 실행할 수 있다. `all`은 전부 실행한다. 이미 검증한 경로는 관련 입력·실패가 바뀔 때 다시 실행한다. `verify_runtime.py`는 기존 입력·메뉴·창·보안·CLI·MCP 회귀를 위해 release 앱을 다시 빌드·서명한다. 두 실행기는 실제 전경 앱과 포인터에 영향을 줄 수 있다. 전용 fixture와 합성 데이터만 사용한다.

`verify_connection.py`는 `--binary`로 지정한 빌드의 MCP 두 개와 검사 자식을 사용한다. 현재 연결과 CLI 호출 경로, PID·시작 ID·instance ID, 실제 handshake, 기존 상태 경로 보존, 검사 자식 정리를 확인한다. 데스크톱 앱이나 다른 MCP는 종료하지 않는다. `ConnectionTests`는 PID 재사용·잘못된 인수·EOF·프로토콜 오류·시간 초과·취소와 실행 잠금 중 진단을 검증한다. [복구 범위](mcp-recovery.md)를 따른다.

- tasks/preview: 두 전용 앱, 커서 격리, 서로 다른 대상의 동시 실행, 같은 대상 충돌, 취소, 포커스, private ID, 새 캡처 프레임과 패널 제어를 확인한다.
- files: 임시 파일의 원본 바이트·해시, Finder 태그, 실제 디스플레이와 CoreAudio를 확인한다. 오디오 쓰기는 현재 값과 같은 값으로 제한한다.
- browser: 실제 Chrome을 새 임시 프로필과 headless 모드로 실행한다. 테스트 전용 debugging pipe로 확장을 활성화한다. 사용자 기본 프로필에는 연결하지 않는다. Swift native host, DOM·iframe, 실제 HTTP 업로드·다운로드를 확인한다. Node.js와 로컬 Chrome이 필요하다.
- safari: 실제 Safari에 전용 localhost 페이지 창을 만든다. 기존 탭을 수정하지 않는다. Automation 동의와 Safari의 Allow JavaScript from Apple Events가 필요하다. 설정을 자동 변경하지 않는다. 소유한 테스트 창만 닫는다.
- codex: 명시적 로컬 `codex`로 합성 진단을 실제 제출하고 응답·자동 전송·중복 방지·오프라인 보존을 확인한다. 로그인·모델 연결이 필요하고 실제 모델 사용량이 발생한다. 테스트는 ephemeral 대화와 비어 있는 임시 workspace를 사용한다.

증거는 `macpilot/evidence/`에 남긴다. 각 report는 바이너리 해시, 단계별 결과와 원시 응답 경로를 갖는다. 패널 스크린샷의 시각 검수는 자동 검사와 구분한다. 전용 fixture의 성공은 모든 앱·모든 OS의 성공을 뜻하지 않는다. Developer ID·공증·App Store·전역 설치·새 세션 도구 노출도 별도다.

## 상태와 경로

컨트롤러 상태는 `TemporaryDirectory` 또는 기본 사용자 Application Support에 둔다. Store는 쓰기 가능한 공유 상위 디렉터리·심볼릭 링크·잘못된 소유권을 거부한다. 외부 체크아웃이 다른 사용자에게 쓰기 가능한 볼륨 아래에 있으면 그 안에 컨트롤러 상태를 만들지 않는다. 테스트를 위해 Store 검사를 완화하지 않는다. 증거와 실행 상태를 분리한다.

Store는 이미 존재하는 환경 변수 지정 디렉터리에 소유 표식 `.macpilot-state-v1`이 없으면 거부한다. `mkdtemp`로 만든 0700 컨테이너 아래의 **아직 없는** `state/`를 자식의 `MACPILOT_STATE_DIR`로 지정하여 Store가 직접 만들고 표식을 쓰게 한다. 임시 폴더를 먼저 만들었다는 이유로 Store의 소유 검사를 우회하지 않는다.

macOS의 `/var`와 `/private/var`처럼 같은 파일의 경로 표현이 다를 수 있다. 파일 경로 비교는 resolve한 경로 또는 파일 정체성으로 한다. 원본 바이트·해시 검증을 경로 문자열 비교로 대신하지 않는다.

`bin/`, `tool/.build/`, `tool/.swiftpm/`, `evidence/`는 생성물이다. Git과 Plugin 미러에 넣지 않는다. 미러는 소스·확장·테스트·문서를 실행 권한까지 일치시킨다. 전역 스킬·MCP 설정·개인 로그인 프로필의 변경은 이 저장소 편입과 별도다.

앱 아이콘 원본은 `assets/app-icon.png`다. `scripts/build.sh`는 macOS 기본 도구 `sips`·`iconutil`로 16–1024px ICNS를 만들고 `Contents/Resources/MacPilot.icns`와 `CFBundleIconFile`을 함께 포함한 뒤 서명한다. 권한 패널은 같은 앱 경로의 `NSWorkspace.icon(forFile:)`을 사용한다. 원본과 생성 근거는 [아이콘 자산](../assets/README.md)을 참고한다.

합성 이벤트는 비동기로 도착한다. 보안 입력으로 포커스가 옮겨질 때 key down 직후 또는 up 직후 중단될 수 있다. 전송 개수를 정확히 2로 고정하지 않는다. 중단 원인, 입력 접두 범위, 보안 값 보존과 cleanup release의 균형으로 판정한다. 프리뷰 검증은 테두리 없는 표시와 실제 데스크톱 커서·대상 강조의 독립 수명도 확인한다.

데스크톱 피드백은 `.floating`으로 다른 앱 위에 사각형을 그리면 안 된다. 대상 창과의 순서를 유지하고 위에 놓인 창의 영역을 제외한다. 프리뷰 숨김·종료와 별개로 커서를 유지한다. 화면에는 내부 cursorID 대신 동작·대상 라벨을 쓴다. UI 검증은 실제 창 가림·이동·드래그와 키보드 포커스 유지까지 확인한다.

WindowServer 인벤토리의 alpha=1이 전체 사각형의 불투명도를 뜻하지는 않는다. Dock의 투명한 전체 화면 입력 관리 창을 일반 앱의 가림 영역으로 계산하지 않는다. 가림 판정은 실제 전경 앱·창과 피드백 표시를 함께 검사한다.

테두리 없는 비활성 프리뷰는 `acceptsFirstMouse`를 명시하고, 이미지 뷰에서 drag와 double-click을 나눠 처리한다. 창 배경의 자동 drag가 double-click을 먼저 소비하지 않게 한다. 테스트는 실제 이벤트로 이동·포커스 유지·대상 활성화 후 프리뷰 종료를 각각 판정한다.

모달 시트를 여닫는 AXPress가 `ax_outcome_uncertain`을 반환하면 실제 시트 상태를 재조회한다. 이미 시트가 열리거나 닫혔으면 후조건으로 조정하고 같은 AXPress를 재전송하지 않는다. 회귀 실행기는 이 경우의 원시 오류와 조정 결과를 함께 보존한다.

공유 데스크톱에서 사용자 앱 전환이 관찰되면 완료 시점의 전경 PID·AX 창 포커스 확인과 이후 사용자 선택을 구분한다. 프리뷰 열기 검증은 해당 실행의 `focus_verified` receipt와 실제 프리뷰 닫힘을 연결한다. 이미 확인한 포커스를 사용자가 바꿨다고 해서 전경을 반복해서 되찾지 않는다.

화면·시스템 오디오 녹화는 `node macpilot/scripts/verify_recording_chrome.mjs`와 `python3 macpilot/scripts/verify_recording_lifecycle.py`로 검증한다. `MACPILOT_RECORDING_SCOPE=display|region`은 실제 GUI 화면과 시스템 소리를 캡처한다. [녹화 검증 범위](recording.md)를 확인한다. Chrome의 별도 프로필 독립 창에서 무음이 나온 결과를 전체 시스템 오디오 성공과 섞지 않는다.

권한 아이콘 패널은 설정 창이 일시적으로 가려지거나 최소화되어 WindowServer의 onscreen 목록에서 사라져도 종료하지 않는다. 그동안 숨기고 설정 창이 다시 나타나면 같은 패널을 표시한다. 자동 종료 타이머는 이 재표시를 막을 수 있으므로 사용하지 않는다.

`NSVisualEffectView`의 behind-window 재질에는 레이어의 `cornerRadius`만 적용하지 않는다. `maskImage`의 알파 채널로 재질과 창 그림자의 라운드 윤곽을 지정한다. `PermissionSetupTests`는 마스크의 네 모서리가 투명하고 중앙이 불투명한지 검사한다. 실제 WindowServer 합성 결과는 실행한 패널로 별도 확인한다.

드래그 시연은 `PermissionDragOnboarding.swift`가 담당한다. 투명 창은 입력을 통과시키며 실제 앱 아이콘은 고정한다. 사용자 입력 중지·동작 줄이기·두 번 제한은 소스 검사와 실제 무권한 앱의 드래그 근거를 구분해 확인한다. [무권한 검증](permission-validation.md)의 실행기는 별도 bundle ID로 동일 실행 코어를 빌드한다. 앱과 실시간 로그는 내부 임시 경로에 둔다. 외장 볼륨의 로그 접근 자체가 별도 동의를 요구하므로 그 동의를 초기 권한 검증과 섞지 않는다.


## Blender 저장 입력 회귀

조합키는 modifier flagsChanged down/up·키 해제를 함께 검사한다. Unicode scalar 단위 이벤트는 surrogate pair를 보존한다. 캡처의 선택 창과 실제 이미지 범위, 클릭 전 mouse-move, 전송 시각과 down/up 간격을 각각 분리해 확인한다. 한글 IME에서 일반 문자 이벤트가 소비되면 명시적 `mac_key|mac_type inputSource=ascii`의 원래 입력 소스 복구까지 검증한다. fixture 성공은 실제 Blender Save As 성공을 대신하지 않는다. 기존 파일·dirty 상태를 먼저 보존하고 새 경로로 저장한 뒤 디스크 파일과 fresh Blender 상태를 교차 확인한다. bpy 저장은 MacPilot 성공 근거로 사용하지 않는다.


입력 fixture 회귀는 `python3 macpilot/scripts/verify_input.py --binary /absolute/MacPilot.app/Contents/MacOS/macpilot --fixture /absolute/macpilot-fixture --evidence /absolute/new-evidence-directory`로 실행한다. fixture는 같은 저장소의 `xcrun swift build --package-path macpilot/tool --product macpilot-fixture`로 만든다. 새 증거 디렉터리만 허용하고 일반 종료만 요청한다. 입력 소스 변경으로 AXWindows 순서가 달라져도 기존 frame/title의 유일성·정확한 포커스·프로세스 정체성을 유지해야 한다. 배열 index를 창 정체성으로 사용하지 않는다.

## 게임 입력 회귀

`verify_input.py`는 동시 키 유지 시간과 실제 fixture의 눌린 키 집합을 확인한다. MCP 취소는 원래 응답을 생략하므로 취소 요청의 응답을 기다리지 않는다. 후속 `mac_doctor`가 응답하는지와 fixture의 모든 키 해제를 함께 검사한다. 게임에서는 튜토리얼의 실제 키를 확인하고 이동·공격·스테이지 완료를 각각 관찰한다. fixture 통과만으로 물리 HID와의 동등성이나 실제 게임 공격 성공을 주장하지 않는다.

ASCII 입력 소스 전환은 별도 IME AX utility 창을 만들 수 있다. private 창 ID를 재검사할 때 관찰한 frame/title 후보만 조회한다. 관련 없는 utility 창의 private ID 실패 때문에 게임 입력 전체를 중단하지 않는다. 원래 대상의 private ID·frame/title·유일성 검사는 유지한다.


전역 입력 안내는 `python3 macpilot/scripts/verify_input_activity.py --binary /absolute/MacPilot.app/Contents/MacOS/macpilot --fixture /absolute/macpilot-fixture --evidence /absolute/new-evidence-directory`로 검증한다. 격리된 상태와 소유한 fixture에서 실제 화면 표시·포커스 유지·클릭 통과·완료와 취소 시 숨김·안내 호스트 종료 후 입력 중단과 키 해제를 검사한다. 렌더링된 `during-input.png`와 `after-input.png`를 직접 검수한다. 호스트 종료 검사는 이 실행이 시작한 격리된 안내 프로세스만 대상으로 한다.

다른 앱의 전체 화면에서는 `fullScreenAuxiliary`만으로 안내의 실제 노출을 보장할 수 없다. UI 호스트를 `.accessory`로 실행하고 `canJoinAllApplications`도 지정한다. 패널 생성 직후부터 반복 생성하지 말고 다음 tick에서 실제 표시 상태가 정착할 시간을 둔다. 안내 패널의 active Space와 WindowServer onscreen 목록을 함께 확인한다. `NSWindow.isVisible`이나 내부 상태만으로 전체 화면 표시 성공을 판정하지 않는다. 실제 게임의 디스플레이 캡처로 별도 확인한다.

안내 호스트의 시작·응답 지연 검사는 격리된 소유 호스트만 2.4초 정지한다. 실제 표시 확인 전 입력이 없고, 대기 중 소유 레코드가 갱신되며, 호스트 재개 후 입력과 종료 시 해제가 이루어지는지 확인한다. 시작 대기는 최대 5초다. 실제 화면·위치·피해에 변화가 없으면 전송 결과와 무관하게 현재 게임 입력 경로는 실패로 기록한다.


## 조건 대기와 선택 기능 회귀

`xcrun swift build --package-path macpilot/tool --product macpilot-capability-fixture` 후 다음 명령을 실행한다. 검증 창과 제어기 상태는 실행별 내부 임시 경로에 격리한다. 실제 앱에 입력하거나 설치된 MCP를 교체하지 않는다.

```sh
python3 macpilot/scripts/verify_capabilities.py --binary /absolute/MacPilot.app/Contents/MacOS/macpilot --fixture /absolute/macpilot-capability-fixture --evidence /absolute/new-evidence-directory --python /absolute/optional-venv/bin/python --model /absolute/pinned-model-snapshot
```

Python·모델 인수를 생략하면 실제 모델 검사는 `NOT_RUN`이다. 기본 비활성 경로 검사는 계속 실행한다. 조건 변화·부분 수집·중복, 무반응 결과, 추적 전후 이미지 해시·보안값 제외·보존 한도·추적 오류, 전체 작업 사전 검사·중복 실행·실패 후 중단·취소 기록, 다른 프로세스 이벤트 감지와 키 해제를 검사한다. 실제 모델 검사에는 후보 위치·캐시 재사용·임계값·중복·검색 중 화면 변경이 포함된다. 제어한 합성 외부 이벤트는 물리 키보드·트랙패드 검증을 대신하지 않는다. 저장된 PNG를 직접 검수하며 arbitrary app 지원이나 사용자 수락과 구분한다.

`verify_runtime.py --skip-build --evidence /absolute/new-directory`는 이미 별도로 빌드·서명한 저장소 바이너리를 재사용한다. 지정한 증거 디렉터리가 있으면 중단하므로 앞선 실행 결과를 덮어쓰지 않는다.

입력 회귀의 MCP 제어기 상태도 fixture별 임시 디렉터리에 둔다. 실제 사용자 상태 디렉터리의 설정·추적·감사 로그와 섞지 않는다. 이미지 검증 fixture는 AppKit 프로세스 신원을 확인할 수 있도록 실행별 ID의 임시 `.app` 번들을 LaunchServices로 실행한다. 프로세스가 살아 있는 상태의 AppKit 메타데이터 조회 실패와 실제 프로세스 종료를 같은 오류로 분류하지 않는다.

드래그 취소 검사는 fixture가 실제 `mouseDown`을 받은 뒤 취소를 보낸다. 고정 지연만으로 입력 시작을 추정하지 않는다. fixture의 제한된 `pointerReceipts`에 이벤트 출처 PID·표식·유형·시각을 남겨 OS/다른 입력과 제어기 입력을 구분한다.

LaunchServices가 실행하는 fixture의 stdout·stderr도 내부 임시 경로에 둔다. 외장 볼륨의 증거 경로를 직접 넘기면 새 앱의 파일 접근 동의와 실행 실패가 섞일 수 있다. 종료 후 호스트가 로그를 증거 경로로 옮긴다. 외부 입력 송신기는 별도 프로세스의 기존 호스트 권한을 사전 확인하며 새 fixture 권한을 자동 요청하지 않는다.

기존 빌드를 재사용할 때는 제어기와 fixture의 소스 범위를 따로 확인한다. 제어기 mtime 검사에 별도 검증용 실행 파일의 소스를 섞지 않는다. mtime은 빌드 증명이 아니므로 실제 빌드 로그·바이너리 해시·서명 검사·런타임 판정을 구분한다.


## 네이티브 AX 분석 검증

`python3 macpilot/scripts/verify_analysis.py --binary /absolute/MacPilot.app/Contents/MacOS/macpilot --fixture /absolute/macpilot-capability-fixture --evidence /absolute/new-evidence-directory`는 두 개의 소유한 합성 창으로 분석·보안 노드 거부·UTF-16·부분 수집·중복·소비한 관찰·MCP 노출·백그라운드 전경 보존을 검사한다. 개인 앱이나 전역 입력을 사용하지 않는다. Swift 단위 검사는 `xcrun swift test --package-path macpilot/tool`로 실행한다. RPC version 협상 검사는 고정 릴리스 문자열 대신 `MacPilotRuntime.version`과 실제 응답의 연결을 확인한다. 버전 변경 때의 불필요한 테스트 실패를 막되 메타데이터 일치는 별도 배포 검사로 확인한다.

Simulator 기능은 [전용 기기 검증](simulator.md#개발-검증)을 사용한다. 일반 macOS UI 분석에는 `verify_analysis.py`를 사용하며 텍스트 bounds·행 조회도 실제 AppKit 필드에서 검사한다. 배포 전에는 최종 서명 앱을 빌드하고 `release_plugin.py pin-runtime`으로 실행 파일 해시를 고정한 다음 미러·스테이지·실행 근거를 맞춘다.

Simulator 검증 계약의 불변식은 다음과 같다. 새 실행은 새 근거 디렉터리를 사용한다. 기존 전용 기기를 재사용하면 그 기기만 재부팅해 이전 시스템 확인창을 제거한다. 앱의 합성 상태 파일뿐 아니라 활성 scene도 확인한 뒤 첫 입력을 보낸다. URL 확인은 테스트 앱 이름과 유일한 열기 버튼을 현재 Vision OCR에서 확인하고 실행한다. 전체 시퀀스가 끝나지 않거나 예외가 발생한 보고서는 `failed`다. 지원 GUI가 없으면 `notRun`에 남기며 다른 창이나 합성 AX 결과로 대체하지 않는다. 결과 판정은 `checks`, `notRun`, 실제 게스트 상태·PNG·동영상, 최종 실행 파일 SHA를 함께 읽는다. 실패 후에는 남은 확인창·접점·부팅 정체성을 확인하며 같은 동작을 자동 재실행하지 않는다.

공개 후 `verify_bootstrap.py --skill /installed/skill --evidence /new/evidence`는 실행 파일이 없는 전용 사본에서 실제 릴리스 다운로드·고정 해시·MCP를 검사한다. 개발 도구 PATH·DEVELOPER_DIR·SDKROOT를 사용할 수 없게 설정하고 기본 실행의 컴파일 전환이 없음을 확인한다. 시스템의 Swift 설치를 삭제하지 않는다. Intel 실행은 해당 하드웨어에서 별도 검사한다.

부팅 정체성은 명시적 `user/UID/com.apple.CoreSimulator.SimDevice.UDID` 호스트 launchd 작업의 단일 PID·bootstrap 경로와 `proc_pidinfo` 시작 시각으로 읽는다. cold boot의 `simctl spawn` 지연을 대상 판정과 분리한다. 작업이 준비되지 않으면 status는 `ready=false`이며 다른 작업이나 기기로 대체하지 않는다. PNG 크기와 OCR 좌표는 NSImage 논리 크기가 아니라 실제 인코딩한 픽셀 크기를 사용한다.

URL 전송 수락 뒤에는 scene의 실제 URL 수신 또는 해당 테스트 앱의 확인창이 나타날 때까지 읽기 관찰만 반복한다. 첫 캡처가 이전 화면이면 실패나 업무 완료로 판정하지 않고 제한 시간 안에서 다시 읽는다. URL 요청 자체는 재전송하지 않는다.

전용 UIKit fixture에는 별도 화면 유지 assertion을 걸지 않는다. Home 검사는 복귀 후 앱 상태로 확인하고, Lock 검사는 UI·캡처 검사 뒤에 실행한다. Lock은 scene 변화 또는 실제 PNG의 명확한 어두워짐으로 확인하며 두 값을 따로 기록한다. Lock 이후 scene 활성만으로 화면이 깨어났다고 판정하지 않는다. OCR은 대소문자가 다른 앱 이름을 같은 문자열로 비교하지만, 앱 이름과 유일한 열기 버튼이 모두 현재 캡처에 있어야 입력한다. 검사 중 화면이 흐려지거나 확인창이 없으면 다른 버튼을 추측하지 않는다.

## 실행 세션의 시작 회귀

`verify_startup.py`는 호출자의 실제 실행 컨텍스트에서 help·도구 목록·MCP handshake와 ping·진단을 검사한다. 제한된 실행 환경과 승인된 GUI 실행 환경에서 각각 실행한다. `SessionGetInfo`의 그래픽 플래그만으로 AppKit 초기화를 허용하지 않는다. 현재 프로세스에서 `CGSessionCopyCurrentDictionary`도 확인해야 한다. 이 사전 검사는 TCC 승인이나 실제 GUI 동작 성공을 보장하지 않는다.

WindowServer 세션을 확인할 수 없으면 `doctor`와 연결 상태는 `desktopSession.available=false`를 반환한다. 생략한 권한은 `null`, `permissionsStatus=not_probed`로 표시한다. 데스크톱 요청은 `gui_session_unavailable`로 중단한다. 이 상태를 사용자 권한 거부로 분류하거나 자동으로 권한을 요청하지 않는다. 실행 컨텍스트를 바꿀 때는 호스트의 승인 절차를 따른다. 도구가 자동으로 다른 세션이나 권한 경로로 전환하지 않는다.

세션이 없는 실행에서는 진단·MCP 메타데이터·일부 컨트롤러 상태 조회만 허용한다. 현재 실행 엔진의 나머지 도구는 파일처럼 GUI를 직접 사용하지 않는 기능도 보수적으로 중단한다. `sessionDictionaryProbeStatus`는 실제 nil 응답과 사전 조건 때문에 생략한 조회를 구분한다. 예상된 세션 오류는 자동 개선 요청을 만들거나 전송하지 않는다.

조건 대기는 불완전한 AX 수집을 원래 마감 시각 안에서 읽기만 다시 시도합니다. 불완전한 수집 뒤에는 안정 구간을 다시 측정합니다. 후속 완전한 관찰이 해소하지 못한 불확실성은 마감 때 `partial_coverage`로 유지하며, 이전 관찰만으로 현재 조건의 부재나 후조건 실패를 단정하지 않습니다. 워크플로의 이미 보낸 동작은 재전송하지 않습니다. `ConditionTests`는 실제 대기 루프의 내부 관찰 공급자를 사용해 복구·불확실성·안정 구간·보안/정체성 오류와 임시 관찰 정리를 검증합니다. 이 공급자는 도구 인수로 노출하지 않습니다.
