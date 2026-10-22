import importlib.util,json,tempfile,unittest,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'payload/team-coordination/scripts'))
import harness as h

class Gates(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.s=h.initial('sample',100,1)
  self.proof=self.root/'identity';self.proof.write_text('synthetic tool identity fixture')
  self.member='exec'
  self.ev('register',member=self.member,role='core',identity=str(self.proof))
  self.ev('assign',task='a',member=self.member,purpose='change sample',context='local only')
  self.ev('claim',task='a',paths=[str(self.root/'sample')])
 def tearDown(self):self.tmp.cleanup()
 def ev(self,op,**kw):self.s=h.apply(self.s,dict(op=op,**kw));return self.s
 def ack(self):
  p=h.packet(self.s,self.member);self.ev('ack',member=self.member,revision=p['revision'],epoch=p['epoch'],digest=h.digest(p))
 def begin(self,run='one',**kw):
  return self.ev('begin',task='a',member=self.member,run=run,reserve=20,**kw)
 def test_stale_revision_and_ack(self):
  self.ack();self.ev('change',instruction='preserve sentinel',decisions=['do not overwrite'])
  with self.assertRaises(h.Invalid):self.begin()
  self.ack();self.begin()
 def test_resume_compaction_invalidates(self):
  self.ack()
  for reason in ['resume','compaction']:
   self.ev('boundary',member=self.member,reason=reason)
   with self.assertRaises(h.Invalid):self.begin()
   self.ack()
 def test_path_alias_conflict(self):
  (self.root/'link').symlink_to(self.root/'sample')
  self.ev('assign',task='b',member=self.member,purpose='other',context='x')
  with self.assertRaises(h.Invalid):self.ev('claim',task='b',paths=[str(self.root/'link')])
 def test_duplicate_and_uncertain_no_retry(self):
  self.ack();self.begin()
  with self.assertRaises(h.Invalid):self.begin()
  self.ev('finish',run='one',outcome='uncertain',evidence='connection lost')
  with self.assertRaises(h.Invalid):self.begin('two')
  self.ev('reconcile',run='one',outcome='not_executed',evidence='server read observed no active turn')
  self.ack();self.begin('two')
 def test_budget_exhaustion_and_missing_usage(self):
  self.ack();self.begin();self.ev('finish',run='one',outcome='completed',evidence='observed')
  self.assertEqual(self.s['harness']['spent'],20)
  with self.assertRaises(h.Invalid):self.ev('begin',task='a',member='exec',run='two',reserve=81)
 def test_support_explicit_corrected_model(self):
  self.ev('register',member='support',role='support',identity=str(self.proof))
  self.ev('assign',task='s',member='support',purpose='lookup',context='x')
  self.ev('claim',task='s',paths=[str(self.root/'else')])
  p=h.packet(self.s,'support');self.ev('ack',member='support',revision=p['revision'],epoch=p['epoch'],digest=h.digest(p))
  self.ev('begin',task='s',member='support',run='s',reserve=1)
  self.assertEqual(self.s['harness']['runs']['s']['model'],'gpt-6-luna')
 def test_context_overflow_not_truncated(self):
  self.ev('change',instruction='x'*70000,decisions=['critical rationale'])
  with self.assertRaises(h.Invalid):h.packet(self.s,'exec')
 def test_review_stop_and_independence(self):
  with self.assertRaises(h.Invalid):self.ev('review',task='a',reviewer='exec',verdict='pass',evidence='x')
  self.ev('register',member='reviewer',role='reviewer',identity=str(self.proof))
  for _ in range(2):
   self.ev('handoff',task='a',artifacts=[str(self.proof)]);self.ev('review',task='a',reviewer='reviewer',verdict='fail',evidence=str(self.proof))
  self.ev('handoff',task='a',artifacts=[str(self.proof)])
  with self.assertRaises(h.Invalid):self.ev('review',task='a',reviewer='reviewer',verdict='pass',evidence='third')
 def test_single_authority_legacy_and_project_preserved(self):
  sentinel=self.root/'sentinel';sentinel.write_bytes(b'original\x00bytes')
  self.assertIn('members',self.s);self.assertIn('tasks',self.s);self.assertNotIn('tasks',self.s['harness'])
  path=self.root/'.codex-team/state.json';h.save(path,self.s)
  self.assertEqual(sentinel.read_bytes(),b'original\x00bytes')
 def test_accept_requires_fresh_review(self):
  self.ev('register',member='reviewer',role='reviewer',identity=str(self.proof))
  artifact=self.root/'artifact';artifact.write_text('first')
  self.ev('handoff',task='a',artifacts=[str(artifact)])
  self.ev('review',task='a',reviewer='reviewer',verdict='pass',evidence=str(self.proof))
  artifact.write_text('changed')
  with self.assertRaises(h.Invalid):self.ev('accept',task='a')
 def test_concurrency_and_release(self):
  self.ack();self.begin()
  self.ev('assign',task='b',member='exec',purpose='b',context='b');self.ev('claim',task='b',paths=[str(self.root/'other')]);self.ack()
  with self.assertRaises(h.Invalid):self.ev('begin',task='b',member='exec',run='two',reserve=1)
  with self.assertRaises(h.Invalid):self.ev('release',task='a',safe_boundary=True)
  self.ev('finish',run='one',outcome='completed',evidence='observed');self.ev('release',task='a',safe_boundary=True)
  self.assertEqual(self.s['tasks']['a']['paths'],[])
 def test_role_contract_change_invalidates_ack(self):
  self.ack()
  from unittest.mock import patch
  original=h.effective_contract();changed=json.loads(json.dumps(original));changed['roles']['core']+=' New critical constraint.'
  with patch.object(h,'effective_contract',return_value=changed):
   with self.assertRaises(h.Invalid):self.begin()
   self.ev('policy_refresh',reason='Leader approved changed role constraint');self.ack();self.begin()
   self.assertIn('New critical constraint.',h.packet(self.s,'exec')['role_contract'])
 def test_concurrent_init_preserves_winner(self):
  from concurrent.futures import ThreadPoolExecutor
  path=self.root/'race/state.json'
  def attempt(goal):
   try:h.initialize(path,goal);return goal
   except h.Invalid:return None
  with ThreadPoolExecutor(max_workers=2)as pool:results=list(pool.map(attempt,['first','second']))
  self.assertEqual(sum(x is not None for x in results),1)
  self.assertEqual(json.loads(path.read_text())['harness']['goal'],next(x for x in results if x is not None))
 def test_policy_limits_and_orphan_recovery(self):
  from unittest.mock import patch
  changed=h.effective_contract();changed['policy']['limits']['concurrency']=2
  with patch.object(h,'effective_contract',return_value=changed):self.assertEqual(h.initial('new')['harness']['concurrency'],2)
  self.ack();self.begin()
  with self.assertRaises(h.Invalid):self.ev('policy_refresh',reason='blocked while active')
  self.ev('mark_uncertain',run='one',evidence='Supported process check: wrapper ended; server terminal status unknown')
  with self.assertRaises(h.Invalid):self.ev('policy_refresh',reason='blocked while uncertain')
  self.ev('reconcile',run='one',outcome='failed',evidence='Supported server receipt: terminal failed');self.ev('policy_refresh',reason='now safe')
 def test_dispatch_preserves_exact_ack_packet(self):
  self.ack();acked=h.digest(h.packet(self.s,'exec'));self.begin()
  self.assertEqual(h.digest(self.s['harness']['runs']['one']['packet']),acked)
  with self.assertRaises(h.Invalid):self.ev('claim',task='a',paths=[str(self.root/'new')])
 def test_no_silent_fallback_and_stale_policy(self):
  self.ack()
  from unittest.mock import patch
  changed=h.effective_contract();changed['policy']['roles']['support']['model']='gpt-other'
  with patch.object(h,'effective_contract',return_value=changed):
   with self.assertRaises(h.Invalid):self.begin()
  with self.assertRaises(h.Invalid):h.check_model('gpt-6-luna',[{'model':'gpt-6.1-sol'}],{'model':'gpt-6-luna'})
 def test_catalog_and_receipt(self):
  with self.assertRaises(h.Invalid):h.check_model('gpt-6.1-sol',[{'model':'gpt-6-luna'}],{'model':'gpt-6.1-sol'})
  with self.assertRaises(h.Invalid):h.check_model('gpt-6.1-sol',[{'model':'gpt-6.1-sol'}],{'model':'gpt-6-luna'})
  h.check_model('gpt-6.1-sol',[{'model':'gpt-6.1-sol'}],{'model':'gpt-6.1-sol'})
if __name__=='__main__':unittest.main()
