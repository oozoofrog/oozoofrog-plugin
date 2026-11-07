// The accessibility tree of a booted iOS Simulator, for the simulator tool's describe and wait actions and
// for tap with target.
//
// Undocumented parts: AccessibilityPlatformTranslation (AXPTranslator) turns the simulator app's
// accessibility into Mac platform elements, and CoreSimulator's SimDevice
// sendAccessibilityRequestAsync:completionQueue:completionHandler: carries its requests to the simulator.
// The bridge delegate is the one of idb's FBSimulatorAccessibilityCommands (github.com/cameroncooke/idb).
// Frames come in points of the device screen, the same as the x and y of tap and swipe.

import AppKit

struct SimulatorElement {
    let role: String
    let label: String
    let identifier: String
    let value: String
    let frame: CGRect
    let depth: Int
    let screen: CGSize

    /// The whole frame is on the screen. Elements of a screen the app left behind can stay in the tree, moved off it.
    var inside: Bool { CGRect(origin: .zero, size: screen).insetBy(dx: -1, dy: -1).contains(frame) }
    var offScreen: Bool { !CGRect(origin: .zero, size: screen).intersects(frame) }

    var center: CGPoint { CGPoint(x: frame.midX, y: frame.midY) }

    /// The words an agent can name the element by.
    var names: [String] { [label, identifier, value].filter { !$0.isEmpty } }

    var line: String {
        var parts = [role]
        if !label.isEmpty { parts.append("\"\(label)\"") }
        if !identifier.isEmpty { parts.append("id=\(identifier)") }
        if !value.isEmpty { parts.append("value=\"\(value)\"") }
        parts.append("at \(Int(center.x)),\(Int(center.y)) (\(Int(frame.width))×\(Int(frame.height)))")
        if offScreen { parts.append("[off screen]") } else if !inside && screen != .zero { parts.append("[partly off screen]") }
        return parts.joined(separator: " ")
    }
}

private let accessibilityQueue = DispatchQueue(label: "mac-cu.simulator-accessibility")

/// Answers AXPTranslator's requests by sending them to the simulator of the token.
final class SimulatorAccessibilityBridge: NSObject {
    private let lock = NSLock()
    private var devices: [String: NSObject] = [:]

    func register(_ device: NSObject) -> String {
        let token = UUID().uuidString
        lock.lock(); devices[token] = device; lock.unlock()
        return token
    }

    func unregister(_ token: String) {
        lock.lock(); devices[token] = nil; lock.unlock()
    }

    @objc(accessibilityTranslationDelegateBridgeCallbackWithToken:)
    func callback(_ token: NSString) -> (AnyObject) -> AnyObject? {
        lock.lock(); let device = devices[token as String]; lock.unlock()
        return { request in
            guard let device else { return nil }
            typealias SendFn = @convention(c) (AnyObject, Selector, AnyObject, DispatchQueue,
                                               @escaping @convention(block) (AnyObject?) -> Void) -> Void
            let selector = NSSelectorFromString("sendAccessibilityRequestAsync:completionQueue:completionHandler:")
            guard let imp = class_getMethodImplementation(object_getClass(device), selector) else { return nil }
            var response: AnyObject?
            let done = DispatchSemaphore(value: 0)
            unsafeBitCast(imp, to: SendFn.self)(device, selector, request, accessibilityQueue) { answer in
                response = answer
                done.signal()
            }
            _ = done.wait(timeout: .now() + 5)
            return response
        }
    }

    @objc(accessibilityTranslationConvertPlatformFrameToSystem:withToken:)
    func convert(_ rect: CGRect, token: NSString) -> CGRect { rect }

    @objc(accessibilityTranslationRootParentWithToken:)
    func rootParent(_ token: NSString) -> AnyObject? { nil }
}

private var accessibilityBridge: SimulatorAccessibilityBridge?
private var accessibilityTranslator: NSObject?

