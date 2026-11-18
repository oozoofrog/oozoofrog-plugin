"""First real run regressions: notices and provenance never change verdicts."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock
from test_questions20 import OUTPUT, fixtures
import test_page
import test_gate
from graphflow import assign, plan, server, state, store, trace

class History20Tests(unittest.TestCase):
    def setUp(self):
        OUTPUT.mkdir(parents=True,exist_ok=True)
        self.tmp=tempfile.TemporaryDirectory(dir=OUTPUT);self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.f=fixtures.Fixture(self.root,'observations')
        env=mock.patch.dict(os.environ,self.f.env,clear=True);env.start();self.addCleanup(env.stop)


    def review(self,verdict):
        f=self.f;f.assign('r',True);f.call('start','r');file=f.root/'findings.json'
        fixtures.write_json(file,[dict(severity='high',file='guide.txt',line=2,text='복구 순서가 없어요.',evidence='2번째 줄 다음이 비어 있어요.')] if verdict=='fail' else [])
        f.call('--role','reviewer','--node','r','review','submit','r','--verdict',verdict,'--findings',str(file));f.call('gate','r')


    def test_r1_previous_failed_review_in_brief_and_r6_no_direct_return(self):
        f=self.f;f.raw['nodes'].append(fixtures.review());f.post(True);f.submit();self.review('fail')
        text=f.call('brief','a')['brief']
        for value in ('Review findings on your previous submission','high','guide.txt:2','복구 순서가 없어요.','2번째 줄 다음이 비어 있어요.'):
            self.assertIn(value,text)
        self.assertEqual(f.call('start','a',code=4)['code'],'not_startable')
        self.assertEqual(f.call('reopen','a','--reason','고쳐요',code=4)['code'],'wrong_status')
        self.assertEqual(f.call('gate','a',code=1)['verdict'],'hold')
        f.call('start','a')  # A hold creates a question, but does not require an answer before another attempt.
        self.assertIn('복구 순서가 없어요.',f.call('brief','a')['brief'])
        f.call('submit','a');self.review('pass')
        self.assertNotIn('Review findings on your previous submission',f.call('brief','a')['brief'])


    def test_r3_run_and_node_rejections_with_current_review_facts(self):
        data=fixtures.build(self.root,'trajectory')
        with mock.patch.dict(os.environ,{'GF_HOME':data['home'],'GF_NO_OPEN':'1'},clear=True):
            run=Path(data['project'])/'.graph-flow/runs'/data['run'];result=trace.trace(run)
            history=result['nodes']['a']['rejection_history']
            self.assertEqual([[c['origin'] for c in h['checks']] for h in history],[['run'],['node']])
            p,events,derived=store.snapshot(run);view=server._view(p,derived,events,Path(data['project']).resolve())
            q=next(d for d in view['decisions'] if d['purpose']=='trajectory')
            self.assertEqual(q['facts']['history'][0]['rejection_checks'][0]['origin'],'run')
            self.assertEqual(q['facts']['history'][1]['rejection_checks'][0]['origin'],'node')
            self.assertEqual(q['facts']['reviews'][0]['verdict'],'pass')


    def test_r4_p10_unplanned_breakdown_is_readable(self):
        metrics={'nodes':{},'run_cmd_checks':{},'stuck':{'replan':0,'superseded_decisions':0,'unverified_at_final':0},'human':{'answers':{'total':3,'planned':1,'unplanned':2,'by_kind':{'plan_approval':1,'plan_reapproval':1,'trajectory':1,'free':0}},'wait':{'total_ms':0,'longest_ms':0,'open':[]}}}
        self.assertIn('unplanned 2: plan_reapproval 1, trajectory 1',trace.conformance({},[],metrics)['P10']['observation'])


    def test_r6_exact_existing_trajectory_threshold(self):
        case=test_gate.EvaluateTests();case.setUp();case.lane(2)
        for attempts,clean,rollbacks,expected in [(1,True,0,'pass'),(2,True,0,'pass'),(3,False,0,'needs_approval'),(1,False,0,'needs_approval'),(1,True,1,'needs_approval')]:
            case.st['attempts']=attempts;case.st['trajectory_clean']=clean
            from graphflow import gate
            outcome=gate.evaluate(case.plan,case.state,case.node['id'],[],[],rollbacks)
            self.assertEqual(outcome['verdict'],expected)
            if expected=='needs_approval':self.assertEqual(outcome['rule'],'R5')
