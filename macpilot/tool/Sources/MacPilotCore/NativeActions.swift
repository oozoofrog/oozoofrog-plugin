import AppKit
import AudioToolbox
import CoreAudio
import CryptoKit

@MainActor public enum NativeFiles {
    public static func call(_ a:Arguments, resources:Store) async throws -> [String:Any] {
        let operation = try a.string("operation")
        let allowed:[String]
        switch operation {
        case "stat": allowed = ["operation","path","timeoutMs"]
        case "list": allowed = ["operation","path","limit","includeHidden","timeoutMs"]
        case "search": allowed = ["operation","path","query","limit","maxDepth","includeHidden","timeoutMs"]
        case "read": allowed = ["operation","path","maxBytes","timeoutMs"]
        case "write": allowed = ["operation","path","text","overwrite","timeoutMs"]
        case "copy","move": allowed = ["operation","path","destination","timeoutMs"]
        case "mkdir": allowed = ["operation","path","timeoutMs"]
        case "tags": allowed = ["operation","path","tags","timeoutMs"]
        default: throw ToolFailure("invalid_argument","Unsupported file operation")
        }
        try a.only(allowed)
        let path = try SystemActions.explicitFileURLs([a.string("path",limit:4096)],key:"path",mustExist: !["write","mkdir"].contains(operation),rejectRoot: !["stat","list","search"].contains(operation))[0]
        let timeout = try a.integer("timeoutMs",default:30_000,range:100...60_000)
        let limit = try a.integer("limit",default:100,range:1...1000)
        let depth = try a.integer("maxDepth",default:8,range:1...32)
        let maxBytes = try a.integer("maxBytes",default:65_536,range:1...1_048_576)
        let includeHidden = try a.bool("includeHidden")
        let overwrite = try a.bool("overwrite")
        let text = try a.string("text",default:"",limit:1_048_576)
        let query = try a.string("query",default:"",limit:256)
        if operation == "search", query.isEmpty { throw ToolFailure("invalid_argument","search requires a nonempty literal query") }
        let tags = try a.strings("tags")
        guard tags.allSatisfy({ !$0.isEmpty && $0.utf8.count <= 255 && !$0.contains("\0") }) else { throw ToolFailure("invalid_argument","Invalid Finder tag") }
        let destination = try a.values["destination"].map { _ in
            try SystemActions.explicitFileURLs([a.string("destination",limit:4096)],key:"destination",mustExist:false,rejectRoot:true)[0]
        }
        if let destination {
            let sourcePath = path.resolvingSymlinksInPath().path
            let destinationPath = destination.deletingLastPathComponent().resolvingSymlinksInPath().appendingPathComponent(destination.lastPathComponent).path
            guard sourcePath != destinationPath, !destinationPath.hasPrefix(sourcePath + "/") else {
                throw ToolFailure("invalid_argument","Destination must not be the source or a descendant of the source")
            }
            guard !FileManager.default.fileExists(atPath:destination.path) else { throw ToolFailure("destination_exists","Destination already exists; nothing was overwritten") }
        }
        // ponytail: one filesystem lease; use canonical ancestor leases only if measured throughput requires it.
        let lease = try resources.lease(".filesystem.lock")
        defer { withExtendedLifetime(lease) {} }
        let result:Result<Data,Error> = try await withBlockingDeadline(timeoutMilliseconds:timeout,
            timeoutFailure:ToolFailure("file_operation_timeout","File operation may still be running. Reconcile the selected source and destination before retrying.")) {
            Result {
                defer { withExtendedLifetime(lease) {} }
                return try jsonData(perform(operation,path:path,destination:destination,text:text,overwrite:overwrite,tags:tags,
                                            query:query,limit:limit,maxDepth:depth,includeHidden:includeHidden,maxBytes:maxBytes))
            }
        }
        let data = try result.get()
        return try JSONSerialization.jsonObject(with:data) as! [String:Any]
    }
    nonisolated private static func info(_ path:URL) throws -> [String:Any] {
        let attributes = try FileManager.default.attributesOfItem(atPath:path.path)
        let type = attributes[.type] as? FileAttributeType
        return ["path":path.path,"name":path.lastPathComponent,"bytes":attributes[.size] as? UInt64 ?? 0,
                "kind":type == .typeDirectory ? "directory" : type == .typeSymbolicLink ? "symlink" : "file",
                "modified":(attributes[.modificationDate] as? Date).map { ISO8601DateFormatter().string(from:$0) } ?? "",
                "tags":(try? path.resourceValues(forKeys:[.tagNamesKey]).tagNames) ?? []]
    }
    nonisolated private static func hash(_ path:URL) throws -> String {
        let input = try FileHandle(forReadingFrom:path); defer { try? input.close() }
        var digest = SHA256()
        while let data = try input.read(upToCount:65_536), !data.isEmpty { digest.update(data:data) }
        return digest.finalize().map { String(format:"%02x",$0) }.joined()
    }
    nonisolated private static func perform(_ operation:String,path:URL,destination:URL?,text:String,overwrite:Bool,tags:[String],
                                            query:String,limit:Int,maxDepth:Int,includeHidden:Bool,maxBytes:Int) throws -> [String:Any] {
        let manager = FileManager.default
        switch operation {
        case "stat": return ["status":"file_metadata","item":try info(path)]
        case "list","search":
            var isDirectory:ObjCBool = false
            guard manager.fileExists(atPath:path.path,isDirectory:&isDirectory),isDirectory.boolValue else { throw ToolFailure("not_directory","Select an existing directory") }
            let options:FileManager.DirectoryEnumerationOptions = includeHidden ? [] : [.skipsHiddenFiles]
            var items:[[String:Any]] = [], scanned = 0, partial = false
            if operation == "list" {
                let children = try manager.contentsOfDirectory(at:path,includingPropertiesForKeys:nil,options:options).sorted { $0.lastPathComponent < $1.lastPathComponent }
                partial = children.count > limit
                items = try children.prefix(limit).map(info)
            } else {
                var errors:[String] = []
                guard let enumerator = manager.enumerator(at:path,includingPropertiesForKeys:[.isDirectoryKey,.isSymbolicLinkKey],options:options,errorHandler:{ url,error in
                    errors.append(url.path); return true
                }) else { throw ToolFailure("file_unavailable","Cannot enumerate selected directory") }
                for case let entry as URL in enumerator {
                    scanned += 1
                    if entry.pathComponents.count - path.pathComponents.count >= maxDepth {
                        if (try? entry.resourceValues(forKeys:[.isDirectoryKey]).isDirectory) == true { partial = true }
                        enumerator.skipDescendants()
                    }
                    if scanned > 10_000 { partial = true; break }
                    if entry.lastPathComponent.localizedStandardContains(query) {
                        items.append(try info(entry))
                        if items.count == limit { partial = true; break }
                    }
                }
                partial = partial || !errors.isEmpty
            }
            return ["status":"file_entries","items":items,"coverage":partial ? "partial" : "selected_scope","scanned":scanned,"maxDepth":maxDepth]
        case "read":
            guard (try manager.attributesOfItem(atPath:path.path)[.type] as? FileAttributeType) == .typeRegular else { throw ToolFailure("not_regular_file","Read requires an explicit regular file") }
            let file = try FileHandle(forReadingFrom:path); defer { try? file.close() }
            var data = try file.read(upToCount:maxBytes+1) ?? Data()
            let truncated = data.count > maxBytes
            if truncated { data = data.prefix(maxBytes) }
            var content = String(data:data,encoding:.utf8)
            if truncated {
                for _ in 0..<3 where content == nil && !data.isEmpty { data.removeLast(); content = String(data:data,encoding:.utf8) }
            }
            guard let content else { throw ToolFailure("invalid_encoding","Selected file is not UTF-8 text") }
            return ["status":"file_text","path":path.path,"text":content,"bytesReturned":data.count,"truncated":truncated]
        case "write":
            if manager.fileExists(atPath:path.path) {
                guard overwrite else { throw ToolFailure("destination_exists","Explicit overwrite=true is required to replace an existing file") }
                guard (try manager.attributesOfItem(atPath:path.path)[.type] as? FileAttributeType) == .typeRegular else { throw ToolFailure("not_regular_file","Only an existing regular file can be replaced") }
            }
            let data = Data(text.utf8)
            try data.write(to:path,options:overwrite ? [.atomic] : [.withoutOverwriting])
            let expected = SHA256.hash(data:data).map { String(format:"%02x",$0) }.joined()
            let actual = try hash(path)
            return ["status":actual == expected ? "file_write_verified" : "file_write_unverified","item":try info(path),"sha256":actual]
        case "copy","move":
            guard let destination else { throw ToolFailure("invalid_argument","destination is required") }
            let sourceInfo = try info(path)
            let sourceHash = sourceInfo["kind"] as? String == "file" ? try hash(path) : nil
            if operation == "copy" { try manager.copyItem(at:path,to:destination) }
            else { try manager.moveItem(at:path,to:destination) }
            let destinationInfo = try info(destination)
            let equal = try sourceHash.map { try hash(destination) == $0 } ?? false
            return ["status":"file_\(operation)_\(equal ? "verified" : "unverified")", "item":destinationInfo,
                    "sourceExists":manager.fileExists(atPath:path.path),"contentHashVerified":equal,
                    "verification":sourceHash == nil ? "Destination metadata exists; directory or symlink contents are not recursively verified" : equal ? "Source and destination SHA-256 match" : "Source and destination SHA-256 differ"]
        case "mkdir":
            try manager.createDirectory(at:path,withIntermediateDirectories:false,attributes:[.posixPermissions:0o700])
            return ["status":"directory_created","item":try info(path)]
        case "tags":
            try (path as NSURL).setResourceValue(tags,forKey:.tagNamesKey)
            let actual = try path.resourceValues(forKeys:[.tagNamesKey]).tagNames ?? []
            return ["status":Set(actual) == Set(tags) ? "tags_verified" : "tags_unverified","tags":actual,"path":path.path]
        default: throw ToolFailure("invalid_argument","Unsupported file operation")
        }
    }
}

