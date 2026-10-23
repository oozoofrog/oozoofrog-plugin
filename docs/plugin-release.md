# Plugin 배포

`python3 scripts/release_plugin.py`는 버전 변경, 검증, 커밋, 패키징, GitHub 게시, Codex 설치를 각각 실행한다. 현재 버전 어댑터와 배포 프로필은 MacPilot을 지원한다. 프로필은 `scripts/releases/macpilot.json`이다. 다른 Plugin을 지원하려면 해당 버전 어댑터와 검증 계약을 추가한다.

각 단계는 명시적으로 실행한다. `prepare` 외에는 버전을 자동 증가시키지 않는다. 같은 버전으로 `prepare`를 다시 실행해도 앱 build 번호는 증가하지 않는다. 이전 버전으로 내리는 요청과 버전 항목의 누락·중복은 쓰기 전에 거부한다. 변경 설명과 CHANGELOG는 작성자가 갱신한다.

## 준비와 검증

아래 예시는 3.5.0 배포다. `--evidence`는 이 배포에만 사용하는 디렉터리다. `receipt.json`과 `command-*.log`를 보존한다. CLI는 Git·Python 3·`gh`·Codex Plugin 명령과 macOS의 `ditto`·`codesign`을 사용한다. 원격 push·GitHub release·설치를 실행할 권한은 요청한 작업 범위에서 별도로 판단한다.

```sh
python3 scripts/release_plugin.py prepare --plugin macpilot --version 3.5.0 --evidence macpilot/evidence/release-3.5.0
```

MacPilot 원본의 Plugin manifest·Chromium manifest·Swift runtime version·앱 버전과 build 번호·README의 MacPilot 절·설치 문서·배포 검사의 버전을 맞추고 미러를 동기화한다. 실제 기능 변경과 필요한 검사도 완료한다. `MACPILOT_UNIVERSAL=1 macpilot/scripts/build.sh`로 arm64·x86_64 앱과 격리 드라이버를 빌드·서명한다. 이어 `python3 scripts/release_plugin.py pin-runtime --plugin macpilot --version 3.5.0 --evidence macpilot/evidence/release-3.5.0`으로 최종 두 실행 파일의 SHA-256을 `runtime/distribution.json`에 고정하고 미러를 갱신한다. 고정 manifest는 앱 내부에 넣지 않는다. 동일 최종 바이너리로 실제 검증한 뒤 스테이지한다. **해당 배포의 파일과 공용 파일의 해당 hunk만 스테이지한다.** 스크립트는 전체 변경을 자동 스테이지하지 않는다. `commit_paths`는 경로 허용 목록이며, 공용 파일 내부의 변경 권한까지 판별하지 않는다. `git diff --cached`로 공용 파일의 내용을 확인한다.

```sh
python3 scripts/release_plugin.py verify --plugin macpilot --version 3.5.0 --evidence macpilot/evidence/release-3.5.0 --runtime-evidence macpilot/evidence/capabilities-implementation-20261018 --feature-report final-10/result.json --runtime-report runtime-final-02/report.json
python3 scripts/release_plugin.py commit --plugin macpilot --version 3.5.0 --evidence macpilot/evidence/release-3.5.0
```

`verify`는 인덱스의 정확한 Git tree를 임시 디렉터리에 펼쳐 배포·미러·릴리스 스크립트 검사를 실행한다. 작업 트리의 다른 변경은 커밋하지 않는다. 실제 실행 검사는 `source-manifest.json`의 선택 패키지 해시가 작업 트리와 인덱스에 모두 일치할 때 재사용한다. 기능 보고서의 모든 `checks[].status`는 `PASS`여야 한다. 런타임 보고서는 `status=passed`, 모든 `checks[].passed=true`여야 한다. 두 보고서의 실행 파일 SHA-256도 실제 패키징할 앱과 같아야 한다. 소스가 달라졌으면 실제 실행 검사를 다시 수행하고 새 보고서를 사용한다. 이 검사는 물리 기기나 임의 앱의 성공을 추가로 증명하지 않는다.

