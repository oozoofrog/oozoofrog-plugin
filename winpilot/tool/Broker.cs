using System.Collections.Concurrent;
using System.Diagnostics;
using System.IO;
using System.Text.Json;

namespace WindowsPilot;

internal sealed class Broker : IDisposable
{
    private readonly ConcurrentDictionary<string, WindowInfo> windows = new();
    private readonly ConcurrentDictionary<string, Observation> observations = new();
    private readonly ConcurrentDictionary<string, CursorState> cursors = new();
    private readonly ConcurrentDictionary<string, Job> jobs = new();
    private readonly object gate = new();
    private const int MaxJobs = 1000;
    internal static readonly TimeSpan ObservationLifetime = TimeSpan.FromSeconds(30);
    private sealed class Job(string id, ActionArgs args, string eventName) : IDisposable
    {
        public string Id { get; } = id;
        public ActionArgs Args { get; } = args;
        public string EventName { get; } = eventName;
        public EventWaitHandle Cancel { get; } = new(false, EventResetMode.ManualReset, eventName);
        public Task<ActionResult>? Task { get; set; }
        public void Dispose() => Cancel.Dispose();
    }
    public object List()
    {
        var current = Native.List();
        var found = new HashSet<string>();
        lock (gate)
        {
            foreach (var w in current)
            {
                var old = windows.Values.FirstOrDefault(x => x.Hwnd == w.Hwnd && x.Pid == w.Pid && x.Started == w.Started);
                string id = old?.WindowId ?? "win_" + Guid.NewGuid().ToString("N");
                windows[id] = w with { WindowId = id };
                found.Add(id);
            }
            foreach (var id in windows.Keys.Where(x => !found.Contains(x))) windows.TryRemove(id, out _);
        }
        return new { windows = found.Select(id => windows[id]).ToArray(), cursors = cursors.Values.ToArray() };
    }

    public async Task<Observation> Observe(string windowId, bool capture)
    {
        var w = GetWindow(windowId);
        Native.Validate(w, false);
        w = Native.Describe((nint)w.Hwnd, windowId);
        var uiaTask = Worker(new("observe", w), 4000);
        var captureTask = capture ? Worker(new("capture", w), 6000) : Task.FromResult(new WorkerResult("not_requested"));
        await Task.WhenAll(uiaTask, captureTask);
        var uia = await uiaTask;
        var shot = await captureTask;
        Native.Validate(w);
        var observation = new Observation("obs_" + Guid.NewGuid().ToString("N"), w, DateTimeOffset.UtcNow,
            uia.Elements?.Take(200).ToArray() ?? [], uia.Truncated, uia.Status, shot.Capture, shot.Status, uia.Message, shot.Message);
        // 오래된 이미지와 참조를 무제한 보존하지 않는다.
        foreach (var item in observations.Values.Where(x => DateTimeOffset.UtcNow - x.ObservedAt > ObservationLifetime || x.Window.WindowId == windowId))
            observations.TryRemove(item.ObservationId, out _);
        if (observations.Count >= 16)
        {
            var oldest = observations.Values.MinBy(x => x.ObservedAt);
            if (oldest != null) observations.TryRemove(oldest.ObservationId, out _);
        }
        observations[observation.ObservationId] = observation;
        return observation;
    }

    public CursorState Cursor(string cursorId, string windowId, string observationId, int x, int y, string? elementId)
    {
        if (string.IsNullOrWhiteSpace(cursorId) || cursorId.Length > 64) throw new PilotException("invalid_arguments", "커서 ID는 1~64자여야 합니다.");
        var o = GetObservation(windowId, observationId);
        ValidatePoint(o, x, y);
        if (elementId != null && !o.Elements.Any(e => e.ElementId == elementId))
            throw new PilotException("stale_element", "관찰에 없는 요소입니다.");
        if (!cursors.ContainsKey(cursorId) && cursors.Count >= 16) throw new PilotException("capacity", "논리 커서는 최대 16개입니다.");
        var cursor = new CursorState(cursorId, windowId, observationId, x, y, elementId);
        cursors[cursorId] = cursor;
        return cursor;
    }

