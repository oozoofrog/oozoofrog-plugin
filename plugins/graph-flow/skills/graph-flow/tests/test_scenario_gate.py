"""Real CLI loops: rejection, scope enforcement, and a signed lane 3 approval."""
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
from graphflow import cli
from human_support import approve_plan


class GateScenarioTests(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, {}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name).resolve()
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        os.environ['GF_HOME'] = str(self.root / 'home')
        self.git('init', '-q')
        self.git('config', 'user.name', 'Scenario Test')
        self.git('config', 'user.email', 'scenario@example.invalid')
        self.write('feature.py', 'def double(value):\n    return 0\n')
        self.write('test_feature.py',
                   'import unittest\nfrom feature import double\n\n'
                   'class FeatureTests(unittest.TestCase):\n'
                   '    def test_double(self):\n'
                   '        self.assertEqual(double(3), 6)\n')
        self.write('unowned.txt', 'original\n')
        self.commit('fixture')
        self.command = 'python3 -B -m unittest test_feature -v'
        self.run = None
        self.run = pathlib.Path(self.call('init', 'scenario')['run'])

    def git(self, *args, cwd=None):
        result = subprocess.run(['git', '-C', str(cwd or self.repo)] + list(args),
                                capture_output=True, text=True, check=True)
        return result.stdout.strip()

    def write(self, filename, text):
        (self.repo / filename).write_text(text, encoding='utf-8')

    def commit(self, message, cwd=None):
        self.git('add', 'feature.py', 'test_feature.py', 'unowned.txt', cwd=cwd)
        self.git('commit', '-q', '-m', message, cwd=cwd)
        return self.git('rev-parse', 'HEAD', cwd=cwd)

    def call(self, *args, code=0):
        argv = ['--json', '--project', str(self.repo)]
        if self.run is not None:
            argv += ['--run', str(self.run)]
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            actual = cli.main(argv + list(args))
        self.assertEqual(actual, code, out.getvalue())
        self.assertEqual(len(out.getvalue().splitlines()), 1)
        data = json.loads(out.getvalue())
        if code == 0:
            self.assertTrue(data['ok'], data)
        return data

    def set_plan(self, lane=1):
        nodes = [{'id': 'feature', 'kind': 'work', 'goal': 'Double a value',
                  'grade': 'daily', 'lane': lane, 'owns': ['feature.py'],
                  'checks': [{'id': 'unit', 'type': 'cmd', 'run': self.command}]}]
        if lane == 3:
            nodes.append({'id': 'review-feature', 'kind': 'review', 'goal': 'Check doubling',
                          'target': 'feature', 'lens': 'correctness', 'grade': 'daily',
                          'lane': 1, 'owns': [], 'checks': [{'id': 'cites', 'type': 'cites'}]})
        file = self.root / 'plan.json'
        file.write_text(json.dumps({'schema_version': 1, 'goal': 'CLI loop', 'nodes': nodes}))
        self.call('plan', 'set', str(file))
        approve_plan(self.run)

    def assign(self, node='feature', family='openai'):
        return self.call('assign', node, '--executor', 'subagent', '--model', 'fixture',
                         '--effort', 'high', '--provider', 'fixture', '--family', family,
                         '--isolation', 'shared')

    def test_reject_then_correct_complete_loop(self):
        self.set_plan()
        self.assign()
        brief = self.call('brief', 'feature')
        self.assertEqual(pathlib.Path(brief['path']).read_text(), brief['brief'])
        self.call('start', 'feature')
        red = self.call('red', 'feature')
        self.assertTrue(red['results'][0]['failed_first'])
        self.write('feature.py', 'def double(value):\n    return value + 1\n')
        self.assertEqual(self.call('check', 'run', 'feature', 'unit', code=1)['result'], 'failed')
        self.call('submit', 'feature')
        rejected = self.call('gate', 'feature', code=1)
        self.assertEqual(rejected['verdict'], 'reject')
        rejection = rejected['rejection']
        self.assertTrue({'unit', 'attempt', 'reason', 'evidence', 'scope'}.issubset(rejection))
        log = self.run / rejection['evidence']['log']
        self.assertTrue(log.is_file())
        self.assertIn('AssertionError', log.read_text())
        self.assertEqual(self.call('ready')['ready'], ['feature'])
        self.assertIn('Previous rejection', self.call('brief', 'feature')['brief'])
        self.assertEqual(self.call('start', 'feature')['attempt'], 2)
        self.write('feature.py', 'def double(value):\n    return value * 2\n')
        self.assertEqual(self.call('check', 'run', 'feature', 'unit')['result'], 'passed')
        self.call('submit', 'feature')
        self.assertEqual(self.call('gate', 'feature')['verdict'], 'pass')
        self.assertEqual(self.call('gate', '--final')['result'], 'passed')
        self.assertEqual(self.call('status')['state']['run']['status'], 'complete')

    def test_unowned_file_is_named_in_scope_rejection(self):
        self.set_plan()
        self.assign()
        self.call('start', 'feature')
        self.write('feature.py', 'def double(value):\n    return value * 2\n')
        self.write('unowned.txt', 'changed without ownership\n')
        self.call('submit', 'feature')
        rejected = self.call('gate', 'feature', code=1)
        self.assertEqual(rejected['verdict'], 'reject')
        self.assertIn('scope', rejected['rejection']['reason'])
        self.assertIn('unowned.txt', rejected['rejection']['reason'])

    def test_lane3_committed_merged_reviewed_and_terminal_approved(self):
        self.set_plan(lane=3)
        self.assign()
        self.assign('review-feature', 'claude')
        worker = self.root / 'worker'
        self.git('worktree', 'add', '-q', '-b', 'scenario-worker', str(worker))
        self.call('start', 'feature', '--cwd', str(worker))
        (worker / 'feature.py').write_text('def double(value):\n    return value * 2\n')
        self.call('check', 'run', 'feature', 'unit', '--cwd', str(worker))
        commit = self.commit('implement feature', cwd=worker)
        self.call('submit', 'feature', '--commit', commit, '--branch', 'scenario-worker', '--cwd', str(worker))
        merged = self.call('merge', 'feature')
        self.assertEqual(merged['merged'][0]['commit'], commit)
        self.assertEqual(merged['conflicted'], [])
        self.assertEqual(len(self.git('rev-list', '--parents', '-n', '1', 'HEAD').split()), 3)
        reviewer = ['--role', 'reviewer', '--node', 'review-feature']
        self.call(*reviewer, 'start', 'review-feature')
        findings = self.root / 'findings.json'
        findings.write_text('[]')
        self.call(*reviewer, 'review', 'submit', 'review-feature', '--verdict', 'pass',
                  '--findings', str(findings))
        self.assertEqual(self.call('gate', 'review-feature')['verdict'], 'pass')
        waiting = self.call('gate', 'feature', code=1)
        self.assertEqual(waiting['verdict'], 'needs_approval')
        requests = self.call('decide', 'list')['decisions']
        self.assertEqual(len(requests), 1)
        request = requests[0]
        self.assertEqual((request['purpose'], request['node']), ('lane3', 'feature'))
        self.assertEqual(request['evidence']['command'], [self.command])
        self.assertEqual(request['evidence']['files'], ['feature.py'])
        self.assertEqual(request['evidence']['checks']['unit']['loop']['result'], 'passed')
        with mock.patch.dict(os.environ, {'GF_HUMAN_TERMINAL': '1'}), \
                mock.patch.object(sys.stdin, 'isatty', return_value=True):
            self.call('--role', 'human', 'decide', 'answer', request['id'],
                      '--outcome', 'approved', '--answer', 'Approved for this submission')
        self.assertTrue(self.call('status')['state']['decisions'][request['id']]['verified'])
        self.assertEqual(self.call('gate', 'feature')['verdict'], 'pass')


if __name__ == '__main__':
    unittest.main()
