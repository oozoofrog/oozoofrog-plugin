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
 def standard_rpc(self,reject=False,contract=True):
  import profile_defaults as profiles
  class RPC:
   calls=[];turn_count=0;tier_contract=profiles.CURRENT_TIER_CONTRACT if contract else None
   def request(self,method,params,**kwargs):
    self.calls.append((method,json.loads(json.dumps(params))))
    if method=='model/list':return {'data':[dict(x,serviceTiers=[{'id':'priority','name':'Fast'}],defaultServiceTier='priority')for x in CATALOG],'nextCursor':None}
    if method=='thread/read':return observed()
    if method=='turn/start':
     if reject:
      from managed_run import RPCError
      raise RPCError(method,{'code':-32602,'message':'Unsupported serviceTierForTurn'})
     self.turn_count+=1;return {'turn':{'id':'turn-'+str(self.turn_count)}}
    raise AssertionError('No tier observation mutation permitted: '+method)
   def next(self,*args):return {'method':'turn/completed','params':{'threadId':'source','turn':{'id':'turn-'+str(self.turn_count),'status':'completed'}}}
   def handle_request(self,event):pass
  self.controller.rpc=RPC();return self.controller.rpc
 def standard_owner(self):
  import profile_defaults as profiles
  state=self.controller.state();value=state['harness']['sessions']['source-owner'];value.update(managed=True);value['policy_expected'].update(reasoning_effort='low',service_tier='normal',tier_resolution=profiles.resolve_service_tier(CATALOG,'gpt-6.1-sol','normal'))
  packet=h.packet(state,'source-owner');state=h.apply(state,{'op':'ack','member':'source-owner','revision':packet['revision'],'epoch':packet['epoch'],'digest':h.digest(packet)});h.save(self.path,state)
 def test_normal_ordinary_turn_is_local_and_has_only_request_acknowledgement(self):
  self.standard_owner();rpc=self.standard_rpc();self.controller.turn('source-owner','inspect',task='task')
  params=next(p for method,p in rpc.calls if method=='turn/start')
  self.assertEqual({'threadId':'source','input':[{'type':'text','text':'inspect','text_elements':[]}],'serviceTierForTurn':'default'},params)
  state=self.controller.state();receipt=next(v for v in state['harness']['controls'].values()if v.get('accepted'))['accepted'];self.assertEqual('request_acknowledgement_only',receipt['scope']);self.assertEqual({'serviceTierForTurn':'default'},receipt['tier_parameters']);self.assertEqual('unavailable',state['harness']['sessions']['source-owner']['runtime_observed']['status']);self.assertNotIn('service_tier_observed',state['harness']['sessions']['source-owner'])
 def test_normal_configuration_turn_does_not_change_persistent_tier_or_resume(self):
  rpc=self.standard_rpc();self.controller.change('source-owner','normal','gpt-6.1-sol','low',service_tier='normal');self.controller.apply_change('source-owner','normal')
  params=next(p for method,p in rpc.calls if method=='turn/start');self.assertEqual('default',params['serviceTierForTurn']);self.assertNotIn('serviceTier',params);self.assertEqual('low',params['effort']);self.assertNotIn('thread/resume',[m for m,p in rpc.calls]);self.assertEqual('configuration_pending_turn',self.controller.state()['harness']['controls']['normal']['state'])
 def test_repeated_standard_turns_and_verification_never_infer_persistent_tier(self):
  self.standard_owner();rpc=self.standard_rpc();self.controller.change('source-owner','normal','gpt-6.1-sol','low',service_tier='normal');self.controller.apply_change('source-owner','normal')
  packet=h.packet(self.controller.state(),'source-owner');h.transaction(self.path,{'op':'ack','member':'source-owner','revision':packet['revision'],'epoch':packet['epoch'],'digest':h.digest(packet)})
  first=self.controller.turn('source-owner','first',task='task');proof=self.controller.verify_after_turn('source-owner','normal',first['turn'])
  self.assertEqual({'model_reasoning':'configured_observed','service_tier':'accepted_per_turn_only','persistent_service_tier':'unavailable','provider_execution':'unavailable'},proof['verification_scope'])
  packet=h.packet(self.controller.state(),'source-owner');h.transaction(self.path,{'op':'ack','member':'source-owner','revision':packet['revision'],'epoch':packet['epoch'],'digest':h.digest(packet)})
  self.controller.turn('source-owner','second',task='task')
  turns=[p for method,p in rpc.calls if method=='turn/start'];self.assertEqual(3,len(turns));self.assertTrue(all(p.get('serviceTierForTurn')=='default'and 'serviceTier'not in p for p in turns));self.assertNotIn('thread/resume',[m for m,p in rpc.calls])
 def test_model_effort_change_without_tier_preserves_requested_standard(self):
  self.standard_owner();rpc=self.standard_rpc();self.controller.change('source-owner','effort-only','gpt-6.1-sol','low');self.controller.apply_change('source-owner','effort-only')
  packet=h.packet(self.controller.state(),'source-owner');h.transaction(self.path,{'op':'ack','member':'source-owner','revision':packet['revision'],'epoch':packet['epoch'],'digest':h.digest(packet)})
  self.controller.turn('source-owner','next',task='task')
  turns=[p for method,p in rpc.calls if method=='turn/start'];self.assertEqual(2,len(turns));self.assertTrue(all(p.get('serviceTierForTurn')=='default'and 'serviceTier'not in p for p in turns))
  self.assertEqual('normal',self.controller.state()['harness']['sessions']['source-owner']['policy_expected']['service_tier'])
 def test_change_without_prior_tier_keeps_current_role_normal_default(self):
  rpc=self.standard_rpc();self.controller.change('source-owner','default-role','gpt-6.1-sol','low');self.controller.apply_change('source-owner','default-role')
  params=next(p for method,p in rpc.calls if method=='turn/start');self.assertEqual('default',params.get('serviceTierForTurn'));self.assertNotIn('serviceTier',params)
 def test_fast_verification_retains_configured_evidence_scope(self):
  rpc=self.standard_rpc();request=rpc.request
  def resume(method,params,**kwargs):
   if method=='thread/resume':return {'thread':{'id':'source'},'model':'gpt-6.1-sol','reasoningEffort':'low','serviceTier':'priority'}
   return request(method,params,**kwargs)
  rpc.request=resume;state=self.controller.state();state['harness']['controls']={'fast':{'member':'source-owner','state':'configuration_pending_turn','configuration_time_ns':0,'requested':{'model':'gpt-6.1-sol','reasoning_effort':'low','service_tier':'fast','tier_resolution':{'wire_id':'priority'}}},'later':{'member':'source-owner','state':'completed','turn':'later','intent_time_ns':1}};h.save(self.path,state)
  proof=self.controller.verify_after_turn('source-owner','fast','later');self.assertEqual('configured_observed',proof['verification_scope']['service_tier']);self.assertEqual('configured_observed',proof['verification_scope']['persistent_service_tier']);self.assertEqual('unavailable',proof['verification_scope']['provider_execution'])
 def test_normal_packet_turn_also_gets_local_default(self):
  import profile_defaults as profiles
  self.standard_owner();rpc=self.standard_rpc();state=self.controller.state();state['harness']['handoffs']['packet']={'state':'recipient_created','source':'source-owner','recipient':'source-owner'};h.save(self.path,state)
  # Stop at the real request boundary: receipt failure cannot hide serialization.
  rpc.next=lambda *args:(_ for _ in ()).throw(TimeoutError('synthetic after request'))
  with self.assertRaises(TimeoutError):self.controller.turn('source-owner','packet',packet_handoff='packet')
  params=next(p for method,p in rpc.calls if method=='turn/start');self.assertEqual('default',params['serviceTierForTurn']);self.assertNotIn('serviceTier',params)
 def test_unknown_protocol_never_dispatches_or_claims_normal_unavailable(self):
  import profile_defaults as profiles
  self.standard_owner();rpc=self.standard_rpc(contract=False)
  with self.assertRaisesRegex(profiles.ProfileError,'protocol contract'):self.controller.turn('source-owner','inspect',task='task')
  self.assertNotIn('turn/start',[m for m,p in rpc.calls]);self.assertEqual({},self.controller.state()['harness'].get('controls',{}))
 def test_rejected_turn_field_has_no_retry_or_tier_fallback(self):
  from managed_run import RPCError
  self.standard_owner();rpc=self.standard_rpc(reject=True)
  with self.assertRaises(RPCError):self.controller.turn('source-owner','inspect',task='task')
  turns=[p for method,p in rpc.calls if method=='turn/start'];self.assertEqual(1,len(turns));self.assertEqual('default',turns[0]['serviceTierForTurn']);self.assertNotIn('serviceTier',turns[0]);self.assertEqual('not_executed',next(iter(self.controller.state()['harness']['runs'].values()))['state'])
 def test_post_completion_observation_error_preserves_completed_run(self):
  from managed_run import RPCError
  for error in (RPCError('thread/read',{'code':503,'message':'Unavailable'}),TimeoutError('Read timed out')):
   with self.subTest(error=type(error).__name__):
    self.standard_owner();rpc=self.standard_rpc();request=rpc.request;reads=0
    def fail_after_completion(method,params,**kwargs):
     nonlocal reads
     if method=='thread/read':
      reads+=1
      if reads==2:raise error
     return request(method,params,**kwargs)
    rpc.request=fail_after_completion
    with self.assertRaises(type(error)):self.controller.turn('source-owner','inspect',task='task')
    state=self.controller.state();run=list(state['harness']['runs'].values())[-1];control=list(state['harness']['controls'].values())[-1]
    self.assertEqual('completed',run['state']);self.assertEqual('completed',control['state'])
    self.assertEqual('turn-1',control['accepted']['turn']);self.assertFalse(control['automatic_retry'])
    self.assertNotIn('turn/interrupt',[method for method,params in rpc.calls])
 def test_rpc_error_after_acceptance_keeps_outcome_uncertain_and_blocks_new_run(self):
  from managed_run import RPCError
  self.standard_owner();rpc=self.standard_rpc()
  def failed_event(*args):raise RPCError('notification/read',{'code':503,'message':'Unavailable after acceptance'})
  rpc.next=failed_event
  with self.assertRaises(RPCError):self.controller.turn('source-owner','inspect',task='task')
  state=self.controller.state();run=next(iter(state['harness']['runs'].values()));control=next(iter(state['harness']['controls'].values()))
  self.assertEqual('uncertain',run['state']);self.assertEqual('outcome_unknown',control['state'])
  packet=h.packet(state,'source-owner');h.transaction(self.path,{'op':'ack','member':'source-owner','revision':packet['revision'],'epoch':packet['epoch'],'digest':h.digest(packet)})
  with self.assertRaises(h.Invalid):h.transaction(self.path,{'op':'begin','member':'source-owner','task':'task','run':'duplicate'})
 def test_accepted_receipt_turn_retains_cross_member_concurrency_slot(self):
  state=self.controller.state();state['harness']['concurrency']=1
  for event in [{'op':'register','member':'other','role':'core','identity':str(self.proof)},{'op':'assign','member':'other','task':'other-task','purpose':'inspect','context':'synthetic'}]:state=h.apply(state,event)
  packet=h.packet(state,'other');state=h.apply(state,{'op':'ack','member':'other','revision':packet['revision'],'epoch':packet['epoch'],'digest':h.digest(packet)});h.save(self.path,state)
  self.controller.bind('other','other-thread',owned=True)
  self.controller.event('control_intent',member='source-owner',operation='receipt',state='request_pending',requested={'kind':'turn','receipt_only':True})
  self.controller.event('control_result',operation='receipt',state='accepted_pending_observation',evidence={'accepted':{'turn':'still-running'}})
  with self.assertRaises(h.Invalid):self.controller.event('control_intent',member='other',operation='second',state='request_pending',requested={'kind':'turn','receipt_only':True})
  with self.assertRaises(h.Invalid):h.transaction(self.path,{'op':'begin','member':'other','task':'other-task','run':'second'})
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name).resolve();self.path=self.root/'state.json';self.proof=self.root/'proof';self.proof.write_text(json.dumps({'source':'source','controller':'fixture-controller','commands_drained':True,'execution_stopped':True}))
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
  import profile_defaults as profiles
  class RPC:
   tier_contract=profiles.CURRENT_TIER_CONTRACT
   def request(self,method,params):
    if method=='model/list':return {'data':CATALOG,'nextCursor':None}
    if method=='thread/read':return observed()
    raise TimeoutError('unknown')
  self.controller.rpc=RPC()
  self.controller.change('source-owner','change1','gpt-6.1-sol','low')
  with self.assertRaises(TimeoutError):self.controller.apply_change('source-owner','change1')
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
 def test_new_leader_defaults_astra_and_coordination_only(self):
  packet={'goal':'coordinate','decisions':[],'constraints':[],'remaining_work':[],'permission_ceiling':{'sandbox':'read-only','publication':False}}
  with self.assertRaises(h.Invalid):self.controller.prepare_handoff('leader','source-owner','leader','leader',['task'],packet,str(self.proof),True,'gpt-6.1-sol')
  s=self.controller.state();s['tasks']['task']['kind']='coordination';h.save(self.path,s)
  self.controller.prepare_handoff('leader','source-owner','leader','leader',['task'],packet,str(self.proof),True)
  self.assertEqual('gpt-6-astra',self.controller.state()['harness']['handoffs']['leader']['selected_model'])
 def test_tier_missing_substituted_and_stale_fail_gate(self):
  import time,profile_defaults as profiles
  state=self.controller.state();value=state['harness']['sessions']['source-owner'];value.update(managed=True,configured_observed=c.configuration(observed()),observed_monotonic_wall=time.time());value['policy_expected'].update(reasoning_effort='low',service_tier='fast',tier_resolution={'wire_id':'priority'})
  for receipt in ({},{'status':'observed','wire_service_tier':'default'},{'status':'observed','wire_service_tier':'priority'}):
   receipt.update(model='gpt-6.1-sol',reasoning_effort='low',generation=value['configuration_generation'],authorized_configured_receipt=True);value['service_tier_observed']=receipt;value['tier_observed_wall']=time.time() if receipt.get('wire_service_tier')!='priority' else 0
   with self.assertRaises(h.Invalid):c.gate(state,'source-owner','implementation')
  value['tier_observed_wall']=time.time();c.gate(state,'source-owner','implementation')
 def test_tier_receipt_model_effort_generation_and_notification_do_not_mix(self):
  import time
  state=self.controller.state();value=state['harness']['sessions']['source-owner'];value.update(managed=True,configured_observed=c.configuration(observed()),observed_monotonic_wall=time.time());value['policy_expected'].update(reasoning_effort='low',service_tier='fast',tier_resolution={'wire_id':'priority'})
  good={'thread_id':'source','model':'gpt-6.1-sol','reasoning_effort':'low','status':'observed','wire_service_tier':'priority','source':'thread/resume','generation':value['configuration_generation'],'authorized_configured_receipt':True};value.update(service_tier_observed=good,tier_observed_wall=time.time())
  c.gate(state,'source-owner','implementation')
  for key,bad in [('model','gpt-6-astra'),('reasoning_effort','ultra'),('generation','old'),('authorized_configured_receipt',False)]:
   value['service_tier_observed']=dict(good,**{key:bad})
   with self.assertRaises(h.Invalid):c.gate(state,'source-owner','implementation')
  value['service_tier_observed']=good;h.save(self.path,state)
  self.controller.observe_settings('source-owner',{'threadId':'source','threadSettings':{'model':'gpt-6.1-sol','effort':'low','serviceTier':'priority'}})
  self.assertNotIn('service_tier_observed',self.controller.state()['harness']['sessions']['source-owner'])
  with self.assertRaises(h.Invalid):self.controller.event('control_tier_observe',member='source-owner',observation=good,generation='old',response_bound=True)
 def test_changed_current_catalogue_never_sends_stored_tier(self):
  import profile_defaults as profiles
  requested={'model':'gpt-6.1-sol','reasoning_effort':'low','service_tier':'fast','tier_resolution':{'wire_id':'priority'}}
  state=self.controller.state();state['harness']['controls']['tier']={'member':'source-owner','state':'pending_turn_application','requested':requested};h.save(self.path,state)
  for options in ([],[{'id':'changed','name':'Fast'}],[{'id':'priority','name':'Other'}]):
   class RPC:
    def request(self,method,params):
     if method=='model/list':return {'data':[dict(CATALOG[0],serviceTiers=options)],'nextCursor':None}
     raise AssertionError('No turn may dispatch after catalogue change')
   self.controller.rpc=RPC()
   with self.assertRaises((h.Invalid,profiles.ProfileError)):self.controller.apply_change('source-owner','tier')
 def test_native_tier_refresh_never_uses_standalone_fallback(self):
  state=self.controller.state();state['harness']['sessions']['source-owner']['identity']['owned']=False;h.save(self.path,state)
  with self.assertRaises(c.ControlError):self.controller.refresh_owned_configuration('source-owner')
 def test_pause_cannot_rebind(self):
  self.prepare()
  with self.assertRaises(h.Invalid):self.controller.bind('source-owner','source',owned=True)
 def test_paused_disabled_source_configuration_never_calls_rpc(self):
  class NoRPC:
   def request(self,*args,**kwargs):raise AssertionError('paused/disabled source must not call RPC')
  for execution in ('paused','disabled'):
   state=self.controller.state();state['harness']['sessions']['source-owner']['execution']=execution;state['harness']['controls']={'pending':{'member':'source-owner','state':'pending_turn_application','requested':{'model':'gpt-6.1-sol','reasoning_effort':'low'}}};h.save(self.path,state);self.controller.rpc=NoRPC()
   with self.assertRaises(h.Invalid):self.controller.apply_change('source-owner','pending')
   with self.assertRaises(h.Invalid):self.controller.change('source-owner','fresh','gpt-6.1-sol','low')
 def test_wrong_read_identity_refused(self):
  class RPC:
   def request(self,method,params):return {'thread':{'id':'different','model':'gpt-6.1-sol','reasoningEffort':'low','status':{'type':'idle'}}}
  self.controller.rpc=RPC()
  with self.assertRaises(h.Invalid):self.controller.inspect('source-owner')
 def test_unknown_change_blocks_fresh_id(self):
  self.controller.event('control_intent',member='source-owner',operation='unknown',state='outcome_unknown',requested={})
  with self.assertRaises(h.Invalid):self.controller.event('control_intent',member='source-owner',operation='fresh-id',state='request_pending',requested={})
 def test_receipt_admission_uses_scheduling_not_token_reservations(self):
  self.controller.event('control_intent',member='source-owner',operation='packet',state='request_pending',requested={'kind':'turn','receipt_only':True})
  self.assertEqual('request_pending',self.controller.state()['harness']['controls']['packet']['state'])
 def test_retired_packet_reservation_cannot_reactivate_legacy_accounting(self):
  with self.assertRaises(h.Invalid):self.controller.event('control_intent',member='source-owner',operation='config',state='request_pending',requested={'packet_reserve':1})
 def test_pretransfer_revision_change_keeps_source(self):
  self.recipient();h.transaction(self.path,{'op':'change','instruction':'new constraint'})
  with self.assertRaises(h.Invalid):self.controller.transfer('handoff1')
  self.assertEqual('source-owner',self.controller.state()['tasks']['task']['owner'])

if __name__=='__main__':unittest.main()
