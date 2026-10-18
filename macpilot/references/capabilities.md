# 조건 대기, 추적과 재사용 작업

이 기능은 MacPilot 3.4의 CLI와 MCP에 같은 이름으로 노출된다. 설치된 MCP가 구버전이면 이 스킬의 `scripts/macpilot call TOOL --json -`를 사용한다. 정확한 인수는 `tools` 출력이 기준이다.

## 조건 대기와 결과

`mac_wait_for`는 `pid`, `processStartID`, `windowID`, `condition`을 받는다. 같은 프로세스 세대와 창을 매번 다시 수집한다. AX 알림을 우선 확인하고 알림이 없는 앱은 폴링한다. 창 이동이나 AppKit 메타데이터의 일시적 조회 실패는 같은 PID·창에서 제한 시간 안에 다시 읽는다. 프로세스 시작 ID·창 기하·AX 정체성 검사는 유지한다. 동작을 재전송하지 않는다.

```json
{"pid":12345,"processStartID":"1770000000.123456","windowID":67890,
 "condition":{"selector":{"identifier":"save-button","role":"AXButton"},"predicate":"enabled"},
 "timeoutMs":5000,"pollMs":100}
```

위 숫자는 형식 예시다. 실제 인벤토리 값을 사용한다. `selector`는 `identifier`·`role`·`title`의 정확한 교집합이다. 중복·부분 수집·잘린 식별자·보안 노드는 검증하지 않는다.

| predicate | 확인 범위 |
|---|---|
| `exists`, `absent` | 유일한 대상의 존재 또는 전체 수집한 창에서의 부재 |
| `enabled`, `disabled`, `focused` | 선택한 AX 노드의 해당 속성 |
| `equals`, `contains` | 선택한 노드의 `value`와 `text` 비교 |
| `stable` | `stableMs` 동안 노드 frame 또는 창 frame 유지 |

`stable`은 화면 픽셀·앱 업무·네트워크 완료를 뜻하지 않는다. 기본 200ms이며 100–2000ms로 설정한다. 대기는 50–30000ms다. `predicate_timeout`과 `matches=false`는 실패한 후조건이며 입력 재시도 지시가 아니다.

모든 도구의 응답에는 기존 상태와 함께 `outcome`이 추가된다.

- `dispatch`: 입력 전송·일부 전송·확인 불가·읽기 구분.
- `effect`: 요청 수락, 상태 기록, 읽기, 선택 후조건 확인 구분.
- `retry`: 재조회·전제 수정·이미 실행한 동작을 다시 보내기 전 관찰 필요 구분.
- `scope`: 선택한 후조건, 해당 동작 또는 선언된 workflow 후조건 범위.

AXPress, 이벤트 전송, 스크립트 종료는 업무 완료가 아니다. `mac_task finish`도 제어기 상태 기록이다. 기존 응답 상태는 계속 유지한다.

## 다른 입력 출처를 감지하면 중단

전역 키보드·마우스 입력에는 Input Monitoring 권한이 필요하다. listen-only event tap은 입력을 가로채거나 키 내용을 저장하지 않는다. MacPilot은 자체 이벤트를 표식과 PID로 식별한다. 다른 출처의 키·마우스·스크롤 이벤트 또는 모니터 중단을 감지하면 추가 입력을 중단하고 눌린 키를 해제한다.

`user_input_interrupted` 또는 `input_monitor_lost` 이후 해당 작업은 `interrupted`다. 사용자가 다시 실행하도록 요청한 범위에서 현재 상태를 확인하고 `mac_task operation=resume taskID=...`을 명시적으로 호출한다. 기한은 연장하지 않는다. 이전 관찰은 재사용하지 않는다. 프로세스 경로 입력은 이 전역 감지의 적용 범위가 아니다.

이 방식은 물리 입력과 다른 자동화 입력을 구분하지 않는다. 다른 입력이 도착하기 전에 이미 전송한 이벤트를 취소할 수 없다. 시스템 입력 격리가 필요하면 별도 세션이나 VM을 사용한다.

## 선택적 동작 추적

기본은 비활성이다. 작업별 상태에 설정하려면 다음 호출에 `taskID`를 함께 전달한다.

```json
{"operation":"configure","enabled":true,"captureText":false,"captureScreenshots":false,"maxEntries":50,"maxBytes":33554432}
```

`mac_trace`는 `status`, `list`, `read`, `export`, `clear`를 지원한다. `read`·`export`는 `traceID`를 받는다. 입력·검증 동작의 전후 AX 상태, 변경 노드, 결과 범위를 기록한다. 텍스트와 화면 저장은 각각 별도 선택이다. 보안 노드의 텍스트 값은 저장하지 않는다. **화면 저장을 켜면 선택 창의 민감한 시각 정보가 PNG에 포함될 수 있다.**

기본 최대 50건·32MiB이며 1–200건·1–64MiB로 설정한다. 오래된 기록·그 기록의 PNG·HTML만 제거한다. `export`는 로컬 HTML 경로를 반환하며 파일 첨부가 아니다. 추적 저장 오류는 원래 동작의 재시도를 허용하지 않는다. `trace.status=recording_failed|preparation_failed`와 원래 동작 결과를 분리해서 보고한다.

## 선택적 이미지 검색

`mac_image_search`는 기본 비활성이다. VisionKit `ImageAnalyzer`로 후보의 텍스트를 읽고 로컬 `google/embeddinggemma-2`로 이미지·텍스트 벡터를 계산한다. AX frame과 Apple Vision의 사각형 후보를 함께 수집한다. 명시적 이미지 픽셀 `regions`도 지원한다. VisionKit의 transcript 자체에는 후보 좌표가 없다.

