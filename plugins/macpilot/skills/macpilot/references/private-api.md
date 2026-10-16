# 비공개 API 범위

기준일: 2026-10-17. 비공개 API도 필요하면 사용한다. 공개 API·AX·앱 스크립팅이 같은 작업을 충족하면 그 경로를 유지한다. 심볼 export, ABI, 호출 성공, 앱 상태 변화와 배포 호환성은 별도 검증이다. OS의 모든 private API를 조사하거나 지원했다고 주장하지 않는다.

## 현재 호출 백엔드

`mac_private operation=window_ids enabled=true`는 대상 `pid`·`processStartID`를 확인하고 `_AXUIElementGetWindow`를 동적 로드한다. AX 창과 WindowServer 창 ID를 연결한다. `mac_observe privateAPI=true`는 이 ID로 창을 선택하고 이후 AX 재조회에서도 같은 창 ID를 검증한다. 제목·크기가 같은 창의 모호한 추정을 줄이는 용도다. 기본은 false다.

함수 선언은 [Rectangle의 bridging header](https://github.com/rxhanson/Rectangle/blob/main/Rectangle/Rectangle-Bridging-Header.h)와 [yabai의 extern.h](https://github.com/asmvik/yabai/blob/master/src/misc/extern.h)에서 확인했다. 헤더의 선언을 참고했으며 외부 제품 코드를 가져오거나 의존성으로 추가하지 않았다. 현재 Apple Silicon/macOS 27.0.1의 전용 앱에서 WindowServer·fixture 창 ID와의 일치를 검증했다. macOS 14·Intel·다른 OS 빌드는 별도 검증이 필요하다.

Accessibility 권한을 먼저 확인한다. 프레임워크·심볼이 없으면 `private_api_unavailable`, 호출 오류는 `private_api_failed`로 반환한다. opt-in이 없으면 호출하지 않는다. TCC·SIP를 우회하거나 별도 프로세스에 코드를 주입하지 않는다.

## 조사 카탈로그

`mac_private operation=catalog`는 현재 OS에서 `dlopen`·`dlsym`으로 export만 조회한다. `callableBackend=research-only`인 심볼은 호출하지 않는다.

| 영역 | 조사 심볼 | 다음 호출 백엔드의 전제 |
|---|---|---|
| HIServices 창 정체성 | `_AXUIElementGetWindow` | opt-in 백엔드 구현·실제 검증 |
| SkyLight 연결·포커스·이벤트 | `SLSMainConnectionID`, `SLSNewConnection`, `_SLPSSetFrontProcessWithOptions`, `SLPSPostEventRecordTo` | OS별 ABI와 이벤트 수신·전경 부작용 검증 |
| 창·Spaces | `SLSOrderWindow`, `SLSGetWindowBounds`, `SLSGetWindowLevel`, `SLSCopyManagedDisplaySpaces`, `SLSCopySpacesForWindows`, `SLSMoveWindowsToManagedSpace` | 실제 작업에 공개 API의 한계가 재현되고 선택 창·Space 후조건을 검사할 수 있어야 함 |
| 시각 상태 | `SLSSetWindowAlpha`, `SLSSetWindowTransform` | 복구 가능한 대상 상태 및 종료 후 정리 검증 |
| 디스플레이 | `DisplayServicesGetBrightness`, `DisplayServicesSetBrightness`, `CoreDisplay_Display_GetUserBrightness`, `CoreDisplay_Display_SetUserBrightness` | 장치별 ABI·지원·원래 값 복원 및 실제 밝기 검증 |

로컬 private framework 이름 목록은 조사 후보 인벤토리다. 전체 함수·ABI 조사나 지원 목록이 아니다. SkyLight 함수 선언의 근거는 위 yabai 소스이며, private API를 사용하는 외부 제품의 권한·설치 방식을 MacPilot에 그대로 적용하지 않는다.

새 백엔드는 실제 실패 재현 → 선언·ABI 확인 → 가용성 probe → 명시적 opt-in → 전용 fixture → 독립 후조건 → OS별 결과 기록 순서로 추가한다. 권한 경계를 완화하는 방법과 임의 주소·함수를 호출하는 범용 FFI 도구는 제공하지 않는다.
