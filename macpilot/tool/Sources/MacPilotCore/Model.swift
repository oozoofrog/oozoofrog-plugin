import Foundation
import CoreGraphics
import CryptoKit
import Darwin
import ImageIO
import UniformTypeIdentifiers

public struct ToolFailure: Error, LocalizedError, CustomStringConvertible, Sendable {
    public let code: String
    public let description: String
    public var errorDescription: String? { description }
    public let improvementRequestID: String?
    public init(_ code: String, _ description: String, improvementRequestID: String? = nil) {
        self.code = code; self.description = description; self.improvementRequestID = improvementRequestID
    }
}

@usableFromInline enum ImageSafety {
    @usableFromInline static let maximumDimension = 8_192
    @usableFromInline static let maximumPixels = 16_777_216
    static let maximumBitsPerComponent = 16
    static let maximumBitsPerPixel = 64
    @usableFromInline static let maximumDecodedBytes = 67_108_864
    @usableFromInline static let maximumEncodedPNGBytes = 67_108_864

    @discardableResult static func validateDecoded(
        _ image: CGImage,
        maximumDimension: Int = ImageSafety.maximumDimension,
        maximumPixels: Int = ImageSafety.maximumPixels,
        maximumDecodedBytes: Int = ImageSafety.maximumDecodedBytes,
        failureCode: String,
        description: String
    ) throws -> CGImage {
        guard maximumDimension > 0, maximumPixels > 0, maximumDecodedBytes > 0 else {
            throw ToolFailure("invalid_argument", "Image safety limits must be positive")
        }
        let width = image.width
        let height = image.height
        let bitsPerComponent = image.bitsPerComponent
        let bitsPerPixel = image.bitsPerPixel
        let bytesPerRow = image.bytesPerRow
        guard width > 0, height > 0,
              width <= maximumDimension, height <= maximumDimension,
              width <= maximumPixels / height,
              bitsPerComponent > 0, bitsPerComponent <= maximumBitsPerComponent,
              bitsPerPixel >= bitsPerComponent, bitsPerPixel <= maximumBitsPerPixel,
              bytesPerRow > 0 else {
            throw ToolFailure(failureCode, description)
        }
        let (rowBits, rowBitsOverflow) = width.multipliedReportingOverflow(by: bitsPerPixel)
        let (roundedRowBits, roundingOverflow) = rowBits.addingReportingOverflow(7)
        guard !rowBitsOverflow, !roundingOverflow,
              bytesPerRow >= roundedRowBits / 8,
              bytesPerRow <= maximumDecodedBytes / height else {
            throw ToolFailure(failureCode, description)
        }
        return image
    }
}

final class CallbackCompletion<Value>: @unchecked Sendable {
    // startIfUnfinished deliberately keeps this recursive lock while invoking
    // the callback-registration closure. A synchronous framework callback can
    // therefore finish on the same thread, while cancellation cannot win the
    // completion race and then launch the operation afterward.
    private let lock = NSRecursiveLock()
    private var continuation: CheckedContinuation<Value, Error>?
    private var pendingResult: Result<Value, Error>?
    private var finished = false

    @discardableResult func install(_ continuation: CheckedContinuation<Value, Error>) -> Bool {
        lock.lock()
        if finished {
            let result = pendingResult
            pendingResult = nil
            lock.unlock()
            continuation.resume(with: result!)
            return false
        }
        self.continuation = continuation
        lock.unlock()
        return true
    }

    @discardableResult func finish(_ result: Result<Value, Error>) -> Bool {
        lock.lock()
        guard !finished else { lock.unlock(); return false }
        finished = true
        let current = continuation
        continuation = nil
        if current == nil { pendingResult = result }
        lock.unlock()
        current?.resume(with: result)
        return true
    }

    @discardableResult func startIfUnfinished(_ operation: () -> Void) -> Bool {
        lock.lock()
        guard !finished else { lock.unlock(); return false }
        operation()
        lock.unlock()
        return true
    }
}

func withCallbackDeadline<Value>(
    timeoutMilliseconds: Int,
    timeoutFailure: ToolFailure,
    onTimeout: @escaping @Sendable () -> Void = {},
    onCancel: @escaping @Sendable () -> Void = {},
    start: (@escaping @Sendable (Result<Value, Error>) -> Void) -> Void
) async throws -> Value {
    guard (1...60_000).contains(timeoutMilliseconds) else {
        throw ToolFailure("invalid_argument", "Callback timeout must be between 1 and 60000 milliseconds")
    }
    let completion = CallbackCompletion<Value>()
    return try await withTaskCancellationHandler {
        try await withCheckedThrowingContinuation { continuation in
            guard completion.install(continuation) else { return }
            if Task.isCancelled {
                if completion.finish(.failure(CancellationError())) { onCancel() }
                return
            }
            let started = completion.startIfUnfinished {
                start { result in completion.finish(result) }
            }
            if started {
                DispatchQueue.global(qos: .userInitiated).asyncAfter(deadline: .now() + .milliseconds(timeoutMilliseconds)) {
                    if completion.finish(.failure(timeoutFailure)) { onTimeout() }
                }
            }
        }
    } onCancel: {
        if completion.finish(.failure(CancellationError())) { onCancel() }
    }
}

