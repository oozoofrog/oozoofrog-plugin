"""Exact management ownership baseline and locked handoff consistency guard.

The digest detects accidental/out-of-band changes; it is not authentication
against an actor able to rewrite both canonical state and its commitment.
"""
import copy,json,stat
from pathlib import Path
import harness as h
import external_handoff as external

def encoded(state):return (json.dumps(state,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
def records(state):
 active=[]
 for key,value in state['harness'].get('handoffs',{}).items():
  reference=value.get('packet',{}).get('canonical_context',{}).get('history_reference');directory=Path(reference).parent if reference else None
  required=directory is not None and directory.name=='.codex-team'and str(directory)in value['packet'].get('baseline',{})
  m=value.get('management');h.require(not required or bool(m),'Required management guard metadata removed')
  if not m:continue
  if m.get('completed'):
   closure=m.get('completion',{});index=closure.get('history_index');history=state['history']
   h.require(value['state']=='resumed'and value.get('owner_ack')and type(index)is int and 0<=index<len(history),'Management guard retirement requires completed ownership and context ACK')
   event=history[index]['event']
   h.require(event['op']=='ack'and event.get('member')==value['recipient']and event.get('revision')==value['transfer_revision']and h.digest(event)==closure.get('event_digest')and h.digest(history[:index+1])==closure.get('history_sha256'),'Management guard retirement ACK/history changed')
   h.require(any(entry['event'].get('op')=='control_resume'and entry['event'].get('handoff')==key for entry in history[:index]),'Management guard retired before actual resume')
  else:active.append((key,value))
 return active
def commitment(state):
 value=copy.deepcopy(state)
 for handoff in value['harness'].get('handoffs',{}).values():
  if handoff.get('management'):handoff['management'].pop('state_commitment',None)
 return h.digest(value)
def prepare(paths,files,state_path):
 if state_path is None:return None
 path=Path(state_path);directory=path.parent
 if str(directory)not in paths:return None
 h.require(directory.name=='.codex-team','Only exact canonical .codex-team state directory is management ownership')
 root=copy.deepcopy(files[str(directory)]);entry=root['entries'].get(path.name)
 h.require(entry and entry['kind']=='file','Exact canonical state file required')
 root['entries'][path.name]={'kind':'canonical_state','expected_mode':0o600,'initial_sha256':entry['sha256'],'initial_mode':entry['mode']}
 return {'state_path':str(path),'directory':str(directory),'expected_tree':root,'state_commitment':None,'completed':False,'scope':'Locked canonical transition consistency; no OS authentication or recipient write permission'}
def tree(record,path,initial=False):
 m=record['management'];directory=m['directory'];current=external.baseline([directory],management_dir=directory)[directory];entry=current['entries'].get(path.name)
 h.require(entry and entry['kind']=='file','Management state type changed')
 expected=m['expected_tree']['entries'][path.name]
 h.require(entry['mode']==(expected['initial_mode']if initial else expected['expected_mode']),'Management state mode changed')
 current['entries'][path.name]=copy.deepcopy(expected)
 return current

def candidate(record,event,path):
 """Only the existing validating phase may introduce one exact evidence file."""
 if event.get('handoff')!=path[0]:return None
 if event['op']=='control_transfer'and record['state']=='packet_received':return event.get('external_observation')
 if event['op']=='control_owner_ack'and record['state']=='transferred':return event.get('evidence')
 return None

def check_files(key,record,events,path,initial=False):
 m=record['management'];actual=tree(record,path,initial);expected=copy.deepcopy(m['expected_tree']);added=[]
 for event in events:
  raw=candidate(record,event,(key,path))
  if not raw:continue
  evidence=external.canonical(raw,allow_evidence=True)
  if not evidence.is_relative_to(Path(m['directory'])):continue
  relative=evidence.relative_to(m['directory']).as_posix()
  h.require(relative not in expected['entries'],'New management evidence cannot overwrite a retained file')
  entry=actual['entries'].get(relative);h.require(entry and entry['kind']=='file','Exact regular management evidence required');expected['entries'][relative]=entry;added.append((event,relative))
 h.require(actual==expected,'Unapproved management file/type/mode/addition/deletion change')
 return actual,added

def products(record):
 product={name:value for name,value in record['packet']['baseline'].items()if name!=record['management']['directory']}
 h.require(external.baseline(product)==product,'Product baseline changed during handoff')

def before(state,events,path,raw):
 for key,record in records(state):
  m=record['management'];h.require(m['state_path']==str(path),'Canonical management state path changed')
  h.require(raw==encoded(state),'Canonical state bytes changed outside a locked transition')
  h.require(m.get('state_commitment')==commitment(state),'Canonical state/history commitment changed; never reseed from current files')
  check_files(key,record,events,path)
  products(record)

def finish(previous,state,events,path,raw):
 active=records(state)
 if not active:return state
 h.require(external.inventory(str(path),allow_evidence=True,read_file=True)[1]==raw,'Canonical state changed during locked transition; CAS refused')
 for key,record in active:
  products(record)
  m=record['management'];old=previous['harness'].get('handoffs',{}).get(key);initial=not old or not old.get('management')
  actual,added=check_files(key,old if not initial else record,events,path,initial)
  for event,relative in added:
   proof=record.get('transfer_source_observation')if event['op']=='control_transfer'else record.get('owner_ack')
   h.require(proof and proof['path']==str(Path(m['directory'])/relative)and external.inventory(proof['path'],allow_evidence=True)['sha256']==proof['sha256']==actual['entries'][relative]['sha256'],'Management evidence was not validated by its canonical phase')
  m['expected_tree']=actual
  m['last_transition']={'prior_commitment':old['management']['state_commitment']if not initial else h.digest(json.loads(raw)),'event_digests':[h.digest(e)for e in events],'history_start':len(previous['history']),'history_end':len(state['history'])}
  if record['state']=='resumed'and any(e['op']=='ack'and e.get('member')==record['recipient']for e in events):
   index=len(state['history'])-1;m['completed']=True;m['completion']={'history_index':index,'event_digest':h.digest(state['history'][index]['event']),'history_sha256':h.digest(state['history'])}
 value=commitment(state)
 for _,record in active:record['management']['state_commitment']=value
 return state
