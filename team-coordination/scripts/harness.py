#!/usr/bin/env python3
"""Managed-run gates layered on the existing team ledger; no OS interception."""
import argparse,base64,copy,fcntl,hashlib,json,math,os,sys,tempfile
from pathlib import Path
import team_ledger as ledger
Invalid,require=ledger.Invalid,ledger.require
POLICY=json.loads((Path(__file__).resolve().parents[1]/'policy.json').read_text())
MODELS={role:item['model'] for role,item in POLICY['roles'].items()}
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
def effective_contract():
 root=Path(__file__).resolve().parents[1]
 return {'policy':json.loads((root/'policy.json').read_text()),'roles':{p.stem:p.read_text()for p in sorted((root/'roles').glob('*.md'))},'schema':json.loads((root/'schema/project-state.schema.json').read_text()),'implementation_sha256':{name:hashlib.sha256((root/'scripts'/name).read_bytes()).hexdigest()for name in ('harness.py','managed_run.py','team_ledger.py','session_control.py','checkpoints.py','profile_defaults.py','external_handoff.py','management_handoff.py','migration.py','observations.py')}}

def work_authorization(s,task):
 a=s['harness'];record=a.get('reworks',{}).get(a.get('work_authorizations',{}).get(task),{})
 if record.get('kind')!='correction':return None
 t=s['tasks'][task];request=record['request'];paths=request['modification_paths']
 if request['member']!=t['owner']or record['original_transition']['owner']!=t['owner']:return None
 if not set(t['paths']).issubset(set(record['authorized_claims'])):return None
 if not all(ledger.canonical(p)==p and any(Path(p).is_relative_to(Path(q))for q in t['paths'])for p in paths):return None
 authority_data=base64.b64decode(record['authority_bytes_base64'],validate=True);authority=json.loads(authority_data);source=base64.b64decode(record['authority_source_bytes_base64'],validate=True);review_data=base64.b64decode(record['review']['bytes_base64'],validate=True)
 require(hashlib.sha256(authority_data).hexdigest()==request['correction_authorization']['sha256']and hashlib.sha256(source).hexdigest()==authority['source']['sha256']and authority['quote']in source.decode('utf-8'),'Retained correction authority changed')
 require(authority['member']==t['owner']and authority['paths']==paths and authority['task']==task and authority['project']==a['goal']and authority['kind']=='correction','Correction authority actor/scope changed')
 require(hashlib.sha256(review_data).hexdigest()==record['review']['proof']['sha256']and all(x['request_sha256']==digest(request)and x.get('correction_authority_verified')is True for x in json.loads(review_data).values()),'Retained correction review binding changed')
 if not ledger.fresh(request['permission_evidence']):return None
 return record

def diagnostic_tasks(s):
 a=s['harness'];result=set()
 for record in a.get('diagnostics',{}).values():
  task=record['request']['task'];authorized=work_authorization(s,task) is not None
  if record['state']in ('granted','active','uncertain')or not authorized:result.add(task)
 return result

def diagnostic_provenance(s,task):
 return digest({'task':s['tasks'][task],'reworks':{k:v for k,v in s['harness'].get('reworks',{}).items()if v['original_transition']['task']==task}})

def diagnostic_invariants(s):
 for record in s['harness'].get('diagnostics',{}).values():
  if record.get('kind')=='permission_recovery':
   import observations
   observations.recovery_verify(s,record)
  if record['state']in ('granted','active','uncertain'):require(s['tasks'][record['request']['task']]==record['original_task'],'Active diagnostic task obligations changed')
  if 'original_task_sha256'in record:require(digest(record['original_task'])==record['original_task_sha256'],'Historical original task snapshot changed')
  require(all(ledger.canonical(path)==path for path in record['request']['modification_paths']+record['original_task']['paths']),'Diagnostic path aliases changed; inspect before continuation')

