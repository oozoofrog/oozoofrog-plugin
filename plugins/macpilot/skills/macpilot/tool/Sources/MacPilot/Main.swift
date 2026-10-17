import AppKit
import Darwin
import ImageIO
import MacPilotCore
import UniformTypeIdentifiers

private let maximumJSONBytes = 2_000_000
private let maximumMCPImageBytes = 3_000_000

private func readBoundedData(_ handle: FileHandle, maximumBytes: Int) throws -> Data {
    var result = Data()
    while result.count <= maximumBytes {
        let allowance = maximumBytes + 1 - result.count
        guard let chunk = try handle.read(upToCount: min(65_536, allowance)), !chunk.isEmpty else { break }
        result.append(chunk)
    }
    guard result.count <= maximumBytes else {
        throw ToolFailure("invalid_argument", "Expected a JSON object no larger than 2 MB")
    }
    return result
}

private func readPrivatePNG(at path: String, maximumBytes: Int) -> Data? {
    let fd = Darwin.open(path, O_RDONLY | O_NOFOLLOW | O_CLOEXEC)
    guard fd >= 0 else { return nil }
    let handle = FileHandle(fileDescriptor: fd, closeOnDealloc: true)
    var info = stat()
    guard fstat(fd, &info) == 0,
          (info.st_mode & S_IFMT) == S_IFREG,
          info.st_uid == geteuid(),
          (info.st_mode & 0o077) == 0,
          info.st_size >= 0,
          info.st_size <= maximumBytes else { return nil }
    guard let data = try? readBoundedData(handle, maximumBytes: maximumBytes),
          data.starts(with: [0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A]),
          let source = CGImageSourceCreateWithData(data as CFData, nil),
          CGImageSourceGetCount(source) == 1,
          let type = CGImageSourceGetType(source), type as String == UTType.png.identifier,
          let properties = CGImageSourceCopyPropertiesAtIndex(source, 0, nil) as? [CFString: Any],
          let width = (properties[kCGImagePropertyPixelWidth] as? NSNumber)?.intValue,
          let height = (properties[kCGImagePropertyPixelHeight] as? NSNumber)?.intValue,
          width > 0, height > 0, width <= 8_192, height <= 8_192,
          width <= 16_777_216 / height else { return nil }
    return data
}

private enum BoundedLineRead: Sendable {
    case line(Data)
    case oversized
    case end
    case failed(String)
}

private final class BoundedLineReader: @unchecked Sendable {
    private let handle: FileHandle
    private let maximumBytes: Int
    private var buffer = Data()
    private var discardingOversizedLine = false

    init(handle: FileHandle, maximumBytes: Int) {
        self.handle = handle
        self.maximumBytes = maximumBytes
    }

    private func readAvailableChunk() throws -> Data? {
        var bytes = [UInt8](repeating: 0, count: 65_536)
        while true {
            let count = bytes.withUnsafeMutableBytes { buffer -> Int in
                Darwin.read(handle.fileDescriptor, buffer.baseAddress, buffer.count)
            }
            if count > 0 { return Data(bytes.prefix(count)) }
            if count == 0 { return nil }
            if errno == EINTR { continue }
            throw NSError(domain: NSPOSIXErrorDomain, code: Int(errno))
        }
    }

    func next() -> BoundedLineRead {
        do {
            while true {
                if let newline = buffer.firstIndex(of: 0x0A) {
                    var line = Data(buffer[..<newline])
                    buffer.removeSubrange(buffer.startIndex...newline)
                    if discardingOversizedLine || line.count > maximumBytes {
                        discardingOversizedLine = false
                        return .oversized
                    }
                    if line.last == 0x0D { line.removeLast() }
                    return .line(line)
                }
                if discardingOversizedLine {
                    buffer.removeAll(keepingCapacity: true)
                } else if buffer.count > maximumBytes {
                    discardingOversizedLine = true
                    buffer.removeAll(keepingCapacity: true)
                }
                guard let chunk = try readAvailableChunk(), !chunk.isEmpty else {
                    if discardingOversizedLine {
                        discardingOversizedLine = false
                        return .oversized
                    }
                    guard !buffer.isEmpty else { return .end }
                    let line = buffer
                    buffer.removeAll(keepingCapacity: true)
                    return line.count <= maximumBytes ? .line(line) : .oversized
                }
                buffer.append(chunk)
            }
        } catch {
            return .failed(error.localizedDescription)
        }
    }
}

