import copy,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'payload/team-coordination/scripts'))
import harness as h
import session_control as c
from unittest import mock

class ExternalHandoff(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name).resolve();self.path=self.root/'state.json';self.claim=self.root/'src';self.claim.mkdir();(self.claim/'a').write_text('uncommitted');(self.claim/'empty').mkdir()
  self.identity={'host':'durable','transport':'codex-app','controller':'source-owner','thread':'external-thread','owned':False}
  self.identity_proof=self.root/'identity';self.identity_proof.write_text('actual identity claim')
  s=h.initial('fixture')
  for e in [{'op':'register','member':'source','role':'core','identity':str(self.identity_proof)},{'op':'assign','member':'source','task':'task','purpose':'implementation','context':'decisions and failure retained','kind':'implementation'},{'op':'claim','task':'task','paths':[str(self.claim)]}]:s=h.apply(s,e)
  h.save(self.path,s);self.ctl=c.Controller(self.path,None,'new-controller','local','official-owned-stdio')
  self.observation=self.root/'observation.json';self.stop=self.root/'stop.json';self.write_observation()
  self.packet={'goal':'fixture','decisions':[{'decision':'retain code','rationale':'existing evidence'}],'constraints':['original ceiling'],'remaining_work':['implement'],'permission_ceiling':{'sandbox':'read-only','publication':False}}
  self.stop.write_text(json.dumps({'source_identity':self.identity,'execution_stopped':True,'commands_drained':True,'stopped_turn':'stopped-turn','project_revision':self.ctl.state()['harness']['revision'],'owner_ack_quote':'Owner confirms execution stopped and commands drained.','permission_ceiling':self.packet['permission_ceiling'],'observation_sha256':h.ledger.evidence(self.observation)['sha256']}))
 def tearDown(self):self.tmp.cleanup()
 def write_observation(self,**changes):
  if hasattr(self,'stop')and self.stop.exists():self.observation=self.root/'refresh.json'
  self.observation.write_text(json.dumps(dict({'source_identity':self.identity,'tool':'codex_app.read_thread','status':'idle','turn':'stopped-turn','turn_status':'completed','final_text':'Owner confirms execution stopped and commands drained.'},**changes)))
 def prepare(self,hid='one',**kw):
  return self.ctl.prepare_handoff(hid,'source','recipient','core',['task'],self.packet,str(self.stop),explicit_request=True,external_source={'identity':self.identity,'observation':str(self.observation)},expected_revision=self.ctl.state()['harness']['revision'],**kw)
 def test_external_prepare_never_queries_an_unavailable_source(self):
  packet=self.prepare();s=self.ctl.state();self.assertEqual(self.identity,packet['source_identity']);self.assertEqual('operator_attestation_with_supported_tool_evidence',s['harness']['handoffs']['one']['source_provenance']['scope']);self.assertEqual('paused',s['harness']['sessions']['source']['execution']);self.assertEqual('unavailable',s['harness']['sessions']['source']['runtime_observed']['status']);self.assertNotIn('configured_observed',s['harness']['sessions']['source'])
 def test_external_stop_requires_exact_identity_drained_stopped_turn_and_revision(self):
  original=json.loads(self.stop.read_text())
  for key,bad in [('execution_stopped',False),('commands_drained',False),('stopped_turn','other'),('project_revision',-1),('source_identity',dict(self.identity,host='other'))]:
   with self.subTest(key=key):
    self.stop.write_text(json.dumps(dict(original,**{key:bad})))
    with self.assertRaises(h.Invalid):self.prepare()
    self.assertNotIn('source',self.ctl.state()['harness'].get('sessions',{}))
  self.stop.write_text(json.dumps(original));self.write_observation(status='active')
  with self.assertRaises(h.Invalid):self.prepare()
 def test_duplicate_and_overlapping_handoffs_do_not_create_new_intents(self):
  self.prepare()
  with self.assertRaises(h.Invalid):self.prepare('two')
  self.ctl.event('control_handoff_intent',handoff='one',phase='creation_pending');self.ctl.event('control_handoff_failure',handoff='one',reason='disconnected',unknown=True)
  with self.assertRaises(h.Invalid):self.prepare('three')
 def test_directory_baseline_retains_claim_and_detects_tree_content_mode_and_links(self):
  before=c.baseline([str(self.claim)]);self.assertEqual([str(self.claim)],list(before));self.assertIn('empty',before[str(self.claim)]['entries'])
  (self.claim/'a').write_text('changed');self.assertNotEqual(before,c.baseline([str(self.claim)]));(self.claim/'a').write_text('uncommitted');(self.claim/'a').chmod(0o755);self.assertNotEqual(before,c.baseline([str(self.claim)]))
  (self.claim/'alias').symlink_to(self.root/'outside')
  with self.assertRaises(h.Invalid):c.baseline([str(self.claim)])
 def recipient(self):
  self.prepare();s=self.ctl.state();x=s['harness']['handoffs']['one']
  for e in [{'op':'control_handoff_intent','handoff':'one','phase':'creation_pending'},{'op':'control_recipient','handoff':'one','identity':dict(self.ctl.identity,thread='new-thread',owned=True),'model':'gpt-6.1-sol','effort':'high'},{'op':'control_handoff_intent','handoff':'one','phase':'delivery_pending'},{'op':'control_packet_received','handoff':'one','turn':'receipt-turn','text':c.ack_text(x),'observation':{'thread':'new-thread','model':'gpt-6.1-sol','reasoning_effort':'high','scope':'live','status':'idle'}}]:s=h.apply(s,e)
  h.save(self.path,s)
  class RPC:
   def request(_,method,params):
    if method!='thread/read'or params['threadId']!='new-thread':raise AssertionError('No source query permitted')
    return {'thread':{'id':'new-thread','model':'gpt-6.1-sol','reasoningEffort':'high','status':{'type':'idle'}}}
  self.ctl.rpc=RPC()
 def test_external_transfer_requires_fresh_supported_observation_and_preserves_fail(self):
  s=self.ctl.state();s['tasks']['task']['state']='ready_for_review';s['tasks']['task']['reviews']=[{'verdict':'fail','reason':'retain'}];s['harness']['work_authorizations']={'task':'old'};h.save(self.path,s);self.recipient();history=copy.deepcopy(self.ctl.state()['tasks']['task'])
  with self.assertRaises(h.Invalid):self.ctl.transfer('one')
  self.write_observation();self.ctl.transfer('one',external_observation=str(self.observation));s=self.ctl.state();history['owner']='recipient';self.assertEqual(history,s['tasks']['task']);self.assertNotIn('task',s['harness']['work_authorizations']);self.assertEqual('disabled',s['harness']['sessions']['source']['execution']);self.assertNotIn('ack',s['harness']['profiles']['recipient'])
 def test_changed_source_turn_or_claim_tree_blocks_transfer(self):
  self.recipient();self.write_observation(turn='restarted')
  with self.assertRaises(h.Invalid):self.ctl.transfer('one',external_observation=str(self.observation))
  self.write_observation();(self.claim/'new-file').write_text('new')
  with self.assertRaises(h.Invalid):self.ctl.transfer('one',external_observation=str(self.observation))
  self.assertEqual('source',self.ctl.state()['tasks']['task']['owner'])
 def test_replaced_checkpoint_link_never_opens_target_during_transfer(self):
  self.recipient();self.write_observation();outside=self.root/'outside-checkpoint.json';outside.write_bytes(self.stop.read_bytes());self.stop.unlink();self.stop.symlink_to(outside);original=Path.open
  def checked(path,*args,**kwargs):
   if path==outside:raise AssertionError('Replaced evidence target was opened')
   return original(path,*args,**kwargs)
  with mock.patch.object(Path,'open',checked):
   with self.assertRaises(h.Invalid):self.ctl.transfer('one',external_observation=str(self.observation))

