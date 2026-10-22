import Foundation

extension Action {
    func presentationLabel(observation:Observation) -> String {
        let title = target.flatMap { id in observation.nodes.first { $0.id == id }?.title } ?? ""
        switch kind {
        case "press": return title.isEmpty ? "선택한 버튼 누르기" : "버튼 누르기 · " + title
        case "focus": return title.isEmpty ? "입력란 선택" : "입력란 선택 · " + title
        case "type": return "텍스트 입력 · \((text ?? "").count)자"
        case "key": return "키 입력 · " + ((modifiers ?? []) + [key ?? ""]).joined(separator:" + ")
        case "launch": return "대상 앱 실행"
        case "activate": return "대상 앱 활성화"
        case "openFile": return "요청한 파일 열기"
        case "selectWindow": return "창 선택 · " + (observation.windows.first { $0.id == windowID }?.title ?? "선택한 창")
        case "scroll": return "대상 창 스크롤"
        case "click": return "대상 창 클릭"
        case "doubleClick": return "대상 창 두 번 클릭"
        case "rightClick": return "대상 창 보조 클릭"
        case "drag": return "대상 창에서 드래그"
        case "move": return "작업 포인터 이동"
        case "raise": return "선택한 창 앞으로 가져오기"
        case "wait": return "화면 응답 대기"
        default: return "대상 앱에서 동작"
        }
    }
}

/// Presentation facts come from the runner. No animation can advance execution or assert completion.
struct RunPresentationEvent: Equatable {
    enum Fact: Equatable {
        case request(String), phase(String), target(String), source(String, String)
        case observation(String), action(String), input(String), result(String), outcome(String), pause(Bool)
    }
    let runID: UUID
    let sequence: Int
    let fact: Fact
}

struct RunPresentationState: Equatable {
    var runID: UUID?
    private var retiredRuns = Set<UUID>()
    var sequence = -1
    var request = ""
    var phase = "요청을 기다리고 있어요"
    var target = ""
    var source = ""
    var sourceTitle = "원문"
    var result = ""
    var outcome: String?
    var paused = false
    var history: [String] = []
    var historyFocus: [Double] = []
    var inputs = 0
    var hasDocumentProvenance: Bool { !source.isEmpty && !result.isEmpty }

    mutating func apply(_ event: RunPresentationEvent) {
        if case .request = event.fact, event.runID != runID {
            guard !retiredRuns.contains(event.runID) else { return }
            var retired = retiredRuns; if let runID { retired.insert(runID) }
            self = RunPresentationState(); runID = event.runID; retiredRuns = retired
        }
        guard event.runID == runID, event.sequence > sequence else { return }
        sequence = event.sequence
        switch event.fact {
        case .request(let text): request = text; record("요청 접수",focus:0)
        case .phase(let text):
            phase = UserStatus.progress(text)
            if history.last != phase { record(phase,focus:text == "source" ? -1 : 0) }
        case .target(let text): target = text
        case .source(let text, let title): source = text; sourceTitle = title; record("원문 확인 · " + title,focus:-1)
        case .observation(let text): record("관찰 · " + text,focus:0)
        case .action(let text): record("선택 · " + text,focus:0)
        case .input(let text): inputs += 1; record("실행 · " + text,focus:1)
        case .result(let text): if result != text { result = text; if !text.isEmpty { record("결과 수신",focus:1) } }
        case .outcome(let text): outcome = text; phase = UserStatus.result(text); record(phase,focus:result.isEmpty ? 0 : 1)
        case .pause(let value): paused = value
        }
    }
    private mutating func record(_ text:String,focus:Double) { history.append(text); historyFocus.append(focus) }
}

/// One clock for the entire world. Pausing preserves camera, content and transfer positions.
struct SpatialMotion {
    var time = 0.0
    var focus = 0.0
    var target = 0.0
    var velocity = 0.0
    var frozen = false
    mutating func advance(_ delta: Double, reducedMotion: Bool) {
        guard !frozen else { return }
        let dt = max(0, min(delta, 0.05)); time += dt
        if reducedMotion { focus = target; velocity = 0; return }
        velocity += ((target-focus)*28 - velocity*10)*dt
        focus += velocity*dt
        if abs(target-focus) < 0.0001 && abs(velocity) < 0.0001 { focus = target; velocity = 0 }
    }
}