검증 후 인덱스가 바뀌면 `commit`은 중단한다. 검증 실패 후에는 이전 검증 결과로 커밋할 수 없다. `commit`은 로컬 커밋만 만든다. 커밋과 원격 게시를 분리한다. 공개 전 수정으로 다시 검증했다면 `commit --amend`로 같은 receipt의 미게시 HEAD만 갱신할 수 있다.

## 패키징과 게시

```sh
python3 scripts/release_plugin.py package --plugin macpilot --version 3.5.0 --evidence macpilot/evidence/release-3.5.0
python3 scripts/release_plugin.py publish --plugin macpilot --version 3.5.0 --evidence macpilot/evidence/release-3.5.0 --notes /absolute/release-notes.md
```

패키징은 검증한 커밋에서 Plugin 소스 tar.gz를 만든다. 실제 검사한 ad-hoc 서명 앱을 ZIP으로 묶고 `SHA256SUMS.txt`를 만든다. ZIP은 `ditto --norsrc`로 생성하여 AppleDouble sidecar를 포함하지 않습니다. 깨끗한 임시 경로에서 `ditto`와 `unzip`으로 각각 추출한 뒤 앱 서명과 실행 파일 해시를 확인합니다. 앱은 notarization을 받지 않았다. Plugin은 스킬·소스·고정 runtime manifest를 포함한다. 첫 실행에서 Universal 배포 앱의 두 실행 파일 해시·버전·서명을 검사해 설치한다. Swift·Xcode가 없는 사용자도 일반 macOS 기능을 실행한다. 다운로드 실패 시 컴파일하지 않는다. 소스 빌드는 명시적 선택이다. 이 절차의 설치 단계도 같은 릴리스 앱을 배치한다. Simulator 기능만 선택한 Xcode·런타임을 요구한다.

게시는 검증한 `main` HEAD만 허용한다. 원격 주소와 fast-forward 조건을 검사하고 push 후 원격 commit을 재확인한다. `<plugin>-v<version>` annotated tag가 다른 커밋을 가리키면 중단한다. GitHub draft release에 파일을 올리고 실제로 다시 내려받은 바이트를 비교한 뒤 공개한다. 이미 공개된 release는 같은 파일인지 확인하며 덮어쓰지 않는다. 네트워크 실패 후에는 같은 근거 디렉터리와 단계를 다시 사용한다. 소스·커밋·파일이 달라졌으면 기록을 검토한 뒤 새 배포를 준비한다.

## 설치와 확인

```sh
python3 scripts/release_plugin.py install --plugin macpilot --version 3.5.0 --evidence macpilot/evidence/release-3.5.0 --launcher "$HOME/.local/bin/macpilot"
```

기존에 등록한 Git marketplace의 주소를 확인하고 그 snapshot만 갱신한다. 선택한 Plugin만 설치한다. 설치된 모든 배포 파일의 Git blob과 실행 모드를 검사한다. 공개 release의 앱을 다시 내려받아 ZIP·실행 파일 해시와 앱 서명을 확인한다. 다른 실행 파일이 이미 설치되어 있으면 덮어쓰지 않고 중단한다. CLI 설치가 이전 cache를 제거하면 이전 버전 경로에 새 버전으로 연결하는 호환 symlink를 만든다. 이전 cache가 남아 있으면 보존한다. 별도 백업은 만들지 않는다.

`--launcher`는 기존 symlink만 원자적으로 교체한다. 일반 파일을 덮어쓰지 않는다. 인수를 생략하면 런처를 바꾸지 않는다. 새 앱의 격리된 MCP handshake·catalog·읽기 검사와 CLI runtime version을 확인한다. 설치 전후 다른 Plugin의 버전·활성화 상태도 비교한다. 기존 MCP와 Codex를 재시작하지 않는다. 현재 대화의 MCP 버전과 새 세션의 Skill 노출은 별도로 확인한다.

같은 저장소의 배포 단계는 `.git/plugin-release.lock`으로 중복 실행을 막는다. 프로세스 비정상 종료로 lock이 남았으면 해당 배포 프로세스와 receipt·원격 상태를 먼저 확인한다. 스크립트는 임의의 lock을 자동 제거하지 않는다. 실패 로그는 `command-*.log`, 마지막 성공 단계와 실패 원인은 `receipt.json`에 남는다. push·공개·설치는 자동 롤백하지 않는다.
