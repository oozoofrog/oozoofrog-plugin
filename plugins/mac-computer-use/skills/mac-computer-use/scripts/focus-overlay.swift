// focus-overlay: show which window mac-cu works on.
//
// - A focus glow around the target window. The glow panel stays directly above the target window
//   in the window order, so windows that cover the target also cover the glow, and the target app
//   does not need to be in front.
// - A small live preview of the target window while most of the window cannot be seen (covered,
//   minimized, or on another Space). The user can drag the preview, close it, or click it to bring
//   the target window to the front.
//
// focus.py starts one process for each target window and stops it. The process also stops when the
// state file is removed or was not touched for 15 minutes, or when the target window closes.
//
// Build: swiftc -O focus-overlay.swift -o focus-overlay

import AppKit
import ScreenCaptureKit
import VideoToolbox

let args = CommandLine.arguments
func option(_ name: String) -> String? {
    guard let i = args.firstIndex(of: name), i + 1 < args.count else { return nil }
    return args[i + 1]
}
func required(_ name: String) -> String {
    if let value = option(name) { return value }
    FileHandle.standardError.write("usage: focus-overlay [--owner APP] --title WINDOW [--color RRGGBB] --state FILE\n".data(using: .utf8)!)
    exit(2)
}
func color(hex: String) -> NSColor {
    let value = UInt32(hex.trimmingCharacters(in: CharacterSet(charactersIn: "#")), radix: 16) ?? 0x339cff
    return NSColor(srgbRed: CGFloat(value >> 16 & 0xff) / 255, green: CGFloat(value >> 8 & 0xff) / 255,
                   blue: CGFloat(value & 0xff) / 255, alpha: 1)
}

// Without the app name, the target is the first normal window with this title.
let owner = option("--owner")
let title = required("--title")
let statePath = required("--state")
let accent = color(hex: option("--color") ?? "339cff")
let margin: CGFloat = 12
/// The width of the ruler bands of the measurement guides.
let rulerWidth: CGFloat = 16
let maxIdle: TimeInterval = 15 * 60
let previewTitle = "mac-cu preview"
// The preview shows while less than this part of the target window can be seen.
let visibleEnough = 0.9

func onScreenWindows() -> [[String: Any]] {
    CGWindowListCopyWindowInfo([.optionOnScreenOnly, .excludeDesktopElements], kCGNullWindowID) as? [[String: Any]] ?? []
}

func findTarget() -> CGWindowID? {
    let mine = onScreenWindows().filter {
        $0[kCGWindowLayer as String] as? Int == 0
            && (owner == nil || $0[kCGWindowOwnerName as String] as? String == owner)
    }
    let titled = mine.first { $0[kCGWindowName as String] as? String == title }
    let match: [String: Any]? = titled ?? (owner == nil ? nil : mine.first)
    return match?[kCGWindowNumber as String] as? CGWindowID
}

func bounds(of window: [String: Any]) -> CGRect? {
    guard let dict = window[kCGWindowBounds as String] as? NSDictionary else { return nil }
    return CGRect(dictionaryRepresentation: dict)
}

/// The part (0...1) of the target window that no normal window in front of it covers.
func visibleFraction(of id: CGWindowID, in rect: CGRect) -> Double {
    let ignoredOwners: Set<String> = ["focus-overlay"]
    var covers: [CGRect] = []
    for window in onScreenWindows() {
        if window[kCGWindowNumber as String] as? CGWindowID == id { break }  // The list goes front to back.
        guard window[kCGWindowLayer as String] as? Int == 0,
              (window[kCGWindowAlpha as String] as? Double ?? 1) > 0,
              !ignoredOwners.contains(window[kCGWindowOwnerName as String] as? String ?? ""),
              let frame = bounds(of: window), frame.width > 40, frame.height > 40
        else { continue }
        covers.append(frame)
    }
    let steps = 12
    var visible = 0
    for row in 0..<steps {
        for column in 0..<steps {
            let point = CGPoint(x: rect.minX + rect.width * (Double(column) + 0.5) / Double(steps),
                                y: rect.minY + rect.height * (Double(row) + 0.5) / Double(steps))
            if !covers.contains(where: { $0.contains(point) }) { visible += 1 }
        }
    }
    return Double(visible) / Double(steps * steps)
}

