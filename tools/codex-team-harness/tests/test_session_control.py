import copy,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'payload/team-coordination/scripts'))
import harness as h
import session_control as c

def observed(model='gpt-6.1-sol',effort='low',status='idle'):
 return {'thread':{'id':'source','model':model,'reasoningEffort':effort,'modelProvider':'openai','status':{'type':status}}}
CATALOG=[{'id':'picker-sol','model':'gpt-6.1-sol','supportedReasoningEfforts':[{'reasoningEffort':'low'}]}, {'id':'picker-astra','model':'gpt-6-astra','supportedReasoningEfforts':[{'reasoningEffort':'low'}]}]

class Sessions(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.path=self.root/'state.json';self.proof=self.root/'proof';self.proof.write_text(json.dumps({'source':'source','controller':'fixture-controller','commands_drained':True,'execution_stopped':True}))
  s=h.initial('fixture')
  for event in [{'op':'register','member':'source-owner','role':'core','identity':str(self.proof)}, {'op':'assign','member':'source-owner','task':'task','purpose':'sample','context':'fixture','kind':'implementation'}, {'op':'claim','task':'task','paths':[str(self.root/'sample')]}]:s=h.apply(s,event)
  (self.root/'sample').write_text('uncommitted sample')
  h.save(self.path,s)
  self.controller=c.Controller(self.path,None,'fixture-controller','local','official-owned-stdio')
  class RPC:
   def request(self,method,params):
    value=observed();value['thread']['id']=params['threadId'];return value
  self.controller.rpc=RPC()
  self.controller.bind('source-owner','source',owned=True)
 def tearDown(self):self.tmp.cleanup()
 def test_missing_and_persisted_are_not_live_gates(self):
  for response in ({'thread':{'id':'source','status':{'type':'idle'}}},observed(status='notLoaded')):
   obs=c.configuration(response)
   self.assertFalse(c.matches(obs,'gpt-6.1-sol','low'))
  self.assertEqual('persisted',c.configuration(observed(status='notLoaded'))['scope'])
 def test_catalog_requestable_model_not_picker_id(self):
  c.validate_choice(CATALOG,'gpt-6.1-sol','low')
  with self.assertRaises(c.ControlError):c.validate_choice(CATALOG,'picker-sol','low')
  with self.assertRaises(c.ControlError):c.validate_choice(CATALOG,'gpt-6.1-sol','ultra')
 def test_unapplied_request_does_not_turn_matching_configuration_into_drift(self):
  state=self.controller.state();value=state['harness']['sessions']['source-owner'];value['managed']=True;value['policy_expected']['reasoning_effort']='low';h.save(self.path,state)
  requested_model='gpt-6-astra'
  observation=self.controller.inspect('source-owner')
  self.assertFalse(c.matches(observation,requested_model,'low'))
  self.assertTrue(c.matches(observation,'gpt-6.1-sol','low'))
  c.gate(self.controller.state(),'source-owner','implementation',observation)
 def test_advisor_implementation_refused_at_assignment(self):
  s=json.loads(self.path.read_text());s=h.apply(s,{'op':'register','member':'advisor','role':'advisor','identity':str(self.proof)})
  with self.assertRaises(h.Invalid):h.apply(s,{'op':'assign','task':'bad','member':'advisor','purpose':'code','context':'x','kind':'implementation'})
 def test_unknown_kind_refused(self):
  with self.assertRaises(h.Invalid):h.apply(json.loads(self.path.read_text()),{'op':'assign','task':'bad','member':'source-owner','purpose':'x','context':'x','kind':'magic'})
 def test_change_queued_busy_and_no_implicit_retry(self):
  class RPC:
   def request(self,method,params):
    if method=='model/list':return {'data':CATALOG,'nextCursor':None}
    if method=='thread/read':return observed(status='active')
    raise AssertionError('must not mutate busy session')
  self.controller.rpc=RPC();r=self.controller.change('source-owner','change1','gpt-6.1-sol','low')
  self.assertEqual('queued',r['state'])
  with self.assertRaises(h.Invalid):self.controller.change('source-owner','change1','gpt-6.1-sol','low')
 def test_timeout_intent_retained_and_gate_blocks(self):
  class RPC:
   def request(self,method,params):
    if method=='model/list':return {'data':CATALOG,'nextCursor':None}
    if method=='thread/read':return observed()
    raise TimeoutError('unknown')
  self.controller.rpc=RPC()
  self.controller.change('source-owner','change1','gpt-6.1-sol','low')
  with self.assertRaises(TimeoutError):self.controller.apply_change('source-owner','change1',2048)
  s=json.loads(self.path.read_text());self.assertEqual('outcome_unknown',s['harness']['controls']['change1']['state'])
  with self.assertRaises(h.Invalid):c.gate(s,'source-owner','implementation')
 def test_external_requires_owner_checkpoint(self):
  state=self.controller.state();state['harness']['sessions']['source-owner']['identity']['owned']=False;h.save(self.path,state)
  with self.assertRaises(c.ControlError):self.controller.require_control('source-owner')
 def prepare(self):
  return self.controller.prepare_handoff('handoff1','source-owner','dest','core',['task'],{'goal':'fixture','decisions':[],'constraints':[],'remaining_work':['inspect sample'],'permission_ceiling':{'sandbox':'read-only','publication':False}},str(self.proof),explicit_request=True)
 def test_prepare_pauses_source_but_keeps_owner(self):
  packet=self.prepare();s=json.loads(self.path.read_text())
  self.assertEqual('source-owner',s['tasks']['task']['owner']);self.assertEqual('paused',s['harness']['sessions']['source-owner']['execution'])
  self.assertIn('baseline',packet)
  with self.assertRaises(h.Invalid):c.gate(s,'source-owner','implementation')
 def test_handoff_requires_explicit_request(self):
  with self.assertRaises(h.Invalid):self.controller.prepare_handoff('x','source-owner','dest','core',['task'],{},str(self.proof),explicit_request=False)
 def recipient(self):
  packet=self.prepare();s=json.loads(self.path.read_text());x=s['harness']['handoffs']['handoff1']
  for event in [{'op':'control_handoff_intent','handoff':'handoff1','phase':'creation_pending'}, {'op':'control_recipient','handoff':'handoff1','identity':{'host':'local','transport':'official-owned-stdio','thread':'dest-thread','controller':'fixture-controller','owned':True},'model':'gpt-6.1-sol','effort':'low'}, {'op':'control_handoff_intent','handoff':'handoff1','phase':'delivery_pending'}, {'op':'control_packet_received','handoff':'handoff1','turn':'packet-turn','text':c.ack_text(x),'observation':c.configuration({'thread':{'id':'dest-thread','model':'gpt-6.1-sol','reasoningEffort':'low','status':{'type':'idle'}}})}]:s=h.apply(s,event)
  h.save(self.path,s)
  class RPC:
   def request(self,method,params):
    value=observed();value['thread']['id']=params['threadId'];return value
  self.controller.rpc=RPC();return packet
 def test_missing_real_packet_receipt_blocks_transfer(self):
  self.prepare()
  with self.assertRaises(h.Invalid):h.transaction(self.path,{'op':'control_transfer','handoff':'handoff1','source_status':'idle','recipient_status':'idle'})
 def test_atomic_transfer_and_revision_owner_ack(self):
  self.recipient();r=self.controller.transfer('handoff1');s=json.loads(self.path.read_text())
  self.assertEqual('dest',s['tasks']['task']['owner']);self.assertEqual('disabled',s['harness']['sessions']['source-owner']['execution'])
  self.assertEqual('paused',s['harness']['sessions']['dest']['execution'])
  with self.assertRaises(h.Invalid):h.transaction(self.path,{'op':'control_owner_ack','handoff':'handoff1','revision':r-1,'evidence':str(self.proof)})
  with self.assertRaises(h.Invalid):h.transaction(self.path,{'op':'control_owner_ack','handoff':'handoff1','revision':r,'evidence':str(self.proof)})
  x=s['harness']['handoffs']['handoff1'];ack=self.root/'transfer-ack.json';ack.write_text(json.dumps({'handoff':'handoff1','recipient':'dest','transfer_revision':r,'transfer_nonce':x['transfer_nonce']}))
  h.transaction(self.path,{'op':'control_owner_ack','handoff':'handoff1','revision':r,'evidence':str(ack)})
  self.assertEqual('acknowledged',json.loads(self.path.read_text())['harness']['handoffs']['handoff1']['state'])
 def test_changed_baseline_retains_source_paused(self):
  self.recipient();(self.root/'sample').write_text('intervening edit')
  with self.assertRaises(h.Invalid):self.controller.transfer('handoff1')
  s=json.loads(self.path.read_text());self.assertEqual('source-owner',s['tasks']['task']['owner']);self.assertEqual('paused',s['harness']['sessions']['dest']['execution'])
 def test_hash_ack_without_exact_nonce_rejected(self):
  self.prepare();s=json.loads(self.path.read_text());x=s['harness']['handoffs']['handoff1']
  with self.assertRaises(h.Invalid):h.apply(s,{'op':'control_packet_received','handoff':'handoff1','turn':'t','text':x['packet_hash'],'observation':c.configuration(observed())})
 def test_catalog_pagination(self):
  class RPC:
   def request(self,method,params):return {'data':CATALOG[:1]if not params['cursor']else CATALOG[1:],'nextCursor':'next'if not params['cursor']else None}
  self.controller.rpc=RPC();self.assertEqual(CATALOG,self.controller.catalog())
 def test_usage_is_last_turn_not_cumulative(self):
  self.assertEqual(7,c.turn_usage({'tokenUsage':{'last':{'totalTokens':7},'total':{'totalTokens':100007}}}))
  self.assertIsNone(c.turn_usage({'tokenUsage':{'total':{'totalTokens':100007}}}))
 def test_new_leader_needs_explicit_model_and_coordination_only(self):
  packet={'goal':'coordinate','decisions':[],'constraints':[],'remaining_work':[],'permission_ceiling':{'sandbox':'read-only','publication':False}}
  with self.assertRaises(h.Invalid):self.controller.prepare_handoff('leader','source-owner','leader','leader',['task'],packet,str(self.proof),True,'gpt-6.1-sol')
  s=self.controller.state();s['tasks']['task']['kind']='coordination';h.save(self.path,s)
  with self.assertRaises(h.Invalid):self.controller.prepare_handoff('leader','source-owner','leader','leader',['task'],packet,str(self.proof),True)
  self.controller.prepare_handoff('leader','source-owner','leader','leader',['task'],packet,str(self.proof),True,'gpt-6.1-sol')
  self.assertEqual('gpt-6.1-sol',self.controller.state()['harness']['handoffs']['leader']['selected_model'])
 def test_pause_cannot_rebind(self):
  self.prepare()
  with self.assertRaises(h.Invalid):self.controller.bind('source-owner','source',owned=True)
 def test_paused_disabled_source_configuration_never_calls_rpc(self):
  class NoRPC:
   def request(self,*args,**kwargs):raise AssertionError('paused/disabled source must not call RPC')
  for execution in ('paused','disabled'):
   state=self.controller.state();state['harness']['sessions']['source-owner']['execution']=execution;state['harness']['controls']={'pending':{'member':'source-owner','state':'pending_turn_application','requested':{'model':'gpt-6.1-sol','reasoning_effort':'low'}}};h.save(self.path,state);self.controller.rpc=NoRPC()
   with self.assertRaises(h.Invalid):self.controller.apply_change('source-owner','pending',100)
   with self.assertRaises(h.Invalid):self.controller.change('source-owner','fresh','gpt-6.1-sol','low')
 def test_wrong_read_identity_refused(self):
  class RPC:
   def request(self,method,params):return {'thread':{'id':'different','model':'gpt-6.1-sol','reasoningEffort':'low','status':{'type':'idle'}}}
  self.controller.rpc=RPC()
  with self.assertRaises(h.Invalid):self.controller.inspect('source-owner')
 def test_unknown_change_blocks_fresh_id(self):
  self.controller.event('control_intent',member='source-owner',operation='unknown',state='outcome_unknown',requested={})
  with self.assertRaises(h.Invalid):self.controller.event('control_intent',member='source-owner',operation='fresh-id',state='request_pending',requested={})
 def test_packet_inference_requires_budget(self):
  self.prepare();s=self.controller.state();s['harness']['budget']=0;h.save(self.path,s)
  with self.assertRaises(h.Invalid):self.controller.event('control_intent',member='source-owner',operation='packet',state='request_pending',requested={'packet_reserve':2048})
 def test_configuration_inference_rejects_zero_missing_negative_reserve(self):
  class NoRPC:
   def request(self,*args,**kwargs):raise AssertionError('invalid reservation must not call RPC')
  self.controller.rpc=NoRPC()
  for reserve in (0,None,-1,True):
   with self.assertRaises(h.Invalid):self.controller.apply_change('source-owner','pending',reserve)
   with self.assertRaises(h.Invalid):self.controller.event('control_intent',member='source-owner',operation='config',state='request_pending',requested={'application_for':'change','packet_reserve':reserve})
 def test_pretransfer_revision_change_keeps_source(self):
  self.recipient();h.transaction(self.path,{'op':'change','instruction':'new constraint'})
  with self.assertRaises(h.Invalid):self.controller.transfer('handoff1')
  self.assertEqual('source-owner',self.controller.state()['tasks']['task']['owner'])

if __name__=='__main__':unittest.main()
