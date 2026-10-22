import XCTest
@testable import JevComputerUse

final class StartupTests: XCTestCase {
    func testPureCommandsDoNotRequestApplicationRegistration() {
        for args in [[], ["help"], ["--help"], ["setup"], ["setup", "--import-pasteboard"], ["install-skill", "--host", "both"], ["doctor"], ["delegate", "--prompt", "test"]] {
            XCTAssertEqual(startupMode(args), .cli)
        }
    }
    func testPreviewAndVirtualMarkerRequireApplicationLoop() {
        XCTAssertEqual(startupMode(["--gui"]), .application)
        XCTAssertEqual(startupMode(["--gui", "--no-preview"]), .application)
        XCTAssertEqual(startupMode(["run"]), .application)
        XCTAssertEqual(startupMode(["run", "--no-preview"]), .nativeServices)
        XCTAssertEqual(startupMode(["run", "--no-preview", "--show-virtual-cursor"]), .application)
        XCTAssertEqual(startupMode(["act", "--show-virtual-cursor"]), .application)
        XCTAssertEqual(startupMode(["act"]), .nativeServices)
        XCTAssertEqual(startupMode(["observe"]), .nativeServices)
    }
    func testMissingDesktopAndLaunchServicesErrorsAreActionable() {
        for context in [GUIContext(sessionStatus: -60500, graphicalAccess: false), GUIContext(sessionStatus: 0, graphicalAccess: false), GUIContext(sessionStatus: 0, graphicalAccess: true, launchServicesError: "test-domain code 801")] {
            XCTAssertThrowsError(try context.requireAvailable()) { error in
                XCTAssertTrue(String(describing: error).contains("logged-in"))
            }
        }
        XCTAssertNoThrow(try GUIContext(sessionStatus: 0, graphicalAccess: true).requireAvailable())
    }
}
