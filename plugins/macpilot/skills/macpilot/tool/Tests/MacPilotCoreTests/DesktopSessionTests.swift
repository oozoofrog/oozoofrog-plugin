import XCTest
@testable import MacPilotCore

final class DesktopSessionTests: XCTestCase {
    func testGraphicsFlagAloneDoesNotAuthorizeAppKitInitialization() {
        let restricted = DesktopSession(securityStatus: 0, hasGraphicAccess: true, sessionDictionaryAvailable: false)
        XCTAssertFalse(restricted.available)
        XCTAssertThrowsError(try restricted.requireAvailable()) { error in
            XCTAssertEqual((error as? ToolFailure)?.code, "gui_session_unavailable")
            XCTAssertFalse((error as? ToolFailure)?.description.contains("permission_denied") ?? true)
        }
        XCTAssertEqual(restricted.object["reason"] as? String, "window_server_session_unavailable")
    }

    func testAllPreflightObservationsAreRequired() throws {
        for session in [DesktopSession(securityStatus: -1, hasGraphicAccess: true, sessionDictionaryAvailable: true),
                        DesktopSession(securityStatus: 0, hasGraphicAccess: false, sessionDictionaryAvailable: true)] {
            XCTAssertFalse(session.available)
            XCTAssertEqual(session.object["sessionDictionaryProbeStatus"] as? String, "not_probed")
            XCTAssertThrowsError(try session.requireAvailable())
        }
        let usable = DesktopSession(securityStatus: 0, hasGraphicAccess: true, sessionDictionaryAvailable: true)
        XCTAssertTrue(usable.available)
        XCTAssertNoThrow(try usable.requireAvailable())
    }

    func testSkippedPermissionProbesRemainUnknownRatherThanDenied() {
        XCTAssertEqual(DesktopSession.unknownPermissions.count, 4)
        XCTAssertTrue(DesktopSession.unknownPermissions.values.allSatisfy { $0 is NSNull })
    }
}
