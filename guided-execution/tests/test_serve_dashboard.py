"""Local dashboard server tests on actual workspaces: access control, read-only, summary limits."""
import hashlib
import http.client
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
import serve_dashboard


class DashboardTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.project = self.root / 'project'
        self.project.mkdir()
        self.workspace = self.project / '.agent-loop' / 'board-test'
        plan = {'schema_version': 1, 'goal': '보드 <b>테스트</b>',
                'decisions': [{'id': 'look', 'kind': 'review', 'question': '확인?'}],
                'tasks': [{'id': name, 'title': name + ' 작업', 'depends_on': deps, 'reads': ['a.txt'],
                           'writes': [name + '.txt'], 'max_attempts': 3, 'decision_ids': gates,
                           'checks': [{'id': 'unit', 'description': '검증', 'command': 'touch SHOULD_NOT_RUN'}]}
                          for name, deps, gates in [('build', [], []), ('ship', ['build'], ['look'])]]}
        (self.root / 'plan.json').write_text(json.dumps(plan), encoding='utf-8')
        (self.root / 'brief.md').write_text('brief', encoding='utf-8')
        result = subprocess.run([sys.executable, str(SCRIPTS / 'loop_workspace.py'), 'init',
                                 '--project', str(self.project), '--run-id', 'board-test',
                                 '--plan', str(self.root / 'plan.json'), '--brief', str(self.root / 'brief.md')],
                                capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.before = self.digest()
        out = io.StringIO()
        self.server, self.board = serve_dashboard.serve(str(self.workspace), stream=out)
        self.announce = json.loads(out.getvalue())
        self.port = self.announce['port']
        thread = threading.Thread(target=self.server.serve_forever, kwargs={'poll_interval': 0.05}, daemon=True)
        thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def digest(self):
        return {str(p.relative_to(self.project)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(self.project.rglob('*')) if p.is_file()}

    def request(self, method, path, body=None, headers=None, token=True):
        connection = http.client.HTTPConnection('127.0.0.1', self.port, timeout=5)
        merged = {'X-Board-Token': self.board.token} if token else {}
        merged.update(headers or {})
        data = json.dumps(body).encode() if body is not None else None
        connection.request(method, path, body=data, headers=merged)
        response = connection.getresponse()
        payload = response.read()
        connection.close()
        return response.status, dict(response.getheaders()), payload

    def test_binds_loopback_and_announces_token_url(self):
        self.assertEqual('127.0.0.1', self.server.server_address[0])
        self.assertEqual(f"http://127.0.0.1:{self.port}/?t={self.board.token}", self.announce['url'])
        self.assertEqual('record_integrity_only', self.announce['verification_scope'])

    def test_rejects_missing_token_and_foreign_host(self):
        self.assertEqual(403, self.request('GET', '/api/records', token=False)[0])
        self.assertEqual(403, self.request('GET', '/api/records', headers={'X-Board-Token': 'wrong'})[0])
        self.assertEqual(403, self.request('GET', '/api/records', headers={'Host': f'evil.example:{self.port}'})[0])
        self.assertEqual(200, self.request('GET', '/?t=' + self.board.token, token=False)[0])

    def test_page_has_nonce_csp_and_no_external_resources(self):
        status, headers, body = self.request('GET', '/')
        html = body.decode()
        self.assertEqual(200, status)
        csp = headers['Content-Security-Policy']
        nonce = csp.split("'nonce-")[1].split("'")[0]
        self.assertIn(f'<script nonce="{nonce}">', html)
        self.assertIn("connect-src 'self'", csp)
        self.assertNotIn('__NONCE__', html)
        self.assertNotRegex(html, r'(src|href)="https?:')
        self.assertIn('prefers-reduced-motion', html)
        self.assertIn('aria-pressed', html)
        self.assertIn('기록 아님', html)
        # Visible paths: what needs the person, selectable cards with a detail region, noncolor glyphs.
        self.assertIn('지금 필요한 것', html)
        self.assertIn('id="announce" class="sr" aria-live="polite"', html)
        self.assertIn('id="detail" aria-labelledby="detail-title" hidden', html)
        # Structure carries the meaning: no sentences explaining the interface itself.
        for sentence in ('Tab으로 이동해', '흐르는 점은 장식', '세션에 새 활동이 생기면', '전체 작업 목록에서 확인하세요', '선행 작업을 확인하세요'):
            self.assertNotIn(sentence, html)
        self.assertIn("role: 'button'", html)
        self.assertIn("e.key === 'Enter' || e.key === ' '", html)
        self.assertIn("e.key === 'Escape'", html)
        # Motion: dots flow only on the selected task's edges, with distinct in/out patterns and static arrows.
        self.assertIn('.motion .flow.hot{', html)
        self.assertNotRegex(html, r'\.motion \.flow\{')
        self.assertIn('.flow.in{stroke-dasharray:3 997}', html)
        self.assertIn('.flow.out{stroke-dasharray:3 9 3 985}', html)
        self.assertIn('url(#arrow-hot)', html)
        self.assertIn("if (!firstDraw && motionOn())", html)
        self.assertIn("freshAttention", html)
        for glyph in ('✓', '✗', '▶', '⏸', '↺', '?'):
            self.assertIn(glyph, html)
        # Stage edges share the `stage` class; no blanket rule may hide them.
        self.assertNotRegex(html, r'(?m)^\.stage\{display:none\}')

    def test_records_reflect_state_and_never_write(self):
        status, _, body = self.request('GET', '/api/records')
        data = json.loads(body)
        self.assertEqual(200, status)
        self.assertTrue(data['ok'])
        self.assertEqual(['build', 'ship'], [t['id'] for t in data['tasks']])
        self.assertEqual('unrecorded', data['tasks'][0]['checks'][0]['result'])
        self.assertEqual(['build'], data['status']['ready'])
        self.assertEqual('pending', data['decisions'][0]['status'])
        self.assertEqual(200, self.request('GET', '/report')[0])
        for method in ('PUT', 'DELETE', 'PATCH'):
            self.assertEqual(405, self.request(method, '/api/records')[0])
        self.assertEqual(self.before, self.digest())
        self.assertFalse((self.project / 'SHOULD_NOT_RUN').exists())

    def test_mismatched_pair_keeps_last_good_and_reports_error(self):
        good = json.loads(self.request('GET', '/api/records')[2])
        plan = self.workspace / 'plan.json'
        plan.write_bytes(plan.read_bytes() + b' ')
        data = json.loads(self.request('GET', '/api/records')[2])
        self.assertFalse(data['ok'])
        self.assertIn('digest', data['error'])
        self.assertEqual(good['fingerprint'], data['last_good']['fingerprint'])

    def test_summary_keeps_labels_and_drops_statuses_and_unknown_refs(self):
        summary = {'headline': '빌드 후 배포 검토 대기', 'model': 'haiku', 'usage_tokens': 360,
                   'stages': [{'id': 's1', 'label': '구현', 'kind': 'build', 'refs': ['build', 'nope'],
                               'status': 'passed'},
                              {'id': 's2', 'label': '배포', 'refs': ['ship'], 'kind': 'bogus'},
                              {'id': 's1', 'label': 'dup'}],
                   'edges': [{'from': 's1', 'to': 's2'}, {'from': 's1', 'to': 'zz'}]}
        status, _, body = self.request('POST', '/api/session', summary)
        self.assertEqual(200, status, body)
        stored = json.loads(self.request('GET', '/api/session')[2])['summary']
        self.assertEqual(['s1', 's2'], [s['id'] for s in stored['stages']])
        self.assertEqual(['build'], stored['stages'][0]['refs'])
        self.assertNotIn('status', stored['stages'][0])
        self.assertEqual('other', stored['stages'][1]['kind'])
        self.assertEqual([{'from': 's1', 'to': 's2'}], stored['edges'])
        self.assertEqual('ai_summary_not_a_record', stored['basis'])
        self.assertEqual(360, stored['usage_tokens'])
        self.assertEqual(self.before, self.digest())

    def test_summary_requires_header_token_and_valid_size(self):
        self.assertEqual(403, self.request('POST', '/api/session?t=' + self.board.token,
                                           {'stages': [{'id': 'a', 'label': 'b'}]}, token=False)[0])
        self.assertEqual(422, self.request('POST', '/api/session', {'stages': []})[0])
        big = {'stages': [{'id': 'a', 'label': 'x' * (serve_dashboard.MAX_BODY + 1)}]}
        self.assertEqual(413, self.request('POST', '/api/session', big)[0])


class CliTests(unittest.TestCase):
    def test_rejects_non_workspace_path(self):
        with tempfile.TemporaryDirectory() as temp:
            result = subprocess.run([sys.executable, str(SCRIPTS / 'serve_dashboard.py'), '--workspace', temp],
                                    capture_output=True, text=True, timeout=10)
        self.assertEqual(1, result.returncode)
        self.assertIn('error:', result.stderr)

    def test_closed_stdin_keeps_serving_and_lost_parent_stops(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            project = root / 'p'
            project.mkdir()
            plan = {'schema_version': 1, 'goal': 'g', 'decisions': [],
                    'tasks': [{'id': 'a', 'title': 'A', 'depends_on': [], 'reads': [], 'writes': ['a'],
                               'max_attempts': 3, 'decision_ids': [], 'checks': [{'id': 'c', 'description': 'd'}]}]}
            (root / 'plan.json').write_text(json.dumps(plan))
            (root / 'brief.md').write_text('b')
            subprocess.run([sys.executable, str(SCRIPTS / 'loop_workspace.py'), 'init', '--project', str(project),
                            '--run-id', 'r', '--plan', str(root / 'plan.json'), '--brief', str(root / 'brief.md')],
                           check=True, capture_output=True)
            workspace = str(project / '.agent-loop' / 'r')
            # The Claude host closes a spawned child's stdin at once; that must not stop the server.
            child = subprocess.Popen([sys.executable, str(SCRIPTS / 'serve_dashboard.py'), '--workspace', workspace],
                                     stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, text=True)
            self.addCleanup(child.stdout.close)
            announce = json.loads(child.stdout.readline())
            self.assertTrue(announce['url'].startswith('http://127.0.0.1:'))
            time.sleep(1.5)
            self.assertIsNone(child.poll())
            connection = http.client.HTTPConnection('127.0.0.1', announce['port'], timeout=5)
            connection.request('GET', '/api/records', headers={'X-Board-Token': announce['token']})
            self.assertEqual(200, connection.getresponse().status)
            connection.close()
            child.terminate()
            child.wait(timeout=10)
            # A parent that is not this process's parent stands for one that went away.
            orphan = subprocess.Popen([sys.executable, str(SCRIPTS / 'serve_dashboard.py'), '--workspace', workspace,
                                       '--parent-pid', str(os.getpid() + 999999)],
                                      stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, text=True)
            self.addCleanup(orphan.stdout.close)
            json.loads(orphan.stdout.readline())
            self.assertEqual(0, orphan.wait(timeout=10))


if __name__ == '__main__':
    unittest.main()
