# Simulator 백엔드

`mac_simulator`는 선택한 Xcode의 `simctl`과 선택적 SimulatorKit 드라이버를 사용한다. 일반 macOS 제어에는 Swift·Xcode가 필요 없다. Simulator 기능은 Xcode·CoreSimulator·해당 OS 런타임을 요구한다. Simulator.app UI 분석에는 해당 GUI 앱과 Accessibility 권한도 필요하다.

## 대상과 동작

`list`에서 명시적 UDID를 선택하고 `status`를 읽는다. `booted`, 기본 기기, 첫 기기 별칭은 받지 않는다. `deviceIdentity`는 UDID·런타임·기기 유형·기기 디렉터리 세대를 묶는다. `bootID`는 해당 기기의 launchd_sim PID·프로세스 시작 ID를 묶는다. 부팅에는 `deviceIdentity`, 그 밖의 실행 중 기기 작업에는 두 식별자가 모두 필요하다. 같은 기기의 작업은 잠금으로 직렬화한다. 식별자가 바뀌면 상태를 다시 읽고 이미 실행한 동작의 결과를 확인한다.

| operation | 추가 인수와 결과 |
|---|---|
| `list`, `status` | 목록 또는 UDID의 정체성·상태. 입력을 보내지 않는다. |
| `boot`, `shutdown` | 정확한 기기의 부팅 요청 또는 종료. 부팅 식별자 조회 가능 상태는 `status.ready=true`와 `bootID`로 확인한다. 앱·화면 준비 완료는 별도 후조건이다. 기기가 Booted여도 IPC가 준비되지 않으면 status는 정체성 오류와 `ready=false`를 반환한다. |
| `install` | 명시한 절대 `.app` 경로. |
| `launch`, `terminate`, `uninstall` | 정확한 `bundleID`. 다른 앱으로 전환하지 않는다. |
| `open_url` | 명시한 scheme의 `url`. 기기 안의 URL handler를 연다. |
| `screenshot` | 정확한 기기의 native PNG를 비공개 로컬 경로에 저장한다. `ocr=true`는 선택적 로컬 Vision 텍스트·픽셀 좌표를 반환한다. `languages`로 언어를 지정한다. OCR 결과는 AX 의미·클릭 승인·요소 부재를 증명하지 않는다. |
| `record` | `durationSeconds=1...10`. simctl 녹화를 SIGINT로 닫고 실제 동영상 트랙·길이·추출 프레임을 검사한다. 오디오·마이크는 녹음하지 않는다. 중단된 파일을 완료로 보고하지 않는다. |
| `observe` | `pid`, `processStartID`, `windowID`로 Simulator.app의 정확한 창을 지정한다. 기기 이름이 전체 목록에서 유일하고 창 제목과 일치해야 한다. 유일한 `iOSContentGroup`의 자식만 반환한다. 누락·중복 시 전체 앱이나 다른 창을 읽지 않는다. 최대 1000노드·깊이 30, 출력 최대 200노드·384 KB다. 가림·미노출 UI 부재를 증명하지 않는다. |
| `probe_input` | 입력 없이 현재 Xcode의 private 드라이버 연결 가능성을 읽는다. 입력 수신 검증은 아니다. |
| `input` | 아래 선택적 입력. `privateAPI=true`를 매번 지정한다. |

```sh
macpilot call mac_simulator --json '{"operation":"list"}'
macpilot call mac_simulator --json '{"operation":"status","udid":"EXACT_UUID"}'
```

## 선택적 IndigoHID 입력

`gesture`는 `tap`, `long_press`, `swipe`, `drag`, `pinch`, `button`, `key` 중 하나다. 좌표는 기기 화면 전체의 0...1 정규화 값이며 원점은 왼쪽 위다. 화면 해상도를 추측하지 않는다. 입력은 해당 기기의 현재 화면으로 전달된다. `bootID`는 앱·화면 정체성이나 좌표 유효성을 보장하지 않으므로 입력 직전에 대상 앱 화면을 확인한다. 현재 screenshot이나 UI 프레임으로 좌표를 결정한다. 가로/세로 회전 후에는 다시 관찰한다.

- 탭·길게 누르기: `x`, `y`. 제스처 시간은 `duration=0.02...2`초다.
- 스와이프·드래그: `x`, `y`, `toX`, `toY`.
- 핀치: 첫 접점의 위 네 값과 `x2`, `y2`, `toX2`, `toY2`. 두 접점을 동시에 이동한다.
- `button`의 `key`: `home`, `lock`.
- `key`의 `key`: `return`, `escape`, `backspace`, `tab`, `space`, `left`, `right`, `up`, `down`. 임의 Unicode 문자열을 일부만 입력하지 않는다.

전체 인수와 부팅 식별자를 검사한 다음 첫 이벤트를 보낸다. raw 메시지는 현재 Xcode의 builder로 만들며 native HID client의 acknowledgement를 확인한다. 드라이버는 별도 실행 파일이라 private ABI 오류가 MCP 프로세스를 직접 종료하지 않는다. 취소·오류 시 남은 동작을 중단하고 눌린 접점을 해제한다. 강제 종료·Xcode 내부 정지까지 해제 완료를 보장할 수 없으므로 실패 후에는 기기 상태를 관찰한다. 전송이 불확실하면 같은 동작을 자동 재실행하지 않는다. macOS 전역 키보드·마우스나 다른 UDID로 전환하지 않는다.

`dispatchAcknowledged=true`는 native client의 전송 확인이다. 앱의 값·화면·장면·제스처 결과는 별도로 관찰한다. `businessPostconditionVerified`는 false다. Xcode private API는 안정된 공개 계약이 아니므로 다른 Xcode 버전은 해당 환경에서 다시 검증한다. 실제 iPhone·iPad 입력을 지원한다는 뜻은 아니다.

## 개발 검증

`verify_simulator.py`는 전용 기기를 만들고 합성 UIKit 앱으로 실제 수신을 검사한다. 기존 전용 기기를 재사용하려면 `--udid`를 주며 이름을 검사한다. 개인 앱·다른 기기는 종료·삭제하지 않는다. 실행 파일 해시, 기능별 검사, 실제 PNG·동영상·게스트 상태와 미검증 범위를 근거 디렉터리에 남긴다. 테스트가 만든 기기만 마지막에 삭제한다.

```sh
python3 macpilot/scripts/verify_simulator.py --binary /absolute/MacPilot.app/Contents/MacOS/macpilot --evidence /new/evidence/directory
```

CoreSimulator와 SimulatorKit은 실행 시 선택한 Xcode에서 읽는다. 해당 framework를 재배포하지 않는다. 함수 계약 조사에는 [Meta idb의 Indigo 구현](https://github.com/facebook/idb/blob/main/FBSimulatorControl/HID/SimulatorIndigoHID.swift)과 [native client](https://github.com/facebook/idb/blob/main/FBSimulatorControl/HID/SimulatorIndigoHIDClient.swift)를 참고했다. Baepsae의 실행 파일이나 private 메시지 코드는 포함하지 않는다.
