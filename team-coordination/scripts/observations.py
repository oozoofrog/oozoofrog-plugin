"""Method-bound continuations; recorded review is not native permission enforcement."""
import base64,copy,hashlib,json
from pathlib import Path

def capture(proof):
 import harness as h
 h.require(h.ledger.fresh(proof),'Missing or changed observation evidence');data=Path(proof['path']).read_bytes();h.require(hashlib.sha256(data).hexdigest()==proof['sha256'],'Evidence changed during capture');return data

def method(value):
 import harness as h
 h.require(set(value)=={'collector','spec','input','schema'}and isinstance(value['schema'],str)and bool(value['schema'].strip()),'Exact method/schema required')
 capture(value['collector']);capture(value['spec']);i=value['input'];h.require(i.get('kind')in ('file','source_defined'),'Explicit file/source-defined input provenance required');capture(i['evidence'])
 return {'collector':value['collector']['sha256'],'spec':value['spec']['sha256'],'input':{'kind':i['kind'],'sha256':i['evidence']['sha256']},'schema':value['schema']}

def fingerprint(task,failure,value):
 import harness as h
 return h.digest({'task':task,'failure':failure,'method':method(value)})

RECOVERY_FLAGS=('environment_initialization_verified','known_not_executed','no_explicit_denial','existing_scope_verified','exact_execution_verified','permission_submission_only','diagnostic_only')

