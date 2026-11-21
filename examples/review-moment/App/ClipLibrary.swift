import Foundation

@MainActor
final class ClipLibrary {
    private let defaults: UserDefaults

    init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
    }

    var clips: [String] { defaults.stringArray(forKey: "clips") ?? [] }

    func save(_ text: String) -> Bool {
        let clip = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !clip.isEmpty, !clips.contains(clip) else { return false }
        defaults.set(clips + [clip], forKey: "clips")
        return true
    }

    func requestAfterSave(version: String, isReady: () -> Bool, request: () -> Void) async {
        do { try await Task.sleep(for: .seconds(2)) } catch { return }
        guard !Task.isCancelled, isReady() else { return }
        guard clips.count >= 3, defaults.string(forKey: "lastRequestVersion") != version else { return }
        defaults.set(version, forKey: "lastRequestVersion")
        request()
    }
}
