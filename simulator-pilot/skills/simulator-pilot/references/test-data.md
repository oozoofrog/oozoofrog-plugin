# 테스트 데이터

## 사진

```sh
sim-pilot photos --udid <UDID> [--count 10] [--width 320] [--height 320] [--seed <단어>] [--grayscale] [--blur 1-10]
```

- picsum.photos에서 받아 `simctl addmedia`로 사진 앱에 넣는다. 기본 10장, 320×320.
- `--seed`를 주면 늘 같은 사진이 들어간다(스냅샷·재현용). 없으면 매번 다르다.
- 100장이 넘으면 사용자에게 확인한 뒤 `--yes`를 붙인다. 최대 2000장.
- 넣은 사진을 지우는 명령은 없다. 비우려면 기기를 `erase`해야 하므로(모든 데이터 삭제) 사용자에게 확인한다.

## 그 밖의 준비 (`xcrun simctl`)

| 항목 | 명령 |
|---|---|
| 위치 | `xcrun simctl location <UDID> set 37.3947,127.1112` (판교), 끝내기 `clear` |
| 권한 미리 허용 | `xcrun simctl privacy <UDID> grant photos\|camera\|microphone\|location\|contacts <번들 ID>` |
| 권한 초기화 | `xcrun simctl privacy <UDID> reset all <번들 ID>` — 실행 전에 확인 |
| 푸시 | 페이로드 JSON 파일을 만들고 `xcrun simctl push <UDID> <번들 ID> <파일>` |
| 다크·라이트 모드 | `xcrun simctl ui <UDID> appearance dark` / `light` |
| 글자 크기 | `xcrun simctl ui <UDID> content_size extra-large` (기본 `large`) |
| 상태 막대 고정(스크린샷용) | `xcrun simctl status_bar <UDID> override --time 9:41 --batteryLevel 100 --cellularBars 4`, 되돌리기 `clear` |
| URL·딥링크 열기 | `xcrun simctl openurl <UDID> "kakaotalk://..."` |
| 클립보드 | 텍스트는 mac-cu `simulator`의 `paste`를 쓴다 |

푸시 페이로드 파일은 `~/Documents/claude-outputs/simulator-pilot/`에 만든다.

## 기기 동작 흉내 (`xcrun devicectl`, Xcode 27 이상)

Xcode 27의 Device Hub와 같은 기능이다. 모든 명령 끝에 `--device <UDID>`를 붙인다. 이 기기에서 되는 기능 목록은 `xcrun devicectl device info details --device <UDID> --json-output -`의 `capabilities`에 있다.

| 항목 | 명령 |
|---|---|
| Face ID 등록·해제 | `xcrun devicectl device settings biometrics --enable` / `--disable`, 상태는 옵션 없이 |
| Face ID 인증 성공·실패 | `xcrun devicectl device simulate biometrics --success` / `--failure` (등록된 상태에서, 앱이 인증을 요청한 뒤) |
| 위치 경로 이동 | 경로 JSON을 만들고 `xcrun devicectl device simulate location route --route-file <파일>`, 끝내기 `simulate location clear` |
| 상태 막대 프리셋 | `xcrun devicectl device simulate statusBar preset screenshot\|low-battery\|no-service\|charging`, 되돌리기 `clear` |
| 회전 | `xcrun devicectl device orientation set p\|ll\|lr\|pu`, 현재 값 `orientation get` |
| 화면 녹화 | `xcrun devicectl device capture screen-record --destination <파일>.mp4 --duration <초>` |
| 메모리 경고 | pid를 찾아(`xcrun simctl spawn <UDID> launchctl list \| grep UIKitApplication:<번들 ID>`의 첫 칸) `xcrun devicectl device process sendMemoryWarning --pid <pid>` |
| 손쉬운 사용 | `xcrun devicectl device settings appearance --reduce-motion on\|off`, `--increase-contrast`, `--reduce-transparency`, `--text-size`, 현재 값 `info appearance` |
| VoiceOver | `xcrun devicectl device settings voiceover --enable` / `--disable` |
| 흔들기 | `xcrun simctl spawn <UDID> notifyutil -p com.apple.UIKit.SimulatorShake` (devicectl의 `notification post`는 시뮬레이터에서 지원하지 않는다) |
| Darwin 알림 상태 읽기·쓰기 | `xcrun simctl spawn <UDID> notifyutil -g <이름>` / `-s <이름> <값>`. 쓰기 전에 원래 값을 읽어 두고 끝나면 되돌린다 |
| 루트 인증서(프록시 디버깅) | `xcrun simctl keychain <UDID> add-root-cert <인증서.pem>`. **빼는 명령이 없다.** 되돌리려면 `keychain reset`(키체인 전체 삭제)뿐이므로 사용자에게 먼저 묻는다 |
| 키체인 초기화 | `xcrun simctl keychain <UDID> reset`. 로그인 토큰 등 앱의 키체인 항목이 모두 지워진다. **실행 전에 사용자에게 확인한다** |
| 키보드 언어 | 아래 "키보드 언어 바꾸기"를 따른다(mac-computer-use 스킬). CoreSimulator `setKeyboardLanguage:`도 같은 값(`KeyboardLastUsed`)을 쓰지만 전역 `AppleKeyboards`를 늘리고 `HardwareKeyboardLastSeen`을 0으로 바꾼다 |

