import copy,json,sys,tempfile,unittest
from unittest import mock
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'payload/team-coordination/scripts'))
import harness as h,session_control as c,profile_defaults as profiles,external_handoff as external

class ManagementHandoff(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name).resolve();self.admin=self.root/'.codex-team';self.admin.mkdir();self.path=self.admin/'state.json';self.src=self.root/'src';self.src.mkdir();self.tests=self.root/'tests';self.tests.mkdir();(self.src/'uncommitted.txt').write_text('original');(self.tests/'sample.txt').write_text('test original')
  self.files=[self.root/name for name in ['README.txt','settings.json','build.txt','notes.txt','consumer-1.txt','consumer-2.txt','consumer-3.txt','consumer-4.txt','consumer-5.txt']]
  for p in self.files:p.write_text('original '+p.name)
  self.claims=[str(self.admin),str(self.src),str(self.tests),*[str(p)for p in self.files]];self.assertEqual(12,len(self.claims));self.failure=self.admin/'failure.json';self.failure.write_text('{"verdict":"fail","reason":"retained"}')
  (self.src/'swiftpm').mkdir();(self.src/'swiftpm/debug').symlink_to('out/Products/Debug');(self.admin/'failure-link').symlink_to('failure.json')
  self.control=self.root/'coordination';self.control.mkdir();self.stop=self.control/'stop.json';self.observation=self.control/'source-observation.json';self.identity={'host':'durable','transport':'codex-app','controller':'fixture-source','thread':'source-thread','owned':False};self.quote='Owner execution stopped and all commands drained.'
  self.observation.write_text(json.dumps({'source_identity':self.identity,'tool':'codex_app.read_thread','status':'idle','turn':'stop-turn','turn_status':'completed','final_text':self.quote}));identity=self.control/'identity.txt';identity.write_text('synthetic owner identity')
  s=h.initial('management-aware twelve-claim mixed sample')
  for e in [{'op':'register','member':'source','role':'core','identity':str(identity)},{'op':'assign','member':'source','task':'task','purpose':'retained implementation','context':'decisions and rationale retained','kind':'implementation'},{'op':'claim','task':'task','paths':self.claims}]:s=h.apply(s,e)
  s['tasks']['task']['state']='ready_for_review';s['tasks']['task']['reviews']=[{'verdict':'fail','evidence':h.ledger.evidence(self.failure)}];h.save(self.path,s)
  self.ceiling={'sandbox':'workspace-write','publication':False,'writable_roots':[str(self.src)],'network_access':False,'approval_policy':'on-request','approvals_reviewer':'auto_review'}
  self.stop.write_text(json.dumps({'source_identity':self.identity,'execution_stopped':True,'commands_drained':True,'stopped_turn':'stop-turn','project_revision':s['harness']['revision'],'owner_ack_quote':self.quote,'permission_ceiling':self.ceiling,'observation_sha256':h.ledger.evidence(self.observation)['sha256']}));self.ctl=c.Controller(self.path,None,'fixture-receiver','local','official-owned-stdio');self.original_task=copy.deepcopy(s['tasks']['task'])
  test=self
  class RPC:
   tier_contract=profiles.CURRENT_TIER_CONTRACT
   def __init__(self):self.calls=[];self.turn='packet-turn';self.messages=[]
   def request(self,method,params,**kwargs):
    self.calls.append((method,copy.deepcopy(params)))
    if method=='model/list':return {'data':[{'model':'gpt-6.1-sol','supportedReasoningEfforts':[{'reasoningEffort':'high'}]}],'nextCursor':None}
    if method=='thread/start':return {'thread':{'id':'receiver-thread'},'model':'gpt-6.1-sol','reasoningEffort':'high','cwd':str(test.src),'sandbox':external.sandbox(test.ceiling),'approvalPolicy':'on-request','approvalsReviewer':'auto_review'}
    if method=='thread/read':return {'thread':{'id':params['threadId'],'model':'gpt-6.1-sol','reasoningEffort':'high','status':{'type':'idle'}}}
    if method=='turn/start':
     x=test.ctl.state()['harness']['handoffs']['one'];self.messages=[{'method':'item/completed','params':{'threadId':'receiver-thread','item':{'type':'agentMessage','text':c.ack_text(x)}}},{'method':'turn/completed','params':{'threadId':'receiver-thread','turn':{'id':self.turn,'status':'completed'}}}];return {'turn':{'id':self.turn}}
    raise AssertionError(method)
   def next(self,*args):return self.messages.pop(0)if self.messages else None
   def handle_request(self,event):pass
  self.rpc=RPC();self.ctl.rpc=self.rpc
 def tearDown(self):self.tmp.cleanup()
 def prepare(self):
  return self.ctl.prepare_handoff('one','source','receiver','core',['task'],{'goal':'retain implementation','decisions':[{'decision':'retain claims','rationale':'preserve failure evidence'}],'constraints':['management ownership is not write permission'],'remaining_work':['fresh successor authority'],'permission_ceiling':self.ceiling},str(self.stop),explicit_request=True,external_source={'identity':self.identity,'observation':str(self.observation)},expected_revision=self.ctl.state()['harness']['revision'])
 def receive(self):
  packet=self.prepare();self.ctl.create_recipient('one','high',self.src);self.ctl.deliver_packet('one');return packet
 def transfer(self):
  self.refresh=self.admin/'transfer-observation.json';self.refresh.write_text(self.observation.read_text());return self.ctl.transfer('one',external_observation=str(self.refresh))
 def test_full_mixed_claim_handoff_preserves_admin_and_failure_without_writable_admin(self):
  packet=self.receive();self.assertEqual(set(self.claims),set(packet['baseline']));revision=self.transfer();s=self.ctl.state();x=s['harness']['handoffs']['one'];ack=self.admin/'committed-owner-ack.json';ack.write_text(json.dumps({'handoff':'one','recipient':'receiver','transfer_revision':revision,'transfer_nonce':x['transfer_nonce']}));self.ctl.event('control_owner_ack',handoff='one',revision=revision,evidence=str(ack));self.ctl.resume('one')
  p=h.packet(self.ctl.state(),'receiver');self.ctl.event('ack',member='receiver',revision=p['revision'],epoch=p['epoch'],digest=h.digest(p));s=self.ctl.state();h.ack_current(s,'receiver');task=copy.deepcopy(self.original_task);task['owner']='receiver';self.assertEqual(task,s['tasks']['task']);self.assertEqual('disabled',s['harness']['sessions']['source']['execution']);self.assertNotIn(str(self.admin),s['harness']['sessions']['receiver']['permission_ceiling']['writable_roots']);self.assertEqual(self.failure.read_text(),'{"verdict":"fail","reason":"retained"}');self.assertEqual(h.digest(packet),s['harness']['handoffs']['one']['packet_hash']);self.assertTrue(s['harness']['handoffs']['one']['management']['completed']);self.ctl.event('change',instruction='New actual constraint')
  with self.assertRaises(h.Invalid):h.ack_current(self.ctl.state(),'receiver')
 def test_same_revision_state_tampering_cannot_reseed_guard(self):
  for area in ('controls','profiles','history'):
   with self.subTest(area=area):
    if area=='controls':self.prepare();original=self.path.read_bytes()
    else:self.path.write_bytes(original)
    s=self.ctl.state();revision=s['harness']['revision']
    if area=='controls':s['harness']['controls']['forged']={'state':'completed','member':'source'}
    elif area=='profiles':s['harness']['profiles']['source']['last_revision']=-123
    else:s['history'][-1]['at']='unauthorized edit'
    h.save(self.path,s)
    with self.assertRaises(h.Invalid):self.ctl.event('control_handoff_intent',handoff='one',phase='creation_pending')
    self.assertEqual(revision,self.ctl.state()['harness']['revision']);self.assertEqual(s,self.ctl.state())
 def test_unknown_admin_changes_and_product_changes_block_before_transfer(self):
  self.receive();before=self.path.read_bytes();(self.admin/'unrecognized.json').write_text('{}')
  with self.assertRaises(h.Invalid):self.transfer()
  self.assertEqual(before,self.path.read_bytes());self.assertEqual('source',self.ctl.state()['tasks']['task']['owner'])
 def test_new_management_evidence_is_rechecked_without_following_ledger_reader(self):
  self.receive();original=h.ledger.fresh;phase_path=str(self.admin/'transfer-observation.json')
  def checked(value):
   if value['path']==phase_path:raise AssertionError('Following evidence reader used for management phase')
   return original(value)
  with mock.patch.object(h.ledger,'fresh',side_effect=checked):self.transfer()
 def test_phase_evidence_swapped_after_inventory_never_opens_link_target(self):
  import management_handoff as management
  self.receive();before=self.path.read_bytes();failure=self.failure.read_bytes();outside=self.control/'outside-phase.json';outside.write_bytes(self.observation.read_bytes());original=management.check_files;opened=external.os.open;reads=[]
  def swap(*args,**kwargs):
   result=original(*args,**kwargs)
   if result[1]:self.refresh.unlink();self.refresh.symlink_to(outside)
   return result
  def checked(name,*args,**kwargs):
   if str(name)in (str(outside),outside.name):reads.append(str(name));raise AssertionError('Phase link target was opened')
   return opened(name,*args,**kwargs)
  original_path_open=Path.open
  def checked_path(path,*args,**kwargs):
   if path==outside:reads.append(str(path));raise AssertionError('Phase link target was opened')
   return original_path_open(path,*args,**kwargs)
  with mock.patch.object(management,'check_files',side_effect=swap),mock.patch.object(external.os,'open',side_effect=checked),mock.patch.object(Path,'open',checked_path):
   with self.assertRaises(h.Invalid):self.transfer()
  self.assertEqual([],reads);self.assertEqual(before,self.path.read_bytes());self.assertEqual(failure,self.failure.read_bytes())
 def test_admin_claim_never_becomes_writable_root(self):
  self.ceiling['writable_roots']=[str(self.admin)];stop=json.loads(self.stop.read_text());stop['permission_ceiling']=self.ceiling;self.stop.write_text(json.dumps(stop))
  with self.assertRaises(h.Invalid):self.prepare()

 def test_pretransfer_context_ack_cannot_complete_management_guard(self):
  self.receive();p=h.packet(self.ctl.state(),'receiver');self.ctl.event('ack',member='receiver',revision=p['revision'],epoch=p['epoch'],digest=h.digest(p));self.assertFalse(self.ctl.state()['harness']['handoffs']['one']['management']['completed']);(self.src/'uncommitted.txt').write_text('changed')
  with self.assertRaises(h.Invalid):self.transfer()

 def test_all_other_admin_entries_and_product_entries_remain_exact(self):
  self.receive();before=self.path.read_bytes();original=self.failure.read_bytes();mode=self.failure.stat().st_mode&0o777
  cases=[('new-file',lambda:(self.admin/'unexpected').write_text('x'),lambda:(self.admin/'unexpected').unlink()),('empty-dir',lambda:(self.admin/'unexpected').mkdir(),lambda:(self.admin/'unexpected').rmdir()),('deleted',self.failure.unlink,lambda:self.failure.write_bytes(original)),('changed',lambda:self.failure.write_text('lost failure'),lambda:self.failure.write_bytes(original)),('mode',lambda:self.failure.chmod(0o600),lambda:self.failure.chmod(mode)),('symlink',lambda:(self.admin/'alias').symlink_to(self.src),lambda:(self.admin/'alias').unlink()),('product-file',lambda:self.files[0].write_text('changed'),lambda:self.files[0].write_text('original '+self.files[0].name)),('product-dir',lambda:(self.src/'new').write_text('changed'),lambda:(self.src/'new').unlink())]
  for name,change,restore in cases:
   with self.subTest(name=name):
    change()
    try:
     with self.assertRaises(h.Invalid):self.ctl.inspect('receiver')
     self.assertEqual(before,self.path.read_bytes())
    finally:restore()
 def test_raw_state_edit_and_mid_transaction_CAS_are_not_adopted(self):
  self.receive();original=self.path.read_bytes();self.path.write_bytes(original+b' ')
  with self.assertRaisesRegex(h.Invalid,'Canonical state bytes'):self.ctl.inspect('receiver')
  self.assertEqual(original+b' ',self.path.read_bytes());self.path.write_bytes(original)
  actual_apply=h.apply
  def concurrent(state,event,*args,**kwargs):
   result=actual_apply(state,event,*args,**kwargs);self.path.write_bytes(b'concurrent foreign bytes');return result
  h.apply=concurrent
  try:
   with self.assertRaisesRegex(h.Invalid,'CAS refused'):self.ctl.inspect('receiver')
   self.assertEqual(b'concurrent foreign bytes',self.path.read_bytes())
  finally:h.apply=actual_apply

 def test_product_edit_during_transition_is_preserved_but_not_committed(self):
  self.receive();original=self.path.read_bytes();actual_apply=h.apply
  def concurrent(state,event,*args,**kwargs):
   result=actual_apply(state,event,*args,**kwargs);(self.src/'uncommitted.txt').write_text('foreign product edit');return result
  h.apply=concurrent
  try:
   with self.assertRaisesRegex(h.Invalid,'Product baseline'):self.ctl.inspect('receiver')
   self.assertEqual(original,self.path.read_bytes());self.assertEqual('foreign product edit',(self.src/'uncommitted.txt').read_text())
  finally:h.apply=actual_apply

 def test_guard_retirement_or_metadata_removal_cannot_bypass_validation(self):
  self.receive();original=self.path.read_bytes()
  for mutation in ('completed','missing','forged-resumed'):
   with self.subTest(mutation=mutation):
    self.path.write_bytes(original);state=self.ctl.state();record=state['harness']['handoffs']['one']
    if mutation=='missing':record.pop('management')
    else:
     record['management']['completed']=True
     if mutation=='forged-resumed':record['state']='resumed'
    h.save(self.path,state)
    with self.assertRaises(h.Invalid):self.ctl.inspect('receiver')
    self.assertEqual(state,self.ctl.state())

if __name__=='__main__':unittest.main()
