# Xcode SwiftLint Run Script 예제

macOS 명령행 target `HelloLintXcode`의 Compile Sources 다음에 SwiftLint Run Script를 연결한다. 프로젝트 원본은 `project.yml`이며 XcodeGen 2.46.0으로 생성한 `.xcodeproj`와 공유 scheme을 함께 제공한다. 프로젝트 또는 `Scripts/lint.sh`를 바꾸면 XcodeGen으로 재생성한다.

필요한 도구는 Xcode, Python 3.9 이상과 실제 SwiftLint 0.65.1 바이너리다. SwiftLint 바이너리는 저장소에 포함하지 않는다. [SwiftPM 예제](../swiftlint-build/README.md)를 빌드하면 고정된 공식 패키지와 checksum 검증을 거쳐 다음 경로에 바이너리를 준비할 수 있다.

```sh
swift build --package-path examples/swiftlint-build
python3 examples/xcode-swiftlint-build/verify.py \
  --swiftlint examples/swiftlint-build/.build/artifacts/swiftlintplugins/SwiftLintBinary/SwiftLintBinary.artifactbundle/macos/swiftlint \
  --output /tmp/new-xcode-swiftlint-proof
```

실행기는 예제를 새 출력 경로로 복사하고 바이너리도 복사본 `.tools/swiftlint`에 복제한다. 원본 바이너리는 변경하지 않는다. 복사본에서 같은 DerivedData를 사용해 실제 `xcodebuild` Debug arm64 빌드를 실행하고 단계별 전체 로그·종료 코드·소스/설정 hash와 `main.o` hash·mtime을 저장한다. 출력 경로는 예제 밖의 새 디렉터리를 사용한다. 결과에는 실제 환경 경로가 포함된다.

프로젝트를 Xcode에서 직접 열려면 먼저 실제 SwiftLint를 예제 `.tools/swiftlint`에 복사한다. GUI 실행은 이번 검증에 포함하지 않았다. target의 `ENABLE_USER_SCRIPT_SANDBOXING=YES`를 유지하고 소스·설정·스크립트·도구 디렉터리를 입력으로 선언했다. 캐시는 `--no-cache`로 사용하지 않는다. `basedOnDependencyAnalysis: false`로 매 빌드 한 번씩 검사하며, output stamp를 사용해 검사를 건너뛰지 않는다. 서명은 필요하지 않은 명령행 예제이므로 target에서 끈다.

검사는 정상/변경 없는 재빌드, 소스 위반, 설정 error→warning→error 변경, 도구 실행 권한 제거/부재와 각각의 복구, 프로그램 출력을 포함한다. 첫 빌드 이후 clean이나 DerivedData 삭제를 하지 않는다. 도구 부재·실행 권한 오류는 Run Script가 각각 127·126으로 실패하고 `xcodebuild`가 65로 전달한다. 실제 lint 오류도 빌드 실패로 전달한다.

[실제 결과와 검증 범위](../../docs/validation/refactor-xcode-swiftlint-build.md)를 참고한다.
