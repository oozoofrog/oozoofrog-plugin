import Foundation
import ApplicationServices

enum AXCoverage: String, Codable { case complete, partial, unknown }
struct AXMetrics: Codable {
    var attributeCalls = 0, batchCalls = 0, childCountCalls = 0, childPageCalls = 0, actionCalls = 0, textRangeCalls = 0
    var observerCalls = 0
    var observerHints = 0
    var collectionMS = 0.0
    var ipcCalls: Int { attributeCalls + batchCalls + childCountCalls + childPageCalls + actionCalls + textRangeCalls + observerCalls }
}
struct AXRegion: Codable {
    var handle: String; var context: String; var offset: Int; var total: Int?; var depth: Int; var descendantPending: Int = 0
}
struct AXOverview: Codable {
    var revision: String; var coverage: AXCoverage; var scanned: Int; var pending: Int
    var regions: [AXRegion]; var roleCounts: [String: Int]; var metrics: AXMetrics
    var unresolvedReason: String?
}
struct AXFilter: Codable {
    var role: String? = nil; var nameContains: String? = nil; var action: String? = nil
    var enabled: Bool? = nil; var selected: Bool? = nil; var checked: Bool? = nil; var focused: Bool? = nil
    var ancestorContains: String? = nil
    func matches(_ node: Node) -> Bool {
        if let role, node.role != role { return false }
        if let nameContains, !node.title.localizedCaseInsensitiveContains(nameContains) { return false }
        if let action, !node.actions.contains(action) { return false }
        if let enabled, node.enabled != enabled { return false }
        if let selected, node.selected != selected { return false }
        if let checked, node.checked != checked { return false }
        if let focused, node.focused != focused { return false }
        if let ancestorContains, !(node.ancestors ?? []).contains(where: { $0.localizedCaseInsensitiveContains(ancestorContains) }) { return false }
        return true
    }
}
struct AXQueryPage: Codable { var nodes: [Node]; var coverage: AXCoverage; var scanned: Int; var cursor: String?; var overview: AXOverview }
struct AXTextRange: Codable, Equatable { var location: Int; var length: Int }
enum AXReadField: String, Codable { case metadata, value, selectedText }
struct AXReadResult: Codable { var handle: String; var node: Node?; var value: String?; var selectedText: String?; var rangeUTF16: AXTextRange? }
struct AXChanges: Codable { var since: String; var revision: String; var coverage: AXCoverage; var changed: [String]; var invalidated: Bool }

// The engine owns traversal, filtering, pagination and evidence boundaries. Providers own IPC.
@MainActor protocol AXSource: AnyObject {
    var metrics: AXMetrics { get set }
    func nativeParent(_ ref: String) -> String?
    func metadata(_ ref: String) -> Node?
    func childCount(_ ref: String) -> Int?
    func children(_ ref: String, offset: Int, count: Int) -> [String]?
    func text(_ ref: String, range: AXTextRange?) throws -> String
    func selectedText(_ ref: String) -> String
}

@MainActor extension AXSource { func nativeParent(_ ref: String) -> String? { nil } }

