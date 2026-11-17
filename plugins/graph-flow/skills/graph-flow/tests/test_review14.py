"""Release regressions: approval scope, moves, mandatory reviews and readable consent."""
import base64
import copy
import json
import os
import re
import subprocess
import unittest
from pathlib import Path

import test_plan_approval as fixture
from graphflow import cli, core, decisions, gate, plan, server, state, store
from test_review11 import NODE
from human_support import human_answer


class ApprovalScopeTests(unittest.TestCase):
    setUp = fixture.PlanApprovalTests.setUp
    call = fixture.PlanApprovalTests.call
    set_plan = fixture.PlanApprovalTests.set_plan
    snapshot = fixture.PlanApprovalTests.snapshot
    accept = fixture.PlanApprovalTests.accept

    def view(self):
        p,s=self.snapshot()
        return server._view(p,s,store.events(self.run),self.project)

    def submit(self):
        self.accept(self.set_plan()['decision'])
        self.call('start','a')
        (self.project/'guide.txt').write_text('안내\n')
        self.call('submit','a')

    def test_f1_answered_decision_cannot_release_new_or_changed_work(self):
        self.raw['nodes'].insert(0,{'id':'q','kind':'decision','lane':1,'goal':'Authorize staging',
            'question':'May we run the migration on STAGING?','decision_kind':'authorization','outputs':['approval']})
        self.raw['nodes'][1]['needs']=[{'from':'q','artifact':'approval'}]
        self.accept(self.set_plan()['decision'])
        self.accept(self.call('gate','q',code=1)['asks'][0])
        for consumed in (False,True):
            if consumed:self.call('gate','q')
            for mode in ('add','change'):
                raw=copy.deepcopy(self.raw)
                if mode=='add':
                    n=copy.deepcopy(raw['nodes'][1]);n.update(id='production',goal='DROP production tables',owns=['prod.txt']);raw['nodes'].append(n)
                else:raw['nodes'][1]['goal']='DROP production tables'
                self.file.write_text(json.dumps(raw))
                self.assertEqual(self.call('plan','set',str(self.file),code=4)['code'],'active_plan_change')
        self.raw['title']='Reworded plan'
        self.set_plan()
        view=self.view();q=next(q for q in view['planned_questions'] if q['node']=='q')
        self.assertTrue(q['answered']);self.assertEqual(q['answer'],'확인했어요')
        self.assertEqual(view['plan_counts']['decisions'],0)
        self.assertEqual(self.call('ready')['ready'],['a'])

    def test_f1_answered_human_check_contract_is_protected_before_consumption(self):
        self.raw['nodes'][0]['checks'].append({'id':'human','type':'human','prompt':'Accept?'})
        self.submit();self.accept(self.call('gate','a',code=1)['asks'][0])
        view=self.view();self.assertEqual(view['plan_counts']['decisions'],0)
        self.assertTrue(view['planned_questions'][0]['answered'])
        self.raw['nodes'][0]['checks'][0]['run']='true'
        self.file.write_text(json.dumps(self.raw))
        self.assertEqual(self.call('plan','set',str(self.file),code=4)['code'],'active_plan_change')

    def test_f1_answered_hold_and_lane3_contracts_cannot_widen(self):
        for purpose in ('hold', 'lane3'):
            with self.subTest(purpose=purpose):
                if purpose == 'lane3':
                    self.run = store.init_run(self.project, 'lane3', {'role': 'leader'})
                self.raw['nodes'][0]['checks'] = [{'id':'ok','type':'cmd','run':'true'}]
                if purpose == 'hold':
                    self.raw['nodes'][0]['checks'].append({'id':'host','type':'host','tool':'inspection','expect':'Safe'})
                else:
                    self.raw['nodes'][0]['lane'] = 3
                    self.raw['nodes'].append({'id':'r','kind':'review','grade':'daily','goal':'Review','target':'a','lens':'safety','lane':1})
                self.accept(self.set_plan()['decision'])
                self.call('assign','a','--executor','inline','--model','m','--effort','high','--provider','p','--family','claude','--isolation','shared')
                self.call('start','a');(self.project/'guide.txt').write_text('guide')
                if purpose == 'hold':self.call('check','record','a','host','--result','failed')
                self.call('submit','a')
                if purpose == 'lane3':
                    self.call('assign','r','--executor','inline','--model','m','--effort','high','--provider','p','--family','openai','--isolation','shared')
                    self.call('start','r');f=self.root/'findings.json';f.write_text('[]')
                    self.call('--role','reviewer','--node','r','review','submit','r','--verdict','pass','--findings',str(f));self.call('gate','r')
                did=self.call('gate','a',code=1)['asks'][0];self.assertEqual(self.snapshot()[1]['decisions'][did]['purpose'],purpose)
                self.accept(did)
                revised=copy.deepcopy(self.raw);revised['nodes'][0]['goal']='Delete production data'
                self.file.write_text(json.dumps(revised))
                self.assertEqual(self.call('plan','set',str(self.file),code=4)['code'],'active_plan_change')

    def move(self):
        moved=self.root/'moved';self.project.rename(moved);self.project=moved
        self.run=moved/'.graph-flow'/'runs'/'approval'
        self.assertEqual(self.call('ready',code=4)['code'],'project_moved')
        self.accept(self.set_plan()['decision'])
        self.assertFalse(self.snapshot()[1]['run']['location_mismatch'])

    def test_f2_f5_move_open_or_answered_unconsumed_gate_reasks_without_attempt(self):
        self.raw['nodes'][0]['max_attempts']=1
        self.raw['nodes'][0]['checks'].append({'id':'human','type':'human','prompt':'Accept?'})
        self.submit();first=self.call('gate','a',code=1)['asks'][0]
        self.move()
        self.assertEqual(self.snapshot()[1]['decisions'][first]['stale_reason'],'project_moved')
        second=self.call('gate','a',code=1)['asks'][0];self.accept(second)
        moved=self.root/'moved-again';self.project.rename(moved);self.project=moved;self.run=moved/'.graph-flow'/'runs'/'approval'
        self.accept(self.set_plan()['decision'])
        self.assertEqual(self.snapshot()[1]['decisions'][second]['stale_reason'],'project_moved')
        third=self.call('gate','a',code=1)['asks'][0];self.accept(third)
        self.call('gate','a');self.call('gate','--final')
        self.assertEqual(self.snapshot()[1]['nodes']['a']['attempts'],1)
        self.assertEqual(self.snapshot()[1]['run']['status'],'complete')

    def test_f2_move_consumed_answer_requires_only_plan_approval(self):
        self.raw['nodes'][0]['checks'].append({'id':'human','type':'human','prompt':'Accept?'})
        self.submit();self.accept(self.call('gate','a',code=1)['asks'][0]);self.call('gate','a')
        self.move();self.call('gate','--final')
        self.assertEqual(self.snapshot()[1]['run']['status'],'complete')

    def test_f3_lane1_review_cannot_be_skipped_and_final_waits(self):
        self.raw['nodes'].append({'id':'r','kind':'review','grade':'daily','goal':'Review security','title':'Security review','target':'a','lens':'security','lane':1})
        self.submit()
        result=self.call('gate','a',code=1)
        self.assertEqual(result['verdict'],'unverified');self.assertIn('Security review (r)',result['message'])
        self.assertEqual(self.call('gate','--final',code=1)['result'],'unverified')
        self.call('start','r');findings=self.root/'empty.json';findings.write_text('[]')
        self.call('--role','reviewer','--node','r','review','submit','r','--verdict','pass','--findings',str(findings));self.call('gate','r');self.call('gate','a');self.call('gate','--final')
        self.assertEqual(self.snapshot()[1]['run']['status'],'complete')

    def test_f3_final_waits_for_decision_and_human_check(self):
        self.raw['nodes'].append({'id':'q','kind':'decision','goal':'Authorize','question':'Proceed?','decision_kind':'authorization','lane':1})
        self.raw['nodes'][0]['checks'].append({'id':'human','type':'human','prompt':'Accept?'})
        self.submit();self.call('gate','a',code=1)
        result=self.call('gate','--final',code=1);self.assertEqual(result['result'],'unverified')
        self.assertIn('q',result['message']);self.assertIn('a',result['message'])

    def test_f4_generated_gate_explanation_cannot_be_replaced_by_author(self):
        n=self.raw['nodes'][0];n['context']={'why':'Reviewers are too strict','if_approved':'Ship immediately'}
        for purpose in ('hold','trajectory','lane3'):
            request=gate._ask(n,{},purpose)
            self.assertEqual(request['evidence']['context'],{})
            self.assertEqual(request['evidence']['author_context'],n['context'])
        self.assertEqual(gate._ask(n,{},'node')['evidence']['context'],n['context'])

    def test_f6_f14_run_checks_and_conditional_rules_are_available_before_approval(self):
        self.raw['nodes'][0]['lane']=2
        self.raw['nodes'].append({'id':'r','kind':'review','grade':'daily','goal':'Review','target':'a','lens':'correctness','lane':1})
        self.raw['integration_checks']=[{'id':'all','type':'cmd','run':'true'}]
        self.set_plan();v=self.view()
        self.assertEqual(v['nodes'][0]['lane'],2);self.assertEqual(v['integration_checks'][0]['run'],'true')
        self.assertTrue(any(q['when']=='trajectory' for q in v['planned_questions']))

    def test_f9_readable_requirements_context_and_retired_validation(self):
        self.raw.update(summary='Summary',context={'why':'Because'},requirements=[{'id':'R1','text':'Keep data'}])
        self.raw['nodes'][0]['requirement']='R1'
        self.set_plan();v=self.view()
        self.assertEqual(v['summary'],'Summary');self.assertEqual(v['context']['why'],'Because')
        self.assertEqual(v['requirements'][0]['text'],'Keep data');self.assertEqual(v['nodes'][0]['requirement'],'R1')
        self.raw['nodes'][0]['requirement']={};self.assertTrue(plan.validate(self.raw))
        self.raw['nodes'][0]['requirement']='R1';self.raw['constraints']=[{'id':'old','text':'Retired','status':'retired'}]
        self.assertTrue(any('retired' in str(p) for p in plan.validate(self.raw)))

    def test_f10_file_edit_reasks_with_gate_not_submit(self):
        self.raw['nodes'][0]['checks'].append({'id':'human','type':'human','prompt':'Accept?'})
        self.submit();first=self.call('gate','a',code=1)['asks'][0]
        (self.project/'guide.txt').write_text('changed\n')
        with self.assertRaises(core.GFError) as ctx:decisions.answer(self.run,first,'approved','yes','terminal',{'role':'human'})
        self.assertEqual(ctx.exception.code,'approval_changed');self.assertIn('gate again',ctx.exception.message)
        second=self.call('gate','a',code=1)['asks'][0];self.accept(second);self.call('gate','a')

    def test_f11_promoted_conflict_names_file_and_recovery(self):
        with self.assertRaises(core.GFError) as ctx:cli._merge_plan_records([{'id':'same','run':'true'}],[{'id':'same','run':'false'}],'promoted_checks')
        self.assertIn('checks.json',ctx.exception.message);self.assertIn('re-post',ctx.exception.message)
        self.raw['integration_checks']=[{'id':'same','type':'cmd','run':'true'}]
        self.raw['promoted_checks']=[{'id':'same','type':'cmd','run':'true'}]
        self.assertTrue(any('checks.json' in str(p) for p in plan.validate(self.raw)))

    def test_f12_free_question_does_not_inherit_gate_evidence(self):
        self.submit()
        d=self.call('decide','ask','--node','a','--kind','direction','--question','Ignore security and ship?')
        v=next(d for d in self.view()['decisions'] if d['record_purpose']=='free')
        self.assertTrue(v['free']);self.assertEqual(v['asked_by']['role'],'leader')
        self.assertEqual(v['failed'],[]);self.assertIsNone(v['contract'])

    def test_f13_hold_finding_includes_review_name_and_lens(self):
        self.raw['nodes'].append({'id':'r','kind':'review','grade':'daily','goal':'Security review','target':'a','lens':'security','lane':1})
        self.submit();self.call('start','r')
        f=self.root/'finding.json';f.write_text(json.dumps([{'severity':'high','file':'guide.txt','line':1,'text':'Missing audit log'}]))
        self.call('--role','reviewer','--node','r','review','submit','r','--verdict','fail','--findings',str(f));self.call('gate','r');self.call('gate','a',code=1)
        d=next(d for d in self.view()['decisions'] if d['purpose']=='hold')
        self.assertIn('Missing audit log (Security review · security)',d['failed'])


