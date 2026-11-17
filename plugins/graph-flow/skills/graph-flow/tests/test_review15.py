"""Round 15: irreversible supersession, workable refusals and consistent consent UI."""
import copy
import json
import os
import re
import subprocess
import time
import threading
import urllib.request
import urllib.parse
import unittest
from pathlib import Path

import test_plan_approval as fixture
from graphflow import core, decisions, gate, server, state, store
from human_support import human_answer, legacy_run
from test_review11 import NODE


class Recovery15Tests(unittest.TestCase):
    setUp = fixture.PlanApprovalTests.setUp
    call = fixture.PlanApprovalTests.call
    set_plan = fixture.PlanApprovalTests.set_plan
    snapshot = fixture.PlanApprovalTests.snapshot
    accept = fixture.PlanApprovalTests.accept

    def prepare(self, purpose='human_check'):
        n = self.raw['nodes'][0]
        n['max_attempts'] = 1
        n['checks'] = [{'id': 'ok', 'type': 'cmd', 'run': 'true'}]
        if purpose == 'node':
            q = {'id':'q','kind':'decision','lane':1,'goal':'Permission','question':'May we publish?',
                 'decision_kind':'authorization','outputs':['approval']}
            self.raw['nodes'].insert(0, q)
            n['needs'] = [{'from':'q','artifact':'approval'}]
        elif purpose == 'human_check':
            n['checks'].append({'id':'human','type':'human','prompt':'Accept the guide?'})
        elif purpose == 'hold':
            n['checks'].append({'id':'host','type':'host','tool':'inspection','expect':'Safe'})
        else:
            n['lane'] = 1 if purpose=='hold_review' else 3
            self.raw['nodes'].append({'id':'r','kind':'review','grade':'daily','goal':'Review','target':'a','lens':'safety','lane':1})
        self.accept(self.set_plan()['decision'])
        if purpose == 'node':
            return 'q', self.call('gate','q',code=1)['asks'][0]
        self.call('assign','a','--executor','inline','--model','m','--effort','high','--provider','p','--family','claude','--isolation','shared')
        self.call('start','a'); (self.project/'guide.txt').write_text('original bytes')
        if purpose == 'hold': self.call('check','record','a','host','--result','failed')
        self.call('submit','a')
        if purpose in ('lane3','hold_review'):
            self.call('assign','r','--executor','inline','--model','m','--effort','high','--provider','p','--family','openai','--isolation','shared')
            self.call('start','r'); f=self.root/'findings.json'; f.write_text(json.dumps([{'file':'guide.txt','line':1,'text':'Unsafe result'}] if purpose=='hold_review' else []))
            self.call('--role','reviewer','--node','r','review','submit','r','--verdict','fail' if purpose=='hold_review' else 'pass','--findings',str(f))
            self.call('gate','r')
        return 'a', self.call('gate','a',code=1)['asks'][0]

    def move(self, name):
        destination = self.root/name
        self.project.rename(destination); self.project=destination
        self.run=destination/'.graph-flow/runs/approval'

    def test_n1_decision_send_back_allows_question_change_remove_or_rename(self):
        for mode in ('question','remove','rename'):
            with self.subTest(mode=mode):
                if mode != 'question':
                    self.run=store.init_run(self.project,mode,{'role':'leader'})
                    self.raw['nodes']=[self.raw['nodes'][-1]];self.raw['nodes'][0].pop('needs',None)
                nid,did=self.prepare('node')
                human_answer(self.run,did,'revision_requested','Use staging')
                self.assertIn('Revise the question',self.call('gate',nid,code=1)['message'])
                if mode == 'question': self.raw['nodes'][0]['question']='May we publish to staging?'
                elif mode == 'remove': self.raw['nodes'].pop(0);self.raw['nodes'][0]['needs']=[]
                else: self.raw['nodes'][0]['id']='q2';self.raw['nodes'][1]['needs'][0]['from']='q2'
                fresh=self.set_plan()['decision'];self.accept(fresh)
                self.assertNotEqual(fresh,did)
                if mode != 'remove':
                    q='q2' if mode=='rename' else 'q';new=self.call('gate',q,code=1)['asks'][0];self.accept(new);self.call('gate',q)
                self.assertEqual(self.call('ready')['ready'],['a'])
                self.call('start','a');self.call('submit','a');self.call('gate','a');self.call('gate','--final')

    def test_n1_human_check_rejection_and_declined_hold_can_raise_attempts(self):
        for purpose in ('human_check','hold'):
            with self.subTest(purpose=purpose):
                if purpose == 'hold': self.run=store.init_run(self.project,'hold',{'role':'leader'})
                nid,did=self.prepare(purpose);human_answer(self.run,did,'rejected','Fix it')
                self.assertEqual(self.call('gate',nid,code=1)['verdict'],'hold')
                error=self.call('start',nid,code=4);self.assertEqual(error['code'],'attempts_exhausted')
                self.assertIn('max_attempts',error['message'])
                self.raw['nodes'][0]['max_attempts']=2
                self.accept(self.set_plan()['decision']);self.call('start',nid)
                if purpose=='hold':self.call('check','record','a','host','--result','passed')
                self.call('submit','a');result=self.call('gate','a',code=1 if purpose=='human_check' else 0)
                if purpose=='human_check':self.accept(result['asks'][0]);self.call('gate','a')
                self.call('gate','--final')

    def test_n1_declined_review_hold_recovers_by_reopening_named_review(self):
        nid,did=self.prepare('hold_review');human_answer(self.run,did,'rejected','Fix the review findings')
        self.call('gate',nid,code=1)
        self.raw['nodes'][0]['max_attempts']=2
        self.file.write_text(json.dumps(self.raw))
        refusal=self.call('plan','set',str(self.file),code=4)
        self.assertIn('gf reopen <review>',refusal['message'])
        self.call('reopen','r','--reason','Revise target')
        self.accept(self.set_plan()['decision']);self.call('start',nid)

    def test_n1_refused_start_preserves_question_submission_and_entire_log(self):
        nid,did=self.prepare();before=(self.run/'events.jsonl').read_bytes();snapshot=self.snapshot()[1]
        self.call('start',nid,code=4)
        self.assertEqual(before,(self.run/'events.jsonl').read_bytes())
        self.assertEqual(snapshot,self.snapshot()[1]);self.accept(did);self.call('gate',nid);self.call('gate','--final')

    def test_n1_changed_approved_bytes_reask_without_attempt_and_never_revive(self):
        nid,did=self.prepare();self.accept(did)
        file=self.project/'guide.txt';file.write_text('current bytes')
        self.call('status')
        self.assertEqual(self.snapshot()[1]['decisions'][did]['status'],'superseded')
        file.write_text('original bytes')
        result=self.call('gate',nid,code=1);self.assertNotEqual(result['asks'][0],did)
        self.accept(result['asks'][0]);self.call('gate',nid);self.call('gate','--final')
        self.assertEqual(self.snapshot()[1]['nodes'][nid]['attempts'],1)

    def test_n1_unusable_approval_allows_replan(self):
        nid,did=self.prepare();self.accept(did);(self.project/'guide.txt').write_text('changed')
        self.raw['nodes'][0]['max_attempts']=2
        self.accept(self.set_plan()['decision']);self.call('start',nid)

    def test_n2_move_back_cannot_revive_any_gate_purpose(self):
        for purpose in ('node','human_check','hold','lane3'):
            with self.subTest(purpose=purpose):
                if purpose!='node':
                    self.run=store.init_run(self.project,'approval-'+purpose,{'role':'leader'})
                    self.raw['nodes']=[copy.deepcopy(self.raw['nodes'][-1])]
                    self.raw['nodes'][0].update(id='a',kind='work',lane=1,owns=['guide.txt'],needs=[])
                original_run=self.run.name
                nid,first=self.prepare(purpose);self.accept(first)
                original_project=self.project
                moved=self.root/('moved-'+purpose);self.project.rename(moved);self.project=moved;self.run=moved/'.graph-flow/runs'/original_run
                self.call('status')
                self.accept(self.set_plan()['decision'])
                second=self.call('gate',nid,code=1)['asks'][0]
                human_answer(self.run,second,'rejected','Do not proceed')
                self.assertEqual(self.call('gate',nid,code=1)['verdict'],'hold')
                moved.rename(original_project);self.project=original_project;self.run=original_project/'.graph-flow/runs'/original_run
                self.accept(self.set_plan()['decision'])
                result=self.call('gate',nid,code=1)
                self.assertNotEqual(result['verdict'],'pass');self.assertTrue(result['asks'])
                self.assertEqual(self.snapshot()[1]['decisions'][first]['status'],'superseded')
                self.assertNotIn('a',self.call('ready')['ready'])
                records=store.events(self.run)
                self.assertTrue(any(e['type']=='decision.superseded' and e['data']['id']==first for e in records))

    def test_n2_observed_move_is_permanent_even_without_reask(self):
        nid,did=self.prepare('node');self.accept(did)
        self.move('away');self.call('status');self.move('project')
        self.assertEqual(self.snapshot()[1]['decisions'][did]['status'],'superseded')
        self.accept(self.set_plan()['decision']);self.assertTrue(self.call('gate',nid,code=1)['asks'])

    def test_n2_trace_and_direct_http_read_record_evidence_invalidation(self):
        nid,did=self.prepare();self.accept(did)
        file=self.project/'guide.txt';file.write_text('edited')
        self.call('trace');file.write_text('original bytes')
        self.assertEqual(self.snapshot()[1]['decisions'][did]['status'],'superseded')
        second=self.call('gate',nid,code=1)['asks'][0];self.accept(second)
        httpd,token=server.make_server()
        thread=threading.Thread(target=httpd.serve_forever,kwargs={'poll_interval':.01},daemon=True);thread.start()
        try:
            file.write_text('edited again')
            url='http://127.0.0.1:%d/api/run?'%httpd.server_address[1]+urllib.parse.urlencode({'project':str(self.project.resolve()),'run':self.run.name})
            request=urllib.request.Request(url,headers={'X-GF-Token':token})
            with urllib.request.urlopen(request) as response: data=json.load(response)
            self.assertEqual(data['state']['decisions'][second]['status'],'superseded')
            file.write_text('original bytes')
            self.assertEqual(self.snapshot()[1]['decisions'][second]['status'],'superseded')
        finally:
            httpd.shutdown();httpd.server_close();thread.join(5)

    def test_s1_legacy_plan_approval_not_voided_by_later_file_edits(self):
        self.run=legacy_run(self.project,'old',{'role':'leader'})
        from graphflow import plan
        p,_=plan.normalize(self.raw)
        with store.transaction(self.run) as tx:
            rev,sha=tx.write_plan(p);tx.append('plan.set',{'revision':rev,'plan_sha256':sha,'fingerprints':{n['id']:state.fingerprint(n) for n in p['nodes']}},{})
            tx.append('node.start',{'node':'a','attempt':1,'base':{}},{})
            tx.append('node.submit',{'node':'a','attempt':1,'changed_files':['guide.txt']},{})
        (self.project/'guide.txt').write_text('legacy bytes')
        did=self.set_plan()['decision'];self.accept(did)
        (self.project/'guide.txt').write_text('legitimate later edit')
        self.call('ready');self.assertTrue(state.plan_approval(self.snapshot()[1])['verified'])

    def test_s3_stale_wait_returns_promptly_with_recovery(self):
        self.accept(self.set_plan()['decision'])
        did=self.call('decide','ask','--kind','information','--question','Which colour?')['id']
        self.move('away');started=time.monotonic()
        result=self.call('decide','wait',did,'--timeout','30')
        self.assertLess(time.monotonic()-started,2);self.assertTrue(result['stale'])
        self.assertEqual(result['stale_reason'],'project_moved');self.assertIn('gf decide ask',result['message'])

    def test_s4_key_recovery_survives_move_but_approval_does_not(self):
        self.accept(self.set_plan()['decision']);(core.gf_home()/'human.key').unlink()
        decisions.repin(self.run,{'role':'human'});self.accept(state.plan_approval(self.snapshot()[1])['id'])
        self.move('away');self.assertFalse(self.snapshot()[1]['run']['key_mismatch'])
        self.accept(self.set_plan()['decision']);self.call('ready')

    def test_s5_approved_decision_advice_gate_then_reopen_works(self):
        nid,did=self.prepare('node');self.accept(did)
        self.raw['nodes'][-1]['goal']='Publish another result'
        self.file.write_text(json.dumps(self.raw))
        error=self.call('plan','set',str(self.file),code=4);self.assertIn('gf reopen',error['message'])
        self.call('gate',nid);self.call('reopen',nid,'--reason','Revise permission')
        self.accept(self.set_plan()['decision']);self.assertTrue(self.call('gate',nid,code=1)['asks'])

    def test_s7_release_card_matches_transitive_contract(self):
        self.raw['nodes']=[{'id':'q','kind':'decision','lane':1,'goal':'Permission','question':'Proceed?','decision_kind':'authorization','outputs':['approval']},
            dict(self.raw['nodes'][0],needs=[{'from':'q','artifact':'approval'}]),
            dict(self.raw['nodes'][0],id='b',owns=['b.txt'],needs=[{'from':'a','artifact':'guide.txt'}])]
        expected=sorted(nid for nid,deps in state._closure({n['id']:n for n in self.raw['nodes']}).items() if 'q' in deps)
        script=Path(__file__).parents[1]/'scripts/graphflow/page.js'
        source=script.read_text();source=source[:source.index("if (typeof document !== 'undefined')")]
        code=source+'\nconsole.log(JSON.stringify(releasedNodes('+json.dumps(self.raw['nodes'])+',"q").map(n=>n.id).sort()));'
        result=subprocess.run([NODE,'--input-type=module','-e',code],text=True,capture_output=True,check=True)
        self.assertEqual(json.loads(result.stdout),expected);self.assertEqual(expected,['a','b'])

    def test_s6_recovery_documentation_names_working_commands(self):
        base=Path(__file__).parents[1]
        for name in ('references/records.md','references/leader.md'):
            text=(base/name).read_text()
            self.assertIn('max_attempts',text);self.assertIn('superseded',text)
        self.assertIn('(references/leader.md)', (base/'SKILL.md').read_text())


