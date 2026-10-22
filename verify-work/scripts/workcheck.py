"""One sequential, evidence-backed project check. Python stdlib only."""
import argparse
import datetime as dt
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys

class NoteCollision(ValueError):
    """A detected alias must block recording even when the run itself fails."""

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def read_json(path):
    def reject(value):
        raise ValueError('Non-finite JSON: '+value)
    def finite_float(value):
        number=float(value)
        if not math.isfinite(number):
            raise ValueError('Non-finite JSON numeric literal: '+value)
        return number
    return json.loads(Path(path).read_text(encoding='utf-8'), parse_constant=reject, parse_float=finite_float)

def save(path, value):
    temp = path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    os.replace(temp,path)

def require(condition, reason):
    if not condition:
        raise ValueError(reason)

def contract_at(path):
    c = read_json(path)
    require(c['schema']=='workcheck-contract/1','Unknown contract schema')
    require(isinstance(c['project'],str) and c['project'].strip(),'Project required')
    require(Path(c['runs']).is_absolute(),'Absolute runs directory required')
    require(isinstance(c['inputs'],list) and c['inputs'],'Pinned inputs required')
    for item in c['inputs']:
        require(Path(item['path']).is_absolute(),'Absolute input required')
        require(re.fullmatch('[0-9a-f]{64}',item['sha256']) is not None,'SHA256 required')
    require(len({i['path'] for i in c['inputs']})==len(c['inputs']),'Duplicate input')
    require(len({str(Path(i['path']).resolve()) for i in c['inputs']})==len(c['inputs']),'Duplicate canonical input')
    for case in c['cases'].values():
        require(isinstance(case['argv'],list) and case['argv'],'argv required')
        require(all(isinstance(a,str) for a in case['argv']),'argv must contain strings')
        require(isinstance(case['scope'],str) and case['scope'].strip(),'Scope required')
    return c

def pinned(c):
    actual = {str(Path(i['path']).resolve()):sha(i['path']) for i in c['inputs']}
    require(all(actual[str(Path(i['path']).resolve())]==i['sha256'] for i in c['inputs']),'Pinned input mismatch; inspect source/code, do not repin silently')
    return actual

def protect_note(c, contract, extra=()):
    note=Path(c['note'])
    require(note.is_absolute() and note.is_file(),'Existing absolute note required; resolve renamed note first')
    if note.resolve().is_relative_to(Path(c['runs']).resolve()):
        raise NoteCollision('Note must be outside the run output tree')
    protected=[Path(contract),Path(__file__)]+[Path(i['path']) for i in c['inputs']]+[Path(p) for p in extra]
    for target in protected:
        # samefile covers both symbolic links and hard links to an existing file.
        if note.resolve()==target.resolve() or (target.exists() and os.path.samefile(note,target)):
            raise NoteCollision('Note collides with protected input, contract, helper or evidence: '+str(target))

def verify_result(path, run, inputs, scope):
    r=read_json(path)
    require(r['schema']=='workcheck-result/1','Unknown result schema')
    require(r['scope']==scope,'Result scope mismatch')
    require(isinstance(r['checks'],list) and r['checks'],'No checks')
    ids=[]
    for row in r['checks']:
        require(isinstance(row['id'],str) and row['id'],'Check id required')
        require(row['status'] in ('PASS','FAIL','UNKNOWN'),'Invalid check status')
        require(isinstance(row['reason'],str) and row['reason'].strip(),'Reason required')
        ids.append(row['id'])
    require(len(set(ids))==len(ids),'Duplicate check ids')
    for key in ('evidence','unverified','next_actions','recovery'):
        require(isinstance(r[key],list) and r[key],key+' must be nonempty')
    require(isinstance(r['coverage'],dict),'Coverage object required')
    files={str(path):sha(path)}
    for raw in r['evidence']:
        p=Path(raw).resolve()
        require(p.is_relative_to(run.resolve()) or str(p) in inputs,'Evidence outside run/pinned inputs: '+str(p))
        require(p.is_file(),'Missing evidence: '+str(p))
        files[str(p)]=sha(p)
    status='FAIL' if any(x['status']=='FAIL' for x in r['checks']) else 'UNKNOWN' if any(x['status']=='UNKNOWN' for x in r['checks']) else 'PASS'
    return r,status,files

