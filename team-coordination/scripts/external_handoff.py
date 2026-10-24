"""Explicit external provenance and bounded filesystem handoff helpers.

Supported-tool evidence is an operator attestation, never native runtime identity
or an OS lock. No private session store or authentication data is inspected.
"""
import contextlib,hashlib,json,os,stat
from pathlib import Path
import harness as h

PRIVATE={'.git','.aws','.ssh','.codex','.codex-team'}
def canonical(raw,allow_evidence=False):
 p=Path(raw)
 h.require(p.is_absolute()and os.path.normpath(str(p))==str(p),'Canonical non-symlink path required')
 h.require(not any(part in (PRIVATE-({'.codex-team'}if allow_evidence else set()))for part in p.parts),'Private metadata path refused')
 for item in reversed([p,*p.parents]):h.require(not item.is_symlink(),'Symlink ancestor refused')
 return p

def fingerprint(value):
 return (value.st_dev,value.st_ino,value.st_mode,value.st_size,value.st_mtime_ns,value.st_ctime_ns)

@contextlib.contextmanager
def parent_fd(path):
 """Anchor every ancestor without resolving/following an alias."""
 descriptors=[];anchors=[]
 try:
  descriptor=os.open('/',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW);descriptors.append(descriptor)
  for name in path.parts[1:-1]:
   before=os.stat(name,dir_fd=descriptor,follow_symlinks=False)
   h.require(stat.S_ISDIR(before.st_mode),'Symlink/non-directory ancestor refused')
   child=os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=descriptor);descriptors.append(child)
   h.require((before.st_dev,before.st_ino,before.st_mode)==(os.fstat(child).st_dev,os.fstat(child).st_ino,os.fstat(child).st_mode),'Ancestor changed during inventory')
   anchors.append((descriptor,name,child));descriptor=child
  yield descriptor,path.name if path.name else '.'
  for parent,name,child in anchors:
   value=os.stat(name,dir_fd=parent,follow_symlinks=False);opened=os.fstat(child)
   h.require((value.st_dev,value.st_ino,value.st_mode)==(opened.st_dev,opened.st_ino,opened.st_mode),'Ancestor changed during inventory')
 finally:
  for descriptor in reversed(descriptors):os.close(descriptor)

def inventory(path,allow_evidence=False,read_file=False,after_ns=None):
 p=canonical(path,allow_evidence);entries={};content=[]
 def item(parent,name,logical,root=False):
  before=os.stat(name,dir_fd=parent,follow_symlinks=False);mode=before.st_mode
  if root and read_file:
   h.require(stat.S_ISREG(mode),'Evidence must be a regular non-symlink file')
   if after_ns is not None:h.require(before.st_mtime_ns>=after_ns,'Refresh evidence after the required phase boundary')
  if stat.S_ISLNK(mode):
   h.require(not root,'Symlink claim root refused');target=os.readlink(name,dir_fd=parent)
   destination=Path(os.path.normpath(os.path.join(str(logical.parent),target)))
   h.require(destination==p or p in destination.parents,'Symlink target escape from original claim refused')
   h.require(not any(part in PRIVATE for part in destination.relative_to(p).parts),'Private metadata link target refused')
   value={'kind':'symlink','mode':stat.S_IMODE(mode),'target':target,'identity':{'device':before.st_dev,'inode':before.st_ino,'ctime_ns':before.st_ctime_ns}}
  else:
   h.require(stat.S_ISREG(mode)or stat.S_ISDIR(mode),'Special ownership file refused')
   flags=os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|(os.O_DIRECTORY if stat.S_ISDIR(mode)else 0)
   descriptor=os.open(name,flags,dir_fd=parent)
   try:
    h.require(fingerprint(before)==fingerprint(os.fstat(descriptor)),'Entry changed before inventory read')
    value={'kind':'directory'if stat.S_ISDIR(mode)else 'file','mode':stat.S_IMODE(mode)}
    if stat.S_ISREG(mode):
     digest=hashlib.sha256()
     while True:
      block=os.read(descriptor,1024*1024)
      if not block:break
      digest.update(block)
      if read_file and root:content.append(block)
     value['sha256']=digest.hexdigest()
    else:
     children=sorted(os.listdir(descriptor))
     for child in children:
      h.require(child not in PRIVATE,'Private metadata in ownership tree refused')
      logical_child=logical/child;entry=item(descriptor,child,logical_child)
      entries[logical_child.relative_to(p).as_posix()]=entry
     h.require(children==sorted(os.listdir(descriptor)),'Directory entries changed during inventory')
    h.require(fingerprint(before)==fingerprint(os.fstat(descriptor)),'Entry changed during inventory read')
   finally:os.close(descriptor)
  h.require(fingerprint(before)==fingerprint(os.stat(name,dir_fd=parent,follow_symlinks=False)),'Entry changed during inventory')
  return value
 try:
  with parent_fd(p)as(parent,name):record=item(parent,name,p,True)
 except FileNotFoundError:
  raise h.Invalid('Ownership entry/ancestor disappeared during inventory')
 if record['kind']=='directory':record['entries']=dict(sorted(entries.items()))
 return (record,b''.join(content))if read_file else record

