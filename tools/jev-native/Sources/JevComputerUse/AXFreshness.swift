import Foundation

func validateAXDiscreteState(_ expected:Node, enabled:Bool?, selected:Bool?, checked:Bool?, focused:Bool?) throws {
    guard (enabled ?? true)==expected.enabled else { throw Failure("AX enabled state changed; reobserve") }
    if let before=expected.selected { guard selected==before else { throw Failure("AX selected state changed; reobserve") } }
    if let before=expected.checked { guard checked==before else { throw Failure("AX checked state changed; reobserve") } }
    if let focused { guard focused==expected.focused else { throw Failure("AX focused state changed; reobserve") } }
}

func validateAXContextLabel(_ expected:Node, role:String, title:String, subrole:String, enabled:Bool?) throws {
    guard role==expected.role, String(title.prefix(300))==expected.title, subrole != "AXSecureTextField", (enabled ?? true)==expected.enabled else { throw Failure("Observed AX ancestor context changed; reobserve") }
}