def diagnostic_grant(s,e,state_root):
 h=s['harness'];identifier=e.get('request_id');require(isinstance(identifier,str)and bool(identifier.strip())and len(identifier)<=128,'Stable diagnostic request ID required')
 require(state_root is not None and Path(e['project_root']).is_absolute()and Path(e['project_root']).resolve()==Path(state_root).resolve(),'Exact canonical state directory required')
 require(e.get('source_sha256')==digest(s)and e.get('project')==h['goal'],'Exact current state and project required')
 require(e.get('policy_hash')==h['policy_hash']==digest(effective_contract()),'Current exact policy contract required')
 import checkpoints
 checkpoints.quiescent(s)
 if h.get('checkpoint'):checkpoints.active(s)
 task=e['task'];t=s['tasks'][task];member=e['member'];require(task not in diagnostic_tasks(s),'Diagnostic cycle already granted for original task; no new-ID retry')
 require(t['owner']==member and t['state']=='ready_for_review','Same owner and original ready_for_review task required')
 require(s['members'][member]['role']not in ('leader','reviewer')and ledger.fresh(s['members'][member]['identity_claim']),'Fresh execution owner required')
 reviews=t['reviews'];require(reviews and reviews[-1]['verdict']=='fail'and ledger.fresh(reviews[-1]['evidence']),'Latest actual fresh failed review required')
 failure=digest({'task':task,'index':len(reviews)-1,'review':reviews[-1]})
 require(e.get('failed_review_digest')==failure and e.get('provenance_sha256')==diagnostic_provenance(s,task),'Exact failed-review and retained rework provenance required')
 require(not any(r['request']['failed_review_digest']==failure for r in h.get('diagnostics',{}).values()),'Failed review already consumed for diagnosis')
 goal=e.get('evidence_goal');require(isinstance(goal,str)and bool(goal.strip()),'Explicit new diagnostic evidence goal required')
 paths=e.get('modification_paths');require(isinstance(paths,list)and paths and all(isinstance(path,str)and Path(path).is_absolute()and ledger.canonical(path)==path for path in paths),'Exact canonical diagnostic modification paths required')
 require(len(set(paths))==len(paths)and all(any(Path(path).is_relative_to(Path(claim))for claim in t['paths'])for path in paths),'Diagnostic paths must remain within retained write claims')
 require('max_reserve'not in e,'Diagnostic reservation field retired')
 requester=e.get('requester');require(requester in s['members']and s['members'][requester]['role']=='leader'and ledger.fresh(s['members'][requester]['identity_claim']),'Fresh registered leader requester required')
 human=e['human_approval'];require(ledger.fresh(human),'Exact human approval bytes required');human_data=Path(human['path']).read_bytes();require(hashlib.sha256(human_data).hexdigest()==human['sha256'],'Human approval changed during capture')
 proof=ledger.evidence(e['approvals']);data=Path(e['approvals']).read_bytes();require(hashlib.sha256(data).hexdigest()==proof['sha256'],'Independent approval changed during capture');approvals=json.loads(data);proposal={k:v for k,v in e.items()if k!='approvals'};members=[]
 for role in ('leader','reviewer'):
  approval=approvals[role];m=approval['member'];require(m in s['members']and s['members'][m]['role']==role and ledger.fresh(s['members'][m]['identity_claim']),'Diagnostic approval role/identity mismatch')
  require(approval.get('request_sha256')==digest(proposal)and all(approval.get(flag)is True for flag in ('approved','safe_boundary','all_current_obligations_retained','human_approval_verified','diagnostic_only')),'Exact diagnostic-only request approval required');members.append(m)
 require(members[0]==requester and members[0]!=members[1]and s['members'][members[0]]['runtime_id_claim']!=s['members'][members[1]]['runtime_id_claim'],'Independent diagnostic review required')
 require(members[1]!=member and s['members'][members[1]]['runtime_id_claim']!=s['members'][member]['runtime_id_claim'],'Diagnostic reviewer cannot share the execution owner runtime')
 h['revision']+=1
 for profile in h['profiles'].values():profile.pop('ack',None)
 transition={'task':task,'owner':member,'state':'granted','revision':h['revision'],'task_state':t['state']}
 h.setdefault('diagnostics',{})[identifier]={'event_digest':digest(e),'request':proposal,'original_task':copy.deepcopy(t),'original_task_sha256':digest(t),'original_transition':transition,'state':'granted','approval_evidence':proof,'approval_bytes_base64':base64.b64encode(data).decode(),'human_approval_bytes_base64':base64.b64encode(human_data).decode(),'authority_limit':'Recorded attestations; one diagnostic run only, no correction or deliverable acceptance; no native permission enforcement'}
 h['changes'].append({'revision':h['revision'],'diagnostic_request':identifier,'task':task,'evidence_goal':goal,'modification_paths':paths})

def diagnostic_result(s,run):
 r=s['harness']['runs'][run];identifier=r.get('diagnostic_request_id')
 if identifier:
  record=s['harness']['diagnostics'][identifier];record['state']='uncertain'if r['state']=='uncertain'else 'closed';record['result']={'run':run,'outcome':r['state'],'evidence':r['evidence'],'task_state':s['tasks'][r['task']]['state']}

def diagnostic_receipt(s,request_id):
 require(request_id in s['harness'].get('diagnostics',{}),'Unknown diagnostic request ID');r=s['harness']['diagnostics'][request_id]
 return {'request_id':request_id,'original_transition':r['original_transition'],'current_observation':{'state':r['state'],'result':r.get('result'),'revision':s['harness']['revision']},'scope':'Historical one-cycle diagnostic receipt; original deliverable remains blocked'}

def initial(goal):
 limits=effective_contract()['policy']['limits'];s=ledger.apply({}, {'op':'init'})
 s['harness']={'schema':2,'revision':1,'goal':goal,'constraints':[],'decisions':[],'changes':[], 'profiles':{},'runs':{},'concurrency':limits['concurrency'],'policy_hash':digest(effective_contract())}
 return s