@MainActor final class AXStore {
    let source: AXSource
    private(set) var revision = UUID().uuidString
    private(set) var nodes: [Node] = []
    private var nativeParentRefs: [String:String] = [:]
    private var refs: [String: String] = [:], handles: [String: String] = [:]
    private var frontier: [AXRegion] = []
    private var visited: Set<String> = []
    private var incomplete = false
    private(set) var requiresRefresh = false
    private var cursors: [String:(String,Int)] = [:]
    private var changesFrom: String?
    private var changed: [String] = []
    private var locators: [String: String] = [:]
    private let maxDepth = 64
    init(source: AXSource) { self.source = source }
    func begin(roots: [(String, String)], budget: Int = 160) {
        revision = UUID().uuidString; nodes = []; refs = [:]; handles = [:]; frontier = []; visited = []; locators = [:]; incomplete = false; nativeParentRefs=[:]; requiresRefresh=false; cursors=[:]; changesFrom=nil; changed=[]
        for (ref, path) in roots { insert(ref, parent: nil, path: path, ancestors: [], depth: 0) }
        collect(budget: max(0, budget - nodes.count))
    }
    private func insert(_ ref: String, parent: String?, path: String, ancestors: [String], depth: Int) {
        guard visited.insert(ref).inserted else { return }
        guard var node = source.metadata(ref) else { incomplete = true; return }
        // Secure elements and their descendants never enter the store.
        guard node.subrole != "AXSecureTextField" else { return }
        let handle = revision + ":" + UUID().uuidString
        refs[handle] = ref; handles[ref] = handle; locators[ref] = path; nativeParentRefs[handle]=source.nativeParent(ref)
        node.id = handle; node.locator = path; node.parent = parent; node.ancestors = ancestors
        nodes.append(node)
        let count = source.childCount(ref)
        if count != 0 {
            if depth < maxDepth { frontier.append(AXRegion(handle: handle, context: (ancestors + [node.title.isEmpty ? node.role : node.title]).suffix(4).joined(separator: " > "), offset: 0, total: count, depth: depth)) }
            else { incomplete = true }
        }
    }
    private func collect(budget: Int, preferred: String? = nil) {
        let start = Date(); var remaining = max(0, budget)
        let preferredPath=preferred.flatMap { id in nodes.first { $0.id == id }?.locator }
        while remaining > 0, !frontier.isEmpty {
            let preferredIndex=preferredPath.flatMap { path in frontier.firstIndex { region in nodes.first(where: { $0.id == region.handle }).map { $0.locator == path || $0.locator?.hasPrefix(path+".") == true } ?? false } }
            if preferredPath != nil && preferredIndex == nil { break }
            var region = frontier.remove(at:preferredIndex ?? 0)
            guard let ref = refs[region.handle], let parent = nodes.first(where: { $0.id == region.handle }) else { incomplete = true; continue }
            let size = min(32, remaining, region.total.map { max(0, $0-region.offset) } ?? 32)
            if size == 0 { continue }
            guard let children = source.children(ref, offset: region.offset, count: size) else { incomplete = true; continue }
            if children.isEmpty { if let total = region.total, region.offset < total { incomplete = true }; continue }
            for (index, child) in children.enumerated() {
                insert(child, parent: region.handle, path: (locators[ref] ?? "") + ".\(region.offset + index)", ancestors: (parent.ancestors ?? []) + [parent.title.isEmpty ? parent.role : parent.title], depth: region.depth + 1)
                remaining -= 1
            }
            region.offset += children.count
            if region.total.map({ region.offset < $0 }) ?? (children.count == size) { frontier.append(region) }
            else if region.total == nil { /* Indexed enumeration exhausted the exposed array. */ }
        }
        source.metrics.collectionMS += milliseconds(start)
    }
    private func compressedRegions() -> [AXRegion] {
        var grouped:[String:AXRegion]=[:],order:[String]=[]
        for raw in frontier {
            var region=raw
            if let node=nodes.first(where:{$0.id==raw.handle}), node.role == "AXUnknown", raw.total == 1,
               let parentID=node.parent, let parent=nodes.first(where:{$0.id==parentID}) {
                region=AXRegion(handle:parentID,context:((parent.ancestors ?? [])+[parent.title.isEmpty ? parent.role : parent.title]).suffix(4).joined(separator:" > "),offset:0,total:nil,depth:max(0,raw.depth-1),descendantPending:1)
            }
            if var existing=grouped[region.handle] { existing.descendantPending += region.descendantPending; if region.total != nil { existing.offset=region.offset;existing.total=region.total };grouped[region.handle]=existing }
            else { grouped[region.handle]=region;order.append(region.handle) }
        }
        return order.compactMap { grouped[$0] }
    }
    func overview() -> AXOverview {
        AXOverview(revision: revision, coverage: !frontier.isEmpty ? .partial : (incomplete ? .unknown : .complete), scanned: nodes.count, pending: frontier.count, regions: compressedRegions(), roleCounts: Dictionary(grouping: nodes, by: \.role).mapValues(\.count), metrics: source.metrics, unresolvedReason: incomplete ? "Some attributes/children failed or the depth bound was reached; exposed AX coverage is unknown. Virtualized/unexposed content requires scroll/open/vision." : nil)
    }
    func expand(_ handle: String?, budget: Int = 160) throws -> AXOverview {
        if let handle { guard refs[handle] != nil, compressedRegions().contains(where: { $0.handle == handle }) else { throw Failure("Expired AX region or no pending children") } }
        collect(budget: min(max(budget, 1), 1024), preferred: handle); return overview()
    }
    func find(_ filter: AXFilter, cursor: String? = nil, limit: Int = 80) throws -> AXQueryPage {
        let matches = nodes.filter(filter.matches)
        let binding="find:" + String(decoding:try jsonData(filter),as:UTF8.self)
        let offset = try cursorOffset(cursor,binding:binding)
        let page = Array(matches.dropFirst(offset).prefix(min(max(limit, 1), 160)))
        return AXQueryPage(nodes: page, coverage: overview().coverage, scanned: nodes.count, cursor: offset+page.count < matches.count ? makeCursor(offset+page.count,binding:binding) : nil, overview: overview())
    }
    private func makeCursor(_ offset: Int, binding: String) -> String { let cursor=revision+":"+UUID().uuidString; cursors[cursor]=(binding,offset); return cursor }
    private func cursorOffset(_ cursor: String?, binding: String) throws -> Int {
        guard let cursor else { return 0 }
        guard let (saved,offset)=cursors[cursor], saved==binding else { throw Failure("Expired or mismatched AX cursor scope/filter") }
        return offset
    }
    func children(_ handle: String, cursor: String? = nil, limit: Int = 32) throws -> AXQueryPage {
        guard let ref = refs[handle] else { throw Failure("Expired AX handle") }
        let binding="children:"+handle
        let offset = try cursorOffset(cursor,binding:binding), count = min(max(limit,1),160)
        guard let children = source.children(ref, offset: offset, count: count), let parent = nodes.first(where: { $0.id == handle }) else { throw Failure("AX children unavailable") }
        for (index, child) in children.enumerated() { insert(child, parent:handle,path:(locators[ref] ?? "") + ".\(offset+index)",ancestors:(parent.ancestors ?? [])+[parent.title.isEmpty ? parent.role : parent.title],depth:(locators[ref]?.filter { $0 == "." }.count ?? 0)+1) }
        let total = source.childCount(ref)
        let next = total.map { offset+children.count < $0 } ?? (children.count == count)
        return AXQueryPage(nodes: children.compactMap { handles[$0] }.compactMap { id in nodes.first { $0.id == id } }, coverage: total == nil ? .unknown : (next ? .partial : .complete), scanned: children.count, cursor: next ? makeCursor(offset+children.count,binding:binding) : nil, overview: overview())
    }
    func read(_ handle: String, fields: [AXReadField], textRangeUTF16: AXTextRange? = nil) throws -> AXReadResult {
        guard let ref = refs[handle] else { throw Failure("Expired AX handle") }
        if let r = textRangeUTF16 { guard r.location >= 0, r.length >= 0, r.location <= Int.max-r.length else { throw Failure("Invalid UTF-16 range") } }
        return AXReadResult(handle:handle,node:fields.contains(.metadata) ? nodes.first { $0.id == handle } : nil,value:fields.contains(.value) ? try source.text(ref,range:textRangeUTF16) : nil,selectedText:fields.contains(.selectedText) ? source.selectedText(ref) : nil,rangeUTF16:textRangeUTF16)
    }
    // Notification hints refresh only the affected loaded subtree. Unknown/root hints force fallback.
    func invalidate(ref: String?) {
        let previous = revision
        guard let ref, let handle = handles[ref], let node = nodes.first(where: { $0.id == handle }), let parent = node.parent, let parentRef = refs[parent] else { revision=UUID().uuidString; nodes=[]; refs=[:]; handles=[:]; frontier=[]; visited=[]; locators=[:]; cursors=[:]; nativeParentRefs=[:]; changesFrom = previous; changed = []; incomplete = true; requiresRefresh=true; return }
        let prefix = (node.locator ?? "")
        let removed = nodes.filter { $0.locator == prefix || $0.locator?.hasPrefix(prefix + ".") == true }
        let ids = Set(removed.map(\.id))
        for id in ids { nativeParentRefs.removeValue(forKey:id); if let sourceRef = refs.removeValue(forKey:id) { handles.removeValue(forKey:sourceRef); visited.remove(sourceRef); locators.removeValue(forKey:sourceRef) } }
        nodes.removeAll { ids.contains($0.id) }; frontier.removeAll { ids.contains($0.handle) }
        if !frontier.contains(where: { $0.handle == parent }) { frontier.insert(AXRegion(handle:parent,context:(node.ancestors ?? []).joined(separator:" > "),offset:0,total:source.childCount(parentRef),depth:max(0,(node.ancestors ?? []).count-1)),at:0) }
        changesFrom = previous; changed = [prefix]
        // Every external handle/cursor expires, even though unaffected local refs remain retained.
        let newRevision = UUID().uuidString
        let mapping = Dictionary(uniqueKeysWithValues: nodes.map { ($0.id,newRevision + ":" + UUID().uuidString) })
        nativeParentRefs=Dictionary(uniqueKeysWithValues:nativeParentRefs.compactMap { key,value in mapping[key].map { ($0,value) } })
        for index in nodes.indices { let old = nodes[index].id; let new = mapping[old]!; nodes[index].id = new; nodes[index].parent = nodes[index].parent.flatMap { mapping[$0] }; if let ref = refs.removeValue(forKey:old) { refs[new] = ref; handles[ref] = new } }
        for index in frontier.indices { if let new = mapping[frontier[index].handle] { frontier[index].handle = new } }
        revision = newRevision; cursors=[:]
    }
    func changes(sinceRevision: String) -> AXChanges { AXChanges(since:sinceRevision,revision:revision,coverage:sinceRevision == revision ? overview().coverage : (changesFrom == sinceRevision ? .partial : .unknown),changed:changesFrom == sinceRevision ? changed : [],invalidated:sinceRevision != revision || incomplete) }
    func sourceRef(_ handle: String) -> String? { refs[handle] }
    func nativeParentSnapshot(_ handle: String) -> String? { nativeParentRefs[handle] }
    func validateNativeParent(_ handle: String, currentRef: String) throws {
        guard refs[handle] != nil, let expected=nativeParentRefs[handle], expected==currentRef else { throw Failure("AX native parent changed or handle expired; reobserve") }
    }
}

