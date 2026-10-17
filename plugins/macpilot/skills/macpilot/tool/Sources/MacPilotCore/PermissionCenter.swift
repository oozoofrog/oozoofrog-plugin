import AppKit
import Carbon

enum PermissionState: String, Equatable {
    case allowed, denied, needsConsent, notRunning, unknown
    var label: String {
        switch self {
        case .allowed: return "허용됨"
        case .denied: return "미허용"
        case .needsConsent: return "승인 필요"
        case .notRunning: return "대상 앱 실행 필요"
        case .unknown: return "확인 필요"
        }
    }
    static func automation(_ status: OSStatus) -> Self {
        switch status {
        case noErr: return .allowed
        case OSStatus(errAEEventNotPermitted): return .denied
        case OSStatus(errAEEventWouldRequireUserConsent): return .needsConsent
        case OSStatus(procNotFound): return .notRunning
        default: return .unknown
        }
    }
}

enum PermissionKind: String, CaseIterable {
    case accessibility, screenCapture, postEvent, inputMonitoring, automation, fullDiskAccess, files, clipboard
    var pane: String {
        switch self {
        case .accessibility, .postEvent: return "Privacy_Accessibility"
        case .screenCapture: return "Privacy_ScreenCapture"
        case .inputMonitoring: return "Privacy_ListenEvent"
        case .automation: return "Privacy_Automation"
        case .fullDiskAccess: return "Privacy_AllFiles"
        case .files: return "Privacy_FilesAndFolders"
        case .clipboard: return "Privacy_Pasteboard"
        }
    }
    var titles: Set<String> {
        switch self {
        case .accessibility, .postEvent: return ["Accessibility", "Device Control and Data Access", "손쉬운 사용", "기기 제어 및 데이터 접근"]
        case .screenCapture: return ["Screen Recording", "Screen & System Audio Recording", "Screen and System Audio Recording", "화면 기록", "화면 녹화", "화면 및 시스템 오디오 녹음", "화면 및 시스템 오디오 기록"]
        case .inputMonitoring: return ["Input Monitoring", "입력 모니터링"]
        case .automation: return ["Automation", "자동화"]
        case .fullDiskAccess: return ["Full Disk Access", "전체 디스크 접근", "전체 디스크 접근 권한"]
        case .files: return ["Files and Folders", "Files & Folders", "파일 및 폴더"]
        case .clipboard: return ["Paste from Other Apps", "Clipboard", "다른 앱에서 붙여넣기", "클립보드"]
        }
    }
    var label: String {
        switch self {
        case .accessibility: return "기기 제어 · 접근성"
        case .screenCapture: return "화면 · 시스템 오디오"
        case .postEvent: return "키보드 · 마우스 전송"
        case .inputMonitoring: return "입력 모니터링 (선택)"
        case .automation: return "앱별 Automation"
        case .fullDiskAccess: return "전체 디스크 접근 (선택)"
        case .files: return "파일 및 폴더"
        case .clipboard: return "다른 앱에서 붙여넣기"
        }
    }
    var systemRequest: Bool { [.accessibility, .screenCapture, .postEvent, .inputMonitoring].contains(self) }
    var acceptsAppDrop: Bool { [.accessibility, .screenCapture, .postEvent, .inputMonitoring, .fullDiskAccess].contains(self) }
    static func plan(_ raw: String) throws -> [Self] {
        if raw == "all" { return [.accessibility, .screenCapture, .automation] }
        guard let kind = Self(rawValue: raw) else { throw ToolFailure("invalid_argument", "Unknown permission kind") }
        return [kind]
    }
}

enum NativePermissionPrompt: String {
    case none, authenticationRequired = "authentication_required", restartRequired = "restart_required", confirmationRequired = "native_confirmation_required"
    static func classify(buttons: [String], hasSecureInput: Bool, hasSheet: Bool) -> Self {
        if buttons.contains(where: { ["Quit & Reopen", "Quit and Reopen", "종료 및 다시 열기", "종료 후 다시 열기"].contains($0) }) { return .restartRequired }
        if hasSecureInput { return .authenticationRequired }
        return hasSheet ? .confirmationRequired : .none
    }
}

enum PermissionCenter {
    static func automation(bundleID: String, request: Bool, timeout: Int) async throws -> PermissionState {
        // Apple's API is thread-safe and must not block the main thread.
        let result = try await withBlockingDeadline(timeoutMilliseconds: timeout,
            timeoutFailure: ToolFailure("permission_timeout", "Automation request timed out; the native prompt may still be open. Recheck before retrying.")) {
            let target = NSAppleEventDescriptor(bundleIdentifier: bundleID)
            return AEDeterminePermissionToAutomateTarget(target.aeDesc, AEEventClass(typeWildCard), AEEventID(typeWildCard), request)
        }
        return PermissionState.automation(result)
    }
}
