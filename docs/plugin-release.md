# Plugin 배포

이 저장소의 카탈로그와 `plugins/` 디렉터리를 기준으로 배포합니다. Mac 자동화 패키지의 개발·릴리스는 별도 [Mac Pilot](https://github.com/oozoofrog/mac-pilot) 저장소에서 수행합니다.

```sh
python3 -m unittest discover -s scripts/tests -v
git diff --check
```

스킬 원본은 `plugins/<plugin>/skills/<skill>/` 하나뿐입니다. 변경한 Plugin의 스킬·manifest·UI metadata·README·CHANGELOG를 맞추고 해당 패키지의 검사를 실행합니다. 게시 시 main의 검증한 커밋과 원격 카탈로그를 확인합니다. 설치·활성화·새 세션 노출과 실제 앱 동작은 배포 검사와 구분합니다.

- WinPilot은 [Windows 개발·배포 절차](../plugins/winpilot/skills/winpilot/references/development.md)를 따릅니다.
- 사용자 프로필·기존 설치본·실행 자료를 배포 변경 때문에 삭제하거나 초기화하지 않습니다.
