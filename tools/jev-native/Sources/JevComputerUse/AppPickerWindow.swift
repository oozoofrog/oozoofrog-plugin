import AppKit

@MainActor final class AppPickerWindow: NSWindowController, NSTableViewDataSource, NSTableViewDelegate, NSWindowDelegate {
    private let available = NSTableView(), ordered = NSTableView()
    private var apps: [AppCandidate]
    private var catalogue: [AppCandidate]
    private let search = NSSearchField()
    private var selected: [AppCandidate] = []
    private let use = NSButton(title: "Use Selected Apps", target: nil, action: nil)
    private var completion: (([String]?) -> Void)?

    init(apps: [AppCandidate], completion: @escaping ([String]?) -> Void) {
        self.apps = apps.sorted { $0.name.localizedStandardCompare($1.name) == .orderedAscending }
        self.catalogue = self.apps
        self.completion = completion
        let window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 610, height: 570), styleMask: [.titled, .closable], backing: .buffered, defer: false)
        super.init(window: window); window.title = "Choose Target Apps"; window.delegate = self; window.isReleasedWhenClosed = false
        let view = NSView(frame: window.contentView!.bounds); window.contentView = view
        func label(_ text: String, _ y: CGFloat) { let field = NSTextField(labelWithString: text); field.frame = NSRect(x: 18, y: y, width: 570, height: 20); view.addSubview(field) }
        func table(_ table: NSTableView, _ frame: NSRect, _ identifier: String) {
            let column = NSTableColumn(identifier: NSUserInterfaceItemIdentifier("app")); column.width = frame.width - 20; table.addTableColumn(column)
            table.headerView = nil; table.rowHeight = 25; table.dataSource = self; table.delegate = self; table.allowsMultipleSelection = table === available
            table.setAccessibilityLabel(identifier)
            let scroll = NSScrollView(frame: frame); scroll.documentView = table; scroll.hasVerticalScroller = true; scroll.borderType = .bezelBorder; view.addSubview(scroll)
        }
        label("Available apps", 533)
        search.frame = NSRect(x:240,y:532,width:352,height:26); search.placeholderString = "Search by name or bundle ID"
        search.setAccessibilityLabel("Search Apps"); search.target = self; search.action = #selector(filterApps); search.sendsSearchStringImmediately = true; view.addSubview(search)
        table(available, NSRect(x:18,y:290,width:574,height:238), "Available Apps")
        label("Workflow order — first app starts the task", 230)
        table(ordered, NSRect(x:18,y:76,width:574,height:150), "Selected Apps in Workflow Order")
        func button(_ title: String, _ x: CGFloat, _ y: CGFloat, _ width: CGFloat, _ action: Selector) {
            let button = NSButton(title:title,target:self,action:action); button.bezelStyle = .rounded; button.frame = NSRect(x:x,y:y,width:width,height:30); view.addSubview(button)
        }
        button("Add",18,251,80,#selector(addApps)); button("Remove",108,251,90,#selector(removeApp))
        button("Move Up",340,251,118,#selector(moveSelectedUp)); button("Move Down",464,251,128,#selector(moveSelectedDown))
        button("Cancel",18,20,95,#selector(cancel))
        use.target = self; use.action = #selector(confirm); use.bezelStyle = .rounded; use.frame = NSRect(x:392,y:20,width:200,height:32); use.isEnabled = false; view.addSubview(use)
        available.target = self; available.doubleAction = #selector(addApps)
    }
    required init?(coder: NSCoder) { fatalError("init(coder:) is unavailable") }
    func numberOfRows(in tableView: NSTableView) -> Int { tableView === available ? apps.count : selected.count }
    func tableView(_ tableView: NSTableView, viewFor tableColumn: NSTableColumn?, row: Int) -> NSView? {
        let app = tableView === available ? apps[row] : selected[row]
        let prefix = tableView === available ? "" : "\(row + 1). "
        let label = NSTextField(labelWithString: prefix + app.name + " · " + app.bundle)
        label.lineBreakMode = .byTruncatingMiddle; label.setAccessibilityLabel(prefix + app.name + " " + app.bundle)
        return label
    }
    @objc private func filterApps() {
        let query = search.stringValue.trimmingCharacters(in:.whitespacesAndNewlines)
        apps = query.isEmpty ? catalogue : catalogue.filter { $0.name.localizedStandardContains(query) || $0.bundle.localizedStandardContains(query) }
        available.deselectAll(nil); available.reloadData()
    }
    @objc private func addApps() {
        for index in available.selectedRowIndexes where !selected.contains(where: { $0.bundle == apps[index].bundle }) { selected.append(apps[index]) }
        ordered.reloadData(); use.isEnabled = !selected.isEmpty
    }
    @objc private func removeApp() {
        let row = ordered.selectedRow; guard selected.indices.contains(row) else { return }
        selected.remove(at:row); ordered.reloadData(); use.isEnabled = !selected.isEmpty
    }
    private func move(_ offset: Int) {
        let row = ordered.selectedRow, destination = ordered.selectedRow + offset
        guard selected.indices.contains(row), selected.indices.contains(destination) else { return }
        selected.swapAt(row,destination); ordered.reloadData(); ordered.selectRowIndexes(IndexSet(integer:destination),byExtendingSelection:false)
    }
    @objc private func moveSelectedUp() { move(-1) }
    @objc private func moveSelectedDown() { move(1) }
    @objc private func confirm() { guard !selected.isEmpty else { return }; finish(selected.map(\.bundle)) }
    @objc func cancel() { finish(nil) }
    func windowShouldClose(_ sender: NSWindow) -> Bool { cancel(); return false }
    private func finish(_ value: [String]?) {
        guard let completion else { return }; self.completion = nil
        if let window, let parent = window.sheetParent { parent.endSheet(window) }; window?.orderOut(nil)
        completion(value)
    }
}