func withBlockingDeadline<Value: Sendable>(
    timeoutMilliseconds: Int,
    timeoutFailure: ToolFailure,
    operation: @escaping @Sendable () -> Value
) async throws -> Value {
    try await withCallbackDeadline(timeoutMilliseconds: timeoutMilliseconds, timeoutFailure: timeoutFailure) { finish in
        DispatchQueue.global(qos: .userInitiated).async { finish(.success(operation())) }
    }
}

public func jsonData(_ value: Any, pretty: Bool = false) throws -> Data {
    try JSONSerialization.data(withJSONObject: value, options: pretty ? [.sortedKeys, .prettyPrinted, .fragmentsAllowed] : [.sortedKeys, .fragmentsAllowed])
}
public func jsonString(_ value: Any) -> String { (try? String(data: jsonData(value), encoding: .utf8)) ?? "null" }

public struct Rect: Codable, Equatable {
    public var x: Double, y: Double, width: Double, height: Double
    public init(_ r: CGRect) { x = r.minX; y = r.minY; width = r.width; height = r.height }
    public var cg: CGRect { CGRect(x: x, y: y, width: width, height: height) }
    public var object: [String: Double] { ["x":x, "y":y, "width":width, "height":height] }
}
public struct Node: Codable, Equatable {
    public var id: String, path: [Int], role: String, subrole: String, title: String, identifier: String
    public var value: String?, valueTruncated: Bool, enabled: Bool, secure: Bool, focused: Bool
    public var description: String? = nil, help: String? = nil, placeholder: String? = nil
    public var selected: Bool? = nil, expanded: Bool? = nil
    public var minValue: Double? = nil, maxValue: Double? = nil
    public var frame: Rect?, actions: [String]
    public var identityTruncated: Bool? = nil, actionsTruncated: Bool? = nil
    public var identity: String { jsonString([role, subrole, title, identifier]) }
}
public struct Observation: Codable {
    public var id: String, created: Date, pid: Int32, processStartID: String, launchTime: Double, bundleID: String
    public var windowID: UInt32, windowFrame: Rect, windowTitle: String, axWindowIndex: Int
    public var nodes: [Node], coverage: String, diagnostics: [String]
    public var screenshot: String?, screenshotSHA256: String?, pixelWidth: Int?, pixelHeight: Int?
    public var consumed: Bool = false
    public var windowIdentityBackend: String? = nil
    public var object: [String: Any] {
        let data = try! JSONEncoder().encode(self)
        var result = (try! JSONSerialization.jsonObject(with: data)) as! [String: Any]
        result.removeValue(forKey:"created")
        result["createdISO8601"] = ISO8601DateFormatter().string(from:created)
        result["ttlSeconds"] = 30
        return result
    }
}
public struct Pointer: Codable {
    public var windowID: UInt32, pid: Int32, x: Double, y: Double
    public var processStartID: String? = nil
    public var windowFrame: Rect? = nil
    public var cursorID: String? = nil
    public var label: String? = nil
}

public enum ProcessIdentity {
    public static func startID(pid: Int32) -> String? {
        guard pid > 0 else { return nil }
        var info = proc_bsdinfo()
        let bytes = proc_pidinfo(pid, PROC_PIDTBSDINFO, 0, &info, Int32(MemoryLayout<proc_bsdinfo>.size))
        guard bytes == Int32(MemoryLayout<proc_bsdinfo>.size), Int32(info.pbi_pid) == pid else { return nil }
        return "\(info.pbi_start_tvsec).\(info.pbi_start_tvusec)"
    }

    private static func validate(_ expected: String) throws {
        guard !expected.isEmpty, expected.utf8.count <= 64,
              expected.allSatisfy({ $0.isNumber || $0 == "." }) else {
            throw ToolFailure("invalid_argument", "processStartID must be the value returned by mac_apps")
        }
    }

    public static func require(pid: Int32, expected: String) throws {
        try validate(expected)
        guard let actual = startID(pid: pid) else {
            throw ToolFailure("app_identity_unavailable", "Cannot read the target process start identity")
        }
        guard actual == expected else {
            throw ToolFailure("stale_app_identity", "PID no longer identifies the process returned by mac_apps; list apps again")
        }
    }

    /// Runs one PID-bound operation between two process-start identity reads.
    /// The optional provider exists so the race handling can be tested without
    /// creating and recycling real processes.
    static func withStableIdentity<Value>(
        pid: Int32,
        expected: String? = nil,
        allowExpectedExit: Bool = false,
        identityProvider: (Int32) -> String? = ProcessIdentity.startID,
        operation: () throws -> Value
    ) throws -> (value: Value, processStartID: String) {
        if let expected { try validate(expected) }
        guard let before = identityProvider(pid) else {
            throw ToolFailure("app_identity_unavailable", "Cannot read the target process start identity")
        }
        if let expected, before != expected {
            throw ToolFailure("stale_app_identity", "PID no longer identifies the process returned by mac_apps; list apps again")
        }

        let result = Result { try operation() }
        let after = identityProvider(pid)
        let expectedExit = allowExpectedExit && expected != nil && after != before
        guard after == before || expectedExit else {
            throw ToolFailure("stale_app_identity", "PID changed while reading or acting on the application; list apps again")
        }
        return (try result.get(), before)
    }
}