기본 제어는 외부 SwiftPM 의존성이나 Python 런타임을 요구하지 않는다. 이 선택 기능만 로컬 Python worker와 고정 버전 패키지를 사용한다. 모델은 캐시 미스 때 로드하고 요청 후 프로세스를 종료한다. 네트워크 추론이나 자동 설치·다운로드는 없다.

사용자가 선택 기능 설치를 요청한 경우 별도 venv에 [고정 패키지](../runtime/requirements-image-search.txt)를 설치한다. 사용자가 접근·라이선스 조건을 충족한 로컬 모델의 revision은 `914f7f89142e33e77833254d9c9b90c3cef7303b`이어야 한다. 설정 시 [manifest](../runtime/embeddinggemma2-manifest.json)의 파일 크기와 SHA-256을 검사한다.

```sh
python3 -m venv /absolute/optional-venv
/absolute/optional-venv/bin/python -m pip install -r runtime/requirements-image-search.txt
```

```json
{"operation":"configure","enabled":true,"pythonPath":"/absolute/optional-venv/bin/python",
 "modelPath":"/absolute/pinned-model-snapshot","device":"mps"}
```

venv interpreter의 symlink를 해석한 원본 Python 경로로 바꾸지 않는다. `mps`가 기본이며 `cpu`도 명시적으로 선택할 수 있다. 설정한 모델 경로·모델 파일 메타데이터·worker가 바뀌면 재설정이 필요하다. 설정 시와 캐시 미스의 worker 실행 시 파일 SHA-256을 검사한다. 캐시만 사용하는 검색은 모델을 다시 로드하지 않는다.

스크린샷을 포함한 **새 관찰**을 얻은 뒤 다음처럼 검색한다.

```json
{"operation":"search","observation":"OBSERVATION_UUID","query":"play button",
 "minimumScore":0.65,"minimumMargin":0.05,"maxCandidates":24,"timeoutMs":25000}
```

`query` 대신 명시적 로컬 `templatePath`를 하나만 지정할 수 있다. 템플릿은 16MiB 이하·단일 프레임·최대 8192px/변·16777216px이다. `regions`가 있으면 이미지 픽셀의 `{x,y,width,height}` 배열을 사용한다.

후보 점수는 확률이 아니다. 기본 임계값과 1·2위 차이를 모두 충족해야 `accepted=true`다. 낮은 점수·중복 위치 후보는 `image_search_abstained`로 반환한다. 후보 제안 영역 밖의 부재를 보장하지 않는다. 검색 중 픽셀·창 정체성·기하가 바뀌면 결과를 거부한다. `regions`를 지정하면 픽셀 안정성 확인도 그 영역에 한정한다.

벡터는 모델·worker·이미지·문자열의 해시로 작업별 최대 256건 재사용한다. 캐시에는 원문·원본 이미지 대신 벡터를 저장한다. `operation=cache_clear`로 삭제한다. `status`와 `configure enabled=false`는 모델을 로드하지 않는다. **검색은 클릭하지 않는다.** 새 관찰과 의미·위치를 확인한 뒤 기존 입력 도구를 사용하고 실제 후조건을 확인한다.

## 명시적 재사용 작업

`mac_workflow`는 저장하거나 인라인으로 지정한 작업을 명시적으로 실행한다. 트리거·스케줄러·임의 스크립트는 없다. `validate`·`save`가 받는 `definition` 예시는 다음과 같다.

```json
{"name":"set_search","parameters":["query"],"steps":[
 {"action":"set_value","selector":{"identifier":"search-field"},"parameter":"query",
  "postcondition":{"selector":{"identifier":"search-field"},"predicate":"equals","textParameter":"query"}},
 {"action":"press","selector":{"identifier":"search-button"},
  "postcondition":{"selector":{"identifier":"results"},"predicate":"exists"},"timeoutMs":5000}
]}
```

최대 24단계다. `set_value`, `press`(AXPress), 물리 키 `key`, `wait`만 지원한다. 문자열과 매개변수는 리터럴이다. 모든 단계·매개변수 참조를 첫 입력 전에 검사한다. 저장된 정의를 덮어쓰려면 `overwrite=true`가 필요하다.

`operation=run`에 `name` 또는 `definition` 중 하나와 `parameters`, `pid`, `processStartID`, `windowID`, `runID`를 전달한다. `runID`는 호출자가 만든 UUID를 보존한다. 같은 ID·같은 인수는 기존 기록만 반환하며 재실행하지 않는다. 다른 인수는 거부한다. 새 UUID를 자동 생성해 불확실한 실행을 반복하지 않는다.

각 동작은 새 관찰로 유일한 대상을 확인하며, 선언한 후조건을 통과해야 다음 단계로 진행한다. 취소·실패는 이미 보낸 동작을 되돌리지 않는다. 전체 기한은 최대 60초, 단계 후조건은 최대 10초다. 전역 키 단계는 전경 허용 작업과 `allowGlobalInput=true`가 모두 필요하다.

`runs`·`run_status`는 중단·취소 뒤에도 읽을 수 있다. 단계별 `dispatching`·`dispatched`·`verified` 기록을 현재 앱 상태와 함께 조정한다. 프로세스가 비정상 종료되어 `running`이 남으면 부분 실행을 배제할 수 없다. 자동 재개하지 않는다. 저장 정의는 최대 100개, 실행 기록은 최대 256개다. 종료한 기록만 `remove_run`으로 명시적으로 제거한다.
