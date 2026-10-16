import AppKit
import ApplicationServices
import Darwin

/// Private SPI is opt-in at the call site. Symbol presence is not ABI or behavior validation.
public enum PrivateAPI {
    private static let hiservices = "/System/Library/Frameworks/ApplicationServices.framework/Frameworks/HIServices.framework/HIServices"
    private static let candidates: [(String, String, [String])] = [
        ("Accessibility window identity", hiservices, ["_AXUIElementGetWindow"]),
        ("WindowServer / Spaces / input", "/System/Library/PrivateFrameworks/SkyLight.framework/SkyLight",
         ["SLSMainConnectionID", "_SLPSSetFrontProcessWithOptions", "SLPSPostEventRecordTo", "SLSOrderWindow",
          "SLSGetWindowBounds", "SLSGetWindowLevel", "SLSCopyManagedDisplaySpaces", "SLSCopySpacesForWindows",
          "SLSMoveWindowsToManagedSpace", "SLSSetWindowAlpha", "SLSSetWindowTransform", "SLSNewConnection"]),
        ("Display brightness", "/System/Library/PrivateFrameworks/DisplayServices.framework/DisplayServices",
         ["DisplayServicesGetBrightness", "DisplayServicesSetBrightness"]),
        ("Display configuration", "/System/Library/PrivateFrameworks/CoreDisplay.framework/CoreDisplay",
         ["CoreDisplay_Display_GetUserBrightness", "CoreDisplay_Display_SetUserBrightness"])
    ]
    public static func catalog() -> [[String: Any]] {
        candidates.flatMap { family, path, symbols in
            let handle = dlopen(path, RTLD_LAZY | RTLD_LOCAL)
            defer { if let handle { dlclose(handle) } }
            return symbols.map { symbol in
                ["family":family, "framework":path, "symbol":symbol,
                 "exported":handle.flatMap { dlsym($0, symbol) } != nil,
                 "callableBackend":symbol == "_AXUIElementGetWindow" ? "window-identity" : "research-only",
                 "private":true] as [String:Any]
            }
        }
    }
    public static func windowID(_ element: AXUIElement) throws -> UInt32 {
        guard AXIsProcessTrusted() else { throw ToolFailure("accessibility_denied", "Private window identity still requires Accessibility permission") }
        guard let handle = dlopen(hiservices, RTLD_LAZY | RTLD_LOCAL) else {
            throw ToolFailure("private_api_unavailable", "HIServices cannot be loaded on this OS")
        }
        defer { dlclose(handle) }
        guard let symbol = dlsym(handle, "_AXUIElementGetWindow") else {
            throw ToolFailure("private_api_unavailable", "_AXUIElementGetWindow is not exported on this OS")
        }
        typealias Function = @convention(c) (AXUIElement, UnsafeMutablePointer<UInt32>) -> AXError
        let function = unsafeBitCast(symbol, to: Function.self)
        var id: UInt32 = 0
        let error = function(element, &id)
        guard error == .success, id > 0 else { throw ToolFailure("private_api_failed", "_AXUIElementGetWindow failed: \(error.rawValue)") }
        return id
    }
    @MainActor public static func call(_ a: Arguments) throws -> [String: Any] {
        let operation = try a.string("operation")
        if operation == "catalog" {
            try a.only(["operation"])
            return ["status":"private_api_catalog", "os":ProcessInfo.processInfo.operatingSystemVersionString,
                    "symbols":catalog(), "verification":"Export checks only. Research-only symbols are never invoked."]
        }
        try a.only(["operation", "pid", "processStartID", "enabled"])
        guard operation == "window_ids" else { throw ToolFailure("invalid_argument", "operation must be catalog or window_ids") }
        guard try a.bool("enabled") else { throw ToolFailure("private_api_disabled", "Set enabled=true to explicitly use the private window-identity SPI") }
        let pid = Int32(try a.integer("pid", range: 1...Int(Int32.max))), identity = try a.string("processStartID", limit:64)
        try ProcessIdentity.require(pid: pid, expected: identity)
        let windows: [[String:Any]] = try AX.windows(pid).map {
            ["windowID":try windowID($0), "title":AX.string($0, kAXTitleAttribute), "frame":AX.frame($0)?.object ?? [:]]
        }
        try ProcessIdentity.require(pid: pid, expected: identity)
        return ["status":"private_window_ids", "backend":"_AXUIElementGetWindow", "pid":pid, "windows":windows]
    }
}
