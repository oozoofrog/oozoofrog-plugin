# SwiftLint 실제 빌드 통합 검증

2026-10-29에 [작은 SwiftPM 예제](../../examples/swiftlint-build/Package.swift)를 만들고 실제 공식 SwiftLint 바이너리로 검증했다. 모든 최종 검사가 기대 결과와 일치했다. 첫 빌드 이후 같은 프로젝트와 빌드 캐시를 유지했다.

환경은 macOS 27.0.1 arm64, Xcode 27.2(27B48), Swift 6.4.2, 기본 `swiftbuild` 엔진이다. SwiftLintPlugins/SwiftLint는 0.65.1이며 잠금 커밋은 `ef7d692fc6706e8f5628e26bcafaefa445c58a97`이다. SwiftPM은 공식 binary artifact를 내려받고 선언된 checksum으로 확인했다. 전역 설치나 sandbox·플러그인 신뢰 검증 해제는 사용하지 않았다.

| 검증 | 실제 결과 |
|---|---|
| 정상 빌드·변경 없는 재빌드 | 종료 0, `Running SwiftLint` 확인 |
| 소스에 `greeting!` 추가 | `force_unwrapping` error, 빌드 종료 1 |
| 소스 유지, 설정만 warning으로 변경 | 빌드 종료 0; 직접 SwiftLint 호출에서 같은 위반의 warning 확인 |
| 소스 유지, 설정만 error로 복구 | 같은 위반의 error, 빌드 종료 1 |
| 소스 복구 | 빌드 종료 0 |
| 복사본 도구의 실행 권한 제거 | `Permission denied`, 빌드 종료 1 |
| 실행 권한 복구 | 빌드 종료 0 |
| 복사본 도구 파일을 임시 이동 | `No such file or directory`, 빌드 종료 1 |
| 도구 복구·최종 빌드 | 빌드 종료 0 |
| 완성 프로그램 실행 | 종료 0, `Hello, SwiftLint` 출력 |

도구·경로 조회를 포함한 최종 실행기의 15개 검사가 모두 통과했다. 소스·설정 hash를 각 단계에 기록해 변경 범위를 구분했다. 도구 실패는 대체 스크립트로 모사하지 않고 이 예제 복사본의 실제 artifact를 일시 변경했다. 정상 소스·설정·도구를 마지막에 복구했다.

초기 검증 실행기는 로그 형식 가정 때문에 두 번 멈췄다. 첫 번째는 SwiftBuild 로그가 원시 실행 인수 대신 `Running SwiftLint`를 표시했기 때문이다. 두 번째는 성공한 prebuild warning이 빌드 로그에 표시되지 않았기 때문이다. 실제 종료 상태와 직접 진단을 함께 검사하도록 수정했으며 원래 로그도 보존했다. 최종 실행 후 독립 리뷰에서 발견한 예제 내부 output 경로의 재귀 복사 가능성을 차단했다. 그 경로 검사를 별도로 실행했고, 강화한 도구 실패 메시지 단언은 보존한 실제 빌드 로그로 확인했다. 이후 전체 Swift 빌드를 반복하지 않았다.

재현 명령은 `python3 examples/swiftlint-build/verify.py --output /tmp/new-swiftlint-proof`다. 전체 로그와 `results.json`은 지정한 로컬 출력 경로에 보존한다. SwiftPM 실행 target의 이 도구 체인에서 확인한 결과이며, 독립 `.xcodeproj`의 Run Script·GUI 빌드, 다른 도구 체인·플랫폼·CI·실제 기기는 검증하지 않았다. 이 검증은 기존 Refactor 0.2.0 지침을 적용한 예제이며 Plugin payload 변경은 없다.
