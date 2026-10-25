namespace WindowsPilot;

internal static class PhysicalInput
{
    public static WorkerResult Run(WorkerRequest request, EventWaitHandle cancellation)
    {
        var a = request.Action!;
        if (a.Type is not ("key" or "click" or "drag")) throw new PilotException("unsupported", "지원하지 않는 전경 입력입니다.");
        if (a.ForegroundPolicy != "allow") throw new PilotException("foreground_required", "실제 입력에는 전경 사용 허용이 필요합니다.");
        using var mutex = new Mutex(false, "Local\\WindowsPilot.PhysicalInput");
        bool acquired = false;
        bool keyDown = false;
        bool mouseDown = false;
        bool releaseFailed = false;
        bool completed = false;
        bool activateByClick = false;
        InputNotice? notice = null;
        try
        {
            try { acquired = mutex.WaitOne(2000); } catch (AbandonedMutexException) { acquired = true; }
            if (!acquired) throw new PilotException("desktop_busy", "다른 전경 입력이 실행 중입니다.");
            Native.Validate(request.Window);
            if (Native.Integrity(request.Window.Pid) > Native.Integrity(Environment.ProcessId))
                throw new PilotException("elevation_required", "대상 앱의 권한 수준이 더 높습니다. 입력하지 않았습니다. 같은 권한의 전용 실행 프로세스가 필요합니다.");
            if (Native.IsIconic((nint)request.Window.Hwnd)) throw new PilotException("minimized", "최소화 창은 자동 복원하지 않습니다.");
            foreach (int k in new[] { 1, 2, 4, 16, 17, 18, 91, 92 })
                if (Native.GetAsyncKeyState(k) < 0) throw new PilotException("user_input_active", "사용자가 버튼 또는 조합 키를 누르고 있습니다.");
            if (a.Type == "key" && Native.GetAsyncKeyState(a.VirtualKey!.Value) < 0)
                throw new PilotException("user_input_active", "대상 키가 이미 눌려 있습니다.");
            if (cancellation.WaitOne(0)) throw new PilotException("interrupted", "취소됐습니다.");
            notice = new InputNotice(cancellation, request.Window);
            if (cancellation.WaitOne(800)) throw new PilotException("interrupted", "안내 중 사용자 입력 또는 중지 요청을 감지했습니다. " + notice.InterruptDetail);
            notice.Stage("대상 창 활성화 중");
            if (Native.GetForegroundWindow() != (nint)request.Window.Hwnd)
            {
                if (!Native.SetForegroundWindow((nint)request.Window.Hwnd))
                {
                    // 전경 권한이 없으면 확인된 제목 표시줄을 정상 클릭해 활성화한다.
                    var hwnd = (nint)request.Window.Hwnd;
                    Native.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x13);
                    bool activated = false;
                    string activationDetail = "";
                    foreach (int offset in new[] { 120, request.Window.Bounds.Width / 2 })
                    {
                        int px = request.Window.Bounds.X + offset, py = request.Window.Bounds.Y + 14;
                        if (cancellation.WaitOne(0)) throw new PilotException("interrupted", "활성화 전에 중지됐습니다.");
                        Native.Validate(request.Window);
                        if (Native.GetAncestor(Native.WindowFromPoint(new() { X = px, Y = py }), 2) != hwnd) { activationDetail = "제목 표시줄이 다른 창에 가려졌습니다."; continue; }
                        var coordinate = unchecked((nint)((px & 65535) | (py << 16)));
                        if (Native.SendMessageValue(hwnd, 0x84, 0, coordinate, 3, 200, out var hit) == 0 || hit != 2) continue;
                        Native.Send(Native.MouseMove(px, py));
                        if (cancellation.WaitOne(30)) throw new PilotException("interrupted", "제목 표시줄 활성화 전에 중지됐습니다.");
                        Native.GetCursorPos(out var positioned);
                        if (positioned.X != px || positioned.Y != py) { activationDetail = "제목 표시줄로 커서를 이동하지 못했습니다."; continue; }
                        Native.Validate(request.Window);
                        if (Native.GetAncestor(Native.WindowFromPoint(positioned), 2) != hwnd) { activationDetail = "제목 표시줄이 다른 창에 가려졌습니다."; continue; }
                        mouseDown = true;
                        Native.Send(Native.MouseButton(false), Native.MouseButton(true));
                        mouseDown = false;
                        Thread.Sleep(100);
                        Native.GetCursorPos(out var actualPoint);
                        activationDetail = $"제목 표시줄 ({px},{py}), 실제 커서 ({actualPoint.X},{actualPoint.Y}), 전경 HWND {Native.GetForegroundWindow()}.";
                        activated = Native.GetForegroundWindow() == hwnd;
                        if (activated) break;
                    }
                    if (!activated)
                    {
                        if (a.Type != "click") throw new PilotException("foreground_denied", "전경 전환과 확인된 제목 표시줄 활성화에 실패했습니다. " + activationDetail);
                        activateByClick = true;
                    }
                }
                Thread.Sleep(100);
            }
            Check(request, cancellation, !activateByClick);
            notice.Stage(a.Type == "drag" ? "드래그 실행 중" : a.Type == "click" ? "클릭 실행 중" : "키 입력 실행 중");
            if (a.Type == "key")
            {
                if (a.KeyTarget == "element") Automation.EnsureFocused(request);
                // shortcut: 단일 가상 키만 지원한다. 게임별 scan code 검증 후 별도 입력 형식을 추가한다.
                keyDown = true;
                Native.Send(Native.Key((ushort)a.VirtualKey!.Value, false));
                Wait(request, cancellation, a.DurationMs);
            }
            else
            {
                int x = checked(request.Window.Bounds.X + a.X!.Value), y = checked(request.Window.Bounds.Y + a.Y!.Value);
                int endX = checked(request.Window.Bounds.X + (a.ToX ?? a.X).Value), endY = checked(request.Window.Bounds.Y + (a.ToY ?? a.Y).Value);
                void Move(int px, int py)
                {
                    Check(request, cancellation, !activateByClick);
                    var hit = Native.WindowFromPoint(new() { X = px, Y = py });
                    if (Native.GetAncestor(hit, 2) != (nint)request.Window.Hwnd)
                        throw new PilotException("target_obscured", $"입력 지점 ({px},{py})이 가려졌습니다. hit={hit}, root={Native.GetAncestor(hit, 2)}, foreground={Native.GetForegroundWindow()}, target={request.Window.Hwnd}");
                    Native.Send(Native.MouseMove(px, py));
                }
                Move(x, y);
                if (activateByClick)
                {
                    // 사용자 지정 제목 표시줄에서는 실제 요청 지점을 한 번만 눌러 활성화한다.
                    if (cancellation.WaitOne(30)) throw new PilotException("interrupted", "클릭 전에 중지됐습니다.");
                    Move(x, y);
                }
                else Wait(request, cancellation, 30);
                mouseDown = true;
                Native.Send(Native.MouseButton(false));
                if (activateByClick)
                {
                    if (cancellation.WaitOne(a.DurationMs)) throw new PilotException("interrupted", "클릭 중 중지됐습니다.");
                    // 활성화 클릭을 앱이 소비할 수도 있으므로 결과 관찰 없이 재클릭하지 않는다.
                    completed = true;
                    return new("dispatched_unverified", "활성화 클릭을 한 번 전달했습니다. 앱 결과를 재관찰하세요.", Verified: false);
                }
                int steps = a.Type == "drag" ? Math.Clamp(a.DurationMs / 16, 1, 120) : 1;
                for (int i = 1; i <= steps; i++)
                {
                    Wait(request, cancellation, Math.Max(1, a.DurationMs / steps));
                    if (a.Type == "drag") Move(x + (endX - x) * i / steps, y + (endY - y) * i / steps);
                }
            }
            completed = true;
        }
        finally
        {
            try
            {
                if (keyDown) Native.Send(Native.Key((ushort)a.VirtualKey!.Value, true));
                if (mouseDown) Native.Send(Native.MouseButton(true));
            }
            catch (Exception) { releaseFailed = true; }
            notice?.Finish(completed && !cancellation.WaitOne(0), releaseFailed);
            notice?.Dispose();
            if (acquired) mutex.ReleaseMutex();
            if (releaseFailed) throw new PilotException("release_unconfirmed", "입력 해제를 확인할 수 없습니다. 사용자가 키·버튼 상태를 확인해야 합니다.");
        }
        return new("dispatched_unverified", "전경 입력과 해제를 전달했습니다. 앱 결과를 재관찰하세요.", Verified: false);
    }

    private static void Check(WorkerRequest r, EventWaitHandle c, bool requireForeground = true)
    {
        if (c.WaitOne(0) || (Native.GetAsyncKeyState(17) < 0 && Native.GetAsyncKeyState(18) < 0 && Native.GetAsyncKeyState(123) < 0))
            throw new PilotException("interrupted", "중지 요청을 받았습니다.");
        if (!InputNotice.Visible) throw new PilotException("notice_unavailable", "입력 제어 안내가 사라져 중단했습니다.");
        Native.Validate(r.Window);
        if (requireForeground && Native.GetForegroundWindow() != (nint)r.Window.Hwnd)
            throw new PilotException("focus_lost", "포커스가 바뀌어 후속 입력을 중단했습니다.");
    }
    private static void Wait(WorkerRequest r, EventWaitHandle c, int milliseconds)
    {
        var until = Environment.TickCount64 + milliseconds;
        while (Environment.TickCount64 < until) { Check(r, c); Thread.Sleep(10); }
    }
}
