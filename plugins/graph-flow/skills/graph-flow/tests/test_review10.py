"""Round-ten attacks use the same plan/log rewrites as review10/tools."""
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest
from unittest import mock
import test_plan_approval as fixture
from graphflow import core, decisions, graph, mcp, plan, server, state, store
from human_support import human_answer


class Review10Tests(unittest.TestCase):
    setUp = fixture.PlanApprovalTests.setUp
    call = fixture.PlanApprovalTests.call
    set_plan = fixture.PlanApprovalTests.set_plan
    snapshot = fixture.PlanApprovalTests.snapshot
    accept = fixture.PlanApprovalTests.accept

    def rewrite(self, change):
        events = store.events(self.run)
        change(events)
        (self.run / 'events.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in events))

    def append_plan(self, modified, identity=None, fingerprints=None):
        last = next(e for e in reversed(store.events(self.run)) if e['type'] == 'plan.set')
        revision = last['data']['revision'] + 1
        raw = json.dumps(modified).encode()
        (self.run/'plans'/('%04d.json' % revision)).write_bytes(raw)
        data = dict(last['data'], revision=revision, plan_sha256=hashlib.sha256(raw).hexdigest())
        if identity is not None: data['plan_identity'] = identity
        if fingerprints is not None: data['fingerprints'] = fingerprints
        self.rewrite(lambda es: es.append(dict(last, seq=es[-1]['seq']+1, data=data)))

    def test_f1_duplicate_node_all_loaders_refuse_and_identity_includes_every_node(self):
        self.accept(self.set_plan()['decision'])
        p, d = self.snapshot()
        evil = copy.deepcopy(p['nodes'][0]); evil['goal'] = 'EVIL'; evil['checks'][0]['run'] = 'touch PWNED_DUP'
        p['nodes'].insert(0, evil)
        self.assertNotEqual(state.plan_identity(p), d['run']['plan_identity'])
        self.append_plan(p)
        for args in [('ready',), ('brief','a'), ('start','a'), ('check','run','a','text'), ('gate','a'), ('merge','a')]:
            self.assertEqual(self.call(*args, code=4)['code'], 'plan_tampered')
        result=mcp._call(mcp.TOOLS['node_brief'], {'run':str(self.run),'node':'a'})
        self.assertTrue(result['isError'])
        p, es, d = server._snapshot(self.run)
        self.assertEqual(server._view(p,d,es,self.project)['nodes'], [])
        self.assertFalse((self.project/'PWNED_DUP').exists())

    def test_f1_all_execution_collections_reject_ambiguity_and_unknown_fields(self):
        self.accept(self.set_plan()['decision'])
        original=self.snapshot()[0]
        mutations = [
            lambda p: p['nodes'][0]['checks'].append(dict(p['nodes'][0]['checks'][0],run='false')),
            lambda p: p['nodes'][0].update(needs=[{'from':'missing','artifact':'x'}]),
            lambda p: p['nodes'][0].update(exec='evil'),
            lambda p: p.update(integration_checks=[{'id':'x','type':'cmd','run':'true'}], promoted_checks=[{'id':'x','type':'cmd','run':'false'}]),
            lambda p: p.update(constraints=[{'id':'x','text':'one'},{'id':'x','text':'two'}]),
            lambda p: p['nodes'][0].update(effective_lane=3),
            lambda p: p.update(constraints=[{'id':'x','text':'test','scope':{'paths':['../outside']}}]),
            lambda p: p.update(constraints=[{'id':'x','text':'test','scope':{'exec':'evil'}}]),
            lambda p: p['nodes'][0]['checks'][0].update(shell='evil'),
        ]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                p=copy.deepcopy(original); mutate(p)
                self.append_plan(p, state.plan_identity(p))
                self.assertEqual(self.call('ready',code=4)['code'],'plan_tampered')
        p=copy.deepcopy(original)
        p['nodes'].append({'id':'b','kind':'decision','goal':'decide','lane':1,'question':'Yes?', 'decision_kind':'authorization', 'needs':[{'from':'a','artifact':'guide.txt'}]*2})
        self.assertTrue(any('duplicate need' in x['message'] for x in plan.validate(p)))

    def test_f2_copied_entire_run_and_genuine_repin_cannot_replay(self):
        self.accept(self.set_plan()['decision'])
        for repinned in (False, True):
            if repinned:
                decisions.repin(self.run, {'role':'human'})
                self.accept(state.plan_approval(self.snapshot()[1])['id'])
            source = self.run
            for project_name, run_name in [('other', 'approval'), ('other', 'renamed')]:
                target=self.root/(project_name+str(repinned))/'.graph-flow/runs'/run_name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(source,target)
                subprocess.run(["git","init","-q",str(target.parent.parent.parent)], check=True)
                subprocess.run(["git","-C",str(target.parent.parent.parent),"-c","user.name=T","-c","user.email=t@t","commit","--allow-empty","-qm","init"],check=True)
                self.run=target
                for args in [('ready',), ('start','a')]:
                    error=self.call(*args,code=4)
                    self.assertEqual(error['code'],'project_moved')
                    self.assertIn('approve once more',error['message'])
                self.assertFalse(any(d['verified'] for d in self.snapshot()[1]['decisions'].values()))
                p, es, d = server._snapshot(self.run)
                self.assertEqual(graph.available(p, d), [])
                self.assertTrue(server._view(p, d, es, target.parent.parent.parent)['location_mismatch'])
                self.run=source

    def prepare_submission(self, purpose):
        self.raw['nodes'][0]['checks']=[{'id':'text','type':'cmd','run':'true'}]
        self.accept(self.set_plan()['decision'])
        self.call('assign','a','--executor','inline','--model','m','--effort','high','--provider','p','--family','claude','--isolation','worktree')
        self.call('start','a')
        commit=subprocess.check_output(['git','-C',str(self.project),'rev-parse','HEAD'],text=True).strip()
        self.call('submit','a','--commit',commit)
        (self.project/'evidence.txt').write_text('reviewed evidence')
        ask=decisions.ask(self.run,'authorization' if purpose=='lane3' else 'review','Approve?', 'a', None,purpose,{'files':['evidence.txt'],'checks':{}}, {'role':'leader'})
        self.accept(ask['id'])
        return commit

    def test_f3_commit_rewrite_blocks_human_lane3_hold_gate_and_merge(self):
        for purpose in ('human_check','lane3','hold'):
            with self.subTest(purpose=purpose):
                if purpose!='human_check':
                    self.run=store.init_run(self.project,purpose,{'role':'leader'})
                self.prepare_submission(purpose)
                subprocess.run(['git','-C',str(self.project),'-c','user.name=Test','-c','user.email=t@t','commit','--allow-empty','-qm','evil'],check=True)
                evil=subprocess.check_output(['git','-C',str(self.project),'rev-parse','HEAD'],text=True).strip()
                self.rewrite(lambda es: next(e['data'] for e in es if e['type']=='node.submit').update(commit=evil))
                for args in [('gate','a'), ('merge','a')]:
                    self.assertEqual(self.call(*args,code=4)['code'],'approval_changed')

    def test_f3_evidence_rewrite_blocks_gate_and_merge(self):
        self.prepare_submission('human_check')
        (self.project/'evidence.txt').write_text('changed after approval')
        for args in [('gate','a'), ('merge','a')]:
            self.assertEqual(self.call(*args,code=4)['code'],'approval_changed')

    def test_f4_repin_does_not_reuse_or_block_on_superseded_submission_consent(self):
        self.prepare_submission('human_check')
        decisions.repin(self.run, {'role':'human'})
        self.accept(state.plan_approval(self.snapshot()[1])['id'])
        p, d = self.snapshot()
        old = [x for x in d['decisions'].values() if x['purpose']=='human_check'][0]
        self.assertTrue(old['stale'])
        self.assertFalse(old['verified'])
        state.require_submission_binding(d, 'a')

    def test_f4_repin_replaces_planted_key_and_forged_answer_fails(self):
        self.accept(self.set_plan()['decision'])
        planted=b'attacker-chosen-key-never-read'
        (core.gf_home()/'human.key').write_bytes(planted)
        self.assertEqual(self.call('ready',code=4)['code'],'human_key_mismatch')
        decisions.repin(self.run,{'role':'human'})
        self.assertNotEqual((core.gf_home()/'human.key').read_bytes(),planted)
        self.raw['goal']='evil new contract'; did=self.set_plan()['decision']
        private=self.root/'attacker'; private.mkdir(); (private/'human.key').write_bytes(planted)
        with mock.patch.dict(os.environ, GF_HOME=str(private)):
            d=self.snapshot()[1];dec=d['decisions'][did]
            sig=core.human_sig(d['run']['id'],did,'approved','',dec)
        with store.transaction(self.run) as tx:
            tx.append('decision.answer',{'id':did,'outcome':'approved','answer':'','sig':sig},{'role':'human'})
        self.assertEqual(self.call('ready',code=4)['code'],'plan_not_approved')

    def test_f4_agent_setup_never_creates_key_and_repin_error_names_command(self):
        from graphflow import launcher
        for role in ('leader','worker','reviewer'):
            with self.subTest(role=role):
                with self.assertRaises(core.GFError): decisions.ensure_key({'role':role})
        with mock.patch.object(launcher,'install',return_value={'installed':True}):
            self.call('setup','--bin-dir',str(self.root/'bin'))
        self.assertFalse((core.gf_home()/'human.key').exists())
        error=self.call('--role','human','key','repin',code=3)
        self.assertIn('key repin requires GF_HUMAN_TERMINAL=1',error['message'])

    def test_f5_forged_plan_fingerprints_cannot_keep_passed_node(self):
        self.raw['nodes'][0]['checks'][0]['run']='true'
        self.accept(self.set_plan()['decision']);self.call('start','a');self.call('submit','a');self.call('gate','a')
        p,d=self.snapshot();self.assertEqual(d['nodes']['a']['status'],'passed')
        old={n['id']:state.fingerprint(n) for n in p['nodes']}
        p['nodes'][0]['checks'][0]['run']='false'
        self.append_plan(p,state.plan_identity(p),old)
        self.assertEqual(self.snapshot()[1]['nodes']['a']['status'],'pending')
        with store.transaction(self.run) as tx:
            ask={'purpose':'plan_approval','kind':'authorization','question':'Approve changed check?', 'plan_identity':state.plan_identity(p)}
            ev=tx.append('decision.ask',ask,{'role':'leader'})
        self.accept('d%d'%ev['seq'])
        self.assertEqual(self.snapshot()[1]['nodes']['a']['status'],'pending')

    def test_f5_deleted_supersession_cannot_revive_earlier_approval(self):
        self.accept(self.set_plan()['decision'])
        self.raw['goal']='different';self.set_plan()
        self.raw['goal']='안내 파일을 만들어요';did=self.set_plan()['decision']
        human_answer(self.run,did,'revision_requested','검사를 고쳐 주세요')
        self.rewrite(lambda es: es.__setitem__(slice(None),[e for e in es if e['type']!='decision.superseded']))
        for args in [('ready',), ('start','a')]:
            error=self.call(*args,code=4)
            self.assertIn('sent the plan back',error['message']);self.assertIn('검사를 고쳐 주세요',error['message'])
            self.assertIn('plan set',error['message']);self.assertNotIn('gf open',error['message'])

    def test_f5_later_same_identity_revision_invalidates_approval_without_flag(self):
        self.accept(self.set_plan()['decision'])
        p, d = self.snapshot()
        self.append_plan(p, d['run']['plan_identity'])
        self.assertEqual(self.call('ready',code=4)['code'], 'plan_not_approved')

    def test_small_docs_cover_upgrade_location_key_writes_and_clipping(self):
        root = Path(__file__).resolve().parents[1]
        for name in ('SKILL.md', 'references/leader.md', 'references/worker.md',
                     'references/records.md', 'references/dashboard.md'):
            text = (root / name).read_text().lower()
            self.assertRegex(text, r'read.{0,20}write.{0,30}human.key')
        for name in ('leader', 'mcp'):
            text = (root / ('references/%s.md' % name)).read_text()
            self.assertNotIn('continue without approval', text)
            self.assertNotIn('remain unblocked until', text)
            self.assertIn('plans/NNNN.json', text)
        records = (root / 'references/records.md').read_text()
        self.assertIn('Moving or renaming a project directory invalidates approvals', records)
        self.assertIn('Log truncation', records)
        self.assertIn('Shared-tree mode cannot bind file contents beyond the recorded evidence hashes', records)
        dashboard = (root / 'references/dashboard.md').read_text()
        self.assertNotIn('remain hidden until fully visible', dashboard)
        self.assertIn('Phone cards clip naturally', dashboard)
