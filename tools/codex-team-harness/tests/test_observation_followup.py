"""Real file-backed synthetic methods; no provider calls or business-project data."""
import copy,json,struct,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'payload/team-coordination/scripts'))
import harness as h

class Followup(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name).resolve();self.path=self.root/'state.json';self.proof=self.root/'proof';self.proof.write_text('Synthetic prior failure and authorized collector-only observation');self.approvals=self.root/'approval';self.s=h.initial('finish sample')
  for member,role in [('owner','core'),('leader','leader'),('reviewer','reviewer')]:self.ev('register',member=member,role=role,identity=str(self.proof))
  self.ev('assign',member='owner',task='task',purpose='complete original deliverable',context='Original FAIL stays until actual correction and independent review');self.ev('claim',task='task',paths=[str(self.root/name)for name in ('collector.py','a','b','c','d','e','f')]);self.ack();self.ev('begin',member='owner',task='task',run='product');self.ev('finish',run='product',outcome='completed',evidence='synthetic terminal');self.ev('handoff',task='task',artifacts=[str(self.proof)]);self.ev('review',task='task',reviewer='reviewer',verdict='fail',evidence=str(self.proof));self.ev('handoff',task='task',artifacts=[str(self.proof)])
  self.old=self.method('old','eight-assertions-v1');self.new=self.method('new','float32-48-pre-post-v1');t=self.s['tasks']['task'];failure=h.digest({'task':'task','index':0,'review':t['reviews'][0]})
  e=dict(op='diagnostic_grant',request_id='first',project='finish sample',project_root=str(self.root),requester='leader',task='task',member='owner',source_sha256=h.digest(self.s),policy_hash=h.digest(h.effective_contract()),failed_review_digest=failure,provenance_sha256=h.diagnostic_provenance(self.s,'task'),evidence_goal='Observe existing collector',modification_paths=[str(self.root/'collector.py')],human_approval=h.ledger.evidence(str(self.proof)),approvals=str(self.approvals));self.approve(e);self.s=h.apply(self.s,e,self.root);self.ack();self.ev('begin',member='owner',task='task',run='diag0',diagnostic_request_id='first')
  terminal=self.root/'terminal.json';terminal.write_text(json.dumps({'run':'diag0','outcome':'completed','assertions':8,'method':self.old,'permission_denied':False}));self.ev('finish',run='diag0',outcome='completed',evidence=str(terminal))
  self.cause=self.root/'cause.json';self.cause.write_text(json.dumps({'category':'insufficient_observation','previous_run':'diag0','reason':'Eight assertions did not capture coefficient bits','permission_denied':False}));self.permission=self.root/'permission.json';self.permission.write_text(json.dumps({'allowed':True,'paths':[str(self.root/'collector.py')],'source':'Synthetic same-scope permission claim, no native authority attestation'}))
 def tearDown(self):self.tmp.cleanup()
 def ev(self,op,**kw):self.s=h.apply(self.s,dict(op=op,**kw),self.root);return self.s
 def ack(self):
  p=h.packet(self.s,'owner');self.ev('ack',member='owner',revision=p['revision'],epoch=p['epoch'],digest=h.digest(p));return p
 def method(self,name,schema):
  collector=self.root/(name+'-collector.py');collector.write_text('synthetic '+schema);spec=self.root/(name+'-spec.json');spec.write_text(json.dumps({'schema':schema,'count':8 if name=='old'else 48}));inputs=self.root/'inputs.json';inputs.write_text(json.dumps([1.0/3]*48))
  return dict(collector=h.ledger.evidence(str(collector)),spec=h.ledger.evidence(str(spec)),input={'kind':'file','evidence':h.ledger.evidence(str(inputs))},schema=schema)
 def approve(self,e,**changes):
  flags=dict(approved=True,safe_boundary=True,all_current_obligations_retained=True,human_approval_verified=True,diagnostic_only=True,material_method_change=True,same_authorized_scope=True,permissions_current=True,prior_method_verified=True);flags.update(changes)
  self.approvals.write_text(json.dumps({role:dict(member=role,request_sha256=h.digest({k:v for k,v in e.items()if k!='approvals'}),**flags)for role in ('leader','reviewer')}));return e
 def request(self,**changes):
  reviews=self.s['tasks']['task']['reviews'];failure=h.digest({'task':'task','index':len(reviews)-1,'review':reviews[-1]});e=dict(op='diagnostic_followup',request_id='bits',previous_request_id='first',project='finish sample',project_root=str(self.root),requester='leader',task='task',member='owner',source_sha256=h.digest(self.s),policy_hash=h.digest(h.effective_contract()),failed_review_digest=failure,provenance_sha256=h.diagnostic_provenance(self.s,'task'),evidence_goal='Capture exactly 48 Float32 pre/post bits',modification_paths=[str(self.root/'collector.py')],prior_method=self.old,method=self.new,legacy_seed={'run':'diag0','terminal':h.ledger.evidence(str(self.root/'terminal.json')),'method':self.old},root_cause_evidence=h.ledger.evidence(str(self.cause)),permission_evidence=h.ledger.evidence(str(self.permission)),approvals=str(self.approvals));e.update(changes);return self.approve(e)
 def test_changed_observation_after_completed_insufficient_run_preserves_product_truth(self):
  before=copy.deepcopy(self.s);e=self.request();self.s=h.apply(self.s,e,self.root);self.assertEqual(before['tasks'],self.s['tasks']);self.assertEqual(before['harness']['diagnostics']['first'],self.s['harness']['diagnostics']['first']);self.assertEqual(before['history'],self.s['history'][:-1])
  with self.assertRaises(h.Invalid):self.ev('begin',member='owner',task='task',run='bits-run',diagnostic_request_id='bits')
  self.ack();self.ev('begin',member='owner',task='task',run='bits-run',diagnostic_request_id='bits');bits=[{'index':i,'before_bits':struct.pack('>f',0.0).hex(),'after_bits':struct.pack('>f',1/3).hex()}for i in range(48)];self.assertEqual('3eaaaaab',bits[47]['after_bits']);self.assertEqual(48,len(bits));output=self.root/'bits.json';output.write_text(json.dumps(bits));self.ev('finish',run='bits-run',outcome='completed',evidence=str(output))
  self.assertEqual(before['tasks'],self.s['tasks']);self.assertEqual('fail',self.s['tasks']['task']['reviews'][-1]['verdict']);self.assertEqual(self.s,h.apply(self.s,e,self.root))
  for op in ('accept','rework','handoff'):
   with self.assertRaises(h.Invalid):h.apply(self.s,dict(op=op,task='task'),self.root)
 def test_same_method_new_id_stale_cas_wrong_seed_and_scope_are_rejected(self):
  for changes in ({'method':self.old},{'source_sha256':'stale'},{'modification_paths':[str(self.root/'a')]},{'prior_method':self.new},{'previous_request_id':'missing'}):
   with self.subTest(changes=changes),self.assertRaises(h.Invalid):h.apply(self.s,self.request(**changes),self.root)
  e=self.request();self.s=h.apply(self.s,e,self.root);self.ack();self.ev('begin',member='owner',task='task',run='bits-run',diagnostic_request_id='bits');self.ev('finish',run='bits-run',outcome='completed',evidence='synthetic terminal')
  with self.assertRaises(h.Invalid):h.apply(self.s,self.request(request_id='new-id',previous_request_id='bits',prior_method=self.new,legacy_seed=None),self.root)
 def test_uncertainty_permissions_evidence_and_independent_judgment_are_strict(self):
  self.permission.write_text(json.dumps({'allowed':False,'paths':[str(self.root/'collector.py')]}))
  with self.assertRaises(h.Invalid):h.apply(self.s,self.request(),self.root)
  self.permission.write_text(json.dumps({'allowed':True,'paths':[str(self.root/'collector.py')]}));e=self.request();self.approve(e,material_method_change=False)
  with self.assertRaises(h.Invalid):h.apply(self.s,e,self.root)
  e=self.request();self.s['harness']['runs']['diag0']['state']='uncertain'
  with self.assertRaises(h.Invalid):h.apply(self.s,e,self.root)
 def test_followup_atomic_failure_and_changed_identity_remain_fail_closed(self):
  e=self.request();h.save(self.path,self.s);raw=self.path.read_bytes()
  with patch.object(h.os,'replace',side_effect=OSError('synthetic pre-rename failure')):
   with self.assertRaises(OSError):h.transaction(self.path,e)
  self.assertEqual(raw,self.path.read_bytes());self.s['members']['reviewer']['runtime_id_claim']='owner'
  with self.assertRaises(h.Invalid):h.apply(self.s,self.request(),self.root)
 def correction(self,**changes):
  source=self.root/'correction-authority';quote='Synthetic human: correct the original sample deliverable within its retained claims, preserving failed evidence.';source.write_text(quote);proof=self.root/'correction-binding.json';proof.write_text(json.dumps({'kind':'correction','project':'finish sample','task':'task','member':changes.get('member','owner'),'paths':[str(self.root/'collector.py')],'source':h.ledger.evidence(str(source)),'quote':quote}))
  values=dict(op='rework',request_id='correct',correction_authorization=h.ledger.evidence(str(proof)));values.update(changes);e=self.request(**values);return self.approve(e,correction_authority_verified=True)
 def test_diagnostic_only_scope_does_not_grant_correction_but_evidenced_changed_work_can_finish(self):
  before=copy.deepcopy(self.s);e=self.correction();without=dict(e);without.pop('correction_authorization');self.approve(without,correction_authority_verified=True)
  with self.assertRaises(h.Invalid):h.apply(self.s,without,self.root)
  e=self.correction();self.s=h.apply(self.s,e,self.root);self.assertEqual('assigned',self.s['tasks']['task']['state']);self.assertEqual(before['harness']['diagnostics']['first'],self.s['harness']['diagnostics']['first']);self.assertEqual(before['tasks']['task']['reviews'],self.s['tasks']['task']['reviews'])
  with self.assertRaises(h.Invalid):self.ev('begin',task='task',member='owner',run='correct-run')
  self.ack();self.ev('begin',task='task',member='owner',run='correct-run');self.ev('finish',run='correct-run',outcome='completed',evidence='observed corrected result')
  with self.assertRaises(h.Invalid):self.ev('accept',task='task')
  artifact=self.root/'corrected-artifact';artifact.write_text('actual synthetic changed output');self.ev('handoff',task='task',artifacts=[str(artifact)]);self.ev('review',task='task',reviewer='reviewer',verdict='pass',evidence=str(self.proof));self.ev('accept',task='task');self.assertEqual(['fail','pass'],[r['verdict']for r in self.s['tasks']['task']['reviews']])
 def test_new_id_with_same_or_unanchored_correction_method_is_not_progress(self):
  with self.assertRaises(h.Invalid):h.apply(self.s,self.correction(method=self.old),self.root)
  e=self.correction();self.s=h.apply(self.s,e,self.root);self.ack();self.ev('begin',task='task',member='owner',run='correct-run');self.ev('finish',run='correct-run',outcome='completed',evidence='terminal');self.ev('handoff',task='task',artifacts=[str(self.proof)])
  with self.assertRaises(h.Invalid):h.apply(self.s,self.correction(request_id='new-id',previous_request_id='correct',prior_method=self.new,legacy_seed=None),self.root)
 def test_second_material_correction_can_continue_without_erasing_first_receipt(self):
  e=self.correction();self.s=h.apply(self.s,e,self.root);first=copy.deepcopy(self.s['harness']['reworks']['correct']);self.ack();self.ev('begin',task='task',member='owner',run='correct-run');self.ev('finish',run='correct-run',outcome='completed',evidence='observed insufficiency');self.ev('handoff',task='task',artifacts=[str(self.proof)])
  self.cause.write_text(json.dumps({'category':'computation_failure','previous_run':'correct-run','reason':'A different measured defect needs a changed correction','permission_denied':False}));third=self.method('third','float32-48-correction-v2');e=self.correction(request_id='correct-again',previous_request_id='correct',prior_method=self.new,method=third,legacy_seed=None);self.s=h.apply(self.s,e,self.root)
  self.assertEqual(first,self.s['harness']['reworks']['correct']);self.assertEqual('assigned',self.s['tasks']['task']['state']);self.assertEqual(1,len(self.s['tasks']['task']['reviews']))
 def test_fresh_actual_fail_binds_next_request_without_rewriting_prior_failure_binding(self):
  e=self.correction();self.s=h.apply(self.s,e,self.root);first=copy.deepcopy(self.s['harness']['reworks']['correct']);self.ack();self.ev('begin',task='task',member='owner',run='correct-run');self.ev('finish',run='correct-run',outcome='completed',evidence='terminal');artifact=self.root/'artifact-new';artifact.write_text('actual changed artifact');report=self.root/'new-fail';report.write_text('Actual independent synthetic finding on changed artifact');self.ev('handoff',task='task',artifacts=[str(artifact)]);self.ev('review',task='task',reviewer='reviewer',verdict='fail',evidence=str(report));self.ev('handoff',task='task',artifacts=[str(artifact)])
  self.cause.write_text(json.dumps({'category':'computation_failure','previous_run':'correct-run','reason':'Fresh independent failure identifies a different material defect','permission_denied':False}));third=self.method('third','different-correction-v3');e=self.correction(request_id='next-fail-fix',previous_request_id='correct',prior_method=self.new,method=third,legacy_seed=None);self.s=h.apply(self.s,e,self.root)
  self.assertNotEqual(first['failed_review_digest'],self.s['harness']['reworks']['next-fail-fix']['failed_review_digest']);self.assertEqual(first,self.s['harness']['reworks']['correct']);self.assertEqual(['fail','fail'],[r['verdict']for r in self.s['tasks']['task']['reviews']])
 def test_owner_transfer_cannot_reuse_old_correction_authority_after_fresh_ack(self):
  self.s=h.apply(self.s,self.correction(),self.root);self.ev('register',member='new-owner',role='core',identity=str(self.proof));self.ev('release',task='task',safe_boundary=True);self.ev('reassign',task='task',member='new-owner');self.ev('claim',task='task',paths=[str(self.root/'collector.py')]);p=h.packet(self.s,'new-owner');self.ev('ack',member='new-owner',revision=p['revision'],epoch=p['epoch'],digest=h.digest(p))
  with self.assertRaises(h.Invalid):self.ev('begin',task='task',member='new-owner',run='unauthorized-owner')
 def test_claim_expansion_cannot_reuse_old_scope_after_fresh_ack(self):
  self.s=h.apply(self.s,self.correction(),self.root);self.ev('claim',task='task',paths=[str(self.root/'outside-correction-scope')]);self.ack()
  with self.assertRaises(h.Invalid):self.ev('begin',task='task',member='owner',run='unauthorized-scope')
 def test_explicit_fresh_actor_scope_binding_allows_legitimate_new_owner(self):
  self.s=h.apply(self.s,self.correction(),self.root);self.ev('register',member='new-owner',role='core',identity=str(self.proof));self.ev('release',task='task',safe_boundary=True);self.ev('reassign',task='task',member='new-owner');self.ev('claim',task='task',paths=[str(self.root/'collector.py')]);third=self.method('third','fresh-owner-correction-v3');e=self.correction(request_id='new-owner-authority',member='new-owner',method=third);self.s=h.apply(self.s,e,self.root)
  p=h.packet(self.s,'new-owner');self.ev('ack',member='new-owner',revision=p['revision'],epoch=p['epoch'],digest=h.digest(p));self.ev('begin',task='task',member='new-owner',run='fresh-owner-run');self.assertEqual([str(self.root/'collector.py')],self.s['harness']['runs']['fresh-owner-run']['execution_paths']);self.assertEqual('new-owner',self.s['harness']['runs']['fresh-owner-run']['member'])
 def test_changed_external_permission_disables_old_begin(self):
  self.s=h.apply(self.s,self.correction(),self.root);self.ack();self.permission.write_text(json.dumps({'allowed':False,'paths':[str(self.root/'collector.py')]}))
  with self.assertRaises(h.Invalid):self.ev('begin',task='task',member='owner',run='denied-old-authority')
 def test_fresh_permission_and_scoped_review_can_reauthorize_without_hiding_corruption(self):
  self.s=h.apply(self.s,self.correction(),self.root);self.permission.write_text(json.dumps({'allowed':True,'paths':[str(self.root/'collector.py')],'source':'Synthetic current renewed permission evidence'}));self.cause.write_text(json.dumps({'category':'permission_renewal','pending_request':'correct','reason':'Existing permission evidence changed before the work ever executed'}));e=self.correction(request_id='renewed',previous_request_id='correct',prior_method=self.new,method=self.new,legacy_seed=None,renew_authorization=True);self.approve(e,correction_authority_verified=True,authority_renewal_only=True,material_method_change=False);self.s=h.apply(self.s,e,self.root);self.ack();self.ev('begin',task='task',member='owner',run='renewed-work');self.assertEqual('active',self.s['harness']['runs']['renewed-work']['state'])
  self.s['harness']['reworks']['renewed']['authority_bytes_base64']='e30='
  with self.assertRaises(h.Invalid):h.packet(self.s,'owner')
 def test_authority_renewal_cannot_replay_an_already_executed_method(self):
  self.s=h.apply(self.s,self.correction(),self.root);self.ack();self.ev('begin',task='task',member='owner',run='already-ran');self.ev('finish',run='already-ran',outcome='completed',evidence='terminal');self.ev('handoff',task='task',artifacts=[str(self.proof)]);self.permission.write_text(json.dumps({'allowed':True,'paths':[str(self.root/'collector.py')],'source':'Renewed'}));self.cause.write_text(json.dumps({'category':'permission_renewal','pending_request':'correct','reason':'Must not replay consumed method'}));e=self.correction(request_id='replay',previous_request_id='correct',prior_method=self.new,method=self.new,legacy_seed=None,renew_authorization=True);self.approve(e,correction_authority_verified=True,authority_renewal_only=True,material_method_change=False)
  with self.assertRaises(h.Invalid):h.apply(self.s,e,self.root)

if __name__=='__main__':unittest.main()
