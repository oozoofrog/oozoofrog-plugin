# CONTEXT.md

## Scope
- `scripts/`는 저장소 자체를 동기화하거나 자동화하는 운영 스크립트를 둔다.
- 상위 규칙은 [../AGENTS.md](../AGENTS.md)를 따른다.

## Key Files
- [sync_repo.sh](./sync_repo.sh): fetch/rebase/add/commit/push 흐름을 묶는 핵심 동기화 스크립트
- [sync_skill_mirrors.py](./sync_skill_mirrors.py): standalone Skill 및 Plugin-shaped 원본 패키지와 배포 사본의 내용·모드 일치 검사 및 원자 동기화
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

- `mac-computer-use`와 `simulator-pilot`은 제공된 Plugin 루트 구조를 유지하고 전체 패키지를 미러링한다. manifest 상대 경로가 필요한 setup을 낱개 스킬 복사로 깨지 않게 하며, 생성 바이너리·개인 상태·개발 증거는 미러에서 제외하고 원본에 보존한다.
