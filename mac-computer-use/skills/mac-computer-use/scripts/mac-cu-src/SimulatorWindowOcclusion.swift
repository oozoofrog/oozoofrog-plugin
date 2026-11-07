import AppKit

/// Subtract opaque window rectangles; any remaining on-display area means the LCD is still visible.
func simulatorVisibleArea(_ target: CGRect, displays: [CGRect], covers: [CGRect]) -> CGFloat {
    var exposed = displays.map { target.intersection($0) }.filter { !$0.isEmpty }
    for cover in covers {
        exposed = exposed.flatMap { rect -> [CGRect] in
            let overlap = rect.intersection(cover)
            guard !overlap.isEmpty else { return [rect] }
            return [CGRect(x: rect.minX, y: rect.minY, width: rect.width, height: overlap.minY - rect.minY),
                    CGRect(x: rect.minX, y: overlap.maxY, width: rect.width, height: rect.maxY - overlap.maxY),
                    CGRect(x: rect.minX, y: overlap.minY, width: overlap.minX - rect.minX, height: overlap.height),
                    CGRect(x: overlap.maxX, y: overlap.minY, width: rect.maxX - overlap.maxX, height: overlap.height)]
                .filter { !$0.isEmpty }
        }
        if exposed.isEmpty { return 0 }
    }
    return exposed.reduce(0) { $0 + $1.width * $1.height }
}

func simulatorOcclusionCovers(_ windows: [[String: Any]], ignoring: Set<Int>, shapedWindows: [Int: [CGRect]]) -> [CGRect] {
    windows.flatMap { entry -> [CGRect] in
        let number = entry[kCGWindowNumber as String] as? Int ?? -1
        guard !ignoring.contains(number), entry[kCGWindowOwnerName as String] as? String != "focus-overlay",
              (entry[kCGWindowAlpha as String] as? Double ?? 1) >= 1,
              (entry[kCGWindowLayer as String] as? Int ?? 0) >= 0 else { return [] }
        if let shape = shapedWindows[number] { return shape }
        guard let bounds = entry[kCGWindowBounds as String] as? NSDictionary,
              let frame = CGRect(dictionaryRepresentation: bounds) else { return [] }
        return [frame]
    }
}

func simulatorWindowNeedsPreview(_ window: NSWindow, ignoring: Set<Int>, contentFrame: CGRect? = nil, shapedWindows: [Int: [CGRect]] = [:]) -> Bool {
    guard !window.isMiniaturized, window.isVisible, window.isOnActiveSpace else { return true }
    let windows = CGWindowListCopyWindowInfo([.optionOnScreenOnly, .excludeDesktopElements], kCGNullWindowID) as? [[String: Any]] ?? []
    guard let index = windows.firstIndex(where: { $0[kCGWindowNumber as String] as? Int == window.windowNumber }),
          let bounds = windows[index][kCGWindowBounds as String] as? NSDictionary,
          let windowBounds = CGRect(dictionaryRepresentation: bounds)
    else { return !window.occlusionState.contains(.visible) }
    // Keep the native visible bit for transparent/shaped windows; bounds also exclude our own preview.
    let top = NSScreen.screens.first?.frame.maxY ?? 0
    let shapes = shapedWindows.mapValues { $0.map { CGRect(x: $0.minX, y: top - $0.maxY, width: $0.width, height: $0.height) } }
    let covers = simulatorOcclusionCovers(Array(windows[..<index]), ignoring: ignoring, shapedWindows: shapes)
    let target = contentFrame.map { CGRect(x: $0.minX, y: top - $0.maxY, width: $0.width, height: $0.height) } ?? windowBounds
    let displays = NSScreen.screens.map { CGRect(x: $0.frame.minX, y: top - $0.frame.maxY, width: $0.frame.width, height: $0.frame.height) }
    return (contentFrame != nil || !window.occlusionState.contains(.visible)) && simulatorVisibleArea(target, displays: displays, covers: covers) == 0
}
