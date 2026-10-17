import AppKit
import ApplicationServices
import Darwin
import Foundation

public struct CommandOutput: Sendable {
    public let exitCode: Int32
    public let stdout: String
    public let stderr: String
    public let stdoutBytes: Int
    public let stderrBytes: Int
    public let stdoutTruncated: Bool
    public let stderrTruncated: Bool

    public var object: [String: Any] {
        var result: [String: Any] = [
            "exitCode": exitCode,
            "stdout": stdout,
            "stdoutBytes": stdoutBytes,
            "stdoutTruncated": stdoutTruncated,
            "stderrBytes": stderrBytes,
            "stderrTruncated": stderrTruncated
        ]
        if !stderr.isEmpty { result["stderr"] = stderr }
        return result
    }
}

private struct StreamCapture: Sendable {
    let data: Data
    let totalBytes: Int
    let readError: String?
    var truncated: Bool { totalBytes > data.count }
}

private final class CaptureSlot: @unchecked Sendable {
    private let lock = NSLock()
    private var value: StreamCapture?

    func set(_ value: StreamCapture) {
        lock.lock(); defer { lock.unlock() }
        self.value = value
    }

    func get() -> StreamCapture? {
        lock.lock(); defer { lock.unlock() }
        return value
    }
}

private final class ProcessCancellationControl: @unchecked Sendable {
    private let lock = NSLock()
    private var process: Process?
    private var cancelled = false

    var isCancelled: Bool {
        lock.lock(); defer { lock.unlock() }
        return cancelled
    }

    @discardableResult func register(_ process: Process) -> Bool {
        lock.lock()
        self.process = process
        let shouldRun = !cancelled
        lock.unlock()
        if !shouldRun, process.isRunning { process.terminate() }
        return shouldRun
    }

    func cancel() {
        lock.lock()
        cancelled = true
        let current = process
        lock.unlock()
        if current?.isRunning == true { current?.terminate() }
    }
}

enum CommandRunner {
    static func timeoutDescription(executableName: String, timeoutMilliseconds: Int) -> String {
        "\(executableName) exceeded timeoutMs=\(timeoutMilliseconds). The wrapper process was terminated, but already-started Apple Events, Shortcut service work, or other external side effects may continue. Reconcile target state before retrying."
    }

    static func run(
        executable: URL,
        arguments: [String],
        standardInput: String? = nil,
        timeoutMilliseconds: Int,
        maxOutputBytes: Int
    ) async throws -> CommandOutput {
        guard executable.isFileURL, executable.path.hasPrefix("/"), FileManager.default.isExecutableFile(atPath: executable.path) else {
            throw ToolFailure("executable_unavailable", "Required executable is unavailable: \(executable.path)")
        }
        guard (100...60_000).contains(timeoutMilliseconds) else {
            throw ToolFailure("invalid_argument", "timeoutMs must be between 100 and 60000")
        }
        guard (1...1_048_576).contains(maxOutputBytes) else {
            throw ToolFailure("invalid_argument", "maxOutputBytes must be between 1 and 1048576")
        }
        guard standardInput?.utf8.count ?? 0 <= 131_072 else {
            throw ToolFailure("invalid_argument", "Process input exceeds 131072 UTF-8 bytes")
        }

        let cancellation = ProcessCancellationControl()
        return try await withTaskCancellationHandler {
            try Task.checkCancellation()
            return try await Task.detached(priority: .userInitiated) {
                try execute(
                    executable: executable,
                    arguments: arguments,
                    standardInput: standardInput,
                    timeoutMilliseconds: timeoutMilliseconds,
                    maxOutputBytes: maxOutputBytes,
                    cancellation: cancellation
                )
            }.value
        } onCancel: {
            cancellation.cancel()
        }
    }

