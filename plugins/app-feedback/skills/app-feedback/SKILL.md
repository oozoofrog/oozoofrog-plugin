---
name: app-feedback
description: iOS 앱에 개발자에게 피드백 보내기 기능을 추가하고 설정·검증한다. 앱에 피드백 보내기 기능 추가, 피드백 메일, Debug 진단 기록 첨부, Mac에서 피드백 복호화 요청에 사용한다. Swift 패키지와 공개키 암호화를 제공하며 서버 전송이나 분석 SDK는 다루지 않는다.
---

# 앱 피드백

## 대상과 설정 확인

- 대상 저장소 규칙을 읽고 iOS 최소 버전, Swift 버전, SwiftUI/UIKit, 설정 화면의 수명과 기존 메일 기능을 확인한다. 패키지는 Swift 6, iOS 17+ SwiftUI UI를 제공한다. UIKit 앱에는 안정적인 `UIHostingController`로 설정 화면을 연결한다. 배포 타깃을 임의로 올리지 않는다.
- macOS 14+에서는 모델·암호화 테스트와 복호화 도구만 제공한다. Mac 메일 UI, Catalyst, watchOS, tvOS, visionOS는 지원을 검증하지 않았다. 다른 플랫폼 요청이면 지원 범위를 먼저 정한다.
- **수신 주소는 사용자에게 받는다.** 이미 명시된 주소는 재사용한다. 앱 이름·버전·빌드 표시, 제목·본문과 번역, 진단에 넣을 항목, 선택 체크리스트를 확인한다. `feedback@example.com`을 실제 배포 설정으로 남기지 않는다.

## 라이브러리 추가와 갱신

이 문서의 폴더를 `SKILL_DIR`, 대상 앱 저장소를 `APP_ROOT`의 절대 경로로 정한다. 설치 캐시를 앱 의존성 경로로 직접 연결하지 않는다.

```sh
mkdir -p "$APP_ROOT/Vendor"
cp -R "$SKILL_DIR/assets/AppFeedback" "$APP_ROOT/Vendor/AppFeedback"
```

기존 폴더는 덮어쓰지 않는다. Xcode의 Add Package Dependencies → Add Local에서 `Vendor/AppFeedback`을 선택하고 **AppFeedback 라이브러리 제품만** 앱 타깃에 연결한다. XcodeGen이면 `packages.AppFeedback.path: Vendor/AppFeedback`과 앱 타깃 `dependencies: [{package: AppFeedback}]`로 연결한다. SwiftPM 앱은 `.package(path: "Vendor/AppFeedback")`와 제품 의존성을 추가한다. 마켓플레이스 URL을 원격 Swift 패키지로 추가하지 않는다.

버전 `0.1.0`, 플러그인 커밋, 복사 경로를 앱의 의존성 기록에 남긴다. 앱별 설정·provider는 Vendor 밖에 둔다. 갱신할 때 새 패키지를 별도 폴더에 복사해 diff를 검토하고, 기존 Vendor 변경을 보존·해소한 뒤 패키지 전체를 교체한다. Debug/Release 빌드와 아래 검증을 다시 실행한다.

## 키와 진단 제공자

메일만 필요하면 이 단계를 건너뛴다. 진단이 필요하면 Mac에서 앱별 service와 키 버전 account를 정해 실행한다. `BUILD_ROOT`는 프로젝트 규칙에 맞는 저장소 밖 빌드 폴더다. 이 환경에서는 `/Volumes/eyedisk/build` 아래를 사용한다.

```sh
mkdir -p "$BUILD_ROOT/module-cache"
xcrun swift -module-cache-path "$BUILD_ROOT/module-cache" \
  "$SKILL_DIR/scripts/feedback_diagnostics.swift" generate-key \
  --service 'ExampleApp feedback diagnostics' --account 'v1'
xcrun swift -module-cache-path "$BUILD_ROOT/module-cache" \
  "$SKILL_DIR/scripts/feedback_diagnostics.swift" public-key \
  --service 'ExampleApp feedback diagnostics' --account 'v1'
```

출력 JSON의 `publicKeyBase64`만 앱의 `#if DEBUG` 설정에 넣는다. 개인키는 Mac 키체인에만 저장되며 같은 service/account의 생성은 거부한다. 기존 키는 삭제·덮어쓰기하지 않는다. 교체 시 새 account를 쓰고 이전 첨부용 키를 유지한다. 키체인을 잃으면 해당 첨부는 열 수 없으므로 개발자의 키체인 백업 정책을 확인한다. 개인키를 저장소·앱·문서·채팅에 복사하지 않는다.

