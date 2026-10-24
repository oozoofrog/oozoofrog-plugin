#!/usr/bin/env python3
"""Opt-in stdio app-server client; live transport receipts, no history scraping."""
import argparse,fcntl,json,os,selectors,subprocess,sys,time
from pathlib import Path
import harness as h
class RPCError(h.Invalid):
 def __init__(self,method,error):self.code=error.get('code');self.error=error;super().__init__('Server rejected '+method+': '+json.dumps(error))
class RPC:
 def __init__(self,command,tier_contract=None):
  self.tier_contract=tier_contract # Selected client schema contract, not server attestation.
  self.p=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,bufsize=0)
  self.selector=selectors.DefaultSelector();self.selector.register(self.p.stdout,selectors.EVENT_READ);self.buffer=b'';self.seq=0
 def send(self,item):
  self.p.stdin.write((json.dumps(item)+'\n').encode());self.p.stdin.flush()
 def next(self,timeout=1):
  if b'\n' not in self.buffer:
   if not self.selector.select(timeout):return None
   chunk=os.read(self.p.stdout.fileno(),65536)
   if not chunk:raise ConnectionError('App-server disconnected')
   self.buffer+=chunk
  if b'\n' not in self.buffer:return None
  line,self.buffer=self.buffer.split(b'\n',1);return json.loads(line)
 def request(self,method,params,on_event=lambda _:None,timeout=20):
  self.seq+=1;request_id=self.seq;self.send({'id':request_id,'method':method,'params':params});end=time.monotonic()+timeout
  while time.monotonic()<end:
   o=self.next()
   if o is None:continue
   if o.get('id')==request_id and 'method'not in o:
    if 'error'in o:raise RPCError(method,o['error'])
    return o['result']
   self.handle_request(o);on_event(o)
  raise TimeoutError('Request outcome unknown: '+method)
 def handle_request(self,o):
  if 'id'in o and 'method'in o:
   self.send({'id':o['id'],'error':{'code':-32601,'message':'Managed client does not grant permission or tool requests'}})
   raise h.Invalid('Unexpected server request; abort without granting permission')
 def close(self):
  self.p.terminate()
  try:self.p.wait(timeout=3)
  except subprocess.TimeoutExpired:self.p.kill();self.p.wait()
  self.selector.close();self.p.stdin.close();self.p.stdout.close()

def read(path):return json.loads(Path(path).read_text())
def dispatch(rpc,path,run,thread_id,prompt,model):
 """Revision check and turn/start write share state lock; ACK alone is insufficient."""
 with open(str(path)+'.lock','a')as lock:
  fcntl.flock(lock,fcntl.LOCK_EX);s=read(path);r=s['harness']['runs'][run];p=s['harness']['profiles'][r['member']]
  h.require(s['harness']['policy_hash']==h.digest(h.effective_contract()),'Effective policy changed before dispatch')
  h.require(r['state']=='active' and not r['stale'] and r['revision']==s['harness']['revision'] and r['epoch']==p['epoch'],'Instruction/epoch changed before dispatch')
  h.require(r['model']==model and s['tasks'][r['task']]['owner']==r['member'],'Owner/model changed')
  import session_control as control
  import profile_defaults as profiles
  control.gate(s,r['member'],s['tasks'][r['task']].get('kind','implementation'))
  expected=s['harness']['sessions'][r['member']]['policy_expected'];params={'threadId':thread_id,'model':model,'input':[{'type':'text','text':prompt,'text_elements':[]}]}
  if expected.get('service_tier')=='normal':
   profiles.require_tier_contract(rpc,expected['tier_resolution']);params.update(profiles.tier_parameters(expected['tier_resolution'],'turn/start'))
  # Persist before sending: a crash here is uncertain, never an automatic retry.
  s=h.apply(s,{'op':'observe','run':run,'phase':'dispatch_uncertain','receipt':{'thread_id':thread_id,'model':model}});h.save(path,s)
  rpc.seq+=1;i=rpc.seq;rpc.send({'id':i,'method':'turn/start','params':params})
  return i

