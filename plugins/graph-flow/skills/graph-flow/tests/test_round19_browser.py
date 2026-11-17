"""Full-text bounds in a real browser, using only an isolated scratch project."""
import json
import os
from pathlib import Path
import shutil
import signal
import time
import subprocess
import tempfile
import threading
import unittest
from unittest import mock
import test_plan_approval as fixture
from graphflow import server

NODE = shutil.which('node')
CHROME = shutil.which('chromium') or shutil.which('google-chrome') or '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'

@unittest.skipUnless(NODE and Path(CHROME).is_file(), 'headless Chrome and Node required')
class Browser19Tests(unittest.TestCase):
    call = fixture.PlanApprovalTests.call
    set_plan = fixture.PlanApprovalTests.set_plan

    def setUp(self):
        output = Path('/Volumes/eyedisk/build/graph-flow-screens/r19')
        output.mkdir(parents=True, exist_ok=True)
        temporary = tempfile.TemporaryDirectory
        with mock.patch.object(tempfile, 'TemporaryDirectory', side_effect=lambda: temporary(dir=output, prefix='browser-test-')):
            fixture.PlanApprovalTests.setUp(self)

    def test_u1_u2_full_sentences_and_unclipped_cards_all_sizes_levels_modes(self):
        base = self.raw['nodes'][0]
        self.raw['nodes'] = []
        for i, kind in enumerate(['work', 'review', 'decision']):
            n = dict(base, id='n%d' % i, kind=kind, title=('제목을 모두 읽을 수 있는지 확인하는 한국어 안내 ' * 3)[:60],
                     summary=('작업의 목적과 만드는 결과를 누구나 이해할 수 있도록 한국어로 설명하고 빠진 내용을 확인해요. ' * 7)[:300], goal='Keep the English goal as a fallback.')
            if kind == 'review':
                n.update(target='n0', lens='정확성', owns=[], checks=[])
            elif kind == 'decision':
                n.update(question='이 안내를 공개할까요?', decision_kind='authorization')
                n.pop('owns'); n.pop('checks'); n.pop('grade')
            else:
                n['checks'] = [dict(id='c%d' % j, type='cmd', run='true', title=('결과 파일에 내용이 있는지와 안내 순서를 확인하는 검사 ' * 5)[:120]) for j in range(4)]
            self.raw['nodes'].append(n)
        self.set_plan()
        httpd, token = server.make_server()
        thread = threading.Thread(target=httpd.serve_forever, kwargs={'poll_interval': .01}, daemon=True)
        thread.start()
        try:
            config = self.root / 'browser.json'
            config.write_text(json.dumps(dict(url='http://127.0.0.1:%d/?t=%s' % (httpd.server_address[1], token), project=str(self.project.resolve()), run=self.run.name, chrome=CHROME, profile=str(self.root / 'chrome-profile'))))
            result = subprocess.run([NODE, str(Path(__file__).with_name('round19_browser.mjs')), str(config)], capture_output=True, text=True, timeout=100)
            self.assertEqual(result.returncode, 0, result.stderr)
        finally:
            httpd.shutdown(); httpd.server_close(); thread.join(5)
            # A timed-out Node process cannot run its finally block. Own only this profile.
            profile = '--user-data-dir=' + str(self.root / 'chrome-profile')
            for attempt in range(20):
                rows = subprocess.check_output(['/bin/ps', '-axo', 'pid=,command='], text=True).splitlines()
                owned = [int(row.split(None, 1)[0]) for row in rows if profile in row]
                if not owned:
                    break
                for pid in owned:
                    try:
                        os.kill(pid, signal.SIGTERM if attempt < 15 else signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                time.sleep(.1)
            self.assertFalse(owned, 'isolated Chrome helpers must stop')
        self.assertFalse(thread.is_alive())