if __name__=='__main__':unittest.main()

class BoundedWriting(ExternalHandoff):
 def writable(self):
  value={'sandbox':'workspace-write','publication':False,'writable_roots':[str(self.claim)],'network_access':False,'approval_policy':'on-request','approvals_reviewer':'auto_review'}
  self.packet['permission_ceiling']=value;stop=json.loads(self.stop.read_text());stop['permission_ceiling']=value;self.stop.write_text(json.dumps(stop));return value
 def test_write_ceiling_rejects_parent_and_state_roots_and_preserves_original(self):
  self.writable();self.prepare();self.assertEqual(self.packet['permission_ceiling'],self.ctl.state()['harness']['handoffs']['one']['packet']['permission_ceiling'])
  import external_handoff as x
  for roots in ([str(self.root)],[str(self.root/'sibling')]):
   with self.assertRaises(h.Invalid):x.ceiling(dict(self.packet['permission_ceiling'],writable_roots=roots),[str(self.claim)],str(self.path))
  with self.assertRaises(h.Invalid):x.ceiling(dict(self.packet['permission_ceiling'],writable_roots=[str(self.root)]),[str(self.root)],str(self.path))
 def test_creation_requires_exact_official_policy_and_scoped_cwd(self):
  import external_handoff as x
  value=self.writable();params=x.creation(value,str(self.claim));self.assertEqual('auto_review',params['approvalsReviewer']);self.assertEqual('on-request',params['approvalPolicy']);self.assertTrue(params['config']['sandbox_workspace_write']['exclude_slash_tmp'])
  with self.assertRaises(h.Invalid):x.creation(value,str(self.root))
  response={'cwd':str(self.claim),'sandbox':x.sandbox(value),'approvalPolicy':'on-request','approvalsReviewer':'auto_review'};x.verify_creation(response,value,str(self.claim))
  for key,bad in [('sandbox',dict(x.sandbox(value),writableRoots=[str(self.root)])),('approvalsReviewer','user'),('approvalPolicy','never'),('cwd',str(self.root))]:
   with self.assertRaises(h.Invalid):x.verify_creation(dict(response,**{key:bad}),value,str(self.claim))
 def test_precreation_scope_failure_never_sends_rpc_or_leaves_unknown_intent(self):
  self.writable();self.prepare()
  import profile_defaults as profiles
  class RPC:
   tier_contract=profiles.CURRENT_TIER_CONTRACT
   def request(_,method,params):
    if method=='model/list':return {'data':[{'model':'gpt-6.1-sol','supportedReasoningEfforts':[{'reasoningEffort':'high'}]}],'nextCursor':None}
    raise AssertionError('Scope rejected before RPC')
  self.ctl.rpc=RPC()
  with self.assertRaises(h.Invalid):self.ctl.create_recipient('one','high',str(self.root))
  self.assertEqual('prepared',self.ctl.state()['harness']['handoffs']['one']['state'])
 def test_permission_readback_failure_retains_returned_official_identity(self):
  self.writable();self.prepare()
  import profile_defaults as profiles
  class RPC:
   tier_contract=profiles.CURRENT_TIER_CONTRACT
   def request(_,method,params):
    if method=='model/list':return {'data':[{'model':'gpt-6.1-sol','supportedReasoningEfforts':[{'reasoningEffort':'high'}]}],'nextCursor':None}
    if method=='thread/start':return {'thread':{'id':'actual-created'},'model':'gpt-6.1-sol','reasoningEffort':'high','cwd':str(self.claim),'sandbox':{'type':'workspaceWrite','writableRoots':[str(self.root)]},'approvalPolicy':'never'}
    raise AssertionError(method)
  self.ctl.rpc=RPC()
  with self.assertRaises(h.Invalid):self.ctl.create_recipient('one','high',str(self.claim))
  x=self.ctl.state()['harness']['handoffs']['one'];self.assertEqual('actual-created',x['creation_receipt']['identity']['thread']);self.assertEqual('outcome_unknown',x['state']);self.assertNotIn('recipient',self.ctl.state()['members'])
 def test_official_normalized_implicit_cwd_is_equal_effective_scope(self):
  import external_handoff as x
  value=self.writable();actual=x.sandbox(value);actual['writableRoots']=[]
  x.verify_creation({'cwd':str(self.claim),'sandbox':actual,'approvalPolicy':'on-request','approvalsReviewer':'auto_review'},value,str(self.claim))
  actual['writableRoots']=[str(self.root)]
  with self.assertRaises(h.Invalid):x.verify_creation({'cwd':str(self.claim),'sandbox':actual,'approvalPolicy':'on-request','approvalsReviewer':'auto_review'},value,str(self.claim))
 def test_reconcile_known_creation_uses_exact_id_without_new_thread_start(self):
  self.writable();self.prepare();self.ctl.event('control_handoff_intent',handoff='one',phase='creation_pending')
  identity=dict(self.ctl.identity,thread='known-created',owned=True)
  self.ctl.event('control_creation_receipt',handoff='one',identity=identity,configured={});self.ctl.event('control_handoff_failure',handoff='one',reason='readback',unknown=True)
  import profile_defaults as profiles,external_handoff as x
  class RPC:
   tier_contract=profiles.CURRENT_TIER_CONTRACT
   def request(_,method,params):
    if method=='model/list':return {'data':[{'model':'gpt-6.1-sol','supportedReasoningEfforts':[{'reasoningEffort':'high'}]}],'nextCursor':None}
    if method=='thread/resume':
     self.assertEqual({'threadId':'known-created','excludeTurns':True},params)
     return {'thread':{'id':'known-created'},'model':'gpt-6.1-sol','reasoningEffort':'high','cwd':str(self.claim),'sandbox':x.sandbox(self.packet['permission_ceiling']),'approvalPolicy':'on-request','approvalsReviewer':'auto_review'}
    if method=='thread/read':return {'thread':{'id':'known-created','model':'gpt-6.1-sol','reasoningEffort':'high','status':{'type':'idle'}}}
    raise AssertionError('No new thread permitted: '+method)
  self.ctl.rpc=RPC();self.assertEqual('known-created',self.ctl.reconcile_recipient('one','high',str(self.claim)));self.assertEqual('recipient_created',self.ctl.state()['harness']['handoffs']['one']['state'])
 def test_idle_observation_without_actual_owner_ack_quote_is_not_stop_evidence(self):
  stop=json.loads(self.stop.read_text());stop.pop('owner_ack_quote',None);self.stop.write_text(json.dumps(stop))
  with self.assertRaises(h.Invalid):self.prepare()
 def test_stale_contract_packet_turn_cannot_dispatch(self):
  self.prepare();s=self.ctl.state();x=s['harness']['handoffs']['one'];s=h.apply(s,{'op':'control_handoff_intent','handoff':'one','phase':'creation_pending'});s=h.apply(s,{'op':'control_recipient','handoff':'one','identity':dict(self.ctl.identity,thread='created',owned=True),'model':'gpt-6.1-sol','effort':'high'});s['harness']['policy_hash']='stale';h.save(self.path,s)
  calls=[]
  import profile_defaults as profiles
  class RPC:
   tier_contract=profiles.CURRENT_TIER_CONTRACT
   def request(_,method,params):
    calls.append(method)
    if method=='thread/read':return {'thread':{'id':'created','model':'gpt-6.1-sol','reasoningEffort':'high','status':{'type':'idle'}}}
    if method=='model/list':return {'data':[{'model':'gpt-6.1-sol','supportedReasoningEfforts':[{'reasoningEffort':'high'}]}],'nextCursor':None}
    raise AssertionError('Stale contract must not dispatch')
  self.ctl.rpc=RPC()
  try:self.ctl.deliver_packet('one')
  except Exception:pass
  self.assertNotIn('turn/start',calls)