def run(path,member,task,run_id,command,cwd,timeout=120):
 h.transaction(path,{'op':'begin','member':member,'task':task,'run':run_id})
 rpc=None;dispatched=False;usage=None;thread_id=None;turn_id=None;terminal=False
 try:
  import profile_defaults as profiles
  rpc=RPC(command,tier_contract=profiles.CURRENT_TIER_CONTRACT);rpc.request('initialize',{'clientInfo':{'name':'team-coordination-harness','version':'0.1.0'}});rpc.send({'method':'initialized'})
  catalog=[];cursor=None
  while True:
   response=rpc.request('model/list',{'limit':100,'includeHidden':True,'cursor':cursor});catalog+=response['data'];cursor=response.get('nextCursor')
   if not cursor:break
  s=read(path);r=s['harness']['runs'][run_id];model=r['model']
  h.require(any(m.get('model')==model for m in catalog),'Exact model absent from live catalog')
  import session_control as control
  import profile_defaults as profiles
  role=s['harness']['profiles'][member]['role'];requested=profiles.role_request(h.effective_contract()['policy'],role);entry=next(m for m in catalog if m.get('model')==model);effort=requested.get('reasoning_effort',entry.get('defaultReasoningEffort'));requested.update(model=model,reasoning_effort=effort);params,resolution=profiles.start_parameters(catalog,requested)
  profiles.require_tier_contract(rpc,resolution)
  response=rpc.request('thread/start',dict(params,cwd=str(Path(cwd).resolve()),sandbox='read-only',approvalPolicy='never'))
  thread_id=response['thread']['id'];h.check_model(model,catalog,response)
  ctl=control.Controller(path,rpc,'managed-run:'+run_id,'local','official-owned-stdio');ctl.bind(member,thread_id,owned=True,effort=effort,managed=True,replacement_run=run_id,service_tier=requested.get('service_tier'),tier_resolution=resolution);ctl.inspect(member)
  if requested.get('service_tier')is not None:
   tier=profiles.configured(response,'thread/start')
   if requested['service_tier']!='normal':h.require(profiles.tier_matches(tier,resolution),'Configured service tier unavailable/substituted')
   ctl.event('control_tier_observe',member=member,observation=tier,generation=ctl.state()['harness']['sessions'][member]['configuration_generation'],response_bound=True)
  h.transaction(path,{'op':'observe','run':run_id,'phase':'thread_verified','receipt':{'thread_id':thread_id,'model':response['model'],'catalog_models':[m.get('model') for m in catalog]}})
  s=read(path);prompt=json.dumps(s['harness']['runs'][run_id]['packet'],ensure_ascii=False)+'\nPerform only the assigned task within read-only capability; return evidence and limits.'
  # Set uncertain before invocation, because send may succeed then throw.
  dispatched=True;request_id=dispatch(rpc,path,run_id,thread_id,prompt,model)
  deadline=time.monotonic()+timeout
  while time.monotonic()<deadline:
   s=read(path);r=s['harness']['runs'][run_id];p=s['harness']['profiles'][member]
   h.require(s['harness']['policy_hash']==h.digest(h.effective_contract()),'Effective policy changed during turn')
   h.require(not r['stale'] and r['revision']==s['harness']['revision'] and r['epoch']==p['epoch'],'Context changed during turn; interrupt required')
   o=rpc.next(.5)
   if o is None:continue
   rpc.handle_request(o)
   if o.get('id')==request_id:
    h.require('error'not in o,'turn/start rejected; inspect server state before retry');turn_id=o['result']['turn']['id']
    h.transaction(path,{'op':'observe','run':run_id,'phase':'turn_observed','receipt':{'turn_id':turn_id,'tier_request_accepted':profiles.tier_parameters(resolution,'turn/start')if requested.get('service_tier')=='normal'else {},'selected_client_contract':rpc.tier_contract,'scope':'request_acknowledgement_only'}})
   method=o.get('method');params=o.get('params',{})
   if method=='model/rerouted':raise h.Invalid('Server model reroute; continuation blocked')
   if method=='thread/tokenUsage/updated' and params.get('threadId')==thread_id:
    value=control.turn_usage(params)
    if type(value)is int:usage=value
   if method in ('thread/compacted','item/completed') and (method=='thread/compacted' or params.get('item',{}).get('type')=='contextCompaction'):
    h.transaction(path,{'op':'boundary','member':member,'reason':'compaction'});raise h.Invalid('Compaction requires fresh context acknowledgement')
   if method=='turn/completed' and params.get('threadId')==thread_id:
    status=params['turn'].get('status');terminal=True
    event={'op':'finish','run':run_id,'outcome':'completed' if status=='completed' else 'failed','evidence':'Observed turn/completed status='+str(status)}
    if usage is not None:event['usage']=usage
    h.transaction(path,event);return {'run':run_id,'thread_id':thread_id,'turn_id':turn_id,'status':status,'receipt_source':'live_app_server','sandbox':'read-only'}
  raise TimeoutError('Turn completion not observed')
 except Exception as exc:
  if rpc and dispatched and thread_id and turn_id:
   try:rpc.request('turn/interrupt',{'threadId':thread_id,'turnId':turn_id},timeout=3)
   except Exception:pass
  # Interrupt acknowledgement is not proof the turn reached a terminal state.
  if not terminal:
   outcome='uncertain' if dispatched else 'not_executed'
   h.transaction(path,{'op':'finish','run':run_id,'outcome':outcome,'evidence':type(exc).__name__+': '+str(exc)})
  raise
 finally:
  if rpc:rpc.close()

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state',type=Path,required=True);p.add_argument('--member',required=True);p.add_argument('--task',required=True);p.add_argument('--run',required=True);p.add_argument('--cwd',type=Path,required=True);a=p.parse_args()
 print(json.dumps(run(a.state,a.member,a.task,a.run,['codex','app-server','--stdio'],a.cwd)))
if __name__=='__main__':
 try:main()
 except Exception as e:print(json.dumps({'error':str(e),'inspect_state_before_retry':True}));sys.exit(2)