    private static func execute(
        executable: URL,
        arguments: [String],
        standardInput: String?,
        timeoutMilliseconds: Int,
        maxOutputBytes: Int,
        cancellation: ProcessCancellationControl
    ) throws -> CommandOutput {
        if cancellation.isCancelled { throw CancellationError() }
        let process = Process()
        let stdoutPipe = Pipe(), stderrPipe = Pipe()
        let inputPipe = standardInput == nil ? nil : Pipe()
        process.executableURL = executable
        process.arguments = arguments
        process.standardOutput = stdoutPipe
        process.standardError = stderrPipe
        process.standardInput = inputPipe ?? FileHandle.nullDevice

        var environment: [String: String] = [
            "HOME": FileManager.default.homeDirectoryForCurrentUser.path,
            "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
            "TMPDIR": NSTemporaryDirectory()
        ]
        for key in ["LANG", "LC_ALL", "__CF_USER_TEXT_ENCODING"] {
            if let value = ProcessInfo.processInfo.environment[key], value.utf8.count <= 1024 {
                environment[key] = value
            }
        }
        process.environment = environment

        let inputData = standardInput.map { Data($0.utf8) }
        var inputHandle = inputPipe?.fileHandleForWriting
        var inputFD = inputHandle?.fileDescriptor
        if let fd = inputFD {
            let flags = fcntl(fd, F_GETFL)
            guard flags >= 0,
                  fcntl(fd, F_SETFL, flags | O_NONBLOCK) >= 0,
                  fcntl(fd, F_SETNOSIGPIPE, 1) >= 0 else {
                throw ToolFailure("process_input_failed", "Cannot configure bounded nonblocking process input")
            }
        }

        do { try process.run() }
        catch { throw ToolFailure("process_launch_failed", "Cannot launch \(executable.lastPathComponent): \(error.localizedDescription)") }
        _ = cancellation.register(process)

        let group = DispatchGroup()
        let stdoutSlot = CaptureSlot(), stderrSlot = CaptureSlot()
        group.enter()
        DispatchQueue.global(qos: .userInitiated).async {
            stdoutSlot.set(drain(stdoutPipe.fileHandleForReading, limit: maxOutputBytes))
            group.leave()
        }
        group.enter()
        DispatchQueue.global(qos: .userInitiated).async {
            stderrSlot.set(drain(stderrPipe.fileHandleForReading, limit: maxOutputBytes))
            group.leave()
        }

        let deadline = DispatchTime.now().uptimeNanoseconds + UInt64(timeoutMilliseconds) * 1_000_000
        var inputOffset = 0
        var inputFailure: String?
        if inputData?.isEmpty == true {
            try? inputHandle?.close()
            inputHandle = nil
            inputFD = nil
        }
        while process.isRunning, DispatchTime.now().uptimeNanoseconds < deadline,
              inputFailure == nil, !cancellation.isCancelled {
            if let data = inputData, inputOffset < data.count, let fd = inputFD {
                let written = data.withUnsafeBytes { buffer -> Int in
                    guard let base = buffer.baseAddress else { return 0 }
                    return Darwin.write(fd, base.advanced(by: inputOffset), data.count - inputOffset)
                }
                if written > 0 {
                    inputOffset += written
                    if inputOffset == data.count {
                        try? inputHandle?.close()
                        inputHandle = nil
                        inputFD = nil
                    }
                } else if written < 0, errno != EAGAIN, errno != EWOULDBLOCK, errno != EINTR {
                    inputFailure = String(cString: strerror(errno))
                }
            }
            usleep(10_000)
        }
        let cancelled = cancellation.isCancelled
        let timedOut = process.isRunning && inputFailure == nil
        try? inputHandle?.close()
        inputHandle = nil
        inputFD = nil
        if process.isRunning, timedOut || inputFailure != nil || cancelled {
            process.terminate()
            let grace = DispatchTime.now().uptimeNanoseconds + 250_000_000
            while process.isRunning, DispatchTime.now().uptimeNanoseconds < grace { usleep(10_000) }
            if process.isRunning { Darwin.kill(process.processIdentifier, SIGKILL) }
        }
        process.waitUntilExit()
        if cancelled { throw CancellationError() }
        let drainResult = group.wait(timeout: .now() + 2)
        if timedOut {
            throw ToolFailure(
                "process_timeout",
                timeoutDescription(executableName: executable.lastPathComponent, timeoutMilliseconds: timeoutMilliseconds)
            )
        }
        if let inputFailure {
            throw ToolFailure(
                "process_input_failed",
                "Cannot deliver complete process input: \(inputFailure). The wrapper may already have started external work; reconcile target state before retrying."
            )
        }
        if let inputData, inputOffset < inputData.count {
            throw ToolFailure(
                "process_input_failed",
                "The wrapper exited before accepting complete process input. It may already have started external work; reconcile target state before retrying."
            )
        }
        guard drainResult == .success,
              let stdoutCapture = stdoutSlot.get(), let stderrCapture = stderrSlot.get() else {
            throw ToolFailure("process_output_failed", "Timed out while draining process output")
        }
        if let error = stdoutCapture.readError ?? stderrCapture.readError {
            throw ToolFailure("process_output_failed", "Cannot read process output: \(error)")
        }
        return CommandOutput(
            exitCode: process.terminationStatus,
            stdout: String(decoding: stdoutCapture.data, as: UTF8.self),
            stderr: String(decoding: stderrCapture.data, as: UTF8.self),
            stdoutBytes: stdoutCapture.totalBytes,
            stderrBytes: stderrCapture.totalBytes,
            stdoutTruncated: stdoutCapture.truncated,
            stderrTruncated: stderrCapture.truncated
        )
    }

