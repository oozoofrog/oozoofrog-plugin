"""Synthetic paused-recipient repair; real JSON-RPC serializer, no model calls."""
import copy,hashlib,io,json,sys,types,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'payload/team-coordination/scripts'))
import harness as h,managed_run,profile_defaults as profiles,session_control as c
import test_management_handoff as fixtures
import test_external_handoff as external_fixtures
from unittest import mock

class Peer(managed_run.RPC):
 def __init__(self,test):
  self.test=test;self.seq=0;self.p=types.SimpleNamespace(stdin=io.BytesIO());self.pending=[];self.seen=set();self.effort='low';self.bad_settings={};self.loaded=True;self.queue=[];self.goal=None;self.tier_contract=profiles.CURRENT_TIER_CONTRACT
 def messages(self):return [json.loads(x)for x in self.p.stdin.getvalue().splitlines()]
 def settings(self):
  value=dict(model='gpt-6.1-sol',effort=self.effort,cwd=str(self.test.src),sandboxPolicy=c.external.sandbox(self.test.ceiling),approvalPolicy='on-request',approvalsReviewer='auto_review',serviceTier='priority');value.update(self.bad_settings);return value
 def next(self,*args):
  if self.pending:return self.pending.pop(0)
  message=self.messages()[-1];i=message['id'];method=message['method'];p=message['params']
  if i in self.seen:return None
  self.seen.add(i);after=[]
  if method=='model/list':result={'data':[{'model':'gpt-6.1-sol','supportedReasoningEfforts':[{'reasoningEffort':'high'}]}],'nextCursor':None}
  elif method in ('thread/start','thread/resume'):
   self.loaded=True;result={'thread':{'id':'receiver-thread'},'model':'gpt-6.1-sol','reasoningEffort':self.effort,'cwd':str(self.test.src),'sandbox':c.external.sandbox(self.test.ceiling),'approvalPolicy':'on-request','approvalsReviewer':'auto_review'}
  elif method=='thread/read':
   if not self.loaded:return {'id':i,'error':{'code':-32600,'message':'thread not loaded: receiver-thread'}}
   result={'thread':{'id':p['threadId'],'model':'gpt-6.1-sol','reasoningEffort':self.effort,'status':{'type':'idle'}}}
  elif method=='thread/queue/list':result={'data':self.queue,'nextCursor':None}
  elif method=='thread/goal/get':result={'goal':self.goal}
  elif method=='thread/settings/update':
   self.effort=p['effort'];result={};self.pending=[{'id':i,'result':result}]
   return {'method':'thread/settings/updated','params':{'threadId':'receiver-thread','threadSettings':self.settings()}}
  elif method=='turn/start':
   x=self.test.ctl.state()['harness']['handoffs']['one'];result={'turn':{'id':'synthetic-packet-turn'}};after=[{'method':'item/completed','params':{'threadId':'receiver-thread','item':{'type':'agentMessage','text':c.ack_text(x)}}},{'method':'turn/completed','params':{'threadId':'receiver-thread','turn':{'id':'synthetic-packet-turn','status':'completed'}}}]
  else:raise AssertionError('Unexpected method: '+method)
  self.pending=after;return {'id':i,'result':result}

