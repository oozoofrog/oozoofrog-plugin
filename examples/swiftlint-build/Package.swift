// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "SwiftLintBuildExample",
    platforms: [.macOS(.v13)],
    dependencies: [
        .package(url: "https://github.com/SimplyDanny/SwiftLintPlugins", exact: "0.65.1")
    ],
    targets: [
        .executableTarget(
            name: "HelloLint",
            plugins: [.plugin(name: "SwiftLintBuildToolPlugin", package: "SwiftLintPlugins")]
        )
    ]
)
