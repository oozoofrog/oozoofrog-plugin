#!/usr/bin/env python3
"""Portable plan-bound installer. Standard library only; no network or privilege changes."""
import argparse,base64,hashlib,json,os,sys,tempfile
from pathlib import Path,PurePosixPath
VERSION='0.5.5'
def check(value,message):
 if not value:raise ValueError(message)
def sha(data):return hashlib.sha256(data).hexdigest()
def safe(root,relative):
 name=PurePosixPath(relative);check(not name.is_absolute()and '..'not in name.parts and name.parts and '\\'not in relative,'Unsafe relative path')
 root=Path(root);target=root.joinpath(*name.parts)
 for item in [target,*target.parents]:
  if item==root.parent:break
  check(not item.is_symlink(),'Symlink refused')
 check(target.resolve().is_relative_to(root.resolve()),'Path escapes target');return target

def verify(bundle):
 manifest=json.loads(safe(bundle,'manifest.json').read_text());check(manifest['version']==VERSION,'Wrong release version')
 for relative,expected in manifest['files'].items():
  path=safe(bundle,relative);check(path.is_file()and sha(path.read_bytes())==expected,'Release integrity failed: '+relative)
 return manifest

def atomic(path,data):
 path.parent.mkdir(parents=True,exist_ok=True);fd,temporary=tempfile.mkstemp(dir=path.parent,prefix='.harness-')
 try:
  with os.fdopen(fd,'wb')as file:file.write(data);file.flush();os.fsync(file.fileno())
  os.replace(temporary,path)
 finally:
  if os.path.exists(temporary):os.unlink(temporary)

def desired(bundle,home,manifest):
 import re
 targets={}
 for relative in manifest['files']:
  if relative.startswith('payload/team-coordination/'):
   targets['skills/'+relative.removeprefix('payload/')]=safe(bundle,relative).read_bytes()
 path=safe(home,'AGENTS.md');before=path.read_bytes()if path.exists()else b''
 block=safe(bundle,'global-block.md').read_bytes().rstrip(b'\n')
 pattern=rb'<!-- team-coordination:v[0-9]+:begin -->.*?<!-- team-coordination:v[0-9]+:end -->'
 matches=list(re.finditer(pattern,before,re.S));check(len(matches)<=1,'Ambiguous managed blocks')
 targets['AGENTS.md']=re.sub(pattern,lambda _:block,before,flags=re.S)if matches else before+(b'\n'if before else b'')+block+b'\n'
 return targets

def inspect(bundle,home):
 check(home.is_absolute(),'Use an explicit absolute Codex home');check(not home.is_symlink(),'Home symlink refused')
 manifest=verify(bundle);targets=desired(bundle,home,manifest);skill=safe(home,'skills/team-coordination')
 if skill.exists():
  for path in skill.rglob('*'):
   check(not path.is_symlink(),'Installed symlink refused')
   if path.is_file():check(str(path.relative_to(home))in targets,'Unknown installed file; preserve and review before migration')
 changes=[]
 for relative,data in targets.items():
  path=safe(home,relative);before=path.read_bytes()if path.exists()else None
  if before!=data:changes.append({'path':relative,'before_sha256':sha(before)if before is not None else None,'after_sha256':sha(data)})
 return {'version':VERSION,'target_home':str(home),'manifest_sha256':sha((bundle/'manifest.json').read_bytes()),'changes':changes},targets

def install(bundle,home,apply=False,plan=None):
 preview,targets=inspect(bundle,home)
 if not apply:return preview
 check(plan==preview,'Fresh matching dry-run plan required before apply')
 if not preview['changes']:return {'changed':0,'idempotent':True}
 journal=safe(home,'team-coordination-install.json');check(not journal.exists(),'Existing journal: rollback or review versioned migration first')
 records=[]
 for change in preview['changes']:
  path=safe(home,change['path']);records.append({**change,'original':base64.b64encode(path.read_bytes()).decode()if path.exists()else None})
 record={'version':VERSION,'files':records};home.mkdir(parents=True,exist_ok=True);atomic(journal,(json.dumps(record,indent=2)+'\n').encode())
 for item in records:
  path=safe(home,item['path']);before=sha(path.read_bytes())if path.exists()else None
  check(before==item['before_sha256'],'Concurrent target change; inspect journal before retry')
  atomic(path,targets[item['path']]);check(sha(path.read_bytes())==item['after_sha256'],'Readback failed')
 return {'changed':len(records),'journal':str(journal),'loaded':'unverified'}

def rollback(home):
 journal=safe(home,'team-coordination-install.json');record=json.loads(journal.read_text());check(record['version']==VERSION,'Use the matching release for rollback')
 changed=[]
 for item in record['files']:
  path=safe(home,item['path']);current=sha(path.read_bytes())if path.is_file()else None
  if current==item['after_sha256']:changed.append(item)
  else:check(current==item['before_sha256'],'Rollback conflict: preserve concurrent edit')
 for item in reversed(changed):
  path=safe(home,item['path'])
  if item['original']is None:path.unlink()
  else:atomic(path,base64.b64decode(item['original']))
 journal.unlink();return {'rolled_back':len(changed)}

def doctor(bundle,home):
 manifest=verify(bundle);targets=desired(bundle,home,manifest);mismatches=[]
 for relative,data in targets.items():
  path=safe(home,relative)
  if not path.is_file()or path.read_bytes()!=data:mismatches.append(relative)
 return {'integrity_ok':not mismatches,'mismatches':mismatches,'python':sys.version.split()[0],'manual_steps':['Install a trusted supported Python and official Codex CLI separately','Sign in through official Codex authentication; never copy credentials','Verify live exact model availability and selected-model receipts','Confirm fresh-session instruction exposure and real acknowledgements'],'scope':'Read-only by default; explicit handoffs may configure bounded workspace writing; bypassing clients are advisory','clean_mac_verified':False}

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--bundle',type=Path,default=Path(__file__).resolve().parent);parser.add_argument('--codex-home',type=Path,required=True);parser.add_argument('--plan',type=Path);parser.add_argument('--save-plan',type=Path);parser.add_argument('command',choices=['dry-run','apply','doctor','rollback']);args=parser.parse_args()
 if args.command=='rollback':result=rollback(args.codex_home)
 elif args.command=='doctor':result=doctor(args.bundle,args.codex_home)
 else:
  plan=json.loads(args.plan.read_text())if args.plan else None;result=install(args.bundle,args.codex_home,args.command=='apply',plan)
  if args.save_plan:check(args.command=='dry-run','Save plan only during dry-run');atomic(args.save_plan,(json.dumps(result,indent=2)+'\n').encode())
 print(json.dumps(result,indent=2));return int(args.command=='doctor'and not result['integrity_ok'])
if __name__=='__main__':
 try:sys.exit(main())
 except (OSError,ValueError,KeyError)as error:print(json.dumps({'error':str(error)}));sys.exit(2)
