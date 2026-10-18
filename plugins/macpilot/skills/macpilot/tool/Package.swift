// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "MacPilot",
    platforms: [.macOS(.v14)],
    products: [.executable(name: "macpilot", targets: ["MacPilot"]),
               .executable(name: "macpilot-simulator-hid", targets: ["MacPilotSimulatorHID"]),
               .executable(name: "macpilot-fixture", targets: ["MacPilotFixture"]),
               .executable(name: "macpilot-capability-fixture", targets: ["MacPilotCapabilityFixture"])],
    dependencies: [],
    targets: [.target(name: "MacPilotCore"),
              .executableTarget(name: "MacPilotSimulatorHID", linkerSettings: [.linkedFramework("AppKit")]),
              .executableTarget(name: "MacPilot", dependencies: ["MacPilotCore"]),
              .executableTarget(name: "MacPilotFixture"),
              .executableTarget(name: "MacPilotCapabilityFixture"),
              .testTarget(name: "MacPilotCoreTests", dependencies: ["MacPilotCore"])]
)
