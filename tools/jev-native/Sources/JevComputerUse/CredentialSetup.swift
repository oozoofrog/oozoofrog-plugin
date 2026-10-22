import AppKit
import Darwin

enum CredentialSetupResult: String { case alreadyConfigured, imported }

/// All UI and pasteboard access is injected so tests never touch the general pasteboard.
@MainActor struct CredentialSetupIO {
    var interactive: Bool
    var readChoice: () -> String?
    var readPasteboard: () throws -> String?
    var openKeys: () -> Bool
    var message: (String) -> Void

    static let keysURL = URL(string: "https://console.typesafe.ai/keys")!
    static func native() -> Self {
        Self(interactive: isatty(STDIN_FILENO) == 1 && isatty(STDERR_FILENO) == 1,
             readChoice: { readLine() },
             readPasteboard: { try GUIContext.current().requireAvailable(); return NSPasteboard.general.string(forType: .string) },
             openKeys: { guard (try? GUIContext.current().requireAvailable()) != nil else { return false }; return NSWorkspace.shared.open(keysURL) },
             message: { fputs($0 + "\n", stderr) })
    }
}

func importedCredential(_ contents: String?) throws -> String {
    guard let contents, !contents.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
        throw Failure("Pasteboard has no text. Copy only the TypeSafe API key, then retry setup.")
    }
    let token = contents.trimmingCharacters(in: .whitespacesAndNewlines)
    // A conservative opaque Bearer-token shape, not an undocumented TypeSafe prefix contract.
    guard (16...4096).contains(token.utf8.count),
          token.range(of: #"^[A-Za-z0-9._~+/\-]+=*$"#, options: .regularExpression) != nil else {
        throw Failure("Pasteboard text is not a single API token. Copy only the key, without quotes, commands or JSON.")
    }
    return token
}

/// Publish a fully written 0600 file atomically. linkat never replaces an existing entry,
/// including a symlink or a credential another process wrote while setup was running.
func saveNewCredential(_ token: String, home: String) throws {
    let directory = open(home, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
    guard directory >= 0 else { throw Failure("Cannot open credential home directory safely.") }
    defer { close(directory) }
    let temporary = ".typesafeai-setup-" + UUID().uuidString
    let fd = openat(directory, temporary, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, mode_t(0o600))
    guard fd >= 0 else { throw Failure("Cannot create private credential staging file.") }
    defer { close(fd); unlinkat(directory, temporary, 0) }
    guard fchmod(fd, mode_t(0o600)) == 0 else { throw Failure("Cannot restrict credential file permissions.") }
    let data = Data((token + "\n").utf8)
    try data.withUnsafeBytes { bytes in
        var offset = 0
        while offset < bytes.count {
            let count = Darwin.write(fd, bytes.baseAddress!.advanced(by: offset), bytes.count-offset)
            if count < 0 && errno == EINTR { continue }
            guard count > 0 else { throw Failure("Cannot write credential file.") }
            offset += count
        }
    }
    guard fsync(fd) == 0 else { throw Failure("Cannot sync credential file; nothing was installed.") }
    guard linkat(directory, temporary, directory, ".typesafeai", 0) == 0 else {
        if errno == EEXIST { throw Failure("~/.typesafeai already exists; setup did not replace it. Resolve an empty or unreadable file manually, then retry.") }
        throw Failure("Cannot atomically install credential file; nothing was replaced.")
    }
    _ = fsync(directory)
}

@MainActor func setupCredential(
    environment: [String:String] = ProcessInfo.processInfo.environment,
    home: String = NSHomeDirectory(),
    importPasteboard: Bool = false,
    io providedIO: CredentialSetupIO? = nil
) throws -> CredentialSetupResult {
    let io = providedIO ?? .native()
    if (try? credential(environment: environment, home: home)) != nil {
        io.message("TypeSafe credential is already configured; no pasteboard was read and no file was changed.")
        return .alreadyConfigured
    }
    if !importPasteboard {
        guard io.interactive else {
            throw Failure("TypeSafe API key missing. In a terminal run 'jev-native setup', or copy the key and explicitly run 'jev-native setup --import-pasteboard'. To open key management: 'jev-native setup --open-keys'. Noninteractive input will not be read.")
        }
        io.message("TypeSafe API key missing. Copy only your API key to the macOS pasteboard. Type 'import' to read it and save ~/.typesafeai (0600), 'open' to open key management, or 'cancel'. Do not paste the key into this terminal.")
        while true {
            guard let choice = io.readChoice()?.trimmingCharacters(in: .whitespacesAndNewlines).lowercased() else {
                throw Failure("TypeSafe setup cancelled (end of input).")
            }
            if choice == "import" { break }
            if choice == "cancel" || choice == "q" { throw Failure("TypeSafe setup cancelled.") }
            if choice == "open" {
                guard io.openKeys() else { throw Failure("Could not open TypeSafe key management. Visit https://console.typesafe.ai/keys .") }
                io.message("Key management opened. Copy only the API key, then type 'import', or 'cancel'.")
            } else { io.message("Type 'import', 'open', or 'cancel'. Do not enter the key here.") }
        }
    }
    // Recheck after the user's wait. Do not read the pasteboard if another setup finished.
    if (try? credential(environment: environment, home: home)) != nil {
        io.message("A TypeSafe credential is now configured; nothing was imported.")
        return .alreadyConfigured
    }
    let token = try importedCredential(io.readPasteboard())
    try saveNewCredential(token, home: home)
    io.message("TypeSafe key saved to ~/.typesafeai with mode 0600. The key was not displayed. API validity has not been checked.")
    return .imported
}
