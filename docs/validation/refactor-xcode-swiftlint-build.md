# Xcode Run Script 실제 빌드 통합 검증

2026-10-29에 [독립 Xcode 예제](../../examples/xcode-swiftlint-build/HelloLintXcode.xcodeproj/project.pbxproj)를 만들고 Run Script에서 실제 SwiftLint 0.65.1을 실행했다. 13개 명령 단계와 두 가지 컴파일 산출물 재사용 검사가 모두 통과했다.

환경은 macOS 27.0.1 arm64, Xcode 27.2(27B48), Swift 6.4.2, XcodeGen 2.46.0이다. `HelloLintXcode`는 macOS 명령행 target이며 Debug arm64로 빌드했다. 같은 DerivedData를 유지했고 clean은 실행하지 않았다. 실제 바이너리는 앞서 공식 SwiftPM artifact로 검증한 SwiftLint를 예제 전용 `.tools`에 복사해 사용했다. 모의 실행 파일을 사용하지 않았다.

| 시험 | 실제 결과 |
|---|---|
| 최초 정상 빌드 | Run Script 1회, 빌드 종료 0 |
| 변경 없는 증분 빌드 | `main.o` hash·mtime 동일, Run Script 1회, 종료 0 |
| 소스에 `greeting!` 추가 | `force_unwrapping` error, 빌드 종료 65 |
| 같은 소스에서 설정만 warning으로 변경 | Xcode 빌드 로그에 같은 규칙의 warning 표시, 종료 0 |
| 설정만 error로 복구 | 같은 규칙의 error, 종료 65 |
| 설정만 바꾼 두 빌드 | `main.o` hash·mtime 동일, 각각 Run Script 1회 |
| 소스 복구 | 종료 0 |
| 도구 실행 권한 제거 | Run Script의 not executable error, 빌드 종료 65 |
| 실행 권한 복구 | 종료 0 |
| 도구 파일을 임시 이동 | Run Script의 missing error, 빌드 종료 65 |
| 도구 복구·최종 빌드 | 종료 0 |
| 프로그램 실행 | 종료 0, `Hello, SwiftLint` 출력 |

Run Script는 Compile Sources 뒤에 있고 `ENABLE_USER_SCRIPT_SANDBOXING=YES` 상태로 통과했다. 소스·설정·스크립트·도구 디렉터리를 입력으로 선언하고 SwiftLint에는 `--no-cache`를 사용했다. 검사 정책은 `basedOnDependencyAnalysis: false`이며 증분 컴파일의 재사용 여부와 무관하게 매 빌드 한 번 검사한다. 전역 Xcode 설정·신뢰 검사는 변경하지 않았다.

실행 명령은 [예제 안내](../../examples/xcode-swiftlint-build/README.md)에 있다. 재현 실행기는 새 복사본에서만 source/config/tool을 바꾸고 finally에서 복구한다. 모든 빌드 종료 코드, 소스·설정 hash, 산출물 hash·mtime은 `results.json`, 증분 재사용 단언은 `incremental-proof.json`, 전체 출력은 단계별 `.log`에 저장한다. 프로젝트 생성 원본으로 다시 생성한 파일들도 체크인할 `.xcodeproj`와 바이트가 일치했다.

이 결과는 독립 `.xcodeproj`의 실제 `xcodebuild` Run Script 경로를 검증했다. Xcode GUI 조작, Release/archive, 앱 서명, iOS·실제 기기·CI와 다른 도구 체인은 검증하지 않았다. 기존 SwiftPM 플러그인 검증과 별도 근거이며 Plugin payload 변경은 없다.