def baseline(paths,management_dir=None):
 result={}
 for raw in paths:
  p=canonical(raw,allow_evidence=raw==management_dir)
  # Missing roots retain existing semantics; the descriptor walker validates all
  # existing ancestors and distinguishes a disappearance during traversal.
  if not os.path.lexists(p):
   try:
    with parent_fd(p)as(parent,name):
     try:os.stat(name,dir_fd=parent,follow_symlinks=False)
     except FileNotFoundError:result[str(p)]={'kind':'missing'};continue
   except FileNotFoundError:result[str(p)]={'kind':'missing'};continue
  result[str(p)]=inventory(str(p),allow_evidence=raw==management_dir)
 return result

def preflight(paths,state_path=None):
 """Pure baseline/management compatibility check: no locks, records or RPC."""
 paths=list(paths);directory=str(Path(state_path).parent)if state_path else None
 files={};failures=[];types={name:0 for name in ('file','directory','symlink','missing')}
 for raw in paths:
  try:
   record=baseline([raw],management_dir=directory)[str(raw)];files[str(raw)]=record
   for value in [record,*record.get('entries',{}).values()]:types[value['kind']]+=1
  except (OSError,h.Invalid)as error:failures.append({'path':str(raw),'reason':str(error)})
 prepared=False
 if directory in files:
  import management_handoff
  try:prepared=management_handoff.prepare(paths,files,state_path)is not None
  except (OSError,h.Invalid,KeyError)as error:failures.append({'path':directory,'reason':str(error)})
 return {'ok':not failures,'claims':len(paths),'types':types,'failures':failures,'management_guard_prepared':prepared,'baseline_sha256':h.digest(files),'link_semantics':'literal metadata only; no target resolution, target read or traversal; lexical containment is not target existence or effective resolution','write_authority_granted':False}

def proof(path,after_ns=None):
 p=canonical(path,allow_evidence=True);entry,data=inventory(str(p),allow_evidence=True,read_file=True,after_ns=after_ns)
 h.require(entry['kind']=='file','Evidence must be a regular file')
 return {'path':str(p),'sha256':entry['sha256'],'captured_at':h.ledger.now()},json.loads(data)

def fresh(value):
 try:return inventory(value['path'],allow_evidence=True,read_file=True)[0]['sha256']==value['sha256']
 except (OSError,h.Invalid,KeyError):return False

def external_observation(path,identity,stopped_turn=None,after_ns=None):
 evidence,value=proof(path,after_ns=after_ns)
 h.require(value.get('source_identity')==identity,'External observation exact identity mismatch')
 h.require(value.get('tool')=='codex_app.read_thread','Supported source observation required')
 h.require(value.get('status')=='idle'and value.get('turn_status')=='completed'and isinstance(value.get('turn'),str)and value['turn'],'Actual idle/completed source observation required; unavailable is not stopped')
 if stopped_turn is not None:h.require(value['turn']==stopped_turn,'Source turn changed since owner stop ACK')
 return evidence,value

