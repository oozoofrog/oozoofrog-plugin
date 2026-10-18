import AppKit
import CryptoKit
import ImageIO
import Vision
import VisionKit

struct ImageSearchSettings: Codable {
    var enabled = false
    var pythonPath: String?
    var modelPath: String?
    var device = "mps"
    var fingerprint: String?
}
struct EmbeddingEntry: Codable {
    var schema = "macpilot-embedding/1"
    var key: String
    var vector: [Double]
}
enum EmbeddingMath {
    static let dimensions = 768
    static func valid(_ vector: [Double]) -> Bool {
        guard vector.count == dimensions, vector.allSatisfy(\.isFinite) else { return false }
        return (0.99...1.01).contains(vector.reduce(0) {$0 + $1 * $1})
    }
    static func cosine(_ first: [Double], _ second: [Double]) throws -> Double {
        guard valid(first), valid(second) else { throw ToolFailure("invalid_embedding","Expected finite normalized 768-dimensional vectors") }
        return zip(first,second).reduce(0) {$0 + $1.0 * $1.1}
    }
    static func accepted(scores: [Double], minimum:Double, margin:Double) -> Bool {
        let sorted = scores.sorted(by:>)
        guard let first = sorted.first, first.isFinite, first >= minimum else { return false }
        // A sole candidate still needs its absolute threshold; duplicates remain distinct.
        return sorted.count == 1 || first - sorted[1] >= margin
    }
}
@MainActor enum EmbeddingCache {
    static func hash(_ data: Data) -> String { SHA256.hash(data:data).map{String(format:"%02x",$0)}.joined() }
    static func name(_ key:String) throws -> String {
        guard key.count == 64, key.allSatisfy({$0.isHexDigit && !$0.isUppercase}) else { throw ToolFailure("invalid_argument","Invalid embedding cache key") }
        return "embedding-\(key).json"
    }
    static func read(_ key:String,store:Store) -> [Double]? {
        guard let name = try? name(key), let data = try? store.read(name,maximumBytes:32768),
              let entry = try? JSONDecoder().decode(EmbeddingEntry.self,from:data), entry.key == key,
              entry.schema == "macpilot-embedding/1", EmbeddingMath.valid(entry.vector) else { return nil }
        return entry.vector
    }
    static func save(_ key:String,vector:[Double],store:Store) throws {
        guard EmbeddingMath.valid(vector) else { throw ToolFailure("invalid_embedding","The optional model returned an invalid vector") }
        try store.write(JSONEncoder().encode(EmbeddingEntry(key:key,vector:vector)),to:store.root.appendingPathComponent(try name(key)))
        let names = try store.names(prefix:"embedding-").filter { value in
            guard value.hasSuffix(".json") else { return false }
            return (try? name(String(value.dropFirst(10).dropLast(5)))) == value
        }
        if names.count > 256 {
            let ordered = names.sorted { a,b in
                let first = (try? FileManager.default.attributesOfItem(atPath:store.root.appendingPathComponent(a).path)[.modificationDate] as? Date) ?? .distantPast
                let second = (try? FileManager.default.attributesOfItem(atPath:store.root.appendingPathComponent(b).path)[.modificationDate] as? Date) ?? .distantPast
                return first < second
            }
            for name in ordered.prefix(names.count-256) { try store.remove(name) }
        }
    }
}
struct SearchCandidate {
    var rect: CGRect
    var source: String
    var nodeID: String?
    var transcript: String
    var imageKey: String
    var textKey: String?
}

