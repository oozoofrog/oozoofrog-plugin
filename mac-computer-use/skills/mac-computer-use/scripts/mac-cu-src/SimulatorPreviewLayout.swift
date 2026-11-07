import Foundation
import CoreGraphics

let simulatorPreviewCaptionHeight: CGFloat = 22

struct SimulatorPreviewLayoutItem {
    let id: String
    let name: String
    let screenSize: CGSize
    var manualFrame: CGRect? = nil
}

struct SimulatorPreviewLayout {
    var frames: [String: CGRect] = [:]
    var overflow: [String] = []
    var overflowFrame: CGRect?
}

/// AppKit coordinates. Manual placements occupy capacity first; automatic cards flow down the right edge.
func layoutSimulatorPreviews(_ items: [SimulatorPreviewLayoutItem], in visibleFrame: CGRect) -> SimulatorPreviewLayout {
    let sorted = items.sorted {
        let order = $0.name.localizedStandardCompare($1.name)
        return order == .orderedSame ? $0.id < $1.id : order == .orderedAscending
    }
    let area = visibleFrame.insetBy(dx: 12, dy: 12)
    guard area.width >= 28, area.height >= 28 else {
        return SimulatorPreviewLayout(overflow: sorted.map(\.id))
    }
    let priority = sorted.filter { $0.manualFrame != nil } + sorted.filter { $0.manualFrame == nil }
    let gap: CGFloat = 12
    for count in stride(from: min(3, items.count), through: 0, by: -1) {
        let chosen = Array(priority.prefix(count))
        let chosenIDs = Set(chosen.map(\.id))
        var result = SimulatorPreviewLayout(overflow: sorted.filter { !chosenIDs.contains($0.id) }.map(\.id))
        var occupied: [CGRect] = []
        var cursor = area.maxY

        func fits(_ rect: CGRect) -> Bool {
            area.contains(rect) && occupied.allSatisfy { !$0.insetBy(dx: -gap / 2, dy: -gap / 2).intersects(rect.insetBy(dx: -gap / 2, dy: -gap / 2)) }
        }
        func nextFrame(_ size: CGSize) -> CGRect? {
            while cursor - size.height >= area.minY {
                let rect = CGRect(x: area.maxX - size.width, y: cursor - size.height, width: size.width, height: size.height)
                if fits(rect) { cursor = rect.minY - gap; return rect }
                let blockers = occupied.filter { $0.insetBy(dx: -gap, dy: -gap).intersects(rect) }
                guard let bottom = blockers.map(\.minY).min() else { return nil }
                cursor = min(cursor - gap, bottom - gap)
            }
            return nil
        }
        for item in chosen {
            let valid = item.screenSize.width.isFinite && item.screenSize.height.isFinite && item.screenSize.width > 0 && item.screenSize.height > 0
            let screen = valid ? item.screenSize : CGSize(width: 1, height: 1)
            let availableHeight = count == 1 ? area.height - (result.overflow.isEmpty ? 0 : 40) : area.height
            guard availableHeight >= 64 else { break }
            let scale = min(min(180, area.width) / screen.width, min(200, availableHeight - simulatorPreviewCaptionHeight) / screen.height)
            let size = CGSize(width: screen.width * scale, height: screen.height * scale + simulatorPreviewCaptionHeight)
            var frame: CGRect?
            if let manual = item.manualFrame, manual.width > 0, manual.height > 0,
               manual.origin.x.isFinite, manual.origin.y.isFinite, manual.width.isFinite, manual.height.isFinite {
                let fit = min(1, area.width / manual.width, area.height / manual.height)
                let extent = CGSize(width: manual.width * fit, height: manual.height * fit)
                let clamped = CGRect(x: min(max(manual.minX, area.minX), area.maxX - extent.width),
                                     y: min(max(manual.minY, area.minY), area.maxY - extent.height),
                                     width: extent.width, height: extent.height)
                if fits(clamped) { frame = clamped }
            }
            if frame == nil { frame = nextFrame(size) }
            guard let frame else { break }
            result.frames[item.id] = frame
            occupied.append(frame)
        }
        guard result.frames.count == count else { continue }
        if !result.overflow.isEmpty {
            guard let frame = nextFrame(CGSize(width: min(60, area.width), height: 28)) else { continue }
            result.overflowFrame = frame
        }
        return result
    }
    return SimulatorPreviewLayout(overflow: sorted.map(\.id))
}