private func translator() throws -> (NSObject, SimulatorAccessibilityBridge) {
    if let accessibilityTranslator, let accessibilityBridge { return (accessibilityTranslator, accessibilityBridge) }
    let path = "/System/Library/PrivateFrameworks/AccessibilityPlatformTranslation.framework/AccessibilityPlatformTranslation"
    guard dlopen(path, RTLD_NOW) != nil, let translatorClass = NSClassFromString("AXPTranslator") as? NSObject.Type,
          let shared = translatorClass.perform(NSSelectorFromString("sharedInstance"))?.takeUnretainedValue() as? NSObject
    else { throw ToolError("macOS has no AccessibilityPlatformTranslation, so mac-cu cannot read the simulator's screen. Use screenshot.") }
    if let helper = objc_getProtocol("AXPTranslationTokenDelegateHelper") {
        class_addProtocol(SimulatorAccessibilityBridge.self, helper)
    }
    let bridge = SimulatorAccessibilityBridge()
    shared.setValue(bridge, forKey: "bridgeTokenDelegate")
    accessibilityTranslator = shared
    accessibilityBridge = bridge
    return (shared, bridge)
}

/// Whether the host process pid is the simulator's SpringBoard (home screen, lock screen).
private func isSpringBoard(_ pid: Int32) -> Bool {
    var path = [CChar](repeating: 0, count: 4096)
    return proc_pidpath(pid, &path, UInt32(path.count)) > 0 && String(cString: path).hasSuffix("/SpringBoard.app/SpringBoard")
}

/// The elements of the front app of a booted simulator, in tree order. With screen (a device with more than one),
/// frames are on that screen as shown.
/// The translation of the simulator's front app, for a registered token.
private func frontTranslation(_ translator: NSObject, token: String) throws -> NSObject {
    typealias FrontFn = @convention(c) (AnyObject, Selector, UInt32, NSString) -> AnyObject?
    let selector = NSSelectorFromString("frontmostApplicationWithDisplayId:bridgeDelegateToken:")
    guard let imp = class_getMethodImplementation(object_getClass(translator), selector),
          let translation = unsafeBitCast(imp, to: FrontFn.self)(translator, selector, 0, token as NSString) as? NSObject
    else { throw ToolError("The simulator did not answer for its front app. Wait until it has booted and an app is open, then try again.") }
    translation.setValue(token, forKey: "bridgeDelegateToken")
    return translation
}

/// The pid of the simulator's front app as its accessibility gives it (SpringBoard for the home screen,
/// Control Center and the lock screen).
func simulatorFrontPid(_ device: NSObject) throws -> Int32 {
    let (translator, bridge) = try translator()
    let token = bridge.register(device)
    defer { bridge.unregister(token) }
    return (try frontTranslation(translator, token: token).value(forKey: "pid") as? NSNumber)?.int32Value ?? 0
}

/// The name of the executable of a pid (the front app's), for answers.
func processName(_ pid: Int32) -> String {
    var path = [CChar](repeating: 0, count: 4096)
    return proc_pidpath(pid, &path, UInt32(path.count)) > 0 ? (String(cString: path) as NSString).lastPathComponent : "pid \(pid)"
}

