import AppKit
import ImageIO
import Vision
import VisionKit

private final class AnalysisTask: @unchecked Sendable {
    private let lock = NSLock()
    private var task: Task<Void,Never>?
    private var cancelled = false
    func install(_ value:Task<Void,Never>) { lock.lock(); task = value; let stop = cancelled; lock.unlock(); if stop { value.cancel() } }
    func cancel() { lock.lock(); cancelled = true; let value = task; lock.unlock(); value?.cancel() }
}
private final class RectangleRequest: @unchecked Sendable {
    let request = VNDetectRectanglesRequest()
}

@MainActor extension ImageSearch {
    static func transcript(_ image:CGImage,timeout:Int) async throws -> String {
        let task = AnalysisTask()
        return try await withCallbackDeadline(timeoutMilliseconds:max(1,min(60_000,timeout)),
            timeoutFailure:ToolFailure("visionkit_timeout","VisionKit exceeded the bounded image-search deadline"),
            onTimeout:{task.cancel()},onCancel:{task.cancel()}) { finish in
            let work = Task { @MainActor in
                do {
                    var config = ImageAnalyzer.Configuration(.text); config.locales = ["en-US","ko-KR"]
                    let result = try await ImageAnalyzer().analyze(image,orientation:.up,configuration:config)
                    finish(.success(String(result.transcript.prefix(512))))
                } catch { finish(.failure(error)) }
            }
            task.install(work)
        }
    }
    static func rectangles(_ image:CGImage,timeout:Int) async throws -> [CGRect] {
        let box = RectangleRequest(); box.request.maximumObservations = 64
        box.request.minimumConfidence = 0.6; box.request.minimumSize = 0.02
        box.request.minimumAspectRatio = 0.1; box.request.maximumAspectRatio = 1
        return try await withCallbackDeadline(timeoutMilliseconds:max(1,min(60_000,timeout)),
            timeoutFailure:ToolFailure("image_regions_timeout","Image region proposals exceeded their deadline"),
            onTimeout:{box.request.cancel()},onCancel:{box.request.cancel()}) { finish in
            DispatchQueue.global(qos:.userInitiated).async {
                do {
                    try VNImageRequestHandler(cgImage:image).perform([box.request])
                    let regions = (box.request.results ?? []).map { row -> CGRect in
                        let b = row.boundingBox
                        return CGRect(x:b.minX * Double(image.width),y:(1-b.maxY) * Double(image.height),
                                      width:b.width * Double(image.width),height:b.height * Double(image.height)).integral
                    }
                    finish(.success(regions))
                } catch { finish(.failure(error)) }
            }
        }
    }
    static func overlaps(_ first:CGRect,_ second:CGRect) -> Bool {
        let intersection = first.intersection(second)
        guard !intersection.isNull else { return false }
        let area = intersection.width * intersection.height
        let firstArea = first.width * first.height, secondArea = second.width * second.height
        if area / (firstArea + secondArea - area) > 0.75 { return true }
        let ratio = max(firstArea,secondArea) / min(firstArea,secondArea)
        let distance = hypot(first.midX-second.midX,first.midY-second.midY)
        return area / min(firstArea,secondArea) > 0.95 && ratio <= 16
            && distance < min(first.width,first.height,second.width,second.height) * 0.25
    }
    static func validatedRegions(_ raw:Any,image:CGImage) throws -> [CGRect] {
        guard let rows = raw as? [[String:Any]], (1...24).contains(rows.count) else { throw ToolFailure("invalid_argument","regions must contain 1–24 image-pixel rectangles") }
        return try rows.map { row in
            let a = Arguments(row); try a.only(["x","y","width","height"])
            let rect = try CGRect(x:a.number("x",range:0...Double(image.width)),y:a.number("y",range:0...Double(image.height)),
                                  width:a.number("width",range:1...Double(image.width)),height:a.number("height",range:1...Double(image.height))).integral
            guard rect.minX >= 0, rect.minY >= 0, rect.maxX <= Double(image.width), rect.maxY <= Double(image.height) else {
                throw ToolFailure("invalid_argument","A search region extends beyond the observed image")
            }
            return rect
        }
    }
    static func search(_ a:Arguments,engine:Engine) async throws -> [String:Any] {
        try a.only(["operation","observation","query","templatePath","regions","maxCandidates","minimumScore","minimumMargin","timeoutMs"])
        let configuration = try settings(engine.store)
        guard configuration.enabled else { throw ToolFailure("image_search_disabled","Optional image search is disabled; explicitly configure its local backend first") }
        guard ImageAnalyzer.isSupported else { throw ToolFailure("visionkit_unavailable","VisionKit image analysis is unavailable") }
        guard try fingerprint(configuration) == configuration.fingerprint else { throw ToolFailure("image_configuration_changed","The pinned model or worker changed; explicitly configure it again") }
        guard (a.values["query"] != nil) != (a.values["templatePath"] != nil) else { throw ToolFailure("invalid_argument","Supply exactly one text query or explicit templatePath") }
        let query = try a.values["query"].map { _ in try a.string("query",limit:4096) }
        if let query, query.trimmingCharacters(in:.whitespacesAndNewlines).isEmpty { throw ToolFailure("invalid_argument","query must not be empty") }
        let maximum = try a.integer("maxCandidates",default:24,range:1...24)
        let minimum = try a.number("minimumScore",default:0.65,range:0...1)
        let margin = try a.number("minimumMargin",default:0.05,range:0.001...1)
        let timeout = try a.integer("timeoutMs",default:25000,range:100...28000)
        let started = DispatchTime.now().uptimeNanoseconds, deadline = started + UInt64(timeout) * 1_000_000
        func remaining() throws -> Int {
            try Task.checkCancellation()
            let now = DispatchTime.now().uptimeNanoseconds
            guard now < deadline else { throw ToolFailure("image_search_timeout","Image search exceeded its deadline; no UI input was sent") }
            return max(1,Int((deadline-now)/1_000_000))
        }
        let observation = try engine.fresh(a), image = try engine.store.image(for:observation)
        var proposed: [(CGRect,String,String?)] = []
        if let raw = a.values["regions"] {
            proposed = try validatedRegions(raw,image:image).map { ($0,"explicit_region",nil) }
        } else {
            let sx = Double(image.width) / observation.windowFrame.width, sy = Double(image.height) / observation.windowFrame.height
            let bounds = CGRect(x:0,y:0,width:image.width,height:image.height)
            for node in observation.nodes where !node.secure && ["AXButton","AXImage","AXCheckBox","AXRadioButton","AXMenuItem"].contains(node.role) {
                guard let frame = node.frame else { continue }
                let rect = CGRect(x:(frame.x-observation.windowFrame.x)*sx,y:(frame.y-observation.windowFrame.y)*sy,
                                  width:frame.width*sx,height:frame.height*sy).integral
                if rect.width >= 8, rect.height >= 8, bounds.contains(rect) { proposed.append((rect,"observed_ax_frame",node.id)) }
            }
            // Chrome/window controls can expose AX frames while the content is
            // entirely custom-drawn. Those frames do not cover the content.
            do {
                let regions = try await rectangles(image,timeout:min(3000,remaining()))
                proposed += regions.filter { $0.width >= 8 && $0.height >= 8 && $0.width*$0.height < Double(image.width*image.height)*0.6 }
                    .sorted{$0.width*$0.height > $1.width*$1.height}.map { ($0,"vision_rectangle",nil) }
            }
        }
        var selected: [(CGRect,String,String?)] = []
        for candidate in proposed where !selected.contains(where:{overlaps($0.0,candidate.0)}) { selected.append(candidate) }
        let truncated = selected.count > maximum; selected = Array(selected.prefix(maximum))
        guard !selected.isEmpty else { throw ToolFailure("image_no_candidates","No candidate regions were proposed; this does not prove the target is absent. Supply explicit regions or use native AX/DOM tools") }
        let runID = UUID().uuidString.lowercased()
        var scratch: [String] = []
        defer { for name in scratch { try? engine.store.remove(name) } }
        var vectors: [String:[Double]] = [:], requests: [String:[String:Any]] = [:], cacheHits = 0
        let namespace = configuration.fingerprint! + ":image-search/1:"
        func key(_ kind:String,_ data:Data) -> String { EmbeddingCache.hash(Data((namespace+kind+":").utf8)+data) }
        func request(_ id:String,_ value:[String:Any]) {
            if vectors[id] != nil || requests[id] != nil { return }
            if let cached = EmbeddingCache.read(id,store:engine.store) { vectors[id] = cached; cacheHits += 1 }
            else { requests[id] = value.merging(["id":id]) { _,new in new } }
        }
        var candidates: [SearchCandidate] = []
        for (i,region) in selected.enumerated() {
            _ = try remaining()
            guard let crop = image.cropping(to:region.0) else { throw ToolFailure("image_crop_failed","A proposed crop is outside the observed image") }
            let bytes = try Capture.png(crop), name = "image-crop-\(runID)-\(i).png"
            try engine.store.write(bytes,to:engine.store.root.appendingPathComponent(name)); scratch.append(name)
            let imageKey = key("image",bytes)
            request(imageKey,["kind":"image","path":engine.store.root.appendingPathComponent(name).path])
            let transcript = try await transcript(crop,timeout:min(2000,remaining()))
            var textKey: String?
            if query != nil, !transcript.trimmingCharacters(in:.whitespacesAndNewlines).isEmpty {
                textKey = key("document",Data(transcript.utf8)); request(textKey!,["kind":"document","text":transcript])
            }
            candidates.append(SearchCandidate(rect:region.0,source:region.1,nodeID:region.2,transcript:transcript,imageKey:imageKey,textKey:textKey))
        }
        let queryKey: String
        if let query { queryKey = key("query",Data(query.utf8)); request(queryKey,["kind":"query","text":query]) }
        else {
            let path = try SystemActions.explicitFileURLs([a.string("templatePath",limit:4096)],key:"templatePath",mustExist:true,rejectRoot:true)[0]
            let size = try FileManager.default.attributesOfItem(atPath:path.path)[.size] as? NSNumber
            guard size?.intValue ?? Int.max <= 16_777_216,
                  let source = CGImageSourceCreateWithURL(path as CFURL,[kCGImageSourceShouldCache:false] as CFDictionary),
                  CGImageSourceGetCount(source) == 1,
                  let properties = CGImageSourceCopyPropertiesAtIndex(source,0,nil) as? [CFString:Any],
                  let width = (properties[kCGImagePropertyPixelWidth] as? NSNumber)?.intValue,
                  let height = (properties[kCGImagePropertyPixelHeight] as? NSNumber)?.intValue,
                  width > 0, height > 0, width <= ImageSafety.maximumDimension, height <= ImageSafety.maximumDimension,
                  width <= ImageSafety.maximumPixels / height,
                  let template = CGImageSourceCreateImageAtIndex(source,0,[kCGImageSourceShouldCache:false] as CFDictionary),
                  template.width == width, template.height == height else { throw ToolFailure("invalid_image_template","Template must be a bounded single-frame local image") }
            try ImageSafety.validateDecoded(template,failureCode:"invalid_image_template",description:"Template exceeds image safety limits")
            let data = try Capture.png(template), name = "image-query-\(runID).png"
            try engine.store.write(data,to:engine.store.root.appendingPathComponent(name)); scratch.append(name)
            queryKey = key("image",data); request(queryKey,["kind":"image","path":engine.store.root.appendingPathComponent(name).path])
        }
        let requestedKeys = Set(requests.keys)
        var modelStatistics: [String:Any] = ["cacheOnly":requests.isEmpty]
        if !requests.isEmpty {
            let response = try await worker(["operation":"embed","items":requests.keys.sorted().compactMap{requests[$0]}],
                                            configuration:configuration,store:engine.store,timeout:remaining())
            guard response["status"] as? String == "embedded", let rows = response["vectors"] as? [[String:Any]], rows.count == requests.count else {
                throw ToolFailure("image_backend_protocol","The model did not return one vector per requested item")
            }
            var received = Set<String>()
            for row in rows {
                guard let id = row["id"] as? String, requestedKeys.contains(id), received.insert(id).inserted,
                      let values = row["vector"] as? [NSNumber], values.allSatisfy({CFGetTypeID($0) != CFBooleanGetTypeID()}),
                      EmbeddingMath.valid(values.map(\.doubleValue)) else { throw ToolFailure("invalid_embedding","Model vector shape, identity or normalization is invalid") }
                vectors[id] = values.map(\.doubleValue)
            }
            guard received == requestedKeys else { throw ToolFailure("image_backend_protocol","The model response is incomplete") }
            for id in received { try EmbeddingCache.save(id,vector:vectors[id]!,store:engine.store) }
            modelStatistics = ["cacheOnly":false,"loadMilliseconds":response["loadMilliseconds"] ?? 0,"inferenceMilliseconds":response["inferenceMilliseconds"] ?? 0]
        }
        guard let queryVector = vectors[queryKey] else { throw ToolFailure("invalid_embedding","No query vector is available") }
        var ranked: [(SearchCandidate,Double)] = []
        for candidate in candidates {
            let imageScore = try EmbeddingMath.cosine(queryVector,vectors[candidate.imageKey]!)
            let score: Double
            if query != nil, let textKey = candidate.textKey { score = try imageScore*0.75 + EmbeddingMath.cosine(queryVector,vectors[textKey]!)*0.25 }
            else { score = imageScore }
            ranked.append((candidate,score))
        }
        ranked.sort{$0.1 > $1.1}
        _ = try engine.fresh(Arguments(["observation":observation.id]))
        let current = try await Capture.image(windowID:observation.windowID,timeoutMilliseconds:max(100,min(3000,remaining())))
        // ROI callers explicitly scope stability to those regions; otherwise require the entire selected image to be unchanged.
        if a.values["regions"] != nil {
            for candidate in candidates {
                guard let latest = current.cropping(to:candidate.rect), let original = image.cropping(to:candidate.rect),
                      try Capture.hash(latest) == Capture.hash(original) else { throw ToolFailure("image_changed_during_search","A selected image region changed; observe again before deciding") }
            }
        } else if try Capture.hash(current) != observation.screenshotSHA256 {
            throw ToolFailure("image_changed_during_search","The selected image changed during inference; observe again before deciding")
        }
        _ = try remaining()
        _ = try engine.fresh(Arguments(["observation":observation.id]))
        try ProcessIdentity.require(pid:observation.pid,expected:observation.processStartID)
        let accepted = EmbeddingMath.accepted(scores:ranked.map(\.1),minimum:minimum,margin:margin)
        let best = ranked[0].1, second = ranked.count > 1 ? ranked[1].1 : nil
        let resultRows: [[String:Any]] = ranked.prefix(5).map { candidate,score in
            var row: [String:Any] = ["imageRect":Rect(candidate.rect).object,"score":score,"source":candidate.source,"text":candidate.transcript]
            if let nodeID = candidate.nodeID { row["node"] = nodeID }; return row
        }
        return ["status":accepted ? "image_candidate_found" : "image_search_abstained", "accepted":accepted,
                "observation":observation.id,"sourceSHA256":observation.screenshotSHA256 ?? "", "candidateCount":candidates.count,
                "candidateCoverage":"Proposed or explicitly selected regions only; no claim of whole-UI target absence",
                "proposalsTruncated":truncated,"candidates":resultRows,"minimumScore":minimum,"minimumMargin":margin,
                "margin":second.map{best-$0} ?? 1,"cacheHits":cacheHits,"vectorsComputed":requestedKeys.count,"model":modelStatistics,
                "elapsedMilliseconds":Int((DispatchTime.now().uptimeNanoseconds-started)/1_000_000),
                "verification":"Selected pixels were unchanged at the final check. Similarity is not probability or task success. No click was sent; reobserve and verify the target before input."]
    }
}
