import Foundation

struct GUIOptions {
    var goal = ""
    var chooseApps = false
    var showPreview = true
    var showVirtualPointer = false
    var model: String?
    init(arguments: [String]) throws {
        guard arguments.first == "--gui" else { throw Failure("Use jev-native --gui to open the task window.") }
        var index = 1, auto = false
        while index < arguments.count {
            let flag = arguments[index]
            switch flag {
            case "--simple": chooseApps = true
            case "--auto": auto = true
            case "--no-preview": showPreview = false
            case "--show-virtual-cursor": showVirtualPointer = true
            case "--goal", "--codex-model":
                index += 1
                guard index < arguments.count, !arguments[index].hasPrefix("--") else { throw Failure("Missing value for \(flag)") }
                if flag == "--goal" { goal = arguments[index] } else { model = arguments[index] }
            default: throw Failure("Unsupported GUI option: \(flag). Use --gui [--goal TEXT] [--auto | --simple] [--no-preview] [--codex-model MODEL]. Use run --apps for an explicit CLI app scope.")
            }
            index += 1
        }
        guard !(auto && chooseApps) else { throw Failure("Use either --auto or --simple with --gui.") }
    }
}
