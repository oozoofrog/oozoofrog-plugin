#!/usr/bin/env python3
"""Launch verified bundled management code under an isolated Python interpreter."""
from pathlib import Path,PurePosixPath
import hashlib,json,runpy,sys
root=Path(__file__).resolve().parent
manifest=json.loads((root/'manifest.json').read_text())
if manifest.get('version')!='0.5.8':raise SystemExit('Wrong release version')
for relative,expected in manifest['files'].items():
 name=PurePosixPath(relative)
 if name.is_absolute()or '..'in name.parts or not name.parts or '\\'in relative:raise SystemExit('Unsafe manifest path')
 path=root.joinpath(*name.parts)
 for ancestor in [path,*path.parents]:
  if ancestor==root.parent:break
  if ancestor.is_symlink():raise SystemExit('Symlink refused')
 if not path.is_file()or not path.resolve().is_relative_to(root)or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:raise SystemExit('Release integrity failed')
if len(sys.argv)<2 or sys.argv[1]not in ('harness','managed-run','session-control','profile-overlay'):raise SystemExit('Choose harness, managed-run, session-control or profile-overlay')
script={'harness':'harness.py','managed-run':'managed_run.py','session-control':'session_control.py','profile-overlay':'profile_overlay.py'}[sys.argv.pop(1)]
scripts=root/'payload/team-coordination/scripts';sys.path.insert(0,str(scripts));sys.argv[0]=str(scripts/script);runpy.run_path(sys.argv[0],run_name='__main__')
