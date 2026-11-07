// Measurement guides on a screenshot (get_app_state and act with guides, simulator screenshot with guides):
// rulers along the top and left edges, a 100 px grid, and a numbered box around each element, so that the
// agent reads positions, sizes and distances from the picture and the @x,y w×h of the tree. The same boxes
// go to focus-overlay for the user (showGuides in Modes.swift): the overlay is a separate panel, so a window
// capture never shows it, and the agent's guides must be drawn on the picture itself.

import AppKit

struct GuideBox {
    let number: Int
    /// Pixels of the picture (from its top left) for drawGuides; Window Server points for showGuides.
    let rect: CGRect
}

/// More boxes than this make the picture unreadable: only the first ones are drawn.
let maxGuideBoxes = 50
private let rulerWidth: CGFloat = 18
private let magenta = CGColor(srgbRed: 1, green: 0x2d / 255, blue: 0x95 / 255, alpha: 1)

/// The boxes for the frames of the numbered elements (nil: no frame): none for an empty frame or for a frame
/// that covers more than 90% of the area (the window itself and its big containers hide the picture).
func guideBoxes(_ frames: [CGRect?], within area: CGRect) -> [GuideBox] {
    frames.enumerated().compactMap { number, rect in
        guard let rect, rect.width > 0, rect.height > 0, rect.width * rect.height <= area.width * area.height * 0.9 else { return nil }
        return GuideBox(number: number, rect: rect)
    }
}

/// A frame in Window Server coordinates as pixels of the window's screenshot (scale 1: window points).
func pixelRect(_ rect: CGRect, window: CGRect, scale: CGFloat) -> CGRect {
    CGRect(x: (rect.minX - window.minX) * scale, y: (rect.minY - window.minY) * scale,
           width: rect.width * scale, height: rect.height * scale)
}

/// The tree suffix for a frame: " @x,y w×h" with whole numbers.
func guideSuffix(_ rect: CGRect) -> String {
    " @\(Int(rect.minX.rounded())),\(Int(rect.minY.rounded())) \(Int(rect.width.rounded()))×\(Int(rect.height.rounded()))"
}

/// The picture with the guides on it. The boxes are in pixels of the picture, from its top left.
func drawGuides(on image: CGImage, boxes: [GuideBox]) -> CGImage {
    let width = CGFloat(image.width), height = CGFloat(image.height)
    guard let context = CGContext(data: nil, width: image.width, height: image.height, bitsPerComponent: 8, bytesPerRow: 0,
                                  space: CGColorSpaceCreateDeviceRGB(), bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue)
    else { return image }
    context.draw(image, in: CGRect(x: 0, y: 0, width: width, height: height))
    // From here y goes down, as in the picture. The text matrix flips the glyphs back.
    context.translateBy(x: 0, y: height)
    context.scaleBy(x: 1, y: -1)
    context.textMatrix = CGAffineTransform(scaleX: 1, y: -1)
    func fill(_ rect: CGRect, _ color: CGColor) {
        context.setFillColor(color)
        context.fill(rect)
    }
    func line(_ text: String, size: CGFloat) -> CTLine {
        CTLineCreateWithAttributedString(NSAttributedString(string: text, attributes: [
            kCTFontAttributeName as NSAttributedString.Key: CTFontCreateWithName("Helvetica" as CFString, size, nil),
            kCTForegroundColorAttributeName as NSAttributedString.Key: CGColor.white]))
    }
    func draw(_ line: CTLine, at point: CGPoint) {
        context.textPosition = point  // The left end of the baseline.
        CTLineDraw(line, context)
    }
    func textWidth(_ line: CTLine) -> CGFloat { CGFloat(CTLineGetTypographicBounds(line, nil, nil, nil)) }

    // Grid: a white and a black line side by side, so that it shows on light and on dark backgrounds.
    for x in stride(from: 100, to: Int(width), by: 100) {
        fill(CGRect(x: CGFloat(x), y: 0, width: 1, height: height), CGColor(gray: 1, alpha: 0.4))
        fill(CGRect(x: CGFloat(x + 1), y: 0, width: 1, height: height), CGColor(gray: 0, alpha: 0.4))
    }
    for y in stride(from: 100, to: Int(height), by: 100) {
        fill(CGRect(x: 0, y: CGFloat(y), width: width, height: 1), CGColor(gray: 1, alpha: 0.4))
        fill(CGRect(x: 0, y: CGFloat(y + 1), width: width, height: 1), CGColor(gray: 0, alpha: 0.4))
    }
    // Rulers: a band along the top and the left edge, a short tick every 50 px, a long tick and the number every 100 px.
    fill(CGRect(x: 0, y: 0, width: width, height: rulerWidth), CGColor(gray: 0, alpha: 0.6))
    fill(CGRect(x: 0, y: rulerWidth, width: rulerWidth, height: height - rulerWidth), CGColor(gray: 0, alpha: 0.6))
    for x in stride(from: 50, to: Int(width), by: 50) {
        let long = x % 100 == 0
        fill(CGRect(x: CGFloat(x), y: long ? 6 : 12, width: 1, height: rulerWidth - (long ? 6 : 12)), .white)
        if long { draw(line("\(x)", size: 10), at: CGPoint(x: CGFloat(x) + 3, y: 12)) }
    }
    for y in stride(from: 50, to: Int(height), by: 50) {
        let long = y % 100 == 0
        fill(CGRect(x: long ? 6 : 12, y: CGFloat(y), width: rulerWidth - (long ? 6 : 12), height: 1), .white)
        guard long else { continue }
        // The number reads from bottom to top, below the tick, inside the band.
        let label = line("\(y)", size: 10)
        context.saveGState()
        context.translateBy(x: 12, y: CGFloat(y) + 3 + textWidth(label))
        context.rotate(by: -.pi / 2)
        draw(label, at: .zero)
        context.restoreGState()
    }
    // Element boxes: a 1 px magenta border on whole pixels, and the number above the top left corner (inside
    // the box when the ruler is in the way).
    context.setStrokeColor(magenta)
    context.setLineWidth(1)
    for box in boxes {
        let rect = CGRect(x: box.rect.minX.rounded(), y: box.rect.minY.rounded(),
                          width: max(box.rect.width.rounded(), 1), height: max(box.rect.height.rounded(), 1))
        context.stroke(rect.insetBy(dx: 0.5, dy: 0.5))
        let label = line("\(box.number)", size: 9)
        let size = CGSize(width: textWidth(label) + 4, height: 11)
        let origin = CGPoint(x: max(rect.minX, rulerWidth),
                             y: rect.minY - size.height < rulerWidth ? rect.minY : rect.minY - size.height)
        fill(CGRect(origin: origin, size: size), magenta)
        draw(label, at: CGPoint(x: origin.x + 2, y: origin.y + 9))
    }
    return context.makeImage() ?? image
}
