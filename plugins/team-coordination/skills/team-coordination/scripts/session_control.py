#!/usr/bin/env python3
"""Official session configuration control and explicit project-scoped handoff.

Configuration receipts are not provider/model execution attestation. Native
callers need an owner checkpoint; this wrapper cannot lock another dispatcher.
"""
import argparse,copy,datetime,fcntl,hashlib,json,secrets,sys,time
from pathlib import Path
import harness as h
import profile_defaults as profiles
import external_handoff as external

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
def creation_parameters(params,creation):
 """Keep profile config and replace each creation policy as a whole value."""
 profile_config=params.get('config',{});creation_config=creation.get('config',{})
 h.require(isinstance(profile_config,dict)and isinstance(creation_config,dict),'Creation config must be an object')
 h.require('model'not in creation or creation['model']==params['model'],'Creation cannot substitute the selected model')
 h.require('model_reasoning_effort'not in creation_config or creation_config['model_reasoning_effort']==profile_config.get('model_reasoning_effort'),'Creation cannot substitute the selected reasoning effort')
 merged=dict(params,**creation)
 if 'config'in params or 'config'in creation:merged['config']=dict(profile_config,**creation_config)
 return merged
def state_cas(s,e,raw):
 h.require(raw is not None and hashlib.sha256(raw).hexdigest()==e.get('expected_state_sha256')and s['harness']['revision']==e.get('expected_revision'),'Stale canonical bytes or project revision; inspect committed receipt')
def predelivery(s,x):
 a=s['harness'];src=session(s,x['source']);dest=session(s,x['recipient']);identity=x.get('creation_receipt',{}).get('identity')
 h.require(identity and identity.get('owned')is True and dest['identity']==identity,'Exact previously registered creation identity required')
 h.require(src['identity']==x['packet']['source_identity']and src['execution']=='paused'and dest['execution']=='paused'and dest['managed']is False,'Original source and unmanaged recipient must remain paused')
 h.require(dest.get('permission_ceiling')==x['packet']['permission_ceiling'],'Original permission ceiling changed')
 h.require(not any(key in x for key in ('receipt','transfer_revision','owner_ack'))and not a['profiles'][x['recipient']].get('ack'),'Only undelivered recipient without ownership/context ACK may recover')
 h.require(not any(r['state']in ('active','uncertain')for r in a['runs'].values())and not any(v['state']in UNRESOLVED for v in a.get('controls',{}).values()),'Active or uncertain operation blocks recovery')
 h.require(not any(v['state']in ('granted','active','uncertain')and v['request']['task']in x['tasks']for v in a.get('diagnostics',{}).values()),'Active diagnostic owner blocks recovery')
 for task in x['tasks']:h.require(s['tasks'][task]['owner']==x['source']and s['tasks'][task]==x['packet']['canonical_context']['tasks'][task],'Canonical owner or original task obligations/claims changed')
 if not x.get('management'):h.require(baseline(x['packet']['baseline'])==x['packet']['baseline'],'Original product baseline changed before recovery transition')
def recovery_settings(x,notification,model,effort):
 h.require(notification.get('threadId')==x['creation_receipt']['identity']['thread'],'Settings notification exact identity mismatch')
 value=notification.get('threadSettings',{});h.require(value.get('model')==model and value.get('effort')==effort,'Exact configured model and reasoning required')
 original=x['creation_receipt']['configured'];observed={key:value.get('sandboxPolicy'if key=='sandbox'else key)for key in ('cwd','sandbox','approvalPolicy','approvalsReviewer')}
 h.require(all(original.get(key)is not None and observed[key]==original[key]for key in observed),'Full original cwd/sandbox/network/tmp/approval settings must remain exact')
 return observed
def typed_task(role,kind):
 h.require(kind in KINDS,'Explicit supported task kind required')
 h.require(not(role=='advisor'and kind=='implementation'),'Advisor independent implementation is forbidden')
 h.require(role!='leader'or kind=='coordination','Leader only coordinates; implementation needs core owner')
def turn_usage(notification):
 value=notification.get('tokenUsage',{}).get('last',{}).get('totalTokens')
 return value if type(value)is int else None
def runtime_unknown():return {'status':'unavailable','source':'official_app_server_schema','at':now(),'capability':'no_authoritative_execution_model_telemetry','reason':'Configuration, provider label, text ACK and absent reroute are not execution attestation'}
def baseline(paths):return external.baseline(paths)
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
 if expected.get('service_tier') not in (None,'normal'):
  tier=x.get('service_tier_observed',{});h.require(profiles.tier_matches(tier,expected['tier_resolution'],expected.get('model'),expected.get('reasoning_effort'))and tier.get('generation')==x.get('configuration_generation')and tier.get('authorized_configured_receipt')is True,'Matching configured service tier required; thread/read cannot verify tier');h.require(time.time()-x.get('tier_observed_wall',0)<=30,'Service-tier observation expired')
 h.require(o.get('status')=='idle','Idle snapshot required; it is not an external lock')
 h.require(time.time()-x.get('observed_monotonic_wall',0)<=30,'Configuration observation expired')