/// Convert Window Server coordinates (top left of the main display) to AppKit (bottom left).
func appKitRect(_ rect: CGRect) -> NSRect {
    let mainHeight = NSScreen.screens.first?.frame.height ?? 0
    return NSRect(x: rect.minX, y: mainHeight - rect.maxY, width: rect.width, height: rect.height)
}

/// An arrow pointer with its tip at (0, 0), in layer coordinates (y goes up).
func makePointer() -> CAShapeLayer {
    let path = CGMutablePath()
    path.addLines(between: [CGPoint(x: 0, y: 0), CGPoint(x: 0, y: -15), CGPoint(x: 4, y: -11.5),
                            CGPoint(x: 7, y: -18), CGPoint(x: 9.5, y: -17), CGPoint(x: 6.5, y: -10.5),
                            CGPoint(x: 11, y: -10.5)])
    path.closeSubpath()
    let pointer = CAShapeLayer()
    pointer.path = path
    pointer.fillColor = NSColor.white.cgColor
    pointer.strokeColor = NSColor.black.cgColor
    pointer.lineWidth = 1
    pointer.shadowOpacity = 0.4
    pointer.shadowRadius = 2
    pointer.shadowOffset = .zero
    pointer.isHidden = true
    return pointer
}

/// A point of the target window (Window Server coordinates) in an area that shows the window (layer
/// coordinates, y up).
func layerPoint(_ point: CGPoint, window: CGRect, in area: CGRect) -> CGPoint {
    CGPoint(x: area.minX + (point.x - window.minX) / window.width * area.width,
            y: area.maxY - (point.y - window.minY) / window.height * area.height)
}

/// A rectangle of the target window in the area, from its two corners.
func layerRect(_ rect: CGRect, window: CGRect, in area: CGRect) -> CGRect {
    let topLeft = layerPoint(rect.origin, window: window, in: area)
    let bottomRight = layerPoint(CGPoint(x: rect.maxX, y: rect.maxY), window: window, in: area)
    return CGRect(x: topLeft.x, y: bottomRight.y, width: bottomRight.x - topLeft.x, height: topLeft.y - bottomRight.y)
}

/// Place the pointer at a point of the target window (Window Server coordinates) inside an area
/// that shows the window, or hide it.
func place(_ pointer: CAShapeLayer, at point: CGPoint?, window: CGRect, in area: CGRect) {
    CATransaction.begin()
    CATransaction.setDisableActions(true)
    if let point, window.contains(point) {
        pointer.position = layerPoint(point, window: window, in: area)
        pointer.isHidden = false
    } else {
        pointer.isHidden = true
    }
    CATransaction.commit()
}

/// Where mac-cu acted on this app in the last 5 seconds (Window Server coordinates), or nil.
/// mac-cu writes the point to $TMPDIR/mac-cu-cursor/<pid>.json.
func macCUCursor(pid: pid_t) -> CGPoint? {
    guard let data = FileManager.default.contents(atPath: NSTemporaryDirectory() + "mac-cu-cursor/\(pid).json"),
          let record = try? JSONSerialization.jsonObject(with: data) as? [String: Double],
          let x = record["x"], let y = record["y"], let time = record["time"],
          Date().timeIntervalSince1970 - time < 5 else { return nil }
    return CGPoint(x: x, y: y)
}

/// What mac-cu does now in this app (`mac-cu --mode show=steps`): the goal of act and its step, or nil
/// 6 seconds after the last step. mac-cu writes it to $TMPDIR/mac-cu-status/<pid>.json.
func macCUStep(pid: pid_t) -> (goal: String, step: String)? {
    guard let data = FileManager.default.contents(atPath: NSTemporaryDirectory() + "mac-cu-status/\(pid).json"),
          let record = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
          let step = record["step"] as? String, let time = record["time"] as? Double,
          Date().timeIntervalSince1970 - time < 6 else { return nil }
    return (record["goal"] as? String ?? "", step)
}