class Recovery(unittest.TestCase):
 setUp=fixtures.ManagementHandoff.setUp
 tearDown=fixtures.ManagementHandoff.tearDown
 prepare=fixtures.ManagementHandoff.prepare
 def failed(self):
  self.prepare();self.rpc=Peer(self);self.ctl.rpc=self.rpc
  with self.assertRaises(h.Invalid):self.ctl.create_recipient('one','high',str(self.src))
  self.assertEqual('recipient_created',self.ctl.state()['harness']['handoffs']['one']['failure']['phase'])
 def args(self):return {'expected_revision':self.ctl.state()['harness']['revision'],'expected_state_sha256':hashlib.sha256(self.path.read_bytes()).hexdigest()}
 def recover(self,**changes):
  arguments=dict(self.args(),**changes);return self.ctl.recover_paused_recipient('one','repair','high',str(self.src),**arguments)
 def fresh_stop(self):
  self.fresh_observation=self.control/'fresh-observation.json';self.fresh_observation.write_text(self.observation.read_text());value=json.loads(self.stop.read_text());value.update(project_revision=self.ctl.state()['harness']['revision'],observation_sha256=h.ledger.evidence(self.fresh_observation)['sha256']);self.fresh_checkpoint=self.control/'fresh-stop.json';self.fresh_checkpoint.write_text(json.dumps(value))
 def refresh(self,**changes):
  args=dict(self.args(),**changes);x=self.ctl.state()['harness']['handoffs']['one'];return self.ctl.refresh_packet('one','refresh',x['packet_hash'],str(self.fresh_checkpoint),str(self.fresh_observation),**args)
 def test_paused_same_id_settings_repair_keeps_binding_failure_owner_and_permissions(self):
  self.failed();before=copy.deepcopy(self.ctl.state());args=self.args();result=self.recover();state=self.ctl.state();x=state['harness']['handoffs']['one'];old=before['harness']['handoffs']['one']
  self.assertEqual('recipient_created',x['state']);self.assertEqual(old['failure'],x['failure']);self.assertEqual(old['creation_receipt'],x['creation_receipt']);self.assertEqual(before['members'],state['members']);self.assertEqual(before['tasks'],state['tasks'])
  for member in ('source','receiver'):self.assertEqual('paused',state['harness']['sessions'][member]['execution'])
  self.assertFalse(state['harness']['sessions']['receiver']['managed']);self.assertEqual('high',state['harness']['sessions']['receiver']['policy_expected']['reasoning_effort'])
  params=next(x['params']for x in self.rpc.messages()if x['method']=='thread/settings/update');self.assertEqual({'threadId':'receiver-thread','model':'gpt-6.1-sol','effort':'high'},params)
  self.assertNotIn('thread/resume',[x['method']for x in self.rpc.messages()]);self.assertNotIn('turn/start',[x['method']for x in self.rpc.messages()])
  raw=self.path.read_bytes();messages=self.rpc.messages();self.assertEqual(result,self.ctl.recover_paused_recipient('one','repair','high',str(self.src),**args));self.assertEqual(raw,self.path.read_bytes());self.assertEqual(messages,self.rpc.messages())
  with self.assertRaises(h.Invalid):self.ctl.recover_paused_recipient('one','repair','low',str(self.src),**args)
 def test_stale_raw_hash_same_revision_refuses_before_rpc(self):
  self.failed();args=self.args();self.ctl.inspect('receiver');raw=self.path.read_bytes();messages=self.rpc.messages()
  with self.assertRaises(h.Invalid):self.ctl.recover_paused_recipient('one','repair','high',str(self.src),**args)
  self.assertEqual(raw,self.path.read_bytes());self.assertEqual(messages,self.rpc.messages())
 def test_not_loaded_never_automatically_resumes_or_creates(self):
  self.failed();self.rpc.loaded=False;raw=self.path.read_bytes()
  with self.assertRaises(h.Invalid):self.recover()
  self.assertEqual(raw,self.path.read_bytes());methods=[x['method']for x in self.rpc.messages()];self.assertNotIn('thread/resume',methods);self.assertEqual(1,methods.count('thread/start'));self.assertNotIn('thread/settings/update',methods)
 def test_permission_notification_drift_retains_failed_recovery_and_blocks_new_id(self):
  self.failed();self.rpc.bad_settings={'approvalPolicy':'never'}
  with self.assertRaises(h.Invalid):self.recover()
  state=self.ctl.state();self.assertEqual('outcome_unknown',state['harness']['handoffs']['one']['state']);self.assertEqual('source',state['tasks']['task']['owner'])
  with self.assertRaises(h.Invalid):self.ctl.recover_paused_recipient('one','other','high',str(self.src),**self.args())
  self.assertEqual(1,len([x for x in self.rpc.messages()if x['method']=='thread/settings/update']))
 def test_packet_refresh_archives_exact_old_packet_and_requires_new_receipt(self):
  self.failed();self.recover();old=copy.deepcopy(self.ctl.state()['harness']['handoffs']['one']);self.ctl.event('policy_refresh',reason='synthetic contract adoption');self.fresh_stop();args=self.args();result=self.refresh();state=self.ctl.state();x=state['harness']['handoffs']['one']
  self.assertEqual(old['packet'],x['packet_versions'][0]['packet']);self.assertEqual(old['packet_hash'],x['packet_versions'][0]['packet_hash']);self.assertEqual(old['nonce'],x['packet_versions'][0]['nonce']);self.assertEqual(old['failure'],x['packet_versions'][0]['failure']);self.assertNotEqual(old['packet_hash'],x['packet_hash']);self.assertNotEqual(old['nonce'],x['nonce']);self.assertEqual(state['harness']['revision'],x['packet']['project_revision'])
  with self.assertRaises(h.Invalid):self.ctl.transfer('one')
  raw=self.path.read_bytes();self.assertEqual(result,self.ctl.refresh_packet('one','refresh',old['packet_hash'],str(self.fresh_checkpoint),str(self.fresh_observation),**args));self.assertEqual(raw,self.path.read_bytes())
  self.ctl.deliver_packet('one');self.assertEqual('packet_received',self.ctl.state()['harness']['handoffs']['one']['state']);self.assertEqual(self.original_task,self.ctl.state()['tasks']['task']);wire=next(m['params']for m in self.rpc.messages()if m['method']=='turn/start');self.assertEqual('default',wire.get('serviceTierForTurn'));self.assertNotIn('serviceTier',wire)
  self.transfer_observation=self.control/'transfer-new.json';self.transfer_observation.write_text(self.observation.read_text());self.ctl.transfer('one',external_observation=str(self.transfer_observation));self.assertEqual('receiver',self.ctl.state()['tasks']['task']['owner'])
  state=self.ctl.state();x=state['harness']['handoffs']['one'];ack=self.admin/'fresh-owner-ack.json';ack.write_text(json.dumps({'handoff':'one','recipient':'receiver','transfer_revision':x['transfer_revision'],'transfer_nonce':x['transfer_nonce']}));self.ctl.event('control_owner_ack',handoff='one',revision=x['transfer_revision'],evidence=str(ack));self.ctl.resume('one');packet=h.packet(self.ctl.state(),'receiver');self.ctl.event('ack',member='receiver',revision=packet['revision'],epoch=packet['epoch'],digest=h.digest(packet));state=self.ctl.state();h.ack_current(state,'receiver');self.assertEqual(h.digest(packet),h.digest(h.packet(state,'receiver')));self.assertTrue(state['harness']['handoffs']['one']['management']['completed']);self.assertEqual('disabled',state['harness']['sessions']['source']['execution']);self.assertEqual('enabled',state['harness']['sessions']['receiver']['execution'])
  # Every lifecycle response above is a synthetic peer fixture, never model proof.
 def test_refresh_refuses_stale_owner_checkpoint_or_changed_task(self):
  self.failed();self.recover();self.ctl.event('policy_refresh',reason='synthetic contract adoption');raw=self.path.read_bytes()
  with self.assertRaises(h.Invalid):self.ctl.refresh_packet('one','bad',self.ctl.state()['harness']['handoffs']['one']['packet_hash'],str(self.stop),str(self.observation),**self.args())
  self.assertEqual(raw,self.path.read_bytes())
  self.fresh_stop();stop=json.loads(self.fresh_checkpoint.read_text());stop['owner_ack_quote']='fabricated absent quote';self.fresh_checkpoint.write_text(json.dumps(stop))
  with self.assertRaises(h.Invalid):self.refresh()
  self.assertEqual(raw,self.path.read_bytes())
 def test_changed_ownership_identity_permission_and_later_phase_are_refused(self):
  self.failed();original=self.ctl.state()
  cases=[lambda s:s['tasks']['task']['paths'].append('/synthetic/extra'),lambda s:s['tasks']['task']['reviews'].append({'verdict':'pass'}),lambda s:s['harness']['sessions']['receiver']['permission_ceiling'].update(network_access=True),lambda s:s['harness']['sessions']['source']['identity'].update(thread='foreign-source'),lambda s:s['harness']['handoffs']['one']['creation_receipt']['identity'].update(thread='foreign-receiver'),lambda s:s['harness']['handoffs']['one'].update(receipt={'turn':'already-delivered'}),lambda s:s['harness']['profiles']['receiver'].update(ack={'digest':'unknown'})]
  for change in cases:
   with self.subTest(change=change):
    state=copy.deepcopy(original);change(state)
    with self.assertRaises(h.Invalid):c.predelivery(state,state['harness']['handoffs']['one'])
 def test_foreign_revision_and_changed_claim_content_fail_without_requests(self):
  self.failed();messages=self.rpc.messages();raw=self.path.read_bytes()
  with self.assertRaises(h.Invalid):self.recover(expected_revision=self.ctl.state()['harness']['revision']+1)
  self.assertEqual(messages,self.rpc.messages());(self.src/'uncommitted.txt').write_text('changed product')
  with self.assertRaises(h.Invalid):self.recover()
  self.assertEqual(raw,self.path.read_bytes());self.assertEqual(messages,self.rpc.messages())
 def test_refresh_requires_raw_cas_and_changed_replay_arguments_fail(self):
  self.failed();self.recover();self.ctl.event('policy_refresh',reason='synthetic adoption');self.fresh_stop();args=self.args();self.ctl.inspect('receiver');raw=self.path.read_bytes()
  with self.assertRaises(h.Invalid):self.ctl.refresh_packet('one','refresh',self.ctl.state()['harness']['handoffs']['one']['packet_hash'],str(self.fresh_checkpoint),str(self.fresh_observation),**args)
  self.assertEqual(raw,self.path.read_bytes());self.refresh();raw=self.path.read_bytes()
  with self.assertRaises(h.Invalid):self.ctl.refresh_packet('one','refresh','foreign-hash',str(self.fresh_checkpoint),str(self.fresh_observation),**self.args())
  self.assertEqual(raw,self.path.read_bytes())
 def test_post_intent_same_revision_write_is_not_adopted(self):
  self.failed();original=self.ctl.event
  def interleave(op,**kwargs):
   committed=original(op,**kwargs)
   if op=='control_paused_recovery_intent':original('control_observe',member='receiver',observation={'thread':'receiver-thread','status':'idle','model':'gpt-6.1-sol','reasoning_effort':'low','scope':'live'})
   return committed
  with mock.patch.object(self.ctl,'event',side_effect=interleave):
   with self.assertRaisesRegex(h.Invalid,'Stale canonical'):self.recover()
  state=self.ctl.state();self.assertEqual('outcome_unknown',state['harness']['handoffs']['one']['state']);self.assertEqual('request_pending',state['harness']['handoffs']['one']['recipient_recoveries']['repair']['state']);self.assertEqual('source',state['tasks']['task']['owner'])
  self.assertNotIn('thread/settings/update',[x['method']for x in self.rpc.messages()])
 def test_intent_save_before_or_after_write_never_dispatches_settings(self):
  for after_write in (False,True):
   with self.subTest(after_write=after_write):
    self.tearDown();self.setUp();self.failed();args=self.args();before=self.path.read_bytes();save=h.save
    def fault(path,state):
     if state['history'][-1]['event']['op']=='control_paused_recovery_intent':
      if after_write:save(path,state)
      raise OSError('synthetic intent persistence failure')
     return save(path,state)
    with mock.patch.object(h,'save',side_effect=fault):
     with self.assertRaises(OSError):self.ctl.recover_paused_recipient('one','repair','high',str(self.src),**args)
    self.assertNotIn('thread/settings/update',[x['method']for x in self.rpc.messages()])
    if after_write:
     raw=self.path.read_bytes();messages=self.rpc.messages();receipt=self.ctl.recover_paused_recipient('one','repair','high',str(self.src),**args);self.assertEqual('request_pending',receipt['state']);self.assertEqual(raw,self.path.read_bytes());self.assertEqual(messages,self.rpc.messages())
     with self.assertRaises(h.Invalid):self.ctl.event('policy_refresh',reason='must resolve pending settings first')
    else:self.assertEqual(before,self.path.read_bytes())
 def test_verified_result_saved_then_error_replays_receipt_without_resend(self):
  self.failed();args=self.args();save=h.save
  def fault(path,state):
   save(path,state)
   if state['history'][-1]['event'].get('status')=='verified':raise OSError('synthetic post-save result failure')
  with mock.patch.object(h,'save',side_effect=fault):
   with self.assertRaises(OSError):self.ctl.recover_paused_recipient('one','repair','high',str(self.src),**args)
  raw=self.path.read_bytes();messages=self.rpc.messages();self.assertEqual('verified',self.ctl.recover_paused_recipient('one','repair','high',str(self.src),**args)['state']);self.assertEqual(raw,self.path.read_bytes());self.assertEqual(messages,self.rpc.messages())
 def test_packet_refresh_saved_then_error_replays_same_nonce_hash(self):
  self.failed();self.recover();self.ctl.event('policy_refresh',reason='synthetic adoption');self.fresh_stop();args=self.args();old_hash=self.ctl.state()['harness']['handoffs']['one']['packet_hash'];save=h.save
  def fault(path,state):
   save(path,state)
   if state['history'][-1]['event']['op']=='control_packet_refresh':raise OSError('synthetic post-save refresh failure')
  with mock.patch.object(h,'save',side_effect=fault):
   with self.assertRaises(OSError):self.refresh()
  raw=self.path.read_bytes();messages=self.rpc.messages();expected=self.ctl.state()['harness']['handoffs']['one']['packet_refreshes']['refresh']['transition'];receipt=self.ctl.refresh_packet('one','refresh',old_hash,str(self.fresh_checkpoint),str(self.fresh_observation),**args);self.assertEqual(expected,receipt);self.assertEqual(raw,self.path.read_bytes());self.assertEqual(messages,self.rpc.messages())
 def test_activity_during_final_metadata_is_not_silently_discarded(self):
  self.failed();request=self.rpc.request
  def activity(method,params,**kwargs):
   if method=='thread/read'and self.rpc.effort=='high':kwargs['on_event']({'method':'turn/completed','params':{'threadId':'receiver-thread','turn':{'id':'foreign-work','status':'completed'}}})
   return request(method,params,**kwargs)
  with mock.patch.object(self.rpc,'request',side_effect=activity):
   with self.assertRaises(c.ControlError):self.recover()
  x=self.ctl.state()['harness']['handoffs']['one'];self.assertEqual('outcome_unknown',x['state']);self.assertEqual('outcome_unknown',x['recipient_recoveries']['repair']['state'])

