# 화면과 시스템 오디오 녹화

`mac_record`는 선택한 화면을 H.264/AAC MP4로 저장하고 파일을 다시 검사한다. 녹화에는 macOS 15 이상과 Screen & System Audio Recording 권한이 필요하다. 마이크는 사용하지 않는다. FFmpeg·브라우저 확장·외부 다운로드 도구는 실행 코어의 의존성이 아니다.

## 녹화 범위

| `source` | 필수 대상 | 화면 | `systemAudio=true`의 오디오 범위 |
| --- | --- | --- | --- |
| `window` | `pid`, `processStartID`, `windowID` | 다른 창에 가려져도 선택한 독립 창 | ScreenCaptureKit이 선택한 창의 앱에 귀속한 오디오. 전체 시스템 오디오가 아님 |
| `display` | `displayID` | 선택한 디스플레이의 실제 합성 화면 | 포함된 앱들의 시스템 오디오 |
| `display` + `region` | `displayID`, `{x,y,width,height}` | 선택한 디스플레이 안의 사각형 영역 | 화면을 잘라도 시스템 오디오 범위는 동일 |

Mac 전체 소리가 필요하면 `source=display`를 사용한다. 특정 앱 화면만 담으면서 시스템 소리를 기록하려면 `region`으로 영역을 제한한다. 좌표는 선택한 디스플레이의 왼쪽 위를 `(0,0)`으로 하는 논리 포인트다. 전체 영역이 해당 디스플레이 안에 들어가야 한다. `mac_windows`의 전역 창 좌표를 사용할 때는 `mac_doctor`의 해당 디스플레이 원점을 뺀다.

디스플레이·영역 모드에는 다른 창이 겹친 모습도 기록된다. 선택한 앱을 온전히 담아야 하면 먼저 정확한 창을 `mac_focus`로 올리고 가림 상태를 확인한다. 독립 창 모드로 실패했다고 화면·오디오 범위를 자동으로 넓히지 않는다.

이번 macOS 27 / Chrome 155 검증에서 별도 프로필로 실행한 두 번째 Chrome 프로세스의 독립 창 오디오는 무음으로 저장됐다. 같은 실제 YouTube 재생을 디스플레이·시스템 오디오 모드로 녹화하면 신호가 검출됐다. 이 차이의 내부 원인은 확정하지 않았다. 앱 귀속 오디오와 전체 시스템 오디오를 같은 범위로 해석하지 않는다.

## 호출과 저장

`operation=record`에 대상과 `durationSeconds=1..120`을 전달한다. 기본 녹화 시간은 10초다. `maxDimension=320..3840`의 기본값은 1920이며 H.264에 맞게 짝수 크기로 맞춘다. `fps=1..60`의 기본값은 30이다. 정지 화면·인코더 부하에 따라 실제 프레임 수는 낮아질 수 있다.

`systemAudio`의 기본값은 `true`다. `false`이면 영상만 기록한다. `showsCursor`의 기본값은 `false`이며 MacPilot의 가상 커서를 영상에 별도로 합성하지 않는다. 디스플레이 모드에서는 실제 합성 화면에 보이는 오버레이가 포함될 수 있다.

```sh
./scripts/macpilot call mac_record --json /absolute/path/record-request.json
```

`mac_apps`, `mac_windows`, `mac_doctor`의 현재 PID·시작 ID·창·디스플레이를 사용한다. 입력 초점이나 커서를 옮기지 않고 녹화한다. 앱·창에 결합된 작업을 전체 디스플레이 녹화로 확장하려면 새 작업을 사용한다. 작업 취소·마감 시 캡처를 중단하고 미완료 영수증을 남긴다. 호스트가 호출을 기다리는 시간은 녹화 시간과 시작·종료·검사 시간을 포함해야 한다.

결과의 `path`가 완성된 MP4다. 작업별 private 상태 디렉터리에 UUID 파일로 생성하므로 기존 파일을 덮어쓰지 않는다. 상태 디렉터리는 0700, 완성 파일과 추출 프레임은 0600이다. 외부 위치가 필요하면 `mac_files copy`로 명시한 새 경로에 복사한다. `recording-<UUID>.json`에 결과를 함께 저장한다. 기본 저장 위치는 `~/Library/Application Support/MacPilot`이며 작업을 지정하면 그 아래 작업 디렉터리를 사용한다.

