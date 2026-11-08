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
        for screen in [screen, landscape, CGSize(width: 678, height: 466)] {
            for viewport in [portrait, CGRect(x: 16, y: 30, width: 233, height: 339), CGRect(x: 0, y: 0, width: 900, height: 450)] {
                for point in [CGPoint(x: 20, y: 30), CGPoint(x: screen.width / 2, y: screen.height / 2), CGPoint(x: screen.width - 1, y: screen.height - 1)] {
                    let shown = simulatorTouchPosition(point, viewport: viewport, screen: screen)!
                    let back = simulatorScreenPoint(shown, viewport: viewport, screen: screen, clamp: false)!
                    assert(hypot(back.x - point.x, back.y - point.y) < 0.00001)
                }
            }
        }
        assert(simulatorScreenPoint(CGPoint(x: -20, y: -20), viewport: portrait, screen: screen, clamp: false) == nil)
        assert(simulatorScreenPoint(CGPoint(x: -20, y: -20), viewport: portrait, screen: screen, clamp: true) == CGPoint(x: 0, y: 678))
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
        for scale: CGFloat in [1, 2, 3] {
            overlay.layout(viewport: portrait, screen: screen, backingScale: scale)
            assert(overlay.layer.sublayers!.flatMap { $0.sublayers ?? [] }.allSatisfy { $0.contentsScale == scale })
        }
        overlay.clear()
        assert((overlay.layer.sublayers ?? []).isEmpty)
        print("Touch overlay checks passed: portrait, landscape fit, three fingers, independent lift, repeated tap and cleanup.")
    }
}
