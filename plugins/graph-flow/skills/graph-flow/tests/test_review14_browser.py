"""Real viewport regressions, with an isolated server and headless Chrome profile."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import threading
import unittest

import test_plan_approval as fixture
from graphflow import server

NODE = shutil.which('node')
CHROME = shutil.which('chromium') or shutil.which('google-chrome') or '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'


@unittest.skipUnless(NODE and Path(CHROME).is_file(), 'headless Chrome and Node are required')
class Browser14Tests(unittest.TestCase):
    setUp = fixture.PlanApprovalTests.setUp
    call = fixture.PlanApprovalTests.call
    set_plan = fixture.PlanApprovalTests.set_plan

    def test_b1_b9_first_fit_selection_and_polling(self):
        dependencies = [[], [0], [0], [1], [1], [1], [2], [2], [], [6, 7], [3, 4], [9, 10, 8]]
        self.raw['nodes'] = []
        for i, needs in enumerate(dependencies):
            node = {'id': 'n%d' % i, 'kind': 'work', 'lane': 1, 'grade': 'daily',
                    'title': '안내 단계 %d' % i, 'goal': '안내 파일을 작성해요', 'owns': ['n%d.txt' % i],
                    'outputs': ['result'], 'checks': [{'id': 'ok', 'type': 'cmd', 'run': 'true'}],
                    'needs': [{'from': 'n%d' % n, 'artifact': 'result'} for n in needs]}
            if i == 8:
                node.update(kind='review', target='n5', lens='접근성', owns=[], checks=[])
            self.raw['nodes'].append(node)
        self.set_plan()
        httpd, token = server.make_server()
        thread = threading.Thread(target=httpd.serve_forever, kwargs={'poll_interval': .01}, daemon=True)
        thread.start()
        try:
            config = self.root / 'browser.json'
            config.write_text(json.dumps({'url': 'http://127.0.0.1:%d/?t=%s' % (httpd.server_address[1], token),
                'project': str(self.project), 'run': self.run.name, 'chrome': CHROME,
                'profile': str(self.root / 'chrome-profile')}))
            result = subprocess.run([NODE, str(Path(__file__).with_name('review14_browser.mjs')), str(config)],
                                    capture_output=True, text=True, timeout=45)
            self.assertEqual(result.returncode, 0, result.stderr)
        finally:
            httpd.shutdown()
            httpd.server_close()
            thread.join(5)
        self.assertFalse(thread.is_alive())
