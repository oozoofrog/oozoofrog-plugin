import AppKit
import QuartzCore

@MainActor private final class PermissionHintPanel: NSPanel {
    override var canBecomeKey: Bool { false }
    override var canBecomeMain: Bool { false }
}

/// A decorative copy demonstrates a drag. It never posts an input event, moves
/// the system pointer, changes the pasteboard, or accepts a permission prompt.
@MainActor final class PermissionDragOnboarding {
    let panel: NSPanel
    private let ghost = NSView(frame: NSRect(x: 0, y: 0, width: 72, height: 72))
    private var kind: PermissionKind?
    private var geometry: CGRect?
    private var nextPlay = Date.distantPast
    private var token: UUID?
    private var suspended = true
    private var manualReplay = false
    private(set) var playCount = 0
    private(set) var userInteracted = false
    private(set) var isPlaying = false

    init(applicationURL: URL) {
        panel = PermissionHintPanel(contentRect: .zero, styleMask: [.borderless, .nonactivatingPanel], backing: .buffered, defer: false)
        panel.title = "MacPilot 드래그 안내"
        panel.isReleasedWhenClosed = false
        panel.isOpaque = false; panel.backgroundColor = .clear; panel.hasShadow = false
        panel.hidesOnDeactivate = false; panel.isFloatingPanel = false
        panel.level = .normal; panel.animationBehavior = .none
        panel.ignoresMouseEvents = true
        panel.collectionBehavior = [.transient, .ignoresCycle, .moveToActiveSpace]
        panel.setAccessibilityElement(false); panel.setAccessibilityChildren([])
        let root = NSView(); root.wantsLayer = true
        root.setAccessibilityElement(false)
        panel.contentView = root
        ghost.wantsLayer = true
        ghost.layer?.anchorPoint = CGPoint(x: 0.5, y: 0.5)
        ghost.setAccessibilityElement(false)
        let icon = NSImageView(frame: NSRect(x: 0, y: 16, width: 56, height: 56))
        icon.image = NSWorkspace.shared.icon(forFile: applicationURL.path)
        icon.imageScaling = .scaleProportionallyUpOrDown
        icon.setAccessibilityElement(false)
        let hand = NSImageView(frame: NSRect(x: 42, y: 0, width: 24, height: 24))
        hand.image = NSCursor.closedHand.image
        hand.imageScaling = .scaleProportionallyUpOrDown
        hand.setAccessibilityElement(false)
        ghost.addSubview(icon); ghost.addSubview(hand); root.addSubview(ghost)
    }

    // The destination is a visual direction cue in the settings content area.
    // It is not an AX-verified drop target, including before AX/Screen consent.
    static func destination(settings: CGRect) -> CGPoint {
        CGPoint(x: settings.minX + settings.width * 0.68,
                y: settings.maxY - min(230, settings.height * 0.3))
    }
    static func bounds(source: CGPoint, destination: CGPoint) -> CGRect {
        CGRect(x: min(source.x, destination.x)-48, y: min(source.y, destination.y)-48,
               width: abs(source.x-destination.x)+96, height: abs(source.y-destination.y)+96)
    }
    var evidence: [String: Any] {
        ["playing": isPlaying, "playCount": playCount, "userInteracted": userInteracted,
         "visible": panel.isVisible, "windowID": panel.windowNumber,
         "ignoresMouseEvents": panel.ignoresMouseEvents, "postsInputEvents": false]
    }
    func stop() {
        token = nil; isPlaying = false
        ghost.layer?.removeAllAnimations(); ghost.layer?.opacity = 0
        panel.orderOut(nil)
    }
    func pause() { suspended = true; stop() }
    func userDidInteract() { userInteracted = true; stop() }
    func replay() {
        userInteracted = false; playCount = 0; nextPlay = .distantPast
        manualReplay = true
        stop()
    }
    func update(source: NSWindow, settings: CGRect, kind selected: PermissionKind,
                allowed: Bool?, eligible: Bool, reducedMotion: Bool, now: Date = Date()) {
        let sourcePoint = CGPoint(x: source.frame.midX, y: source.frame.midY)
        let end = Self.destination(settings: settings)
        let bounds = Self.bounds(source: sourcePoint, destination: end)
        if kind != selected {
            kind = selected; playCount = 0; userInteracted = false
            manualReplay = false
            nextPlay = now.addingTimeInterval(0.8); stop()
        }
        if geometry != bounds {
            geometry = bounds; nextPlay = now.addingTimeInterval(0.8); stop()
        }
        guard eligible, selected.acceptsAppDrop, allowed != true || manualReplay, !reducedMotion else { pause(); return }
        if suspended { suspended = false; nextPlay = now.addingTimeInterval(0.8) }
        if isPlaying { panel.order(.above, relativeTo: source.windowNumber); return }
        guard !userInteracted, !isPlaying, playCount < 2, now >= nextPlay else { return }
        panel.setFrame(bounds, display: false)
        let start = CGPoint(x: sourcePoint.x-bounds.minX+8, y: sourcePoint.y-bounds.minY-8)
        let finish = CGPoint(x: end.x-bounds.minX+8, y: end.y-bounds.minY-8)
        let midpoint = CGPoint(x: (start.x+finish.x)/2, y: (start.y+finish.y)/2+16)
        ghost.layer?.position = start
        ghost.layer?.opacity = 0
        let position = CAKeyframeAnimation(keyPath: "position")
        position.values = [NSValue(point: start), NSValue(point: start), NSValue(point: midpoint), NSValue(point: finish), NSValue(point: finish)]
        position.keyTimes = [0, 0.15, 0.5, 0.86, 1]
        position.calculationMode = .cubic
        let opacity = CAKeyframeAnimation(keyPath: "opacity")
        opacity.values = [0, 0.85, 0.85, 0]
        opacity.keyTimes = [0, 0.12, 0.82, 1]
        let animation = CAAnimationGroup()
        animation.animations = [position, opacity]
        animation.duration = 1.45
        animation.timingFunction = CAMediaTimingFunction(name: .easeInEaseOut)
        panel.order(.above, relativeTo: source.windowNumber)
        let current = UUID(); token = current; isPlaying = true; playCount += 1
        ghost.layer?.add(animation, forKey: "permission.drag.demonstration")
        DispatchQueue.main.asyncAfter(deadline: .now()+1.5) { [weak self] in
            guard let self, self.token == current else { return }
            self.stop(); self.nextPlay = Date().addingTimeInterval(3)
        }
    }
}
