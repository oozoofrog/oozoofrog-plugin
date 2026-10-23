"""Synthetic state-only rework; no native sessions or project operations."""
import copy,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'payload/team-coordination/scripts'));import harness as h
class Rework(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name).resolve();self.proof=self.root/'evidence';self.proof.write_text('Synthetic failed review and leader decision');self.path=self.root/'state.json';self.s=h.initial('same owner correction',100,1)
  for member,role in [('owner','core'),('reviewer','reviewer'),('leader','leader')]:self.ev('register',member=member,role=role,identity=str(self.proof))
  self.ev('assign',member='owner',task='sample',purpose='correct within original scope',context='sentinel');self.ev('claim',task='sample',paths=[str(self.root/'sample.txt')]);self.ack();self.ev('begin',member='owner',task='sample',run='first',reserve=20);self.ev('finish',run='first',outcome='completed',evidence='actual synthetic completion',usage=5);self.ev('handoff',task='sample',artifacts=[str(self.proof)]);self.ev('review',task='sample',reviewer='reviewer',verdict='fail',evidence=str(self.proof));self.ev('handoff',task='sample',artifacts=[str(self.proof)]);self.ack()
 def tearDown(self):self.temp.cleanup()
 def ev(self,op,**values):self.s=h.apply(self.s,dict(op=op,**values));return self.s
 def ack(self):
  packet=h.packet(self.s,'owner');self.ev('ack',member='owner',revision=packet['revision'],epoch=packet['epoch'],digest=h.digest(packet))
 def request(self,**values):return dict({'op':'rework','request_id':'fix-one','task':'sample','member':'owner','requester':'leader','source_sha256':h.digest(self.s),'reason':'Address latest failed review without changing scope','evidence':str(self.proof)},**values)
 def execute(self,event):
  try:self.s=h.apply(self.s,event)
  except h.Invalid as exc:
   if str(exc)=='Unknown harness operation':self.fail('Missing atomic same-owner rework operation')
   raise
  return self.s
 def test_preserves_claims_reviews_runs_ledger_and_history_then_requires_fresh_ack(self):
  before=copy.deepcopy(self.s);self.execute(self.request());expected=copy.deepcopy(before['tasks']['sample']);expected['state']='assigned';self.assertEqual(expected,self.s['tasks']['sample']);self.assertEqual(before['harness']['runs'],self.s['harness']['runs']);self.assertEqual(20,self.s['harness']['spent']);self.assertEqual(100,self.s['harness']['budget']);self.assertEqual(2,self.s['harness']['review_limit']);self.assertEqual(before['history'],self.s['history'][:-1]);self.assertEqual(1,len(self.s['tasks']['sample']['reviews']));self.assertNotIn('ack',self.s['harness']['profiles']['owner'])
  with self.assertRaises(h.Invalid):self.ev('begin',member='owner',task='sample',run='second',reserve=20)
  with self.assertRaises(h.Invalid):self.ev('review',task='sample',reviewer='reviewer',verdict='pass',evidence=str(self.proof))
  with self.assertRaises(h.Invalid):self.ev('accept',task='sample')
  self.ack();self.ev('begin',member='owner',task='sample',run='second',reserve=20);self.assertEqual('active',self.s['harness']['runs']['second']['state'])
 def test_only_failed_ready_state_and_remaining_review_are_legal(self):
  original=copy.deepcopy(self.s)
  for state in ('assigned','running','reviewed','accepted'):
   self.s=copy.deepcopy(original);self.s['tasks']['sample']['state']=state
   with self.assertRaises(h.Invalid):self.ev(**self.request())
  for reviews in ([],[dict(original['tasks']['sample']['reviews'][0],verdict='pass')],original['tasks']['sample']['reviews']*2):
   self.s=copy.deepcopy(original);self.s['tasks']['sample']['reviews']=reviews
   with self.assertRaises(h.Invalid):self.ev(**self.request())
 def test_wrong_owner_requester_stale_state_and_evidence_refused(self):
  for values in ({'member':'reviewer'},{'requester':'owner'},{'source_sha256':'0'*64},{'reason':''},{'evidence':str(self.root/'missing')}):
   with self.assertRaises((h.Invalid,OSError)):self.ev(**self.request(**values))
  event=self.request();self.ev('register',member='extra',role='support',identity=str(self.proof))
  with self.assertRaises(h.Invalid):self.ev(**event)
 def test_all_project_active_uncertain_and_pending_controls_refused(self):
  for state in ('active','uncertain'):
   self.s['harness']['runs']['elsewhere']={'task':'other','member':'other','state':state}
   with self.assertRaises(h.Invalid):self.ev(**self.request())
  self.s['harness']['runs'].pop('elsewhere');self.s['harness']['controls']={'pending':{'state':'outcome_unknown'}}
  with self.assertRaises(h.Invalid):self.ev(**self.request())
 def test_duplicate_is_unchanged_readback_even_after_later_activity(self):
  event=self.request();self.execute(event);self.ack();self.ev('begin',member='owner',task='sample',run='second',reserve=20);current=copy.deepcopy(self.s);self.assertEqual(current,h.apply(self.s,event));self.assertEqual(current,self.s)
  with self.assertRaises(h.Invalid):h.apply(self.s,dict(event,reason='different payload'))
 def test_fresh_request_cannot_reuse_old_fail_and_duplicate_receipt_is_historical(self):
  event=self.request();self.execute(event);self.ev('handoff',task='sample',artifacts=[str(self.proof)])
  with self.assertRaises(h.Invalid):self.ev(**self.request(request_id='another-id'))
  receipt=h.rework_receipt(self.s,event['request_id']);self.assertEqual('assigned',receipt['original_transition']['state']);self.assertEqual('ready_for_review',receipt['current_observation']['state']);self.assertEqual(1,len(self.s['harness']['reworks']))
 def test_before_rename_failure_keeps_original_bytes_then_single_retry(self):
  h.save(self.path,self.s);event=self.request();original=self.path.read_bytes()
  with patch.object(h.os,'replace',side_effect=OSError('injected before rename')):
   with self.assertRaises(OSError):h.transaction(self.path,event)
  self.assertEqual(original,self.path.read_bytes());self.assertEqual([],list(self.root.glob('.state-*')));after=h.transaction(self.path,event);self.assertEqual('assigned',after['tasks']['sample']['state']);self.assertEqual(1,len(after['harness']['reworks']))
 def test_after_rename_failure_reconciles_committed_id_without_rewrite(self):
  h.save(self.path,self.s);event=self.request();original=h.os.fsync;calls=[]
  def fail_directory(fd):
   calls.append(fd)
   if len(calls)==2:raise OSError('injected after rename directory durability unknown')
   return original(fd)
  with patch.object(h.os,'fsync',side_effect=fail_directory):
   with self.assertRaises(OSError):h.transaction(self.path,event)
  committed=self.path.read_bytes();state=json.loads(committed);self.assertEqual('assigned',state['tasks']['sample']['state']);self.assertIn(event['request_id'],state['harness']['reworks'])
  with patch.object(h,'save',side_effect=AssertionError('idempotent readback must not save')):self.assertEqual(state,h.transaction(self.path,event))
  self.assertEqual(committed,self.path.read_bytes())
if __name__=='__main__':unittest.main()
