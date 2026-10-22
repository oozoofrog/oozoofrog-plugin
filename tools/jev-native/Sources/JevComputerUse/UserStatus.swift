import Foundation

enum UserStatus {
    static func progress(_ phase: String) -> String {
        switch phase {
        case "intent": return "요청 내용을 확인하고 있어요"
        case "apps": return "사용할 앱을 찾고 있어요"
        case "source": return "선택한 문서의 원문을 읽고 있어요"
        case "followup": return "답변을 기다리고 있어요"
        case "vision": return "선택한 화면을 살펴보고 있어요"
        case "writing": return "요청한 글을 작성하고 있어요"
        default:
            if phase.hasPrefix("Finished: ") { return result(String(phase.dropFirst("Finished: ".count))) }
            if phase == "Starting" { return "작업을 준비하고 있어요" }
            if phase.hasPrefix("Observed") { return "작업 화면을 확인하고 있어요" }
            if phase.hasPrefix("Stopping") { return "중지하고 있어요" }
            if phase.hasPrefix("Selecting") || phase.hasPrefix("Choose") { return "사용할 앱을 확인하고 있어요" }
            if phase.hasPrefix("Running") || phase.hasPrefix("Executing") { return "앱에서 작업을 진행하고 있어요" }
            if phase == "Codex writing" || phase.contains("delegateText") { return "요청한 글을 작성하고 있어요" }
            if phase == "Codex inspecting image" || phase.contains("delegateVision") { return "선택한 화면을 살펴보고 있어요" }
            return "다음 작업을 확인하고 있어요"
        }
    }
    static func result(_ status: String) -> String {
        switch status {
        case "verified_complete": return "지정한 완료 조건을 확인했어요"
        case "jev_observed_complete": return "관찰한 상태를 기준으로 작업을 마쳤어요. 결과를 확인해 주세요."
        case "content_delivered": return "요청한 결과가 준비됐어요"
        case "cancelled", "request_cancelled": return "작업을 중지했어요"
        case "request_visual_destination_unresolved": return "화면 설명을 다른 앱에 쓰는 경로는 아직 지원하지 않아요. 작업 창에 설명해 달라고 요청해 주세요."
        case "request_unsupported": return "현재 도우미가 실행할 수 없는 요청이에요. 앱에서 할 동작이나 작성할 내용을 구체적으로 적어 주세요."
        case "source_unavailable": return "원문 전체를 읽지 못했어요. 문서를 열거나 원문을 요청에 포함해 주세요."
        case "request_unresolved", "request_needs_input": return "필요한 정보를 정하지 못했어요. 사용할 앱·문서·내용을 구체적으로 적어 주세요."
        case "uncertain", "blocked", "recovery_exhausted", "step_limit": return "다음 동작을 확실히 정하지 못해 멈췄어요. 대상이나 원하는 결과를 더 구체적으로 적어 주세요."
        default:
            if status.hasPrefix("app_selection_") { return "사용할 앱을 정하지 못했어요. 앱 이름을 포함해 다시 요청해 주세요." }
            return "작업을 진행하지 못했어요. 연결 설정과 접근 권한을 확인해 주세요. 자세한 내용은 작업 기록에서 볼 수 있어요."
        }
    }
}
