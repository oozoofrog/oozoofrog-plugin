using System.Windows.Automation;

namespace WindowsPilot;

internal static class Automation
{
    private static readonly TreeWalker Walker = TreeWalker.ControlViewWalker;
    private static IEnumerable<AutomationElement> Walk(nint hwnd)
    {
        var queue = new Queue<(AutomationElement Element, int Depth)>();
        queue.Enqueue((AutomationElement.FromHandle(hwnd), 0));
        int count = 0;
        while (queue.Count > 0 && count++ < 201)
        {
            var (element, depth) = queue.Dequeue();
            yield return element;
            if (depth >= 8) continue;
            var child = Walker.GetFirstChild(element);
            while (child != null && queue.Count < 201)
            {
                queue.Enqueue((child, depth + 1));
                child = Walker.GetNextSibling(child);
            }
        }
    }
    public static ElementInfo[] Inspect(WindowInfo window)
    {
        Native.Validate(window, false);
        var result = new List<ElementInfo>();
        foreach (var element in Walk((nint)window.Hwnd))
        {
            try
            {
                var c = element.Current;
                var patterns = new List<string>();
                if (element.TryGetCurrentPattern(InvokePattern.Pattern, out _)) patterns.Add("invoke");
                string? value = null;
                if (!c.IsPassword && element.TryGetCurrentPattern(ValuePattern.Pattern, out var pattern))
                {
                    var p = (ValuePattern)pattern;
                    if (!p.Current.IsReadOnly) patterns.Add("set_value");
                    value = p.Current.Value;
                    if (value?.Length > 2048) value = value[..2048];
                }
                var rect = c.BoundingRectangle;
                var bounds = rect.IsEmpty ? new Bounds(0, 0, 0, 0) :
                    new Bounds((int)rect.X, (int)rect.Y, (int)rect.Width, (int)rect.Height);
                var runtime = element.GetRuntimeId();
                result.Add(new(string.Join(".", runtime), runtime, c.Name, c.ControlType.ProgrammaticName,
                    bounds, c.IsEnabled, c.HasKeyboardFocus, c.IsPassword, patterns.ToArray(), value, c.ClassName));
            }
            catch (ElementNotAvailableException) { }
        }
        return result.ToArray();
    }

    private static AutomationElement Resolve(WorkerRequest request)
    {
        if (request.RuntimeId == null) throw new PilotException("invalid_arguments", "요소 참조가 필요합니다.");
        foreach (var element in Walk((nint)request.Window.Hwnd))
        {
            if (!element.GetRuntimeId().SequenceEqual(request.RuntimeId)) continue;
            var c = element.Current;
            if (!c.IsEnabled || c.IsPassword) throw new PilotException("blocked_element", "비활성 또는 암호 요소입니다.");
            var r = c.BoundingRectangle;
            var bounds = r.IsEmpty ? new Bounds(0, 0, 0, 0) : new Bounds((int)r.X, (int)r.Y, (int)r.Width, (int)r.Height);
            if (request.ExpectedBounds != null && request.ExpectedBounds != bounds)
                throw new PilotException("stale_element", "요소 위치가 바뀌었습니다.");
            return element;
        }
        throw new PilotException("stale_element", "이전 요소가 없어졌습니다. 이름으로 대체하지 않습니다.");
    }

    public static void EnsureFocused(WorkerRequest request)
    {
        if (!Resolve(request).Current.HasKeyboardFocus)
            throw new PilotException("focus_lost", "관찰한 입력 요소에 포커스가 없습니다.");
    }

    public static WorkerResult Act(WorkerRequest request)
    {
        var a = request.Action ?? throw new PilotException("invalid_arguments", "동작이 필요합니다.");
        Broker.ValidateAction(a);
        Native.Validate(request.Window);
        using var mutex = new Mutex(false, $"Local\\WindowsPilot.Target.{request.Window.Pid}");
        bool acquired = false;
        try
        {
            try { acquired = mutex.WaitOne(2000); } catch (AbandonedMutexException) { acquired = true; }
            if (!acquired) throw new PilotException("target_busy", "같은 앱의 다른 작업이 실행 중입니다.");
            Native.Validate(request.Window);
            using var cancellation = EventWaitHandle.OpenExisting(request.CancelEvent!);
            if (cancellation.WaitOne(0)) throw new PilotException("interrupted", "실행 전에 취소됐습니다.");
            if (a.Type is "click" or "drag" or "key") return PhysicalInput.Run(request, cancellation);
            var element = Resolve(request);
            var before = Native.GetForegroundWindow();
            bool verified = false;
            string backend = "uia";
            if (a.Type == "set_value")
            {
                if (!element.TryGetCurrentPattern(ValuePattern.Pattern, out var p))
                    throw new PilotException("unsupported", "Value 패턴을 지원하지 않습니다.");
                var control = (nint)element.Current.NativeWindowHandle;
                var className = new System.Text.StringBuilder(256);
                Native.GetClassName(control, className, className.Capacity);
                // 기본 Edit의 UIA 공급자는 SetValue 중 포커스를 바꿀 수 있다.
                if (control != 0 && (className.ToString().Equals("Edit", StringComparison.OrdinalIgnoreCase) ||
                    className.ToString().StartsWith("WindowsForms10.EDIT.", StringComparison.OrdinalIgnoreCase)))
                {
                    backend = "win32_edit";
                    if (Native.SendMessageTimeout(control, 0x000C, 0, a.Value!, 3, 1500, out var accepted) == 0 || accepted == 0)
                        return new("outcome_unknown", "WM_SETTEXT 결과가 불명확합니다. 재시도 전에 관찰하세요.", Backend: backend);
                }
                else ((ValuePattern)p).SetValue(a.Value!);
                verified = ((ValuePattern)p).Current.Value == a.Value;
            }
            else if (a.Type == "invoke")
            {
                if (!element.TryGetCurrentPattern(InvokePattern.Pattern, out var p))
                    throw new PilotException("unsupported", "Invoke 패턴을 지원하지 않습니다.");
                ((InvokePattern)p).Invoke();
            }
            else throw new PilotException("unsupported", "지원하지 않는 동작입니다.");
            bool changed = before != Native.GetForegroundWindow();
            if (changed && a.ForegroundPolicy == "never")
                return new("interference_detected", "앱 또는 사용자 동작으로 전경이 바뀌었습니다. 동작은 이미 실행됐을 수 있습니다.", Verified: verified, ForegroundChanged: true, Backend: backend);
            return new(verified ? "completed" : "dispatched_unverified",
                verified ? "UIA 값을 다시 읽어 일치를 확인했습니다." : "Invoke 전달 후 작업 완료는 별도 관찰이 필요합니다.",
                Verified: verified, ForegroundChanged: changed, Backend: backend);
        }
        finally { if (acquired) mutex.ReleaseMutex(); }
    }
}
