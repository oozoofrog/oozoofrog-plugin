# macOS 입력·관찰 기술 조사

조사일: 2026-10-16. 현재 개발 환경은 Apple Silicon, macOS 27.0.1, Apple Swift 6.4다. 이 문서는 공개 Apple 문서와 로컬 SDK를 우선한다. API가 존재한다는 사실과 현재 기기에서 동작을 검증했다는 사실을 구분한다.

## 결론

외부 패키지나 모델 없이 일반 macOS 앱을 제어하는 기본 조합은 AXUIElement, Quartz CGEvent, ScreenCaptureKit, Vision이다. 앱별 좌표를 별도로 보관하면 사용자 커서를 이동하지 않는 가상 포인터를 구현할 수 있다. 이 상태는 WindowServer의 두 번째 커서나 독립된 키보드 포커스가 아니다.

공개 API의 PID 대상 이벤트는 지원하지만 모든 앱의 백그라운드 클릭·드래그를 보장하지 않는다. 호스트 데스크톱과 입력 포커스까지 분리해야 한다면 별도 VM 또는 별도 로그인 세션이라는 실행 환경이 필요하다. 가상 HID를 하나 더 연결하는 것만으로 앱마다 독립된 커서·포커스가 생기지 않는다. 이 결론은 아래 API의 기능과 입력 대상 범위에 따른 설계 판단이다.

## 기술별 판단

