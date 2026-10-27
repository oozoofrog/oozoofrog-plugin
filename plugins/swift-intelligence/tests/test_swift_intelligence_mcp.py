import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).parents[1] / "scripts" / "swift_intelligence_mcp.py"
SPEC = importlib.util.spec_from_file_location("swift_intelligence_mcp", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RecoveringSession(MODULE.SourceKitSession):
    def __init__(self, error):
        super().__init__("/")
        self.error = error
        self.request_count = 0
        self.restart_count = 0

    def prepare_document(self, file_path, refresh=False):
        return Path(file_path).as_uri()

    def request(self, method, params, timeout=60):
        self.request_count += 1
        if self.request_count == 1:
            raise self.error
        return {"method": method, "params": params}

    def restart(self):
        self.restart_count += 1


class PullDiagnosticsSession(MODULE.SourceKitSession):
    def __init__(self):
        super().__init__("/")
        self.server_capabilities = {"diagnosticProvider": {}}

    def prepare_document(self, file_path, refresh=False):
        return Path(file_path).as_uri()

    def request_document(self, method, file_path, params=None, until_nonempty=False):
        self.method = method
        return {"kind": "full", "items": [{"message": "test diagnostic"}]}


class PrepareDocumentSession(MODULE.SourceKitSession):
    def __init__(self, workspace):
        super().__init__(workspace)
        self.notifications = []

    def start(self):
        return None

    def notify(self, method, params):
        self.notifications.append((method, params))


class SourceKitSessionTests(unittest.TestCase):
    def test_document_request_restarts_once_for_missing_language_service(self):
        error = MODULE.SourceKitRPCError(
            "textDocument/hover",
            -32001,
            "No language service found",
        )
        session = RecoveringSession(error)

        result = session.request_document(
            "textDocument/hover",
            "/tmp/Test.swift",
            {"position": {"line": 0, "character": 0}},
        )

        self.assertEqual(session.restart_count, 1)
        self.assertEqual(session.request_count, 2)
        self.assertEqual(
            result["params"]["textDocument"]["uri"],
            "file:///tmp/Test.swift",
        )

    def test_document_request_does_not_restart_for_other_rpc_errors(self):
        session = RecoveringSession(
            MODULE.SourceKitRPCError("textDocument/hover", -32601, "Method not found")
        )

        with self.assertRaises(MODULE.SourceKitRPCError):
            session.request_document("textDocument/hover", "/tmp/Test.swift")

        self.assertEqual(session.restart_count, 0)
        self.assertEqual(session.request_count, 1)

    def test_diagnostics_prefers_pull_when_advertised(self):
        session = PullDiagnosticsSession()

        result = session.diagnostics_for_document("/tmp/Test.swift")

        self.assertEqual(result, [{"message": "test diagnostic"}])
        self.assertEqual(session.method, "textDocument/diagnostic")

    def test_prepare_document_only_changes_when_contents_change(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "Test.swift"
            path.write_text("let value = 1\n", encoding="utf-8")
            session = PrepareDocumentSession(directory)

            session.prepare_document(path, refresh=True)
            session.prepare_document(path, refresh=True)
            path.write_text("let value = 2\n", encoding="utf-8")
            session.prepare_document(path, refresh=True)

        self.assertEqual(
            [method for method, _ in session.notifications],
            ["textDocument/didOpen", "textDocument/didChange"],
        )

    def test_diagnostics_rejects_stale_document_version(self):
        self.assertFalse(MODULE.SourceKitSession._diagnostics_version_matches(
            {"version": 1, "items": []},
            2,
        ))
        self.assertTrue(MODULE.SourceKitSession._diagnostics_version_matches(
            {"version": 2, "items": []},
            2,
        ))


class XcodeProjectTests(unittest.TestCase):
    def test_infers_index_store_from_build_argument(self):
        with tempfile.TemporaryDirectory() as directory:
            derived_data = Path(directory)
            build_product = derived_data / "Build" / "Products" / "Debug"
            index_store = derived_data / "Index.noindex" / "DataStore"
            build_product.mkdir(parents=True)
            (index_store / "v5").mkdir(parents=True)

            result = MODULE.XcodeProject._index_store_from_arguments([
                "-F" + str(build_product),
            ])

        self.assertEqual(result, index_store)

    def test_guesses_unselected_scheme_from_source_path(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = (Path(directory) / "workspace").resolve()
            workspace.mkdir()
            project = MODULE.XcodeProject(
                workspace,
                workspace / "Talk.xcworkspace",
                "TalkSound",
            )
            project._schemes = ["TalkSound", "TalkMarkdown"]
            source = workspace / "Projects" / "TalkMarkdown" / "Sources" / "Text.swift"

            scheme = project.guess_scheme(source)
            project.extra_schemes.append(scheme)

        self.assertEqual(scheme, "TalkMarkdown")
        self.assertEqual(project.selected_schemes(), ["TalkSound", "TalkMarkdown"])

    def test_retargets_configuration_to_built_simulator(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            products = root / "Build" / "Products"
            configuration = "Inhouse(iTeam)-Debug"
            (products / f"{configuration}-iphonesimulator").mkdir(parents=True)
            values = {
                "swiftASTCommandArguments": [
                    str(products / "Debug-iphoneos" / "TalkSound.framework"),
                    "-target", "arm64-apple-ios18.0", "-sdk", "/Xcode/iPhoneOS.sdk"
                ],
                "outputFilePath": str(
                    root / "Build" / "TalkSound.build" / "Debug-iphoneos" / "Sound.o"
                ),
            }
            settings = {"TalkSound": {"/tmp/Sound.swift": values}}
            project = MODULE.XcodeProject(root, root / "Talk.xcworkspace", "TalkSound")
            project._scheme_configuration = lambda _: configuration

            result = MODULE.subprocess.CompletedProcess([], 0, "/Xcode/iPhoneSimulator.sdk\n", "")
            with patch.object(MODULE.subprocess, "run", return_value=result):
                project._retarget_configuration(settings, "TalkSound")

        self.assertIn(
            f"{configuration}-iphonesimulator",
            values["swiftASTCommandArguments"][0],
        )
        self.assertIn(f"{configuration}-iphonesimulator", values["outputFilePath"])

    def test_index_cache_tracks_configuration_dependencies_and_refresh(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            container = root / "App.xcodeproj"
            container.mkdir()
            (container / "project.pbxproj").write_text("project")
            dependencies = [root / "Config.xcconfig", root / "App.xcscheme",
                            root / "contents.xcworkspacedata", root / "Workspace.xcsettings"]
            for dependency in dependencies:
                dependency.write_text("OLD")
            generation = [0]

            def xcode(*arguments):
                generation[0] += 1
                return {"App": {"/A.swift": {"swiftASTCommandArguments":
                    ["-D", f"GEN_{generation[0]}"]}}}

            def load():
                project = MODULE.XcodeProject(root, container, "App")
                project._scheme_configuration = lambda _: None
                project._xcode_json = xcode  # External Xcode unavailable on Linux.
                return project._index_settings("App")["App"]["/A.swift"]["swiftASTCommandArguments"]

            with patch.object(MODULE, "INDEX_SETTINGS_CACHE", root / "cache"):
                self.assertEqual(load(), ["-D", "GEN_1"])
                self.assertEqual(load(), ["-D", "GEN_1"])
                for index, dependency in enumerate(dependencies, 2):
                    dependency.write_text("NEW")
                    self.assertEqual(load(), ["-D", f"GEN_{index}"])
                dependencies[0].unlink()
                self.assertEqual(load(), ["-D", "GEN_6"])
                for cache in (root / "cache").glob("*.json.gz"):
                    cache.write_bytes(b"broken gzip")
                with patch.dict(MODULE.os.environ, {"SWIFT_INTELLIGENCE_REFRESH_INDEX_SETTINGS": "1"}):
                    self.assertEqual(load(), ["-D", "GEN_7"])

    def test_simulator_retarget_updates_target_and_sdk_together(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            products = root / "Build/Products"
            (products / "Debug-iphonesimulator").mkdir(parents=True)
            values = {"swiftASTCommandArguments": [
                "-target", "arm64-apple-ios18.0", "-sdk", "/Xcode/iPhoneOS.sdk",
                "-F", str(products / "Debug-iphoneos")], "outputFilePath": "A.o"}
            project = MODULE.XcodeProject(root, root / "App.xcodeproj", "App")
            project._scheme_configuration = lambda _: "Debug"
            result = MODULE.subprocess.CompletedProcess([], 0, "/Xcode/iPhoneSimulator.sdk\n", "")
            with patch.object(MODULE.subprocess, "run", return_value=result):
                project._retarget_configuration({"App": {"/A.swift": values}}, "App")
            self.assertEqual(values["swiftASTCommandArguments"], [
                "-target", "arm64-apple-ios18.0-simulator", "-sdk", "/Xcode/iPhoneSimulator.sdk",
                "-F", str(products / "Debug-iphonesimulator")])

    def test_simulator_retarget_rewrites_sdk_relative_search_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            products = root / "Build/Products"
            (products / "Debug-iphonesimulator").mkdir(parents=True)
            values = {"swiftASTCommandArguments": [
                "-target", "arm64-apple-ios18.0", "-sdk", "/Xcode/iPhoneOS.platform/Developer/SDKs/iPhoneOS.sdk",
                "-I/Xcode/iPhoneOS.platform/Developer/SDKs/iPhoneOS.sdk/usr/include", "-I/toolchain/usr/lib/swift/iphoneos",
                "-F/Xcode/iPhoneOS.platform/Developer/Library/Frameworks",
                "-F", str(products / "Debug-iphoneos")]}
            project = MODULE.XcodeProject(root, root / "App.xcodeproj", "App")
            project._scheme_configuration = lambda _: "Debug"
            result = MODULE.subprocess.CompletedProcess([], 0, "/Xcode/iPhoneSimulator.platform/Developer/SDKs/iPhoneSimulator.sdk\n", "")
            with patch.object(MODULE.subprocess, "run", return_value=result):
                project._retarget_configuration({"App": {"/A.swift": values}}, "App")
            self.assertIn("-I/Xcode/iPhoneSimulator.platform/Developer/SDKs/iPhoneSimulator.sdk/usr/include", values["swiftASTCommandArguments"])
            self.assertIn("-I/toolchain/usr/lib/swift/iphonesimulator", values["swiftASTCommandArguments"])

            self.assertIn("-F/Xcode/iPhoneSimulator.platform/Developer/Library/Frameworks",
                          values["swiftASTCommandArguments"])

    def test_tvOS_is_not_redirected_to_existing_ios_simulator_products(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            products = root / "Build/Products"
            (products / "Debug-iphonesimulator").mkdir(parents=True)
            values = {"swiftASTCommandArguments": ["-target", "arm64-apple-tvos18.0",
                "-sdk", "/Xcode/AppleTVOS.sdk", "-F", str(products / "Debug-appletvos")]}
            project = MODULE.XcodeProject(root, root / "App.xcodeproj", "App")
            project._scheme_configuration = lambda _: "Debug"
            project._retarget_configuration({"App": {"/A.swift": values}}, "App")
            self.assertEqual(values["swiftASTCommandArguments"][-1], str(products / "Debug-appletvos"))

    def test_attached_framework_flag_selects_built_simulator(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "Build/Products/Debug-iphonesimulator").mkdir(parents=True)
            values = {"swiftASTCommandArguments": ["-F" + str(root / "Build/Products/Debug-iphoneos"),
                "-target", "arm64-apple-ios18.0", "-sdk", "/Xcode/iPhoneOS.sdk"]}
            project = MODULE.XcodeProject(root, root / "App.xcodeproj", "App")
            project._scheme_configuration = lambda _: "Debug"
            result = MODULE.subprocess.CompletedProcess([], 0, "/Xcode/iPhoneSimulator.sdk\n", "")
            with patch.object(MODULE.subprocess, "run", return_value=result):
                project._retarget_configuration({"App": {"/A.swift": values}}, "App")
            self.assertEqual(values["swiftASTCommandArguments"][0],
                             "-F" + str(root / "Build/Products/Debug-iphonesimulator"))

    def test_simulator_retarget_rejects_unsupported_architecture(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "Build/Products/Debug-iphonesimulator").mkdir(parents=True)
            values = {"swiftASTCommandArguments": ["-target", "armv7-apple-ios10.0",
                "-sdk", "/Xcode/iPhoneOS.sdk", "-F", str(root / "Build/Products/Debug-iphoneos")]}
            original = list(values["swiftASTCommandArguments"])
            project = MODULE.XcodeProject(root, root / "App.xcodeproj", "App")
            project._scheme_configuration = lambda _: "Debug"
            with self.assertRaisesRegex(MODULE.SourceKitError, "Cannot safely retarget"):
                project._retarget_configuration({"App": {"/A.swift": values}}, "App")
            self.assertEqual(values["swiftASTCommandArguments"], original)

    def test_simulator_retarget_fails_cleanly_without_xcrun(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "Build/Products/Debug-iphonesimulator").mkdir(parents=True)
            values = {"swiftASTCommandArguments": ["-target", "arm64-apple-ios18.0",
                "-sdk", "/Xcode/iPhoneOS.sdk", "-F", str(root / "Build/Products/Debug-iphoneos")]}
            project = MODULE.XcodeProject(root, root / "App.xcodeproj", "App")
            project._scheme_configuration = lambda _: "Debug"
            with patch.object(MODULE.subprocess, "run", side_effect=FileNotFoundError("xcrun")):
                with self.assertRaisesRegex(MODULE.SourceKitError, "Simulator SDK"):
                    project._retarget_configuration({"App": {"/A.swift": values}}, "App")

    def test_simulator_retarget_rejects_missing_or_incomplete_compiler_environment(self):
        for flags in ([], ["-sdk", "/Xcode/iPhoneOS.sdk"], ["-target"],
                      ["-target", "-sdk", "/Xcode/iPhoneOS.sdk"],
                      ["-target", "arm64-apple-ios18.0"],
                      ["-target", "arm64-apple-ios18.0", "-sdk"]):
            with self.subTest(flags=flags), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / "Build/Products/Debug-iphonesimulator").mkdir(parents=True)
                values = {"swiftASTCommandArguments": ["-F", str(root / "Build/Products/Debug-iphoneos"), *flags]}
                project = MODULE.XcodeProject(root, root / "App.xcodeproj", "App")
                project._scheme_configuration = lambda _: "Debug"
                with self.assertRaises(MODULE.SourceKitError):
                    project._retarget_configuration({"App": {"/A.swift": values}}, "App")

    def test_macos_release_override_retargets_unsuffixed_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            values = {"swiftASTCommandArguments": [
                "-F" + str(root / "Build/Products/Debug"),
                str(root / "My-App.build/Debug/Objects-normal/arm64/A.o")],
                "outputFilePath": str(root / "My-App.build/Debug/A.o")}
            project = MODULE.XcodeProject(root, root / "App.xcodeproj", "App")
            project._scheme_configuration = lambda _: "Debug"
            with patch.dict(MODULE.os.environ, {MODULE.CONFIGURATION_ENV: "Release"}):
                project._retarget_configuration({"App": {"/A.swift": values}}, "App")
            self.assertEqual(values["swiftASTCommandArguments"], [
                "-F" + str(root / "Build/Products/Release"),
                str(root / "My-App.build/Release/Objects-normal/arm64/A.o")])
            self.assertEqual(values["outputFilePath"], str(root / "My-App.build/Release/A.o"))

    def test_macos_retarget_preserves_nested_build_object_directories(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = root / "Build/Intermediates.noindex/Foo.build/Debug/Foo.build/Objects-normal/arm64/Foo.o"
            expected = root / "Build/Intermediates.noindex/Foo.build/Release/Foo.build/Objects-normal/arm64/Foo.o"
            values = {"swiftASTCommandArguments": [str(original)], "outputFilePath": str(original)}
            project = MODULE.XcodeProject(root, root / "App.xcodeproj", "App")
            with patch.dict(MODULE.os.environ, {MODULE.CONFIGURATION_ENV: "Release"}):
                project._retarget_configuration({"App": {"/A.swift": values}}, "App")
            self.assertEqual(values["swiftASTCommandArguments"], [str(expected)])
            self.assertEqual(values["outputFilePath"], str(expected))

    def test_shared_index_database_falls_back_when_locked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            first = MODULE.XcodeProject(root, root / "Talk.xcworkspace")
            second = MODULE.XcodeProject(root, root / "Talk.xcworkspace")
            with patch.object(MODULE, "INDEX_SETTINGS_CACHE", root / "cache"):
                shared = first._index_database(root / "lsp-one", root / "IndexStore")
                fallback = second._index_database(root / "lsp-two", root / "IndexStore")
            first.release_index_lock()
            second.release_index_lock()

        self.assertEqual(shared.parent, root / "cache")
        self.assertEqual(fallback, root / "lsp-two" / "IndexDatabase")


class WorkspaceSymbolTests(unittest.TestCase):
    def test_exact_symbols_are_ranked_first_and_duplicates_are_removed(self):
        symbols = [
            {
                "name": "UnrelatedSoundSourceBuilder",
                "kind": 5,
                "location": {
                    "uri": "file:///tmp/Other.swift",
                    "range": {"start": {"line": 2, "character": 0}},
                },
            },
            {
                "name": "SoundSource",
                "kind": 11,
                "location": {
                    "uri": "file:///tmp/SoundSource.swift",
                    "range": {"start": {"line": 0, "character": 0}},
                },
            },
            {
                "name": "SoundSource",
                "kind": 11,
                "location": {
                    "uri": "file:///tmp/SoundSource.swift",
                    "range": {"start": {"line": 0, "character": 0}},
                },
            },
        ]

        result = MODULE.rank_workspace_symbols(symbols, "SoundSource")

        self.assertEqual([symbol["name"] for symbol in result], [
            "SoundSource",
            "UnrelatedSoundSourceBuilder",
        ])


if __name__ == "__main__":
    unittest.main()
