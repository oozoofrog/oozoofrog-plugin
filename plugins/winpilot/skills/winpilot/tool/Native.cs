using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text;

namespace WindowsPilot;

internal static class Native
{
    [StructLayout(LayoutKind.Sequential)] internal struct Rect { public int Left, Top, Right, Bottom; }
    [StructLayout(LayoutKind.Sequential)] internal struct Point { public int X, Y; }
    [StructLayout(LayoutKind.Sequential)] internal struct Input { public uint Type; public InputUnion Data; }
    [StructLayout(LayoutKind.Explicit)] internal struct InputUnion
    {
        [FieldOffset(0)] public MouseInput Mouse;
        [FieldOffset(0)] public KeyboardInput Keyboard;
    }
    [StructLayout(LayoutKind.Sequential)] internal struct MouseInput
    { public int X, Y; public uint Data, Flags, Time; public nuint Extra; }
    [StructLayout(LayoutKind.Sequential)] internal struct KeyboardInput
    { public ushort Key, Scan; public uint Flags, Time; public nuint Extra; }
    internal delegate bool EnumProc(nint hwnd, nint param);
    [DllImport("user32.dll")] internal static extern bool EnumWindows(EnumProc callback, nint param);
    [DllImport("user32.dll")] internal static extern bool IsWindow(nint hwnd);
    [DllImport("user32.dll")] internal static extern bool IsWindowVisible(nint hwnd);
    [DllImport("user32.dll")] internal static extern bool IsWindowEnabled(nint hwnd);
    [DllImport("user32.dll")] internal static extern bool IsIconic(nint hwnd);
    [DllImport("user32.dll")] internal static extern uint GetWindowThreadProcessId(nint hwnd, out uint pid);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] internal static extern int GetWindowText(nint hwnd, StringBuilder text, int max);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] internal static extern int GetClassName(nint hwnd, StringBuilder text, int max);
    [DllImport("user32.dll", CharSet = CharSet.Unicode, SetLastError = true)] internal static extern nint SendMessageTimeout(nint hwnd, uint message, nuint wparam, string lparam, uint flags, uint timeout, out nuint result);
    [DllImport("user32.dll")] internal static extern bool GetWindowRect(nint hwnd, out Rect rect);
    [DllImport("dwmapi.dll")] internal static extern int DwmGetWindowAttribute(nint hwnd, int attribute, out Rect rect, int size);
    [DllImport("user32.dll")] internal static extern nint GetForegroundWindow();
    [DllImport("user32.dll")] internal static extern bool SetForegroundWindow(nint hwnd);
    [DllImport("user32.dll")] internal static extern bool ShowWindow(nint hwnd, int command);
    [DllImport("user32.dll")] internal static extern bool SetWindowPos(nint hwnd, nint after, int x, int y, int width, int height, uint flags);
    [DllImport("user32.dll", EntryPoint = "SendMessageTimeoutW", SetLastError = true)] internal static extern nint SendMessageValue(nint hwnd, uint message, nuint wp, nint lp, uint flags, uint timeout, out nuint result);
    [DllImport("user32.dll")] internal static extern nint WindowFromPoint(Point point);
    [DllImport("user32.dll")] internal static extern nint GetAncestor(nint hwnd, uint flags);
    [DllImport("user32.dll")] internal static extern bool GetCursorPos(out Point point);
    [DllImport("user32.dll")] internal static extern short GetAsyncKeyState(int key);
    [DllImport("user32.dll")] internal static extern uint MapVirtualKey(uint code, uint mapType);
    [DllImport("user32.dll", SetLastError = true)] internal static extern uint SendInput(uint count, Input[] inputs, int size);
    [DllImport("user32.dll")] internal static extern int GetSystemMetrics(int index);
    [DllImport("user32.dll", SetLastError = true)] private static extern nint OpenInputDesktop(uint flags, bool inherit, uint access);
    [DllImport("user32.dll")] private static extern bool CloseDesktop(nint desktop);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] private static extern bool GetUserObjectInformation(nint handle, int index, StringBuilder info, int size, out uint needed);
    [DllImport("user32.dll")] private static extern nint GetThreadDesktop(uint id);
    [DllImport("kernel32.dll")] private static extern uint GetCurrentThreadId();
    [DllImport("kernel32.dll", SetLastError = true)] private static extern nint OpenProcess(uint access, bool inherit, int pid);
    [DllImport("kernel32.dll")] private static extern bool CloseHandle(nint handle);
    [DllImport("advapi32.dll", SetLastError = true)] private static extern bool OpenProcessToken(nint process, uint access, out nint token);
    [DllImport("advapi32.dll", SetLastError = true)] private static extern bool GetTokenInformation(nint token, int kind, nint data, uint size, out uint needed);
    [DllImport("advapi32.dll")] private static extern nint GetSidSubAuthorityCount(nint sid);
    [DllImport("advapi32.dll")] private static extern nint GetSidSubAuthority(nint sid, uint index);
    [DllImport("user32.dll")] internal static extern bool SetProcessDpiAwarenessContext(nint context);

    public static void CheckDesktop()
    {
        var desktop = OpenInputDesktop(0, false, 1);
        if (desktop == 0) throw new PilotException("blocked_desktop", "입력 데스크톱에 접근할 수 없습니다.");
        try
        {
            var active = new StringBuilder(256);
            var current = new StringBuilder(256);
            if (!GetUserObjectInformation(desktop, 2, active, 512, out _) ||
                !GetUserObjectInformation(GetThreadDesktop(GetCurrentThreadId()), 2, current, 512, out _) ||
                active.ToString() != "Default" || active.ToString() != current.ToString())
                throw new PilotException("blocked_desktop", "잠금 또는 다른 데스크톱에서는 실행하지 않습니다.");
        }
        finally { CloseDesktop(desktop); }
    }

    internal static int Integrity(int pid)
    {
        nint process = OpenProcess(0x1000, false, pid), token = 0, data = 0;
        try
        {
            if (process == 0 || !OpenProcessToken(process, 8, out token))
                throw new PilotException("integrity_unverified", "프로세스 입력 권한 수준을 확인하지 못했습니다.");
            GetTokenInformation(token, 25, 0, 0, out uint size);
            if (size == 0 || size > 65536) throw new PilotException("integrity_unverified", "잘못된 토큰 정보 크기입니다.");
            data = Marshal.AllocHGlobal((int)size);
            if (!GetTokenInformation(token, 25, data, size, out _)) throw new PilotException("integrity_unverified", "권한 정보 조회 실패입니다.");
            var sid = Marshal.ReadIntPtr(data);
            byte count = Marshal.ReadByte(GetSidSubAuthorityCount(sid));
            if (count == 0) throw new PilotException("integrity_unverified", "권한 SID가 비어 있습니다.");
            return Marshal.ReadInt32(GetSidSubAuthority(sid, (uint)count - 1));
        }
        finally
        {
            if (data != 0) Marshal.FreeHGlobal(data);
            if (token != 0) CloseHandle(token);
            if (process != 0) CloseHandle(process);
        }
    }

    public static Bounds GetBounds(nint hwnd)
    {
        if (DwmGetWindowAttribute(hwnd, 9, out var r, Marshal.SizeOf<Rect>()) != 0 && !GetWindowRect(hwnd, out r))
            throw new PilotException("target_gone", "창 경계를 읽지 못했습니다.");
        return new(r.Left, r.Top, r.Right - r.Left, r.Bottom - r.Top);
    }

    public static WindowInfo Describe(nint hwnd, string id = "")
    {
        if (!IsWindow(hwnd)) throw new PilotException("target_gone", "창이 닫혔습니다.");
        GetWindowThreadProcessId(hwnd, out var pid);
        using var process = Process.GetProcessById((int)pid);
        var title = new StringBuilder(1024);
        GetWindowText(hwnd, title, title.Capacity);
        return new(id, hwnd, (int)pid, process.StartTime.ToUniversalTime().Ticks,
            process.ProcessName, title.ToString(), GetBounds(hwnd), IsIconic(hwnd), GetForegroundWindow() == hwnd);
    }

    public static WindowInfo[] List()
    {
        CheckDesktop();
        var list = new List<WindowInfo>();
        EnumWindows((hwnd, _) =>
        {
            if (IsWindowVisible(hwnd))
                try { var w = Describe(hwnd); if (w.Bounds.Width > 0 && w.Bounds.Height > 0) list.Add(w); }
                catch (Exception) { /* 접근할 수 없는 프로세스는 입력 대상으로 등록하지 않는다. */ }
            return true;
        }, 0);
        return list.ToArray();
    }

    public static void Validate(WindowInfo expected, bool geometry = true)
    {
        CheckDesktop();
        var current = Describe((nint)expected.Hwnd);
        if (current.Pid != expected.Pid || current.Started != expected.Started || current.Process != expected.Process)
            throw new PilotException("target_changed", "창 소유 프로세스가 변경됐습니다.");
        if (geometry && current.Bounds != expected.Bounds)
            throw new PilotException("stale_observation", "창 위치 또는 크기가 변경됐습니다. 다시 관찰하세요.");
        if (!IsWindowEnabled((nint)expected.Hwnd))
            throw new PilotException("blocked_modal", "대상 창이 비활성화됐습니다. 모달 창을 확인하세요.");
    }

    internal static void Send(params Input[] inputs)
    {
        if (inputs.Any(input => input.Type > 1 || input.Type == 0 && input.Data.Mouse.Flags != 4 && !InputNotice.Visible))
            throw new PilotException("physical_pointer_forbidden", "마우스 입력에는 표시 중인 전경 제어 안내가 필요합니다.");
        if (SendInput((uint)inputs.Length, inputs, Marshal.SizeOf<Input>()) != inputs.Length)
            throw new PilotException("input_rejected", "입력 전달이 실패하거나 일부만 전달됐습니다. 결과를 재관찰하세요.");
    }
    internal static Input Key(ushort key, bool up) => new()
    {
        Type = 1, Data = new() { Keyboard = new() { Key = key,
            Flags = (up ? 2u : 0u) | (key is >= 37 and <= 40 or 46 ? 1u : 0u), Extra = 0x5750494C } }
    };
    internal static Input MouseButton(bool up) => new() { Type = 0, Data = new() { Mouse = new() { Flags = up ? 4u : 2u, Extra = 0x5750494C } } };
    internal static Input MouseMove(int x, int y)
    {
        int left = GetSystemMetrics(76), top = GetSystemMetrics(77), width = GetSystemMetrics(78), height = GetSystemMetrics(79);
        if (width < 2 || height < 2 || x < left || y < top || (long)x >= (long)left + width || (long)y >= (long)top + height)
            throw new PilotException("invalid_coordinates", "가상 데스크톱 밖의 좌표입니다.");
        return new() { Type = 0, Data = new() { Mouse = new() { X = (int)(((long)x - left) * 65536 / width + 32768 / width),
            Y = (int)(((long)y - top) * 65536 / height + 32768 / height), Flags = 0xC001, Extra = 0x5750494C } } };
    }
}