/// The measurement guides of get_app_state or act with guides: the numbered element boxes (Window Server
/// coordinates), or nil 8 seconds after the call. mac-cu writes them to $TMPDIR/mac-cu-guides/<pid>.json.
func macCUGuides(pid: pid_t) -> [(number: Int, rect: CGRect)]? {
    guard let data = FileManager.default.contents(atPath: NSTemporaryDirectory() + "mac-cu-guides/\(pid).json"),
          let record = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
          let boxes = record["boxes"] as? [[String: Double]], let time = record["time"] as? Double,
          Date().timeIntervalSince1970 - time < 8 else { return nil }
    return boxes.compactMap { box in
        guard let n = box["n"], let x = box["x"], let y = box["y"], let w = box["w"], let h = box["h"] else { return nil }
        return (Int(n), CGRect(x: x, y: y, width: w, height: h))
    }
}

/// A small white label on a dark box, in the style of the caption box.
func makeLabel() -> CATextLayer {
    let label = CATextLayer()
    label.contentsScale = NSScreen.main?.backingScaleFactor ?? 2
    label.font = NSFont.systemFont(ofSize: 10, weight: .semibold)
    label.fontSize = 10
    label.foregroundColor = NSColor.white.cgColor
    label.alignmentMode = .center
    label.backgroundColor = NSColor.black.withAlphaComponent(0.78).cgColor
    label.borderColor = accent.cgColor
    label.borderWidth = 1
    label.cornerRadius = 3
    return label
}

/// Keep as many layers as needed in the parent: add or remove only the difference.
func fit<Layer: CALayer>(_ layers: inout [Layer], count: Int, in parent: CALayer, make: () -> Layer) {
    while layers.count < count {
        let layer = make()
        parent.addSublayer(layer)
        layers.append(layer)
    }
    while layers.count > count { layers.removeLast().removeFromSuperlayer() }
}

final class GlowView: NSView {
    private let ring = CAShapeLayer()
    let pointer = makePointer()
    private let captionBox = CALayer()
    private let caption = CATextLayer()
    private var boxes: [CAShapeLayer] = []
    private var labels: [CATextLayer] = []
    private let rulerBands = CAShapeLayer()
    private let rulerTicks = CAShapeLayer()
    private var rulerLabels: [CATextLayer] = []

    override init(frame: NSRect) {
        super.init(frame: frame)
        wantsLayer = true
        ring.fillColor = nil
        ring.strokeColor = accent.cgColor
        ring.lineWidth = 3
        ring.shadowColor = accent.cgColor
        ring.shadowOpacity = 0.9
        ring.shadowRadius = 8
        ring.shadowOffset = .zero
        layer?.addSublayer(ring)
        if !NSWorkspace.shared.accessibilityDisplayShouldReduceMotion {
            let pulse = CABasicAnimation(keyPath: "opacity")
            pulse.fromValue = 1
            pulse.toValue = 0.5
            pulse.duration = 1.2
            pulse.autoreverses = true
            pulse.repeatCount = .infinity
            ring.add(pulse, forKey: "pulse")
        }
        layer?.addSublayer(pointer)
        captionBox.backgroundColor = NSColor.black.withAlphaComponent(0.78).cgColor
        captionBox.borderColor = accent.cgColor
        captionBox.borderWidth = 1.5
        captionBox.cornerRadius = 9
        captionBox.isHidden = true
        caption.contentsScale = NSScreen.main?.backingScaleFactor ?? 2
        caption.isWrapped = true
        captionBox.addSublayer(caption)
        layer?.addSublayer(captionBox)
        rulerBands.fillColor = NSColor.black.withAlphaComponent(0.6).cgColor
        rulerTicks.strokeColor = NSColor.white.cgColor
        rulerTicks.lineWidth = 1
        layer?.addSublayer(rulerBands)
        layer?.addSublayer(rulerTicks)
    }

    required init?(coder: NSCoder) { nil }

