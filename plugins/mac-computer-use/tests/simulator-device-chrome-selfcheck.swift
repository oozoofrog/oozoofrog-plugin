import AppKit

@main
struct SimulatorDeviceChromeSelfcheck {
    static func descendants(_ view: NSView) -> [NSView] { [view] + view.subviews.flatMap(descendants) }
    static func main() {
        _ = NSApplication.shared
        let chrome = SimulatorDeviceChrome()
        let tools = SimulatorToolboxView(deviceName: "Fixture", isWatch: false)
        let lcd = NSView(frame: CGRect(x: 0, y: 0, width: 400, height: 600))
        let content = SimulatorLCDContentView(lcd: lcd, tools: tools, appearance: SimulatorDeviceAppearance(typeName: "iPhone"))
        let window = SimulatorDeviceWindow(contentRect: CGRect(x: 0, y: 0, width: 750, height: 800),
                                           styleMask: [.borderless, .resizable, .miniaturizable, .closable], backing: .buffered, defer: false)
        window.isReleasedWhenClosed = false
        defer { window.close() }
        window.isOpaque = false; window.backgroundColor = .clear
        window.contentView = content
        content.screen = CGSize(width: 466, height: 678)
        content.needsLayout = true; content.layoutSubtreeIfNeeded()
        assert(window.canBecomeKey && window.canBecomeMain && !window.styleMask.contains(.titled))
        assert(window.isMovable && !window.isMovableByWindowBackground, "Borderless dragging requires explicit movability without LCD background dragging")
        window.interactiveMove = true
        let unbounded = CGRect(x: -9000, y: 9000, width: 750, height: 800)
        assert(window.constrainFrameRect(unbounded, to: NSScreen.main) == unbounded, "Do not apply AppKit screen correction in the native drag lifecycle")
        window.interactiveMove = false
        assert(window.standardWindowButton(.closeButton) == nil && window.standardWindowButton(.miniaturizeButton) == nil)
        assert(window.alphaValue == 1)
        assert(content.body.layer!.backgroundColor!.alpha == 1)
        assert(content.hitTest(CGPoint(x: 1, y: 1)) == nil, "Transparent margins must not produce an AppKit hit target")
        let center = lcd.convert(CGPoint(x: lcd.bounds.midX, y: lcd.bounds.midY), to: content)
        assert(content.hitTest(center) === lcd)
        let grip = content.chrome.grip
        let gripCenter = grip.convert(CGPoint(x: grip.bounds.midX, y: grip.bounds.midY), to: content)
        assert(content.hitTest(gripCenter) === grip, "Handle labels must remain draggable and never become LCD input")
        let resize = content.chrome.resize
        let resizeCenter = resize.convert(CGPoint(x: resize.bounds.midX, y: resize.bounds.midY), to: content)
        assert(content.hitTest(resizeCenter) === resize)
        assert(!content.body.frame.intersects(content.chrome.resize.frame), "Resize target must stay outside LCD")
        content.focused = true
        content.needsLayout = true; content.layoutSubtreeIfNeeded()
        assert(content.chrome.controls.isHidden && content.chrome.rail.isHidden && content.chrome.resize.isHidden)
        assert(!content.chrome.handle.isHidden && content.hitTest(grip.convert(CGPoint(x: 20, y: 20), to: content)) === grip)
        assert(content.hitTest(resizeCenter) !== resize, "Focus mode must remove hidden resize hit targets even when LCD occupies the old position")

        var requests: [[String: Any]] = []
        chrome.onRun = { requests.append($0) }
        chrome.updateDevice(name: "Fixture", runtime: "iOS 27.2", connected: true, foldable: false, isWatch: false, rotation: "rot0")
        assert(chrome.grip.label.stringValue.contains("연결됨") && chrome.grip.label.stringValue.contains("iOS 27.2"))
        let buttons = descendants(chrome.controls).compactMap { $0 as? NSButton }
        let fold = buttons.first { $0.title == "접기" }!
        assert(fold.isHidden)
        chrome.updateDevice(name: "Fixture", runtime: "iOS 27.2", connected: false, foldable: true, isWatch: false, rotation: "rot0")
        chrome.updateAngle(130)
        assert(!fold.isHidden && fold.title.contains("130°") && chrome.grip.label.stringValue.contains("화면 대기"))
        chrome.controls.frame = CGRect(x: 0, y: 0, width: 304, height: 60)
        chrome.controls.layoutSubtreeIfNeeded()
        for button in buttons {
            assert(button.frame.width >= 56 && button.frame.height >= 40)
            assert(button.toolTip != nil && button.accessibilityLabel() != nil)
        }
        let rotate = buttons.first { $0.title == "회전" }!
        rotate.performClick(nil)
        assert(requests.last?["orientation"] as? String == "landscape-left")
        rotate.performClick(nil)
        assert(requests.last?["orientation"] as? String == "landscape-left", "A click cannot pretend the device rotated")
        chrome.updateDevice(name: "Fixture", runtime: "iOS 27.2", connected: true, foldable: true, isWatch: false,
                            rotation: "rot90", primaryDisplay: false)
        rotate.performClick(nil)
        assert(requests.last?["orientation"] as? String == "landscape-left", "Duo inner display uses the orientation picker axes")
        chrome.updateDevice(name: "Fixture", runtime: "iOS 27.2", connected: true, foldable: true, isWatch: false, rotation: "rot0", primaryDisplay: false)
        rotate.performClick(nil)
        assert(requests.last?["orientation"] as? String == "portrait", "The next request follows actual inner-display readback")
        chrome.setBusy(true)
        let count = requests.count
        rotate.performClick(nil)
        assert(requests.count == count)
        chrome.showFeedback("저장 실패", failed: true)
        let feedback = descendants(chrome.controls).compactMap { $0 as? NSTextField }.first { $0.accessibilityLabel() == "시뮬레이터 조작 결과" }!
        assert(feedback.stringValue == "저장 실패" && feedback.textColor == .systemRed)
        chrome.setBusy(false)
        let capture = buttons.first { $0.title == "캡처" }!
        capture.performClick(nil)
        assert(requests.last?["action"] as? String == "screenshot")
        let first = Data([1, 2]), active = Data([3, 4])
        assert(simulatorActiveCaptureData([["type": "image", "data": first.base64EncodedString()],
                                           ["type": "text", "text": "Screen 1 LCD (on: its pixels are coordinates)"],
                                           ["type": "image", "data": active.base64EncodedString()]]) == active)
        assert(simulatorActiveCaptureData([["type": "text", "text": "failed"]]) == nil)
        for display in [CGRect(x: -1920, y: 0, width: 1920, height: 1080), CGRect(x: 0, y: 80, width: 1024, height: 768)] {
            let frame = simulatorConstrainedFrame(CGRect(x: -3000, y: -200, width: 1800, height: 1400), to: display)
            assert(display.contains(frame))
        }
        for focused in [false, true] {
            for size in [CGSize(width: 336, height: 400), CGSize(width: 900, height: 700)] {
                let layout = simulatorDeviceLayout(in: size, screen: content.screen, bezel: 5, toolsVisible: false, focused: focused)
                let viewport = CGRect(origin: .zero, size: size)
                assert(viewport.contains(layout.handle) && viewport.contains(layout.body))
                if !focused { assert(viewport.contains(layout.controls) && viewport.contains(layout.rail) && viewport.contains(layout.resize)) }
            }
        }
        print("PASS device chrome: borderless focus eligibility, opaque body, transparent/handle/LCD/resize hit separation, focus recovery, usable controls, backend-driven rotation, busy gating, capture selection/failure feedback and display bounds.")
    }
}
