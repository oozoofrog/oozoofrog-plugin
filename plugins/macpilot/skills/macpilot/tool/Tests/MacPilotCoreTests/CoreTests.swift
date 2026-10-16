import XCTest
import CryptoKit
@testable import MacPilotCore

final class CoreTests: XCTestCase {
    func observation() -> Observation {
        Observation(id:UUID().uuidString.lowercased(),created:Date(),pid:42,processStartID:"1.1",launchTime:1,bundleID:"test",windowID:7,
            windowFrame:Rect(CGRect(x:-800,y:120,width:600,height:400)),windowTitle:"fixture",axWindowIndex:0,nodes:[],coverage:"partial",diagnostics:[],
            pixelWidth:1200,pixelHeight:800)
    }
    func testCoordinateSpacesOnNegativeDisplay() throws {
        let o=observation()
        for (x,y,space) in [(300.0,200.0,"window"),(0.5,0.5,"normalized"),(600.0,400.0,"image"),(-500.0,320.0,"screen")] {
            XCTAssertEqual(try Geometry.point(x:x,y:y,space:space,observation:o),CGPoint(x:-500,y:320))
        }
    }
    func testRejectsOutsideAndNonfiniteCoordinates() {
        let o=observation()
        for (x,y,space) in [(600.0,0.0,"window"),(-1.0,0.0,"window"),(1.0,0.5,"normalized"),(Double.nan,0.0,"screen"),(Double.infinity,0.0,"image")] {
            XCTAssertThrowsError(try Geometry.point(x:x,y:y,space:space,observation:o))
        }
    }
    func testImageCoordinatesRequireScreenshotGeometry() {
        var o=observation(); o.pixelWidth=nil
        XCTAssertThrowsError(try Geometry.point(x:1,y:1,space:"image",observation:o))
    }
    func testTokenExpiryAndOneUse() throws {
        var o=observation(); try Geometry.validateAge(o)
        o.created=Date().addingTimeInterval(-31); XCTAssertThrowsError(try Geometry.validateAge(o))
        o.created=Date().addingTimeInterval(10); XCTAssertThrowsError(try Geometry.validateAge(o))
        o.created=Date(); o.consumed=true; XCTAssertThrowsError(try Geometry.validateAge(o))
    }
    func testRejectsBoolAsIntegerAndFractionAsInteger() {
        XCTAssertThrowsError(try Arguments(["pid":true]).integer("pid"))
        XCTAssertThrowsError(try Arguments(["pid":1.5]).integer("pid"))
        XCTAssertThrowsError(try Arguments(["pid":-1]).integer("pid"))
        XCTAssertThrowsError(try Arguments(["ok":1]).bool("ok"))
    }
    func testUnknownArgumentsAndTypesFailClosed() {
        XCTAssertThrowsError(try Arguments(["pdi":1]).only(["pid"]))
        XCTAssertThrowsError(try Arguments(["text":12]).string("text"))
        XCTAssertThrowsError(try Arguments(["modifiers":"command"]).strings("modifiers"))
    }
    func testUnicodePreservesKoreanEmojiAndCombiningText() {
        let text="한글 😀👩🏽‍💻 e\u{301}" + String(repeating:"🚀",count:30)
        let chunks=Geometry.unicodeChunks(text)
        XCTAssertTrue(chunks.allSatisfy { $0.count <= 20 })
        XCTAssertEqual(chunks.map { String(decoding:$0,as:UTF16.self) }.joined(),text)
        XCTAssertEqual(Geometry.unicodeChunks(""),[])
    }
    func testPrivateStoreAndTokenTraversal() throws {
        let dir=FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { if FileManager.default.fileExists(atPath:dir.path) { try? FileManager.default.removeItem(at:dir) } }
        let store=try Store(root:dir), o=observation()
        try store.save(o); XCTAssertEqual(try store.load(o.id).id,o.id)
        XCTAssertThrowsError(try store.tokenURL("../../secret"))
        try store.consume(o); XCTAssertTrue(try store.load(o.id).consumed)
        let mode=(try FileManager.default.attributesOfItem(atPath:dir.path)[.posixPermissions] as? NSNumber)?.intValue
        XCTAssertEqual(mode,0o700)
        let fileMode=(try FileManager.default.attributesOfItem(atPath:store.tokenURL(o.id).path)[.posixPermissions] as? NSNumber)?.intValue
        XCTAssertEqual(fileMode,0o600)
    }
    @MainActor func testStoreLoadsOnlyBoundedHashMatchedObservationPNG() throws {
        let dir=FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { if FileManager.default.fileExists(atPath:dir.path) { try? FileManager.default.removeItem(at:dir) } }
        let store=try Store(root:dir)
        guard let context=CGContext(data:nil,width:2,height:2,bitsPerComponent:8,bytesPerRow:0,
                                    space:CGColorSpaceCreateDeviceRGB(),bitmapInfo:CGImageAlphaInfo.premultipliedLast.rawValue),
              let source=context.makeImage() else {
            return XCTFail("Cannot create fixture image")
        }
        let data=try Capture.png(source)
        var o=observation()
        let url=store.root.appendingPathComponent(o.id+".png")
        o.screenshot=url.path
        o.pixelWidth=2; o.pixelHeight=2
        o.screenshotSHA256=SHA256.hash(data:data).map { String(format:"%02x",$0) }.joined()
        try store.write(data,to:url)
        let decoded=try store.image(for:o)
        XCTAssertEqual(decoded.width,2); XCTAssertEqual(decoded.height,2)

        var wrongDimensions=o; wrongDimensions.pixelWidth=3
        XCTAssertThrowsError(try store.image(for:wrongDimensions)) { error in
            XCTAssertEqual((error as? ToolFailure)?.code,"invalid_image")
        }
        try store.write(Data("not a png".utf8),to:url)
        XCTAssertThrowsError(try store.image(for:o)) { error in
            XCTAssertTrue(["invalid_image","stale_image"].contains((error as? ToolFailure)?.code ?? ""))
        }
    }
    func testStoreRejectsUnsafeParentsAndFinalSymlinks() throws {
        let container=FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString,isDirectory:true)
        try FileManager.default.createDirectory(at:container,withIntermediateDirectories:false,attributes:[.posixPermissions:0o700])
        defer { if FileManager.default.fileExists(atPath:container.path) { try? FileManager.default.removeItem(at:container) } }

