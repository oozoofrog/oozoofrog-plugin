import AppKit

@MainActor final class ConnectionWindow: NSWindowController {
    private let message = NSTextField(wrappingLabelWithString:"")
    private let connect = NSButton(title:"복사한 연결 키로 연결",target:nil,action:nil)
    init() {
        let window = NSWindow(contentRect:NSRect(x:0,y:0,width:500,height:230),styleMask:[.titled,.closable],backing:.buffered,defer:false)
        super.init(window:window); window.title = "연결 설정"; window.isReleasedWhenClosed = false
        let content = window.contentView!
        let heading = NSTextField(labelWithString:"작업 도우미 연결"); heading.font = .systemFont(ofSize:18,weight:.semibold)
        let detail = NSTextField(wrappingLabelWithString:"연결 키는 이 Mac에 저장합니다. 기존 연결 키는 바꾸지 않습니다."); detail.textColor = .secondaryLabelColor
        let manage = NSButton(title:"연결 키 관리 열기",target:self,action:#selector(openKeys)); manage.bezelStyle = .rounded
        connect.target = self; connect.action = #selector(importKey); connect.bezelStyle = .rounded
        let stack = NSStackView(views:[heading,message,detail,connect,manage]); stack.orientation = .vertical; stack.alignment = .leading; stack.spacing = 12; stack.translatesAutoresizingMaskIntoConstraints = false; content.addSubview(stack)
        NSLayoutConstraint.activate([stack.leadingAnchor.constraint(equalTo:content.leadingAnchor,constant:24),stack.trailingAnchor.constraint(equalTo:content.trailingAnchor,constant:-24),stack.topAnchor.constraint(equalTo:content.topAnchor,constant:24)])
        message.widthAnchor.constraint(equalTo:stack.widthAnchor).isActive = true; detail.widthAnchor.constraint(equalTo:stack.widthAnchor).isActive = true
        refresh(); window.center()
    }
    required init?(coder:NSCoder) { fatalError("init(coder:) is unavailable") }
    func show() { refresh(); showWindow(nil); window?.makeKeyAndOrderFront(nil) }
    private func refresh() { let ready = (try? credential()) != nil; message.stringValue = ready ? "연결 키가 설정되어 있어요" : "연결 키를 복사한 뒤 아래 버튼을 누르세요."; connect.isEnabled = !ready }
    @objc private func importKey() {
        do { _ = try setupCredential(importPasteboard:true); refresh() }
        catch { message.stringValue = "연결하지 못했어요. 연결 키를 확인해 주세요. 기존 키가 있으면 직접 확인해야 합니다." }
    }
    @objc private func openKeys() { if !CredentialSetupIO.native().openKeys() { message.stringValue = "연결 관리 페이지를 열지 못했어요." } }
}
