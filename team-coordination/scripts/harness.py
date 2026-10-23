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
 return {'policy':json.loads((root/'policy.json').read_text()),'roles':{p.stem:p.read_text()for p in sorted((root/'roles').glob('*.md'))},'schema':json.loads((root/'schema/project-state.schema.json').read_text()),'implementation_sha256':{name:hashlib.sha256((root/'scripts'/name).read_bytes()).hexdigest()for name in ('harness.py','managed_run.py','team_ledger.py','session_control.py','checkpoints.py','profile_defaults.py')}}

def budget_ceiling(a,default):
 # Validate retained copied approval bytes; later migration does not reauthenticate a human.
 ceilings=[default]
 for identifier,record in a.get('budget_changes',{}).items():
  request=record['request'];transition=record['original_transition']
  require(request['request_id']==identifier and request['new_budget']==transition['budget']and request['expected_budget']==transition['previous_budget']and request['project']==transition['project']==a['goal'],'Budget receipt binding changed')
  require(type(transition['budget'])is int and type(transition['previous_budget'])is int and transition['previous_budget']<transition['budget'],'Invalid committed budget bounds')
  for field,proof in [('approval_bytes_base64','approval_evidence'),('human_approval_bytes_base64','human_approval')]:
   data=base64.b64decode(record[field],validate=True);require(hashlib.sha256(data).hexdigest()==record[proof]['sha256'],'Copied budget evidence changed')
  require(record['human_approval']==request['human_approval'],'Human approval binding changed')
  approvals=json.loads(base64.b64decode(record['approval_bytes_base64']))
  for role in ('leader','reviewer'):
   approval=approvals[role];require(approval['request_sha256']==digest(request)and all(approval.get(flag)is True for flag in ('approved','safe_boundary','all_current_obligations_retained','human_approval_verified')),'Retained budget approval changed')
  if transition['budget']==a['budget']:ceilings.append(transition['budget'])
 return max(ceilings)

def budget_change_receipt(state,request_id):
 a=state['harness'];require(request_id in a.get('budget_changes',{}),'Unknown budget request ID')
 record=a['budget_changes'][request_id]
 return {'request_id':request_id,'original_transition':record['original_transition'],'current_observation':{'budget':a['budget'],'spent':a['spent'],'revision':a['revision']},'scope':'Committed administrative receipt; no execution permission or native reload'}

def diagnostic_tasks(s):
 return {record['request']['task'] for record in s['harness'].get('diagnostics',{}).values()}

def diagnostic_provenance(s,task):
 return digest({'task':s['tasks'][task],'reworks':{k:v for k,v in s['harness'].get('reworks',{}).items()if v['original_transition']['task']==task}})

def diagnostic_invariants(s):
 for record in s['harness'].get('diagnostics',{}).values():
  require(s['tasks'][record['request']['task']]==record['original_task'],'Diagnostic task obligations changed; separately authorized transition required')
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
 reserve=e.get('max_reserve');require(type(reserve)is int and 0<reserve<=h['budget']-h['spent'],'Diagnostic reservation must fit existing remaining budget')
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
 h.setdefault('diagnostics',{})[identifier]={'event_digest':digest(e),'request':proposal,'original_task':copy.deepcopy(t),'original_transition':transition,'state':'granted','approval_evidence':proof,'approval_bytes_base64':base64.b64encode(data).decode(),'human_approval_bytes_base64':base64.b64encode(human_data).decode(),'authority_limit':'Recorded attestations; one diagnostic run only, no correction or deliverable acceptance; no native permission enforcement'}
 h['changes'].append({'revision':h['revision'],'diagnostic_request':identifier,'task':task,'evidence_goal':goal,'modification_paths':paths,'max_reserve':reserve})

