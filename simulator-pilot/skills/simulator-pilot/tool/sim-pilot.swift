// sim-pilot: KakaoTalk 앱의 시뮬레이터 실행·로그와 테스트 사진 넣기. Xcode(xcrun simctl, swiftc)만 쓴다.
//
// 빌드: swiftc -O sim-pilot.swift -o ~/.local/bin/sim-pilot
//
//   sim-pilot devices                                   부팅된 시뮬레이터 (JSON)
//   sim-pilot schemes --udid U [--project-root DIR]     스킴별 설치·빌드 상태 (JSON)
//   sim-pilot launch --udid U --scheme S [--build | --reinstall]
//                                                       필요하면 빌드·설치하고 앱을 다시 실행
//   sim-pilot logs --udid U --scheme S [--filter K] [--seconds N] [--debug]
//                                                       os_log 스트림 (앱은 그대로 둔다)
//   sim-pilot console --udid U --scheme S [--filter K] [--seconds N]
//                                                       앱을 다시 실행하고 stdout·stderr를 본다 (끝나면 앱 종료)
//   sim-pilot claim --udid U [--note 하는 일] [--force]  이 세션이 이 기기를 쓴다고 기록 (다른 세션이 쓰는 중이면 거절)
//   sim-pilot release --udid U [--force]                기록을 지운다
//   sim-pilot status                                    부팅된 기기마다 켜진 화면·방향과 사용 기록 (JSON, mac-cu 메뉴 막대와 같은 내용)
//   sim-pilot claims                                    기기별 사용 기록 (JSON, 꺼진 기기·끝난 세션은 지운다)
//   sim-pilot caps --udid U                             이 기기에서 되는 기기 동작(L1) 표 (capabilities와 화면 수로)
//   sim-pilot photos --udid U [--count N] [--width W] [--height H] [--seed S] [--grayscale] [--blur 1-10] [--yes]
//                                                       picsum.photos 사진을 사진 앱에 넣는다
//
// --scheme 대신 --bundle <번들 ID>로 다른 앱을 지정할 수 있다. Real 스킴(com.kakao.talk)은 --allow-real이 있어야 한다.

import Foundation

let version = "1.4.0"

let schemes: [(name: String, bundle: String)] = [
    ("Inhouse(iTeam)-Debug", "com.kakao.iPart.Talk"),
    ("Sandbox(iTeam)", "com.kakao.iPart.sandbox.Talk"),
    ("Real", "com.kakao.talk"),
    ("Alpha(iTeam)", "com.kakao.iPart.alpha.Talk"),
    ("Beta(CI)", "com.kakao.iPart.beta.Talk"),
]
let realBundle = "com.kakao.talk"

// MARK: - 공통

struct Failure: Error { let message: String }

func fail(_ message: String) -> Never {
    FileHandle.standardError.write(("sim-pilot: " + message + "\n").data(using: .utf8)!)
    exit(1)
}

func printJSON(_ object: Any) {
    let data = try! JSONSerialization.data(withJSONObject: object, options: [.prettyPrinted, .sortedKeys, .withoutEscapingSlashes])
    print(String(data: data, encoding: .utf8)!)
}

@discardableResult
func run(_ arguments: [String], directory: String? = nil, environment: [String: String] = [:]) -> (status: Int32, output: String, error: String) {
    let process = Process()
    process.executableURL = URL(fileURLWithPath: "/usr/bin/xcrun")
    process.arguments = arguments
    if let directory { process.currentDirectoryURL = URL(fileURLWithPath: directory) }
    if !environment.isEmpty { process.environment = ProcessInfo.processInfo.environment.merging(environment) { $1 } }
    let out = Pipe(), err = Pipe()
    process.standardOutput = out
    process.standardError = err
    do { try process.run() } catch { return (127, "", "\(error)") }
    let outData = out.fileHandleForReading.readDataToEndOfFile()
    let errData = err.fileHandleForReading.readDataToEndOfFile()
    process.waitUntilExit()
    return (process.terminationStatus, String(decoding: outData, as: UTF8.self), String(decoding: errData, as: UTF8.self))
}

