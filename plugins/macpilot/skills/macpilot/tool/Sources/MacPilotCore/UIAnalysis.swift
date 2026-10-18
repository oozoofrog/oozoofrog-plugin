import AppKit
import ApplicationServices

// Read-only analysis stays on the same native AX, identity and observation path as input.
// No AX wrapper package, external executable, LLM, or simulator-private driver is used.
enum UIAnalysisModel {
    static func object(_ node: Node) -> [String: Any] {
        var result: [String: Any] = ["node":node.id, "path":node.path, "role":node.role,
                                    "subrole":node.subrole, "enabled":node.enabled, "secure":node.secure,
                                    "focused":node.focused, "actions":node.actions,
                                    "identityTruncated":node.identityTruncated == true,
                                    "valueTruncated":node.valueTruncated, "actionsTruncated":node.actionsTruncated == true]
        if let frame = node.frame { result["frame"] = frame.object }
        // Secure providers sometimes repeat their value in a label or description.
        if !node.secure {
            var truncated: [String] = []
            for (key, value) in [("title",node.title),("identifier",node.identifier),("value",node.value),
                                 ("description",node.description),("placeholder",node.placeholder),("help",node.help)] {
                if let value {
                    let bounded = AX.boundedString(value,limit:key == "value" ? 1024 : 512)
                    result[key] = bounded.value
                    if bounded.truncated { truncated.append(key) }
                }
            }
            result["displayTruncatedFields"] = truncated
            result["selected"] = node.selected; result["expanded"] = node.expanded
        }
        return result
    }

    static func isInteractive(_ node: Node) -> Bool {
        node.enabled && (!node.actions.isEmpty || ["AXTextField","AXTextArea","AXComboBox","AXSlider"].contains(node.role))
    }

    static func matches(_ node: Node, query: String) -> Bool {
        guard !node.secure else { return false }
        return [node.title,node.identifier,node.value,node.description,node.help,node.placeholder]
            .compactMap { $0 }.contains { $0.range(of:query,options:.caseInsensitive) != nil }
    }

    static func summarize(_ observation: Observation, query: String?, role: String?, interactiveOnly: Bool,
                          inWindowOnly: Bool, offset: Int, limit: Int) -> [String: Any] {
        var counts: [String: Int] = [:]
        observation.nodes.forEach { counts[$0.role,default:0] += 1 }
        let nodes = observation.nodes.filter { node in
            (query.map { matches(node,query:$0) } ?? true)
            && (role.map { node.role == $0 } ?? true)
            && (!interactiveOnly || isInteractive(node))
            && (!inWindowOnly || node.frame.map { $0.cg.intersects(observation.windowFrame.cg) } == true)
        }
        var page: [[String: Any]] = [], encodedPageBytes = 2
        for node in nodes.dropFirst(offset).prefix(limit) {
            let value = object(node)
            // Budget the encoded bytes, including provider-controlled JSON escapes.
            guard let encoded = try? JSONSerialization.data(withJSONObject:value),
                  encodedPageBytes + encoded.count + 1 <= 384_000 else { break }
            page.append(value); encodedPageBytes += encoded.count + 1
        }
        let roleCounts = Dictionary(uniqueKeysWithValues:counts.keys.sorted().prefix(128).map { ($0,counts[$0]!) })
        var result: [String: Any] = ["status":"ui_analyzed", "observation":observation.id,
            "pid":observation.pid, "processStartID":observation.processStartID, "windowID":observation.windowID,
            "scope":"selected_window_ax", "createdISO8601":ISO8601DateFormatter().string(from:observation.created),
            "coverage":observation.coverage, "diagnostics":observation.diagnostics,
            "totalCollectedNodes":observation.nodes.count, "roleCounts":roleCounts,
            "roleCountsTruncated":counts.count > 128, "distinctCollectedRoles":counts.count,
            "matchedCount":nodes.count, "returnedCount":page.count, "nodes":page,
            "offset":offset, "hasMore":offset + page.count < nodes.count,
            "absenceEstablished":false, "occlusionTested":false, "readOnly":true]
        if offset + page.count < nodes.count { result["nextOffset"] = offset + page.count }
        if let query { result["query"] = query }
        return result
    }

    static func validateRange(start: Int, length: Int, count: Int) throws {
        guard count >= 0, start >= 0, length >= 0, length <= 4096, start <= count, length <= count - start else {
            throw ToolFailure("invalid_text_range", "UTF-16 range exceeds the current AX text length or the 4096-unit read budget")
        }
    }
}

