import XCTest
@testable import JevComputerUse

final class AXFreshnessTests:XCTestCase {
    func testCheckboxSelectionChangesDuringDecisionRejectInput()throws {
        let snapshot=Node(id:"owned",role:"AXCheckBox",title:"Include",value:"0",enabled:true,actions:["AXPress"],frame:nil,selected:false,checked:false)
        XCTAssertNoThrow(try validateAXDiscreteState(snapshot,enabled:true,selected:false,checked:false,focused:false))
        XCTAssertThrowsError(try validateAXDiscreteState(snapshot,enabled:true,selected:false,checked:true,focused:false))
        XCTAssertThrowsError(try validateAXDiscreteState(snapshot,enabled:true,selected:true,checked:false,focused:false))
        XCTAssertThrowsError(try validateAXDiscreteState(snapshot,enabled:true,selected:nil,checked:false,focused:false))
        XCTAssertThrowsError(try validateAXDiscreteState(snapshot,enabled:false,selected:false,checked:false,focused:false))
    }
    func testFlattenedNativeParentDoesNotHideTraversalGroupRename()throws {
        let group=Node(id:"group",role:"AXGroup",title:"Right controls",value:"",enabled:true,actions:[],frame:nil)
        XCTAssertNoThrow(try validateAXContextLabel(group,role:"AXGroup",title:"Right controls",subrole:"",enabled:true))
        XCTAssertThrowsError(try validateAXContextLabel(group,role:"AXGroup",title:"Left controls",subrole:"",enabled:true))
        XCTAssertThrowsError(try validateAXContextLabel(group,role:"AXGroup",title:"Right controls",subrole:"AXSecureTextField",enabled:true))
    }
}