    public object Run(ActionArgs a)
    {
        ValidateAction(a);
        lock (gate)
        {
            var existing = jobs.Values.FirstOrDefault(j => j.Args.RequestId == a.RequestId);
            if (existing != null)
            {
                if (existing.Args != a) throw new PilotException("request_id_conflict", "같은 request_id를 다른 동작에 사용할 수 없습니다.");
                return new { job_id = existing.Id, reused = true };
            }
            if (jobs.Count >= MaxJobs) throw new PilotException("capacity", "세션 작업 한도에 도달했습니다. 작업을 확인하고 서버를 다시 시작하세요.");
            var o = GetObservation(a.WindowId, a.ObservationId);
            var e = a.ElementId == null ? null : o.Elements.FirstOrDefault(x => x.ElementId == a.ElementId);
            if (a.Type is "invoke" or "set_value")
            {
                if (e == null || e.Password || !e.Enabled || !e.Patterns.Contains(a.Type))
                    throw new PilotException("unsupported", "관찰한 요소가 요청한 동작을 지원하지 않습니다.");
            }
            if (a.Type is "click" or "drag")
            {
                ValidatePoint(o, a.X!.Value, a.Y!.Value);
                if (a.Type == "drag") ValidatePoint(o, a.ToX!.Value, a.ToY!.Value);
            }
            if (a.Type is "key")
            {
                if (a.KeyTarget == "element" && (e == null || !e.Focused || e.Password))
                    throw new PilotException("focus_unverified", "키 입력에는 관찰한 비암호 포커스 요소가 필요합니다.");
                if (a.KeyTarget == "window" && o.Capture == null)
                    throw new PilotException("coordinate_unverified", "창 단위 키 입력에는 최신 캡처가 필요합니다.");
            }
            var id = "job_" + Guid.NewGuid().ToString("N");
            var job = new Job(id, a, "Local\\WindowsPilot.Cancel." + Guid.NewGuid().ToString("N"));
            jobs[id] = job;
            // 한 관찰로 중복 변경을 실행하지 않도록 접수 시 소비한다.
            observations.TryRemove(o.ObservationId, out _);
            job.Task = Execute(job, o, e);
            return new { job_id = id, reused = false };
        }
    }

    private async Task<ActionResult> Execute(Job job, Observation o, ElementInfo? e)
    {
        string backend = job.Args.Type is "invoke" or "set_value" ? "uia" : "sendinput";
        try
        {
            var result = await Worker(new("action", o.Window, e?.RuntimeId, job.Args.Value, e?.Bounds, job.Args, job.EventName),
                backend == "uia" ? 5000 : 12000, job.Cancel);
            return new(result.Status, result.Backend ?? backend, result.Message ?? "결과 없음", result.Verified ?? false, result.ForegroundChanged);
        }
        catch (Exception ex) { return new("outcome_unknown", backend, ex.Message); }
    }

    public object Status(string id)
    {
        if (!jobs.TryGetValue(id, out var job)) throw new PilotException("unknown_job", "작업 ID가 없습니다.");
        return new { job_id = id, state = job.Task?.IsCompleted == true ? "finished" : "running", result = job.Task?.IsCompletedSuccessfully == true ? job.Task.Result : null };
    }
    public object Cancel(string? id)
    {
        if (id != null && !jobs.ContainsKey(id)) throw new PilotException("unknown_job", "작업 ID가 없습니다.");
        int count = 0;
        foreach (var j in jobs.Values.Where(j => id == null || j.Id == id))
            if (j.Task?.IsCompleted != true) { j.Cancel.Set(); count++; }
        return new { cancellation_requested = count, message = "취소 접수는 이미 실행한 작업을 되돌리지 않습니다. job_status로 확인하세요." };
    }