| 기술 | 제공 기능 | 대상·권한·제약 | 이번 구현 |
|---|---|---|---|
| AXUIElement / AXUIElementPerformAction | 의미가 있는 컨트롤의 조회·클릭·증감·메뉴 동작 | 접근성 권한. 앱의 AX 지원 수준에 좌우됨 | 기본 조작 경로 |
| AXUIElementSetAttributeValue | 값, 포커스, 선택 범위 변경 | 속성이 settable인지 검사해야 함. 앱이 거부할 수 있음 | 값·포커스·UTF-16 선택 범위 |
| AXObserver | 접근성 변경 알림 | 알림 누락·앱 지원 차이. 알림 자체는 대상의 최신성 증거가 아님 | 기본 구현은 동작 직전 재조회 |
| CGEvent.postToPid | 특정 프로세스에 Quartz 키·마우스 이벤트 전송 | Post Event/접근성 권한. 창별 백그라운드 수신은 보장되지 않음 | 기본 합성 입력 경로 |
| CGEvent.post(tap:) | 세션/HID 이벤트 스트림에 합성 입력 | 실제 커서·전경 포커스와 공유. 대상 전환·가림 위험 | 명시적 global 경로 |
| CGEvent.keyboardSetUnicodeString | 키 이벤트에 Unicode 문자열 부착 | IME 조합이나 하드웨어 키 입력과 다름 | 클립보드 없는 문자열 전송 |
| CGEventSource.privateState | 생성 이벤트 소스 상태 분리 | 이벤트 소스 상태 분리이며 별도 사용자 세션이 아님 | 사용자 modifier 상태의 암묵적 상속 감소 |
| CGEventTap / NSEvent global monitor | 실제 입력 관찰·필터 | listen 권한 및 보안 입력의 제약. 합성 입력·장치 생성과 별개 | 키보드 후킹을 구현하지 않음 |
| CGWarpMouseCursorPosition / CGDisplayMoveCursorToPoint | 실제 단일 커서 위치 변경 | 워프만으로 mouse event를 만들지 않음 | 가상 포인터에는 사용하지 않음 |
| CGAssociateMouseAndMouseCursorPosition | 전경 앱에서 마우스 delta와 화면 커서 연결·해제 | 주로 게임·상대 좌표 처리. 앱별 두 번째 커서 아님 | 사용하지 않음 |
| NSCursor / 오버레이 NSPanel | 커서 모양·시각 표시 | 이벤트 라우팅이나 독립 포커스를 만들지 않음 | 테두리 없는 라이브 프리뷰와 별도 데스크톱 화살표·대상 강조 |
| NSEvent.mouseEvent / windowNumber | AppKit 창 메타데이터를 가진 이벤트 구성 | 다른 앱 수신을 보장하지 않음. CGEvent 변환 시 창 로컬 좌표 메타데이터에 주의 | 조사·런타임 비교 후 Quartz 직접 생성 선택 |
| NSApplication.postEvent / sendEvent | 현재 앱의 이벤트 큐·응답 체인에 전달 | 다른 앱을 임의로 제어하는 API가 아님 | fixture 수신 검증에만 해당 |
| AXUIElementPostKeyboardEvent | AX 앱 대상으로 키 전달 | 현재 문서에서 deprecated. 현대 Unicode·이벤트 API를 우선 | 신규 구현에서 제외 |
| IOHIDManager / IOHIDDevice | HID 장치 열거·장치 통신·report 관찰 | 물리 장치 접근과 가상 장치 생성은 구분해야 함 | 기본 제어에 불필요 |
| IOHIDUserDevice | 사용자 공간에서 가상 HID report 장치 생성 | 권한·시스템 정책·배포 조건을 별도 검증해야 함 | 기본 빌드에서 장치 생성 안 함 |
| CoreHID.HIDVirtualDevice | Swift actor로 가상 키보드·마우스 등의 HID report 장치 모델링 | macOS 15+. 가상 장치 entitlement와 서명 조건을 확인해야 함 | 조사·SDK 확인. 기본 의존성에 포함하지 않음 |
| HIDDriverKit / IOUserHIDDevice | 드라이버 형태의 HID 서비스·입력 report 구현 | DEXT 서명·프로비저닝·시스템 확장 승인 및 필요한 entitlement | 일반 제어의 필수 조건이 아니므로 제외 |
| IOKit HIDSystem / IOHIDPostEvent / kernel extension | 저수준 입력 서비스·구형 드라이버 경로 | API 공개성·권한·현대 OS 호환성 차이. kext는 별도 시스템 변경 | 미사용 |
| Virtualization.framework | VM의 가상 키보드·마우스·트랙패드와 게스트 디스플레이 | 게스트 전용 장치. 호스트의 기존 앱 창을 제어하는 기능이 아님 | VM 백엔드가 필요한 경우의 대안 |
| Apple Events / ScriptingBridge / AppleScript | 스크립팅 가능한 앱의 의미 기반 자동화 | 앱 사전·Automation 동의에 의존. 일반 포인터 가상화가 아님 | 사용자가 지정한 AppleScript/JXA만 고정된 `osascript` 경로로 실행 |
| System Events UI scripting | AX를 스크립팅으로 호출 | 같은 AX 제약에 추가 실행·Automation 경로 발생 | 직접 Swift AX 사용 |
| InputMethodKit / NSTextInputClient | 입력기·후보·조합 문자열과 클라이언트의 텍스트 입력 세션 | 입력 소스 설치·선택과 텍스트 클라이언트 구현에 속함. 임의 앱의 범용 키보드·포인터 가상화가 아님 | 일반 제어와 분리 |
| XCTest / XCUIAutomation | 테스트 러너에서 UI 조작·검증 | 테스트 실행·앱 구성에 의존. 범용 무설치 runtime 대체 아님 | 전용 fixture와 단위 테스트로 검증 |
| ScreenCaptureKit / SCScreenshotManager | 창·디스플레이 캡처 | 화면 기록 권한. 입력 기능 없음. 보호된 화면은 제한 가능 | 창 캡처 |
| Vision VNRecognizeTextRequest | 로컬 OCR | 인식 오차. 의미 판단 모델이나 앱 입력 기능이 아님 | 로컬 OCR |
| Screen Sharing / VNC / Remote Desktop | 별도 원격 제어·화면 전달 | 서버·세션·인증 설정 필요. 여러 클라이언트가 같은 세션을 공유할 수 있음 | 외부 서비스 없는 로컬 도구에는 미사용 |
| SkyLight / CGS / SLS 및 undocumented CGEvent 필드 | 비공개 WindowServer 이벤트 주석 등 | ABI·OS 호환성·배포를 보장할 수 없음 | export 조사. 호출 가능한 창 정체성 SPI와 나머지 연구 대상을 분리 |

비공개 API 추가 조사와 현재 호출 범위는 [비공개 API 범위](private-api.md)를 따른다.

## 가상 HID의 최신 경로

