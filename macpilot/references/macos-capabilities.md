# macOS 관찰·입력 백엔드 선택 기준

조사 기준일: 2026-10-16. 이 문서는 공개 Apple API와 선택적 private SPI를 선택하기 위한 유지보수용 기준이다. API 제공 여부, 현재 권한, 대상 앱의 실제 수신, 배포 서명은 서로 다른 증거다.

## 선택 순서

1. 작업이 공개된 협력형 동작에 정확히 대응하면 해당 백엔드를 먼저 사용한다. 앱·URL·파일 열기와 활성화는 `NSWorkspace`, 설치된 워크플로 실행은 `shortcuts` CLI, 사용자가 명시한 스크립트는 `NSAppleScript` 또는 `/usr/bin/osascript`, 명시적 클립보드 읽기·쓰기는 `NSPasteboard`를 사용한다.
2. 협력형 백엔드가 맞지 않으면 `AXUIElement`에서 대상과 필요한 동작을 다시 조회한다. 의미가 있는 컨트롤에는 `AXUIElementPerformAction`과 settable attribute를 사용한다.
3. AX에 의미 동작이 없고 합성 입력이 필요한 경우에만 `CGEvent.postToPid`를 사용한다. 전송 뒤에는 AX 또는 픽셀 후조건을 확인한다.
4. PID 대상 입력이 부족하고 사용자가 실제 데스크톱 조작을 허용한 경우에만 세션 전역 `CGEvent.post(tap:)`을 사용한다. 먼저 전경 앱과 좌표의 가림 상태를 확인한다.
5. 호스트 사용자와 독립된 포인터·키보드 포커스·데스크톱이 필수이면 입력 API를 바꾸지 말고 `Virtualization.framework` 기반의 별도 게스트를 설계한다.
6. 장치 수준 입력 호환성이 제품 요구사항일 때만 Core HID 또는 DriverKit을 별도 제품 범위로 검토한다. 일반 앱 자동화의 실패 복구 수단으로 추가하지 않는다.

브라우저·멀티 커서·프리뷰·파일·Codex 진단의 현재 지원 범위는 [작업별 워크플로](workflows.md)에 있다.

관찰은 AX와 ScreenCaptureKit을 함께 사용한다. AX가 노출하지 않은 화면 텍스트에는 Vision OCR을 보조 수단으로 사용한다. AppleScript는 사용자가 지정한 소스나 고정된 도구 동작에만 실행한다. 대상 앱의 scripting dictionary가 작업을 지원하는지 먼저 확인한다.

## 기능과 채택 판단

