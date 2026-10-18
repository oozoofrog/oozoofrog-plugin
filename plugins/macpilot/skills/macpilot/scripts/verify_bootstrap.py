#!/usr/bin/env python3
"""Fresh-install proof using the published release, with developer tools unavailable."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from verify_connection import Server


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--skill',type=Path,required=True);p.add_argument('--evidence',type=Path,required=True)
    args=p.parse_args();source=args.skill.resolve(strict=True);out=args.evidence.resolve();out.mkdir(parents=True,exist_ok=False)
    checks=[];server=None;completed=False
    def check(name,value,**detail):
        checks.append(dict(check=name,passed=bool(value),**detail))
        if not value:raise AssertionError((name,detail))
    try:
        with tempfile.TemporaryDirectory(prefix='macpilot-no-swift-')as tmp:
            skill=Path(tmp)/'skill'
            shutil.copytree(source,skill,ignore=shutil.ignore_patterns('bin','evidence','.build','.swiftpm','__pycache__'))
            check('fresh skill has no runtime',not (skill/'bin').exists())
            env=dict(os.environ,PATH='/developer-tools-unavailable',DEVELOPER_DIR='/developer-tools-unavailable',SDKROOT='/developer-tools-unavailable',MACPILOT_STATE_DIR=str(Path(tmp)/'state'))
            env.pop('MACPILOT_BUILD_FROM_SOURCE',None)
            launcher=skill/'scripts/macpilot'
            command=[str(launcher),'call','mac_connection','--json','-']
            first=subprocess.run(command,input=json.dumps(dict(operation='status')),capture_output=True,text=True,env=env,timeout=210)
            (out/'first.stdout.json').write_text(first.stdout);(out/'first.stderr.log').write_text(first.stderr)
            check('first launch downloads runtime without developer tools',first.returncode==0,returncode=first.returncode)
            response=json.loads(first.stdout);pins=json.loads((skill/'runtime/distribution.json').read_text())
            check('runtime reports pinned version',response['version']==pins['version'])
            binary=skill/'bin/MacPilot.app/Contents/MacOS/macpilot';helper=binary.with_name('macpilot-simulator-hid')
            for path,key in [(binary,'mainSHA256'),(helper,'helperSHA256')]:
                check('downloaded '+path.name+' matches pinned bytes',hashlib.sha256(path.read_bytes()).hexdigest()==pins[key])
            check('download is official versioned HTTPS asset','Downloading MacPilot '+pins['version']in first.stderr)
            second=subprocess.run(command,input=json.dumps(dict(operation='status')),capture_output=True,text=True,env=env,timeout=15)
            check('second launch reuses verified runtime',second.returncode==0 and 'Downloading'not in second.stderr)
            server=Server(launcher,Path(tmp)/'mcp-state',environment=env)
            catalog=server.request('tools/list',{})['tools'];names={t['name']for t in catalog}
            check('fresh prebuilt MCP exposes native analysis and Simulator',{'mac_analyze','mac_simulator'}.issubset(names),toolCount=len(catalog))
            check('fresh prebuilt MCP executes ordinary read',server.call('mac_connection',operation='status')['version']==pins['version'])
            server.close();server=None
            if Path('/Library/Apple/usr/share/rosetta/rosetta').exists():
                intel=subprocess.run(['/usr/bin/arch','-x86_64',str(binary),'call','mac_connection','--json','-'],input=json.dumps(dict(operation='status')),capture_output=True,text=True,env=env,timeout=45)
                (out/'rosetta.stdout.json').write_text(intel.stdout);(out/'rosetta.stderr.log').write_text(intel.stderr)
                check('x86_64 runtime executes without developer tools under Rosetta',intel.returncode==0 and json.loads(intel.stdout)['version']==pins['version'],runtime='Rosetta on Apple Silicon; not native Intel hardware')
            # Validation rejects altered signed app bytes without executing them. Missing network is explicit.
            data=helper.read_bytes();helper.write_bytes(data+b'tampered')
            bad=subprocess.run(['/bin/sh',str(skill/'scripts/install-runtime.sh')],capture_output=True,text=True,env=dict(env,HTTPS_PROXY='http://127.0.0.1:1',https_proxy='http://127.0.0.1:1'),timeout=20)
            (out/'tamper.stderr.log').write_text(bad.stderr)
            check('altered helper is not accepted as installed runtime',bad.returncode!=0)
            check('failed download never compiles sources','swift build'not in bad.stderr and 'xcrun'not in bad.stderr)
            completed=True
    except BaseException as error:
        checks.append(dict(check='bootstrap verification completes',passed=False,error=type(error).__name__,message=str(error)));raise
    finally:
        if server:server.close()
        report=dict(status='passed'if completed and all(c['passed']for c in checks)else'failed',checks=checks,scope='published_asset_fresh_install_developer_tools_unavailable',osSwiftCompilerRemoved=False)
        (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status=report['status'],checks=len(checks),report=str(out/'report.json'))))

if __name__=='__main__':main()
