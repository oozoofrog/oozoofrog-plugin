# CONTEXT.md

## Scope
- `scripts/`는 저장소 자체를 동기화하거나 자동화하는 운영 스크립트를 둔다.
- 상위 규칙은 [../AGENTS.md](../AGENTS.md)를 따른다.

## Key Files
- [sync_repo.sh](./sync_repo.sh): fetch/rebase/add/commit/push 흐름을 묶는 핵심 동기화 스크립트
- [auto_sync_daemon.py](./auto_sync_daemon.py): 변경 감시와 debounce 기반 자동 동기화 실행기
- [install_auto_sync_launchd.sh](./install_auto_sync_launchd.sh): launchd 설치 진입점
- [uninstall_auto_sync_launchd.sh](./uninstall_auto_sync_launchd.sh): launchd 제거 진입점

## Local Rules
- shell script는 `bash -n`, Python script는 `python3 -m py_compile`로 먼저 검증하기.
- 배포·동기화 변경은 `python3 -m unittest discover -s scripts/tests -v`로 검증하고 무관한 패키지 변경을 보존하기.
- 안전한 경우를 제외하면 실 repo 상태를 바꾸는 명령보다 dry-run 또는 임시 디렉토리 재현을 우선하기.
- launchd 래퍼는 `sync_repo.sh`와 `auto_sync_daemon.py`의 경로 계약을 깨지 않게 유지하기.

## Verification Notes
- `sync_repo.sh`를 수정하면 `--dry-run` 시나리오를 먼저 확인하기.
- daemon이나 launchd 스크립트를 수정하면 경로, 기본값, 로그 경로를 함께 점검하기.

- 외부 패키지를 들여올 때는 실행 경로뿐 아니라 endpoint·환경변수·설정 화면·네트워크 예외·문서·검사 fixture의 공개 사용 가능 여부를 먼저 확인한다. 배포 대상에 불필요한 비공개 서비스 설정을 복사하지 않는다. 민감 정보 제거가 요청되면 지운 식별자를 문서·테스트·커밋 메시지에 다시 적지 않는다.
- Mac 자동화 패키지는 별도 mac-pilot 저장소에서 개발·배포한다. 이 저장소에는 소스·미러·실행 자료를 다시 복사하지 않는다.