@MainActor public enum NativeSystem {
    private static func defaultOutput() throws -> AudioObjectID {
        var property = AudioObjectPropertyAddress(mSelector:kAudioHardwarePropertyDefaultOutputDevice,mScope:kAudioObjectPropertyScopeGlobal,mElement:kAudioObjectPropertyElementMain)
        var device:AudioObjectID = 0, bytes = UInt32(MemoryLayout<AudioObjectID>.size)
        guard AudioObjectGetPropertyData(AudioObjectID(kAudioObjectSystemObject),&property,0,nil,&bytes,&device) == noErr,device != kAudioObjectUnknown else {
            throw ToolFailure("audio_unavailable","No default audio output device")
        }
        return device
    }
    public static func call(_ a:Arguments) throws -> [String:Any] {
        let operation = try a.string("operation")
        if operation == "info" {
            try a.only(["operation"])
            return ["status":"system_info","os":ProcessInfo.processInfo.operatingSystemVersionString,
                    "lowPowerMode":ProcessInfo.processInfo.isLowPowerModeEnabled,"thermalState":ProcessInfo.processInfo.thermalState.rawValue,
                    "screens":NSScreen.screens.map { ["frame":Rect($0.frame).object,"visibleFrame":Rect($0.visibleFrame).object,"scale":$0.backingScaleFactor] as [String:Any] }]
        }
        guard operation == "audio" else { throw ToolFailure("invalid_argument","operation must be info or audio") }
        try a.only(["operation","volume","muted"])
        let volume = a.values["volume"] == nil ? nil : Float32(try a.number("volume",range:0...1))
        let muted = a.values["muted"] == nil ? nil : try a.bool("muted")
        let device = try defaultOutput()
        var channels:[[String:Any]] = []
        for element:UInt32 in [0,1,2] {
            var property = AudioObjectPropertyAddress(mSelector:kAudioDevicePropertyVolumeScalar,mScope:kAudioDevicePropertyScopeOutput,mElement:element)
            guard AudioObjectHasProperty(device,&property) else { continue }
            if var volume {
                var settable:DarwinBoolean = false
                guard AudioObjectIsPropertySettable(device,&property,&settable) == noErr,settable.boolValue,
                      AudioObjectSetPropertyData(device,&property,0,nil,UInt32(MemoryLayout<Float32>.size),&volume) == noErr else {
                    throw ToolFailure("audio_not_settable","Output volume is not writable on this device")
                }
            }
            var actual:Float32 = 0, bytes = UInt32(MemoryLayout<Float32>.size)
            guard AudioObjectGetPropertyData(device,&property,0,nil,&bytes,&actual) == noErr else { continue }
            channels.append(["element":element,"volume":actual])
            if element == 0 { break }
        }
        var muteProperty = AudioObjectPropertyAddress(mSelector:kAudioDevicePropertyMute,mScope:kAudioDevicePropertyScopeOutput,mElement:kAudioObjectPropertyElementMain)
        var actualMute:UInt32 = 0, muteBytes = UInt32(MemoryLayout<UInt32>.size)
        let hasMute = AudioObjectHasProperty(device,&muteProperty)
        if let muted {
            var value:UInt32 = muted ? 1 : 0
            var settable:DarwinBoolean = false
            guard hasMute,AudioObjectIsPropertySettable(device,&muteProperty,&settable) == noErr,settable.boolValue,
                  AudioObjectSetPropertyData(device,&muteProperty,0,nil,muteBytes,&value) == noErr else { throw ToolFailure("audio_not_settable","Output mute is not writable on this device") }
        }
        let muteRead = hasMute && AudioObjectGetPropertyData(device,&muteProperty,0,nil,&muteBytes,&actualMute) == noErr
        let volumeVerified = volume.map { requested in !channels.isEmpty && channels.allSatisfy { abs(($0["volume"] as? Float32 ?? -1)-requested) <= 0.02 } } ?? true
        let muteVerified = muted.map { muteRead && (actualMute != 0) == $0 } ?? true
        return ["status":volumeVerified && muteVerified ? "audio_verified" : "audio_unverified","deviceID":device,"channels":channels,
                "muteSupported":muteRead,"muted":actualMute != 0,"verification":"Only requested output device properties were reread; no audio or microphone was captured"]
    }
}