def usage_summary(s):
 a=s['harness'];rows=[r for r in a['runs'].values()if r['state']in ('completed','failed')]
 for key,r in a.get('controls',{}).items():
  requested=r.get('requested',{})
  if requested.get('kind')=='turn'and r['state']in ('completed','failed')and key not in a['runs']and requested.get('run')not in a['runs']:rows.append(r)
 values=[r.get('reported_usage',r.get('usage'))for r in rows];known=[x for x in values if type(x)is int]
 return {'reported_tokens':sum(known)if known else None,'unknown_runs':len(values)-len(known),'complete':bool(rows)and len(known)==len(rows),'provenance':'recorded provisional provider/client usage reports; billing not measured'}

def active_changes(changes):
 # Only known internal accounting keys; actual instruction/decision text is untouched.
 retired={'budget_request','old_budget','new_budget','max_reserve','reserve_estimate','reserve','charged','human_approval_bytes_base64','approval_bytes_base64'};result=[]
 for change in changes:
  item={k:v for k,v in change.items()if k not in retired and not(k=='reason'and 'budget_request'in change)}
  if set(item)-{'revision'}:result.append(item)
 return result

def packet(s,member):
 import migration
 migration.verify(s)
 h=s['harness'];p=h['profiles'][member];contract=effective_contract()
 require(h['policy_hash']==digest(contract),'Effective policy/role/schema changed; explicit policy_refresh required')
 tasks=[{'id':k,'purpose':v['purpose'],'context':v.get('context',''),'paths':v['paths'],'state':v['state']} for k,v in s['tasks'].items() if v['owner']==member]
 require(h.get('schema')==2,'Explicit contract_migrate required for historical state')
 result={'schema':2,'revision':h['revision'],'epoch':p['epoch'],'policy_hash':h['policy_hash'],'policy_version':contract['policy']['version'],'role_contract':contract['roles'][p['role']],'limits':contract['policy']['limits'],'goal':h['goal'],'constraints':h['constraints'],'decisions':h['decisions'],'role':p['role'],'tasks':tasks,'changes':active_changes([c for c in h['changes'] if c['revision']>p.get('last_revision',0)]),'unresolved_runs':[k for k,v in h['runs'].items() if v['state'] in ('active','uncertain')]}
 result['usage']=usage_summary(s)
 import checkpoints
 working=checkpoints.projection(s)
 if working:
  contexts=working.pop('task_contexts');result.update(working)
  for task in result['tasks']:
   if task['id']in contexts:task['context']=contexts[task['id']]
  result['task_obligations']={k:{field:value for field,value in v.items()if field!='context'}for k,v in s['tasks'].items()if v['state']!='accepted'or v.get('block')}
  result['usage']=usage_summary(s)
 result['task_obligations']={k:{field:value for field,value in v.items()if field!='context'}for k,v in s['tasks'].items()if v['state']!='accepted'or v.get('block')}
 if h.get('diagnostics'):result['diagnostics']={key:{'task':record['request']['task'],'evidence_goal':record['request']['evidence_goal'],'modification_paths':record['request']['modification_paths'],'state':record['state'],'run':record.get('run'),'result':{k:v for k,v in record.get('result',{}).items()if k!='charged'},'method_fingerprint':record.get('method_fingerprint'),'root_cause_evidence':record['request'].get('root_cause_evidence'),'method':record.get('method'),'authority_limit':record['authority_limit']}for key,record in h['diagnostics'].items()}
 for key,record in h.get('diagnostics',{}).items():
  if record.get('kind')=='permission_recovery':
   import observations
   execution=observations.recovery_verify(s,record,current=record['state']=='granted');result['diagnostics'][key].update(recovery_of=record['recovery_of'],execution=execution,tool_authorization='Normal command-specific require_escalated decision still required')
 result['work_authorizations']={task:{'request_id':identifier,'active':work_authorization(s,task)is not None if h.get('reworks',{}).get(identifier,{}).get('kind')=='correction'else True,'kind':h.get('reworks',{}).get(identifier,{}).get('kind','original-scope rework'),'paths':h.get('reworks',{}).get(identifier,{}).get('request',{}).get('modification_paths',s['tasks'][task]['paths']),'method_fingerprint':h.get('reworks',{}).get(identifier,{}).get('method_fingerprint')}for task,identifier in h.get('work_authorizations',{}).items()}
 result['next_action']='Resolve observed uncertainty before new work'if result['unresolved_runs']else 'Read current purpose/criteria and failure evidence; choose a justified next action within existing authority'
 result['failure_alternatives']='For insufficient evidence, change the observation method with retained provenance; for denied access, obtain actual permission; do not replay an unchanged failed attempt'

 return result

def ack_current(s,member):
 p=s['harness']['profiles'][member];a=p.get('ack')
 require(s['harness']['policy_hash']==digest(effective_contract()),'Policy changed; leader must migrate project policy and refresh ACKs')
 require(a is not None and a=={'revision':s['harness']['revision'],'epoch':p['epoch'],'digest':digest(packet(s,member))},'Latest context acknowledgement required')