def append_note(note, run, receipt):
    marker='<!-- workcheck:'+receipt['run_id']+':'+receipt['fingerprint']+' -->'
    end_marker='<!-- /workcheck:'+receipt['run_id']+':'+receipt['fingerprint']+' -->'
    require(note.is_file(),'Existing note missing; resolve renamed note before recording')
    # Advisory lock serializes helper writers. O_APPEND preserves other user content.
    with note.open('a+',encoding='utf-8') as f:
        fcntl.flock(f,fcntl.LOCK_EX)
        f.seek(0);before=f.read()
        if marker in before:
            require(end_marker in before,'Incomplete note marker; preserve text and inspect before retry')
            return 'ALREADY_RECORDED'
        backup=run/'note-before.md'
        if backup.exists():
            require(backup.read_text(encoding='utf-8')==before,'Note changed since interrupted append; inspect before retry')
        else:
            backup.write_text(before,encoding='utf-8')
        r=receipt.get('result',{})
        lines=['',marker,'',f"### {receipt['project']} · {receipt['case']} · {receipt['run_id']}",
               f"확인 UTC {receipt['created_utc']}. 실행 {receipt['execution']} / 자동 검사 {receipt['verification']} / 사람 수락 미기록.",
               '근거: [실행 영수증](<'+str(run/'receipt.json')+'>). 판정 범위: '+receipt['scope'],
               '미검증: '+'; '.join(map(str,r.get('unverified',['실행 실패로 판정 불가']))),
               '다음 행동: '+'; '.join(map(str,r.get('next_actions',['실패 로그와 계약을 확인']))),
               '복구: '+'; '.join(map(str,r.get('recovery',['원본을 바꾸지 말고 해당 실행 폴더를 보존']))),end_marker,'']
        f.write('\n'.join(lines));f.flush();os.fsync(f.fileno())
        require(note.stat().st_ino==os.fstat(f.fileno()).st_ino,'Note was atomically replaced during append; inspect current note, do not overwrite it')
        return 'APPENDED'

def run(args):
    path=Path(args.contract).resolve();c=contract_at(path)
    require(args.case in c['cases'],'Unknown case')
    require(re.fullmatch('[A-Za-z0-9][A-Za-z0-9_-]{0,79}',args.run_id) is not None,'Unsafe run id')
    inputs=pinned(c);case=c['cases'][args.case]
    if args.note:protect_note(c,path)
    fingerprint=hashlib.sha256(json.dumps({'contract':sha(path),'helper':sha(__file__),'inputs':inputs,'case':args.case},sort_keys=True).encode()).hexdigest()
    root=Path(c['runs']);root.mkdir(parents=True,exist_ok=True)
    with (root/'.workcheck.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise ValueError('Another check is active; no duplicate execution')
        folder=root/args.run_id;receipt_path=folder/'receipt.json'
        if folder.exists():
            require(receipt_path.is_file(),'Incomplete run exists; inspect it and use a new run ID')
            rec=read_json(receipt_path)
            require(rec['fingerprint']==fingerprint,'Stale replay: contract, inputs or helper changed')
            require(all(Path(p).is_file() and sha(p)==v for p,v in rec['files'].items()),'Stored evidence changed; replay refused')
            replay=True
        else:
            folder.mkdir();replay=False
            argv=[a.replace('{out}',str(folder)).replace('{case}',args.case) for a in case['argv']]
            rec={'schema':'workcheck-receipt/1','project':c['project'],'case':args.case,'run_id':args.run_id,
                 'fingerprint':fingerprint,'created_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
                 'scope':case['scope'],'argv':argv,'inputs':inputs,'execution':'FAILED','verification':'UNKNOWN',
                 'human_acceptance':'NOT_RECORDED','files':{}}
            try:
                with (folder/'process.log').open('wb') as log:
                    completed=subprocess.run(argv,stdout=log,stderr=subprocess.STDOUT,check=False)
                rec['process_exit_code']=completed.returncode
                require(completed.returncode==0,'Process failed; inspect process.log')
                result,verdict,files=verify_result(folder/'result.json',folder,inputs,case['scope'])
                rec['files'].update(files)
                require(pinned(c)==inputs,'Input changed during execution')
                if args.note:protect_note(c,path,files)
                rec.update(execution='COMPLETED',verification=verdict,result=result,files=files)
            except NoteCollision as error:
                rec['error']=str(error)
                rec['note_recording']='BLOCKED_COLLISION'
            except (ValueError,KeyError,TypeError,OSError) as error:
                rec['error']=str(error)
            for p in (folder/'process.log',folder/'result.json'):
                if p.is_file():rec['files'][str(p)]=sha(p)
            save(receipt_path,rec)
        note_status='NOT_REQUESTED'
        if args.note:
            if rec.get('note_recording')=='BLOCKED_COLLISION':
                note_status='BLOCKED_COLLISION'
            else:
                protect_note(c,path,list(rec['files'])+[receipt_path]+[p for p in folder.rglob('*') if p.is_file()])
                note_status=append_note(Path(c['note']),folder,rec)
        print(json.dumps({'receipt':str(receipt_path),'execution':rec['execution'],'verification':rec['verification'],
                          'scope':rec['scope'],'replay':replay,'note':note_status},ensure_ascii=False))
        return 0 if rec['execution']=='COMPLETED' and rec['verification']=='PASS' else 1

def main():
    p=argparse.ArgumentParser(description=__doc__);subs=p.add_subparsers(dest='command',required=True)
    r=subs.add_parser('run');r.add_argument('--contract',required=True);r.add_argument('--case',required=True)
    r.add_argument('--run-id',required=True);r.add_argument('--note',action='store_true')
    args=p.parse_args()
    try:return run(args)
    except (ValueError,KeyError,TypeError,OSError) as error:
        print('WORKCHECK_STOP: '+str(error),file=sys.stderr);return 2
if __name__=='__main__':sys.exit(main())
