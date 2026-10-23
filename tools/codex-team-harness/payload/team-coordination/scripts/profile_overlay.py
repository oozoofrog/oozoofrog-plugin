"""Guarded requested-default instructions; does not change runtime contracts."""
import argparse,base64,contextlib,fcntl,hashlib,json,os,stat,tempfile
from pathlib import Path
class OverlayError(ValueError):pass
JOURNAL='team-coordination-profile-defaults-install.json'
PROFILE='team-coordination-desired-profiles.json'
LEGACY='team-coordination-install.json'
BEGIN='<!-- team-coordination:desired-profile:v1:begin -->'
BLOCK='\n<!-- team-coordination:desired-profile:v1:begin -->\nRequested defaults for every existing and future project: leader/design/advisor use gpt-6-astra with reasoning high; core/reviewer use gpt-6.1-sol with reasoning high; support uses gpt-6-luna with reasoning medium. Every role requests service mode Normal. Model, reasoning effort, and service mode are separate fields. Choose supported reasoning effort to fit task difficulty; do not automatically restore ultra or Fast defaults. Read team-coordination-desired-profiles.json beside this global AGENTS.md under CODEX_HOME (normally ~/.codex), not in the project directory. Normal is the human-requested mode; no native tier mapping or configured/runtime state is verified through the current app MCP. Only apply a wire value through a supported official control with observed mapping; never inject unsupported service-tier arguments. Existing project contracts require explicit safe owner adoption; do not restart completed work. These instructions request defaults and do not prove session configuration or runtime identity.\n<!-- team-coordination:desired-profile:v1:end -->\n'.encode()
def raw(path):
 if path.is_symlink():raise OverlayError('symlink refused: '+path.name)
 if not path.exists():return None
 s=path.stat()
 if not stat.S_ISREG(s.st_mode) or s.st_nlink!=1:raise OverlayError('nonregular or hard-linked file refused: '+path.name)
 return path.read_bytes()
