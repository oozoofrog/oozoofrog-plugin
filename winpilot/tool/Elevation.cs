using System.IO;
using System.Runtime.InteropServices;

namespace WindowsPilot;

internal static class Elevation
{
    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    private struct ShellExecuteInfo
    {
        public uint Size, Mask;
        public nint Window;
        public string? Verb, File, Parameters, Directory;
        public int Show;
        public nint Instance, IdList;
        public string? Class;
        public nint ClassKey;
        public uint HotKey;
        public nint Icon, Process;
    }
    [DllImport("shell32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern bool ShellExecuteExW(ref ShellExecuteInfo info);
    [DllImport("kernel32.dll")] private static extern uint GetProcessId(nint process);
    [DllImport("kernel32.dll")] private static extern bool CloseHandle(nint handle);
    [DllImport("ole32.dll")] private static extern int CoInitializeEx(nint reserved, uint flags);
    [DllImport("ole32.dll")] private static extern void CoUninitialize();

    public static object RequestGameClick(string path)
    {
        path = Path.GetFullPath(path);
        var (plan, hash) = GameClickPlan.Load(path);
        plan.ValidateTarget(plan.Window);
        if (plan.Window.Process != "MabinogiMobile") throw new PilotException("invalid_plan", "마비노기 모바일 관찰이 필요합니다.");
        var current = Native.Describe((nint)plan.Window.Hwnd);
        plan.ValidateTarget(current);
        Native.Validate(plan.Window);
        return Launch($"--verify-game-click \"{path}\" {hash}", hash);
    }

    public static object RequestGameSettings()
    {
        var games = Native.List().Where(w => w.Process == "MabinogiMobile").ToArray();
        if (games.Length != 1) throw new PilotException("target_ambiguous", "마비노기 모바일 창이 정확히 하나여야 합니다.");
        var game = games[0];
        Native.Validate(game);
        return Launch($"--verify-game {game.Pid} {game.Started}", null);
    }

    private static object Launch(string parameters, string? hash)
    {
        string executable = Environment.ProcessPath!;
        if (Path.GetFileNameWithoutExtension(executable) != "windows-pilot")
            throw new PilotException("unsupported", "배포된 windows-pilot.exe로 실행하세요.");
        var info = new ShellExecuteInfo
        {
            Size = (uint)Marshal.SizeOf<ShellExecuteInfo>(),
            // 프로세스 handle 반환·동기 launch·오류 대화상자 억제. Windows UAC 승인은 유지한다.
            Mask = 0x40 | 0x100 | 0x400,
            Verb = "runas", File = executable,
            Parameters = parameters,
            Directory = AppContext.BaseDirectory, Show = 0
        };
        int apartment = CoInitializeEx(0, 0x2 | 0x4);
        if (apartment < 0) Marshal.ThrowExceptionForHR(apartment);
        bool launched;
        int error;
        try { launched = ShellExecuteExW(ref info); error = Marshal.GetLastWin32Error(); }
        finally { CoUninitialize(); }
        if (!launched)
        {
            throw new PilotException(error == 1223 ? "uac_cancelled" : "elevation_failed", $"Windows 관리자 실행 요청 실패 (Win32 {error}).");
        }
        try
        {
            if (info.Process == 0) throw new PilotException("elevation_unverified", "실행 프로세스 handle을 받지 못했습니다. 재실행하지 말고 기록을 확인하세요.");
            return new { status = "elevated_process_started", runner_pid = GetProcessId(info.Process), plan_sha256 = hash, verified = false };
        }
        finally { if (info.Process != 0) CloseHandle(info.Process); }
    }
}
