using System.Windows.Forms;
using System.Drawing;

namespace WindowsPilot;

internal static class Fixture
{
    public static void Run(string name)
    {
        ApplicationConfiguration.Initialize();
        var form = new Form { Text = "Windows Pilot Fixture " + name, Width = 480, Height = 340, StartPosition = FormStartPosition.Manual,
            Location = name == "A" ? new Point(80, 100) : new Point(600, 100) };
        var edit = new TextBox { Name = "PilotValue", AccessibleName = "PilotValue", Left = 30, Top = 30, Width = 380, Text = "initial-" + name };
        var button = new Button { Name = "PilotButton", AccessibleName = "PilotButton", Text = "Count", Left = 30, Top = 75, Width = 120 };
        var counter = new Label { Name = "PilotCount", Text = "Count:0", Left = 170, Top = 80, Width = 200 };
        int clicks = 0;
        button.Click += (_, _) => { counter.Text = "Count:" + ++clicks; edit.Focus(); };
        var panel = new Panel { Name = "PilotCanvas", AccessibleName = "PilotCanvas", Left = 30, Top = 120, Width = 380, Height = 140, BackColor = Color.White };
        Point? last = null;
        var lines = new List<(Point From, Point To)>();
        var strokes = new Label { Name = "PilotStrokes", Text = "Segments:0;Held:False", Left = 30, Top = 265, Width = 380 };
        panel.Paint += (_, e) => { foreach (var line in lines) e.Graphics.DrawLine(Pens.DarkBlue, line.From, line.To); };
        panel.MouseDown += (_, e) => last = e.Location;
        panel.MouseMove += (_, e) => { if (e.Button == MouseButtons.Left && last != null) { lines.Add((last.Value, e.Location)); last = e.Location; panel.Invalidate(); strokes.Text = $"Segments:{lines.Count};Held:True"; } };
        panel.MouseUp += (_, _) => { last = null; strokes.Text = $"Segments:{lines.Count};Held:False"; };
        form.Controls.AddRange([edit, button, counter, panel, strokes]);
        System.Windows.Forms.Application.Run(form);
    }
}