def apply(s,e,state_root=None,state_path=None,source_bytes=None):
 """Called by harness.apply under its single project-record transaction lock."""
 a=s['harness'];sessions=a.setdefault('sessions',{});controls=a.setdefault('controls',{});handoffs=a.setdefault('handoffs',{});op=e['op']
 if op=='control_bind':
  m=e['member'];h.require(m in a['profiles'],'Registered project member required');old=sessions.get(m)
  h.require(not old or old['execution']=='enabled','Paused/disabled source cannot rebind')
  if old and old['identity']!=e['identity']:
   run=e.get('replacement_run');candidate=a['runs'].get(run,{})
   h.require(candidate.get('member')==m and candidate.get('state')=='active'and candidate.get('phase')=='prepared','Only newly prepared managed run may replace terminal identity')
   h.require(not any(key!=run and value['member']==m and value['state']in ('active','uncertain')for key,value in a['runs'].items()),'Prior run unresolved')
   h.require(not any(v.get('member')==m and v['state']in UNRESOLVED for v in controls.values()),'Prior session operation unresolved')
  identity=e['identity'];h.require(all(isinstance(identity.get(k),str)and identity[k]for k in ('host','transport','thread','controller')),'Exact session identity required')
  sessions[m]={'identity':identity,'managed':e.get('managed',False),'configuration_generation':e.get('generation',secrets.token_hex(16)),'execution':'enabled','policy_expected':{'model':a['profiles'][m]['model'],'reasoning_effort':e.get('effort')},'runtime_observed':runtime_unknown()}
  if e.get('service_tier') is not None:sessions[m]['policy_expected'].update(service_tier=e['service_tier'],tier_resolution=e['tier_resolution'])
 elif op=='control_tier_observe':
  x=session(s,e['member']);h.require(e['observation'].get('thread_id')==x['identity']['thread'],'Tier observation identity mismatch');h.require(e.get('generation')==x['configuration_generation'],'Stale configuration generation');observation=dict(e['observation'],generation=e['generation'],authorized_configured_receipt=e.get('response_bound')is True and e['observation'].get('source')in ('thread/start','thread/resume'))
  if observation['authorized_configured_receipt']:x['service_tier_observed']=observation;x['tier_observed_wall']=time.time()
  else:x['settings_notification_observed']=observation;x.pop('service_tier_observed',None);x.pop('tier_observed_wall',None)
 elif op=='control_observe':
  x=session(s,e['member']);x['configured_observed']=e['observation'];x['observed_monotonic_wall']=time.time();x['runtime_observed']=runtime_unknown()
 elif op=='control_intent':
  h.require(e['operation']not in controls,'Operation ID already exists; inspect/reconcile, never resend')
  h.require(not any(v.get('member')==e['member']and v['state']in UNRESOLVED and key!=e['requested'].get('application_for')for key,v in controls.items()),'Prior unresolved operation blocks new IDs; inspect/reconcile first')
  requested=e['requested'];h.require('packet_reserve'not in requested,'Packet reservations retired')
  if requested.get('kind')=='turn' and requested.get('receipt_only'):
   active=[v for v in controls.values()if v['state']in ('request_pending','outcome_unknown','accepted_pending_observation')and v.get('requested',{}).get('receipt_only')];runs=[v for v in a['runs'].values()if v['state']in ('active','uncertain')]
   h.require(len(active)+len(runs)<a['concurrency'],'Receipt turn scheduling conflict')
  target=session(s,e['member'])
  if requested.get('model')is not None:target['configuration_generation']=e['operation'];target.pop('service_tier_observed',None);target.pop('tier_observed_wall',None)
  controls[e['operation']]={'member':e['member'],'state':e['state'],'requested':requested,'at':now(),'intent_time_ns':time.time_ns(),'source':'controller_before_rpc','pending_next_turn':True}
 elif op=='control_result':
  x=controls[e['operation']];x['state']=e['state'];x.update(e.get('evidence',{}));x['updated_at']=now()
  if e['state']=='configuration_pending_turn':
   member=x['member'];sessions[member]['policy_expected']=x['requested'];sessions[member]['configured_observed']=e['evidence']['configured_observed'];sessions[member]['observed_monotonic_wall']=time.time()
   x['configuration_time_ns']=time.time_ns()
 elif op=='control_handoff_prepare':
  hid=e['handoff'];h.require(hid not in handoffs,'Duplicate handoff ID')
  h.require(not any(v['state']!='resumed'and (v['source']==e['source']or v['recipient']==e['recipient']or set(v['tasks']).intersection(e['tasks']))for v in handoffs.values()),'Prior overlapping handoff unresolved; no new-ID retry')
  if e.get('expected_revision')is not None:h.require(a['revision']==e['expected_revision'],'Stale handoff project revision')
  provenance=None
  if e.get('external_source'):
   h.require(e.get('expected_revision')is not None,'External handoff requires revision CAS')
   provenance=external.external_source(e['external_source'],e['checkpoint'],a['revision'],e['packet']['permission_ceiling'])
   existing=sessions.get(e['source']);h.require(not existing or existing['identity']==provenance['identity'],'Existing source identity conflicts with external evidence')
   if not existing:sessions[e['source']]={'identity':provenance['identity'],'managed':False,'execution':'enabled','runtime_observed':runtime_unknown(),'policy_expected':{}}
  x=session(s,e['source']);h.require(x['execution']=='enabled','Source paused or already transferred')
  h.require(not any(v['state']in ('active','uncertain')for v in a['runs'].values()),'Drain all source commands and resolve uncertainty first')
  h.require(not any(v['state']in UNRESOLVED for v in controls.values()),'Pending controls block handoff')
  h.require(e['recipient']not in s['members'],'Recipient must be a new project member')
  role=e['role'];h.require(role in h.MODELS,'Unknown recipient role');model=h.MODELS[role]or e.get('selected_model');h.require(bool(model),'Null-model role requires explicit selected model')
  h.require(e.get('selected_model')in (None,model),'Selected model conflicts with exact role policy')
  for task in e['tasks']:
   t=s['tasks'][task];h.require(t['owner']==e['source'],'Source task ownership changed');typed_task(role,t.get('kind','implementation'))
  h.require(e.get('explicit_request')is True and e.get('drained')is True,'Explicit transition request and drained source checkpoint required')
  proof,stop=external.proof(e['checkpoint']);identity=x['identity']
  if not provenance:h.require(stop.get('source')==identity['thread']and stop.get('controller')==identity['controller']and stop.get('commands_drained')is True,'Stop ACK must identify actual source/controller and drained commands')
  h.require(stop.get('execution_stopped')is True or (identity.get('owned')and stop.get('exclusive_dispatch')is True),'External source requires explicit owner stop attestation; no OS lock inferred')
  paths=[p for task in e['tasks']for p in s['tasks'][task]['paths']]
  management_dir=str(Path(state_path).parent)if state_path is not None and str(Path(state_path).parent)in paths else None
  files=external.baseline(paths,management_dir=management_dir)
  packet=copy.deepcopy(e['packet']);h.require(all(k in packet for k in ('goal','decisions','constraints','remaining_work','permission_ceiling')),'Minimal handoff packet incomplete')
  external.ceiling(packet['permission_ceiling'],paths,str(state_root)if state_root else e.get('state_path'))
  packet['canonical_context']={'goal':a['goal'],'decisions':copy.deepcopy(a['decisions']),'constraints':copy.deepcopy(a['constraints']),'tasks':{key:copy.deepcopy(s['tasks'][key])for key in e['tasks']},'history_sha256':h.digest(s['history']),'history_reference':e.get('state_path'),'scope':'Retained canonical history and artifacts; no authority grant'}
  packet.update({'tasks':e['tasks'],'baseline':files,'source_identity':x['identity'],'source_checkpoint':proof,'project_revision':a['revision']})
  handoffs[hid]={'state':'prepared','source':e['source'],'recipient':e['recipient'],'role':role,'selected_model':model,'tasks':e['tasks'],'packet':packet,'packet_hash':h.digest(packet),'nonce':e['nonce'],'checkpoint':proof,'at':now()}
  import management_handoff as management
  record=management.prepare(paths,files,state_path)
  if record:handoffs[hid]['management']=record
  if provenance:handoffs[hid].update(source_provenance=provenance,prepared_time_ns=time.time_ns())
  x['execution']='paused'
 elif op=='control_handoff_intent':
  x=handoffs[e['handoff']];phase=e['phase'];expected={'creation_pending':'prepared','delivery_pending':'recipient_created'}
  h.require(x['state']==expected.get(phase),'Invalid or unresolved handoff operation; no automatic retry');x['state']=phase;x['intent_at']=now()
 elif op=='control_reconcile_creation':
  x=handoffs[e['handoff']]
  h.require(x['state']=='outcome_unknown'and x.get('failure',{}).get('phase')=='creation_pending'and x.get('creation_receipt',{}).get('identity')==e['identity'],'Only exact known creation identity may reconcile; no duplicate creation')
  x['state']='creation_pending';x.setdefault('reconciliation_attempts',[]).append({'identity':e['identity'],'at':now(),'scope':'Resume exact returned official identity; no new thread'})
 elif op=='control_creation_receipt':
  x=handoffs[e['handoff']];h.require(x['state']=='creation_pending'and 'creation_receipt'not in x,'Creation receipt already recorded or not pending')
  x['creation_receipt']={'identity':e['identity'],'configured':e['configured'],'at':now(),'scope':'Official returned identity/settings only; no recipient authority'}
 elif op=='control_paused_recovery_intent':
  state_cas(s,e,source_bytes);x=handoffs[e['handoff']];predelivery(s,x)
  h.require(x['state']=='outcome_unknown'and x.get('failure',{}).get('phase')=='recipient_created','Only retained recipient_created uncertainty may use paused recovery')
  h.require(e['identity']==x['creation_receipt']['identity']and e['model']==x['selected_model'],'Recovery identity/model substitution refused')
  h.require(not any(v['state']in ('request_pending','outcome_unknown')for v in x.get('recipient_recoveries',{}).values()),'Prior recovery unresolved; never resend or use a new operation ID')
  x.setdefault('recipient_recoveries',{})[e['request_id']]={'state':'request_pending','request_event':copy.deepcopy(e),'event_digest':h.digest(e),'at':now()}
 elif op=='control_paused_recovery_result':
  state_cas(s,e,source_bytes);x=handoffs[e['handoff']];predelivery(s,x);record=x['recipient_recoveries'][e['request_id']];request=record['request_event']
  h.require(record['state']=='request_pending','Recovery result already resolved')
  h.require(e['status']in ('verified','outcome_unknown','rejected'),'Unsupported recovery outcome')
  if e['status']=='verified':
   recovery_settings(x,e['notification'],request['model'],request['effort']);o=e['observation'];h.require(o.get('thread')==request['identity']['thread']and matches(o,request['model'],request['effort'])and o.get('status')=='idle','Fresh matching same-ID live idle metadata required')
   dest=session(s,x['recipient']);dest['policy_expected'].update(model=request['model'],reasoning_effort=request['effort']);dest['configuration_generation']=e['request_id'];dest['configured_observed']=o;dest['observed_monotonic_wall']=time.time();dest.pop('service_tier_observed',None);dest.pop('tier_observed_wall',None);dest['runtime_observed']=runtime_unknown();x['state']='recipient_created'
  record.update(state=e['status'],result=copy.deepcopy(e),result_event_digest=h.digest(e),completed_at=now())
 elif op=='control_packet_refresh':
  state_cas(s,e,source_bytes);x=handoffs[e['handoff']];predelivery(s,x)
  h.require(x['state']=='recipient_created'and e['identity']==x['creation_receipt']['identity'],'Exact paused predelivery recipient required')
  h.require(not any(v['state']in ('request_pending','outcome_unknown')for v in x.get('recipient_recoveries',{}).values()),'Resolve recipient settings uncertainty before packet refresh')
  h.require(x['packet_hash']==e['expected_packet_hash']and x['packet']['project_revision']!=a['revision'],'Exact stale packet CAS required')
  h.require(a['policy_hash']==h.digest(h.effective_contract()),'Adopt the current contract before packet refresh')
  original=x['packet']['canonical_context'];h.require(all(a[key]==original[key]for key in ('goal','decisions','constraints')),'Packet refresh is limited to unchanged task context under contract adoption')
  # Fresh evidence stays outside inventoried claims; no management-tree reseeding.
  for raw in (e['checkpoint'],e['external_observation']):
   p=external.canonical(raw,allow_evidence=True);h.require(not any(p==Path(root)or Path(root)in p.parents for root in x['packet']['baseline']),'Capture refresh evidence outside retained claim baselines')
  floor=x.get('prepared_time_ns',0)
  for item in s['history']:
   if item['event']['op']in ('policy_refresh','contract_migrate','change','claim_expand'):floor=max(floor,int(datetime.datetime.fromisoformat(item['at']).timestamp()*1e9))
  external.proof(e['checkpoint'],after_ns=floor);external.external_observation(e['external_observation'],session(s,x['source'])['identity'],after_ns=floor)
  source_identity=session(s,x['source'])['identity']
  if x.get('source_provenance'):provenance=external.external_source({'identity':source_identity,'observation':e['external_observation']},e['checkpoint'],a['revision'],x['packet']['permission_ceiling'])
  else:
   proof,stop=external.proof(e['checkpoint'],after_ns=floor);observation_proof,source_observation=external.external_observation(e['external_observation'],source_identity,after_ns=floor)
   h.require(source_identity.get('owned')is True and stop.get('source')==source_identity['thread']and stop.get('controller')==source_identity['controller']and stop.get('commands_drained')is True and stop.get('execution_stopped')is True,'Actual owned-source stopped/drained identity required')
   h.require(stop.get('project_revision')==a['revision']and stop.get('permission_ceiling')==x['packet']['permission_ceiling']and stop.get('observation_sha256')==observation_proof['sha256']and stop.get('actual_stop_turn')==source_observation['turn'],'Fresh owned-source stop must bind current revision, ceiling and supported stopped turn')
   quote=stop.get('actual_owner_text');h.require(isinstance(quote,str)and bool(quote.strip())and quote in source_observation.get('final_text',''),'Actual source-owner stop text from supported observation required')
   provenance={'scope':'operator_attestation_with_supported_tool_evidence_owned_source','identity':source_identity,'observation':observation_proof,'stopped_turn':source_observation['turn'],'owner_ack_quote':quote,'checkpoint':proof}
  observed=e['observation'];expected=session(s,x['recipient'])['policy_expected'];h.require(observed.get('thread')==e['identity']['thread']and matches(observed,expected['model'],expected['reasoning_effort'])and observed['status']=='idle','Fresh matching recipient metadata required')
  version=x.get('packet_version',1);archive={key:copy.deepcopy(x[key])for key in ('packet','packet_hash','nonce','checkpoint','source_provenance','packet_refresh_source','failure')if key in x};archive['packet_version']=version;x.setdefault('packet_versions',[]).append(archive)
  packet=copy.deepcopy(x['packet']);packet.update(project_revision=a['revision'],source_checkpoint=provenance['checkpoint'],packet_version=version+1,prior_packet_hash=x['packet_hash'],policy_hash=a['policy_hash']);packet['canonical_context'].update(history_sha256=h.digest(s['history']))
  x.update(packet=packet,packet_hash=h.digest(packet),nonce=e['nonce'],checkpoint=provenance['checkpoint'],packet_version=version+1,prepared_time_ns=time.time_ns())
  x['source_provenance'if x.get('source_provenance')else 'packet_refresh_source']=provenance
  transition={'packet_version':version+1,'packet_hash':x['packet_hash'],'nonce':x['nonce'],'project_revision':a['revision'],'source_owner':x['source'],'recipient_identity':e['identity']}
  x.setdefault('packet_refreshes',{})[e['request_id']]={'event_digest':h.digest(e),'request_event':copy.deepcopy(e),'transition':transition,'at':now()}
 elif op=='control_recipient':
  x=handoffs[e['handoff']];h.require(x['state']=='creation_pending','Recipient creation not pending');m=x['recipient'];h.require(e['model']==x['selected_model'],'Recipient model substitution')
  s['members'][m]={'role':x['role'],'identity_claim':x['checkpoint'],'runtime_id_claim':e['identity']['thread']}
  a['profiles'][m]={'role':x['role'],'epoch':0,'model':e['model'],'last_revision':0}
  h.require(e['identity'].get('thread')!=session(s,x['source'])['identity']['thread'],'Recipient must be a new session')
  sessions[m]={'identity':e['identity'],'permission_ceiling':x['packet']['permission_ceiling'],'managed':False,'configuration_generation':secrets.token_hex(16),'execution':'paused','policy_expected':{'model':e['model'],'reasoning_effort':e['effort']},'runtime_observed':runtime_unknown()}
  if e.get('service_tier')is not None:sessions[m]['policy_expected'].update(service_tier=e['service_tier'],tier_resolution=e['tier_resolution']);sessions[m].update(service_tier_observed=dict(e['tier_observation'],generation=sessions[m]['configuration_generation'],authorized_configured_receipt=True),tier_observed_wall=time.time())
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
  h.require(external.fresh(x['checkpoint']),'Stale source stop ACK')
  provenance=x.get('source_provenance')or x.get('packet_refresh_source')
  if provenance:
   proof,value=external.external_observation(e.get('external_observation')or '',provenance['identity'],provenance['stopped_turn'],x['prepared_time_ns'])
   h.require(external.fresh(provenance['observation']),'Original supported source evidence changed');h.require(provenance['owner_ack_quote']in value.get('final_text',''),'Source owner stop ACK no longer observed');x['transfer_source_observation']=proof
  h.require(e['source_status']=='idle'and e['recipient_status']=='idle','Both sides must be quiescent')
  if not x.get('management'):h.require(baseline(x['packet']['baseline'])==x['packet']['baseline'],'Uncommitted baseline changed')
  for task in x['tasks']:
   h.require(s['tasks'][task]['owner']==x['source'],'Canonical owner changed')
   h.require(s['tasks'][task]==x['packet']['canonical_context']['tasks'][task],'Task obligations/reviews changed since preparation')
  h.require(not any(r['state']in ('active','uncertain')for r in a['runs'].values()),'Unresolved source execution')
  h.require(not any(v['state']in UNRESOLVED for v in controls.values()),'Pending session operation blocks transfer')
  for task in x['tasks']:
   s['tasks'][task]['owner']=x['recipient'];a.get('work_authorizations',{}).pop(task,None)
  session(s,x['source'])['execution']='disabled';session(s,x['recipient'])['execution']='paused';a['revision']+=1
  if e.get('recipient_observation'):session(s,x['recipient'])['configured_observed']=e['recipient_observation'];session(s,x['recipient'])['observed_monotonic_wall']=time.time()
  x.update({'state':'transferred','transfer_revision':a['revision'],'transferred_at':now(),'transfer_time_ns':time.time_ns(),'transfer_nonce':secrets.token_hex(16)})
  for profile in a['profiles'].values():profile.pop('ack',None)
 elif op=='control_owner_ack':
  x=handoffs[e['handoff']];h.require(x['state']=='transferred'and e['revision']==x['transfer_revision']==a['revision'],'ACK must bind exact transfer revision')
  proof,value=external.proof(e['evidence'],after_ns=x['transfer_time_ns']);expected={'handoff':e['handoff'],'recipient':x['recipient'],'transfer_revision':x['transfer_revision'],'transfer_nonce':x['transfer_nonce']}
  h.require(value==expected,'Owner ACK must be created after commit and contain exact transfer receipt')
  x['owner_ack']=proof;x['owner_ack_source']='operator_attestation_of_committed_transfer_revision';x['state']='acknowledged'
 elif op=='control_resume':
  x=handoffs[e['handoff']];h.require(x['state']=='acknowledged','Actual owner transfer ACK required');h.require(x['transfer_revision']==a['revision'],'Project revision changed after transfer; keep recipient paused');h.require(external.fresh(x['owner_ack']),'Owner ACK changed')
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
 def bind(self,member,thread,owned=False,effort=None,managed=False,replacement_run=None,service_tier=None,tier_resolution=None):
  return self.event('control_bind',member=member,identity=dict(self.identity,thread=thread,owned=owned),effort=effort,managed=managed,replacement_run=replacement_run,service_tier=service_tier,tier_resolution=tier_resolution,generation=secrets.token_hex(16))
 def observe_settings(self,member,notification):
  identity=self.require_control(member);value=profiles.settings(notification,identity['thread']);self.event('control_tier_observe',member=member,observation=value,generation=session(self.state(),member)['configuration_generation'],response_bound=False);return value
 def refresh_owned_configuration(self,member):
  identity=self.require_control(member);h.require(identity.get('owned'),'Configuration refresh requires exclusively owned session');before=self.inspect(member);h.require(before['status']=='idle'and before['scope']=='live','Owned idle boundary required')
  generation=session(self.state(),member)['configuration_generation'];response=self.rpc.request('thread/resume',{'threadId':identity['thread'],'excludeTurns':True});value=profiles.configured(response,'thread/resume');h.require(value['thread_id']==identity['thread'],'Configuration refresh identity mismatch');self.event('control_tier_observe',member=member,observation=value,generation=generation,response_bound=True);return value
 def require_control(self,member,checkpoint=None):
  x=session(self.state(),member);identity=x['identity']
  if any(identity[k]!=self.identity[k]for k in self.identity):raise ControlError('ownership_conflict','Host/transport/controller mismatch')
  if not identity.get('owned')and not checkpoint:raise ControlError('manual_required','External dispatcher requires actual owner quiescent checkpoint; idle is not a lock')
  if checkpoint:external.inventory(str(checkpoint),allow_evidence=True,read_file=True)
  return identity
 def inspect(self,member,record=True):
  x=session(self.state(),member);identity=x['identity']
  if any(identity[k]!=self.identity[k]for k in self.identity):raise ControlError('unsupported_platform','Session host/transport/controller differs; no fallback')
  o=configuration(self.rpc.request('thread/read',{'threadId':identity['thread'],'includeTurns':False}));h.require(o['thread']==identity['thread'],'Server returned different thread identity');
  if record:self.event('control_observe',member=member,observation=o)
  return o
 def catalog(self,on_event=None):
  models=[];cursor=None;seen=set()
  while True:
   params={'limit':100,'includeHidden':True,'cursor':cursor};page=self.rpc.request('model/list',params,**({'on_event':on_event}if on_event is not None else {}));models.extend(page['data']);cursor=page.get('nextCursor')
   if not cursor:return models
   h.require(cursor not in seen,'Catalog pagination cycle');seen.add(cursor)
 def change(self,member,operation,model,effort,checkpoint=None,service_tier=None):
  identity=self.require_control(member,checkpoint);profile=self.state()['harness']['profiles'][member]
  h.require(session(self.state(),member)['execution']=='enabled','Paused/disabled source cannot request model change')
  h.require(model==(h.MODELS[profile['role']]or profile['model']),'Requested model violates role policy; no silent substitution')
  if service_tier is None:service_tier=session(self.state(),member)['policy_expected'].get('service_tier')or profiles.role_request(h.effective_contract()['policy'],profile['role']).get('service_tier')
  catalog=self.catalog();validate_choice(catalog,model,effort);resolution=profiles.resolve_service_tier(catalog,model,service_tier);before=self.inspect(member);requested={'model':model,'reasoning_effort':effort,'source':'explicit_request','at':now()}
  if service_tier is not None:requested.update(service_tier=service_tier,tier_resolution=resolution)
  state='pending_turn_application'if before['status']=='idle'and before['scope']=='live'else 'queued'
  self.event('control_intent',member=member,operation=operation,state=state,requested=requested)
  self.event('control_result',operation=operation,state=state,evidence={'accepted':None,'configured_observed':self.inspect(member),'runtime_observed':runtime_unknown(),'pending_next_turn':True,'reason':'Explicit apply-change sends official turn/start model+effort at idle boundary; resume is not used as a loaded-session setter'})
  return self.state()['harness']['controls'][operation]
 def apply_change(self,member,operation,checkpoint=None):
  x=self.state()['harness']['controls'][operation];h.require(x['member']==member and x['state']in ('pending_turn_application','queued'),'Change is not pending or has uncertain outcome')
  h.require(session(self.state(),member)['execution']=='enabled','Paused/disabled source cannot apply configuration')
  self.require_control(member,checkpoint);catalog=self.catalog();validate_choice(catalog,x['requested']['model'],x['requested']['reasoning_effort'])
  if x['requested'].get('service_tier')is not None:
   current=profiles.resolve_service_tier(catalog,x['requested']['model'],x['requested']['service_tier']);h.require(current['wire_id']==x['requested']['tier_resolution']['wire_id'],'Catalogue tier mapping changed; no stale wire dispatch')
  return self.turn(member,'Do not use tools, delegate, edit files or perform implementation. Return exactly HARNESS_CONFIGURATION_CHECK.',configuration_operation=operation,checkpoint=checkpoint)
 def verify_after_turn(self,member,operation,turn):
  state=self.state();x=state['harness']['controls'][operation];h.require(x['state']=='configuration_pending_turn','Configuration change not ready for next-turn verification')
  h.require(any(v.get('member')==member and v.get('turn')==turn and v.get('state')=='completed'and v['intent_time_ns']>x['configuration_time_ns']for v in state['harness']['controls'].values()),'Observed completed controlled turn after configuration required')
  after=self.inspect(member)
  h.require(matches(after,x['requested']['model'],x['requested']['reasoning_effort']),'Configuration mismatch after turn')
  if x['requested'].get('service_tier') not in (None,'normal'):
   tier=self.refresh_owned_configuration(member);h.require(profiles.tier_matches(tier,x['requested']['tier_resolution'],x['requested']['model'],x['requested']['reasoning_effort']),'Configured service tier unavailable/mismatched after next turn')
  proof={'model_reasoning':'configured_observed','service_tier':'unavailable','provider_execution':'unavailable'}
  if x['requested'].get('service_tier')not in (None,'normal'):proof.update(service_tier='configured_observed',persistent_service_tier='configured_observed')
  if x['requested'].get('service_tier')=='normal':
   accepted=next(v.get('accepted',{})for v in state['harness']['controls'].values()if v.get('member')==member and v.get('turn')==turn and v.get('state')=='completed');h.require(accepted.get('tier_parameters')=={'serviceTierForTurn':'default'},'Later turn requires explicit Standard request acknowledgement');proof.update(service_tier='accepted_per_turn_only',persistent_service_tier='unavailable')
  self.event('control_result',operation=operation,state='configuration_verified_after_turn',evidence={'configured_observed':after,'turn':turn,'pending_next_turn':False,'runtime_observed':runtime_unknown(),'verification_scope':proof});return dict(after,verification_scope=proof)
 def prepare_handoff(self,hid,source,recipient,role,tasks,packet,checkpoint,explicit_request=False,selected_model=None,external_source=None,expected_revision=None):
  if external_source is None:
   self.require_control(source,checkpoint)
   snapshot=self.inspect(source);h.require(snapshot['scope']=='live'and snapshot['status']=='idle','Source must be loaded and quiescent at owner checkpoint')
  s=self.event('control_handoff_prepare',handoff=hid,source=source,recipient=recipient,role=role,selected_model=selected_model,tasks=tasks,packet=packet,checkpoint=checkpoint,explicit_request=explicit_request,drained=True,nonce=secrets.token_hex(16),external_source=external_source,expected_revision=expected_revision,state_path=str(external.canonical(str(self.path),allow_evidence=True)));return s['harness']['handoffs'][hid]['packet']
 def create_recipient(self,hid,effort,cwd):
  x=self.state()['harness']['handoffs'][hid];model=x['selected_model'];catalog=self.catalog();requested=profiles.role_request(h.effective_contract()['policy'],x['role']);entry=next((m for m in catalog if m.get('model')==model),{});effort=effort or requested.get('reasoning_effort',entry.get('defaultReasoningEffort'));requested.update(model=model,reasoning_effort=effort);params,resolution=profiles.start_parameters(catalog,requested)
  profiles.require_tier_contract(self.rpc,resolution)
  permission=x['packet']['permission_ceiling'];creation=external.creation(permission,str(cwd));params=creation_parameters(params,creation)
  self.event('control_handoff_intent',handoff=hid,phase='creation_pending')
  try:
   r=self.rpc.request('thread/start',params)
   tid=r['thread']['id']
   self.event('control_creation_receipt',handoff=hid,identity=dict(self.identity,thread=tid,owned=True),configured={k:r.get(k)for k in ('model','reasoningEffort','sandbox','cwd','approvalPolicy','approvalsReviewer')})
   external.verify_creation(r,permission,creation['cwd'])
   self.event('control_recipient',handoff=hid,identity=dict(self.identity,thread=tid,owned=True),model=r.get('model'),effort=r.get('reasoningEffort'),service_tier=requested.get('service_tier'),tier_resolution=resolution,tier_observation=profiles.configured(r,'thread/start'))
   if requested.get('service_tier')not in (None,'normal'):h.require(profiles.tier_matches(profiles.configured(r,'thread/start'),resolution),'Recipient configured service tier unavailable/substituted')
   o=self.inspect(x['recipient']);h.require(matches(o,model,effort),'Recipient configuration unavailable/mismatched');return tid
  except Exception as exc:
   self.event('control_handoff_failure',handoff=hid,reason=str(exc),unknown=not hasattr(exc,'code'));raise
 def reconcile_recipient(self,hid,effort,cwd):
  x=self.state()['harness']['handoffs'][hid];identity=x.get('creation_receipt',{}).get('identity',{})
  h.require(identity.get('owned')is True and all(identity.get(k)==v for k,v in self.identity.items()),'Only this explicit official controller may reconcile known owned identity')
  model=x['selected_model'];catalog=self.catalog();validate_choice(catalog,model,effort);permission=x['packet']['permission_ceiling'];creation=external.creation(permission,str(cwd));requested=profiles.role_request(h.effective_contract()['policy'],x['role']);requested.update(model=model,reasoning_effort=effort);_,resolution=profiles.start_parameters(catalog,requested);profiles.require_tier_contract(self.rpc,resolution)
  self.event('control_reconcile_creation',handoff=hid,identity=identity)
  try:
   response=self.rpc.request('thread/resume',{'threadId':identity['thread'],'excludeTurns':True})
   h.require(response.get('thread',{}).get('id')==identity['thread']and response.get('model')==model and response.get('reasoningEffort')==effort,'Exact created identity/configuration required for reconciliation')
   external.verify_creation(response,permission,creation['cwd'])
   self.event('control_recipient',handoff=hid,identity=identity,model=model,effort=effort,service_tier=requested.get('service_tier'),tier_resolution=resolution,tier_observation=profiles.configured(response,'thread/resume'))
   o=self.inspect(x['recipient']);h.require(matches(o,model,effort)and o['status']=='idle','Reconciled recipient must be live and idle');return identity['thread']
  except Exception as exc:
   self.event('control_handoff_failure',handoff=hid,reason=str(exc),unknown=True);raise
 def recovery_snapshot(self,hid,expected_revision,expected_state_sha256):
  raw=self.path.read_bytes();state=json.loads(raw);state_cas(state,{'expected_revision':expected_revision,'expected_state_sha256':expected_state_sha256},raw)
  import management_handoff as management
  management.before(state,[],self.path,raw);x=state['harness']['handoffs'][hid];predelivery(state,x)
  h.require(all(x['creation_receipt']['identity'].get(k)==v for k,v in self.identity.items()),'Recovery host/transport/controller mismatch')
  if x.get('management'):management.products(x)
  else:h.require(baseline(x['packet']['baseline'])==x['packet']['baseline'],'Original claim baseline changed')
  return state,x
 def recover_paused_recipient(self,hid,request_id,effort,cwd,expected_revision,expected_state_sha256,timeout=20):
  signature={'handoff':hid,'request_id':request_id,'effort':effort,'cwd':str(cwd),'expected_revision':expected_revision,'expected_state_sha256':expected_state_sha256}
  prior=self.state()['harness']['handoffs'][hid].get('recipient_recoveries',{}).get(request_id)
  if prior:
   h.require(all(prior['request_event'].get(k)==v for k,v in signature.items()),'Conflicting recovery operation ID; inspect committed receipt');return copy.deepcopy(prior)
  state,x=self.recovery_snapshot(hid,expected_revision,expected_state_sha256);h.require(x['state']=='outcome_unknown'and x.get('failure',{}).get('phase')=='recipient_created','Only same paused recipient_created failure is recoverable')
  h.require(not any(v['state']in ('request_pending','outcome_unknown')for v in x.get('recipient_recoveries',{}).values()),'Prior recovery unresolved; do not resend')
  notifications=[]
  def observe(event):
   method=event.get('method');p=event.get('params',{})
   if method in ('turn/started','turn/completed','item/started','item/completed','model/rerouted'):raise ControlError('unexpected_activity','Unexpected backend execution during settings recovery')
   if method=='thread/settings/updated'and p.get('threadId')==x['creation_receipt']['identity']['thread']:notifications.append(p)
  model=x['selected_model'];catalog=self.catalog(on_event=observe);validate_choice(catalog,model,effort);external.verify_creation(x['creation_receipt']['configured'],x['packet']['permission_ceiling'],str(cwd))
  before=configuration(self.rpc.request('thread/read',{'threadId':x['creation_receipt']['identity']['thread'],'includeTurns':False},on_event=observe));h.require(before['thread']==x['creation_receipt']['identity']['thread']and before['scope']=='live'and before['status']=='idle','Same recipient must already be loaded and idle; no automatic resume or new creation')
  # Drain already buffered notifications before the new request. This does not
  # authorize another producer; the original owner still holds the idle boundary.
  while True:
   event=self.rpc.next(0)
   if event is None:break
   self.rpc.handle_request(event)
   observe(event)
  committed=self.event('control_paused_recovery_intent',**signature,identity=x['creation_receipt']['identity'],model=model)
  import management_handoff as management
  pending_hash=hashlib.sha256(management.encoded(committed)).hexdigest();notifications=[]
  try:
   h.require(not self.path.is_symlink()and not Path(str(self.path)+'.lock').is_symlink(),'State/lock symlink refused')
   with open(str(self.path)+'.lock','a')as lock:
    fcntl.flock(lock,fcntl.LOCK_EX);raw=self.path.read_bytes();current=json.loads(raw);state_cas(current,{'expected_revision':expected_revision,'expected_state_sha256':pending_hash},raw);predelivery(current,current['harness']['handoffs'][hid]);management.before(current,[],self.path,raw)
    self.rpc.request('thread/settings/update',{'threadId':x['creation_receipt']['identity']['thread'],'model':model,'effort':effort},on_event=observe,timeout=timeout)
   end=time.monotonic()+timeout
   while not notifications and time.monotonic()<end:
    event=self.rpc.next(.5)
    if event is not None:self.rpc.handle_request(event);observe(event)
   h.require(bool(notifications),'Queued settings response is not applied verification; same-ID notification required')
   recovery_settings(x,notifications[-1],model,effort)
   response=self.rpc.request('thread/read',{'threadId':x['creation_receipt']['identity']['thread'],'includeTurns':False},on_event=observe);after=configuration(response);h.require(after['thread']==x['creation_receipt']['identity']['thread']and matches(after,model,effort)and after['status']=='idle','Same-ID configured model/effort must be live and idle')
   while True:
    event=self.rpc.next(0)
    if event is None:break
    self.rpc.handle_request(event);observe(event)
   notification=notifications[-1];recovery_settings(x,notification,model,effort)
   committed=self.event('control_paused_recovery_result',handoff=hid,request_id=request_id,expected_revision=expected_revision,expected_state_sha256=pending_hash,status='verified',notification=notification,observation=after,verification_scope='Configured settings only; no execution, binding, ownership or ACK authority')
  except Exception as error:
   if hashlib.sha256(self.path.read_bytes()).hexdigest()==pending_hash:self.event('control_paused_recovery_result',handoff=hid,request_id=request_id,expected_revision=expected_revision,expected_state_sha256=pending_hash,status='rejected'if hasattr(error,'code')else 'outcome_unknown',error=str(error),automatic_retry=False)
   raise
  return copy.deepcopy(committed['harness']['handoffs'][hid]['recipient_recoveries'][request_id])
 def refresh_packet(self,hid,request_id,expected_packet_hash,checkpoint,external_observation,expected_revision,expected_state_sha256):
  signature={'handoff':hid,'request_id':request_id,'expected_packet_hash':expected_packet_hash,'checkpoint':str(checkpoint),'external_observation':str(external_observation),'expected_revision':expected_revision,'expected_state_sha256':expected_state_sha256}
  prior=self.state()['harness']['handoffs'][hid].get('packet_refreshes',{}).get(request_id)
  if prior:
   h.require(all(prior['request_event'].get(k)==v for k,v in signature.items()),'Conflicting packet refresh operation ID');return copy.deepcopy(prior['transition'])
  state,x=self.recovery_snapshot(hid,expected_revision,expected_state_sha256);observation=self.inspect(x['recipient'],record=False)
  committed=self.event('control_packet_refresh',**signature,identity=x['creation_receipt']['identity'],observation=observation,nonce=secrets.token_hex(16))
  return copy.deepcopy(committed['harness']['handoffs'][hid]['packet_refreshes'][request_id]['transition'])
 def turn(self,member,prompt,timeout=120,packet_handoff=None,task=None,configuration_operation=None,checkpoint=None):
  identity=self.require_control(member,checkpoint);before=self.inspect(member);receipt_only=bool(packet_handoff or configuration_operation)
  if packet_handoff:
   x=self.state()['harness']['handoffs'][packet_handoff];h.require(member==x['recipient'],'Packet recipient identity mismatch');expected=session(self.state(),member)['policy_expected'];h.require(matches(before,expected['model'],expected['reasoning_effort'])and before['status']=='idle','Packet target not ready')
   self.event('control_handoff_intent',handoff=packet_handoff,phase='delivery_pending')
  elif configuration_operation:
   change=self.state()['harness']['controls'][configuration_operation];h.require(change['member']==member and change['state']in ('pending_turn_application','queued')and before['status']=='idle'and before['scope']=='live','Configuration application requires owned idle boundary')
   catalog=self.catalog();validate_choice(catalog,change['requested']['model'],change['requested']['reasoning_effort'])
   if change['requested'].get('service_tier')is not None:
    resolved=profiles.resolve_service_tier(catalog,change['requested']['model'],change['requested']['service_tier']);h.require(resolved['wire_id']==change['requested']['tier_resolution']['wire_id'],'Current catalogue no longer supports requested tier mapping')
  else:
   state=self.state();h.require(task in state['tasks'],'Explicit owned task required');gate(state,member,state['tasks'][task].get('kind','implementation'),before)
  expected=change['requested']if configuration_operation else session(self.state(),member)['policy_expected']
  if expected.get('service_tier')=='normal':
   catalog=self.catalog();validate_choice(catalog,expected['model'],expected['reasoning_effort']);resolution=profiles.resolve_service_tier(catalog,expected['model'],'normal');profiles.require_tier_contract(self.rpc,resolution)
  operation='turn-'+secrets.token_hex(16);completed=False
  # Normal is explicit for each new idle turn; configured tier may remain unknown.
  try:
   with open(str(self.path)+'.lock','a')as lock:
    h.require(not self.path.is_symlink()and not Path(str(self.path)+'.lock').is_symlink(),'State/lock symlink refused')
    fcntl.flock(lock,fcntl.LOCK_EX);raw=self.path.read_bytes();state=json.loads(raw);events=[]
    h.require(state['harness']['policy_hash']==h.digest(h.effective_contract()),'Effective policy changed before turn dispatch')
    if not receipt_only:
     gate(state,member,state['tasks'][task].get('kind','implementation'),before)
     events.append({'op':'begin','member':member,'task':task,'run':operation})
    elif packet_handoff:h.require(state['harness']['handoffs'][packet_handoff]['state']=='delivery_pending','Packet delivery state changed')
    else:
     h.require(session(state,member)['execution']=='enabled','Paused/disabled source cannot dispatch configuration turn')
     h.require(state['harness']['controls'][configuration_operation]['state']in ('pending_turn_application','queued'),'Configuration intent changed')
    events.append({'op':'control_intent','member':member,'operation':operation,'state':'request_pending','requested':{'kind':'turn','packet_handoff':packet_handoff,'application_for':configuration_operation,'receipt_only':receipt_only,'source':'turn/start','at':now()}});state=h.apply_locked(self.path,state,events,raw)
    params={'threadId':identity['thread'],'input':[{'type':'text','text':prompt,'text_elements':[]}]}
    if configuration_operation:
     params.update(model=change['requested']['model'],effort=change['requested']['reasoning_effort'])
     if change['requested'].get('service_tier')is not None:params.update(profiles.tier_parameters(change['requested']['tier_resolution'],'turn/start'))
    if expected.get('service_tier')=='normal':params.update(profiles.tier_parameters(resolution,'turn/start'))
    permission=session(state,member).get('permission_ceiling')
    if permission and permission['sandbox']=='workspace-write':
     external.ceiling(permission,list(state['harness']['handoffs'][packet_handoff]['packet']['baseline'])if packet_handoff else [p for key in state['tasks']if state['tasks'][key]['owner']==member for p in state['tasks'][key]['paths']],str(external.canonical(str(self.path),allow_evidence=True)))
     params.update(sandboxPolicy=external.sandbox({'sandbox':'read-only'}if receipt_only else permission),approvalPolicy='on-request',approvalsReviewer='auto_review')
    r=self.rpc.request('turn/start',params)
   turn=r['turn']['id'];text=[];end=time.monotonic()+timeout;usage=None
   accepted={'turn':turn,'tier_parameters':{k:params[k]for k in ('serviceTierForTurn','serviceTier')if k in params},'selected_client_contract':getattr(self.rpc,'tier_contract',None),'scope':'request_acknowledgement_only','source':'turn/start_parameter_acknowledgement','at':now()}
   self.event('control_result',operation=operation,state='accepted_pending_observation',evidence={'accepted':accepted})
   if configuration_operation:self.event('control_result',operation=configuration_operation,state='accepted_pending_observation',evidence={'accepted':dict(accepted,model=params['model'],reasoning_effort=params['effort'],requested_service_tier=change['requested'].get('service_tier'))})
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
    if method=='thread/settings/updated':self.observe_settings(member,p)
    if method=='model/rerouted':raise ControlError('substitution','Server reported model reroute: '+json.dumps(p))
    if method=='thread/tokenUsage/updated':
     usage=turn_usage(p)
    if method=='thread/compacted'or (method=='item/completed'and p.get('item',{}).get('type')=='contextCompaction'):
     h.transaction(self.path,{'op':'boundary','member':member,'reason':'compaction'});raise h.Invalid('Compaction requires fresh acknowledgement')
    if method=='item/completed'and p.get('item',{}).get('type')=='agentMessage':text.append(p['item'].get('text',''))
    if method=='turn/completed'and p.get('turn',{}).get('id')==turn:
     h.require(p['turn'].get('status')=='completed','Turn failed: '+json.dumps(p['turn'].get('error')))
     completed=True
     # Persist execution evidence before fallible post-turn configuration reads.
     if not receipt_only:
      event={'op':'finish','run':operation,'outcome':'completed','evidence':'Observed turn/completed '+turn}
      if type(usage)is int:event['usage']=usage
      h.transaction(self.path,event)
     after=self.inspect(member);body='\n'.join(text)
     if packet_handoff:self.event('control_packet_received',handoff=packet_handoff,turn=turn,text=body,observation=after)
     elif configuration_operation:
      h.require(matches(after,params['model'],params['effort']),'Configuration application substituted or unavailable')
      if change['requested'].get('service_tier')not in (None,'normal'):
       tier=self.refresh_owned_configuration(member);h.require(profiles.tier_matches(tier,change['requested']['tier_resolution'],params['model'],params['effort']),'Configuration service tier unavailable/substituted')
      proof={'model_reasoning':'configured_observed','service_tier':'accepted_per_turn_only'if change['requested'].get('service_tier')=='normal'else 'configured_observed'if change['requested'].get('service_tier')else 'unavailable','persistent_service_tier':'unavailable'if change['requested'].get('service_tier')=='normal'else 'see_configured_receipt','provider_execution':'unavailable'}
      self.event('control_result',operation=configuration_operation,state='configuration_pending_turn',evidence={'configured_observed':after,'runtime_observed':runtime_unknown(),'pending_next_turn':True,'verification_scope':proof})
     self.event('control_result',operation=operation,state='completed',evidence={'turn':turn,'usage':usage if type(usage)is int else None,'configured_observed':after,'runtime_observed':runtime_unknown()})
     return {'turn':turn,'text':body,'before':before,'after':after,'accepted':accepted,'runtime_observed':runtime_unknown()}
   raise TimeoutError('Turn completion unknown; do not resend')
  except Exception as exc:
   if 'turn'in locals()and not completed:
    try:self.rpc.request('turn/interrupt',{'threadId':identity['thread'],'turnId':turn},timeout=3)
    except Exception:pass
   # An RPC error after turn/start acceptance is not a dispatch rejection.
   rejected='turn'not in locals()and hasattr(exc,'code')
   if operation in self.state()['harness'].get('controls',{}):self.event('control_result',operation=operation,state='completed'if completed else 'rejected'if rejected else 'outcome_unknown',evidence={'error':str(exc),'automatic_retry':False})
   if packet_handoff:self.event('control_handoff_failure',handoff=packet_handoff,reason=str(exc),unknown=True)
   if configuration_operation:self.event('control_result',operation=configuration_operation,state='outcome_unknown',evidence={'error':str(exc),'automatic_retry':False})
   elif self.state()['harness']['runs'].get(operation,{}).get('state')=='active':
    h.transaction(self.path,{'op':'finish','run':operation,'outcome':'completed'if completed else 'not_executed'if rejected else 'uncertain','evidence':str(exc)})
   raise
 def deliver_packet(self,hid):
  x=self.state()['harness']['handoffs'][hid]
  prompt='Read this project handoff packet. Do no implementation, tools, delegation or file edits. Confirm receipt by returning exactly the ACK line below. It proves packet receipt only.\n'+json.dumps(x['packet'],ensure_ascii=False)+'\n'+ack_text(x)
  return self.turn(x['recipient'],prompt,packet_handoff=hid)
 def transfer(self,hid,external_observation=None):
  x=self.state()['harness']['handoffs'][hid]
  src={'status':'idle'}if x.get('source_provenance')else self.inspect(x['source'],record=False);dest=self.inspect(x['recipient'],record=False)
  h.require(matches(dest,session(self.state(),x['recipient'])['policy_expected']['model'],session(self.state(),x['recipient'])['policy_expected']['reasoning_effort']),'Recipient drift blocks transfer')
  s=self.event('control_transfer',handoff=hid,source_status=src['status'],recipient_status=dest['status'],external_observation=external_observation,recipient_observation=dest);return s['harness']['handoffs'][hid]['transfer_revision']
 def resume(self,hid):
  x=self.state()['harness']['handoffs'][hid];self.require_control(x['recipient']);o=self.inspect(x['recipient']);return self.event('control_resume',handoff=hid,observation=o)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state',type=Path,required=True);p.add_argument('--controller',required=True);p.add_argument('--host',required=True)
 p.add_argument('--transport',choices=('native-proxy','owned-stdio'),required=True);p.add_argument('--socket',help='Explicit authorized official proxy endpoint; never discovered from private files')
 sub=p.add_subparsers(dest='operation',required=True)
 for name in ('inspect','change'):
  q=sub.add_parser(name);q.add_argument('--member',required=True)
  if name=='change':q.add_argument('--operation-id',required=True);q.add_argument('--model',required=True);q.add_argument('--effort',required=True);q.add_argument('--owner-checkpoint');q.add_argument('--service-tier',choices=('normal','fast'))
 q=sub.add_parser('bind');q.add_argument('--member',required=True);q.add_argument('--thread',required=True)
 q=sub.add_parser('prepare');q.add_argument('--handoff',required=True);q.add_argument('--source',required=True);q.add_argument('--recipient',required=True);q.add_argument('--role',choices=tuple(h.MODELS),required=True);q.add_argument('--model',help='Required explicit choice for null-model leader; never inferred');q.add_argument('--tasks',nargs='+',required=True);q.add_argument('--packet',type=Path,required=True);q.add_argument('--owner-stop-ack',required=True);q.add_argument('--explicit-user-request',action='store_true');q.add_argument('--external-source',type=Path,help='Exact external identity and supported observation JSON; explicit opt-in');q.add_argument('--expected-revision',type=int)
 for name in ('create','reconcile-create'):
  q=sub.add_parser(name);q.add_argument('--handoff',required=True);q.add_argument('--effort',required=name=='reconcile-create');q.add_argument('--cwd',type=Path,required=True)
 q=sub.add_parser('recover-paused');q.add_argument('--handoff',required=True);q.add_argument('--request-id',required=True);q.add_argument('--effort',required=True);q.add_argument('--cwd',type=Path,required=True);q.add_argument('--expected-revision',type=int,required=True);q.add_argument('--expected-state-sha256',required=True)
 q=sub.add_parser('refresh-packet');q.add_argument('--handoff',required=True);q.add_argument('--request-id',required=True);q.add_argument('--expected-packet-hash',required=True);q.add_argument('--owner-stop-ack',required=True);q.add_argument('--external-observation',required=True);q.add_argument('--expected-revision',type=int,required=True);q.add_argument('--expected-state-sha256',required=True)
 for name in ('deliver','transfer','resume'):
  q=sub.add_parser(name);q.add_argument('--handoff',required=True)
  if name=='transfer':q.add_argument('--external-observation',type=Path)
 q=sub.add_parser('owner-ack');q.add_argument('--handoff',required=True);q.add_argument('--revision',type=int,required=True);q.add_argument('--evidence',required=True)
 q=sub.add_parser('verify');q.add_argument('--member',required=True);q.add_argument('--operation-id',required=True);q.add_argument('--turn',required=True)
 q=sub.add_parser('apply-change');q.add_argument('--member',required=True);q.add_argument('--operation-id',required=True);q.add_argument('--owner-checkpoint')
 q=sub.add_parser('turn');q.add_argument('--member',required=True);q.add_argument('--task',required=True);q.add_argument('--prompt',type=Path,required=True)
 a=p.parse_args();from managed_run import RPC
 if a.transport=='native-proxy'and not a.socket:raise ControlError('unsupported_transport','Explicit authorized native proxy socket required; no automatic standalone fallback')
 command=['codex','app-server','proxy','--sock',a.socket]if a.transport=='native-proxy'else ['codex','app-server','--stdio'];rpc=RPC(command,tier_contract=profiles.CURRENT_TIER_CONTRACT)
 try:
  rpc.request('initialize',{'clientInfo':{'name':'team-session-control','version':'0.2.0'}});rpc.send({'method':'initialized'});ctl=Controller(a.state,rpc,a.controller,a.host,'official-'+a.transport+(':'+a.socket if a.transport=='native-proxy'else ''))
  if a.operation=='inspect':result=ctl.inspect(a.member)
  elif a.operation=='change':result=ctl.change(a.member,a.operation_id,a.model,a.effort,a.owner_checkpoint,a.service_tier)
  elif a.operation=='bind':result=ctl.bind(a.member,a.thread)
  elif a.operation=='prepare':result=ctl.prepare_handoff(a.handoff,a.source,a.recipient,a.role,a.tasks,json.loads(a.packet.read_text()),a.owner_stop_ack,a.explicit_user_request,a.model,external_source=json.loads(a.external_source.read_text())if a.external_source else None,expected_revision=a.expected_revision)
  elif a.operation=='create':result=ctl.create_recipient(a.handoff,a.effort,a.cwd)
  elif a.operation=='recover-paused':result=ctl.recover_paused_recipient(a.handoff,a.request_id,a.effort,a.cwd,a.expected_revision,a.expected_state_sha256)
  elif a.operation=='refresh-packet':result=ctl.refresh_packet(a.handoff,a.request_id,a.expected_packet_hash,a.owner_stop_ack,a.external_observation,a.expected_revision,a.expected_state_sha256)
  elif a.operation=='reconcile-create':result=ctl.reconcile_recipient(a.handoff,a.effort,a.cwd)
  elif a.operation=='deliver':result=ctl.deliver_packet(a.handoff)
  elif a.operation=='transfer':result={'transfer_revision':ctl.transfer(a.handoff,external_observation=str(a.external_observation)if a.external_observation else None)}
  elif a.operation=='owner-ack':result=ctl.event('control_owner_ack',handoff=a.handoff,revision=a.revision,evidence=a.evidence)
  elif a.operation=='resume':result=ctl.resume(a.handoff)
  elif a.operation=='verify':result=ctl.verify_after_turn(a.member,a.operation_id,a.turn)
  elif a.operation=='apply-change':result=ctl.apply_change(a.member,a.operation_id,a.owner_checkpoint)
  else:result=ctl.turn(a.member,a.prompt.read_text(),task=a.task)
  print(json.dumps(result))
 finally:rpc.close()
if __name__=='__main__':
 try:main()
 except Exception as exc:print(json.dumps({'error':str(exc),'kind':getattr(exc,'kind','unknown'),'automatic_retry':False}));sys.exit(2)