def diagnostic_result(s,run):
 r=s['harness']['runs'][run];identifier=r.get('diagnostic_request_id')
 if identifier:
  record=s['harness']['diagnostics'][identifier];record['state']='uncertain'if r['state']=='uncertain'else 'closed';record['result']={'run':run,'outcome':r['state'],'evidence':r['evidence'],'charged':r.get('charged'),'task_state':s['tasks'][r['task']]['state']}

def diagnostic_receipt(s,request_id):
 require(request_id in s['harness'].get('diagnostics',{}),'Unknown diagnostic request ID');r=s['harness']['diagnostics'][request_id]
 return {'request_id':request_id,'original_transition':r['original_transition'],'current_observation':{'state':r['state'],'result':r.get('result'),'revision':s['harness']['revision']},'scope':'Historical one-cycle diagnostic receipt; original deliverable remains blocked'}

def initial(goal,budget=None,concurrency=None):
 limits=effective_contract()['policy']['limits'];budget=limits['project_token_budget']if budget is None else budget;concurrency=limits['concurrency']if concurrency is None else concurrency
 require(type(budget)is int and budget>=0 and type(concurrency)is int and concurrency>0 and budget<=limits['project_token_budget']and concurrency<=limits['concurrency'],'Invalid project limits')
 s=ledger.apply({}, {'op':'init'})
 s['harness']={'schema':1,'revision':1,'goal':goal,'constraints':[],'decisions':[],'changes':[], 'profiles':{},'runs':{},'budget':budget,'spent':0,'concurrency':concurrency,'context_limit':limits['context_estimate_limit'],'review_limit':limits['review_passes'],'policy_hash':digest(effective_contract())}
 return s

def packet(s,member):
 h=s['harness'];p=h['profiles'][member];contract=effective_contract()
 require(h['policy_hash']==digest(contract),'Effective policy/role/schema changed; explicit policy_refresh required')
 tasks=[{'id':k,'purpose':v['purpose'],'context':v.get('context',''),'paths':v['paths'],'state':v['state']} for k,v in s['tasks'].items() if v['owner']==member]
 result={'schema':1,'revision':h['revision'],'epoch':p['epoch'],'policy_hash':h['policy_hash'],'policy_version':contract['policy']['version'],'role_contract':contract['roles'][p['role']],'limits':contract['policy']['limits'],'goal':h['goal'],'constraints':h['constraints'],'decisions':h['decisions'],'role':p['role'],'tasks':tasks,'changes':[c for c in h['changes'] if c['revision']>p.get('last_revision',0)],'unresolved_runs':[k for k,v in h['runs'].items() if v['state'] in ('active','uncertain')]}
 result['accounting']={'budget':h['budget'],'spent':h['spent'],'meaning':'reservation ledger, not billing'}
 import checkpoints
 working=checkpoints.projection(s)
 if working:
  contexts=working.pop('task_contexts');result.update(working)
  for task in result['tasks']:
   if task['id']in contexts:task['context']=contexts[task['id']]
  result['task_obligations']={k:{field:value for field,value in v.items()if field!='context'}for k,v in s['tasks'].items()if v['state']!='accepted'or v.get('block')}
  result['accounting']={'budget':h['budget'],'spent':h['spent'],'meaning':'reservation ledger, not billing'}
 if h.get('diagnostics'):result['diagnostics']={key:{'request':record['request'],'state':record['state'],'run':record.get('run'),'result':record.get('result'),'original_task':{field:value for field,value in record['original_task'].items()if field!='context'},'authority_limit':record['authority_limit']}for key,record in h['diagnostics'].items()}
 require(math.ceil(len(json.dumps(result,ensure_ascii=False).encode())/4)<=h['context_limit'],'Context estimate exceeds limit; leader must reduce irrelevant context, preserve decisions')
 return result

def ack_current(s,member):
 p=s['harness']['profiles'][member];a=p.get('ack')
 require(s['harness']['policy_hash']==digest(effective_contract()),'Policy changed; leader must migrate project policy and refresh ACKs')
 require(a is not None and a=={'revision':s['harness']['revision'],'epoch':p['epoch'],'digest':digest(packet(s,member))},'Latest context acknowledgement required')

