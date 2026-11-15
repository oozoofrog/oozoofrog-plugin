import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'scripts'))
from graphflow import route
from graphflow.core import GFError


class RouteTests(unittest.TestCase):
    def setUp(self):
        self.routing = route.load_routing()

    def pick(self, grade='daily', kind='work', state=None, host=(), usage=None):
        node = {'kind': kind}
        if grade is not None:
            node['grade'] = grade
        return route.suggest(node, state, host, usage, self.routing)

    def provider(self, name, family='claude', used=10, stale=False):
        return dict(provider=name, family=family, used_percent=used, stale=stale)

    def test_table(self):
        self.assertEqual(set(self.routing['grades']), {'bulk', 'scoped', 'daily', 'large', 'security'})
        for grade in self.routing['grades'].values():
            self.assertEqual(set(grade), {'claude', 'openai'})
        text = json.dumps(self.routing)
        self.assertNotIn('/', text)
        self.assertNotIn('provider', self.routing)
        self.assertEqual(set(self.routing), {'schema_version', 'grades', 'ladders', 'efforts', 'effort_caps', 'thresholds', 'default_family'})

    def test_bad_table(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / 'routing.json'
            for value in ('{', '[]', '{}', '{"schema_version": 2}'):
                p.write_text(value)
                with self.assertRaises(GFError) as cm:
                    route.load_routing(p)
                self.assertEqual((cm.exception.code, cm.exception.exit_code), ('bad_routing', 2))
            with self.assertRaises(GFError):
                route.load_routing(p / 'missing')

    def test_grade_and_models(self):
        self.assertEqual(self.pick(None)['model'], 'claude-opus-5-5')
        for grade in self.routing['grades']:
            for family in ('claude', 'openai'):
                self.routing['default_family'] = family
                result = self.pick(grade)
                self.assertEqual((result['model'], result['effort']), tuple(self.routing['grades'][grade][family][k] for k in ('model', 'effort')))

    def test_review_family(self):
        self.assertEqual(self.pick(kind='review', state={'target_family':'claude'})['family'], 'openai')
        self.assertEqual(self.pick(kind='review', state={'target_family':'openai'})['family'], 'claude')
        self.assertIn('unknown', self.pick(kind='review')['why'])
        self.assertEqual(self.pick(state={'target_family':'claude'})['family'], 'claude')

    def test_work_usage_family(self):
        usage = {'providers':[self.provider('a', used=80), self.provider('b', 'openai', 89)]}
        self.assertEqual(self.pick(usage=usage)['family'], 'openai')
        for key, value in [('used_percent',79), ('used_percent',None), ('stale',True)]:
            changed = copy.deepcopy(usage)
            changed['providers'][0][key] = value
            self.assertEqual(self.pick(usage=changed)['family'], 'claude')
        usage['providers'][1]['used_percent'] = 90
        self.assertEqual(self.pick(usage=usage)['family'], 'claude')
        self.assertEqual(self.pick(usage={'providers':[]})['family'], 'claude')

    def test_escalation(self):
        self.assertEqual(self.pick(state={'rejections':[]})['effort'], 'medium')
        defect = {'rejections':[{'reason':'defect: wrong result'}]}
        approach = {'rejections':[{'reason':'approach: wrong design'}]}
        self.assertEqual(self.pick(state=defect)['effort'], 'high')
        self.assertEqual(self.pick('scoped', state=approach)['model'], 'claude-opus-5-5')
        self.assertEqual(self.pick('scoped', state=approach)['effort'], 'medium')
        self.routing['grades']['daily']['claude']['effort'] = 'high'
        self.assertEqual(self.pick(state=defect)['model'], 'claude-fable-5-2')
        self.assertEqual(self.pick(state=defect)['effort'], 'medium')
        self.assertIn('at the top of the ladder', self.pick('large', state=approach)['why'])
        self.routing['grades']['large']['claude']['effort'] = 'max'
        self.assertIn('at the top of the ladder', self.pick('large', state=defect)['why'])
        self.assertEqual(self.pick('large', state=defect)['effort'], 'max')
        self.assertEqual(self.pick('large', state={'rejections':[{'reason':'approach:'}, {'reason':'defect:'}]})['effort'], 'max')

    def test_provider(self):
        usage = {'providers':[self.provider('z'), self.provider('a'), self.provider('full',used=90), self.provider('stale',used=0,stale=True), self.provider('unknown',used=None), self.provider('other','openai',0)]}
        self.assertEqual(self.pick(usage=usage)['provider'], 'a')
        usage['providers'][0]['used_percent'] = 9
        self.assertEqual(self.pick(usage=usage)['provider'], 'z')
        self.assertIsNone(self.pick()['provider'])
        self.assertIn('no eligible', self.pick(usage={'providers':[]})['why'])

    def test_isolation_and_executor(self):
        self.assertEqual(self.pick(host=['worktree'])['isolation'], 'worktree')
        self.assertEqual(self.pick(host=[])['isolation'], 'shared')
        self.assertEqual(self.pick(kind='review', host=['worktree'])['isolation'], 'shared')
        self.assertEqual(self.pick(host=[])['executor'], 'inline')
        self.assertEqual(self.pick(host=['subagent'])['executor'], 'subagent')
        self.assertEqual(self.pick(host=['t3_delegate'])['executor'], 't3')
        self.assertEqual(self.pick(host=['t3_delegate','subagent'])['executor'], 'subagent')
        for grade in ('large','security'):
            self.assertEqual(self.pick(grade, host=['t3_delegate','subagent'])['executor'], 't3')
        self.assertEqual(self.pick(kind='review', host=['t3_delegate','subagent'])['executor'], 't3')
        self.assertEqual(self.pick('bulk', host=['workflow','subagent'])['executor'], 'workflow')
        self.assertEqual(self.pick('daily', host=['workflow','subagent'])['executor'], 'subagent')
        self.assertEqual(self.pick('bulk', host=['t3_delegate','workflow'])['executor'], 'workflow')
        self.assertEqual(self.pick(kind='review', state={'target_family':'claude'}, host=['t3_delegate','subagent'])['executor'], 't3')

    def test_pure(self):
        args = ({'kind':'work','grade':'daily'}, {'rejections':[{'reason':'defect:'}]}, ['subagent','worktree'], {'providers':[self.provider('a')]}, self.routing)
        before = copy.deepcopy(args)
        self.assertEqual(route.suggest(*args), route.suggest(*args))
        self.assertEqual(args, before)

    def test_usage_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(route.load_usage(root / 'absent'), {})
            self.assertEqual(route.load_usage(root), {'providers':[], 'warnings':[]})
            now = datetime.now(timezone.utc)
            base = dict(enabled=True, status='ready', auth={'status':'authenticated'}, driver='codex', usageLimits={'checkedAt':now.isoformat(), 'windows':[{'usedPercent':10,'resetsAt':now.isoformat()}, {'usedPercent':30}]})
            cases = {'ready':base, 'full':dict(base, usageLimits={'checkedAt':now.isoformat(),'windows':[{'usedPercent':90}]}), 'disabled':dict(base,enabled=False), 'busy':dict(base,status='busy'), 'unauth':dict(base,auth={'status':'expired'}), 'claude':dict(base,driver='claudeAgent',instanceId='chosen'), 'other':dict(base,driver='unknown'), 'stale':dict(base,usageLimits={'checkedAt':(now-timedelta(hours=7)).isoformat(),'windows':[{'usedPercent':0}]}), 'missing':dict(base,usageLimits={})}
            for name, data in cases.items():
                (root / (name+'.json')).write_text(json.dumps(data))
            for name, value in [('broken','{'), ('array','[]'), ('bad-window',json.dumps(dict(base,usageLimits={'windows':[None]}))), ('bad-date',json.dumps(dict(base,usageLimits={'checkedAt':'invalid'})))]:
                (root / (name+'.json')).write_text(value)
            result = route.load_usage(root)
            providers = {p['provider']:p for p in result['providers']}
            self.assertEqual(set(providers), {'ready','full','chosen','other','stale','missing'})
            self.assertEqual(providers['ready']['used_percent'],30)
            self.assertEqual(providers['chosen']['family'],'claude')
            self.assertEqual(providers['other']['family'],'other')
            self.assertTrue(providers['stale']['stale'])
            self.assertTrue(providers['missing']['stale'])
            self.assertFalse(providers['ready']['stale'])
            self.assertGreaterEqual(len(result['warnings']),6)
            self.assertEqual(self.pick(usage=result)['provider'], 'chosen')


if __name__ == '__main__':
    unittest.main()
