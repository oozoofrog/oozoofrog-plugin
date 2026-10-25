using System.Drawing;
using System.Drawing.Imaging;
using System.IO;
using System.Runtime.InteropServices;

namespace WindowsPilot;

internal static class GameSettings
{
    public static bool IsOpen(CaptureInfo capture)
    {
        using var stream = new MemoryStream(Convert.FromBase64String(capture.PngBase64));
        using var bitmap = new Bitmap(stream);
        using var header = new Bitmap(Path.Combine(AppContext.BaseDirectory, "settings-header.png"));
        return IsOpen(bitmap, header);
    }

    internal static bool IsOpen(Bitmap current, Bitmap header)
    {
        var gear = Components(header).OrderByDescending(c => c.Pixels.Count).First();
        foreach (var c in Components(current).Where(c => Similar(c, gear)))
        {
            foreach (double adjustment in new[] { 1.0, .97, 1.03, .94, 1.06 })
            {
                double scale = c.Bounds.Width / (double)gear.Bounds.Width * adjustment;
                using var scaled = new Bitmap((int)(header.Width * scale), (int)(header.Height * scale));
                using (var g = Graphics.FromImage(scaled))
                    g.DrawImage(header, new Rectangle(0, 0, scaled.Width, scaled.Height), 0, 0, header.Width, header.Height, GraphicsUnit.Pixel);
                var mask = new bool[scaled.Width * scaled.Height];
                for (int y = 0; y < scaled.Height; y++)
                for (int x = 0; x < scaled.Width; x++) mask[y * scaled.Width + x] = White(scaled.GetPixel(x, y));
                for (int dy = -2; dy <= 2; dy++)
                for (int dx = -2; dx <= 2; dx++)
                {
                    int left = c.Bounds.X - (int)(gear.Bounds.X * scale) + dx, top = c.Bounds.Y - (int)(gear.Bounds.Y * scale) + dy;
                    if (left < 0 || top < 0 || left + scaled.Width >= current.Width || top + scaled.Height >= current.Height) continue;
                    int overlap = 0, total = 0;
                    for (int y = 0; y < scaled.Height; y++)
                    for (int x = 0; x < scaled.Width; x++)
                    {
                        bool a = mask[y * scaled.Width + x]; bool b = White(current.GetPixel(left + x, top + y));
                        if (a) total++; if (b) total++; if (a && b) overlap++;
                    }
                    // 실제 게임의 반응형 UI는 글자를 다시 렌더링하므로 단순 확대와 다른 가장자리를 허용한다.
                    if (total > 0 && 2.0 * overlap / total >= .84) return true;
                }
            }
        }
        return false;
    }
    private static bool White(Color color) => Math.Min(color.R, Math.Min(color.G, color.B)) >= 170 &&
        Math.Max(color.R, Math.Max(color.G, color.B)) - Math.Min(color.R, Math.Min(color.G, color.B)) <= 65;

    public static Point Locate(CaptureInfo capture)
    {
        string reference = Path.Combine(AppContext.BaseDirectory, "settings-icon.png");
        if (!File.Exists(reference)) throw new PilotException("reference_missing", "설정 버튼 기준 이미지가 없어요");
        using var expected = new Bitmap(reference);
        using var stream = new MemoryStream(Convert.FromBase64String(capture.PngBase64));
        using var current = new Bitmap(stream);
        return Locate(current, expected);
    }

    // 배포에는 아이콘 표본만 포함한다. 입력 좌표는 현재 화면에서 찾는다.
    internal static Point Locate(Bitmap current, Bitmap expected)
    {
        var sample = Components(expected).OrderByDescending(c => c.Pixels.Count).FirstOrDefault()
            ?? throw new PilotException("reference_invalid", "설정 아이콘 표본이 올바르지 않아요");
        var candidates = Components(current).Where(c => Similar(c, sample)).ToArray();
        if (candidates.Length == 0) throw new PilotException("target_unrecognized", "현재 화면에서 설정 아이콘을 찾지 못했어요");
        if (candidates.Length != 1) throw new PilotException("target_ambiguous", "설정 아이콘이 여러 개라 중단했어요");
        var b = candidates[0].Bounds;
        return new(b.X + b.Width / 2, b.Y + b.Height / 2);
    }

