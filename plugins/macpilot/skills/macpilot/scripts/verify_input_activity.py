#!/usr/bin/env python3
"""Verify visible system-input feedback on an owned fixture and isolated state."""
import argparse, hashlib, json, os, shutil, signal, subprocess, tempfile, time
from pathlib import Path

p=argparse.ArgumentParser();p.add_argument('--binary',type=Path,required=True);p.add_argument('--fixture',type=Path,required=True);p.add_argument('--evidence',type=Path,required=True);a=p.parse_args()
B=str(a.binary.resolve());out=a.evidence.resolve();out.mkdir(parents=True,exist_ok=False)
root=Path(tempfile.mkdtemp(prefix='macpilot-activity-'));env=dict(os.environ,MACPILOT_STATE_DIR=str(root/'state'),MACPILOT_FIXTURE_DIR=str(root/'fixture'))
checks=[];identity=None;input_process=None;own_host=None
log=(out/'fixture.log').open('w');fixture=subprocess.Popen([str(a.fixture.resolve())],env=env,stdout=log,stderr=log)
def call(name,args,check=True):
 r=subprocess.run([B,'call',name,'--json','-'],input=json.dumps(args),capture_output=True,text=True,env=env,timeout=20)
 d=json.loads(r.stdout)
 if check and r.returncode:raise RuntimeError(d)
 return d

