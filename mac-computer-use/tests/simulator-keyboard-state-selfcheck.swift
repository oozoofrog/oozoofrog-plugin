import Foundation

func shell(_ path: String, _ arguments: [String]) -> (status: Int32, output: String) {
    assert(arguments.contains("export"))
    let preferences: [String: Any] = arguments[2] == "korean" ?
        ["KeyboardsCurrentAndNext": ["ko_KR@sw=Korean;hw=Automatic", "en_US@hw=US"]] :
        ["KeyboardsCurrentAndNext": ["en_US@hw=US"], "KeyboardLastUsed": "ko_KR"]
    let data = try! PropertyListSerialization.data(fromPropertyList: preferences, format: .xml, options: 0)
    return (0, String(data: data, encoding: .utf8)!)
}

@main
struct SimulatorKeyboardStateSelfcheck {
    static func main() {
        assert(keyboardInputMode("korean").hasPrefix("ko"))
        assert(keyboardInputMode("english").hasPrefix("en"))
        assert(simulatorKeyboardInputMode(from: ["KeyboardLastUsed": "ko_KR"]) == "ko_KR")
        assert(simulatorKeyboardInputMode(from: ["KeyboardsCurrentAndNext": [""], "KeyboardLastUsed": "en_US"]) == "en_US")
        assert(simulatorKeyboardInputMode(from: [:]).isEmpty)
        assert(simulatorPasteSelectionIsValid(NSRange(location: 2, length: 2), value: "하이🙂"))
        assert(!simulatorPasteSelectionIsValid(NSRange(location: NSNotFound, length: 0), value: "하이"))
        assert(!simulatorPasteSelectionIsValid(NSRange(location: -1, length: 0), value: "하이"))
        assert(!simulatorPasteSelectionIsValid(NSRange(location: 0, length: -1), value: "하이"))
        assert(!simulatorPasteSelectionIsValid(NSRange(location: 2, length: 3), value: "하이🙂"))
        print("Keyboard state checks passed: current Korean layout without KeyboardLastUsed, stale last-used layouts, fallback and empty preferences.")
    }
}