        let writableParent=container.appendingPathComponent("writable",isDirectory:true)
        try FileManager.default.createDirectory(at:writableParent,withIntermediateDirectories:false)
        try FileManager.default.setAttributes([.posixPermissions:0o777],ofItemAtPath:writableParent.path)
        XCTAssertThrowsError(try Store(root:writableParent.appendingPathComponent("state"))) { error in
            XCTAssertEqual((error as? ToolFailure)?.code,"unsafe_state_directory")
        }

        let target=container.appendingPathComponent("target",isDirectory:true)
        try FileManager.default.createDirectory(at:target,withIntermediateDirectories:false,attributes:[.posixPermissions:0o700])
        let alias=container.appendingPathComponent("state",isDirectory:true)
        try FileManager.default.createSymbolicLink(at:alias,withDestinationURL:target)
        XCTAssertThrowsError(try Store(root:alias)) { error in
            XCTAssertEqual((error as? ToolFailure)?.code,"unsafe_state_directory")
        }

        func changeACL(_ arguments:[String]) throws {
            let process=Process()
            process.executableURL=URL(fileURLWithPath:"/bin/chmod")
            process.arguments=arguments
            try process.run()
            process.waitUntilExit()
            XCTAssertEqual(process.terminationStatus,0)
        }
        try changeACL(["+a","everyone deny delete",container.path])
        XCTAssertNoThrow(try Store(root:container.appendingPathComponent("deny-protected-state")))
        try changeACL(["-N",container.path])

        try changeACL(["+a","everyone allow add_subdirectory,delete_child,writesecurity",container.path])
        XCTAssertThrowsError(try Store(root:container.appendingPathComponent("acl-state"))) { error in
            XCTAssertEqual((error as? ToolFailure)?.code,"unsafe_state_directory")
        }
        try changeACL(["-N",container.path])

