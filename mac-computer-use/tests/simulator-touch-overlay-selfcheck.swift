import AppKit

struct GestureContact { let id: Int; let point: CGPoint; let touching: Bool }

@main
struct TouchOverlaySelfcheck {
    static func main() {
        let portrait = CGRect(x: 0, y: 0, width: 466, height: 678)
        let screen = portrait.size
        assert(simulatorTouchPosition(.zero, viewport: portrait, screen: screen) == CGPoint(x: 0, y: 678))
        assert(simulatorTouchPosition(CGPoint(x: 466, y: 678), viewport: portrait, screen: screen) == CGPoint(x: 466, y: 0))
        let landscape = CGSize(width: 951, height: 669)
        assert(simulatorTouchPosition(CGPoint(x: 475.5, y: 334.5), viewport: portrait, screen: landscape) == CGPoint(x: 233, y: 339))
        assert(simulatorTouchPosition(.zero, viewport: portrait, screen: .zero) == nil)
        let overlay = SimulatorTouchOverlay()
        overlay.layout(viewport: portrait, screen: screen)
        let three = (1...3).map { GestureContact(id: $0, point: CGPoint(x: $0 * 100, y: 400), touching: true) }
        overlay.update(three)
        assert(overlay.layer.sublayers?.count == 3)
        assert(overlay.layer.sublayers!.allSatisfy { $0.opacity == 1 && $0.position.y == 278 })
        overlay.update([three[1]])
        assert(overlay.layer.sublayers!.filter { $0.opacity == 1 }.count == 1)
        overlay.update([three[0], three[1]])  // A second tap must survive the first tap's pending fade.
        RunLoop.main.run(until: Date().addingTimeInterval(0.3))
        assert(overlay.layer.sublayers?.count == 2)
        overlay.update([])
        RunLoop.main.run(until: Date().addingTimeInterval(0.3))
        assert((overlay.layer.sublayers ?? []).isEmpty)
        overlay.update(three)
        overlay.clear()
        assert((overlay.layer.sublayers ?? []).isEmpty)
        print("Touch overlay checks passed: portrait, landscape fit, three fingers, independent lift, repeated tap and cleanup.")
    }
}
