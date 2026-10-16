import AppKit
import CryptoKit

private struct SafariTabHandle:Codable {
    var tabID:Int,windowID:Int,index:Int,pid:Int32
    var processStartID:String,url:String,title:String
    var object:[String:Any]{(try? JSONSerialization.jsonObject(with:JSONEncoder().encode(self))) as? [String:Any] ?? [:]}
}

@MainActor public enum SafariBridge {
    private static func source() throws -> String {
        guard var root=Bundle.main.executableURL else{throw ToolFailure("browser_assets_missing","Cannot locate MacPilot browser assets")}
        for _ in 0..<5 { root.deleteLastPathComponent() }
        let configured=ProcessInfo.processInfo.environment["MACPILOT_SKILL_DIR"].map{URL(fileURLWithPath:$0)}
        let path=(configured ?? root).appendingPathComponent("browser/extension/content.js")
        guard let data=try? Data(contentsOf:path),data.count<131072,let source=String(data:data,encoding:.utf8) else{
            throw ToolFailure("browser_assets_missing","Invoke the skill launcher or install browser/ beside bin/")
        }
        return source
    }
    private static func jxa(_ body:String,request:[String:Any],timeout:Int) async throws -> [String:Any] {
        let script="""
        function run() {
          const request=\(jsonString(request));
          const Safari=Application('com.apple.Safari');
          function fail(code,message){throw Object.assign(new Error(message),{code:code});}
          try { return JSON.stringify({ok:true,result:(function(){\(body)})()}); }
          catch(error){return JSON.stringify({ok:false,error:{code:error.code||'safari_error',message:String(error.message||error)}});}
        }
        """
        let output=try await CommandRunner.run(executable:URL(fileURLWithPath:"/usr/bin/osascript"),arguments:["-l","JavaScript"],standardInput:script,timeoutMilliseconds:timeout,maxOutputBytes:262144)
        guard output.exitCode==0,!output.stdoutTruncated,let data=output.stdout.trimmingCharacters(in:.whitespacesAndNewlines).data(using:.utf8),
              let value=try? JSONSerialization.jsonObject(with:data) as? [String:Any] else{
            throw ToolFailure("safari_error","Safari Apple Events failed: \(String(output.stderr.prefix(2048)))")
        }
        if let error=value["error"] as? [String:Any]{
            let message=String((error["message"] as? String ?? "Safari operation failed").prefix(2048))
            let denied=message.localizedCaseInsensitiveContains("not authorized") || message.contains("-1743") || message.contains("JavaScript from Apple Events")
            throw ToolFailure(denied ? "permission_required" : (error["code"] as? String ?? "safari_error"),message)
        }
        return value["result"] as? [String:Any] ?? [:]
    }
    private static let selected="""
    if(!Safari.running())fail('browser_not_running','Safari is not running');
    const windows=Safari.windows().filter(w=>w.id()===request.windowID);
    if(windows.length!==1)fail('stale_tab','Safari window changed');
    const window=windows[0],tabs=window.tabs()||[];
    if(request.index<1||request.index>tabs.length)fail('stale_tab','Safari tab index changed');
    const tab=tabs[request.index-1];
    if(tab.url()!==request.expectedURL)fail('stale_tab','Safari tab URL changed; list tabs again');
    if(tabs.filter(t=>t.url()===request.expectedURL).length!==1)fail('ambiguous_tab','Duplicate URLs make this positional target ambiguous');
    """
    private static func remember(_ raw:[String:Any],store:Store) throws -> SafariTabHandle {
        guard let app=NSRunningApplication.runningApplications(withBundleIdentifier:"com.apple.Safari").first,
              let identity=ProcessIdentity.startID(pid:app.processIdentifier),let window=raw["windowID"] as? Int,let index=raw["index"] as? Int,
              let url=raw["url"] as? String else{throw ToolFailure("safari_error","Safari returned an incomplete tab")}
        for name in try store.names(prefix:"safari-tab-") where name.hasSuffix(".json"){
            if let old=try? JSONDecoder().decode(SafariTabHandle.self,from:store.read(name)),old.windowID==window,old.index==index,old.url==url,old.processStartID==identity{return old}
        }
        let record=SafariTabHandle(tabID:Int.random(in:1...Int(Int32.max)),windowID:window,index:index,pid:app.processIdentifier,processStartID:identity,url:url,title:raw["title"] as? String ?? "")
        try store.write(JSONEncoder().encode(record),to:store.root.appendingPathComponent("safari-tab-\(record.tabID).json"))
        return record
    }
    private static func dom(_ payload:[String:Any],target:[String:Any],store:Store,timeout:Int) async throws -> [String:Any] {
        var target=target
        let frame=payload["frameID"] as? Int ?? 0
        var frameURL=""
        if frame>0 {
            guard let tab=payload["tabID"] as? Int,
                  let data=try? store.read("safari-frames-\(tab).json"),
                  let frames=try? JSONSerialization.jsonObject(with:data) as? [String:String],let url=frames[String(frame)] else{
                throw ToolFailure("missing_frame","List Safari frames again before selecting a child frame")
            }
            frameURL=url
        }
        func scoped(_ code:String) -> String {
            if frame==0 { return code }
            return """
            (()=>{const w=window.frames[\(frame-1)];if(!w)throw new Error('Frame disappeared');
            try{if(w.location.href!==\(jsonString(frameURL)))throw new Error('Frame URL changed; list frames again');}
            catch(e){throw new Error('Frame is inaccessible or changed; use host browser tools for cross-origin frames');}
            return w.eval(\(jsonString(code)));})()
            """
        }
        let token=UUID().uuidString.lowercased()
        target["inject"]=scoped(try source())
        target["script"]=scoped("""
        (()=>{const id=\(jsonString(token));globalThis.__macpilotNative=globalThis.__macpilotNative||{};
        Promise.resolve(globalThis.__macpilotBridge.dispatch(\(jsonString(payload)))).then(result=>globalThis.__macpilotNative[id]=JSON.stringify({ok:true,result}),error=>globalThis.__macpilotNative[id]=JSON.stringify({ok:false,error:{code:error.code||'safari_error',message:error.message}}));return id;})()
        """)
        _ = try await jxa(selected+"Safari.doJavaScript(request.inject,{in:tab});Safari.doJavaScript(request.script,{in:tab});return {status:'submitted'};",request:target,timeout:timeout)
        let deadline=Date().addingTimeInterval(Double(timeout)/1000)
        repeat {
            try Task.checkCancellation()
            target["script"]=scoped("(()=>{const id=\(jsonString(token));const value=globalThis.__macpilotNative?.[id]||'';if(value)delete globalThis.__macpilotNative[id];return value;})()")
            let polled=try await jxa(selected+"return {value:Safari.doJavaScript(request.script,{in:tab})};",request:target,timeout:timeout)
            if let raw=polled["value"] as? String,!raw.isEmpty,let data=raw.data(using:.utf8),let response=try? JSONSerialization.jsonObject(with:data) as? [String:Any] {
                if let error=response["error"] as? [String:Any]{throw ToolFailure(error["code"] as? String ?? "safari_error",error["message"] as? String ?? "Safari DOM command failed")}
                guard let value=response["result"] as? [String:Any] else{throw ToolFailure("safari_error","Missing Safari DOM result")}
                return value
            }
            try await Task.sleep(nanoseconds:50_000_000)
        } while Date()<deadline
        throw ToolFailure("browser_response_timeout","Safari DOM response was not received; do not repeat a mutation without reconciling its target")
    }
    public static func call(_ a:Arguments,store:Store,preserveForeground:Bool) async throws -> [String:Any] {
        let operation=try a.string("operation")
        var payload=try BrowserBridge.validatedPayload(a,operation:operation,preserveForeground:preserveForeground)
        let timeout=payload["timeoutMs"] as! Int,activate=try a.bool("activate")
        let frame=payload["frameID"] as? Int ?? 0
        if frame>0,["tabs","open","select","close","navigate","back","forward","reload","frames"].contains(operation) {
            throw ToolFailure("invalid_argument","Tab operations require frameID=0")
        }
        // ponytail: Apple Events tab references are positional. Serialize Safari
        // until a stable native tab-ID backend is needed; duplicate URLs fail closed.
        let lease=try store.lease(".safari-browser.lock");defer{withExtendedLifetime(lease){}}
        if operation=="tabs"{
            let response=try await jxa("""
            if(!Safari.running())return {tabs:[]};
            const rows=[];for(const w of Safari.windows()){const tabs=w.tabs()||[];for(let i=0;i<tabs.length&&rows.length<500;i++)rows.push({windowID:w.id(),index:i+1,url:tabs[i].url(),title:tabs[i].name()});}
            return {tabs:rows};
            """,request:[:],timeout:timeout)
            let rows=try (response["tabs"] as? [[String:Any]] ?? []).map{try remember($0,store:store).object}
            return ["status":"tabs","browser":"safari","tabs":rows,"coverage":rows.count==500 ? "partial" : "listed"]
        }
        if operation=="open"{
            let response=try await jxa("""
            if(!Safari.running()&&!request.activate)fail('foreground_required','Start Safari explicitly before background work');
            if(request.activate)Safari.activate();
            const before=Safari.windows().map(w=>w.id());
            Safari.Document({url:request.url}).make();
            const window=Safari.windows().find(w=>!before.includes(w.id()));
            if(!window)fail('ambiguous_tab','Could not identify the newly created Safari window');
            const tab=window.tabs()[0];return {windowID:window.id(),index:1,url:tab.url(),title:tab.name()};
            """,request:["url":try a.string("url",limit:8192),"activate":activate],timeout:timeout)
            let handle=try remember(response,store:store)
            return ["status":"tab_opened","browser":"safari","tabID":handle.tabID,"windowID":handle.windowID,"url":handle.url,
                    "verification":"Window created; relist tabs after navigation or redirects before DOM work"]
        }
        let tabID=try a.integer("tabID",range:1...Int(Int32.max))
        guard var handle=try? JSONDecoder().decode(SafariTabHandle.self,from:store.read("safari-tab-\(tabID).json")) else{throw ToolFailure("missing_tab","Use tabs or open to get a current Safari tab handle")}
        try ProcessIdentity.require(pid:handle.pid,expected:handle.processStartID)
        let id=UUID().uuidString.lowercased()
        var receipt:[String:Any]=["id":id,"connectionID":"safari","operation":operation,"tabID":tabID,"state":"dispatched"]
        try store.write(jsonData(receipt),to:store.root.appendingPathComponent("browser-request-\(id).json"))
        var target:[String:Any]=["windowID":handle.windowID,"index":handle.index,"expectedURL":handle.url]
        do {
            var result:[String:Any]
            switch operation {
            case "close":
                result=try await jxa(selected+"tab.close();return {status:'tab_closed'};",request:target,timeout:timeout)
                try store.remove("safari-tab-\(tabID).json")
            case "navigate":
                target["url"]=try a.string("url",limit:8192)
                result=try await jxa(selected+"tab.url=request.url;return {status:'navigation_requested',url:tab.url(),title:tab.name()};",request:target,timeout:timeout)
                handle.url=result["url"] as? String ?? handle.url;handle.title=result["title"] as? String ?? ""
                try store.write(JSONEncoder().encode(handle),to:store.root.appendingPathComponent("safari-tab-\(tabID).json"))
            case "select":
                target["activate"]=activate
                result=try await jxa(selected+"window.currentTab=tab;if(request.activate)Safari.activate();return {status:'tab_selected'};",request:target,timeout:timeout)
            case "frames":
                target["script"]="""
                JSON.stringify({frames:[{frameID:0,url:location.href,accessible:true},...Array.from(window.frames,(w,i)=>{try{return {frameID:i+1,url:w.location.href,accessible:true}}catch(e){return {frameID:i+1,accessible:false}}})],coverage:'top_and_direct_children'})
                """
                let raw=try await jxa(selected+"return {value:Safari.doJavaScript(request.script,{in:tab})};",request:target,timeout:timeout)
                guard let value=raw["value"] as? String,let data=value.data(using:.utf8),let object=try JSONSerialization.jsonObject(with:data) as? [String:Any] else{throw ToolFailure("safari_error","Missing frame list")}
                var urls:[String:String]=[:]
                for row in object["frames"] as? [[String:Any]] ?? [] { if let number=row["frameID"] as? Int,let url=row["url"] as? String { urls[String(number)]=url } }
                try store.write(jsonData(urls),to:store.root.appendingPathComponent("safari-frames-\(tabID).json"));result=object
            case "download","download_status","screenshot":
                throw ToolFailure("unsupported_action","Use connected host browser tools or native window/file tools for Safari downloads and screenshots")
            case "back","forward","reload":
                target["script"]=operation=="back" ? "history.back()" : operation=="forward" ? "history.forward()" : "location.reload()"
                result=try await jxa(selected+"Safari.doJavaScript(request.script,{in:tab});return {status:'navigation_requested',verification:'Relist tabs after navigation'};",request:target,timeout:timeout)
            case "wait":
                guard timeout<=30000 else{throw ToolFailure("invalid_argument","DOM wait is limited to the 30-second observation lifetime")}
                payload["operation"]="verify"
                let deadline=Date().addingTimeInterval(Double(timeout)/1000)
                repeat {
                    result=try await dom(payload,target:target,store:store,timeout:min(timeout,5000))
                    if result["matches"] as? Bool==true { break }
                    if Date()<deadline { try await Task.sleep(nanoseconds:100_000_000) }
                } while Date()<deadline
            case "upload":
                let path=try SystemActions.explicitFileURLs([a.string("path",limit:4096)],key:"path",mustExist:true,rejectRoot:true)[0]
                let attributes=try FileManager.default.attributesOfItem(atPath:path.path)
                let size=(attributes[.size] as? NSNumber)?.intValue ?? -1
                guard attributes[.type] as? FileAttributeType == .typeRegular,(0...33_554_432).contains(size) else{throw ToolFailure("invalid_upload","Upload requires a regular file of at most 32 MiB")}
                payload.removeValue(forKey:"path");payload["operation"]="upload_begin";payload["name"]=path.lastPathComponent;payload["size"]=size
                let begun=try await dom(payload,target:target,store:store,timeout:timeout)
                guard let upload=begun["uploadID"] as? String else{throw ToolFailure("invalid_upload","Missing upload receipt")}
                let file=try FileHandle(forReadingFrom:path);defer{try? file.close()}
                var digest=SHA256(),offset=0
                while let chunk=try file.read(upToCount:32768),!chunk.isEmpty {
                    try Task.checkCancellation();digest.update(data:chunk)
                    _ = try await dom(["operation":"upload_chunk","tabID":tabID,"frameID":frame,"uploadID":upload,"offset":offset,"data":chunk.base64EncodedString()],target:target,store:store,timeout:timeout)
                    offset+=chunk.count
                }
                result=try await dom(["operation":"upload_end","tabID":tabID,"frameID":frame,"uploadID":upload,"sha256":digest.finalize().map{String(format:"%02x",$0)}.joined()],target:target,store:store,timeout:timeout)
            default: result=try await dom(payload,target:target,store:store,timeout:timeout)
            }
            try ProcessIdentity.require(pid:handle.pid,expected:handle.processStartID)
            try store.write(jsonData(["id":id,"result":result]),to:store.root.appendingPathComponent("browser-response-\(id).json"))
            result["requestID"]=id;result["browser"]="safari";return result
        } catch {
            receipt["state"]="unconfirmed";try? store.write(jsonData(receipt),to:store.root.appendingPathComponent("browser-request-\(id).json"))
            throw ToolFailure((error as? ToolFailure)?.code ?? "safari_error","\(error.localizedDescription) [Safari requestID: \(id)]")
        }
    }
}