    private sealed record Component(Rectangle Bounds, HashSet<Point> Pixels);

    private static bool Similar(Component candidate, Component sample)
    {
        var a = candidate.Bounds; var b = sample.Bounds;
        double scale = a.Width / (double)b.Width;
        // shortcut: 0.6~3배의 동일한 밝은 톱니 아이콘만 인식한다. 다른 스킨은 실제 표본을 추가한다.
        if (scale < .6 || scale > 3 || Math.Abs(a.Height / (double)b.Height / scale - 1) > .15) return false;
        int overlap = 0, total = 0;
        for (int y = 0; y < 40; y++)
        for (int x = 0; x < 40; x++)
        {
            bool left = candidate.Pixels.Contains(new(a.X + x * a.Width / 40, a.Y + y * a.Height / 40));
            bool right = sample.Pixels.Contains(new(b.X + x * b.Width / 40, b.Y + y * b.Height / 40));
            if (left) total++; if (right) total++; if (left && right) overlap++;
        }
        return total > 0 && 2.0 * overlap / total >= .88;
    }

    private static List<Component> Components(Bitmap source)
    {
        if ((long)source.Width * source.Height > 40_000_000) throw new PilotException("image_too_large", "화면 크기가 처리 범위를 넘었어요");
        using var bitmap = new Bitmap(source.Width, source.Height, PixelFormat.Format32bppArgb);
        using (var graphics = Graphics.FromImage(bitmap))
            graphics.DrawImage(source, new Rectangle(0, 0, source.Width, source.Height), 0, 0, source.Width, source.Height, GraphicsUnit.Pixel);
        int width = bitmap.Width, height = bitmap.Height;
        var data = bitmap.LockBits(new(0, 0, width, height), ImageLockMode.ReadOnly, PixelFormat.Format32bppArgb);
        var bytes = new byte[data.Stride * height];
        try { Marshal.Copy(data.Scan0, bytes, 0, bytes.Length); }
        finally { bitmap.UnlockBits(data); }
        var bright = new bool[width * height];
        for (int y = 0; y < height; y++)
        for (int x = 0; x < width; x++)
        {
            int i = y * data.Stride + x * 4;
            int min = Math.Min(bytes[i], Math.Min(bytes[i + 1], bytes[i + 2]));
            int max = Math.Max(bytes[i], Math.Max(bytes[i + 1], bytes[i + 2]));
            bright[y * width + x] = min >= 170 && max - min <= 65;
        }
        var found = new List<Component>(); var queue = new Queue<int>();
        for (int index = 0; index < bright.Length; index++)
        {
            if (!bright[index]) continue;
            bright[index] = false; queue.Enqueue(index);
            int left = width, top = height, right = 0, bottom = 0, count = 0;
            var points = new HashSet<Point>();
            while (queue.TryDequeue(out int p))
            {
                int x = p % width, y = p / width;
                left = Math.Min(left, x); top = Math.Min(top, y); right = Math.Max(right, x); bottom = Math.Max(bottom, y);
                if (++count <= 20000) points.Add(new(x, y));
                for (int dy = -1; dy <= 1; dy++)
                for (int dx = -1; dx <= 1; dx++)
                {
                    int nx = x + dx, ny = y + dy;
                    if (nx < 0 || ny < 0 || nx >= width || ny >= height) continue;
                    int next = ny * width + nx;
                    if (bright[next]) { bright[next] = false; queue.Enqueue(next); }
                }
            }
            if (count >= 12 && count <= 20000 && right - left >= 7 && bottom - top >= 7)
                found.Add(new(Rectangle.FromLTRB(left, top, right + 1, bottom + 1), points));
        }
        return found;
    }
}
