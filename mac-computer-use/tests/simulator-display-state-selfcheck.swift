import Foundation

private let readLock = NSLock()
private var requestPaths: [String] = []

func shell(_ path: String, _ arguments: [String]) -> (status: Int32, output: String) {
    let file = URL(fileURLWithPath: arguments.last!)
    readLock.lock()
    requestPaths.append(file.path)
    readLock.unlock()
    try! Data("{\"result\":{\"displays\":[{\"displayId\":1}]}}".utf8).write(to: file)
    usleep(25_000)
    return (0, "")
}

@main
struct SimulatorDisplayStateSelfcheck {
    static func main() {
        var successes = 0
        DispatchQueue.concurrentPerform(iterations: 16) { _ in
            let result = displays(of: "same-device")
            readLock.lock()
            if result?.first?["displayId"] as? Int == 1 { successes += 1 }
            readLock.unlock()
        }
        guard successes == 16 else {
            fputs("Display state race: only \(successes)/16 simultaneous reads completed.\n", stderr)
            exit(1)
        }
        assert(Set(requestPaths).count == 16)
        assert(requestPaths.allSatisfy { !FileManager.default.fileExists(atPath: $0) })
        #if !DISPLAY_RACE_ONLY
        assert(!simulatorCommandNeedsActiveScreen("button"))
        assert(!simulatorCommandNeedsActiveScreen("crown"))
        for action in ["gesture", "rotate", "hinge", "tap", "describe"] { assert(simulatorCommandNeedsActiveScreen(action)) }
        var refresh = SimulatorDisplayRefresh()
        let first = refresh.begin()!
        assert(refresh.begin() == nil)
        refresh.changed()
        assert(!refresh.finish(first))
        let current = refresh.begin()!
        assert(refresh.finish(current))
        #endif
        print("Display state checks passed: concurrent reads have isolated files and cleanup; hardware controls and stale refreshes are independent of screen reads.")
    }
}
