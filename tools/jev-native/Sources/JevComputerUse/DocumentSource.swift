import Foundation
import CryptoKit
import ApplicationServices

struct DocumentSourceEvidence: Codable {
    var origin: String
    var window: WindowInfo? = nil
    var locator: String? = nil
    var utf16Length: Int
    var coverage: String
    var sha256: String
    var artifact = "source-text.txt"
    var stableDoubleRead: Bool
    var selectedAXWindowIdentityVerified: Bool = false
}
struct DocumentSource {
    var text: String
    var evidence: DocumentSourceEvidence
    static let maximumUTF16 = 12000

    static func supplied(_ text: String) throws -> Self {
        guard !text.isEmpty, text.utf16.count <= maximumUTF16 else { throw Failure("Source is empty or exceeds the bounded transformation limit") }
        return Self(text:text,evidence:DocumentSourceEvidence(origin:"user_supplied",utf16Length:text.utf16.count,coverage:"complete_supplied_source",sha256:SHA256.hash(data:Data(text.utf8)).map { String(format:"%02x",$0) }.joined(),stableDoubleRead:false))
    }

    /// A transformation requires the whole exposed source, never a preview masquerading as a document.
    @MainActor static func read(native: Native, observation: Observation) throws -> Self {
        guard let window = observation.selectedWindow, let target = observation.target,
              native.sessionWindowID == window.id, let store = native.axStore, let source = native.axSource else { throw Failure("No selected readable document window") }
        for _ in 0..<12 where store.overview().coverage != .complete {
            guard store.nodes.count < 2000 else { break }
            _ = try store.expand(nil,budget:160)
        }
        guard store.overview().coverage == .complete else { throw Failure("Document AX coverage is partial or unknown") }
        let editors = store.nodes.filter { $0.role == "AXTextArea" && ($0.locator ?? "").hasPrefix("w.") }
        guard editors.count == 1, let editor = editors.first,
              let length = editor.textLengthUTF16, length > 0, length <= maximumUTF16 else { throw Failure("Source editor is missing, ambiguous, empty or exceeds the bounded transformation limit") }
        guard let ref = store.sourceRef(editor.id), let element = source.element(ref) else { throw Failure("Source handle expired") }
        var pid: pid_t = 0
        guard AXUIElementGetPid(element,&pid) == .success, pid == target.pid,
              native.windows(pid:pid).contains(where: { $0.id == window.id && $0.frame == window.frame }) else { throw Failure("Source window ownership changed") }
        guard let root = store.nodes.first(where: { $0.locator == "w" }), let rootRef = store.sourceRef(root.id), let rootWindow = source.element(rootRef) else { throw Failure("Selected AX window identity is unavailable") }
        func checkOwnership() throws {
            var currentPID: pid_t = 0
            let currentWindow = native.attr(element,kAXWindowAttribute)
            guard AXUIElementGetPid(element,&currentPID) == .success, currentPID == target.pid,
                  let currentWindow, CFGetTypeID(currentWindow) == AXUIElementGetTypeID(), CFEqual(currentWindow,rootWindow),
                  native.frame(rootWindow) == window.frame,
                  native.windows(pid:currentPID).contains(where: { $0.id == window.id && $0.frame == window.frame }),
                  let parent = native.attr(element,kAXParentAttribute), CFGetTypeID(parent) == AXUIElementGetTypeID() else { throw Failure("Source editor no longer belongs to the selected AX window") }
            try store.validateNativeParent(editor.id,currentRef:source.register(parent as! AXUIElement))
        }
        try checkOwnership()
        let range = AXTextRange(location:0,length:length)
        guard let first = try store.read(editor.id,fields:[.value],textRangeUTF16:range).value,
              let second = try store.read(editor.id,fields:[.value],textRangeUTF16:range).value,
              first == second, first.utf16.count == length,
              source.metadata(ref)?.textLengthUTF16 == length else { throw Failure("Source text changed or its complete UTF-16 range could not be read") }
        try checkOwnership()
        return Self(text:first,evidence:DocumentSourceEvidence(origin:"selected_window_ax",window:window,locator:editor.locator,utf16Length:length,coverage:"complete_exposed_document",sha256:SHA256.hash(data:Data(first.utf8)).map { String(format:"%02x",$0) }.joined(),stableDoubleRead:true,selectedAXWindowIdentityVerified:true))
    }
}

func validateProtectedSourceAction(_ action: Action, observedWindow: UInt32?, protectedWindow: UInt32?) throws {
    guard let protectedWindow, observedWindow == protectedWindow else { return }
    let newDocument = action.kind == "key" && action.key == "n" && Set(action.modifiers ?? []) == ["cmd"]
    guard ["launch","activate","openFile","selectWindow","wait","focus","raise"].contains(action.kind) || newDocument else {
        throw Failure("The source window is read-only for this request; choose the requested result destination")
    }
}
