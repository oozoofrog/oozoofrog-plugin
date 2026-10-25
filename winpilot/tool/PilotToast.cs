using System.Drawing;
using System.Drawing.Drawing2D;
using System.Windows.Forms;

namespace WindowsPilot;

// 준비·입력·종료 안내가 같은 작은 표면을 사용한다. 포커스를 가져오지 않는다.
internal class PilotToast : Form
{
    private readonly Label heading;
    private readonly Label detail;
    protected readonly Button StopButton;
    private readonly System.Windows.Forms.Timer dismiss = new();
    protected override bool ShowWithoutActivation => true;
    protected override CreateParams CreateParams
    {
        get { var p = base.CreateParams; p.ExStyle |= 0x08000000 | 0x00000080; return p; }
    }
    public PilotToast()
    {
        AutoScaleMode = AutoScaleMode.None;
        FormBorderStyle = FormBorderStyle.None; ShowInTaskbar = false; TopMost = true;
        StartPosition = FormStartPosition.Manual; ClientSize = new(420, 88);
        BackColor = Color.FromArgb(29, 32, 39); ForeColor = Color.FromArgb(239, 242, 247);
        Opacity = SystemInformation.HighContrast ? 1 : .94;
        heading = new Label { Bounds = new(32, 12, 302, 26), Font = new Font("맑은 고딕", 14, FontStyle.Bold, GraphicsUnit.Pixel), ForeColor = ForeColor };
        detail = new Label { Bounds = new(32, 42, 302, 32), Font = new Font("맑은 고딕", 13, FontStyle.Regular, GraphicsUnit.Pixel), ForeColor = Color.FromArgb(176, 186, 201) };
        StopButton = new Button { Text = "중지", AccessibleName = "자동 조작 중지", Bounds = new(348, 21, 58, 44),
            Font = new Font("맑은 고딕", 13, FontStyle.Regular, GraphicsUnit.Pixel), FlatStyle = FlatStyle.Flat,
            ForeColor = ForeColor, BackColor = Color.FromArgb(42, 47, 57), TabStop = true };
        StopButton.FlatAppearance.BorderSize = 0;
        StopButton.FlatAppearance.MouseOverBackColor = Color.FromArgb(60, 68, 81);
        Controls.AddRange([heading, detail, StopButton]);
        using var shape = new GraphicsPath();
        shape.AddRoundedRectangle(new Rectangle(0, 0, Width, Height), new Size(16, 16));
        Region = new Region(shape);
        if (SystemInformation.HighContrast)
        { BackColor = SystemColors.Window; heading.ForeColor = detail.ForeColor = StopButton.ForeColor = SystemColors.WindowText; StopButton.BackColor = SystemColors.Window; }
        dismiss.Tick += (_, _) => { dismiss.Stop(); Close(); };
        FormClosed += (_, _) => dismiss.Dispose();
    }
    protected override void OnPaint(PaintEventArgs e)
    {
        base.OnPaint(e); e.Graphics.SmoothingMode = SmoothingMode.AntiAlias;
        using var dot = new SolidBrush(SystemInformation.HighContrast ? SystemColors.Highlight : Color.FromArgb(142, 177, 228));
        e.Graphics.FillEllipse(dot, 16, 21, 6, 6);
    }
    public void SetStatus(string title, string message)
    {
        heading.Text = title; detail.Text = message;
        heading.AccessibleName = title; detail.AccessibleName = message;
    }
    public void DismissAfter(int milliseconds)
    {
        StopButton.Text = "닫기"; StopButton.AccessibleName = "안내 닫기";
        dismiss.Interval = milliseconds; dismiss.Start();
    }
    public void Place(Bounds target, bool requireOutside = false)
    {
        var rect = new Rectangle(target.X, target.Y, target.Width, target.Height);
        var position = Outside(rect, Size, Screen.AllScreens.Select(s => s.WorkingArea));
        if (position == null && requireOutside) throw new PilotException("no_notice_space", "안내 공간이 없어 실행하지 않았어요.");
        var area = Screen.FromRectangle(rect).WorkingArea;
        Location = position?.Location ?? new Point(area.Right - Width - 16, area.Bottom - Height - 16);
    }
    internal static Rectangle? Outside(Rectangle target, Size size, IEnumerable<Rectangle> areas)
    {
        foreach (var r in areas)
        foreach (int left in new[] { r.Right - size.Width - 16, r.Left + 16, target.Right + 16, target.Left - size.Width - 16 })
        foreach (int top in new[] { r.Bottom - size.Height - 16, r.Top + 16, target.Bottom + 16, target.Top - size.Height - 16 })
        {
            var candidate = new Rectangle(new(left, top), size);
            if (r.Contains(candidate) && !candidate.IntersectsWith(target)) return candidate;
        }
        return null;
    }
}
