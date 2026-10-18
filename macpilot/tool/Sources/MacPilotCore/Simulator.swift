import AppKit
import ApplicationServices
import CryptoKit
import Darwin

// simctl is optional. Ordinary desktop operations do not resolve or load Xcode.
enum SimulatorModel {
    static let operations = ["list","status","boot","shutdown","install","uninstall","launch","terminate","open_url","screenshot","record","observe","probe_input","input"]
    static func uuid(_ value: String) throws -> String {
        guard let id = UUID(uuidString:value) else { throw ToolFailure("invalid_argument","An explicit Simulator UDID is required; aliases are not accepted") }
        return id.uuidString
    }
    static func launchdPID(_ output: String, udid: String, uid: UInt32) throws -> Int32 {
        let header="user/\(uid)/com.apple.CoreSimulator.SimDevice.\(udid) = {"
        guard output.hasPrefix(header + "\n") else {throw ToolFailure("simulator_boot_unavailable","Exact launchd job not found")}
        let rows=output.components(separatedBy:"\n").map{$0.trimmingCharacters(in:.whitespaces)}.filter{$0.hasPrefix("pid = ")}
        guard rows.count==1, let row=rows.first, let pid=Int32(row.dropFirst(6)), pid>0,
              output.contains("/" + udid + "/data/var/run/launchd_bootstrap.plist") else {
            throw ToolFailure("simulator_boot_unavailable","No unique running launchd_sim for this device")
        }; return pid
    }
    static func bundleID(_ value: String) throws -> String {
        guard !value.isEmpty, value.utf8.count <= 255, value.first != "-", value.contains("."),
              value.allSatisfy({ $0.isASCII && ($0.isLetter || $0.isNumber || $0 == "." || $0 == "-" || $0 == "_") }) else {
            throw ToolFailure("invalid_argument","Invalid bundle ID")
        }; return value
    }
    static func identity(_ row: [String:Any], runtime: String) throws -> String {
        guard let path = row["dataPath"] as? String, let udid = row["udid"] as? String,
              path.hasSuffix("/" + udid + "/data") else { throw ToolFailure("simulator_identity_unavailable","No device data directory") }
        let attrs = try FileManager.default.attributesOfItem(atPath:URL(fileURLWithPath:path).deletingLastPathComponent().path)
        let value = "\(udid)|\(runtime)|\(row["deviceTypeIdentifier"] ?? "")|\(attrs[.systemFileNumber] ?? "")|\(attrs[.creationDate] ?? "")"
        return SHA256.hash(data:Data(value.utf8)).map { String(format:"%02x",$0) }.joined()
    }
}

