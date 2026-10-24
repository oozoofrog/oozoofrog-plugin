"""Synthetic same-owner claims; no actual project or permission attestations."""
import copy,hashlib,json,subprocess,sys,threading,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'payload/team-coordination/scripts'));sys.path.insert(0,str(ROOT/'tests'))
import harness as h
import test_observation_followup as followup_fixture

class ClaimExpand(unittest.TestCase):
 def setUp(self):
  self.f=followup_fixture.Followup('runTest');self.f.setUp();self.addCleanup(self.f.tearDown)
  self.root=self.f.root;self.path=self.f.path;self.s=self.f.s
  self.paths=[str(self.root/name)for name in ('integration.py','integration-test.py')]
  self.f.ack();self.s=self.f.s;h.save(self.path,self.s)
 def event(self,**changes):
  raw=self.path.read_bytes();s=json.loads(raw)
  e=dict(op='claim_expand',request_id='integration-claims',project=s['harness']['goal'],project_root=str(self.root),task='task',member='owner',source_sha256=h.digest(s),source_raw_sha256=hashlib.sha256(raw).hexdigest(),policy_hash=h.digest(h.effective_contract()),additional_paths=self.paths,reason='Synthetic integration fix requires two additional files')
  e.update(changes);return e
 def test_ready_review_deadlock_then_union_and_existing_correction(self):
  with self.assertRaisesRegex(h.Invalid,'Claim in invalid state'):h.apply(self.s,dict(op='claim',task='task',paths=self.paths),self.root)
  before=copy.deepcopy(self.s);e=self.event();after=h.transaction(self.path,e)
  expected=copy.deepcopy(before['tasks']);expected['task']['paths']=sorted(expected['task']['paths']+self.paths)
  self.assertEqual(expected,after['tasks']);self.assertEqual(before['history'],after['history'][:-1]);self.assertEqual(before['harness']['diagnostics'],after['harness']['diagnostics'])
  self.assertEqual(before['harness']['revision']+1,after['harness']['revision']);self.assertTrue(all('ack'not in p for p in after['harness']['profiles'].values()))
  self.assertNotIn('task',after['harness'].get('work_authorizations',{}));self.assertEqual('ready_for_review',after['tasks']['task']['state'])
  with self.assertRaises(h.Invalid):h.apply(after,dict(op='begin',task='task',member='owner',run='unapproved'),self.root)
  # The existing correction API still requires independently bound authority.
  self.f.s=after;c=self.f.correction();c['modification_paths']+=self.paths
  permission=json.loads(self.f.permission.read_text());permission['paths']=c['modification_paths'];self.f.permission.write_text(json.dumps(permission));c['permission_evidence']=h.ledger.evidence(str(self.f.permission))
  authority_path=Path(c['correction_authorization']['path']);authority=json.loads(authority_path.read_text());authority['paths']=c['modification_paths'];authority_path.write_text(json.dumps(authority));c['correction_authorization']=h.ledger.evidence(str(authority_path));self.f.approve(c,correction_authority_verified=True)
  self.f.s=h.apply(after,c,self.root)
  with self.assertRaises(h.Invalid):self.f.ev('begin',task='task',member='owner',run='correction')
  self.f.ack();self.f.ev('begin',task='task',member='owner',run='correction');self.assertEqual(c['modification_paths'],self.f.s['harness']['runs']['correction']['execution_paths'])
 def test_replay_is_read_only_after_later_changes_and_conflicts_refuse(self):
  e=self.event();after=h.transaction(self.path,e);after=h.apply(after,dict(op='change',instruction='Synthetic later decision'),self.root);h.save(self.path,after);raw=self.path.read_bytes()
  self.assertEqual(after,h.transaction(self.path,e));self.assertEqual(raw,self.path.read_bytes())
  for field,value in [('reason','different'),('additional_paths',[self.paths[0]])]:
   with self.subTest(field=field),self.assertRaises(h.Invalid):h.transaction(self.path,dict(e,**{field:value}))
  self.assertEqual(raw,self.path.read_bytes())
 def test_other_task_pending_grant_and_every_fresh_ack_are_preserved_or_invalidated(self):
  before=copy.deepcopy(self.s);other=copy.deepcopy(before['tasks']['task']);other['paths']=[str(self.root/'separate.py')];before['tasks']['other']=other
  event=dict(op='diagnostic_grant',request_id='separate',project=before['harness']['goal'],project_root=str(self.root),requester='leader',task='other',member='owner',source_sha256=h.digest(before),policy_hash=h.digest(h.effective_contract()),failed_review_digest=h.digest({'task':'other','index':0,'review':other['reviews'][0]}),provenance_sha256=h.diagnostic_provenance(before,'other'),evidence_goal='Synthetic independently retained other-task observation',modification_paths=other['paths'],human_approval=h.ledger.evidence(str(self.f.proof)),approvals=str(self.f.approvals));self.f.approve(event);before=h.apply(before,event,self.root);grant=copy.deepcopy(before['harness']['diagnostics']['separate'])
  for member in before['harness']['profiles']:
   packet=h.packet(before,member);before=h.apply(before,dict(op='ack',member=member,revision=packet['revision'],epoch=packet['epoch'],digest=h.digest(packet)),self.root)
  h.save(self.path,before);after=h.transaction(self.path,self.event());self.assertEqual(before['tasks']['other'],after['tasks']['other']);self.assertEqual(grant,after['harness']['diagnostics']['separate'])
  for member,profile in after['harness']['profiles'].items():
   self.assertNotIn('ack',profile)
   with self.assertRaises(h.Invalid):h.ack_current(after,member)
  packet=h.packet(after,'owner');after=h.apply(after,dict(op='ack',member='owner',revision=packet['revision'],epoch=packet['epoch'],digest=h.digest(packet)),self.root)
  with self.assertRaises(h.Invalid):h.apply(after,dict(op='begin',task='task',member='owner',run='ownership-only'),self.root)
  other_run=h.apply(after,dict(op='begin',task='other',member='owner',run='other-observation',diagnostic_request_id='separate'),self.root);self.assertEqual(other['paths'],other_run['harness']['runs']['other-observation']['execution_paths'])
 def test_same_owner_different_task_and_shared_resource_conflicts_refuse(self):
  for paths,resources in [([self.paths[0]],[]),([str(self.root/'separate.py')],['shared'])]:
   state=copy.deepcopy(self.s);state['tasks']['task']['resources']=['shared'];state['tasks']['other']=dict(owner='owner',paths=paths,resources=resources,state='accepted');h.save(self.path,state);raw=self.path.read_bytes()
   with self.assertRaises(h.Invalid):h.transaction(self.path,self.event())
   self.assertEqual(raw,self.path.read_bytes())
 def test_nested_same_task_union_keeps_next_boundary_usable(self):
  import checkpoints
  self.paths=[str(self.root/'collector.py'/'nested'),str(self.root)]
  self.test_ready_review_deadlock_then_union_and_existing_correction()
  checkpoints.quiescent(json.loads(self.path.read_bytes()))
 def test_preserves_real_consumed_correction_record_and_scope_requirement(self):
  self.f.s=h.apply(self.s,self.f.correction(),self.root);self.f.ack();self.f.ev('begin',task='task',member='owner',run='prior-correction');self.f.ev('finish',run='prior-correction',outcome='completed',evidence='synthetic insufficient correction');self.f.ev('handoff',task='task',artifacts=[str(self.f.proof)])
  before=copy.deepcopy(self.f.s);self.assertIsNotNone(h.work_authorization(before,'task'));h.save(self.path,before);after=h.transaction(self.path,self.event())
  for key in ('reworks','runs','diagnostics','work_scope_required'):self.assertEqual(before['harness'][key],after['harness'][key])
  self.assertIsNone(h.work_authorization(after,'task'));self.assertNotIn('task',after['harness']['work_authorizations']);self.assertEqual(before['tasks']['task']['reviews'],after['tasks']['task']['reviews'])
 def test_checkpoint_and_closed_diagnostic_snapshots_and_cli_receipt(self):
  import checkpoints
  view=dict(historical_constraints={},historical_decisions={},constraint_indices=[],decision_indices=[],historical_summary='Synthetic retained full history',remaining_work=['Correct integration'],task_contexts={'task':'Synthetic original review remains failed'})
  candidate=checkpoints.prepare(self.path,'before-expansion',view,[]);proposal=json.loads(candidate.read_text());approval=self.root/'checkpoint-approval.json';approval.write_text(json.dumps({role:dict(member=role,proposal_sha256=h.digest(proposal),source_sha256=proposal['source_sha256'],target_policy_hash=proposal['target_policy_hash'],approved=True,safe_boundary=True,all_current_obligations_retained=True)for role in ('leader','reviewer')}))
  before=h.transaction(self.path,dict(op='checkpoint_commit',candidate=str(candidate),approvals=str(approval)));archived={str(p):p.read_bytes()for p in candidate.parent.rglob('*')if p.is_file()};e=self.event();event_path=self.root/'event.json';event_path.write_text(json.dumps(e))
  result=subprocess.run([sys.executable,'-I','-S','-B',str(ROOT/'run.py'),'harness','--state',str(self.path),'apply','--event',str(event_path)],capture_output=True,text=True);self.assertEqual(0,result.returncode,result.stdout+result.stderr);receipt=json.loads(result.stdout);self.assertEqual(e['request_id'],receipt['request_id']);self.assertIn('no native permission or execution grant',receipt['scope'])
  after=json.loads(self.path.read_bytes());checkpoints.active(after);self.assertEqual(before['harness']['checkpoint'],after['harness']['checkpoint']);self.assertEqual(archived,{str(p):p.read_bytes()for p in candidate.parent.rglob('*')if p.is_file()});self.assertEqual(before['harness']['diagnostics'],after['harness']['diagnostics'])
  self.assertEqual(before['tasks']['task'],after['harness']['diagnostics']['first']['original_task'])
 def test_identity_and_claim_alias_drift_and_parsed_raw_mismatch_refuse(self):
  event=self.event();raw=self.path.read_bytes();self.f.proof.write_text('synthetic changed identity')
  with self.assertRaises(h.Invalid):h.transaction(self.path,event)
  self.assertEqual(raw,self.path.read_bytes())
  self.f.proof.write_text('Synthetic prior failure and authorized collector-only observation')
  different=copy.deepcopy(self.s);different['harness']['goal']='different'
  with self.assertRaises(h.Invalid):h.apply(different,dict(event,project='different',source_sha256=h.digest(different)),self.root,source_bytes=raw)
  claim=Path(self.s['tasks']['task']['paths'][0]);claim.symlink_to(self.root/'other')
  with self.assertRaises(h.Invalid):h.transaction(self.path,event)
  self.assertEqual(raw,self.path.read_bytes())
 def test_invalid_requests_leave_exact_bytes(self):
  alias=self.root/'alias';alias.symlink_to(self.root,target_is_directory=True)
  cases=[dict(member='reviewer'),dict(project='other'),dict(project_root=str(alias)),dict(policy_hash='stale'),dict(source_sha256='stale'),dict(source_raw_sha256='stale'),dict(request_id=''),dict(reason=''),dict(additional_paths=[]),dict(additional_paths=[self.paths[0],self.paths[0]]),dict(additional_paths=[str(alias/'x')]),dict(additional_paths=['relative']),dict(additional_paths=[str(self.root/'a/../x')]),dict(additional_paths=[self.s['tasks']['task']['paths'][0]])]
  raw=self.path.read_bytes()
  for changes in cases:
   with self.subTest(changes=changes),self.assertRaises(h.Invalid):h.transaction(self.path,self.event(**changes))
   self.assertEqual(raw,self.path.read_bytes())
 def test_other_claims_and_nondrained_states_refuse(self):
  variants=[]
  for state in ('active','uncertain'):
   s=copy.deepcopy(self.s);s['harness']['runs']['diag0']['state']=state;variants.append(s)
  for state in ('request_pending','outcome_unknown','accepted_pending_observation','configuration_pending_turn'):
   s=copy.deepcopy(self.s);s['harness']['controls']={'pending':{'state':state}};variants.append(s)
  s=copy.deepcopy(self.s);s['harness']['handoffs']={'pending':{'state':'prepared'}};variants.append(s)
  s=copy.deepcopy(self.s);s['harness']['diagnostics']['first']['state']='granted';variants.append(s)
  s=copy.deepcopy(self.s);s['tasks']['task']['state']='assigned';variants.append(s)
  for path in (self.paths[0],str(self.root),str(Path(self.paths[0])/'child')):
   s=copy.deepcopy(self.s);s['tasks']['other']=dict(owner='reviewer',paths=[path],resources=[],state='accepted');variants.append(s)
  for index,s in enumerate(variants):
   h.save(self.path,s);raw=self.path.read_bytes()
   with self.subTest(index=index),self.assertRaises(h.Invalid):h.transaction(self.path,self.event())
   self.assertEqual(raw,self.path.read_bytes())
 def test_old_authority_records_and_obligations_are_preserved(self):
  s=copy.deepcopy(self.s);s['tasks']['task'].update(resources=['synthetic-resource'],block={'reason':'retained permission judgment'},extension={'immutable':'obligation'})
  old={'kind':'historical synthetic fixture','original_transition':{'task':'task'}};s['harness']['reworks']={'old':old};s['harness']['work_authorizations']={'task':'old'};h.save(self.path,s)
  after=h.transaction(self.path,self.event());self.assertEqual({'old':old},after['harness']['reworks']);self.assertNotIn('task',after['harness']['work_authorizations'])
  expected=copy.deepcopy(s['tasks']);expected['task']['paths']=sorted(expected['task']['paths']+self.paths);self.assertEqual(expected,after['tasks'])
 def test_raw_cas_and_pre_rename_failure_preserve_bytes(self):
  e=self.event();raw=self.path.read_bytes();self.path.write_bytes(raw+b' ')
  with self.assertRaises(h.Invalid):h.transaction(self.path,e)
  self.path.write_bytes(raw)
  with patch.object(h.os,'replace',side_effect=OSError('synthetic pre-rename failure')):
   with self.assertRaises(OSError):h.transaction(self.path,e)
  self.assertEqual(raw,self.path.read_bytes())
 def test_post_rename_unknown_read_same_id_and_concurrent_cas(self):
  e=self.event();original=h.os.fsync;calls=[]
  def fsync(fd):
   calls.append(fd)
   if len(calls)==2:raise OSError('synthetic post-rename uncertainty')
   return original(fd)
  with patch.object(h.os,'fsync',side_effect=fsync):
   with self.assertRaises(OSError):h.transaction(self.path,e)
  committed=self.path.read_bytes();h.transaction(self.path,e);self.assertEqual(committed,self.path.read_bytes())
  h.save(self.path,self.s);first=self.event(request_id='first');second=self.event(request_id='second',additional_paths=[str(self.root/'second.py')]);results=[];barrier=threading.Barrier(2)
  def execute(event):
   barrier.wait()
   try:h.transaction(self.path,event);results.append('committed')
   except h.Invalid:results.append('stale')
  threads=[threading.Thread(target=execute,args=(event,))for event in (first,second)]
  for thread in threads:thread.start()
  for thread in threads:thread.join()
  self.assertCountEqual(['committed','stale'],results)

if __name__=='__main__':unittest.main()
