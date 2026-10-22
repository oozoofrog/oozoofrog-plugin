import Foundation

struct AXCommand: Codable {
    enum Kind: String, Codable { case overview, find, children, read, expand, changes }
    var kind: Kind
    var filter: AXFilter? = nil
    var locator: String? = nil
    var cursor: String? = nil
    var limit: Int? = nil
    var fields: [AXReadField]? = nil
    var textRangeUTF16: AXTextRange? = nil
    var sinceRevision: String? = nil
    var delayMS: Int? = nil
    var cursorFrom: Int? = nil
    var targetFrom: Int? = nil
    var targetIndex: Int? = nil
}

@MainActor func performAXCommands(_ commands: [AXCommand], native: Native, directory: String) async throws {
    let observation=try await native.observe(directory:nil,images:false)
    guard var store=native.axStore else { throw Failure("AX query store unavailable; check selected app/window/permissions") }
    try writeJSON(observation,directory+"/initial.json")
    var pages:[Int:AXQueryPage]=[:]
    for (index,command) in commands.enumerated() {
        if let delay=command.delayMS, delay > 0 { try await Task.sleep(nanoseconds:UInt64(min(delay,5000))*1_000_000);native.reuseAXOnce=true;_ = try await native.observe(directory:nil,images:false);guard let current=native.axStore else { throw Failure("AX scope disappeared") };store=current }
        func handle() throws -> String {
            if let source=command.targetFrom {
                guard source < index, let page=pages[source], page.nodes.indices.contains(command.targetIndex ?? 0) else { throw Failure("Invalid preceding AX page target reference") }
                let handle=page.nodes[command.targetIndex ?? 0].id
                guard store.sourceRef(handle) != nil else { throw Failure("Referenced AX page target expired") }
                return handle
            }
            guard let locator=command.locator, let node=store.nodes.first(where: { $0.locator == locator }) else { throw Failure("Locator not collected in current session; expand its region first") }
            return node.id
        }
        func cursor() throws -> String? {
            guard let source=command.cursorFrom else { return command.cursor }
            guard source < index, let cursor=pages[source]?.cursor else { throw Failure("Referenced AX page has no continuation") }
            return cursor
        }
        let path=directory+"/query-\(index).json"
        switch command.kind {
        case .overview: try writeJSON(store.overview(),path)
        case .find: let page=try store.find(command.filter ?? AXFilter(),cursor:cursor(),limit:command.limit ?? 80);pages[index]=page;try writeJSON(page,path)
        case .children: let page=try store.children(handle(),cursor:cursor(),limit:command.limit ?? 32);pages[index]=page;try writeJSON(page,path)
        case .read: try writeJSON(store.read(handle(),fields:command.fields ?? [.metadata],textRangeUTF16:command.textRangeUTF16),path)
        case .expand: try writeJSON(store.expand(command.locator == nil && command.targetFrom == nil ? nil : handle(),budget:command.limit ?? 160),path)
        case .changes: try writeJSON(store.changes(sinceRevision:command.sinceRevision ?? observation.axOverview!.revision),path)
        }
    }
    try writeJSON(store.overview(),directory+"/final-overview.json"); try emit(store.overview())
}