    /// The measurement guides on the window: a box with its number around each element, and rulers along the
    /// top and the left edge (a tick every 50 points, a long one with the number every 100, from the top left
    /// of the window). nil hides them.
    func showGuides(_ guides: [(number: Int, rect: CGRect)]?, window: CGRect) {
        CATransaction.begin()
        CATransaction.setDisableActions(true)
        defer { CATransaction.commit() }
        let area = bounds.insetBy(dx: margin, dy: margin)
        let guides = guides ?? []
        rulerBands.isHidden = guides.isEmpty
        rulerTicks.isHidden = guides.isEmpty
        fit(&boxes, count: guides.count, in: layer!) {
            let box = CAShapeLayer()
            box.fillColor = nil
            box.strokeColor = accent.cgColor
            box.lineWidth = 1.5
            return box
        }
        fit(&labels, count: guides.count, in: layer!, make: makeLabel)
        for (index, guide) in guides.enumerated() {
            let rect = layerRect(guide.rect, window: window, in: area)
            boxes[index].path = CGPath(rect: rect, transform: nil)
            let text = "\(guide.number)"
            let width = ceil((text as NSString).size(withAttributes: [.font: NSFont.systemFont(ofSize: 10, weight: .semibold)]).width) + 8
            // Above the top left corner (the frame's y is the label's bottom); inside the box when the ruler band is in the way.
            let bottom = rect.maxY + 14 > area.maxY - rulerWidth ? rect.maxY - 14 : rect.maxY
            labels[index].frame = CGRect(x: max(rect.minX, area.minX + rulerWidth), y: bottom, width: width, height: 14)
            labels[index].string = text
        }
        guard !guides.isEmpty else { return fit(&rulerLabels, count: 0, in: layer!, make: makeLabel) }
        let bands = CGMutablePath()
        bands.addRect(CGRect(x: area.minX, y: area.maxY - rulerWidth, width: area.width, height: rulerWidth))
        bands.addRect(CGRect(x: area.minX, y: area.minY, width: rulerWidth, height: area.height - rulerWidth))
        rulerBands.path = bands
        let ticks = CGMutablePath()
        var numbers: [(String, CGRect)] = []
        for x in stride(from: 50, to: Int(window.width), by: 50) {
            let long = x % 100 == 0
            let at = layerPoint(CGPoint(x: window.minX + CGFloat(x), y: window.minY), window: window, in: area)
            ticks.move(to: CGPoint(x: at.x, y: at.y))
            ticks.addLine(to: CGPoint(x: at.x, y: at.y - (long ? 12 : 6)))
            if long { numbers.append(("\(x)", CGRect(x: at.x + 2, y: at.y - 14, width: 30, height: 12))) }
        }
        for y in stride(from: 50, to: Int(window.height), by: 50) {
            let long = y % 100 == 0
            let at = layerPoint(CGPoint(x: window.minX, y: window.minY + CGFloat(y)), window: window, in: area)
            ticks.move(to: CGPoint(x: at.x, y: at.y))
            ticks.addLine(to: CGPoint(x: at.x + (long ? 12 : 6), y: at.y))
            if long { numbers.append(("\(y)", CGRect(x: at.x + 1, y: at.y - 14, width: 30, height: 12))) }
        }
        rulerTicks.path = ticks
        fit(&rulerLabels, count: numbers.count, in: layer!) {
            let label = makeLabel()
            label.backgroundColor = nil
            label.borderWidth = 0
            label.alignmentMode = .left
            return label
        }
        for (index, number) in numbers.enumerated() {
            rulerLabels[index].frame = number.1
            rulerLabels[index].string = number.0
        }
    }

