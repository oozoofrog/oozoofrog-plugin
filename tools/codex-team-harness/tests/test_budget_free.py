"""Budget removal and exact legacy retention; all actors/evidence are synthetic."""
import base64,copy,hashlib,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'payload/team-coordination/scripts'))
import harness as h,managed_run as m,session_control as c

class BudgetFree(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name).resolve();self.path=self.root/'state.json';self.proof=self.root/'proof';self.proof.write_text('Synthetic identity and reviewed purpose');self.s=h.initial('complete the sample')
  for member,role in [('owner','core'),('leader','leader'),('reviewer','reviewer')]:self.ev('register',member=member,role=role,identity=str(self.proof))
  self.ev('assign',task='task',member='owner',purpose='complete sample',context='criteria: retain failed evidence; verify changed output');self.ev('claim',task='task',paths=[str(self.root/'collector')])
 def tearDown(self):self.tmp.cleanup()
 def ev(self,op,**kw):self.s=h.apply(self.s,dict(op=op,**kw),self.root);return self.s
 def ack(self):
  p=h.packet(self.s,'owner');self.ev('ack',member='owner',revision=p['revision'],epoch=p['epoch'],digest=h.digest(p));return p
 def legacy(self):
  self.s['harness'].update(schema=1,budget=100000,spent=100000,context_limit=16000,review_limit=2,policy_hash='legacy-contract',budget_changes={'past':{'record':'retained'}})
  self.s['harness']['runs']={'old-'+str(i):dict(task='task',member='owner',state='completed',reserve=5000,charged=5000,observed_usage=None,measurement='reserved_missing_usage',evidence='synthetic terminal',packet={'limits':{'project_token_budget':100000}})for i in range(20)}
  self.s['tasks']['task'].update(state='ready_for_review',paths=[str(self.root/name)for name in ('collector','a','b','c','d','e','f')],artifacts=[h.ledger.evidence(str(self.proof))],reviews=[{'verdict':'fail','reviewer':'reviewer','evidence':h.ledger.evidence(str(self.proof))}])
  self.s['history'].append({'at':'synthetic','event':{'op':'historical-accounting','budget':100000,'spent':100000}})
 def migration(self,raw):
  e=dict(op='contract_migrate',request_id='migrate',project='complete the sample',project_root=str(self.root),source_sha256=h.digest(self.s),source_raw_sha256=hashlib.sha256(raw).hexdigest(),policy_hash=h.digest(h.effective_contract()),reason='User explicitly removed artificial budgets and count quotas',requester='leader',approvals=str(self.root/'approvals'))
  Path(e['approvals']).write_text(json.dumps({role:dict(member=role,request_sha256=h.digest({k:v for k,v in e.items()if k!='approvals'}),approved=True,safe_boundary=True,all_current_obligations_retained=True)for role in ('leader','reviewer')}));return e
 def test_new_state_and_packet_have_no_resource_allowance_and_begin_needs_no_reserve(self):
  for name in ('budget','spent','context_limit','review_limit'):self.assertNotIn(name,self.s['harness'])
  p=self.ack();self.assertNotIn('accounting',p);self.assertEqual('complete the sample',p['goal']);self.ev('begin',member='owner',task='task',run='one');self.ev('finish',run='one',outcome='completed',evidence='terminal')
  self.assertNotIn('charged',self.s['harness']['runs']['one']);self.assertIsNone(self.s['harness']['runs']['one']['reported_usage']);self.assertIsNone(h.usage_summary(self.s)['reported_tokens'])
 def test_no_arbitrary_packet_or_review_count_stop_but_latest_fail_still_blocks_acceptance(self):
  self.ev('change',instruction='critical decision '+('x'*70000));self.ack()
  for i in range(3):self.ev('handoff',task='task',artifacts=[str(self.proof)]);self.ev('review',task='task',reviewer='reviewer',verdict='fail',evidence=str(self.proof))
  self.assertEqual(3,len(self.s['tasks']['task']['reviews']))
  with self.assertRaises(h.Invalid):self.ev('accept',task='task')
 def test_exact_legacy_raw_archive_business_preservation_and_progress(self):
  self.legacy();before=copy.deepcopy(self.s);h.save(self.path,self.s);raw=self.path.read_bytes();e=self.migration(raw);self.s=h.transaction(self.path,e);archive=self.s['harness']['legacy_archives']['migrate']
  self.assertEqual(raw,base64.b64decode(archive['source_bytes_base64']));self.assertEqual(before['tasks'],self.s['tasks']);self.assertEqual(before['history'],self.s['history'][:-1]);self.assertEqual(20,len(self.s['harness']['runs']));self.assertEqual(20,h.usage_summary(self.s)['unknown_runs']);self.assertIsNone(h.usage_summary(self.s)['reported_tokens'])
  for r in self.s['harness']['runs'].values():self.assertNotIn('reserve',r);self.assertNotIn('charged',r)
  for name in ('budget','spent','context_limit','review_limit','budget_changes'):self.assertNotIn(name,self.s['harness'])
  self.assertNotIn('ack',self.s['harness']['profiles']['owner']);self.assertEqual(self.s,h.transaction(self.path,e))
  self.ack();self.ev('rework',request_id='correct',task='task',member='owner',requester='leader',source_sha256=h.digest(self.s),reason='new scoped correction',evidence=str(self.proof));self.ack();self.ev('begin',member='owner',task='task',run='next')
 def test_stale_cas_unknown_run_and_atomic_failure_preserve_bytes(self):
  self.legacy();h.save(self.path,self.s);raw=self.path.read_bytes();e=self.migration(raw)
  for key in ('source_sha256','source_raw_sha256'):
   bad=dict(e,**{key:'stale'})
   with self.assertRaises(h.Invalid):h.transaction(self.path,bad)
   self.assertEqual(raw,self.path.read_bytes())
  with patch.object(h.os,'replace',side_effect=OSError('synthetic rename failure')):
   with self.assertRaises(OSError):h.transaction(self.path,e)
  self.assertEqual(raw,self.path.read_bytes());self.s['harness']['runs']['old-0']['state']='uncertain';h.save(self.path,self.s);e=self.migration(self.path.read_bytes())
  with self.assertRaises(h.Invalid):h.transaction(self.path,e)
 def test_budget_operations_and_reserve_fields_are_retired_not_reinterpreted(self):
  self.ack()
  for e in (dict(op='budget_change',request_id='x'),dict(op='resource_policy_adopt'),dict(op='begin',member='owner',task='task',run='x',reserve=5)):
   with self.assertRaises(h.Invalid):h.apply(self.s,e,self.root)
 def test_adapter_high_reported_usage_completes_and_actual_permission_request_stops(self):
  for mode in ('high-usage','missing-usage','request'):
   self.ack();h.save(self.path,self.s);log=self.root/('methods-'+mode)
   invoke=lambda:m.run(self.path,'owner','task',mode,[sys.executable,'-I','-S','-B',str(ROOT/'tests/fake_server.py'),mode,str(log)],self.root,5)
   if mode=='request':
    with self.assertRaises(h.Invalid):invoke()
    self.assertEqual('uncertain',json.loads(self.path.read_text())['harness']['runs'][mode]['state'])
   else:
    self.assertEqual('completed',invoke()['status']);self.assertNotIn('turn/interrupt',log.read_text());r=json.loads(self.path.read_text())['harness']['runs'][mode];self.assertEqual(35 if mode=='high-usage'else None,r['reported_usage'])
 def test_provider_quota_refusal_is_not_hidden_or_automatically_retried(self):
  self.ack();h.save(self.path,self.s);log=self.root/'quota-methods'
  with self.assertRaises(h.Invalid):m.run(self.path,'owner','task','quota',[sys.executable,'-I','-S','-B',str(ROOT/'tests/fake_server.py'),'provider-quota',str(log)],self.root,5)
  self.assertEqual(1,log.read_text().splitlines().count('turn/start'));self.assertEqual('uncertain',json.loads(self.path.read_text())['harness']['runs']['quota']['state'])
 def controller(self,usage=None,quota=False):
  methods=[];events=[]
  if usage is not None:events.append({'method':'thread/tokenUsage/updated','params':{'threadId':'fixture','tokenUsage':{'last':{'totalTokens':usage}}}})
  events.append({'method':'turn/completed','params':{'threadId':'fixture','turn':{'id':'turn','status':'completed'}}})
  class RPC:
   def request(inner,method,params,**kw):
    methods.append(method)
    if method=='thread/read':return {'thread':{'id':'fixture','model':'gpt-6.1-sol','reasoningEffort':'high','status':{'type':'idle'}}}
    if method=='turn/start':
     if quota:raise m.RPCError(method,{'code':429,'message':'Synthetic provider quota refusal'})
     return {'turn':{'id':'turn'}}
    return {}
   def next(inner,*args):return events.pop(0)
   def handle_request(inner,event):pass
  self.ack();h.save(self.path,self.s);ctl=c.Controller(self.path,RPC(),'fixture','local','fixture');ctl.bind('owner','fixture',owned=True,managed=True,effort='high');return ctl,methods
 def test_controller_usage_is_reporting_only_unknown_stays_null_and_quota_stays_rejected(self):
  for usage in (200000,None):
   ctl,methods=self.controller(usage);ctl.turn('owner','fixture',task='task');self.assertNotIn('turn/interrupt',methods);record=list(ctl.state()['harness']['controls'].values())[-1];self.assertEqual(usage,record['usage'])
  ctl,methods=self.controller(quota=True)
  with self.assertRaises(m.RPCError):ctl.turn('owner','fixture',task='task')
  self.assertEqual(1,methods.count('turn/start'));self.assertEqual('rejected',list(ctl.state()['harness']['controls'].values())[-1]['state']);self.assertEqual('not_executed',list(ctl.state()['harness']['runs'].values())[-1]['state'])
 def test_old_pass_does_not_accept_changed_artifact_or_supersede_new_fail(self):
  artifact=self.root/'artifact';artifact.write_text('first');self.ev('handoff',task='task',artifacts=[str(artifact)]);self.ev('review',task='task',reviewer='reviewer',verdict='pass',evidence=str(self.proof));artifact.write_text('changed')
  with self.assertRaises(h.Invalid):self.ev('accept',task='task')
  self.ev('handoff',task='task',artifacts=[str(artifact)]);self.ev('review',task='task',reviewer='reviewer',verdict='fail',evidence=str(self.proof))
  with self.assertRaises(h.Invalid):self.ev('accept',task='task')
 def test_corrupt_historical_bytes_cannot_be_hidden_by_new_contract(self):
  self.legacy();h.save(self.path,self.s);e=self.migration(self.path.read_bytes());self.s=h.transaction(self.path,e);self.s['harness']['legacy_archives']['migrate']['source_bytes_base64']=base64.b64encode(b'{}').decode()
  with self.assertRaises(h.Invalid):h.packet(self.s,'owner')
 def test_receipt_usage_is_counted_once_and_unknown_receipt_is_not_measured_zero(self):
  self.s['harness']['runs']={'real':{'state':'completed','reported_usage':7}}
  self.s['harness']['controls']={'real':{'state':'completed','requested':{'kind':'turn'},'usage':7},'receipt':{'state':'completed','requested':{'kind':'turn','receipt_only':True},'usage':3},'unknown':{'state':'completed','requested':{'kind':'turn','receipt_only':True},'usage':None}}
  summary=h.usage_summary(self.s);self.assertEqual(10,summary['reported_tokens']);self.assertEqual(1,summary['unknown_runs']);self.assertFalse(summary['complete'])
 def test_migrated_changes_retire_internal_accounting_but_keep_actual_decisions(self):
  self.legacy();self.s['harness']['changes']=[{'revision':1,'budget_request':'old','old_budget':100000,'new_budget':120000,'reason':'internal raise approval'},{'revision':2,'diagnostic_request':'old','max_reserve':5000,'evidence_goal':'Keep real evidence goal'},{'revision':3,'instruction':'User instruction about a product budget must remain verbatim','decisions':['Retain a real denied-write decision']}]
  h.save(self.path,self.s);self.s=h.transaction(self.path,self.migration(self.path.read_bytes()));p=h.packet(self.s,'owner');encoded=json.dumps(p['changes']);self.assertNotIn('new_budget',encoded);self.assertNotIn('budget_request',encoded);self.assertNotIn('max_reserve',encoded);self.assertIn('product budget must remain verbatim',encoded);self.assertIn('denied-write decision',encoded)
  self.assertEqual(p['changes'],h.active_changes(self.s['harness']['changes']))

if __name__=='__main__':unittest.main()