    private static func drain(_ handle: FileHandle, limit: Int) -> StreamCapture {
        var kept = Data(), total = 0
        do {
            while let chunk = try handle.read(upToCount: 8192), !chunk.isEmpty {
                total = total > Int.max - chunk.count ? Int.max : total + chunk.count
                if kept.count < limit { kept.append(chunk.prefix(limit - kept.count)) }
            }
            return StreamCapture(data: kept, totalBytes: total, readError: nil)
        } catch {
            return StreamCapture(data: kept, totalBytes: total, readError: error.localizedDescription)
        }
    }
}

private struct TrashRecycleOutcome: @unchecked Sendable {
    let destinations: [URL: URL]
    let errorDescription: String?
}

@MainActor public enum SystemActions {
    private static let shortcutsURL = URL(fileURLWithPath: "/usr/bin/shortcuts")
    private static let osascriptURL = URL(fileURLWithPath: "/usr/bin/osascript")

    static func trashTimeoutDescription(timeoutMilliseconds: Int) -> String {
        "NSWorkspace.recycle did not finish within \(timeoutMilliseconds) ms. The system recycle operation may still complete after this timeout; reconcile every requested source and Trash state before retrying."
    }

    public static func app(_ a: Arguments) async throws -> [String: Any] {
        try a.only(["pid", "processStartID", "action", "timeoutMs"])
        let pid = Int32(try a.integer("pid", range: 1...Int(Int32.max)))
        let processStartID = try a.string("processStartID", limit: 64)
        try ProcessIdentity.require(pid: pid, expected: processStartID)
        let action = try a.string("action", limit: 32)
        let timeout = try a.integer("timeoutMs", default: 3_000, range: 100...10_000)
        guard let application = NSRunningApplication(processIdentifier: pid), !application.isTerminated else {
            throw ToolFailure("app_unavailable", "Target PID is not running")
        }
        guard pid != ProcessInfo.processInfo.processIdentifier else {
            throw ToolFailure("self_target", "MacPilot cannot change its own application lifecycle")
        }

        let matches: () -> Bool
        let accepted: Bool
        switch action {
        case "activate":
            matches = { application.isActive }
            if matches() {
                accepted = true
            } else {
                try ProcessIdentity.require(pid: pid, expected: processStartID)
                accepted = application.activate(options: [])
            }
        case "hide":
            matches = { application.isHidden }
            if matches() {
                accepted = true
            } else {
                try ProcessIdentity.require(pid: pid, expected: processStartID)
                if application.hide() {
                    accepted = true
                } else {
                    try ProcessIdentity.require(pid: pid, expected: processStartID)
                    try AX.set(AX.app(pid), kAXHiddenAttribute, kCFBooleanTrue)
                    accepted = true
                }
            }
        case "unhide":
            matches = { !application.isHidden && !application.isTerminated }
            if matches() {
                accepted = true
            } else {
                try ProcessIdentity.require(pid: pid, expected: processStartID)
                if application.unhide() {
                    accepted = true
                } else {
                    try ProcessIdentity.require(pid: pid, expected: processStartID)
                    try AX.set(AX.app(pid), kAXHiddenAttribute, kCFBooleanFalse)
                    accepted = true
                }
            }
        case "terminate":
            matches = { application.isTerminated || NSRunningApplication(processIdentifier: pid) == nil }
            if matches() {
                accepted = true
            } else {
                try ProcessIdentity.require(pid: pid, expected: processStartID)
                accepted = application.terminate()
            }
        case "force_terminate":
            matches = { application.isTerminated || NSRunningApplication(processIdentifier: pid) == nil }
            if matches() {
                accepted = true
            } else {
                try ProcessIdentity.require(pid: pid, expected: processStartID)
                accepted = application.forceTerminate()
            }
        default:
            throw ToolFailure("invalid_argument", "action must be activate, hide, unhide, terminate, or force_terminate")
        }
        guard accepted else { throw ToolFailure("app_action_rejected", "The target application rejected \(action)") }
        guard try await wait(timeoutMilliseconds: timeout, predicate: matches) else {
            throw ToolFailure("verification_timeout", "The \(action) request was accepted, but its postcondition was not observed within \(timeout) ms")
        }
        return ["status":"app_state_verified", "pid":pid, "action":action,
                "active":application.isActive, "hidden":application.isHidden, "terminated":application.isTerminated]
    }

