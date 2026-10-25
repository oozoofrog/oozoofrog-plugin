using System.Text.Json;
using System.Text.Json.Serialization;

namespace WindowsPilot;

public static class Json
{
    public static readonly JsonSerializerOptions Options = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
        UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow
    };
    public static string Write(object value) => JsonSerializer.Serialize(value, Options);
    public static T Read<T>(string value) => JsonSerializer.Deserialize<T>(value, Options)
        ?? throw new PilotException("invalid_arguments", "JSON 객체가 필요합니다.");
}

public sealed class PilotException(string code, string message) : Exception(message)
{
    public string Code { get; } = code;
}
public record Bounds(int X, int Y, int Width, int Height);
public record WindowInfo(string WindowId, long Hwnd, int Pid, long Started, string Process,
    string Title, Bounds Bounds, bool Minimized, bool Foreground);
public record ElementInfo(string ElementId, int[] RuntimeId, string Name, string ControlType,
    Bounds Bounds, bool Enabled, bool Focused, bool Password, string[] Patterns, string? Value, string? ClassName = null);
public record CaptureInfo(string Backend, int Width, int Height, Bounds Bounds, long FrameTicks,
    bool CoordinateMappingValid, string PngBase64);
public record WorkerRequest(string Operation, WindowInfo Window,
    int[]? RuntimeId = null, string? Value = null, Bounds? ExpectedBounds = null,
    ActionArgs? Action = null, string? CancelEvent = null);
public record WorkerResult(string Status, string? Message = null, ElementInfo[]? Elements = null,
    CaptureInfo? Capture = null, bool Truncated = false, bool? Verified = null,
    bool? ForegroundChanged = null, string? Backend = null);
public record Observation(string ObservationId, WindowInfo Window, DateTimeOffset ObservedAt,
    ElementInfo[] Elements, bool Truncated, string AccessibilityStatus, CaptureInfo? Capture,
    string CaptureStatus, string? AccessibilityMessage = null, string? CaptureMessage = null);
public record CursorState(string CursorId, string WindowId, string ObservationId, int X, int Y,
    string? ElementId, string Kind = "logical_only");
public record ActionArgs(string WindowId, string ObservationId, string RequestId, string Type,
    string ForegroundPolicy = "never", string? ElementId = null, string? Value = null,
    int? X = null, int? Y = null, int? ToX = null, int? ToY = null, int? VirtualKey = null,
    int DurationMs = 100, string? ExpectedValue = null, string KeyTarget = "element");
public record ActionResult(string Status, string Backend, string Message, bool Verified = false,
    bool? ForegroundChanged = null);
