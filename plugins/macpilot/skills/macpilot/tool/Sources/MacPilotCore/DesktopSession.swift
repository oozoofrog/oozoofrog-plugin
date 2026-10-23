import CoreGraphics
import Foundation
import Security

/// Preflight for this invocation, not a TCC verdict or a promise that GUI actions work.
public struct DesktopSession: Sendable {
    public let securityStatus: OSStatus
    public let hasGraphicAccess: Bool
    public let sessionDictionaryAvailable: Bool

    public var available: Bool { securityStatus == errSecSuccess && hasGraphicAccess && sessionDictionaryAvailable }

    public static func current() -> DesktopSession {
        var session: SecuritySessionId = 0
        var attributes: SessionAttributeBits = []
        let status = SessionGetInfo(callerSecuritySession, &session, &attributes)
        let graphic = status == errSecSuccess && attributes.contains(.sessionHasGraphicAccess)
        return DesktopSession(securityStatus: status, hasGraphicAccess: graphic,
                              sessionDictionaryAvailable: graphic && CGSessionCopyCurrentDictionary() != nil)
    }

    public var object: [String: Any] {
        ["available": available, "securityStatus": securityStatus, "hasGraphicAccess": hasGraphicAccess,
         "sessionDictionaryAvailable": sessionDictionaryAvailable,
         "sessionDictionaryProbeStatus": securityStatus == errSecSuccess && hasGraphicAccess ? "probed" : "not_probed",
         "reason": available ? "preflight_passed" : "window_server_session_unavailable",
         "verification": "Current invocation preflight only; this does not establish TCC permission or GUI operation success"]
    }

    public func requireAvailable() throws {
        guard available else {
            throw ToolFailure("gui_session_unavailable", "This invocation cannot establish its WindowServer session. Run desktop operations from an authorized GUI execution context; this is not a TCC permission verdict. No desktop action was sent.")
        }
    }

    public static var unknownPermissions: [String: Any] {
        ["accessibility": NSNull(), "screenCapture": NSNull(), "postEvent": NSNull(), "inputMonitoring": NSNull()]
    }
}