## 결과를 판단하는 기준

- `recorded`: 네이티브 출력 완료 후 영상 트랙을 확인했다. 시스템 오디오를 요청했다면 오디오 트랙과 디코딩한 비무음 신호도 확인했다.
- `recorded_without_audio_signal`: 오디오 트랙은 있으나 검사한 PCM 샘플에서 신호를 검출하지 못했다. 소리까지 성공했다고 보고하지 않는다. 재생·음소거·캡처 범위를 확인한다.
- `sampledFramesDiffer=true`: 서로 다른 시점의 디코딩 프레임 해시가 다르다. 영상의 의미나 입 모양과 소리의 동기화를 보증하지 않는다. 정지 화면에서 `false`는 정상일 수 있다.
- `audioRMS`, `audioPeak`, `decodedAudioSamples`, `audioAnalysisComplete`: 첫 오디오 트랙의 PCM 검사 결과다. `audioAnalysisComplete=false`이면 시간·샘플 예산 내 일부만 분석했다.
- 실패·취소: 이미 생긴 파일과 `status=incomplete` 영수증을 보존한다. 완성 영상으로 보고하지 않는다. 취소는 이미 기록한 내용을 지우지 않는다.

`operation=inspect`는 `path`의 기존 로컬 파일을 검사한다. 최대 파일 크기는 1 GiB, 길이는 600초다. `frames=0..6`으로 추출 PNG 수를 정하며 기본값은 3이다. 트랙·코덱·길이·프레임 크기·오디오 신호와 시간별 PNG 경로를 반환한다. 오디오 디코딩은 20초 또는 33,554,432 샘플까지 분석한다. 녹화 중 파일 크기 예산은 1 GB다.

녹화 요청은 사용자가 지정한 범위에서만 수행한다. 재생 제한·보호 콘텐츠·권한 경계를 우회하지 않는다. 유료·보호 콘텐츠의 캡처 가능성을 보장하지 않는다. 파일 생성, 트랙 존재, 비무음 신호, 실제 내용과 재생 확인은 구분한다.

## 개발 검증

```sh
xcrun swift test --package-path macpilot/tool
node macpilot/scripts/verify_recording_chrome.mjs
MACPILOT_RECORDING_SCOPE=display node macpilot/scripts/verify_recording_chrome.mjs
MACPILOT_RECORDING_SCOPE=region node macpilot/scripts/verify_recording_chrome.mjs
python3 macpilot/scripts/verify_recording_lifecycle.py
```

Chrome 검증기는 새 전용 프로필의 실제 GUI Chrome을 실행한다. 상속된 debugging pipe는 테스트 재생·상태 조회에만 사용하며 녹화는 MacPilot으로 수행한다. 사용자 기본 프로필·remote-debugging port를 변경하지 않는다. 디스플레이·영역 검증은 해당 창을 전경으로 올린다. Node.js, Chrome과 독립 검사용 FFmpeg·ffprobe가 필요하다. 창·디스플레이·영역을 별도 결과로 남기며 지원하지 않는 경로의 실패도 보존한다.

생명주기 검증기는 별도 네이티브 fixture를 실행하고 영상만 녹화·저장 파일 검사·실제 MCP 취소·파일 쓰기 종료·다음 호출 수락을 확인한다. 개발 검증에만 Python을 사용한다. 각 실행의 결과와 파일은 `evidence/recording-*/`에 남기며 배포 미러·Git에는 포함하지 않는다.

## API 근거

- [Apple: SCRecordingOutput](https://developer.apple.com/documentation/screencapturekit/screcordingoutput)
- [Apple: addRecordingOutput](https://developer.apple.com/documentation/screencapturekit/scstream/addrecordingoutput(_:))
- [Apple: capturesAudio](https://developer.apple.com/documentation/screencapturekit/scstreamconfiguration/capturesaudio)
- [Apple: ScreenCaptureKit 캡처 예제](https://developer.apple.com/documentation/screencapturekit/capturing-screen-content-in-macos)