/// With objects, it is called with the elements and their accessibility objects while the device can still answer them.
func simulatorElements(_ device: NSObject, screen active: ActiveScreen?, maxElements: Int = 600,
                       objects: (([SimulatorElement], [NSObject]) throws -> Void)? = nil) throws -> [SimulatorElement] {
    let (translator, bridge) = try translator()
    let token = bridge.register(device)
    defer { bridge.unregister(token) }
    let translation = try frontTranslation(translator, token: token)
    guard let root = translator.perform(NSSelectorFromString("macPlatformElementFromTranslation:"), with: translation)?
        .takeUnretainedValue() as? NSObject
    else { throw ToolError("The simulator's front app gave no accessibility element.") }

    var elements: [SimulatorElement] = []
    var found: [NSObject] = []
    let screen = active?.points ?? screenSize(of: device)
    // On a turned screen (iPhone Duo's inner screen), apps give frames as the screen is shown, but SpringBoard gives
    // them on the screen before rotation.
    let pid = (translation.value(forKey: "pid") as? NSNumber)?.int32Value ?? 0
    let turn = active.flatMap { $0.rotation != "rot0" && isSpringBoard(pid) ? $0 : nil }
    func string(_ object: NSObject, _ key: String) -> String {
        guard let value = object.value(forKey: key) else { return "" }
        return (value as? String) ?? "\(value)"
    }
    func visit(_ element: NSObject, depth: Int) {
        guard elements.count < maxElements, depth < 40 else { return }
        (element.value(forKey: "translation") as? NSObject)?.setValue(token, forKey: "bridgeDelegateToken")
        let role = string(element, "accessibilityRole")
        let frame = (element.value(forKey: "accessibilityFrame") as? NSValue)?.rectValue ?? .zero
        // On iPhone Duo's inner screen an app gives its children as shown, but its own (root) frame as the screen
        // before rotation; a turned iPhone gives the root as shown too, so only a root of the unrotated size is turned.
        let rootTurn = depth == 0 && active.map { ($0.rotation == "rot90" || $0.rotation == "rot270") && frame.size == $0.unrotated } == true
        elements.append(SimulatorElement(
            role: role.hasPrefix("AX") ? String(role.dropFirst(2)) : role,
            label: string(element, "accessibilityLabel"),
            identifier: string(element, "accessibilityIdentifier"),
            value: string(element, "accessibilityValue"),
            frame: (turn ?? (rootTurn ? active : nil)).map { $0.shown(frame) } ?? frame,
            depth: depth,
            screen: screen))
        found.append(element)
        for child in element.value(forKey: "accessibilityChildren") as? [NSObject] ?? [] {
            visit(child, depth: depth + 1)
        }
    }
    visit(root, depth: 0)
    try objects?(elements, found)
    return elements
}

/// Use iOS's three-finger editing menu without moving the input's caret or selection.
func pasteThroughSimulatorEditMenu(_ device: NSObject, screen: ActiveScreen?, link: HIDLink) throws -> Bool {
    var input: SimulatorElement?
    var selection: NSRange?
    _ = try simulatorElements(device, screen: screen) { elements, objects in
        let inputs = elements.indices.filter { ["TextField", "TextArea"].contains(elements[$0].role) && !elements[$0].offScreen }
        let focused = inputs.first(where: {
            (objects[$0].perform(NSSelectorFromString("accessibilityAttributeValue:"), with: "AXFocused")?.takeUnretainedValue() as? NSNumber)?.boolValue == true
        })
        guard let index = focused ?? (inputs.count == 1 ? inputs.first : nil),
              let range = objects[index].perform(NSSelectorFromString("accessibilityAttributeValue:"), with: "AXSelectedTextRange")?.takeUnretainedValue() as? NSValue,
              simulatorPasteSelectionIsValid(range.rangeValue, value: elements[index].value)
        else { return }
        input = elements[index]
        selection = range.rangeValue
    }
    guard let input, let selection else { return false }
    let spread = min(30, input.frame.width / 4)
    let contacts = (-1...1).enumerated().map { index, offset in
        ["id": index + 1, "x": input.center.x + Double(offset) * spread, "y": input.center.y] as [String: Any]
    }
    let frames = ["down", "up"].enumerated().map { index, phase in
        ["time": Double(index) * 0.1, "touches": contacts.map { $0.merging(["phase": phase]) { _, new in new } }] as [String: Any]
    }
    _ = try runSimulatorGesture(arguments: ["frames": frames], device: device, screen: screen,
                                cancelled: { currentSession?.requestCancelled ?? false })
    usleep(250_000)  // UIKit exposes the editing bar before its presentation animation accepts touches.
    var preserved = false
    _ = try simulatorElements(device, screen: screen) { elements, objects in
        for index in elements.indices where elements[index].role == input.role && elements[index].value == input.value
            && input.frame.insetBy(dx: -20, dy: -20).contains(elements[index].center) {
            let range = objects[index].perform(NSSelectorFromString("accessibilityAttributeValue:"), with: "AXSelectedTextRange")?.takeUnretainedValue() as? NSValue
            preserved = range?.rangeValue == selection
            break
        }
    }
    guard preserved else { throw ToolError("입력란의 선택 범위가 바뀌어 붙여넣기를 중단했습니다. 입력란을 다시 선택하고 시도하세요.") }
    for _ in 0..<5 {
        if let item = try simulatorElements(device, screen: screen).first(where: {
            ["붙여넣기", "Paste"].contains($0.label) && !$0.offScreen
        }) {
            link.touch(item.center, phase: 0, screen: screen)
            usleep(50_000)
            link.touch(item.center, phase: 2, screen: screen)
            return true
        }
        usleep(100_000)
    }
    return false
}