class UnguardedProducts(unittest.TestCase):
 def setUp(self):
  external_fixtures.ExternalHandoff.setUp(self);self.src=self.claim;self.ceiling=external_fixtures.BoundedWriting.writable(self);self.ctl.rpc=Peer(self);self.rpc=self.ctl.rpc;self.prepare()
  with self.assertRaises(h.Invalid):self.ctl.create_recipient('one','high',str(self.src))
 tearDown=external_fixtures.ExternalHandoff.tearDown
 write_observation=external_fixtures.ExternalHandoff.write_observation
 prepare=external_fixtures.ExternalHandoff.prepare
 args=Recovery.args
 fresh_stop=Recovery.fresh_stop
 refresh=Recovery.refresh
 def test_product_change_during_settings_cannot_commit_verified_recovery(self):
  request=self.rpc.request
  def mutate(method,params,**kwargs):
   result=request(method,params,**kwargs)
   if method=='thread/settings/update':(self.src/'a').write_text('foreign product edit')
   return result
  with mock.patch.object(self.rpc,'request',side_effect=mutate):
   with self.assertRaisesRegex(h.Invalid,'product baseline'):self.ctl.recover_paused_recipient('one','repair','high',str(self.src),self.ctl.state()['harness']['revision'],hashlib.sha256(self.path.read_bytes()).hexdigest())
  x=self.ctl.state()['harness']['handoffs']['one'];self.assertEqual('outcome_unknown',x['state']);self.assertEqual('request_pending',x['recipient_recoveries']['repair']['state']);self.assertEqual('foreign product edit',(self.src/'a').read_text())
 def test_product_change_during_refresh_inspection_cannot_replace_packet(self):
  self.ctl.recover_paused_recipient('one','repair','high',str(self.src),**self.args());self.ctl.event('policy_refresh',reason='synthetic adoption');self.control=self.root/'refresh-evidence';self.control.mkdir();self.fresh_stop();before=self.path.read_bytes();request=self.rpc.request
  def mutate(method,params,**kwargs):
   result=request(method,params,**kwargs)
   if method=='thread/read':(self.src/'a').write_text('foreign product edit')
   return result
  with mock.patch.object(self.rpc,'request',side_effect=mutate):
   with self.assertRaisesRegex(h.Invalid,'product baseline'):self.refresh()
  self.assertEqual(before,self.path.read_bytes());self.assertNotIn('packet_versions',self.ctl.state()['harness']['handoffs']['one'])

