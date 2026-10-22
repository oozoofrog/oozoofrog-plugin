#!/usr/bin/env python3
"""Managed-run gates layered on the existing team ledger; no OS interception."""
import argparse,copy,fcntl,hashlib,json,math,os,sys,tempfile
from pathlib import Path
import team_ledger as ledger
Invalid,require=ledger.Invalid,ledger.require
POLICY=json.loads((Path(__file__).resolve().parents[1]/'policy.json').read_text())
MODELS={role:item['model'] for role,item in POLICY['roles'].items()}
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
def effective_contract():
 root=Path(__file__).resolve().parents[1]
 return {'policy':json.loads((root/'policy.json').read_text()),'roles':{p.stem:p.read_text()for p in sorted((root/'roles').glob('*.md'))},'schema':json.loads((root/'schema/project-state.schema.json').read_text()),'implementation_sha256':{name:hashlib.sha256((root/'scripts'/name).read_bytes()).hexdigest()for name in ('harness.py','managed_run.py','team_ledger.py')}}

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
 require(math.ceil(len(json.dumps(result,ensure_ascii=False).encode())/4)<=h['context_limit'],'Context estimate exceeds limit; leader must reduce irrelevant context, preserve decisions')
 return result

def ack_current(s,member):
 p=s['harness']['profiles'][member];a=p.get('ack')
 require(s['harness']['policy_hash']==digest(effective_contract()),'Policy changed; leader must migrate project policy and refresh ACKs')
 require(a is not None and a=={'revision':s['harness']['revision'],'epoch':p['epoch'],'digest':digest(packet(s,member))},'Latest context acknowledgement required')

def apply(state,e):
 s=copy.deepcopy(state);h=s['harness'];op=e['op']
 if op=='register':
  m=e['member'];role=e['role'];require(m not in s['members'] and role in MODELS,'Duplicate member or unknown role')
  # Identity is a file-backed claim. Only adapter runtime receipt is observed transport data.
  s['members'][m]={'role':role,'identity_claim':ledger.evidence(e['identity']),'runtime_id_claim':e.get('runtime_id',m)}
  h['profiles'][m]={'role':role,'epoch':0,'model':effective_contract()['policy']['roles'][role]['model'],'last_revision':0}
 elif op=='assign':
  require(e['task'] not in s['tasks'],'Duplicate task')
  require(e['member'] in s['members'] and s['members'][e['member']]['role'] not in ('leader','reviewer'),'Execution owner required')
  s['tasks'][e['task']]={'owner':e['member'],'purpose':e['purpose'],'context':e['context'],'state':'assigned','paths':[],'resources':[],'reviews':[]}
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
  h['budget']=min(h['budget'],limits['project_token_budget']);h['concurrency']=limits['concurrency'];h['context_limit']=limits['context_estimate_limit'];h['review_limit']=limits['review_passes']
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
  require(t['owner']==m and t['state'] in ('assigned','running'),'Wrong task owner/state')
  require(ledger.fresh(s['members'][m]['identity_claim']),'Stale identity claim')
  require(p['role'] not in ('leader','reviewer') and p['model'] is not None,'Requested role model unresolved or nonexecuting role')
  ack_current(s,m);require(t['paths'],'Write ownership required')
  require(e['run'] not in h['runs'],'Duplicate run id')
  require(not any(r['state']=='uncertain' for r in h['runs'].values()),'Uncertain run must be reconciled')
  active=[r for r in h['runs'].values() if r['state']=='active']
  require(len(active)<h['concurrency'],'Concurrency exhausted')
  require(not any(r['task']==e['task'] for r in active),'Task already executing')
  reserve=e['reserve'];require(type(reserve)is int and reserve>0,'Positive integer reservation required')
  require(h['spent']+sum(r['reserve'] for r in active)+reserve<=h['budget'],'Budget exhausted')
  h['runs'][e['run']]={'task':e['task'],'member':m,'model':p['model'],'revision':h['revision'],'epoch':p['epoch'],'state':'active','reserve':reserve,'stale':False,'phase':'reserved','observed':{},'packet':packet(s,m)}
  t['state']='running'
 elif op=='observe':
  r=h['runs'][e['run']];require(r['state']=='active','Run not active');r['observed'].update(e['receipt']);r['phase']=e['phase']
 elif op=='finish':
  r=h['runs'][e['run']];require(r['state']=='active','Run already terminal');out=e['outcome'];require(out in ('completed','failed','uncertain','not_executed'),'Invalid outcome')
  require(bool(e['evidence']),'Outcome evidence required');r['state']=out;r['evidence']=e['evidence']
  if out!='uncertain':
   used=e.get('usage',0 if out=='not_executed' else r['reserve']);require(type(used)is int and used>=0,'Invalid usage')
   r['observed_usage']=e.get('usage');charged=0 if out=='not_executed'else max(r['reserve'],used)
   r['charged']=charged;r['measurement']='reported_provisional_reservation_retained' if 'usage'in e else ('none_started' if out=='not_executed' else 'reserved_missing_usage');h['spent']+=charged
  p=h['profiles'][r['member']];p['last_revision']=r['revision'];p.pop('ack',None)
 elif op=='mark_uncertain':
  r=h['runs'][e['run']];require(r['state']=='active' and bool(e.get('evidence')),'Observed orphan evidence required')
  r['state']='uncertain';r['evidence']=e['evidence'];h['profiles'][r['member']].pop('ack',None)
 elif op=='reconcile':
  r=h['runs'][e['run']];require(r['state']=='uncertain','Only uncertain outcome needs reconcile')
  require(e['outcome'] in ('not_executed','completed','failed') and bool(e['evidence']),'Observed terminal outcome required')
  r['state']=e['outcome'];r['evidence']=e['evidence'];r['charged']=0 if r['state']=='not_executed' else r['reserve'];h['spent']+=r['charged']
 elif op=='release':
  t=s['tasks'][e['task']]
  require(e.get('safe_boundary')is True,'Confirmed safe boundary required')
  require(not any(r['task']==e['task'] and r['state']in ('active','uncertain')for r in h['runs'].values()),'Run still unresolved')
  t['paths']=[];t['resources']=[]
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
 s['history'].append({'at':ledger.now(),'event':e})
 return s

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
  fcntl.flock(lock,fcntl.LOCK_EX);s=json.loads(path.read_text());s=apply(s,event);save(path,s);return s

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state',type=Path,required=True)
 sub=p.add_subparsers(dest='command',required=True)
 i=sub.add_parser('init');i.add_argument('--goal',required=True);i.add_argument('--budget',type=int)
 a=sub.add_parser('apply');a.add_argument('--event',type=Path,required=True)
 q=sub.add_parser('packet');q.add_argument('--member',required=True);sub.add_parser('status')
 args=p.parse_args()
 if args.command=='init':initialize(args.state,args.goal,args.budget)
 elif args.command=='apply':transaction(args.state,json.loads(args.event.read_text()))
 elif args.command=='packet':print(json.dumps(packet(json.loads(args.state.read_text()),args.member),ensure_ascii=False,indent=2))
 else:
  s=json.loads(args.state.read_text());h=s['harness'];print(json.dumps({'revision':h['revision'],'budget':h['budget'],'spent':h['spent'],'members':h['profiles'],'tasks':s['tasks'],'runs':h['runs'],'limits':'Managed boundary only; identities claimed unless receipt observed'},ensure_ascii=False,indent=2))
if __name__=='__main__':
 try:main()
 except (Invalid,KeyError,OSError,ValueError)as e:print(json.dumps({'error':str(e)}));sys.exit(2)
