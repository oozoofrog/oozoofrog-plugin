"""Consent binds to structure, has one human signing path, and never blocks old runs."""
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from graphflow import cli, core, decisions, graph, mcp, plan, server, state, store
from human_support import human_answer


class PlanApprovalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        env = mock.patch.dict(os.environ, {'GF_HOME': str(self.root / 'home'), 'GF_NO_OPEN': '1'}, clear=True)
        env.start(); self.addCleanup(env.stop)
        self.project = self.root / 'project'; self.project.mkdir()
        subprocess.run(['git', 'init', '-q', str(self.project)], check=True)
        subprocess.run(['git', '-C', str(self.project), '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '--allow-empty', '-qm', 'fixture'], check=True)
        self.run = store.init_run(self.project, 'approval', core.actor_from_env())
        self.file = self.root / 'plan.json'
        self.raw = {'schema_version': 1, 'title': '안내 만들기', 'goal': '안내 파일을 만들어요', 'nodes': [
            {'id': 'a', 'kind': 'work', 'title': '안내 쓰기', 'goal': '안내를 써요', 'lane': 1, 'grade': 'daily',
             'owns': ['guide.txt'], 'checks': [{'id': 'text', 'type': 'cmd', 'title': '안내가 비어 있지 않아요', 'run': 'test -s guide.txt'}]}]}

    def call(self, *args, code=0):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            actual = cli.main(['--json', '--run', str(self.run)] + list(args))
        data = json.loads(out.getvalue())
        self.assertEqual(actual, code, data)
        return data

    def set_plan(self, raw=None, *flags):
        self.file.write_text(json.dumps(raw or self.raw, ensure_ascii=False))
        return self.call('plan', 'set', str(self.file), *flags)

    def snapshot(self):
        with store.transaction(self.run) as tx:
            return tx.plan, state.derive(tx.plan, tx.events)

    def accept(self, did):
        human_answer(self.run, did, 'approved', '확인했어요')

    def test_blocks_every_dispatch_surface_but_planning_remains_available(self):
        result = self.set_plan()
        did = result['decision']
        commands = [('ready',), ('start', 'a'), ('brief', 'a'), ('gate', '--final'),
                    ('assign', 'a', '--executor', 'inline', '--model', 'test', '--effort', 'high', '--provider', 'test', '--family', 'openai', '--isolation', 'shared')]
        for command in commands:
            error = self.call(*command, code=4)
            self.assertEqual(error['code'], 'plan_not_approved')
            self.assertIn('gf open --decision ' + did, error['message'])
        for role in ('worker', 'reviewer'):
            self.assertEqual(self.call('--role', role, '--node', 'a', 'start', 'a', code=4)['code'], 'plan_not_approved')
        self.call('brief', '--plan'); self.call('status'); self.call('trace')
        self.call('plan', 'validate', str(self.file)); self.call('decide', 'list')
        self.call('decide', 'wait', did, '--timeout', '0', code=1)
        self.assertEqual(self.snapshot()[1]['decisions'][did]['question'], '이 계획대로 시작할까요?')
        self.accept(did)
        self.assertEqual(self.call('ready')['ready'], ['a'])
        self.call('brief', 'a'); self.call('start', 'a')

    def test_every_new_revision_requires_consent_unchanged_work_is_preserved(self):
        first = self.set_plan()['decision']; self.accept(first)
        revised = copy.deepcopy(self.raw)
        revised.update(title='새 안내', context={'note': '설명만 바꿨어요'})
        revised['nodes'][0].update(title='안내 정리', summary='읽기 쉽게 정리해요')
        revised['nodes'][0]['checks'][0]['title'] = '내용이 있어요'
        wording = self.set_plan(revised)['decision']
        self.assertNotEqual(wording, first)
        self.call('ready', code=4)
        self.accept(wording)
        self.call('ready')
        revised['nodes'][0]['checks'][0]['run'] = 'test -s guide.txt && test -r guide.txt'
        second = self.set_plan(revised)['decision']
        self.assertNotEqual(first, second)
        self.assertEqual(self.snapshot()[1]['decisions'][first]['status'], 'superseded')
        self.call('ready', code=4)

    def test_send_back_text_and_same_structure_resubmission(self):
        first = self.set_plan()['decision']
        human_answer(self.run, first, 'revision_requested', '검사 내용을 쉽게 써 주세요')
        self.call('ready', code=4)
        second = self.set_plan()['decision']
        p, derived = self.snapshot()
        self.assertNotEqual(first, second)
        self.assertEqual(derived['decisions'][first]['answer'], '검사 내용을 쉽게 써 주세요')
        self.assertFalse(any(d['id'] == first for d in decisions.open_decisions(derived)))
        view = server._view(p, derived, store.events(self.run), self.project)
        self.assertTrue(any(r['kind'] == 'superseded' for r in view['timeline']))
        self.assertTrue(any(r.get('answer') == '검사 내용을 쉽게 써 주세요' for r in view['timeline']))
        self.accept(second); self.call('ready')

    def test_replacing_open_plan_closes_old_decision_and_rejects_stale_answer(self):
        first = self.set_plan()['decision']
        self.raw['goal'] = '다른 결과를 만들어요'
        second = self.set_plan()['decision']
        self.assertNotEqual(first, second)
        self.assertEqual(self.call('decide', 'wait', first, '--timeout', '0')['status'], 'superseded')
        with self.assertRaises(core.GFError) as ctx:
            decisions.answer(self.run, first, 'approved', '', 'terminal', {'role': 'human'})
        self.assertEqual(ctx.exception.code, 'stale_decision')

    def test_no_nonhuman_or_forged_answer_can_approve(self):
        did = self.set_plan()['decision']
        for role in ('leader', 'worker', 'reviewer'):
            self.call('--role', role, '--node', 'a', 'decide', 'answer', did, '--outcome', 'approved', code=3)
            with self.assertRaises(core.GFError):
                decisions.answer(self.run, did, 'approved', '', 'terminal', {'role': role})
        self.call('--role', 'human', 'decide', 'answer', did, '--outcome', 'approved', code=3)
        with store.transaction(self.run) as tx:
            tx.append('decision.answer', {'id': did, 'outcome': 'approved', 'answer': '', 'sig': 'forged'}, {'role': 'leader'})
        self.call('ready', code=4)

    def test_send_back_requires_text_on_human_path(self):
        did = self.set_plan()['decision']
        with self.assertRaises(core.GFError) as ctx:
            decisions.answer(self.run, did, 'revision_requested', ' ', 'terminal', {'role': 'human'})
        self.assertEqual(ctx.exception.code, 'answer_required')

    def test_mid_run_new_work_waits_finished_and_running_survive(self):
        did = self.set_plan()['decision']; self.accept(did)
        self.call('start', 'a')
        (self.project / 'guide.txt').write_text('안내 내용\n')
        self.call('submit', 'a'); self.call('gate', 'a')
        revised = copy.deepcopy(self.raw)
        b = copy.deepcopy(revised['nodes'][0]); b.update(id='b', owns=['b.txt'], title='요약 쓰기')
        revised['nodes'].append(b)
        did = self.set_plan(revised)['decision']
        self.assertEqual(self.snapshot()[1]['nodes']['a']['status'], 'passed')
        self.call('start', 'b', code=4); self.accept(did); self.call('start', 'b')
        c = copy.deepcopy(b); c.update(id='c', owns=['c.txt'])
        revised['nodes'].append(c)
        self.set_plan(revised)
        self.assertEqual(self.snapshot()[1]['nodes']['b']['status'], 'running')
        self.call('submit', 'b')
        self.call('start', 'c', code=4)

    def test_active_contract_cannot_be_rewritten(self):
        self.accept(self.set_plan()['decision']); self.call('start', 'a')
        self.raw['nodes'][0]['goal'] = '전혀 다른 일'
        self.file.write_text(json.dumps(self.raw))
        self.assertEqual(self.call('plan', 'set', str(self.file), code=4)['code'], 'active_plan_change')
        self.assertEqual(self.snapshot()[1]['nodes']['a']['status'], 'running')

    def test_legacy_record_requires_one_explicit_plan_approval(self):
        from human_support import legacy_run
        self.run = legacy_run(self.project, "legacy", core.actor_from_env())
        normalized, _ = plan.normalize(self.raw)
        with store.transaction(self.run) as tx:
            rev, sha = tx.write_plan(normalized)
            tx.append('plan.set', {'revision': rev, 'plan_sha256': sha,
                                  'fingerprints': {n['id']: state.fingerprint(n) for n in normalized['nodes']}}, core.actor_from_env())
        self.assertEqual(state.plan_approval(self.snapshot()[1]), {})
        self.call('ready', code=4); self.call('brief', 'a', code=4); self.call('start', 'a', code=4)
        did=self.set_plan()['decision']; self.call('ready', code=4)
        self.accept(did); self.call('start', 'a')
        self.assertEqual(self.snapshot()[1]['nodes']['a']['status'], 'running')

    def test_open_is_one_optional_side_effect_and_never_approval(self):
        with mock.patch.object(server, 'open_dashboard') as opened:
            self.set_plan(None, '--open'); opened.assert_not_called()
            with mock.patch.dict(os.environ, {'GF_NO_OPEN': '0'}):
                result = self.set_plan(None, '--open')
            opened.assert_called_once()
            self.assertEqual(opened.call_args.kwargs['target']['decision'], result['decision'])
        self.call('ready', code=4)

    def test_mcp_parity_and_no_open_or_answer_tool(self):
        def call(name, args):
            result = mcp._call(mcp.TOOLS[name], dict(run=str(self.run), **args))
            return result, json.loads(result['content'][0]['text'])
        result, data = call('plan_set', {'plan': self.raw})
        self.assertIn('graph-flow open', data['message'])
        for name, args in [('ready_nodes', {}), ('node_start', {'node': 'a'}), ('node_brief', {'node': 'a'}),
                           ('assign_node', dict(node='a', executor='inline', model='test', effort='high', provider='test', family='openai', isolation='shared'))]:
            result, error = call(name, args)
            self.assertTrue(result['isError']); self.assertEqual(error['code'], 'plan_not_approved')
        self.assertFalse({'decision_answer', 'open', 'serve'} & mcp.TOOLS.keys())
        self.accept(data['decision']); self.assertFalse(call('ready_nodes', {})[0]['isError'])

    def test_structural_identity_ignores_labels_and_order_not_checks(self):
        extra = copy.deepcopy(self.raw['nodes'][0])
        extra.update(id='b', owns=['b.txt'], needs=[{'from':'a','artifact':'file','label':'안내'}])
        self.raw['nodes'][0]['outputs'] = ['file']
        self.raw['nodes'].append(extra)
        original, _ = plan.normalize(self.raw)
        revised = copy.deepcopy(original)
        revised['nodes'][1]['needs'][0]['label'] = '정리한 안내'
        revised['nodes'].reverse()
        revised['nodes'][0]['context'] = {'why': '설명'}
        self.assertEqual(state.plan_identity(original), state.plan_identity(revised))
        revised['integration_checks'] = [{'id': 'all', 'type': 'cmd', 'run': 'test -s guide.txt'}]
        self.assertNotEqual(state.plan_identity(original), state.plan_identity(revised))