def claim_expand(s,e,state_root,raw):
 """Append ownership only; correction and execution authority remain separate."""
 h=s['harness'];identifier=e.get('request_id');task=e['task'];t=s['tasks'][task]
 require(isinstance(identifier,str)and bool(identifier.strip())and len(identifier)<=128,'Stable claim expansion request ID required')
 require(state_root is not None and isinstance(e.get('project_root'),str)and e['project_root']==ledger.canonical(e['project_root'])==str(Path(state_root).resolve()),'Exact canonical state directory required')
 require(raw is not None and digest(json.loads(raw))==digest(s)and e.get('source_sha256')==digest(s)and e.get('source_raw_sha256')==hashlib.sha256(raw).hexdigest(),'Fresh parsed/raw claim expansion CAS required')
 require(e.get('project')==h['goal']and e.get('policy_hash')==h['policy_hash']==digest(effective_contract()),'Current exact project/policy contract required')
 require(t['owner']==e['member']and t['state']=='ready_for_review','Claim expansion requires same owner and ready_for_review task')
 require(s['members'][e['member']]['role']not in ('leader','reviewer')and ledger.fresh(s['members'][e['member']]['identity_claim']),'Fresh execution owner required')
 require(isinstance(e.get('reason'),str)and bool(e['reason'].strip()),'Explicit claim expansion reason required')
 import checkpoints
 checkpoints.quiescent(s)
 if h.get('checkpoint'):checkpoints.active(s)
 require(not any(r['request']['task']==task and r['state']in ('granted','active','uncertain')for r in h.get('diagnostics',{}).values()),'Resolve pending diagnostic authority before claim expansion')
 require(all(ledger.canonical(p)==p for v in s['tasks'].values()for p in v['paths']),'Existing claim aliases changed; inspect before expansion')
 paths=e.get('additional_paths');require(isinstance(paths,list)and bool(paths)and all(isinstance(p,str)and Path(p).is_absolute()and ledger.canonical(p)==p for p in paths),'Explicit canonical additional paths required')
 require(len(set(paths))==len(paths),'Duplicate additional paths refused')
 require(any(p not in t['paths']for p in paths),'At least one additional claim required')
 for path in paths:
  for key,other in s['tasks'].items():
   if key!=task:
    require(not any(ledger.overlaps(path,p)for p in other['paths']),'Overlapping ownership')
    require(not set(t['resources']).intersection(other['resources']),'Shared resource already claimed')
 original=copy.deepcopy(t);t['paths']=sorted(set(t['paths']+paths));h['revision']+=1
 h.get('work_authorizations',{}).pop(task,None)
 for profile in h['profiles'].values():profile.pop('ack',None)
 transition={'task':task,'owner':t['owner'],'state':t['state'],'paths':copy.deepcopy(t['paths']),'revision':h['revision']}
 h.setdefault('claim_expansions',{})[identifier]={'event_digest':digest(e),'request':copy.deepcopy(e),'original_task':original,'original_transition':transition,'authority_limit':'Ownership record only; fresh applicable correction authority and packet acknowledgement remain required; no native permission or execution grant'}
 h['changes'].append({'revision':h['revision'],'claim_expansion':identifier,'task':task,'owner':t['owner'],'additional_paths':copy.deepcopy(paths),'reason':e['reason']})

