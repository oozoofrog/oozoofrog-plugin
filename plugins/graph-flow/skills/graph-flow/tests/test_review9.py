"""Round-nine reproductions: unsigned history cannot authorize execution."""
import copy
import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
import unittest
import test_plan_approval as fixture
from graphflow import cli, core, decisions, server, state, store
from human_support import human_answer, legacy_run

class Review9Tests(unittest.TestCase):
    setUp = fixture.PlanApprovalTests.setUp
    call = fixture.PlanApprovalTests.call
    set_plan = fixture.PlanApprovalTests.set_plan
    snapshot = fixture.PlanApprovalTests.snapshot
    accept = fixture.PlanApprovalTests.accept

    def rewrite(self, change):
        events = store.events(self.run)
        change(events)
        (self.run / 'events.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in events))

    def view(self):
        p, es, d = server._snapshot(self.run)
        return server._view(p, d, es, self.project)

    def test_n1_two_edits_never_exempt_execution(self):
        self.raw['nodes'][0]['checks'][0]['run'] = 'touch UNAPPROVED_RAN'
        self.set_plan()
        def tamper(es):
            es[0]['data']['schema_version'] = 1
            es[0]['data'].pop('approval_required', None)
            for e in es:
                if e['type'] == 'plan.set': e['data'].pop('plan_identity', None)
        self.rewrite(tamper)
        for args in [('ready',), ('start','a'), ('brief','a'), ('check','run','a','text'), ('gate','--final')]:
            self.assertEqual(self.call(*args, code=4)['code'], 'plan_not_approved')
        self.assertFalse((self.project/'UNAPPROVED_RAN').exists())
        self.assertEqual(self.view()['plan_approval']['id'], None)
        self.call('status'); self.call('trace')

    def test_n1_old_run_waits_then_one_approval_preserves_submission(self):
        self.run = legacy_run(self.project, 'old', core.actor_from_env())
        from graphflow import plan
        p, _ = plan.normalize(self.raw)
        with store.transaction(self.run) as tx:
            rev, sha = tx.write_plan(p)
            tx.append('plan.set', {'revision':rev,'plan_sha256':sha,'fingerprints':{n['id']:state.fingerprint(n) for n in p['nodes']}}, {})
            tx.append('node.start', {'node':'a','attempt':1,'base':{}}, {})
            tx.append('node.submit', {'node':'a','attempt':1,'changed_files':[]}, {})
        for args in [('ready',), ('gate','a')]: self.call(*args, code=4)
        self.assertTrue(self.view()['legacy'])
        did = self.set_plan()['decision']
        self.assertEqual(self.snapshot()[1]['nodes']['a']['status'], 'submitted')
        self.accept(did)
        self.call('ready')
        self.assertEqual(self.snapshot()[1]['nodes']['a']['status'], 'submitted')
        self.assertTrue(self.snapshot()[1]['run']['run_nonce'])

    def test_n2_old_answer_append_is_history_not_gate_consent(self):
        self.raw['nodes'][0]['checks'] = [{'id':'ok','type':'cmd','run':'true'},{'id':'h','type':'human','prompt':'배포할까요?'}]
        self.accept(self.set_plan()['decision']); self.call('start','a'); self.call('submit','a')
        did = self.call('gate','a',code=1)['asks'][0]
        # A genuine 0.2 signature binds only these four fields, regardless of project/question.
        sig = core.human_sig('approval',did,'approved','')
        with store.transaction(self.run) as tx:
            tx.append('decision.answer',{'id':did,'outcome':'approved','answer':'','sig':sig,'source':'terminal'},{'role':'human'})
        self.assertFalse(self.snapshot()[1]['decisions'][did]['verified'])
        self.assertEqual(self.call('gate','a',code=4)['code'],'approval_changed')
        self.assertFalse(decisions.verify('approval',did,{'sig':sig,'outcome':'approved','answer':''},self.snapshot()[1]['decisions'][did]))

    def test_n3_same_id_and_plan_other_project_cannot_replay(self):
        did=self.set_plan()['decision']; self.accept(did)
        answer=next(e['data'] for e in store.events(self.run) if e['type']=='decision.answer')
        first_nonce=self.snapshot()[1]['run']['run_nonce']
        project=self.root/'other';project.mkdir()
        self.run=store.init_run(project,'approval',core.actor_from_env())
        self.assertEqual(self.set_plan()['decision'],did)
        with store.transaction(self.run) as tx:
            tx.append('human.key',{'human_key_sha256':core.key_fingerprint()},{'role':'human'})
            tx.append('decision.answer',answer,{'role':'human'})
        self.assertNotEqual(first_nonce,self.snapshot()[1]['run']['run_nonce'])
        self.call('ready',code=4)

    def test_n4_agent_init_has_no_key_first_human_pins_and_rotation_recovers(self):
        self.assertFalse((core.gf_home()/'human.key').exists())
        did=self.set_plan()['decision']
        self.assertIsNone(self.snapshot()[1]['run']['human_key_sha256'])
        self.accept(did)
        (core.gf_home()/'human.key').unlink()
        error=self.call('ready',code=4)
        self.assertEqual(error['code'],'human_key_mismatch');self.assertIn('key repin',error['message'])
        for args in [('key','repin'),('--role','human','key','repin')]: self.call(*args,code=3)
        with mock.patch.dict(os.environ,GF_HUMAN_TERMINAL='1'), mock.patch('sys.stdin.isatty',return_value=True):
            self.call('--role','human','key','repin')
        self.call('ready',code=4)
        d=state.plan_approval(self.snapshot()[1]);self.assertNotEqual(d['id'],did)
        self.accept(d['id']);self.call('ready')

    def test_n5_missing_or_tampered_revision_can_be_replaced(self):
        for remove in (False,True):
            did=self.set_plan()['decision']
            if self.snapshot()[1]['decisions'][did]['status']=='open': self.accept(did)
            self.call('start','a')
            path=self.run/'plans'/('%04d.json'%self.snapshot()[1]['run']['plan_revision'])
            if remove: path.unlink()
            else: path.write_text('{}')
            self.call('ready',code=4)
            replacement=self.set_plan()['decision']
            self.assertEqual(self.snapshot()[1]['nodes']['a']['status'],'pending')
            self.assertTrue(self.view()['replaced_unverifiable'])
            self.call('ready',code=4);self.accept(replacement);self.call('ready')

    def test_n6_unverified_answer_timeline_never_claims_consent(self):
        did=self.set_plan()['decision']
        with store.transaction(self.run) as tx:
            tx.append('decision.answer',{'id':did,'outcome':'approved','answer':'ok','sig':'forged'},{'role':'human'})
        row=next(r for r in self.view()['timeline'] if r['kind']=='answered')
        self.assertFalse(row['verified'])
        self.accept(self.set_plan()['decision'])
        rows=[r for r in self.view()['timeline'] if r['kind']=='answered']
        self.assertEqual([r['verified'] for r in rows],[False,True])

    def test_n7_key_mismatch_unanswered_approval_is_not_actionable(self):
        self.accept(self.set_plan()['decision'])
        self.raw['goal']+=' 요약도 써요';self.set_plan()
        (core.gf_home()/'human.key').write_bytes(b'rotated')
        v=self.view();self.assertTrue(v['key_mismatch']);self.assertEqual(v['decisions'],[])
        self.assertIn('key repin',v['key_recovery']);self.assertEqual(v['plan_approval']['status'],'open')

    def test_n6_genuine_sent_back_answer_stays_verified_when_superseded(self):
        did=self.set_plan()['decision']
        human_answer(self.run,did,'revision_requested','설치 순서를 넣어 주세요.')
        self.raw['goal']+=' 설치 순서';self.set_plan()
        old=self.snapshot()[1]['decisions'][did]
        self.assertTrue(old['stale']);self.assertTrue(old['verified'])
        self.assertEqual(old['status'],'superseded')
        row=next(r for r in self.view()['timeline'] if r['kind']=='answered')
        self.assertTrue(row['verified']);self.assertEqual(row['outcome'],'revision_requested')
        self.call('ready',code=4)

    def test_n8_no_plan_says_set_plan(self):
        error=self.call('ready',code=4)
        self.assertIn('plan set',error['message']);self.assertNotIn('--decision missing',error['message'])

    def test_n9_no_open_suppresses_browser_at_shared_entrypoint(self):
        # Do not execute gf open: test the common browser boundary, with both side effects trapped.
        with mock.patch.object(server,'_launch') as launch, mock.patch.object(server.webbrowser,'open') as browse:
            self.assertEqual(server.open_dashboard()['suppressed'],True)
            launch.assert_not_called();browse.assert_not_called()
        with mock.patch.object(server,'open_dashboard',return_value={'suppressed':True}) as opened:
            result=cli._open(SimpleNamespace(stop=False,run=None,decision=None,target_node=None),{})
            self.assertIn('suppressed',result['message'])

    def test_n10_review_lens_display_and_identity(self):
        self.raw['nodes'].append({'id':'review','kind':'review','goal':'안내를 검토해요','target':'a','lens':'빠진 설치 순서를 찾아요','grade':'daily','lane':1,'checks':[{'id':'cites','type':'cites'}]})
        self.set_plan();original=self.snapshot()[1]['run']['plan_identity']
        self.assertEqual(self.view()['nodes'][1]['lens'],'빠진 설치 순서를 찾아요')
        self.raw['nodes'][1]['lens']='다른 기준';self.set_plan()
        self.assertNotEqual(original,self.snapshot()[1]['run']['plan_identity'])

    def test_n11_skill_forbids_log_edits_and_states_same_account_limit(self):
        text=(Path(__file__).resolve().parents[1]/'SKILL.md').read_text()
        self.assertIn('.graph-flow/runs/**',text);self.assertIn('same OS account',text)
