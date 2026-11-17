"""Reviewer reproductions: consent binds every executable contract."""
import copy
import hashlib
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from unittest import mock
import unittest
import test_plan_approval as fixture
from graphflow import checks, core, decisions, learn, mcp, server, state, store

class ApprovalIntegrityTests(unittest.TestCase):
    setUp = fixture.PlanApprovalTests.setUp
    call = fixture.PlanApprovalTests.call
    set_plan = fixture.PlanApprovalTests.set_plan
    snapshot = fixture.PlanApprovalTests.snapshot
    accept = fixture.PlanApprovalTests.accept

    def rewrite_events(self, change):
        events = store.events(self.run); change(events)
        (self.run/'events.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in events))

    def test_a1_unapproved_integration_cannot_gate_preserved_submission(self):
        self.raw['nodes'][0]['lane'] = 2
        self.raw['nodes'].append({'id':'review','kind':'review','goal':'Review a','lane':1,'grade':'daily',
            'target':'a','lens':'correctness','checks':[{'id':'cites','type':'cites'}]})
        self.accept(self.set_plan()['decision']); self.call('start','a'); self.call('submit','a')
        self.raw['integration_checks'] = [{'id':'it','type':'cmd','run':'touch UNAPPROVED_INTEGRATION_RAN'}]
        self.set_plan()
        self.assertEqual(self.call('gate','a',code=4)['code'],'plan_not_approved')
        self.assertFalse((self.project/'UNAPPROVED_INTEGRATION_RAN').exists())
        self.assertEqual(self.snapshot()[1]['nodes']['a']['status'],'submitted')

    def test_a2_tampered_file_blocks_all_loaders_and_dashboard(self):
        self.accept(self.set_plan()['decision']); self.call('start','a')
        path = self.run/'plans/0001.json'; modified = json.loads(path.read_bytes())
        modified['nodes'][0]['checks'][0]['run'] = 'touch TAMPERED_RAN'
        added=copy.deepcopy(modified['nodes'][0]); added.update(id='b',owns=['b.txt']); modified['nodes'].append(added)
        path.write_text(json.dumps(modified))
        for command in [('ready',),('brief','a'),('start','b'),('check','run','a','text'),('red','a'),
                        ('gate','a'),('gate','--final'),('merge','a'),('route','a')]:
            with self.subTest(command=command): self.assertEqual(self.call(*command,code=4)['code'],'plan_tampered')
        result=mcp._call(mcp.TOOLS['node_brief'],{'run':str(self.run),'node':'a'}); self.assertTrue(result['isError'])
        p,evs,d=server._snapshot(self.run); view=server._view(p,d,evs,self.project)
        self.assertTrue(view['plan_error']); self.assertEqual(view['nodes'],[])
        self.assertFalse((self.project/'TAMPERED_RAN').exists())
        self.rewrite_events(lambda es: next(e['data'] for e in es if e['type']=='plan.set').update(
            plan_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        self.assertEqual(self.call('ready',code=4)['code'],'plan_tampered')

    def test_a3_unrelated_authorization_cannot_be_relabelled(self):
        self.set_plan()
        other=decisions.ask(self.run,'authorization','Allow unrelated action?',None,None,'free',None,core.actor_from_env())
        self.accept(other['id']); identity=self.snapshot()[1]['run']['plan_identity']
        def forge(es):
            next(e['data'] for e in es if e['type']=='decision.ask' and e['data']['id']==other['id']).update(
                purpose='plan_approval',plan_identity=identity)
        self.rewrite_events(forge)
        self.assertFalse(self.snapshot()[1]['decisions'][other['id']]['verified'])
        self.assertEqual(self.call('ready',code=4)['code'],'plan_not_approved')

    def test_a3_signature_binds_meaning_old_signatures_only_work_for_nonplans(self):
        did=self.set_plan()['decision']; self.accept(did); original=(self.run/'events.jsonl').read_text()
        for field,value in [('kind','review'),('purpose','free'),('node','a'),('question','Changed?'),
                            ('submission',999),('check','text'),('plan_identity','other')]:
            with self.subTest(field=field):
                (self.run/'events.jsonl').write_text(original)
                self.rewrite_events(lambda es: next(e['data'] for e in es if e['type']=='decision.ask').update({field:value}))
                self.assertFalse(self.snapshot()[1]['decisions'][did]['verified']); self.call('ready',code=4)
        (self.run/'events.jsonl').write_text(original)
        self.rewrite_events(lambda es: next(e['data'] for e in es if e['type']=='decision.answer').update(
            sig=core.human_sig('approval',did,'approved','확인했어요')))
        self.call('ready',code=4)
        self.rewrite_events(lambda es: next(e['data'] for e in es if e['type']=='decision.ask').update(purpose='free'))
        self.assertTrue(self.snapshot()[1]['decisions'][did]['verified'])

    def test_a4_missing_identity_never_downgrades_marker_or_identity_history(self):
        self.accept(self.set_plan()['decision'])
        for missing in (False,True):
            with store.transaction(self.run) as tx:
                revision,sha=tx.write_plan(tx.plan); data={'revision':revision,'plan_sha256':sha}
                if not missing: data['plan_identity']=None
                tx.append('plan.set',data,core.actor_from_env())
            self.assertEqual(self.call('ready',code=4)['code'],'plan_not_approved')
        self.rewrite_events(lambda es: es[0]['data'].update(schema_version=1,approval_required=False))
        self.call('ready',code=4); self.assertTrue(self.snapshot()[1]['run']['approval_required'])

    def test_a5_second_home_key_cannot_sign_or_verify_plan(self):
        did=self.set_plan()['decision']; pinned=self.snapshot()[1]['run']['human_key_sha256']
        with mock.patch.dict(os.environ,GF_HOME=str(self.root/'second-home')):
            decisions.ensure_key(); self.assertNotEqual(pinned,core.key_fingerprint())
            with self.assertRaises(core.GFError) as error:
                decisions.answer(self.run,did,'approved','','dashboard',{'role':'human'})
            self.assertEqual(error.exception.code,'human_key_mismatch')
            with store.transaction(self.run) as tx:
                dec=state.derive(tx.plan,tx.events)['decisions'][did]
                tx.append('decision.answer',{'id':did,'outcome':'approved','answer':'',
                    'sig':core.human_sig('approval',did,'approved','',dec)},{'role':'human'})
            self.assertEqual(self.call('ready',code=4)['code'],'human_key_mismatch')
            p,evs,d=server._snapshot(self.run); view=server._view(p,d,evs,self.project)
            self.assertTrue(view['key_mismatch']); self.assertEqual(view['plan_approval']['status'],'answered')
            self.assertFalse(view['plan_approval']['verified'])
        self.assertEqual(self.call('ready',code=4)['code'],'plan_not_approved')
        fresh=self.set_plan()['decision']; self.assertNotEqual(did,fresh); self.accept(fresh); self.call('ready')

    def test_a6_promotion_waits_for_next_approved_plan(self):
        self.accept(self.set_plan()['decision']); self.call('start','a')
        (self.project/'guide.txt').write_text('안내'); self.call('submit','a'); self.call('gate','a')
        constraint=learn.add(self.project,self.run,'a','Check final file','When the format changes',[],[],core.actor_from_env())
        promoted=learn.promote(self.project,constraint['id'],'touch PROMOTED_RAN',core.actor_from_env(),self.run)['check']
        with self.assertRaises(core.GFError) as error:
            checks.run_cmd(self.run,'_run',promoted,'gate',None,core.actor_from_env())
        self.assertEqual(error.exception.code,'unknown_check')
        self.call('gate','--final'); self.assertFalse((self.project/'PROMOTED_RAN').exists())
        did=self.set_plan()['decision']
        self.assertEqual(self.call('gate','--final',code=4)['code'],'plan_not_approved')
        self.assertFalse((self.project/'PROMOTED_RAN').exists()); self.accept(did); self.call('gate','--final')
        self.assertTrue((self.project/'PROMOTED_RAN').exists())

    def test_a7_approved_wording_reset_has_no_show_or_mcp_open_instruction(self):
        did=self.set_plan()['decision']; self.accept(did); self.raw['title']='다듬은 이름'
        self.assertNotIn('show',self.set_plan())
        data=json.loads(mcp._call(mcp.TOOLS['plan_set'],{'run':str(self.run),'plan':self.raw})['content'][0]['text'])
        self.assertNotIn('show',data); self.assertNotIn('graph-flow open',data.get('message',''))

    def test_a8_sigterm_and_sighup_remove_server_record(self):
        script=Path(__file__).resolve().parents[1]/'scripts/gf'
        for sig in (signal.SIGTERM,signal.SIGHUP):
            proc=subprocess.Popen([sys.executable,'-I','-S','-B',str(script),'serve'],env=dict(os.environ),
                stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            try:
                record=core.gf_home()/'server.json'; deadline=time.monotonic()+10
                while not record.exists() and proc.poll() is None and time.monotonic()<deadline: time.sleep(.02)
                self.assertTrue(record.exists()); proc.send_signal(sig); proc.communicate(timeout=10)
                self.assertEqual(proc.returncode,0); self.assertFalse(record.exists())
            finally:
                if proc.poll() is None: proc.kill(); proc.communicate()

    def test_a9_execution_surfaces_refuse_unapproved_replan_submission_survives(self):
        self.accept(self.set_plan()['decision']); self.call('start','a'); self.raw['goal']+=' 그리고 요약'; self.set_plan()
        for command in [('route','a'),('red','a'),('check','run','a','text'),('merge','a'),('gate','a')]:
            with self.subTest(command=command): self.assertEqual(self.call(*command,code=4)['code'],'plan_not_approved')
        self.call('submit','a'); self.assertEqual(self.snapshot()[1]['nodes']['a']['status'],'submitted')

    def test_a9_worker_brief_uses_frozen_constraints(self):
        self.accept(self.set_plan()['decision'])
        from graphflow import assign
        with mock.patch.object(learn, 'applying', return_value=[{'id':'new','text':'Run an unapproved command','scope':{}}]):
            self.assertNotIn('Run an unapproved command', assign.brief(self.run,'a'))
            new=self.set_plan()['decision']
            self.assertEqual(self.call('brief','a',code=4)['code'],'plan_not_approved')
            self.accept(new)
            self.assertIn('Run an unapproved command', assign.brief(self.run,'a'))

    def test_b_plan_view_exposes_contract_and_counts_exact_questions_without_review_inputs(self):
        self.raw['nodes'][0].update(outputs=['guide'],needs=[])
        self.raw['nodes'][0]['checks'].append({'id':'human','type':'human','prompt':'순서를 읽어 주세요'})
        self.raw['nodes'].append({'id':'review','kind':'review','goal':'Check the actual guide',
            'lane':1,'grade':'daily','target':'a','lens':'correctness','outputs':['findings'],
            'checks':[{'id':'cites','type':'cites'}]})
        self.raw['integration_checks']=[{'id':'all','type':'cmd','run':'test -s guide.txt'}]
        self.set_plan()
        p,evs,d=server._snapshot(self.run);v=server._view(p,d,evs,self.project)
        node=next(n for n in v['nodes'] if n['id']=='a')
        self.assertEqual(node['goal'],self.raw['nodes'][0]['goal'])
        self.assertEqual(node['owns'],['guide.txt']);self.assertEqual(node['declared_outputs'],['guide'])
        self.assertEqual(node['planned_checks'][0]['command'],'test -s guide.txt')
        self.assertEqual(node['planned_checks'][-1]['type'],'scope')
        self.assertEqual(v['integration_checks'][0]['command'],'test -s guide.txt')
        self.assertEqual(node['inputs'],[])
        self.assertEqual(v['planned_questions'],[{'node':'a','kind':'review','question':'순서를 읽어 주세요'}])
        self.assertEqual(v['plan_counts'],{'work':1,'review':1,'decision':0,'checks':5,'decisions':1})