@MainActor enum NativeAXInspection {
    static func names(_ element: AXUIElement, kind: String) -> [String: Any] {
        var raw: CFArray?
        let error: AXError
        switch kind {
        case "attributes": error = AXUIElementCopyAttributeNames(element,&raw)
        case "actions": error = AXUIElementCopyActionNames(element,&raw)
        default: error = AXUIElementCopyParameterizedAttributeNames(element,&raw)
        }
        guard error == .success, let names = raw as? [String] else {
            return ["status":"unavailable", "axError":error.rawValue, "names":[String](), "truncated":false]
        }
        var truncated = names.count > 128
        let bounded = names.prefix(128).map { value in
            let text = AX.boundedString(value,limit:256); truncated = truncated || text.truncated
            return text.value
        }.sorted()
        return ["status":"read", "names":bounded, "truncated":truncated]
    }

    static func characterCount(_ element: AXUIElement) throws -> Int {
        var raw: CFTypeRef?
        let error = AXUIElementCopyAttributeValue(element,kAXNumberOfCharactersAttribute as CFString,&raw)
        guard error == .success, let number = raw as? NSNumber, CFGetTypeID(number) != CFBooleanGetTypeID(),
              number.doubleValue.isFinite, number.doubleValue >= 0, number.doubleValue.rounded() == number.doubleValue,
              number.doubleValue <= Double(Int32.max) else {
            throw ToolFailure("ax_text_unavailable", "AXNumberOfCharacters is unavailable or invalid (AX error \(error.rawValue))")
        }
        return number.intValue
    }

    static func inspect(_ element: AXUIElement, node: Node) -> [String: Any] {
        var settable: [String: Any] = [:]
        for name in [kAXValueAttribute,kAXSelectedTextRangeAttribute,kAXFocusedAttribute,kAXPositionAttribute,kAXSizeAttribute] {
            var value = DarwinBoolean(false)
            let error = AXUIElementIsAttributeSettable(element,name as CFString,&value)
            settable[name] = error == .success ? ["status":"read", "settable":value.boolValue] : ["status":"unavailable", "axError":error.rawValue]
        }
        var rangeInfo: [String: Any] = ["status":"unavailable"]
        var raw: CFTypeRef?
        let rangeError = AXUIElementCopyAttributeValue(element,kAXSelectedTextRangeAttribute as CFString,&raw)
        if rangeError == .success, let raw, CFGetTypeID(raw) == AXValueGetTypeID() {
            var range = CFRange()
            if AXValueGetValue(raw as! AXValue,.cfRange,&range), range.location >= 0, range.length >= 0 {
                rangeInfo = ["status":"read", "start":range.location, "length":range.length, "units":"UTF-16"]
            }
        } else { rangeInfo["axError"] = rangeError.rawValue }
        let countInfo: [String: Any]
        if let count = try? characterCount(element) { countInfo = ["status":"read","count":count,"units":"UTF-16"] }
        else { countInfo = ["status":"unavailable"] }
        return ["status":"ui_inspected", "node":UIAnalysisModel.object(AX.node(element,path:node.path)),
                "attributes":names(element,kind:"attributes"), "actions":names(element,kind:"actions"),
                "parameterizedAttributes":names(element,kind:"parameterized"), "settable":settable,
                "selectedTextRange":rangeInfo,"textLength":countInfo,"readOnly":true]
    }

    static func text(_ element: AXUIElement, start: Int, length: Int) throws -> [String: Any] {
        let count = try characterCount(element)
        try UIAnalysisModel.validateRange(start:start,length:length,count:count)
        var range = CFRange(location:start,length:length)
        guard let parameter = AXValueCreate(.cfRange,&range) else { throw ToolFailure("ax_text_unavailable", "Cannot encode AX text range") }
        var raw: CFTypeRef?
        let error = AXUIElementCopyParameterizedAttributeValue(element,kAXStringForRangeParameterizedAttribute as CFString,parameter,&raw)
        guard error == .success, let value = raw as? String else {
            throw ToolFailure("ax_parameterized_read_failed", "AXStringForRange failed (\(error.rawValue)); no value or clipboard fallback was used")
        }
        guard value.utf16.count <= length, value.utf8.count <= 16_384 else {
            throw ToolFailure("ax_text_range_mismatch", "AXStringForRange exceeded the requested range")
        }
        guard try characterCount(element) == count else { throw ToolFailure("ax_text_changed", "AX text length changed during the read; reobserve") }
        return ["status":"ui_text_read", "attribute":"AXStringForRange", "text":value, "start":start,
                "length":length, "returnedUTF16Length":value.utf16.count, "totalUTF16Length":count,
                "rangeUnits":"UTF-16", "rangeComplete":value.utf16.count == length,"atomicSnapshot":false, "readOnly":true]
    }