def recovery_verify(s,record,current=False):
 """Verify copied bindings; freshness gates submission, never truthful termination."""
 import harness as h,migration
 e=record['request'];a=s['harness'];prior=a['diagnostics'][e['previous_request_id']];run=a['runs'][prior['run']]
 h.require(record['recovery_of']==e['previous_request_id'],'Recovery predecessor identity changed')
 h.require(h.digest({'diagnostic':prior,'run':run})==record['predecessor_sha256'],'Recovery predecessor changed')
 review=record['review'];event=dict(e,approvals=review['proof']['path']);h.require(h.digest(event)==record['event_digest'],'Recovery request binding changed')
 values=json.loads(base64.b64decode(review['bytes_base64'],validate=True));h.require(hashlib.sha256(base64.b64decode(review['bytes_base64'],validate=True)).hexdigest()==review['proof']['sha256'],'Recovery retained review changed')
 for role in ('leader','reviewer'):
  x=values[role];h.require(x['request_sha256']==h.digest(e)and all(x.get(k)is True for k in RECOVERY_FLAGS+('approved','safe_boundary','all_current_obligations_retained')),'Recovery retained approval binding changed')
 blobs={}
 for key in ('terminal_evidence','root_cause_evidence','submission_authorization'):
  data=base64.b64decode(record[key+'_bytes_base64'],validate=True);h.require(hashlib.sha256(data).hexdigest()==e[key]['sha256'],'Recovery copied evidence changed');blobs[key]=json.loads(data)
  if current:h.require(capture(e[key])==data,'Recovery evidence changed')
 authority=blobs['submission_authorization'];human=base64.b64decode(record['authority_source_bytes_base64'],validate=True)
 h.require(hashlib.sha256(human).hexdigest()==authority['source']['sha256']and authority['quote']in human.decode('utf-8'),'Recovery authority source changed')
 h.require(authority.get('kind')=='permission_recovery_submission'and authority.get('project')==a['goal']and authority.get('task')==e['task']and authority.get('member')==e['member']and authority.get('paths')==e['modification_paths'],'Recovery applicable authority changed')
 terminal=blobs['terminal_evidence'];cause=blobs['root_cause_evidence']
 h.require(prior['state']=='closed'and run['state']=='not_executed'and prior['result']['outcome']=='not_executed'and run['diagnostic_request_id']==e['previous_request_id'],'Known non-executed closed predecessor required')
 h.require(e['terminal_evidence']['path']==str(Path(run['evidence']).resolve())and terminal.get('run')==prior['run']and terminal.get('diagnostic_request_id')==e['previous_request_id'],'Original terminal identity required')
 h.require(terminal.get('command_terminal')is True and all(k in terminal and terminal[k]is None for k in ('binary_path','collector_result_path')),'Terminal must establish no collector binary/output')
 h.require(all(terminal.get(k)is not True for k in ('user_denied','auto_review_denied','access_denied')),'Explicit original denial cannot be recovered')
 h.require(e['execution']=={k:terminal[k]for k in ('argv','environment','cwd')},'Exact frozen argv/environment/cwd required')
 execution=e['execution'];h.require(isinstance(execution['argv'],list)and execution['argv']and all(isinstance(v,str)and v for v in execution['argv'])and isinstance(execution['environment'],dict)and all(isinstance(k,str)and isinstance(v,str)for k,v in execution['environment'].items())and Path(execution['cwd']).is_absolute(),'Explicit execution descriptor required')
 h.require(e['method']==prior['method']and record['method']==prior['method']and record['method_fingerprint']==prior['method_fingerprint'],'Exact unchanged retained method required')
 h.require(terminal.get('collector_sha256')==e['method']['collector']['sha256']and terminal.get('binding_sha256')==e['method']['input']['evidence']['sha256'],'Original terminal collector/input binding required')
 h.require(cause.get('category')=='environment_initialization_failure'and cause.get('previous_run')==prior['run']and all(cause.get('terminal_evidence',{}).get(k)==e['terminal_evidence'][k]for k in ('path','sha256'))and cause.get('collector_executed')is False and all(cause.get(k)is False for k in ('user_denied','auto_review_denied','access_denied'))and isinstance(cause.get('reason'),str)and bool(cause['reason'].strip()),'Known environment initialization failure without explicit denial required')
 proof=cause['environment_evidence'];log=base64.b64decode(record['environment_bytes_base64'],validate=True);h.require(proof['path']==terminal.get('log')and proof['sha256']==terminal.get('log_sha256')==hashlib.sha256(log).hexdigest(),'Original initialization evidence binding required')
 if current:
  t=s['tasks'][e['task']];reviews=t['reviews'];h.require(reviews and reviews[-1]['verdict']=='fail'and h.ledger.fresh(reviews[-1]['evidence'])and e['failed_review_digest']==h.digest({'task':e['task'],'index':len(reviews)-1,'review':reviews[-1]})and e['provenance_sha256']==h.diagnostic_provenance(s,e['task']),'Recovery failed-review evidence/provenance changed')
  h.require(capture(proof)==log and capture(authority['source'])==human,'Recovery source evidence changed');method(e['method'])
  h.require(fingerprint(e['task'],e['failed_review_digest'],e['method'])==record['method_fingerprint'],'Recovery method fingerprint changed')
  actual=migration.approvals(s,event);h.require(actual['bytes_base64']==review['bytes_base64']and all(actual['proof'][k]==review['proof'][k]for k in ('path','sha256')),'Recovery approval evidence changed')
  reviewer=values['reviewer']['member'];h.require(reviewer!=e['member']and s['members'][reviewer]['runtime_id_claim']!=s['members'][e['member']]['runtime_id_claim'],'Execution owner cannot review recovery')
 return e['execution']

