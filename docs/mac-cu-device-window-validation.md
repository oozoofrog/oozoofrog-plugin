# Native device window validation

The simulator LCD is an AppKit device window. The HTML concept is a visual reference only; framebuffer content, control actions, masks, input and lifetime come from the native implementation.

## Reproducible checks

From the repository root:

```sh
swiftc -typecheck mac-computer-use/skills/mac-computer-use/scripts/mac-cu-src/*.swift
bash mac-computer-use/tests/check-simulator-gestures.sh
python3 scripts/sync_skill_mirrors.py --package mac-computer-use --write
python3 -m unittest discover -s scripts/tests -v
python3 scripts/sync_skill_mirrors.py --package mac-computer-use
git diff --check
```

The gesture suite compiles actual production classes. It checks model masks, aspect fitting, chrome bounds, transparent/handle/LCD/resize hit targets, focus-mode visibility, control availability, actual-state-driven command arguments, capture image selection, inverse coordinate fitting at different view sizes, and Retina marker scale. It retains the existing keyboard, touch, HID, preview, occlusion, toolbox consent/draft/error, and native spring tests.

Two native details matter for future layout changes:

- NSWindow can normalize fractional requested dimensions. Tests compare the window after a transition against its initial **actual content bounds**, while still requiring exact final component frames and suppressing stale completions.
- On macOS 27 the AppKit/SwiftUI spring bridge can omit completion after a reversal during the initial delay, leaving subpixel residuals. `SimulatorToolboxView` keeps the live spring for motion and schedules one cancellable, generation-checked settlement after its response envelope. It does not poll or add a recurring window timer. Immediate transitions and stale settlement work cannot finish a later transition. Keep the early/middle/late reversal tests.

## Isolated live app

Use an unlocked, awake interactive desktop and run foreground tests serially. Check current devices and claims, then claim an explicitly selected booted device. Do not force another session’s claim, boot/shutdown/reset a shared device, or replace the installed app.

```sh
~/.local/bin/sim-pilot status
~/.local/bin/sim-pilot claims
~/.local/bin/sim-pilot claim --udid <UDID> --note 'Native LCD validation'
python3 mac-computer-use/tests/check-simulator-window-live.py --udid <UDID> --output /tmp/mac-cu-lcd-check-unique
~/.local/bin/sim-pilot release --udid <UDID>
```

The live runner builds every production Swift source, replacing only the temporary executable dispatch so it opens a development window rather than the installed daemon/client. It uses a separate bundle identifier, no setup.py, no global registration, no daemon socket and no installed cache writes. Its app, source hashes, compile log, live log and available screenshots remain under the chosen new output directory. The runner rejects an unclaimed device and a locked/asleep desktop.

`--backend-only` runs separate background backend/presentation checks without Mac input or activation. It does not relax the foreground runner’s focus guard or count as physical control/focus validation. Use it for independent device readbacks after retaining a foreground interference failure.

Background checks also invoke the production focus-loss delegate with real held HID input; that validates cleanup delivery, not an OS focus transition.

The runner uses programmatic AppKit events and real production buttons in the native foreground window, plus the existing serialized simulator backend. It checks actual framebuffer/activation, a Settings-icon tap when available and Home readback, rotation on the inner display (the folded SpringBoard cover stays portrait), hinge readback, focus entry/return, view coordinate mapping, focus-loss cleanup, actual capture bytes, close/reopen and the Dock restore function. It attempts to restore the initial hinge and orientation on success and caught failures; a forcibly terminated test cannot run this cleanup. No device is shut down. Home/navigation are visible test actions and do not restore the previously foreground guest app.

A successful command, source assertion or cached NSView bitmap alone is not visual proof. `LIVE_UI` paths name actual WindowServer screenshots. `ENVIRONMENT screenshot unavailable` retains the capture error and means no screenshot was obtained for that stage. Inspect the images before reporting their appearance. A failed assertion stops dependent checks and still attempts device restoration. The rotation readback assertion records its failure while allowing independent lifecycle/capture checks to complete; the run still exits as failed.

Physical capsule/resize drags, click-through to another app through transparent pixels, multiple physical displays/scales, VoiceOver operation, OS accessibility setting changes, save-panel interaction/failure presentation and actual device-shutdown handling require separate checks. A model/mock shutdown check must not be described as actual device shutdown. Do not weaken guards or terminate somebody else’s simulator to complete validation.