@MainActor final class LiveAXSource: AXSource {
    var metrics = AXMetrics()
    private var refs: [String: AXUIElement] = [:]
    private var order: [String] = []
    private var hashBuckets: [CFHashCode:[String]] = [:]
    private(set) var nativeParents: [String:AXUIElement] = [:]
    private(set) var exactAttributes: [String: [String: Any]] = [:]
    let pid: Int32; let windowID: UInt32?
    init(pid: Int32, windowID: UInt32?) { self.pid = pid; self.windowID = windowID }
    func register(_ element: AXUIElement) -> String {
        let hash=CFHash(element)
        if let id = hashBuckets[hash]?.first(where: { CFEqual(refs[$0]!,element) }) { return id }
        let id = UUID().uuidString; refs[id] = element; order.append(id); hashBuckets[hash,default:[]].append(id); return id
    }
    func element(_ ref: String) -> AXUIElement? { refs[ref] }
    func nativeParent(_ ref: String) -> String? { nativeParents[ref].map(register) }
    private func one(_ element: AXUIElement, _ name: String) -> CFTypeRef? { metrics.attributeCalls += 1; var value: CFTypeRef?; guard AXUIElementCopyAttributeValue(element,name as CFString,&value) == .success else { return nil }; return value }
    func metadata(_ ref: String) -> Node? {
        guard let e = refs[ref] else { return nil }
        let names = [kAXRoleAttribute,kAXSubroleAttribute,kAXTitleAttribute,kAXDescriptionAttribute,kAXHelpAttribute,kAXEnabledAttribute,kAXFocusedAttribute,kAXPositionAttribute,kAXSizeAttribute,kAXSelectedAttribute,kAXParentAttribute]
        metrics.batchCalls += 1
        var values: CFArray?
        guard AXUIElementCopyMultipleAttributeValues(e,names as CFArray,[],&values) == .success, let array = values as? [Any], array.count == names.count else { return nil }
        var attrs: [String:Any] = [:]
        for (name,value) in zip(names,array) { if CFGetTypeID(value as CFTypeRef) != AXValueGetTypeID() || AXValueGetType(value as! AXValue) != .axError { if !(value is NSNull) { attrs[name] = value } } }
        let role = attrs[kAXRoleAttribute] as? String ?? "", subrole = attrs[kAXSubroleAttribute] as? String ?? ""
        guard subrole != "AXSecureTextField" else { return Node(id:ref,role:role,title:"",value:"",enabled:false,actions:[],frame:nil,subrole:subrole) }
        var actions: CFArray?; metrics.actionCalls += 1; AXUIElementCopyActionNames(e,&actions)
        var rect: Rect?
        if let p = attrs[kAXPositionAttribute], let s = attrs[kAXSizeAttribute], CFGetTypeID(p as CFTypeRef) == AXValueGetTypeID(), CFGetTypeID(s as CFTypeRef) == AXValueGetTypeID() { var point=CGPoint.zero,size=CGSize.zero; if AXValueGetValue(p as! AXValue,.cgPoint,&point), AXValueGetValue(s as! AXValue,.cgSize,&size) { rect=Rect(x:point.x,y:point.y,width:size.width,height:size.height) } }
        let title = [kAXTitleAttribute,kAXDescriptionAttribute,kAXHelpAttribute].compactMap { attrs[$0] as? String }.filter { !$0.isEmpty }.joined(separator:" | ")
        var value = "", truncated = false, selectedText: String?, textLength: Int?
        if ["AXTextArea","AXTextField","AXComboBox"].contains(role) {
            let count = (one(e,kAXNumberOfCharactersAttribute) as? NSNumber)?.intValue; textLength=count
            if let count, count > 512 { value = Jev.prefixUTF16((try? text(ref,range:AXTextRange(location:0,length:min(count,514)))) ?? "",limit:512); truncated = true }
            else { let raw=one(e,kAXValueAttribute); attrs[kAXValueAttribute]=raw; value=string(raw); truncated=value.utf16.count>512; value=String(value.prefix(512)) }
            if attrs[kAXFocusedAttribute] as? Bool == true { selectedText = self.selectedText(ref) }
        } else { let raw=one(e,kAXValueAttribute); attrs[kAXValueAttribute]=raw; value=string(raw) }
        if let parent=attrs[kAXParentAttribute], CFGetTypeID(parent as CFTypeRef)==AXUIElementGetTypeID() { nativeParents[ref]=(parent as! AXUIElement) }
        exactAttributes[ref] = attrs
        let checked: Bool? = ["AXCheckBox","AXRadioButton"].contains(role) ? ((attrs[kAXValueAttribute] as? NSNumber)?.intValue == 1) : nil
        return Node(id:ref,role:role,title:String(title.prefix(300)),value:String(value.prefix(2000)),enabled:attrs[kAXEnabledAttribute] as? Bool ?? true,actions:actions as? [String] ?? [],frame:rect,focused:attrs[kAXFocusedAttribute] as? Bool ?? false,subrole:subrole,valueTruncated:truncated || value.count>2000,selectedText:selectedText,selected:attrs[kAXSelectedAttribute] as? Bool,checked:checked,ownerPID:pid,ownerWindowID:windowID,textLengthUTF16:textLength)
    }
    private func string(_ raw: Any?) -> String { (raw as? String) ?? (raw as? NSNumber)?.stringValue ?? "" }
    func childCount(_ ref: String) -> Int? { guard let e=refs[ref] else { return nil }; metrics.childCountCalls += 1; var count: CFIndex=0; let status=AXUIElementGetAttributeValueCount(e,kAXChildrenAttribute as CFString,&count); if status == .attributeUnsupported || status == .noValue { return 0 }; return status == .success ? count : nil }
    func children(_ ref: String, offset: Int, count: Int) -> [String]? { guard let e=refs[ref] else { return nil }; metrics.childPageCalls += 1; var values: CFArray?; let status=AXUIElementCopyAttributeValues(e,kAXChildrenAttribute as CFString,offset,count,&values); if status == .attributeUnsupported || status == .noValue { return [] }; guard status == .success, let elements=values as? [AXUIElement] else { return nil }; return elements.map(register) }
    func text(_ ref: String, range: AXTextRange?) throws -> String {
        guard let e=refs[ref], string(one(e,kAXSubroleAttribute)) != "AXSecureTextField" else { throw Failure("Expired or secure AX field") }
        if let range {
            var r=CFRange(location:range.location,length:range.length); guard let parameter=AXValueCreate(.cfRange,&r) else { throw Failure("Invalid UTF-16 range") }
            metrics.textRangeCalls += 1; var result: CFTypeRef?
            guard AXUIElementCopyParameterizedAttributeValue(e,kAXStringForRangeParameterizedAttribute as CFString,parameter,&result) == .success, let value=result as? String else { throw Failure("AX UTF-16 range unavailable; no whole-document fallback") }; return value
        }
        let raw=one(e,kAXValueAttribute); exactAttributes[ref,default:[:]][kAXValueAttribute]=raw; return string(raw)
    }
    func selectedText(_ ref: String) -> String { guard let e=refs[ref], string(one(e,kAXSubroleAttribute)) != "AXSecureTextField" else { return "" }; return string(one(e,kAXSelectedTextAttribute)) }
}
