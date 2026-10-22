#!/usr/bin/env python3
"""Build only the public allowlist; deterministic archive, no local history/state."""
from pathlib import Path
import gzip,hashlib,io,json,re,tarfile
VERSION='0.1.1-public.1'
ROOT=Path(__file__).resolve().parent
FILES=['.gitignore','README.md','bootstrap.py','run.py','make_release.py','global-block.md','payload/team-coordination/SKILL.md','payload/team-coordination/policy.json','payload/team-coordination/schema/project-state.schema.json']
FILES += ['payload/team-coordination/scripts/'+name for name in ['harness.py','managed_run.py','team_ledger.py']]
FILES += ['payload/team-coordination/roles/'+name+'.md' for name in ['leader','core','support','advisor','reviewer']]
FILES += ['tests/'+name for name in ['test_harness.py','test_adapter.py','fake_server.py','test_bootstrap.py']]
def sha(data):return hashlib.sha256(data).hexdigest()
def scan(data):
 # Patterns are assembled so this source does not itself contain a private-path example.
 forbidden=[b'/' + b'Users/',b'/' + b'Volumes/',b'Sentinel'+b'_',b'source'+b'_thread_id',b'BEGIN '+b'PRIVATE KEY']
 if any(value in data for value in forbidden)or re.search(rb'sk-[A-Za-z0-9_-]{24,}',data):raise ValueError('Non-public content detected')
def main():
 manifest={'version':VERSION,'files':{}}
 for relative in FILES:
  path=ROOT/relative
  if path.is_symlink():raise ValueError('Symlink in public allowlist')
  data=path.read_bytes();scan(data);manifest['files'][relative]=sha(data)
 (ROOT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 dist=ROOT/'dist';dist.mkdir(exist_ok=True);name='codex-team-harness-'+VERSION;archive=dist/(name+'.tar.gz')
 with archive.open('wb')as raw,gzip.GzipFile(filename='',fileobj=raw,mode='wb',mtime=0)as compressed,tarfile.open(fileobj=compressed,mode='w')as tar:
  for relative in FILES+['manifest.json']:
   data=(ROOT/relative).read_bytes();scan(data);item=tarfile.TarInfo(name+'/'+relative);item.size=len(data);item.mode=0o644;item.mtime=0;tar.addfile(item,io.BytesIO(data))
 checksum=sha(archive.read_bytes());(dist/(archive.name+'.sha256')).write_text(checksum+'  '+archive.name+'\n');print(json.dumps({'archive':archive.name,'sha256':checksum,'files':len(FILES)+1}))
if __name__=='__main__':main()
