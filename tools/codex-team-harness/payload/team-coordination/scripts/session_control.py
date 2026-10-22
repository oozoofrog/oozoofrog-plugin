#!/usr/bin/env python3
"""Official session configuration control and explicit project-scoped handoff.

Configuration receipts are not provider/model execution attestation. Native
callers need an owner checkpoint; this wrapper cannot lock another dispatcher.
"""
import argparse,copy,fcntl,hashlib,json,secrets,sys,time
from pathlib import Path
import harness as h

KINDS=('implementation','design','review','support','coordination')
UNRESOLVED=('request_pending','outcome_unknown','accepted_pending_observation','queued','pending_turn_application')
class ControlError(h.Invalid):
 def __init__(self,kind,message):self.kind=kind;super().__init__(message)
def now():return h.ledger.now()
def configuration(response):
 t=response.get('thread',{});status=t.get('status',{}).get('type')
 return {'thread':t.get('id'),'model':t.get('model'),'reasoning_effort':t.get('reasoningEffort'),'model_provider':t.get('modelProvider'),'status':status,'scope':'persisted'if status=='notLoaded'else 'live'if status in ('idle','active','systemError')else 'unknown','at':now(),'source':'thread/read','capability':'configured_metadata','reason':'Null/missing model or effort is unknown/unset; never per-turn telemetry'}
def matches(o,model,effort):return o.get('scope')=='live'and o.get('model')==model and effort is not None and o.get('reasoning_effort')==effort
def validate_choice(catalog,model,effort):
 entry=next((m for m in catalog if m.get('model')==model),None)
 if entry is None:raise ControlError('unsupported_model','Exact requestable model absent from complete catalog')
 if effort not in [e.get('reasoningEffort')for e in entry.get('supportedReasoningEfforts',[])]:raise ControlError('unsupported_effort','Effort absent from model catalog; no default inferred')
def typed_task(role,kind):
 h.require(kind in KINDS,'Explicit supported task kind required')
 h.require(not(role=='advisor'and kind=='implementation'),'Advisor independent implementation is forbidden')
 h.require(role!='leader'or kind=='coordination','Leader only coordinates; implementation needs core owner')
def turn_usage(notification):
 value=notification.get('tokenUsage',{}).get('last',{}).get('totalTokens')
 return value if type(value)is int else None