public struct Arguments {
    public let values: [String: Any]
    public init(_ values: [String: Any]) { self.values = values }
    public func only(_ allowed: [String]) throws {
        if let key = values.keys.first(where: { !allowed.contains($0) }) { throw ToolFailure("invalid_argument", "Unknown argument: \(key)") }
    }
    public func string(_ key: String, default fallback: String? = nil, limit: Int = 65536) throws -> String {
        guard let raw = values[key] else {
            if let fallback { return fallback }; throw ToolFailure("invalid_argument", "Missing string: \(key)")
        }
        guard let value = raw as? String, value.utf8.count <= limit else { throw ToolFailure("invalid_argument", "Invalid or oversized string: \(key)") }
        return value
    }
    public func number(_ key: String, default fallback: Double? = nil, range: ClosedRange<Double> = -1e7...1e7) throws -> Double {
        guard let raw = values[key] else {
            if let fallback { return fallback }; throw ToolFailure("invalid_argument", "Missing number: \(key)")
        }
        guard let value = raw as? NSNumber, CFGetTypeID(value) != CFBooleanGetTypeID(), value.doubleValue.isFinite, range.contains(value.doubleValue) else {
            throw ToolFailure("invalid_argument", "Invalid number: \(key)")
        }
        return value.doubleValue
    }
    public func integer(_ key: String, default fallback: Int? = nil, range: ClosedRange<Int> = 0...Int(Int32.max)) throws -> Int {
        let value = try number(key, default: fallback.map(Double.init), range: Double(range.lowerBound)...Double(range.upperBound))
        guard value.rounded() == value else { throw ToolFailure("invalid_argument", "Expected integer: \(key)") }
        return Int(value)
    }
    public func bool(_ key: String, default fallback: Bool = false) throws -> Bool {
        guard let raw = values[key] else { return fallback }
        guard let value = raw as? NSNumber, CFGetTypeID(value) == CFBooleanGetTypeID() else { throw ToolFailure("invalid_argument", "Expected boolean: \(key)") }
        return value.boolValue
    }
    public func strings(_ key: String) throws -> [String] {
        guard let raw = values[key] else { return [] }
        guard let value = raw as? [String], value.count <= 8 else { throw ToolFailure("invalid_argument", "Expected short string array: \(key)") }
        return value
    }
}

/// Cubic Bézier geometry with minimum-jerk time: zero velocity/acceleration at each end.
public struct CursorTrajectory {
    public let start:CGPoint,end:CGPoint,firstControl:CGPoint,secondControl:CGPoint,duration:Double
    public init(from:CGPoint,to:CGPoint,bounds:CGRect) {
        start=from;end=to
        let dx=to.x-from.x,dy=to.y-from.y,distance=hypot(dx,dy)
        duration=min(0.65,max(0.18,Double(distance)/1200))
        let bend=min(60,distance*0.16),nx=distance>0 ? -dy/distance : 0,ny=distance>0 ? dx/distance : 0
        func clamp(_ p:CGPoint)->CGPoint{CGPoint(x:min(bounds.maxX,max(bounds.minX,p.x)),y:min(bounds.maxY,max(bounds.minY,p.y)))}
        firstControl=clamp(CGPoint(x:from.x+dx*0.25+nx*bend,y:from.y+dy*0.25+ny*bend))
        secondControl=clamp(CGPoint(x:from.x+dx*0.75+nx*bend,y:from.y+dy*0.75+ny*bend))
    }
    public func position(elapsed:Double)->CGPoint {
        let t=min(1,max(0,elapsed/duration)),u=t*t*t*(10+t*(-15+6*t)),v=1-u
        return CGPoint(x:v*v*v*start.x+3*v*v*u*firstControl.x+3*v*u*u*secondControl.x+u*u*u*end.x,
                       y:v*v*v*start.y+3*v*v*u*firstControl.y+3*v*u*u*secondControl.y+u*u*u*end.y)
    }
}

