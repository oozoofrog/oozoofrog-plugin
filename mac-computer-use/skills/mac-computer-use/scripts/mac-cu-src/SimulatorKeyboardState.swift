import Foundation

func simulatorPasteSelectionIsValid(_ selection: NSRange, value: String) -> Bool {
    let length = value.utf16.count
    return selection.location >= 0 && selection.length >= 0 && selection.location <= length && selection.length <= length - selection.location
}

func simulatorKeyboardInputMode(from preferences: [String: Any]) -> String {
    if let current = (preferences["KeyboardsCurrentAndNext"] as? [String])?.first, !current.isEmpty { return current }
    return preferences["KeyboardLastUsed"] as? String ?? ""
}

/// KeyboardLastUsed may be absent even with an active Korean keyboard.
func keyboardInputMode(_ id: String) -> String {
    let result = shell("/usr/bin/xcrun", ["simctl", "spawn", id, "defaults", "export", "com.apple.keyboard.preferences", "-"])
    guard result.status == 0,
          let preferences = try? PropertyListSerialization.propertyList(from: Data(result.output.utf8), format: nil) as? [String: Any]
    else { return "" }
    return simulatorKeyboardInputMode(from: preferences)
}
