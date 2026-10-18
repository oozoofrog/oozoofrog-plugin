import AppKit
import ScreenCaptureKit
import Vision
import CryptoKit

private func boundedOCRText(_ raw: String, maximumBytes: Int = 4_096) -> (String, Bool) {
    guard raw.utf8.count > maximumBytes else { return (raw, false) }
    var bytes = Array(raw.utf8.prefix(maximumBytes))
    while !bytes.isEmpty {
        if let value = String(bytes: bytes, encoding: .utf8) { return (value, true) }
        bytes.removeLast()
    }
    return ("", true)
}

private final class OCRRequestBox: @unchecked Sendable {
    let request = VNRecognizeTextRequest()
}

@MainActor public enum Capture {
    private static let maximumCaptureDimension = 8_192
    private static let maximumCapturePixels = 16_777_216

    private static func checkedMaxDimension(_ value: Int) throws -> Int {
        guard (1...maximumCaptureDimension).contains(value) else {
            throw ToolFailure("invalid_argument", "maxDimension must be between 1 and \(maximumCaptureDimension)")
        }
        return value
    }

    private static func deadline(after milliseconds: Int) throws -> UInt64 {
        guard (100...60_000).contains(milliseconds) else {
            throw ToolFailure("invalid_argument", "timeoutMs must be between 100 and 60000")
        }
        return DispatchTime.now().uptimeNanoseconds + UInt64(milliseconds) * 1_000_000
    }

    private static func remainingMilliseconds(until deadline: UInt64) throws -> Int {
        let now = DispatchTime.now().uptimeNanoseconds
        guard now < deadline else {
            throw ToolFailure("capture_timeout", "ScreenCaptureKit exceeded its bounded request time; no capture result was accepted")
        }
        return max(1, Int((deadline - now + 999_999) / 1_000_000))
    }

    private static func shareableContent(excludingDesktopWindows: Bool, deadline: UInt64) async throws -> SCShareableContent {
        let remaining = try remainingMilliseconds(until: deadline)
        return try await withCallbackDeadline(
            timeoutMilliseconds: remaining,
            timeoutFailure: ToolFailure("capture_timeout", "ScreenCaptureKit shareable-content discovery exceeded its bounded request time")
        ) { finish in
            SCShareableContent.getExcludingDesktopWindows(excludingDesktopWindows, onScreenWindowsOnly: false) { content, error in
                if let content { finish(.success(content)) }
                else { finish(.failure(error ?? ToolFailure("capture_failed", "ScreenCaptureKit returned no shareable content"))) }
            }
        }
    }

    private static func capture(filter: SCContentFilter, configuration: SCStreamConfiguration, deadline: UInt64) async throws -> CGImage {
        let remaining = try remainingMilliseconds(until: deadline)
        return try await withCallbackDeadline(
            timeoutMilliseconds: remaining,
            timeoutFailure: ToolFailure("capture_timeout", "ScreenCaptureKit image capture exceeded its bounded request time")
        ) { finish in
            SCScreenshotManager.captureImage(contentFilter: filter, configuration: configuration) { image, error in
                if let image { finish(.success(image)) }
                else { finish(.failure(error ?? ToolFailure("capture_failed", "ScreenCaptureKit returned no image"))) }
            }
        }
    }

    private static func validatedCapture(_ image: CGImage, maximumDimension: Int) throws -> CGImage {
        let width = image.width, height = image.height
        guard width > 0, height > 0,
              width <= maximumDimension, height <= maximumDimension,
              width <= maximumCapturePixels / height else {
            throw ToolFailure("capture_failed", "ScreenCaptureKit returned an image outside the requested dimension or pixel limits")
        }
        return image
    }

    public static func image(windowID: UInt32, maxDimension: Int = 1600, timeoutMilliseconds: Int = 10_000) async throws -> CGImage {
        guard CGPreflightScreenCaptureAccess() else { throw ToolFailure("screen_capture_denied", "Enable Screen Recording for this executable or its responsible host") }
        let maxDimension = try checkedMaxDimension(maxDimension)
        let deadline = try deadline(after: timeoutMilliseconds)
        let content = try await shareableContent(excludingDesktopWindows: true, deadline: deadline)
        guard let window = content.windows.first(where: { $0.windowID == windowID }) else { throw ToolFailure("window_unavailable", "Window is not shareable") }
        let filter = SCContentFilter(desktopIndependentWindow: window)
        let config = SCStreamConfiguration()
        let size = filter.contentRect.size
        guard size.width.isFinite, size.height.isFinite, size.width > 0, size.height > 0 else {
            throw ToolFailure("window_unavailable", "Window has invalid capture geometry")
        }
        let dimensionScale = Double(maxDimension) / max(size.width, size.height)
        let pixelScale = sqrt(Double(maximumCapturePixels) / (size.width * size.height))
        let scale = min(Double(filter.pointPixelScale), dimensionScale, pixelScale)
        config.width = max(1, Int((size.width * scale).rounded()))
        config.height = max(1, Int((size.height * scale).rounded()))
        config.showsCursor = false
        config.ignoreShadowsSingleWindow = true
        // Keep the returned pixels in the selected window's coordinate space.
        // SCK includes child/grouped windows by default, which can expand the
        // captured composition while metadata still describes this one window.
        if #available(macOS 14.2, *) { config.includeChildWindows = false }
        config.captureResolution = .best
        return try validatedCapture(
            try await capture(filter: filter, configuration: config, deadline: deadline),
            maximumDimension: maxDimension
        )
    }