    public static func open(_ a: Arguments) async throws -> [String: Any] {
        try a.only(["url", "bundleID", "activate", "timeoutMs"])
        let url = try validatedOpenURL(a.string("url", limit: 8_192))
        let activate = try a.bool("activate", default: true)
        let timeout = try a.integer("timeoutMs", default: 10_000, range: 100...60_000)
        let configuration = NSWorkspace.OpenConfiguration()
        configuration.activates = activate
        let applicationURL: URL?
        if a.values["bundleID"] != nil {
            let bundleID = try boundedName(a.string("bundleID", limit: 256), field: "bundleID", allowLeadingDash: true)
            guard let resolved = NSWorkspace.shared.urlForApplication(withBundleIdentifier: bundleID) else {
                throw ToolFailure("app_unavailable", "Installed bundle not found")
            }
            applicationURL = resolved
        } else {
            applicationURL = nil
        }
        let application: NSRunningApplication = try await withCallbackDeadline(
            timeoutMilliseconds: timeout,
            timeoutFailure: ToolFailure("workspace_timeout", "NSWorkspace open did not return within \(timeout) ms. The URL or file request may still complete; reconcile target state before retrying.")
        ) { finish in
            let complete: @Sendable (NSRunningApplication?, Error?) -> Void = { application, error in
                if let application { finish(.success(application)) }
                else { finish(.failure(error ?? ToolFailure("open_failed", "NSWorkspace returned no application for the open request"))) }
            }
            if let applicationURL {
                NSWorkspace.shared.open([url], withApplicationAt: applicationURL, configuration: configuration, completionHandler: complete)
            } else {
                NSWorkspace.shared.open(url, configuration: configuration, completionHandler: complete)
            }
        }
        return ["status":"open_accepted", "scheme":url.scheme ?? "", "pid":application.processIdentifier,
                "bundleID":application.bundleIdentifier ?? "", "activate":activate]
    }

