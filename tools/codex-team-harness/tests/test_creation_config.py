"""Creation wire regression, using the real Controller and JSON-RPC serializer."""
import copy,io,json,sys,types,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'payload/team-coordination/scripts'))
import external_handoff as external
import harness as h
import managed_run
import profile_defaults as profiles
import session_control as control
import test_external_handoff as fixtures
from unittest import mock

class SerializedRPC(managed_run.RPC):
 """Synthetic peer, no process, socket, session or inference."""
 def __init__(self,effort=None,model=None,read_effort=None):
  self.p=types.SimpleNamespace(stdin=io.BytesIO());self.seq=0
  self.tier_contract=profiles.CURRENT_TIER_CONTRACT
  self.effort=effort;self.model=model;self.read_effort=read_effort
 def messages(self):return [json.loads(x)for x in self.p.stdin.getvalue().splitlines()]
 def next(self,timeout=1):
  message=self.messages()[-1];method=message['method'];params=message['params']
  if method=='model/list':result={'data':[{'model':'gpt-6.1-sol','supportedReasoningEfforts':[{'reasoningEffort':'high'}],'serviceTiers':[{'id':'priority','name':'Fast'}]}],'nextCursor':None}
  elif method=='thread/start':
   config=params.get('config',{});sandbox=config.get('sandbox_workspace_write')
   result={'thread':{'id':'synthetic-recipient'},'model':self.model or params['model'],'reasoningEffort':self.effort or config.get('model_reasoning_effort','low'),'cwd':params['cwd'],'sandbox':external.sandbox({'sandbox':'workspace-write','writable_roots':sandbox['writable_roots']})if sandbox else {'type':'readOnly','networkAccess':False},'approvalPolicy':params['approvalPolicy'],'approvalsReviewer':params.get('approvalsReviewer')}
   self.created=result
  elif method=='thread/read':result={'thread':{'id':'synthetic-recipient','model':self.created['model'],'reasoningEffort':self.read_effort or self.created['reasoningEffort'],'status':{'type':'idle'}}}
  else:raise AssertionError('No execution/reload permitted: '+method)
  return {'id':message['id'],'result':result}

