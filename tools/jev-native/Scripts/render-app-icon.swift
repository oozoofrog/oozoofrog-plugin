import AppKit

// Original JEV mark: a virtual pointer crossing a spatial orbit.
// All coordinates are vector paths; small representations get optical corrections.
let root = URL(fileURLWithPath: CommandLine.arguments[1], isDirectory: true)
let fm = FileManager.default
let iconset = root.appendingPathComponent("AppIcon.iconset", isDirectory: true)
try fm.createDirectory(at: iconset, withIntermediateDirectories: true)

func color(_ r: CGFloat, _ g: CGFloat, _ b: CGFloat) -> NSColor {
    NSColor(srgbRed: r, green: g, blue: b, alpha: 1)
}

func drawMark(pixels: Int) {
    let small = pixels <= 32
    let tile = NSBezierPath(roundedRect: NSRect(x: 72, y: 72, width: 880, height: 880), xRadius: 198, yRadius: 198)
    NSGraphicsContext.saveGraphicsState()
    if !small {
        let shadow = NSShadow(); shadow.shadowColor = NSColor.black.withAlphaComponent(0.25)
        shadow.shadowBlurRadius = 22; shadow.shadowOffset = NSSize(width: 0, height: -10); shadow.set()
    }
    NSGradient(starting: color(0.10, 0.24, 0.29), ending: color(0.025, 0.07, 0.12))!.draw(in: tile, angle: -65)
    NSGraphicsContext.restoreGraphicsState()
    if !small {
        color(0.28, 0.49, 0.53).withAlphaComponent(0.45).setStroke()
        tile.lineWidth = 3; tile.stroke()
    }

    NSGraphicsContext.saveGraphicsState()
    let transform = NSAffineTransform(); transform.translateX(by: 512, yBy: 512)
    transform.rotate(byDegrees: 33); transform.concat()
    let orbit = NSBezierPath(ovalIn: NSRect(x: -298, y: -204, width: 596, height: 408))
    orbit.lineWidth = small ? 64 : 43
    color(0.26, 0.86, 0.84).setStroke(); orbit.stroke()
    NSGraphicsContext.restoreGraphicsState()

    // Broad silhouette and generous gaps remain readable at 16 logical points.
    let pointer = NSBezierPath()
    pointer.move(to: NSPoint(x: 365, y: 770))
    for point in [NSPoint(x: 365, y: 395), NSPoint(x: 458, y: 486),
                  NSPoint(x: 564, y: 315), NSPoint(x: 646, y: 366),
                  NSPoint(x: 542, y: 537), NSPoint(x: 677, y: 557)] {
        pointer.line(to: point)
    }
    pointer.close()
    NSGraphicsContext.saveGraphicsState()
    if !small {
        let shadow = NSShadow(); shadow.shadowColor = NSColor.black.withAlphaComponent(0.34)
        shadow.shadowBlurRadius = 15; shadow.shadowOffset = NSSize(width: 0, height: -8); shadow.set()
    }
    color(0.055, 0.15, 0.19).setStroke(); pointer.lineWidth = small ? 22 : 14
    pointer.lineJoinStyle = .round; pointer.stroke()
    NSGradient(starting: color(0.98, 1, 0.98), ending: color(0.80, 0.94, 0.92))!.draw(in: pointer, angle: -90)
    NSGraphicsContext.restoreGraphicsState()
    if pixels >= 128 {
        let node = NSBezierPath(ovalIn: NSRect(x: 728, y: 617, width: 63, height: 63))
        color(0.06, 0.16, 0.20).setStroke(); node.lineWidth = 13; node.stroke()
        color(0.63, 1, 0.91).setFill(); node.fill()
    }
}

func bitmap(_ size: Int, draw: () -> Void) -> NSBitmapImageRep {
    let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: size, pixelsHigh: size,
        bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false,
        colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)
    NSGraphicsContext.current!.imageInterpolation = .high
    draw()
    NSGraphicsContext.restoreGraphicsState()
    return rep
}

var rendered: [Int: NSBitmapImageRep] = [:]
for size in [16, 32, 64, 128, 256, 512, 1024] {
    // Oversample each size independently; no large-master downsampling of thin details.
    let oversample = size < 128 ? 4 : 2
    let high = bitmap(size * oversample) {
        let t = NSAffineTransform(); t.scale(by: CGFloat(size * oversample) / 1024); t.concat()
        drawMark(pixels: size)
    }
    let rep = bitmap(size) {
        let image = NSImage(size: NSSize(width: size * oversample, height: size * oversample))
        image.addRepresentation(high)
        image.draw(in: NSRect(x: 0, y: 0, width: size, height: size))
    }
    rendered[size] = rep
}
for logical in [16, 32, 128, 256, 512] {
    for scale in [1, 2] {
        let suffix = scale == 2 ? "@2x" : ""
        let url = iconset.appendingPathComponent("icon_\(logical)x\(logical)\(suffix).png")
        try rendered[logical * scale]!.representation(using: .png, properties: [:])!.write(to: url)
    }
}
try rendered[256]!.representation(using: .png, properties: [:])!.write(to: root.appendingPathComponent("JevNative-icon-preview.png"))
print(iconset.path)