    public static func reveal(_ a: Arguments) async throws -> [String: Any] {
        try a.only(["paths", "timeoutMs"])
        let urls = try explicitFileURLs(a.values["paths"], key: "paths", mustExist: true, rejectRoot: false)
        let timeout = try a.integer("timeoutMs", default: 10_000, range: 100...60_000)
        let _: Void = try await withBlockingDeadline(
            timeoutMilliseconds: timeout,
            timeoutFailure: ToolFailure("workspace_timeout", "Finder reveal did not return within \(timeout) ms. The reveal may still complete; reconcile Finder state before retrying.")
        ) {
            NSWorkspace.shared.activateFileViewerSelecting(urls)
        }
        return ["status":"reveal_requested", "count":urls.count]
    }

    public static func permission(_ a: Arguments) async throws -> [String: Any] {
        try a.only(["kind", "operation", "timeoutMs", "targetBundleID"])
        let kind = try a.string("kind")
        let timeout = try a.integer("timeoutMs", default: 10_000, range: 100...60_000)
        let operation = try a.string("operation", default: "request")
        let target = try a.string("targetBundleID", default: "com.apple.Safari", limit: 255)
        guard !target.isEmpty, target.allSatisfy({ $0.isASCII && ($0.isLetter || $0.isNumber || $0 == "." || $0 == "-") }) else {
            throw ToolFailure("invalid_argument", "targetBundleID must be an installed app bundle identifier")
        }
        if operation == "setup" { return try await PermissionSetup.open(kind: kind, timeout: timeout, targetBundleID: target) }
        guard a.values["targetBundleID"] == nil else { throw ToolFailure("invalid_argument", "targetBundleID is used only by setup") }
        guard operation == "request" else { throw ToolFailure("invalid_argument", "Permission operation must be request or setup") }
        let granted: Bool
        switch kind {
        case "accessibility":
            granted = AXIsProcessTrustedWithOptions([
                kAXTrustedCheckOptionPrompt.takeUnretainedValue() as String:true
            ] as CFDictionary)
        case "screenCapture":
            granted = try await withBlockingDeadline(
                timeoutMilliseconds: timeout,
                timeoutFailure: ToolFailure("permission_timeout", "Screen Recording permission request did not return within \(timeout) ms. The system request may still complete; recheck mac_doctor before retrying.")
            ) { CGRequestScreenCaptureAccess() }
        case "postEvent":
            granted = try await withBlockingDeadline(
                timeoutMilliseconds: timeout,
                timeoutFailure: ToolFailure("permission_timeout", "Post Event permission request did not return within \(timeout) ms. The system request may still complete; recheck mac_doctor before retrying.")
            ) { CGRequestPostEventAccess() }
        case "inputMonitoring":
            granted = try await withBlockingDeadline(
                timeoutMilliseconds: timeout,
                timeoutFailure: ToolFailure("permission_timeout", "Input Monitoring request timed out; recheck before retrying.")
            ) { CGRequestListenEventAccess() }
        default:
            throw ToolFailure("invalid_argument", "Request kind must be accessibility, screenCapture, postEvent, or inputMonitoring; other kinds use operation=setup")
        }
        return ["status":"permission_requested", "granted":granted]
    }

    public static func trash(_ a: Arguments) async throws -> [String: Any] {
        try a.only(["paths", "timeoutMs"])
        let urls = try explicitFileURLs(a.values["paths"], key: "paths", mustExist: true, rejectRoot: true)
        let timeout = try a.integer("timeoutMs", default: 30_000, range: 100...60_000)
        let outcome: TrashRecycleOutcome = try await withCallbackDeadline(
            timeoutMilliseconds: timeout,
            timeoutFailure: ToolFailure("trash_timeout", trashTimeoutDescription(timeoutMilliseconds: timeout))
        ) { finish in
            NSWorkspace.shared.recycle(urls) { destinations, error in
                finish(.success(TrashRecycleOutcome(
                    destinations: destinations,
                    errorDescription: error?.localizedDescription
                )))
            }
        }
        return trashResult(sources: urls, destinations: outcome.destinations, errorDescription: outcome.errorDescription)
    }