def launch(name,args):
 proc=subprocess.Popen([B,'call',name,'--json','-'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=env)
 proc.stdin.write(json.dumps(args));proc.stdin.close();proc.stdin=None
 return proc

def state():return json.loads((root/'fixture/state.json').read_text())
def status():
 try:return json.loads((root/'state/input-activity-status.json').read_text())
 except (FileNotFoundError,json.JSONDecodeError):return {}
def wait(predicate,seconds=4):
 end=time.monotonic()+seconds
 while time.monotonic()<end:
  if predicate():return True
  time.sleep(.04)
 return False

def ck(name,condition):
 checks.append({'check':name,'passed':bool(condition)});assert condition,(name,status(),state())
def observe():
 end=time.monotonic()+6
 while True:
  result=call('mac_observe',dict(identity,screenshot=False),False)
  if 'observation' in result:return result['observation']
  if result.get('code') not in ['window_unavailable','stale_observation'] or time.monotonic()>=end:raise RuntimeError(result)
  time.sleep(.1)
def node(o,identifier):return next(n for n in o['nodes'] if n.get('identifier')==identifier)
def focus_field():
 o=observe();call('mac_ax',{'observation':o['id'],'node':node(o,'literal-text')['id'],'operation':'focus'})
def task():return call('mac_task',{'operation':'begin','goal':'Owned visible input feedback verification','preserveForeground':False,'durationSeconds':90})['task']['id']
def hold(tid,duration=3000):
 o=call('mac_observe',dict(identity,screenshot=False,taskID=tid))['observation']
 return launch('mac_game_input',{'taskID':tid,'observation':o['id'],'node':node(o,'literal-text')['id'],'route':'global','keys':['left','up'],'durationMs':duration})
def finish(proc):
 stdout,stderr=proc.communicate(timeout=15)
 return json.loads(stdout)
try:
 assert wait(lambda:(root/'fixture/state.json').exists(),12)
 app=next(x for x in call('mac_apps',{})['apps'] if x['pid']==fixture.pid);identity={k:app[k] for k in ['pid','processStartID']}
 call('mac_app',dict(identity,action='activate'));focus_field()
 display=call('mac_doctor',{})['displays'][0]['id']
 # Delay only this test's host beyond the former two-second deadline.
 # No keyboard event may precede the actual visible acknowledgement.
 host=subprocess.Popen([B,'input-activity-host',str(root/'state')],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 assert wait(lambda:status().get('pid')==host.pid and status().get('running'),8)
 own_host=host.pid;os.kill(own_host,signal.SIGSTOP)
 tid=task();input_process=hold(tid)
 assert wait(lambda:(root/'state/input-activity.json').exists())
 time.sleep(2.4)
 record=json.loads((root/'state/input-activity.json').read_text())
 ck('delayed_notice_blocks_input_and_keeps_owner_fresh',input_process.poll() is None and not state()['heldKeys'] and record['active'] and time.time()-(record['updatedAt']+978307200)<1)
 os.kill(own_host,signal.SIGCONT)
 ck('notice_visible_before_and_during_system_input',wait(lambda:status().get('visible') and len(state().get('heldKeys',[]))==2))
 live=status();(out/'visible-status.json').write_text(json.dumps(live,indent=2))
 ck('all_screen_edges_and_notice_are_input_transparent',live['inputTransparent'] and not live['takesFocus'] and live['panelCount']>=5 and state()['active'])
 captured=call('mac_capture',{'displayID':display,'maxDimension':1600});shutil.copy2(captured['screenshot'],out/'during-input.png')
 result=finish(input_process);input_process=None
 ck('normal_completion_hides_notice_and_releases_keys',result['status']=='dispatched_unverified' and wait(lambda:not status().get('visible') and not state()['heldKeys']))
 o=observe();button=node(o,'increment')['frame'];before=state()['buttonCount']
 clicked=call('mac_click',{'observation':o['id'],'space':'screen','route':'global','x':button['x']+button['width']/2,'y':button['y']+button['height']/2})
 ck('mouse_click_passes_through_feedback',clicked['status']=='dispatched_unverified' and wait(lambda:state()['buttonCount']==before+1))
 ck('mouse_completion_hides_notice',wait(lambda:not status().get('visible')))
 focus_field();tid=task();input_process=hold(tid,10000)
 assert wait(lambda:status().get('visible') and len(state()['heldKeys'])==2)
 call('mac_task',{'operation':'cancel','taskID':tid})
 cancelled=finish(input_process);input_process=None
 ck('task_cancellation_hides_notice_and_releases_keys',wait(lambda:not status().get('visible') and not state()['heldKeys']))
 focus_field();tid=task();input_process=hold(tid,10000)
 assert wait(lambda:status().get('visible') and len(state()['heldKeys'])==2)
 own_host=status()['pid'];os.kill(own_host,signal.SIGTERM)
 failed=finish(input_process);input_process=None
 ck('lost_notice_stops_further_input_and_releases_keys',failed.get('code')=='activity_indicator_failed' and wait(lambda:not state()['heldKeys']))
 (out/'notice-loss.json').write_text(json.dumps(failed,indent=2))
 focus_field();o=observe()
 call('mac_key',{'observation':o['id'],'node':node(o,'literal-text')['id'],'key':'right','route':'process'})
 record=json.loads((root/'state/input-activity.json').read_text())
 ck('process_route_does_not_show_system_input_notice',not record['active'])
 after=call('mac_capture',{'displayID':display,'maxDimension':1600});shutil.copy2(after['screenshot'],out/'after-input.png')
 print(json.dumps(checks,indent=2))
finally:
 if own_host:
  try:os.kill(own_host,signal.SIGCONT)
  except ProcessLookupError:pass
 if input_process and input_process.poll() is None:
  # Close the owned task through its normal cancellation path.
  call('mac_task',{'operation':'cancel','taskID':tid},False)
  input_process.wait(timeout=15)
 if fixture.poll() is None:
  if identity:call('mac_app',dict(identity,action='terminate'),False)
  else:fixture.terminate()
  fixture.wait(timeout=5)
 if 'host' in locals() and host.poll() is None:
  host.terminate();host.wait(timeout=5)
 log.close()
 (out/'report.json').write_text(json.dumps({'checks':checks,'binary':B,'binarySHA256':hashlib.sha256(Path(B).read_bytes()).hexdigest(),'isolatedState':str(root),'visibleEvidence':'during-input.png','afterEvidence':'after-input.png'},indent=2))
