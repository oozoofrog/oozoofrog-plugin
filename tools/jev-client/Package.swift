// swift-tools-version:6.0
import PackageDescription

let package = Package(
    name: "jev-client",
    platforms: [.macOS(.v14)],
    targets: [
        .target(name: "JevClientCore"),
        .executableTarget(name: "jev-client", dependencies: ["JevClientCore"]),
        .testTarget(name: "JevClientCoreTests", dependencies: ["JevClientCore"]),
    ]
)