class OwnedSource(unittest.TestCase):
 setUp=fixtures.ManagementHandoff.setUp
 tearDown=fixtures.ManagementHandoff.tearDown
 failed=Recovery.failed
 args=Recovery.args
 recover=Recovery.recover
 refresh=Recovery.refresh
 def prepare(self):
  # A distinct synthetic case matching the original owned-source provenance.
  state=self.ctl.state();state['harness'].setdefault('sessions',{})['source']={'identity':dict(self.ctl.identity,thread='source-thread',owned=True),'execution':'enabled','managed':False,'policy_expected':{}};h.save(self.path,state);self.identity=state['harness']['sessions']['source']['identity'];self.observation.write_text(json.dumps({'source_identity':self.identity,'tool':'codex_app.read_thread','status':'idle','turn':'stop-turn','turn_status':'completed','final_text':self.quote}));self.stop.write_text(json.dumps({'source':'source-thread','controller':self.ctl.identity['controller'],'commands_drained':True,'execution_stopped':True,'actual_owner_text':self.quote,'actual_stop_turn':'stop-turn'}));self.rpc=Peer(self);self.rpc.effort='high';self.ctl.rpc=self.rpc
  return self.ctl.prepare_handoff('one','source','receiver','core',['task'],{'goal':'retain implementation','decisions':[{'decision':'retain claims','rationale':'preserve failure evidence'}],'constraints':['management ownership is not write permission'],'remaining_work':['fresh successor authority'],'permission_ceiling':self.ceiling},str(self.stop),explicit_request=True)
 def fresh_stop(self):
  Recovery.fresh_stop(self);value=json.loads(self.fresh_checkpoint.read_text());value.update(actual_owner_text=self.quote,actual_stop_turn='stop-turn',permission_ceiling=self.ceiling);self.fresh_checkpoint.write_text(json.dumps(value))
 def test_owned_source_refresh_retains_owned_provenance_and_supported_quote(self):
  self.failed();self.recover();before=copy.deepcopy(self.ctl.state()['harness']['handoffs']['one']);self.assertNotIn('source_provenance',before);self.ctl.event('policy_refresh',reason='synthetic owned-source adoption');self.fresh_stop();self.refresh();x=self.ctl.state()['harness']['handoffs']['one'];self.assertNotIn('source_provenance',x);self.assertEqual('operator_attestation_with_supported_tool_evidence_owned_source',x['packet_refresh_source']['scope']);self.assertEqual(before['checkpoint'],x['packet_versions'][0]['checkpoint']);self.assertEqual(before['failure'],x['failure'])
  self.ctl.deliver_packet('one');transfer=self.control/'owned-transfer-observation.json';transfer.write_text(self.observation.read_text());before=self.path.read_bytes();original=self.fresh_observation.read_bytes();self.fresh_observation.write_text('{}')
  with self.assertRaises(h.Invalid):self.ctl.transfer('one',external_observation=str(transfer))
  self.assertEqual(before,self.path.read_bytes());self.fresh_observation.write_bytes(original);value=json.loads(transfer.read_text());value['turn']='foreign-stopped-turn';transfer.write_text(json.dumps(value))
  with self.assertRaises(h.Invalid):self.ctl.transfer('one',external_observation=str(transfer))
  self.assertEqual(before,self.path.read_bytes());transfer.write_text(self.observation.read_text());revision=self.ctl.transfer('one',external_observation=str(transfer));x=self.ctl.state()['harness']['handoffs']['one'];ack=self.admin/'owned-fresh-ack.json';ack.write_text(json.dumps({'handoff':'one','recipient':'receiver','transfer_revision':revision,'transfer_nonce':x['transfer_nonce']}));self.ctl.event('control_owner_ack',handoff='one',revision=revision,evidence=str(ack));self.ctl.resume('one');packet=h.packet(self.ctl.state(),'receiver');self.ctl.event('ack',member='receiver',revision=packet['revision'],epoch=packet['epoch'],digest=h.digest(packet));h.ack_current(self.ctl.state(),'receiver');self.assertTrue(self.ctl.state()['harness']['handoffs']['one']['management']['completed'])

if __name__=='__main__':unittest.main()
