# Device Hub 직접 다루기

Xcode 27의 Device Hub(`com.apple.dt.Devices`, `Xcode.app/Contents/Applications/DeviceHub.app`)는 시뮬레이터와 USB 기기의 화면을 실시간으로 보여 주고, 기기 버튼과 설정을 누르는 앱이다. mac-cu의 Mac 앱 도구(`get_app_state`, `act`)로 백그라운드에서 읽고 누른다. 사용자가 화면을 함께 보게 할 때 쓴다.

mac-cu 1.17.1 이상이 필요하다. 그 아래에서는 Device Hub를 "창 없음"으로 읽는다(LaunchServices가 Device Hub의 pid를 -1로 주기 때문).

## 열기

- 창이 없으면 `open -b com.apple.dt.Devices`로 연다. 이때 Device Hub가 앞으로 나온다. `open -g`(백그라운드)는 창이 없을 때 창을 만들지 않는다.
- 창이 있으면 그다음부터는 `get_app_state`·`act`가 백그라운드에서 동작한다.

## 창의 구성 (`get_app_state {"app": "com.apple.dt.Devices"}`)

| 부분 | 요소 | 하는 일 |
|---|---|---|
| 왼쪽 목록 | `Row` 안의 기기 이름·런타임·`Simulator` | 행을 `click`하면 그 기기를 보여 준다. 창 제목이 "<기기> – iOS <버전>"으로 바뀐다 |
| 가운데(꺼진 기기) | `Button desc="Start"` | 부팅. 기기 부팅은 사용자에게 먼저 묻는다 |
| 가운데(켜진 기기) | `Home`, `Screenshot`, `Record`, `Rotate Right` | 홈, 스크린샷, 화면 녹화, 오른쪽으로 회전 |
| 가운데(접는 기기) | `Closed`, `Partially Open`, `Open` | 접기·반쯤 펴기·펴기 |
| 가운데 | 기기 화면의 요소(`설정`, `Safari`…) | 기기 안 앱의 접근성 요소. 탭은 mac-cu `simulator`로 한다 |
| 오른쪽 | `Appearance`(Light/Dark), `Liquid Glass`, `Color Filter`, `Text Size`, `Reduce Motion`, `Increase Contrast`, `Show Borders`, `Reduce Transparency`, `VoiceOver`, `Slow Animations`, `Location`, `Sound`, `Output`, `Input` | 기기 설정 |
| 도구 막대 | `Capture Keyboard`, `Resize mode`, 확대 단계, `Switch to compact window`, `More Actions` | 창 보기 |

요소 번호는 호출마다 바뀌므로 매번 트리에서 `desc`로 찾아 누른다.

## 예: Duo를 펴서 보여 주기

1. `get_app_state {"app": "com.apple.dt.Devices"}` → 목록에서 "iPhone Duo 27.1" 행 번호를 찾는다.
2. `act {"app": "com.apple.dt.Devices", "actions": [{"type": "click", "element": <행>}, {"type": "wait", "seconds": 2}]}`
3. 새 트리에서 `Button desc="Open"`을 `click`한다.
4. 독립 확인: `xcrun devicectl device info displays --device <UDID>`에서 안쪽 화면(`displayId` 3)이 `active: true`, 또는 mac-cu `simulator {"action": "hinge"}`가 180°.

같은 동작을 Device Hub 없이 하려면 mac-cu `simulator`의 `hinge`·`rotate`를 쓴다(drive.md). 둘은 같은 신호를 기기에 보낸다. Device Hub는 사용자가 보는 화면이고, `simulator`는 창 없이 동작한다.

## 무엇이 백그라운드로 되는가 (실측)

| 컨트롤 | mac-cu로 | 확인 경로 | 결과 |
|---|---|---|---|
| `Open` / `Closed` | `click` | devicectl 켜진 화면, `hinge` 각도 | 180° 안쪽 / 0° 바깥 |
| `Partially Open` | `click` | `hinge` 각도 | 130°, 안쪽 화면 |
| `Rotate Right` | `click` | `currentOrientation` | 한 번에 90°씩(rot90→180→270→0→90). 기기 자세 값은 남으니 끝나면 mac-cu `rotate portrait`로 되돌린다 |
| `Home` | `click` | 앞 앱(`describe`) | 설정 → 홈 화면 |
| `Screenshot` | `click` | 파일 | 바탕화면에 `Screenshot <기기> <날짜> at <시각>.png`(켜진 화면, 1398×2034) |
| `Record` → `Stop` | `click` 두 번 | 파일 | 바탕화면에 `Screen Recording <기기> … .mp4`. 녹화 중에는 버튼이 `Stop`, 끝나면 미리보기 `Close` 버튼이 생긴다 |
| `Reduce Motion` 등 스위치 | `click` | `devicectl device info appearance` | false↔true |
| `Text Size` 등 슬라이더 | `perform Increment/Decrement` | 같은 곳 | Large↔Extra Large |
| `Appearance`·`Color Filter`·`Location`·`Output`·`Input` 팝업 | 안 됨 | — | 항목이 트리에 나오지 않는다. `devicectl device settings appearance`, `simulate location`을 쓴다 |
| `More Actions` | 안 됨 | — | 메뉴 항목이 트리에 나오지 않는다 |
| 메뉴 막대 `Device`·`Controls` | 안 됨 | — | 항목이 모두 꺼진 상태(off)로 보이고, 앞으로 불러 눌러도 반영되지 않았다(Dark 시험) |

메뉴 막대에는 배터리, Face ID·Touch ID 결과, 위치 프리셋·이동 경로, 낙상 감지, Shake, Action Button, App Switcher, CarPlay, 메모리 경고, 초기화가 있다. 같은 일은 devicectl(`simulate biometrics`, `simulate location`, `process sendMemoryWarning`)이나 mac-cu `simulator button`으로 한다. 파일 이름의 `PM` 앞 공백은 좁은 공백(U+202F)이라 셸에서는 `*`로 찾는다.

## Watch 크라운

Device Hub에서는 크라운 그림 위에 커서를 두고 휠을 굴리면 크라운이 돈다(버튼은 없다). Device Hub 로그(`com.apple.dt.devicekit:ChromeInputView`)에 `Crown Scroll: Rotation ~0°, using normal -deltaY (…)`가 이벤트마다 찍히고, CoreDevice `IndigoHIDScroll`로 기기에 보낸다. 창 없이 같은 일은 mac-cu `simulator` `crown`으로 한다.

## 확인한 것 (2026-11-06, Xcode 27.2)

- Duo 27.1: `Open` → devicectl 안쪽 화면 active, 힌지 180°. `Closed` → 바깥 화면 active, 힌지 0°. Device Hub는 백그라운드였다.
- `devices://` URL 스킴이 있지만 어떤 경로를 받는지는 찾지 못했다(DeviceKit 안 Swift 코드).