CoreHID는 `HIDVirtualDevice`와 `HIDVirtualDeviceDelegate`를 제공한다. descriptor와 vendor ID로 장치를 만들고 `dispatchInputReport(data:timestamp:)`로 report를 보낸다. Apple 문서는 가상 키보드 예제를 제공한다. 로컬 SDK의 availability는 macOS 15 이상이다. [Core HID](https://developer.apple.com/documentation/corehid), [HIDVirtualDevice](https://developer.apple.com/documentation/corehid/hidvirtualdevice), [Creating virtual devices](https://developer.apple.com/documentation/corehid/creatingvirtualdevices).

가상 장치에 대한 `com.apple.developer.hid.virtual.device`와 DriverKit 관련 `com.apple.developer.driverkit.family.hid.virtual.device`는 별도 키다. 이름이 유사하다는 이유로 교환하거나 DEXT와 일반 앱에 무작정 함께 넣으면 안 된다. 공식 문서의 설명과 실제 서명·프로비저닝 정책을 해당 배포 환경에서 확인해야 한다. 기본 바이너리는 어느 제한 entitlement도 요구하거나 추가하지 않는다. [HID virtual device entitlement](https://developer.apple.com/documentation/bundleresources/entitlements/com.apple.developer.hid.virtual.device), [DriverKit Family virtual HID](https://developer.apple.com/documentation/bundleresources/entitlements/com.apple.developer.driverkit.family.hid.virtual.device).

DriverKit은 서명과 필요한 entitlement를 검증하며 앱 번들에 포함한 시스템 확장을 통해 드라이버를 활성화한다. entitlement 파일에 키를 적거나 ad-hoc 서명하는 것만으로 승인된 권한을 얻었다고 볼 수 없다. 이번 구현은 드라이버 설치나 보안 설정 변경 없이 동작하는 경로를 선택했다. [Requesting Entitlements for DriverKit Development](https://developer.apple.com/documentation/driverkit/requesting-entitlements-for-driverkit-development), [IOUserHIDDevice](https://developer.apple.com/documentation/hiddriverkit/iouserhiddevice).

Apple OSS의 IOHIDUserDevice 헤더는 가상 장치 생성 API의 존재를 확인하는 자료다. 오래된 공개 소스가 현재 OS에서 제한 없는 실행을 보장하지는 않는다. [Apple IOHIDUserDevice source](https://github.com/opensource-apple/IOKitUser/blob/master/hid.subproj/IOHIDUserDevice.h), [Apple IOHIDResourceUserClient source](https://github.com/apple-oss-distributions/IOHIDFamily/blob/main/IOHIDFamily/IOHIDResourceUserClient.cpp).

## 스크립팅·입력기·테스트·원격 제어

InputMethodKit은 입력기와 텍스트 클라이언트 사이의 조합·후보 세션을 구현하는 프레임워크다. 일반 앱의 임의 컨트롤을 선택하고 독립된 포인터를 보내는 API로 해석하지 않는다. ScriptingBridge는 스크립팅 가능한 앱의 객체·동작을 다루는 별도 경로다. [InputMethodKit](https://developer.apple.com/documentation/inputmethodkit), [Scripting Bridge](https://developer.apple.com/documentation/scriptingbridge).

XCUIAutomation은 XCTest 기반 UI 조작과 상태 검증에 적합하다. 이번 도구의 범용 실행 파일은 테스트 러너를 요구하지 않는다. Screen Sharing은 다른 Mac의 화면·입력을 연결하는 서비스이며, High Performance 연결의 가상 디스플레이도 별도 연결 설정에 속한다. 로컬 앱별 가상 커서와 같은 개념으로 취급하지 않는다. [XCUIAutomation](https://developer.apple.com/documentation/xcuiautomation), [Share the screen of another Mac](https://support.apple.com/guide/mac-help/share-the-screen-of-another-mac-mh14066/mac).

## 커서와 키보드의 독립성

`CGAssociateMouseAndMouseCursorPosition(false)`는 마우스와 화면 커서의 연결을 해제한다. 별도의 포인터나 앱별 입력 세션을 생성하지 않는다. `CGWarpMouseCursorPosition`은 실제 커서를 옮기고 이벤트는 생성하지 않는다. 이러한 API로 두 번째 macOS 커서를 만들었다고 주장하면 부정확하다. [CGAssociateMouseAndMouseCursorPosition](https://developer.apple.com/documentation/coregraphics/cgassociatemouseandmousecursorposition(_:)), [CGWarpMouseCursorPosition](https://developer.apple.com/documentation/coregraphics/cgwarpmousecursorposition(_:)), [Controlling the Mouse Cursor](https://developer.apple.com/library/archive/documentation/GraphicsImaging/Conceptual/QuartzDisplayServicesConceptual/Articles/MouseCursor.html).

이번 도구의 가상 커서는 선택 창에 속한 좌표다. 입력은 AX나 PID 이벤트로 실행한다. 포커스는 앱의 AX 포커스와 검증하며 실제 전경 앱과 구분한다. PID 이벤트를 보냈다는 사실은 해당 창이 올바르게 처리했다는 증거가 아니므로 별도 후조건을 확인한다. [CGEvent](https://developer.apple.com/documentation/coregraphics/cgevent), [postToPid](https://developer.apple.com/documentation/coregraphics/cgevent/posttopid(_:)), [AXUIElement header](https://developer.apple.com/documentation/applicationservices/axuielement_h).

마우스 이벤트에는 이름이 공개된 `CGEventField.mouseEventWindowUnderMousePointer`와 `mouseEventWindowUnderMousePointerThatCanHandleThisEvent`를 사용한다. 로컬 SDK의 `CGEventTypes.h`는 이 필드가 10.7부터 공개됐다고 명시한다. 이 필드와 비공개 숫자 필드·SkyLight 주석 함수를 구분한다. 전경 입력의 실제 hit test는 `NSWindow.windowNumber(at:belowWindowWithWindowNumber:)`로 수행한다. 이 API는 마우스를 무시하는 창과 투명한 영역을 고려한다. [CGEventField](https://developer.apple.com/documentation/coregraphics/cgeventfield), [NSWindow hit test](https://developer.apple.com/documentation/appkit/nswindow/windownumber(at:belowwindowwithwindownumber:)).

Virtualization은 게스트에 절대 좌표 포인팅 장치를 제공하며 `VZVirtualMachineView`가 VM에 입력을 전달한다. macOS 게스트용 키보드·트랙패드 구성도 제공한다. 호스트 사용자와 포커스가 충돌하지 않는 완전한 격리가 필수라면 VM을 별도 제품 범위로 설계해야 한다. [VZUSBScreenCoordinatePointingDeviceConfiguration](https://developer.apple.com/documentation/virtualization/vzusbscreencoordinatepointingdeviceconfiguration), [VZMacKeyboardConfiguration](https://developer.apple.com/documentation/virtualization/vzmackeyboardconfiguration), [Running macOS in a virtual machine on Apple silicon](https://developer.apple.com/documentation/virtualization/running-macos-in-a-virtual-machine-on-apple-silicon).

## 관찰과 보안 조건

AX는 컨트롤의 의미·값을 제공하고 ScreenCaptureKit은 픽셀을 제공한다. 어느 한쪽의 빈 결과만으로 UI가 없다고 결론 내리지 않는다. screenshot은 `desktopIndependentWindow` filter와 `SCScreenshotManager`를 사용한다. 그림자와 실제 커서를 제외하고 반환 크기를 좌표 변환에 기록한다. [SCScreenshotManager](https://developer.apple.com/documentation/screencapturekit/scscreenshotmanager), [captureImage](https://developer.apple.com/documentation/screencapturekit/scscreenshotmanager/captureimage(contentfilter:configuration:completionhandler:)).

접근성·화면 기록·이벤트 전송·이벤트 관찰 권한은 각각 조회한다. 일반 제어에는 이벤트 후킹을 설치하지 않는다. 보안 입력이 활성화되면 합성 입력을 중단한다. 비밀번호용 AX 노드와 하위 노드는 값 수집·입력에서 제외한다. [CGPreflightPostEventAccess](https://developer.apple.com/documentation/coregraphics/cgpreflightposteventaccess()), [AXUIElementSetAttributeValue](https://developer.apple.com/documentation/applicationservices/axuielementsetattributevalue(_:_:_:)).

## 의존성과 검증 경계

- 개발 시: Apple Swift 컴파일러와 SDK, XCTest. 외부 SwiftPM 패키지 없음.
- 실행 시: macOS 14 이상, Apple 시스템 프레임워크. 명시적 Shortcuts·OSA 작업에는 고정된 Apple 시스템 실행 파일 `/usr/bin/shortcuts`, `/usr/bin/osascript`를 사용함. ChatGPT·Codex·TypeSafe·Python·Node·브라우저·API 키·모델 다운로드와 제3자 패키지는 없음.
- 호출 형식: 로컬 CLI JSON 또는 직접 구현한 로컬 stdio MCP. 어느 호스트나 로컬 스크립트에서도 호출 가능.
- 자연어 이해·계획·이미지 의미 해석: 호스트의 역할. 도구는 모델을 포함하지 않으며 스스로 자유 형식 목표를 계획하지 않음.
- CoreHID 장치 생성·DriverKit·VM·다른 로그인 세션: 조사 범위이며 이 배포의 실행 검증 범위에는 포함하지 않음.
- 실제 수신 결과·현재 권한·서명·빌드 결과는 각 실행의 로컬 `evidence/` 보고서에 기록한다. 기존 설치본의 증거는 배포에 포함하지 않는다. API 조사만으로 이 결과를 대신하지 않는다.
