"""Round-eleven regressions: shown consent must equal enforced/executed input."""
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from unittest import mock

import test_plan_approval as fixture
from graphflow import cli, core, decisions, gate, plan, server, state, store
from human_support import human_answer

NODE = shutil.which('node')
LEADER = {'role': 'leader', 'node': None, 'session': 'regression'}
HUMAN = {'role': 'human', 'node': None, 'session': 'regression'}


class Review11Tests(unittest.TestCase):
    setUp = fixture.PlanApprovalTests.setUp
    call = fixture.PlanApprovalTests.call
    set_plan = fixture.PlanApprovalTests.set_plan
    snapshot = fixture.PlanApprovalTests.snapshot
    accept = fixture.PlanApprovalTests.accept

    def submit(self):
        self.accept(self.set_plan()['decision'])
        self.call('start', 'a')
        (self.project/'guide.txt').write_text('approved content\n')
        self.call('check', 'run', 'a', 'text')
        self.call('submit', 'a')

    def human_check(self):
        self.raw['nodes'][0]['checks'].append({'id':'look','type':'human',
            'prompt':'Approve deleting the production database?',
            'context':{'why':'This deletes production data.', 'undo':'No undo.'}})
        self.submit()
        return self.call('gate','a',code=1)['asks'][0]

    def rewrite(self, change):
        es=store.events(self.run);change(es)
        (self.run/'events.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in es))

    def test_a1_b12_gate_owned_questions_and_exact_signed_context(self):
        self.raw['nodes'].append({'id':'q','kind':'decision','goal':'Choose deletion',
            'lane':1,'question':'Approve deleting the production database?',
            'decision_kind':'authorization','context':{'why':'Irreversible'}})
        did=self.human_check()
        for role in ('leader','worker','reviewer','human'):
            for purpose in ('node','human_check','lane3','trajectory'):
                with self.subTest(role=role,purpose=purpose):
                    error=self.call('--role',role,'--node','a','decide','ask','--kind','review',
                        '--question','Is the typo fix in a.txt fine?','--check','look','--purpose',purpose,code=2)
                    self.assertEqual(error['code'],'bad_purpose')
        # Even a signed question injected into the log cannot stand in for the plan question.
        self.rewrite(lambda es: next(e['data'] for e in es if e['type']=='decision.ask' and e['data'].get('id')==did).update(question='Is the typo fine?'))
        self.accept(did)
        fresh=self.call('gate','a',code=1)['asks'][0]
        d=self.snapshot()[1]['decisions'][fresh]
        self.assertEqual(d['question'],'Approve deleting the production database?')
        self.assertEqual(d['evidence']['context']['undo'],'No undo.')
        self.accept(fresh);self.call('gate','a')
        q=self.call('gate','q',code=1)['asks'][0]
        self.rewrite(lambda es: next(e['data'] for e in es if e['type']=='decision.ask' and e['data'].get('id')==q)['evidence'].update(context={'why':'A harmless log line'}))
        self.accept(q)
        self.assertTrue(self.call('gate','q',code=1)['asks'])

    def test_a2_all_executor_inputs_reach_view_and_brief(self):
        c=self.raw['nodes'][0]['checks'][0]
        c.update(run='make test',cwd='evil',timeout_s=17)
        self.raw['integration_checks']=[dict(c,id='whole')]
        self.accept(self.set_plan()['decision'])
        p,d=self.snapshot();view=server._view(p,d,store.events(self.run),self.project)
        expected=plan.check_inputs(c)
        for shown in (view['nodes'][0]['planned_checks'][0],view['integration_checks'][0]):
            self.assertEqual({k:shown[k] for k in expected},expected)
        brief=self.call('brief','a')['brief']
        for k,v in expected.items(): self.assertIn(json.dumps(k)+': '+json.dumps(v),brief)
        self.assertEqual(view['nodes'][0]['contract'],plan.node_contract(p['nodes'][0]))
        # Execute the actual UI projection, enumerating every input the executor consumes.
        js=(Path(__file__).resolve().parents[1]/'scripts/graphflow/page.js').read_text()
        shown=dict(c,command=c['run'],**{k:v for k,v in expected.items() if k not in c})
        script=("const m=await import('data:text/javascript;base64,'+Buffer.from("+json.dumps(js)+
                ").toString('base64'));const rows=[];m.renderCheckInputs({append:r=>rows.push(r)},"+
                json.dumps(shown)+",'en',(tag,text)=>({tag,text,dataset:{},append:r=>rows.push(r)}));"+
                "console.log(JSON.stringify(Object.fromEntries(rows.filter(r=>r.dataset.input).map(r=>[r.dataset.input,r.text]))));")
        self.assertIn('renderCheckInputs(item,c,language,el)',js)
        result=subprocess.check_output([NODE,'--input-type=module'],input=script,text=True)
        rendered=json.loads(result)
        self.assertEqual(set(rendered),set(expected))
        for k in ('run','cwd','timeout_s','shell'):self.assertIn(str(expected[k]),str(rendered[k]))
        self.assertIn('inherited',rendered['environment'])

    def test_a3_d5_worktree_cannot_complete_unmerged_and_committed_bytes_are_shown(self):
        self.raw['nodes'][0]['checks'].append({'id':'look','type':'human','prompt':'Read the committed guide'})
        (self.project/'guide.txt').write_text('old content a\n')
        self.git('add','guide.txt');self.git('commit','-qm','old')
        self.accept(self.set_plan()['decision'])
        wt=self.root/'worker';self.git('worktree','add','-qb','worker',str(wt))
        self.call('start','a','--cwd',str(wt));(wt/'guide.txt').write_text('work that must land\n')
        self.git('add','guide.txt',cwd=wt);self.git('commit','-qm','new',cwd=wt)
        commit=self.git('rev-parse','HEAD',cwd=wt)
        self.call('check','run','a','text','--cwd',str(wt));self.call('submit','a','--cwd',str(wt),'--commit',commit)
        self.assertEqual(self.call('gate','a','--cwd',str(wt),code=4)['code'],'not_merged')
        self.assertEqual(self.call('gate','--final','--cwd',str(wt),code=4)['code'],'not_merged')
        self.call('merge','a');did=self.call('gate','a',code=1)['asks'][0]
        (self.project/'guide.txt').write_text('uncommitted distracting bytes\n')
        self.assertEqual(server._file(self.run,did,'guide.txt'),b'work that must land\n')
        d=self.snapshot()[1]['decisions'][did]
        self.assertEqual(d['artifact_hashes']['file:guide.txt'],hashlib.sha256(b'work that must land\n').hexdigest())
        self.accept(did);self.call('gate','a');self.call('gate','--final')
        self.assertEqual(self.snapshot()[1]['run']['status'],'complete')
        self.assertTrue(self.snapshot()[1]['nodes']['a']['merged_head'])

    def git(self,*args,cwd=None):
        return subprocess.check_output(['git','-C',str(cwd or self.project),'-c','user.name=Test','-c','user.email=t@t']+list(args),stderr=subprocess.PIPE,text=True).strip()

    def test_a4_stale_displayed_identity_cannot_answer_replaced_plan_or_same_id(self):
        first=self.set_plan()['decision'];displayed=state.decision_identity(self.snapshot()[1]['decisions'][first])
        self.raw['nodes'][0]['goal']='A different operation'
        second=self.set_plan()['decision']
        for did in (first,second):
            with self.assertRaises(core.GFError) as caught:
                decisions.answer(self.run,did,'approved','','dashboard',HUMAN,displayed)
            self.assertEqual(caught.exception.code,'stale_decision')
        current=state.decision_identity(self.snapshot()[1]['decisions'][second])
        self.rewrite(lambda es: next(e['data'] for e in es if e['type']=='decision.ask' and e['data'].get('id')==second).update(question='Changed question'))
        with self.assertRaises(core.GFError) as caught:decisions.answer(self.run,second,'approved','','dashboard',HUMAN,current)
        self.assertEqual(caught.exception.code,'stale_decision')

    def test_a5_eT_file_changed_after_asking_cannot_be_read_or_accepted(self):
        did=self.human_check();displayed=state.decision_identity(self.snapshot()[1]['decisions'][did])
        self.assertEqual(server._file(self.run,did,'guide.txt'),b'approved content\n')
        (self.project/'guide.txt').write_text('different bytes\n')
        with self.assertRaises(server._HTTPError) as caught: server._file(self.run,did,'guide.txt')
        self.assertEqual(caught.exception.code,'evidence_changed')
        with self.assertRaises(core.GFError):decisions.answer(self.run,did,'approved','','dashboard',HUMAN,displayed)
        fresh=self.call('gate','a',code=1)['asks'][0]
        self.assertNotEqual(fresh,did)
        self.assertEqual(server._file(self.run,fresh,'guide.txt'),b'different bytes\n')
        self.accept(fresh);self.call('gate','a')
        self.assertEqual(self.snapshot()[1]['nodes']['a']['attempts'],1)

    def test_a6_genuine_021_open_decision_submission_survives_upgrade(self):
        fixture=json.loads((Path(__file__).parent/'fixtures/legacy021.json').read_text())
        self.run=self.project/'.graph-flow/runs/old'
        self.run.mkdir(parents=True)
        for path,text in fixture['files'].items():
            target=self.run/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(text)
        # Restore the actual base Git object used by the old CLI; events stay byte-for-byte intact.
        subprocess.run(['git','-C',str(self.project),'hash-object','-t','commit','-w','--stdin'],
                       input=fixture['git_base_commit'],text=True,check=True,stdout=subprocess.PIPE)
        self.raw=fixture['raw_plan'];did=fixture['decision']
        (self.project/'guide.txt').write_text('old submission\n')
        self.assertTrue(self.snapshot()[1]['decisions'][did]['stale'])
        with self.assertRaises(core.GFError) as caught: decisions.answer(self.run,did,'approved','','terminal',HUMAN)
        self.assertEqual(caught.exception.code,'legacy_decision')
        plan_decision=self.set_plan()['decision']
        current,events,derived=server._snapshot(self.run)
        self.assertTrue(server._view(current,derived,events,self.project)['nodes'][0]['preapproval_submission'])
        self.accept(plan_decision);fresh=self.call('gate','a',code=1)['asks'][0]
        self.accept(fresh);self.call('gate','a');self.call('gate','--final')
        self.assertEqual(self.snapshot()[1]['run']['status'],'complete')
        self.assertEqual(self.snapshot()[1]['nodes']['a']['attempts'],1)

    def test_a7_case_insensitive_project_and_run_aliases(self):
        if not (self.project.parent/self.project.name.upper()).exists():self.skipTest('case-sensitive filesystem')
        did=self.set_plan()['decision'];self.accept(did)
        canonical=store.location(self.run)
        alias=Path(str(self.run).replace('/project/','/PROJECT/').replace('/approval','/APPROVAL'))
        self.assertEqual(store.location(alias),canonical)
        self.run=alias;self.assertEqual(self.call('ready')['ready'],['a'])

    def test_a8_nonfinite_time_limits_are_rejected_for_node_and_run_checks(self):
        for value in (float('nan'),float('inf'),float('-inf'),0,-1):
            for runlevel in (False,True):
                p=copy.deepcopy(self.raw);c=dict(p['nodes'][0]['checks'][0],timeout_s=value)
                if runlevel:p['integration_checks']=[c]
                else:p['nodes'][0]['checks']=[c]
                self.assertTrue(plan.validate(p),(runlevel,value))
                self.file.write_text(json.dumps(p));self.assertEqual(self.call('plan','set',str(self.file),code=1)['code'],'invalid_plan')

    def test_a9_moved_project_registered_on_successful_status(self):
        self.accept(self.set_plan()['decision'])
        moved=self.project.with_name('moved');self.project.rename(moved)
        self.run=moved/'.graph-flow/runs/approval';self.project=moved
        self.call('status')
        self.assertIn(str(moved.resolve()),server._projects())
        self.assertTrue(self.snapshot()[1]['run']['location_mismatch'])

    def test_a10_low_sequence_plan_relabel_rejected_by_every_reader(self):
        self.accept(self.set_plan()['decision']);p,d=self.snapshot()
        last=copy.deepcopy(next(e for e in store.events(self.run) if e['type']=='plan.set'))
        last['seq']=2
        self.rewrite(lambda es:es.append(last))
        for read in (store.events,store.read_plan):
            with self.assertRaises(core.GFError) as caught:read(self.run)
            self.assertEqual(caught.exception.code,'log_sequence');self.assertIn('line ',caught.exception.message)
        self.assertEqual(server._snapshot(self.run)[2]['run']['integrity'][0]['code'], 'log_sequence')
        self.assertEqual(self.call('status')['integrity'][0]['code'], 'log_sequence')
        self.assertEqual(self.call('gate','a',code=4)['code'],'log_sequence')

    def test_a11_docs_state_unsigned_execution_and_cwd(self):
        root=Path(__file__).resolve().parents[1]
        for file in ('references/records.md','references/dashboard.md','SKILL.md'):
            text=(root/file).read_text();self.assertIn('unsigned',text);self.assertIn('bypasses',text)
        self.assertIn('--cwd',(root/'references/records.md').read_text())
