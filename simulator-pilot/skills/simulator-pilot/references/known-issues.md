# 알려진 문제 (Xcode 27.2, macOS 27에서 겪은 것)

원인을 모르거나 우회만 있는 문제다.

**먼저: 다른 세션과 기기를 함께 쓴다.** 이미 켜져 있는 기기는 다른 세션이 쓰고 있을 수 있다. `sim-pilot claims`로 누가 쓰는지 보고(sim-pilot 1.2.0, 스킬 1.5.0부터), 내가 쓰는 기기는 `claim`으로 기록한다. 사용자가 고르지 않았다면 켜진 기기를 끄거나 다시 부팅하지 말고, 상태(접기·회전·설정)를 바꾸기 전에 묻는다. 내가 켠 기기만 끈다. 증상이 보이면 같은 명령을 반복하지 말고 아래 확인부터 한다. 기록 원본: mac-computer-use `docs/development/simulator-deep/README.md`의 E 표.

| 증상 | 확인 | 대처 |
|---|---|---|
| 켜져 있던 시뮬레이터가 **여러 대 동시에** 꺼짐. 진단 보고서에 `XPC_EXIT_REASON_SIGTERM_TIMEOUT` | `ls -t ~/Library/Logs/DiagnosticReports`의 `coalitionName`(`SimDevice.<UDID>`)과 시각이 같은지 | 같은 Mac의 **다른 세션이 기기를 켜고 끌 수 있다**(이 문제를 겪을 때 다른 세션이 같은 시뮬레이터를 쓰고 있었다). 작업 전후로 `xcrun simctl list devices booted`를 확인하고, 꺼졌으면 사용자에게 묻고 다시 부팅한다 |
| 부팅 직후 SpringBoard가 반복해서 죽음(`BKSDisplayServicesStart` 또는 `FBSDisplayMonitor _initWithDisplays`에서 `EXC_BREAKPOINT`), 앱 실행이 `FBSOpenApplicationServiceErrorDomain 5 system shell probably crashed` | `xcrun devicectl device info displays --device <UDID>`가 `No displays found` | 그 기기를 종료하고 **한 대만** 다시 부팅한다. iPad Pro 13(M5)은 이렇게 나았다. iPhone Duo 27.2(`1039F3C1-…`)에서도 같은 크래시가 반복됐다 |
| 여러 기기를 한 명령줄에서 잇달아 `simctl boot`하자 하나가 `NSPOSIXErrorDomain 22 Invalid argument` | — | 한 대씩 부팅하고 `simctl bootstatus`로 끝난 뒤 다음 기기를 켠다 |
| mac-cu `act`의 `verify`(결과 판정)가 `'str' object has no attribute 'to_dict'` | — | 판정 API 쪽 문제로 보인다. `verify`를 빼고 스크린샷이나 devicectl로 확인한다 |
| mac-cu가 Device Hub를 "창 없음"으로 읽음 | mac-cu 버전 | 1.17.1 이상으로 올린다(LaunchServices가 Device Hub pid를 -1로 줌) |
| 키보드 언어를 바꾼 직후 첫 `type`이 칸에 들어가지 않음 | 스크린샷 | 한 번 더 보낸다. 원인 미상 |
| 홈 버튼이 아닌 같은 앱 안의 화면 전환(제어 센터 편집 모드 등) 뒤 `describe`가 몇 초 동안 이전 화면을 줌 | — | `wait`로 다음 화면의 요소를 기다린다 |
