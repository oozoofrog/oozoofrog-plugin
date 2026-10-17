import AppKit
import XCTest
import Carbon
@testable import MacPilotCore

final class PermissionSetupTests: XCTestCase {
    func testFullDiskAccessRecognizesObservedKoreanSettingsTitle() {
        XCTAssertTrue(PermissionKind.fullDiskAccess.titles.contains("전체 디스크 접근 권한"))
    }

    @MainActor func testOnboardingCueStaysInSettingsContentAndContainsItsPath() {
        let settings = CGRect(x: 800, y: 100, width: 740, height: 810)
        let source = CGPoint(x: 748, y: 702)
        let end = PermissionDragOnboarding.destination(settings: settings)
        XCTAssertTrue(settings.contains(end))
        XCTAssertGreaterThan(end.x, settings.minX+settings.width*0.28)
        let bounds = PermissionDragOnboarding.bounds(source: source, destination: end)
        XCTAssertTrue(bounds.contains(source)); XCTAssertTrue(bounds.contains(end))
    }

    @MainActor func testOnboardingIsInputTransparentAndStopsAfterUserInteraction() throws {
        _ = NSApplication.shared
        let controller = PermissionSetupController(applicationURL: try fixture(), plan: [.accessibility], targetBundleID: "com.apple.Safari")
        defer { controller.window.close() }
        let hint = controller.onboarding
        XCTAssertTrue(hint.panel.ignoresMouseEvents)
        XCTAssertFalse(hint.panel.canBecomeKey)
        XCTAssertFalse(hint.panel.canBecomeMain)
        XCTAssertFalse(hint.panel.isOpaque)
        XCTAssertEqual(hint.panel.backgroundColor.alphaComponent, 0)
        let settings = CGRect(x: 800, y: 100, width: 740, height: 810)
        let now = Date()
        hint.update(source: controller.window, settings: settings, kind: .accessibility, allowed: false,
                    eligible: true, reducedMotion: true, now: now)
        XCTAssertFalse(hint.isPlaying); XCTAssertFalse(hint.panel.isVisible)
        hint.userDidInteract()
        hint.update(source: controller.window, settings: settings, kind: .accessibility, allowed: false,
                    eligible: true, reducedMotion: false, now: now.addingTimeInterval(2))
        hint.update(source: controller.window, settings: settings, kind: .accessibility, allowed: false,
                    eligible: true, reducedMotion: false, now: now.addingTimeInterval(5))
        XCTAssertTrue(hint.userInteracted)
        XCTAssertEqual(hint.playCount, 0)
        XCTAssertFalse(hint.panel.isVisible)
        hint.replay()
        hint.update(source: controller.window, settings: settings, kind: .accessibility, allowed: true,
                    eligible: true, reducedMotion: true, now: now.addingTimeInterval(7))
        XCTAssertFalse(hint.isPlaying)
        XCTAssertFalse(hint.panel.isVisible)
    }