## 실행 기록 — 2026-11-08

macOS 27.2 / Xcode 27.2, 실제 iPhone Duo `18090CB8-DCB2-4344-A6BE-A70C40DDEF69` (iOS 27.2)에서 확인했다. 전역 설치본과 Plugin 캐시는 교체하지 않았다.

- 타입 검사, 전체 `check-simulator-gestures.sh`(Phone 및 두 Watch 크기의 네이티브 스프링 샘플링 포함), 배포 unittest 48개, 정식 미러 동기화/일치 검사, `git diff --check`가 통과했다. 원본·미러 `quick_validate.py`는 기본 Python에 PyYAML이 없어 `uv run --with pyyaml python`으로 각각 통과했다. 트리거와 UI 메타데이터는 기존 범위를 유지하며 원본·미러가 일치한다.
- 전경 격리 앱에서는 표준 제목 막대/신호등 부재, 실제 프레임버퍼, 키보드 포커스, 손잡이/LCD/여백 hit 분리, 2× Retina에서 두 창 크기의 좌표 변환, 실제 LCD 이벤트와 Home 복귀를 확인했다. 후속 전경 실행은 Brave가 전경이 되어 보호 검사에서 중단됐다. 해당 실패 기록은 유지했고 보호 검사를 완화하지 않았다.
- 최종 백그라운드 실행에서는 실제 안쪽 화면의 `rot90 → rot0`, 130° 접기 readback, 집중 모드/도구 복원, 실제 캡처 저장·재읽기 바이트 일치, 프리뷰 25%에서도 LCD alpha 1 유지, 닫기 시 timer/registry/preview 정리와 재열기를 통과했다. 실제로 누른 HID 키/접점의 해제는 생산 focus-loss delegate를 테스트에서 호출해 확인했으며 OS 포커스 전환 자체의 검증과 구분한다.
- 실제 WindowServer PNG를 읽어 제목 막대 없는 기기와 주변 조작부, 집중/고급 도구 상태를 확인했다. PNG 외곽 픽셀 alpha는 0이었다. 초기 창 캡처 실패도 보존했다. 최종 격리 앱의 모든 생산 Swift 소스 해시는 최종 checkout 파일과 일치했다.
- 처음 회전 검사는 펼친 뒤 이미 바뀐 화면 방향 대신 커버 방향을 기준으로 삼아 실패했다. 검사를 회전 직전 실제 방향과 비교하도록 고친 뒤 실제 변화와 복원을 확인했다. 네이티브 스프링의 초기 지연 중 역전 실패 및 NSWindow의 소수점 크기 정규화도 검사·생산 전환 처리에 반영했다.

재현에 사용한 최종 명령은 다음과 같다. 출력 디렉터리는 새 경로여야 한다.

```sh
python3 mac-computer-use/tests/check-simulator-window-live.py --backend-only --udid 18090CB8-DCB2-4344-A6BE-A70C40DDEF69 --output /tmp/mac-cu-lcd-native-check-20261108-backend-final
```

개발 증거는 `/tmp/mac-cu-lcd-native-check-20261108-backend-final/`의 `source-hashes.json`, `build.log`, `live.log`, `01-rotated.png`~`05-restored.png`, `active-display.jpg`에 남겼다. 전경 확인과 실패 기록은 `/tmp/mac-cu-lcd-native-check-20261108-2/`, `-3/`, `-5/` 등에 보존했다. 이 경로/파일 기록은 채팅 파일 첨부나 설치 완료를 뜻하지 않는다.

기기는 원래의 `rot0`, 0°로 복원했고 종료·재부팅·초기화하지 않았다. 실제 포인터로 손잡이/크기 조절, 다른 앱으로의 투명 영역 click-through, 여러 물리 디스플레이/배율, VoiceOver·OS 접근성 설정 변경, 저장 패널 조작과 저장 실패 표시, 실제 Dock 최소화/복원 및 기기 종료는 남은 수동 확인이다. 외부 HEAD 변경으로 보존 대상 문서가 추적 파일이 되었지만 이 작업에서는 해당 문서를 수정하거나 커밋·푸시하지 않았다.


## 추가 통합 검증 — 부동 툴바와 판단 설정