@MainActor private final class MCPRequestRegistry {
    private let maximumActiveCalls = 16
    private var tasks: [String: Task<Void, Never>] = [:]

    func contains(_ key: String) -> Bool { tasks[key] != nil }
    var hasCapacity: Bool { tasks.count < maximumActiveCalls }
    func insert(_ task: Task<Void, Never>, for key: String) { tasks[key] = task }
    func remove(_ key: String) { tasks.removeValue(forKey: key) }
    func cancel(_ key: String) { tasks[key]?.cancel() }
    func cancelAllAndWait() async {
        tasks.values.forEach { $0.cancel() }
        let deadline = DispatchTime.now().uptimeNanoseconds + 500_000_000
        while !tasks.isEmpty {
            let now = DispatchTime.now().uptimeNanoseconds
            guard now < deadline else { return }
            try? await Task.sleep(nanoseconds: min(10_000_000, deadline - now))
        }
    }
}

@main struct Main {
    private static func requestKey(_ value: Any?) -> String? {
        if let value = value as? String { return "s:\(value)" }
        if let value = value as? NSNumber, CFGetTypeID(value) != CFBooleanGetTypeID() {
            return "n:\(value.stringValue)"
        }
        return nil
    }

    @MainActor private static func emit(_ response: [String: Any]) {
        print(jsonString(response))
        fflush(stdout)
    }

    private static func toolErrorResponse(id: Any, code: String, message: String, improvementRequestID:String? = nil) -> [String: Any] {
        var failure:[String:Any]=[
            "code":code,
            "message":message
        ]
        if let improvementRequestID{failure["improvementRequestID"]=improvementRequestID}
        return RPC.success(id:id,result:["content":[["type":"text","text":jsonString(failure)]],"structuredContent":failure,"isError":true])
    }

    @MainActor private static func toolCallResponse(
        engine: Engine,
        id: Any,
        name: String,
        arguments: [String: Any]
    ) async -> [String: Any] {
        do {
            let result = try await engine.call(name, arguments: arguments)
            var content: [[String:Any]] = [["type":"text","text":jsonString(result)]]
            let observationPath = (result["observation"] as? [String:Any])?["screenshot"] as? String
            if let path = observationPath ?? result["screenshot"] as? String,
               let image = readPrivatePNG(at: path, maximumBytes: maximumMCPImageBytes) {
                content.append(["type":"image","mimeType":"image/png","data":image.base64EncodedString()])
            }
            return RPC.success(id:id,result:["content":content,"structuredContent":result,"isError":false])
        } catch {
            let e = error as? ToolFailure
            return toolErrorResponse(id:id,code:e?.code ?? "native_error",message:e?.description ?? error.localizedDescription,improvementRequestID:e?.improvementRequestID)
        }
    }