public enum Geometry {
    public static func visiblePortions(of frame:CGRect,behind occluders:[CGRect]) -> [CGRect] {
        var regions=[frame]
        for cover in occluders {
            regions=regions.flatMap { region -> [CGRect] in
                let cut=region.intersection(cover)
                guard !cut.isNull,!cut.isEmpty else{return [region]}
                return [CGRect(x:region.minX,y:region.minY,width:region.width,height:cut.minY-region.minY),
                        CGRect(x:region.minX,y:cut.maxY,width:region.width,height:region.maxY-cut.maxY),
                        CGRect(x:region.minX,y:cut.minY,width:cut.minX-region.minX,height:cut.height),
                        CGRect(x:cut.maxX,y:cut.minY,width:region.maxX-cut.maxX,height:cut.height)].filter{!$0.isEmpty}
            }
            // ponytail: cap region fragmentation; hide feedback if a desktop needs a more complex mask.
            if regions.count>256{return []}
        }
        return regions
    }
    public static func point(x: Double, y: Double, space: String, observation: Observation) throws -> CGPoint {
        guard x.isFinite, y.isFinite else { throw ToolFailure("invalid_argument", "Coordinates must be finite") }
        let frame = observation.windowFrame.cg
        let point: CGPoint
        switch space {
        case "screen": point = CGPoint(x: x, y: y)
        case "window": point = CGPoint(x: frame.minX + x, y: frame.minY + y)
        case "normalized":
            guard (0..<1).contains(x), (0..<1).contains(y) else { throw ToolFailure("invalid_argument", "Normalized coordinates must be in [0, 1)") }
            point = CGPoint(x: frame.minX + x * frame.width, y: frame.minY + y * frame.height)
        case "image":
            guard let w = observation.pixelWidth, let h = observation.pixelHeight, w > 0, h > 0 else { throw ToolFailure("missing_image", "Observe with screenshot before using image coordinates") }
            point = CGPoint(x: frame.minX + x / Double(w) * frame.width, y: frame.minY + y / Double(h) * frame.height)
        default: throw ToolFailure("invalid_argument", "space must be screen, window, normalized, or image")
        }
        guard frame.contains(point) else { throw ToolFailure("out_of_bounds", "Point is outside the observed window") }
        return point
    }
    public static func validateAge(_ observation: Observation, now: Date = Date()) throws {
        let age = now.timeIntervalSince(observation.created)
        guard age >= -1, age <= 30, !observation.consumed else { throw ToolFailure("stale_observation", "Observation expired or already used; observe again") }
    }
    public static func unicodeChunks(_ text: String, maxUTF16: Int = 20) -> [[UniChar]] {
        // Never split a Unicode scalar/surrogate pair across Quartz events.
        var chunks: [[UniChar]] = [], chunk: [UniChar] = []
        for scalar in text.unicodeScalars {
            let units = Array(String(scalar).utf16)
            if chunk.count + units.count > maxUTF16, !chunk.isEmpty { chunks.append(chunk); chunk = [] }
            chunk.append(contentsOf: units)
        }
        if !chunk.isEmpty { chunks.append(chunk) }
        return chunks
    }
}

