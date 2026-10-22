import Foundation

/// Values are always copied from the source. JEV selects IDs, never writes or repairs a value.
struct RequestSpan: Codable, Equatable {
    var id: String
    var source: String
    var rangeUTF16: AXTextRange
    var text: String
}

enum RequestSpans {
    static func candidates(in text: String, source: String = "request") -> [RequestSpan] {
        let ns = text as NSString
        var ranges: [NSRange] = []
        // Over-find possible payloads; these expressions do not decide the requested operation.
        let patterns = ["(?s)\"\"\"(.*?)\"\"\"", "(?s)```(?:[^\\n]*\\n)?(.*?)```", "(?s)\"([^\"]*)\"", "(?s)“([^”]*)”", "(?s)‘([^’]*)’", "(?s)'([^']*)'", "(?s)`([^`\\n]+)`", "(?s)(?:다음(?:의)?\\s*(?:문구|내용|텍스트)?\\s*[:：]\\s*\\n?)(.+)$", "(?is)(?:type|enter|paste)\\s+(.+?)(?:\\s+(?:into|in|on)\\b|$)", "(?s)(?:에서|에는|에)\\s+(.+?)(?:라고|을|를)?\\s*(?:입력해|적어|붙여|써\\s*줘)", "(?m)(/[^\\s\"'`“”]+)"]
        for pattern in patterns {
            guard let expression = try? NSRegularExpression(pattern: pattern) else { continue }
            for match in expression.matches(in: text, range: NSRange(location: 0, length: ns.length)) {
                let range = match.range(at: 1)
                if range.length > 0, !ranges.contains(range) { ranges.append(range) }
            }
        }
        // Bound both the catalogue and its wire preview. Missing coverage causes a follow-up.
        return ranges.prefix(32).enumerated().map { index, range in
            RequestSpan(id: "span_\(index)", source: source, rangeUTF16: AXTextRange(location: range.location, length: range.length), text: ns.substring(with: range))
        }
    }

    static func exact(_ span: RequestSpan, in source: String) throws -> String {
        let range = span.rangeUTF16
        guard range.location >= 0, range.length >= 0, range.location <= source.utf16.count,
              range.length <= source.utf16.count - range.location,
              let swiftRange = Range(NSRange(location: range.location, length: range.length), in: source),
              String(source[swiftRange]) == span.text else { throw Failure("Request source span is invalid or changed") }
        return String(source[swiftRange])
    }
}