def apply(state,e,state_root=None,source_bytes=None,state_path=None):
 import migration
 migration.verify(state)
 s=copy.deepcopy(state);h=s['harness'];op=e['op']
 if op=='claim_expand'and e.get('request_id')in h.get('claim_expansions',{}):
  require(h['claim_expansions'][e['request_id']]['event_digest']==digest(e),'Conflicting claim expansion request ID; inspect committed receipt');return s
 if op in ('diagnostic_grant','diagnostic_followup','diagnostic_permission_recovery')and e.get('request_id')in h.get('diagnostics',{}):
  require(h['diagnostics'][e['request_id']]['event_digest']==digest(e),'Conflicting diagnostic request ID; inspect committed receipt');return s
 if op=='rework'and e.get('request_id')in h.get('reworks',{}):
  require(h['reworks'][e['request_id']]['event_digest']==digest(e),'Conflicting rework request ID; inspect committed receipt')
  return s  # Readback only: never rewrite later state or repeat the transition.
 if op=='contract_migrate':
  old=h.get('legacy_archives',{}).get(e.get('request_id'))
  if old:require(old['event_digest']==digest(e),'Conflicting contract migration ID');return s
  import migration
  result=migration.apply(s,e,state_root,source_bytes);result['history'].append({'at':ledger.now(),'event':e});return result
 require(h.get('schema')==2,'Historical state requires explicit contract_migrate')
 require(op not in ('budget_change','resource_policy_adopt'),'Budget operations retired; historical evidence cannot be reactivated')
 diagnostic_invariants(s)
 guarded=diagnostic_tasks(s)
 if op in ('claim','release','reassign','handoff','review','accept','rework')and e.get('task')in guarded and not(op=='rework'and 'method'in e)and not(op in ('claim','release','reassign')and not any(r['request']['task']==e['task']and r['state']in ('granted','active','uncertain')for r in h.get('diagnostics',{}).values())):raise Invalid('Diagnostic-only task remains blocked pending separately authorized future transition')
 if op in ('control_handoff_prepare','control_transfer'):
  tasks=e.get('tasks',[])if op=='control_handoff_prepare'else h.get('handoffs',{}).get(e.get('handoff'),{}).get('tasks',[])
  require(not any(r['request']['task']in tasks and r['state']in ('granted','active','uncertain')for r in h.get('diagnostics',{}).values()),'Active/uncertain diagnostic owner cannot transfer')
 if op in ('checkpoint_commit','checkpoint_restore'):
  import checkpoints
  return checkpoints.apply(s,e,state_root)
 if op in ('begin','control_intent')and h.get('checkpoint'):
  import checkpoints
  checkpoints.active(s)
 if op.startswith('control_'):
  import session_control
  s=session_control.apply(s,e,state_root,state_path)
 elif op=='diagnostic_permission_recovery':
  import observations
  observations.permission_recovery(s,e,state_root,source_bytes)
 elif op=='diagnostic_followup':
  import observations
  observations.followup(s,e,state_root)
 elif op=='diagnostic_grant':diagnostic_grant(s,e,state_root)
 elif op=='claim_expand':claim_expand(s,e,state_root,source_bytes)
 elif op=='register':
  m=e['member'];role=e['role'];require(m not in s['members'] and role in MODELS,'Duplicate member or unknown role')
  # Identity is a file-backed claim. Only adapter runtime receipt is observed transport data.
  s['members'][m]={'role':role,'identity_claim':ledger.evidence(e['identity']),'runtime_id_claim':e.get('runtime_id',m)}
  h['profiles'][m]={'role':role,'epoch':0,'model':effective_contract()['policy']['roles'][role]['model'],'last_revision':0}
 elif op=='assign':
  require(e['task'] not in s['tasks'],'Duplicate task')
  require(e['member'] in s['members'] and s['members'][e['member']]['role'] not in ('leader','reviewer'),'Execution owner required')
  import session_control
  kind=e.get('kind','implementation');session_control.typed_task(s['members'][e['member']]['role'],kind)
  s['tasks'][e['task']]={'owner':e['member'],'purpose':e['purpose'],'context':e['context'],'kind':kind,'state':'assigned','paths':[],'resources':[],'reviews':[]}
 elif op=='claim':
  t=s['tasks'][e['task']];require(t['state'] in ('assigned','running'),'Claim in invalid state')
  require(not any(r['task']==e['task']and r['state']in ('active','uncertain')for r in h['runs'].values()),'Unresolved run freezes write claims')
  paths=[ledger.canonical(p) for p in e['paths']];require(paths,'Paths required')
  for k,v in s['tasks'].items():
   if k!=e['task']:require(not any(ledger.overlaps(a,b) for a in paths for b in v['paths']),'Overlapping ownership')
  combined=sorted(set(paths+t['paths']))
  if combined!=t['paths']:h.get('work_authorizations',{}).pop(e['task'],None)
  t['paths']=combined
 elif op=='change':
  h['revision']+=1;h['constraints'].append(e['instruction']);h['decisions']+=e.get('decisions',[])
  h['changes'].append({'revision':h['revision'],'instruction':e['instruction'],'decisions':e.get('decisions',[])})
  # Active operations become stale; transport must interrupt at the next observed event.
  for r in h['runs'].values():
   if r['state']=='active':r['stale']=True
 elif op=='policy_refresh':
  require(bool(e.get('reason')),'Leader migration reason required')
  require(not any(r['state']in ('active','uncertain')for r in h['runs'].values()),'Resolve active/uncertain runs before policy migration')
  contract=effective_contract();limits=contract['policy']['limits'];h['policy_hash']=digest(contract);h['revision']+=1
  h['concurrency']=limits['concurrency']
  for p in h['profiles'].values():p['model']=contract['policy']['roles'][p['role']]['model'];p.pop('ack',None)
  h['changes'].append({'revision':h['revision'],'policy_refresh':e['reason']})
  for r in h['runs'].values():
   if r['state']=='active':r['stale']=True
 elif op=='boundary':
  require(e['reason'] in ('resume','compaction','reconnect','handoff'),'Unknown context boundary')
  p=h['profiles'][e['member']];p['epoch']+=1;p.pop('ack',None)
 elif op=='ack':
  m=e['member'];expected=packet(s,m)
  require(e['revision']==expected['revision'] and e['epoch']==expected['epoch'] and e['digest']==digest(expected),'Stale packet acknowledgement')
  h['profiles'][m]['ack']={k:e[k] for k in ('revision','epoch','digest')}
  # last_revision tracks previous confirmed packet; changing it would change current packet hash.
 elif op=='begin':
  m=e['member'];t=s['tasks'][e['task']];p=h['profiles'][m]
  diagnostic=e.get('diagnostic_request_id');grant=h.get('diagnostics',{}).get(diagnostic)if diagnostic else None
  if diagnostic:
   require(grant is not None and grant['request']['task']==e['task']and grant['request']['member']==m and grant['state']=='granted','Exact unconsumed diagnostic grant required')
   if grant.get('kind')=='permission_recovery':
    import observations
    require(e.get('execution')==observations.recovery_verify(s,grant,current=True),'Exact reviewed recovery execution required')
  else:require(e['task']not in diagnostic_tasks(s),'Diagnostic-only task cannot begin normal work')
  require(t['owner']==m and (t['state']=='ready_for_review'if diagnostic else t['state']in ('assigned','running')),'Wrong task owner/state')
  require(ledger.fresh(s['members'][m]['identity_claim']),'Stale identity claim')
  require(p['role'] not in ('leader','reviewer') and p['model'] is not None,'Requested role model unresolved or nonexecuting role')
  import session_control
  session_control.typed_task(p['role'],t.get('kind','implementation'))
  if m in h.get('sessions',{}):require(h['sessions'][m]['execution']=='enabled','Source/recipient execution paused or disabled')
  ack_current(s,m);require(t['paths'],'Write ownership required')
  if h.get('work_scope_required',{}).get(e['task']):require(work_authorization(s,e['task'])is not None,'Current owner/scope requires explicit fresh work authority')
  require('reserve'not in e,'Reservation field retired')
  require(e['run'] not in h['runs'],'Duplicate run id')
  require(not any(r['state']=='uncertain' for r in h['runs'].values()),'Uncertain run must be reconciled')
  active=[r for r in h['runs'].values() if r['state']=='active']
  packets=[r for r in h.get('controls',{}).values()if r['state']in ('request_pending','outcome_unknown','accepted_pending_observation')and r.get('requested',{}).get('kind')=='turn']
  require(len(active)+len(packets)<h['concurrency'],'Concurrency exhausted')
  require(not any(r['task']==e['task'] for r in active),'Task already executing')
  h['runs'][e['run']]={'task':e['task'],'member':m,'model':p['model'],'revision':h['revision'],'epoch':p['epoch'],'state':'active','stale':False,'phase':'prepared','observed':{},'work_request_id':h.get('work_authorizations',{}).get(e['task'])if not diagnostic else None,'execution_paths':work_authorization(s,e['task'])['request']['modification_paths']if work_authorization(s,e['task'])is not None and not diagnostic else (grant['request']['modification_paths']if diagnostic else t['paths']),'packet':packet(s,m)}
  if diagnostic:h['runs'][e['run']]['diagnostic_request_id']=diagnostic;grant['state']='active';grant['run']=e['run']
  else:t['state']='running'
 elif op=='observe':
  r=h['runs'][e['run']];require(r['state']=='active','Run not active');r['observed'].update(e['receipt']);r['phase']=e['phase']
 elif op=='finish':
  r=h['runs'][e['run']];require(r['state']=='active','Run already terminal');out=e['outcome'];require(out in ('completed','failed','uncertain','not_executed'),'Invalid outcome')
  require(bool(e['evidence']),'Outcome evidence required');r['state']=out;r['evidence']=e['evidence']
  if out!='uncertain':
   used=e.get('usage');require(used is None or type(used)is int and used>=0,'Invalid reported usage');r['reported_usage']=used
  p=h['profiles'][r['member']];p['last_revision']=r['revision'];p.pop('ack',None);diagnostic_result(s,e['run'])
 elif op=='mark_uncertain':
  r=h['runs'][e['run']];require(r['state']=='active' and bool(e.get('evidence')),'Observed orphan evidence required')
  r['state']='uncertain';r['evidence']=e['evidence'];h['profiles'][r['member']].pop('ack',None);diagnostic_result(s,e['run'])
 elif op=='reconcile':
  r=h['runs'][e['run']];require(r['state']=='uncertain','Only uncertain outcome needs reconcile')
  require(e['outcome'] in ('not_executed','completed','failed') and bool(e['evidence']),'Observed terminal outcome required')
  r['state']=e['outcome'];r['evidence']=e['evidence'];r['reported_usage']=e.get('usage');require(r['reported_usage']is None or type(r['reported_usage'])is int and r['reported_usage']>=0,'Invalid reported usage');diagnostic_result(s,e['run'])
 elif op=='release':
  t=s['tasks'][e['task']]
  require(e.get('safe_boundary')is True,'Confirmed safe boundary required')
  require(not any(r['task']==e['task'] and r['state']in ('active','uncertain')for r in h['runs'].values()),'Run still unresolved')
  h.get('work_authorizations',{}).pop(e['task'],None);t['paths']=[];t['resources']=[]
 elif op=='rework'and 'method'in e:
  import observations
  observations.followup(s,e,state_root,correction=True)
 elif op=='rework':
  identifier=e.get('request_id');require(isinstance(identifier,str)and bool(identifier.strip())and len(identifier)<=128,'Stable rework request ID required')
  require(e.get('source_sha256')==digest(state),'Stale full-state canonical digest; inspect before retry')
  require(h['policy_hash']==digest(effective_contract()),'Explicit policy migration required before rework')
  require(not any(r['state']in ('active','uncertain')for r in h['runs'].values()),'Drain all active/uncertain project runs before rework')
  import session_control
  require(not any(v.get('state')in session_control.UNRESOLVED+('configuration_pending_turn',)for v in h.get('controls',{}).values()),'Resolve pending/uncertain session controls before rework')
  require(not any(v.get('state')not in ('resumed','blocked')for v in h.get('handoffs',{}).values()),'Resolve in-flight handoff before rework')
  t=s['tasks'][e['task']];member=e['member'];require(t['owner']==member and t['state']=='ready_for_review','Rework requires same owner and ready_for_review task')
  requester=e.get('requester');require(requester in s['members']and s['members'][requester]['role']=='leader','Registered leader must request rework')
  require(ledger.fresh(s['members'][requester]['identity_claim']),'Stale leader identity claim')
  require(isinstance(e.get('reason'),str)and bool(e['reason'].strip()),'Explicit scoped rework reason required')
  proof=ledger.evidence(e['evidence']);require(ledger.fresh(proof),'Fresh leader decision evidence required')
  reviews=t['reviews'];require(bool(reviews)and reviews[-1]['verdict']=='fail','Latest actual failed review required')
  require(ledger.fresh(reviews[-1]['evidence']),'Failed review report changed or missing')
  failure=digest({'task':e['task'],'index':len(reviews)-1,'review':reviews[-1]})
  require(not any(value['failed_review_digest']==failure for value in h.get('reworks',{}).values()),'Failed review already consumed by rework; fresh failed review required')
  h['revision']+=1;t['state']='assigned';h['profiles'][member].pop('ack',None)
  h.setdefault('reworks',{})[identifier]={'event_digest':digest(e),'source_sha256':e['source_sha256'],'failed_review_digest':failure,'decision_evidence':proof,'reason':e['reason'],'original_transition':{'task':e['task'],'owner':member,'state':'assigned','revision':h['revision']}}
  h.setdefault('work_authorizations',{})[e['task']]=identifier
  h['changes'].append({'revision':h['revision'],'rework_request':identifier,'task':e['task'],'owner':member,'reason':e['reason'],'decision_evidence':proof})
 elif op=='reassign':
  t=s['tasks'][e['task']];require(not t['paths'] and not t['resources'],'Release ownership before reassignment')
  require(e['member']in s['members'] and s['members'][e['member']]['role']not in ('leader','reviewer'),'Execution owner required')
  require(not any(r['task']==e['task'] and r['state']in ('active','uncertain')for r in h['runs'].values()),'Run unresolved')
  h.get('work_authorizations',{}).pop(e['task'],None);t['owner']=e['member'];t['state']='assigned';h['profiles'][e['member']].pop('ack',None)
 elif op=='handoff':
  t=s['tasks'][e['task']]
  require(not any(r['task']==e['task'] and r['state']in ('active','uncertain')for r in h['runs'].values()),'Run unresolved')
  require(bool(e['artifacts']),'Artifact evidence required');t['artifacts']=[ledger.evidence(p)for p in e['artifacts']];t['state']='ready_for_review'
 elif op=='review':
  t=s['tasks'][e['task']];require(t['state']=='ready_for_review','Fresh handoff required')
  require(all(ledger.fresh(a)for a in t['artifacts']),'Stale artifact evidence')
  require(e['reviewer']!=t['owner'] and s['members'][e['reviewer']]['role']=='reviewer','Independent reviewer required')
  require(s['members'][e['reviewer']]['runtime_id_claim']!=s['members'][t['owner']]['runtime_id_claim'],'Same underlying runtime cannot review itself')
  require(e['verdict'] in ('pass','fail') and bool(e['evidence']),'Review evidence required')
  t['reviews'].append({'reviewer':e['reviewer'],'verdict':e['verdict'],'evidence':ledger.evidence(e['evidence'])})
  t['state']='reviewed'if e['verdict']=='pass'else 'assigned'
 elif op=='accept':
  t=s['tasks'][e['task']];require(t['state']=='reviewed' and t['reviews'][-1]['verdict']=='pass','Passing independent review required')
  require(all(ledger.fresh(a)for a in t['artifacts'])and ledger.fresh(t['reviews'][-1]['evidence']),'Stale evidence')
  t['state']='accepted'
 else:raise Invalid('Unknown harness operation')
 diagnostic_invariants(s)
 s['history'].append({'at':ledger.now(),'event':e})
 return s

