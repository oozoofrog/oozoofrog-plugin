# SwiftUI 설정에 연결

앱의 실제 값으로 `feedback@example.com`, 이름, 버전·빌드와 공개키를 교체한다. 이 예제는 진단에 개인 정보 없는 예시 사건 한 개만 넣는다. 실제 로그를 수집했다는 뜻이 아니다. 공개키가 없으면 Debug에서도 일반 메일만 제공한다.

```swift
import AppFeedback
import SwiftUI
import UIKit

@main
struct ExampleApp: App {
    var body: some Scene {
        WindowGroup { NavigationStack { SettingsView() } }
    }
}

struct SettingsView: View {
    @StateObject private var feedback = makeFeedback()

    var body: some View {
        FeedbackHost(session: feedback) {
            Form {
                Section("Settings") { Text("Example app") }
                FeedbackSection(session: feedback)
            }
        }
        .navigationTitle("Settings")
    }

    @MainActor
    private static func makeFeedback() -> FeedbackSession {
        let bundle = Bundle.main
        let info = FeedbackAppInfo(
            name: "Example App",
            version: bundle.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "Unknown",
            build: bundle.object(forInfoDictionaryKey: "CFBundleVersion") as? String ?? "Unknown",
            system: "\(UIDevice.current.systemName) \(UIDevice.current.systemVersion)",
            device: UIDevice.current.model)
        var labels = FeedbackLabels()
        labels.title = "Feedback"
        let session = FeedbackSession(recipient: "feedback@example.com", appInfo: info, labels: labels) { info in
            FeedbackContent(subject: "\(info.name) feedback", body: FeedbackContent.standard(info).body)
        }
        #if DEBUG
        // Supply the generated public key through this app's Debug-only configuration.
        if let publicKey = bundle.object(forInfoDictionaryKey: "FeedbackPublicKey") as? String,
           !publicKey.isEmpty {
            session.diagnostics = FeedbackDiagnostics(
                publicKeyBase64: publicKey,
                disclosure: "Attaches an encrypted sample app event and your check answers. No personal data.") {
                    try JSONSerialization.data(withJSONObject: ["event": "settingsOpened"])
                }
            session.checklist = [FeedbackCheck(id: "settings", title: "Settings opens")]
        }
        #endif
        return session
    }
}
```

기존 앱에는 `@main`을 추가하지 않고 설정 View와 생성 함수만 가져온다. 공개키는 Debug 전용 Swift 설정으로 직접 주입해도 된다. Info.plist 방식을 쓰면 키 값이 Release에 복사되지 않도록 구성별 파일/빌드 설정을 분리한다. 지역화는 앱의 문자열 카탈로그와 `FeedbackLabels`의 각 문구에 연결한다.

`FeedbackDiagnostics`와 체크리스트는 Debug에만 존재하므로 Release가 이를 참조하면 컴파일이 실패한다. 설정 화면을 다시 만들 때마다 세션을 만들지 않는다. `FeedbackHost`와 `@StateObject`의 identity를 유지한다. UIKit 앱은 이 View를 오래 유지되는 `UIHostingController`에 넣고 컨트롤러를 행 갱신 때마다 교체하지 않는다.

`FeedbackSession.prepare(canSendMail:)`와 `finish(_:)`는 커스텀 UI용 상태 API다. SwiftUI 제공 화면을 사용할 때 직접 호출할 필요는 없다. 수집 중 중복 요청을 무시하며 실패 시 진단 없이 메일을 만든다. provider는 취소에 반응하고 외부 기기 요청에는 앱에 맞는 timeout을 적용해야 한다. 앱이 소유한 진단 데이터의 보존 기간과 개인정보 제거는 앱의 책임이다.
