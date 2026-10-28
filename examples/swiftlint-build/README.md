# SwiftLint 빌드 통합 예제

SwiftPM 실행 target `HelloLint`에 공식 `SwiftLintBuildToolPlugin`을 연결한다. 패키지 버전은 `0.65.1`로 고정했으며 `Package.resolved`에 커밋을 기록했다. 첫 빌드는 의존성 및 공식 바이너리 artifact를 다운로드하고 SwiftPM이 패키지의 checksum으로 검증한다. macOS 13 이상과 호환되는 Xcode/Swift toolchain, Python 3.9 이상이 필요하다. 전역 SwiftLint 설치는 필요하지 않다.

```sh
swift build --package-path examples/swiftlint-build
python3 examples/swiftlint-build/verify.py --output /tmp/my-swiftlint-build-proof
```

출력 디렉터리는 존재하지 않는 경로를 지정하고 예제 디렉터리 밖에 둔다. 생략하면 임시 디렉터리를 만든다. 실행기는 예제를 복사한 뒤 실제 Swift 빌드를 수행한다. 예제 원본은 변경하지 않고, 도구 실패 시험은 복사본의 artifact만 변경한 뒤 복구한다. JSON 결과와 단계별 전체 로그를 출력 디렉터리에 보존한다. 실패한 SwiftPM prebuild 로그에는 실행 환경이 포함될 수 있으므로 공개 전 내용을 확인한다.

검사는 정상 빌드, 변경 없는 재빌드, 소스 위반 추가, 설정의 error→warning→error 변경, 소스 복구, 도구 실행 권한 제거·복구, 도구 파일 부재·복구와 최종 프로그램 실행을 포함한다. 첫 빌드 이후 `clean`이나 cache 삭제를 하지 않는다. `force_unwrapping` 한 규칙만 의도적으로 사용하며 기본 상태의 소스는 위반이 없다.

Swift 6.4의 기본 `swiftbuild` 엔진은 `Running SwiftLint`를 기록하지만 성공한 prebuild 명령의 warning 출력은 이 환경에서 표시하지 않았다. 실행기는 warning 설정에서 별도로 실제 SwiftLint를 호출해 진단을 확인한다. 실행 파일 경로는 `.build/debug`로 가정하지 않고 `swift build --show-bin-path`로 찾는다.

[실제 검증 결과와 한계](../../docs/validation/refactor-swiftlint-build.md)를 참고한다.
