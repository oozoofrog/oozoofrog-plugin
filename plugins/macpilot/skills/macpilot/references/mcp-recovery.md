# MCP 연결 진단과 작업을 유지하는 복구

`mac_connection`은 현재 서버의 실행 경로와 프로세스 신원을 조회하거나 격리된 새 MCP 연결을 검사한다. 기존 서버·Codex 앱·app-server를 종료하지 않는다. 끊긴 호스트의 stdio 연결을 외부 CLI가 교체할 수 있다고 가정하지 않는다.

## 현재 연결 조회

현재 대화에 `mac_connection`이 있으면 먼저 호출한다.

```json
{"operation":"status"}
```

- `server`: PID, `processStartID`, 프로세스 수명 동안 유지하는 `instanceID`, 실행 파일 경로.
- `parent`: 부모 PID와 시작 ID. 부모가 Codex인지 또는 다른 대화가 진행 중인지는 이 값만으로 판정하지 않는다.
- `transport`: `mcp_stdio` 또는 `cli`. `hostConnectionVerified=true`는 이 MCP 호출이 반환했다는 뜻이다. GUI 동작·업무 완료까지 검증하지 않는다.
- `permissions`: 현재 프로세스의 Accessibility·화면 캡처·이벤트 입력·Input Monitoring 상태. 다른 프로세스나 실행 파일의 권한과 같다고 가정하지 않는다.

이전 결과가 있으면 PID와 시작 ID를 **같이** 전달한다. `previousServerPID`·`previousServerStartID`, `previousParentPID`·`previousParentStartID`를 지원한다. `comparison.relation`은 `same_instance`, `different_instance`, `current_identity_unavailable` 중 하나다. `previousIdentityAvailable=false`이면 이전 프로세스의 종료 여부를 단정하지 않는다. `previousPIDReused=true`이면 같은 PID가 다른 프로세스에 할당되었다.

진단은 작업·입력 잠금을 얻지 않으므로 다른 호출이 실행 중이어도 조회할 수 있다. `taskID`를 받지 않는다. 프로세스 신원 비교는 종료 권한을 부여하지 않는다.

## 연결이 끊겼거나 구버전 도구만 있을 때

1. 현재 MCP에서 `status` 또는 구버전의 `mac_doctor`를 한 번 호출한다. `Transport closed` 뒤 다음 사용자 요청에서 복구된 사례가 있지만, 새 요청이 항상 재연결을 보장하지는 않는다. 진단만을 위해 다른 대화에 메시지를 보내거나 새 대화를 만들지 않는다.
2. MCP 호출이 실패하면 이 스킬 디렉터리의 CLI로 검사한다.

```sh
./scripts/macpilot connection-check
```

`connection-check`는 현재 실행 파일의 새 `mcp` 자식을 만든다. 별도의 0700 임시 상태에서 `initialize` → `notifications/initialized` → `tools/list` → `mac_connection status` → `mac_doctor`를 검사한다. 자식의 PID·시작 ID를 응답과 비교하고, 자식 종료와 임시 상태 제거도 확인한다. 기존 상태 경로가 잠겼거나 잘못되어도 이 검사를 실행할 수 있다. 성공 시 종료 코드는 0, 검사·정리 실패 시 2다.

MCP에서도 `{"operation":"probe","timeoutMs":10000}`으로 같은 검사를 할 수 있다. `timeoutMs`는 500–30000이며, 자식 정리에 최대 약 750ms가 추가된다. 호출 취소 시에도 생성한 자식을 정리한다. 오류가 나면 단계와 오류 코드가 반환된다. 권한 값이 false여도 MCP 통신 검사는 통과할 수 있으므로 `permissions`를 별도로 확인한다.

3. `probe_passed`는 **별도 연결의 성공**이다. 최상위 `scope=isolated_probe`, `hostConnectionVerified=false`를 유지한다. `probeConnection`은 검사 자식의 결과이며 `caller`는 검사를 시작한 프로세스의 결과다. 이 값을 현재 대화의 재연결 성공으로 보고하지 않는다. 필요한 작업은 검증된 CLI 경로로 계속할 수 있다.
4. 현재 MCP를 다시 사용할 수 있으면 `status`로 그 연결을 확인한다. 필요한 경우 사용자가 요청한 대상에서 AX 재조회·캡처·작업 후조건을 검사한다. 진단 때문에 사용자 문서·앱 값을 변경하지 않는다. 이전 입력·전송·파일 쓰기의 결과가 불확실하면 먼저 실제 상태를 확인하고, 변경 명령을 재전송하지 않는다.

## 자동 실행하지 않는 동작

현재 확인한 Codex app-server의 `config/mcpServer/reload`는 서버·대화 선택 인수 없이 로드된 대화들에 갱신을 예약한다. `mcpServerStatus/list`의 `serverName`은 조회 필터이며, `threadId`는 기존 연결을 재사용한다. 설치된 앱의 MCP 설정 화면에서 Restart는 `codex-app-server-restart`를 실행한다. 이 동작들은 MacPilot 하나만의 강제 재연결로 취급하지 않는다. [공식 app-server API](https://learn.chatgpt.com/docs/app-server#api-overview).

MacPilot은 이 기능으로 전체 MCP 갱신·app-server 재시작·기존 서버 종료·설정 파일 변경을 실행하지 않는다. `recovery.scopedHostReconnectAvailable=false`는 현재 도구에 그 기능이 없다는 뜻이며, 향후 모든 호스트가 지원하지 않는다는 주장이 아니다. `hostRestartRequired=not_established`이므로 단일 실패만으로 앱 재시작이 필수라고 결론 내리지 않는다.

## 검증 범위

2026-10-17 실제 대화에서 이전 실패 연결과 다른 MacPilot PID로 호출이 성공했다. Codex 앱·app-server의 PID·시작 시각은 유지되었다. 현재 MCP의 권한 조회·전용 창의 백그라운드 텍스트 변경·AX 재조회·PNG 캡처를 확인했다. 정확한 호스트 복구 트리거는 확인하지 못했다. 이 관찰을 자동 재연결 알고리즘으로 일반화하지 않는다.

`verify_connection.py`는 소유한 MCP 두 개 사이에서 신원 유지, 검사 자식 분리·정리, CLI fallback을 확인한다. 이 검증은 실행 중인 다른 Codex 대화의 진행이나 배포된 Plugin의 새 세션 노출을 증명하지 않는다.

## 설치본 갱신

Plugin 갱신은 실행 중인 MCP의 메모리 이미지를 교체하지 않는다. 설치된 버전·새 프로세스의 버전·기존 연결의 버전을 각각 확인한다. 2026-10-17 공식 CLI의 로컬 3.1.0 설치에서는 이전 3.0.0 캐시 경로가 제거되었다. 실행 중인 서버가 그 경로에서 보조 프로세스나 참조 문서를 다시 열 수 있으므로 경로 보존도 확인한다. 이번 갱신에서는 보조 프로세스 인터페이스가 유지되어 기존 경로를 새 설치본으로 연결했다. 향후 버전에서도 같은 호환성을 가정하지 않는다.

MCP 설정에는 `~/.local/bin/macpilot`처럼 갱신 시 대상을 원자적으로 바꿀 수 있는 사용자의 안정된 절대 경로를 사용할 수 있다. 이 경로가 실제 새 설치본을 가리키는지 확인한다. 다른 작업이 실행 중이면 전체 MCP reload나 app-server 재시작 없이 새 CLI·MCP 연결에서 먼저 검사한다. 기존 연결과 이전 경로의 호환 링크는 해당 참조가 끝나기 전에 임의로 제거하지 않는다.
