"""Synthetic actor reviews; real files/transactions, no business project access."""
import copy,hashlib,json,sys,unittest
from pathlib import Path
from unittest.mock import patch
import test_observation_followup as fixtures
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'payload/team-coordination/scripts'))
import harness as h

class PermissionRecovery(unittest.TestCase):
 tearDown=fixtures.Followup.tearDown
 ev=fixtures.Followup.ev
 ack=fixtures.Followup.ack
 method=fixtures.Followup.method
 approve=fixtures.Followup.approve
 def setUp(self):
  fixtures.Followup.setUp(self)
  self.failed_report=self.root/'actual-failed-review';self.failed_report.write_text('Synthetic retained independent product FAIL');self.s['tasks']['task']['reviews'][-1]['evidence']=h.ledger.evidence(str(self.failed_report))
  e=fixtures.Followup.request(self);self.s=h.apply(self.s,e,self.root);self.ack();self.ev('begin',member='owner',task='task',run='uninitialized',diagnostic_request_id='bits')
  self.execution={'argv':['/usr/bin/true'],'environment':{'HOME':str(self.root),'PATH':'/usr/bin:/bin'},'cwd':str(self.root)}
  self.log=self.root/'initialization.log';self.log.write_text('Synthetic manifest sandbox initialization failed before collector binary or output existed')
  self.terminal=self.root/'original-execution.json';self.terminal.write_text(json.dumps(dict(self.execution,run='uninitialized',diagnostic_request_id='bits',command_terminal=True,exitCode=1,binary_path=None,collector_result_path=None,collector_sha256=self.new['collector']['sha256'],binding_sha256=self.new['input']['evidence']['sha256'],log=str(self.log),log_sha256=h.ledger.evidence(str(self.log))['sha256'],permissionDenied=True)))
  self.ev('finish',run='uninitialized',outcome='not_executed',evidence=str(self.terminal))
  self.human=self.root/'submission-human.txt';self.human.write_text('Synthetic human permits submission of the exact original observation command for normal scoped tool authorization.')
  self.authority=self.root/'submission-authority.json';self.authority.write_text(json.dumps({'kind':'permission_recovery_submission','project':'finish sample','task':'task','member':'owner','paths':[str(self.root/'collector.py')],'source':h.ledger.evidence(str(self.human)),'quote':self.human.read_text()}))
  self.cause.write_text(json.dumps({'category':'environment_initialization_failure','previous_run':'uninitialized','terminal_evidence':h.ledger.evidence(str(self.terminal)),'environment_evidence':h.ledger.evidence(str(self.log)),'collector_executed':False,'user_denied':False,'auto_review_denied':False,'access_denied':False,'reason':'Synthetic manifest initialization failed before collector execution; normal tool review still required'}))
  h.save(self.path,self.s)
 def request(self,**changes):
  t=self.s['tasks']['task'];e=dict(op='diagnostic_permission_recovery',request_id='recover',previous_request_id='bits',project='finish sample',project_root=str(self.root),requester='leader',task='task',member='owner',source_sha256=h.digest(self.s),source_raw_sha256=hashlib.sha256(self.path.read_bytes()).hexdigest(),policy_hash=h.digest(h.effective_contract()),failed_review_digest=h.digest({'task':'task','index':len(t['reviews'])-1,'review':t['reviews'][-1]}),provenance_sha256=h.diagnostic_provenance(self.s,'task'),evidence_goal='Submit unchanged observation for normal command-specific tool review',modification_paths=[str(self.root/'collector.py')],method=self.new,execution=copy.deepcopy(self.execution),terminal_evidence=h.ledger.evidence(str(self.terminal)),root_cause_evidence=h.ledger.evidence(str(self.cause)),submission_authorization=h.ledger.evidence(str(self.authority)),approvals=str(self.approvals));e.update(changes)
  return self.approve(e,environment_initialization_verified=True,known_not_executed=True,no_explicit_denial=True,existing_scope_verified=True,exact_execution_verified=True,permission_submission_only=True)
 def apply_recovery(self,e=None):
  self.s=h.transaction(self.path,e or self.request());return self.s
 def begin(self,**changes):
  e=dict(op='begin',task='task',member='owner',run='recovery-run',diagnostic_request_id='recover',execution=copy.deepcopy(self.execution));e.update(changes);return self.ev(**e)
 def test_closed_not_executed_can_append_reviewed_submission_without_rewriting_truth(self):
  before=copy.deepcopy(self.s);event=self.request();self.apply_recovery(event)
  self.assertEqual(before['tasks'],self.s['tasks']);self.assertEqual(before['harness']['runs'],self.s['harness']['runs']);self.assertEqual(before['harness']['diagnostics']['bits'],self.s['harness']['diagnostics']['bits']);self.assertEqual(before['history'],self.s['history'][:-1]);self.assertEqual('granted',self.s['harness']['diagnostics']['recover']['state'])
  with self.assertRaisesRegex(h.Invalid,'acknowledgement'):self.begin()
  self.ack();self.begin();self.ev('finish',run='recovery-run',outcome='not_executed',evidence='Synthetic normal tool review refused submission')
  self.assertEqual(before['tasks'],self.s['tasks']);self.assertEqual('closed',self.s['harness']['diagnostics']['recover']['state']);self.assertEqual(self.s,h.apply(self.s,event,self.root));self.assertEqual('fail',self.s['tasks']['task']['reviews'][-1]['verdict'])
  with self.assertRaises(h.Invalid):self.begin(run='repeated')
 def test_refuses_changed_execution_method_scope_and_stale_cas(self):
  for changes in ({'execution':dict(self.execution,argv=['/usr/bin/false'])},{'execution':dict(self.execution,environment={})},{'execution':dict(self.execution,cwd='/tmp')},{'method':self.old},{'modification_paths':[str(self.root/'a')]},{'source_sha256':'stale'},{'source_raw_sha256':'stale'}):
   with self.subTest(changes=changes),self.assertRaises(h.Invalid):self.apply_recovery(self.request(**changes))
 def test_refuses_executed_uncertain_ambiguous_and_explicit_denial_predecessors(self):
  before=copy.deepcopy(self.s)
  for state in ('completed','failed','uncertain','active'):
   self.s=copy.deepcopy(before);self.s['harness']['runs']['uninitialized']['state']=state;h.save(self.path,self.s)
   with self.subTest(state=state),self.assertRaises(h.Invalid):self.apply_recovery()
  self.s=before;h.save(self.path,self.s)
  cause=json.loads(self.cause.read_text())
  for field,value in [('category','computation_failure'),('collector_executed',True),('user_denied',True),('auto_review_denied',True),('access_denied',True),('collector_executed',None)]:
   self.cause.write_text(json.dumps(dict(cause,**{field:value})))
   with self.subTest(field=field),self.assertRaises(h.Invalid):self.apply_recovery()
 def test_refuses_duplicate_successor_conflicting_id_and_nonindependent_judgment(self):
  event=self.request();self.approve(event,environment_initialization_verified=False)
  with self.assertRaises(h.Invalid):self.apply_recovery(event)
  self.s['members']['reviewer']['runtime_id_claim']='owner';h.save(self.path,self.s)
  with self.assertRaises(h.Invalid):self.apply_recovery()
  self.s['members']['reviewer']['runtime_id_claim']='reviewer';h.save(self.path,self.s);event=self.request();self.apply_recovery(event)
  self.assertEqual(self.s,h.transaction(self.path,event))
  with self.assertRaises(h.Invalid):self.apply_recovery(self.request(request_id='branch'))
  with self.assertRaises(h.Invalid):self.apply_recovery(dict(event,evidence_goal='changed'))
 def test_begin_rechecks_evidence_execution_and_retained_review_integrity(self):
  self.apply_recovery();granted=copy.deepcopy(self.s)
  with self.assertRaises(h.Invalid):self.ack();self.begin(execution=dict(self.execution,argv=['/usr/bin/false']))
  self.s=copy.deepcopy(granted);self.log.write_text('Changed evidence')
  with self.assertRaises(h.Invalid):self.ack();self.begin()
  self.log.write_text('Synthetic manifest sandbox initialization failed before collector binary or output existed');self.s=copy.deepcopy(granted);self.s['harness']['diagnostics']['recover']['review']['bytes_base64']='e30='
  with self.assertRaises(h.Invalid):self.ack();self.begin()
 def test_refuses_stale_terminal_input_human_authority_and_atomic_save_failure(self):
  event=self.request();raw=self.path.read_bytes()
  with patch.object(h.os,'replace',side_effect=OSError('Synthetic pre-rename failure')):
   with self.assertRaises(OSError):self.apply_recovery(event)
  self.assertEqual(raw,self.path.read_bytes());self.assertEqual([],list(self.root.glob('.state-*')))
  for path in (self.terminal,Path(self.new['input']['evidence']['path']),self.human):
   original=path.read_bytes();event=self.request();path.write_bytes(original+b'changed')
   with self.subTest(path=path),self.assertRaises((h.Invalid,ValueError)):self.apply_recovery(event)
   path.write_bytes(original)
 def test_after_commit_fsync_error_requires_stable_id_readback_without_another_transition(self):
  event=self.request();real=h.os.fsync;calls=[]
  def directory_error(fd):
   calls.append(fd)
   if len(calls)==2:raise OSError('Synthetic directory fsync failure after committed replace')
   return real(fd)
  with patch.object(h.os,'fsync',side_effect=directory_error):
   with self.assertRaises(OSError):self.apply_recovery(event)
  committed=json.loads(self.path.read_bytes());self.assertIn('recover',committed['harness']['diagnostics']);self.assertEqual(committed,h.transaction(self.path,event));self.assertEqual('closed',committed['harness']['diagnostics']['bits']['state']);self.assertEqual('granted',committed['harness']['diagnostics']['recover']['state'])
 def test_terminal_must_explicitly_establish_absent_collector_and_original_descriptor(self):
  terminal=json.loads(self.terminal.read_text())
  before=copy.deepcopy(self.s)
  for field in ('binary_path','collector_result_path','argv','environment','cwd','collector_sha256','binding_sha256'):
   self.s=copy.deepcopy(before);h.save(self.path,self.s)
   changed=dict(terminal);changed.pop(field);self.terminal.write_text(json.dumps(changed));cause=json.loads(self.cause.read_text());cause['terminal_evidence']=h.ledger.evidence(str(self.terminal));self.cause.write_text(json.dumps(cause))
   with self.subTest(field=field),self.assertRaises((h.Invalid,KeyError)):self.apply_recovery()
  self.terminal.write_text(json.dumps(terminal))
 def test_changed_failed_report_and_approval_after_grant_cannot_begin(self):
  self.apply_recovery();granted=copy.deepcopy(self.s)
  for path in (self.failed_report,self.approvals):
   self.s=copy.deepcopy(granted);original=path.read_bytes();path.write_bytes(original+b'changed')
   with self.subTest(path=path),self.assertRaises((h.Invalid,ValueError)):self.ack();self.begin()
   path.write_bytes(original)
 def test_recovery_of_cannot_be_changed_to_branch_a_closed_successor(self):
  self.apply_recovery();self.s['harness']['diagnostics']['recover']['recovery_of']='another'
  with self.assertRaises(h.Invalid):h.packet(self.s,'owner')

if __name__=='__main__':unittest.main()
