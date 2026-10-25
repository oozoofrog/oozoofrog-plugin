using System.Runtime.InteropServices;
using Windows.Graphics.Capture;
using Windows.Graphics.DirectX;
using Windows.Graphics.DirectX.Direct3D11;
using Windows.Graphics.Imaging;
using Windows.Storage.Streams;

namespace WindowsPilot;

internal static class Capture
{
    [ComImport, Guid("3628e81b-3cac-4c60-b7f4-23ce0e0c3356"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    private interface ICaptureInterop
    {
        [PreserveSig] int CreateForWindow(nint window, ref Guid iid, out nint item);
        [PreserveSig] int CreateForMonitor(nint monitor, ref Guid iid, out nint item);
    }
    [DllImport("combase.dll", CharSet = CharSet.Unicode)] private static extern int WindowsCreateString(string value, int length, out nint handle);
    [DllImport("combase.dll")] private static extern int WindowsDeleteString(nint handle);
    [DllImport("combase.dll")] private static extern int RoGetActivationFactory(nint name, ref Guid iid, out nint factory);
    [DllImport("d3d11.dll")] private static extern int D3D11CreateDevice(nint adapter, int driverType, nint software,
        uint flags, nint levels, uint count, uint version, out nint device, out int level, out nint context);
    [DllImport("d3d11.dll")] private static extern int CreateDirect3D11DeviceFromDXGIDevice(nint dxgi, out nint device);

    public static async Task<CaptureInfo> Take(WindowInfo window)
    {
        Native.Validate(window);
        if (window.Minimized || Native.IsIconic((nint)window.Hwnd))
            throw new PilotException("minimized", "최소화 창을 자동 복원하지 않습니다.");
        if (!GraphicsCaptureSession.IsSupported()) throw new PilotException("capture_unsupported", "WGC를 사용할 수 없습니다.");
        nint name = 0, factory = 0, itemPtr = 0, device = 0, context = 0, dxgi = 0, inspectable = 0;
        try
        {
            const string className = "Windows.Graphics.Capture.GraphicsCaptureItem";
            Marshal.ThrowExceptionForHR(WindowsCreateString(className, className.Length, out name));
            var interopId = typeof(ICaptureInterop).GUID;
            Marshal.ThrowExceptionForHR(RoGetActivationFactory(name, ref interopId, out factory));
            var interop = (ICaptureInterop)Marshal.GetObjectForIUnknown(factory);
            var itemId = new Guid("79c3f95b-31f7-4ec2-a464-632ef5d30760");
            Marshal.ThrowExceptionForHR(interop.CreateForWindow((nint)window.Hwnd, ref itemId, out itemPtr));
            var item = WinRT.MarshalInterface<GraphicsCaptureItem>.FromAbi(itemPtr);
            Marshal.ThrowExceptionForHR(D3D11CreateDevice(0, 1, 0, 0x20, 0, 0, 7, out device, out _, out context));
            var dxgiId = new Guid("54ec77fa-1377-44e6-8c32-88fd5f44c84c");
            Marshal.ThrowExceptionForHR(Marshal.QueryInterface(device, in dxgiId, out dxgi));
            Marshal.ThrowExceptionForHR(CreateDirect3D11DeviceFromDXGIDevice(dxgi, out inspectable));
            using var directDevice = WinRT.MarshalInterface<IDirect3DDevice>.FromAbi(inspectable);
            using var pool = Direct3D11CaptureFramePool.CreateFreeThreaded(directDevice,
                DirectXPixelFormat.B8G8R8A8UIntNormalized, 2, item.Size);
            using var session = pool.CreateCaptureSession(item);
            session.IsCursorCaptureEnabled = false;
            var ready = new TaskCompletionSource<Direct3D11CaptureFrame>(TaskCreationOptions.RunContinuationsAsynchronously);
            pool.FrameArrived += (sender, _) =>
            {
                try { var next = sender.TryGetNextFrame(); if (next != null && !ready.TrySetResult(next)) next.Dispose(); }
                catch (Exception ex) { ready.TrySetException(ex); }
            };
            session.StartCapture();
            using var frame = await ready.Task.WaitAsync(TimeSpan.FromSeconds(3));
            using var bitmap = await SoftwareBitmap.CreateCopyFromSurfaceAsync(frame.Surface, BitmapAlphaMode.Premultiplied);
            using var stream = new InMemoryRandomAccessStream();
            var encoder = await BitmapEncoder.CreateAsync(BitmapEncoder.PngEncoderId, stream);
            encoder.SetSoftwareBitmap(bitmap);
            await encoder.FlushAsync();
            stream.Seek(0);
            using var reader = new DataReader(stream);
            if (stream.Size > 24 * 1024 * 1024) throw new PilotException("capture_too_large", "PNG가 24 MiB를 초과합니다.");
            await reader.LoadAsync((uint)stream.Size);
            var data = new byte[(int)stream.Size];
            reader.ReadBytes(data);
            Native.Validate(window);
            var bounds = Native.GetBounds((nint)window.Hwnd);
            bool mapping = bitmap.PixelWidth == bounds.Width && bitmap.PixelHeight == bounds.Height;
            return new("wgc", bitmap.PixelWidth, bitmap.PixelHeight, bounds, frame.SystemRelativeTime.Ticks,
                mapping, Convert.ToBase64String(data));
        }
        finally
        {
            foreach (var pointer in new[] { inspectable, dxgi, context, device, itemPtr, factory })
                if (pointer != 0) Marshal.Release(pointer);
            if (name != 0) WindowsDeleteString(name);
        }
    }
}
