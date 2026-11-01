# 전달 결과와 재시도

MacPilot 3.6은 CLI와 MCP의 도구 성공·오류 응답에 `disposition`을 추가한다. 기존 `status`와 `outcome`은 유지한다. `outcome.disposition`에도 같은 계약을 제공한다. 전송 계층에서 동작 근거를 얻지 못한 오류는 `unknown`이다.

| delivery | retry | 의미와 다음 행동 |
|---|---|---|
| `not_delivered` | `safe` | 대상 동작을 보내지 않았다. 오류 전제를 수정하고 필요한 경우 새 관찰을 얻는다. |
| `delivery_uncertain` | `unsafe` | 일부 전송 또는 전달 여부가 불확실하다. 대상 상태·브라우저 receipt를 먼저 조회한다. |
| `delivered_unverified` | `unsafe` | 동작 경로가 반환됐지만 기대한 효과는 확인하지 못했다. 새 관찰과 명시한 후조건을 확인한다. |
| `delivered_verified` | `unsafe` | 해당 동작의 후조건을 읽어 확인했다. 같은 동작을 다시 보내지 않는다. |
| `unknown` | `unknown` | 전달 근거가 없다. 자동 재시도하지 않고 현재 상태와 오류를 확인한다. |

`mac_browser receipt` 같은 읽기 호출의 최상위 `disposition`은 현재 조회 호출을 설명한다. 조회의 `safe`는 앞선 변경 동작을 재전송해도 된다는 뜻이 아니다. 원래 요청의 receipt와 현재 대상 상태를 함께 확인한다.

`safe`는 중복 전달 위험에 대한 분류다. 실행 권한, 같은 인수의 유효성, 작업 완료를 보장하지 않는다. `already_satisfied`에는 추가 입력이 필요 없다. 읽기와 제어기 상태 기록의 `not_delivered`는 대상 앱 입력이 없다는 뜻이다. `mac_task finish` 같은 상태 변경을 반복하라는 지시가 아니다.

`outcome.scope`는 검증 범위다. `selected_predicate`는 이번 읽기의 조건이며 이전 쓰기의 전달 증거가 아니다. `operation_postcondition`도 앱의 저장·네트워크 완료나 전체 업무 수락을 보장하지 않는다. 반환 상태를 알 수 없는 새로운 동작은 보수적으로 `unknown`을 사용한다. 기존 자동 재시도·입력 경로 전환은 추가하지 않는다.

AX 시간 초과는 대상이 이미 동작했을 수 있으므로 `delivery_uncertain`이다. 실행이 반환된 뒤 전경 검사에서 실패하면 원래 동작의 전달 결과를 오류에 보존한다. `details.afterAction`에는 완료된 동작의 결과와 receipt 식별자가 남는다. 이 내용은 자동 개선 요청에 복사하지 않는다. AX 값 쓰기는 실제 문자열 읽기가 있을 때만 일치를 확인한다. `postcondition.state`는 `verified`, `mismatch`, `unavailable`을 구분한다. 확인 실패나 상태 불일치는 미전달 증거가 아니다. 취소는 이미 보낸 입력을 되돌리지 않는다. MCP 취소는 응답을 생략할 수 있으므로 응답 부재 역시 미전달 증거가 아니다.

## 참고 구현

[Agent Desktop의 전달 계약](https://github.com/vercel-labs/agent-desktop/blob/5261b5287b5208e7c4bf3713df6f66faaaf2c4cc/docs/json-output.md)과 [DeliverySemantics](https://github.com/vercel-labs/agent-desktop/blob/5261b5287b5208e7c4bf3713df6f66faaaf2c4cc/crates/core/src/actions/delivery_semantics.rs)를 참고해 MacPilot의 기존 결과에 맞게 구현했다. Rust 실행 코어나 C ABI를 포함하지 않는다. 이 계약은 WindowServer 세션·권한·실제 입력 수신의 제약을 해결하지 않는다.