def external_source(spec,checkpoint,revision,ceiling):
 identity=spec.get('identity',{})
 h.require(all(isinstance(identity.get(k),str)and identity[k]for k in ('host','transport','controller','thread'))and identity.get('owned')is False,'Exact external source identity required')
 evidence,value=external_observation(spec['observation'],identity)
 stop_proof,stop=proof(checkpoint)
 h.require(stop.get('source_identity')==identity and stop.get('commands_drained')is True and stop.get('execution_stopped')is True,'Actual external owner stopped/drained attestation required')
 h.require(stop.get('stopped_turn')==value['turn']and stop.get('observation_sha256')==evidence['sha256'],'Stop ACK must bind exact supported observation and stopped turn')
 quote=stop.get('owner_ack_quote');h.require(isinstance(quote,str)and bool(quote.strip())and quote in value.get('final_text',''),'Actual source owner stop ACK quote from supported final evidence required; idle is not a stop ACK')
 h.require(stop.get('project_revision')==revision,'Stop ACK project revision changed')
 h.require(stop.get('permission_ceiling')==ceiling,'Original owner permission ceiling must be preserved')
 return {'scope':'operator_attestation_with_supported_tool_evidence','identity':identity,'observation':evidence,'stopped_turn':value['turn'],'owner_ack_quote':quote,'checkpoint':stop_proof,'configured_model':'unknown','provider_execution':'unavailable'}

def ceiling(value,paths,state_path=None):
 if value=={'sandbox':'read-only','publication':False}:return value
 expected={'sandbox','publication','writable_roots','network_access','approval_policy','approvals_reviewer'}
 h.require(set(value)==expected and value['sandbox']=='workspace-write'and value['publication']is False and value['network_access']is False and value['approval_policy']=='on-request'and value['approvals_reviewer']=='auto_review','Exact bounded workspace-write/no-publication/normal-review ceiling required')
 roots=value['writable_roots'];h.require(isinstance(roots,list)and bool(roots)and len(set(roots))==len(roots),'Explicit unique writable roots required')
 for raw in roots:
  p=canonical(raw);h.require(raw in paths,'Writable root must equal an original transferred claim; no parent expansion')
  if state_path:h.require(not canonical(str(state_path),allow_evidence=True).is_relative_to(p),'Write ceiling cannot include canonical project state')
 baseline(roots)
 return value

def sandbox(value):
 if value['sandbox']=='read-only':return {'type':'readOnly','networkAccess':False}
 return {'type':'workspaceWrite','writableRoots':value['writable_roots'],'networkAccess':False,'excludeSlashTmp':True,'excludeTmpdirEnvVar':True}

def creation(value,cwd):
 p=canonical(cwd)
 if value['sandbox']=='read-only':return {'cwd':str(p),'sandbox':'read-only','approvalPolicy':'never'}
 h.require(str(p)in value['writable_roots']and p.is_dir(),'Implicit writable cwd must equal an approved directory claim')
 return {'cwd':str(p),'sandbox':'workspace-write','approvalPolicy':'on-request','approvalsReviewer':'auto_review','config':{'sandbox_workspace_write':{'writable_roots':value['writable_roots'],'network_access':False,'exclude_slash_tmp':True,'exclude_tmpdir_env_var':True}}}

def verify_creation(response,value,cwd):
 if value['sandbox']=='read-only':return
 observed=response.get('sandbox',{});expected=sandbox(value)
 h.require(response.get('cwd')==cwd and 'writableRoots'in observed and isinstance(observed['writableRoots'],list),'Explicit official cwd and root list required')
 for root in observed['writableRoots']:canonical(root)
 actual_roots=set(observed['writableRoots'])|{cwd};desired_roots=set(value['writable_roots'])
 h.require(actual_roots==desired_roots and {k:v for k,v in observed.items()if k!='writableRoots'}=={k:v for k,v in expected.items()if k!='writableRoots'}and response.get('approvalPolicy')=='on-request'and response.get('approvalsReviewer')=='auto_review','Official sandbox/cwd/approval readback differs from exact approved ceiling')