    @MainActor func testPermissionActionsAreRejectedBeforeLaunchInBackgroundTasks() async throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: root) }
        let store = try Store(root: root), engine = Engine(store: store)
        let created = try await engine.call("mac_task", arguments: ["operation": "begin", "goal": "Synthetic permission guard check"])
        let task = try XCTUnwrap((created["task"] as? [String: Any])?["id"] as? String)
        for kind in PermissionKind.allCases {
            for operation in ["request", "setup"] {
                do {
                    _ = try await engine.call("mac_permission", arguments: ["taskID": task, "kind": kind.rawValue, "operation": operation])
                    XCTFail("Background task reached a permission action")
                } catch { XCTAssertEqual((error as? ToolFailure)?.code, "foreground_required") }
            }
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

    @MainActor func testApplicationURLWithUnicodeAndSpaces() throws {
        let app = try fixture()
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

    @MainActor func testNativePlanDoesNotRequestUnneededBroadPermissions() throws {
        XCTAssertEqual(try PermissionKind.plan("all"), [.accessibility, .screenCapture, .automation])
        for kind in PermissionKind.allCases {
            XCTAssertEqual(try PermissionKind.plan(kind.rawValue), [kind])
            XCTAssertTrue(try PermissionSetup.settingsURL(for: kind.rawValue).absoluteString.hasSuffix(kind.pane))
        }
        XCTAssertFalse(PermissionKind.automation.acceptsAppDrop)
        XCTAssertFalse(PermissionKind.files.acceptsAppDrop)
        XCTAssertFalse(PermissionKind.clipboard.acceptsAppDrop)
        for kind in ["", "../screenCapture", "safari", "camera", "microphone"] {
            XCTAssertThrowsError(try PermissionKind.plan(kind))
        }
    }

    @MainActor func testInvalidSetupArgumentsFailBeforeNativeWindowsOpen() async throws {
        for input: [String: Any] in [
            ["kind": "invalid", "operation": "setup"],
            ["kind": "screenCapture", "operation": "setup", "timeoutMs": 0],
            ["kind": "automation", "operation": "setup", "targetBundleID": "../Safari"],
            ["kind": "screenCapture", "targetBundleID": "com.apple.Safari"],
            ["kind": "automation", "operation": "approve"]
        ] {
            do { _ = try await SystemActions.permission(Arguments(input)); XCTFail("Invalid setup launched") }
            catch { XCTAssertEqual((error as? ToolFailure)?.code, "invalid_argument") }
        }
    }

    func testNativeRestartPromptIsNotMisreportedAsAuthentication() {
        XCTAssertEqual(NativePermissionPrompt.classify(buttons: ["종료 및 다시 열기", "나중에"], hasSecureInput: false, hasSheet: true), .restartRequired)
        XCTAssertEqual(NativePermissionPrompt.classify(buttons: ["Cancel", "OK"], hasSecureInput: true, hasSheet: true), .authenticationRequired)
        XCTAssertEqual(NativePermissionPrompt.classify(buttons: ["나중에"], hasSecureInput: false, hasSheet: true), .confirmationRequired)
        XCTAssertEqual(NativePermissionPrompt.classify(buttons: [], hasSecureInput: false, hasSheet: false), .none)
    }

    func testAutomationStatusDoesNotInventAResultForUnknownErrors() {
        XCTAssertEqual(PermissionState.automation(noErr), .allowed)
        XCTAssertEqual(PermissionState.automation(OSStatus(errAEEventNotPermitted)), .denied)
        XCTAssertEqual(PermissionState.automation(OSStatus(errAEEventWouldRequireUserConsent)), .needsConsent)
        XCTAssertEqual(PermissionState.automation(OSStatus(procNotFound)), .notRunning)
        XCTAssertEqual(PermissionState.automation(-50), .unknown)
    }

    @MainActor func testNativeListSelectionExcludesSidebarAndAudioOnlyList() throws {
        func node(_ id: String, _ r: CGRect) -> Node {
            Node(id: id, path: [], role: kAXOutlineRole, subrole: "", title: "", identifier: "", value: nil, valueTruncated: false, enabled: true, secure: false, focused: false, frame: Rect(r), actions: [])
        }
        let window = Rect(CGRect(x: 100, y: 100, width: 740, height: 800))
        let sidebar = node("sidebar", CGRect(x: 100, y: 200, width: 232, height: 600))
        let screen = node("screen", CGRect(x: 352, y: 200, width: 468, height: 240))
        let audio = node("audio", CGRect(x: 352, y: 500, width: 468, height: 80))
        let offscreen = node("outside", CGRect(x: 352, y: 0, width: 468, height: 80))
        XCTAssertEqual(try PermissionSetup.listNode([sidebar, audio, screen, offscreen], window: window, kind: .screenCapture).id, "screen")
        XCTAssertThrowsError(try PermissionSetup.listNode([sidebar, offscreen], window: window, kind: .accessibility))
        XCTAssertThrowsError(try PermissionSetup.listNode([screen], window: window, kind: .automation))
    }

    @MainActor func testAttachedGuideDragCarriesActualFileURLWithoutOpeningFinder() throws {
        let app = try fixture(), view = PermissionAppDragView(applicationURL: app)
        let item = view.draggingItem(at: NSPoint(x: 44, y: 41))
        let writer = try XCTUnwrap(item.item as? NSURL)
        let pasteboard = NSPasteboard.withUniqueName()
        defer { pasteboard.releaseGlobally() }
        XCTAssertTrue(pasteboard.writeObjects([writer]))
        let received = try XCTUnwrap(pasteboard.readObjects(forClasses: [NSURL.self])?.first as? URL)
        XCTAssertEqual(received.standardizedFileURL, app.standardizedFileURL)
    }

    @MainActor func testAttachmentFollowsSettingsAndStaysInsideScreen() {
        let visible = CGRect(x: 0, y: 0, width: 1920, height: 1080), size = CGSize(width: 304, height: 440)
        let settings = CGRect(x: 1100, y: 200, width: 740, height: 810)
        let first = PermissionSetupController.attachmentFrame(settings: settings, panel: size, visible: visible)
        let moved = PermissionSetupController.attachmentFrame(settings: settings.offsetBy(dx: -40, dy: -30), panel: size, visible: visible)
        XCTAssertEqual(moved.minX-first.minX, -40)
        XCTAssertEqual(moved.minY-first.minY, -30)
        let atLeft = PermissionSetupController.attachmentFrame(settings: CGRect(x: 0, y: 200, width: 740, height: 810), panel: size, visible: visible)
        XCTAssertGreaterThan(atLeft.minX, 740)
        XCTAssertTrue(visible.contains(first))
        XCTAssertTrue(visible.contains(atLeft))
    }

    @MainActor func testIconOnlyGuideHasOneVisibleControlAndSecondaryActions() throws {
        _ = NSApplication.shared
        let app = try fixture()
        for kind in PermissionKind.allCases {
            let controller = PermissionSetupController(applicationURL: app, plan: [kind], targetBundleID: "com.apple.Safari")
            let content = try XCTUnwrap(controller.window.contentView)
            XCTAssertEqual(content.subviews.count, 1)
            XCTAssertTrue(content.subviews[0] === controller.drag)
            XCTAssertEqual(controller.window.frame.size, NSSize(width: 88, height: 88))
            XCTAssertFalse(controller.window.canBecomeKey)
            XCTAssertEqual(controller.drag.isDraggable, kind.acceptsAppDrop)
            let menu = controller.makeMenu()
            XCTAssertEqual(menu.items.contains { $0.title == "자동으로 추가" }, kind.acceptsAppDrop)
            if let prefix = ProcessInfo.processInfo.environment["MACPILOT_PERMISSION_TEST_EVIDENCE"] {
                let bitmap = try XCTUnwrap(content.bitmapImageRepForCachingDisplay(in: content.bounds))
                content.cacheDisplay(in: content.bounds, to: bitmap)
                let url = URL(fileURLWithPath: prefix).deletingPathExtension().appendingPathExtension("\(kind.rawValue).png")
                try XCTUnwrap(bitmap.representation(using: .png, properties: [:])).write(to: url)
            }
            controller.window.close()
        }
    }

    @MainActor func testMaterialMaskKeepsRoundedCornersTransparent() throws {
        _ = NSApplication.shared
        let controller = PermissionSetupController(applicationURL: try fixture(), plan: [.accessibility], targetBundleID: "com.apple.Safari")
        defer { controller.window.close() }
        let material = try XCTUnwrap(controller.window.contentView as? NSVisualEffectView)
        let mask = try XCTUnwrap(material.maskImage)
        let bitmap = try XCTUnwrap(NSBitmapImageRep(data: try XCTUnwrap(mask.tiffRepresentation)))
        for (x, y) in [(0, 0), (bitmap.pixelsWide-1, 0), (0, bitmap.pixelsHigh-1), (bitmap.pixelsWide-1, bitmap.pixelsHigh-1)] {
            XCTAssertEqual(try XCTUnwrap(bitmap.colorAt(x: x, y: y)).alphaComponent, 0)
        }
        XCTAssertEqual(try XCTUnwrap(bitmap.colorAt(x: bitmap.pixelsWide/2, y: bitmap.pixelsHigh/2)).alphaComponent, 1)
        XCTAssertFalse(controller.window.isOpaque)
        XCTAssertEqual(controller.window.backgroundColor.alphaComponent, 0)
    }
}
