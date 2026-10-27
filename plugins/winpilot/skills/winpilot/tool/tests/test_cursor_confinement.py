"""Run serially on an unlocked Windows desktop with a locally built fixture.

ClipCursor confines movement to the fixture's Count button while the request
points at its canvas. Neither click nor drag may send a button-down there.
"""
import sys
import unittest


@unittest.skipUnless(sys.platform == 'win32', 'requires interactive Windows desktop')
class CursorConfinementTests(unittest.TestCase):
    def test_clipped_click_and_drag_never_press_the_wrong_control(self):
        import ctypes as c
        from ctypes import wintypes as w
        import subprocess
        import time
        from integration import Client, EXE, CREATE_NO_WINDOW

        u = c.WinDLL('user32', use_last_error=True)
        u.ClipCursor.argtypes = [c.POINTER(w.RECT)]
        u.GetClipCursor.argtypes = [c.POINTER(w.RECT)]
        u.SetForegroundWindow.argtypes = [w.HWND]
        u.GetForegroundWindow.restype = w.HWND
        u.GetAsyncKeyState.restype = c.c_short
        previous = w.RECT()
        self.assertTrue(u.GetClipCursor(c.byref(previous)))
        fixture = subprocess.Popen([str(EXE), '--fixture', 'A'], creationflags=CREATE_NO_WINDOW)
        client = None
        try:
            client = Client()
            win = None
            for _ in range(60):
                listing, _ = client.tool('windows_list')
                win = next((x for x in listing['windows'] if x['pid'] == fixture.pid), None)
                if win:
                    break
                time.sleep(.1)
            self.assertIsNotNone(win)
            u.SetForegroundWindow(win['hwnd'])
            self.assertEqual(u.GetForegroundWindow(), win['hwnd'], 'fixture must be foreground')
            for action in ('click', 'drag'):
                obs, _ = client.tool('window_observe', {'window_id': win['window_id']})
                button = next(e['bounds'] for e in obs['elements'] if e['name'] == 'PilotButton')
                canvas = next(e['bounds'] for e in obs['elements'] if e['name'] == 'PilotCanvas')
                px, py = button['x'] + 10, button['y'] + 10
                self.assertTrue(u.SetCursorPos(px, py))
                clip = w.RECT(px, py, px + 1, py + 1)
                self.assertTrue(u.ClipCursor(c.byref(clip)))
                bounds = obs['capture']['bounds']
                x, y = canvas['x'] - bounds['x'] + 25, canvas['y'] - bounds['y'] + 25
                args = dict(window_id=win['window_id'], observation_id=obs['observation_id'],
                            request_id='clipped-' + action, type=action, foreground_policy='allow',
                            x=x, y=y, duration_ms=100)
                if action == 'drag':
                    args.update(to_x=x + 20, to_y=y + 20)
                job, _ = client.tool('action_run', args)
                result = client.wait(job['job_id'])
                self.assertEqual(result['status'], 'cursor_position_unverified', result)
                self.assertGreaterEqual(u.GetAsyncKeyState(1), 0, 'left button must be released')
                after, _ = client.tool('window_observe', {'window_id': win['window_id']})
                self.assertTrue(any(e['name'] == 'Count:0' for e in after['elements']), after)
                self.assertTrue(u.ClipCursor(c.byref(previous)))
        finally:
            u.ClipCursor(c.byref(previous))
            if client:
                client.close()
            if fixture.poll() is None:
                fixture.terminate()
                fixture.wait(timeout=5)


if __name__ == '__main__':
    unittest.main()
