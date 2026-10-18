import AppKit
import AVFoundation
import CryptoKit
import Darwin
import ScreenCaptureKit

@available(macOS 15.0, *)
private final class RecordingEvents: NSObject, SCRecordingOutputDelegate, SCStreamDelegate, @unchecked Sendable {
    private let lock = NSLock()
    private var started = false, finished = false, stopping = false, failure: String?
    var state: (started: Bool, finished: Bool, failure: String?) {
        lock.lock(); defer { lock.unlock() }; return (started, finished, failure)
    }
    var stopRequested: Bool { lock.lock(); defer { lock.unlock() }; return stopping }
    func requestStop() { lock.lock(); defer { lock.unlock() }; stopping = true }
    func recordingOutputDidStartRecording(_ recordingOutput: SCRecordingOutput) {
        lock.lock(); defer { lock.unlock() }; started = true
    }
    func recordingOutputDidFinishRecording(_ recordingOutput: SCRecordingOutput) {
        lock.lock(); defer { lock.unlock() }; finished = true
    }
    func recordingOutput(_ recordingOutput: SCRecordingOutput, didFailWithError error: Error) {
        lock.lock(); defer { lock.unlock() }; failure = error.localizedDescription
    }
    func stream(_ stream: SCStream, didStopWithError error: Error) {
        lock.lock(); defer { lock.unlock() }; failure = error.localizedDescription
    }
}

