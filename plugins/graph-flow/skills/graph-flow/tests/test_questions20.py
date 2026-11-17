"""Q1–Q6: every decision has an ordered choice screen with recorded facts."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import test_page
from graphflow import server, store, mcp

SCREENS = Path(__file__).resolve().parents[3] / 'dev/screens'
spec = importlib.util.spec_from_file_location('screen_fixtures20', SCREENS / 'build_fixtures.py')
fixtures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixtures)
OUTPUT = Path('/Volumes/eyedisk/build/graph-flow-screens/r20')

class Question20Tests(unittest.TestCase):
    run_dom = test_page.PageTests.run_dom
    run_controller = test_page.PageTests.run_controller

    def test_q1_q5_all_kinds_render_ordered_blocks_and_distinct_consequences(self):
        self.run_dom(r"""
const api=globalThis.surfaceTest;
for(const [purpose,kind] of [['human_check','review'],['hold','review'],['trajectory','review'],['lane3','authorization'],['authorization','authorization'],['review','review'],['information','information'],['direction','direction']]){
 get('flow-tab').click();live={...live,language:'ko',decisions:[{...d,purpose,kind,record_purpose:['authorization','review'].includes(purpose)?'node':purpose,free:['information','direction'].includes(kind),node_title:'안내 쓰기',facts:{attempts:3,max_attempts:3,releases:['안내 전달'],blocked:['배포'],history:[{attempt:1,state:'reject',reasons:['안내 검사'],reviews:[{title:'안내 검토',verdict:'fail',findings:[{severity:'high',file:'guide.txt',line:2,text:'복구 순서가 없어요.',evidence:'2번째 줄'}]}]},{attempt:2,state:'reject',reasons:['전체 검사']},{attempt:3,state:'needs_approval'}],reviews:[{title:'안내 검토',verdict:'pass',accepted:true}]}}]};api.applyView(live);get('attention').querySelectorAll('button').at(-1).click();
 const root=get('decision'),all=[];const walk=e=>{if(e.dataset.questionBlock)all.push(e.dataset.questionBlock);e.children.forEach(walk);};walk(root);
 assert.deepEqual(all.slice(0,5),['question','why','choices','history','verified']);
 const effects=get('answer-actions').querySelectorAll('.action-effect').map(e=>e.textContent);assert(effects.length>=2);assert(effects.every(Boolean));assert.equal(new Set(effects).size,effects.length);
 assert(root.querySelector('.answer-form').hidden,'inputs wait for an option');
 if(purpose==='trajectory'){assert(root.textContent.includes('3번 만에 제출'));assert(root.textContent.includes('시도 3번을 다 써서'));assert(root.textContent.includes('복구 순서가 없어요.'));}
}
""")

    def test_q6_reading_gate_and_negative_text_remain_required(self):
        self.run_dom(r"""
get('attention').querySelectorAll('button').at(-1).click();
const actions=get('answer-actions').querySelectorAll('button[data-outcome]');
const yes=actions.find(b=>b.dataset.outcome==='approved'),no=actions.find(b=>b.dataset.outcome==='revision_requested');
assert(yes.disabled);no.click();assert(!get('decision').querySelector('.answer-form').hidden);
get('decision').querySelector('.answer-form').querySelector('button').click();await settle();assert.equal(posts.length,0);
get('decision').querySelector('.file-choices').querySelector('button').click();await settle();assert(yes.disabled,'hold requires detailed evidence');
get('decision').querySelector('.evidence-action').click();assert(!yes.disabled);
""")

    def test_q4_facts_from_real_attempts_and_q3_exhaustion(self):
        OUTPUT.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=OUTPUT) as scratch:
            data=fixtures.build(Path(scratch),'trajectory')
            with mock.patch.dict(os.environ,{'GF_HOME':data['home'],'GF_NO_OPEN':'1'},clear=True):
                run=Path(data['project'])/'.graph-flow/runs'/data['run']
                p,events,state=store.snapshot(run)
                before=(run/'events.jsonl').read_bytes()
                view=server._view(p,state,events,Path(data['project']).resolve())
                decision=next(d for d in view['decisions'] if d['purpose']=='trajectory')
                facts=decision['facts'];self.assertEqual(facts['attempts'],3)
                self.assertEqual([a['state'] for a in facts['history']],['reject','reject','needs_approval'])
                self.assertEqual(facts['history'][0]['reviews'][0]['verdict'],'fail')
                self.assertEqual(facts['reviews'][0]['verdict'],'pass')
                self.assertEqual(facts['releases'],['안내 전달'])
                self.assertEqual((run/'events.jsonl').read_bytes(),before)
                self.assertNotIn('facts',decision['identity'])

    def test_q4_reapproval_changes_survive_reload_and_free_options_are_recorded(self):
        OUTPUT.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=OUTPUT) as scratch:
            for scenario in ('reapproval','free'):
                data=fixtures.build(Path(scratch),scenario)
                with mock.patch.dict(os.environ,{'GF_HOME':data['home'],'GF_NO_OPEN':'1'},clear=True):
                    p,events,state=store.snapshot(Path(data['project'])/'.graph-flow/runs'/data['run'])
                    view=server._view(p,state,events,Path(data['project']).resolve())
                    if scenario=='reapproval':
                        self.assertTrue(view['plan_approval']['facts']['reapproval'])
                        self.assertNotEqual(view['previous_plan'],view['current_plan'])
                    else:
                        self.assertEqual([x['label'] for x in view['decisions'][0]['facts']['options']],['처음 쓰는 사람','이미 써 본 사람'])
                        response=mcp._call(mcp.TOOLS['decision_ask'],{'run':str(Path(data['project'])/'.graph-flow/runs'/data['run']),'kind':'information','question':'고를까요?','options':['--first','둘째']})
                        payload=json.loads(response['content'][0]['text'])
                        self.assertEqual([o['answer'] for o in payload['evidence']['options']],['--first','둘째'])
