import AppKit
import XCTest
@testable import MacPilotCore

final class PermissionSetupTests: XCTestCase {
    @MainActor func testPermissionActionsAreRejectedBeforeLaunchInBackgroundTasks() async throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: root) }
        let store = try Store(root: root), engine = Engine(store: store)
        let created = try await engine.call("mac_task", arguments: ["operation": "begin", "goal": "Synthetic permission guard check"])
        let task = try XCTUnwrap((created["task"] as? [String: Any])?["id"] as? String)
        for operation in ["request", "setup"] {
            do {
                _ = try await engine.call("mac_permission", arguments: ["taskID": task, "kind": "accessibility", "operation": operation])
                XCTFail("Background task reached a permission action")
            } catch { XCTAssertEqual((error as? ToolFailure)?.code, "foreground_required") }
        }
    }

    @MainActor func testPermissionSetupRespectsTheSharedSystemInputLeaseBeforeLaunch() async throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: root) }
        let store = try Store(root: root)
        let lease = try store.lease(".system-input.lock")
        defer { withExtendedLifetime(lease) {} }
        do {
            _ = try await Engine(store: store).call("mac_permission", arguments: ["kind": "accessibility", "operation": "setup"])
            XCTFail("Permission setup ignored the active system input lease")
        } catch { XCTAssertEqual((error as? ToolFailure)?.code, "busy") }
    }

    private func fixture() throws -> URL {
        let app = FileManager.default.temporaryDirectory.appendingPathComponent("permission-\(UUID().uuidString)/한글 공백/MacPilot.app")
        let executable = app.appendingPathComponent("Contents/MacOS/macpilot")
        try FileManager.default.createDirectory(at: executable.deletingLastPathComponent(), withIntermediateDirectories: true)
        try Data().write(to: executable)
        let plist: [String: Any] = ["CFBundleIdentifier": "local.macpilot", "CFBundleExecutable": "macpilot", "CFBundlePackageType": "APPL"]
        try PropertyListSerialization.data(fromPropertyList: plist, format: .xml, options: 0).write(to: app.appendingPathComponent("Contents/Info.plist"))
        addTeardownBlock { try? FileManager.default.removeItem(at: app.deletingLastPathComponent().deletingLastPathComponent()) }
        return app
    }

    @MainActor func testDragPayloadRoundTripsActualFileURLWithUnicodeAndSpaces() throws {
        let app = try fixture()
        let view = PermissionAppDragView(applicationURL: app)
        let item = view.draggingItem(at: NSPoint(x: 60, y: 60))
        let writer = try XCTUnwrap(item.item as? NSURL)
        let pasteboard = NSPasteboard.withUniqueName()
        defer { pasteboard.releaseGlobally() }
        XCTAssertTrue(pasteboard.writeObjects([writer]))
        XCTAssertTrue(pasteboard.types?.contains(.fileURL) == true)
        let read = try XCTUnwrap(pasteboard.readObjects(forClasses: [NSURL.self])?.first as? URL)
        XCTAssertEqual(read.standardizedFileURL, app.standardizedFileURL)
        let resolved = try PermissionSetup.applicationURL(executable: app.appendingPathComponent("Contents/MacOS/macpilot"))
        XCTAssertEqual(resolved.resolvingSymlinksInPath().path, app.resolvingSymlinksInPath().path)
    }

    @MainActor func testRawExecutablesAndOtherAppIdentitiesCannotBeDraggedAsMacPilot() throws {
        XCTAssertThrowsError(try PermissionSetup.applicationURL(executable: URL(fileURLWithPath: "/tmp/.build/release/macpilot")))
        let app = try fixture()
        XCTAssertThrowsError(try PermissionSetup.applicationURL(executable: app.appendingPathComponent("Contents/MacOS/other")))
        let alien = app.deletingLastPathComponent().appendingPathComponent("Other.app/Contents/MacOS/macpilot")
        XCTAssertThrowsError(try PermissionSetup.applicationURL(executable: alien))
    }

    @MainActor func testOnlySupportedSettingsPanesAreAccepted() async throws {
        XCTAssertTrue(try PermissionSetup.settingsURL(for: "accessibility").absoluteString.hasSuffix("Privacy_Accessibility"))
        XCTAssertTrue(try PermissionSetup.settingsURL(for: "screenCapture").absoluteString.hasSuffix("Privacy_ScreenCapture"))
        for kind in ["postEvent", "inputMonitoring", "", "../screenCapture"] {
            XCTAssertThrowsError(try PermissionSetup.settingsURL(for: kind))
        }
        for input: [String: Any] in [["kind": "accessibility", "operation": "approve"], ["kind": "postEvent", "operation": "setup"], ["kind": "screenCapture", "operation": "setup", "timeoutMs": 0]] {
            do { _ = try await SystemActions.permission(Arguments(input)); XCTFail("Invalid setup launched: \(input)") }
            catch { XCTAssertEqual((error as? ToolFailure)?.code, "invalid_argument") }
        }
    }

    @MainActor func testLayoutAndPermissionSelectionWithoutChangingSystemSettings() throws {
        _ = NSApplication.shared
        let app = try fixture()
        let controller = PermissionSetupController(applicationURL: app, kind: "screenCapture")
        XCTAssertEqual(controller.kind, "screenCapture")
        controller.selector.selectedSegment = 0
        controller.selectionChanged()
        XCTAssertEqual(controller.kind, "accessibility")
        XCTAssertTrue(controller.status.stringValue.contains("손쉬운 사용:"))
        let content = try XCTUnwrap(controller.window.contentView)
        content.layoutSubtreeIfNeeded()
        let stack = try XCTUnwrap(content.subviews.first as? NSStackView)
        XCTAssertGreaterThan(stack.frame.height, 400)
        for view in stack.arrangedSubviews {
            let frame = view.convert(view.bounds, to: content)
            XCTAssertGreaterThanOrEqual(frame.minY, 19, "Clipped view: \(view)")
            XCTAssertLessThanOrEqual(frame.maxY, content.bounds.maxY - 20)
            XCTAssertLessThanOrEqual(frame.maxX, content.bounds.maxX - 20)
        }
        if let path = ProcessInfo.processInfo.environment["MACPILOT_PERMISSION_TEST_EVIDENCE"] {
            let bitmap = try XCTUnwrap(content.bitmapImageRepForCachingDisplay(in: content.bounds))
            content.cacheDisplay(in: content.bounds, to: bitmap)
            try XCTUnwrap(bitmap.representation(using: .png, properties: [:])).write(to: URL(fileURLWithPath: path))
        }
        controller.window.close()
    }
}
