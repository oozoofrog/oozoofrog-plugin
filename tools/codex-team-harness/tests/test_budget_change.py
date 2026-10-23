"""Synthetic governance and crash tests; no project/native access."""
import copy,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'payload/team-coordination/scripts'));import harness as h
class BudgetChange(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.proof=self.root/'human';self.proof.write_text('Synthetic explicit human approval: project A 100000 to120000; preserve obligations')
  self.s=h.initial('project A');self.path=self.root/'state.json';self.approvals=self.root/'approvals.json'
  for member,role in [('owner','core'),('leader','leader'),('reviewer','reviewer')]:self.s=h.apply(self.s,dict(op='register',member=member,role=role,identity=str(self.proof)))
  self.s=h.apply(self.s,dict(op='assign',member='owner',task='work',purpose='same scope',context='keep FAIL'));self.s['tasks']['work']['reviews']=[{'verdict':'fail','evidence':h.ledger.evidence(str(self.proof))}];self.s['harness']['spent']=100000
 def tearDown(self):self.temp.cleanup()
 def request(self,**changes):
  e=dict(op='budget_change',request_id='approved-one',project='project A',project_root=str(self.root),requester='leader',source_sha256=h.digest(self.s),policy_hash=h.digest(h.effective_contract()),expected_budget=100000,new_budget=120000,reason='Human approved extra resource use only',human_approval=h.ledger.evidence(str(self.proof)),approvals=str(self.approvals));e.update(changes)
  proposal={k:v for k,v in e.items()if k!='approvals'}
  self.approvals.write_text(json.dumps({role:dict(member=role,request_sha256=h.digest(proposal),approved=True,safe_boundary=True,all_current_obligations_retained=True,human_approval_verified=True)for role in ('leader','reviewer')}));return e
 def execute(self,e):
  try:self.s=h.apply(self.s,e,self.root)
  except h.Invalid as exc:
   if str(exc)=='Unknown harness operation':self.fail('Missing audited budget_change API')
   raise
 def test_exact_change_preserves_all_business_records_and_invalidates_ack(self):
  self.s['harness']['profiles']['owner']['ack']={'old':True};before=copy.deepcopy(self.s);self.execute(self.request());self.assertEqual(120000,self.s['harness']['budget']);self.assertEqual(before['tasks'],self.s['tasks']);self.assertEqual(before['harness']['runs'],self.s['harness']['runs']);self.assertEqual(100000,self.s['harness']['spent']);self.assertEqual(before['history'],self.s['history'][:-1]);self.assertNotIn('ack',self.s['harness']['profiles']['owner']);self.assertEqual(100000,h.initial('other')['harness']['budget'])
 def test_stale_wrong_project_limits_contract_or_actor_refused(self):
  for change in ({'source_sha256':'0'*64},{'project':'other'},{'expected_budget':99999},{'new_budget':True},{'new_budget':99999},{'policy_hash':'0'*64},{'requester':'owner'}):
   with self.subTest(change=change),self.assertRaises(h.Invalid):h.apply(self.s,self.request(**change),self.root)
 def test_approval_binding_independence_and_human_bytes(self):
  e=self.request();data=json.loads(self.approvals.read_text())
  for field,value in [('request_sha256','0'*64),('safe_boundary',False),('human_approval_verified',False),('member','leader')]:
   wrong=copy.deepcopy(data);wrong['reviewer'][field]=value;self.approvals.write_text(json.dumps(wrong))
   with self.assertRaises(h.Invalid):h.apply(self.s,e,self.root)
  self.approvals.write_text(json.dumps(data));self.proof.write_text('changed human approval')
  with self.assertRaises(h.Invalid):h.apply(self.s,e,self.root)
 def test_quiescence_blocks_runs_controls_and_handoffs(self):
  original=copy.deepcopy(self.s)
  for key,value in [('runs',{'x':{'state':'active'}}),('runs',{'x':{'state':'uncertain'}}),('controls',{'x':{'state':'configuration_pending_turn'}}),('handoffs',{'x':{'state':'source_paused'}})]:
   self.s=copy.deepcopy(original);self.s['harness'][key]=value
   with self.subTest(key=key,value=value),self.assertRaises(h.Invalid):h.apply(self.s,self.request(),self.root)
 def test_duplicate_readback_conflict_and_receipt_after_later_change(self):
  e=self.request();self.execute(e);self.s=h.apply(self.s,dict(op='change',instruction='later'));current=copy.deepcopy(self.s);self.assertEqual(current,h.apply(self.s,e,self.root));self.assertEqual(120000,h.budget_change_receipt(self.s,e['request_id'])['original_transition']['budget'])
  with self.assertRaises(h.Invalid):h.apply(self.s,dict(e,new_budget=130000),self.root)
 def test_policy_refresh_preserves_approved_exception(self):
  self.execute(self.request());self.s=h.apply(self.s,dict(op='policy_refresh',reason='same approved budget'));self.assertEqual(120000,self.s['harness']['budget'])
 def test_checkpoint_migration_preserves_override_spent_reviews_and_approval_bytes(self):
  import checkpoints as c
  self.execute(self.request());before=copy.deepcopy(self.s);self.s['harness']['policy_hash']='old-contract';h.save(self.path,self.s)
  view=dict(historical_constraints={},historical_decisions={},constraint_indices=[],decision_indices=[],historical_summary='Synthetic preserved history',remaining_work=['Keep existing FAIL and scope'],task_contexts={'work':'Same task and failed review'})
  candidate=c.prepare(self.path,'budget-preserved',view,[str(self.proof)]);proposal=json.loads(candidate.read_text());approved=self.root/'checkpoint-approval';approved.write_text(json.dumps({role:dict(member=role,proposal_sha256=h.digest(proposal),source_sha256=proposal['source_sha256'],target_policy_hash=proposal['target_policy_hash'],approved=True,safe_boundary=True,all_current_obligations_retained=True)for role in ('leader','reviewer')}))
  after=h.transaction(self.path,dict(op='checkpoint_commit',candidate=str(candidate),approvals=str(approved),policy_refresh=True,reason='Synthetic contract adoption'))
  self.assertEqual(120000,after['harness']['budget']);self.assertEqual(100000,after['harness']['spent']);self.assertEqual(before['tasks'],after['tasks']);self.assertEqual(before['harness']['budget_changes'],after['harness']['budget_changes']);self.assertEqual({'budget':120000,'spent':100000,'meaning':'reservation ledger, not billing'},h.packet(after,'owner')['accounting'])
 def test_altered_retained_approval_cannot_grant_migration_ceiling(self):
  self.execute(self.request());self.s['harness']['budget_changes']['approved-one']['original_transition']['budget']=140000;self.s['harness']['budget']=140000
  with self.assertRaises(h.Invalid):h.apply(self.s,dict(op='policy_refresh',reason='invalid forged ceiling'))
 def test_atomic_pre_and_post_rename_failures(self):
  e=self.request();h.save(self.path,self.s);original=self.path.read_bytes()
  with patch.object(h.os,'replace',side_effect=OSError('before rename')):
   with self.assertRaises(OSError):h.transaction(self.path,e)
  self.assertEqual(original,self.path.read_bytes());real=h.os.fsync;calls=[]
  def fail_second(fd):
   calls.append(fd)
   if len(calls)==2:raise OSError('after rename')
   return real(fd)
  with patch.object(h.os,'fsync',side_effect=fail_second):
   with self.assertRaises(OSError):h.transaction(self.path,e)
  committed=self.path.read_bytes()
  with patch.object(h,'save',side_effect=AssertionError('duplicate write')):h.transaction(self.path,e)
  self.assertEqual(committed,self.path.read_bytes())
if __name__=='__main__':unittest.main()