| 공개 기술 | 제공 범위 | 권한·배포 조건 | MacPilot 판단 |
|---|---|---|---|
| [`NSWorkspace`](https://developer.apple.com/documentation/appkit/nsworkspace) | 앱 실행·활성화 요청, URL·파일 열기 | 파일 접근 범위와 대상 앱의 수락에 의존 | 정확히 대응하면 UI 조작보다 우선 |
| [`shortcuts` CLI](https://support.apple.com/guide/shortcuts-mac/run-shortcuts-from-the-command-line-apd455c82f02/mac) | 설치된 단축어에 파일·텍스트 입력을 전달하고 결과 수신 | 단축어 자체의 권한·대화형 입력 조건을 따름 | 사용자가 식별한 단축어만 실행 |
| [`NSAppleScript`](https://developer.apple.com/documentation/foundation/nsapplescript) / [`/usr/bin/osascript`](https://support.apple.com/guide/terminal/automate-tasks-using-applescript-and-terminal-trml1003/mac) | 명시적 AppleScript 컴파일·실행, scriptable 앱의 명령 호출 | 대상 앱의 scripting dictionary와 Automation 동의에 의존 | 명시적 스크립트에만 사용 |
| [`NSPasteboard`](https://developer.apple.com/documentation/appkit/nspasteboard) | 공유 pasteboard의 형식화된 데이터 읽기·쓰기 | 읽기 시 사용자 pasteboard 접근 설정을 따름 | 명시적 read/write만. 입력 우회에 사용하지 않음 |
| [`AXUIElement`](https://developer.apple.com/documentation/applicationservices/axuielement_h) | UI 트리, 속성, 포커스, 노출된 action | 접근성 신뢰 필요. 대상 앱의 AX 구현에 의존 | 기본 관찰·조작 |
| [`CGEvent.postToPid`](https://developer.apple.com/documentation/coregraphics/cgevent/posttopid%28_%3A%29) | 지정 PID의 Quartz event stream에 키·마우스 이벤트 전송 | Post Event 접근 필요. 특정 창의 수신을 보장하지 않음 | AX가 부족할 때의 기본 합성 입력 |
| [`CGEvent.post(tap:)`](https://developer.apple.com/documentation/coregraphics/cgevent/post%28tap%3A%29) | 로그인 세션의 event stream에 이벤트 전송 | Post Event 접근 필요. 실제 세션의 포인터·포커스·가림 상태를 공유 | 명시적으로 허용한 전경 조작만 |
| [`SCScreenshotManager`](https://developer.apple.com/documentation/screencapturekit/scscreenshotmanager) | 창·앱·디스플레이 픽셀 캡처 | 화면 기록 승인 또는 시스템 content-sharing picker 선택 | 관찰 전용. 입력 기능 없음 |
| [`VNRecognizeTextRequest`](https://developer.apple.com/documentation/vision/vnrecognizetextrequest) | 캡처 이미지의 로컬 OCR과 후보 confidence | 이미지 소스의 접근 조건을 따름 | AX 문자열이 없을 때만 보조 관찰 |
| [Scripting Bridge](https://developer.apple.com/documentation/scriptingbridge) | scriptable 앱의 객체·명령을 Apple Events로 제어 | Automation 동의, usage description, 배포 구성 필요 | 앱별 명시적 통합에만 사용 |
| [`HIDVirtualDevice`](https://developer.apple.com/documentation/corehid/hidvirtualdevice) | 시스템이 외부 장치처럼 취급하는 가상 HID와 input report | macOS 15 이상. HID entitlement와 서명·프로비저닝을 별도 검증 | 기본 빌드에서 제외 |
| [HIDDriverKit](https://developer.apple.com/documentation/hiddriverkit) | DEXT 형태의 HID 서비스 | DriverKit entitlement, 프로비저닝, 시스템 확장 활성화 필요 | 드라이버 제품일 때만 사용 |
| [Virtualization](https://developer.apple.com/documentation/virtualization/running-macos-in-a-virtual-machine-on-apple-silicon) | 게스트 디스플레이와 게스트 전용 키보드·포인팅 장치 | VM 구성·게스트 설치·배포 범위가 추가됨 | 완전한 입력 격리가 필요할 때의 별도 백엔드 |
| [XCUIAutomation](https://developer.apple.com/documentation/xcuiautomation) | XCTest 과정의 UI 조작·검증 | 테스트 러너와 테스트 구성 필요 | fixture·회귀 테스트용. 범용 runtime이 아님 |

## 권한

- AX 사용 전에는 [`AXIsProcessTrustedWithOptions`](https://developer.apple.com/documentation/applicationservices/1459186-axisprocesstrustedwithoptions)를 조회한다. 프롬프트 요청과 사용자의 시스템 설정 승인을 구분한다.
- Quartz 입력 전에는 [`CGPreflightPostEventAccess`](https://developer.apple.com/documentation/coregraphics/cgpreflightposteventaccess%28%29)를 조회한다. 요청이 필요할 때만 `CGRequestPostEventAccess`를 호출한다.
- 화면 캡처 전에는 [`CGPreflightScreenCaptureAccess`](https://developer.apple.com/documentation/coregraphics/cgpreflightscreencaptureaccess%28%29)를 조회하거나 [`SCContentSharingPicker`](https://developer.apple.com/documentation/screencapturekit/sccontentsharingpicker)를 사용한다. 픽커는 사용자가 선택한 콘텐츠 범위만 승인한다.
- event tap으로 실제 입력을 관찰하는 기능에는 별도의 [`CGPreflightListenEventAccess`](https://developer.apple.com/documentation/coregraphics/cgpreflightlisteneventaccess%28%29)가 필요하다. MacPilot의 일반 제어는 입력을 후킹하지 않으며 이 권한을 요청하지 않는다.
- `NSAppleScript` 또는 `osascript`가 다른 앱을 제어하면 Automation 동의를 확인한다. 앱 패키징에는 [`NSAppleEventsUsageDescription`](https://developer.apple.com/documentation/bundleresources/information-property-list/nsappleeventsusagedescription)과, hardened runtime에서 [`com.apple.security.automation.apple-events`](https://developer.apple.com/documentation/bundleresources/entitlements/com.apple.security.automation.apple-events)를 함께 검토한다.
- `NSPasteboard.general`은 실행 중인 앱이 공유한다. 읽기와 쓰기는 사용자 요청에 포함된 경우에만 수행하고, 요청한 데이터 형식만 다룬다.
- 권한 승인은 이벤트 전송 성공이나 대상 앱의 상태 변경을 증명하지 않는다. 각 입력 뒤에 새 관찰과 작업별 후조건을 확인한다.

## 패키징과 보안 경계

범용 보조 앱의 Accessibility API 사용은 App Sandbox와 호환되지 않는다. 임의 앱으로 Apple Events를 보내는 기능도 sandbox 제한 대상이다. Apple은 이 제한을 [App Sandbox 문서](https://developer.apple.com/documentation/security/protecting-user-data-with-app-sandbox)에 명시한다. 따라서 범용 MacPilot 배포는 Mac App Store sandbox를 전제로 하지 않는다.

외부 배포 후보는 안정된 번들 식별자와 실행 경로를 사용하고 Developer ID로 서명한다. Hardened Runtime을 켜고 [Apple notarization](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution)을 통과한 산출물을 별도로 검증한다. ad-hoc 서명이나 로컬 실행 성공은 배포 증거가 아니다.

[`com.apple.developer.hid.virtual.device`](https://developer.apple.com/documentation/bundleresources/entitlements/com.apple.developer.hid.virtual.device)와 [`com.apple.developer.driverkit.family.hid.virtual.device`](https://developer.apple.com/documentation/bundleresources/entitlements/com.apple.developer.driverkit.family.hid.virtual.device)는 이름이 비슷하지만 서로 다른 entitlement다. DriverKit 경로는 [Apple의 entitlement 요청과 프로비저닝 절차](https://developer.apple.com/documentation/driverkit/requesting-entitlements-for-driverkit-development)를 따른다. 기본 앱에는 HID·DriverKit·시스템 확장 entitlement를 넣지 않는다.

도구는 보안 텍스트 노드의 값을 읽거나 입력하지 않는다. 캡처, AX 값, pasteboard 내용은 사용자 데이터로 취급한다. 클립보드는 명시적 읽기·쓰기에만 사용하며 암묵적 타이핑이나 키 입력 우회에 사용하지 않는다. 권한 우회와 키보드 후킹은 포함하지 않는다. Private API는 [비공개 API 범위](private-api.md)의 opt-in 백엔드만 호출하며 나머지는 심볼 조회로 제한한다.

## 공개 API의 한계

- AX는 대상 앱이 공개한 요소·속성·action만 제공한다. 빈 트리나 누락된 값은 화면에 콘텐츠가 없다는 증거가 아니다.
- `postToPid`는 PID의 event stream을 지정한다. 공개 API는 특정 백그라운드 창의 클릭·드래그 수신을 보장하지 않는다. 창 ID를 event routing 계약으로 해석하지 않는다.
- 전역 Quartz 입력은 동일 로그인 세션의 실제 포인터와 포커스를 공유한다. `CGWarpMouseCursorPosition`은 [실제 단일 커서를 이동](https://developer.apple.com/documentation/coregraphics/cgwarpmousecursorposition%28_%3A%29)하며 두 번째 커서를 만들지 않는다.
- 가상 포인터와 비활성 preview panel은 MacPilot 내부 상태와 표시다. 별도의 WindowServer 커서, 키보드 포커스 또는 입력 세션이 아니다.
- 가상 HID는 시스템에 장치를 추가한다. 앱별 독립 포인터나 포커스를 생성하지 않는다. 완전한 격리는 VM 또는 별도 로그인 세션의 책임이다.
- ScreenCaptureKit은 픽셀을 제공하고 Vision은 그 픽셀에서 텍스트 후보를 만든다. 둘 다 컨트롤 의미, 입력 수신, 작업 완료를 증명하지 않는다.
- SkyLight/CGS/SLS는 현재 export 조사 대상이다. ABI 검증 없이 호출하지 않는다. `_AXUIElementGetWindow`는 opt-in 창 정체성 백엔드로 제공한다. 문서화되지 않은 raw event 필드·커널 주입은 사용하지 않는다.