@MainActor enum ImageSearch {
    static let modelRevision = "914f7f89142e33e77833254d9c9b90c3cef7303b"
    static var resources: URL {
        if let root = Bundle.main.resourceURL?.appendingPathComponent("ImageSearch"),
           FileManager.default.fileExists(atPath:root.appendingPathComponent("image_search_worker.py").path) { return root }
        return URL(fileURLWithPath:#filePath).deletingLastPathComponent().deletingLastPathComponent()
            .deletingLastPathComponent().deletingLastPathComponent().appendingPathComponent("runtime")
    }
    static func settings(_ store:Store) throws -> ImageSearchSettings {
        guard try store.byteCount("image-search-settings.json") != nil else { return ImageSearchSettings() }
        guard let value = try? JSONDecoder().decode(ImageSearchSettings.self,from:store.read("image-search-settings.json",maximumBytes:8192)) else {
            throw ToolFailure("invalid_image_search_configuration","Explicitly configure optional image search again")
        }
        return value
    }
    static func manifest() throws -> [String:Any] {
        let data = try Data(contentsOf:resources.appendingPathComponent("embeddinggemma2-manifest.json"))
        guard let value = try JSONSerialization.jsonObject(with:data) as? [String:Any],
              value["model"] as? String == "google/embeddinggemma-2", value["revision"] as? String == modelRevision else {
            throw ToolFailure("image_resources_unavailable","The pinned optional model manifest is unavailable")
        }
        return value
    }
    static func fingerprint(_ configuration:ImageSearchSettings) throws -> String {
        guard let model = configuration.modelPath, let python = configuration.pythonPath,
              model.hasPrefix("/"), python.hasPrefix("/"), !model.contains("\0"), !python.contains("\0"),
              FileManager.default.isExecutableFile(atPath:python) else {
            throw ToolFailure("image_backend_unconfigured","Provide absolute local modelPath and pythonPath; preserve the venv interpreter path")
        }
        let root = URL(fileURLWithPath:model)
        guard let entries = try manifest()["files"] as? [[String:Any]] else { throw ToolFailure("image_resources_unavailable","Model manifest has no files") }
        var stamps: [[String:Any]] = []
        for entry in entries {
            guard let name = entry["path"] as? String, !name.hasPrefix("/"), !name.split(separator:"/").contains(".."),
                  let size = entry["size"] as? NSNumber else { throw ToolFailure("image_resources_unavailable","Invalid model manifest entry") }
            let path = root.appendingPathComponent(name).resolvingSymlinksInPath()
            let attributes = try FileManager.default.attributesOfItem(atPath:path.path)
            guard attributes[.type] as? FileAttributeType == .typeRegular,
                  (attributes[.size] as? NSNumber)?.int64Value == size.int64Value else {
                throw ToolFailure("image_model_unavailable","A pinned model file is missing or has the wrong size")
            }
            stamps.append(["name":name,"path":path.path,"size":size,"inode":attributes[.systemFileNumber] as? NSNumber ?? 0,
                           "modified":(attributes[.modificationDate] as? Date)?.timeIntervalSince1970 ?? 0])
        }
        let script = try Data(contentsOf:resources.appendingPathComponent("image_search_worker.py"))
        return EmbeddingCache.hash(try jsonData(["files":stamps,"python":python,"device":configuration.device,"worker":EmbeddingCache.hash(script),"pipeline":"image-search/1"]))
    }
    static func worker(_ request:[String:Any],configuration:ImageSearchSettings,store:Store,timeout:Int) async throws -> [String:Any] {
        guard let python = configuration.pythonPath, let model = configuration.modelPath else { throw ToolFailure("image_backend_unconfigured","Configure image search first") }
        let id = UUID().uuidString.lowercased(); var payload = request; payload["requestID"] = id
        // Do not resolve the interpreter symlink: doing so loses its pyvenv.cfg.
        let result = try await CommandRunner.run(executable:URL(fileURLWithPath:python),
            arguments:["-I","-u",resources.appendingPathComponent("image_search_worker.py").path,"--model",model,
                       "--manifest",resources.appendingPathComponent("embeddinggemma2-manifest.json").path,
                       "--allowed-root",store.root.path,"--device",configuration.device],
            standardInput:jsonString(payload),timeoutMilliseconds:max(100,min(60000,timeout)),maxOutputBytes:1_048_576)
        guard !result.stdoutTruncated, let data = result.stdout.data(using:.utf8),
              let object = try? JSONSerialization.jsonObject(with:data) as? [String:Any] else {
            throw ToolFailure("image_backend_protocol","The optional model worker returned no bounded JSON result")
        }
        guard result.exitCode == 0, object["requestID"] as? String == id,
              object["revision"] as? String == modelRevision, object["dimensions"] as? Int == 768 else {
            let known = Set(["dependency_missing","dependency_version_mismatch","model_integrity_failed","model_device_unavailable","invalid_embedding"])
            let code = object["code"] as? String ?? "worker_failed"
            throw ToolFailure("image_" + (known.contains(code) ? code : "worker_failed"),"Optional EmbeddingGemma 2 worker failed; verify the pinned model and optional runtime dependencies")
        }
        return object
    }
    static func call(_ a:Arguments,engine:Engine) async throws -> [String:Any] {
        let operation = try a.string("operation")
        switch operation {
        case "configure":
            try a.only(["operation","enabled","pythonPath","modelPath","device"])
            var value = (try? settings(engine.store)) ?? ImageSearchSettings()
            value.enabled = try a.bool("enabled",default:value.enabled)
            if a.values["pythonPath"] != nil { value.pythonPath = try a.string("pythonPath",limit:4096) }
            if a.values["modelPath"] != nil { value.modelPath = try a.string("modelPath",limit:4096) }
            value.device = try a.string("device",default:value.device,limit:16)
            guard ["mps","cpu"].contains(value.device) else { throw ToolFailure("invalid_argument","device must be mps or cpu") }
            if value.enabled {
                guard ImageAnalyzer.isSupported else { throw ToolFailure("visionkit_unavailable","VisionKit image analysis is unavailable on this device") }
                let before = try fingerprint(value)
                _ = try await worker(["operation":"probe"],configuration:value,store:engine.store,timeout:60_000)
                guard try fingerprint(value) == before else { throw ToolFailure("image_configuration_changed","The model changed during configuration") }
                value.fingerprint = before
            }
            try engine.store.write(JSONEncoder().encode(value),to:engine.store.root.appendingPathComponent("image-search-settings.json"))
            return ["status":"image_search_configured","settings":try Tracing.object(value),"model":"google/embeddinggemma-2","revision":modelRevision,
                    "verification":"Optional local backend configuration only; no UI input or model download was performed"]
        case "status":
            try a.only(["operation"])
            let value = try settings(engine.store)
            return ["status":"image_search_status","settings":try Tracing.object(value),"visionKitSupported":ImageAnalyzer.isSupported,
                    "model":"google/embeddinggemma-2","revision":modelRevision,"modelLoaded":false,
                    "runtime":"A bounded local worker runs only on cache misses and exits after each request"]
        case "cache_clear":
            try a.only(["operation"])
            let names = try engine.store.names(prefix:"embedding-").filter { name in
                name.hasSuffix(".json") && (try? EmbeddingCache.name(String(name.dropFirst(10).dropLast(5)))) == name
            }
            for name in names { try engine.store.remove(name) }
            return ["status":"image_cache_cleared","count":names.count]
        case "search": return try await search(a,engine:engine)
        default: throw ToolFailure("invalid_argument","operation must be configure, status, search or cache_clear")
        }
    }
}
