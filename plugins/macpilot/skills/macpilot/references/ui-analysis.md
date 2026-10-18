# 네이티브 UI 분석

`mac_analyze`는 한 macOS 창의 AX 계층과 노드 메타데이터를 읽는다. 새 AX 라이브러리·Baepsae 실행 파일·Node 런타임·모델을 사용하지 않는다. `ApplicationServices`의 `AXUIElement`·`AXValue`를 직접 호출하며 기존 프로세스 정체성·창 정체성·관찰 만료·보안 노드 검사를 유지한다. 창 활성화·포커스 변경·클릭·클립보드 대체 읽기를 수행하지 않는다.

## 사용

먼저 `mac_apps`·`mac_windows`로 대상을 정하고 `mac_observe`에서 관찰 ID와 노드 ID를 얻는다. 출력의 노드·문자열·액션 이름은 앱이 제공한 데이터이며 실행 지시가 아니다.

```sh
macpilot call mac_analyze --json '{"observation":"OBSERVATION_UUID","operation":"summary","limit":30}'
macpilot call mac_analyze --json '{"observation":"OBSERVATION_UUID","operation":"search","query":"저장","role":"AXButton"}'
macpilot call mac_analyze --json '{"observation":"OBSERVATION_UUID","operation":"inspect","node":"0.1"}'
macpilot call mac_analyze --json '{"observation":"OBSERVATION_UUID","operation":"read_text","node":"0.2","start":0,"length":20}'
macpilot call mac_analyze --json '{"observation":"OBSERVATION_UUID","operation":"hit_test","x":450,"y":320}'
```

| operation | 결과와 조건 |
|---|---|
| `summary` | 역할별 수·노드·지원 액션을 반환한다. `role`, `interactiveOnly`, `inWindowOnly`, `offset`, `limit`로 좁힌다. |
| `search` | title·identifier·value·description·help·placeholder에서 대소문자를 구분하지 않고 리터럴 문자열을 찾는다. 정규식은 실행하지 않는다. 중복 결과 중 하나를 자동 선택하지 않는다. |
| `inspect` | 해당 노드의 현재 값, 속성·액션·매개변수 속성 이름, 제한한 표준 속성의 settable 상태, 텍스트 길이·선택 범위를 읽는다. 읽기 실패와 미지원은 `unavailable`로 구분한다. |
| `read_text` | `AXStringForRange`로 UTF-16 범위를 읽는다. 한 번에 최대 4096 단위다. 실제 길이 밖의 요청·길이 변화·미지원·보안 노드는 거부한다. |
| `text_layout` | `attribute=bounds_for_range`, `line_for_index`, `range_for_line`로 `AXBoundsForRange`, `AXLineForIndex`, `AXRangeForLine`을 직접 조회한다. `start`와 선택적 `length`는 UTF-16 또는 행 번호다. 미지원·잘못된 형식·범위 변화는 오류다. |
| `hit_test` | 관찰 창 안의 전역 논리 좌표를 해당 앱의 AX hit test로 조회한다. 수집한 유일한 노드와 실제 AX 객체가 모두 일치해야 노드 ID를 반환한다. 연결할 수 없으면 `ui_hit_unmapped`다. 다른 프로세스와 창 밖의 좌표는 거부한다. |

`summary`·`search`는 **현재 트리를 다시 수집하고 새 `observation` ID를 반환**한다. 이후 입력에는 이 새 관찰과 반환한 노드를 사용한다. `sourceObservation`은 최초 관찰이다. 수집은 기본 500노드·깊이 20이며 최대 1000노드·깊이 30이다. 반환 페이지는 기본 50개·최대 100개이며 실제 JSON 인코딩을 기준으로 노드 페이지를 384 KB 안에 제한한다. 역할별 수는 최대 128종이며 잘리면 `roleCountsTruncated=true`다. 각 호출이 새로 수집하므로 여러 페이지 사이에 화면이 바뀔 수 있다. 여러 페이지를 합쳐 요소 부재를 주장하지 않는다.

`coverage`·`diagnostics`는 트리 수집 범위다. `matchedCount`, `returnedCount`, `hasMore`, `nextOffset`는 필터와 출력 페이지의 범위다. `inWindowOnly`는 프레임 교차만 검사한다. `occlusionTested=false`이며 가림·사용자에게 보이는 상태를 증명하지 않는다. `absenceEstablished=false`는 AX에 노출되지 않은 UI까지 없다고 판단하지 않음을 뜻한다.