[통합 예제](references/integration.md)를 읽고 진단 provider를 앱의 실제 기록에 연결한다. provider는 `@MainActor () async throws -> Data`로 **JSON 객체**를 반환한다. 패키지는 최대 2MB JSON을 암호화하며 자체 기록 저장소나 기기 간 전송은 만들지 않는다. 수집 코드·호출부·설정도 `#if DEBUG`로 감싼다. 기존 로그에서 필요한 동작 사건만 골라 개수·기간을 제한한다. 계정·토큰·건강·위치·사용자 콘텐츠·오류 원문은 넣지 않는다. 암호화가 불필요한 수집을 허용하지는 않는다. 다른 기기의 기록을 못 받으면 이유를 남기고 정상 값으로 채우지 않는다.

`disclosure`에는 실제 포함 항목을 사용자 언어로 적는다. 선택 체크리스트는 `FeedbackCheck` 배열에 앱별 ID·제목을 넣는다. 초기 답은 `unchecked`; 결과·메모는 암호화 첨부에만 들어가며 상태는 메모리에만 유지한다.

## 화면 연결

[통합 예제](references/integration.md)의 `FeedbackSession`을 설정 루트 `@StateObject`로 소유한다. 설정 **Form 전체를 `FeedbackHost(session:)`로 감싸고**, Form 안에 `FeedbackSection(session:)`을 넣는다. Host를 Section, List 행, 조건에 따라 교체되는 자식 안에 넣지 않는다. 수집 중 행이 바뀌어도 메일 시트 호스트가 유지되어야 한다. 지연 시간으로 표시를 맞추지 않는다.

앱 정보와 제목·본문은 `FeedbackAppInfo`와 `content` 클로저로, 사용자 문구는 `FeedbackLabels`로 주입한다. native composer가 없으면 mailto·주소 복사와 암호화 파일 ShareLink를 제공한다. mailto는 파일을 붙이지 못한다. 설정을 실제로 떠나고 공유 시트가 닫힌 뒤 `clearTemporaryFile()`로 해당 세션의 암호화 임시 파일을 지운다. 시트를 여는 중 실행될 수 있는 `.onDisappear`에 정리를 연결하지 않는다.

## 검증

- 패키지 Debug·Release 테스트와 앱의 두 구성 빌드를 실행한다. Release에 `DEBUG`를 정의하지 않는다. Release에는 진단 provider·체크리스트·암호화·첨부 UI가 컴파일되지 않아야 한다. 앱 자체 수집 코드도 별도로 확인한다.
- 제목·본문·수신 주소, 첨부 해제, 수집 실패 후 메일 계속 작성, 메일 계정 없는 환경의 복사·파일 공유, 취소·임시 저장·메일 앱 넘김을 확인한다. 메일 앱 넘김은 도착 증거가 아니다.
- Mac에서 `python3 "$SKILL_DIR/scripts/verify.py" --output "$BUILD_ROOT/verification"`로 라이브러리 테스트와 새 임시 키체인 항목의 라이브러리→도구 복호화 왕복·변조 거부를 실행한다. `eyebuild`가 있으면 사용한다. 임시 키는 finally에서 삭제한다. 중단됐다면 출력 폴더의 `cleanup-keychain.json`에 있는 정확한 삭제 명령을 확인한다.
- 독립 SwiftUI iOS 앱에 통합 예제만 따라 붙여 Simulator용으로 빌드한다. `python3 "$SKILL_DIR/scripts/smoke_ios.py" --output "$BUILD_ROOT/smoke"`는 설치된 XcodeGen으로 같은 예제 코드와 Vendor 복사를 사용한다. 없으면 기존 프로젝트 도구를 쓰고 의존성을 임의로 설치하지 않는다.
- UI 배치·모양을 자동 단언하지 않는다. 요청된 UI 검토에는 Simulator 스크린샷을 제시한다. 실제 Mail 계정이 있는 기기의 작성기 유지·첨부·메일 도착은 별도 검증이며 단위 테스트나 Simulator 빌드로 확인했다고 보고하지 않는다.

## 받은 첨부 복호화

`.afdiag`를 저장하고 해당 앱 service/account를 선택한다.

```sh
xcrun swift -module-cache-path "$BUILD_ROOT/module-cache" \
  "$SKILL_DIR/scripts/feedback_diagnostics.swift" decrypt /absolute/path/feedback.afdiag \
  --service 'ExampleApp feedback diagnostics' --account 'v1' \
  --out /absolute/path/new-report.json
```

파일 머리·키 ID·인증 태그 검증 후 사용자만 읽고 쓸 수 있는 새 파일을 만든다. 기존 출력은 덮어쓰지 않는다. 키 불일치·변조·알 수 없는 형식이면 중단한다. 결과는 필요한 범위에서만 읽고 개인정보를 이슈·공개 저장소에 붙이지 않는다.