class CreationConfig(unittest.TestCase):
 setUp=fixtures.ExternalHandoff.setUp
 tearDown=fixtures.ExternalHandoff.tearDown
 write_observation=fixtures.ExternalHandoff.write_observation
 prepare=fixtures.ExternalHandoff.prepare
 writable=fixtures.BoundedWriting.writable
 def create(self,writable=True,**overrides):
  if writable:self.writable()
  self.prepare();self.ctl.rpc=SerializedRPC(**overrides)
  return self.ctl.create_recipient('one','high',str(self.claim))
 def test_workspace_write_serialized_request_retains_high_and_exact_ceiling(self):
  outcome=None
  try:outcome=self.create()
  except h.Invalid:pass # Inspect the actual serialized request even when the gate blocks it.
  message=next(x for x in self.ctl.rpc.messages()if x['method']=='thread/start');params=message['params']
  expected=external.creation(self.packet['permission_ceiling'],str(self.claim))
  self.assertEqual(dict(expected['config'],model_reasoning_effort='high'),params['config'])
  self.assertEqual('synthetic-recipient',outcome)
  for key,value in expected.items():
   if key!='config':self.assertEqual(value,params[key])
  self.assertEqual('gpt-6.1-sol',params['model']);self.assertNotIn('serviceTier',params)
  self.assertEqual(['model/list','thread/start','thread/read'],[x['method']for x in self.ctl.rpc.messages()])
 def test_readonly_serialized_request_preserves_high(self):
  self.create(False);params=next(x['params']for x in self.ctl.rpc.messages()if x['method']=='thread/start')
  self.assertEqual({'model_reasoning_effort':'high'},params['config']);self.assertEqual('read-only',params['sandbox']);self.assertEqual('never',params['approvalPolicy'])
 def test_other_config_keys_survive_and_creation_security_policy_replaces_stale_whole_value(self):
  original=profiles.start_parameters;inputs=[];original_creation=external.creation
  def defaults(*args):
   params,resolution=original(*args);params['config'].update(extra_setting={'retained':True},sandbox_workspace_write={'network_access':True,'stale_setting':True});inputs.append((params,copy.deepcopy(params)));return params,resolution
  def creation(*args):
   value=original_creation(*args);value['config']['creation_extra']={'retained':True};return value
  with mock.patch.object(profiles,'start_parameters',defaults),mock.patch.object(external,'creation',creation):
   try:self.create()
   except h.Invalid:pass
  params=next(x['params']for x in self.ctl.rpc.messages()if x['method']=='thread/start')
  self.assertEqual({'retained':True},params['config'].get('extra_setting'))
  self.assertEqual({'retained':True},params['config'].get('creation_extra'))
  self.assertEqual(external.creation(self.packet['permission_ceiling'],str(self.claim))['config']['sandbox_workspace_write'],params['config']['sandbox_workspace_write'])
  self.assertEqual(inputs[0][1],inputs[0][0])
 def test_conflicting_model_or_reasoning_rejected_before_intent_and_rpc(self):
  original=external.creation
  for conflict in ({'model':'gpt-6-luna'},{'config':{'model_reasoning_effort':'low'}}):
   with self.subTest(conflict=conflict):
    self.tearDown();self.setUp();self.writable();self.prepare();self.ctl.rpc=SerializedRPC()
    def creation(*args):return dict(original(*args),**conflict)
    with mock.patch.object(external,'creation',creation):
     with self.assertRaises(h.Invalid):self.ctl.create_recipient('one','high',str(self.claim))
    self.assertNotIn('thread/start',[x['method']for x in self.ctl.rpc.messages()])
    self.assertEqual('prepared',self.ctl.state()['harness']['handoffs']['one']['state'])
 def test_official_wrong_model_or_effort_remains_blocked_and_retains_identity(self):
  for overrides in ({'effort':'low'},{'model':'gpt-6-luna'},{'read_effort':'low'}):
   with self.subTest(overrides=overrides):
    # Each isolated fixture is a distinct synthetic case, never an automatic retry.
    self.tearDown();self.setUp()
    with self.assertRaises(h.Invalid):self.create(**overrides)
    state=self.ctl.state();x=state['harness']['handoffs']['one']
    self.assertEqual('synthetic-recipient',x['creation_receipt']['identity']['thread'])
    self.assertEqual('source',state['tasks']['task']['owner'])
    self.assertEqual(1,len([x for x in self.ctl.rpc.messages()if x['method']=='thread/start']))
    self.assertNotIn('turn/start',[x['method']for x in self.ctl.rpc.messages()])
 def test_same_identity_mismatch_cannot_reconcile_wrong_phase_or_create_again(self):
  with self.assertRaises(h.Invalid):self.create(read_effort='low')
  before=copy.deepcopy(self.ctl.state());x=before['harness']['handoffs']['one']
  self.assertEqual('recipient_created',x['failure']['phase'])
  with self.assertRaises(h.Invalid):self.ctl.reconcile_recipient('one','high',str(self.claim))
  self.assertEqual(before,self.ctl.state())
  with self.assertRaises(h.Invalid):self.ctl.create_recipient('one','high',str(self.claim))
  self.assertEqual(before,self.ctl.state())
  methods=[x['method']for x in self.ctl.rpc.messages()]
  self.assertEqual(1,methods.count('thread/start'));self.assertNotIn('thread/resume',methods);self.assertNotIn('turn/start',methods)
 def test_merge_preserves_inputs_and_rejects_malformed_config(self):
  params={'model':'gpt-6.1-sol','config':{'model_reasoning_effort':'high','retained':1}}
  creation={'cwd':'/synthetic','config':{'model_reasoning_effort':'high','other':2}}
  before=copy.deepcopy((params,creation));merged=control.creation_parameters(params,creation)
  self.assertEqual({'model_reasoning_effort':'high','retained':1,'other':2},merged['config'])
  self.assertEqual(before,(params,creation));self.assertIsNot(merged['config'],params['config'])
  for bad in (None,[],False,'config'):
   with self.subTest(bad=bad):
    with self.assertRaises(h.Invalid):control.creation_parameters(params,{'config':bad})
  self.assertEqual({'model':'gpt-6.1-sol','cwd':'/synthetic'},control.creation_parameters({'model':'gpt-6.1-sol'},{'cwd':'/synthetic'}))

if __name__=='__main__':unittest.main()
