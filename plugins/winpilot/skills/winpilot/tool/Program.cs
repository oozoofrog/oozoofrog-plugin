using System.Text;

namespace WindowsPilot;

internal static class Program
{
    [STAThread]
    public static int Main(string[] args)
    {
        Console.InputEncoding = new UTF8Encoding(false);
        Console.OutputEncoding = new UTF8Encoding(false);
        Native.SetProcessDpiAwarenessContext(-4);
        try
        {
            if (args is ["--fixture", var name]) { Fixture.Run(name); return 0; }
            if (args is ["--inspect-game-image", var imagePath])
            {
                using var bitmap = new System.Drawing.Bitmap(imagePath);
                using var header = new System.Drawing.Bitmap(System.IO.Path.Combine(AppContext.BaseDirectory, "settings-header.png"));
                using var reference = new System.Drawing.Bitmap(System.IO.Path.Combine(AppContext.BaseDirectory, "settings-icon.png"));
                bool open = GameSettings.IsOpen(bitmap, header);
                System.Drawing.Point? point = null;
                string status = open ? "settings_open" : "target_unrecognized";
                if (!open)
                {
                    try { point = GameSettings.Locate(bitmap, reference); status = "settings_icon"; }
                    catch (PilotException e) when (e.Code is "target_unrecognized" or "target_ambiguous") { status = e.Code; }
                }
                Console.WriteLine(Json.Write(new { status, bitmap.Width, bitmap.Height, point, native_input_sent = false }));
                return 0;
            }
            if (args is ["--verify-game-click", var planPath])
            {
                var plan = GameClickPlan.Read(planPath);
                ApplicationConfiguration.Initialize();
                System.Windows.Forms.Application.Run(new VerificationForm(plan.Window.Pid, plan.Window.Started, false, plan));
                return 0;
            }
            if (args is ["--verify-game" or "--verify-fixture" or "--verify-game-layout", var pid, var started])
            {
                ApplicationConfiguration.Initialize();
                System.Windows.Forms.Application.Run(new VerificationForm(int.Parse(pid), long.Parse(started), args[0] == "--verify-fixture", layoutOnly: args[0] == "--verify-game-layout"));
                return 0;
            }
            if (args is ["--self-test"]) { SelfTest.Run(); return 0; }
            if (args is ["--self-test-notice"]) { SelfTest.Notice(); return 0; }
            if (args is ["--worker"])
            {
                WorkerResult result;
                try
                {
                    var request = Json.Read<WorkerRequest>(Console.ReadLine() ?? "");
                    result = Task.Run(async () => request.Operation switch
                    {
                        "observe" => Observe(request),
                        "capture" => new WorkerResult("captured", Capture: await Capture.Take(request.Window)),
                        "action" => Automation.Act(request),
                        _ => throw new PilotException("unsupported", "잘못된 worker 명령입니다.")
                    }).GetAwaiter().GetResult();
                }
                catch (PilotException e) { result = new(e.Code, e.Message); }
                catch (Exception e) { result = new("worker_error", e.GetType().Name + ": " + e.Message); }
                Console.WriteLine(Json.Write(result));
                return 0;
            }
            if (args is ["--stdio"])
            {
                using var broker = new Broker();
                Console.CancelKeyPress += (_, e) => { e.Cancel = true; broker.Cancel(null); };
                return new Mcp(broker).Run().GetAwaiter().GetResult();
            }
            Console.WriteLine("WinPilot 0.5.0 (화면 안내와 사용자 입력 자동 중지)\n--stdio       MCP 서버\n--self-test   입력 없는 검사\n--fixture A   테스트 전용 창");
            return 0;
        }
        catch (Exception e) { Console.Error.WriteLine(e.Message); return 1; }
    }
    private static WorkerResult Observe(WorkerRequest request)
    {
        var items = Automation.Inspect(request.Window);
        return new("observed", Elements: items.Take(200).ToArray(), Truncated: items.Length > 200);
    }
}