/// 인자: --key value, --flag
struct Options {
    var values: [String: String] = [:]
    var flags: Set<String> = []

    init(_ arguments: ArraySlice<String>, flags known: Set<String>) {
        var rest = arguments.makeIterator()
        while let argument = rest.next() {
            guard argument.hasPrefix("--") else { fail("알 수 없는 인자: \(argument)") }
            let key = String(argument.dropFirst(2))
            if known.contains(key) { flags.insert(key); continue }
            guard let value = rest.next() else { fail("\(argument)에 값이 필요합니다.") }
            values[key] = value
        }
    }

    func require(_ key: String) -> String {
        guard let value = values[key], !value.isEmpty else { fail("--\(key)가 필요합니다.") }
        return value
    }

    func int(_ key: String, default value: Int) -> Int {
        guard let text = values[key] else { return value }
        guard let number = Int(text) else { fail("--\(key)는 정수여야 합니다: \(text)") }
        return number
    }
}

// MARK: - 시뮬레이터

struct Device { let udid: String; let name: String; let runtime: String }

func bootedDevices() -> [Device] {
    let result = run(["simctl", "list", "devices", "booted", "-j"])
    guard result.status == 0, let json = try? JSONSerialization.jsonObject(with: Data(result.output.utf8)) as? [String: Any],
          let byRuntime = json["devices"] as? [String: [[String: Any]]]
    else { fail("simctl이 시뮬레이터 목록을 주지 않았습니다: \(result.error)") }
    var devices: [Device] = []
    for (runtime, list) in byRuntime {
        let label = runtime.components(separatedBy: "SimRuntime.").last?.replacingOccurrences(of: "-", with: ".")
            .replacingOccurrences(of: "iOS.", with: "iOS ") ?? runtime
        for device in list where device["state"] as? String == "Booted" {
            devices.append(Device(udid: device["udid"] as? String ?? "", name: device["name"] as? String ?? "", runtime: label))
        }
    }
    return devices.sorted { $0.name < $1.name }
}

func bootedDevice(_ udid: String) -> Device {
    guard let device = bootedDevices().first(where: { $0.udid.caseInsensitiveCompare(udid) == .orderedSame }) else {
        fail("\(udid)는 부팅된 시뮬레이터가 아닙니다. sim-pilot devices로 확인하세요.")
    }
    return device
}

func isInstalled(_ udid: String, _ bundle: String) -> Bool {
    run(["simctl", "get_app_container", udid, bundle]).status == 0
}

/// DerivedData에서 그 스킴의 가장 최근 시뮬레이터 빌드. 앱 이름은 스킴마다 달라서(SandboxTalk.app 등) 번들 ID로 찾는다.
/// root 레포 사본에서 만든 빌드만 본다(다른 작업 사본·워크트리의 빌드를 설치하지 않게).
func builtApp(_ scheme: String, bundle: String, root: String) -> String? {
    let fm = FileManager.default
    let derived = fm.homeDirectoryForCurrentUser.appendingPathComponent("Library/Developer/Xcode/DerivedData")
    let projects = (try? fm.contentsOfDirectory(atPath: derived.path)) ?? []
    let rootPath = URL(fileURLWithPath: root).standardizedFileURL.resolvingSymlinksInPath().path
    var newest: (path: String, date: Date)?
    for project in projects where project.hasPrefix("Talk-") {
        guard let data = try? Data(contentsOf: derived.appendingPathComponent("\(project)/info.plist")),
              let info = try? PropertyListSerialization.propertyList(from: data, format: nil) as? [String: Any],
              let workspace = info["WorkspacePath"] as? String,
              URL(fileURLWithPath: workspace).standardizedFileURL.resolvingSymlinksInPath().path.hasPrefix(rootPath + "/")
        else { continue }
        let products = derived.appendingPathComponent("\(project)/Build/Products/\(scheme)-iphonesimulator")
        for name in (try? fm.contentsOfDirectory(atPath: products.path)) ?? [] where name.hasSuffix(".app") {
            let app = products.appendingPathComponent(name)
            guard let data = try? Data(contentsOf: app.appendingPathComponent("Info.plist")),
                  let info = try? PropertyListSerialization.propertyList(from: data, format: nil) as? [String: Any],
                  info["CFBundleIdentifier"] as? String == bundle,
                  let date = (try? fm.attributesOfItem(atPath: app.path))?[.modificationDate] as? Date
            else { continue }
            if newest == nil || date > newest!.date { newest = (app.path, date) }
        }
    }
    return newest?.path
}

