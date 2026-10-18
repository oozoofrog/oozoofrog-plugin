# 개발과 검증

실행 코어·CLI·MCP·AX·캡처·CoreAudio·private API·Codex app-server 연결은 Swift다. 브라우저 확장은 JavaScript다. Python과 Node.js는 개발 검증 스크립트에서만 사용한다. 패키지는 외부 SwiftPM 의존성이 없다.

## 검증 명령

저장소 루트에서 실행한다.

```sh
xcrun swift test --package-path macpilot/tool
macpilot/scripts/build.sh
python3 macpilot/scripts/verify_mcp.py
python3 macpilot/scripts/verify_connection.py --binary macpilot/bin/MacPilot.app/Contents/MacOS/macpilot
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