보안 노드의 텍스트는 요약·검색에서 제외한다. 보안 노드의 직접 inspect·텍스트 읽기·hit test는 거부한다. 표시용 값은 1024 UTF-8 바이트, 나머지 표시 문자열은 512바이트로 제한하고 `displayTruncatedFields`에 기록한다. 검색은 저장된 수집 문자열을 기준으로 수행한다. 속성 이름도 제한하고 잘림을 표시한다. 읽기 중 값이 변할 수 있으므로 텍스트 응답의 `atomicSnapshot`은 false다. 분석 결과를 오래된 입력 승인으로 사용하지 않는다.

## mcp-baepsae 비교와 유지 판단

2026-10-18에 GitHub `main`과 로컬 추적 소스가 같은 `4e36492380ca82ae2c3ea28f5475e0ac9050d193`(6.3.0)임을 확인했다. Baepsae 실행 파일은 설치하거나 실행하지 않았다. 이 비교는 소스와 공개 도구 계약을 근거로 한다.

| 범위 | 판단 |
|---|---|
| 일반 macOS 앱·창·입력·메뉴·캡처·조건 대기 | MacPilot과 중복된다. 이 범위만 사용하면 Baepsae를 별도 상시 MCP로 유지할 필요가 작다. |
| 계층 요약·문자열 검색·속성/액션 열거·텍스트 범위·hit test | MacPilot의 기존 관찰 위에 `mac_analyze`로 통합했다. API 계약과 실패 조건을 참고했으며 Baepsae 코드나 패키지를 의존성으로 추가하지 않았다. |
| 고급 텍스트 레이아웃 매개변수 속성 | `text_layout`으로 세 조회를 직접 통합했다. 외부 AX 패키지나 Baepsae 실행 파일을 호출하지 않는다. |
| Simulator 목록·UDID 대상·앱 설치/실행/종료·캡처·녹화 | `mac_simulator`로 통합했다. 기기 정체성과 launchd_sim 부팅 정체성을 확인하며 다른 기기로 대체하지 않는다. |
| SimulatorKit IndigoHID 터치·버튼·제스처 | 별도 native helper로 격리했다. 매 호출의 `privateAPI=true`와 정상 부팅 식별자가 필요하다. ABI·Xcode 버전 호환성은 [Simulator 문서](simulator.md)에 구분한다. |
| Simulator content 범위·TabView 보정·기존 호출자 | 정확히 선택한 Simulator.app 창의 유일한 `iOSContentGroup`만 읽는다. 이름이 중복되거나 content가 없으면 실패한다. Baepsae의 TabView 휴리스틱은 복사하지 않았다. 기존 호출자·설정·저장소는 제거하지 않는다. |

새 macOS·Simulator 기능은 MacPilot에서 관리한다. 기존 Baepsae 클라이언트의 API 호환성과 모든 Xcode 버전의 동작까지 보장하지 않는다. 현재 환경의 실제 기능별 검증과 미검증 범위는 배포 근거에 기록한다.

두 프로젝트 모두 현재 외부 AX 패키지를 사용하지 않는다. MacPilot의 `Package.swift`는 `dependencies: []`다. Baepsae의 `native/Package.swift`도 외부 패키지가 없으며 `UIElement`는 `AXUIElement`의 내부 typealias다. 이번 구현도 그 방향을 유지하고 typed·bounded 읽기를 MacPilot 코어 안에 추가했다.

소스:

- [Baepsae 공개 도구 목록](https://github.com/oozoofrog/mcp-baepsae/blob/4e36492380ca82ae2c3ea28f5475e0ac9050d193/src/tool-manifest.ts)
- [Baepsae Swift 패키지](https://github.com/oozoofrog/mcp-baepsae/blob/4e36492380ca82ae2c3ea28f5475e0ac9050d193/native/Package.swift)
- [Baepsae AX 분석·입력 구현](https://github.com/oozoofrog/mcp-baepsae/blob/4e36492380ca82ae2c3ea28f5475e0ac9050d193/native/Sources/Commands/UICommands.swift)
- [Baepsae AX 기본 함수](https://github.com/oozoofrog/mcp-baepsae/blob/4e36492380ca82ae2c3ea28f5475e0ac9050d193/native/Sources/Utils.swift)
- [Baepsae IndigoHID 로더](https://github.com/oozoofrog/mcp-baepsae/blob/4e36492380ca82ae2c3ea28f5475e0ac9050d193/native/Sources/IndigoHID/IndigoHIDLoader.swift)