    static func layout(_ element: AXUIElement, attribute: String, start: Int, length: Int) throws -> [String:Any] {
        let count = try characterCount(element)
        var range = CFRange(location:start,length:length)
        let name: String
        let parameter: CFTypeRef
        switch attribute {
        case "bounds_for_range":
            try UIAnalysisModel.validateRange(start:start,length:length,count:count)
            guard let value = AXValueCreate(.cfRange,&range) else { throw ToolFailure("ax_text_unavailable","Cannot encode range") }
            parameter = value; name = "AXBoundsForRange"
        case "line_for_index":
            try UIAnalysisModel.validateRange(start:start,length:0,count:count)
            parameter = NSNumber(value:start); name = "AXLineForIndex"
        case "range_for_line":
            parameter = NSNumber(value:start); name = "AXRangeForLine"
        default: throw ToolFailure("invalid_argument","Unknown text layout attribute")
        }
        var raw: CFTypeRef?
        let error = AXUIElementCopyParameterizedAttributeValue(element,name as CFString,parameter,&raw)
        guard error == .success, let raw else { throw ToolFailure("ax_parameterized_read_failed","\(name) failed (\(error.rawValue))") }
        var result: [String:Any] = ["status":"ui_layout_read","attribute":name,"readOnly":true,"atomicSnapshot":false]
        if name == "AXLineForIndex", let value = raw as? NSNumber, CFGetTypeID(value) != CFBooleanGetTypeID(),
           value.doubleValue.isFinite, value.doubleValue >= 0, value.doubleValue <= Double(count), value.doubleValue.rounded() == value.doubleValue {
            result["line"] = value.intValue
        } else if CFGetTypeID(raw) == AXValueGetTypeID() {
            let value = raw as! AXValue
            if name == "AXBoundsForRange", AXValueGetType(value) == .cgRect {
                var rect = CGRect.zero
                guard AXValueGetValue(value,.cgRect,&rect), [rect.origin.x,rect.origin.y,rect.width,rect.height].allSatisfy({$0.isFinite}),rect.width >= 0,rect.height >= 0 else { throw ToolFailure("ax_layout_invalid","Invalid bounds") }
                result["bounds"] = Rect(rect).object; result["coordinateSystem"] = "AX global logical points"
            } else if name == "AXRangeForLine", AXValueGetType(value) == .cfRange {
                var selected = CFRange()
                guard AXValueGetValue(value,.cfRange,&selected), selected.location >= 0,selected.length >= 0,selected.location <= count,selected.length <= count-selected.location else { throw ToolFailure("ax_layout_invalid","Invalid line range") }
                result["start"] = selected.location; result["length"] = selected.length; result["rangeUnits"] = "UTF-16"
            } else { throw ToolFailure("ax_layout_invalid","Unexpected AXValue type") }
        } else { throw ToolFailure("ax_layout_invalid","Unexpected result type") }
        guard try characterCount(element) == count else { throw ToolFailure("ax_text_changed","Text length changed during layout read") }
        return result
    }

    static func hit(_ observation: Observation, point: CGPoint) throws -> [String: Any] {
        guard observation.windowFrame.cg.contains(point) else { throw ToolFailure("outside_window", "Hit test is restricted to the observed window") }
        var raw: AXUIElement?
        let error = AXUIElementCopyElementAtPosition(AX.app(observation.pid),Float(point.x),Float(point.y),&raw)
        guard error == .success, let found = raw else { throw ToolFailure("ax_hit_unavailable", "AX hit test failed (\(error.rawValue))") }
        var pid: pid_t = 0
        guard AXUIElementGetPid(found,&pid) == .success, pid == observation.pid else { throw ToolFailure("ax_hit_target_mismatch", "Hit test returned a different process") }
        let actual = AX.node(found,path:[])
        guard !actual.secure else { throw ToolFailure("invalid_node", "Hit test found a secure element") }
        let candidates = observation.nodes.filter { !$0.secure && $0.identity == actual.identity && $0.frame == actual.frame }
        guard candidates.count == 1, let candidate = candidates.first else {
            return ["status":"ui_hit_unmapped", "candidateCount":candidates.count, "matched":false,
                    "observation":observation.id, "readOnly":true]
        }
        let resolved = try AX.resolve(observation,nodeID:candidate.id,requireEnabled:false,requireStableValue:false)
        guard CFEqual(found,resolved) else { throw ToolFailure("stale_observation", "Hit test no longer corresponds to the observed node") }
        return ["status":"ui_hit", "matched":true, "node":UIAnalysisModel.object(actualWithID(actual,candidate)),
                "observation":observation.id, "readOnly":true]
    }

