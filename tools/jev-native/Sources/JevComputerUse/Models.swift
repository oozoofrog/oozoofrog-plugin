import Foundation

struct Failure: Error, CustomStringConvertible { let description: String; init(_ s: String) { description = s } }
func milliseconds(_ start: Date) -> Double { Date().timeIntervalSince(start) * 1000 }
func jsonData<T: Encodable>(_ value: T) throws -> Data { let e = JSONEncoder(); e.outputFormatting = [.prettyPrinted, .sortedKeys]; return try e.encode(value) }
func writeJSON<T: Encodable>(_ value: T, _ path: String) throws { try jsonData(value).write(to: URL(fileURLWithPath: path), options: .atomic) }
func emit<T: Encodable>(_ value: T) throws { print(String(decoding: try jsonData(value), as: UTF8.self)) }
struct Rect: Codable, Equatable { var x: Double; var y: Double; var width: Double; var height: Double }
struct AppInfo: Codable { var pid: Int32; var bundle: String; var name: String }
struct Node: Codable, Equatable { var id: String; var role: String; var title: String; var value: String; var enabled: Bool; var actions: [String]; var frame: Rect?; var focused: Bool = false; var subrole: String = ""; var valueTruncated: Bool = false; var selectedText: String? = nil; var selected: Bool? = nil; var checked: Bool? = nil; var parent: String? = nil; var ancestors: [String]? = nil; var locator: String? = nil; var ownerPID: Int32? = nil; var ownerWindowID: UInt32? = nil; var textLengthUTF16: Int? = nil; var valueRangeUTF16: AXTextRange? = nil }
struct WindowInfo: Codable, Equatable { var id: UInt32; var pid: Int32; var title: String; var frame: Rect; var onScreen: Bool }
struct WindowCapture: Codable { var window: WindowInfo; var screenshot: String?; var pixelWidth: Int; var pixelHeight: Int; var ocr: [String]; var imageSHA256: String? = nil }
struct DisplayInfo: Codable { var id: UInt32; var frame: Rect; var pixelWidth: Int; var pixelHeight: Int; var screenshot: String?; var ocr: [String] }
struct AXModalStamp: Codable, Equatable { var role: String; var title: String; var frame: Rect? }
struct Observation: Codable { var id: String; var timestamp: Date; var front: AppInfo?; var apps: [AppInfo]; var nodes: [Node]; var displays: [DisplayInfo]; var truncated: Bool; var axError: String?; var elapsedMS: Double; var target: AppInfo? = nil; var windows: [WindowInfo] = []; var selectedWindow: WindowInfo? = nil; var windowCapture: WindowCapture? = nil; var axOverview: AXOverview? = nil; var axMetrics: AXMetrics? = nil; var axReadHandle: String? = nil; var axModalStamps: [AXModalStamp]? = nil }
struct Action: Codable, Equatable {
    var kind: String
    var target: String? = nil
    var app: String? = nil
    var text: String? = nil
    var key: String? = nil
    var modifiers: [String]? = nil
    var x: Double? = nil
    var y: Double? = nil
    var toX: Double? = nil
    var toY: Double? = nil
    var amount: Int? = nil
    var label: String? = nil
    var windowID: UInt32? = nil
    var path: String? = nil
    var coordinateSpace: String? = nil
    var axAction: String? = nil
    var selectionStart: Int? = nil
    var selectionLength: Int? = nil
    var horizontalAmount: Int? = nil
}
struct VirtualPointer: Codable { var x: Double = 0; var y: Double = 0; var buttons: [String] = []; var targetPID: Int32? = nil }
struct TaskSpec: Codable {
    var goal: String
    var apps: [String] = []
    var texts: [String] = []
    var actions: [Action] = []
    var generateText: Bool = false
    var inspectImage: Bool = false
    var sourceTransform: Bool = false
    var sourceText: String? = nil
    var sourceEvidence: DocumentSourceEvidence? = nil
    var protectedWindowID: UInt32? = nil
    var initialWindowID: UInt32? = nil
    var maxSteps: Int = 30
    var settleMS: Int = 250
    var maxRecovery: Int = 3
    var confidence: Double = 0.55
    // Deterministic completion conditions are optional, but take precedence over JEV completion.
    var expectText: String? = nil
    var expectApp: String? = nil
}
enum AXQueryKind: String, Codable { case expand, page, read, find }
struct AXQuery: Codable { var kind: AXQueryKind; var handle: String? = nil; var page: Int? = nil; var filter: AXFilter? = nil; var rangeUTF16: AXTextRange? = nil; var localValue: Bool? = nil }
struct Candidate: Codable { var id: String; var description: String; var action: Action?; var query: AXQuery? = nil }
struct Decision: Codable { var choice: String; var confidence: Double; var apiMS: Double; var localMS: Double; var model: String; var usage: [String: Int]; var response: String; var progressProbability: Double? = nil; var verificationApiMS: Double? = nil; var requestBytes: Int? = nil; var verificationRequestBytes: Int? = nil }
struct Step: Codable { var index: Int; var observation: String; var decision: Decision?; var action: Action?; var executionMS: Double?; var error: String?; var afterObservation: String?; var query: AXQuery? = nil; var queryLabel: String? = nil; var delegate: DelegateProvenance? = nil }
struct RunReport: Codable { var status: String; var goal: String; var steps: [Step]; var finalObservation: String; var directory: String; var apps: [String]? = nil; var appSelection: AppResolution? = nil; var error: String? = nil; var completionSource: String? = nil; var requestResolution: RequestResolution? = nil; var response: String? = nil }

