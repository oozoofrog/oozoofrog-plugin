"""Synthetic original-failure diagnostics; no business-project access."""
import copy,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'payload/team-coordination/scripts'));import harness as h
class Diagnostics(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name).resolve();self.proof=self.root/'proof';self.proof.write_text('Synthetic actual failure and explicit bounded diagnostic authorization');self.approvals=self.root/'approval.json';self.path=self.root/'state.json';self.s=h.initial('original failure',100,1)
  for member,role in [('owner','core'),('leader','leader'),('reviewer','reviewer')]:self.ev('register',member=member,role=role,identity=str(self.proof))
  self.ev('assign',task='original',member='owner',purpose='original deliverable',context='retain failed finding');self.ev('claim',task='original',paths=[str(self.root/'collector.py')]);self.ack();self.ev('begin',task='original',member='owner',run='initial',reserve=95);self.ev('finish',run='initial',outcome='completed',evidence='synthetic terminal');self.ev('handoff',task='original',artifacts=[str(self.proof)]);self.ev('review',task='original',reviewer='reviewer',verdict='fail',evidence=str(self.proof));self.ev('handoff',task='original',artifacts=[str(self.proof)])
  self.ev('rework',request_id='consumed-original-failure',task='original',member='owner',requester='leader',source_sha256=h.digest(self.s),reason='original correction',evidence=str(self.proof));self.ev('handoff',task='original',artifacts=[str(self.proof)])
 def tearDown(self):self.temp.cleanup()
 def ev(self,op,**kw):self.s=h.apply(self.s,dict(op=op,**kw),self.root);return self.s
 def ack(self):
  p=h.packet(self.s,'owner');self.ev('ack',member='owner',revision=p['revision'],epoch=p['epoch'],digest=h.digest(p));return p
 def request(self,**changes):
  t=self.s['tasks']['original'];reviews=t['reviews'];failure=h.digest({'task':'original','index':len(reviews)-1,'review':reviews[-1]})
  provenance=h.digest({'task':t,'reworks':{k:v for k,v in self.s['harness'].get('reworks',{}).items()if v['original_transition']['task']=='original'}})
  e=dict(op='diagnostic_grant',request_id='one-cycle',project='original failure',project_root=str(self.root),requester='leader',task='original',member='owner',source_sha256=h.digest(self.s),policy_hash=h.digest(h.effective_contract()),failed_review_digest=failure,provenance_sha256=provenance,evidence_goal='Capture six actual coordinates and clipping intermediates',modification_paths=[str(self.root/'collector.py')],max_reserve=5,human_approval=h.ledger.evidence(str(self.proof)),approvals=str(self.approvals));e.update(changes)
  self.approvals.write_text(json.dumps({role:dict(member=role,request_sha256=h.digest({k:v for k,v in e.items()if k!='approvals'}),approved=True,safe_boundary=True,all_current_obligations_retained=True,human_approval_verified=True,diagnostic_only=True)for role in ('leader','reviewer')}));return e
 def grant(self,**kw):
  e=self.request(**kw);self.s=h.apply(self.s,e,self.root);return e
 def begin(self,**kw):
  e=dict(task='original',member='owner',run='diagnosis',reserve=5,diagnostic_request_id='one-cycle');e.update(kw);return self.ev('begin',**e)
 def test_original_records_retained_fresh_ack_gate_budget_and_terminal_stop(self):
  before=copy.deepcopy(self.s);self.grant();self.assertEqual(before['tasks'],self.s['tasks']);self.assertEqual(before['harness']['runs'],self.s['harness']['runs']);self.assertEqual(95,self.s['harness']['spent']);self.assertEqual(before['history'],self.s['history'][:-1])
  with self.assertRaises(h.Invalid):self.begin()
  packet=self.ack();self.assertEqual(5,packet['diagnostics']['one-cycle']['request']['max_reserve']);self.begin();self.ev('finish',run='diagnosis',outcome='completed',evidence='synthetic six measured points',usage=2);self.assertEqual(100,self.s['harness']['spent']);self.assertEqual(before['tasks'],self.s['tasks']);self.assertEqual('closed',self.s['harness']['diagnostics']['one-cycle']['state']);self.assertEqual('synthetic six measured points',self.s['harness']['diagnostics']['one-cycle']['result']['evidence'])
  self.ack()
  for event in [dict(op='begin',task='original',member='owner',run='retry',reserve=1),dict(op='handoff',task='original',artifacts=[str(self.proof)]),dict(op='review',task='original',reviewer='reviewer',verdict='pass',evidence=str(self.proof)),dict(op='accept',task='original'),dict(op='release',task='original',safe_boundary=True),dict(op='reassign',task='original',member='owner'),dict(op='claim',task='original',paths=[str(self.root/'other')]),dict(op='control_handoff_prepare',tasks=['original']),dict(op='rework',task='original')]:
   with self.subTest(event=event),self.assertRaises(h.Invalid):h.apply(self.s,event,self.root)
  with self.assertRaises(h.Invalid):self.begin(run='second')
  with self.assertRaises(h.Invalid):self.grant(request_id='fresh-id')
 def test_scope_cas_owner_failure_provenance_and_bound_checks(self):
  for changes in [{'source_sha256':'bad'},{'project':'other'},{'project_root':str(self.root/'other')},{'policy_hash':'bad'},{'member':'reviewer'},{'requester':'owner'},{'failed_review_digest':'bad'},{'provenance_sha256':'bad'},{'evidence_goal':''},{'modification_paths':[]},{'modification_paths':[str(self.root)]},{'max_reserve':6},{'max_reserve':True}]:
   with self.subTest(changes=changes),self.assertRaises(h.Invalid):h.apply(self.s,self.request(**changes),self.root)
  alias=self.root/'alias';alias.symlink_to(self.root/'outside');
  with self.assertRaises(h.Invalid):h.apply(self.s,self.request(modification_paths=[str(alias)]),self.root)
 def test_approval_binding_and_capture(self):
  e=self.request();a=json.loads(self.approvals.read_text());a['reviewer']['diagnostic_only']=False;self.approvals.write_text(json.dumps(a))
  with self.assertRaises(h.Invalid):h.apply(self.s,e,self.root)
 def test_scope_reviewer_cannot_share_execution_owner_runtime(self):
  self.s['members']['reviewer']['runtime_id_claim']=self.s['members']['owner']['runtime_id_claim']
  with self.assertRaises(h.Invalid):self.grant()
  e=self.request();self.proof.write_text('changed authorization')
  with self.assertRaises(h.Invalid):h.apply(self.s,e,self.root)
 def test_idempotent_receipt_copied_bytes_and_no_fresh_id_retry(self):
  e=self.grant();record=copy.deepcopy(self.s['harness']['diagnostics']['one-cycle']);self.ack();self.begin();current=copy.deepcopy(self.s);self.assertEqual(current,h.apply(self.s,e,self.root));self.assertEqual(record['human_approval_bytes_base64'],self.s['harness']['diagnostics']['one-cycle']['human_approval_bytes_base64'])
  with self.assertRaises(h.Invalid):h.apply(self.s,dict(e,evidence_goal='other'),self.root)
  receipt=h.diagnostic_receipt(self.s,'one-cycle');self.assertEqual('granted',receipt['original_transition']['state']);self.assertEqual('active',receipt['current_observation']['state'])
 def test_uncertain_requires_explicit_recovery_and_does_not_reopen_cycle(self):
  self.grant();self.ack();self.begin();self.ev('finish',run='diagnosis',outcome='uncertain',evidence='synthetic transport lost');self.assertEqual('uncertain',self.s['harness']['diagnostics']['one-cycle']['state']);self.assertEqual(95,self.s['harness']['spent']);self.ack()
  with self.assertRaises(h.Invalid):self.begin(run='second')
  self.ev('reconcile',run='diagnosis',outcome='failed',evidence='observed terminal diagnostic error');self.assertEqual(100,self.s['harness']['spent']);self.assertEqual('ready_for_review',self.s['tasks']['original']['state']);self.assertEqual('closed',self.s['harness']['diagnostics']['one-cycle']['state'])
 def test_not_executed_consumes_cycle_without_charge(self):
  self.grant();self.ack();self.begin();self.ev('finish',run='diagnosis',outcome='not_executed',evidence='no dispatch');self.assertEqual(95,self.s['harness']['spent']);self.ack()
  with self.assertRaises(h.Invalid):self.begin(run='again')
 def test_quiescence_and_grant_run_match(self):
  self.s['harness']['runs']['other']={'state':'uncertain'}
  with self.assertRaises(h.Invalid):self.grant()
  self.s['harness']['runs'].pop('other');self.grant();self.ack()
  for kw in [{'reserve':6},{'diagnostic_request_id':'unknown'},{'member':'reviewer'}]:
   with self.subTest(kw=kw),self.assertRaises(h.Invalid):self.begin(**kw)
 def test_atomic_failure_replay_reads_committed_receipt(self):
  e=self.request();h.save(self.path,self.s);old=self.path.read_bytes()
  with patch.object(h.os,'replace',side_effect=OSError('before rename')):
   with self.assertRaises(OSError):h.transaction(self.path,e)
  self.assertEqual(old,self.path.read_bytes());real=h.os.fsync;calls=[]
  def fail_directory(fd):
   calls.append(fd)
   if len(calls)==2:raise OSError('durability uncertain after rename')
   return real(fd)
  with patch.object(h.os,'fsync',side_effect=fail_directory):
   with self.assertRaises(OSError):h.transaction(self.path,e)
  current=self.path.read_bytes()
  with patch.object(h,'save',side_effect=AssertionError('duplicate write')):h.transaction(self.path,e)
  self.assertEqual(current,self.path.read_bytes())
 def test_stored_control_transfer_and_alias_mutation_cannot_bypass(self):
  self.grant();self.s['harness']['handoffs']={'old':{'tasks':['original']}}
  with self.assertRaises(h.Invalid):self.ev('control_transfer',handoff='old')
  self.s['harness']['handoffs']={};self.ack();(self.root/'collector.py').symlink_to(self.root/'outside')
  with self.assertRaises(h.Invalid):self.begin()
 def test_retained_rework_and_diagnostic_replay_are_readback_after_grant_or_path_drift(self):
  old=next(item['event']for item in self.s['history']if item['event']['op']=='rework');event=self.grant();h.save(self.path,self.s);current=self.path.read_bytes()
  with patch.object(h,'save',side_effect=AssertionError('historical receipt rewrite')):self.assertEqual(self.s,h.transaction(self.path,old))
  (self.root/'collector.py').symlink_to(self.root/'outside')
  with patch.object(h,'save',side_effect=AssertionError('historical receipt rewrite')):
   self.assertEqual(self.s,h.transaction(self.path,old));self.assertEqual(self.s,h.transaction(self.path,event))
  self.assertEqual(current,self.path.read_bytes())
  with self.assertRaises(h.Invalid):self.ev('change',instruction='mutation after path drift')
 def test_checkpoint_and_policy_refresh_retain_guard_and_packet_obligations(self):
  import checkpoints as c
  self.grant();original=copy.deepcopy(self.s['harness']['diagnostics']);self.ev('policy_refresh',reason='same exact diagnostic contract');self.assertEqual(original,self.s['harness']['diagnostics']);h.save(self.path,self.s)
  view=dict(historical_constraints={},historical_decisions={},constraint_indices=[],decision_indices=[],historical_summary='Synthetic retained diagnostic history',remaining_work=['One diagnostic run then stop'],task_contexts={'original':'Retain original failure and single diagnostic restriction'})
  candidate=c.prepare(self.path,'diagnostic-sample',view,[str(self.proof)]);proposal=json.loads(candidate.read_text());approval=self.root/'checkpoint-approval';approval.write_text(json.dumps({role:dict(member=role,proposal_sha256=h.digest(proposal),source_sha256=proposal['source_sha256'],target_policy_hash=proposal['target_policy_hash'],approved=True,safe_boundary=True,all_current_obligations_retained=True)for role in ('leader','reviewer')}))
  self.s=h.transaction(self.path,dict(op='checkpoint_commit',candidate=str(candidate),approvals=str(approval),reason='Synthetic compact view'))
  packet=self.ack();self.assertEqual(original,self.s['harness']['diagnostics']);self.assertEqual('fail',packet['diagnostics']['one-cycle']['original_task']['reviews'][0]['verdict']);self.assertEqual(1,len(packet['diagnostics']['one-cycle']['original_task']['reviews']));self.assertEqual(2,self.s['harness']['review_limit']);self.begin();self.ev('finish',run='diagnosis',outcome='failed',evidence='recorded terminal diagnostic error');self.ack()
  with self.assertRaises(h.Invalid):self.ev('handoff',task='original',artifacts=[str(self.proof)])
if __name__=='__main__':unittest.main()