        let privateRoot=container.appendingPathComponent("private-state",isDirectory:true)
        let firstStore=try Store(root:privateRoot)
        try changeACL(["+a","everyone allow read,list,search",privateRoot.path])
        XCTAssertThrowsError(try Store(root:privateRoot)) { error in
            XCTAssertEqual((error as? ToolFailure)?.code,"unsafe_state_directory")
        }
        withExtendedLifetime(firstStore) {}
    }
    func testStoreAnchorsDirectoryAndDoesNotFollowStateFileSymlinks() throws {
        let container=FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString,isDirectory:true)
        try FileManager.default.createDirectory(at:container,withIntermediateDirectories:false,attributes:[.posixPermissions:0o700])
        defer { if FileManager.default.fileExists(atPath:container.path) { try? FileManager.default.removeItem(at:container) } }
        let root=container.appendingPathComponent("state",isDirectory:true)
        let store=try Store(root:root)

        let outside=container.appendingPathComponent("outside")
        try Data("sentinel".utf8).write(to:outside)
        try FileManager.default.createSymbolicLink(
            at:root.appendingPathComponent("audit.jsonl"),
            withDestinationURL:outside
        )
        store.audit(tool:"fixture",status:"attempted")
        XCTAssertEqual(try String(contentsOf:outside,encoding:.utf8),"sentinel")

        let observation=observation()
        try FileManager.default.createSymbolicLink(
            at:try store.tokenURL(observation.id),
            withDestinationURL:outside
        )
        try store.save(observation)
        XCTAssertEqual(try store.load(observation.id).id,observation.id)
        XCTAssertEqual(try String(contentsOf:outside,encoding:.utf8),"sentinel")

        let anchored=container.appendingPathComponent("anchored-state",isDirectory:true)
        try FileManager.default.moveItem(at:root,to:anchored)
        try FileManager.default.createDirectory(at:root,withIntermediateDirectories:false,attributes:[.posixPermissions:0o700])
        try store.savePointer(Pointer(windowID:7,pid:42,x:1,y:2))
        XCTAssertTrue(FileManager.default.fileExists(atPath:anchored.appendingPathComponent("pointer.json").path))
        XCTAssertFalse(FileManager.default.fileExists(atPath:root.appendingPathComponent("pointer.json").path))
    }
    func testLockPreventsConcurrentMutation() throws {
        let dir=FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { if FileManager.default.fileExists(atPath:dir.path) { try? FileManager.default.removeItem(at:dir) } }
        let a=try Store(root:dir),b=try Store(root:dir)
        try a.lock(); XCTAssertThrowsError(try b.lock()); a.unlock(); try b.lock(); b.unlock()
    }
    func testRPCVersionNegotiation() {
        let current=RPC.initialize(["protocolVersion":"2024-11-05"])
        XCTAssertEqual(current["protocolVersion"] as? String,"2024-11-05")
        XCTAssertEqual((current["serverInfo"] as? [String:Any])?["name"] as? String,"macpilot")
        XCTAssertEqual((current["serverInfo"] as? [String:Any])?["version"] as? String,"3.0.0")
        XCTAssertEqual(RPC.initialize(["protocolVersion":"future"])["protocolVersion"] as? String,"2025-11-25")
    }
    func testSystemActionSchemasArePresentAndStrict() throws {
        let tools=ToolCatalog.tools
        let names=Set(tools.compactMap { $0["name"] as? String })
        XCTAssertTrue(Set(["mac_app","mac_open","mac_reveal","mac_trash","mac_clipboard_read","mac_clipboard_write","mac_shortcuts","mac_script"]).isSubset(of:names))
        let script=try XCTUnwrap(tools.first { $0["name"] as? String == "mac_script" })
        let schema=try XCTUnwrap(script["inputSchema"] as? [String:Any])
        XCTAssertEqual(schema["additionalProperties"] as? Bool,false)
        XCTAssertEqual(Set(schema["required"] as? [String] ?? []),Set(["language","source"]))
        let shortcuts=try XCTUnwrap(tools.first { $0["name"] as? String == "mac_shortcuts" })
        let shortcutsSchema=try XCTUnwrap(shortcuts["inputSchema"] as? [String:Any])
        XCTAssertEqual((shortcutsSchema["oneOf"] as? [[String:Any]])?.count,3)
    }
    func testFindAndWaitSchemasArePresentAndStrict() throws {
        let tools=ToolCatalog.tools
        let find=try XCTUnwrap(tools.first { $0["name"] as? String == "mac_find" })
        let findSchema=try XCTUnwrap(find["inputSchema"] as? [String:Any])
        XCTAssertEqual(findSchema["additionalProperties"] as? Bool,false)
        XCTAssertEqual(Set(findSchema["required"] as? [String] ?? []),Set(["observation"]))
        XCTAssertEqual((findSchema["anyOf"] as? [[String:Any]])?.count,4)
        let wait=try XCTUnwrap(tools.first { $0["name"] as? String == "mac_wait" })
        let waitSchema=try XCTUnwrap(wait["inputSchema"] as? [String:Any])
        XCTAssertEqual(waitSchema["additionalProperties"] as? Bool,false)
        XCTAssertEqual(Set(waitSchema["required"] as? [String] ?? []),Set(["observation","node"]))
        XCTAssertEqual((waitSchema["oneOf"] as? [[String:Any]])?.count,2)
        let verify=try XCTUnwrap(tools.first { $0["name"] as? String == "mac_verify" })
        let verifySchema=try XCTUnwrap(verify["inputSchema"] as? [String:Any])
        XCTAssertEqual((verifySchema["oneOf"] as? [[String:Any]])?.count,2)
        for tool in [find,wait] {
            let annotations=try XCTUnwrap(tool["annotations"] as? [String:Any])
            XCTAssertEqual(annotations["readOnlyHint"] as? Bool,true)
            XCTAssertEqual(annotations["destructiveHint"] as? Bool,false)
        }
    }
    func testDisplayMenuAndWindowSchemasAreTypedAndStrict() throws {
        let tools=ToolCatalog.tools
        let names=Set(tools.compactMap { $0["name"] as? String })
        XCTAssertTrue(Set(["mac_capture","mac_menu","mac_window"]).isSubset(of:names))

        let capture=try XCTUnwrap(tools.first { $0["name"] as? String == "mac_capture" })
        let captureSchema=try XCTUnwrap(capture["inputSchema"] as? [String:Any])
        let captureProperties=try XCTUnwrap(captureSchema["properties"] as? [String:Any])
        let displayID=try XCTUnwrap(captureProperties["displayID"] as? [String:Any])
        let maxDimension=try XCTUnwrap(captureProperties["maxDimension"] as? [String:Any])
        XCTAssertEqual(captureSchema["additionalProperties"] as? Bool,false)
        XCTAssertEqual(Set(captureSchema["required"] as? [String] ?? []),Set(["displayID"]))
        XCTAssertEqual(displayID["type"] as? String,"integer")
        XCTAssertEqual(displayID["minimum"] as? Int,1)
        XCTAssertEqual(maxDimension["maximum"] as? Int,8192)
        let captureAnnotations=try XCTUnwrap(capture["annotations"] as? [String:Any])
        XCTAssertEqual(captureAnnotations["readOnlyHint"] as? Bool,true)
        XCTAssertEqual(captureAnnotations["destructiveHint"] as? Bool,false)

        let menu=try XCTUnwrap(tools.first { $0["name"] as? String == "mac_menu" })
        let menuSchema=try XCTUnwrap(menu["inputSchema"] as? [String:Any])
        let menuProperties=try XCTUnwrap(menuSchema["properties"] as? [String:Any])
        let menuOperation=try XCTUnwrap(menuProperties["operation"] as? [String:Any])
        let titlePath=try XCTUnwrap(menuProperties["titlePath"] as? [String:Any])
        XCTAssertEqual(menuSchema["additionalProperties"] as? Bool,false)
        XCTAssertEqual(Set(menuSchema["required"] as? [String] ?? []),Set(["pid","operation"]))
        XCTAssertEqual(Set(menuOperation["enum"] as? [String] ?? []),Set(["list","press"]))
        XCTAssertEqual(titlePath["minItems"] as? Int,1)
        XCTAssertEqual(titlePath["maxItems"] as? Int,8)
        XCTAssertEqual((menuSchema["oneOf"] as? [[String:Any]])?.count,2)
        let menuVariants=try XCTUnwrap(menuSchema["oneOf"] as? [[String:Any]])
        XCTAssertTrue(menuVariants.contains { Set($0["required"] as? [String] ?? []) == Set(["pid","operation","titlePath","processStartID"]) })

        let window=try XCTUnwrap(tools.first { $0["name"] as? String == "mac_window" })
        let windowSchema=try XCTUnwrap(window["inputSchema"] as? [String:Any])
        let windowProperties=try XCTUnwrap(windowSchema["properties"] as? [String:Any])
        let windowOperation=try XCTUnwrap(windowProperties["operation"] as? [String:Any])
        XCTAssertEqual(windowSchema["additionalProperties"] as? Bool,false)
        XCTAssertEqual(Set(windowSchema["required"] as? [String] ?? []),Set(["observation","operation"]))
        XCTAssertEqual(Set(windowOperation["enum"] as? [String] ?? []),
                       Set(["state","raise","close","minimize","unminimize","toggle_full_screen","move","resize"]))
        let windowVariants=try XCTUnwrap(windowSchema["oneOf"] as? [[String:Any]])
        XCTAssertEqual(windowVariants.count,3)
        XCTAssertTrue(windowVariants.contains { Set($0["required"] as? [String] ?? []) == Set(["observation","operation","x","y"]) })
        XCTAssertTrue(windowVariants.contains { Set($0["required"] as? [String] ?? []) == Set(["observation","operation","width","height"]) })
        for tool in [menu,window] {
            let annotations=try XCTUnwrap(tool["annotations"] as? [String:Any])
            XCTAssertEqual(annotations["readOnlyHint"] as? Bool,false)
            XCTAssertEqual(annotations["destructiveHint"] as? Bool,true)
            XCTAssertEqual(annotations["idempotentHint"] as? Bool,false)
        }
        let ax=try XCTUnwrap(tools.first { $0["name"] as? String == "mac_ax" })
        let axSchema=try XCTUnwrap(ax["inputSchema"] as? [String:Any])
        XCTAssertEqual((axSchema["oneOf"] as? [[String:Any]])?.count,4)
        let click=try XCTUnwrap(tools.first { $0["name"] as? String == "mac_click" })
        let clickSchema=try XCTUnwrap(click["inputSchema"] as? [String:Any])
        XCTAssertEqual((clickSchema["oneOf"] as? [[String:Any]])?.count,2)
        let scroll=try XCTUnwrap(tools.first { $0["name"] as? String == "mac_scroll" })
        let scrollSchema=try XCTUnwrap(scroll["inputSchema"] as? [String:Any])
        XCTAssertEqual((scrollSchema["anyOf"] as? [[String:Any]])?.count,4)
        let observe=try XCTUnwrap(tools.first { $0["name"] as? String == "mac_observe" })
        let observeSchema=try XCTUnwrap(observe["inputSchema"] as? [String:Any])
        XCTAssertEqual(Set(observeSchema["required"] as? [String] ?? []),Set(["pid","processStartID"]))
    }
    func testConditionalSchemaBranchesRemainCompleteForMCPHosts() throws {
        for tool in ToolCatalog.tools {
            let schema=try XCTUnwrap(tool["inputSchema"] as? [String:Any])
            let rootProperties=Set((schema["properties"] as? [String:Any] ?? [:]).keys)
            let rootRequired=Set(schema["required"] as? [String] ?? [])
            let branches=(schema["oneOf"] as? [[String:Any]]) ?? (schema["anyOf"] as? [[String:Any]]) ?? []
            for branch in branches {
                XCTAssertEqual(branch["type"] as? String,"object")
                XCTAssertEqual(branch["additionalProperties"] as? Bool,false)
                let branchProperties=Set((branch["properties"] as? [String:Any] ?? [:]).keys)
                let branchRequired=Set(branch["required"] as? [String] ?? [])
                XCTAssertTrue(rootProperties.isSubset(of:branchProperties))
                XCTAssertTrue(rootRequired.isSubset(of:branchRequired))
            }
        }
    }
    @MainActor func testNewSurfaceRejectsOperationMismatchesBeforeSystemAccess() async throws {
        let dir=FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString,isDirectory:true)
        defer { if FileManager.default.fileExists(atPath:dir.path) { try? FileManager.default.removeItem(at:dir) } }
        let engine=Engine(store:try Store(root:dir))
        let invalidCalls:[(String,[String:Any])]=[
            ("mac_capture",["displayID":1,"maxDimension":0]),
            ("mac_observe",["pid":1]),
            ("mac_menu",["pid":1,"operation":"list","titlePath":["File"]]),
            ("mac_menu",["pid":1,"operation":"press"]),
            ("mac_menu",["pid":1,"operation":"press","titlePath":[""]]),
            ("mac_menu",["pid":1,"operation":"press","titlePath":["File"]]),
            ("mac_window",["observation":UUID().uuidString,"operation":"state","x":0]),
            ("mac_window",["observation":UUID().uuidString,"operation":"move","x":0]),
            ("mac_window",["observation":UUID().uuidString,"operation":"resize","width":0,"height":100]),
            ("mac_window",["observation":UUID().uuidString,"operation":"unknown"]),
            ("mac_ax",["observation":UUID().uuidString,"node":"root","operation":"focus","text":"ignored"]),
            ("mac_ax",["observation":UUID().uuidString,"node":"root","operation":"set_value"]),
            ("mac_shortcuts",["operation":"list","name":"ignored"]),
            ("mac_click",["observation":UUID().uuidString,"x":1,"y":1,"button":"right"]),
            ("mac_click",["observation":UUID().uuidString,"x":1,"y":1,"toX":2]),
            ("mac_scroll",["observation":UUID().uuidString,"x":1,"y":1,"vertical":0,"horizontal":0]),
            ("mac_key",["observation":UUID().uuidString,"node":"root","key":"a","text":"ignored"]),
            ("mac_type",["observation":UUID().uuidString,"node":"root","text":"x","key":"ignored"]),
            ("mac_find",["observation":UUID().uuidString]),
            ("mac_wait",["observation":UUID().uuidString,"node":"root"]),
            ("mac_wait",["observation":UUID().uuidString,"node":"root","equals":"a","contains":"b"]),
            ("mac_verify",["observation":UUID().uuidString,"node":"root"]),
            ("mac_verify",["observation":UUID().uuidString,"node":"root","equals":"a","contains":"b"])
        ]
        for (tool,arguments) in invalidCalls {
            do {
                _ = try await engine.call(tool,arguments:arguments)
                XCTFail("Expected invalid_argument for \(tool): \(arguments)")
            } catch let failure as ToolFailure {
                XCTAssertEqual(failure.code,"invalid_argument","\(tool): \(arguments)")
            } catch {
                XCTFail("Unexpected error for \(tool): \(error)")
            }
        }
    }
    func testProcessStartIdentityRejectsStalePIDBinding() throws {
        let pid=ProcessInfo.processInfo.processIdentifier
        let identity=try XCTUnwrap(ProcessIdentity.startID(pid:pid))
        XCTAssertNoThrow(try ProcessIdentity.require(pid:pid,expected:identity))
        XCTAssertThrowsError(try ProcessIdentity.require(pid:pid,expected:identity+"0")) { error in
            XCTAssertEqual((error as? ToolFailure)?.code,"stale_app_identity")
        }
    }
    @MainActor func testFailedObservationAndObservationBoundCallsAuditTargetPID() async throws {
        let dir=FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString,isDirectory:true)
        defer { if FileManager.default.fileExists(atPath:dir.path) { try? FileManager.default.removeItem(at:dir) } }
        let store=try Store(root:dir), engine=Engine(store:store)
        let pid=ProcessInfo.processInfo.processIdentifier
        let identity=try XCTUnwrap(ProcessIdentity.startID(pid:pid))
        do {
            _ = try await engine.call("mac_observe",arguments:["pid":pid,"processStartID":identity+"0","screenshot":false])
            XCTFail("Expected stale identity")
        } catch let failure as ToolFailure {
            XCTAssertEqual(failure.code,"stale_app_identity")
        }
        var o=observation(); o.pid=pid; o.processStartID=identity
        try store.save(o)
        do {
            _ = try await engine.call("mac_ax",arguments:["observation":o.id,"node":"root","operation":"focus"])
            XCTFail("Expected stale observation")
        } catch {
            XCTAssertNotNil(error as? ToolFailure)
        }
        let rows=try String(contentsOf:dir.appendingPathComponent("audit.jsonl"),encoding:.utf8)
            .split(separator:"\n").map { try XCTUnwrap(try JSONSerialization.jsonObject(with:Data($0.utf8)) as? [String:Any]) }
        XCTAssertEqual(rows.count,2)
        XCTAssertTrue(rows.allSatisfy { ($0["pid"] as? NSNumber)?.int32Value == pid })
    }
    @MainActor func testCancelledEngineCallIsAuditedBeforeLockAcquisition() async throws {
        let dir=FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString,isDirectory:true)
        defer { if FileManager.default.fileExists(atPath:dir.path) { try? FileManager.default.removeItem(at:dir) } }
        let engine=Engine(store:try Store(root:dir))
        let task=Task { @MainActor in
            withUnsafeCurrentTask { $0?.cancel() }
            return try await engine.call("mac_doctor",arguments:[:])
        }
        do {
            _ = try await task.value
            XCTFail("Expected cancellation")
        } catch is CancellationError {
        } catch {
            XCTFail("Unexpected error: \(error)")
        }
        let rows=try String(contentsOf:dir.appendingPathComponent("audit.jsonl"),encoding:.utf8)
            .split(separator:"\n").map { try XCTUnwrap(try JSONSerialization.jsonObject(with:Data($0.utf8)) as? [String:Any]) }
        XCTAssertEqual(rows.count,1)
        XCTAssertEqual(rows.first?["tool"] as? String,"mac_doctor")
        XCTAssertEqual(rows.first?["status"] as? String,"cancelled")
    }
    @MainActor func testSystemActionURLAndExplicitPathValidation() throws {
        let dir=FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString,isDirectory:true)
        try FileManager.default.createDirectory(at:dir,withIntermediateDirectories:true)
        defer { if FileManager.default.fileExists(atPath:dir.path) { try? FileManager.default.removeItem(at:dir) } }
        let file=dir.appendingPathComponent("a file.txt")
        try Data("fixture".utf8).write(to:file)
        XCTAssertEqual(try SystemActions.validatedOpenURL(file.absoluteURL.absoluteString).path,file.path)
        XCTAssertEqual(try SystemActions.validatedOpenURL("https://example.com/a").host,"example.com")
        XCTAssertThrowsError(try SystemActions.validatedOpenURL("ftp://example.com/a"))
        XCTAssertThrowsError(try SystemActions.validatedOpenURL(dir.appendingPathComponent("missing").absoluteString))
        XCTAssertEqual(try SystemActions.explicitFileURLs([file.path],key:"paths",mustExist:true,rejectRoot:true),[file.standardizedFileURL])
        XCTAssertThrowsError(try SystemActions.explicitFileURLs(["relative"],key:"paths",mustExist:false,rejectRoot:false))
        XCTAssertThrowsError(try SystemActions.explicitFileURLs([file.path,file.path],key:"paths",mustExist:true,rejectRoot:false))
        XCTAssertThrowsError(try SystemActions.explicitFileURLs(["/"],key:"paths",mustExist:true,rejectRoot:true))
    }
    @MainActor func testShortcutArgumentsRemainTyped() throws {
        XCTAssertEqual(try SystemActions.shortcutArguments(Arguments(["showIdentifiers":true]),operation:"list"),["list","--show-identifiers"])
        XCTAssertEqual(try SystemActions.shortcutArguments(Arguments(["name":"Fixture"]),operation:"view"),["view","Fixture"])
        XCTAssertEqual(try SystemActions.shortcutArguments(Arguments(["name":"Fixture","outputType":"public.json"]),operation:"run"),["run","Fixture","--output-type","public.json"])
        XCTAssertThrowsError(try SystemActions.shortcutArguments(Arguments(["name":"-option"]),operation:"run"))
        XCTAssertThrowsError(try SystemActions.shortcutArguments(Arguments(["folder":"A","folders":true]),operation:"list"))
        XCTAssertThrowsError(try SystemActions.shortcutArguments(Arguments([:]),operation:"delete"))
        XCTAssertEqual(try SystemActions.scriptLanguage("applescript"),"AppleScript")
        XCTAssertEqual(try SystemActions.scriptLanguage("javascript"),"JavaScript")
        XCTAssertThrowsError(try SystemActions.scriptLanguage("shell"))
    }
    func testCommandRunnerUsesStdinWithoutShellInterpolationAndBoundsOutput() async throws {
        let sentinel=FileManager.default.temporaryDirectory.appendingPathComponent("macpilot-\(UUID().uuidString)")
        let literal="$(touch \(sentinel.path)) `whoami`\n"
        let cat=try await CommandRunner.run(executable:URL(fileURLWithPath:"/bin/cat"),arguments:[],standardInput:literal,timeoutMilliseconds:1_000,maxOutputBytes:4_096)
        XCTAssertEqual(cat.exitCode,0)
        XCTAssertEqual(cat.stdout,literal)
        XCTAssertFalse(FileManager.default.fileExists(atPath:sentinel.path))
        let long=String(repeating:"x",count:256)
        let bounded=try await CommandRunner.run(executable:URL(fileURLWithPath:"/usr/bin/printf"),arguments:["%s",long],timeoutMilliseconds:1_000,maxOutputBytes:32)
        XCTAssertEqual(bounded.stdout,String(repeating:"x",count:32))
        XCTAssertEqual(bounded.stdoutBytes,256)
        XCTAssertTrue(bounded.stdoutTruncated)
    }
    func testCommandRunnerTerminatesAtTimeout() async {
        do {
            _ = try await CommandRunner.run(executable:URL(fileURLWithPath:"/bin/sleep"),arguments:["2"],timeoutMilliseconds:100,maxOutputBytes:32)
            XCTFail("Expected timeout")
        } catch let error as ToolFailure {
            XCTAssertEqual(error.code,"process_timeout")
            XCTAssertTrue(error.description.contains("wrapper process was terminated"))
            XCTAssertTrue(error.description.contains("Apple Events"))
            XCTAssertTrue(error.description.contains("Shortcut service work"))
            XCTAssertTrue(error.description.contains("external side effects may continue"))
            XCTAssertTrue(error.description.contains("Reconcile target state before retrying"))
        } catch {
            XCTFail("Unexpected error: \(error)")
        }
    }
    func testCommandRunnerTimeoutIncludesBlockedStdinDelivery() async {
        let started=Date()
        do {
            _ = try await CommandRunner.run(
                executable:URL(fileURLWithPath:"/bin/sleep"),
                arguments:["5"],
                standardInput:String(repeating:"x",count:131_072),
                timeoutMilliseconds:100,
                maxOutputBytes:32
            )
            XCTFail("Expected timeout")
        } catch let error as ToolFailure {
            XCTAssertEqual(error.code,"process_timeout")
            XCTAssertTrue(error.description.contains("wrapper process was terminated"))
            XCTAssertTrue(error.description.contains("Reconcile target state before retrying"))
            XCTAssertLessThan(Date().timeIntervalSince(started),1.5)
        } catch {
            XCTFail("Unexpected error: \(error)")
        }
    }
    func testCommandRunnerKeepsTimeoutDiagnosisWhenChildHoldsOutputPipes() async {
        do {
            _ = try await CommandRunner.run(
                executable:URL(fileURLWithPath:"/bin/sh"),
                arguments:["-c","(trap '' HUP TERM; sleep 3) & sleep 3"],
                timeoutMilliseconds:100,
                maxOutputBytes:32
            )
            XCTFail("Expected timeout")
        } catch let error as ToolFailure {
            XCTAssertEqual(error.code,"process_timeout")
            XCTAssertTrue(error.description.contains("wrapper process was terminated"))
            XCTAssertTrue(error.description.contains("external side effects may continue"))
            XCTAssertTrue(error.description.contains("Reconcile target state before retrying"))
        } catch {
            XCTFail("Unexpected error: \(error)")
        }
    }
    @MainActor func testTrashResultPreservesFullSuccessShapeAndInputOrder() {
        let first=URL(fileURLWithPath:"/tmp/source-b")
        let second=URL(fileURLWithPath:"/tmp/source-a")
        let firstDestination=URL(fileURLWithPath:"/tmp/.Trash/source-b")
        let secondDestination=URL(fileURLWithPath:"/tmp/.Trash/source-a")
        let result=SystemActions.trashResult(
            sources:[first,second],
            destinations:[second:secondDestination,first:firstDestination],
            errorDescription:nil
        )
        XCTAssertEqual(result["status"] as? String,"trashed")
        XCTAssertEqual(result["count"] as? Int,2)
        XCTAssertNil(result["error"])
        let items=result["items"] as? [[String:String]]
        XCTAssertEqual(items?.map { $0["source"] },[first.path,second.path])
        XCTAssertEqual(items?.map { $0["destination"] },[firstDestination.path,secondDestination.path])
    }
    @MainActor func testTrashResultReturnsEveryKnownMappingAndUncertainty() {
        let first=URL(fileURLWithPath:"/tmp/source-a")
        let second=URL(fileURLWithPath:"/tmp/source-b")
        let unexpected=URL(fileURLWithPath:"/tmp/source-extra")
        let firstDestination=URL(fileURLWithPath:"/tmp/.Trash/source-a")
        let unexpectedDestination=URL(fileURLWithPath:"/tmp/.Trash/source-extra")
        let result=SystemActions.trashResult(
            sources:[first,second],
            destinations:[unexpected:unexpectedDestination,first:firstDestination],
            errorDescription:"fixture failure"
        )
        XCTAssertEqual(result["status"] as? String,"trash_incomplete")
        XCTAssertEqual(result["count"] as? Int,2)
        XCTAssertEqual(result["requestedCount"] as? Int,2)
        XCTAssertEqual(result["complete"] as? Bool,false)
        XCTAssertEqual(result["uncertain"] as? Bool,true)
        XCTAssertEqual(result["uncertainSources"] as? [String],[second.path])
        let items=result["items"] as? [[String:String]]
        XCTAssertEqual(items?.count,2)
        XCTAssertEqual(Set(items?.compactMap { $0["source"] } ?? []),Set([first.path,unexpected.path]))
        let error=result["error"] as? [String:String]
        XCTAssertEqual(error?["code"],"trash_failed")
        XCTAssertTrue(error?["message"]?.contains("fixture failure") == true)
        XCTAssertTrue((result["verification"] as? String)?.contains("before retrying") == true)
    }
    @MainActor func testTrashResultReportsIncompleteCallbackWithoutNSError() {
        let first=URL(fileURLWithPath:"/tmp/source-a")
        let second=URL(fileURLWithPath:"/tmp/source-b")
        let result=SystemActions.trashResult(
            sources:[first,second],
            destinations:[first:URL(fileURLWithPath:"/tmp/.Trash/source-a")],
            errorDescription:nil
        )
        let error=result["error"] as? [String:String]
        XCTAssertEqual(result["status"] as? String,"trash_incomplete")
        XCTAssertEqual(error?["code"],"trash_incomplete")
        XCTAssertTrue(error?["message"]?.contains("without an error") == true)
        XCTAssertEqual(result["uncertainSources"] as? [String],[second.path])
    }
    @MainActor func testTrashTimeoutReportsLateCompletionRiskAndReconciliation() {
        let message=SystemActions.trashTimeoutDescription(timeoutMilliseconds:1234)
        XCTAssertTrue(message.contains("NSWorkspace.recycle did not finish within 1234 ms"))
        XCTAssertTrue(message.contains("system recycle operation may still complete after this timeout"))
        XCTAssertTrue(message.contains("reconcile every requested source and Trash state before retrying"))
    }
    @MainActor func testKeyEventsBalanceAndPrivateModifierFlags() async throws {
        let events=try Input.keyEvents(key:"a",modifiers:["command","shift"])
        XCTAssertEqual(events.map(\.type),[.keyDown,.keyUp])
        XCTAssertTrue(events.allSatisfy { $0.flags.contains([.maskCommand,.maskShift]) })
        XCTAssertThrowsError(try Input.keyEvents(key:"a",modifiers:["typo"]))
        XCTAssertThrowsError(try Input.keyEvents(key:"unknown",modifiers:[]))
        let text=try Input.textEvents("한글😀")
        XCTAssertEqual(text.count % 2,0); XCTAssertTrue(text.allSatisfy { $0.flags.isEmpty })
    }
    func testCallbackDeadlineReturnsWithoutAFrameworkCallback() async {
        let started=DispatchTime.now().uptimeNanoseconds
        do {
            let _: String = try await withCallbackDeadline(
                timeoutMilliseconds:50,
                timeoutFailure:ToolFailure("fixture_timeout","fixture callback did not arrive")
            ) { _ in }
            XCTFail("Expected timeout")
        } catch let error as ToolFailure {
            XCTAssertEqual(error.code,"fixture_timeout")
            XCTAssertLessThan(DispatchTime.now().uptimeNanoseconds-started,1_000_000_000)
        } catch {
            XCTFail("Unexpected error: \(error)")
        }
    }
    @MainActor func testAXConfiguresProcessWideMessagingTimeout() {
        XCTAssertNoThrow(try AX.ensureMessagingTimeout())
    }
}
