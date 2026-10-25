using System.Drawing;
using System.Runtime.InteropServices;
using System.Windows.Forms;

namespace WindowsPilot;

// 별도 UI 스레드가 안내·중지 버튼·사용자 입력 감지를 담당한다. 입력을 차단하지 않는다.
internal sealed class InputNotice : IDisposable
{
    private delegate nint Hook(int code, nint wp, nint lp);
    [DllImport("user32.dll", SetLastError = true)] private static extern nint SetWindowsHookExW(int kind, Hook callback, nint module, uint thread);
    [DllImport("user32.dll")] private static extern bool UnhookWindowsHookEx(nint hook);
    [DllImport("user32.dll")] private static extern nint CallNextHookEx(nint hook, int code, nint wp, nint lp);
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode)] private static extern nint GetModuleHandle(string? name);
    [StructLayout(LayoutKind.Sequential)] private struct MouseEvent { public Native.Point Point; public uint Data, Flags, Time; public nuint Extra; }
    [StructLayout(LayoutKind.Sequential)] private struct KeyEvent { public uint Key, Scan, Flags, Time; public nuint Extra; }
    private readonly ManualResetEventSlim ready = new(false);
    private readonly Thread thread;
    private readonly EventWaitHandle cancellation;
    private Form? border;
    private Exception? error;
    private Action<bool, bool>? finish;
    private Action<string>? stage;
    private static int visible;
    public static bool Visible => Volatile.Read(ref visible) == 1;
    public bool UserInterrupted { get; private set; }
    public string? InterruptDetail { get; private set; }
    public InputNotice(EventWaitHandle cancel, WindowInfo target)
    {
        cancellation = cancel;
        thread = new Thread(() => Run(target)) { IsBackground = true, Name = "WindowsPilot.InputNotice" };
        thread.SetApartmentState(ApartmentState.STA);
        thread.Start();
        if (!ready.Wait(3000) || error != null || !Visible)
        {
            Dispose();
            throw new PilotException("notice_unavailable", "화면 안내 또는 사용자 입력 감지를 시작하지 못했습니다. " + error?.Message);
        }
    }
    private void Run(WindowInfo target)
    {
        nint mouseHook = 0, keyHook = 0;
        Native.GetCursorPos(out var previousPoint);
        Hook mouse = (code, wp, lp) =>
        {
            if (code >= 0)
            {
                var input = Marshal.PtrToStructure<MouseEvent>(lp);
                bool moved = input.Point.X != previousPoint.X || input.Point.Y != previousPoint.Y;
                previousPoint = input.Point;
                if (input.Extra != 0x5750494C && (wp != 0x200 || moved))
                { UserInterrupted = true; InterruptDetail = $"mouse message={wp:X}, flags={input.Flags}, moved={moved}"; cancellation.Set(); }
            }
            return CallNextHookEx(0, code, wp, lp);
        };
        Hook keyboard = (code, wp, lp) =>
        {
            if (code >= 0 && Marshal.PtrToStructure<KeyEvent>(lp).Extra != 0x5750494C)
            { UserInterrupted = true; InterruptDetail = "keyboard input"; cancellation.Set(); }
            return CallNextHookEx(0, code, wp, lp);
        };
        try
        {
            using var frame = new PilotToast { Text = "Windows Pilot 입력 제어 중" };
            border = frame;
            frame.Place(target.Bounds);
            frame.SetStatus("Windows Pilot · 준비 중", "마우스와 키보드를 잠시 사용할게요");
            var stop = frame.Controls.OfType<Button>().Single();
            bool ended = false;
            stage = text => { if (!ended) frame.SetStatus("Windows Pilot · " + text, "직접 입력하면 자동으로 중지해요"); };
            stop.Click += (_, _) => { if (ended) frame.Close(); else cancellation.Set(); };
            finish = (completed, releaseFailed) =>
            {
                if (mouseHook != 0) { UnhookWindowsHookEx(mouseHook); mouseHook = 0; }
                if (keyHook != 0) { UnhookWindowsHookEx(keyHook); keyHook = 0; }
                Volatile.Write(ref visible, 0);
                ended = true;
                frame.Text = "Windows Pilot 제어 종료";
                frame.SetStatus(releaseFailed ? "입력 해제를 확인하지 못했어요" : completed ? "입력 전달이 끝났어요" : "자동 조작을 중단했어요",
                    releaseFailed ? "키·버튼 상태를 직접 확인해 주세요" : "이제 마우스와 키보드를 직접 사용하세요");
                frame.DismissAfter(2500);
            };
            frame.Shown += (_, _) =>
            {
                mouseHook = SetWindowsHookExW(14, mouse, GetModuleHandle(null), 0);
                keyHook = SetWindowsHookExW(13, keyboard, GetModuleHandle(null), 0);
                if (mouseHook == 0 || keyHook == 0) { error = new Exception("사용자 입력 감지 훅 등록 실패"); frame.Close(); }
                else Volatile.Write(ref visible, 1);
                ready.Set();
            };
            Application.Run(frame);
        }
        catch (Exception e) { error = e; ready.Set(); cancellation.Set(); }
        finally
        {
            Volatile.Write(ref visible, 0);
            if (mouseHook != 0) UnhookWindowsHookEx(mouseHook);
            if (keyHook != 0) UnhookWindowsHookEx(keyHook);
            GC.KeepAlive(mouse); GC.KeepAlive(keyboard);
        }
    }
    public void Stage(string text)
    {
        try { if (border is { IsHandleCreated: true, IsDisposed: false }) border.BeginInvoke(() => stage?.Invoke(text)); }
        catch (InvalidOperationException) { }
    }
    public void Finish(bool completed, bool releaseFailed)
    {
        try { if (border is { IsHandleCreated: true, IsDisposed: false }) border.BeginInvoke(() => finish?.Invoke(completed, releaseFailed)); }
        catch (InvalidOperationException) { }
        thread.Join(3000);
    }
    public void Dispose()
    {
        try { if (border is { IsHandleCreated: true, IsDisposed: false }) border.BeginInvoke(() => border.Close()); } catch (InvalidOperationException) { }
        thread.Join(1500);
        // UI 스레드가 늦게 끝나도 ready를 해제한 핸들에 접근하지 않게 한다.
        if (!thread.IsAlive) ready.Dispose();
    }
}