    static func trashResult(sources: [URL], destinations: [URL: URL], errorDescription: String?) -> [String: Any] {
        let requested = Set(sources)
        var items = sources.compactMap { source in
            destinations[source].map { ["source":source.path, "destination":$0.path] }
        }
        items.append(contentsOf: destinations
            .filter { !requested.contains($0.key) }
            .sorted { $0.key.path < $1.key.path }
            .map { ["source":$0.key.path, "destination":$0.value.path] })

        let uncertainSources = sources.filter { destinations[$0] == nil }.map(\.path)
        guard errorDescription == nil, uncertainSources.isEmpty, destinations.count == sources.count else {
            let code = errorDescription == nil ? "trash_incomplete" : "trash_failed"
            let detail: String
            if let errorDescription {
                detail = "NSWorkspace.recycle returned \(destinations.count) known source-to-destination mapping(s) for \(sources.count) requested item(s): \(errorDescription)"
            } else {
                detail = "NSWorkspace.recycle returned \(destinations.count) known source-to-destination mapping(s) for \(sources.count) requested item(s) without an error."
            }
            return [
                "status":"trash_incomplete", "count":destinations.count, "requestedCount":sources.count,
                "items":items, "complete":false, "uncertain":true, "uncertainSources":uncertainSources,
                "error":["code":code, "message":detail],
                "verification":"Reconcile every requested source and Trash destination before retrying uncertain items."
            ]
        }
        return ["status":"trashed", "count":destinations.count, "items":items]
    }

    public static func clipboardRead(_ a: Arguments) throws -> [String: Any] {
        try a.only(["maxBytes"])
        let limit = try a.integer("maxBytes", default: 65_536, range: 1...1_048_576)
        guard let value = NSPasteboard.general.string(forType: .string) else {
            throw ToolFailure("clipboard_type_unavailable", "The general clipboard has no plain-text value")
        }
        let data = Data(value.utf8), truncated = data.count > limit
        var prefix = Data(data.prefix(limit))
        while String(data: prefix, encoding: .utf8) == nil, !prefix.isEmpty { prefix.removeLast() }
        return ["status":"clipboard_read", "text":String(data:prefix,encoding:.utf8) ?? "", "bytes":data.count,
                "truncated":truncated, "changeCount":NSPasteboard.general.changeCount]
    }

    public static func clipboardWrite(_ a: Arguments) throws -> [String: Any] {
        try a.only(["text"])
        let text = try a.string("text", limit: 1_048_576)
        let pasteboard = NSPasteboard.general
        pasteboard.clearContents()
        guard pasteboard.setString(text, forType: .string), pasteboard.string(forType:.string) == text else {
            throw ToolFailure("clipboard_write_failed", "The clipboard did not retain the requested plain text")
        }
        return ["status":"clipboard_write_verified", "bytes":text.utf8.count, "changeCount":pasteboard.changeCount]
    }

    public static func shortcuts(_ a: Arguments) async throws -> [String: Any] {
        let operation = try a.string("operation", limit: 16)
        switch operation {
        case "list":
            try a.only(["operation", "folder", "folders", "showIdentifiers", "timeoutMs", "maxOutputBytes"])
        case "run":
            try a.only(["operation", "name", "inputPaths", "outputPath", "outputType", "timeoutMs", "maxOutputBytes"])
        case "view":
            try a.only(["operation", "name", "timeoutMs", "maxOutputBytes"])
        default:
            throw ToolFailure("invalid_argument", "operation must be list, run, or view")
        }
        let arguments = try shortcutArguments(a, operation: operation)
        let timeout = try a.integer("timeoutMs", default: 30_000, range: 100...60_000)
        let maxOutput = try a.integer("maxOutputBytes", default: 65_536, range: 1...1_048_576)
        let output = try await CommandRunner.run(executable: shortcutsURL, arguments: arguments,
                                                 timeoutMilliseconds: timeout, maxOutputBytes: maxOutput)
        try requireSuccess(output, command: "shortcuts \(operation)")
        var result = output.object
        result["status"] = "shortcut_completed"
        result["operation"] = operation
        return result
    }

