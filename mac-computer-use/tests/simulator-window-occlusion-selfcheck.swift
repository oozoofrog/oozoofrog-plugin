import AppKit

@main
struct SimulatorWindowOcclusionSelfcheck {
    static func main() {
        let lcd = CGRect(x: 0, y: 0, width: 100, height: 100)
        func area(_ covers: [CGRect], displays: [CGRect] = [CGRect(x: 0, y: 0, width: 100, height: 100)]) -> CGFloat {
            simulatorVisibleArea(lcd, displays: displays, covers: covers)
        }
        assert(area([]) == 10_000)
        assert(area([CGRect(x: 200, y: 200, width: 100, height: 100)]) == 10_000)
        let left = CGRect(x: 0, y: 0, width: 50, height: 100)
        let right = CGRect(x: 50, y: 0, width: 50, height: 100)
        assert(area([left]) == 5_000)
        assert(area([left, right]) == 0)
        assert(area([left, left]) == 5_000)
        assert(area([CGRect(x: 0, y: 0, width: 99, height: 100)]) == 100)
        assert(area([], displays: [CGRect(x: 200, y: 0, width: 100, height: 100)]) == 0)
        assert(area([], displays: [left, right]) == 10_000)
        assert(area([CGRect(x: 25, y: 25, width: 50, height: 50)]) == 7_500)
        let withTools = CGRect(x: 0, y: 0, width: 400, height: 100)
        let display = CGRect(x: 0, y: 0, width: 800, height: 600)
        assert(simulatorVisibleArea(withTools, displays: [display], covers: [lcd]) > 0)
        assert(simulatorVisibleArea(lcd, displays: [display], covers: [lcd]) == 0)
        let cover: [String: Any] = [kCGWindowNumber as String: 42, kCGWindowBounds as String: withTools.dictionaryRepresentation]
        assert(simulatorOcclusionCovers([cover], ignoring: [], shapedWindows: [:]) == [withTools])
        assert(simulatorOcclusionCovers([cover], ignoring: [], shapedWindows: [42: [right]]) == [right])
        assert(simulatorOcclusionCovers([cover], ignoring: [42], shapedWindows: [42: [right]]).isEmpty)
        assert(simulatorOcclusionCovers([cover], ignoring: [], shapedWindows: [42: []]).isEmpty)
        print("LCD occlusion checks passed: focus-independent visibility, partial/full covers, overlaps, thin exposed areas and displays.")
    }
}
