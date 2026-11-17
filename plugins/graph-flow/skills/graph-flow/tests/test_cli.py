import contextlib
import io
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock

SCRIPTS = pathlib.Path(__file__).resolve().parent.parent / 'scripts'
sys.path.insert(0, str(SCRIPTS))
from graphflow import cli, core, store
from human_support import approve_plan


class CLITests(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, {}, clear=True)
        self.env.start()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name).resolve()
        os.environ['GF_HOME'] = str(self.root / 'home')
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        subprocess.run(['git', 'init', '-q', str(self.repo)], check=True)
        self.run = store.init_run(self.repo, 'test', core.actor_from_env())
        self.file = self.root / 'plan.json'
        self.raw = {'schema_version': 1, 'goal': 'test', 'nodes': [
            {'id': 'a', 'kind': 'work', 'goal': 'a', 'grade': 'daily', 'lane': 1,
             'owns': ['a.py'], 'checks': [{'id': 'unit', 'type': 'cmd', 'run': 'true'}]},
            {'id': 'r', 'kind': 'review', 'goal': 'review', 'grade': 'daily',
             'lane': 1, 'target': 'a', 'lens': 'bugs', 'checks': []}]}
        self.write()

    def tearDown(self):
        self.tmp.cleanup()
        self.env.stop()

    def write(self):
        self.file.write_text(json.dumps(self.raw))

    def call(self, *args, code=0):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            result = cli.main(['--json', '--run', str(self.run)] + list(args))
        self.assertEqual(result, code, out.getvalue())
        lines = out.getvalue().splitlines()
        self.assertEqual(len(lines), 1)
        data = json.loads(lines[0])
        self.assertIs(data['ok'], code == 0 or 'code' not in data)
        if code and not data['ok']:
            self.assertIn('code', data)
            self.assertIn('message', data)
        return data

    def set_plan(self):
        result = self.call('plan', 'set', str(self.file))
        approve_plan(self.run)
        return result

    def test_init_and_host(self):
        data = self.call('--project', str(self.repo), 'init', 'second')
        self.assertTrue(pathlib.Path(data['run']).is_absolute())
        self.call('--project', str(self.repo), 'init', 'second', code=4)
        self.assertEqual(self.call('host', 'set', 'workflow')['capabilities'], ['workflow'])
        self.assertEqual(self.call('status')['state']['run']['host'], ['workflow'])
        self.call('host', 'set', code=2)

    def test_validate_and_atomic_failure(self):
        self.call('plan', 'validate', str(self.file))
        before = (self.run / 'events.jsonl').read_bytes()
        self.raw['nodes'] = []
        self.write()
        self.assertTrue(self.call('plan', 'validate', str(self.file), code=1)['problems'])
        self.call('plan', 'set', str(self.file), code=1)
        self.assertEqual(list((self.run / 'plans').iterdir()), [])
        self.assertEqual((self.run / 'events.jsonl').read_bytes(), before)
        self.file.write_text('{')
        self.assertEqual(self.call('plan', 'validate', str(self.file), code=2)['code'], 'bad_json')
        self.call('plan', 'set', str(self.file), code=2)

    def test_revisions_reset_changed_node(self):
        self.assertEqual(self.set_plan()['revision'], 1)
        with store.transaction(self.run) as tx:
            tx.append('node.start', {'node': 'a', 'attempt': 1, 'base': {}, 'cwd': str(self.repo)}, core.actor_from_env())
        self.assertEqual(self.call('status', 'a')['node']['attempts'], 1)
        self.raw['nodes'][0]['goal'] = 'changed'
        self.write()
        self.assertEqual(self.call('plan', 'set', str(self.file), code=4)['code'], 'active_plan_change')
        self.assertEqual(self.call('status', 'a')['node']['attempts'], 1)
        self.call('status', 'missing', code=4)

    def test_roles_and_views(self):
        self.set_plan()
        self.call('--role', 'worker', '--node', 'a', 'plan', 'set', str(self.file), code=3)
        data = self.call('--role', 'worker', '--node', 'a', 'status')
        self.assertEqual(set(data), {'ok', 'node', 'id'})
        self.call('--role', 'worker', '--node', 'a', 'status', 'r', code=3)
        data = self.call('--role', 'reviewer', '--node', 'r', 'status')
        self.assertEqual(set(data['state']['nodes']), {'r', 'a'})
        self.call('--role', 'reviewer', '--node', 'r', 'status', 'a')
        self.assertIn('ready', self.call('--role', 'human', 'status'))
        self.assertEqual(self.call('decide', 'answer', code=3)['code'], 'forbidden')
        self.assertEqual(self.call('ready')['ready'], ['a'])
        self.assertEqual(self.call('submit', '--commit', 'abc', code=2)['code'], 'usage')
        self.call('--role', 'worker', 'status', code=2)
        self.call('--role', 'bogus', 'status', code=2)

    def test_environment_and_usage(self):
        self.set_plan()
        os.environ.update(GF_RUN=str(self.run), GF_ROLE='worker', GF_NODE='a')
        self.call('status')
        self.call('--role', 'leader', 'status')
        self.call('unknown', code=2)
        self.call('--unknown', code=2)
        self.call('plan', code=2)
        with mock.patch.object(cli.state, 'derive', side_effect=RuntimeError('oops')):
            self.assertEqual(self.call('status', code=5)['code'], 'internal')

    def test_registry_role_table(self):
        self.assertEqual(len(cli.COMMANDS), 31)
        for path, entry in cli.COMMANDS.items():
            for role in core.ROLES:
                if role in entry['roles']:
                    continue
                args = ['--role', role, '--node', 'a'] + list(path)
                if path == ('init',):
                    args.append('new')
                elif path == ('plan', 'set'):
                    args.append(str(self.file))
                elif path == ('host', 'set'):
                    args.append('workflow')
                with self.subTest(path=path, role=role):
                    self.assertEqual(self.call(*args, code=3)['code'], 'forbidden')

    def test_human_output_and_no_run(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(cli.main(['plan', 'validate', str(self.file)]), 0)
        self.assertIn('problems', out.getvalue())
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(['--json', 'ready']), 2)

    def test_optional_constraints(self):
        learn = types.ModuleType('graphflow.learn')
        learn.applying = mock.Mock(return_value=[{'id': 'c1'}])
        with mock.patch.dict(sys.modules, {'graphflow.learn': learn}):
            self.assertEqual(self.set_plan()['constraints_applied'], ['c1'])
        self.assertEqual(next(e['data'] for e in store.events(self.run) if e['type'] == 'constraint.apply'), {'ids': ['c1']})

    def git(self, *args):
        result = subprocess.run(['git', '-C', str(self.repo)] + list(args),
                                capture_output=True, text=True, check=True)
        return result.stdout.strip()

    def loop_plan(self, command='true'):
        self.git('config', 'user.name', 'CLI Test')
        self.git('config', 'user.email', 'cli@example.invalid')
        (self.repo / 'a.py').write_text('value = 0\n')
        self.git('add', 'a.py')
        self.git('commit', '-q', '-m', 'fixture')
        self.raw['nodes'][0]['checks'] = [
            {'id': 'unit', 'type': 'cmd', 'run': command},
            {'id': 'ide', 'type': 'host', 'tool': 'test', 'expect': 'green'}]
        self.write()
        self.set_plan()

    def assign_node(self, node='a', family='openai'):
        return self.call('assign', node, '--executor', 'subagent', '--model', 'fixture',
                         '--effort', 'high', '--provider', 'fixture', '--family', family,
                         '--isolation', 'shared')

    def test_ready_route_assign_and_briefs(self):
        self.loop_plan()
        self.assertEqual(self.call('ready')['ready'], ['a'])
        self.assertEqual(self.assign_node()['family'], 'openai')
        self.call('assign', 'a', '--executor', 'invalid', '--model', 'm', '--effort', 'high',
                  '--provider', 'p', '--family', 'openai', '--isolation', 'shared', code=2)
        self.call('host', 'set', 'subagent')
        with mock.patch.object(cli.route, 'load_usage', return_value={}):
            self.assertEqual(self.call('route', 'a')['executor'], 'subagent')
            self.assertEqual(self.call('route', 'r')['family'], 'claude')
            self.assertNotIn('target_family', self.call('status', 'r')['node'])
            self.call('route', 'missing', code=4)
        result = self.call('brief', 'a')
        self.assertEqual(pathlib.Path(result['path']).read_text(), result['brief'])
        self.call('brief', 'missing', code=4)
        self.assertIn('Planning brief', self.call('brief', '--plan')['brief'])
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(cli.main(['--run', str(self.run), 'brief', 'a']), 0)
        self.assertEqual(out.getvalue(), result['brief'])
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(cli.main(['--json', '--project', str(self.repo), 'brief', '--plan']), 0)
        self.assertIn('Planning brief', json.loads(out.getvalue())['brief'])
        self.call('brief', 'a', '--plan', code=2)
        self.call('--run', str(self.root / 'missing'), 'ready', code=4)

    def test_work_loop_checks_and_submit(self):
        self.loop_plan('false')
        self.call('red', 'a', code=4)
        self.call('check', 'run', 'a', 'unit', code=4)
        self.call('check', 'record', 'a', 'ide', '--result', 'passed', code=4)
        self.call('submit', 'a', code=4)
        self.assertEqual(self.call('start', 'a', '--cwd', str(self.repo))['attempt'], 1)
        self.call('start', 'a', code=4)
        self.assertTrue(self.call('red', 'a', 'unit', '--cwd', str(self.repo))['results'][0]['failed_first'])
        self.assertEqual(self.call('red', 'a', 'unknown', code=4)['code'], 'unknown_check')
        result = self.call('check', 'run', 'a', 'unit', '--cwd', str(self.repo), code=1)
        self.assertEqual((result['result'], result['phase']), ('failed', 'loop'))
        self.assertTrue(result['ok'])
        self.assertEqual(self.call('check', 'run', 'a', 'missing', code=4)['code'], 'unknown_check')
        self.assertEqual(self.call('check', 'run', 'a', 'ide', code=4)['code'], 'wrong_check_type')
        self.assertEqual(self.call('check', 'record', 'a', 'ide', '--result', 'passed',
                                   '--note', 'observed')['note'], 'observed')
        submitted = self.call('submit', 'a', '--notes', 'done', '--branch', 'fixture',
                              '--low-confidence', 'one', 'two', '--low-confidence', 'three',
                              '--cwd', str(self.repo))
        self.assertEqual(submitted['low_confidence'], ['one', 'two', 'three'])
        self.assertEqual(submitted['notes'], 'done')
        self.call('submit', 'a', code=4)

    def test_gate_final_reopen_and_human_rejection(self):
        self.loop_plan()
        self.call('gate', 'a', code=4)
        self.call('reopen', 'a', '--reason', 'retry', code=4)
        self.call('start', 'a')
        self.assertEqual(self.call('check', 'run', 'a', 'unit')['result'], 'passed')
        self.call('check', 'record', 'a', 'ide', '--result', 'passed')
        self.call('submit', 'a')
        self.assertEqual(self.call('gate', 'a', '--cwd', str(self.repo))['verdict'], 'pass')
        self.assertEqual(self.call('gate', '--final')['result'], 'passed')
        self.assertEqual(self.call('reopen', 'a', '--reason', 'retry')['invalidated'], ['a', 'r'])
        self.call('start', 'a')
        self.call('submit', 'a')
        (self.repo / 'outside.txt').write_text('outside scope')
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(cli.main(['--run', str(self.run), 'gate', 'a']), 1)
        self.assertIn('UNIT      a', out.getvalue())
        self.assertIn('SCOPE', out.getvalue())
        self.raw['integration_checks'] = [{'id': 'final', 'type': 'cmd', 'run': 'false'}]
        self.write()
        self.set_plan()
        self.assertEqual(self.call('gate', '--final', code=1)['result'], 'failed')
        self.call('gate', 'a', '--final', code=2)

    def test_review_submit_validates_json_and_role(self):
        self.loop_plan()
        findings = self.root / 'findings.json'
        findings.write_text('[]')
        role = ['--role', 'reviewer', '--node', 'r']
        self.call(*role, 'review', 'submit', 'r', '--verdict', 'pass', '--findings', str(findings), code=4)
        self.call('start', 'a')
        self.call('submit', 'a')
        self.call(*role, 'start', 'r')
        for value in ('{', '{}', 'null'):
            findings.write_text(value)
            self.assertEqual(self.call(*role, 'review', 'submit', 'r', '--verdict', 'pass',
                                       '--findings', str(findings), code=2)['code'], 'bad_json')
        findings.write_text('[]')
        self.assertEqual(self.call(*role, 'review', 'submit', 'r', '--verdict', 'pass',
                                   '--findings', str(findings))['target'], 'a')
        self.assertEqual(self.call('gate', 'r')['verdict'], 'pass')

    def test_merge_committed_submission(self):
        self.loop_plan()
        self.call('merge', 'a', code=4)
        self.call('start', 'a')
        (self.repo / 'a.py').write_text('value = 1\n')
        self.git('add', 'a.py')
        self.git('commit', '-q', '-m', 'submission')
        commit = self.git('rev-parse', 'HEAD')
        self.call('submit', 'a', '--commit', commit)
        result = self.call('merge', 'a')
        self.assertEqual(result['merged'][0]['commit'], commit)
        self.assertEqual(result['conflicted'], [])

    def test_own_node_limits(self):
        self.loop_plan()
        worker = ['--role', 'worker', '--node', 'a']
        for command in (['start', 'r'], ['red', 'r'], ['check', 'run', 'r', 'unit'],
                        ['check', 'record', 'r', 'ide', '--result', 'passed'], ['submit', 'r']):
            with self.subTest(command=command):
                self.assertEqual(self.call(*(worker + command), code=3)['code'], 'forbidden')
        reviewer = ['--role', 'reviewer', '--node', 'r']
        self.call(*reviewer, 'start', 'a', code=3)
        self.call(*reviewer, 'review', 'submit', 'a', '--verdict', 'pass', '--findings', 'unused', code=3)
        self.call(*worker, 'start', '', code=3)
        self.call(*worker, 'start', 'a')
        self.call(*worker, 'red', 'a')
        self.call(*worker, 'check', 'run', 'a', 'unit')
        self.call(*worker, 'check', 'record', 'a', 'ide', '--result', 'passed')
        self.call(*worker, 'submit', 'a')
        self.call(*reviewer, 'start', 'r')
        findings = self.root / 'findings.json'
        findings.write_text('[]')
        self.call(*reviewer, 'review', 'submit', 'r', '--verdict', 'pass', '--findings', str(findings))

    def test_decisions_binding_wait_and_verified_terminal_answer(self):
        self.loop_plan()
        worker = ['--role', 'worker', '--node', 'a']
        reviewer = ['--role', 'reviewer', '--node', 'r']
        first = self.call(*worker, 'decide', 'ask', '--kind', 'information', '--question', 'Which?',
                          '--check', 'unit', '--purpose', 'free', '--command', 'echo test',
                          '--files', 'a.py')
        self.assertEqual(first['node'], 'a')
        self.assertEqual(first['evidence'], {'command': 'echo test', 'files': ['a.py'], 'checks': []})
        second = self.call(*reviewer, 'decide', 'ask', '--kind', 'review', '--question', 'Review?')
        free = self.call('decide', 'ask', '--kind', 'direction', '--question', 'Direction?')
        self.assertIsNone(free['node'])
        for role, other in ((worker, 'r'), (reviewer, 'a')):
            self.call(*role, 'decide', 'ask', '--kind', 'direction', '--question', '?', '--node', other, code=3)
        self.call('decide', 'ask', '--kind', 'invalid', '--question', '?', code=2)
        self.assertEqual([d['id'] for d in self.call(*worker, 'decide', 'list')['decisions']], [first['id']])
        self.assertEqual([d['id'] for d in self.call(*reviewer, 'decide', 'list')['decisions']], [second['id']])
        self.assertEqual(len(self.call('decide', 'list')['decisions']), 3)
        self.call(*worker, 'decide', 'wait', free['id'], '--timeout', '0', code=3)
        self.call(*worker, 'decide', 'wait', second['id'], '--timeout', '0', code=3)
        self.call(*reviewer, 'decide', 'wait', first['id'], '--timeout', '0', code=3)
        self.assertEqual(self.call(*worker, 'decide', 'wait', first['id'], '--timeout', '0', code=1)['code'], 'wait_timeout')
        self.call('decide', 'wait', 'missing', '--timeout', '0', code=4)
        answer = ['decide', 'answer', first['id'], '--outcome', 'answered', '--answer', 'That one']
        self.assertIn('role human', self.call(*answer, code=3)['message'])
        self.assertIn('GF_HUMAN_TERMINAL=1', self.call('--role', 'human', *answer, code=3)['message'])
        os.environ['GF_HUMAN_TERMINAL'] = '1'
        with mock.patch.object(sys.stdin, 'isatty', return_value=False):
            self.assertIn('TTY', self.call('--role', 'human', *answer, code=3)['message'])
        with mock.patch.object(sys.stdin, 'isatty', return_value=True):
            self.call('--role', 'human', 'decide', 'answer', first['id'], '--outcome', 'approved', code=2)
            self.assertEqual(self.call('--role', 'human', *answer)['source'], 'terminal')
            self.call('--role', 'human', *answer, code=4)
        decision = self.call('status')['state']['decisions'][first['id']]
        self.assertTrue(decision['verified'])
        self.assertEqual(self.call(*worker, 'decide', 'wait', first['id'])['answer'], 'That one')
        self.call('--run', str(self.root / 'missing'), 'decide', 'list', code=4)

    def test_lazy_learn_and_trace_absence(self):
        commands = [
            ['learn', 'add', '--from', 'a', '--text', 'rule', '--review-when', 'later'],
            ['learn', 'list'], ['learn', 'promote', 'c1', '--run', 'true'],
            ['learn', 'retire', 'c1', '--reason', 'old'], ['trace']]
        with mock.patch.object(cli, '_lazy_import', side_effect=core.GFError('not_implemented', 'absent')):
            for command in commands:
                with self.subTest(command=command):
                    self.assertEqual(self.call(*command, code=2)['code'], 'not_implemented')
        for name in ('learn', 'trace'):
            missing = ModuleNotFoundError(name='graphflow.' + name)
            with mock.patch.object(cli.importlib, 'import_module', side_effect=missing):
                self.assertEqual(self.call(*(['learn', 'list'] if name == 'learn' else ['trace']), code=2)['code'], 'not_implemented')

    def test_serve_absence_and_lazy_dispatch(self):
        missing = ModuleNotFoundError(name='graphflow.server')
        with mock.patch.object(cli.importlib, 'import_module', side_effect=missing):
            self.assertEqual(self.call('serve', code=2)['code'], 'not_implemented')
        server = types.SimpleNamespace(serve=mock.Mock())
        with mock.patch.object(cli, '_lazy_import', return_value=server):
            self.call('serve', '--port', '12345')
            server.serve.assert_called_once_with(port=12345)
            server.serve.reset_mock()
            self.call('serve')
            server.serve.assert_called_once_with(port=0)

    def test_open_dispatch_stop_and_roles(self):
        server = types.SimpleNamespace(
            open_dashboard=mock.Mock(return_value={"opened": True, "started": True, "port": 5}),
            stop_dashboard=mock.Mock(side_effect=[True, False]))
        with mock.patch.object(cli, '_lazy_import', return_value=server):
            opened = self.call('open')
            self.assertEqual(opened, {'ok': True, 'opened': True, 'started': True, 'port': 5,
                                      'message': 'Dashboard opened in the browser.'})
            self.assertEqual(self.call('open', '--stop')['stopped'], True)
            self.assertEqual(self.call('open', '--stop')['message'], 'No dashboard is running.')
            server.open_dashboard.assert_called_once_with(target={
                'project': str(store.project_of(self.run)), 'run': self.run.name, 'decision': None, 'node': None})
            server.open_dashboard.reset_mock()
            shown = self.call('open', '--decision', 'd4')
            self.assertEqual(shown['message'], 'Dashboard opened in the browser on d4.')
            self.assertEqual(server.open_dashboard.call_args.kwargs['target']['decision'], 'd4')
            self.call('open', '--node', 'a')
            self.assertEqual(server.open_dashboard.call_args.kwargs['target']['node'], 'a')
            # Without a run there is nothing to point at.
            out = io.StringIO()
            with mock.patch.dict(os.environ), contextlib.redirect_stdout(out):
                os.environ.pop('GF_RUN', None)
                self.assertEqual(cli.main(['--json', 'open', '--decision', 'd4']), 2)
                server.open_dashboard.reset_mock()
                self.assertEqual(cli.main(['--json', 'open']), 0)
                server.open_dashboard.assert_called_once_with()
            self.assertEqual(json.loads(out.getvalue().splitlines()[0])['code'], 'run_required')
            for role in ('worker', 'reviewer'):
                with mock.patch.dict(os.environ, GF_ROLE=role, GF_NODE='n'):
                    self.assertEqual(self.call('open', code=3)['code'], 'forbidden')

    def test_status_without_a_run_lists_the_projects_runs(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(cli.main(['--json', '--project', str(self.repo), 'status']), 0)
        listed = json.loads(out.getvalue())
        self.assertEqual([(r['id'], r['run'], r['status'], r['open_decisions']) for r in listed['runs']],
                         [('test', str(self.run), 'open', [])])
        self.assertIn('GF_RUN', listed['message'])
        out = io.StringIO()
        with mock.patch.dict(os.environ, GF_ROLE='worker', GF_NODE='a'), contextlib.redirect_stdout(out):
            self.assertEqual(cli.main(['--json', '--project', str(self.repo), 'status']), 2)
        self.assertEqual(json.loads(out.getvalue())['code'], 'run_required')

    def test_setup_installs_a_working_command_and_keeps_foreign_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            bin_dir = pathlib.Path(temporary).resolve() / "bin"
            with mock.patch.dict(os.environ, PATH=os.pathsep.join([str(bin_dir), "/usr/bin"])):
                installed = self.call('setup', '--bin-dir', str(bin_dir))
            self.assertEqual((installed['installed'], installed['commands'], installed['on_path']),
                             (str(bin_dir / "graph-flow"), ["graph-flow", "gf"], True))
            for name in ("graph-flow", "gf"):
                self.assertTrue(os.access(str(bin_dir / name), os.X_OK))
                ran = subprocess.run([sys.executable, str(bin_dir / name), "--json", "plan", "validate",
                                      "/nonexistent"], capture_output=True, text=True)
                self.assertEqual((bin_dir / name).read_text().splitlines()[0], "#!/usr/bin/env python3")
                self.assertEqual(json.loads(ran.stdout)["ok"], False)
            with mock.patch.dict(os.environ, PATH="/usr/bin"):
                again = self.call('setup', '--bin-dir', str(bin_dir))
            self.assertFalse(again['on_path'])
            self.assertIn('export PATH="%s:$PATH"' % bin_dir, again['message'])
            self.assertEqual(self.call('setup', '--bin-dir', str(bin_dir), '--remove')['commands'], ["graph-flow", "gf"])
            self.assertEqual(self.call('setup', '--bin-dir', str(bin_dir), '--remove')['removed'], False)
            # A `gf` that belongs to another program stays; `graph-flow` is still installed.
            (bin_dir / "gf").write_text("#!/bin/sh\necho other\n")
            partial = self.call('setup', '--bin-dir', str(bin_dir))
            self.assertEqual(partial['commands'], ["graph-flow"])
            self.assertIn("left alone", partial['message'])
            self.assertEqual(self.call('setup', '--bin-dir', str(bin_dir), '--remove')['commands'], ["graph-flow"])
            self.assertEqual((bin_dir / "gf").read_text(), "#!/bin/sh\necho other\n")
            (bin_dir / "graph-flow").write_text("#!/bin/sh\necho other\n")
            self.assertEqual(self.call('setup', '--bin-dir', str(bin_dir), code=4)['code'], 'exists')
            self.assertEqual(self.call('setup', '--bin-dir', str(bin_dir), '--remove')['removed'], False)
            self.assertEqual((bin_dir / "graph-flow").read_text(), "#!/bin/sh\necho other\n")
            with mock.patch.dict(os.environ, GF_ROLE='worker', GF_NODE='n'):
                self.assertEqual(self.call('setup', code=3)['code'], 'forbidden')

    def test_launcher_follows_the_newest_installed_version(self):
        from graphflow import launcher
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary).resolve()
            scripts = {}
            for version in ("0.1.1", "0.2.0", "0.10.0", "tmp-abc123"):
                scripts[version] = root / "cache" / "graph-flow" / version / "skills" / "graph-flow" / "scripts" / "gf"
                scripts[version].parent.mkdir(parents=True)
                scripts[version].write_text("print(%r)\n" % version)
            launcher.install(root / "bin", scripts["0.1.1"])
            run = lambda: subprocess.run([sys.executable, str(root / "bin" / "graph-flow")], capture_output=True, text=True)
            self.assertEqual(run().stdout.strip(), "0.10.0")
            shutil.rmtree(str(scripts["0.10.0"].parents[3]))
            shutil.rmtree(str(scripts["0.1.1"].parents[3]))
            self.assertEqual(run().stdout.strip(), "0.2.0")
            shutil.rmtree(str(root / "cache"))
            gone = run()
            self.assertEqual(gone.returncode, 5)
            self.assertIn("run gf setup again", gone.stderr)
            plain = root / "checkout" / "skills" / "graph-flow" / "scripts" / "gf"
            plain.parent.mkdir(parents=True)
            plain.write_text("print('checkout')\n")
            launcher.install(root / "bin", plain)
            self.assertEqual(run().stdout.strip(), "checkout")

    def test_mcp_eof_has_no_cli_envelope(self):
        out = io.StringIO()
        with mock.patch.object(sys, 'stdin', io.StringIO('')), contextlib.redirect_stdout(out):
            self.assertEqual(cli.main(['--json', 'mcp']), 0)
        self.assertEqual(out.getvalue(), '')

    def test_lazy_learn_and_trace_dispatch(self):
        actor = core.actor_from_env()
        learn = types.SimpleNamespace(
            add=mock.Mock(return_value={'id': 'c1'}),
            all_constraints=mock.Mock(return_value=[{'id': 'c1'}]),
            promote=mock.Mock(return_value={'constraint': {'id': 'c1'}, 'check': {}}),
            retire=mock.Mock(return_value={'constraint': {'id': 'c1'}}))
        trace = types.SimpleNamespace(trace=mock.Mock(return_value={'run': {'attempts': 1}, 'nodes': {}}))
        with mock.patch.object(cli, '_lazy_import', side_effect=lambda name: {'learn': learn, 'trace': trace}[name]):
            self.assertEqual(self.call('learn', 'add', '--from', 'a', '--text', 'rule',
                                       '--review-when', 'later', '--paths', 'a.py', '--tags', 'python')['id'], 'c1')
            learn.add.assert_called_once_with(self.repo, str(self.run), 'a', 'rule', 'later', ['a.py'], ['python'], actor)
            self.assertEqual(self.call('learn', 'list')['constraints'], [{'id': 'c1'}])
            learn.all_constraints.assert_called_once_with(self.repo)
            self.call('learn', 'promote', 'c1', '--run', 'true')
            learn.promote.assert_called_once_with(self.repo, 'c1', 'true', actor, str(self.run))
            self.call('learn', 'retire', 'c1', '--reason', 'obsolete')
            learn.retire.assert_called_once_with(self.repo, 'c1', 'obsolete', actor, str(self.run))
            self.assertEqual(self.call('trace')['run']['attempts'], 1)
            trace.trace.assert_called_once_with(str(self.run))
            for command in (['learn', 'add', '--from', 'a', '--text', 'rule', '--review-when', 'later'],
                            ['learn', 'list'], ['learn', 'promote', 'c1', '--run', 'true'],
                            ['learn', 'retire', 'c1', '--reason', 'old'], ['trace']):
                function = trace.trace if command[0] == 'trace' else getattr(learn, {'list': 'all_constraints'}.get(command[1], command[1]))
                function.side_effect = core.GFError('fixture_failure', 'library failure', 4)
                self.assertEqual(self.call(*command, code=4)['code'], 'fixture_failure')

    def test_subprocess_success(self):
        result = subprocess.run(['python3', '-B', str(SCRIPTS / 'gf'), '--json',
                                 '--project', str(self.repo), 'init', 'sub'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)['ok'])

    def test_subprocess_usage_failure(self):
        result = subprocess.run(['python3', '-B', str(SCRIPTS / 'gf'), '--json', 'plan'],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)['code'], 'usage')


if __name__ == '__main__':
    unittest.main()
