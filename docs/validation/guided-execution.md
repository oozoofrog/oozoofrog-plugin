# Guided Execution 0.1.0 검증 범위

## 대상

- Standalone: [guided-execution](../../guided-execution/SKILL.md)
- Plugin: [guided-execution manifest](../../plugins/guided-execution/.codex-plugin/plugin.json)
- 실행 규칙: [project loop](../../guided-execution/references/execution.md)
- 기록 규약: [workspace contract](../../guided-execution/references/workspace.md)

스킬은 프로젝트 분석과 최소 질문을 거쳐 작업 환경을 만들고, 호스트 에이전트가 실제 작업·검증·피드백 반영을 수행하도록 안내합니다. 보조 도구는 작업을 실행하거나 권한을 부여하지 않습니다.

## 보조 도구 검사

저장소 루트에서 다음 명령으로 포함된 26개 검사를 실행합니다.

```sh
python3 -B -m unittest discover -s guided-execution/tests -v
```

Linux의 Python 3.12에서 통과했습니다. 실제 임시 디렉터리와 CLI 프로세스로 다음을 확인합니다.

- 환경 생성, 기존 진행 상태 보존, 프로젝트·작업 식별 확인.
- 잘못된 경로, 심볼릭 링크, 누락·순환 의존 관계 거부.
- 요청 전체 질문 예산과 작업 시도 횟수 확인.
- 거절·수정 요청이 검토 또는 실행 승인으로 처리되지 않음.
- 증거 파일의 존재·내용 해시·검증 버전과 현재 검사 결과의 일관성.
- 보류·소진·재검증 필요·취소 상태를 완료로 처리하지 않음.
- 상태 검사 명령의 읽기 전용 동작과 작업 파일 미실행.

## 행동 평가와 예제 실행

초기 질문, 재개, 실행 환경 실패, 질문 예산 소진, 승인 대기라는 다섯 상황을 별도 에이전트로 검토했습니다. 비교용 기본 응답도 여러 요구를 이미 만족했으므로 이 관찰을 정량적인 성능 향상으로 주장하지 않습니다.

별도의 작은 메모 프로젝트에서는 질문 없이 작업 환경 생성, JSON 내보내기 구현, 사용법 문서화와 완료 기록을 수행했습니다. 원본 보존·덮어쓰기 거부·CLI 동작 등 9개 기능 검사와 실제 사용 명령이 통과했습니다. 이 예제는 개발 중 수용 검증이며, 예제의 소스와 9개 검사는 이 Plugin에 포함되지 않습니다.

## 배포 검증

```sh
python3 -B -m unittest discover -s scripts/tests -v
python3 -B scripts/sync_skill_mirrors.py --package guided-execution
git diff --check
```

배포 검사는 marketplace, manifest, 원본과 미러, 메타데이터와 문서 경로를 확인합니다. GitHub 게시, 사용자 기기에 설치·활성화, 새 대화의 스킬 노출, 실제 프로젝트의 성공은 각각 별도로 확인해야 합니다.

## 한계

`record_integrity_only`는 실제 실행을 증명하는 보안 경계가 아닙니다. 호스트가 현재 파일의 식별값을 대조하고 적절한 검사를 실제로 실행해야 합니다. 한 조정자만 작업 상태를 수정하며, 별도의 상시 실행 서버·스케줄러는 제공하지 않습니다. 이번 검증은 macOS·Windows의 실제 실행이나 모든 프로젝트 유형에 대한 성공을 입증하지 않습니다.
