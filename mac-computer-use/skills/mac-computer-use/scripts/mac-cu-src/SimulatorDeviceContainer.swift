import AppKit

struct SimulatorDeviceAppearance {
    enum Family { case phone, tablet, watch, other }
    let family: Family
    let resources: URL?

    init(typeName: String, resources: URL? = nil) {
        family = typeName.contains("Watch") ? .watch : typeName.contains("iPad") ? .tablet : typeName.contains("iPhone") ? .phone : .other
        self.resources = resources
    }

    var bezel: CGFloat { family == .watch ? 20 : family == .tablet ? 17 : 12 }
    var fallbackCorner: CGFloat { family == .watch ? 45 : family == .phone ? 48 : 20 }

    func mask(for points: CGSize, rotation: String) -> SimulatorDeviceMask? {
        guard let resources else { return nil }
        let portrait = rotation == "rot90" || rotation == "rot270" ? CGSize(width: points.height, height: points.width) : points
        let files = (try? FileManager.default.contentsOfDirectory(at: resources, includingPropertiesForKeys: nil)) ?? []
        return files.filter { $0.pathExtension == "pdf" && !$0.lastPathComponent.hasPrefix("sensor_") }
            .compactMap(SimulatorDeviceMask.init).min { abs($0.aspect - portrait.width / portrait.height) < abs($1.aspect - portrait.width / portrait.height) }
    }
}

func simulatorDeviceAppearance(_ device: NSObject) -> SimulatorDeviceAppearance {
    let type = device.value(forKey: "deviceType") as? NSObject
    let name = type?.responds(to: NSSelectorFromString("name")) == true ? type?.value(forKey: "name") as? String ?? "" : ""
    let resources = URL(fileURLWithPath: "/Library/Developer/CoreSimulator/Profiles/DeviceTypes")
        .appendingPathComponent(name + ".simdevicetype/Contents/Resources")
    return SimulatorDeviceAppearance(typeName: name, resources: resources)
}

/// The simulator's own PDF mask supplies model-specific rounded corners and display cutouts.
final class SimulatorDeviceMask {
    let bitmap: NSBitmapImageRep
    let image: CGImage
    var aspect: CGFloat { CGFloat(bitmap.pixelsWide) / CGFloat(bitmap.pixelsHigh) }
    var cornerFraction: CGFloat {
        CGFloat((0..<bitmap.pixelsWide / 2).first { (bitmap.colorAt(x: $0, y: 0)?.alphaComponent ?? 0) > 0.5 } ?? 0) / CGFloat(bitmap.pixelsWide)
    }

    init?(_ url: URL) {
        guard let source = NSImage(contentsOf: url), let data = source.tiffRepresentation,
              let bitmap = NSBitmapImageRep(data: data), let image = bitmap.cgImage else { return nil }
        self.bitmap = bitmap
        self.image = image
    }

    func contains(_ point: CGPoint, size: CGSize, rotation: String) -> Bool {
        var u = point.x / size.width, v = point.y / size.height
        switch rotation {
        case "rot90": (u, v) = (v, 1 - u)
        case "rot180": (u, v) = (1 - u, 1 - v)
        case "rot270": (u, v) = (1 - v, u)
        default: break
        }
        let x = min(bitmap.pixelsWide - 1, max(0, Int(u * CGFloat(bitmap.pixelsWide))))
        let y = min(bitmap.pixelsHigh - 1, max(0, Int(v * CGFloat(bitmap.pixelsHigh))))
        return (bitmap.colorAt(x: x, y: y)?.alphaComponent ?? 0) > 0.1
    }
}

struct SimulatorDeviceLayout {
    let body: CGRect
    let lcd: CGRect
    let tools: CGRect
}

let simulatorToolboxWidth: CGFloat = 360
let simulatorToolboxHeight: CGFloat = 576
let simulatorToolboxMinimumSize = CGSize(width: 280, height: 344)
let simulatorToolboxGap: CGFloat = 28
let simulatorToolboxRim: CGFloat = 12

/// Sizes are Mac display points, never the guest framebuffer resolution.
func simulatorToolboxSize(forLCD lcd: CGSize, bezel: CGFloat) -> CGSize {
    let height = min(simulatorToolboxHeight, max(simulatorToolboxMinimumSize.height, lcd.height + 2 * bezel))
    return CGSize(width: max(simulatorToolboxMinimumSize.width, simulatorToolboxWidth * height / simulatorToolboxHeight), height: height)
}

func simulatorLCDContentSize(forLCD lcd: CGSize, bezel: CGFloat, toolsVisible: Bool) -> CGSize {
    let tools = simulatorToolboxSize(forLCD: lcd, bezel: bezel)
    return CGSize(width: lcd.width + 2 * bezel + 32 + (toolsVisible ? simulatorToolboxGap + tools.width : 0),
                  height: max(lcd.height + 2 * bezel, toolsVisible ? tools.height : 0) + 32)
}

func simulatorDeviceLayout(in size: CGSize, screen: CGSize, bezel: CGFloat, toolsVisible: Bool) -> SimulatorDeviceLayout {
    let aspect = max(1, screen.width) / max(1, screen.height)
    let availableWidth = max(1, size.width - 32 - 2 * bezel - (toolsVisible ? simulatorToolboxGap : 0))
    let toolLimit = max(0, availableWidth - 1)
    var widthLimitedHeight = availableWidth / aspect
    if toolsVisible {
        // Invert the same clamped proportional width used by simulatorToolboxSize, without iterative fitting drift.
        let minimumWidth = min(toolLimit, simulatorToolboxMinimumSize.width)
        let maximumWidth = min(toolLimit, simulatorToolboxWidth)
        let ratio = simulatorToolboxWidth / simulatorToolboxHeight
        widthLimitedHeight = (availableWidth - minimumWidth) / aspect
        if (widthLimitedHeight + 2 * bezel) * ratio > minimumWidth {
            widthLimitedHeight = (availableWidth - 2 * bezel * ratio) / (aspect + ratio)
            if (widthLimitedHeight + 2 * bezel) * ratio > maximumWidth {
                widthLimitedHeight = (availableWidth - maximumWidth) / aspect
            }
        }
    }
    let height = max(1, min(widthLimitedHeight, size.height - 32 - 2 * bezel))
    let lcdSize = CGSize(width: height * aspect, height: height)
    let preferred = simulatorToolboxSize(forLCD: lcdSize, bezel: bezel)
    let toolSize = CGSize(width: min(toolLimit, preferred.width), height: max(1, min(preferred.height, size.height - 32)))
    let occupiedWidth = lcdSize.width + 2 * bezel + (toolsVisible ? simulatorToolboxGap + toolSize.width : 0)
    let body = CGRect(x: (size.width - occupiedWidth) / 2, y: size.height - lcdSize.height - 2 * bezel - 16,
                      width: lcdSize.width + 2 * bezel, height: lcdSize.height + 2 * bezel)
    return SimulatorDeviceLayout(body: body, lcd: body.insetBy(dx: bezel, dy: bezel),
        tools: CGRect(x: body.maxX, y: size.height - 16 - toolSize.height,
                      width: simulatorToolboxGap + toolSize.width, height: toolSize.height))
}
