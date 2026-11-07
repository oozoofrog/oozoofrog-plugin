# 도구가 없을 때

| 상황 | 대신 할 일 |
|---|---|
| mac-cu가 설치돼 있지 않다 | mac-computer-use 스킬의 설치 절차(`setup.py`, Xcode의 `swiftc`만 필요)를 안내한다. 설치 후 에이전트를 다시 시작해야 도구가 보인다 |
| Xcode 27 미만이라 `simulator`의 입력 동작이 안 된다 ("has no com.apple.coredevice.feature.remote.hid.digitizer") | `describe`·`wait`와 `screenshot`은 그대로 쓴다. 누르기·입력은 Claude 데스크톱 앱의 iOS 시뮬레이터 도구가 있으면 그것으로, 없으면 사용자에게 맡긴다 |
| 시뮬레이터가 막 부팅 중이다 | `xcrun simctl bootstatus <UDID> -b`로 기다린 뒤 다시 한다 |
| `describe`가 앞 앱을 못 읽는다 | 앱이 실행 중인지 확인하고 잠시 뒤 다시 한다. 그래도 안 되면 `screenshot` 좌표로 조작한다 |
| 스크린샷만 필요하고 mac-cu가 없다 | `xcrun simctl io <UDID> screenshot ~/Documents/claude-outputs/simulator-pilot/<이름>.png` |
| `swiftc`가 없다 | `xcode-select --install`로 Xcode 명령행 도구를 설치하라고 안내한다 |
| 사내망이 아니라 `decide`가 답하지 않는다 | 스크린샷을 보여 주고 사람이 판정한다 |