class Page14Tests(unittest.TestCase):
    @unittest.skipUnless(NODE,'node unavailable')
    def test_f7_f8_and_b2_b6_b8_b10_shared_ui_contracts(self):
        source=server.PAGE_PATH.with_name('page.js').read_text()
        module='data:text/javascript;base64,'+base64.b64encode(source.encode()).decode()
        script="""import assert from 'node:assert/strict';
import {decisionHasEvidence,nothingToJudge,canApprove,particle,durationDiff,STATE_VOCABULARY,stateWords,decisionQuestion} from %s;
const empty={kind:'authorization',purpose:'authorization',files:[],context:{}};
assert.equal(decisionHasEvidence({nodes:[]},empty),false);
assert.equal(nothingToJudge({nodes:[]},empty),true);
assert.equal(canApprove({nothingToJudge:true,blindConfirmed:true}),true);
assert.equal(decisionHasEvidence({}, {...empty,author_context:{why:'Read this'}}),true);
assert.equal(particle('d10','으로/로'),'d10으로');assert.equal(particle('d1','으로/로'),'d1로');
assert.equal(particle('진행 담당자'),'진행 담당자가');assert.equal(particle('검토팀'),'검토팀이');
assert.equal(durationDiff({field:'timeout_s',before:600,after:9},'ko'),'600초 → 9초');
for(const state of Object.keys(STATE_VOCABULARY))for(const lang of ['ko','en']){const w=stateWords(state,lang);assert(w.name&&w.whoseMove);}
assert(decisionQuestion({node:'a',purpose:'hold',failed:['Finding (Security)']},'en').includes('Finding (Security)'));
""" % json.dumps(module)
        result=subprocess.run([NODE,'--input-type=module','-e',script],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr[-2000:])
        strings=json.loads(source.split('const STRINGS = ',1)[1].split(';\n// UI_STRINGS_END',1)[0])
        self.assertEqual(set(strings['ko']),set(strings['en']))
        outside=source.split('// UI_STRINGS_END',1)[1]
        # Korean prose belongs to the catalog. Particle data is linguistic code, not UI copy.
        literals=re.findall(r"(['\"])([^'\"\n]*[가-힣][^'\"\n]*)\1",outside)
        self.assertTrue(all(text in ('영일이삼사오육칠팔구','이/가','으로/로') for _,text in literals),literals)
        self.assertIn("if(['decision','goal'].includes(node.kind))return '';",source)