def apply(state,e,state_root=None):
 s=copy.deepcopy(state);h=s['harness'];op=e['op']
 if op=='diagnostic_grant'and e.get('request_id')in h.get('diagnostics',{}):
  require(h['diagnostics'][e['request_id']]['event_digest']==digest(e),'Conflicting diagnostic request ID; inspect committed receipt');return s
 if op=='budget_change'and e.get('request_id')in h.get('budget_changes',{}):
  require(h['budget_changes'][e['request_id']]['event_digest']==digest(e),'Conflicting budget request ID; inspect committed receipt')
  return s
 if op=='rework'and e.get('request_id')in h.get('reworks',{}):
  require(h['reworks'][e['request_id']]['event_digest']==digest(e),'Conflicting rework request ID; inspect committed receipt')
  return s  # Readback only: never rewrite later state or repeat the transition.
 diagnostic_invariants(s)
 guarded=diagnostic_tasks(s)
 if op in ('claim','release','reassign','handoff','review','accept','rework')and e.get('task')in guarded:raise Invalid('Diagnostic-only task remains blocked pending separately authorized future transition')
 if op=='control_handoff_prepare':require(not guarded.intersection(e.get('tasks',[])),'Diagnostic owner/claims cannot transfer')
 if op=='control_transfer':require(not guarded.intersection(h.get('handoffs',{}).get(e.get('handoff'),{}).get('tasks',[])),'Diagnostic owner/claims cannot transfer')
 if op in ('checkpoint_commit','checkpoint_restore'):
  import checkpoints
  return checkpoints.apply(s,e,state_root)
 if op in ('begin','control_intent')and h.get('checkpoint'):
  import checkpoints
  checkpoints.active(s)
 if op.startswith('control_'):
  import session_control
  s=session_control.apply(s,e)
 elif op=='diagnostic_grant':diagnostic_grant(s,e,state_root)
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
  t['paths']=sorted(set(paths+t['paths']))
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
  h['budget']=min(h['budget'],budget_ceiling(h,limits['project_token_budget']));h['concurrency']=limits['concurrency'];h['context_limit']=limits['context_estimate_limit'];h['review_limit']=limits['review_passes']
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
   require(type(e['reserve'])is int and 0<e['reserve']<=grant['request']['max_reserve'],'Diagnostic reservation exceeds approved bound')
  else:require(e['task']not in diagnostic_tasks(s),'Diagnostic-only task cannot begin normal work')
  require(t['owner']==m and (t['state']=='ready_for_review'if diagnostic else t['state']in ('assigned','running')),'Wrong task owner/state')
  require(ledger.fresh(s['members'][m]['identity_claim']),'Stale identity claim')
  require(p['role'] not in ('leader','reviewer') and p['model'] is not None,'Requested role model unresolved or nonexecuting role')
  import session_control
  session_control.typed_task(p['role'],t.get('kind','implementation'))
  if m in h.get('sessions',{}):require(h['sessions'][m]['execution']=='enabled','Source/recipient execution paused or disabled')
  ack_current(s,m);require(t['paths'],'Write ownership required')
  require(e['run'] not in h['runs'],'Duplicate run id')
  require(not any(r['state']=='uncertain' for r in h['runs'].values()),'Uncertain run must be reconciled')
  active=[r for r in h['runs'].values() if r['state']=='active']
  packets=[r for r in h.get('controls',{}).values()if r.get('packet_reserve')and r['state']in ('request_pending','outcome_unknown')]
  require(len(active)+len(packets)<h['concurrency'],'Concurrency exhausted')
  require(not any(r['task']==e['task'] for r in active),'Task already executing')
  reserve=e['reserve'];require(type(reserve)is int and reserve>0,'Positive integer reservation required')
  require(h['spent']+sum(r['reserve'] for r in active)+sum(r['packet_reserve']for r in packets)+reserve<=h['budget'],'Budget exhausted')
  h['runs'][e['run']]={'task':e['task'],'member':m,'model':p['model'],'revision':h['revision'],'epoch':p['epoch'],'state':'active','reserve':reserve,'stale':False,'phase':'reserved','observed':{},'packet':packet(s,m)}
  if diagnostic:h['runs'][e['run']]['diagnostic_request_id']=diagnostic;grant['state']='active';grant['run']=e['run']
  else:t['state']='running'
 elif op=='observe':
  r=h['runs'][e['run']];require(r['state']=='active','Run not active');r['observed'].update(e['receipt']);r['phase']=e['phase']
 elif op=='finish':
  r=h['runs'][e['run']];require(r['state']=='active','Run already terminal');out=e['outcome'];require(out in ('completed','failed','uncertain','not_executed'),'Invalid outcome')
  require(bool(e['evidence']),'Outcome evidence required');r['state']=out;r['evidence']=e['evidence']
  if out!='uncertain':
   used=e.get('usage',0 if out=='not_executed' else r['reserve']);require(type(used)is int and used>=0,'Invalid usage')
   r['observed_usage']=e.get('usage');charged=0 if out=='not_executed'else max(r['reserve'],used)
   r['charged']=charged;r['measurement']='reported_provisional_reservation_retained' if 'usage'in e else ('none_started' if out=='not_executed' else 'reserved_missing_usage');h['spent']+=charged
  p=h['profiles'][r['member']];p['last_revision']=r['revision'];p.pop('ack',None);diagnostic_result(s,e['run'])
 elif op=='mark_uncertain':
  r=h['runs'][e['run']];require(r['state']=='active' and bool(e.get('evidence')),'Observed orphan evidence required')
  r['state']='uncertain';r['evidence']=e['evidence'];h['profiles'][r['member']].pop('ack',None);diagnostic_result(s,e['run'])
 elif op=='reconcile':
  r=h['runs'][e['run']];require(r['state']=='uncertain','Only uncertain outcome needs reconcile')
  require(e['outcome'] in ('not_executed','completed','failed') and bool(e['evidence']),'Observed terminal outcome required')
  r['state']=e['outcome'];r['evidence']=e['evidence'];r['charged']=0 if r['state']=='not_executed' else r['reserve'];h['spent']+=r['charged'];diagnostic_result(s,e['run'])
 elif op=='release':
  t=s['tasks'][e['task']]
  require(e.get('safe_boundary')is True,'Confirmed safe boundary required')
  require(not any(r['task']==e['task'] and r['state']in ('active','uncertain')for r in h['runs'].values()),'Run still unresolved')
  t['paths']=[];t['resources']=[]
 elif op=='budget_change':
  identifier=e.get('request_id');require(isinstance(identifier,str)and bool(identifier.strip())and len(identifier)<=128,'Stable budget request ID required')
  require(state_root is not None and Path(e['project_root']).is_absolute()and Path(e['project_root']).resolve()==Path(state_root).resolve(),'Exact canonical project root required')
  require(e.get('source_sha256')==digest(state),'Stale full-state canonical digest; inspect before retry')
  require(e.get('project')==h['goal'],'Exact project goal required')
  require(e.get('policy_hash')==h['policy_hash']==digest(effective_contract()),'Current exact policy contract required; migrate separately')
  old=e.get('expected_budget');new=e.get('new_budget')
  require(type(old)is int and type(new)is int and old==h['budget']and h['spent']<=old<new,'Exact current budget and additive integer increase required')
  import checkpoints
  checkpoints.quiescent(s)
  if h.get('checkpoint'):checkpoints.active(s)
  requester=e.get('requester');require(requester in s['members']and s['members'][requester]['role']=='leader','Registered leader must request budget change')
  require(ledger.fresh(s['members'][requester]['identity_claim']),'Stale leader identity claim')
  require(isinstance(e.get('reason'),str)and bool(e['reason'].strip()),'Explicit budget change reason required')
  human=e['human_approval'];require(ledger.fresh(human),'Exact human approval bytes required')
  human_data=Path(human['path']).read_bytes();require(hashlib.sha256(human_data).hexdigest()==human['sha256'],'Human approval changed during capture')
  approval_proof=ledger.evidence(e['approvals']);approval_data=Path(e['approvals']).read_bytes();require(hashlib.sha256(approval_data).hexdigest()==approval_proof['sha256'],'Approval changed during capture')
  approvals=json.loads(approval_data);proposal={k:v for k,v in e.items()if k!='approvals'};members=[]
  for role in ('leader','reviewer'):
   approval=approvals[role];member=approval['member'];require(member in s['members']and s['members'][member]['role']==role,'Budget approval role mismatch')
   require(ledger.fresh(s['members'][member]['identity_claim']),'Stale budget approval identity')
   require(approval.get('request_sha256')==digest(proposal)and all(approval.get(flag)is True for flag in ('approved','safe_boundary','all_current_obligations_retained','human_approval_verified')),'Exact budget request and safe boundary approval required')
   members.append(member)
  require(members[0]==requester and members[0]!=members[1]and s['members'][members[0]]['runtime_id_claim']!=s['members'][members[1]]['runtime_id_claim'],'Independent budget review required')
  h['budget']=new;h['revision']+=1
  for profile in h['profiles'].values():profile.pop('ack',None)
  transition={'project':h['goal'],'project_root':str(Path(state_root).resolve()),'previous_budget':old,'budget':new,'spent':h['spent'],'revision':h['revision']}
  h.setdefault('budget_changes',{})[identifier]={'event_digest':digest(e),'request':proposal,'approval_evidence':approval_proof,'approval_bytes_base64':base64.b64encode(approval_data).decode(),'human_approval':human,'human_approval_bytes_base64':base64.b64encode(human_data).decode(),'original_transition':transition,'authority_limit':'Recorded leader and reviewer attestations; hashes do not authenticate human identity'}
  h['changes'].append({'revision':h['revision'],'budget_request':identifier,'old_budget':old,'new_budget':new,'reason':e['reason']})
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
  require(len(reviews)<h['review_limit'],'Review allowance exhausted; separate leader decision required')
  failure=digest({'task':e['task'],'index':len(reviews)-1,'review':reviews[-1]})
  require(not any(value['failed_review_digest']==failure for value in h.get('reworks',{}).values()),'Failed review already consumed by rework; fresh failed review required')
  h['revision']+=1;t['state']='assigned';h['profiles'][member].pop('ack',None)
  h.setdefault('reworks',{})[identifier]={'event_digest':digest(e),'source_sha256':e['source_sha256'],'failed_review_digest':failure,'decision_evidence':proof,'reason':e['reason'],'original_transition':{'task':e['task'],'owner':member,'state':'assigned','revision':h['revision']}}
  h['changes'].append({'revision':h['revision'],'rework_request':identifier,'task':e['task'],'owner':member,'reason':e['reason'],'decision_evidence':proof})
 elif op=='reassign':
  t=s['tasks'][e['task']];require(not t['paths'] and not t['resources'],'Release ownership before reassignment')
  require(e['member']in s['members'] and s['members'][e['member']]['role']not in ('leader','reviewer'),'Execution owner required')
  require(not any(r['task']==e['task'] and r['state']in ('active','uncertain')for r in h['runs'].values()),'Run unresolved')
  t['owner']=e['member'];t['state']='assigned';h['profiles'][e['member']].pop('ack',None)
 elif op=='handoff':
  t=s['tasks'][e['task']]
  require(not any(r['task']==e['task'] and r['state']in ('active','uncertain')for r in h['runs'].values()),'Run unresolved')
  require(bool(e['artifacts']),'Artifact evidence required');t['artifacts']=[ledger.evidence(p)for p in e['artifacts']];t['state']='ready_for_review'
 elif op=='review':
  t=s['tasks'][e['task']];require(t['state']=='ready_for_review','Fresh handoff required')
  require(all(ledger.fresh(a)for a in t['artifacts']),'Stale artifact evidence')
  require(e['reviewer']!=t['owner'] and s['members'][e['reviewer']]['role']=='reviewer','Independent reviewer required')
  require(s['members'][e['reviewer']]['runtime_id_claim']!=s['members'][t['owner']]['runtime_id_claim'],'Same underlying runtime cannot review itself')
  require(len(t['reviews'])<h['review_limit'],'Review limit reached; leader decision required')
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

