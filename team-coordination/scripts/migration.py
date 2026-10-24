"""Explicit contract migration; prior state bytes remain private historical evidence."""
import base64,copy,hashlib,json
from pathlib import Path

def project(raw):
 """Pure uncommitted projection. No authorization, write, ACK or execution implied."""
 import harness as h
 old=json.loads(raw);s=copy.deepcopy(old);a=s['harness']
 for key in ('budget','spent','context_limit','review_limit','budget_changes','resource_policy','resource_adoptions'):a.pop(key,None)
 for r in a['runs'].values():
  r['reported_usage']=r.pop('observed_usage',r.get('reported_usage'))
  for key in ('reserve','charged','measurement','packet'):r.pop(key,None)
 for r in a.get('controls',{}).values():
  old_usage=r.get('usage');r['reported_usage']=r.get('reported_usage',old_usage if type(old_usage)is int and old_usage>0 else None)
  if r.get('packet_reserve'):r.setdefault('requested',{}).update(kind='turn',receipt_only=True)
  for key in ('packet_reserve','charged','measurement'):r.pop(key,None)
  r.get('requested',{}).pop('packet_reserve',None)
 for record in a.get('diagnostics',{}).values():record['original_task_sha256']=h.digest(record['original_task'])
 a.update(schema=2,policy_hash=h.digest(h.effective_contract()),revision=a['revision']+1)
 for p in a['profiles'].values():p.pop('ack',None)
 return s

def approvals(s,e):
 import harness as h
 proof=h.ledger.evidence(e['approvals']);data=Path(e['approvals']).read_bytes();h.require(hashlib.sha256(data).hexdigest()==proof['sha256'],'Approval changed during capture');value=json.loads(data);members=[]
 for role in ('leader','reviewer'):
  x=value[role];m=x['member'];h.require(m in s['members']and s['members'][m]['role']==role and h.ledger.fresh(s['members'][m]['identity_claim']),'Fresh approval role/identity required')
  h.require(x.get('request_sha256')==h.digest({k:v for k,v in e.items()if k!='approvals'})and all(x.get(k)is True for k in ('approved','safe_boundary','all_current_obligations_retained')),'Exact scoped independent approval required');members.append(m)
 h.require(members[0]==e['requester']and members[0]!=members[1]and s['members'][members[0]]['runtime_id_claim']!=s['members'][members[1]]['runtime_id_claim'],'Independent leader/reviewer required')
 return {'proof':proof,'bytes_base64':base64.b64encode(data).decode()}

def apply(s,e,root,raw):
 import harness as h,checkpoints
 h.require(raw is not None and h.digest(json.loads(raw))==h.digest(s),'Exact original state bytes required')
 h.require(root is not None and Path(e['project_root']).is_absolute()and Path(e['project_root']).resolve()==Path(root).resolve(),'Exact canonical state directory required')
 h.require(e['source_sha256']==h.digest(s)and e['source_raw_sha256']==hashlib.sha256(raw).hexdigest()and e['project']==s['harness']['goal'],'Stale parsed/raw project CAS')
 h.require(e['policy_hash']==h.digest(h.effective_contract())and bool(e.get('reason'))and isinstance(e.get('request_id'),str)and bool(e['request_id'].strip()),'Exact target, reason and stable ID required')
 checkpoints.quiescent(s);review=approvals(s,e);result=project(raw);a=result['harness']
 a.setdefault('legacy_archives',{})[e['request_id']]={'event_digest':h.digest(e),'event':copy.deepcopy(e),'source_sha256':h.digest(s),'source_raw_sha256':hashlib.sha256(raw).hexdigest(),'source_bytes_base64':base64.b64encode(raw).decode(),'review':review,'meaning':'Historical original bytes only; never active limits','revision':a['revision']}
 a['changes'].append({'revision':a['revision'],'contract_migration':e['request_id'],'reason':e['reason']});return result

def verify(s):
 import harness as h
 try:
  for record in s['harness'].get('legacy_archives',{}).values():
   raw=base64.b64decode(record['source_bytes_base64'],validate=True);event=record['event'];review=record['review'];data=base64.b64decode(review['bytes_base64'],validate=True)
   h.require(hashlib.sha256(raw).hexdigest()==record['source_raw_sha256']==event['source_raw_sha256']and h.digest(json.loads(raw))==record['source_sha256']==event['source_sha256']and h.digest(event)==record['event_digest'],'Historical source bytes/binding changed')
   h.require(hashlib.sha256(data).hexdigest()==review['proof']['sha256'],'Historical review evidence changed')
 except (KeyError,ValueError,TypeError)as exc:raise h.Invalid('Invalid historical archive: '+str(exc))from exc
