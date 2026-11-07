import Foundation
import CoreGraphics

@main
struct SimulatorPreviewLayoutSelfcheck {
    static func main() {
        let display = CGRect(x: 1728, y: 30, width: 1920, height: 1000)
        let items = (1...6).map { SimulatorPreviewLayoutItem(id: "\($0)", name: "Device \($0)", screenSize: CGSize(width: 100, height: 200)) }
        func check(_ result: SimulatorPreviewLayout, in frame: CGRect, expected: Int) {
            assert(result.frames.count <= 3)
            assert(result.frames.count + result.overflow.count == expected)
            let rectangles = Array(result.frames.values) + (result.overflowFrame.map { [$0] } ?? [])
            for (index, rect) in rectangles.enumerated() {
                assert(frame.contains(rect))
                assert(rectangles.dropFirst(index + 1).allSatisfy { !$0.intersects(rect) })
            }
            assert(result.overflow.isEmpty == (result.overflowFrame == nil))
        }
        for count in [1, 3, 4, 6] {
            let result = layoutSimulatorPreviews(Array(items.prefix(count)), in: display)
            check(result, in: display, expected: count)
            assert(result.frames.count == min(3, count))
            assert(result.overflow == (count > 3 ? Array(4...count).map(String.init) : []))
            assert(result.frames == layoutSimulatorPreviews(Array(items.prefix(count).reversed()), in: display).frames)
        }
        let short = CGRect(x: -1000, y: 0, width: 500, height: 550)
        let reduced = layoutSimulatorPreviews(items, in: short)
        check(reduced, in: short, expected: 6)
        assert(reduced.frames.count < 3)
        let tiny = CGRect(x: 0, y: 0, width: 300, height: 180)
        check(layoutSimulatorPreviews(items, in: tiny), in: tiny, expected: 6)
        var moved = items[4]
        moved.manualFrame = CGRect(x: 1800, y: 300, width: 110, height: 222)
        let manual = layoutSimulatorPreviews(items + [], in: display)
        let preserved = layoutSimulatorPreviews([moved] + items.filter { $0.id != moved.id }, in: display)
        check(preserved, in: display, expected: 6)
        assert(preserved.frames[moved.id] == moved.manualFrame)
        assert(preserved.frames == layoutSimulatorPreviews([moved] + items.filter { $0.id != moved.id }, in: display).frames)
        assert(manual.frames["5"] == nil)
        moved.manualFrame = CGRect(x: 6000, y: -4000, width: 110, height: 222)
        check(layoutSimulatorPreviews([moved] + Array(items.prefix(2)), in: display), in: display, expected: 3)
        let sameNames = [SimulatorPreviewLayoutItem(id: "b", name: "Same", screenSize: CGSize(width: 300, height: 100)),
                         SimulatorPreviewLayoutItem(id: "a", name: "Same", screenSize: CGSize(width: 100, height: 200))]
        let tie = layoutSimulatorPreviews(sameNames, in: display)
        assert(tie.frames["a"]!.minY > tie.frames["b"]!.minY)
        let one = layoutSimulatorPreviews(Array(items.prefix(1)), in: display).frames["1"]!
        assert(abs(one.width / (one.height - 22) - 0.5) < 0.0001)
        print("Preview layout checks passed: stable order, 1/3/4/6 items, overflow counts, short displays, manual placement, boundaries and aspect ratio.")
    }
}