최종 전경 실행은 `/tmp/mac-cu-toolbar-final-live-20261108-8/`에 보존했다. 다음 명령으로 새 격리 앱을 빌드하고 실행했다(같은 셸에서 기기 claim 후 실행).

```sh
~/.local/bin/sim-pilot claim --udid 18090CB8-DCB2-4344-A6BE-A70C40DDEF69 --note 'Verify Duo inner orientation mapping'
python3 mac-computer-use/tests/check-simulator-window-live.py --udid 18090CB8-DCB2-4344-A6BE-A70C40DDEF69 --output /tmp/mac-cu-toolbar-final-live-20261108-8
```

- 실제 부동 메인 툴바 표시, 기본 모듈 분리·재결합과 단일 뷰 소유권을 통과했다. 설정 창의 보안 키 입력 필드와 기본 설정/키 없음 표시를 확인했고 `settings.png`를 읽어 확인했다. 실제 API 키를 입력하거나 인증 요청을 보내지 않았다.
- 네이티브 버튼의 실제 Home, 회전 `rot90 → rot0`, 130° 접기 readback, 집중 모드의 도구 패널 숨김·복귀, OS 창 포커스 이동 후 실제 HID 키/접점 해제, 실제 캡처 저장·재읽기, 닫기·재열기, 최소화 후 기존 Dock 복원 함수를 통과했다. Dock 아이콘을 실제 포인터로 클릭한 검사는 아니다.
- Duo 안쪽 화면은 방향 picker의 portrait를 `rot90`, landscape-left를 `rot0`으로 보고한다. 커버와 다른 축을 반영했고 실제 버튼 요청/기기 readback 및 네이티브 회귀검사로 확인했다. 앞선 실패 기록은 보존했다. 상태 모듈 분리 후 기본 모듈 레이아웃이 텍스트를 덮는 회귀도 검사한다.
- OpenAI 모의 검사는 요청 형식·응답 검증·거절·HTTP 오류·시간 초과·취소·입력 해제 중 요청 차단·성공 콜백 도착 중 취소·중복/늦은 완료를 검사했다. 브라우저 MCP 결과는 `text` 타입을 반환하며, verify 실패 시 이미 실행한 동작 결과를 보존한다. 실제 OpenAI 인증은 미검증이다.
- 실제 포인터 전송 권한 확인은 거부 상태였으므로 전역 입력을 보내지 않았다. 손잡이/크기 조절/도킹의 실제 포인터 드래그와 투명 영역의 다른 앱 클릭 통과는 수동 확인이 남는다. 보호 검사는 유지했다. 다중 디스플레이, VoiceOver, OS 접근성 설정 변경, 저장 패널 조작과 실패 표시, 실제 기기 종료도 남는다.

지속 실행 개발 창은 아래처럼 `--preview`로 연다. 자동 기기 조작 없이 생산 메뉴바와 실제 LCD를 표시하고 별도 preferences/Keychain service를 사용한다. 전역 설치본·설치 캐시·daemon socket을 교체하지 않는다.

```sh
python3 mac-computer-use/tests/check-simulator-window-live.py --preview --udid 18090CB8-DCB2-4344-A6BE-A70C40DDEF69 --output /tmp/mac-cu-device-final-preview-20261108-v2
```

배포 unittest 48개, 전체 Swift 타입 검사, 네이티브 제스처/도킹 검사, 판단 서비스 모의 검사와 응답 formatter 검사, 원본·미러 스킬 검증 및 정식 동기화 검사를 실행했다. 로컬 Git 이력 정리 후 원본·미러의 비공개 설정과 모든 Git 객체의 해당 식별자를 재검사했다. 로컬 refs/해시가 변경됐으며 원격 이력은 변경하거나 푸시하지 않았다. 사용자 파일과 무관한 문서를 보존했다.

최종 지속 실행본은 `/tmp/mac-cu-device-final-preview-20261108-v2/LCD Window Check.app`이며 준비 기록의 LCD alpha는 1, 제목 막대는 false, 실제 framebuffer는 true였다. 최종 생산 Swift 소스 전체를 `source-hashes.json`과 대조해 일치를 확인했다. `window.png`와 `toolbar.png`는 WindowServer에서 다시 캡처해 읽었고, 실제 설정 캡처와 함께 채팅의 HTML 렌더로 표시했다. 개발 앱은 실행 상태로 남겼다.