def rework_receipt(state,request_id):
 require(request_id in state['harness'].get('reworks',{}),'Unknown rework request ID')
 record=state['harness']['reworks'][request_id];task=state['tasks'][record['original_transition']['task']]
 return {'request_id':request_id,'original_transition':record['original_transition'],'current_observation':{'state':task['state'],'owner':task['owner'],'revision':state['harness']['revision']},'scope':'Committed transition receipt, not a new transition or execution permission'}

def claim_expansion_receipt(state,request_id):
 require(request_id in state['harness'].get('claim_expansions',{}),'Unknown claim expansion request ID')
 record=state['harness']['claim_expansions'][request_id];task=state['tasks'][record['original_transition']['task']]
 return {'request_id':request_id,'original_transition':record['original_transition'],'current_observation':{'state':task['state'],'owner':task['owner'],'paths':task['paths'],'revision':state['harness']['revision']},'scope':record['authority_limit']}

def check_model(model,catalog,receipt):
 require(any(m.get('model')==model for m in catalog),'Exact model absent from live catalog')
 require(receipt.get('model')==model,'Observed thread model mismatch')

def save(path,state):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 require(not path.is_symlink(),'State symlink refused')
 fd,tmp=tempfile.mkstemp(dir=path.parent,prefix='.state-')
 try:
  with os.fdopen(fd,'w')as f:json.dump(state,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
  os.replace(tmp,path)
  directory=os.open(str(path.parent),os.O_RDONLY)
  try:os.fsync(directory)
  finally:os.close(directory)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)