func explicitCompletion(_ spec:TaskSpec, observation:Observation, pendingTexts:[String], generated:Bool, inspected:Bool) -> Bool {
    guard spec.expectText != nil || spec.expectApp != nil,
          pendingTexts.isEmpty, (!spec.generateText || generated), (!spec.inspectImage || inspected) else { return false }
    let appOK=spec.expectApp.map { observation.target?.bundle == $0 } ?? true
    let evidence=observation.nodes.map { $0.title+"\n"+$0.value }.joined(separator:"\n")+"\n"+(observation.windowCapture?.ocr ?? []).joined(separator:"\n")
    let textOK=spec.expectText.map { evidence.contains($0) } ?? true
    return appOK && textOK
}

func stableTargetState(_ a: Observation, _ b: Observation, action: Action? = nil) -> Bool {
    guard a.target?.pid == b.target?.pid, a.selectedWindow == b.selectedWindow, a.axModalStamps == b.axModalStamps else { return false }
    func relevant(_ nodes: [Node]) -> [Node] {
        nodes.filter { node in
            if ["AXMenu", "AXMenuItem"].contains(node.role), (node.frame?.width ?? 0) <= 0 || (node.frame?.height ?? 0) <= 0 { return false }
            if (node.locator ?? node.id) == "m" || (node.locator ?? node.id).hasPrefix("m.") { return a.nodes.first(where: { $0.id == action?.target }).map { ($0.locator ?? $0.id).hasPrefix("m") } == true && (node.frame?.width ?? 0) > 0 && (node.frame?.height ?? 0) > 0 }
            return node.role == "AXWindow" || !node.actions.isEmpty || !node.title.isEmpty || !node.value.isEmpty || node.focused
        }
    }
    func normalized(_ nodes: [Node]) -> [Node] { relevant(nodes).map { value in var node=value; node.id=node.locator ?? node.id; node.parent=nil; return node } }
    return normalized(a.nodes) == normalized(b.nodes)
}

func credential(environment: [String: String] = ProcessInfo.processInfo.environment, home: String = NSHomeDirectory()) throws -> String {
    if let value = environment["TYPESAFE_API_KEY"], !value.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty { return value }
    let path = home + "/.typesafeai"
    guard let value = try? String(contentsOfFile: path, encoding: .utf8).trimmingCharacters(in: .whitespacesAndNewlines), !value.isEmpty else { throw Failure("No TYPESAFE_API_KEY or nonempty ~/.typesafeai") }
    return value
}
func validateAction(_ a: Action, apps: [String]) throws {
    let kinds = ["launch", "activate", "openFile", "selectWindow", "press", "secondary", "selectText", "focus", "setValue", "type", "key", "click", "doubleClick", "rightClick", "move", "drag", "scroll", "raise", "resize", "moveWindow", "wait"]
    guard kinds.contains(a.kind) else { throw Failure("Unsupported action: \(a.kind)") }
    if ["launch", "activate", "openFile"].contains(a.kind) { guard let app = a.app, apps.contains(app) else { throw Failure("App is outside explicit allowlist") } }
    if a.kind == "openFile", a.path == nil { throw Failure("openFile requires literal path") }
    if a.kind == "selectWindow", a.windowID == nil { throw Failure("Window selection requires windowID") }
    if ["press", "secondary", "selectText", "focus", "setValue", "raise", "resize", "moveWindow"].contains(a.kind), a.target == nil { throw Failure("AX action requires target from current observation") }
    if a.kind == "secondary", a.axAction == nil { throw Failure("secondary requires an observed axAction") }
    if a.kind == "selectText", (a.selectionStart ?? -1) < 0 || (a.selectionLength ?? -1) < 0 { throw Failure("selectText requires nonnegative UTF-16 selectionStart/selectionLength") }
    if let space = a.coordinateSpace, !["global", "windowPoints", "screenshotPixels"].contains(space) { throw Failure("Unknown coordinateSpace") }
    if ["type", "setValue"].contains(a.kind), a.text == nil { throw Failure("Text action requires literal text") }
    if ["click", "doubleClick", "rightClick", "move", "drag"].contains(a.kind), a.x == nil || a.y == nil { throw Failure("Pointer action requires global logical x/y") }
    if a.kind == "drag", a.toX == nil || a.toY == nil { throw Failure("Drag requires toX/toY") }
    if a.kind == "resize", a.toX == nil || a.toY == nil { throw Failure("Resize requires width/height in toX/toY") }
    if a.kind == "moveWindow", a.x == nil || a.y == nil { throw Failure("moveWindow requires x/y") }
    if a.kind == "key", a.key == nil { throw Failure("Key action requires key") }
    for m in a.modifiers ?? [] { guard ["cmd", "shift", "alt", "ctrl"].contains(m) else { throw Failure("Unknown modifier: \(m)") } }
    for v in [a.x, a.y, a.toX, a.toY].compactMap({ $0 }) { guard v.isFinite else { throw Failure("Nonfinite coordinate") } }
}

