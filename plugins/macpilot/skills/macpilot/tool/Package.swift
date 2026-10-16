// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "MacPilot",
    platforms: [.macOS(.v14)],
    products: [.executable(name: "macpilot", targets: ["MacPilot"]),
               .executable(name: "macpilot-fixture", targets: ["MacPilotFixture"])],
    dependencies: [],
    targets: [.target(name: "MacPilotCore"),
              .executableTarget(name: "MacPilot", dependencies: ["MacPilotCore"]),
              .executableTarget(name: "MacPilotFixture"),
              .testTarget(name: "MacPilotCoreTests", dependencies: ["MacPilotCore"])]
)