/// --scheme 또는 --bundle로 정한 앱. Real은 --allow-real이 있어야 한다.
func target(_ options: Options) -> (scheme: String?, bundle: String) {
    if let bundle = options.values["bundle"] {
        if bundle == realBundle && !options.flags.contains("allow-real") { fail(realWarning) }
        return (schemes.first { $0.bundle == bundle }?.name, bundle)
    }
    let scheme = options.require("scheme")
    guard let bundle = schemes.first(where: { $0.name == scheme })?.bundle else {
        fail("알 수 없는 스킴: \(scheme). 스킴: \(schemes.map(\.name).joined(separator: ", ")). 다른 앱은 --bundle로 지정하세요.")
    }
    if bundle == realBundle && !options.flags.contains("allow-real") { fail(realWarning) }
    return (scheme, bundle)
}

let realWarning = """
    Real 스킴(com.kakao.talk)은 실서비스 앱이라 로그에 실제 계정 정보가 나올 수 있습니다. \
    사용자에게 확인을 받은 뒤 --allow-real을 붙이세요.
    """

/// 앱 실행 파일 이름(로그 스트림의 process 이름).
func executableName(_ udid: String, _ bundle: String) -> String? {
    let container = run(["simctl", "get_app_container", udid, bundle, "app"])
    guard container.status == 0 else { return nil }
    let plist = URL(fileURLWithPath: container.output.trimmingCharacters(in: .whitespacesAndNewlines)).appendingPathComponent("Info.plist")
    guard let data = try? Data(contentsOf: plist),
          let info = try? PropertyListSerialization.propertyList(from: data, format: nil) as? [String: Any]
    else { return nil }
    return info["CFBundleExecutable"] as? String
}

func projectRoot(_ options: Options) -> String {
    let root = options.values["project-root"] ?? FileManager.default.currentDirectoryPath
    guard FileManager.default.fileExists(atPath: root + "/Scripts/build.sh") else {
        fail("\(root)에 Scripts/build.sh가 없습니다. KakaoTalk 레포 루트를 --project-root로 지정하세요.")
    }
    return root
}

/// 필요하면(또는 --build면) 빌드하고, 설치돼 있지 않거나 새로 빌드했으면 설치한다.
/// --reinstall은 빌드하지 않고 DerivedData의 최신 빌드를 다시 설치한다.
func ensureInstalled(_ device: Device, scheme: String?, bundle: String, options: Options) {
    let force = options.flags.contains("build")
    if !force && !options.flags.contains("reinstall") && isInstalled(device.udid, bundle) { return }
    guard let scheme else { fail("\(bundle)이 \(device.name)에 설치돼 있지 않습니다. 스킴 앱이 아니면 직접 설치하세요.") }
    let root = projectRoot(options)
    var app = force ? nil : builtApp(scheme, bundle: bundle, root: root)
    if app == nil {
        print("[\(scheme)] ./Scripts/build.sh로 빌드합니다 (수 분 걸릴 수 있음)…")
        let build = Process()
        build.executableURL = URL(fileURLWithPath: root + "/Scripts/build.sh")
        build.arguments = [scheme]
        build.currentDirectoryURL = URL(fileURLWithPath: root)
        do { try build.run() } catch { fail("빌드를 시작하지 못했습니다: \(error)") }
        build.waitUntilExit()
        guard build.terminationStatus == 0 else { fail("빌드가 실패했습니다(종료 코드 \(build.terminationStatus)).") }
        app = builtApp(scheme, bundle: bundle, root: root)
        guard app != nil else { fail("빌드 결과물(\(scheme)-iphonesimulator, \(bundle))을 DerivedData에서 찾지 못했습니다.") }
    }
    print("[\(scheme)] \(device.name)에 설치합니다…")
    let install = run(["simctl", "install", device.udid, app!])
    guard install.status == 0 else { fail("설치가 실패했습니다: \(install.error)") }
}

