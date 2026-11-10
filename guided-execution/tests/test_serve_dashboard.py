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
        self.assertIn('AI 요약 · 참고용', html)
        # Visible paths: what needs the person, selectable cards with a detail region, noncolor glyphs.
        self.assertIn('지금 필요한 것', html)
        self.assertIn('id="announce" class="sr" aria-live="polite"', html)
        self.assertIn('class="detail frame" id="detail" aria-labelledby="detail-title" hidden', html)
        # Structure carries the meaning: no sentences explaining the interface itself.
        for sentence in ('Tab으로 이동해', '흐르는 점은 장식', '세션에 새 활동이 생기면', '전체 작업 목록에서 확인하세요',
                         '선행 작업을 확인하세요', '노드를 누르면'):
            self.assertNotIn(sentence, html)
        self.assertIn("role: 'button'", html)
        self.assertIn("e.key === 'Enter' || e.key === ' '", html)
        self.assertIn("if (e.key !== 'Escape') return;", html)
        # Ontology graph: session hub, decision gates, task nodes with check arcs, typed link labels.
        for token in ("const HUB = '__session'", "class: 'node gate'", "class: 'seg'", "'선행'", 'url(#arrow-hot)'):
            self.assertIn(token, html)
        # The task panel speaks plainly: what happens now, what was done, check results; no tool jargon.
        for phrase in ('지금 하는 일', '최근 한 일', '확인 결과', '지나온 과정', '파일 수정', '시작한 지'):
            self.assertIn(phrase, html)
        for jargon in ('리비전', "'쓰기'", "'읽기'", ' · via', '기록 타임라인'):
            self.assertNotIn(jargon, html)
        # Claude questions, quick view and command explanations are reachable without a pointer.
        for token in ('id="ask"', 'Claude 질문', 'role="dialog" aria-modal="true"', 'role="tooltip"', "addEventListener('focus', () => showTip",
                      '설명 만드는 중…', "if (!$('qv').hidden) { closeQuick(); return; }", '/api/question/answer', '/api/file?path='):
            self.assertIn(token, html)
        # Live activity moves only with motion on.
        self.assertIn("if (seenEvents && motionOn())", html)
        self.assertIn("if (!firstLoad && motionOn())", html)
        self.assertIn('.motion .node.st-running .spin{animation:spin', html)
        self.assertRegex(html, r'@media \(prefers-reduced-motion:reduce\)\{[^}]*\.spin,[^{]*\.dots\{animation:none\}')
        self.assertIn("freshAttention", html)
        for glyph in ('✓', '✗', '▶', '⏸', '↺', '?', '◌'):
            self.assertIn(glyph, html)

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

    def control(self, *args):
        result = subprocess.run([sys.executable, str(SCRIPTS / 'loop_control.py'), args[0],
                                 '--workspace', str(self.workspace), *args[1:]], capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stderr)

    def test_records_carry_task_timeline_scopes_and_evidence(self):
        self.control('start', '--task', 'build', '--revision', 'r1')
        (self.workspace / 'evidence' / 'build-1.log').write_text('ok', encoding='utf-8')
        self.control('record-check', '--task', 'build', '--revision', 'r1', '--check', 'unit',
                     '--path', 'evidence/build-1.log', '--result', 'failed')
        self.control('finish', '--task', 'build', '--revision', 'r1', '--result', 'failed', '--reason', 'unit 실패')
        self.control('start', '--task', 'build', '--revision', 'r2')
        data = json.loads(self.request('GET', '/api/records')[2])
        build = data['tasks'][0]
        self.assertEqual(['start', 'record-check', 'finish', 'start'], [e['action'] for e in build['timeline']])
        self.assertEqual(('unit', 'failed'), (build['timeline'][1]['check'], build['timeline'][1]['result']))
        self.assertEqual(('failed', 'unit 실패'), (build['timeline'][2]['result'], build['timeline'][2]['reason']))
        self.assertEqual(build['timeline'][3]['at'], build['started_at'])
        self.assertEqual(('r2', ['a.txt'], ['build.txt']), (build['revision'], build['reads'], build['writes']))
        self.assertIsNone(build['checks'][0]['evidence'])  # a new attempt starts without current records
        self.control('invalidate', '--task', 'build', '--reason', '입력 변경')
        ship = json.loads(self.request('GET', '/api/records')[2])['tasks'][1]
        self.assertEqual([('invalidated', 'build')], [(e['action'], e['by']) for e in ship['timeline']])

    def test_records_carry_requirement_todos_and_old_runs_have_none(self):
        data = json.loads(self.request('GET', '/api/records')[2])
        self.assertEqual(([], []), (data['requirements'], data['todos']))
        self.control('todo-add', '--todo', 'parse', '--title', '입력 <b>파싱</b>', '--task', 'build')
        self.control('start', '--task', 'build', '--revision', 'r1')
        self.control('todo-set', '--todo', 'parse', '--status', 'in_progress')
        todo = json.loads(self.request('GET', '/api/records')[2])['todos'][0]
        self.assertEqual(('parse', '입력 <b>파싱</b>', 'in_progress', 'build', None),
                         (todo['id'], todo['title'], todo['status'], todo['task_id'], todo['requirement_id']))
        page = self.request('GET', '/')[2].decode()
        self.assertIn('id="tab-todos"', page)
        self.assertIn("'#view=todos'", page)

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

    def test_activity_keeps_bounded_metadata_on_known_tasks(self):
        events = [{'id': 'a1', 'task': 'build', 'tool': 'Bash', 'target': 'x' * 500, 'phase': 'ok',
                   'started_at': 1000, 'ended_at': 1300, 'status': 'passed'},
                  {'id': 'a2', 'task': 'nope', 'tool': 'Read', 'phase': 'running', 'started_at': 1400},
                  {'id': 'a1', 'task': 'build', 'tool': 'dup', 'phase': 'ok', 'started_at': 1},
                  {'id': 'a3', 'task': 'build', 'tool': 'Grep', 'phase': 'done', 'started_at': 1},
                  {'id': 'a4', 'task': 'build', 'tool': 'Grep', 'phase': 'ok', 'started_at': 'soon'}]
        status, _, body = self.request('POST', '/api/activity', {'events': events})
        self.assertEqual(200, status, body)
        stored = json.loads(self.request('GET', '/api/session')[2])['activity']
        self.assertEqual(['a1', 'a2'], [e['id'] for e in stored['events']])
        self.assertEqual(120, len(stored['events'][0]['target']))
        self.assertNotIn('status', stored['events'][0])
        self.assertEqual('__session', stored['events'][1]['task'])
        self.assertEqual('session_activity_not_a_record', stored['basis'])
        self.assertEqual(403, self.request('POST', '/api/activity?t=' + self.board.token,
                                           {'events': []}, token=False)[0])
        self.assertEqual(422, self.request('POST', '/api/activity', {'events': 'no'})[0])
        self.assertEqual(self.before, self.digest())

    def post_activity(self, *events):
        base = {'task': 'build', 'phase': 'ok', 'started_at': 1000}
        status, _, body = self.request('POST', '/api/activity', {'events': [{**base, **e} for e in events]})
        self.assertEqual(200, status, body)

    def test_quick_view_opens_only_touched_non_secret_text_files(self):
        readable = self.root / 'notes.md'
        readable.write_text('# 메모\n내용', encoding='utf-8')
        secret = self.root / '.env.local'
        secret.write_text('TOKEN=x', encoding='utf-8')
        binary = self.root / 'blob.bin'
        binary.write_bytes(b'\x00\x01')
        link = self.root / 'link.md'
        link.symlink_to(readable)
        untouched = self.root / 'other.md'
        untouched.write_text('x', encoding='utf-8')
        self.post_activity(*[{'id': f'f{i}', 'tool': 'Read', 'path': str(p)}
                             for i, p in enumerate([readable, secret, binary, link])])
        from urllib.parse import quote
        get = lambda p: self.request('GET', '/api/file?path=' + quote(str(p)))
        status, _, body = get(readable)
        self.assertEqual(200, status, body)
        self.assertEqual('# 메모\n내용', json.loads(body)['text'])
        self.assertEqual(403, get(secret)[0])
        self.assertEqual(422, get(binary)[0])
        self.assertEqual(422, get(link)[0])
        self.assertEqual(403, get(untouched)[0])
        self.assertEqual(403, get('/etc/hosts')[0])

    def test_explanations_only_for_observed_commands_and_flow_through_pending(self):
        self.post_activity({'id': 'c1', 'tool': 'Bash', 'command': 'git status --short'})
        self.assertEqual(422, self.request('POST', '/api/explain', {'command': 'rm -rf /'})[0])
        first = json.loads(self.request('POST', '/api/explain', {'command': 'git status --short'})[2])
        self.assertEqual('pending', first['state'])
        pending = json.loads(self.request('GET', '/api/explain/pending')[2])['items']
        self.assertEqual([{'key': first['key'], 'command': 'git status --short'}], pending)
        self.request('POST', '/api/explain/answer', {'items': [{'key': first['key'], 'text': '바뀐 파일 목록을 짧게 보여 줍니다.'},
                                                               {'key': 'unknown', 'text': 'x'}]})
        ready = json.loads(self.request('POST', '/api/explain', {'command': 'git status --short'})[2])
        self.assertEqual(('ready', '바뀐 파일 목록을 짧게 보여 줍니다.'), (ready['state'], ready['text']))
        self.assertEqual([], json.loads(self.request('GET', '/api/explain/pending')[2])['items'])

    def test_question_is_shown_answered_once_and_resolved(self):
        ask = {'id': 'tu1', 'questions': [{'question': '형식은?', 'header': '형식', 'multiSelect': False,
                                           'options': [{'label': 'JSON', 'description': '구조화'}, {'label': 'MD'}]}]}
        self.assertEqual(200, self.request('POST', '/api/question', ask)[0])
        shown = json.loads(self.request('GET', '/api/session')[2])['questions']
        self.assertEqual(('open', '형식은?', ['JSON', 'MD']),
                         (shown[0]['status'], shown[0]['questions'][0]['question'], [o['label'] for o in shown[0]['questions'][0]['options']]))
        self.assertEqual(422, self.request('POST', '/api/question/answer', {'id': 'tu1', 'answers': {'다른 질문': 'x'}})[0])
        self.assertEqual(200, self.request('POST', '/api/question/answer', {'id': 'tu1', 'answers': {'형식은?': 'JSON'}})[0])
        self.assertEqual(409, self.request('POST', '/api/question/answer', {'id': 'tu1', 'answers': {'형식은?': 'MD'}})[0])
        polled = json.loads(self.request('GET', '/api/question?id=tu1')[2])['question']
        self.assertEqual(('answered', {'형식은?': 'JSON'}, 'dashboard'), (polled['status'], polled['answers'], polled['via']))
        self.request('POST', '/api/question/resolve', {'id': 'tu1', 'answers': {'형식은?': 'JSON'}, 'via': 'dashboard'})
        self.assertEqual('resolved', json.loads(self.request('GET', '/api/session')[2])['questions'][0]['status'])
        self.assertEqual(409, self.request('POST', '/api/question/answer', {'id': 'nope', 'answers': {}})[0])
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