def initialize(path,goal):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 require(not path.is_symlink() and not Path(str(path)+'.lock').is_symlink(),'State/lock symlink refused')
 with open(str(path)+'.lock','a')as lock:
  fcntl.flock(lock,fcntl.LOCK_EX);require(not path.exists(),'Existing project state preserved');save(path,initial(goal))

def apply_locked(path,before,events,raw):
 """Caller holds the existing project lock; never adopt a reread after apply."""
 import management_handoff as management
 path=Path(path);management.before(before,events,path,raw);state=before;applied=[]
 for event in events:
  updated=apply(state,event,path.parent,source_bytes=raw,state_path=path)
  if updated!=state:applied.append(event)
  state=updated
 if state!=before:
  require([entry['event']for entry in state['history'][len(before['history']):]]==applied,'Canonical transition history changed')
  state=management.finish(before,state,applied,path,raw);save(path,state)
 return state

def transaction(path,event):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 require(not path.is_symlink() and not Path(str(path)+'.lock').is_symlink(),'State/lock symlink refused')
 with open(str(path)+'.lock','a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX);raw=path.read_bytes();before=json.loads(raw)
  return apply_locked(path,before,[event],raw)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state',type=Path,required=True)
 sub=p.add_subparsers(dest='command',required=True)
 i=sub.add_parser('init');i.add_argument('--goal',required=True)
 a=sub.add_parser('apply');a.add_argument('--event',type=Path,required=True)
 c=sub.add_parser('checkpoint-prepare');c.add_argument('--id',required=True);c.add_argument('--view',type=Path,required=True);c.add_argument('--evidence',action='append',default=[])
 c=sub.add_parser('checkpoint-verify');c.add_argument('--directory',type=Path,required=True)
 q=sub.add_parser('packet');q.add_argument('--member',required=True);sub.add_parser('status')
 args=p.parse_args()
 if args.command=='init':initialize(args.state,args.goal)
 elif args.command=='apply':
  event=json.loads(args.event.read_text());result=transaction(args.state,event)
  if event['op']in ('diagnostic_grant','diagnostic_permission_recovery'):print(json.dumps(diagnostic_receipt(result,event['request_id']),ensure_ascii=False,indent=2))
  if event['op']=='rework':print(json.dumps(rework_receipt(result,event['request_id']),ensure_ascii=False,indent=2))
  if event['op']=='claim_expand':print(json.dumps(claim_expansion_receipt(result,event['request_id']),ensure_ascii=False,indent=2))
 elif args.command=='checkpoint-prepare':
  import checkpoints
  print(json.dumps({'candidate':str(checkpoints.prepare(args.state,args.id,json.loads(args.view.read_text()),args.evidence))}))
 elif args.command=='checkpoint-verify':
  import checkpoints
  proposal,_=checkpoints.verify(args.directory);print(json.dumps({'verified':True,'proposal_sha256':digest(proposal),'source_sha256':proposal['source_sha256']}))
 elif args.command=='packet':print(json.dumps(packet(json.loads(args.state.read_text()),args.member),ensure_ascii=False,indent=2))
 else:
  s=json.loads(args.state.read_text());h=s['harness'];print(json.dumps({'revision':h['revision'],'usage':usage_summary(s),'members':h['profiles'],'tasks':s['tasks'],'runs':h['runs'],'limits':'Managed boundary only; identities claimed unless receipt observed'},ensure_ascii=False,indent=2))
if __name__=='__main__':
 try:main()
 except (Invalid,KeyError,OSError,ValueError)as e:print(json.dumps({'error':str(e)}));sys.exit(2)
