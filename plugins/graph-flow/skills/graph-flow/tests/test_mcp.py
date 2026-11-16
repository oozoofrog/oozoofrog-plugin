"""Protocol, role filtering, and end-to-end parity with the CLI."""
import contextlib
import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SCRIPTS = pathlib.Path(__file__).resolve().parent.parent / 'scripts'
sys.path.insert(0, str(SCRIPTS))
from graphflow import __version__, cli, mcp


class MCPTests(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, {}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name).resolve()
        os.environ['GF_HOME'] = str(self.root / 'home')
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        self.git('init', '-q')
        self.git('config', 'user.name', 'MCP Test')
        self.git('config', 'user.email', 'mcp@example.invalid')
        (self.repo / 'a.py').write_text('value = 0\n')
        self.git('add', 'a.py')
        self.git('commit', '-q', '-m', 'fixture')
        self.request_id = 0

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.repo)] + list(args), check=True,
                              capture_output=True, text=True).stdout.strip()

    def exchange(self, *requests):
        incoming = io.StringIO(''.join(json.dumps(request) + '\n' for request in requests))
        outgoing, stray = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stray):
            mcp.serve(incoming, outgoing)
        self.assertEqual(stray.getvalue(), '')
        replies = [json.loads(line) for line in outgoing.getvalue().splitlines()]
        for reply in replies:
            self.assertEqual(reply['jsonrpc'], '2.0')
            self.assertEqual(set(reply) & {'result', 'error'}, {'error'} if 'error' in reply else {'result'})
        return replies

    def request(self, method, params=None):
        self.request_id += 1
        request = {'jsonrpc': '2.0', 'id': self.request_id, 'method': method}
        if params is not None:
            request['params'] = params
        replies = self.exchange(request)
        self.assertEqual(len(replies), 1)
        self.assertEqual(replies[0]['id'], self.request_id)
        return replies[0]

    def call(self, name, arguments=None, error=False):
        reply = self.request('tools/call', {'name': name, 'arguments': arguments or {}})
        self.assertNotIn('error', reply, reply)
        result = reply['result']
        self.assertIs(result['isError'], error, result)
        self.assertEqual(len(result['content']), 1)
        self.assertEqual(result['content'][0]['type'], 'text')
        return json.loads(result['content'][0]['text'])

    def plan(self):
        return {'schema_version': 1, 'goal': 'one passing unit', 'nodes': [
            {'id': 'a', 'kind': 'work', 'goal': 'write one', 'grade': 'daily',
             'lane': 1, 'owns': ['a.py'], 'checks': [
                 {'id': 'unit', 'type': 'cmd', 'run': 'test "$(cat a.py)" = "value = 1"'}]},
            {'id': 'r', 'kind': 'review', 'goal': 'review a', 'lane': 1, 'grade': 'daily',
             'target': 'a', 'lens': 'bugs', 'checks': []}]}

    def init_plan(self):
        run = self.call('run_init', {'run_id': 'test', 'project': str(self.repo)})['run']
        os.environ['GF_RUN'] = run
        self.assertEqual(self.call('plan_set', {'plan': self.plan()})['revision'], 1)
        return pathlib.Path(run)

    def test_initialize_ping_and_notifications(self):
        reply = self.request('initialize', {'protocolVersion': '2024-11-05'})['result']
        self.assertEqual(reply, {'protocolVersion': '2024-11-05', 'capabilities': {'tools': {}},
                                'serverInfo': {'name': 'graph-flow', 'version': __version__}})
        self.assertEqual(self.request('initialize')['result']['protocolVersion'], '2025-06-18')
        self.assertEqual(self.request('ping')['result'], {})
        self.assertEqual(self.exchange({'jsonrpc': '2.0', 'method': 'notifications/initialized'}), [])
        with mock.patch.object(cli, 'main') as main:
            self.assertEqual(self.exchange({'jsonrpc': '2.0', 'method': 'tools/call',
                                             'params': {'name': 'run_init'}}), [])
            main.assert_not_called()

    def test_role_tool_lists_and_schemas(self):
        expected = {
            'leader': {'plan_set', 'assign_node', 'gate_node'},
            'worker': {'node_start', 'check_run', 'node_submit', 'decision_ask', 'run_status'},
            'reviewer': {'review_submit', 'node_start', 'run_status'},
            'human': set(),
        }
        for role, required in expected.items():
            with self.subTest(role=role), mock.patch.dict(os.environ, GF_ROLE=role):
                definitions = self.request('tools/list')['result']['tools']
                names = {tool['name'] for tool in definitions}
                self.assertLessEqual(required, names)
                self.assertEqual(names, {name for name, tool in mcp.TOOLS.items()
                                       if role != 'human' and role in cli.COMMANDS[tool['command']]['roles']})
                self.assertFalse(any('answer' in name for name in names))
                if role == 'worker':
                    self.assertTrue(names.isdisjoint({'plan_set', 'gate_node', 'assign_node'}))
                if role == 'reviewer':
                    self.assertNotIn('node_submit', names)
                for tool in definitions:
                    self.assertTrue(tool['description'])
                    schema = tool['inputSchema']
                    self.assertEqual(schema['type'], 'object')
                    self.assertIsInstance(schema['properties'], dict)
                    self.assertIsInstance(schema['required'], list)
                    self.assertLessEqual(set(schema['required']), set(schema['properties']))
                    self.assertNotIn('role', schema['properties'])
                    self.assertIn('run', schema['properties'])
                    for field in schema['properties'].values():
                        self.assertTrue(field['description'])
                        self.assertIn(field['type'], {'object', 'array', 'string', 'boolean', 'number'})
                        if field['type'] == 'array':
                            self.assertIn('items', field)

    def test_filter_uses_cli_role_table(self):
        entry = dict(cli.COMMANDS[('ready',)], roles=('worker',))
        with mock.patch.dict(cli.COMMANDS, {('ready',): entry}):
            self.assertNotIn('ready_nodes', {t['name'] for t in self.request('tools/list')['result']['tools']})
            with mock.patch.dict(os.environ, GF_ROLE='worker'):
                self.assertIn('ready_nodes', {t['name'] for t in self.request('tools/list')['result']['tools']})

    def test_full_loop_through_tools(self):
        run = self.init_plan()
        self.assertEqual(self.call('ready_nodes')['ready'], ['a'])
        self.call('host_set', {'capabilities': ['subagent']})
        self.call('assign_node', {'node': 'a', 'executor': 'subagent', 'model': 'fixture',
                                 'effort': 'high', 'provider': 'fixture', 'family': 'openai', 'isolation': 'shared'})
        self.assertIn('a', self.call('node_brief', {'node': 'a'})['brief'])
        with mock.patch.dict(os.environ, GF_ROLE='worker', GF_NODE='a', GF_SESSION='mcp-worker'):
            self.assertEqual(self.call('node_start', {'node': 'a'})['attempt'], 1)
            failed = self.call('check_run', {'node': 'a', 'check': 'unit'})
            self.assertTrue(failed['ok'])
            self.assertEqual(failed['result'], 'failed')
            self.call('node_submit', {'node': 'a', 'notes': 'first try'})
        rejected = self.call('gate_node', {'node': 'a'})
        self.assertTrue(rejected['ok'])
        self.assertEqual(rejected['verdict'], 'reject')
        with mock.patch.dict(os.environ, GF_ROLE='worker', GF_NODE='a'):
            self.assertEqual(self.call('node_start', {'node': 'a'})['attempt'], 2)
            (self.repo / 'a.py').write_text('value = 1\n')
            self.assertEqual(self.call('check_run', {'node': 'a', 'check': 'unit'})['result'], 'passed')
            self.call('node_submit', {'node': 'a'})
        self.assertEqual(self.call('gate_node', {'node': 'a'})['verdict'], 'pass')
        self.assertEqual(self.call('run_status', {'node': 'a'})['node']['status'], 'passed')
        self.call('gate_node', {'final': True})
        events = [json.loads(line) for line in (run / 'events.jsonl').read_text().splitlines()]
        start = next(event for event in events if event['type'] == 'node.start')
        self.assertEqual(start['actor'], {'role': 'worker', 'node': 'a', 'session': 'mcp-worker'})

    def test_own_node_forbidden_and_hidden_tools_do_not_call_cli(self):
        self.init_plan()
        with mock.patch.dict(os.environ, GF_ROLE='worker', GF_NODE='a'):
            for name, arguments in [('node_start', {'node': 'r'}),
                                    ('check_run', {'node': 'r', 'check': 'unit'}),
                                    ('node_submit', {'node': 'r'}), ('run_status', {'node': 'r'})]:
                with self.subTest(name=name):
                    self.assertEqual(self.call(name, arguments, error=True)['code'], 'forbidden')
            with mock.patch.object(cli, 'main') as main:
                for name in ('plan_set', 'decision_answer', 'unknown', 'mcp', 'serve'):
                    self.assertEqual(self.request('tools/call', {'name': name})['error']['code'], -32602)
                main.assert_not_called()
        with mock.patch.dict(os.environ, GF_ROLE='human'), mock.patch.object(cli, 'main') as main:
            self.assertEqual(self.request('tools/list')['result']['tools'], [])
            self.assertEqual(self.request('tools/call', {'name': 'run_status'})['error']['code'], -32602)
            main.assert_not_called()

    def test_json_file_arguments_and_cleanup(self):
        seen = []
        def command(argv):
            self.assertIn('--json', argv)
            args = cli._parser().parse_args(argv)
            path = pathlib.Path(args.file if args.command_path[0] == 'plan' else args.findings)
            seen.append(path)
            self.assertEqual(json.loads(path.read_text()), self.plan() if args.command_path[0] == 'plan' else [])
            print('{"ok": true}')
            return 0
        with mock.patch.object(cli, 'main', side_effect=command):
            self.call('plan_validate', {'plan': self.plan()})
            self.call('plan_set', {'plan': self.plan()})
            with mock.patch.dict(os.environ, GF_ROLE='reviewer', GF_NODE='r'):
                self.call('review_submit', {'node': 'r', 'verdict': 'pass', 'findings': []})
        self.assertTrue(all(not path.exists() for path in seen))

    def test_run_override_and_option_values(self):
        run = self.init_plan()
        os.environ['GF_RUN'] = str(self.root / 'missing')
        self.assertEqual(self.call('run_status', {'run': str(run)})['state']['run']['id'], 'test')
        self.assertEqual(self.call('run_status', error=True)['code'], 'no_run')
        decision = self.call('decision_ask', {'run': str(run), 'kind': 'information', 'question': '--help'})
        self.assertEqual(decision['question'], '--help')
        reply = self.call('plan_validate', {'plan': {'nodes': []}})
        self.assertFalse(reply['ok'])
        self.assertEqual(reply['code'], 'invalid_plan')

    def test_exit_codes_preserve_cli_payload(self):
        for code in range(6):
            def command(argv):
                print(json.dumps({'ok': code in (0, 1), 'fixture': code}))
                return code
            with self.subTest(code=code), mock.patch.object(cli, 'main', side_effect=command):
                self.assertEqual(self.call('run_status', error=code in (2, 3, 4, 5))['fixture'], code)

    def test_bad_argument_shapes(self):
        cases = [None, [], {'role': 'leader'}, {'node': 1}, {'run': []}]
        with mock.patch.object(cli, 'main') as main:
            for arguments in cases:
                with self.subTest(arguments=arguments):
                    reply = self.request('tools/call', {'name': 'run_status', 'arguments': arguments})
                    self.assertEqual(reply['error']['code'], -32602)
            for name in (None, [], {}):
                self.assertEqual(self.request('tools/call', {'name': name})['error']['code'], -32602)
            for name, arguments in [('plan_set', {}), ('plan_set', {'plan': []}),
                                    ('merge_nodes', {'nodes': []}), ('host_set', {'capabilities': [1]}),
                                    ('decision_wait', {'id': 'd1', 'timeout': True})]:
                self.assertEqual(self.request('tools/call', {'name': name, 'arguments': arguments})['error']['code'], -32602)
            main.assert_not_called()

    def test_protocol_errors_keep_loop_alive(self):
        lines = ['{', '[' * 2000, '[]', json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'missing'}),
                 json.dumps({'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call', 'params': {'name': 'unknown'}}),
                 json.dumps({'jsonrpc': '2.0', 'id': 3, 'method': 'ping'})]
        output = io.StringIO()
        mcp.serve(io.StringIO('\n'.join(lines) + '\n'), output)
        replies = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual([r['error']['code'] for r in replies[:-1]], [-32700, -32700, -32600, -32601, -32602])
        self.assertEqual(replies[-1]['result'], {})
        with mock.patch.object(cli, 'main', side_effect=RuntimeError('fixture crash')):
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                self.assertEqual(self.request('tools/call', {'name': 'run_status'})['error']['code'], -32603)
            self.assertIn('fixture crash', err.getvalue())
        self.assertEqual(self.request('ping')['result'], {})

    def test_subprocess_stdio_protocol(self):
        process = subprocess.Popen(['python3', '-B', str(SCRIPTS / 'gf'), 'mcp'],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True, env=dict(os.environ, GF_ROLE='leader'))
        try:
            for request_id, method, params in [(1, 'initialize', {'protocolVersion': 'test-version'}),
                                                (2, 'tools/list', {}),
                                                (3, 'tools/call', {'name': 'run_init', 'arguments': {
                                                    'project': str(self.repo), 'run_id': 'stdio'}})]:
                process.stdin.write(json.dumps({'jsonrpc': '2.0', 'id': request_id, 'method': method, 'params': params}) + '\n')
                process.stdin.flush()
                reply = json.loads(process.stdout.readline())
                self.assertEqual((reply['id'], reply['jsonrpc']), (request_id, '2.0'))
                self.assertNotIn('error', reply)
                if method == 'initialize':
                    self.assertEqual(reply['result']['protocolVersion'], 'test-version')
                elif method == 'tools/list':
                    self.assertIn('run_init', {t['name'] for t in reply['result']['tools']})
                else:
                    self.assertTrue(json.loads(reply['result']['content'][0]['text'])['ok'])
            process.stdin.close()
            self.assertEqual(process.wait(timeout=10), 0)
            self.assertEqual(process.stdout.read(), '')
            self.assertEqual(process.stderr.read(), '')
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=10)
            for stream in (process.stdin, process.stdout, process.stderr):
                stream.close()


if __name__ == '__main__':
    unittest.main()