/// Presses the first element named target (exact label, id or value first, then contains) with the accessibility press
/// action (AXPress), as VoiceOver does: no touch, so no coordinates, screens or rotation are involved, and an element
/// that another view covers or that is partly off the screen is pressed too. Elements a list has not made are not in the tree.
func pressSimulatorElement(_ device: NSObject, screen: ActiveScreen?, target: String) throws -> SimulatorElement {
    let wanted = target.trimmingCharacters(in: .whitespaces)
    var pressed: SimulatorElement?
    _ = try simulatorElements(device, screen: screen) { elements, objects in
        let exact = elements.indices.first { elements[$0].names.contains { $0.caseInsensitiveCompare(wanted) == .orderedSame } }
        guard let index = exact ?? elements.indices.first(where: { elements[$0].names.contains { $0.range(of: wanted, options: .caseInsensitive) != nil } })
        else { throw ToolError("No element named \"\(target)\". Run describe to see the screen.") }
        typealias PressFn = @convention(c) (AnyObject, Selector) -> Bool
        let selector = NSSelectorFromString("accessibilityPerformPress")
        guard let imp = class_getMethodImplementation(object_getClass(objects[index]), selector),
              unsafeBitCast(imp, to: PressFn.self)(objects[index], selector)
        else { throw ToolError("\(elements[index].line) did not take the press action. Use tap.") }
        pressed = elements[index]
    }
    return pressed!
}

/// The elements on the screen whose label, identifier or value is target (ignoring case), or else contains
/// it. Elements wholly on the screen come first.
func simulatorMatches(_ elements: [SimulatorElement], _ target: String) -> [SimulatorElement] {
    let wanted = target.trimmingCharacters(in: .whitespaces)
    guard !wanted.isEmpty else { return [] }
    let visible = elements.filter { $0.frame.width > 0 && $0.frame.height > 0 && !$0.offScreen }
    var matches = visible.filter { $0.names.contains { $0.caseInsensitiveCompare(wanted) == .orderedSame } }
    if matches.isEmpty { matches = visible.filter { $0.names.contains { $0.range(of: wanted, options: .caseInsensitive) != nil } } }
    return matches.filter(\.inside) + matches.filter { !$0.inside }
}

/// The text of describe: the tree, or the elements that match query.
func describeSimulator(_ device: NSObject, screen: ActiveScreen?, query: String) throws -> String {
    let elements = try simulatorElements(device, screen: screen)
    let name = device.value(forKey: "name") ?? udid(of: device)
    if !query.isEmpty {
        let matches = simulatorMatches(elements, query)
        if matches.isEmpty { return "No element of \(name)'s front app is named \"\(query)\". Run describe without query to see all." }
        return "Elements of \(name) named \"\(query)\" (role, label, id, value, center x,y in points, size):\n"
            + matches.map(\.line).joined(separator: "\n")
    }
    let lines = elements.map { String(repeating: "  ", count: $0.depth) + $0.line }
    return """
        Front app of \(name) (role, label, id, value, center x,y in points, size). Tap a center with tap x/y, \
        or tap with target set to a label or id.
        """ + "\n" + lines.joined(separator: "\n")
}

/// The first element named target, waiting up to seconds for it to appear.
func waitForSimulatorElement(_ device: NSObject, screen: ActiveScreen?, target: String, seconds: Double) throws -> (SimulatorElement, [SimulatorElement]) {
    let deadline = Date().addingTimeInterval(seconds)
    while true {
        let matches = simulatorMatches(try simulatorElements(device, screen: screen), target)
        if let first = matches.first { return (first, matches) }
        if Date() >= deadline {
            throw ToolError("No element named \"\(target)\" appeared in \(Int(seconds.rounded())) seconds. Run describe to see the screen.")
        }
        usleep(400_000)
    }
}