def permission_recovery(s,e,root,raw):
 """Append submission authority; native tool authorization is still required."""
 import harness as h,checkpoints,migration
 a=s['harness'];identifier=e.get('request_id');h.require(isinstance(identifier,str)and bool(identifier.strip())and len(identifier)<=128,'Stable recovery ID required')
 h.require(root is not None and Path(e['project_root']).is_absolute()and Path(e['project_root']).resolve()==Path(root).resolve(),'Exact canonical state directory required')
 h.require(raw is not None and h.digest(json.loads(raw))==h.digest(s)and e['source_sha256']==h.digest(s)and e['source_raw_sha256']==hashlib.sha256(raw).hexdigest(),'Fresh parsed/raw recovery CAS required')
 h.require(e['project']==a['goal']and e['policy_hash']==a['policy_hash']==h.digest(h.effective_contract()),'Current exact recovery project/contract required');checkpoints.quiescent(s)
 if a.get('checkpoint'):checkpoints.active(s)
 h.require(not any(k in e for k in ('reserve','reserve_estimate','max_reserve','permission_evidence')),'Recovery authorizes normal tool submission, not a permission grant')
 prior=a.get('diagnostics',{}).get(e['previous_request_id']);h.require(prior is not None and prior['state']=='closed'and prior.get('method')is not None,'Closed method-bound predecessor required')
 h.require(not any(r.get('recovery_of')==e['previous_request_id']for r in a['diagnostics'].values()),'Predecessor already has a recovery successor')
 task=e['task'];t=s['tasks'][task];h.require(prior['request']['task']==task and prior['request']['member']==e['member']==t['owner']and t['state']=='ready_for_review'and not t.get('block'),'Same unblocked original owner/task required')
 h.require(not any(r['request']['task']==task and r['state']in ('granted','active','uncertain')for r in a['diagnostics'].values()),'Pending diagnostic authority already exists')
 h.require(e['modification_paths']==prior['request']['modification_paths']and t==prior['original_task'],'Recovery cannot alter original scope or obligations')
 h.require(h.ledger.fresh(s['members'][e['member']]['identity_claim']),'Fresh execution owner required')
 reviews=t['reviews'];h.require(reviews and reviews[-1]['verdict']=='fail'and h.ledger.fresh(reviews[-1]['evidence']),'Latest actual fresh failed review required')
 failure=h.digest({'task':task,'index':len(reviews)-1,'review':reviews[-1]});h.require(e['failed_review_digest']==failure and e['provenance_sha256']==h.diagnostic_provenance(s,task),'Original failure/provenance changed')
 h.require(isinstance(e.get('evidence_goal'),str)and bool(e['evidence_goal'].strip()),'Explicit submission goal required')
 review=migration.approvals(s,e);proposal={k:v for k,v in e.items()if k!='approvals'}
 record={'event_digest':h.digest(e),'request':proposal,'original_task':copy.deepcopy(t),'original_task_sha256':h.digest(t),'state':'granted','kind':'permission_recovery','recovery_of':e['previous_request_id'],'predecessor_sha256':h.digest({'diagnostic':prior,'run':a['runs'][prior['run']]}),'method':copy.deepcopy(e['method']),'method_fingerprint':prior['method_fingerprint'],'review':review,'authority_limit':'Submission for normal command-specific exec_command require_escalated review only; no native permission, correction or acceptance grant'}
 for key in ('terminal_evidence','root_cause_evidence','submission_authorization'):record[key+'_bytes_base64']=base64.b64encode(capture(e[key])).decode()
 authority=json.loads(base64.b64decode(record['submission_authorization_bytes_base64']));quote=authority.get('quote');h.require(isinstance(quote,str)and bool(quote.strip()),'Exact human submission authority quote required')
 record['authority_source_bytes_base64']=base64.b64encode(capture(authority['source'])).decode();cause=json.loads(base64.b64decode(record['root_cause_evidence_bytes_base64']));record['environment_bytes_base64']=base64.b64encode(capture(cause['environment_evidence'])).decode()
 recovery_verify(s,record,current=True)
 a['revision']+=1
 for profile in a['profiles'].values():profile.pop('ack',None)
 record['original_transition']={'task':task,'owner':t['owner'],'state':'granted','revision':a['revision'],'task_state':t['state']};a['diagnostics'][identifier]=record
 a['changes'].append({'revision':a['revision'],'diagnostic_permission_recovery':identifier,'previous':e['previous_request_id'],'task':task,'execution':copy.deepcopy(e['execution']),'authority_limit':record['authority_limit']})