    private static func actualWithID(_ actual: Node, _ expected: Node) -> Node {
        var node = actual; node.id = expected.id; node.path = expected.path; return node
    }
}

@MainActor extension Engine {
    func analyzeUI(_ arguments: Arguments) async throws -> [String: Any] {
        let operation = try arguments.string("operation",default:"summary",limit:32)
        switch operation {
        case "summary", "search":
            try arguments.only(["observation","operation","query","role","interactiveOnly","inWindowOnly","offset","limit","maxNodes","maxDepth"])
            let query = try arguments.values["query"].map { _ in try arguments.string("query",limit:512) }
            if operation == "search", query?.isEmpty != false { throw ToolFailure("invalid_argument", "search requires a nonempty literal query") }
            let role = try arguments.values["role"].map { _ in try arguments.string("role",limit:128) }
            let interactive = try arguments.bool("interactiveOnly"), inWindow = try arguments.bool("inWindowOnly")
            let offset = try arguments.integer("offset",default:0,range:0...1000)
            let limit = try arguments.integer("limit",default:50,range:1...100)
            let maxNodes = try arguments.integer("maxNodes",default:500,range:1...1000)
            let maxDepth = try arguments.integer("maxDepth",default:20,range:1...30)
            let seed = try fresh(arguments)
            let current = try await observe(pid:seed.pid,processStartID:seed.processStartID,windowID:seed.windowID,
                screenshot:false,maxNodes:maxNodes,maxDepth:maxDepth,privateAPI:seed.windowIdentityBackend == "_AXUIElementGetWindow")
            _ = try fresh(Arguments(["observation":current.id]))
            try Task.checkCancellation()
            var result = UIAnalysisModel.summarize(current,query:query,role:role,interactiveOnly:interactive,
                                                   inWindowOnly:inWindow,offset:offset,limit:limit)
            result["sourceObservation"] = seed.id
            return result
        case "inspect", "read_text", "text_layout":
            try arguments.only(operation == "inspect" ? ["observation","operation","node"] : ["observation","operation","node","start","length","attribute"])
            let nodeID = try arguments.string("node",limit:128)
            let start = operation != "inspect" ? try arguments.integer("start",range:0...Int(Int32.max)) : 0
            let length = operation == "read_text" ? try arguments.integer("length",range:0...4096) : 0
            let observation = try fresh(arguments)
            guard let expected = observation.nodes.first(where: { $0.id == nodeID }) else { throw ToolFailure("invalid_node", "Node is absent") }
            let element = try AX.resolve(observation,nodeID:nodeID,requireEnabled:false,requireStableValue:false)
            var result: [String:Any]
            if operation == "inspect" { result = NativeAXInspection.inspect(element,node:expected) }
            else if operation == "text_layout" {
                result = try NativeAXInspection.layout(element,attribute:arguments.string("attribute",limit:32),start:start,
                    length:arguments.integer("length",default:0,range:0...4096))
            } else { result = try NativeAXInspection.text(element,start:start,length:length) }
            _ = try fresh(arguments)
            _ = try AX.resolve(observation,nodeID:nodeID,requireEnabled:false,requireStableValue:false)
            try Task.checkCancellation()
            result["observation"] = observation.id; result["pid"] = observation.pid; result["windowID"] = observation.windowID
            return result
        case "hit_test":
            try arguments.only(["observation","operation","x","y"])
            let point = CGPoint(x:try arguments.number("x"),y:try arguments.number("y"))
            let observation = try fresh(arguments)
            let result = try NativeAXInspection.hit(observation,point:point)
            _ = try fresh(arguments)
            try Task.checkCancellation()
            return result
        default: throw ToolFailure("invalid_argument", "Unknown UI analysis operation")
        }
    }
}
