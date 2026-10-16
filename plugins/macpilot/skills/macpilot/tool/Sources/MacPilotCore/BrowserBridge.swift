import AppKit
import CryptoKit
import Darwin

public struct BrowserConnection: Codable {
    public var id:String, browser:String, extensionID:String, processStartID:String
    public var pid:Int32
    public var lastSeen:Double
    public var connected:Bool
    public var object:[String:Any] { (try? JSONSerialization.jsonObject(with:JSONEncoder().encode(self))) as? [String:Any] ?? [:] }
    public var live:Bool { connected && Date().timeIntervalSince1970-lastSeen < 12 && ProcessIdentity.startID(pid:pid) == processStartID }
}

@MainActor public enum BrowserBridge {
    public static let hostName = "com.oozoofrog.macpilot"
    static let common = ["operation","connectionID","tabID","frameID","timeoutMs","browser"]
    static let fields:[String:[String]] = [
        "tabs":[],"open":["url","activate"],"select":["activate"],"close":[],"navigate":["url"],"back":[],"forward":[],"reload":[],"frames":[],
        "observe":["maxNodes"],"click":["observation","node"],"fill":["observation","node","text"],"select_option":["observation","node","text"],
        "scroll":["observation","node","x","y"],"key":["observation","node","key"],
        "verify":["observation","node","equals","contains"],"wait":["observation","node","equals","contains"],
        "upload":["observation","node","path","mime"],"download":["url","filename"],"download_status":["downloadID"],"screenshot":[]
    ]
    public static func connections(_ store:Store) throws -> [BrowserConnection] {
        try store.names(prefix:"browser-connection-").compactMap { name in
            guard name.hasSuffix(".json") else { return nil }
            return try? JSONDecoder().decode(BrowserConnection.self,from:store.read(name))
        }
    }
    private static func connection(_ a:Arguments, store:Store) throws -> BrowserConnection {
        let active = try connections(store).filter(\.live)
        if let selected = a.values["connectionID"] as? String {
            let id = try Tasks.id(selected)
            guard let connection = active.first(where:{$0.id == id}) else { throw ToolFailure("browser_not_connected","Selected extension connection is not live") }
            return connection
        }
        guard active.count == 1, let connection = active.first else {
            throw ToolFailure(active.isEmpty ? "browser_not_connected" : "ambiguous_browser",active.isEmpty ? "Enable the MacPilot browser extension and install its native host" : "Specify connectionID from connections; multiple browsers are connected")
        }
        return connection
    }
    static func validatedPayload(_ a:Arguments,operation:String,preserveForeground:Bool) throws -> [String:Any] {
        guard let specific = fields[operation] else { throw ToolFailure("invalid_argument","Unsupported browser operation") }
        try a.only(common + specific)
        var payload = a.values;payload.removeValue(forKey:"connectionID")
        let timeout = try a.integer("timeoutMs",default:operation == "wait" ? 5000 : 10_000,range:100...60_000)
        payload["timeoutMs"] = timeout
        if operation != "tabs" && operation != "open" && operation != "download" && operation != "download_status" {
            payload["tabID"] = try a.integer("tabID",range:1...Int(Int32.max))
        }
        if a.values["frameID"] != nil { payload["frameID"] = try a.integer("frameID",range:0...Int(Int32.max)) }
        if a.values["maxNodes"] != nil { payload["maxNodes"] = try a.integer("maxNodes",range:1...500) }
        if a.values["activate"] != nil { payload["activate"] = try a.bool("activate") }
        let activate = try a.bool("activate")
        if preserveForeground && activate { throw ToolFailure("foreground_required","This task preserves foreground; use activate=false or an explicitly foreground task") }
        if a.values["url"] != nil {
            let raw = try a.string("url",limit:8192)
            if raw != "about:blank" { _ = try SystemActions.validatedOpenURL(raw) }
            payload["url"] = raw
        }
        for key in ["text","equals","contains"] where a.values[key] != nil { payload[key] = try a.string(key,limit:65536) }
        for key in ["observation","node","key","mime","filename"] where a.values[key] != nil { payload[key] = try a.string(key,limit:1024) }
        for key in ["x","y"] where a.values[key] != nil { payload[key] = try a.number(key) }
        if operation == "verify" || operation == "wait" {
            guard (a.values["equals"] != nil) != (a.values["contains"] != nil) else { throw ToolFailure("invalid_argument","Specify exactly one equals or contains predicate") }
        }
        if operation == "fill" || operation == "select_option" { _ = try a.string("text",limit:65536) }
        if operation == "key" { _ = try a.string("key",limit:64) }
        if ["click","fill","select_option","scroll","key","verify","wait","upload"].contains(operation) {
            _ = try a.string("observation",limit:64);_ = try a.string("node",limit:64)
        }
        if operation == "download_status" { payload["downloadID"] = try a.integer("downloadID",range:0...Int(Int32.max)) }
        if let name = payload["filename"] as? String {
            guard !name.hasPrefix("/"),!name.split(separator:"/").contains(".."),!name.contains("\\"),!name.contains("\0") else {
                throw ToolFailure("invalid_argument","Download filename must be a relative path within the browser download directory")
            }
        }
        return payload
    }
    public static func call(_ a:Arguments, store:Store, preserveForeground:Bool) async throws -> [String:Any] {
        let operation = try a.string("operation")
        if operation == "connections" {
            try a.only(["operation"])
            return ["status":"browser_connections","connections":try connections(store).map { var value=$0.object;value["live"]=$0.live;return value }]
        }
        if operation == "install_host" { return try install(a,store:store) }
        if operation == "receipt" {
            try a.only(["operation","requestID"])
            let id = try Tasks.id(a.string("requestID"))
            if let data = try? store.read("browser-response-\(id).json") {
                return ["status":"response_received","requestID":id,"response":try JSONSerialization.jsonObject(with:data)]
            }
            return try object(store.read("browser-request-\(id).json"))
        }
        if a.values["browser"] as? String=="safari"{return try await SafariBridge.call(a,store:store,preserveForeground:preserveForeground)}
        var payload = try validatedPayload(a, operation:operation, preserveForeground:preserveForeground)
        let timeout = payload["timeoutMs"] as! Int
        let selected = try connection(a,store:store)
        let tab = (payload["tabID"] as? Int).map(String.init) ?? "browser"
        let lease = try store.lease(".browser-\(selected.id)-\(tab).lock")
        defer { withExtendedLifetime(lease) {} }
        if operation == "wait" {
            guard timeout <= 30_000 else { throw ToolFailure("invalid_argument","DOM wait is limited to the observation's 30-second lifetime") }
            // Background tabs throttle page timers. Poll read-only predicates from
            // the native host so unrelated tabs continue to make progress.
            payload["operation"]="verify"
            let deadline=Date().addingTimeInterval(Double(timeout)/1000)
            var latest:[String:Any]=["status":"predicate_not_met","matches":false]
            repeat {
                try Task.checkCancellation()
                latest=try await command(payload,connection:selected,store:store,timeout:5000)
                if latest["matches"] as? Bool == true { return latest }
                if Date()<deadline { try await Task.sleep(nanoseconds:100_000_000) }
            } while Date()<deadline
            return latest
        }
        if operation == "upload" {
            let path = try SystemActions.explicitFileURLs([a.string("path",limit:4096)],key:"path",mustExist:true,rejectRoot:true)[0]
            guard (try FileManager.default.attributesOfItem(atPath:path.path)[.type] as? FileAttributeType) == .typeRegular else { throw ToolFailure("invalid_upload","Upload requires a regular file") }
            let size = (try FileManager.default.attributesOfItem(atPath:path.path)[.size] as? NSNumber)?.intValue ?? -1
            guard (0...33_554_432).contains(size) else { throw ToolFailure("invalid_upload","Upload size limit is 32 MiB") }
            payload.removeValue(forKey:"path");payload["operation"]="upload_begin";payload["name"]=path.lastPathComponent;payload["size"]=size
            let begun = try await command(payload,connection:selected,store:store,timeout:timeout)
            guard let uploadID = begun["uploadID"] as? String else { throw ToolFailure("browser_error","Upload did not return a receipt") }
            let file = try FileHandle(forReadingFrom:path);defer { try? file.close() }
            var digest=SHA256(),offset=0
            while let chunk = try file.read(upToCount:196608),!chunk.isEmpty {
                try Task.checkCancellation();digest.update(data:chunk)
                _ = try await command(["operation":"upload_chunk","tabID":payload["tabID"]!,"frameID":payload["frameID"] ?? 0,
                                       "uploadID":uploadID,"offset":offset,"data":chunk.base64EncodedString()],connection:selected,store:store,timeout:timeout)
                offset += chunk.count
            }
            return try await command(["operation":"upload_end","tabID":payload["tabID"]!,"frameID":payload["frameID"] ?? 0,"uploadID":uploadID,
                                      "sha256":digest.finalize().map{String(format:"%02x",$0)}.joined()],connection:selected,store:store,timeout:timeout)
        }
        var result = try await command(payload,connection:selected,store:store,timeout:timeout)
        if let encoded = result.removeValue(forKey:"pngBase64") as? String {
            guard let data=Data(base64Encoded:encoded),data.count<=1_048_576,data.starts(with:[0x89,0x50,0x4e,0x47]) else { throw ToolFailure("invalid_image","Browser did not return a bounded PNG") }
            let path=store.root.appendingPathComponent("browser-capture-\(UUID().uuidString.lowercased()).png")
            try store.write(data,to:path);result["screenshot"]=path.path
        }
        return result
    }
    private static func object(_ data:Data) throws -> [String:Any] {
        guard let value=try JSONSerialization.jsonObject(with:data) as? [String:Any] else { throw ToolFailure("browser_protocol_error","Expected a JSON object") }
        return value
    }
    private static func command(_ payload:[String:Any],connection:BrowserConnection,store:Store,timeout:Int) async throws -> [String:Any] {
        let id=UUID().uuidString.lowercased(), name="browser-request-\(id).json"
        var request:[String:Any]=["id":id,"connectionID":connection.id,"payload":payload,"state":"queued","expires":Date().timeIntervalSince1970+Double(timeout)/1000]
        try store.write(jsonData(request),to:store.root.appendingPathComponent(name))
        do {
            let deadline=Date().addingTimeInterval(Double(timeout)/1000+0.5)
            while Date()<deadline {
                try Task.checkCancellation()
                if let data=try? store.read("browser-response-\(id).json") {
                    let response=try object(data)
                    if let error=response["error"] as? [String:Any] {
                        throw ToolFailure(error["code"] as? String ?? "browser_error",String((error["message"] as? String ?? "Browser operation failed").prefix(4096)))
                    }
                    guard var result=response["result"] as? [String:Any] else { throw ToolFailure("browser_protocol_error","Browser response has no result") }
                    result["requestID"]=id;result["connectionID"]=connection.id
                    return result
                }
                try await Task.sleep(nanoseconds:50_000_000)
            }
            throw ToolFailure("browser_response_timeout","Browser request \(id) has no response. Query receipt before retrying a mutation.")
        } catch {
            if let current=try? object(store.read(name)) { request=current }
            request["state"]=error is CancellationError ? "cancelled" : (request["state"] as? String == "dispatched" ? "unconfirmed" : "expired")
            try? store.write(jsonData(request),to:store.root.appendingPathComponent(name))
            throw error
        }
    }
    private static func quote(_ value:String) -> String { "'"+value.replacingOccurrences(of:"'",with:"'\\''")+"'" }
    private static func install(_ a:Arguments,store:Store) throws -> [String:Any] {
        try a.only(["operation","extensionID","browser","manifestDirectory"])
        let id=try a.string("extensionID",limit:32)
        guard id.count==32,id.allSatisfy({("a"..."p").contains(String($0))}) else { throw ToolFailure("invalid_argument","Chromium extensionID must have 32 letters a through p") }
        let browser=try a.string("browser",default:"chrome",limit:32)
        let folder:String
        switch browser {
        case "chrome":folder="Google/Chrome"
        case "edge":folder="Microsoft Edge"
        case "chromium":folder="Chromium"
        default:throw ToolFailure("invalid_argument","browser must be chrome, edge or chromium")
        }
        let defaultDirectory=FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library/Application Support/\(folder)/NativeMessagingHosts")
        let directory:URL
        if a.values["manifestDirectory"] != nil {
            directory=try SystemActions.explicitFileURLs([a.string("manifestDirectory",limit:4096)],key:"manifestDirectory",mustExist:false,rejectRoot:true)[0]
        } else { directory=defaultDirectory }
        try FileManager.default.createDirectory(at:directory,withIntermediateDirectories:true,attributes:[.posixPermissions:0o700])
        guard let executable=Bundle.main.executableURL else { throw ToolFailure("process_launch_failed","Cannot locate MacPilot") }
        let launcher=store.root.appendingPathComponent("browser-native-host")
        let script="#!/bin/sh\nexec \(quote(executable.path)) native-host --state \(quote(store.root.path)) \"$@\"\n"
        try store.write(Data(script.utf8),to:launcher)
        try FileManager.default.setAttributes([.posixPermissions:0o700],ofItemAtPath:launcher.path)
        let manifest:[String:Any]=["name":hostName,"description":"MacPilot native browser bridge","path":launcher.path,"type":"stdio","allowed_origins":["chrome-extension://\(id)/"]]
        let path=directory.appendingPathComponent(hostName+".json"), data=try jsonData(manifest,pretty:true)
        if FileManager.default.fileExists(atPath:path.path) {
            guard let current=try? Data(contentsOf:path),let object=try? object(current),
                  object["path"] as? String==launcher.path,object["allowed_origins"] as? [String]==manifest["allowed_origins"] as? [String] else {
                throw ToolFailure("host_already_configured","Existing native host belongs to a different installation or extension; it was not replaced")
            }
        } else {
            try data.write(to:path,options:.withoutOverwriting)
            try FileManager.default.setAttributes([.posixPermissions:0o600],ofItemAtPath:path.path)
        }
        return ["status":"native_host_installed","manifest":path.path,"extensionID":id,"stateDirectory":store.root.path]
    }
    nonisolated private static func readFrame(_ handle:FileHandle) throws -> Data? {
        func exact(_ count:Int) throws -> Data? {
            var result=Data()
            while result.count<count {
                guard let chunk=try handle.read(upToCount:count-result.count),!chunk.isEmpty else {
                    if result.isEmpty { return nil };throw ToolFailure("browser_protocol_error","Truncated native message")
                }
                result.append(chunk)
            }
            return result
        }
        guard let header=try exact(4) else { return nil }
        let count=header.enumerated().reduce(0){$0 | Int($1.element) << (8*$1.offset)}
        guard count>0,count<=1_048_576 else { throw ToolFailure("browser_protocol_error","Native message exceeds 1 MiB") }
        guard let body=try exact(count) else { throw ToolFailure("browser_protocol_error","Missing native message body") }
        return body
    }
    private static func writeFrame(_ object:[String:Any]) throws {
        let data=try jsonData(object)
        guard data.count<=1_048_576 else { throw ToolFailure("browser_protocol_error","Outgoing native message exceeds 1 MiB") }
        var count=UInt32(data.count).littleEndian
        var frame=Data();withUnsafeBytes(of:&count){frame.append(contentsOf:$0)};frame.append(data)
        try FileHandle.standardOutput.write(contentsOf:frame)
    }
    public static func runHost(store:Store,origin:String?) async throws {
        var connection=BrowserConnection(id:UUID().uuidString.lowercased(),browser:"chromium",extensionID:"",processStartID:ProcessIdentity.startID(pid:getpid()) ?? "",pid:getpid(),lastSeen:Date().timeIntervalSince1970,connected:false)
        let name="browser-connection-\(connection.id).json"
        func persist(){try? store.write(JSONEncoder().encode(connection),to:store.root.appendingPathComponent(name))}
        var sent=Set<String>()
        let sender=Task { @MainActor in
            while !Task.isCancelled {
                if connection.connected {
                    for name in (try? store.names(prefix:"browser-request-")) ?? [] where name.hasSuffix(".json") {
                        guard var request=try? object(store.read(name)),request["connectionID"] as? String==connection.id,
                              let id=request["id"] as? String,(try? Tasks.id(id))==id,!sent.contains(id),
                              request["state"] as? String=="queued",(request["expires"] as? Double ?? 0)>Date().timeIntervalSince1970,
                              let payload=request["payload"] as? [String:Any] else {continue}
                        request["state"]="dispatched";request["dispatchedAt"]=Date().timeIntervalSince1970
                        do {
                            try store.write(jsonData(request),to:store.root.appendingPathComponent(name))
                            sent.insert(id)
                            try writeFrame(["type":"command","id":id,"payload":payload])
                        } catch {return}
                    }
                }
                try? await Task.sleep(nanoseconds:100_000_000)
            }
        }
        defer {sender.cancel();connection.connected=false;persist()}
        while let data=try await Task.detached(operation:{try readFrame(.standardInput)}).value {
            let message=try object(data)
            connection.lastSeen=Date().timeIntervalSince1970
            switch message["type"] as? String {
            case "hello":
                guard let id=message["extensionID"] as? String,id.count==32,
                      origin==nil || origin=="chrome-extension://\(id)/" else {throw ToolFailure("browser_protocol_error","Extension origin mismatch")}
                connection.extensionID=id;connection.browser=message["browser"] as? String ?? "chromium";connection.connected=true
                try writeFrame(["type":"connected","connectionID":connection.id])
            case "response":
                guard let id=message["id"] as? String,sent.contains(id),
                      message["result"] is [String:Any] || message["error"] is [String:Any] else {throw ToolFailure("browser_protocol_error","Unexpected response ID or body")}
                try store.write(data,to:store.root.appendingPathComponent("browser-response-\(id).json"))
                sent.remove(id)
            case "heartbeat": break
            default:throw ToolFailure("browser_protocol_error","Unknown native message")
            }
            persist()
        }
    }
}