def sha(data):return hashlib.sha256(data).hexdigest() if data is not None else None
def encode(data):return base64.b64encode(data).decode() if data is not None else None
def decode(data):return base64.b64decode(data,validate=True) if data is not None else None
def packed(value):return (json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()
def homepath(home):
 p=Path(home).absolute()
 if p.is_symlink() or p.resolve()!=p or not p.is_dir():raise OverlayError('home must be a canonical existing directory')
 return p
@contextlib.contextmanager
def locked(home):
 p=home/'.team-coordination-profile-defaults.lock'
 if p.is_symlink() or (p.exists() and p.stat().st_nlink!=1):raise OverlayError('unsafe lock')
 fd=os.open(str(p),os.O_CREAT|os.O_RDWR|getattr(os,'O_NOFOLLOW',0),0o600)
 try:
  fcntl.flock(fd,fcntl.LOCK_EX);yield
 finally:os.close(fd)
def write(path,data):
 if data is None:path.unlink();return
 fd,name=tempfile.mkstemp(prefix='.profile-',dir=str(path.parent))
 try:
  with os.fdopen(fd,'wb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
  os.replace(name,str(path))
 finally:
  if os.path.exists(name):os.unlink(name)
def validate(payload):
 if payload.get('requested_scope')!='all_existing_and_future_projects' or payload.get('schema')!=1 or payload.get('execution_authorized') is not False or payload.get('adoption')!='pending_explicit_owner_safe_boundary':raise OverlayError('requested-only profile required')
 expected={role:{'model':model,'reasoning_effort':effort,'service_tier':'normal'}for role,model,effort in [('leader','gpt-6-astra','high'),('advisor','gpt-6-astra','high'),('core','gpt-6.1-sol','high'),('reviewer','gpt-6.1-sol','high'),('support','gpt-6-luna','medium')]}
 if payload.get('roles')!=expected:raise OverlayError('Normal defaults require exact separate model, reasoning and service fields for every role')
def state(home):
 data=raw(home/JOURNAL)
 return validate_journal(json.loads(data)) if data else None
def validate_journal(value):
 if not isinstance(value,dict)or value.get('schema')!=1 or not isinstance(value.get('changes'),list)or len(value['changes'])!=2:raise OverlayError('Unknown overlay journal schema')
 if [c.get('path')for c in value['changes']]!=['AGENTS.md',PROFILE]:raise OverlayError('Journal must contain only exact ordered overlay targets')
 for c in value['changes']:
  for side in ('before','after'):
   try:data=decode(c[side])
   except (KeyError,ValueError,TypeError)as exc:raise OverlayError('Invalid journal endpoint')from exc
   if sha(data)!=c.get(side+'_sha256'):raise OverlayError('Journal endpoint hash mismatch')
 if not isinstance(value.get('legacy_sha256'),(str,type(None))):raise OverlayError('Invalid legacy journal pin')
 return value
def check(home,journal,after=True):
 validate_journal(journal)
 if sha(raw(home/LEGACY))!=journal['legacy_sha256']:raise OverlayError('legacy journal changed')
 for change in journal['changes']:
  current=raw(home/change['path']);expected=decode(change['after' if after else 'before'])
  if current!=expected:raise OverlayError('concurrent or incomplete edit: '+change['path'])
def plan(home,payload):
 home=homepath(home);validate(payload);existing=state(home)
 if existing:
  check(home,existing)
  if decode(existing['changes'][1]['after'])!=packed(payload):raise OverlayError('different overlay already installed')
  return {'changes':[],'changed':0}
 before=raw(home/'AGENTS.md')
 if before is None:before=b''
 if BEGIN.encode() in before or raw(home/PROFILE) is not None:raise OverlayError('unmanaged overlay exists')
 changes=[]
 for name,old,new in [('AGENTS.md',raw(home/'AGENTS.md'),before+BLOCK),(PROFILE,None,packed(payload))]:changes.append({'path':name,'before':encode(old),'after':encode(new),'before_sha256':sha(old),'after_sha256':sha(new)})
 return {'schema':1,'legacy_sha256':sha(raw(home/LEGACY)),'changes':changes,'changed':2}
def apply(home,payload):
 home=homepath(home)
 with locked(home):
  proposal=plan(home,payload)
  if not proposal['changes']:return {'changed':0}
  check(home,proposal,False);write(home/JOURNAL,packed(proposal))
  for change in proposal['changes']:
   if raw(home/change['path'])!=decode(change['before']):raise OverlayError('concurrent edit before write')
   write(home/change['path'],decode(change['after']))
  check(home,proposal);return {'changed':2,'instruction_defaults_installed':True,'per_session_configured':False}
def doctor(home):
 home=homepath(home)
 with locked(home):
  journal=state(home)
  if not journal:raise OverlayError('overlay not installed')
  check(home,journal);return {'integrity_ok':True,'instruction_defaults_installed':True,'per_session_configured':False}
def rollback(home):
 home=homepath(home)
 with locked(home):
  journal=state(home)
  if not journal:raise OverlayError('overlay not installed')
  # Validate the entire transaction before restoring anything. A partial apply
  # is recoverable only when each file equals one of its pinned endpoints.
  if sha(raw(home/LEGACY))!=journal['legacy_sha256']:raise OverlayError('legacy journal changed')
  for c in journal['changes']:
   if raw(home/c['path']) not in (decode(c['before']),decode(c['after'])):raise OverlayError('concurrent edit: '+c['path'])
  for c in reversed(journal['changes']):
   if raw(home/c['path'])!=decode(c['before']):write(home/c['path'],decode(c['before']))
  check(home,journal,False);(home/JOURNAL).unlink();return {'changed':len(journal['changes'])}
def main():
 p=argparse.ArgumentParser();p.add_argument('--codex-home',required=True);p.add_argument('--profile');p.add_argument('command',choices=['plan','apply','doctor','rollback']);a=p.parse_args()
 try:
  if a.command in ('plan','apply'):
   if not a.profile:raise OverlayError('--profile required')
   result=globals()[a.command](a.codex_home,json.loads(Path(a.profile).read_text()))
   if a.command=='plan':result={'changed':result['changed'],'changes':[{k:v for k,v in c.items() if k not in ('before','after')} for c in result['changes']]}
  else:result=globals()[a.command](a.codex_home)
  print(json.dumps(result,sort_keys=True))
 except (OverlayError,ValueError,OSError) as e:p.exit(2,str(e)+'\n')
if __name__=='__main__':main()