    public static func image(displayID: CGDirectDisplayID, maxDimension: Int = 1600, timeoutMilliseconds: Int = 10_000) async throws -> CGImage {
        guard CGPreflightScreenCaptureAccess() else { throw ToolFailure("screen_capture_denied", "Enable Screen Recording for this executable or its responsible host") }
        let maxDimension = try checkedMaxDimension(maxDimension)
        let deadline = try deadline(after: timeoutMilliseconds)
        let content = try await shareableContent(excludingDesktopWindows: false, deadline: deadline)
        guard let display = content.displays.first(where: { $0.displayID == displayID }) else {
            throw ToolFailure("display_unavailable", "Display is not shareable")
        }
        let width = display.width, height = display.height
        guard width > 0, height > 0 else { throw ToolFailure("display_unavailable", "Display has invalid capture geometry") }
        let dimensionScale = Double(maxDimension) / Double(max(width, height))
        let pixelScale = sqrt(Double(maximumCapturePixels) / (Double(width) * Double(height)))
        let scale = min(1, dimensionScale, pixelScale)
        let config = SCStreamConfiguration()
        config.width = max(1, Int((Double(width) * scale).rounded()))
        config.height = max(1, Int((Double(height) * scale).rounded()))
        config.showsCursor = false
        config.captureResolution = .best
        let filter = SCContentFilter(display: display, excludingApplications: [], exceptingWindows: [])
        return try validatedCapture(
            try await capture(filter: filter, configuration: config, deadline: deadline),
            maximumDimension: maxDimension
        )
    }

    public static func png(_ image: CGImage) throws -> Data {
        guard let data = NSBitmapImageRep(cgImage: image).representation(using: .png, properties: [:]) else { throw ToolFailure("image_failed", "PNG encoding failed") }
        return data
    }
    public nonisolated static func ocr(_ image: CGImage, languages: [String], timeoutMilliseconds: Int = 30_000) async throws -> [[String: Any]] {
        guard (100...60_000).contains(timeoutMilliseconds) else {
            throw ToolFailure("invalid_argument", "timeoutMs must be between 100 and 60000")
        }
        guard languages.count <= 8,
              languages.allSatisfy({ !$0.isEmpty && $0.utf8.count <= 64 && !$0.contains("\0") }) else {
            throw ToolFailure("invalid_argument", "OCR languages must contain at most 8 nonempty identifiers of at most 64 UTF-8 bytes")
        }
        let requestBox = OCRRequestBox()
        let request = requestBox.request
        request.recognitionLevel = .accurate; request.usesLanguageCorrection = true
        if !languages.isEmpty { request.recognitionLanguages = languages }
        return try await withCallbackDeadline(
            timeoutMilliseconds: timeoutMilliseconds,
            timeoutFailure: ToolFailure("ocr_timeout", "Vision OCR exceeded its bounded request time and was cancelled"),
            onTimeout: { requestBox.request.cancel() },
            onCancel: { requestBox.request.cancel() }
        ) { finish in
            DispatchQueue.global(qos: .userInitiated).async {
                do {
                    try VNImageRequestHandler(cgImage: image).perform([requestBox.request])
                    let result: [[String: Any]] = (requestBox.request.results ?? []).prefix(300).compactMap { row in
                        guard let candidate = row.topCandidates(1).first else { return nil }
                        let text = boundedOCRText(candidate.string)
                        let b = row.boundingBox
                        return ["text":text.0, "textTruncated":text.1, "confidence":candidate.confidence,
                                "imageRect":Rect(CGRect(x: b.minX * Double(image.width), y: (1-b.maxY) * Double(image.height), width: b.width * Double(image.width), height: b.height * Double(image.height))).object]
                    }
                    finish(.success(result))
                } catch {
                    finish(.failure(error))
                }
            }
        }
    }
    public static func hash(_ image: CGImage) throws -> String { SHA256.hash(data: try png(image)).map { String(format: "%02x", $0) }.joined() }
}
