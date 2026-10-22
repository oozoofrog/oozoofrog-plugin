import AppKit

final class WrappingTextView: NSTextView {
    override func layout() {
        super.layout()
        guard let scroll = enclosingScrollView, let container = textContainer else { return }
        let width = max(1,scroll.contentSize.width - 2 * textContainerInset.width)
        container.widthTracksTextView = false
        if container.containerSize.width != width {
            container.containerSize = NSSize(width:width,height:CGFloat.greatestFiniteMagnitude)
        }
    }
}

@MainActor final class GoalWindowController: NSWindowController, NSWindowDelegate, NSTextViewDelegate {
    let session = RunSession()
    private let goal = WrappingTextView(usingTextLayoutManager:false)
    private let workspace = SpatialWorkspace(frame:.zero)
    private var presentation = RunPresentationState()
    private var preview: PreviewController?
    private var picker: AppPickerWindow?
    private var followUp: FollowUpWindow?
    private var connection: ConnectionWindow?
    private var currentDirectory: String?
    private let options: GUIOptions
    private var showPreview: Bool
    private var previewMenu: NSMenuItem?
    private var connectionMenu: NSMenuItem?

    init(options: GUIOptions) {
        self.options = options; showPreview = options.showPreview
        let window = NSWindow(contentRect:NSRect(x:0,y:0,width:1100,height:820),styleMask:[.titled,.closable,.miniaturizable,.resizable],backing:.buffered,defer:false)
        super.init(window:window)
        window.title = "JEV"; window.minSize = NSSize(width:760,height:700); window.isReleasedWhenClosed = false; window.delegate = self
        NSApp.setActivationPolicy(.regular)
        if let icon = Bundle.main.url(forResource:"JevNative",withExtension:"icns").flatMap({ NSImage(contentsOf:$0) }) { NSApp.applicationIconImage = icon }
        let content = window.contentView!
        workspace.translatesAutoresizingMaskIntoConstraints = false; content.addSubview(workspace)
        let scroll = NSScrollView(); scroll.borderType = .bezelBorder; scroll.hasVerticalScroller = true; scroll.autohidesScrollers = true
        scroll.translatesAutoresizingMaskIntoConstraints = false; content.addSubview(scroll)
        goal.minSize = NSSize(width:0,height:110); goal.maxSize = NSSize(width:CGFloat.greatestFiniteMagnitude,height:CGFloat.greatestFiniteMagnitude)
        goal.isRichText = false; goal.isAutomaticQuoteSubstitutionEnabled = false; goal.isAutomaticTextReplacementEnabled = false; goal.font = .systemFont(ofSize:16)
        goal.textContainerInset = NSSize(width:14,height:14); goal.isVerticallyResizable = true; goal.isHorizontallyResizable = false; goal.autoresizingMask = [.width]
        goal.textContainer?.widthTracksTextView = true; goal.textContainer?.lineBreakMode = .byWordWrapping; goal.setAccessibilityLabel("작업 요청"); goal.delegate = self
        scroll.documentView = goal; goal.string = options.goal
        NSLayoutConstraint.activate([workspace.leadingAnchor.constraint(equalTo:content.leadingAnchor),workspace.trailingAnchor.constraint(equalTo:content.trailingAnchor),workspace.topAnchor.constraint(equalTo:content.topAnchor),workspace.bottomAnchor.constraint(equalTo:scroll.topAnchor,constant:-10),scroll.leadingAnchor.constraint(equalTo:content.leadingAnchor,constant:24),scroll.trailingAnchor.constraint(equalTo:content.trailingAnchor,constant:-24),scroll.bottomAnchor.constraint(equalTo:content.bottomAnchor,constant:-20),scroll.heightAnchor.constraint(equalToConstant:120)])
        workspace.onCommand = { [weak self] command in
            guard let self else { return }
            switch command { case "run": self.runTask(); case "pause": self.togglePause(); case "stop": self.requestStop(); case "report": self.showReport(); default: break }
        }
        session.onChange = { [weak self] in self?.refresh() }
        installMenu(); refresh(); window.center()
    }
    required init?(coder:NSCoder) { fatalError("init(coder:) is unavailable") }
    @objc func show() { window?.makeKeyAndOrderFront(nil); NSApp.activate(ignoringOtherApps:true); if !session.active { window?.makeFirstResponder(goal) } }
    private func installMenu() {
        let main = NSMenu(), appMenu = NSMenu(), edit = NSMenu(), taskMenu = NSMenu(), windowMenu = NSMenu()
        func submenu(_ title:String,_ menu:NSMenu) { let item = NSMenuItem(title:title,action:nil,keyEquivalent:""); item.submenu = menu; main.addItem(item) }
        let settings = NSMenuItem(title:"연결 설정…",action:#selector(showConnection),keyEquivalent:","); settings.target = self; appMenu.addItem(settings); connectionMenu = settings
        appMenu.addItem(.separator()); appMenu.addItem(withTitle:"JEV Native 종료",action:#selector(NSApplication.terminate(_:)),keyEquivalent:"q")
        for (title,action,key) in [("실행 취소","undo:","z"),("다시 실행","redo:","Z"),("오려두기","cut:","x"),("복사","copy:","c"),("붙여넣기","paste:","v"),("모두 선택","selectAll:","a")] { edit.addItem(withTitle:title,action:NSSelectorFromString(action),keyEquivalent:key) }
        let show = NSMenuItem(title:"작업 창 보기",action:#selector(show),keyEquivalent:"1"); show.target = self; windowMenu.addItem(show)
        let previewItem = NSMenuItem(title:"작업 미리보기",action:#selector(togglePreview),keyEquivalent:""); previewItem.target = self; previewItem.state = showPreview ? .on : .off; windowMenu.addItem(previewItem); previewMenu = previewItem
        for (title,action,key) in [("요청하기",#selector(runTask),"\r"),("일시정지 / 계속하기",#selector(togglePause),"p"),("중지",#selector(requestStop),"."),("작업 기록 보기",#selector(showReport),"r")] {
            let item = NSMenuItem(title:title,action:action,keyEquivalent:key); item.target = self; taskMenu.addItem(item)
        }
        submenu("JEV Native",appMenu); submenu("작업",taskMenu); submenu("편집",edit); submenu("윈도우",windowMenu); NSApp.mainMenu = main
    }
    func textDidChange(_ notification:Notification) { refreshControls() }
    private func refreshControls() {
        goal.isEditable = !session.active; connectionMenu?.isEnabled = !session.active
        workspace.execution(active:session.active,pauseRequested:session.control?.pauseRequested ?? false,paused:session.control?.isPaused ?? false)
    }
    private func refresh() {
        refreshControls()
        if !session.active { preview?.finish(); AppDelegate.completePendingTermination() }
    }
    @objc private func togglePause() {
        guard let control = session.control else { return }
        if control.pauseRequested { control.resume() } else { control.requestPause() }
    }
    @objc private func runTask() {
        guard !session.active else { return }
        guard !goal.string.trimmingCharacters(in:.whitespacesAndNewlines).isEmpty else { workspace.message("맡길 작업을 입력해 주세요."); return }
        let original = goal.string
        guard original.utf16.count <= 6000 else { workspace.message("요청이 길어요. 더 짧게 나누어 주세요. 입력 한도는 UTF-16 코드 단위 6,000개입니다."); return }
        let directory = FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library/Application Support/JEV Native/Runs/" + UUID().uuidString).path
        currentDirectory = directory
        do {
            let runner = NaturalTaskRunner(showVirtualPointer:options.showVirtualPointer), model = options.model
            try session.start(status:{ _ in },presentation:{ [weak self] event in
                guard let self else { return }; self.presentation.apply(event); self.workspace.update(self.presentation)
            },request:original) { [weak self] control in
                guard let self else { throw CancellationError() }
                return try await runner.run(request:original,directory:directory,model:model,control:control,
                    followUp:{ [weak self] question in guard let self else { return nil }; return await self.ask(question) },
                    chooseApps:self.options.chooseApps,
                    selection:{ [weak self] apps in guard let self else { return nil }; return await self.chooseApps(apps) },
                    makePreview:{ [weak self] in
                        guard let self, self.showPreview else { return nil }
                        if self.preview == nil { self.preview = PreviewController() }; self.preview?.onStop = { [weak self] in self?.requestStop() }; self.preview?.beginRun(); AppDelegate.preview = self.preview; return self.preview
                    })
            }
        } catch { workspace.message(UserStatus.result("error")) }
    }
    private func ask(_ question:RequestQuestion) async -> RequestAnswer? {
        guard let window, session.control?.isCancelled == false else { return nil }
        return await withCheckedContinuation { continuation in
            let sheet = FollowUpWindow(question:question) { [weak self] answer in self?.followUp = nil; continuation.resume(returning:answer) }
            followUp = sheet; if let child = sheet.window { window.beginSheet(child) }
        }
    }
    private func chooseApps(_ apps:[AppCandidate]) async -> [String]? {
        guard let window, session.control?.isCancelled == false else { return nil }
        return await withCheckedContinuation { continuation in
            let picker = AppPickerWindow(apps:apps) { [weak self] ids in self?.picker = nil; continuation.resume(returning:ids) }
            self.picker = picker; if let sheet = picker.window { window.beginSheet(sheet) }
        }
    }
    @objc private func togglePreview() { showPreview.toggle(); previewMenu?.state = showPreview ? .on : .off; if showPreview { preview?.show() } else { preview?.hide() } }
    @objc func requestStop() { session.stop(); picker?.cancel(); followUp?.cancel() }
    func windowShouldClose(_ sender:NSWindow) -> Bool { if session.active { requestStop() }; sender.orderOut(nil); return false }
    @objc private func showReport() { if let directory = currentDirectory, FileManager.default.fileExists(atPath:directory + "/report.json") { NSWorkspace.shared.activateFileViewerSelecting([URL(fileURLWithPath:directory + "/report.json")]) } }
    @objc private func showConnection() { guard !session.active else { return }; if connection == nil { connection = ConnectionWindow() }; connection?.show() }
}
