import XCTest
@testable import MacPilotCore

final class SimulatorTests: XCTestCase {
    func testUUIDRequiresExplicitDevice() throws {
        for value in ["booted","default","","../../other"] {XCTAssertThrowsError(try SimulatorModel.uuid(value))}
        XCTAssertEqual(try SimulatorModel.uuid("e936dce4-1ce9-4fdf-ad09-a1b526e16907"),"E936DCE4-1CE9-4FDF-AD09-A1B526E16907")
    }
    func testBundleIDsCannotBecomeOptions() throws {
        for value in ["--console","-app.id","app.id\nextra","app/id","", "app id"] {XCTAssertThrowsError(try SimulatorModel.bundleID(value))}
        XCTAssertEqual(try SimulatorModel.bundleID("local.macpilot.test-fixture"),"local.macpilot.test-fixture")
    }
    func testLaunchdBootIdentityRequiresExactJobAndOnePID() throws {
        let id="E936DCE4-1CE9-4FDF-AD09-A1B526E16907"
        let text="user/501/com.apple.CoreSimulator.SimDevice.\(id) = {\n pid = 1234\n /Devices/\(id)/data/var/run/launchd_bootstrap.plist\n}\n"
        XCTAssertEqual(try SimulatorModel.launchdPID(text,udid:id,uid:501),1234)
        XCTAssertThrowsError(try SimulatorModel.launchdPID(text,udid:id,uid:502))
        XCTAssertThrowsError(try SimulatorModel.launchdPID(text+" pid = 4321\n",udid:id,uid:501))
        XCTAssertThrowsError(try SimulatorModel.launchdPID(text.replacingOccurrences(of:"pid = 1234",with:"pid = 0"),udid:id,uid:501))
        XCTAssertThrowsError(try SimulatorModel.launchdPID(text.replacingOccurrences(of:"data/var/run/launchd_bootstrap.plist",with:"other"),udid:id,uid:501))
    }
    func testReadOperationsDoNotClaimInputDispatch() {
        for op in ["list","status","screenshot","observe","probe_input"] {
            XCTAssertTrue(Outcomes.isRead("mac_simulator",arguments:["operation":op]))
        }
        XCTAssertFalse(Outcomes.isRead("mac_simulator",arguments:["operation":"input"]))
    }
    func testPrivateInputIsOptInInSchema() throws {
        let tool=try XCTUnwrap(ToolCatalog.tools.first{$0["name"] as? String == "mac_simulator"})
        let schema=try XCTUnwrap(tool["inputSchema"] as? [String:Any]),properties=try XCTUnwrap(schema["properties"] as? [String:Any])
        XCTAssertEqual((properties["privateAPI"] as? [String:Any])?["default"] as? Bool,false)
        XCTAssertNil(properties["route"])
        for key in ["x","y","toX","toY","x2","y2","toX2","toY2"] {
            let point=properties[key] as? [String:Any]
            XCTAssertEqual(point?["minimum"] as? Int,0);XCTAssertEqual(point?["maximum"] as? Int,1)
        }
    }
}