def initialize(path,goal,budget=None):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 require(not path.is_symlink() and not Path(str(path)+'.lock').is_symlink(),'State/lock symlink refused')
 with open(str(path)+'.lock','a')as lock:
  fcntl.flock(lock,fcntl.LOCK_EX);require(not path.exists(),'Existing project state preserved');save(path,initial(goal,budget))

def transaction(path,event):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 require(not path.is_symlink() and not Path(str(path)+'.lock').is_symlink(),'State/lock symlink refused')
 with open(str(path)+'.lock','a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX);before=json.loads(path.read_text());s=apply(before,event,path.parent)
  if s!=before:save(path,s)
  return s

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state',type=Path,required=True)
 sub=p.add_subparsers(dest='command',required=True)
 i=sub.add_parser('init');i.add_argument('--goal',required=True);i.add_argument('--budget',type=int)
 a=sub.add_parser('apply');a.add_argument('--event',type=Path,required=True)
 c=sub.add_parser('checkpoint-prepare');c.add_argument('--id',required=True);c.add_argument('--view',type=Path,required=True);c.add_argument('--evidence',action='append',default=[])
 c=sub.add_parser('checkpoint-verify');c.add_argument('--directory',type=Path,required=True)
 q=sub.add_parser('packet');q.add_argument('--member',required=True);sub.add_parser('status')
 args=p.parse_args()
 if args.command=='init':initialize(args.state,args.goal,args.budget)
 elif args.command=='apply':
  event=json.loads(args.event.read_text());result=transaction(args.state,event)
  if event['op']=='diagnostic_grant':print(json.dumps(diagnostic_receipt(result,event['request_id']),ensure_ascii=False,indent=2))
  if event['op']=='budget_change':print(json.dumps(budget_change_receipt(result,event['request_id']),ensure_ascii=False,indent=2))
  if event['op']=='rework':print(json.dumps(rework_receipt(result,event['request_id']),ensure_ascii=False,indent=2))
 elif args.command=='checkpoint-prepare':
  import checkpoints
  print(json.dumps({'candidate':str(checkpoints.prepare(args.state,args.id,json.loads(args.view.read_text()),args.evidence))}))
 elif args.command=='checkpoint-verify':
  import checkpoints
  proposal,_=checkpoints.verify(args.directory);print(json.dumps({'verified':True,'proposal_sha256':digest(proposal),'source_sha256':proposal['source_sha256']}))
 elif args.command=='packet':print(json.dumps(packet(json.loads(args.state.read_text()),args.member),ensure_ascii=False,indent=2))
 else:
  s=json.loads(args.state.read_text());h=s['harness'];print(json.dumps({'revision':h['revision'],'budget':h['budget'],'spent':h['spent'],'members':h['profiles'],'tasks':s['tasks'],'runs':h['runs'],'limits':'Managed boundary only; identities claimed unless receipt observed'},ensure_ascii=False,indent=2))
if __name__=='__main__':
 try:main()
 except (Invalid,KeyError,OSError,ValueError)as e:print(json.dumps({'error':str(e)}));sys.exit(2)