    /// The goal and the step, in a box at the bottom middle of the target window, or nothing.
    func show(goal: String, step: String?) {
        CATransaction.begin()
        CATransaction.setDisableActions(true)
        defer { CATransaction.commit() }
        guard let step else { return captionBox.isHidden = true }
        let paragraph = NSMutableParagraphStyle()
        paragraph.alignment = .center
        paragraph.lineBreakMode = .byTruncatingTail
        let text = NSMutableAttributedString()
        if !goal.isEmpty {
            text.append(NSAttributedString(string: goal + "\n", attributes: [
                .font: NSFont.systemFont(ofSize: 11), .foregroundColor: NSColor.white.withAlphaComponent(0.75)]))
        }
        text.append(NSAttributedString(string: step, attributes: [
            .font: NSFont.systemFont(ofSize: 13, weight: .semibold), .foregroundColor: NSColor.white]))
        text.addAttribute(.paragraphStyle, value: paragraph, range: NSRange(location: 0, length: text.length))
        let widest = max(bounds.width - 2 * margin - 40, 80)
        let size = text.boundingRect(with: NSSize(width: widest, height: 120), options: [.usesLineFragmentOrigin]).size
        let box = NSSize(width: ceil(size.width) + 24, height: ceil(size.height) + 12)
        captionBox.frame = NSRect(x: bounds.midX - box.width / 2, y: margin + 14, width: box.width, height: box.height)
        caption.frame = captionBox.bounds.insetBy(dx: 12, dy: 6)
        caption.string = text
        captionBox.isHidden = false
    }

    override func layout() {
        super.layout()
        ring.frame = bounds
        // The stroke sits just outside the target window's edge.
        let edge = bounds.insetBy(dx: margin - 1.5, dy: margin - 1.5)
        ring.path = CGPath(roundedRect: edge, cornerWidth: 14, cornerHeight: 14, transform: nil)
    }
}

/// A panel that keeps the frame it gets. AppKit otherwise moves a window down below the menu bar,
/// and the glow around a window at the top of the screen goes out of line by the margin.
final class UnconstrainedPanel: NSPanel {
    override func constrainFrameRect(_ frameRect: NSRect, to screen: NSScreen?) -> NSRect { frameRect }
}

/// A button that works on the first click, while another app is active.
final class FirstClickButton: NSButton {
    override func acceptsFirstMouse(for event: NSEvent?) -> Bool { true }
}

/// The preview image. A click calls `onClick`; a drag moves the preview.
final class ClickableView: NSView {
    var onClick: () -> Void = {}

    override func acceptsFirstMouse(for event: NSEvent?) -> Bool { true }
    override var mouseDownCanMoveWindow: Bool { false }
    override func resetCursorRects() { addCursorRect(bounds, cursor: .pointingHand) }
    override func accessibilityPerformPress() -> Bool {
        onClick()
        return true
    }

    override func mouseDown(with event: NSEvent) {
        let start = event.locationInWindow
        while let next = window?.nextEvent(matching: [.leftMouseUp, .leftMouseDragged]) {
            if next.type == .leftMouseUp { return onClick() }
            if hypot(next.locationInWindow.x - start.x, next.locationInWindow.y - start.y) > 3 {
                window?.performDrag(with: event)
                return
            }
        }
    }
}

/// Show the user the target window: un-minimize it, raise it, and bring its app to the front.
/// The accessibility window is found by its frame, else by its title. Without the Accessibility
/// permission (or with no match, for example on another Space), only the app comes to the front.
func bringToFront(_ id: CGWindowID) {
    guard let target = (CGWindowListCopyWindowInfo(.optionIncludingWindow, id) as? [[String: Any]])?.first,
          let pid = target[kCGWindowOwnerPID as String] as? pid_t else { return }
    let frame = bounds(of: target)
    let name = target[kCGWindowName as String] as? String
    let axApp = AXUIElementCreateApplication(pid)
    var value: CFTypeRef?
    AXUIElementCopyAttributeValue(axApp, kAXWindowsAttribute as CFString, &value)
    let windows = value as? [AXUIElement] ?? []
    func attribute(_ window: AXUIElement, _ name: String) -> CFTypeRef? {
        var result: CFTypeRef?
        AXUIElementCopyAttributeValue(window, name as CFString, &result)
        return result
    }
    func axFrame(_ window: AXUIElement) -> CGRect? {
        var origin = CGPoint.zero, size = CGSize.zero
        guard let position = attribute(window, kAXPositionAttribute), let extent = attribute(window, kAXSizeAttribute),
              AXValueGetValue(position as! AXValue, .cgPoint, &origin),
              AXValueGetValue(extent as! AXValue, .cgSize, &size) else { return nil }
        return CGRect(origin: origin, size: size)
    }
    let match = windows.first { frame != nil && axFrame($0) == frame }
        ?? windows.first { name != nil && attribute($0, kAXTitleAttribute) as? String == name }
    if let match {
        AXUIElementSetAttributeValue(match, kAXMinimizedAttribute as CFString, kCFBooleanFalse)
        AXUIElementPerformAction(match, kAXRaiseAction as CFString)
        AXUIElementSetAttributeValue(axApp, kAXFrontmostAttribute as CFString, kCFBooleanTrue)
    }
    NSRunningApplication(processIdentifier: pid)?.activate()
}