extension TaskSpec {
    private enum Keys: String, CodingKey { case goal, apps, texts, actions, generateText, inspectImage, sourceTransform, sourceText, sourceEvidence, protectedWindowID, initialWindowID, maxSteps, settleMS, maxRecovery, confidence, expectText, expectApp }
    func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: Keys.self)
        try c.encode(goal, forKey: .goal)
        if !apps.isEmpty { try c.encode(apps, forKey: .apps) }
        try c.encode(texts, forKey: .texts); try c.encode(actions, forKey: .actions)
        try c.encode(generateText, forKey: .generateText); try c.encode(inspectImage, forKey: .inspectImage)
        if sourceTransform { try c.encode(sourceTransform, forKey: .sourceTransform) }
        try c.encodeIfPresent(sourceText, forKey: .sourceText); try c.encodeIfPresent(sourceEvidence,forKey:.sourceEvidence); try c.encodeIfPresent(protectedWindowID,forKey:.protectedWindowID); try c.encodeIfPresent(initialWindowID, forKey: .initialWindowID)
        try c.encode(maxSteps, forKey: .maxSteps); try c.encode(settleMS, forKey: .settleMS)
        try c.encode(maxRecovery, forKey: .maxRecovery); try c.encode(confidence, forKey: .confidence)
        try c.encodeIfPresent(expectText, forKey: .expectText); try c.encodeIfPresent(expectApp, forKey: .expectApp)
    }
    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: Keys.self)
        goal = try c.decode(String.self, forKey: .goal)
        if c.contains(.apps) {
            apps = try c.decode([String].self, forKey: .apps)
            guard !apps.isEmpty else { throw Failure("Task apps must not be empty; omit apps for automatic selection.") }
        } else { apps = [] }
        texts = try c.decodeIfPresent([String].self, forKey: .texts) ?? []
        actions = try c.decodeIfPresent([Action].self, forKey: .actions) ?? []
        generateText = try c.decodeIfPresent(Bool.self, forKey: .generateText) ?? false
        inspectImage = try c.decodeIfPresent(Bool.self, forKey: .inspectImage) ?? false
        sourceTransform = try c.decodeIfPresent(Bool.self, forKey: .sourceTransform) ?? false
        sourceText = try c.decodeIfPresent(String.self, forKey: .sourceText)
        sourceEvidence = try c.decodeIfPresent(DocumentSourceEvidence.self, forKey:.sourceEvidence)
        protectedWindowID = try c.decodeIfPresent(UInt32.self, forKey:.protectedWindowID)
        initialWindowID = try c.decodeIfPresent(UInt32.self, forKey: .initialWindowID)
        maxSteps = try c.decodeIfPresent(Int.self, forKey: .maxSteps) ?? 30
        settleMS = try c.decodeIfPresent(Int.self, forKey: .settleMS) ?? 250
        maxRecovery = try c.decodeIfPresent(Int.self, forKey: .maxRecovery) ?? 3
        confidence = try c.decodeIfPresent(Double.self, forKey: .confidence) ?? 0.55
        expectText = try c.decodeIfPresent(String.self, forKey: .expectText); expectApp = try c.decodeIfPresent(String.self, forKey: .expectApp)
    }
}