// MARK: - 스트림

/// 줄 단위로 읽어 filter가 들어간 줄만 출력하고, seconds가 지나면 끝낸다.
func stream(_ arguments: [String], filter: String?, seconds: Int, environment: [String: String] = [:], onEnd: () -> Void = {}) {
    let process = Process()
    process.executableURL = URL(fileURLWithPath: "/usr/bin/xcrun")
    process.arguments = arguments
    if !environment.isEmpty { process.environment = ProcessInfo.processInfo.environment.merging(environment) { $1 } }
    let pipe = Pipe()
    process.standardOutput = pipe
    process.standardError = pipe
    var buffer = Data()
    let lock = NSLock()
    pipe.fileHandleForReading.readabilityHandler = { handle in
        let chunk = handle.availableData
        lock.lock(); defer { lock.unlock() }
        buffer.append(chunk)
        while let newline = buffer.firstIndex(of: 0x0A) {
            let line = String(decoding: buffer[buffer.startIndex..<newline], as: UTF8.self)
            buffer.removeSubrange(buffer.startIndex...newline)
            if line.hasPrefix("getpwuid_r did not find") { continue }  // log stream이 시뮬레이터에서 늘 내는 잡음
            if let filter, !line.localizedCaseInsensitiveContains(filter) { continue }
            print(line)
            fflush(stdout)
        }
    }
    signal(SIGINT, SIG_IGN)
    let interrupt = DispatchSource.makeSignalSource(signal: SIGINT)
    interrupt.setEventHandler { process.terminate() }
    interrupt.resume()
    do { try process.run() } catch { fail("\(arguments.joined(separator: " ")) 실행 실패: \(error)") }
    if seconds > 0 {
        DispatchQueue.global().asyncAfter(deadline: .now() + .seconds(seconds)) { if process.isRunning { process.terminate() } }
    }
    process.waitUntilExit()
    pipe.fileHandleForReading.readabilityHandler = nil
    onEnd()
}

// MARK: - 명령

func devicesCommand() {
    let claims = loadClaims(), mine = currentSession()
    printJSON(bootedDevices().map { device -> [String: Any] in
        var row: [String: Any] = ["udid": device.udid, "name": device.name, "runtime": device.runtime]
        if let claim = claims[device.udid] { row["claimed_by"] = claim.note.isEmpty ? claim.by : claim.note; row["mine"] = claim.by == mine.by }
        return row
    })
}

// MARK: - 기기 사용 기록
//
// 같은 Mac의 여러 세션(Claude Code·Codex)이 시뮬레이터를 함께 쓴다. 한 세션이 기기를 끄거나 접거나 설정을 바꾸면
// 다른 세션의 작업이 깨지므로, 쓰는 세션이 기록을 남기고 다른 세션은 바꾸기 전에 그 기록을 본다.

struct Claim: Codable { let by: String; let note: String; let pid: Int32; let since: String }

let claimsURL = FileManager.default.homeDirectoryForCurrentUser
    .appendingPathComponent("Library/Application Support/sim-pilot/claims.json")

/// The session that runs this command: Claude Code's session id and process, else the parent process.
func currentSession() -> (by: String, pid: Int32) {
    let env = ProcessInfo.processInfo.environment
    let by = env["CLAUDE_CODE_HOST_SESSION_ID"] ?? env["CLAUDE_CODE_SESSION_ID"] ?? env["CODEX_SESSION_ID"] ?? "pid \(getppid())"
    return (by, Int32(env["CLAUDE_PID"] ?? "") ?? getppid())
}

