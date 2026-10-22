import Foundation
import ApplicationServices

// AXObserver is an optimization hint. Unsupported/missing events never establish freshness.
@MainActor final class AXInvalidation {
    private var observer: AXObserver?
    private(set) var hints: [(AXUIElement, String)] = []
    private(set) var registrations = 0
    private(set) var requestCalls = 0
    func start(pid: Int32, roots: [AXUIElement], values: [AXUIElement] = []) {
        stop()
        requestCalls += 1
        var created: AXObserver?
        let result = AXObserverCreate(pid, { _, element, notification, context in
            guard let context else { return }
            MainActor.assumeIsolated {
                let owner = Unmanaged<AXInvalidation>.fromOpaque(context).takeUnretainedValue()
                owner.hints.append((element, notification as String))
            }
        }, &created)
        guard result == .success, let created else { return }
        observer = created
        let context = Unmanaged.passUnretained(self).toOpaque()
        for root in roots {
            for name in [kAXFocusedUIElementChangedNotification,kAXWindowCreatedNotification,kAXUIElementDestroyedNotification,kAXValueChangedNotification,"AXChildrenChanged","AXLayoutChanged"] {
                requestCalls += 1
                if AXObserverAddNotification(created,root,name as CFString,context) == .success { registrations += 1 }
            }
        }
        for value in values { for name in [kAXValueChangedNotification,kAXUIElementDestroyedNotification] { requestCalls += 1; if AXObserverAddNotification(created,value,name as CFString,context) == .success { registrations += 1 } } }
        CFRunLoopAddSource(CFRunLoopGetMain(),AXObserverGetRunLoopSource(created),.commonModes)
    }
    func drain() -> [(AXUIElement, String)] { defer { hints=[] }; return hints }
    func stop() { if let observer { CFRunLoopRemoveSource(CFRunLoopGetMain(),AXObserverGetRunLoopSource(observer),.commonModes) }; observer=nil; hints=[]; registrations=0;requestCalls=0 }
    deinit { if let observer { CFRunLoopRemoveSource(CFRunLoopGetMain(),AXObserverGetRunLoopSource(observer),.commonModes) } }
}