class Screen15Tests(unittest.TestCase):
    def test_b1_names_enumerated_across_all_surfaces_and_languages(self):
        page=(Path(__file__).parents[1]/'scripts/graphflow/page.js').read_text()
        words=json.loads(page.split('const STRINGS = ',1)[1].split(';\n// UI_STRINGS_END',1)[0])
        self.assertEqual(set(words['ko']),set(words['en']))
        surfaces={
            'binding': ['decision','decisionRef','answerHere','decisionTab','supersededNotice','supersededLink',
                        'planChangeIds','planChangesRead','planCardQuestion','planQuestions','questionsForNode',
                        'planUnverifiedHelp','legacyDecision','evidenceChanged','answeredQuestion','countDecision','countPlannedDecision','evDecisionAsked','decisionOnly','newPlanDecision','newPlanRead'],
            'free': ['freeEvidenceChanged','questionRef','freeQuestion','freeTab','questionOnly','countQuestions','evAsked','evAnswered','freeAnswerHere'],
            'returned': ['returned','filterReturned','evReturned','evReplan','attemptReturned','returnedKey','pastReturn'],
            'final': ['runChecksTitle','evFinalPassed','evFinalFailed'],
            'automatic': ['checksPassed','planCardChecks','countChecks','checkProgress'],
            'human_review': ['holdReviewExact'],
        }
        for language,terms in words.items():
            for concept,keys in surfaces.items():
                for key in keys:
                    with self.subTest(language=language,concept=concept,key=key):
                        value=re.sub(r'\{[^}]+\}', '', terms[key].lower())
                        if concept=='binding':self.assertNotIn('질문' if language=='ko' else 'question',value)
                        if concept=='free':self.assertNotIn('결정' if language=='ko' else 'decision',value)
                        if concept=='returned':self.assertIn('고치러 돌아옴' if language=='ko' else 'returned',value)
                        if concept=='final':self.assertIn('전체 결과 확인' if language=='ko' else 'whole',value)
                        if concept=='automatic':self.assertIn('자동 검사' if language=='ko' else 'automated',value)
        self.assertIn("r.purpose==='free'",page)
        self.assertIn("d.free?'freeRead':'read'",page)

    def test_b2_b4_b7_counts_compact_fit_and_plain_permission_refusal(self):
        page=(Path(__file__).parents[1]/'scripts/graphflow/page.js').read_text()
        code=page[:page.index("if (typeof document !== 'undefined')")]+r'''
import assert from 'node:assert/strict';
const nodes=Array.from({length:12},(_,i)=>({id:'n'+i,kind:'work',title:'Step '+i,status:i<3?'running':i<5?'submitted':'pending',needs:i?[{from:'n'+(i-1)}]:[]}));
const counts=stateCounts(nodes,[]);assert.equal(Object.values(counts).reduce((a,b)=>a+b,0),12);assert.equal(counts.running,3);assert.equal(counts.submitted,2);
const rejected=planFlow({nodes:nodes.map(n=>({...n,plan_revision_wait:true})),edges:[]});assert(rejected.nodes.every(n=>displayState(n,[])==='planRevisionState'));
const edges=nodes.slice(1).map((n,i)=>({from:'n'+i,to:n.id}));
const layout=compactOverview(layeredLayout(nodes,edges,[],true,{level:'overview'}),900);
const scale=fitScale(layout.bounds,900,500);assert(layout.bounds.width*scale<=900);assert(layout.bounds.height*scale<=500);
for(const r of layout.cardRects)assert.equal(offscreenDirection({x:r.x*scale,y:r.y*scale,width:r.width*scale,height:r.height*scale},900,500),null);
const c=createDecisionController(),q={id:'d1',kind:'authorization',purpose:'authorization',record_purpose:'node',files:[],context:{},identity:{}};
c.refresh({decisions:[q],nodes:[]},{project:'p',run:'r'});c.open('d1');assert(c.canSubmit('rejected',''));assert(!c.canSubmit('revision_requested',''));
console.log('counts, compact fit, refusal passed');
'''
        result=subprocess.run([NODE,'--input-type=module','-e',code],text=True,capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr[-2000:])