/// The claims of booted devices whose session still runs. Others are dropped.
func loadClaims() -> [String: Claim] {
    guard let data = try? Data(contentsOf: claimsURL), let all = try? JSONDecoder().decode([String: Claim].self, from: data) else { return [:] }
    let booted = Set(bootedDevices().map(\.udid))
    let live = all.filter { booted.contains($0.key) && (kill($0.value.pid, 0) == 0 || errno == EPERM) }
    if live.count != all.count { saveClaims(live) }
    return live
}

func saveClaims(_ claims: [String: Claim]) {
    try? FileManager.default.createDirectory(at: claimsURL.deletingLastPathComponent(), withIntermediateDirectories: true)
    let encoder = JSONEncoder(); encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
    try? encoder.encode(claims).write(to: claimsURL, options: .atomic)
}

func claimCommand(_ options: Options) {
    let device = bootedDevice(options.require("udid"))
    var claims = loadClaims()
    let me = currentSession()
    if let other = claims[device.udid], other.by != me.by, !options.flags.contains("force") {
        fail("\(device.name)는 다른 세션이 쓰는 중입니다(\(other.note.isEmpty ? other.by : other.note), \(other.since)부터). 사용자에게 묻고, 함께 써도 된다고 하면 --force를 붙입니다.")
    }
    let since = ISO8601DateFormatter().string(from: Date())
    claims[device.udid] = Claim(by: me.by, note: options.values["note"] ?? "", pid: me.pid, since: since)
    saveClaims(claims)
    print("\(device.name)를 이 세션이 쓴다고 기록했습니다. 끝나면 sim-pilot release --udid \(device.udid)")
}

func releaseCommand(_ options: Options) {
    let udid = options.require("udid")
    var claims = loadClaims()
    guard let claim = claims[udid] else { print("기록이 없습니다."); return }
    guard claim.by == currentSession().by || options.flags.contains("force") else {
        fail("다른 세션의 기록입니다(\(claim.note.isEmpty ? claim.by : claim.note)). 지우려면 사용자에게 묻고 --force를 붙입니다.")
    }
    claims[udid] = nil
    saveClaims(claims)
    print("기록을 지웠습니다.")
}

/// devicectl's JSON result for one device (`info details`, `info displays`), nil when it fails.
func devicectlResult(_ udid: String, _ arguments: [String]) -> [String: Any]? {
    let file = FileManager.default.temporaryDirectory.appendingPathComponent("sim-pilot-\(UUID().uuidString).json")
    defer { try? FileManager.default.removeItem(at: file) }
    guard run(["devicectl", "device"] + arguments + ["--device", udid, "--quiet", "--json-output", file.path]).status == 0,
          let data = try? Data(contentsOf: file) else { return nil }
    return (try? JSONSerialization.jsonObject(with: data) as? [String: Any])?["result"] as? [String: Any]
}

func statusCommand() {
    let claims = loadClaims(), me = currentSession().by
    printJSON(bootedDevices().map { device -> [String: Any] in
        let screens = (devicectlResult(device.udid, ["info", "displays"])?["displays"] as? [[String: Any]] ?? [])
            .filter { ($0["type"] as? [String: Any])?["integrated"] != nil }
        let on = screens.count > 1 ? screens.first { $0["active"] as? Bool == true } : screens.first
        var row: [String: Any] = ["udid": device.udid, "name": device.name, "runtime": device.runtime, "screens": screens.count]
        if let on { row["screen"] = on["name"] as? String ?? "?"; row["orientation"] = on["currentOrientation"] as? String ?? "" }
        if let claim = claims[device.udid] {
            row["claimed_by"] = claim.note.isEmpty ? claim.by : claim.note; row["since"] = claim.since; row["mine"] = claim.by == me
        }
        return row
    })
}

func claimsCommand() {
    let me = currentSession().by
    let names = Dictionary(bootedDevices().map { ($0.udid, $0.name) }, uniquingKeysWith: { a, _ in a })
    printJSON(loadClaims().sorted { $0.key < $1.key }.map {
        ["udid": $0.key, "name": names[$0.key] ?? "?", "by": $0.value.by, "note": $0.value.note, "since": $0.value.since, "mine": $0.value.by == me] as [String: Any]
    })
}