@MainActor public enum Recording {
    struct Request {
        let source: String, duration: Double, dimension: Int, fps: Int, audio: Bool, cursor: Bool
        let pid: Int32?, identity: String?, windowID: UInt32?, displayID: UInt32?
        let region: CGRect?
        init(_ a: Arguments) throws {
            try a.only(["operation", "source", "pid", "processStartID", "windowID", "displayID", "region", "durationSeconds", "maxDimension", "fps", "systemAudio", "showsCursor"])
            source = try a.string("source")
            duration = try a.number("durationSeconds", default: 10, range: 1...120)
            dimension = try a.integer("maxDimension", default: 1920, range: 320...3840)
            fps = try a.integer("fps", default: 30, range: 1...60)
            audio = try a.bool("systemAudio", default: true); cursor = try a.bool("showsCursor")
            if source == "window" {
                guard a.values["displayID"] == nil, a.values["region"] == nil else { throw ToolFailure("invalid_argument", "Window capture does not accept displayID or a composited display region") }
                pid = Int32(try a.integer("pid", range: 1...Int(Int32.max)))
                identity = try a.string("processStartID", limit: 64)
                windowID = UInt32(try a.integer("windowID", range: 1...Int(UInt32.max))); displayID = nil; region = nil
            } else if source == "display" {
                guard ["pid", "processStartID", "windowID"].allSatisfy({ a.values[$0] == nil }) else { throw ToolFailure("invalid_argument", "Display capture does not accept window targeting") }
                displayID = UInt32(try a.integer("displayID", range: 1...Int(UInt32.max))); pid = nil; identity = nil; windowID = nil
                if let raw = a.values["region"] {
                    guard let object = raw as? [String: Any] else { throw ToolFailure("invalid_argument", "region requires x, y, width and height in display-relative logical points") }
                    let bounds = Arguments(object); try bounds.only(["x", "y", "width", "height"])
                    region = CGRect(x: try bounds.number("x", range: 0...1e7), y: try bounds.number("y", range: 0...1e7),
                                    width: try bounds.number("width", range: 1...1e7), height: try bounds.number("height", range: 1...1e7))
                } else { region = nil }
            } else { throw ToolFailure("invalid_argument", "source must be window or display") }
        }
    }
    static func dimensions(size: CGSize, pixelScale: Double, maximum: Int) throws -> (Int, Int) {
        guard size.width.isFinite, size.height.isFinite, size.width > 0, size.height > 0,
              pixelScale.isFinite, pixelScale > 0, (320...3840).contains(maximum) else { throw ToolFailure("invalid_capture_geometry", "Recording target has invalid geometry") }
        let scale = min(pixelScale, Double(maximum) / max(size.width, size.height), sqrt(8_294_400 / (size.width * size.height)))
        // H.264 requires even encoded dimensions.
        return (max(2, Int(size.width * scale) / 2 * 2), max(2, Int(size.height * scale) / 2 * 2))
    }
    public static func call(_ a: Arguments, store: Store) async throws -> [String: Any] {
        switch try a.string("operation") {
        case "record":
            let request = try Request(a)
            guard #available(macOS 15.0, *) else { throw ToolFailure("unsupported_platform", "Movie recording requires macOS 15 or later; still capture remains available on macOS 14") }
            return try await record(request, store: store)
        case "inspect":
            try a.only(["operation", "path", "frames"])
            let path = try SystemActions.explicitFileURLs([a.string("path", limit: 4096)], key: "path", mustExist: true, rejectRoot: true)[0]
            return try await inspect(path, store: store, frames: a.integer("frames", default: 3, range: 0...6))
        default: throw ToolFailure("invalid_argument", "operation must be record or inspect")
        }
    }
    @available(macOS 15.0, *)
    private static func record(_ r: Request, store: Store) async throws -> [String: Any] {
        guard CGPreflightScreenCaptureAccess() else { throw ToolFailure("screen_capture_denied", "Allow Screen & System Audio Recording for this executable or its responsible host") }
        if let pid = r.pid, let identity = r.identity { try ProcessIdentity.require(pid: pid, expected: identity) }
        let content: SCShareableContent = try await withCallbackDeadline(timeoutMilliseconds: 10_000,
            timeoutFailure: ToolFailure("capture_timeout", "Recording target discovery timed out")) { finish in
            SCShareableContent.getExcludingDesktopWindows(true, onScreenWindowsOnly: false) { content, error in
                if let content { finish(.success(content)) } else { finish(.failure(error ?? ToolFailure("capture_failed", "No shareable content"))) }
            }
        }
        let filter: SCContentFilter
        if let windowID = r.windowID, let pid = r.pid, let identity = r.identity {
            try ProcessIdentity.require(pid: pid, expected: identity)
            guard let window = content.windows.first(where: { $0.windowID == windowID && $0.owningApplication?.processID == pid }) else {
                throw ToolFailure("window_unavailable", "Selected PID/window is no longer shareable")
            }
            filter = SCContentFilter(desktopIndependentWindow: window)
        } else {
            guard let display = content.displays.first(where: { $0.displayID == r.displayID }) else { throw ToolFailure("display_unavailable", "Selected display is no longer shareable") }
            filter = SCContentFilter(display: display, excludingApplications: [], exceptingWindows: [])
        }
        if let region = r.region, !CGRect(origin: .zero, size: filter.contentRect.size).contains(region) {
            throw ToolFailure("invalid_capture_region", "The complete region must fit inside the selected display; coordinates are display-relative logical points")
        }
        let (width, height) = try dimensions(size: r.region?.size ?? filter.contentRect.size, pixelScale: Double(filter.pointPixelScale), maximum: r.dimension)
        let configuration = SCStreamConfiguration()
        configuration.width = width; configuration.height = height
        if let region = r.region { configuration.sourceRect = region }
        configuration.minimumFrameInterval = CMTime(value: 1, timescale: CMTimeScale(r.fps))
        configuration.queueDepth = 5; configuration.showsCursor = r.cursor
        configuration.capturesAudio = r.audio; configuration.sampleRate = 48_000; configuration.channelCount = 2
        configuration.excludesCurrentProcessAudio = true
        configuration.ignoreShadowsSingleWindow = true
        configuration.captureMicrophone = false
        let id = UUID().uuidString.lowercased()
        let movie = store.root.appendingPathComponent("recording-\(id).mp4")
        let outputConfiguration = SCRecordingOutputConfiguration()
        outputConfiguration.outputURL = movie; outputConfiguration.videoCodecType = .h264; outputConfiguration.outputFileType = .mp4
        let events = RecordingEvents(), output = SCRecordingOutput(configuration: outputConfiguration, delegate: events)
        let stream = SCStream(filter: filter, configuration: configuration, delegate: events)
        try stream.addRecordingOutput(output)
        do {
            let _: Bool = try await withCallbackDeadline(timeoutMilliseconds: 10_000,
                timeoutFailure: ToolFailure("recording_start_timeout", "ScreenCaptureKit did not acknowledge recording start"),
                onTimeout: { events.requestStop(); stream.stopCapture { _ in } },
                onCancel: { events.requestStop(); stream.stopCapture { _ in } }) { finish in
                stream.startCapture { error in
                    // Cancellation/timeout may win before a delayed start callback.
                    if events.stopRequested { stream.stopCapture { _ in } }
                    if let error { finish(.failure(error)) } else { finish(.success(true)) }
                }
            }
            let startDeadline = Date().addingTimeInterval(5)
            while !events.state.started {
                try Task.checkCancellation()
                if let failure = events.state.failure { throw ToolFailure("recording_failed", failure) }
                guard output.recordedFileSize < 1_000_000_000 else { throw ToolFailure("recording_size_limit", "Movie reached the 1 GB capture budget") }
                guard Date() < startDeadline else { throw ToolFailure("recording_start_timeout", "Movie output did not start") }
                try await Task.sleep(nanoseconds: 20_000_000)
            }
            // Start duration at the output's actual start acknowledgement.
            let deadline = Date().addingTimeInterval(r.duration)
            repeat {
                try Task.checkCancellation()
                if let pid = r.pid, let identity = r.identity { try ProcessIdentity.require(pid: pid, expected: identity) }
                if let failure = events.state.failure { throw ToolFailure("recording_failed", failure) }
                try await Task.sleep(nanoseconds: 50_000_000)
            } while Date() < deadline
            try await stop(stream)
            try await waitForFinish(events)
        } catch {
            // Cancellation still stops capture and lets the native output close.
            // Keep an incomplete file for reconciliation; never report it as done.
            let cleanup = Task.detached { @MainActor in
                events.requestStop()
                try? await stop(stream)
                try? await waitForFinish(events)
                if FileManager.default.fileExists(atPath: movie.path) { _ = chmod(movie.path, 0o600) }
            }
            await cleanup.value
            try? store.write(jsonData(["status": "incomplete", "path": movie.path, "reason": (error as? ToolFailure)?.code ?? "cancelled_or_failed"]),
                             to: store.root.appendingPathComponent("recording-\(id).json"))
            throw error
        }
        guard chmod(movie.path, 0o600) == 0 else { throw ToolFailure("recording_file_permission_failed", "Cannot restrict completed movie permissions") }
        var result = try await inspect(movie, store: store, frames: 3)
        guard (result["videoTracks"] as? Int ?? 0) > 0 else { throw ToolFailure("recording_missing_video", "Movie has no video track: \(movie.path)") }
        if r.audio, (result["audioTracks"] as? Int ?? 0) == 0 { throw ToolFailure("recording_missing_audio", "Movie has no requested system-audio track: \(movie.path)") }
        result["status"] = r.audio && result["audioSignalDetected"] as? Bool != true ? "recorded_without_audio_signal" : "recorded"
        result["source"] = r.source; result["requestedDurationSeconds"] = r.duration
        result["recordingID"] = id
        if let pid = r.pid { result["pid"] = pid; result["processStartID"] = r.identity; result["windowID"] = r.windowID }
        if let display = r.displayID { result["displayID"] = display }
        if let region = r.region { result["region"] = Rect(region).object }
        result["audioScope"] = r.audio ? (r.source == "window" ? "selected_window_application" : "included_display_applications") : "disabled"
        result["microphoneCaptured"] = false; result["systemAudioRequested"] = r.audio
        result["requestedFPS"] = r.fps; result["encodedWidth"] = width; result["encodedHeight"] = height
        result["verification"] = "SCRecordingOutput finished; saved local movie tracks, decoded audio energy and sampled video frames were inspected. Content meaning and lip sync require review."
        try store.write(jsonData(result), to: store.root.appendingPathComponent("recording-\(id).json"))
        return result
    }
    @available(macOS 15.0, *) private static func stop(_ stream: SCStream) async throws {
        let _: Bool = try await withCallbackDeadline(timeoutMilliseconds: 5000,
            timeoutFailure: ToolFailure("recording_stop_timeout", "ScreenCaptureKit stop was not acknowledged")) { finish in
            stream.stopCapture { error in if let error { finish(.failure(error)) } else { finish(.success(true)) } }
        }
    }
    @available(macOS 15.0, *) private static func waitForFinish(_ events: RecordingEvents) async throws {
        let deadline = Date().addingTimeInterval(10)
        while !events.state.finished {
            try Task.checkCancellation()
            if let failure = events.state.failure { throw ToolFailure("recording_failed", failure) }
            guard Date() < deadline else { throw ToolFailure("recording_finish_timeout", "Movie was not finalized") }
            try await Task.sleep(nanoseconds: 25_000_000)
        }
    }
    private static func fourCC(_ value: FourCharCode) -> String {
        String(bytes: [24, 16, 8, 0].map { UInt8((value >> $0) & 255) }, encoding: .ascii) ?? String(value)
    }
    static func inspect(_ url: URL, store: Store, frames: Int) async throws -> [String: Any] {
        let attributes = try FileManager.default.attributesOfItem(atPath: url.path)
        guard attributes[.type] as? FileAttributeType == .typeRegular,
              let bytes = attributes[.size] as? NSNumber, bytes.int64Value > 0, bytes.int64Value <= 1_073_741_824 else {
            throw ToolFailure("invalid_media", "Inspect requires a nonempty regular local file no larger than 1 GiB")
        }
        let asset = AVURLAsset(url: url)
        let duration = try await asset.load(.duration).seconds
        guard duration.isFinite, duration > 0, duration <= 600 else { throw ToolFailure("invalid_media", "Movie duration must be within 600 seconds for bounded inspection") }
        let video = try await asset.loadTracks(withMediaType: .video), audio = try await asset.loadTracks(withMediaType: .audio)
        var tracks: [[String: Any]] = []
        for track in video + audio {
            let format = try await track.load(.formatDescriptions), timeRange = try await track.load(.timeRange)
            var row: [String: Any] = ["kind": track.mediaType.rawValue, "startSeconds": timeRange.start.seconds, "durationSeconds": timeRange.duration.seconds,
                                     "codecs": format.map { fourCC(CMFormatDescriptionGetMediaSubType($0)) }]
            if track.mediaType == .video {
                let size = try await track.load(.naturalSize)
                row["width"] = size.width; row["height"] = size.height; row["nominalFPS"] = try await track.load(.nominalFrameRate)
            }
            tracks.append(row)
        }
        let audioWorker = Task.detached { try audioMetrics(asset, tracks: audio) }
        let audioResult = try await withTaskCancellationHandler(operation: { try await audioWorker.value }, onCancel: { audioWorker.cancel() })
        try Task.checkCancellation()
        var samples: [[String: Any]] = []
        if !video.isEmpty, frames > 0 {
            let generator = AVAssetImageGenerator(asset: asset)
            generator.appliesPreferredTrackTransform = true; generator.maximumSize = CGSize(width: 960, height: 960)
            generator.requestedTimeToleranceBefore = CMTime(seconds: 0.1, preferredTimescale: 600)
            generator.requestedTimeToleranceAfter = generator.requestedTimeToleranceBefore
            for index in 0..<frames {
                try Task.checkCancellation()
                let seconds = duration * Double(index + 1) / Double(frames + 1)
                var actual = CMTime.zero
                let image = try generator.copyCGImage(at: CMTime(seconds: seconds, preferredTimescale: 600), actualTime: &actual)
                let data = try Capture.png(image), path = store.root.appendingPathComponent("movie-frame-\(UUID().uuidString.lowercased()).png")
                try store.write(data, to: path)
                samples.append(["requestedSeconds": seconds, "actualSeconds": actual.seconds, "path": path.path,
                                "sha256": SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined()])
            }
        }
        return ["status": "movie_inspected", "path": url.path, "bytes": bytes, "durationSeconds": duration,
                "videoTracks": video.count, "audioTracks": audio.count, "tracks": tracks,
                "audioRMS": audioResult.rms, "audioPeak": audioResult.peak, "decodedAudioSamples": audioResult.samples,
                "audioSignalDetected": audioResult.peak > 0.00001, "audioAnalysisComplete": audioResult.complete,
                "frames": samples, "sampledFramesDiffer": Set(samples.compactMap { $0["sha256"] as? String }).count > 1]
    }
    nonisolated private static func audioMetrics(_ asset: AVAsset, tracks: [AVAssetTrack]) throws -> (rms: Double, peak: Double, samples: Int, complete: Bool) {
        guard let track = tracks.first else { return (0, 0, 0, true) }
        let reader = try AVAssetReader(asset: asset)
        let output = AVAssetReaderTrackOutput(track: track, outputSettings: [AVFormatIDKey: kAudioFormatLinearPCM,
            AVLinearPCMIsFloatKey: true, AVLinearPCMBitDepthKey: 32, AVLinearPCMIsNonInterleaved: false])
        guard reader.canAdd(output) else { throw ToolFailure("audio_decode_failed", "Cannot inspect movie audio") }
        reader.add(output)
        guard reader.startReading() else { throw reader.error ?? ToolFailure("audio_decode_failed", "Cannot decode movie audio") }
        defer { reader.cancelReading() }
        var sum = 0.0, peak = 0.0, samples = 0
        let deadline = Date().addingTimeInterval(20)
        while let buffer = output.copyNextSampleBuffer() {
            try Task.checkCancellation()
            guard Date() < deadline, samples < 33_554_432 else { return (samples > 0 ? sqrt(sum / Double(samples)) : 0, peak, samples, false) }
            guard let block = CMSampleBufferGetDataBuffer(buffer) else { throw ToolFailure("audio_decode_failed", "Decoded audio has no PCM block") }
            let length = CMBlockBufferGetDataLength(block)
            guard length <= 1_048_576, length % 4 == 0 else { throw ToolFailure("audio_decode_failed", "Unexpected PCM block size") }
            var data = Data(count: length)
            let status = data.withUnsafeMutableBytes { CMBlockBufferCopyDataBytes(block, atOffset: 0, dataLength: length, destination: $0.baseAddress!) }
            guard status == kCMBlockBufferNoErr else { throw ToolFailure("audio_decode_failed", "Cannot copy PCM samples") }
            data.withUnsafeBytes { raw in
                for value in raw.bindMemory(to: Float.self) where value.isFinite {
                    let number = Double(value); sum += number * number; peak = max(peak, abs(number)); samples += 1
                }
            }
        }
        if reader.status == .failed { throw reader.error ?? ToolFailure("audio_decode_failed", "Audio decoding failed") }
        return (samples > 0 ? sqrt(sum / Double(samples)) : 0, peak, samples, reader.status == .completed)
    }
}
