# 권한 아이콘 안내 디자인 검토

검토일: 2026-10-17. 공개 저장소의 설명과 실제 창·드래그 소스를 확인했다. 해당 앱을 설치하거나 사용자의 권한을 변경하는 비교 실험은 하지 않았다. 외부 코드를 복사하거나 새 패키지 의존성을 추가하지 않았다.

- [AskForPermission](https://github.com/riko2chen/AskForPermission/tree/91f4dde33f9f5dd58a89d72f3f05aa4b149a1f0e): 시스템 설정 옆 안내 카드, 네이티브 `.app` 파일 URL 드래그, 설정 창 추적을 제공한다. `GuidePanelWindow.swift`는 테두리 없는 nonactivating panel을 사용한다. `DraggableAppIconView.swift`는 `NSWorkspace.icon(forFile:)`과 `NSDraggingItem(pasteboardWriter: bundleURL as NSURL)`를 사용한다.
- [PermissionFlow](https://github.com/jaywcjlove/PermissionFlow/tree/cb96db4bfd2342e8d8c56f2a7d51ca65b8aed6e2): 설정 창을 따라가는 부착 패널과 네이티브 앱 드래그를 제공한다. `FloatingDropPanel.swift`는 key/main 창이 되지 않도록 해 설정 창의 포커스를 유지한다. 드래그가 가능한 권한과 카메라·마이크·캘린더처럼 시스템 요청만 가능한 권한을 구분한다.

## MacPilot에 반영한 결정

평상시에는 **88×88pt 패널 안의 56pt 앱 아이콘 하나만** 표시한다. 제목, 설명문, 상태, 드롭다운과 버튼은 표시하지 않는다. macOS 설정이 권한 설명과 승인 UI를 제공한다. 안내는 툴팁·VoiceOver로 제공하고 자동 추가·권한 전환·재검사·닫기는 아이콘의 우클릭 메뉴에 둔다.

패널은 설정 창 옆에 붙고 위치를 따라간다. key/main 창이 되지 않으며 다른 앱으로 전환하면 숨는다. 기존 구현의 자동 추가는 안내 앱을 활성화해 포커스를 바꾸고 AX 창 목록에 의존했다. 아이콘 전용 패널에서는 이 전환을 제거하고, 소스의 공개 NSWindow 좌표·WindowServer 정체성과 대상의 AX 목록을 검증한다. 패널의 AX 노출도 별도로 지정해 VoiceOver 탐색을 지원한다.

자동 추가는 선택 기능이다. 수동 드래그는 최초 접근성이 없어도 사용할 수 있지만, 자동 추가에는 접근성·이벤트 전송 권한이 필요하다. 권한 스위치·사용자 인증·재실행 버튼은 자동 조작하지 않는다. 드롭 수락·목록 등록·권한 사전 검사·현재 MCP 노출은 별도 결과로 유지한다.