/// The device actions this simulator supports, from devicectl's capabilities (the authority on what the device can do)
/// and its number of built-in screens (a foldable has two: hinge and its own turn).
func capsCommand(_ options: Options) {
    let device = bootedDevice(options.require("udid"))
    func json(_ arguments: [String]) -> [String: Any]? {
        let file = FileManager.default.temporaryDirectory.appendingPathComponent("sim-pilot-\(UUID().uuidString).json")
        defer { try? FileManager.default.removeItem(at: file) }
        guard run(["devicectl", "device"] + arguments + ["--device", device.udid, "--quiet", "--json-output", file.path]).status == 0,
              let data = try? Data(contentsOf: file) else { return nil }
        return (try? JSONSerialization.jsonObject(with: data) as? [String: Any])?["result"] as? [String: Any]
    }
    guard let details = json(["info", "details"]), let list = details["capabilities"] as? [[String: Any]] else {
        fail("devicectl이 \(device.name)의 기능 목록을 주지 않았습니다.")
    }
    let caps = Set(list.compactMap { ($0["featureIdentifier"] as? String)?.replacingOccurrences(of: "com.apple.coredevice.feature.", with: "") })
    let screens = (json(["info", "displays"])?["displays"] as? [[String: Any]] ?? []).filter { ($0["type"] as? [String: Any])?["integrated"] != nil }.count
    let foldable = screens > 1
    // (동작, 필요한 capability, 방법)
    let rows: [(String, Bool, String)] = [
        ("Face ID 등록·인증", caps.contains("simulatefaceid"), "devicectl device settings biometrics / simulate biometrics"),
        ("Touch ID 등록·인증", caps.contains("simulatetouchid"), "devicectl device settings biometrics / simulate biometrics"),
        ("회전", caps.contains("remote.devicecontrol.orientation"), foldable ? "mac-cu simulator rotate (orientation set은 적용 안 됨)" : "devicectl device orientation set 또는 mac-cu simulator rotate"),
        ("접기·펴기(힌지)", foldable && caps.contains("remote.hid.vendordefined"), "mac-cu simulator hinge"),
        ("힌지 각도 읽기", foldable && caps.contains("monitormotion"), "mac-cu simulator hinge (값 없이)"),
        ("탭·스와이프", caps.contains("remote.hid.digitizer"), "mac-cu simulator tap / swipe"),
        ("1~3손가락 제스처 전송", caps.contains("remote.universalhidservice"), "mac-cu 1.21.0+ simulator gesture (서비스 존재; 앱 인식은 별도 확인)"),
        ("키 입력", caps.contains("remote.hid.keyboard"), "mac-cu simulator type / key"),
        ("하드웨어 버튼", caps.contains("remote.hid.button"), "mac-cu simulator button"),
        ("상태 막대", caps.contains("simulateStatusBar"), "devicectl device simulate statusBar"),
        ("위치·경로", caps.contains("simulatelocation"), "devicectl device simulate location"),
        ("스크린샷", caps.contains("capturescreenshot"), "devicectl device capture screenshot" + (foldable ? " --display-unique-id" : "")),
        ("화면 녹화", caps.contains("screenrecording"), "devicectl device capture screen-record"),
        ("메모리 경고", caps.contains("sendmemorywarningtoprocess"), "devicectl device process sendMemoryWarning"),
        ("손쉬운 사용(모양)", caps.contains("customizeappearancesettings"), "devicectl device settings appearance"),
        ("VoiceOver", caps.contains("voiceover"), "devicectl device settings voiceover"),
        ("StandBy", caps.contains("standby"), "devicectl device info standby"),
        ("앱 크기 조절", caps.contains("resizableappmanagement"), "devicectl device appResize"),
        ("Watch 페어링", caps.contains("companiondevicepairing"), "devicectl device pairings"),
    ]
    // iPad Pro 13-inch (M5): devicectl info displays answers "No displays found".
    print("\(device.name) (\(device.runtime)): capability \(caps.count)개, " + (screens == 0 ? "화면 정보 없음(devicectl info displays가 비어 있음)" : "화면 \(screens)개"))
    for (name, ok, how) in rows { print("\(ok ? "O" : "-") \(name)\(ok ? ": \(how)" : "")") }
}