    @MainActor static func main() async {
        NSApplication.shared.setActivationPolicy(.prohibited)
        do {
            let args = Array(CommandLine.arguments.dropFirst())
            let command = args.first ?? "permission-setup-ui"
            guard command != "--help", command != "help" else {
                print("""
                macpilot — macOS and browser automation tools (macOS 14+)
                  doctor                        Permission/backend status
                  connection-check              Isolated MCP probe; does not reconnect the host
                  permission-setup [KIND]        Native Settings with attached icon guide; default all
                  tools                         JSON tool schemas
                  call TOOL --json FILE|-       One tool call; '-' reads JSON stdin
                  mcp                           JSON-RPC/MCP over newline-delimited stdio
                  preview OBSERVATION_UUID      Non-activating borderless live preview
                No embedded model, API key, network client, or external package.
                Explicit Shortcuts and script calls can perform their configured external actions.
                State: ~/Library/Application Support/MacPilot (override MACPILOT_STATE_DIR;
                legacy MAC_COMPUTER_USE_STATE_DIR is accepted when the new variable is absent).
                """)
                return
            }
            if command == "permission-setup-ui" {
                guard args.count <= 3 else { throw ToolFailure("invalid_argument", "permission-setup-ui [KIND] [TARGET_BUNDLE_ID]") }
                try PermissionSetup.run(kind: args.count >= 2 ? args[1] : "all", targetBundleID: args.count >= 3 ? args[2] : "com.apple.Safari")
                return
            }
            if command == "permission-setup" {
                guard args.count <= 3 else { throw ToolFailure("invalid_argument", "permission-setup [KIND] [TARGET_BUNDLE_ID]") }
                var request: [String: Any] = ["kind": args.count >= 2 ? args[1] : "all", "operation": "setup", "timeoutMs": 60_000]
                if args.count == 3 { request["targetBundleID"] = args[2] }
                let result = try await Engine(store: Store(), transport: .cli).call("mac_permission", arguments: request)
                print(String(data: try jsonData(result, pretty: true), encoding: .utf8)!)
                return
            }
            if command == "tools" { print(String(data: try jsonData(ToolCatalog.tools, pretty:true), encoding:.utf8)!); return }
            if command == "connection-check" {
                guard args.count == 1 else { throw ToolFailure("invalid_argument", "connection-check accepts no arguments; use call mac_connection for probe options") }
                let result = try await ConnectionDiagnostics.call(Arguments(["operation": "probe"]), transport: .cli)
                print(String(data: try jsonData(result, pretty: true), encoding: .utf8)!)
                if result["status"] as? String != "probe_passed" { exit(2) }
                return
            }
            if command == "deliver-improvement" {
                guard args.count==5,args[1]=="--state",args[3]=="--request",args[2].hasPrefix("/") else{throw ToolFailure("invalid_argument","deliver-improvement requires --state and --request")}
                let result=try await Improvements.deliver(args[4],store:Store(root:URL(fileURLWithPath:args[2])),timeout:120_000)
                print(jsonString(result.object));return
            }
            if command == "native-host" {
                signal(SIGPIPE,SIG_IGN)
                guard args.count >= 3,args[1] == "--state",args[2].hasPrefix("/") else { throw ToolFailure("invalid_argument","native-host requires --state /absolute/directory") }
                do { try await BrowserBridge.runHost(store:Store(root:URL(fileURLWithPath:args[2])),origin:args.dropFirst(3).first(where:{$0.hasPrefix("chrome-extension://")})) }
                catch { try? FileHandle.standardError.write(contentsOf:Data((error.localizedDescription+"\n").utf8));exit(2) }
                return
            }
            if command == "overlay-host" {
                guard args.count==2,args[1].hasPrefix("/") else{throw ToolFailure("invalid_argument","overlay-host needs an absolute state directory")}
                try DesktopOverlay.run(store:Store(root:URL(fileURLWithPath:args[1])));return
            }
            if command == "preview-host" {
                guard args.count == 4, args[1].hasPrefix("/"), UUID(uuidString:args[3]) != nil else {
                    throw ToolFailure("invalid_argument", "preview-host needs a state directory, observation UUID and command UUID")
                }
                try SnapshotPanel.run(store:Store(root:URL(fileURLWithPath:args[1])),id:args[2],sequence:args[3]); return
            }
            let store = try Store(), engine = Engine(store: store, transport: command == "mcp" ? .mcpStdio : .cli)
            if command == "mcp" { await serve(engine); return }
            if command == "preview" {
                guard args.count == 2 else { throw ToolFailure("invalid_argument", "preview requires an observation UUID") }
                try SnapshotPanel.run(store:store, id:args[1]); return
            }
            let name: String, input: [String: Any]
            if command == "doctor", args.count == 1 { name = "mac_doctor"; input = [:] }
            else {
                guard command == "call", args.count == 4, args[2] == "--json" else { throw ToolFailure("invalid_argument", "Use call TOOL --json FILE|-") }
                name = args[1]
                let data: Data
                if args[3] == "-" {
                    data = try readBoundedData(.standardInput, maximumBytes: maximumJSONBytes)
                } else {
                    guard args[3].hasPrefix("/") else { throw ToolFailure("invalid_argument", "JSON file path must be absolute") }
                    let handle = try FileHandle(forReadingFrom: URL(fileURLWithPath:args[3]))
                    defer { try? handle.close() }
                    data = try readBoundedData(handle, maximumBytes: maximumJSONBytes)
                }
                guard let object = try JSONSerialization.jsonObject(with:data) as? [String:Any] else { throw ToolFailure("invalid_argument", "Expected a JSON object no larger than 2 MB") }
                input = object
            }
            print(String(data:try jsonData(try await engine.call(name, arguments:input), pretty:true), encoding:.utf8)!)
        } catch {
            let e = error as? ToolFailure
            var failure:[String:Any]=["status":"error", "code":e?.code ?? "native_error", "message":e?.description ?? error.localizedDescription]
            if let id=e?.improvementRequestID{failure["improvementRequestID"]=id}
            print(jsonString(failure))
            exit(2)
        }
    }
    @MainActor static func serve(_ engine: Engine) async {
        // stdin blocks only a detached reader. Main-actor callbacks stay available to AppKit/SCK.
        var initialized = false
        let reader = BoundedLineReader(handle: .standardInput, maximumBytes: maximumJSONBytes)
        let registry = MCPRequestRegistry()
        while true {
            let next = await Task.detached(operation: { reader.next() }).value
            let data: Data
            switch next {
            case .line(let value): data = value
            case .oversized:
                emit(RPC.failure(id:NSNull(),code:-32700,message:"Message exceeds 2 MB")); continue
            case .end: await registry.cancelAllAndWait(); return
            case .failed(let message):
                emit(RPC.failure(id:NSNull(),code:-32700,message:"Cannot read stdin: \(message)"))
                await registry.cancelAllAndWait()
                return
            }
            guard let request = (try? JSONSerialization.jsonObject(with:data)) as? [String:Any] else {
                emit(RPC.failure(id:NSNull(),code:-32700,message:"Expected JSON object")); continue
            }
            let id = request["id"] ?? NSNull()
            guard request["jsonrpc"] as? String == "2.0", let method = request["method"] as? String else {
                emit(RPC.failure(id:id,code:-32600,message:"Invalid JSON-RPC request")); continue
            }
            let params = request["params"] as? [String:Any] ?? [:]
            if request["id"] == nil {
                if method == "notifications/cancelled", let key = requestKey(params["requestId"]) {
                    registry.cancel(key)
                }
                continue
            }
            let response: [String:Any]
            switch method {
            case "initialize": initialized = true; response = RPC.success(id:id,result:RPC.initialize(params))
            case "ping": response = RPC.success(id:id,result:[:])
            case "tools/list" where initialized: response = RPC.success(id:id,result:["tools":ToolCatalog.tools])
            case "tools/call" where initialized:
                guard let name = params["name"] as? String,
                      params["arguments"] == nil || params["arguments"] is [String:Any] else {
                    emit(RPC.failure(id:id,code:-32602,message:"Expected tool name and arguments object")); continue
                }
                let arguments = params["arguments"] as? [String:Any] ?? [:]
                guard let key = requestKey(id) else {
                    emit(RPC.failure(id:NSNull(),code:-32600,message:"Request id must be a string or number")); continue
                }
                guard !registry.contains(key) else {
                    emit(RPC.failure(id:id,code:-32600,message:"A request with this id is already active")); continue
                }
                guard registry.hasCapacity else {
                    emit(toolErrorResponse(id:id,code:"busy",message:"Another tool call is active; wait for it to finish or cancel it before retrying"))
                    continue
                }
                let task = Task { @MainActor in
                    defer { registry.remove(key) }
                    let response = await toolCallResponse(engine:engine,id:id,name:name,arguments:arguments)
                    if !Task.isCancelled { emit(response) }
                }
                registry.insert(task, for:key)
                continue
            default: response = RPC.failure(id:id,code:initialized ? -32601 : -32002,message:initialized ? "Method not supported" : "Initialize first")
            }
            emit(response)
        }
    }
}
