import AppKit
import CoreImage
import CoreMedia
import ScreenCaptureKit

public final class LiveCapture: NSObject, SCStreamOutput, SCStreamDelegate, @unchecked Sendable {
    private let context = CIContext(options: [.cacheIntermediates:false])
    private let outputQueue = DispatchQueue(label: "macpilot.live-capture")
    private let receive: @MainActor (CGImage) -> Void
    private let failure: @MainActor (String) -> Void
    @MainActor private var stream: SCStream?

    @MainActor public init(receive: @escaping @MainActor (CGImage) -> Void, failure: @escaping @MainActor (String) -> Void) {
        self.receive = receive; self.failure = failure
    }
    @MainActor public func start(windowID: UInt32, pid: Int32) async throws {
        guard CGPreflightScreenCaptureAccess() else { throw ToolFailure("screen_capture_denied", "Enable Screen Recording for live preview") }
        let content: SCShareableContent = try await withCallbackDeadline(
            timeoutMilliseconds: 10_000, timeoutFailure: ToolFailure("capture_timeout", "Live window discovery timed out")
        ) { finish in
            SCShareableContent.getExcludingDesktopWindows(true, onScreenWindowsOnly: false) { content, error in
                if let content { finish(.success(content)) }
                else { finish(.failure(error ?? ToolFailure("capture_failed", "No shareable content"))) }
            }
        }
        guard let window = content.windows.first(where: { $0.windowID == windowID && $0.owningApplication?.processID == pid }) else {
            throw ToolFailure("window_unavailable", "The selected window is no longer shareable")
        }
        let filter = SCContentFilter(desktopIndependentWindow: window)
        let size = filter.contentRect.size
        guard size.width > 0, size.height > 0, size.width.isFinite, size.height.isFinite else {
            throw ToolFailure("window_unavailable", "Live window geometry is invalid")
        }
        let configuration = SCStreamConfiguration()
        let scale = min(2, 1600 / max(size.width, size.height))
        configuration.width = max(1, Int(size.width * scale))
        configuration.height = max(1, Int(size.height * scale))
        configuration.minimumFrameInterval = CMTime(value: 1, timescale: 10)
        configuration.queueDepth = 3
        configuration.showsCursor = false
        configuration.capturesAudio = false
        configuration.ignoreShadowsSingleWindow = true
        let capture = SCStream(filter: filter, configuration: configuration, delegate: self)
        try capture.addStreamOutput(self, type: .screen, sampleHandlerQueue: outputQueue)
        stream = capture
        try await capture.startCapture()
    }
    @MainActor public func stop() async {
        let current = stream; stream = nil
        guard let current else{return}
        let _:Bool? = try? await withCallbackDeadline(timeoutMilliseconds:1500,
            timeoutFailure:ToolFailure("capture_stop_timeout","Capture stop acknowledgement timed out")) { finish in
            current.stopCapture { error in
                if let error{finish(.failure(error))}else{finish(.success(true))}
            }
        }
    }
    public func stream(_ stream: SCStream, didOutputSampleBuffer sampleBuffer: CMSampleBuffer, of outputType: SCStreamOutputType) {
        guard outputType == .screen, sampleBuffer.isValid,
              let attachments = CMSampleBufferGetSampleAttachmentsArray(sampleBuffer, createIfNecessary: false) as? [[SCStreamFrameInfo: Any]],
              let raw = attachments.first?[.status] as? Int, SCFrameStatus(rawValue: raw) == .complete,
              let pixelBuffer = CMSampleBufferGetImageBuffer(sampleBuffer) else { return }
        let input = CIImage(cvPixelBuffer: pixelBuffer)
        guard let image = context.createCGImage(input, from: input.extent),
              (try? ImageSafety.validateDecoded(image, failureCode:"invalid_image", description:"Unsafe live frame")) != nil else { return }
        Task { @MainActor [receive] in receive(image) }
    }
    public func stream(_ stream: SCStream, didStopWithError error: Error) {
        let message = error.localizedDescription
        Task { @MainActor [failure] in failure(message) }
    }
}