@MainActor extension Engine {
    private func simctl(_ args: [String], timeout: Int = 20000) async throws -> CommandOutput {
        let output = try await CommandRunner.run(executable:URL(fileURLWithPath:"/usr/bin/xcrun"),arguments:["simctl"] + args,
                                                timeoutMilliseconds:timeout,maxOutputBytes:1_048_576)
        guard output.exitCode == 0, !output.stdoutTruncated, !output.stderrTruncated else {
            throw ToolFailure("simctl_failed","simctl \(args.first ?? "") failed (\(output.exitCode)): \(output.stderr.prefix(1024)); reconcile device state before retry")
        }; return output
    }
    private func simulatorDevices() async throws -> [[String:Any]] {
        let output = try await simctl(["list","devices","--json"])
        guard let data = output.stdout.data(using:.utf8), let object = try JSONSerialization.jsonObject(with:data) as? [String:Any],
              let groups = object["devices"] as? [String:[[String:Any]]] else { throw ToolFailure("simctl_invalid_response","Device inventory is not valid JSON") }
        var result: [[String:Any]] = []
        for runtime in groups.keys.sorted() {
            for var row in groups[runtime]! {
                row["runtime"] = runtime
                if row["isAvailable"] as? Bool == true { do {row["deviceIdentity"] = try SimulatorModel.identity(row,runtime:runtime)} catch {row["identityUnavailable"]=true} }
                result.append(row)
            }
        }; return result
    }
    private func simulatorBoot(_ udid: String) async throws -> (pid:Int32,start:String) {
        let label="user/\(getuid())/com.apple.CoreSimulator.SimDevice.\(udid)"
        let output=try await CommandRunner.run(executable:URL(fileURLWithPath:"/bin/launchctl"),arguments:["print",label],
                                               timeoutMilliseconds:3000,maxOutputBytes:65536)
        guard output.exitCode==0, !output.stdoutTruncated else {throw ToolFailure("simulator_boot_unavailable","Simulator launchd job is not ready")}
        let pid=try SimulatorModel.launchdPID(output.stdout,udid:udid,uid:getuid())
        guard let start=ProcessIdentity.startID(pid:pid) else {
            throw ToolFailure("simulator_boot_unavailable","Cannot identify launchd_sim process generation")
        }; return (pid,start)
    }
    private func simulatorCurrent(_ udid: String, deviceIdentity: String) async throws -> [String:Any] {
        guard let row = try await simulatorDevices().first(where:{ $0["udid"] as? String == udid }),
              row["deviceIdentity"] as? String == deviceIdentity else { throw ToolFailure("stale_simulator_identity","Device was replaced or is unavailable; refresh status") }
        return row
    }
    func simulator(_ a: Arguments) async throws -> [String:Any] {
        let operation = try a.string("operation",limit:32)
        guard SimulatorModel.operations.contains(operation) else { throw ToolFailure("invalid_argument","Unknown Simulator operation") }
        let common = ["operation","udid","deviceIdentity","bootID"]
        let extra: [String]
        switch operation {
        case "install": extra=["path"]
        case "launch","terminate","uninstall": extra=["bundleID"]
        case "open_url": extra=["url"]
        case "record": extra=["durationSeconds"]
        case "screenshot": extra=["ocr","languages"]
        case "observe": extra=["pid","processStartID","windowID","maxNodes","maxDepth"]
        case "input": extra=["privateAPI","gesture","x","y","toX","toY","x2","y2","toX2","toY2","duration","key"]
        default: extra=[]
        }
        try a.only(common + extra)
        if operation == "list" { return ["status":"simulators_listed","devices":try await simulatorDevices(),"requiresXcode":true] }
        let udid = try SimulatorModel.uuid(a.string("udid",limit:36))
        let lease = try baseStore.lease(".simulator-\(udid.lowercased()).lock")
        defer { withExtendedLifetime(lease) {} }
        let inventory = try await simulatorDevices()
        guard let row = inventory.first(where: { $0["udid"] as? String == udid }), let identity = row["deviceIdentity"] as? String else {
            throw ToolFailure("simulator_not_found","Exact available Simulator not found")
        }
        let booted = row["state"] as? String == "Booted"
        var boot: (pid:Int32,start:String)?
        var bootFailure: String?
        if booted {
            do {boot=try await simulatorBoot(udid)}
            catch {
                if operation != "status" {throw error}
                bootFailure=(error as? ToolFailure)?.code ?? "simulator_boot_unavailable"
            }
        }
        let bootID = boot.map { "\($0.pid):\($0.start)" }
        var result: [String:Any] = ["status":"simulator_status","device":row,"udid":udid,"deviceIdentity":identity]
        if let bootID {result["bootID"]=bootID}
        result["ready"] = boot != nil
        if let bootFailure {result["bootIdentityStatus"]="unavailable";result["bootIdentityError"]=bootFailure}
        if operation == "status" { return result }
        guard try a.string("deviceIdentity",limit:64) == identity else { throw ToolFailure("stale_simulator_identity","Refresh status before device operations") }
        if operation == "boot" {
            guard !booted else { throw ToolFailure("simulator_already_booted","Device is already booted; inspect status") }
            _ = try await simctl(["boot",udid])
            result["status"]="simulator_boot_requested"; return result
        }
        guard let boot, let bootID, try a.string("bootID",limit:96) == bootID else { throw ToolFailure("stale_simulator_boot","Exact bootID from status is required") }
        var command: [String] = []
        switch operation {
        case "shutdown": command=["shutdown",udid]
        case "install":
            let path = try a.string("path",limit:8192)
            guard path.hasPrefix("/"), path.hasSuffix(".app"), FileManager.default.fileExists(atPath:path + "/Info.plist") else { throw ToolFailure("invalid_argument","Install requires an existing absolute .app path") }
            command=["install",udid,path]
        case "launch","terminate","uninstall": command=[operation,udid,try SimulatorModel.bundleID(a.string("bundleID",limit:255))]
        case "open_url":
            let value = try a.string("url",limit:8192)
            guard let url = URL(string:value), let scheme = url.scheme, !scheme.isEmpty, !value.contains("\n") else { throw ToolFailure("invalid_argument","Explicit URL with scheme required") }
            command=["openurl",udid,value]
        case "screenshot":
            let path = store.root.appendingPathComponent("simulator-\(UUID().uuidString.lowercased()).png")
            _ = try await simctl(["io",udid,"screenshot","--type=png",path.path]); _ = chmod(path.path,0o600)
            let data = try Data(contentsOf:path)
            guard let image = NSImage(data:data), let pixels=image.cgImage(forProposedRect:nil,context:nil,hints:nil), pixels.width>0, pixels.height>0 else { throw ToolFailure("invalid_media","Simulator screenshot is not a valid image") }
            result["status"]="simulator_screenshot";result["path"]=path.path;result["width"]=pixels.width;result["height"]=pixels.height
            if try a.bool("ocr") {
                result["text"]=try await Capture.ocr(pixels,languages:a.strings("languages"),timeoutMilliseconds:30000)
                result["coordinateSystem"]="image pixels, top-left origin"
            }
        case "record":
            let duration = try a.number("durationSeconds",default:3,range:1...10)
            let path = store.root.appendingPathComponent("simulator-\(UUID().uuidString.lowercased()).mov")
            let p=Process();p.executableURL=URL(fileURLWithPath:"/usr/bin/xcrun");p.arguments=["simctl","io",udid,"recordVideo","--codec=h264",path.path]
            p.standardOutput=FileHandle.nullDevice;p.standardError=FileHandle.nullDevice;p.standardInput=FileHandle.nullDevice
            try p.run()
            let pid=p.processIdentifier, start=ProcessIdentity.startID(pid:p.processIdentifier)
            func signalOwned(_ signal: Int32) { if p.isRunning, let start, ProcessIdentity.startID(pid:pid)==start { _=kill(pid,signal) } }
            var interrupted=false
            do { try await Task.sleep(nanoseconds:UInt64(duration*1e9)) } catch { interrupted=true }
            signalOwned(SIGINT)
            // Finalize even when the enclosing task is cancelled; bounded owned-child cleanup.
            let finish = Task.detached { @MainActor in
                let deadline=Date().addingTimeInterval(5)
                while p.isRunning && Date()<deadline {try? await Task.sleep(nanoseconds:50_000_000)}
                if p.isRunning {signalOwned(SIGTERM)}
            }; await finish.value
            guard !p.isRunning, p.terminationStatus == 0, !interrupted else { throw ToolFailure("simulator_record_incomplete","Recording was interrupted or did not finalize: \(path.path)") }
            _=chmod(path.path,0o600)
            result["recording"] = try await Recording.inspect(path,store:store,frames:2);result["status"]="simulator_recorded"
        case "observe":
            let pid=Int32(try a.integer("pid",range:1...Int(Int32.max))), start=try a.string("processStartID",limit:64)
            guard NSRunningApplication(processIdentifier:pid)?.bundleIdentifier == "com.apple.iphonesimulator" else { throw ToolFailure("simulator_window_mismatch","Target PID must be Simulator.app") }
            let o = try await observe(pid:pid,processStartID:start,windowID:UInt32(a.integer("windowID",range:1...Int(UInt32.max))),screenshot:false,
                                      maxNodes:a.integer("maxNodes",default:500,range:1...1000),maxDepth:a.integer("maxDepth",default:20,range:1...30))
            guard let name=row["name"] as? String, inventory.filter({$0["name"] as? String == name}).count==1,
                  o.windowTitle.hasPrefix(name + " – ") || o.windowTitle == name || o.windowTitle.hasPrefix(name + " - ") else {
                throw ToolFailure("ambiguous_simulator_window","Window title does not uniquely identify the device; no fallback to another Simulator window")
            }
            let groups=o.nodes.filter{$0.subrole=="iOSContentGroup"}
            guard groups.count==1, let group=groups.first else {throw ToolFailure("simulator_content_unavailable","Exact window exposes no unique iOSContentGroup; no whole-app fallback")}
            let nodes=o.nodes.filter{$0.path.starts(with:group.path)}
            var page: [[String:Any]]=[], bytes=2
            for node in nodes.prefix(200) {
                let value=UIAnalysisModel.object(node), data=try jsonData(UIAnalysisModel.object(node))
                if bytes+data.count>384000 {break};page.append(value);bytes+=data.count+1
            }
            result["status"]="simulator_ui_analyzed";result["scope"]="selected_device_ios_content";result["nodes"]=page
            result["coverage"]=o.coverage;result["totalCollectedNodes"]=nodes.count;result["returnedCount"]=page.count;result["readOnly"]=true
            result["hasMore"]=page.count<nodes.count;result["absenceEstablished"]=false
        case "probe_input","input":
            if operation == "input", try !a.bool("privateAPI") {throw ToolFailure("private_api_disabled","Simulator input requires privateAPI=true on every call")}
            let developer=try await CommandRunner.run(executable:URL(fileURLWithPath:"/usr/bin/xcode-select"),arguments:["-p"],timeoutMilliseconds:3000,maxOutputBytes:8192)
            guard developer.exitCode == 0 else {throw ToolFailure("xcode_unavailable","Select a full Xcode installation")}
            var request=a.values
            request["developerDir"]=developer.stdout.trimmingCharacters(in:.whitespacesAndNewlines);request["bootPID"]=boot.pid;request["bootStartID"]=boot.start
            request["operation"]=operation == "probe_input" ? "probe" : try a.string("gesture",limit:32)
            let helper=URL(fileURLWithPath:CommandLine.arguments[0]).resolvingSymlinksInPath().deletingLastPathComponent().appendingPathComponent("macpilot-simulator-hid")
            let output=try await CommandRunner.run(executable:helper,arguments:[],standardInput:String(data:jsonData(request),encoding:.utf8),timeoutMilliseconds:12000,maxOutputBytes:16384)
            guard let data=output.stdout.data(using:.utf8), let response=try JSONSerialization.jsonObject(with:data) as? [String:Any] else {throw ToolFailure("private_driver_failed","Private driver exited without a valid receipt; inspect guest before retry")}
            guard output.exitCode == 0 else {throw ToolFailure(response["code"] as? String ?? "private_driver_failed",response["message"] as? String ?? "Delivery uncertain")}
            result.merge(response){_,new in new}
        default: break
        }
        if !command.isEmpty {result["command"]=try await simctl(command).object;result["status"]="simulator_\(operation)_completed"}
        _ = try await simulatorCurrent(udid,deviceIdentity:identity)
        if operation != "shutdown" {
            let after=try await simulatorBoot(udid)
            guard after.pid==boot.pid,after.start==boot.start else {throw ToolFailure("stale_simulator_boot","Boot changed during operation; reconcile before retry")}
        }
        return result
    }
}
