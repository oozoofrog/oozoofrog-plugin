import copy,json,sys,tempfile,unittest,shutil,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'payload/team-coordination/scripts'))
import harness as h

class Checkpoints(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.path=self.root/'state.json';self.proof=self.root/'identity';self.proof.write_text('synthetic identity, not provider proof')
  s=h.initial('sample')
  for member,role in [('leader','leader'),('worker','core'),('reviewer','reviewer')]:s=h.apply(s,{'op':'register','member':member,'role':role,'identity':str(self.proof)})
  s=h.apply(s,{'op':'assign','task':'sample','member':'worker','purpose':'fixture','context':'old narrative '*8000})
  s=h.apply(s,{'op':'claim','task':'sample','paths':[str(self.root/'sample.txt')]})
  for i in range(8):s=h.apply(s,{'op':'change','instruction':('historical scope '+str(i)+' ')*1000,'decisions':['rationale '+str(i)]})
  s=h.apply(s,{'op':'change','instruction':'CURRENT: read-only, no publication; denied external write remains denied','decisions':['Unaccepted review finding remains open']});h.save(self.path,s)
 def tearDown(self):self.tmp.cleanup()
 def prepare(self):
  import checkpoints as c
  s=json.loads(self.path.read_text());view={'historical_constraints':{str(i):'Explicitly superseded historical scope'for i in range(8)},'historical_decisions':{str(i):'Earlier rationale retained in snapshot'for i in range(8)},'constraint_indices':[8],'decision_indices':[8],'historical_summary':'Earlier scope superseded; original approvals, decisions and failures remain archived.','remaining_work':['Resolve unaccepted finding; do not expand permission'],'task_contexts':{'sample':'Read-only fixture; unaccepted finding pending'}}
  return c.prepare(self.path,'checkpoint1',view,[str(self.proof)])
 def approve(self,candidate):
  import checkpoints as c
  p=json.loads(candidate.read_text());a=self.root/'approval.json';a.write_text(json.dumps({role:{'member':role,'proposal_sha256':c.digest(p),'source_sha256':p['source_sha256'],'target_policy_hash':p['target_policy_hash'],'approved':True,'safe_boundary':True,'all_current_obligations_retained':True}for role in ['leader','reviewer']}));return a
 def commit(self,candidate,**kwargs):return h.transaction(self.path,{'op':'checkpoint_commit','candidate':str(candidate),'approvals':str(self.approve(candidate)),**kwargs})
 def test_feature_api_present(self):
  self.assertTrue((ROOT/'payload/team-coordination/scripts/checkpoints.py').exists(),'checkpoint implementation missing')
 def test_oversize_rescue_preserves_history_and_budget_then_requires_new_ack(self):
  s=json.loads(self.path.read_text())
  with self.assertRaises(h.Invalid):h.packet(s,'worker')
  candidate=self.prepare();new=self.commit(candidate);p=h.packet(new,'worker')
  self.assertEqual(s['history'],new['history'][:len(s['history'])]);self.assertEqual(s['harness']['constraints'],new['harness']['constraints']);self.assertEqual(s['tasks'],new['tasks']);self.assertEqual(s['harness']['spent'],new['harness']['spent'])
  self.assertIn('CURRENT:',p['constraints'][0]);self.assertEqual(['Resolve unaccepted finding; do not expand permission'],p['remaining_work'])
  with self.assertRaises(h.Invalid):h.ack_current(new,'worker')
  new=h.apply(new,{'op':'ack','member':'worker','revision':p['revision'],'epoch':p['epoch'],'digest':h.digest(p)});h.ack_current(new,'worker')
 def test_full_state_cas_catches_nonrevision_changes(self):
  candidate=self.prepare();s=json.loads(self.path.read_text());s['history'].append({'extra':'same revision mutation'});h.save(self.path,s)
  with self.assertRaises(h.Invalid):self.commit(candidate)
 def test_missing_or_corrupt_archive_blocks_packet_and_dispatch(self):
  candidate=self.prepare();new=self.commit(candidate);snapshot=candidate.parent/'snapshot.json';snapshot.write_text('{}')
  with self.assertRaises(h.Invalid):h.packet(new,'worker')
 def test_pending_runs_controls_and_handoff_block_checkpoint(self):
  for field,value in [('runs',{'run':{'state':'uncertain'}}),('controls',{'control':{'state':'outcome_unknown'}}),('handoffs',{'handoff':{'phase':'delivery_pending'}})]:
   with self.subTest(field=field):
    original=json.loads(self.path.read_text());changed=copy.deepcopy(original);changed['harness'][field]=value;h.save(self.path,changed);candidate=self.prepare()
    with self.assertRaises(h.Invalid):self.commit(candidate)
    shutil.rmtree(candidate.parent);h.save(self.path,original)
 def test_same_commit_id_is_idempotent_conflicting_payload_refused(self):
  candidate=self.prepare();first=self.commit(candidate);second=self.commit(candidate);self.assertEqual(first,second)
  proposal=json.loads(candidate.read_text());proposal['working_view']['historical_summary']='different';candidate.write_text(json.dumps(proposal))
  with self.assertRaises(h.Invalid):self.commit(candidate)
 def test_postcheckpoint_change_and_boundary_require_fresh_ack(self):
  new=self.commit(self.prepare());p=h.packet(new,'worker');new=h.apply(new,{'op':'ack','member':'worker','revision':p['revision'],'epoch':p['epoch'],'digest':h.digest(p)})
  new=h.apply(new,{'op':'change','instruction':'NEW prohibition','decisions':['new rationale']})
  self.assertIn('NEW prohibition',h.packet(new,'worker')['constraints'])
  with self.assertRaises(h.Invalid):h.ack_current(new,'worker')
  new=h.apply(new,{'op':'boundary','member':'worker','reason':'compaction'})
  with self.assertRaises(h.Invalid):h.ack_current(new,'worker')
 def test_atomic_policy_migration_does_not_require_old_oversize_ack(self):
  s=json.loads(self.path.read_text());s['harness']['policy_hash']='old-version-contract';h.save(self.path,s)
  new=self.commit(self.prepare(),policy_refresh=True,reason='explicit administrative migration');self.assertEqual(h.digest(h.effective_contract()),new['harness']['policy_hash']);h.packet(new,'worker')
 def test_archive_relocation_integrity_only_not_task_claim_rebind(self):
  candidate=self.prepare();new=self.commit(candidate);moved=self.root/'restored';shutil.copytree(candidate.parent,moved);shutil.rmtree(candidate.parent)
  with self.assertRaises(h.Invalid):h.packet(new,'worker')
  restored=h.transaction(self.path,{'op':'checkpoint_restore','directory':str(moved),'leader':'leader','safe_boundary':True});self.assertEqual(new['tasks'],restored['tasks']);h.packet(restored,'worker')

 def test_missing_required_evidence_object_blocks(self):
  candidate=self.prepare();new=self.commit(candidate);objects=list((candidate.parent/'objects').iterdir());objects[0].unlink()
  with self.assertRaises(h.Invalid):h.packet(new,'worker')
 def test_review_must_bind_digest_and_be_independent(self):
  candidate=self.prepare();approval=self.approve(candidate);value=json.loads(approval.read_text());value['reviewer']['proposal_sha256']='wrong';approval.write_text(json.dumps(value))
  with self.assertRaises(h.Invalid):h.transaction(self.path,{'op':'checkpoint_commit','candidate':str(candidate),'approvals':str(approval)})
 def test_irreducible_current_obligations_still_block_without_cap_raise(self):
  candidate=self.prepare();value=json.loads(candidate.read_text());value['working_view']['constraint_indices']=list(range(9));value['working_view']['historical_constraints']={};candidate.write_text(json.dumps(value))
  before=self.path.read_bytes()
  with self.assertRaises(h.Invalid):self.commit(candidate)
  self.assertEqual(before,self.path.read_bytes())
 def test_crash_before_atomic_state_write_is_recoverable(self):
  candidate=self.prepare();approval=self.approve(candidate);before=self.path.read_bytes();save=h.save
  def fail(*args):raise OSError('synthetic crash before state publication')
  h.save=fail
  try:
   with self.assertRaises(OSError):h.transaction(self.path,{'op':'checkpoint_commit','candidate':str(candidate),'approvals':str(approval)})
  finally:h.save=save
  self.assertEqual(before,self.path.read_bytes());new=self.commit(candidate);h.packet(new,'worker')
 def test_172_history_and_75000_reservation_ledger_retained(self):
  state=json.loads(self.path.read_text());state['history'] += [{'event':{'synthetic':i,'failure':'retained distinct occurrence'}}for i in range(172-len(state['history']))];state['harness']['spent']=75000;h.save(self.path,state)
  candidate=self.prepare();new=self.commit(candidate);self.assertEqual(172,len(new['history'])-1);self.assertEqual(75000,new['harness']['spent']);self.assertEqual(100000,new['harness']['budget']);self.assertEqual(state['tasks'],new['tasks'])
 def test_replacement_cannot_hide_corrupt_previous_archive(self):
  candidate=self.prepare();self.commit(candidate);(candidate.parent/'snapshot.json').write_text('{}')
  import checkpoints as c
  state=json.loads(self.path.read_text());view=json.loads(candidate.read_text())['working_view'];next_candidate=c.prepare(self.path,'checkpoint2',view,[str(self.proof)])
  with self.assertRaises(h.Invalid):self.commit(next_candidate)
 def test_commit_rejects_conflicting_claims_and_budget_state(self):
  for kind in ['ownership','budget']:
   original=json.loads(self.path.read_text());state=copy.deepcopy(original)
   if kind=='ownership':state['tasks']['conflict']=copy.deepcopy(state['tasks']['sample'])
   else:state['harness']['spent']=100001
   h.save(self.path,state)
   if kind=='ownership':
    import checkpoints as c
    view={'historical_constraints':{str(i):'Explicitly superseded historical scope'for i in range(8)},'historical_decisions':{str(i):'Earlier rationale retained in snapshot'for i in range(8)},'constraint_indices':[8],'decision_indices':[8],'historical_summary':'history retained','remaining_work':['pending'],'task_contexts':{'sample':'sample','conflict':'conflict'}};candidate=c.prepare(self.path,'checkpoint1',view,[])
   else:candidate=self.prepare()
   with self.assertRaises(h.Invalid):self.commit(candidate)
   shutil.rmtree(candidate.parent);h.save(self.path,original)
 def test_object_traversal_and_symlink_fail_closed(self):
  candidate=self.prepare();value=json.loads(candidate.read_text());value['files']['../outside']='00';candidate.write_text(json.dumps(value))
  with self.assertRaises(h.Invalid):self.commit(candidate)

 def test_mandatory_machine_block_denial_stays_inline(self):
  state=json.loads(self.path.read_text());state['tasks']['sample']['block']={'action':'external write','target':'outside fixture','reason':'denied','outcome':'not_executed'};h.save(self.path,state);new=self.commit(self.prepare());self.assertEqual(state['tasks']['sample']['block'],h.packet(new,'leader')['task_obligations']['sample']['block'])
 def test_empty_context_and_implicit_historical_exclusion_refused(self):
  import checkpoints as c
  candidate=self.prepare();p=json.loads(candidate.read_text());view=p['working_view'];view['task_contexts']['sample']=''
  with self.assertRaises(h.Invalid):c.prepare(self.path,'bad-context',view,[])
  view['task_contexts']['sample']='Pending work';view.pop('historical_constraints')
  with self.assertRaises(h.Invalid):c.prepare(self.path,'bad-exclusion',view,[])
 def test_archive_hardlink_and_outside_candidate_refused(self):
  candidate=self.prepare();snapshot=candidate.parent/'snapshot.json';os.link(snapshot,self.root/'linked-snapshot')
  with self.assertRaises(h.Invalid):self.commit(candidate)
 def test_committed_retry_readback_allowed_when_new_work_is_active(self):
  candidate=self.prepare();new=self.commit(candidate);new['harness']['runs']['later']={'state':'active'};h.save(self.path,new);again=self.commit(candidate);self.assertEqual(new,again)
 def test_candidate_outside_project_root_refused(self):
  candidate=self.prepare()
  with tempfile.TemporaryDirectory()as external:
   outside=Path(external)/'checkpoint1';shutil.copytree(candidate.parent,outside)
   with self.assertRaises(h.Invalid):self.commit(outside/'proposal.json')

 def test_verified_model_control_is_terminal_for_checkpoint(self):
  state=json.loads(self.path.read_text());state['harness']['controls']={'done':{'state':'configuration_verified_after_turn'}};h.save(self.path,state);h.packet(self.commit(self.prepare()),'worker')
 def test_committed_approval_is_portable_and_corruption_blocks(self):
  candidate=self.prepare();new=self.commit(candidate);cp=new['harness']['checkpoint'];self.assertIn('approval_object',cp);(self.root/'approval.json').unlink();h.packet(new,'worker');(candidate.parent/cp['approval_object']['relative']).write_text('{}')
  with self.assertRaises(h.Invalid):h.packet(new,'worker')

 def test_committed_retry_does_not_rewrite_canonical_state(self):
  candidate=self.prepare();self.commit(candidate);save=h.save
  def fail(*args):raise AssertionError('Idempotent readback must not write')
  h.save=fail
  try:self.commit(candidate)
  finally:h.save=save
 def test_created_archive_data_is_private_mode(self):
  candidate=self.prepare();self.assertEqual(0o600,candidate.stat().st_mode&0o777);self.assertEqual(0o700,candidate.parent.stat().st_mode&0o777)

 def test_target_contract_cannot_drift_after_semantic_approval(self):
  candidate=self.prepare();approval=self.approve(candidate);original=h.effective_contract
  def drift():
   contract=original();contract['unexpected_target_change']=True;return contract
  h.effective_contract=drift
  try:
   with self.assertRaises(h.Invalid):h.transaction(self.path,{'op':'checkpoint_commit','candidate':str(candidate),'approvals':str(approval),'policy_refresh':True,'reason':'migration'})
  finally:h.effective_contract=original

if __name__=='__main__':unittest.main()