func schemesCommand(_ options: Options) {
    let device = bootedDevice(options.require("udid"))
    let root = options.values["project-root"] ?? FileManager.default.currentDirectoryPath  // 상태 보기는 레포 밖에서도 실패하지 않게
    printJSON(schemes.map { scheme -> [String: String] in
        let status = isInstalled(device.udid, scheme.bundle) ? "installed" : (builtApp(scheme.name, bundle: scheme.bundle, root: root) != nil ? "built" : "needs_build")
        return ["scheme": scheme.name, "bundle_id": scheme.bundle, "status": status]
    })
}

func relaunch(_ device: Device, _ bundle: String) {
    run(["simctl", "terminate", device.udid, bundle])
    let launch = run(["simctl", "launch", device.udid, bundle])
    guard launch.status == 0 else { fail("실행이 실패했습니다: \(launch.error)") }
    print("[\(device.name)] \(bundle) 실행: \(launch.output.trimmingCharacters(in: .whitespacesAndNewlines))")
}

func launchCommand(_ options: Options) {
    let device = bootedDevice(options.require("udid"))
    let (scheme, bundle) = target(options)
    ensureInstalled(device, scheme: scheme, bundle: bundle, options: options)
    relaunch(device, bundle)
}

func logsCommand(_ options: Options) {
    let device = bootedDevice(options.require("udid"))
    let (_, bundle) = target(options)
    guard let process = executableName(device.udid, bundle) else { fail("\(bundle)이 \(device.name)에 설치돼 있지 않습니다. 먼저 launch 하세요.") }
    let seconds = options.int("seconds", default: 30)
    print("[\(device.name)] \(process) os_log \(seconds > 0 ? "\(seconds)초" : "중단할 때까지")\(options.values["filter"].map { ", 필터 \"\($0)\"" } ?? "")")
    print("---")
    var arguments = ["simctl", "spawn", device.udid, "log", "stream", "--style", "compact",
                     "--predicate", "process == \"\(process)\""]
    if options.flags.contains("debug") { arguments += ["--level", "debug"] }
    stream(arguments, filter: options.values["filter"], seconds: seconds)
}

func consoleCommand(_ options: Options) {
    let device = bootedDevice(options.require("udid"))
    let (scheme, bundle) = target(options)
    ensureInstalled(device, scheme: scheme, bundle: bundle, options: options)
    let seconds = options.int("seconds", default: 30)
    run(["simctl", "terminate", device.udid, bundle])
    print("[\(device.name)] \(bundle) 다시 실행, 콘솔 \(seconds > 0 ? "\(seconds)초" : "중단할 때까지") (끝나면 앱을 종료합니다)")
    print("---")
    stream(["simctl", "launch", "--console-pty", device.udid, bundle], filter: options.values["filter"], seconds: seconds,
           environment: ["SIMCTL_CHILD_OS_ACTIVITY_DT_MODE": "YES"]) {
        run(["simctl", "terminate", device.udid, bundle])
    }
}