def renew_authority(s,e):
 """Renew pending authority, never replay a consumed execution attempt."""
 import harness as h,migration
 a=s['harness'];task=e['task'];t=s['tasks'][task];prior=a.get('reworks',{}).get(e['previous_request_id']);h.require(prior is not None and prior.get('kind')=='correction'and a.get('work_authorizations',{}).get(task)==e['previous_request_id'],'Exact current pending correction authority required')
 h.require(not any(r.get('work_request_id')==e['previous_request_id']for r in a['runs'].values())and t['state']=='assigned','Already executed work cannot be renewed into another attempt')
 h.require(e['member']==t['owner']==prior['request']['member']and e['modification_paths']==prior['request']['modification_paths'],'Renewal cannot transfer actor or expand scope')
 h.require(e['method']==e['prior_method']==prior['method']and e['failed_review_digest']==prior['failed_review_digest']and e['provenance_sha256']==h.diagnostic_provenance(s,task),'Renewal retains exact pending method/failure/provenance')
 method(e['method']);h.require(e['permission_evidence']['sha256']!=prior['request']['permission_evidence']['sha256'],'No changed permission evidence to renew')
 permission_data=capture(e['permission_evidence']);permission=json.loads(permission_data);h.require(permission.get('allowed')is True and all(p in permission.get('paths',[])for p in e['modification_paths'])and not t.get('block'),'Actual current permission remains required')
 cause_data=capture(e['root_cause_evidence']);cause=json.loads(cause_data);h.require(cause.get('category')=='permission_renewal'and cause.get('pending_request')==e['previous_request_id']and bool(cause.get('reason')),'Pending authority renewal reason required')
 authority_data=capture(e['correction_authorization']);authority=json.loads(authority_data);human=capture(authority['source']);quote=authority.get('quote')
 h.require(authority.get('kind')=='correction'and authority.get('project')==a['goal']and authority.get('task')==task and authority.get('member')==t['owner']and authority.get('paths')==e['modification_paths']and isinstance(quote,str)and bool(quote.strip())and quote in human.decode('utf-8'),'Exact applicable correction authority/source required')
 review=migration.approvals(s,e);values=json.loads(base64.b64decode(review['bytes_base64']))
 h.require(all(x.get('authority_renewal_only')is True and x.get('correction_authority_verified')is True and x.get('permissions_current')is True for x in values.values()),'Independent pending-authority renewal judgment required')
 h.require(values['reviewer']['member']!=t['owner']and s['members'][values['reviewer']['member']]['runtime_id_claim']!=s['members'][t['owner']]['runtime_id_claim'],'Execution owner cannot approve renewal')
 a['revision']+=1
 for p in a['profiles'].values():p.pop('ack',None)
 identifier=e['request_id'];record=copy.deepcopy(prior);record.update(event_digest=h.digest(e),request={k:v for k,v in e.items()if k!='approvals'},source_sha256=e['source_sha256'],authority_renewal_of=e['previous_request_id'],review=review,authority_bytes_base64=base64.b64encode(authority_data).decode(),authority_source_bytes_base64=base64.b64encode(human).decode(),root_cause_bytes_base64=base64.b64encode(cause_data).decode(),permission_bytes_base64=base64.b64encode(permission_data).decode(),original_transition={'task':task,'owner':t['owner'],'state':'assigned','revision':a['revision']})
 a['reworks'][identifier]=record;a['work_authorizations'][task]=identifier;a['changes'].append({'revision':a['revision'],'authority_renewal':identifier,'previous':e['previous_request_id'],'task':task})

