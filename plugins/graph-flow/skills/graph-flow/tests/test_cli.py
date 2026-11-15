import contextlib
import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock

SCRIPTS = pathlib.Path(__file__).resolve().parent.parent / 'scripts'
sys.path.insert(0, str(SCRIPTS))
from graphflow import cli, core, store


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
        self.assertIs(data['ok'], code == 0)
        if code:
            self.assertIn('code', data)
            self.assertIn('message', data)
        return data

    def set_plan(self):
        return self.call('plan', 'set', str(self.file))

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
        self.assertEqual(self.set_plan()['revision'], 2)
        self.assertEqual(self.call('status', 'a')['node']['attempts'], 0)
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
        self.assertEqual(self.call('ready', code=2)['code'], 'not_implemented')
        self.assertEqual(self.call('submit', '--commit', 'abc', code=2)['code'], 'not_implemented')
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
        self.assertEqual(len(cli.COMMANDS), 29)
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
            self.assertEqual(cli.main(['--json', 'status']), 2)

    def test_optional_constraints(self):
        learn = types.ModuleType('graphflow.learn')
        learn.applying = mock.Mock(return_value=[{'id': 'c1'}])
        with mock.patch.dict(sys.modules, {'graphflow.learn': learn}):
            self.assertEqual(self.set_plan()['constraints_applied'], ['c1'])
        self.assertEqual(store.events(self.run)[-1]['data'], {'ids': ['c1']})

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
