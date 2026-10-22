import AppKit

@MainActor final class FollowUpWindow: NSWindowController, NSWindowDelegate {
    private let question: RequestQuestion
    private let completion: (RequestAnswer?) -> Void
    private let options = NSPopUpButton()
    private let resume = NSButton(title:"이어서 진행",target:nil,action:nil)
    private let text = WrappingTextView(usingTextLayoutManager:false)
    private let validation = NSTextField(wrappingLabelWithString:"")
    private var finished = false

    init(question: RequestQuestion, completion: @escaping (RequestAnswer?) -> Void) {
        self.question = question; self.completion = completion
        let window = NSWindow(contentRect:NSRect(x:0,y:0,width:540,height:question.allowsText ? 340 : 210),styleMask:[.titled],backing:.buffered,defer:false)
        super.init(window:window); window.title = "한 가지만 알려 주세요"; window.delegate = self
        let content = window.contentView!
        let prompt = NSTextField(wrappingLabelWithString:question.prompt); prompt.font = .systemFont(ofSize:16,weight:.semibold); prompt.setAccessibilityLabel("추가 질문")
        let stack = NSStackView(); stack.orientation = .vertical; stack.alignment = .leading; stack.spacing = 16
        stack.translatesAutoresizingMaskIntoConstraints = false; content.addSubview(stack)
        NSLayoutConstraint.activate([stack.leadingAnchor.constraint(equalTo:content.leadingAnchor,constant:24),stack.trailingAnchor.constraint(equalTo:content.trailingAnchor,constant:-24),stack.topAnchor.constraint(equalTo:content.topAnchor,constant:24),stack.bottomAnchor.constraint(equalTo:content.bottomAnchor,constant:-24)])
        stack.addArrangedSubview(prompt); prompt.widthAnchor.constraint(equalTo:stack.widthAnchor).isActive = true
        if !question.options.isEmpty {
            options.addItem(withTitle:"선택해 주세요"); options.addItems(withTitles:question.options.map(\.title)); options.target=self; options.action=#selector(selectionChanged);  options.setAccessibilityLabel("답변 선택")
            stack.addArrangedSubview(options); options.widthAnchor.constraint(equalTo:stack.widthAnchor).isActive = true
        }
        if question.allowsText {
            let scroll = NSScrollView(); scroll.borderType = .bezelBorder; scroll.hasVerticalScroller = true
            text.isRichText = false; text.isAutomaticQuoteSubstitutionEnabled = false; text.isAutomaticTextReplacementEnabled = false; text.font = .systemFont(ofSize:14)
            text.textContainerInset = NSSize(width:10,height:10); text.isVerticallyResizable = true; text.isHorizontallyResizable = false; text.autoresizingMask = [.width]; text.textContainer?.widthTracksTextView = true; text.setAccessibilityLabel("추가 답변")
            scroll.documentView = text; stack.addArrangedSubview(scroll)
            NSLayoutConstraint.activate([scroll.widthAnchor.constraint(equalTo:stack.widthAnchor),scroll.heightAnchor.constraint(greaterThanOrEqualToConstant:120)])
        } else { let spacer = NSView(); stack.addArrangedSubview(spacer); spacer.heightAnchor.constraint(greaterThanOrEqualToConstant:0).isActive = true }
        validation.isHidden = true; validation.textColor = .systemRed; validation.font = .systemFont(ofSize:12); validation.setAccessibilityLabel("답변 안내"); stack.addArrangedSubview(validation); validation.widthAnchor.constraint(equalTo:stack.widthAnchor).isActive = true
        let buttons = NSStackView(); buttons.orientation = .horizontal; buttons.spacing = 8
        let cancel = NSButton(title:"취소",target:self,action:#selector(cancel)); cancel.bezelStyle = .rounded; cancel.keyEquivalent = "\u{1b}"
        resume.target=self; resume.action=#selector(submit); resume.bezelStyle = .rounded; resume.keyEquivalent = "\r"
        buttons.addArrangedSubview(cancel); buttons.addArrangedSubview(resume); stack.addArrangedSubview(buttons)
        if question.allowsText { window.initialFirstResponder = text }
    }
    required init?(coder:NSCoder) { fatalError("init(coder:) is unavailable") }
    private func finish(_ answer: RequestAnswer?) {
        guard !finished else { return }; finished = true
        if let window, let parent = window.sheetParent { parent.endSheet(window) }; window?.orderOut(nil); completion(answer)
    }
    @objc func cancel() { finish(nil) }
    @objc private func selectionChanged() { validation.isHidden = true }
    @objc private func submit() {
        let answer: RequestAnswer
        if question.allowsText { answer = RequestAnswer(question:question,text:text.string) }
        else {
            guard question.options.indices.contains(options.indexOfSelectedItem - 1) else { validation.isHidden=false; validation.stringValue="선택지에서 작업할 대상을 선택해 주세요."; return }
            answer = RequestAnswer(question:question,option:question.options[options.indexOfSelectedItem - 1])
        }
        do { try answer.validate() } catch { validation.isHidden = false; validation.stringValue = text.string.trimmingCharacters(in:.whitespacesAndNewlines).isEmpty ? "답변을 입력해 주세요." : "답변이 길어요. 입력 한도는 UTF-16 코드 단위 6,000개입니다. 원문을 나누거나 더 짧은 범위를 요청해 주세요."; return }
        finish(answer)
    }
    func windowShouldClose(_ sender:NSWindow) -> Bool { cancel(); return false }
}
