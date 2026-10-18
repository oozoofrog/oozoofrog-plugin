#!/usr/bin/env python3
"""Real Simulator integration on an owned synthetic device. Requires full Xcode for development only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import signal
import struct
import subprocess
import tempfile
import time
import zlib

from verify_connection import Server

BUNDLE='local.macpilot.simulator-fixture'

def run(*args,**kw):
    return subprocess.run(args,check=True,capture_output=True,text=True,timeout=60,**kw).stdout.strip()

def frame_rgb(path, sample):
    # One-pixel native resampling measures the retained synthetic frame, without an image library.
    run('/usr/bin/sips','-z','1','1',str(path),'--out',str(sample))
    data=sample.read_bytes();position=8;compressed=b'';header=None
    while position<len(data):
        length=struct.unpack('>I',data[position:position+4])[0]
        kind=data[position+4:position+8];value=data[position+8:position+8+length];position+=length+12
        if kind==b'IHDR':header=struct.unpack('>IIBBBBB',value)
        if kind==b'IDAT':compressed+=value
    assert header[:3]==(1,1,8) and header[3]in (2,6),header
    # For the first pixel, each PNG row filter has a zero predictor.
    raw=zlib.decompress(compressed);return list(raw[1:4])

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--binary',type=Path,required=True);p.add_argument('--evidence',type=Path,required=True)
    p.add_argument('--udid',help='Existing owned MacPilot integration fixture only; otherwise create one')
    args=p.parse_args();binary=args.binary.resolve(strict=True);out=args.evidence.resolve();out.mkdir(parents=True,exist_ok=False)
    checks=[];server=None;created=False;udid=args.udid;not_run=[];completed=False
    def check(name,passed,**detail):
        checks.append(dict(check=name,passed=bool(passed),**detail));(out/'checks.json').write_text(json.dumps(checks,indent=2)+'\n')
        if not passed:raise AssertionError((name,detail))
    try:
        with tempfile.TemporaryDirectory(prefix='macpilot-simulator-verify-') as tmp:
            root=Path(tmp);server=Server(binary,root/'state',timeout=60)
            def call(operation,**a):return server.call('mac_simulator',operation=operation,**a)
            def reject(code,**a):
                r=server.request('tools/call',dict(name='mac_simulator',arguments=a))
                v=r.get('structuredContent') or json.loads(r['content'][0]['text'])
                check('reject '+code,r.get('isError') is True and v.get('code')==code,response=v)
            inventory=call('list')['devices'];check('inventory names exact UUID devices',len(inventory)>0 and all('udid'in d for d in inventory))
            if not udid:
                runtimes=json.loads(run('xcrun','simctl','list','runtimes','-j'))['runtimes']
                runtime=next(r for r in runtimes if r['isAvailable'] and '.iOS-'in r['identifier'])
                dtype=next(d['identifier']for d in runtime['supportedDeviceTypes']if d['productFamily']=='iPhone')
                udid=run('xcrun','simctl','create','MacPilot integration owned fixture',dtype,runtime['identifier']);created=True
            device=call('status',udid=udid)
            check('destructive checks restricted to owned fixture',device['device']['name']=='MacPilot integration owned fixture')
            if args.udid and device['device']['state']=='Booted':
                # Existing owned fixtures may retain a system dialog from an interrupted run.
                call('shutdown',**{k:device[k]for k in ['udid','deviceIdentity','bootID']})
                device=call('status',udid=udid)
            if device['device']['state']!='Booted':
                call('boot',udid=udid,deviceIdentity=device['deviceIdentity']);run('xcrun','simctl','bootstatus',udid,'-b')
                device=call('status',udid=udid)
            for _ in range(6):
                if device.get('ready'):break
                time.sleep(.5);device=call('status',udid=udid)
            check('boot service reports ready before actions',device.get('ready') is True)
            target={k:device[k]for k in ['udid','deviceIdentity','bootID']}
            check('status binds device and launchd_sim generations',len(target['deviceIdentity'])==64 and ':'in target['bootID'])
            reject('invalid_argument',operation='status',udid='booted')
            reject('stale_simulator_identity',operation='input',**dict(target,deviceIdentity='0'*64),privateAPI=True,gesture='tap',x=.5,y=.2)
            reject('stale_simulator_boot',operation='input',**dict(target,bootID='stale'),privateAPI=True,gesture='tap',x=.5,y=.2)
            reject('private_api_disabled',operation='input',**target,gesture='tap',x=.5,y=.2)
            app=root/'MacPilotSimulatorFixture.app';app.mkdir()
            plist=dict(CFBundleIdentifier=BUNDLE,CFBundleExecutable='fixture',CFBundleName='MacPilot Simulator fixture',CFBundlePackageType='APPL',CFBundleVersion='1',CFBundleShortVersionString='1.0',LSRequiresIPhoneOS=True,UIDeviceFamily=[1],UILaunchScreen={},MinimumOSVersion='17.0',UIApplicationSceneManifest={'UIApplicationSupportsMultipleScenes':False,'UISceneConfigurations':{}},CFBundleURLTypes=[{'CFBundleURLSchemes':['macpilotfixture']}])
            (app/'Info.plist').write_bytes(plistlib.dumps(plist))
            source=Path(__file__).resolve().parent.parent/'tool/Fixtures/SimulatorFixture.m'
            arch=run('uname','-m');run('xcrun','--sdk','iphonesimulator','clang','-target',arch+'-apple-ios17.0-simulator','-fobjc-arc','-framework','UIKit','-framework','Foundation','-framework','CoreGraphics',str(source),'-o',str(app/'fixture'))
            run('codesign','--force','--sign','-',str(app))
            # Only the explicitly named test app on this owned device is replaced.
            try:call('terminate',**target,bundleID=BUNDLE)
            except AssertionError:pass
            call('install',**target,path=str(app));check('native app installation',True)
            launch=call('launch',**target,bundleID=BUNDLE);check('native app launch returns PID',BUNDLE in launch['command']['stdout'])
            data=Path(run('xcrun','simctl','get_app_container',udid,BUNDLE,'data'))/'Documents/state.json'
            deadline=time.monotonic()+8
            while not data.exists()and time.monotonic()<deadline:time.sleep(.05)
            def state():return json.loads(data.read_text())
            def wait(predicate):
                deadline=time.monotonic()+3
                while time.monotonic()<deadline:
                    if predicate(state()):return state()
                    time.sleep(.03)
                raise AssertionError(('guest postcondition',state()))
            wait(lambda s:s.get('becomeActive',0)>=1)
            check('guest app writes active synthetic state',state()['width']>0 and state()['becomeActive']>=1)
            probe=call('probe_input',**target);check('private driver probe sends no input',probe['status']=='private_driver_available' and not probe['dispatchAcknowledged'])
            def gesture(name,**kw):return call('input',**target,privateAPI=True,gesture=name,**kw)
            v=state();count=v['clicks'];tap=dict(x=v['buttonX'],y=v['buttonY'])
            reject('private_api_disabled',operation='input',**target,privateAPI=False,gesture='tap',**tap)
            check('disabled private input leaves guest state unchanged',state()==v)
            r=gesture('tap',**tap);wait(lambda s:s['clicks']==count+1)
            check('one tap is received once by UIButton',state()['clicks']==count+1 and r['dispatchAcknowledged'] and not r['businessPostconditionVerified'])
            before=state();reject('invalid_argument',operation='input',**target,privateAPI=True,gesture='pinch',x=.3,y=.6,toX=.2,toY=.6,x2=.7,y2=.6,toX2=2,toY2=.6)
            check('entire invalid gesture is rejected before any event',state()==before)
            for name in ['swipe','drag']:
                moves=state()['touchMoves'];gesture(name,x=.3,y=.65,toX=.7,toY=.65,duration=.35);wait(lambda s:s['touchMoves']>moves)
                check(name+' is received by guest touch callbacks',state()['touchMoves']>moves)
            count=state()['longPresses'];gesture('long_press',x=.5,y=.55,duration=.6);wait(lambda s:s['longPresses']>count)
            check('long press recognized in guest',state()['longPresses']==count+1)
            gesture('pinch',x=.3,y=.65,toX=.15,toY=.65,x2=.7,y2=.65,toX2=.85,toY2=.65,duration=.6)
            v=wait(lambda s:s['pinchEvents']>0);check('two-finger pinch changes recognizer scale',v['maxTouches']==2 and v['pinchScale']>1.3)
            gesture('tap',x=.5,y=300/v['height']);gesture('key',key='space');wait(lambda s:s.get('text')==' ')
            check('keyboard space changes UITextField',state()['text']==' ')
            gesture('key',key='backspace');wait(lambda s:s.get('text')=='');check('keyboard backspace changes UITextField',state()['text']=='')
            reject('invalid_argument',operation='input',**target,privateAPI=True,gesture='key',key='unsupported_unicode_가')
            resign=state().get('resignActive',0);gesture('button',key='home');wait(lambda s:s.get('resignActive',0)>resign)
            check('Home hardware button resigns guest scene',state()['resignActive']>resign)
            call('launch',**target,bundleID=BUNDLE);wait(lambda s:s.get('becomeActive',0)>=2)
            call('open_url',**target,url='macpilotfixture://verified')
            deadline=time.monotonic()+20
            while state().get('lastURL')!='macpilotfixture://verified':
                # Confirm only this owned app's URL request. Native OCR determines the actual button position.
                screen=call('screenshot',**target,ocr=True,languages=['ko-KR','en-US'])
                shutil.copy2(screen['path'],out/'fixture-url-confirmation.png')
                (out/'fixture-url-confirmation.json').write_text(json.dumps(screen,indent=2)+'\n')
                texts=[r['text']for r in screen['text']]
                buttons=[r for r in screen['text']if r['text']in ['열기','Open']]
                if any('macpilot simulator fixture'in t.casefold() for t in texts) and len(buttons)==1:
                    check('URL confirmation names owned fixture',True,texts=texts)
                    check('URL confirmation has one exact Open button',True)
                    box=buttons[0]['imageRect'];gesture('tap',x=(box['x']+box['width']/2)/screen['width'],y=(box['y']+box['height']/2)/screen['height'])
                    break
                if time.monotonic()>=deadline:
                    check('URL callback or exact owned confirmation appears within deadline',state().get('lastURL')=='macpilotfixture://verified',texts=texts)
                    break
                time.sleep(.15)
            wait(lambda s:s.get('lastURL')=='macpilotfixture://verified')
            check('open_url reaches exact fixture URL handler',state()['lastURL']=='macpilotfixture://verified')
            # Cancellation is sent to the isolated driver while a touch is held.
            bootpid,bootstart=target['bootID'].split(':',1)
            req=dict(operation='long_press',udid=udid,developerDir=run('xcode-select','-p'),bootPID=int(bootpid),bootStartID=bootstart,privateAPI=True,x=.5,y=.55,duration=2)
            child=subprocess.Popen([str(binary.with_name('macpilot-simulator-hid'))],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            child.stdin.write(json.dumps(req));child.stdin.close();child.stdin=None;time.sleep(.25);child.send_signal(signal.SIGTERM)
            stdout,stderr=child.communicate(timeout=4);receipt=json.loads(stdout)
            check('cancelled driver exits with explicit receipt',receipt.get('code')=='cancelled' and 'releaseError'not in receipt)
            count=state()['clicks'];gesture('tap',**tap);wait(lambda s:s['clicks']==count+1);check('touch released after cancellation',state()['clicks']==count+1)
            capture=call('screenshot',**target);shutil.copy2(capture['path'],out/'simulator.png')
            dimensions=struct.unpack('>II',Path(capture['path']).read_bytes()[16:24])
            check('device PNG reports physical pixel dimensions',tuple(dimensions)==(capture['width'],capture['height']) and capture['width']>300 and capture['height']>600)
            recording=call('record',**target,durationSeconds=2)['recording'];shutil.copy2(recording['path'],out/'simulator.mov')
            for index,frame in enumerate(recording['frames']):
                retained=out/('recording-frame-'+str(index)+'.png');shutil.copy2(frame['path'],retained);frame['retainedPath']=str(retained)
            (out/'recording.json').write_text(json.dumps(recording,indent=2)+'\n')
            check('device recording finalized with decoded video',recording['videoTracks']>0 and recording['durationSeconds']>0 and len(recording['frames'])==2)
            reject('simulator_window_mismatch',operation='observe',**target,pid=os.getpid(),processStartID='0.0',windowID=1)
            apps=server.call('mac_apps')['apps'];sim=next((a for a in apps if a.get('bundleID')=='com.apple.iphonesimulator'),None)
            if sim:
                windows=server.call('mac_windows',pid=sim['pid'])['windows']
                win=next(w for w in windows if str(w.get('title','')).startswith(device['device']['name']))
                observed=call('observe',**target,pid=sim['pid'],processStartID=sim['processStartID'],windowID=win['windowID'])
                check('native Simulator iOSContentGroup contains fixture UI',observed['scope']=='selected_device_ios_content' and any(n.get('identifier')=='increment'for n in observed['nodes']))
            else:not_run.append(dict(feature='Simulator.app iOSContentGroup positive runtime',reason='Simulator.app not present in the selected Xcode installation; no app-wide fallback or synthetic substitute'))
            # Lock is terminal. Observe both scene and display; Simulator power state can keep a scene active.
            before_lock=call('screenshot',**target);before_png=out/'before-lock.png';shutil.copy2(before_lock['path'],before_png)
            resign=state().get('resignActive',0);gesture('button',key='lock')
            deadline=time.monotonic()+3
            while state().get('resignActive',0)<=resign and time.monotonic()<deadline:time.sleep(.03)
            after_lock=call('screenshot',**target);after_png=out/'after-lock.png';shutil.copy2(after_lock['path'],after_png)
            before_rgb=frame_rgb(before_png,out/'before-lock-sample.png');after_rgb=frame_rgb(after_png,out/'after-lock-sample.png')
            scene_changed=state().get('resignActive',0)>resign
            display_dimmed=sum(before_rgb)>384 and sum(after_rgb)<sum(before_rgb)*.6
            check('Lock changes guest scene or captured device display',scene_changed or display_dimmed,sceneChanged=scene_changed,displayDimmed=display_dimmed,beforeRGB=before_rgb,afterRGB=after_rgb)
            (out/'guest-state.json').write_text(json.dumps(state(),indent=2)+'\n')
            call('terminate',**target,bundleID=BUNDLE);check('terminate removes guest process',not run('xcrun','simctl','spawn',udid,'launchctl','list').find(BUNDLE)>=0)
            call('uninstall',**target,bundleID=BUNDLE);r=subprocess.run(['xcrun','simctl','get_app_container',udid,BUNDLE,'data'],capture_output=True)
            check('uninstall removes exact fixture container',r.returncode!=0)
            call('shutdown',**target);off=call('status',udid=udid);check('shutdown ends prior boot generation',off['device']['state']=='Shutdown' and 'bootID'not in off)
            call('boot',udid=udid,deviceIdentity=off['deviceIdentity']);run('xcrun','simctl','bootstatus',udid,'-b');fresh=call('status',udid=udid)
            check('reboot changes bootID and preserves deviceIdentity',fresh['bootID']!=target['bootID'] and fresh['deviceIdentity']==target['deviceIdentity'])
            reject('stale_simulator_boot',operation='screenshot',**target)
            completed=True
    except BaseException as error:
        checks.append(dict(check='requested verification sequence completes',passed=False,error=type(error).__name__,message=str(error)))
        raise
    finally:
        if server:server.close()
        if created and udid:
            subprocess.run(['xcrun','simctl','shutdown',udid],capture_output=True);subprocess.run(['xcrun','simctl','delete',udid],check=True,capture_output=True)
        report=dict(status='passed'if completed and checks and all(c['passed']for c in checks)else'failed',binarySHA256=hashlib.sha256(binary.read_bytes()).hexdigest(),checks=checks,notRun=not_run,deviceUDID=udid,scope='owned_synthetic_simulator',physicalDevice='NOT_RUN')
        (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status=report['status'],checks=len(checks),notRun=not_run,report=str(out/'report.json'))))

if __name__=='__main__':main()
