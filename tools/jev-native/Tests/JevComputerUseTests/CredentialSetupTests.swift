import XCTest
import AppKit
@testable import JevComputerUse

final class CredentialSetupTests: XCTestCase {
    private func isolatedHome() throws -> URL {
        let home = FileManager.default.temporaryDirectory.appendingPathComponent("jev-key-test-" + UUID().uuidString)
        try FileManager.default.createDirectory(at: home, withIntermediateDirectories: true, attributes: [.posixPermissions: 0o700])
        addTeardownBlock { try FileManager.default.removeItem(at: home) }
        return home
    }
    @MainActor private func io(interactive: Bool = true, choices: [String] = [], clipboard: String? = nil) -> CredentialSetupIO {
        var choices = choices
        return CredentialSetupIO(interactive: interactive, readChoice: { choices.isEmpty ? nil : choices.removeFirst() }, readPasteboard: { clipboard }, openKeys: { true }, message: { _ in })
    }
    @MainActor func testCancelledAndEOFNeverReadPasteboard() throws {
        for choices in [["cancel"], []] {
            let home = try isolatedHome()
            var adapter = io(choices: choices)
            adapter.readPasteboard = { XCTFail("Must not read before agreement"); return nil }
            XCTAssertThrowsError(try setupCredential(environment: [:], home: home.path, io: adapter))
            XCTAssertFalse(FileManager.default.fileExists(atPath: home.appendingPathComponent(".typesafeai").path))
        }
    }
    @MainActor func testNoninteractiveMissingKeyNeverReadsInputOrPasteboardOrOpensURL() throws {
        let home = try isolatedHome()
        var adapter = io(interactive: false)
        adapter.readChoice = { XCTFail("Must not wait for stdin"); return nil }
        adapter.readPasteboard = { XCTFail("Must not read clipboard"); return nil }
        adapter.openKeys = { XCTFail("Must not open browser"); return false }
        XCTAssertThrowsError(try setupCredential(environment: [:], home: home.path, io: adapter)) { error in
            XCTAssertTrue(String(describing: error).contains("Noninteractive"))
        }
    }
    @MainActor func testExistingEnvironmentAndFilePrecedenceSkipAllSetup() throws {
        let home = try isolatedHome(), file = home.appendingPathComponent(".typesafeai")
        try "existing-file-token".write(to: file, atomically: true, encoding: .utf8)
        var adapter = io()
        adapter.readPasteboard = { XCTFail("Existing key must be preserved"); return nil }
        adapter.readChoice = { XCTFail("No prompt for existing key"); return nil }
        adapter.openKeys = { XCTFail("No implicit browser"); return false }
        for environment in [["TYPESAFE_API_KEY":"environment-token"], ["TYPESAFE_API_KEY":" \n"], [:]] {
            XCTAssertEqual(try setupCredential(environment: environment, home: home.path, importPasteboard: true, io: adapter), .alreadyConfigured)
        }
        XCTAssertEqual(try String(contentsOf: file, encoding: .utf8), "existing-file-token")
    }
    @MainActor func testImportFromPrivateNativePasteboardHas0600AndNoSecretMessages() throws {
        let home = try isolatedHome()
        let pasteboard = NSPasteboard.withUniqueName()
        defer { pasteboard.releaseGlobally() }
        let token = "synthetic_api_token_731"
        pasteboard.setString(" \n" + token + "\n", forType: .string)
        var messages: [String] = []
        var adapter = io(choices: ["import"])
        adapter.readPasteboard = { pasteboard.string(forType: .string) }
        adapter.message = { messages.append($0) }
        XCTAssertEqual(try setupCredential(environment: [:], home: home.path, io: adapter), .imported)
        let file = home.appendingPathComponent(".typesafeai")
        XCTAssertEqual(try credential(environment: [:], home: home.path), token)
        let attrs = try FileManager.default.attributesOfItem(atPath: file.path)
        XCTAssertEqual((attrs[.posixPermissions] as? NSNumber)?.intValue, 0o600)
        XCTAssertEqual((attrs[.ownerAccountID] as? NSNumber)?.intValue, Int(getuid()))
        XCTAssertFalse(messages.joined().contains(token))
        XCTAssertEqual(try FileManager.default.contentsOfDirectory(atPath: home.path), [".typesafeai"])
    }
    @MainActor func testEmptyMalformedClipboardIsRejectedWithoutEchoOrFiles() throws {
        let malformed: [String?] = [nil, " \n", "short", "export TYPESAFE_API_KEY=synthetic_token_731", "{\"key\":\"synthetic_token_731\"}", "token_line_one\ntoken_line_two", "https://console.typesafe.ai/keys", "synthetic_한글_token_731"]
        for contents in malformed {
            let home = try isolatedHome()
            XCTAssertThrowsError(try setupCredential(environment: [:], home: home.path, importPasteboard: true, io: io(interactive: false, clipboard: contents))) { error in
                if let contents, !contents.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                    XCTAssertFalse(String(describing: error).contains(contents))
                }
            }
            XCTAssertEqual(try FileManager.default.contentsOfDirectory(atPath: home.path), [])
        }
    }
    @MainActor func testExplicitImportWorksNoninteractivelyWithoutReadingStdin() throws {
        let home = try isolatedHome()
        var adapter = io(interactive: false, clipboard: "synthetic_noninteractive_token")
        adapter.readChoice = { XCTFail("Explicit import does not prompt"); return nil }
        XCTAssertEqual(try setupCredential(environment: [:], home: home.path, importPasteboard: true, io: adapter), .imported)
    }
    @MainActor func testOpeningRequiresChoiceAndDoesNotReadPasteboardBeforeImport() throws {
        let home = try isolatedHome()
        var opens = 0, reads = 0
        var adapter = io(choices: ["open", "cancel"])
        adapter.openKeys = { opens += 1; return true }
        adapter.readPasteboard = { reads += 1; return nil }
        XCTAssertThrowsError(try setupCredential(environment: [:], home: home.path, io: adapter))
        XCTAssertEqual(opens, 1); XCTAssertEqual(reads, 0)
        XCTAssertEqual(CredentialSetupIO.keysURL.absoluteString, "https://console.typesafe.ai/keys")
    }
    @MainActor func testCredentialAppearingDuringPromptSkipsPasteboard() throws {
        let home = try isolatedHome(), file = home.appendingPathComponent(".typesafeai")
        var adapter = io()
        adapter.readChoice = { try! "concurrent_existing_token".write(to: file, atomically: true, encoding: .utf8); return "import" }
        adapter.readPasteboard = { XCTFail("Recheck must precede clipboard read"); return nil }
        XCTAssertEqual(try setupCredential(environment: [:], home: home.path, io: adapter), .alreadyConfigured)
    }
    func testAtomicPublicationNeverReplacesExistingOrSymlinkAndCleansStaging() throws {
        let home = try isolatedHome(), file = home.appendingPathComponent(".typesafeai")
        try saveNewCredential("synthetic_original_token", home: home.path)
        XCTAssertThrowsError(try saveNewCredential("synthetic_replacement_token", home: home.path))
        XCTAssertEqual(try credential(environment: [:], home: home.path), "synthetic_original_token")
        try FileManager.default.removeItem(at: file)
        let target = home.appendingPathComponent("untouched")
        try "original".write(to: target, atomically: true, encoding: .utf8)
        try FileManager.default.createSymbolicLink(at: file, withDestinationURL: target)
        XCTAssertThrowsError(try saveNewCredential("synthetic_replacement_token", home: home.path))
        XCTAssertEqual(try String(contentsOf: target, encoding: .utf8), "original")
        XCTAssertFalse(try FileManager.default.contentsOfDirectory(atPath: home.path).contains { $0.hasPrefix(".typesafeai-setup-") })
    }
    @MainActor func testEmptyExistingFileIsPreservedRatherThanReplaced() throws {
        let home = try isolatedHome(), file = home.appendingPathComponent(".typesafeai")
        try Data().write(to: file)
        XCTAssertThrowsError(try setupCredential(environment: [:], home: home.path, importPasteboard: true, io: io(interactive: false, clipboard: "synthetic_new_token_731")))
        XCTAssertEqual(try Data(contentsOf: file).count, 0)
    }
}