    public static func script(_ a: Arguments) async throws -> [String: Any] {
        try a.only(["language", "source", "timeoutMs", "maxOutputBytes"])
        let language = try a.string("language", limit: 16)
        let nativeLanguage = try scriptLanguage(language)
        let source = try a.string("source", limit: 131_072)
        guard !source.isEmpty, !source.contains("\0") else {
            throw ToolFailure("invalid_argument", "source must be nonempty and contain no NUL")
        }
        let timeout = try a.integer("timeoutMs", default: 10_000, range: 100...60_000)
        let maxOutput = try a.integer("maxOutputBytes", default: 65_536, range: 1...1_048_576)
        let output = try await CommandRunner.run(executable: osascriptURL, arguments: ["-l",nativeLanguage],
                                                 standardInput:source, timeoutMilliseconds:timeout, maxOutputBytes:maxOutput)
        try requireSuccess(output, command: "osascript")
        var result = output.object
        result["status"] = "script_completed"
        result["language"] = language
        return result
    }

    static func validatedOpenURL(_ raw: String) throws -> URL {
        guard !raw.isEmpty, !raw.contains("\0"), let parsed = URL(string: raw), let scheme = parsed.scheme?.lowercased() else {
            throw ToolFailure("invalid_url", "url must be an absolute file, http, or https URL")
        }
        switch scheme {
        case "file":
            guard parsed.isFileURL, parsed.host == nil || parsed.host == "" || parsed.host == "localhost" else {
                throw ToolFailure("invalid_url", "Only local file URLs are supported")
            }
            let url = parsed.standardizedFileURL
            guard url.path.hasPrefix("/"), FileManager.default.fileExists(atPath:url.path) else {
                throw ToolFailure("file_unavailable", "The file URL does not identify an existing local item")
            }
            return url
        case "http", "https":
            guard let host = parsed.host, !host.isEmpty else { throw ToolFailure("invalid_url", "Web URL requires a host") }
            return parsed
        default:
            throw ToolFailure("invalid_url", "url scheme must be file, http, or https")
        }
    }

    static func explicitFileURLs(_ raw: Any?, key: String, mustExist: Bool, rejectRoot: Bool) throws -> [URL] {
        guard let paths = raw as? [String], (1...16).contains(paths.count) else {
            throw ToolFailure("invalid_argument", "\(key) must contain 1 to 16 path strings")
        }
        var urls: [URL] = [], seen = Set<String>(), total = 0
        for path in paths {
            total += path.utf8.count
            guard !path.isEmpty, path.utf8.count <= 4_096, total <= 32_768, !path.contains("\0"), path.hasPrefix("/") else {
                throw ToolFailure("invalid_argument", "Each \(key) entry must be an absolute path of at most 4096 UTF-8 bytes")
            }
            let url = URL(fileURLWithPath:path).standardizedFileURL
            guard !rejectRoot || url.path != "/" else { throw ToolFailure("invalid_argument", "The filesystem root cannot be moved to Trash") }
            guard !mustExist || FileManager.default.fileExists(atPath:url.path) else {
                throw ToolFailure("file_unavailable", "A requested path does not exist")
            }
            guard seen.insert(url.path).inserted else { throw ToolFailure("invalid_argument", "Duplicate paths are not allowed") }
            urls.append(url)
        }
        return urls
    }

