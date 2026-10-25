using System.Drawing;
using System.IO;
using System.Windows.Forms;

namespace WindowsPilot;

// 별도 준비 화면 없이 관찰 → 대상 확인 → 단일 입력 → 결과 기록 순서로 자동 진행한다.
internal sealed class VerificationForm : PilotToast
{
    private readonly int pid;
    private readonly long started;
    private readonly bool fixture;
    private readonly GameClickPlan? plan;
    private readonly bool layoutOnly;
    private readonly string eventName = "Local\\WindowsPilot.Verify." + Guid.NewGuid().ToString("N");
    private readonly EventWaitHandle cancel;
    private WindowInfo? target;
    private CaptureInfo? beforeCapture, afterCapture;
    private bool busy = true, stopped, dispatched;
    private readonly string directory = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "verification",
        DateTime.UtcNow.ToString("yyyyMMdd-HHmmss") + "-" + Guid.NewGuid().ToString("N")[..8]));
    private readonly List<object> events = [];
    private WorkerResult? result;

    public VerificationForm(int targetPid, long targetStarted, bool isFixture, GameClickPlan? clickPlan = null, bool layoutOnly = false)
    {
        pid = targetPid; started = targetStarted; fixture = isFixture; plan = clickPlan; this.layoutOnly = layoutOnly;
        cancel = new(false, EventResetMode.ManualReset, eventName);
        Text = "Windows Pilot 검증 · 준비";
        var area = Screen.PrimaryScreen!.WorkingArea;
        Location = new(area.Right - Width - 16, area.Bottom - Height - 16);
        SetStatus("Windows Pilot", "대상 화면을 확인하고 있어요");
        StopButton.Click += (_, _) => { if (busy) { stopped = true; cancel.Set(); SetStatus("중단하고 있어요", "입력 해제를 확인하는 중이에요"); } else Close(); };
        FormClosing += (_, e) => { if (busy) { e.Cancel = true; stopped = true; cancel.Set(); } };
        Load += (_, _) => BeginInvoke(async () => { Native.ShowWindow(Handle, 4); await Execute(); });
        FormClosed += (_, _) => cancel.Dispose();
    }
    private void State(string state, string message)
    {
        Text = "Windows Pilot 검증 · " + state;
        SetStatus(state, message);
        events.Add(new { at = DateTimeOffset.UtcNow, state, message });
    }
    private void CheckStop()
    {
        if (stopped) throw new PilotException("interrupted", "요청에 따라 중단했어요");
    }
    private async Task<CaptureInfo> CaptureTarget()
    {
        var shot = await Broker.Worker(new("capture", target!), 6000);
        if (shot.Capture is not { CoordinateMappingValid: true } capture)
            throw new PilotException("capture_failed", "화면을 확인하지 못했어요");
        return capture;
    }
    private async Task Execute()
    {
        bool uncertain = false;
        try
        {
            State("준비", "대상 화면을 확인하고 있어요");
            var matches = Native.List().Where(w => w.Pid == pid && w.Started == started &&
                (fixture ? w.Process == "windows-pilot" && w.Title.StartsWith("Windows Pilot Fixture ") : w.Process.Equals("MabinogiMobile", StringComparison.OrdinalIgnoreCase))).ToArray();
            if (matches.Length != 1) throw new PilotException("target_changed", "대상 창을 찾지 못했어요");
            target = matches[0]; Native.Validate(target);
            if (Native.Integrity(Environment.ProcessId) < Native.Integrity(pid))
                throw new PilotException("elevation_required", "대상 앱과 실행 권한이 달라요");
            Place(target.Bounds);
            beforeCapture = await CaptureTarget();
            CheckStop();
            if (layoutOnly) { await VerifyLayout(); return; }
            if (!fixture && plan == null && await Task.Run(() => GameSettings.IsOpen(beforeCapture)))
            {
                result = new("already_satisfied", "환경 설정 화면을 확인했습니다. 입력하지 않았습니다.", Verified: true);
                State("설정 화면 확인", "이미 열려 있어 입력하지 않았어요");
                return;
            }
            Point point;
            if (fixture)
            {
                var inspection = await Broker.Worker(new("observe", target), 4000);
                var b = inspection.Elements!.Single(e => e.Name == "PilotButton").Bounds;
                point = new(b.X - target.Bounds.X + b.Width / 2, b.Y - target.Bounds.Y + b.Height / 2);
            }
            else point = await Task.Run(() => plan?.Validate(target, beforeCapture) ?? GameSettings.Locate(beforeCapture));
            CheckStop(); Native.Validate(target);
            var observation = new Observation("fresh", target, DateTimeOffset.UtcNow, [], false, "not_requested", beforeCapture, "captured");
            Broker.ValidatePoint(observation, point.X, point.Y);
            var action = new ActionArgs("verification", "fresh", Guid.NewGuid().ToString("N"), "click", "allow", X: point.X, Y: point.Y, DurationMs: 80);
            Broker.ValidateAction(action);
            State("실행", plan?.Purpose ?? "설정 화면을 열고 있어요");
            Save(); Hide(); dispatched = true;
            result = await Broker.Worker(new("action", target, Action: action, CancelEvent: eventName), 12000, cancel);
            uncertain = result.Status is "outcome_unknown" or "release_unconfirmed" or "worker_failed";
            if (!uncertain)
            {
                try { afterCapture = await CaptureTarget(); }
                catch (Exception e) { events.Add(new { at = DateTimeOffset.UtcNow, state = "capture_failed", message = e.Message }); }
            }
            if (!fixture && plan == null && result.Status == "dispatched_unverified" && afterCapture != null &&
                await Task.Run(() => GameSettings.IsOpen(afterCapture)))
                result = result with { Status = "completed", Message = "입력 이후 환경 설정 제목과 아이콘을 확인했습니다.", Verified = true };
            // 입력 worker가 이미 종료 알림을 표시했다. 같은 내용을 두 번 띄우지 않는다.
            State(result.Status, uncertain ? "입력 해제를 확인하지 못했어요" : "실행 기록을 저장했어요");
            if (uncertain) { Show(); Native.ShowWindow(Handle, 4); }
            else if (result.Status is not ("completed" or "dispatched_unverified" or "interrupted"))
            {
                State("작업을 마치지 못했어요", "대상 상태가 바뀌었어요 · 기록을 남겼습니다");
                Show(); Native.ShowWindow(Handle, 4);
            }
        }
        catch (Exception e)
        {
            bool restoreFailed = e is PilotException { Code: "restore_failed" };
            uncertain = dispatched || restoreFailed;
            result = new(dispatched ? "outcome_unknown" : e is PilotException p ? p.Code : "verification_error", e.Message, Verified: false);
            State(stopped ? "중단했어요" : "실행하지 못했어요", restoreFailed ? e.Message : uncertain ? "키·버튼 상태를 직접 확인해 주세요" : e.Message);
            Show(); Native.ShowWindow(Handle, 4);
        }
        finally
        {
            busy = false;
            try { Save(); }
            catch (Exception) { State("기록을 저장하지 못했어요", "작업을 다시 실행하지 않습니다"); Show(); Native.ShowWindow(Handle, 4); }
            if (Visible) DismissAfter(uncertain ? 10000 : 4000); else Close();
        }
    }
    private async Task VerifyLayout()
    {
        var original = target!; var hwnd = (nint)original.Hwnd;
        if (!await Task.Run(() => GameSettings.IsOpen(beforeCapture!))) throw new PilotException("target_unrecognized", "설정 화면이 열려 있어야 해요");
        if (!Native.GetWindowRect(hwnd, out var rect)) throw new PilotException("target_changed", "창 크기를 확인하지 못했어요");
        State("화면 크기 확인", "창 크기를 잠시 바꾼 뒤 복원해요");
        try
        {
            CheckStop(); Native.Validate(original);
            if (!Native.SetWindowPos(hwnd, 0, rect.Left, rect.Top, 1280, 920, 0x14)) throw new PilotException("resize_denied", "창 크기를 바꾸지 못했어요");
            await Task.Delay(500); CheckStop(); Native.Validate(original, geometry: false);
            target = Native.Describe(hwnd);
            afterCapture = await CaptureTarget();
            bool changed = target.Bounds.Width != original.Bounds.Width && target.Bounds.Height != original.Bounds.Height;
            bool verified = changed && await Task.Run(() => GameSettings.IsOpen(afterCapture));
            events.Add(new { state = "layout_observed", original = original.Bounds, resized = target.Bounds, verified });
            result = new(verified ? "completed" : "result_unverified", "창 크기 변경 후 환경 설정 화면 인식 검사", Verified: verified);
        }
        finally
        {
            Native.Validate(original, geometry: false);
            if (!Native.SetWindowPos(hwnd, 0, rect.Left, rect.Top, rect.Right - rect.Left, rect.Bottom - rect.Top, 0x14))
                throw new PilotException("restore_failed", "원래 창 크기를 복원하지 못했어요");
            await Task.Delay(200); Native.Validate(original); target = original;
            events.Add(new { state = "layout_restored", bounds = original.Bounds });
        }
        State(result!.Verified == true ? "화면 확인 완료" : "결과 확인 필요", "원래 창 크기로 복원했어요");
    }
    private void Save()
    {
        Directory.CreateDirectory(directory);
        if (beforeCapture != null) File.WriteAllBytes(Path.Combine(directory, "before.png"), Convert.FromBase64String(beforeCapture.PngBase64));
        if (afterCapture != null) File.WriteAllBytes(Path.Combine(directory, "after.png"), Convert.FromBase64String(afterCapture.PngBase64));
        File.WriteAllText(Path.Combine(directory, "result.json"), Json.Write(new
        {
            target, runner_pid = Environment.ProcessId, runner_integrity = Native.Integrity(Environment.ProcessId),
            automatic = true, dispatched, result, verified = result?.Verified == true, purpose = layoutOnly ? "다른 창 크기에서 설정 화면 인식" : plan?.Purpose ?? "설정 화면 열기", events,
            before_image = beforeCapture == null ? null : "before.png", after_image = afterCapture == null ? null : "after.png"
        }));
    }
}