final class Preview: NSObject, SCStreamOutput, SCStreamDelegate {
    static let width: CGFloat = 280
    static let header: CGFloat = 28

    let windowID: CGWindowID
    let panel: NSPanel
    let image = CALayer()
    let pointer = makePointer()
    let message = NSTextField(wrappingLabelWithString: "")
    let label = NSTextField(labelWithString: "")
    let name = owner.map { $0 == title ? title : "\($0) — \(title)" } ?? title
    var stream: SCStream?
    var starting = false
    /// Where place() last put the preview. A different origin means that the user dragged it.
    var placedOrigin: NSPoint?
    /// The user closed the preview. It stays closed while this process runs.
    var dismissed = false

    init(windowID: CGWindowID, aspect: CGFloat) {
        self.windowID = windowID
        let imageHeight = min(max(Preview.width * aspect, 90), 240)
        let size = NSSize(width: Preview.width, height: imageHeight + Preview.header)
        panel = NSPanel(contentRect: NSRect(origin: .zero, size: size),
                        styleMask: [.borderless, .nonactivatingPanel], backing: .buffered, defer: false)
        panel.title = previewTitle
        panel.isOpaque = false
        panel.backgroundColor = .clear
        panel.hasShadow = true
        panel.level = .floating
        panel.hidesOnDeactivate = false
        panel.becomesKeyOnlyIfNeeded = true
        panel.isMovableByWindowBackground = true
        panel.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary, .ignoresCycle]
        super.init()

        let background = NSVisualEffectView(frame: NSRect(origin: .zero, size: size))
        background.material = .hudWindow
        background.blendingMode = .behindWindow
        background.state = .active
        background.wantsLayer = true
        background.layer?.cornerRadius = 10
        background.layer?.masksToBounds = true
        background.layer?.borderWidth = 1.5
        background.layer?.borderColor = accent.cgColor  // Same color as this window's glow.
        panel.contentView = background

        label.stringValue = name
        label.font = .systemFont(ofSize: 11, weight: .medium)
        label.lineBreakMode = .byTruncatingTail
        label.frame = NSRect(x: 10, y: size.height - Preview.header + 7, width: size.width - 44, height: 15)
        background.addSubview(label)

        let close = FirstClickButton(frame: NSRect(x: size.width - 28, y: size.height - Preview.header + 4, width: 22, height: 20))
        close.image = NSImage(systemSymbolName: "xmark.circle.fill", accessibilityDescription: "미리보기 닫기")
        close.isBordered = false
        close.contentTintColor = .secondaryLabelColor
        close.toolTip = "미리보기 닫기"
        close.target = self
        close.action = #selector(closeClicked)
        background.addSubview(close)

        let imageView = ClickableView(frame: NSRect(x: 6, y: 6, width: size.width - 12, height: imageHeight - 6))
        imageView.onClick = { bringToFront(windowID) }
        imageView.toolTip = "클릭하면 이 창으로 이동합니다"
        imageView.wantsLayer = true
        // Captured frames have opaque corners, so the image gets the window's aspect and its own rounded corners.
        let box = imageView.bounds
        let fitted = aspect > box.height / box.width
            ? NSSize(width: box.height / aspect, height: box.height)
            : NSSize(width: box.width, height: box.width * aspect)
        image.frame = NSRect(x: box.midX - fitted.width / 2, y: box.midY - fitted.height / 2,
                             width: fitted.width, height: fitted.height)
        image.contentsGravity = .resize
        image.cornerRadius = 14
        image.masksToBounds = true
        imageView.layer?.addSublayer(image)
        imageView.layer?.addSublayer(pointer)
        imageView.setAccessibilityElement(true)
        imageView.setAccessibilityRole(.button)
        imageView.setAccessibilityLabel("\(name) 창으로 이동")
        background.addSubview(imageView)