func photosCommand(_ options: Options) {
    let device = bootedDevice(options.require("udid"))
    let count = options.int("count", default: 10)
    let width = options.int("width", default: 320), height = options.int("height", default: 320)
    guard (1...2000).contains(count) else { fail("--count는 1~2000입니다.") }
    guard (1...5000).contains(width), (1...5000).contains(height) else { fail("--width·--height는 1~5000입니다.") }
    if count > 100 && !options.flags.contains("yes") {
        fail("\(count)장은 많습니다. 사용자에게 확인을 받은 뒤 --yes를 붙이세요.")
    }
    let blur = options.values["blur"].map { Int($0) ?? -1 }
    if let blur, !(1...10).contains(blur) { fail("--blur는 1~10입니다.") }
    let seed = options.values["seed"]

    var common: [URLQueryItem] = []
    if options.flags.contains("grayscale") { common.append(URLQueryItem(name: "grayscale", value: nil)) }
    if let blur { common.append(URLQueryItem(name: "blur", value: String(blur))) }
    /// 시드가 있으면 시드-번호로 늘 같은 사진, 없으면 random 값으로 서로 다른 사진.
    func url(_ index: Int) -> URL {
        var components = URLComponents(string: "https://picsum.photos")!
        var items = common
        if let seed {
            let name = count == 1 ? seed : "\(seed)-\(index)"
            components.percentEncodedPath = "/seed/\(name.addingPercentEncoding(withAllowedCharacters: .alphanumerics) ?? "x")/\(width)/\(height)"
        } else {
            components.path = "/\(width)/\(height)"
            items.append(URLQueryItem(name: "random", value: String(index)))
        }
        components.queryItems = items.isEmpty ? nil : items
        return components.url!
    }

    let folder = FileManager.default.temporaryDirectory.appendingPathComponent("sim-pilot-photos-\(UUID().uuidString)")
    try? FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
    defer { try? FileManager.default.removeItem(at: folder) }

    print("[\(device.name)] picsum.photos에서 \(width)×\(height) 사진 \(count)장을 받습니다…")
    let session = URLSession(configuration: .ephemeral)
    let group = DispatchGroup()
    let limit = DispatchSemaphore(value: 8)
    let lock = NSLock()
    var files: [URL] = [], failures = 0
    for index in 0..<count {
        let source = url(index)
        limit.wait()
        group.enter()
        session.dataTask(with: source) { data, response, _ in
            defer { limit.signal(); group.leave() }
            guard let data, (response as? HTTPURLResponse)?.statusCode == 200, data.count > 100 else {
                lock.lock(); failures += 1; lock.unlock(); return
            }
            let file = folder.appendingPathComponent(String(format: "picsum-%05d.jpg", index))
            do { try data.write(to: file) } catch { lock.lock(); failures += 1; lock.unlock(); return }
            lock.lock(); files.append(file); lock.unlock()
        }.resume()
    }
    group.wait()
    guard !files.isEmpty else { fail("사진을 하나도 받지 못했습니다(네트워크 확인).") }
    files.sort { $0.path < $1.path }
    var added = 0
    for start in stride(from: 0, to: files.count, by: 50) {
        let batch = Array(files[start..<min(start + 50, files.count)])
        let result = run(["simctl", "addmedia", device.udid] + batch.map(\.path))
        guard result.status == 0 else { fail("addmedia 실패(\(added)장 넣은 뒤): \(result.error)") }
        added += batch.count
    }
    print("\(device.name) 사진 앱에 \(added)장을 넣었습니다\(failures > 0 ? " (다운로드 실패 \(failures)장)" : "").")
}

// MARK: - 진입점

let arguments = CommandLine.arguments
guard arguments.count > 1 else {
    print("""
        sim-pilot \(version)
          devices | schemes | launch | logs | console | photos | caps | status | claim | release | claims | --version
        자세한 사용법은 simulator-pilot 스킬 문서를 보세요.
        """)
    exit(0)
}
let flags: Set<String> = ["build", "reinstall", "debug", "grayscale", "yes", "allow-real", "force"]
let options = Options(arguments.dropFirst(2), flags: flags)
switch arguments[1] {
case "--version", "version": print(version)
case "devices": devicesCommand()
case "schemes": schemesCommand(options)
case "launch": launchCommand(options)
case "logs": logsCommand(options)
case "console": consoleCommand(options)
case "photos": photosCommand(options)
case "caps": capsCommand(options)
case "claim": claimCommand(options)
case "release": releaseCommand(options)
case "claims": claimsCommand()
case "status": statusCommand()
default: fail("알 수 없는 명령: \(arguments[1])")
}
