import StoreKit
import SwiftUI

@main
struct ClipsApp: App {
    var body: some Scene {
        WindowGroup { ClipView() }
    }
}

struct ClipView: View {
    @Environment(\.requestReview) private var requestReview
    @Environment(\.scenePhase) private var phase
    @State private var draft = ""
    @State private var savedClip: String?
    @State private var library = ClipLibrary()

    var body: some View {
        VStack {
            TextField("Clip text", text: $draft)
                .onChange(of: draft) { text in
                    if !text.isEmpty { savedClip = nil }
                }
            Button("Save clip") {
                guard library.save(draft) else { return }
                savedClip = draft
                draft = ""
            }
            List(library.clips, id: \.self) { Text($0) }
        }
        .padding()
        .onChange(of: phase) { if $0 != .active { savedClip = nil } }
        .task(id: savedClip) {
            guard let clip = savedClip,
                  let version = Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String else { return }
            await library.requestAfterSave(version: version, isReady: {
                phase == .active && draft.isEmpty && savedClip == clip
            }) { requestReview() }
        }
    }
}
