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

class Notices20Tests(unittest.TestCase):
    def setUp(self):
        OUTPUT.mkdir(parents=True,exist_ok=True)
        self.tmp=tempfile.TemporaryDirectory(dir=OUTPUT);self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.f=fixtures.Fixture(self.root,'observations')
        env=mock.patch.dict(os.environ,self.f.env,clear=True);env.start();self.addCleanup(env.stop)


    def test_r2a_literal_later_paths_transitive_cwd_no_false_prefix_and_no_refusal(self):
        raw=self.f.raw;raw['nodes'] += [fixtures.review(),fixtures.work('b','중간 작업',['a']),fixtures.work('c','후속 작업',['b'])]
        raw['nodes'][0]['lane']=2;raw['nodes'][-1]['owns']=['later/out.txt']
        raw['integration_checks']=[dict(id='all',type='cmd',title='전체 확인',run='test -s out.txt',cwd='later')]
        self.assertEqual(plan.validate(raw),[])
        normalized,notices=plan.normalize(raw);found=[n for n in notices if n['code']=='circular_run_check']
        self.assertEqual([(n['check'],n['node'],n['later']) for n in found],[('all','a','c')])
        self.assertEqual(self.f.post(),self.f.approval)
        self.assertTrue(any(n['code']=='circular_run_check' for n in self.f.call('plan','validate',str(self.f.root/'plan.json'))['notices']))
        for command in ('test -s out.txt.backup','test -s "$LATER"','python runner.py'):
            other=copy.deepcopy(raw);other['integration_checks'][0]['run']=command
            self.assertFalse(plan.circular_run_checks(plan.normalize(other)[0]),command)
        other=copy.deepcopy(raw);other['nodes'][-1]['needs']=[]
        self.assertFalse(plan.circular_run_checks(plan.normalize(other)[0]))
        raw['nodes'][0]['lane']=3;self.assertEqual(len(plan.circular_run_checks(plan.normalize(raw)[0])),1)


    def test_r2b_red_and_first_check_record_prework_pass_without_changing_results(self):
        f=self.f;f.raw['nodes'][0]['checks'][0]['run']='test -d .';f.post(True);f.call('start','a')
        red=f.call('red','a');self.assertTrue(red['results'][0]['passes_before_work']);self.assertFalse(red['results'][0]['failed_first'])
        (f.project/'guide.txt').write_text('작업했어요')
        self.assertNotIn('passes_before_work',f.call('red','a')['results'][0])
        f.call('submit','a');f.call('gate','a')
        f.raw['nodes'].append(fixtures.work('b','다른 안내'));f.raw['nodes'][-1]['checks'][0]['run']='test -d .';f.post(True);f.call('start','b')
        result=f.call('check','run','b','text');self.assertTrue(result['passes_before_work']);self.assertEqual(result['result'],'passed')
        self.assertNotIn('passes_before_work',f.call('check','run','b','text'))
        result=trace.trace(f.run);self.assertIn('checks passing before work: 2',result['conformance']['P1']['observation'])
        p,events,derived=store.snapshot(f.run);view=server._view(p,derived,events,f.project.resolve())
        self.assertEqual(len([n for n in view['notices'] if n['code']=='passes_before_work']),2)
        self.assertEqual(view['nodes'][0]['notices'][0]['check'],'text')
        for command,key in [(('plan','validate',str(f.root/'plan.json')),'notices'),(('plan','set',str(f.root/'plan.json')),'normalization_notices')]:
            self.assertEqual(len([n for n in f.call(*command)[key] if n['code']=='passes_before_work']),2)
