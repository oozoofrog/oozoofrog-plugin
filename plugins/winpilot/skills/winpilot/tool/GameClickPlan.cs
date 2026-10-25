using System.Drawing;
using System.IO;

namespace WindowsPilot;

// 에이전트가 실제 화면에서 확인한 단일 버튼만 전달한다. 실행 명령이나 임의 키는 받지 않는다.
internal sealed record GameClickPlan(WindowInfo Window, DateTimeOffset ObservedAt, int X, int Y, string PngBase64, string Purpose)
{
    public static GameClickPlan Read(string path)
    {
        if (new FileInfo(path).Length > 12_000_000) throw new PilotException("invalid_plan", "관찰 파일이 너무 커요");
        return Json.Read<GameClickPlan>(File.ReadAllText(path));
    }

    public Point Validate(WindowInfo current, CaptureInfo capture)
    {
        var age = DateTimeOffset.UtcNow - ObservedAt;
        if (age < TimeSpan.Zero || age > TimeSpan.FromMinutes(2)) throw new PilotException("stale_observation", "화면을 다시 확인해야 해요");
        if (current.Pid != Window.Pid || current.Started != Window.Started || current.Hwnd != Window.Hwnd || current.Bounds != Window.Bounds)
            throw new PilotException("target_changed", "관찰 이후 대상 창이 바뀌었어요");
        if (Purpose.Length is < 1 or > 60) throw new PilotException("invalid_plan", "작업 설명이 올바르지 않아요");
        using var oldStream = new MemoryStream(Convert.FromBase64String(PngBase64));
        using var newStream = new MemoryStream(Convert.FromBase64String(capture.PngBase64));
        using var before = new Bitmap(oldStream); using var now = new Bitmap(newStream);
        if (!PatchMatches(before, now, X, Y)) throw new PilotException("target_changed", "확인했던 버튼이 바뀌어 중단했어요");
        return new(X, Y);
    }

    internal static bool PatchMatches(Bitmap before, Bitmap now, int x, int y)
    {
        if (before.Size != now.Size || x < 24 || y < 24 || x + 24 >= now.Width || y + 24 >= now.Height) return false;
        long difference = 0; int shapeChanges = 0, bright = 0, dark = 0;
        for (int dy = -24; dy <= 24; dy++)
        for (int dx = -24; dx <= 24; dx++)
        {
            var a = before.GetPixel(x + dx, y + dy); var b = now.GetPixel(x + dx, y + dy);
            difference += Math.Abs(a.R - b.R) + Math.Abs(a.G - b.G) + Math.Abs(a.B - b.B);
            bool white = Math.Min(a.R, Math.Min(a.G, a.B)) > 170;
            if (white) bright++; else dark++;
            if (white != (Math.Min(b.R, Math.Min(b.G, b.B)) > 170)) shapeChanges++;
        }
        // 빈 배경의 우연한 일치를 거부한다. 실제 의미 확인은 관찰한 에이전트의 책임이다.
        return bright >= 30 && dark >= 30 && difference / (2401.0 * 3) <= 18 && shapeChanges / 2401.0 <= .08;
    }
}
