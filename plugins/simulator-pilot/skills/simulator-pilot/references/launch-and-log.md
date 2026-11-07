# 실행과 로그

`sim-pilot`으로 KakaoTalk 스킴을 실행하고 로그를 본다. 다른 앱은 `--scheme` 대신 `--bundle <번들 ID>`를 쓴다.

| 스킴 | 번들 ID |
|---|---|
| Inhouse(iTeam)-Debug | com.kakao.iPart.Talk |
| Sandbox(iTeam) | com.kakao.iPart.sandbox.Talk |
| Real | com.kakao.talk (실행·로그 전에 확인, `--allow-real`) |
| Alpha(iTeam) | com.kakao.iPart.alpha.Talk |
| Beta(CI) | com.kakao.iPart.beta.Talk |

스킴 이름에 괄호가 있으니 늘 큰따옴표로 감싼다.

## 1. 상태 보기

```sh
sim-pilot devices                      # 부팅된 기기 (JSON)
sim-pilot schemes --udid <UDID> [--project-root <레포>]   # installed / built(이 레포 사본의 빌드) / needs_build
```

스킴을 사용자가 정하지 않았으면 상태와 함께 보여 주고 묻는다.

## 2. 실행

```sh
sim-pilot launch --udid <UDID> --scheme "Sandbox(iTeam)" [--build | --reinstall] [--project-root <KakaoTalk 레포>]
```

- 설치돼 있으면 다시 실행만 한다. 설치돼 있지 않으면 DerivedData의 빌드를 설치하고, 빌드도 없으면 `./Scripts/build.sh <스킴>`으로 빌드한다(수 분).
- `--reinstall`: 빌드하지 않고 DerivedData의 최신 빌드를 다시 설치한다(방금 따로 빌드했을 때).
- `--build`: 새로 빌드해서 설치한다.
- 설치·빌드할 때는 `--project-root`(KakaoTalk 레포 루트, `Scripts/build.sh`가 있는 곳)가 필요하다. 현재 폴더가 레포 루트면 생략한다. DerivedData에서는 이 레포 사본(워크스페이스가 root 아래)에서 만든 빌드만 쓴다.
- 빌드 에러·워닝 처리는 프로젝트의 빌드 지침의 규칙을 따른다. 빌드를 오래 기다려야 하면 백그라운드로 실행한다(Claude Code: Bash `run_in_background`).

## 3. 로그

두 가지가 있다. 보통은 `logs`를 쓴다.

| 명령 | 보는 것 | 앱 |
|---|---|---|
| `sim-pilot logs --udid <UDID> --scheme "<스킴>" [--filter <단어>] [--seconds N] [--debug]` | os_log·NSLog (`log stream`) | 그대로 둔다. 조작하면서 볼 수 있다 |
| `sim-pilot console --udid <UDID> --scheme "<스킴>" [--filter <단어>] [--seconds N]` | `print`·stdout·stderr까지 (`launch --console-pty`) | 다시 실행하고, 끝나면 종료한다 |

- `--seconds` 기본은 30초다. `0`은 멈출 때까지인데, 에이전트에서는 쓰지 않는다.
- `--filter`는 대소문자를 가리지 않는 부분 일치다.
- 조작하면서 로그를 보려면 `logs`를 백그라운드로 돌리고(Claude Code `run_in_background`, Codex는 출력 파일로 리다이렉트), 화면 조작([drive.md](drive.md))을 한 뒤 출력을 읽는다.
- 로그를 보고할 때는 필요한 줄만 옮긴다. 토큰·전화번호·계정 정보가 보이면 가린다.
