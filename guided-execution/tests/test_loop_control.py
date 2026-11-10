"""Exercise coordinator transitions against actual workspace files and CLI calls."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest
import test_loop_workspace as fixtures

CONTROL = Path(__file__).resolve().parents[1] / 'scripts' / 'loop_control.py'


class ControlTests(unittest.TestCase):
    setUp = fixtures.WorkspaceTests.setUp
    save_plan = fixtures.WorkspaceTests.save_plan
    cli = fixtures.WorkspaceTests.cli
    init = fixtures.WorkspaceTests.init
    state = fixtures.WorkspaceTests.state
    save_state = fixtures.WorkspaceTests.save_state
    status = fixtures.WorkspaceTests.status

    def control(self, command, *args, ok=True):
        before = (self.workspace / 'state.json').read_bytes()
        p = subprocess.run([sys.executable, str(CONTROL), command, '--workspace',
                            str(self.workspace), *map(str, args)],
                           cwd=self.root, capture_output=True, text=True)
        if ok:
            self.assertEqual(p.returncode, 0, p.stderr)
            result = json.loads(p.stdout)
            self.assertEqual(result['verification_scope'], 'record_integrity_only')
            return result
        self.assertNotEqual(p.returncode, 0)
        self.assertTrue(p.stderr.startswith('error:'), p.stderr)
        self.assertNotIn('Traceback', p.stderr)
        self.assertEqual((self.workspace / 'state.json').read_bytes(), before)
        return p.stderr

    def start(self, task='build', revision='r1', ok=True):
        return self.control('start', '--task', task, '--revision', revision, ok=ok)

    def evidence(self, task='build', check='unit', path='evidence/check.log', result='passed', revision='r1', ok=True):
        return self.control('record-check', '--task', task, '--check', check,
                            '--path', path, '--result', result, '--revision', revision, ok=ok)

    def finish(self, task='build', result='passed', revision='r1', ok=True):
        return self.control('finish', '--task', task, '--result', result,
                            '--revision', revision, '--reason', 'Observed result', ok=ok)

    def log(self, path='evidence/check.log'):
        (self.workspace / path).write_text('Actual fixture observation\n')

    def pass_task(self, task):
        self.start(task)
        path = 'evidence/' + task + '.log'
        self.log(path)
        self.evidence(task=task, path=path)
        self.finish(task)

    def test_requirement_todos_progress_only_with_their_task_and_never_pass_it(self):
        self.plan['requirements'] = [{'id': 'export', 'text': 'Export notes as JSON'}]
        self.save_plan()
        self.init()
        self.control('todo-add', '--todo', 'write', '--title', 'Write the exporter', '--task', 'build',
                     '--requirement', 'export')
        self.control('todo-add', '--todo', 'docs', '--title', 'Document it', '--task', 'build')
        self.control('todo-add', '--todo', 'write', '--title', 'Again', '--task', 'build', ok=False)
        self.control('todo-add', '--todo', 'x', '--title', 'Unknown task', '--task', 'nope', ok=False)
        self.control('todo-add', '--todo', 'y', '--title', 'Unknown need', '--task', 'build',
                     '--requirement', 'nope', ok=False)
        self.control('todo-set', '--todo', 'write', '--status', 'in_progress', ok=False)
        self.start()
        self.control('todo-set', '--todo', 'write', '--status', 'completed')
        self.control('todo-set', '--todo', 'docs', '--status', 'dropped', ok=False)
        self.control('todo-set', '--todo', 'docs', '--status', 'dropped', '--reason', 'README already covers it')
        state = self.state()
        self.assertEqual([(t['id'], t['status'], t['requirement_id']) for t in state['todos']],
                         [('write', 'completed', 'export'), ('docs', 'dropped', None)])
        self.assertEqual(state['tasks']['build']['status'], 'running')
        self.assertEqual(state['history'][-1]['previous_todo']['status'], 'pending')
        self.cli('check', '--workspace', self.workspace)

    def test_runs_without_requirements_or_todos_stay_valid(self):
        for bad in ([{'id': 'r'}], [{'id': 'r', 'text': 'A'}, {'id': 'r', 'text': 'B'}]):
            self.plan['requirements'] = bad
            self.save_plan()
            self.cli('validate-plan', '--plan', self.plan_file, ok=False)
        del self.plan['requirements']
        self.save_plan()
        self.init()
        self.assertNotIn('todos', self.state())
        self.cli('check', '--workspace', self.workspace)
        state = self.state()
        state['todos'] = [{'id': 'a', 'title': 'A', 'task_id': 'build', 'requirement_id': None, 'status': 'done'}]
        self.save_state(state)
        self.cli('check', '--workspace', self.workspace, ok=False)

    def test_start_records_attempt_and_history_without_running_plan_command(self):
        self.init()
        self.start()
        state = self.state()
        self.assertEqual(state['tasks']['build']['status'], 'running')
        self.assertEqual(state['tasks']['build']['attempts'], 1)
        self.assertEqual(state['tasks']['build']['running_revision'], 'r1')
        self.assertEqual(state['history'][0]['action'], 'start')
        self.assertFalse((self.root / 'SHOULD_NOT_RUN').exists())
        self.start(ok=False)

    def test_pass_requires_every_check_at_started_revision(self):
        self.plan['tasks'][0]['checks'].append({'id': 'review', 'description': 'Review'})
        self.save_plan()
        self.init()
        self.start()
        self.finish(ok=False)
        self.log()
        self.evidence(revision='wrong', ok=False)
        self.evidence()
        self.finish(ok=False)
        self.log('evidence/review.log')
        self.evidence(check='review', path='evidence/review.log')
        self.finish(revision='wrong', ok=False)
        self.finish()
        self.assertEqual(self.state()['tasks']['build']['verified_revision'], 'r1')
        self.assertTrue(self.status()['complete'])

    def test_attempt_exhaustion_retains_old_evidence_and_history(self):
        self.plan['tasks'][0]['max_attempts'] = 2
        self.save_plan()
        self.init()
        self.start()
        self.log()
        self.evidence(result='failed')
        self.finish(result='passed', ok=False)
        self.finish(result='failed')
        self.start(revision='r2')
        self.assertEqual(self.state()['tasks']['build']['evidence'], [])
        self.evidence(revision='r2', ok=False)  # Never reuse an earlier path.
        self.finish(result='failed', revision='r2')
        self.start(ok=False)
        self.assertEqual(self.state()['tasks']['build']['attempts'], 2)
        self.assertIn('evidence/check.log', json.dumps(self.state()['history']))
        self.assertEqual((self.workspace / 'evidence/check.log').read_text(), 'Actual fixture observation\n')

    def test_invalid_log_paths_duplicates_and_tampering_are_rejected(self):
        self.init()
        self.start()
        self.log()
        for path in ['../brief.md', 'brief.md', '/etc/passwd', 'evidence/missing.log']:
            self.evidence(path=path, ok=False)
        (self.workspace / 'evidence/alias.log').symlink_to(self.workspace / 'evidence/check.log')
        self.evidence(path='evidence/alias.log', ok=False)
        (self.workspace / 'evidence/link').symlink_to(self.workspace / 'evidence', target_is_directory=True)
        self.evidence(path='evidence/link/check.log', ok=False)
        self.evidence()
        self.log('evidence/second.log')
        self.evidence(path='evidence/second.log', ok=False)
        (self.workspace / 'evidence/check.log').write_text('Overwritten')
        self.finish(ok=False)

    def test_decisions_need_actual_answer_source_outcome_and_pinned_revision(self):
        self.plan['decisions'] = [{'id': 'approval', 'kind': 'authorization',
                                  'question': 'Proceed?', 'artifact_version': 'preview-1'}]
        self.plan['tasks'][0]['decision_ids'] = ['approval']
        self.save_plan()
        self.init()
        self.start(ok=False)
        base = ['--decision', 'approval', '--outcome', 'approved', '--revision', 'preview-1']
        self.control('resolve-decision', *base, '--answer', ' ', '--source', 'message-1', ok=False)
        self.control('resolve-decision', *base, '--answer', 'Yes', '--source', ' ', ok=False)
        self.control('resolve-decision', '--decision', 'approval', '--outcome', 'approved',
                     '--revision', 'wrong', '--answer', 'Yes', '--source', 'message-1', ok=False)
        self.control('resolve-decision', '--decision', 'approval', '--outcome', 'rejected',
                     '--revision', 'preview-1', '--answer', 'No', '--source', 'message-1')
        self.start(ok=False)
        self.assertEqual(self.state()['decisions']['approval']['answer'], 'No')
        self.assertEqual(self.state()['decisions']['approval']['source'], 'message-1')
        self.control('resolve-decision', *base, '--answer', 'Yes', '--source', 'message-2', ok=False)

    def test_invalidation_preserves_unrelated_passes_and_attempts(self):
        for name, deps in [('child', ['build']), ('leaf', ['child']), ('unrelated', [])]:
            task = copy.deepcopy(self.plan['tasks'][0])
            task.update(id=name, depends_on=deps)
            self.plan['tasks'].append(task)
        self.save_plan()
        self.init()
        self.start('child', ok=False)
        for name in ['build', 'child', 'leaf', 'unrelated']:
            self.pass_task(name)
        before = self.state()['tasks']['unrelated']
        logs = {p.name: p.read_bytes() for p in (self.workspace / 'evidence').iterdir()}
        self.control('invalidate', '--task', 'build', '--reason', 'Input changed')
        tasks = self.state()['tasks']
        self.assertEqual(tasks['unrelated'], before)
        for name in ['build', 'child', 'leaf']:
            self.assertEqual(tasks[name]['status'], 'stale')
            self.assertEqual(tasks[name]['attempts'], 1)
            self.assertIsNone(tasks[name]['verified_revision'])
        self.assertEqual(logs, {p.name: p.read_bytes() for p in (self.workspace / 'evidence').iterdir()})
        self.assertEqual(self.status()['ready'], ['build'])

    def test_block_cancel_and_lock_prevent_start(self):
        self.init()
        lock = self.workspace / '.control.lock'
        lock.write_text('Existing writer')
        self.start(ok=False)
        self.assertEqual(lock.read_text(), 'Existing writer')
        lock.unlink()
        self.control('block', '--task', 'build', '--reason', 'Missing input')
        self.start(ok=False)
        self.assertEqual(self.state()['tasks']['build']['block_reason'], 'Missing input')
        self.control('invalidate', '--task', 'build', '--reason', 'Input now available')
        self.start()
        self.control('cancel', '--task', 'build', '--reason', 'User cancelled')
        self.start(ok=False)
        self.control('invalidate', '--task', 'build', '--reason', 'Retry', ok=False)

    def test_malformed_history_fails_cleanly_without_writing(self):
        self.init()
        state = self.state()
        state['history'] = [{'action': 'start', 'timestamp': 'earlier', 'previous_tasks': []}]
        self.save_state(state)
        self.start(ok=False)

    def test_edited_archived_log_cannot_be_hidden_by_new_attempt(self):
        self.init()
        self.start()
        self.log()
        self.evidence(result='failed')
        self.finish(result='failed')
        self.start(revision='r2')
        (self.workspace / 'evidence/check.log').write_text('Edited old evidence')
        self.finish(result='failed', revision='r2', ok=False)

    def test_actual_approval_opens_gate_and_does_not_consume_question_budget(self):
        self.plan['decisions'] = [{'id': 'approval', 'kind': 'review', 'question': 'Accept?'}]
        self.plan['tasks'][0]['decision_ids'] = ['approval']
        self.plan['question_budget'] = {'max_questions': 0, 'max_rounds': 0}
        self.save_plan()
        self.init()
        self.control('resolve-decision', '--decision', 'approval', '--answer', 'Accept preview',
                     '--source', 'message-17', '--outcome', 'approved')
        self.pass_task('build')
        self.assertTrue(self.status()['complete'])
        self.assertEqual(self.state()['question_usage'], {'questions': 0, 'rounds': 0})

    def test_disjoint_ready_tasks_can_run_concurrently(self):
        other = copy.deepcopy(self.plan['tasks'][0])
        other.update(id='other', reads=['separate/input'], writes=['separate/output'])
        self.plan['tasks'].append(other)
        self.save_plan()
        self.init()
        self.start()
        self.start('other')
        self.assertEqual(self.status()['running'], ['build', 'other'])

    def test_overlapping_running_task_scopes_block_start(self):
        for index, (reads, writes) in enumerate([(['src/new.py'], []), ([], ['src']), (['.'], [])]):
            with self.subTest(reads=reads, writes=writes):
                other = copy.deepcopy(self.plan['tasks'][0])
                other.update(id='other', reads=reads, writes=writes)
                self.plan['tasks'] = [self.plan['tasks'][0], other]
                self.save_plan()
                run_id = 'conflict-' + str(index)
                self.init(run_id=run_id)
                self.workspace = self.project / '.agent-loop' / run_id
                self.start()
                self.start('other', ok=False)

    def test_archived_evidence_survives_reviewed_check_and_task_replan(self):
        self.init()
        self.start()
        self.log()
        self.evidence(result='failed')
        self.finish(result='failed')
        self.start(revision='r2')
        self.finish(result='failed', revision='r2')
        # Simulate explicit coordinator-reviewed replan: the former task is removed,
        # its history is retained, and the new task declares a different check.
        plan = json.loads((self.workspace / 'plan.json').read_text())
        plan['tasks'][0].update(id='replacement', checks=[{'id': 'new-check', 'description': 'New requirement'}])
        data = (json.dumps(plan) + '\n').encode()
        (self.workspace / 'plan.json').write_bytes(data)
        state = self.state()
        state['tasks'] = {'replacement': {'status': 'pending', 'attempts': 0,
                                         'verified_revision': None, 'evidence': []}}
        import hashlib
        state['plan_sha256'] = hashlib.sha256(data).hexdigest()
        self.save_state(state)
        self.start('replacement')
        self.assertIn('evidence/check.log', json.dumps(self.state()['history']))
        (self.workspace / 'evidence/check.log').write_text('Changed archived log')
        self.finish('replacement', result='failed', ok=False)

    def test_set_revision_records_actual_post_work_revision_before_checks(self):
        self.init()
        self.start()
        self.control('set-revision', '--task', 'build', '--revision', 'r2',
                     '--reason', 'Implementation changed artifact fingerprint')
        task = self.state()['tasks']['build']
        self.assertEqual(task['running_revision'], 'r2')
        self.assertEqual(task['attempts'], 1)
        previous = self.state()['history'][-1]['previous_tasks']['build']
        self.assertEqual(previous['running_revision'], 'r1')
        self.log()
        self.evidence(revision='r1', ok=False)
        self.evidence(revision='r2')
        self.finish(revision='r2')
        self.assertTrue(self.status()['complete'])

    def test_set_revision_rejects_existing_evidence_or_nonrunning_task(self):
        self.init()
        self.control('set-revision', '--task', 'build', '--revision', 'r2',
                     '--reason', 'Changed', ok=False)
        self.start()
        self.control('set-revision', '--task', 'build', '--revision', ' ',
                     '--reason', 'Changed', ok=False)
        self.control('set-revision', '--task', 'build', '--revision', 'r2',
                     '--reason', ' ', ok=False)
        self.log()
        self.evidence()
        self.control('set-revision', '--task', 'build', '--revision', 'r2',
                     '--reason', 'Changed', ok=False)

    def test_invalid_input_state_is_not_repaired_or_overwritten(self):
        self.init()
        state = self.state()
        state['tasks']['build']['attempts'] = -1
        self.save_state(state)
        self.start(ok=False)


if __name__ == '__main__':
    unittest.main()
