// swift-tools-version: 6.0
import PackageDescription
let package = Package(name: "JevComputerUse", platforms: [.macOS(.v14)], products: [.executable(name: "jev-native", targets: ["JevComputerUse"]),.executable(name:"jev-native-fixture",targets:["JevNativeFixture"])], targets: [.executableTarget(name: "JevComputerUse"),.executableTarget(name:"JevNativeFixture"), .testTarget(name: "JevComputerUseTests", dependencies: ["JevComputerUse"])], swiftLanguageModes: [.v5])