def runtime_unknown():return {'status':'unavailable','source':'official_app_server_schema','at':now(),'capability':'no_authoritative_execution_model_telemetry','reason':'Configuration, provider label, text ACK and absent reroute are not execution attestation'}
def baseline(paths):
 result={}
 for raw in paths:
  p=Path(raw);h.require(p.is_absolute()and not p.is_symlink(),'Canonical non-symlink paths required')
  h.require(str(p.resolve())==str(p),'Noncanonical ownership path')
  h.require(not any(part in ('.git','.aws','.ssh')for part in p.parts),'Private metadata path refused')
  h.require(not p.is_dir(),'Handoff requires explicit file paths; expand the allowlist first')
  result[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()if p.is_file()else None
 return result
def ack_text(x):return 'HARNESS_PACKET_RECEIVED '+x['packet_hash']+' '+x['nonce']
def session(s,member):
 value=s['harness'].get('sessions',{}).get(member)
 h.require(value is not None,'Session is not bound to this project');return value
def gate(s,member,kind,observation=None):
 typed_task(s['harness']['profiles'][member]['role'],kind)
 x=session(s,member);h.require(x.get('managed')is True,'Unmanaged session must complete explicit transfer first');h.require(x['execution']=='enabled','Session execution is paused or disabled')
 h.require(not any(v.get('member')==member and v['state']in UNRESOLVED for v in s['harness'].get('controls',{}).values()),'Pending/unknown control blocks execution')
 o=observation or x.get('configured_observed',{});expected=x.get('policy_expected',{})
 h.require(matches(o,expected.get('model'),expected.get('reasoning_effort')),'Fresh matching live configuration required')
 h.require(o.get('status')=='idle','Idle snapshot required; it is not an external lock')
 h.require(time.time()-x.get('observed_monotonic_wall',0)<=30,'Configuration observation expired')

def apply(s,e):
 """Called by harness.apply under its single project-record transaction lock."""
 a=s['harness'];sessions=a.setdefault('sessions',{});controls=a.setdefault('controls',{});handoffs=a.setdefault('handoffs',{});op=e['op']
 if op=='control_bind':
  m=e['member'];h.require(m in a['profiles'],'Registered project member required');old=sessions.get(m)
  h.require(not old or old['execution']=='enabled','Paused/disabled source cannot rebind')
  if old and old['identity']!=e['identity']:
   run=e.get('replacement_run');candidate=a['runs'].get(run,{})
   h.require(candidate.get('member')==m and candidate.get('state')=='active'and candidate.get('phase')=='reserved','Only newly reserved managed run may replace terminal identity')
   h.require(not any(key!=run and value['member']==m and value['state']in ('active','uncertain')for key,value in a['runs'].items()),'Prior run unresolved')
   h.require(not any(v.get('member')==m and v['state']in UNRESOLVED for v in controls.values()),'Prior session operation unresolved')
  identity=e['identity'];h.require(all(isinstance(identity.get(k),str)and identity[k]for k in ('host','transport','thread','controller')),'Exact session identity required')
  sessions[m]={'identity':identity,'managed':e.get('managed',False),'execution':'enabled','policy_expected':{'model':a['profiles'][m]['model'],'reasoning_effort':e.get('effort')},'runtime_observed':runtime_unknown()}
 elif op=='control_observe':
  x=session(s,e['member']);x['configured_observed']=e['observation'];x['observed_monotonic_wall']=time.time();x['runtime_observed']=runtime_unknown()
 elif op=='control_intent':
  h.require(e['operation']not in controls,'Operation ID already exists; inspect/reconcile, never resend')
  h.require(not any(v.get('member')==e['member']and v['state']in UNRESOLVED and key!=e['requested'].get('application_for')for key,v in controls.items()),'Prior unresolved operation blocks new IDs; inspect/reconcile first')
  requested=e['requested'];reservation=requested.get('packet_reserve',0)
  if requested.get('packet_handoff')is not None or requested.get('application_for')is not None or reservation:
   active=[v for v in controls.values()if v.get('packet_reserve')and v['state']in ('request_pending','outcome_unknown')];runs=[v for v in a['runs'].values()if v['state']in ('active','uncertain')]
   h.require(type(reservation)is int and reservation>0,'Positive packet reservation required')
   h.require(len(active)+len(runs)<a['concurrency'],'Concurrency exhausted by packet receipt')
   h.require(a['spent']+sum(v['packet_reserve']for v in active)+sum(v['reserve']for v in runs)+reservation<=a['budget'],'Packet receipt budget exhausted')
  session(s,e['member']);controls[e['operation']]={'member':e['member'],'state':e['state'],'requested':requested,'at':now(),'intent_time_ns':time.time_ns(),'source':'controller_before_rpc','pending_next_turn':True,'packet_reserve':reservation}
 elif op=='control_result':
  x=controls[e['operation']];x['state']=e['state'];x.update(e.get('evidence',{}));x['updated_at']=now()
  if x.get('packet_reserve')and e['state']=='completed'and not x.get('charged'):
   x['charged']=max(x['packet_reserve'],e.get('evidence',{}).get('usage',0));a['spent']+=x['charged']
  if e['state']=='configuration_pending_turn':
   member=x['member'];sessions[member]['policy_expected']=x['requested'];sessions[member]['configured_observed']=e['evidence']['configured_observed'];sessions[member]['observed_monotonic_wall']=time.time()
   x['configuration_time_ns']=time.time_ns()
 elif op=='control_handoff_prepare':
  hid=e['handoff'];h.require(hid not in handoffs,'Duplicate handoff ID');x=session(s,e['source']);h.require(x['execution']!='disabled','Source already transferred')
  h.require(not any(v['state']in ('active','uncertain')for v in a['runs'].values()),'Drain all source commands and resolve uncertainty first')
  h.require(not any(v['state']in UNRESOLVED for v in controls.values()),'Pending controls block handoff')
  h.require(e['recipient']not in s['members'],'Recipient must be a new project member')
  role=e['role'];h.require(role in h.MODELS,'Unknown recipient role');model=h.MODELS[role]or e.get('selected_model');h.require(bool(model),'Null-model role requires explicit selected model')
  h.require(e.get('selected_model')in (None,model),'Selected model conflicts with exact role policy')
  for task in e['tasks']:
   t=s['tasks'][task];h.require(t['owner']==e['source'],'Source task ownership changed');typed_task(role,t.get('kind','implementation'))
  h.require(e.get('explicit_request')is True and e.get('drained')is True,'Explicit transition request and drained source checkpoint required')
  proof=h.ledger.evidence(e['checkpoint']);h.require(h.ledger.fresh(proof),'Source owner stop ACK required')
  stop=json.loads(Path(e['checkpoint']).read_text());identity=x['identity']
  h.require(stop.get('source')==identity['thread']and stop.get('controller')==identity['controller']and stop.get('commands_drained')is True,'Stop ACK must identify actual source/controller and drained commands')
  h.require(stop.get('execution_stopped')is True or (identity.get('owned')and stop.get('exclusive_dispatch')is True),'External source requires explicit owner stop attestation; no OS lock inferred')
  paths=[p for task in e['tasks']for p in s['tasks'][task]['paths']];files=baseline(paths)
  packet=copy.deepcopy(e['packet']);h.require(all(k in packet for k in ('goal','decisions','constraints','remaining_work','permission_ceiling')),'Minimal handoff packet incomplete')
  h.require(packet['permission_ceiling']=={'sandbox':'read-only','publication':False},'This adapter supports read-only/no-publication ceiling only')
  packet.update({'tasks':e['tasks'],'baseline':files,'source_identity':x['identity'],'source_checkpoint':proof,'project_revision':a['revision']})
  handoffs[hid]={'state':'prepared','source':e['source'],'recipient':e['recipient'],'role':role,'selected_model':model,'tasks':e['tasks'],'packet':packet,'packet_hash':h.digest(packet),'nonce':e['nonce'],'checkpoint':proof,'at':now()}
  x['execution']='paused'
 elif op=='control_handoff_intent':
  x=handoffs[e['handoff']];phase=e['phase'];expected={'creation_pending':'prepared','delivery_pending':'recipient_created'}
  h.require(x['state']==expected.get(phase),'Invalid or unresolved handoff operation; no automatic retry');x['state']=phase;x['intent_at']=now()
 elif op=='control_recipient':
  x=handoffs[e['handoff']];h.require(x['state']=='creation_pending','Recipient creation not pending');m=x['recipient'];h.require(e['model']==x['selected_model'],'Recipient model substitution')
  s['members'][m]={'role':x['role'],'identity_claim':x['checkpoint'],'runtime_id_claim':e['identity']['thread']}
  a['profiles'][m]={'role':x['role'],'epoch':0,'model':e['model'],'last_revision':0}
  sessions[m]={'identity':e['identity'],'managed':False,'execution':'paused','policy_expected':{'model':e['model'],'reasoning_effort':e['effort']},'runtime_observed':runtime_unknown()}
  x['state']='recipient_created'
 elif op=='control_packet_received':
  x=handoffs[e['handoff']];h.require(x['state']=='delivery_pending','Delivery not pending')
  h.require(a['revision']==x['packet']['project_revision'],'Project changed after handoff preparation')
  h.require(ack_text(x)in e['text']and bool(e['turn']),'Actual matching packet receipt required')
  dest=session(s,x['recipient']);h.require(e['observation'].get('thread')==dest['identity']['thread'],'Packet observation identity mismatch');h.require(matches(e['observation'],**{'model':dest['policy_expected']['model'],'effort':dest['policy_expected']['reasoning_effort']}),'Recipient live config mismatch')
  x.update({'state':'packet_received','receipt':{'turn':e['turn'],'packet_hash':x['packet_hash'],'at':now(),'source':'completed_model_turn_text','scope':'packet_receipt_only'}})
  dest['configured_observed']=e['observation'];dest['observed_monotonic_wall']=time.time()
 elif op=='control_transfer':
  x=handoffs[e['handoff']];h.require(x['state']=='packet_received','Recipient packet receipt required')
  h.require(a['revision']==x['packet']['project_revision'],'Project changed before transfer; keep both paused')
  h.require(h.ledger.fresh(x['checkpoint']),'Stale source stop ACK')
  h.require(e['source_status']=='idle'and e['recipient_status']=='idle','Both sides must be quiescent')
  h.require(baseline(x['packet']['baseline'])==x['packet']['baseline'],'Uncommitted baseline changed')
  for task in x['tasks']:h.require(s['tasks'][task]['owner']==x['source'],'Canonical owner changed')
  h.require(not any(r['state']in ('active','uncertain')for r in a['runs'].values()),'Unresolved source execution')
  h.require(not any(v['state']in UNRESOLVED for v in controls.values()),'Pending session operation blocks transfer')
  for task in x['tasks']:s['tasks'][task]['owner']=x['recipient'];s['tasks'][task]['state']='assigned'
  session(s,x['source'])['execution']='disabled';session(s,x['recipient'])['execution']='paused';a['revision']+=1
  x.update({'state':'transferred','transfer_revision':a['revision'],'transferred_at':now(),'transfer_time_ns':time.time_ns(),'transfer_nonce':secrets.token_hex(16)})
  for profile in a['profiles'].values():profile.pop('ack',None)
 elif op=='control_owner_ack':
  x=handoffs[e['handoff']];h.require(x['state']=='transferred'and e['revision']==x['transfer_revision']==a['revision'],'ACK must bind exact transfer revision')
  proof=Path(e['evidence']);expected={'handoff':e['handoff'],'recipient':x['recipient'],'transfer_revision':x['transfer_revision'],'transfer_nonce':x['transfer_nonce']}
  h.require(proof.stat().st_mtime_ns>=x['transfer_time_ns']and json.loads(proof.read_text())==expected,'Owner ACK must be created after commit and contain exact transfer receipt')
  x['owner_ack']=h.ledger.evidence(proof);h.require(h.ledger.fresh(x['owner_ack']),'Real owner ACK evidence required');x['owner_ack_source']='operator_attestation_of_committed_transfer_revision';x['state']='acknowledged'
 elif op=='control_resume':
  x=handoffs[e['handoff']];h.require(x['state']=='acknowledged','Actual owner transfer ACK required');h.require(x['transfer_revision']==a['revision'],'Project revision changed after transfer; keep recipient paused');h.require(h.ledger.fresh(x['owner_ack']),'Owner ACK changed')
  dest=session(s,x['recipient']);h.require(matches(e['observation'],dest['policy_expected']['model'],dest['policy_expected']['reasoning_effort']),'Recipient configuration unknown/mismatched')
  h.require(e['observation']['status']=='idle','Recipient busy');dest['managed']=True;dest['execution']='enabled';dest['configured_observed']=e['observation'];dest['observed_monotonic_wall']=time.time();x['state']='resumed'
 elif op=='control_handoff_failure':
  x=handoffs[e['handoff']];x['failure']={'phase':x['state'],'reason':e['reason'],'at':now(),'automatic_retry':False};x['state']='outcome_unknown'if e.get('unknown')else 'blocked'
  # Canonical owner remains source before transfer, destination afterwards.
  for m in (x['source'],x['recipient']):
   if m in sessions and sessions[m]['execution']!='disabled':sessions[m]['execution']='paused'
 else:raise h.Invalid('Unknown control operation')
 return s

class Controller:
 def __init__(self,path,rpc,controller,host,transport):self.path=Path(path);self.rpc=rpc;self.identity={'controller':controller,'host':host,'transport':transport}
 def state(self):return json.loads(self.path.read_text())
 def event(self,op,**values):return h.transaction(self.path,dict(op=op,**values))
 def bind(self,member,thread,owned=False,effort=None,managed=False,replacement_run=None):
  return self.event('control_bind',member=member,identity=dict(self.identity,thread=thread,owned=owned),effort=effort,managed=managed,replacement_run=replacement_run)
 def require_control(self,member,checkpoint=None):
  x=session(self.state(),member);identity=x['identity']
  if any(identity[k]!=self.identity[k]for k in self.identity):raise ControlError('ownership_conflict','Host/transport/controller mismatch')
  if not identity.get('owned')and not checkpoint:raise ControlError('manual_required','External dispatcher requires actual owner quiescent checkpoint; idle is not a lock')
  if checkpoint:h.require(h.ledger.fresh(h.ledger.evidence(checkpoint)),'Checkpoint evidence unavailable')
  return identity
 def inspect(self,member):
  x=session(self.state(),member);identity=x['identity']
  if any(identity[k]!=self.identity[k]for k in self.identity):raise ControlError('unsupported_platform','Session host/transport/controller differs; no fallback')
  o=configuration(self.rpc.request('thread/read',{'threadId':identity['thread'],'includeTurns':False}));h.require(o['thread']==identity['thread'],'Server returned different thread identity');self.event('control_observe',member=member,observation=o);return o
 def catalog(self):
  models=[];cursor=None;seen=set()
  while True:
   page=self.rpc.request('model/list',{'limit':100,'includeHidden':True,'cursor':cursor});models.extend(page['data']);cursor=page.get('nextCursor')
   if not cursor:return models
   h.require(cursor not in seen,'Catalog pagination cycle');seen.add(cursor)
 def change(self,member,operation,model,effort,checkpoint=None):
  identity=self.require_control(member,checkpoint);profile=self.state()['harness']['profiles'][member]
  h.require(session(self.state(),member)['execution']=='enabled','Paused/disabled source cannot request model change')
  h.require(model==(h.MODELS[profile['role']]or profile['model']),'Requested model violates role policy; no silent substitution')
  validate_choice(self.catalog(),model,effort);before=self.inspect(member);requested={'model':model,'reasoning_effort':effort,'source':'explicit_request','at':now()}
  state='pending_turn_application'if before['status']=='idle'and before['scope']=='live'else 'queued'
  self.event('control_intent',member=member,operation=operation,state=state,requested=requested)
  self.event('control_result',operation=operation,state=state,evidence={'accepted':None,'configured_observed':self.inspect(member),'runtime_observed':runtime_unknown(),'pending_next_turn':True,'reason':'Explicit apply-change sends official turn/start model+effort at idle boundary; resume is not used as a loaded-session setter'})
  return self.state()['harness']['controls'][operation]
 def apply_change(self,member,operation,reserve,checkpoint=None):
  h.require(type(reserve)is int and reserve>0,'Positive configuration-turn reservation required')
  x=self.state()['harness']['controls'][operation];h.require(x['member']==member and x['state']in ('pending_turn_application','queued'),'Change is not pending or has uncertain outcome')
  h.require(session(self.state(),member)['execution']=='enabled','Paused/disabled source cannot apply configuration')
  self.require_control(member,checkpoint);validate_choice(self.catalog(),x['requested']['model'],x['requested']['reasoning_effort'])
  return self.turn(member,'Do not use tools, delegate, edit files or perform implementation. Return exactly HARNESS_CONFIGURATION_CHECK.',reserve=reserve,configuration_operation=operation,checkpoint=checkpoint)
 def verify_after_turn(self,member,operation,turn):
  state=self.state();x=state['harness']['controls'][operation];h.require(x['state']=='configuration_pending_turn','Configuration change not ready for next-turn verification')
  h.require(any(v.get('member')==member and v.get('turn')==turn and v.get('state')=='completed'and v['intent_time_ns']>x['configuration_time_ns']for v in state['harness']['controls'].values()),'Observed completed controlled turn after configuration required')
  after=self.inspect(member)
  h.require(matches(after,x['requested']['model'],x['requested']['reasoning_effort']),'Configuration mismatch after turn')
  self.event('control_result',operation=operation,state='configuration_verified_after_turn',evidence={'configured_observed':after,'turn':turn,'pending_next_turn':False,'runtime_observed':runtime_unknown()});return after
 def prepare_handoff(self,hid,source,recipient,role,tasks,packet,checkpoint,explicit_request=False,selected_model=None):
  self.require_control(source,checkpoint)
  snapshot=self.inspect(source);h.require(snapshot['scope']=='live'and snapshot['status']=='idle','Source must be loaded and quiescent at owner checkpoint')
  s=self.event('control_handoff_prepare',handoff=hid,source=source,recipient=recipient,role=role,selected_model=selected_model,tasks=tasks,packet=packet,checkpoint=checkpoint,explicit_request=explicit_request,drained=True,nonce=secrets.token_hex(16));return s['harness']['handoffs'][hid]['packet']
 def create_recipient(self,hid,effort,cwd):
  x=self.state()['harness']['handoffs'][hid];model=x['selected_model'];validate_choice(self.catalog(),model,effort)
  self.event('control_handoff_intent',handoff=hid,phase='creation_pending')
  try:
   r=self.rpc.request('thread/start',{'model':model,'cwd':str(Path(cwd).resolve()),'sandbox':'read-only','approvalPolicy':'never','config':{'model_reasoning_effort':effort}})
   tid=r['thread']['id']
   self.event('control_recipient',handoff=hid,identity=dict(self.identity,thread=tid,owned=True),model=r.get('model'),effort=r.get('reasoningEffort'))
   o=self.inspect(x['recipient']);h.require(matches(o,model,effort),'Recipient configuration unavailable/mismatched');return tid
  except Exception as exc:
   self.event('control_handoff_failure',handoff=hid,reason=str(exc),unknown=not hasattr(exc,'code'));raise
 def turn(self,member,prompt,timeout=120,packet_handoff=None,task=None,reserve=None,configuration_operation=None,checkpoint=None):
  if packet_handoff or configuration_operation:h.require(type(reserve)is int and reserve>0,'Positive receipt-turn reservation required')
  identity=self.require_control(member,checkpoint);before=self.inspect(member);receipt_only=bool(packet_handoff or configuration_operation)
  if packet_handoff:
   x=self.state()['harness']['handoffs'][packet_handoff];h.require(member==x['recipient'],'Packet recipient identity mismatch');expected=session(self.state(),member)['policy_expected'];h.require(matches(before,expected['model'],expected['reasoning_effort'])and before['status']=='idle','Packet target not ready')
   self.event('control_handoff_intent',handoff=packet_handoff,phase='delivery_pending')
  elif configuration_operation:
   change=self.state()['harness']['controls'][configuration_operation];h.require(change['member']==member and change['state']in ('pending_turn_application','queued')and before['status']=='idle'and before['scope']=='live','Configuration application requires owned idle boundary')
  else:
   state=self.state();h.require(task in state['tasks'],'Explicit owned task required');gate(state,member,state['tasks'][task].get('kind','implementation'),before)
  operation='turn-'+secrets.token_hex(16)
  # No per-turn model/effort override: test and use persistent configured defaults.
  try:
   with open(str(self.path)+'.lock','a')as lock:
    h.require(not self.path.is_symlink()and not Path(str(self.path)+'.lock').is_symlink(),'State/lock symlink refused')
    fcntl.flock(lock,fcntl.LOCK_EX);state=self.state()
    if not receipt_only:
     gate(state,member,state['tasks'][task].get('kind','implementation'),before)
     state=h.apply(state,{'op':'begin','member':member,'task':task,'run':operation,'reserve':reserve})
    elif packet_handoff:h.require(state['harness']['handoffs'][packet_handoff]['state']=='delivery_pending','Packet delivery state changed')
    else:
     h.require(session(state,member)['execution']=='enabled','Paused/disabled source cannot dispatch configuration turn')
     h.require(state['harness']['controls'][configuration_operation]['state']in ('pending_turn_application','queued'),'Configuration intent changed')
    state=h.apply(state,{'op':'control_intent','member':member,'operation':operation,'state':'request_pending','requested':{'kind':'turn','packet_handoff':packet_handoff,'application_for':configuration_operation,'packet_reserve':reserve if receipt_only else 0,'source':'turn/start','at':now()}});h.save(self.path,state)
    params={'threadId':identity['thread'],'input':[{'type':'text','text':prompt,'text_elements':[]}]}
    if configuration_operation:params.update(model=change['requested']['model'],effort=change['requested']['reasoning_effort'])
    r=self.rpc.request('turn/start',params)
   turn=r['turn']['id'];text=[];end=time.monotonic()+timeout;usage=None
   if configuration_operation:self.event('control_result',operation=configuration_operation,state='accepted_pending_observation',evidence={'accepted':{'model':params['model'],'reasoning_effort':params['effort'],'turn':turn,'source':'turn/start_parameter_acknowledgement','at':now()}})
   start_revision=self.state()['harness']['revision']
   while time.monotonic()<end:
    current=self.state()
    h.require(current['harness']['policy_hash']==h.digest(h.effective_contract()),'Effective policy changed during turn')
    if not receipt_only:
     run=current['harness']['runs'][operation];profile=current['harness']['profiles'][member]
     h.require(not run['stale']and run['revision']==current['harness']['revision']and run['epoch']==profile['epoch'],'Instruction/context changed during turn')
    else:h.require(current['harness']['revision']==start_revision,'Project revision changed during receipt turn')
    event=self.rpc.next(.5)
    if event is None:continue
    self.rpc.handle_request(event);method=event.get('method');p=event.get('params',{})
    if p.get('threadId')!=identity['thread']:continue
    if method=='model/rerouted':raise ControlError('substitution','Server reported model reroute: '+json.dumps(p))
    if method=='thread/tokenUsage/updated':
     usage=turn_usage(p)
     if type(usage)is int:h.require(usage<reserve,'Reported usage reached reservation')
    if method=='thread/compacted'or (method=='item/completed'and p.get('item',{}).get('type')=='contextCompaction'):
     h.transaction(self.path,{'op':'boundary','member':member,'reason':'compaction'});raise h.Invalid('Compaction requires fresh acknowledgement')
    if method=='item/completed'and p.get('item',{}).get('type')=='agentMessage':text.append(p['item'].get('text',''))
    if method=='turn/completed'and p.get('turn',{}).get('id')==turn:
     h.require(p['turn'].get('status')=='completed','Turn failed: '+json.dumps(p['turn'].get('error')))
     after=self.inspect(member);body='\n'.join(text)
     if packet_handoff:self.event('control_packet_received',handoff=packet_handoff,turn=turn,text=body,observation=after)
     elif configuration_operation:
      h.require(matches(after,params['model'],params['effort']),'Configuration application substituted or unavailable')
      self.event('control_result',operation=configuration_operation,state='configuration_pending_turn',evidence={'configured_observed':after,'runtime_observed':runtime_unknown(),'pending_next_turn':True})
     else:
      event={'op':'finish','run':operation,'outcome':'completed','evidence':'Observed turn/completed '+turn}
      if type(usage)is int:event['usage']=usage
      h.transaction(self.path,event)
     self.event('control_result',operation=operation,state='completed',evidence={'turn':turn,'usage':usage if type(usage)is int else 0,'configured_observed':after,'runtime_observed':runtime_unknown()})
     return {'turn':turn,'text':body,'before':before,'after':after,'runtime_observed':runtime_unknown()}
   raise TimeoutError('Turn completion unknown; do not resend')
  except Exception as exc:
   if 'turn'in locals():
    try:self.rpc.request('turn/interrupt',{'threadId':identity['thread'],'turnId':turn},timeout=3)
    except Exception:pass
   if operation in self.state()['harness'].get('controls',{}):self.event('control_result',operation=operation,state='rejected'if hasattr(exc,'code')else 'outcome_unknown',evidence={'error':str(exc),'automatic_retry':False})
   if packet_handoff:self.event('control_handoff_failure',handoff=packet_handoff,reason=str(exc),unknown=True)
   if configuration_operation:self.event('control_result',operation=configuration_operation,state='outcome_unknown',evidence={'error':str(exc),'automatic_retry':False})
   elif operation in self.state()['harness']['runs']:
    h.transaction(self.path,{'op':'finish','run':operation,'outcome':'not_executed'if hasattr(exc,'code')else 'uncertain','evidence':str(exc)})
   raise
 def deliver_packet(self,hid,reserve):
  x=self.state()['harness']['handoffs'][hid]
  prompt='Read this project handoff packet. Do no implementation, tools, delegation or file edits. Confirm receipt by returning exactly the ACK line below. It proves packet receipt only.\n'+json.dumps(x['packet'],ensure_ascii=False)+'\n'+ack_text(x)
  h.require(len(prompt.encode())//4<=self.state()['harness']['context_limit'],'Packet exceeds context estimate limit')
  return self.turn(x['recipient'],prompt,packet_handoff=hid,reserve=reserve)
 def transfer(self,hid):
  x=self.state()['harness']['handoffs'][hid]
  src=self.inspect(x['source']);dest=self.inspect(x['recipient'])
  h.require(matches(dest,session(self.state(),x['recipient'])['policy_expected']['model'],session(self.state(),x['recipient'])['policy_expected']['reasoning_effort']),'Recipient drift blocks transfer')
  s=self.event('control_transfer',handoff=hid,source_status=src['status'],recipient_status=dest['status']);return s['harness']['handoffs'][hid]['transfer_revision']
 def resume(self,hid):
  x=self.state()['harness']['handoffs'][hid];self.require_control(x['recipient']);o=self.inspect(x['recipient']);return self.event('control_resume',handoff=hid,observation=o)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state',type=Path,required=True);p.add_argument('--controller',required=True);p.add_argument('--host',required=True)
 p.add_argument('--transport',choices=('native-proxy','owned-stdio'),required=True);p.add_argument('--socket',help='Explicit authorized official proxy endpoint; never discovered from private files')
 sub=p.add_subparsers(dest='operation',required=True)
 for name in ('inspect','change'):
  q=sub.add_parser(name);q.add_argument('--member',required=True)
  if name=='change':q.add_argument('--operation-id',required=True);q.add_argument('--model',required=True);q.add_argument('--effort',required=True);q.add_argument('--owner-checkpoint')
 q=sub.add_parser('bind');q.add_argument('--member',required=True);q.add_argument('--thread',required=True)
 q=sub.add_parser('prepare');q.add_argument('--handoff',required=True);q.add_argument('--source',required=True);q.add_argument('--recipient',required=True);q.add_argument('--role',choices=tuple(h.MODELS),required=True);q.add_argument('--model',help='Required explicit choice for null-model leader; never inferred');q.add_argument('--tasks',nargs='+',required=True);q.add_argument('--packet',type=Path,required=True);q.add_argument('--owner-stop-ack',required=True);q.add_argument('--explicit-user-request',action='store_true')
 q=sub.add_parser('create');q.add_argument('--handoff',required=True);q.add_argument('--effort',required=True);q.add_argument('--cwd',type=Path,required=True)
 for name in ('deliver','transfer','resume'):
  q=sub.add_parser(name);q.add_argument('--handoff',required=True)
  if name=='deliver':q.add_argument('--reserve',type=int,required=True)
 q=sub.add_parser('owner-ack');q.add_argument('--handoff',required=True);q.add_argument('--revision',type=int,required=True);q.add_argument('--evidence',required=True)
 q=sub.add_parser('verify');q.add_argument('--member',required=True);q.add_argument('--operation-id',required=True);q.add_argument('--turn',required=True)
 q=sub.add_parser('apply-change');q.add_argument('--member',required=True);q.add_argument('--operation-id',required=True);q.add_argument('--reserve',type=int,required=True);q.add_argument('--owner-checkpoint')
 q=sub.add_parser('turn');q.add_argument('--member',required=True);q.add_argument('--task',required=True);q.add_argument('--reserve',type=int,required=True);q.add_argument('--prompt',type=Path,required=True)
 a=p.parse_args();from managed_run import RPC
 if a.transport=='native-proxy'and not a.socket:raise ControlError('unsupported_transport','Explicit authorized native proxy socket required; no automatic standalone fallback')
 command=['codex','app-server','proxy','--sock',a.socket]if a.transport=='native-proxy'else ['codex','app-server','--stdio'];rpc=RPC(command)
 try:
  rpc.request('initialize',{'clientInfo':{'name':'team-session-control','version':'0.2.0'}});rpc.send({'method':'initialized'});ctl=Controller(a.state,rpc,a.controller,a.host,'official-'+a.transport+(':'+a.socket if a.transport=='native-proxy'else ''))
  if a.operation=='inspect':result=ctl.inspect(a.member)
  elif a.operation=='change':result=ctl.change(a.member,a.operation_id,a.model,a.effort,a.owner_checkpoint)
  elif a.operation=='bind':result=ctl.bind(a.member,a.thread)
  elif a.operation=='prepare':result=ctl.prepare_handoff(a.handoff,a.source,a.recipient,a.role,a.tasks,json.loads(a.packet.read_text()),a.owner_stop_ack,a.explicit_user_request,a.model)
  elif a.operation=='create':result=ctl.create_recipient(a.handoff,a.effort,a.cwd)
  elif a.operation=='deliver':result=ctl.deliver_packet(a.handoff,a.reserve)
  elif a.operation=='transfer':result={'transfer_revision':ctl.transfer(a.handoff)}
  elif a.operation=='owner-ack':result=ctl.event('control_owner_ack',handoff=a.handoff,revision=a.revision,evidence=a.evidence)
  elif a.operation=='resume':result=ctl.resume(a.handoff)
  elif a.operation=='verify':result=ctl.verify_after_turn(a.member,a.operation_id,a.turn)
  elif a.operation=='apply-change':result=ctl.apply_change(a.member,a.operation_id,a.reserve,a.owner_checkpoint)
  else:result=ctl.turn(a.member,a.prompt.read_text(),task=a.task,reserve=a.reserve)
  print(json.dumps(result))
 finally:rpc.close()
if __name__=='__main__':
 try:main()
 except Exception as exc:print(json.dumps({'error':str(exc),'kind':getattr(exc,'kind','unknown'),'automatic_retry':False}));sys.exit(2)
