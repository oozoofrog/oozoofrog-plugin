---
name: verify-work
description: Turn a repeated work failure into a small enforceable invariant, run the project-owned verification contract, and record evidence, unresolved judgment, and recovery. Use for adopting or rerunning an evidence workflow, not every small edit.
---

# Verify Work

먼저 목적을 자신의 말로 요약하고 접근 가능한 현재 대화·보고서·Git 근거에서 재현 가능한 오류 유형을 고른다. 세션 저장소·다른 프로젝트를 임의 탐색하지 않는다. 기존 도구를 먼저 재사용한다.

규모에 맞춰 **구조/타입/불변식 → 자동 검사 → 자동화할 수 없는 최소 기록 → 중요한 사람 판단** 순으로 예방한다. 작은 변경에 설계 경쟁·다중 모델 검토를 강제하지 않는다. 같은 가정의 수정이 반복 실패하면 그 가정을 먼저 시험한다.

프로젝트별 의미·임계값·변경 생성은 프로젝트 adapter가 소유한다. 이 스킬은 실행 상태와 검증 판정, 실제 시각 관찰과 사용자 수락을 분리하고, 입력 SHA·근거 파일·재실행·기록의 무결성을 다룬다. 숫자나 렌더 성공을 제품 완료로 바꾸지 않는다.

아래 `/absolute/loaded-skill-root`는 실제로 로드한 이 스킬의 패키지 경로로 바꾼다. Plugin·standalone 설치 위치나 기본 `CODEX_HOME`을 가정하지 않는다. 사용자 프로젝트의 현재 작업 디렉터리는 유지하고 스크립트는 확인된 절대 경로로 실행한다.

```sh
python3 /absolute/loaded-skill-root/scripts/workcheck.py run --contract /absolute/project/contract.json --case CASE --run-id UNIQUE-ID --note
```

`--note`는 contract에 명시된 기존 노트에 짧은 실행 근거를 추가한다. 먼저 노트를 읽고 기록 범위가 승인됐는지 확인한다. 노트 경로가 바뀌면 실제 파일을 찾아 contract만 수정한다. 역사적 영수증의 당시 경로는 보존한다. 출력/노트/계약이 충돌하면 덮어쓰거나 우회하지 말고 그 상태를 보고한다. 새 실행에는 새 ID를 쓰며, 같은 ID 재호출은 입력·코드·근거가 같은 저장 결과만 재사용한다.

adapter의 작업 자체에 기존 권한을 적용한다. 이 스킬·contract는 외부 메시지·티켓·push·merge·배포·삭제·설치·새 보안권한을 부여하지 않는다. 실행은 순차이며 기존 앱·서버를 중단하지 않는다. 독립 검토는 요청되거나 위험에 비례해 필요할 때 수행한다. 현재 요청에서 요구한 검토는 생략하지 않는다.

새 adapter는 정상/의도적 결함/경계/재실행을 격리 fixture에서 검증한다. 형식 검사와 실제 운영 검증을 구분한다. 결과에는 근거·판정 범위·미검증·다음 행동·복구를 남긴다. 계약 형식과 경계는 [계약 안내](references/contracts.md)를 읽는다.