경로 JSON 예(판교, 1초마다 20m/s로 이동):

```json
{"mode": "interval", "interval": 1.0, "speed": 20.0,
 "waypoints": [{"latitude": 37.3947, "longitude": 127.1112}, {"latitude": 37.4000, "longitude": 127.1080}]}
```

이 기기에서 위 동작 중 무엇이 되는지는 `sim-pilot caps --udid <UDID>`로 먼저 본다. 표에 `-`인 동작은 `CoreDeviceError 1001 not supported`로 실패한다.

### 손쉬운 사용 상태 읽기

접근성 문제를 재현하기 전에 현재 값을 읽어 두고, 끝나면 그 값으로 되돌린다.

| 읽기 | 명령 |
|---|---|
| Reduce Motion·투명도·테두리·Liquid Glass·색 필터·큰 글자 | `xcrun devicectl device info appearance` |
| VoiceOver | `xcrun devicectl device info voiceover` |
| 화면 요소의 접근성 라벨·id·value | mac-cu `simulator`의 `describe` ([drive.md](drive.md)) |

### iPhone Duo (화면이 둘인 기기)

iPhone Duo에서 확인한 차이다.

- **생체인증은 Touch ID다.** `settings biometrics`와 `simulate biometrics`를 그대로 쓰면 Touch ID에 적용된다.
- **화면을 지정해야 한다.** `capture screenshot`과 `capture screen-record`에 `--display-unique-id`가 없으면 "Cannot choose between 2 displays" 오류가 난다. `xcrun devicectl device info displays`에서 `active: true`인 화면의 `uniqueId`를 쓴다. 꺼진 화면(`backlight is off`)은 검은 화면으로 찍힌다.
- **`orientation set`은 적용되지 않는다.** 성공했다고 답하지만 화면은 그대로이고, `orientation get` 값도 실제와 다르다. Duo의 회전과 접기·펴기는 mac-cu `simulator`의 `rotate`·`hinge`로 한다([drive.md](drive.md)). 방향은 `info displays`의 `currentOrientation`과 `Main display orientation`으로 읽는다.
- 위치, 경로 이동, 상태 막대, 메모리 경고, 흔들기, 손쉬운 사용, VoiceOver는 iPhone 17과 똑같이 동작한다.
- mac-cu `simulator`로 화면을 다루는 방법은 [drive.md](drive.md)의 "iPhone Duo" 절을 따른다.

바꾼 설정(Face ID 등록, 회전, 손쉬운 사용, VoiceOver, 상태 막대)은 확인이 끝나면 되돌린다. `settings reset`은 기기의 모든 데이터를 지우므로 실행 전에 확인한다.
