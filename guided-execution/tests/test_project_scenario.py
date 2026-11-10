"""Real local-project scenarios; all review answers are SIMULATED fixture data.

Run normally with unittest discovery, or retain inspectable projects and reports:
  python guided-execution/tests/test_project_scenario.py --output-dir /tmp/notes-demo
The output directory must not exist. Nothing uses the network or installs packages.
The coordinator explicitly fingerprints inputs and invalidates changed work: these
helpers check records, not product correctness or real human authorization.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import unittest

import test_loop_control as control_fixtures
import test_loop_workspace as workspace_fixtures

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
RETAIN = None

# The regression this fixture catches is truncating/overwriting existing output.
BROKEN = '''import argparse
import json
from pathlib import Path

def export(source, destination):
    text = Path(source).read_text(encoding="utf-8")
    with Path(destination).open("w", encoding="utf-8") as output:
        json.dump({"notes": text.upper()}, output, ensure_ascii=False)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("destination")
    args = parser.parse_args()
    export(args.source, args.destination)
'''
# Repair only the producer; tests, sample notes and documentation stay unchanged.
REPAIRED = BROKEN.replace('.open("w",', '.open("x",').replace('text.upper()', 'text')
PROJECT_TESTS = '''import json
from pathlib import Path
import tempfile
import unittest
from export_notes import export

class ExportTests(unittest.TestCase):
    def test_preserves_unicode_and_source_bytes(self):
        with tempfile.TemporaryDirectory() as root:
            source, output = Path(root) / "notes.txt", Path(root) / "export.json"
            source.write_bytes("회의 메모: café 🌱\\n".encode("utf-8"))
            before = source.read_bytes()
            export(source, output)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), {"notes": "회의 메모: café 🌱\\n"})
            self.assertIn("회의 메모", output.read_text(encoding="utf-8"))
            self.assertEqual(source.read_bytes(), before)

    def test_refuses_existing_output_without_modification(self):
        with tempfile.TemporaryDirectory() as root:
            source, output = Path(root) / "notes.txt", Path(root) / "export.json"
            source.write_text("fresh", encoding="utf-8")
            output.write_bytes(b"keep existing export")
            with self.assertRaises(FileExistsError):
                export(source, output)
            self.assertEqual(output.read_bytes(), b"keep existing export")
            self.assertEqual(source.read_bytes(), b"fresh")

if __name__ == "__main__":
    unittest.main()
'''
SMOKE = '''import json
from pathlib import Path
import subprocess
import sys
import tempfile

# Execute the documented argument list, not a second hand-written CLI command.
command = json.loads(Path("usage.json").read_text(encoding="utf-8"))
before = Path("notes.txt").read_bytes()
with tempfile.TemporaryDirectory() as root:
    output = Path(root) / "export.json"
    args = [sys.executable, *command, str(output)]
    first = subprocess.run(args, capture_output=True)
    assert first.returncode == 0, first.stderr
    assert json.loads(output.read_text(encoding="utf-8")) == {"notes": before.decode("utf-8")}
    exported = output.read_bytes()
    second = subprocess.run(args, capture_output=True)
    assert second.returncode != 0, "CLI must refuse overwriting output"
    assert output.read_bytes() == exported
    assert Path("notes.txt").read_bytes() == before
print("Documented JSON CLI passed: Unicode, original source, and existing output preserved")
'''


class ProjectScenarioTests(unittest.TestCase):
    cli = workspace_fixtures.WorkspaceTests.cli
    init = workspace_fixtures.WorkspaceTests.init
    state = workspace_fixtures.WorkspaceTests.state
    status = workspace_fixtures.WorkspaceTests.status
    save_plan = workspace_fixtures.WorkspaceTests.save_plan
    control = control_fixtures.ControlTests.control
    start = control_fixtures.ControlTests.start
    evidence = control_fixtures.ControlTests.evidence
    finish = control_fixtures.ControlTests.finish

    def setUp(self):
        if RETAIN:
            self.root = RETAIN / self._testMethodName
            self.root.mkdir()
        else:
            temporary = tempfile.TemporaryDirectory()
            self.addCleanup(temporary.cleanup)
            self.root = Path(temporary.name)
        self.project = self.root / 'project'
        self.project.mkdir()
        self.workspace = self.project / '.agent-loop' / 'run-1'
        self.brief = self.root / 'brief.md'
        self.brief.write_text('Fixture only: preserve Korean notes and existing exports.\n', encoding='utf-8')
        self.plan_file = self.root / 'plan.json'
        self.commands = {
            'producer': ['-m', 'unittest', '-v', 'test_export'],
            'docs': ['smoke.py'],
            'unrelated': ['-c', 'from pathlib import Path; assert Path("unrelated.txt").read_text() == "keep independent result\\n"'],
        }
        self.check_environment = {'PYTHONIOENCODING': 'utf-8', 'PYTHONHASHSEED': '0'}
        if 'SYSTEMROOT' in os.environ:
            self.check_environment['SYSTEMROOT'] = os.environ['SYSTEMROOT']
        self.plan = {'schema_version': 1, 'goal': 'SIMULATED fixture: export notes to JSON safely',
                     'decisions': [{'id': 'review', 'kind': 'review',
                                    'question': 'SIMULATED fixture review of CLI preview'}],
                     'tasks': []}
        for name, deps, gates, inputs in [
                ('producer', [], [], ['export_notes.py', 'test_export.py', 'notes.txt']),
                ('docs', ['producer'], ['review'], ['export_notes.py', 'notes.txt', 'usage.json', 'smoke.py']),
                ('unrelated', [], [], ['unrelated.txt'])]:
            self.plan['tasks'].append({'id': name, 'title': name, 'depends_on': deps,
                'decision_ids': gates, 'reads': inputs,
                'writes': ['export_notes.py'] if name == 'producer' else [], 'max_attempts': 3,
                'checks': [{'id': 'unit', 'description': 'Observed actual subprocess exit and output',
                            'argv': [sys.executable, '-B', *self.commands[name]]}]})
        self.save_plan()
        for name, content in {'export_notes.py': BROKEN, 'test_export.py': PROJECT_TESTS,
                              'notes.txt': '회의 메모: café 🌱\n', 'smoke.py': SMOKE,
                              'usage.json': '["export_notes.py", "notes.txt"]\n',
                              'unrelated.txt': 'keep independent result\n'}.items():
            (self.project / name).write_text(content, encoding='utf-8')
        self.init()
        self.log_counter = 0

    def revision_manifest(self, task):
        spec = next(item for item in self.plan['tasks'] if item['id'] == task)
        return {
            'files': {name: hashlib.sha256((self.project / name).read_bytes()).hexdigest()
                      for name in sorted(spec['reads'])},
            'runtime': {'version': sys.version, 'platform': platform.platform(),
                        'executable': sys.executable,
                        'executable_sha256': hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest()},
            'environment': self.check_environment,
            'check_configuration': spec['checks'],
        }

    def fingerprint(self, task):
        return hashlib.sha256(json.dumps(self.revision_manifest(task), sort_keys=True).encode()).hexdigest()

    def run_check(self, task, args, expected=0, repair=False):
        """Start before editing, then fingerprint, execute, and record actual output."""
        self.assertEqual(args, self.commands[task], 'Check must match fingerprinted configuration')
        revision = self.fingerprint(task)
        self.start(task, revision)
        if repair:
            self.assertEqual(task, 'producer')
            (self.project / 'export_notes.py').write_text(REPAIRED, encoding='utf-8')
            current = self.fingerprint(task)
            self.assertNotEqual(revision, current)
            self.control('set-revision', '--task', task, '--revision', current,
                         '--reason', 'Measured fingerprint after producer repair, before checks')
            revision = current
        command = [sys.executable, '-B', *args]
        completed = subprocess.run(command, cwd=self.project, capture_output=True,
                                   text=True, encoding='utf-8', timeout=30, env=self.check_environment)
        self.assertEqual(completed.returncode, expected, completed.stdout + completed.stderr)
        self.assertEqual(self.fingerprint(task), revision, 'Check changed its declared inputs')
        self.log_counter += 1
        path = 'evidence/%02d-%s.json' % (self.log_counter, task)
        record = {'command': command, 'returncode': completed.returncode,
                  'stdout': completed.stdout, 'stderr': completed.stderr,
                  'source_fingerprint': revision, 'revision_manifest': self.revision_manifest(task), 'feedback_type': 'SIMULATED fixture, not human evidence'}
        with (self.workspace / path).open('x', encoding='utf-8') as stream:
            json.dump(record, stream, ensure_ascii=False, indent=2)
        result = 'passed' if completed.returncode == 0 else 'failed'
        self.evidence(task=task, path=path, result=result, revision=revision)
        self.finish(task, result, revision)
        return path

    def review(self, outcome):
        self.control('resolve-decision', '--decision', 'review', '--outcome', outcome,
                     '--answer', 'SIMULATED fixture user answer: ' + outcome,
                     '--source', 'fixture://test_project_scenario/' + self._testMethodName)

    def snapshot(self):
        return {str(path.relative_to(self.workspace)): path.read_bytes()
                for path in self.workspace.rglob('*') if path.is_file()}

    def report(self):
        if RETAIN:
            result = subprocess.run([sys.executable, str(SCRIPTS / 'render_report.py'),
                                     '--workspace', str(self.workspace), '--output', str(self.root / 'report.html')],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_real_failure_repair_review_resume_and_input_revalidation(self):
        self.start('docs', self.fingerprint('docs'), ok=False)
        failure_log = self.run_check('producer', ['-m', 'unittest', '-v', 'test_export'], expected=1)
        failure = json.loads((self.workspace / failure_log).read_text(encoding='utf-8'))
        self.assertIn('AssertionError', failure['stderr'])
        self.assertIn('FileExistsError not raised', failure['stderr'])
        self.assertIn('FAILED (failures=2)', failure['stderr'])
        protected = {name: (self.project / name).read_bytes() for name in
                     ['test_export.py', 'notes.txt', 'usage.json', 'smoke.py', 'unrelated.txt']}
        self.run_check('producer', ['-m', 'unittest', '-v', 'test_export'], repair=True)
        self.assertNotEqual(failure['source_fingerprint'], self.fingerprint('producer'))
        self.assertEqual(protected, {name: (self.project / name).read_bytes() for name in protected})
        self.assertIn('docs', self.status()['blocked_by_decisions'])
        self.start('docs', self.fingerprint('docs'), ok=False)
        self.review('approved')
        self.run_check('docs', ['smoke.py'])
        self.run_check('unrelated', ['-c', 'from pathlib import Path; assert Path("unrelated.txt").read_text() == "keep independent result\\n"'])
        self.assertTrue(self.status()['complete'])
        before = self.snapshot()
        self.assertTrue(self.init()['reused'])
        self.assertEqual(self.snapshot(), before, 'Resume must retain history and all evidence')
        independent = self.state()['tasks']['unrelated']
        old_revision = self.fingerprint('producer')
        (self.project / 'notes.txt').write_text('새 메모: résumé 🍀\n', encoding='utf-8')
        self.assertNotEqual(old_revision, self.fingerprint('producer'))
        # This is coordinator responsibility, not automatic source detection by helper.
        self.control('invalidate', '--task', 'producer', '--reason', 'Coordinator observed changed notes.txt fingerprint')
        state = self.state()
        self.assertEqual(state['tasks']['producer']['status'], 'stale')
        self.assertEqual(state['tasks']['docs']['status'], 'stale')
        self.assertEqual(state['tasks']['unrelated'], independent)
        self.assertEqual(state['tasks']['producer']['attempts'], 2)
        self.start('docs', self.fingerprint('docs'), ok=False)
        for path, data in before.items():
            if path.startswith('evidence/'):
                self.assertEqual((self.workspace / path).read_bytes(), data)
        self.run_check('producer', ['-m', 'unittest', '-v', 'test_export'])
        self.run_check('docs', ['smoke.py'])
        self.assertTrue(self.status()['complete'])
        self.assertEqual(self.state()['tasks']['producer']['verified_revision'], self.fingerprint('producer'))
        self.assertIn(failure_log, json.dumps(self.state()['history']))
        self.report()

    def test_simulated_rejection_never_releases_review_gate(self):
        self.run_check('producer', ['-m', 'unittest', '-v', 'test_export'], repair=True)
        self.review('rejected')
        self.start('docs', self.fingerprint('docs'), ok=False)
        self.assertIn('docs', self.status()['blocked_by_decisions'])
        self.assertEqual(self.state()['tasks']['docs']['attempts'], 0)
        self.assertFalse(self.status()['complete'])
        self.report()

    def test_actual_failures_stop_at_attempt_bound_without_reusing_logs(self):
        paths = [self.run_check('producer', ['-m', 'unittest', '-v', 'test_export'], expected=1)
                 for _ in range(3)]
        self.assertEqual(len(set(paths)), 3)
        before = self.snapshot()
        self.start('producer', self.fingerprint('producer'), ok=False)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.status()['exhausted'], ['producer'])
        self.assertEqual(self.state()['tasks']['producer']['attempts'], 3)
        self.assertTrue(self.init()['reused'])
        self.assertEqual(self.snapshot(), before)
        self.report()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path)
    options, remaining = parser.parse_known_args()
    if options.output_dir:
        RETAIN = options.output_dir.resolve()
        RETAIN.mkdir(parents=True, exist_ok=False)
    unittest.main(argv=[sys.argv[0], *remaining])
