#!/usr/bin/env python3
"""Reviewed compact working views; immutable source history, not conversation compaction."""
import copy,hashlib,json,os,re
from pathlib import Path,PurePosixPath
import harness as h
require=h.require

def digest(value):return h.digest(value)
def encoded(value):return (json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()
def sha(data):return hashlib.sha256(data).hexdigest()
def safe(root,relative):
 p=PurePosixPath(relative);require(not p.is_absolute() and p.parts and '..'not in p.parts and '\\'not in relative,'Unsafe checkpoint object path')
 root=Path(root);dest=root.joinpath(*p.parts)
 for x in [dest,*dest.parents]:
  require(not x.is_symlink(),'Checkpoint symlink refused')
  if x.is_file():require(x.stat().st_nlink==1,'Checkpoint hardlink refused')
  if x==root:break
 require(dest.resolve().is_relative_to(root.resolve()),'Checkpoint object escapes root');return dest

def durable_directory(path):
 fd=os.open(str(path),os.O_RDONLY)
 try:os.fsync(fd)
 finally:os.close(fd)

def immutable(path,data):
 path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
 require(not path.is_symlink(),'Checkpoint symlink refused')
 if path.exists():require(path.read_bytes()==data,'Conflicting immutable checkpoint object');return
 with os.fdopen(os.open(str(path),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'wb')as f:f.write(data);f.flush();os.fsync(f.fileno())
 durable_directory(path.parent)

def view_valid(source,view):
 require(all(k in view for k in ('historical_constraints','historical_decisions','constraint_indices','decision_indices','historical_summary','remaining_work','task_contexts')),'Explicit historical classification required')
 for key,field in [('constraint_indices','constraints'),('decision_indices','decisions')]:
  indices=view[key];require(isinstance(indices,list)and all(type(i)is int and 0<=i<len(source['harness'][field])for i in indices)and len(set(indices))==len(indices),'Invalid working-view source indices')
  historical=view['historical_'+field];require(isinstance(historical,dict)and set(historical)=={str(i)for i in range(len(source['harness'][field]))if i not in indices}and all(isinstance(v,str)and v.strip()for v in historical.values()),'Each historical exclusion needs explicit reviewed rationale')
 require(isinstance(view['historical_summary'],str)and bool(view['historical_summary'].strip()),'Reviewed historical rationale summary required')
 require(isinstance(view['remaining_work'],list)and all(isinstance(v,str)and v.strip()for v in view['remaining_work'])and view['remaining_work'],'Remaining obligations required')
 require(set(view['task_contexts'])==set(source['tasks'])and all(isinstance(v,str)and v.strip()for v in view['task_contexts'].values()),'Every existing task needs a reviewed working context')

def capture_parent(source,directory,files):
 cp=source['harness'].get('checkpoint')
 if not cp:return []
 parent,_=active(source);old=Path(cp['directory'])
 def capture(relative,expected):
  data=safe(old,relative).read_bytes();require(sha(data)==expected,'Parent archive changed during capture');key='objects/'+sha(data);immutable(safe(directory,key),data);files[key]=sha(data);return key
 mapping={rel:capture(rel,value)for rel,value in parent['files'].items()}
 proposal_bytes=safe(old,'proposal.json').read_bytes();proposal_key='objects/'+sha(proposal_bytes);immutable(safe(directory,proposal_key),proposal_bytes);files[proposal_key]=sha(proposal_bytes)
 proof=cp['approval_object'];approval_key=capture(proof['relative'],proof['sha256'])
 entry={'proposal_sha256':digest(parent),'proposal_object':proposal_key,'source_sha256':parent['source_sha256'],'files':mapping,'approval_object':approval_key}
 return parent.get('lineage',[])+[entry]

def verify_lineage(directory,p,source):
 lineage=p.get('lineage',[]);parent_id=p['parent_checkpoint'];require(bool(lineage)==bool(parent_id),'Missing parent checkpoint closure')
 prior=[]
 for entry in lineage:
  def blob(relative):
   require(relative in p['files']and re.fullmatch(r'objects/[0-9a-f]{64}',relative),'Missing lineage object');return safe(directory,relative).read_bytes()
  parent=json.loads(blob(entry['proposal_object']));require(digest(parent)==entry['proposal_sha256'],'Parent proposal digest changed')
  require(parent.get('lineage',[])==prior,'Checkpoint lineage truncated/reordered')
  require(set(parent['files'])==set(entry['files']),'Parent object closure incomplete')
  for relative,value in parent['files'].items():require(sha(blob(entry['files'][relative]))==value,'Parent evidence object changed')
  snapshot=json.loads(blob(entry['files']['snapshot.json']));require(digest(snapshot)==parent['source_sha256']==entry['source_sha256'],'Parent source digest changed')
  approved=json.loads(blob(entry['approval_object']))
  for role in ['leader','reviewer']:
   ack=approved[role];require(ack['proposal_sha256']==digest(parent)and ack['source_sha256']==parent['source_sha256']and ack['target_policy_hash']==parent['target_policy_hash']and ack['approved']is True,'Parent approval binding changed')
  prior.append(entry)
 if lineage:require(lineage[-1]['proposal_sha256']==parent_id==source['harness']['checkpoint']['proposal_sha256'],'Checkpoint parent identity mismatch')

def prepare(state_path,identifier,working_view,required_evidence):
 state_path=Path(state_path);require(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}',identifier)is not None,'Invalid checkpoint ID')
 source=json.loads(state_path.read_text());view_valid(source,working_view)
 parent=safe(state_path.parent,'checkpoints');parent.mkdir(mode=0o700,exist_ok=True);directory=safe(state_path.parent,'checkpoints/'+identifier);directory.mkdir(mode=0o700,exist_ok=True);durable_directory(directory.parent);durable_directory(state_path.parent)
 snapshot=encoded(source);immutable(safe(directory,'snapshot.json'),snapshot);files={'snapshot.json':sha(snapshot)};evidence=[]
 # Only explicitly selected evidence is opened. No recursive filesystem or credential scan.
 for name in required_evidence:
  p=Path(name);require(p.is_file()and not p.is_symlink(),'Required evidence must be a regular non-symlink file');data=p.read_bytes();key='objects/'+sha(data);immutable(safe(directory,key),data);files[key]=sha(data);evidence.append({'original_path':str(p.resolve()),'relative':key,'sha256':sha(data)})
 lineage=capture_parent(source,directory,files)
 proposal={'schema':1,'lineage':lineage,'id':identifier,'source_sha256':digest(source),'source_revision':source['harness']['revision'],'source_policy_hash':source['harness']['policy_hash'],'target_policy_hash':digest(h.effective_contract()),'parent_checkpoint':source['harness'].get('checkpoint',{}).get('proposal_sha256'),'working_view':working_view,'required_evidence':evidence,'files':files,'coverage':{field:[{'index':i,'sha256':digest(v),'carry_verbatim':i in working_view[key]}for i,v in enumerate(source['harness'][field])]for key,field in [('constraint_indices','constraints'),('decision_indices','decisions')]},'semantic_limit':'Coverage hashes prove references only; owner and independent reviewer must approve all current obligations retained inline.'}
 path=safe(directory,'proposal.json');immutable(path,encoded(proposal));durable_directory(directory);return path

def verify(directory,expected=None):
 try:
  directory=Path(directory);p=json.loads(safe(directory,'proposal.json').read_text());require(p['schema']==1,'Unknown checkpoint schema')
  if expected:require(digest(p)==expected,'Checkpoint proposal changed')
  require('snapshot.json'in p['files'],'Snapshot required')
  for rel,value in p['files'].items():
   require(rel=='snapshot.json'or re.fullmatch(r'objects/[0-9a-f]{64}',rel),'Unexpected checkpoint object')
   require(sha(safe(directory,rel).read_bytes())==value,'Checkpoint object missing/corrupt')
  source=json.loads(safe(directory,'snapshot.json').read_text());require(digest(source)==p['source_sha256'],'Snapshot source digest mismatch');view_valid(source,p['working_view'])
  verify_lineage(directory,p,source)
  for e in p['required_evidence']:require(p['files'].get(e['relative'])==e['sha256'],'Required evidence manifest mismatch')
  return p,source
 except (OSError,ValueError,KeyError,TypeError)as e:raise h.Invalid('Checkpoint verification failed: '+str(e))from e

def quiescent(s):
 a=s['harness'];require(type(a['spent'])is int and 0<=a['spent']<=a['budget'],'Unresolved budget accounting')
 claims=[]
 for task in s['tasks'].values():
  for path in task['paths']:
   require(not any(h.ledger.overlaps(path,other)for other in claims),'Conflicting canonical ownership');claims.append(path)
 require(not any(x['state']in ('active','uncertain')for x in a['runs'].values()),'Resolve active/uncertain runs first')
 require(not any(x.get('state')not in ('completed','rejected','failed','verified','configuration_verified_after_turn','not_executed')for x in a.get('controls',{}).values()),'Resolve pending control operations first')
 require(not any(x.get('state',x.get('phase'))!='resumed'for x in a.get('handoffs',{}).values()),'Resolve pending handoffs first')

def active(s):
 a=s['harness'];cp=a.get('checkpoint')
 if not cp:return None
 p,source=verify(cp['directory'],cp['proposal_sha256'])
 proof=cp['approval_object'];object_path=safe(cp['directory'],proof['relative']);require(object_path.is_file()and sha(object_path.read_bytes())==proof['sha256'],'Checkpoint approval object changed')
 for field in ['constraints','decisions','changes']:
  original=source['harness'][field];require(a[field][:len(original)]==original,'Canonical checkpoint history changed')
 require(s['history'][:len(source['history'])]==source['history'],'Canonical audit history changed')
 return p,source

def projection(s):
 item=active(s)
 if not item:return None
 p,source=item;v=p['working_view'];a=s['harness'];old=source['harness']
 return {'checkpoint':{'id':p['id'],'proposal_sha256':digest(p),'source_sha256':p['source_sha256'],'archive_relative':'checkpoints/'+p['id'],'history_count':len(source['history']),'semantic_approval':'recorded owner/reviewer attestations, not cryptographic identity'},'constraints':[old['constraints'][i]for i in v['constraint_indices']]+a['constraints'][len(old['constraints']):],'decisions':[old['decisions'][i]for i in v['decision_indices']]+a['decisions'][len(old['decisions']):],'historical_summary':v['historical_summary'],'remaining_work':v['remaining_work'],'changes':a['changes'][len(old['changes']):],'task_contexts':v['task_contexts']}

def approval(s,p,path):
 proof=h.ledger.evidence(path);data=Path(path).read_bytes();require(sha(data)==proof['sha256'],'Approval changed during capture');value=json.loads(data);members=[]
 for role in ['leader','reviewer']:
  x=value[role];m=x['member'];require(s['members'][m]['role']==role,'Checkpoint approval role mismatch');require(h.ledger.fresh(s['members'][m]['identity_claim']),'Stale approval identity claim')
  require(x['proposal_sha256']==digest(p)and x['source_sha256']==p['source_sha256']and x.get('target_policy_hash')==p['target_policy_hash']and x.get('approved')is True and x.get('safe_boundary')is True and x.get('all_current_obligations_retained')is True,'Exact reviewed checkpoint and safe boundary approval required');members.append(m)
 require(members[0]!=members[1]and s['members'][members[0]]['runtime_id_claim']!=s['members'][members[1]]['runtime_id_claim'],'Independent checkpoint review required');return proof,data

def apply(state,e,state_root=None):
 require(state_root is not None,'Checkpoint administration needs a bound canonical state path')
 state_root=Path(state_root).resolve();s=copy.deepcopy(state);a=s['harness']
 if e['op']=='checkpoint_commit':
  candidate=Path(e['candidate']);p,source=verify(candidate.parent);require(candidate.name=='proposal.json'and candidate.parent.resolve()==safe(state_root,'checkpoints/'+p['id']).resolve(),'Candidate outside canonical checkpoint root');current=a.get('checkpoint')
  if current and current['id']==p['id']:
   require(current['proposal_sha256']==digest(p),'Conflicting committed checkpoint ID');active(s);return s
  quiescent(s)
  if current:active(s)
  require(digest(s)==p['source_sha256'],'Checkpoint full source state changed; prepare again')
  require(p['target_policy_hash']==digest(h.effective_contract()),'Target contract changed after proposal; prepare and approve again')
  proof,approval_data=approval(s,p,e['approvals']);approval_relative='objects/'+sha(approval_data);immutable(safe(candidate.parent,approval_relative),approval_data);old_contract=a['policy_hash']
  require(old_contract==digest(h.effective_contract())or e.get('policy_refresh')is True,'Explicit policy migration required')
  if e.get('policy_refresh'):
   require(bool(e.get('reason')),'Policy migration reason required');contract=h.effective_contract();limits=contract['policy']['limits'];require(a['spent']<=a['budget']<=limits['project_token_budget'],'Preserve budget; resolve accounting before migration')
   a.update(policy_hash=digest(contract),concurrency=min(a['concurrency'],limits['concurrency']),context_limit=min(a['context_limit'],limits['context_estimate_limit']),review_limit=min(a['review_limit'],limits['review_passes']))
   for x in a['profiles'].values():x['model']=contract['policy']['roles'][x['role']]['model']
  a['checkpoint']={'id':p['id'],'directory':str(candidate.parent.resolve()),'proposal_sha256':digest(p),'approval':proof,'approval_object':{'relative':approval_relative,'sha256':sha(approval_data)},'source_policy_hash':old_contract}
 elif e['op']=='checkpoint_restore':
  quiescent(s);require(Path(e['directory']).resolve().is_relative_to(state_root),'Restore outside canonical project root')
  require(e.get('safe_boundary')is True and s['members'][e['leader']]['role']=='leader','Leader safe-boundary restore required');cp=a['checkpoint'];p,source=verify(e['directory'],cp['proposal_sha256']);cp['directory']=str(Path(e['directory']).resolve())
 else:raise h.Invalid('Unknown checkpoint operation')
 a['revision']+=1
 for x in a['profiles'].values():x['epoch']+=1;x.pop('ack',None)
 a['changes'].append({'revision':a['revision'],'checkpoint':a['checkpoint']['id'],'operation':e['op']})
 s['history'].append({'at':h.ledger.now(),'event':e})
 # Preview every member, including roles that do not own tasks, before atomic save.
 for member in a['profiles']:h.packet(s,member)
 return s
