import json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'payload/team-coordination/scripts'))
import harness as h,managed_run as m
class Adapter(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.path=self.root/'state.json';proof=self.root/'proof';proof.write_text('synthetic')
  s=h.initial('probe');
  for e in [{'op':'register','member':'exec','role':'core','identity':str(proof)},{'op':'assign','task':'a','member':'exec','purpose':'inspect','context':'sample'},{'op':'claim','task':'a','paths':[str(self.root/'sample')]}]:s=h.apply(s,e)
  p=h.packet(s,'exec');s=h.apply(s,{'op':'ack','member':'exec','revision':p['revision'],'epoch':p['epoch'],'digest':h.digest(p)});h.save(self.path,s)
 def tearDown(self):self.tmp.cleanup()
 def run_fake(self,mode):
  log=self.root/'methods';result=m.run(self.path,'exec','a','one',[sys.executable,'-I','-S','-B',str(ROOT/'tests/fake_server.py'),mode,str(log)],self.root,5);return result
 def test_observed_fake_receipt_usage(self):
  r=self.run_fake('ok');self.assertEqual(r['thread_id'],'synthetic-thread');s=m.read(self.path);self.assertEqual(s['harness']['runs']['one']['reported_usage'],5)
 def test_second_terminal_run_can_rebind_with_fresh_ack(self):
  self.run_fake('ok');s=m.read(self.path);p=h.packet(s,'exec');h.transaction(self.path,{'op':'ack','member':'exec','revision':p['revision'],'epoch':p['epoch'],'digest':h.digest(p)})
  result=m.run(self.path,'exec','a','two',[sys.executable,'-I','-S','-B',str(ROOT/'tests/fake_server.py'),'ok',str(self.root/'second-methods')],self.root,5)
  self.assertEqual('completed',result['status']);self.assertEqual(5,m.read(self.path)['harness']['runs']['two']['reported_usage'])
 def test_mismatch_never_turn_start(self):
  with self.assertRaises(h.Invalid):self.run_fake('mismatch')
  self.assertNotIn('turn/start',(self.root/'methods').read_text());self.assertEqual(m.read(self.path)['harness']['runs']['one']['state'],'not_executed')
 def test_disconnect_uncertain_and_held(self):
  with self.assertRaises(ConnectionError):self.run_fake('disconnect')
  s=m.read(self.path);self.assertEqual(s['harness']['runs']['one']['state'],'uncertain');self.assertTrue(s['tasks']['a']['paths'])
 def test_unknown_request_aborts_uncertain(self):
  with self.assertRaises(h.Invalid):self.run_fake('request')
  self.assertEqual(m.read(self.path)['harness']['runs']['one']['state'],'uncertain')
 def test_revision_dispatch_recheck(self):
  h.transaction(self.path,{'op':'begin','member':'exec','task':'a','run':'one'});h.transaction(self.path,{'op':'change','instruction':'new instruction','decisions':['keep rationale']})
  class NoSend:
   def send(self,x):raise AssertionError('must not send')
  with self.assertRaises(h.Invalid):m.dispatch(NoSend(),self.path,'one','thread','prompt','gpt-6.1-sol')
 def assert_standard_envelopes(self):
  requests=[json.loads(line)for line in (self.root/'methods.rpc.jsonl').read_text().splitlines()]
  start=next(x for x in requests if x.get('method')=='thread/start')
  turn=next(x for x in requests if x.get('method')=='turn/start')
  self.assertNotIn('serviceTier',start['params'])
  self.assertEqual({'id':turn['id'],'method':'turn/start','params':{'threadId':'synthetic-thread','model':'gpt-6.1-sol','input':turn['params']['input'],'serviceTierForTurn':'default'}},turn)
  state=m.read(self.path);self.assertEqual('unavailable',state['harness']['sessions']['exec']['runtime_observed']['status'])
 def test_priority_only_catalogue_allows_explicit_standard(self):
  self.assertEqual('completed',self.run_fake('normal-absent')['status']);self.assert_standard_envelopes()
  self.assertEqual('unavailable',m.read(self.path)['harness']['sessions']['exec']['service_tier_observed']['status'])
 def test_empty_additional_tiers_allow_explicit_standard(self):
  self.assertEqual('completed',self.run_fake('empty-tiers')['status']);self.assert_standard_envelopes()
 def test_turn_local_standard_does_not_inherit_observed_fast(self):
  self.assertEqual('completed',self.run_fake('inherited-fast')['status']);self.assert_standard_envelopes()
  self.assertEqual('priority',m.read(self.path)['harness']['sessions']['exec']['service_tier_observed']['wire_service_tier'])
if __name__=='__main__':unittest.main()
