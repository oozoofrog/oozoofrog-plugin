import Foundation
import CoreGraphics
import Darwin

/// Optional Apple-private event annotation. It never posts to the global event stream.
/// The public CGEvent API does not expose a setter for target-window local coordinates.
final class WindowEvents {
    private typealias SetWindowLocation = @convention(c) (CGEvent, CGPoint) -> Void
    private let handle: UnsafeMutableRawPointer?
    private let setLocation: SetWindowLocation?
    let available: Bool
    init() {
        handle = ProcessInfo.processInfo.environment["JEV_DISABLE_PRIVATE_EVENTS"] == "1" ? nil : dlopen("/System/Library/PrivateFrameworks/SkyLight.framework/SkyLight", RTLD_LAZY | RTLD_LOCAL)
        if let handle, let symbol = dlsym(handle, "SLEventSetWindowLocation") { setLocation = unsafeBitCast(symbol, to: SetWindowLocation.self) } else { setLocation = nil }
        available = setLocation != nil
    }
    deinit { if let handle { dlclose(handle) } }
    func annotate(_ event: CGEvent, local: CGPoint, windowID: UInt32? = nil) {
        setLocation?(event, local)
        // AppKit's NSEvent.mouseEvent(windowNumber:) writes field 51. A bare public
        // scroll CGEvent omits it; annotation is necessary for background window routing.
        if let windowID, let field=CGEventField(rawValue:51) { event.setIntegerValueField(field,value:Int64(windowID)) }
    }
}