public final class Store {
    private static let markerName = ".macpilot-state-v1"
    private static let markerContents = Data("MacPilot state directory v1\n".utf8)
    public let root: URL
    private var rootFD: Int32
    private var lockFD: Int32 = -1
    public init(root: URL? = nil) throws {
        let environment = ProcessInfo.processInfo.environment
        let configuredRoot = try Self.configuredRoot(from: environment)
        let home = FileManager.default.homeDirectoryForCurrentUser
        let defaultRoot = home.appendingPathComponent("Library/Application Support/MacPilot", isDirectory: true).standardizedFileURL
        let legacyRoot = home.appendingPathComponent("Library/Application Support/MacComputerUse", isDirectory: true).standardizedFileURL
        let requested = (root ?? configuredRoot ?? defaultRoot).standardizedFileURL
        guard requested.isFileURL, requested.path.hasPrefix("/"), requested.path != "/" else {
            throw ToolFailure("unsafe_state_directory", "State directory must be an absolute local path")
        }
        let name = requested.lastPathComponent
        guard !name.isEmpty, name != ".", name != "..", !name.contains("/") else {
            throw ToolFailure("unsafe_state_directory", "State directory has an invalid final component")
        }
        let canonicalParent = try Self.canonicalExistingDirectory(requested.deletingLastPathComponent())
        let selected = canonicalParent.appendingPathComponent(name, isDirectory: true)
        let parentFD = try Self.openValidatedAncestor(canonicalParent)
        defer { Darwin.close(parentFD) }
        var finalInfo = stat()
        let finalStatus = fstatat(parentFD, name, &finalInfo, AT_SYMLINK_NOFOLLOW)
        var created = false
        if finalStatus != 0 {
            guard errno == ENOENT else {
                throw ToolFailure("unsafe_state_directory", "Cannot inspect the MacPilot state directory")
            }
            guard mkdirat(parentFD, name, mode_t(0o700)) == 0 else {
                throw ToolFailure("state_directory_failed", "Cannot create private MacPilot state directory: \(String(cString:strerror(errno)))")
            }
            created = true
        } else {
            guard (finalInfo.st_mode & S_IFMT) == S_IFDIR else {
                throw ToolFailure("unsafe_state_directory", "The MacPilot state path is not a real directory")
            }
        }
        let directoryFD = openat(parentFD, name, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
        guard directoryFD >= 0 else {
            if created { unlinkat(parentFD, name, AT_REMOVEDIR) }
            throw ToolFailure("unsafe_state_directory", "Cannot anchor the MacPilot state directory")
        }
        do {
            var openedInfo = stat()
            guard fstat(directoryFD, &openedInfo) == 0 else {
                throw ToolFailure("unsafe_state_directory", "Cannot inspect the anchored MacPilot state directory")
            }
            try Self.validatePrivateDirectory(openedInfo, descriptor: directoryFD, path: selected.path)
            if created, fchmod(directoryFD, mode_t(0o700)) != 0 {
                throw ToolFailure("state_directory_failed", "Cannot set private MacPilot state directory permissions")
            }
            var markerInfo = stat()
            if fstatat(directoryFD, Self.markerName, &markerInfo, AT_SYMLINK_NOFOLLOW) == 0 {
                try Self.validateMarker(directoryFD: directoryFD)
            } else if errno == ENOENT {
                let internallySelectedDefault = root == nil && configuredRoot == nil
                guard created || internallySelectedDefault || requested.path == legacyRoot.path else {
                    throw ToolFailure("unsafe_state_directory", "Existing state override is not marked as owned by MacPilot")
                }
                try Self.createMarker(directoryFD: directoryFD)
            } else {
                throw ToolFailure("unsafe_state_directory", "Cannot inspect the MacPilot state ownership marker")
            }
        } catch {
            Darwin.close(directoryFD)
            throw error
        }
        self.root = selected
        self.rootFD = directoryFD
    }
    static func configuredRoot(from environment: [String: String]) throws -> URL? {
        for key in ["MACPILOT_STATE_DIR", "MAC_COMPUTER_USE_STATE_DIR"] {
            guard let raw = environment[key], !raw.isEmpty else { continue }
            guard raw.hasPrefix("/"), raw.utf8.count <= 4_096, !raw.contains("\0") else {
                throw ToolFailure("unsafe_state_directory", "State directory override must be an absolute local path of at most 4096 UTF-8 bytes")
            }
            return URL(fileURLWithPath: raw, isDirectory: true)
        }
        return nil
    }
    private static func canonicalExistingDirectory(_ url: URL) throws -> URL {
        let resolved: String? = url.path.withCString { path in
            guard let pointer = Darwin.realpath(path, nil) else { return nil }
            defer { Darwin.free(pointer) }
            return String(cString: pointer)
        }
        guard let resolved else {
            throw ToolFailure("unsafe_state_directory", "State directory parent must already exist")
        }
        // Do not call standardizedFileURL here. Foundation maps the physical
        // /private/var path back to the /var firmlink, which would defeat the
        // descriptor walk with O_NOFOLLOW.
        return URL(fileURLWithPath: resolved, isDirectory: true)
    }
    private static func openValidatedAncestor(_ url: URL) throws -> Int32 {
        var currentFD = Darwin.open("/", O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
        guard currentFD >= 0 else {
            throw ToolFailure("unsafe_state_directory", "Cannot anchor the file-system root")
        }
        var currentPath = ""
        do {
            try validateAncestorDirectory(descriptor: currentFD, path: "/")
            for component in url.pathComponents.dropFirst() {
                let nextFD = openat(currentFD, component, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
                guard nextFD >= 0 else {
                    let failedPath = currentPath + "/" + component
                    throw ToolFailure("unsafe_state_directory", "State path contains an unavailable, non-directory, or symbolic-link component: \(failedPath) (\(String(cString:strerror(errno))))")
                }
                Darwin.close(currentFD)
                currentFD = nextFD
                currentPath += "/" + component
                try validateAncestorDirectory(descriptor: currentFD, path: currentPath)
            }
            return currentFD
        } catch {
            Darwin.close(currentFD)
            throw error
        }
    }
    private static func validateAncestorDirectory(descriptor: Int32, path: String) throws {
        var info = stat()
        guard fstat(descriptor, &info) == 0, (info.st_mode & S_IFMT) == S_IFDIR else {
            throw ToolFailure("unsafe_state_directory", "State ancestor is not an anchored directory: \(path)")
        }
        guard info.st_uid == 0 || info.st_uid == geteuid() else {
            throw ToolFailure("unsafe_state_directory", "State ancestor is owned by another user: \(path)")
        }
        let sharedWrite = (info.st_mode & 0o022) != 0
        let sticky = (info.st_mode & mode_t(S_ISVTX)) != 0
        guard !sharedWrite || sticky else {
            throw ToolFailure("unsafe_state_directory", "State ancestor is writable by another user without sticky-directory protection: \(path)")
        }
        guard try !hasUnsafeACL(descriptor, rejectAnyAllow: false) else {
            throw ToolFailure("unsafe_state_directory", "State ancestor grants mutation access through an extended ACL: \(path)")
        }
    }
    private static func validatePrivateDirectory(_ info: stat, descriptor: Int32, path: String) throws {
        guard (info.st_mode & S_IFMT) == S_IFDIR else {
            throw ToolFailure("unsafe_state_directory", "State path is not a real directory: \(path)")
        }
        guard info.st_uid == geteuid(), (info.st_mode & 0o077) == 0,
              try !hasUnsafeACL(descriptor, rejectAnyAllow: true) else {
            throw ToolFailure("unsafe_state_directory", "Existing state directory must be owned by the current user and inaccessible to group and other users")
        }
    }
    private static func hasUnsafeACL(_ descriptor: Int32, rejectAnyAllow: Bool) throws -> Bool {
        errno = 0
        guard let acl = acl_get_fd_np(descriptor, ACL_TYPE_EXTENDED) else {
            if errno == ENOENT { return false }
            throw ToolFailure("unsafe_state_directory", "Cannot inspect extended ACLs on the state path")
        }
        defer { _ = acl_free(UnsafeMutableRawPointer(acl)) }
        guard acl_valid(acl) == 0 else {
            throw ToolFailure("unsafe_state_directory", "The state path has an invalid extended ACL")
        }
        var entry: acl_entry_t?
        var selector = Int32(ACL_FIRST_ENTRY.rawValue)
        var readEntry = false
        while true {
            errno = 0
            let result = acl_get_entry(acl, selector, &entry)
            // Darwin reports the end of a valid ACL as -1/EINVAL rather than
            // the positive sentinel used by some other POSIX ACL variants.
            if result == -1, errno == EINVAL, readEntry { return false }
            guard result == 0, let entry else {
                throw ToolFailure("unsafe_state_directory", "Cannot inspect an extended ACL entry on the state path")
            }
            readEntry = true
            selector = Int32(ACL_NEXT_ENTRY.rawValue)
            var tag = acl_tag_t(rawValue: 0)
            guard acl_get_tag_type(entry, &tag) == 0 else {
                throw ToolFailure("unsafe_state_directory", "Cannot inspect an extended ACL tag on the state path")
            }
            guard tag == ACL_EXTENDED_ALLOW else { continue }
            var permissions: acl_permset_t?
            guard acl_get_permset(entry, &permissions) == 0, let permissions else {
                throw ToolFailure("unsafe_state_directory", "Cannot inspect extended ACL permissions on the state path")
            }
            if rejectAnyAllow ||
                acl_get_perm_np(permissions, ACL_ADD_FILE) == 1 ||
                acl_get_perm_np(permissions, ACL_ADD_SUBDIRECTORY) == 1 ||
                acl_get_perm_np(permissions, ACL_DELETE_CHILD) == 1 ||
                acl_get_perm_np(permissions, ACL_DELETE) == 1 ||
                acl_get_perm_np(permissions, ACL_WRITE_ATTRIBUTES) == 1 ||
                acl_get_perm_np(permissions, ACL_WRITE_EXTATTRIBUTES) == 1 ||
                acl_get_perm_np(permissions, ACL_WRITE_SECURITY) == 1 ||
                acl_get_perm_np(permissions, ACL_CHANGE_OWNER) == 1 {
                return true
            }
        }
    }
    private static func validateMarker(directoryFD: Int32) throws {
        let fd = openat(directoryFD, markerName, O_RDONLY | O_NOFOLLOW | O_CLOEXEC)
        guard fd >= 0 else { throw ToolFailure("unsafe_state_directory", "MacPilot state ownership marker is invalid") }
        defer { Darwin.close(fd) }
        var info = stat()
        guard fstat(fd, &info) == 0, (info.st_mode & S_IFMT) == S_IFREG,
              info.st_uid == geteuid(), (info.st_mode & 0o077) == 0,
              let data = try? readDescriptor(fd, maximumBytes: markerContents.count + 1), data == markerContents else {
            throw ToolFailure("unsafe_state_directory", "MacPilot state ownership marker is invalid")
        }
    }
    private static func createMarker(directoryFD: Int32) throws {
        let fd = openat(directoryFD, markerName, O_CREAT | O_EXCL | O_WRONLY | O_NOFOLLOW | O_CLOEXEC, mode_t(0o600))
        guard fd >= 0 else { throw ToolFailure("state_directory_failed", "Cannot create MacPilot state ownership marker") }
        defer { Darwin.close(fd) }
        guard writeDescriptor(fd, data: markerContents), fchmod(fd, mode_t(0o600)) == 0, fsync(fd) == 0 else {
            unlinkat(directoryFD, markerName, 0)
            throw ToolFailure("state_directory_failed", "Cannot persist MacPilot state ownership marker")
        }
    }
    private static func readDescriptor(_ fd: Int32, maximumBytes: Int) throws -> Data {
        guard lseek(fd, 0, SEEK_SET) >= 0 else { throw ToolFailure("state_read_failed", "Cannot seek state file") }
        var result = Data(), bytes = [UInt8](repeating: 0, count: 16_384)
        while result.count <= maximumBytes {
            let allowance = min(bytes.count, maximumBytes + 1 - result.count)
            let count = bytes.withUnsafeMutableBytes { buffer -> Int in
                guard let base = buffer.baseAddress else { return 0 }
                return Darwin.read(fd, base, allowance)
            }
            if count > 0 { result.append(contentsOf: bytes.prefix(count)); continue }
            if count == 0 { break }
            if errno == EINTR { continue }
            throw ToolFailure("state_read_failed", "Cannot read state file")
        }
        guard result.count <= maximumBytes else { throw ToolFailure("state_read_failed", "State file exceeds its size limit") }
        return result
    }
    private static func writeDescriptor(_ fd: Int32, data: Data) -> Bool {
        var offset = 0
        while offset < data.count {
            let count = data.withUnsafeBytes { buffer -> Int in
                guard let base = buffer.baseAddress else { return 0 }
                return Darwin.write(fd, base.advanced(by: offset), data.count - offset)
            }
            if count > 0 { offset += count; continue }
            if count < 0, errno == EINTR { continue }
            return false
        }
        return true
    }
    private func validatedName(for url: URL) throws -> String {
        let candidate = url
        guard candidate.deletingLastPathComponent().path == root.path else {
            throw ToolFailure("unsafe_state_path", "State file must be a direct child of the anchored state directory")
        }
        let name = candidate.lastPathComponent
        guard !name.isEmpty, name != ".", name != "..", !name.contains("/") else {
            throw ToolFailure("unsafe_state_path", "Invalid state file name")
        }
        return name
    }
    private func readFile(named name: String, maximumBytes: Int) throws -> Data {
        guard !name.isEmpty, name != ".", name != "..", !name.contains("/") else {
            throw ToolFailure("unsafe_state_path", "Invalid state file name")
        }
        let fd = openat(rootFD, name, O_RDONLY | O_NOFOLLOW | O_CLOEXEC)
        guard fd >= 0 else { throw ToolFailure("state_read_failed", "State file is unavailable") }
        defer { Darwin.close(fd) }
        var info = stat()
        guard fstat(fd, &info) == 0, (info.st_mode & S_IFMT) == S_IFREG,
              info.st_uid == geteuid(), (info.st_mode & 0o077) == 0 else {
            throw ToolFailure("state_read_failed", "State file is not a private regular file")
        }
        return try Self.readDescriptor(fd, maximumBytes: maximumBytes)
    }
    public func read(_ name: String, maximumBytes: Int = 1_048_576) throws -> Data {
        try readFile(named: name, maximumBytes: maximumBytes)
    }
    public func names(prefix: String) throws -> [String] {
        // Enumerated names are untrusted until the anchored no-follow read validates them.
        try FileManager.default.contentsOfDirectory(atPath: root.path)
            .filter { $0.hasPrefix(prefix) }.sorted()
    }
    public func remove(_ name: String) throws {
        _ = try validatedName(for: root.appendingPathComponent(name))
        guard unlinkat(rootFD, name, 0) == 0 || errno == ENOENT else {
            throw ToolFailure("state_write_failed", "Cannot remove private state file")
        }
    }
    public func lease(_ name: String) throws -> StateLease {
        guard !name.isEmpty, name.utf8.count <= 240,
              name.allSatisfy({ $0.isASCII && ($0.isLetter || $0.isNumber || "._-".contains($0)) }) else {
            throw ToolFailure("invalid_argument", "Invalid resource lock name")
        }
        let fd = openat(rootFD, name, O_CREAT | O_RDWR | O_NOFOLLOW | O_CLOEXEC, mode_t(0o600))
        var info = stat()
        guard fd >= 0, fstat(fd, &info) == 0, (info.st_mode & S_IFMT) == S_IFREG,
              info.st_uid == geteuid(), (info.st_mode & 0o077) == 0,
              flock(fd, LOCK_EX | LOCK_NB) == 0 else {
            if fd >= 0 { Darwin.close(fd) }
            throw ToolFailure("busy", "This task or target is in use; reconcile before retrying")
        }
        return StateLease(fd)
    }
    public func image(for observation: Observation, maximumBytes: Int = ImageSafety.maximumEncodedPNGBytes,
                      maximumDimension: Int = ImageSafety.maximumDimension,
                      maximumPixels: Int = ImageSafety.maximumPixels,
                      maximumDecodedBytes: Int = ImageSafety.maximumDecodedBytes) throws -> CGImage {
        guard let path = observation.screenshot,
              let expectedHash = observation.screenshotSHA256,
              let expectedWidth = observation.pixelWidth,
              let expectedHeight = observation.pixelHeight else {
            throw ToolFailure("missing_image", "Observation has no complete screenshot metadata")
        }
        guard maximumBytes > 0, maximumDimension > 0, maximumPixels > 0, maximumDecodedBytes > 0 else {
            throw ToolFailure("invalid_argument", "Image limits must be positive")
        }
        // Keep the anchored physical path spelling. Foundation can map
        // /private/var back to the /var firmlink during standardization.
        let url = URL(fileURLWithPath: path)
        let data = try readFile(named: validatedName(for: url), maximumBytes: maximumBytes)
        guard data.starts(with: [0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A]) else {
            throw ToolFailure("invalid_image", "Observation screenshot is not a PNG")
        }
        let actualHash = SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined()
        guard actualHash == expectedHash else {
            throw ToolFailure("stale_image", "Observation screenshot hash no longer matches its recorded value")
        }
        guard let source = CGImageSourceCreateWithData(data as CFData, nil),
              CGImageSourceGetCount(source) == 1,
              let type = CGImageSourceGetType(source), type as String == UTType.png.identifier,
              let properties = CGImageSourceCopyPropertiesAtIndex(source, 0, nil) as? [CFString: Any],
              let width = (properties[kCGImagePropertyPixelWidth] as? NSNumber)?.intValue,
              let height = (properties[kCGImagePropertyPixelHeight] as? NSNumber)?.intValue,
              width > 0, height > 0,
              width <= maximumDimension, height <= maximumDimension,
              width <= maximumPixels / height,
              width == expectedWidth, height == expectedHeight else {
            throw ToolFailure("invalid_image", "Observation screenshot metadata is invalid or exceeds the image safety limits")
        }
        let options = [kCGImageSourceShouldCache: false] as CFDictionary
        guard let image = CGImageSourceCreateImageAtIndex(source, 0, options),
              image.width == width, image.height == height else {
            throw ToolFailure("invalid_image", "Observation screenshot cannot be decoded safely")
        }
        return try ImageSafety.validateDecoded(
            image,
            maximumDimension: maximumDimension,
            maximumPixels: maximumPixels,
            maximumDecodedBytes: maximumDecodedBytes,
            failureCode: "invalid_image",
            description: "Observation screenshot decoded layout is invalid or exceeds the image safety limits"
        )
    }
    public func lock() throws {
        guard lockFD < 0 else {
            throw ToolFailure("busy", "Another local call is active or the lock file is unsafe; retry after reconciliation")
        }
        let candidate = openat(rootFD, ".lock", O_CREAT | O_RDWR | O_NOFOLLOW | O_CLOEXEC, mode_t(0o600))
        var info = stat()
        guard candidate >= 0, fstat(candidate, &info) == 0, (info.st_mode & S_IFMT) == S_IFREG,
              info.st_uid == geteuid(), (info.st_mode & 0o077) == 0,
              flock(candidate, LOCK_EX | LOCK_NB) == 0 else {
            if candidate >= 0 { Darwin.close(candidate) }
            throw ToolFailure("busy", "Another local call is active or the lock file is unsafe; retry after reconciliation")
        }
        lockFD = candidate
    }
    public func unlock() { if lockFD >= 0 { flock(lockFD, LOCK_UN); Darwin.close(lockFD); lockFD = -1 } }
    deinit { unlock(); if rootFD >= 0 { Darwin.close(rootFD) } }
    public func tokenURL(_ id: String) throws -> URL {
        guard let uuid = UUID(uuidString: id) else { throw ToolFailure("invalid_argument", "Observation must be a UUID") }
        return root.appendingPathComponent(uuid.uuidString.lowercased() + ".json")
    }
    public func save(_ observation: Observation) throws {
        let data = try JSONEncoder().encode(observation)
        guard data.count <= 4_000_000 else { throw ToolFailure("observation_too_large", "Observation exceeds 4 MB; observe with fewer nodes") }
        try write(data, to:tokenURL(observation.id))
    }
    public func load(_ id: String) throws -> Observation {
        let url = try tokenURL(id)
        guard let data = try? readFile(named: validatedName(for: url), maximumBytes: 4_000_000),
              let result = try? JSONDecoder().decode(Observation.self, from: data) else { throw ToolFailure("missing_observation", "Observation does not exist") }
        return result
    }
    public func consume(_ observation: Observation) throws { var used = observation; used.consumed = true; try save(used) }
    public func write(_ data: Data, to url: URL) throws {
        let name = try validatedName(for: url)
        let temporary = ".tmp-\(UUID().uuidString.lowercased())"
        let fd = openat(rootFD, temporary, O_CREAT | O_EXCL | O_WRONLY | O_NOFOLLOW | O_CLOEXEC, mode_t(0o600))
        guard fd >= 0 else { throw ToolFailure("state_write_failed", "Cannot create a private temporary state file") }
        var installed = false
        defer {
            Darwin.close(fd)
            if !installed { unlinkat(rootFD, temporary, 0) }
        }
        guard Self.writeDescriptor(fd, data: data), fchmod(fd, mode_t(0o600)) == 0, fsync(fd) == 0,
              renameat(rootFD, temporary, rootFD, name) == 0 else {
            throw ToolFailure("state_write_failed", "Cannot atomically persist private state")
        }
        installed = true
    }
    public func pointer(_ observation: Observation, cursorID: String = "primary") -> Pointer? {
        guard let name = try? Self.pointerName(cursorID),
              let data = try? readFile(named: name, maximumBytes: 65_536),
              var p = try? JSONDecoder().decode(Pointer.self, from: data),
              p.pid == observation.pid, p.windowID == observation.windowID,
              p.processStartID == nil || p.processStartID == observation.processStartID else { return nil }
        if let frame = p.windowFrame, frame.width > 0, frame.height > 0 {
            p.x = observation.windowFrame.x + (p.x - frame.x) / frame.width * observation.windowFrame.width
            p.y = observation.windowFrame.y + (p.y - frame.y) / frame.height * observation.windowFrame.height
        }
        return p
    }
    public static func pointerName(_ id: String) throws -> String {
        guard !id.isEmpty, id.utf8.count <= 64,
              id.allSatisfy({ $0.isASCII && ($0.isLetter || $0.isNumber || "-_".contains($0)) }) else {
            throw ToolFailure("invalid_argument", "cursorID must be 1 to 64 ASCII letters, digits, hyphens or underscores")
        }
        return id == "primary" ? "pointer.json" : "pointer-\(id).json"
    }
    public func savePointer(_ pointer: Pointer) throws {
        try write(JSONEncoder().encode(pointer), to: root.appendingPathComponent(Self.pointerName(pointer.cursorID ?? "primary")))
    }
    public func pointers(_ observation: Observation) throws -> [Pointer] {
        try names(prefix: "pointer").compactMap { name in
            guard name == "pointer.json" || (name.hasPrefix("pointer-") && name.hasSuffix(".json")),
                  let value = try? JSONDecoder().decode(Pointer.self, from: read(name, maximumBytes: 65_536)) else { return nil }
            return pointer(observation, cursorID: value.cursorID ?? "primary")
        }
    }
    public func audit(tool: String, status: String, pid: Int32? = nil) {
        var row: [String: Any] = ["time":ISO8601DateFormatter().string(from: Date()), "tool":tool, "status":status]
        if let pid { row["pid"] = pid }
        guard var data = try? jsonData(row) else { return }
        data.append(10)
        let fd = openat(rootFD, "audit.jsonl", O_CREAT | O_WRONLY | O_APPEND | O_NOFOLLOW | O_CLOEXEC, mode_t(0o600))
        guard fd >= 0 else { return }
        defer { Darwin.close(fd) }
        var info = stat()
        guard fstat(fd, &info) == 0, (info.st_mode & S_IFMT) == S_IFREG,
              info.st_uid == geteuid(), (info.st_mode & 0o077) == 0 else { return }
        _ = Self.writeDescriptor(fd, data: data)
    }
}