        message.font = .systemFont(ofSize: 11)
        message.textColor = .secondaryLabelColor
        message.alignment = .center
        message.frame = imageView.frame.insetBy(dx: 12, dy: 12)
        // Below the image, so that clicks go to the image. The message shows only while there is no image.
        background.addSubview(message, positioned: .below, relativeTo: imageView)
    }

    /// The window's name, and the step of mac-cu while there is one.
    func show(step: String?) {
        let text = step.map { "\($0) — \(name)" } ?? name
        if label.stringValue != text { label.stringValue = text }
    }

    @objc func closeClicked() {
        dismissed = true
        hide()
    }

    func show() {
        guard !dismissed else { return }
        // Order the panel front only when it appears. Each target window has its own process, and
        // previews that order themselves front on every check change places with each other.
        if !panel.isVisible {
            if placedOrigin == nil || panel.frame.origin == placedOrigin { place() }
            panel.orderFrontRegardless()
        } else if panel.frame.origin == placedOrigin && coversOlderPreview() {
            place()  // Two previews that appeared at the same time chose the same place. The newer one moves.
        }
        startStream()
    }

    /// True when this preview covers the preview of a process that started before this one.
    func coversOlderPreview() -> Bool {
        onScreenWindows().contains {
            $0[kCGWindowName as String] as? String == previewTitle
                && ($0[kCGWindowOwnerPID as String] as? pid_t ?? .max) < getpid()
                && bounds(of: $0).map(appKitRect)?.intersects(panel.frame) == true
        }
    }

    func hide() {
        panel.orderOut(nil)
        stream?.stopCapture { _ in }
        stream = nil
    }

    /// Put the preview in the lowest free place in the lower right corner, where it does not cover
    /// the previews of other target windows.
    func place() {
        guard let screen = NSScreen.main?.visibleFrame else { return }
        let others = onScreenWindows().filter {
            $0[kCGWindowName as String] as? String == previewTitle
                && $0[kCGWindowOwnerPID as String] as? pid_t != getpid()
        }.compactMap { bounds(of: $0).map(appKitRect) }
        let size = panel.frame.size
        let x = screen.maxX - size.width - 16
        let candidates = ([screen.minY + 16] + others.map { $0.maxY + 12 }).sorted()
        let free = candidates.first { y in
            y + size.height <= screen.maxY
                && !others.contains { $0.intersects(NSRect(x: x, y: y, width: size.width, height: size.height)) }
        }
        let origin = NSPoint(x: x, y: free ?? screen.maxY - size.height)
        panel.setFrameOrigin(origin)
        placedOrigin = origin
    }

    func startStream() {
        guard stream == nil, !starting else { return }
        starting = true
        let size = image.bounds.size
        let scale = panel.backingScaleFactor
        Task { @MainActor in
            defer { starting = false }
            do {
                let content = try await SCShareableContent.excludingDesktopWindows(false, onScreenWindowsOnly: false)
                guard let window = content.windows.first(where: { $0.windowID == windowID }) else { return }
                let config = SCStreamConfiguration()
                let fit = min(size.width / window.frame.width, size.height / window.frame.height)
                config.width = max(Int(window.frame.width * fit * scale), 1)
                config.height = max(Int(window.frame.height * fit * scale), 1)
                config.minimumFrameInterval = CMTime(value: 1, timescale: 5)
                config.showsCursor = false
                config.backgroundColor = .clear  // Keep the rounded window corners transparent.
                config.shouldBeOpaque = false
                let newStream = SCStream(filter: SCContentFilter(desktopIndependentWindow: window), configuration: config, delegate: self)
                try newStream.addStreamOutput(self, type: .screen, sampleHandlerQueue: .main)
                try await newStream.startCapture()
                message.stringValue = ""
                if panel.isVisible { stream = newStream } else { try? await newStream.stopCapture() }
            } catch {
                message.stringValue = "미리보기를 표시할 수 없습니다. 이 터미널 앱의 화면 기록 권한을 확인하세요."
            }
        }
    }

    func stream(_ stream: SCStream, didOutputSampleBuffer buffer: CMSampleBuffer, of type: SCStreamOutputType) {
        // Only complete frames carry new pixels; idle frames have no image.
        guard type == .screen, let pixels = buffer.imageBuffer,
              let infos = CMSampleBufferGetSampleAttachmentsArray(buffer, createIfNecessary: false) as? [[SCStreamFrameInfo: Any]],
              let status = infos.first?[.status] as? Int, SCFrameStatus(rawValue: status) == .complete
        else { return }
        // A CGImage keeps the alpha channel, so the rounded window corners stay transparent.
        var frame: CGImage?
        VTCreateCGImageFromCVPixelBuffer(pixels, options: nil, imageOut: &frame)
        image.contents = frame
    }

    func stream(_ stream: SCStream, didStopWithError error: Error) {
        DispatchQueue.main.async { if self.stream === stream { self.stream = nil } }
    }
}

