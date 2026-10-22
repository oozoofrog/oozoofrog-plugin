import XCTest
@testable import JevComputerUse

final class AppSelectionTests: XCTestCase {
    func testRequestModesAndTaskOmission() throws {
        XCTAssertTrue(try RunRequest(arguments: ["--goal", "Calculate"]).spec.apps.isEmpty)
        XCTAssertFalse(try RunRequest(arguments: ["--goal", "Calculate", "--auto"]).allowInteractiveFallback)
        XCTAssertTrue(try RunRequest(arguments: ["--goal", "Calculate", "--simple"]).chooseApps)
        XCTAssertEqual(try RunRequest(arguments: ["--goal", "Calculate", "--apps", "a, b"]).spec.apps, ["a", "b"])
        for args in [["--auto", "--simple"], ["--auto", "--apps", "a"], ["--simple", "--apps", "a"], ["--apps", ""], ["--apps", "a,"], ["--apps"]] {
            XCTAssertThrowsError(try RunRequest(arguments: ["--goal", "Calculate"] + args))
        }
        XCTAssertTrue(try JSONDecoder().decode(TaskSpec.self, from: Data(#"{"goal":"Calculate"}"#.utf8)).apps.isEmpty)
        XCTAssertThrowsError(try JSONDecoder().decode(TaskSpec.self, from: Data(#"{"goal":"Calculate","apps":[]}"#.utf8)))
        let automatic = TaskSpec(goal:"Calculate")
        XCTAssertTrue(try JSONDecoder().decode(TaskSpec.self, from: jsonData(automatic)).apps.isEmpty)
        let explicit = TaskSpec(goal:"Calculate",apps:["test.a"])
        XCTAssertEqual(try JSONDecoder().decode(TaskSpec.self, from: jsonData(explicit)).apps,["test.a"])
    }

    @MainActor func testPickerParsing() throws {
        XCTAssertEqual(try AppResolver.parseSelection("3, 1,3", count: 3), [2, 0])
        XCTAssertNil(try AppResolver.parseSelection("cancel", count: 3))
        for text in ["", "0", "4", "1,", "1,foo"] { XCTAssertThrowsError(try AppResolver.parseSelection(text, count: 3)) }
    }

    @MainActor func testCandidateValidityAndDeduplication() throws {
        let dir = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: dir) }
        func bundle(_ name: String, flags: [String: Any] = [:]) throws -> URL {
            let app = dir.appendingPathComponent(name + ".app")
            try FileManager.default.createDirectory(at: app.appendingPathComponent("Contents/MacOS"), withIntermediateDirectories: true)
            var info: [String: Any] = ["CFBundleIdentifier":"test." + name,"CFBundleExecutable":"fixture","CFBundleName": name,"CFBundlePackageType":"APPL"]
            for (key,value) in flags { info[key] = value }
            try PropertyListSerialization.data(fromPropertyList: info, format: .xml, options: 0).write(to: app.appendingPathComponent("Contents/Info.plist"))
            let exe = app.appendingPathComponent("Contents/MacOS/fixture")
            try Data("#!/bin/sh\nexit 0\n".utf8).write(to: exe)
            try FileManager.default.setAttributes([.posixPermissions: 0o755], ofItemAtPath: exe.path)
            return app
        }
        let valid = try XCTUnwrap(AppCatalog.candidate(at: bundle("Valid"), running: false))
        XCTAssertEqual(valid.bundle,"test.Valid")
        XCTAssertNil(AppCatalog.candidate(at: try bundle("Helper",flags:["LSUIElement":true]), running:false))
        XCTAssertNil(AppCatalog.candidate(at: try bundle("Background",flags:["LSBackgroundOnly":true]), running:false))
        XCTAssertNil(AppCatalog.candidate(at: try bundle("Wrong",flags:["CFBundlePackageType":"BNDL"]), running:false))
        var running = valid; running.running = true; running.path = "/running"
        XCTAssertEqual(AppCatalog.normalized([valid,running],excludedBundle:"self"),[running])
        XCTAssertTrue(AppCatalog.normalized([valid],excludedBundle:valid.bundle).isEmpty)
    }

    @MainActor func testInferenceBoundariesAndProvenance() async throws {
        for scenario in ["single","multi","ambiguous","unavailable","low","bad","fit","service"] {
            let dir = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
            try FileManager.default.createDirectory(at:dir,withIntermediateDirectories:true)
            defer { try? FileManager.default.removeItem(at:dir) }
            let apps = (0..<2).map { AppCandidate(bundle:"test.\($0)",name:"App \($0)",aliases:[],path:"/fixture",running:false) }
            var calls = 0; var validations = 0
            let resolver = AppResolver(discover:{ AppDiscovery(apps:apps,roots:[],elapsedMS:1) }, validate:{ ids,_ in validations += 1; XCTAssertFalse(ids.isEmpty) }, evaluate:{ request in
                calls += 1
                if scenario == "service", calls == 2 { throw Failure("Synthetic service failure") }
                let answer: AppSelectionAnswer
                if request.questions["fits"] != nil {
                    answer = AppSelectionAnswer(type:"noul",noul:scenario == "fit" ? 0.2 : 0.99)
                    return (AppSelectionReply(model:"test",answers:["fits":answer],usage:[:]),2)
                }
                let next: String
                switch scenario {
                case "ambiguous","unavailable": next = scenario
                case "bad": next = "not_a_candidate"
                default: next = calls == 1 ? "app_0" : (scenario == "multi" && calls == 2 ? "app_1" : "finish")
                }
                answer = AppSelectionAnswer(type:"choice",choice:next,confidence:scenario == "low" ? 0.1 : 0.99)
                return (AppSelectionReply(model:"test",answers:["next":answer],usage:["tokens":1]),2)
            }, picker:AppPickerIO(interactive:false,read:{ XCTFail("Must not read"); return nil },write:{_ in}))
            let result = await resolver.resolve(spec:TaskSpec(goal:"fixture"),simple:false,allowFallback:false,directory:dir.path)
            let expected = ["single":"resolved","multi":"resolved","ambiguous":"ambiguous","unavailable":"unavailable","low":"uncertain","bad":"error","fit":"uncertain","service":"error"][scenario]!
            XCTAssertEqual(result.status,expected,scenario)
            XCTAssertEqual(validations, expected == "resolved" ? 1 : 0,scenario)
            XCTAssertFalse(result.calls.isEmpty,scenario)
            if expected == "resolved" { XCTAssertEqual(result.apps,scenario == "multi" ? ["test.0","test.1"] : ["test.0"]) }
            if scenario == "service" { XCTAssertEqual(result.calls.count,1) }
            XCTAssertEqual(try JSONDecoder().decode(AppResolution.self,from:jsonData(result)).source,"goal")
        }
    }

    @MainActor func testExplicitBypassAndInteractiveFallback() async throws {
        let apps = [AppCandidate(bundle:"test.a",name:"Alpha",aliases:[],path:"/fixture",running:false)]
        let dir = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at:dir,withIntermediateDirectories:true)
        defer { try? FileManager.default.removeItem(at:dir) }
        var discoveries = 0; var reads = 0; var calls = 0
        let resolver = AppResolver(discover:{ discoveries += 1; return AppDiscovery(apps:apps,roots:[],elapsedMS:1) },validate:{_,_ in},evaluate:{_ in calls += 1; return (AppSelectionReply(model:"test",answers:["next":AppSelectionAnswer(type:"choice",choice:"ambiguous",confidence:0.99)],usage:[:]),1) },picker:AppPickerIO(interactive:true,read:{ reads += 1; return "1" },write:{_ in}))
        let explicit = await resolver.resolve(spec:TaskSpec(goal:"fixture",apps:["pid:123"]),simple:false,allowFallback:true,directory:dir.path)
        XCTAssertEqual(explicit.apps,["pid:123"]); XCTAssertEqual(discoveries,0); XCTAssertEqual(calls,0)
        let fallback = await resolver.resolve(spec:TaskSpec(goal:"fixture"),simple:false,allowFallback:true,directory:dir.path)
        XCTAssertEqual(fallback.source,"interactive"); XCTAssertEqual(fallback.status,"resolved"); XCTAssertEqual(reads,1)
        let auto = await resolver.resolve(spec:TaskSpec(goal:"fixture"),simple:false,allowFallback:false,directory:dir.path)
        XCTAssertEqual(auto.status,"ambiguous"); XCTAssertEqual(reads,1)
        let simple = await resolver.resolve(spec:TaskSpec(goal:"fixture"),simple:true,allowFallback:true,directory:dir.path)
        XCTAssertEqual(simple.status,"resolved"); XCTAssertEqual(calls,2)
        resolver.picker.read = { nil }
        let cancelled = await resolver.resolve(spec:TaskSpec(goal:"fixture"),simple:true,allowFallback:true,directory:dir.path)
        XCTAssertEqual(cancelled.status,"cancelled")
        resolver.picker.interactive = false
        let noninteractive = await resolver.resolve(spec:TaskSpec(goal:"fixture"),simple:true,allowFallback:true,directory:dir.path)
        XCTAssertEqual(noninteractive.status,"requires_tty")
    }

    @MainActor func testLargeCatalogueDoesNotDropCandidates() async throws {
        let apps = (0..<601).map { AppCandidate(bundle:"test.\($0)",name:"App \($0)",aliases:[],path:"/fixture",running:false) }
        let dir = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at:dir,withIntermediateDirectories:true)
        defer { try? FileManager.default.removeItem(at:dir) }
        var covered = Set<String>()
        let resolver = AppResolver(discover:{AppDiscovery(apps:apps,roots:[],elapsedMS:1)},validate:{_,_ in},evaluate:{ request in
            var answers: [String:AppSelectionAnswer] = [:]
            for (key,question) in request.questions {
                XCTAssertLessThanOrEqual(question.criteria.count,255)
                if key.hasPrefix("group_") {
                    covered.formUnion(question.criteria.keys.filter{$0 != "none"})
                    answers[key] = AppSelectionAnswer(type:"choice",choice:question.criteria["app_600"] != nil && request.state.selected.isEmpty ? "app_600" : "none",confidence:0.99)
                } else if key == "next" {
                    answers[key] = AppSelectionAnswer(type:"choice",choice:request.state.selected.isEmpty ? "app_600" : "finish",confidence:0.99)
                } else { answers[key] = AppSelectionAnswer(type:"noul",noul:0.99) }
            }
            return (AppSelectionReply(model:"test",answers:answers,usage:[:]),1)
        },picker:AppPickerIO(interactive:false,read:{nil},write:{_ in}))
        let result = await resolver.resolve(spec:TaskSpec(goal:"App 600"),simple:false,allowFallback:false,directory:dir.path)
        XCTAssertEqual(result.apps,["test.600"]); XCTAssertEqual(covered.count,601)
        resolver.evaluate = { request in
            let answers = Dictionary(uniqueKeysWithValues: request.questions.keys.map { ($0, AppSelectionAnswer(type:"choice",choice:"none",confidence:0.1)) })
            return (AppSelectionReply(model:"test",answers:answers,usage:[:]),1)
        }
        let uncertain = await resolver.resolve(spec:TaskSpec(goal:"App 600"),simple:false,allowFallback:false,directory:dir.path)
        XCTAssertEqual(uncertain.status,"uncertain"); XCTAssertTrue(uncertain.apps.isEmpty)
    }
}
