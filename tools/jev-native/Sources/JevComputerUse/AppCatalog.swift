import AppKit
import Foundation

struct AppCandidate: Codable, Equatable {
    var bundle: String
    var name: String
    var aliases: [String]
    var category: String?
    var path: String
    var running: Bool

    var label: AppLabel { AppLabel(bundle: bundle, name: name, aliases: aliases, category: category, running: running) }
}

/// Only names/identities reach JEV. Local bundle paths stay in the local discovery artifact.
struct AppLabel: Codable, Equatable {
    var bundle: String
    var name: String
    var aliases: [String] = []
    var category: String? = nil
    var running: Bool = false
}

struct AppDiscovery: Codable {
    var apps: [AppCandidate]
    var roots: [String]
    var elapsedMS: Double
}

@MainActor enum AppCatalog {
    static func candidate(at url: URL, running: Bool) -> AppCandidate? {
        let url = url.standardizedFileURL.resolvingSymlinksInPath()
        guard url.pathExtension.lowercased() == "app", let bundle = Bundle(url: url),
              bundle.object(forInfoDictionaryKey: "CFBundlePackageType") as? String == "APPL",
              let id = bundle.bundleIdentifier, !id.isEmpty,
              id.rangeOfCharacter(from: .whitespacesAndNewlines) == nil,
              let executable = bundle.executableURL, FileManager.default.isExecutableFile(atPath: executable.path),
              !(bundle.object(forInfoDictionaryKey: "LSUIElement") as? Bool ?? false),
              !(bundle.object(forInfoDictionaryKey: "LSBackgroundOnly") as? Bool ?? false) else { return nil }
        let aliases = [bundle.localizedInfoDictionary?["CFBundleDisplayName"] as? String,
                       bundle.localizedInfoDictionary?["CFBundleName"] as? String,
                       bundle.infoDictionary?["CFBundleDisplayName"] as? String,
                       bundle.infoDictionary?["CFBundleName"] as? String,
                       url.deletingPathExtension().lastPathComponent].compactMap { $0 }.filter { !$0.isEmpty }
        let names = Array(Set(aliases)).sorted()
        return AppCandidate(bundle: id, name: aliases.first ?? id, aliases: names,
                            category: bundle.object(forInfoDictionaryKey: "LSApplicationCategoryType") as? String,
                            path: url.path, running: running)
    }

    static func normalized(_ apps: [AppCandidate], excludedBundle: String) -> [AppCandidate] {
        var unique: [String: AppCandidate] = [:]
        // Running installations win; otherwise path ordering breaks duplicate-install ties.
        for app in apps.sorted(by: { $0.running != $1.running ? $0.running : $0.path < $1.path }) where app.bundle != excludedBundle {
            if unique[app.bundle] == nil { unique[app.bundle] = app }
        }
        return unique.values.sorted { $0.bundle < $1.bundle }
    }

    static func discover() -> AppDiscovery {
        let start = Date()
        let roots = ["/Applications", "/System/Applications", "/System/Library/CoreServices", NSHomeDirectory() + "/Applications"]
        let running = NSWorkspace.shared.runningApplications.filter { $0.activationPolicy == .regular && !$0.isTerminated }
        let runningPaths = Set(running.compactMap { $0.bundleURL?.resolvingSymlinksInPath().path })
        var urls = running.compactMap(\.bundleURL)
        for root in roots {
            guard let enumerator = FileManager.default.enumerator(at: URL(fileURLWithPath: root), includingPropertiesForKeys: nil,
                options: [.skipsHiddenFiles, .skipsPackageDescendants], errorHandler: { _, _ in true }) else { continue }
            for case let url as URL in enumerator where url.pathExtension.lowercased() == "app" { urls.append(url) }
        }
        let candidates = urls.compactMap { candidate(at: $0, running: runningPaths.contains($0.resolvingSymlinksInPath().path)) }
        return AppDiscovery(apps: normalized(candidates, excludedBundle: Bundle.main.bundleIdentifier ?? "com.oozoofrog.JevComputerUse"), roots: roots, elapsedMS: milliseconds(start))
    }

    static func validate(_ selected: [String], in candidates: [AppCandidate]) throws {
        guard !selected.isEmpty, Set(selected).count == selected.count else { throw Failure("App selection must contain distinct discovered bundle IDs.") }
        for id in selected {
            guard let app = candidates.first(where: { $0.bundle == id }), let current = candidate(at: URL(fileURLWithPath: app.path), running: app.running), current.bundle == id else {
                throw Failure("Selected app is no longer installed. Re-run selection or pass --apps with an available bundle ID.")
            }
            let running = NSRunningApplication.runningApplications(withBundleIdentifier: id).contains { !$0.isTerminated }
            guard running || NSWorkspace.shared.urlForApplication(withBundleIdentifier: id).flatMap({ candidate(at: $0, running: false) })?.bundle == id else {
                throw Failure("Selected app \(id) is installed but cannot be resolved by LaunchServices. Open/register the app normally, or choose another app with --simple.")
            }
        }
    }
}
