namespace WindowsPilot;

internal static class SelfTest
{
    public static void Notice()
    {
        using var cancel = new EventWaitHandle(false, EventResetMode.ManualReset);
        var target = new WindowInfo("test", 0, 0, 0, "화면 검사 · 입력 없음", "", new(800, 200, 800, 600), false, false);
        using var notice = new InputNotice(cancel, target);
        var windows = Native.List().Where(w => w.Pid == Environment.ProcessId).ToArray();
        if (windows.Any(w => w.Title == "Windows Pilot 제어 테두리")) throw new Exception("불필요한 화면 테두리가 남았습니다.");
        var toast = windows.Single(w => w.Title == "Windows Pilot 입력 제어 중");
        if (toast.Bounds.Width > 440 || toast.Bounds.Height > 100)
            throw new Exception("작은 상태 창을 확인하지 못했습니다.");
        var shot = Broker.Worker(new("capture", toast), 6000).GetAwaiter().GetResult();
        if (shot.Capture == null) throw new Exception("안내 캡처 실패");
        System.IO.File.WriteAllBytes(System.IO.Path.Combine(AppContext.BaseDirectory, "..", "notice-preview.png"), Convert.FromBase64String(shot.Capture.PngBase64));
        notice.Finish(false, false);
        Console.WriteLine(Json.Write(new { status = "passed", edge_windows = 0, toast.Bounds, native_input_sent = false }));
    }
    public static void Run()
    {
        int passed = 0;
        using (var icon = new System.Drawing.Bitmap(System.IO.Path.Combine(AppContext.BaseDirectory, "settings-icon.png")))
        using (var reference = new System.Drawing.Bitmap(900, 700))
        using (var blank = new System.Drawing.Bitmap(reference.Width, reference.Height))
        {
            using (var g = System.Drawing.Graphics.FromImage(reference))
                g.DrawImage(icon, new System.Drawing.Rectangle(39, 186, 28, 28), 0, 0, 28, 28, System.Drawing.GraphicsUnit.Pixel);
            var original = GameSettings.Locate(reference, icon);
            if (Math.Abs(original.X - 52) > 3 || Math.Abs(original.Y - 199) > 3) throw new Exception("원본 설정 아이콘 위치 오류"); passed++;
            Reject("blank image", () => GameSettings.Locate(blank, icon), "target_unrecognized");
            foreach (double scale in new[] { .75, 1.0, 1.25, 1.5, 2.0 })
            {
                using var relocated = new System.Drawing.Bitmap(900, 500);
                int size = (int)(28 * scale);
                using (var g = System.Drawing.Graphics.FromImage(relocated))
                {
                    g.Clear(System.Drawing.Color.FromArgb(30, 40, 50));
                    g.DrawImage(reference, new System.Drawing.Rectangle(700, 300, size, size), 39, 186, 28, 28, System.Drawing.GraphicsUnit.Pixel);
                }
                System.Drawing.Point found;
                try { found = GameSettings.Locate(relocated, icon); }
                catch (PilotException e) { throw new Exception($"크기 {scale}: {e.Code}"); }
                if (Math.Abs(found.X - (700 + size / 2)) > 4 || Math.Abs(found.Y - (300 + size / 2)) > 4)
                    throw new Exception($"이동·크기 변경 탐색 실패: {scale}");
                passed++;
            }
            using var duplicate = (System.Drawing.Bitmap)reference.Clone();
            using (var g = System.Drawing.Graphics.FromImage(duplicate))
                g.DrawImage(reference, new System.Drawing.Rectangle(500, 500, 28, 28), 39, 186, 28, 28, System.Drawing.GraphicsUnit.Pixel);
            Reject("ambiguous icons", () => GameSettings.Locate(duplicate, icon), "target_ambiguous");
            using (var g = System.Drawing.Graphics.FromImage(blank))
            { g.Clear(System.Drawing.Color.Black); g.FillEllipse(System.Drawing.Brushes.White, 400, 300, 25, 25); }
            Reject("unrelated white icon", () => GameSettings.Locate(blank, icon), "target_unrecognized");
            if (!GameClickPlan.PatchMatches(reference, reference, 52, 199)) throw new Exception("관찰 버튼 비교 실패"); passed++;
            if (GameClickPlan.PatchMatches(reference, blank, 52, 199)) throw new Exception("변경된 버튼 허용"); passed++;
            if (GameClickPlan.PatchMatches(blank, blank, 52, 199)) throw new Exception("빈 배경 허용"); passed++;
            using var header = new System.Drawing.Bitmap(System.IO.Path.Combine(AppContext.BaseDirectory, "settings-header.png"));
            if (GameSettings.IsOpen(reference, header)) throw new Exception("시작 화면을 설정 화면으로 오인"); passed++;
            using var noTitle = new System.Drawing.Bitmap(1000, 600);
            using (var g = System.Drawing.Graphics.FromImage(noTitle))
                g.DrawImage(header, new System.Drawing.Rectangle(400, 200, 32, header.Height), 0, 0, 32, header.Height, System.Drawing.GraphicsUnit.Pixel);
            if (GameSettings.IsOpen(noTitle, header)) throw new Exception("제목 없는 아이콘을 설정 화면으로 오인"); passed++;
            foreach (double scale in new[] { .75, 1.0, 1.25, 1.5, 2.0 })
            {
                using var panel = new System.Drawing.Bitmap(1000, 600);
                using (var g = System.Drawing.Graphics.FromImage(panel))
                    g.DrawImage(header, new System.Drawing.Rectangle(400, 200, (int)(header.Width * scale), (int)(header.Height * scale)), 0, 0, header.Width, header.Height, System.Drawing.GraphicsUnit.Pixel);
                if (!GameSettings.IsOpen(panel, header)) throw new Exception($"설정 결과 인식 실패 {scale}"); passed++;
            }
        }
        var area = new System.Drawing.Rectangle(0, 0, 1920, 1080);
        var game = new System.Drawing.Rectangle(700, 100, 1100, 900);
        var placement = PilotToast.Outside(game, new(420, 88), [area]);
        if (placement == null || placement.Value.IntersectsWith(game) || !area.Contains(placement.Value))
            throw new Exception("검증 창이 대상 게임을 가립니다.");
        passed++;
        if (PilotToast.Outside(area, new(420, 88), [area]) != null) throw new Exception("게임 밖 공간이 없는데 위치를 허용했습니다.");
        passed++;
        var secondMonitor = new System.Drawing.Rectangle(-1600, 0, 1600, 900);
        placement = PilotToast.Outside(area, new(420, 88), [area, secondMonitor]);
        if (placement == null || !secondMonitor.Contains(placement.Value)) throw new Exception("음수 좌표 보조 화면 배치 실패");
        passed++;
        void Reject(string label, Action action, string code)
        {
            try { action(); throw new Exception(label + ": 거부되지 않았습니다."); }
            catch (PilotException e) when (e.Code == code) { passed++; }
        }
        var a = new ActionArgs("w", "o", "r", "key", VirtualKey: 65);
        Reject("foreground never", () => Broker.ValidateAction(a), "foreground_required");
        Reject("unknown policy", () => Broker.ValidateAction(a with { ForegroundPolicy = "auto" }), "invalid_arguments");
        Reject("unbounded hold", () => Broker.ValidateAction(a with { ForegroundPolicy = "allow", DurationMs = 2001 }), "invalid_arguments");
        Reject("click without foreground approval", () => Broker.ValidateAction(a with { Type = "click", X = 1, Y = 1 }), "foreground_required");
        Reject("drag without foreground approval", () => Broker.ValidateAction(a with { Type = "drag", X = 1, Y = 1, ToX = 2, ToY = 2 }), "foreground_required");
        Broker.ValidateAction(a with { Type = "drag", ForegroundPolicy = "allow", X = 1, Y = 1, ToX = 2, ToY = 2 }); passed++;
        Reject("native mouse packet", () => Native.Send(new Native.Input { Type = 0 }), "physical_pointer_forbidden");
        Reject("unknown action", () => Broker.ValidateAction(a with { Type = "shell" }), "unsupported");
        Reject("windows key", () => Broker.ValidateAction(a with { Type = "key", ForegroundPolicy = "allow", VirtualKey = 91 }), "invalid_arguments");
        Reject("unassigned virtual key", () => Broker.ValidateAction(a with { Type = "key", ForegroundPolicy = "allow", VirtualKey = 58 }), "invalid_arguments");
        if (Native.Key(37, false).Data.Keyboard.Flags != 1 || Native.Key(37, true).Data.Keyboard.Flags != 3)
            throw new Exception("방향 키의 extended/key-up 플래그 오류");
        passed++;
        Reject("empty request id", () => Broker.ValidateAction(a with { RequestId = "" }), "invalid_arguments");
        Reject("unsupported expectation", () => Broker.ValidateAction(a with { ForegroundPolicy = "allow", ExpectedValue = "x" }), "unsupported");
        var w = new WindowInfo("w", 1, 1, 1, "fixture", "fixture", new(0, 0, 100, 100), false, false);
        var plan = new GameClickPlan(w, DateTimeOffset.UtcNow.AddMinutes(-3), 50, 50, "", "테스트");
        var capture = new CaptureInfo("wgc", 100, 100, w.Bounds, 1, true, "");
        Reject("stale game plan", () => plan.Validate(w, capture), "stale_observation");
        Reject("changed game process", () => (plan with { ObservedAt = DateTimeOffset.UtcNow }).Validate(w with { Started = 2 }, capture), "target_changed");
        var o = new Observation("o", w, DateTimeOffset.UtcNow, [], false, "observed", new("wgc", 100, 100, w.Bounds, 1, true, ""), "captured");
        Reject("negative coordinate", () => Broker.ValidatePoint(o, -1, 1), "invalid_coordinates");
        Reject("exclusive upper bound", () => Broker.ValidatePoint(o, 100, 1), "invalid_coordinates");
        Reject("missing screenshot", () => Broker.ValidatePoint(o with { Capture = null }, 1, 1), "coordinate_unverified");
        Reject("ambiguous mapping", () => Broker.ValidatePoint(o with { Capture = o.Capture! with { CoordinateMappingValid = false } }, 1, 1), "coordinate_unverified");
        Broker.ValidatePoint(o, 99, 99); passed++;
        try { Json.Read<ActionArgs>("{\"window_id\":\"w\",\"observation_id\":\"o\",\"request_id\":\"r\",\"type\":\"invoke\",\"surprise\":1}"); throw new Exception("미지 필드 허용"); }
        catch (System.Text.Json.JsonException) { passed++; }
        Console.WriteLine(Json.Write(new { status = "passed", checks = passed, native_input_sent = false }));
    }
}