    static func shortcutArguments(_ a: Arguments, operation: String) throws -> [String] {
        switch operation {
        case "list":
            guard a.values["name"] == nil, a.values["inputPaths"] == nil, a.values["outputPath"] == nil, a.values["outputType"] == nil else {
                throw ToolFailure("invalid_argument", "list does not accept name, inputPaths, outputPath, or outputType")
            }
            var result = ["list"]
            if a.values["folder"] != nil {
                let folder = try boundedName(a.string("folder", limit:1_024), field:"folder")
                guard try a.bool("folders") == false else { throw ToolFailure("invalid_argument", "folder and folders cannot be combined") }
                result += ["--folder-name",folder]
            }
            if try a.bool("folders") { result.append("--folders") }
            if try a.bool("showIdentifiers") { result.append("--show-identifiers") }
            return result
        case "run":
            guard a.values["folder"] == nil, a.values["folders"] == nil, a.values["showIdentifiers"] == nil else {
                throw ToolFailure("invalid_argument", "run does not accept folder, folders, or showIdentifiers")
            }
            let name = try boundedName(a.string("name", limit:1_024), field:"name")
            var result = ["run",name]
            if a.values["inputPaths"] != nil {
                for url in try explicitFileURLs(a.values["inputPaths"], key:"inputPaths", mustExist:true, rejectRoot:false) {
                    result += ["--input-path",url.path]
                }
            }
            if a.values["outputPath"] != nil {
                let raw = try a.string("outputPath", limit:4_096)
                guard raw.hasPrefix("/"), !raw.contains("\0") else { throw ToolFailure("invalid_argument", "outputPath must be absolute") }
                let output = URL(fileURLWithPath:raw).standardizedFileURL
                var isDirectory: ObjCBool = false
                guard FileManager.default.fileExists(atPath:output.deletingLastPathComponent().path,isDirectory:&isDirectory), isDirectory.boolValue else {
                    throw ToolFailure("file_unavailable", "outputPath parent directory does not exist")
                }
                result += ["--output-path",output.path]
            }
            if a.values["outputType"] != nil {
                let type = try a.string("outputType", limit:256)
                let allowed = CharacterSet(charactersIn:"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-")
                guard !type.isEmpty, type.unicodeScalars.allSatisfy(allowed.contains) else { throw ToolFailure("invalid_argument", "outputType must be a UTI") }
                result += ["--output-type",type]
            }
            return result
        case "view":
            guard a.values["folder"] == nil, a.values["folders"] == nil, a.values["showIdentifiers"] == nil,
                  a.values["inputPaths"] == nil, a.values["outputPath"] == nil, a.values["outputType"] == nil else {
                throw ToolFailure("invalid_argument", "view accepts only name and execution limits")
            }
            return ["view",try boundedName(a.string("name", limit:1_024), field:"name")]
        default:
            throw ToolFailure("invalid_argument", "operation must be list, run, or view")
        }
    }

    static func scriptLanguage(_ language: String) throws -> String {
        switch language {
        case "applescript": return "AppleScript"
        case "javascript": return "JavaScript"
        default: throw ToolFailure("invalid_argument", "language must be applescript or javascript")
        }
    }

    private static func boundedName(_ value: String, field: String, allowLeadingDash: Bool = false) throws -> String {
        guard !value.isEmpty, !value.contains("\0"), allowLeadingDash || !value.hasPrefix("-") else {
            throw ToolFailure("invalid_argument", "\(field) is empty or could be parsed as an option")
        }
        return value
    }

    private static func wait(timeoutMilliseconds: Int, predicate: @escaping () -> Bool) async throws -> Bool {
        let deadline = DispatchTime.now().uptimeNanoseconds + UInt64(timeoutMilliseconds) * 1_000_000
        repeat {
            try Task.checkCancellation()
            if predicate() { return true }
            try await Task.sleep(nanoseconds: 50_000_000)
        } while DispatchTime.now().uptimeNanoseconds < deadline
        try Task.checkCancellation()
        return predicate()
    }

    private static func requireSuccess(_ output: CommandOutput, command: String) throws {
        guard output.exitCode == 0 else {
            var diagnostic = output.stderr.trimmingCharacters(in:.whitespacesAndNewlines)
            if diagnostic.isEmpty { diagnostic = output.stdout.trimmingCharacters(in:.whitespacesAndNewlines) }
            if diagnostic.utf8.count > 2_048 { diagnostic = String(decoding:Data(diagnostic.utf8).prefix(2_048),as:UTF8.self) + "…" }
            throw ToolFailure("command_failed", diagnostic.isEmpty ? "\(command) exited with status \(output.exitCode)" : "\(command) exited with status \(output.exitCode): \(diagnostic)")
        }
    }
}