final class Overlay: NSObject {
    let panel: NSPanel
    var target: CGWindowID?
    var preview: Preview?
    var waitedTicks = 0
    var ticks = 0

    override init() {
        panel = UnconstrainedPanel(contentRect: .zero, styleMask: [.borderless, .nonactivatingPanel], backing: .buffered, defer: false)
        panel.isOpaque = false
        panel.backgroundColor = .clear
        panel.hasShadow = false
        panel.ignoresMouseEvents = true
        panel.level = .normal
        panel.collectionBehavior = [.ignoresCycle, .fullScreenAuxiliary, .transient]
        panel.contentView = GlowView(frame: .zero)
        super.init()
        Timer.scheduledTimer(withTimeInterval: 1.0 / 20, repeats: true) { [weak self] _ in self?.tick() }
    }

    func leaseIsValid() -> Bool {
        guard let attributes = try? FileManager.default.attributesOfItem(atPath: statePath),
              let modified = attributes[.modificationDate] as? Date else { return false }
        return Date().timeIntervalSince(modified) < maxIdle
    }

    func tick() {
        guard leaseIsValid() else { exit(0) }
        if target == nil {
            target = findTarget()
            if target == nil {
                waitedTicks += 1
                if waitedTicks > 100 { exit(0) }  // No such window after 5 seconds.
                return
            }
        }
        guard let id = target,
              let info = (CGWindowListCopyWindowInfo(.optionIncludingWindow, id) as? [[String: Any]])?.first,
              let rect = bounds(of: info)
        else { exit(0) }  // The target window closed.
        ticks += 1
        let onScreen = info[kCGWindowIsOnscreen as String] as? Bool == true
        if onScreen {
            let frame = appKitRect(rect).insetBy(dx: -margin, dy: -margin)
            if panel.frame != frame { panel.setFrame(frame, display: true) }
            panel.order(.above, relativeTo: Int(id))
        } else {
            panel.orderOut(nil)  // Minimized, hidden, or on another Space.
        }
        if ticks % 4 == 1 {  // Check about five times a second.
            if preview == nil {
                preview = Preview(windowID: id, aspect: rect.height / max(rect.width, 1))
            }
            if !onScreen || visibleFraction(of: id, in: rect) < visibleEnough {
                preview?.show()
            } else {
                preview?.hide()
            }
            // The pointer shows where mac-cu acted, on the window and on the preview.
            let pid = info[kCGWindowOwnerPID as String] as? pid_t
            let point = pid.flatMap(macCUCursor)
            let step = pid.flatMap(macCUStep)
            if let glow = panel.contentView as? GlowView {
                place(glow.pointer, at: point, window: rect, in: glow.bounds.insetBy(dx: margin, dy: margin))
                glow.show(goal: step?.goal ?? "", step: step?.step)
                glow.showGuides(pid.flatMap(macCUGuides), window: rect)
            }
            if let preview {
                place(preview.pointer, at: point, window: rect, in: preview.image.frame)
                preview.show(step: step?.step)
            }
        }
    }
}

let app = NSApplication.shared
app.setActivationPolicy(.accessory)
let overlay = Overlay()
signal(SIGTERM) { _ in exit(0) }
app.run()
