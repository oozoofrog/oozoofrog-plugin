import XCTest
@testable import MacPilotCore

final class BrowserTests: XCTestCase {
    @MainActor func testBothBrowserBackendsShareMutationValidation() throws {
        for browser in ["safari","chrome"] {
            let invalid:[[String:Any]] = [
                ["operation":"fill","tabID":1,"observation":"id","node":"0"],
                ["operation":"verify","tabID":1,"observation":"id","node":"0","equals":"a","contains":"a"],
                ["operation":"observe","tabID":true],
                ["operation":"open","url":"javascript:alert(1)"],
                ["operation":"download","url":"https://example.invalid","filename":"../private.txt"]
            ]
            for var value in invalid {
                value["browser"]=browser
                XCTAssertThrowsError(try BrowserBridge.validatedPayload(Arguments(value),operation:value["operation"] as! String,preserveForeground:true))
            }
            XCTAssertThrowsError(try BrowserBridge.validatedPayload(Arguments(["operation":"select","tabID":1,"activate":true,"browser":browser]),operation:"select",preserveForeground:true))
            let safe = try BrowserBridge.validatedPayload(Arguments(["operation":"fill","browser":browser,"tabID":1,"observation":"id","node":"0","text":"한글 😀"]),operation:"fill",preserveForeground:true)
            XCTAssertEqual(safe["text"] as? String,"한글 😀")
        }
    }
}