    public static void ValidateAction(ActionArgs a)
    {
        if (string.IsNullOrWhiteSpace(a.RequestId) || a.RequestId.Length > 128)
            throw new PilotException("invalid_arguments", "request_id는 1~128자여야 합니다.");
        if (a.ForegroundPolicy is not ("never" or "allow")) throw new PilotException("invalid_arguments", "전경 정책은 never 또는 allow입니다.");
        if (a.KeyTarget is not ("element" or "window") || a.KeyTarget == "window" && (a.Type != "key" || a.ElementId != null))
            throw new PilotException("invalid_arguments", "key_target=window는 요소 없는 key 요청에만 사용합니다.");
        if (a.Type is not ("invoke" or "set_value" or "click" or "drag" or "key")) throw new PilotException("unsupported", "지원하지 않는 동작입니다.");
        if (a.Type is "click" or "drag" or "key" && a.ForegroundPolicy != "allow")
            throw new PilotException("foreground_required", "백그라운드 전용 요청을 전경 입력으로 바꾸지 않습니다.");
        if (a.DurationMs < 1 || a.DurationMs > 2000) throw new PilotException("invalid_arguments", "입력 시간은 1~2000ms입니다.");
        if (a.Type == "set_value" && (a.Value == null || a.Value.Length > 4096)) throw new PilotException("invalid_arguments", "값은 최대 4096자입니다.");
        if (a.Type is "click" or "drag" && (a.X == null || a.Y == null)) throw new PilotException("invalid_arguments", "좌표가 필요합니다.");
        if (a.Type == "drag" && (a.ToX == null || a.ToY == null)) throw new PilotException("invalid_arguments", "드래그 끝 좌표가 필요합니다.");
        if (a.Type == "key" && (a.VirtualKey == null || !AllowedKey(a.VirtualKey.Value))) throw new PilotException("invalid_arguments", "단일 영문·숫자·방향·기본 탐색 키만 지원합니다.");
        if (a.ExpectedValue != null) throw new PilotException("unsupported", "일반 완료 조건은 아직 지원하지 않습니다. set_value는 자체 읽기 검증을 제공합니다.");
    }
    private static bool AllowedKey(int k) => k is >= 48 and <= 57 or >= 65 and <= 90 or >= 37 and <= 40 or 8 or 9 or 13 or 27 or 32 or 46;
    internal static void ValidatePoint(Observation o, int x, int y)
    {
        var c = o.Capture;
        if (c == null || !c.CoordinateMappingValid) throw new PilotException("coordinate_unverified", "좌표 매핑을 확인한 WGC 이미지가 필요합니다.");
        if (x < 0 || y < 0 || x >= c.Width || y >= c.Height) throw new PilotException("invalid_coordinates", "이미지 범위를 벗어난 좌표입니다.");
    }
    private WindowInfo GetWindow(string id) => windows.TryGetValue(id, out var w) ? w : throw new PilotException("unknown_window", "windows_list에서 창을 다시 선택하세요.");
    private Observation GetObservation(string windowId, string id)
    {
        if (!observations.TryGetValue(id, out var o) || o.Window.WindowId != windowId)
            throw new PilotException("stale_observation", "관찰 참조가 없거나 소비됐습니다.");
        if (DateTimeOffset.UtcNow - o.ObservedAt > ObservationLifetime)
            throw new PilotException("stale_observation", "관찰 후 30초가 지났습니다.");
        Native.Validate(o.Window);
        return o;
    }

    public static async Task<WorkerResult> Worker(WorkerRequest request, int timeoutMs, EventWaitHandle? cancel = null)
    {
        var start = new ProcessStartInfo(Environment.ProcessPath!)
        {
            UseShellExecute = false, RedirectStandardInput = true, RedirectStandardOutput = true,
            RedirectStandardError = true, CreateNoWindow = true,
            StandardInputEncoding = new System.Text.UTF8Encoding(false), StandardOutputEncoding = System.Text.Encoding.UTF8,
            StandardErrorEncoding = System.Text.Encoding.UTF8
        };
        if (string.Equals(Path.GetFileNameWithoutExtension(Environment.ProcessPath), "dotnet", StringComparison.OrdinalIgnoreCase))
            start.ArgumentList.Add(typeof(Broker).Assembly.Location);
        start.ArgumentList.Add("--worker");
        using var process = Process.Start(start) ?? throw new PilotException("worker_failed", "작업 프로세스를 시작하지 못했습니다.");
        var output = process.StandardOutput.ReadToEndAsync();
        var errors = process.StandardError.ReadToEndAsync();
        await process.StandardInput.WriteLineAsync(Json.Write(request));
        process.StandardInput.Close();
        long deadline = Environment.TickCount64 + timeoutMs;
        bool interrupted = false;
        while (!process.HasExited && Environment.TickCount64 < deadline)
        {
            if (cancel?.WaitOne(0) == true)
            {
                interrupted = true;
                // 해제 직후 사용자에게 직접 조작 가능 상태를 2.5초 표시한다.
                deadline = Math.Min(deadline, Environment.TickCount64 + 4000);
                if (request.Action?.Type is "invoke" or "set_value") break;
            }
            await Task.Delay(25);
        }
        if (!process.HasExited)
        {
            process.Kill(entireProcessTree: true);
            await process.WaitForExitAsync();
            await output; await errors;
            return new(request.Operation == "action" ? "outcome_unknown" : interrupted ? "interrupted" : "timeout",
                "작업 프로세스를 종료했습니다. 실행된 변경과 입력 해제 여부는 재확인이 필요합니다.");
        }
        var text = await output;
        await errors;
        try { return Json.Read<WorkerResult>(text); }
        catch (Exception) { return new("worker_failed", "작업 프로세스가 올바른 결과를 반환하지 않았습니다."); }
    }
    public void Dispose()
    {
        Cancel(null);
        try { Task.WaitAll(jobs.Values.Where(j => j.Task != null).Select(j => j.Task!).ToArray(), 9000); } catch (Exception) { }
        foreach (var job in jobs.Values) job.Dispose();
    }
}
