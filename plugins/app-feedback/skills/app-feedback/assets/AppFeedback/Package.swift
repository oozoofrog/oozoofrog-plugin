// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "AppFeedback",
    platforms: [.iOS(.v17), .macOS(.v14)],
    products: [.library(name: "AppFeedback", targets: ["AppFeedback"])],
    targets: [
        .target(name: "AppFeedback"),
        .testTarget(name: "AppFeedbackTests", dependencies: ["AppFeedback"])
    ]
)