def followup(s,e,root,correction=False):
 import harness as h,checkpoints,migration
 a=s['harness'];identifier=e.get('request_id');h.require(isinstance(identifier,str)and bool(identifier.strip()),'Stable follow-up ID required')
 h.require(root is not None and Path(e['project_root']).is_absolute()and Path(e['project_root']).resolve()==Path(root).resolve(),'Exact canonical state directory required')
 h.require(e['source_sha256']==h.digest(s)and e['project']==a['goal']and e['policy_hash']==a['policy_hash']==h.digest(h.effective_contract()),'Fresh exact project/contract/CAS required')
 h.require(not any(k in e for k in ('reserve_estimate','max_reserve','reserve')),'Diagnostic reservations retired');checkpoints.quiescent(s)
 if correction and e.get('renew_authorization')is True:return renew_authority(s,e)
 previous=a.get('diagnostics',{}).get(e['previous_request_id'])
 if previous is None and correction:
  previous=copy.deepcopy(a.get('reworks',{}).get(e['previous_request_id']))
  if previous is not None:
   matches=[(key,r)for key,r in a['runs'].items()if r.get('work_request_id')==e['previous_request_id']]
   h.require(bool(matches),'Actual predecessor correction run required');previous['run']=matches[-1][0];previous['state']='closed'if matches[-1][1]['state']in ('completed','failed','not_executed')else'uncertain';previous.setdefault('request',{'task':previous['original_transition']['task'],'member':previous['original_transition']['owner'],'modification_paths':s['tasks'][e['task']]['paths']})
 h.require(previous is not None and previous['state']=='closed','Observed terminal predecessor required')
 prior_run=a['runs'].get(previous.get('run'));h.require(prior_run is not None and prior_run['state']in ('completed','failed','not_executed'),'Actual prior run must be terminal')
 task=e['task'];t=s['tasks'][task];owner=e['member'];h.require(previous['request']['task']==task and (correction or previous['request']['member']==owner)and owner==t['owner']and t['state']in (('ready_for_review','assigned')if correction else('ready_for_review',)),'Same original owner/task required')
 h.require(not t.get('block'),'Unresolved permission/action block remains');reviews=t['reviews'];h.require(reviews and reviews[-1]['verdict']=='fail'and h.ledger.fresh(reviews[-1]['evidence']),'Latest actual fresh failed product review required')
 failure=h.digest({'task':task,'index':len(reviews)-1,'review':reviews[-1]});h.require(e['failed_review_digest']==failure and e['provenance_sha256']==h.diagnostic_provenance(s,task),'Original failure/provenance changed')
 paths=e['modification_paths'];allowed=t['paths']if correction else previous['request']['modification_paths'];h.require(isinstance(paths,list)and paths and len(set(paths))==len(paths)and all(Path(p).is_absolute()and h.ledger.canonical(p)==p and any(Path(p).is_relative_to(Path(q))for q in allowed)and any(Path(p).is_relative_to(Path(q))for q in t['paths'])for p in paths),'Changed work must stay inside applicable permission and retained claims')
 authority_data=None;human=None
 if correction:
  h.require(isinstance(e.get('correction_authorization'),dict),'Applicable correction authority required');authority_data=capture(e['correction_authorization']);authority=json.loads(authority_data)
  h.require(authority.get('kind')=='correction'and authority.get('project')==a['goal']and authority.get('task')==task and authority.get('member')==owner and authority.get('paths')==paths,'Actual applicable correction authority required; observation authority cannot promote itself')
  human=capture(authority['source']);quote=authority.get('quote');h.require(isinstance(quote,str)and bool(quote.strip())and quote in human.decode('utf-8'),'Exact retained correction authority source/quote required')
 permission_data=capture(e['permission_evidence']);permission=json.loads(permission_data);h.require(permission.get('allowed')is True and all(p in permission.get('paths',[])for p in paths),'Current actual scope permission required; no implicit resolution of denial')
 cause_data=capture(e['root_cause_evidence']);cause=json.loads(cause_data);h.require(cause.get('previous_run')==previous['run']and cause.get('category')in ('insufficient_observation','computation_failure')and not cause.get('permission_denied')and bool(cause.get('reason')),'Observed root cause required; denied permission is not a retry reason')
 h.require(isinstance(e.get('evidence_goal'),str)and bool(e['evidence_goal'].strip()),'Explicit next observation goal required')
 prior=e['prior_method'];method(prior);new=e['method'];new_parts=method(new);prior_failure=previous.get('failed_review_digest',previous['request'].get('failed_review_digest',failure))
 seeds=a.get('diagnostic_method_seeds',{});seed=None
 if previous.get('method')is not None:h.require(prior==previous['method']and previous['method_fingerprint']==fingerprint(task,prior_failure,prior),'Predecessor method must match its exact retained record')
 elif e['previous_request_id']in seeds:h.require(prior==seeds[e['previous_request_id']]['method'],'Exact retained legacy method seed required')
 else:
  seed=e.get('legacy_seed');h.require(isinstance(seed,dict)and seed.get('run')==previous['run']and seed.get('method')==prior,'Actual legacy run-bound seed required')
  proof=seed['terminal'];h.require(proof['path']==str(Path(prior_run['evidence']).resolve()),'Seed must use actual retained terminal artifact');terminal_data=capture(proof);terminal=json.loads(terminal_data)
  h.require(terminal.get('run')in (None,previous['run'])and not terminal.get('permission_denied'),'Terminal artifact identity/permission mismatch')
  if terminal.get('method')is not None:h.require(terminal['method']==prior,'Prior method differs from actual retained terminal method')
  else:
   definition=terminal.get('commandDefinition');h.require(definition==prior['spec']['path'],'Retained terminal must explicitly link prior command definition');manifest=json.loads(capture(prior['spec']));sources=manifest.get('sources',[])
   h.require(any(x.get('frozen')==prior['collector']['path']and x.get('sha256')==prior['collector']['sha256']for x in sources),'Prior collector not bound to retained executed-source manifest')
   h.require(prior['input']['kind']=='source_defined'and any(x.get('frozen')==prior['input']['evidence']['path']and x.get('sha256')==prior['input']['evidence']['sha256']for x in sources),'Missing frozen source-defined input provenance; owner must supply an existing bound input record')
  seed=copy.deepcopy(seed);seed['terminal_bytes_base64']=base64.b64encode(terminal_data).decode();seed['method_fingerprint']=fingerprint(task,prior_failure,prior)
 prior_parts=method(prior);h.require(any(new_parts[k]!=prior_parts[k]for k in ('collector','spec','schema')),'Material method delta required; a new ID/prose/input alone is insufficient')
 fp=fingerprint(task,failure,new);used={r.get('method_fingerprint')for r in a.get('diagnostics',{}).values()}|{r.get('method_fingerprint')for r in a.get('reworks',{}).values()}|{r.get('method_fingerprint')for r in seeds.values()}
 if seed:used.add(seed['method_fingerprint'])
 h.require(fp not in used,'Repeated observation method fingerprint; no new-ID retry')
 review=migration.approvals(s,e);values=json.loads(base64.b64decode(review['bytes_base64']))
 for role in ('leader','reviewer'):
  x=values[role];h.require(all(x.get(k)is True for k in (('correction_authority_verified',)if correction else('diagnostic_only',))+('material_method_change','same_authorized_scope','permissions_current','prior_method_verified')),'Independent semantic method/scope/permission judgment required')
 reviewer=values['reviewer']['member'];h.require(reviewer!=owner and s['members'][reviewer]['runtime_id_claim']!=s['members'][owner]['runtime_id_claim'],'Execution owner cannot review its method')
 if seed:a.setdefault('diagnostic_method_seeds',{})[e['previous_request_id']]=dict(seed,review=review)
 a['revision']+=1
 for p in a['profiles'].values():p.pop('ack',None)
 proposal={k:v for k,v in e.items()if k!='approvals'}
 if correction:
  t['state']='assigned';transition={'task':task,'owner':owner,'state':'assigned','revision':a['revision']}
  a.setdefault('reworks',{})[identifier]={'event_digest':h.digest(e),'request':proposal,'source_sha256':e['source_sha256'],'failed_review_digest':failure,'original_transition':transition,'kind':'correction','authorized_claims':copy.deepcopy(t['paths']),'method':copy.deepcopy(new),'method_fingerprint':fp,'review':review,'authority_bytes_base64':base64.b64encode(authority_data).decode(),'authority_source_bytes_base64':base64.b64encode(human).decode(),'root_cause_bytes_base64':base64.b64encode(cause_data).decode(),'permission_bytes_base64':base64.b64encode(permission_data).decode()}
  a.setdefault('work_scope_required',{})[task]=True;a.setdefault('work_authorizations',{})[task]=identifier;a['changes'].append({'revision':a['revision'],'method_bound_rework':identifier,'task':task,'method_fingerprint':fp});return
 transition={'task':task,'owner':owner,'state':'granted','revision':a['revision'],'task_state':t['state']}
 a['diagnostics'][identifier]={'event_digest':h.digest(e),'request':proposal,'original_task':copy.deepcopy(t),'original_task_sha256':h.digest(t),'original_transition':transition,'state':'granted','method':copy.deepcopy(new),'method_fingerprint':fp,'review':review,'root_cause_bytes_base64':base64.b64encode(cause_data).decode(),'permission_bytes_base64':base64.b64encode(permission_data).decode(),'authority_limit':'Same-scope observation only; semantic judgment recorded, no correction/acceptance or native permission grant'}
 a['changes'].append({'revision':a['revision'],'diagnostic_followup':identifier,'previous':e['previous_request_id'],'method_fingerprint':fp,'evidence_goal':e['evidence_goal']})
