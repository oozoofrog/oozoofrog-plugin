import Foundation
import Security
import CoreServices

enum StartupMode: Equatable { case cli, nativeServices, application }

func startupMode(_ arguments: [String]) -> StartupMode {
    switch arguments.first ?? "help" {
    case "--gui": return .application
    case "run": return arguments.contains("--no-preview") && !arguments.contains("--show-virtual-cursor") ? .nativeServices : .application
    case "act": return arguments.contains("--show-virtual-cursor") ? .application : .nativeServices
    case "observe", "ax-query": return .nativeServices
    default: return .cli
    }
}

struct GUIContext {
    var sessionStatus: OSStatus
    var graphicalAccess: Bool
    var launchServicesError: String?

    static func current() -> Self {
        var id = SecuritySessionId(), attributes = SessionAttributeBits()
        let status = SessionGetInfo(callerSecuritySession, &id, &attributes)
        // This public read-only lookup can detect a LaunchServices error before AppKit
        // registration. A successful lookup is not a guarantee that registration will succeed.
        var diagnostic: String?
        if status == errSecSuccess && attributes.contains(.sessionHasGraphicAccess) {
            var error: Unmanaged<CFError>?
            _ = LSCopyApplicationURLsForBundleIdentifier("com.apple.finder" as CFString, &error)?.takeRetainedValue()
            if let value = error?.takeRetainedValue() {
                diagnostic = "\(CFErrorGetDomain(value) as String? ?? "unknown domain") code \(CFErrorGetCode(value))"
            }
        }
        return Self(sessionStatus: status, graphicalAccess: attributes.contains(.sessionHasGraphicAccess), launchServicesError: diagnostic)
    }

    func requireAvailable() throws {
        guard sessionStatus == errSecSuccess, graphicalAccess else {
            throw Failure("Native macOS UI requires a graphical login session (Security session status \(sessionStatus)). Run from Terminal or Codex in the logged-in user's desktop session, rather than a headless/system session. Help, setup without a UI action, skill installation and file-based delegation do not require NSApplication registration.")
        }
        if let launchServicesError {
            throw Failure("LaunchServices is unavailable before AppKit startup (\(launchServicesError)). Retry from the logged-in user's Terminal or Codex with normal desktop-service access. Do not reset system databases; retain stderr and the launch context if this persists.")
        }
    }
}
