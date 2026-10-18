#!/usr/bin/env python3
"""Owned AppKit input regression; never touches user documents or force-quits apps.
Build macpilot-fixture first with xcrun swift build --package-path macpilot/tool
--product macpilot-fixture. Pass the exact signed MacPilot --binary under test.
"""
import argparse,atexit,hashlib,json,subprocess,sys,time,os,shutil,tempfile
from pathlib import Path
parser=argparse.ArgumentParser()
parser.add_argument('--binary',type=Path,required=True)
parser.add_argument('--fixture',type=Path,required=True)
parser.add_argument('--evidence',type=Path,required=True)
args=parser.parse_args()
BIN=str(args.binary.resolve());fixture=args.fixture.resolve();OUT=args.evidence.resolve()
OUT.mkdir(parents=True,exist_ok=False)
assert Path(BIN).is_file() and fixture.is_file()
rpc=None
identity=None
rpc_log=(OUT/'mcp-stderr.log').open('w')
seq=0
def send(obj):
 rpc.stdin.write(json.dumps(obj,ensure_ascii=False)+'\n');rpc.stdin.flush()
 while True:
  line=rpc.stdout.readline()
  if not line:raise RuntimeError('MCP EOF')
  msg=json.loads(line)
  if msg.get('id')==obj.get('id'):return msg

def call(name,args,label=None,check=True):
 global rpc,seq
 if rpc is None:
  rpc=subprocess.Popen([BIN,'mcp'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=rpc_log,text=True)
  send({'jsonrpc':'2.0','id':0,'method':'initialize','params':{'protocolVersion':'2024-11-05','capabilities':{},'clientInfo':{'name':'macpilot-input-validation','version':'1'}}})
  rpc.stdin.write(json.dumps({'jsonrpc':'2.0','method':'notifications/initialized'})+'\n');rpc.stdin.flush()
  atexit.register(lambda:rpc.stdin.close())
 seq+=1
 msg=send({'jsonrpc':'2.0','id':seq,'method':'tools/call','params':{'name':name,'arguments':args}})
 if 'error' in msg:raise RuntimeError(msg)
 result=msg['result'];r=json.loads(next(c['text'] for c in result['content'] if c['type']=='text'))
 failed=result.get('isError',False)
 if label:
  (OUT/(label+'.json')).write_text(json.dumps(r,ensure_ascii=False,indent=2))
  for key in ['screenshot']:
   path=r.get(key) or r.get('observation',{}).get(key)
   if path and Path(path).exists():shutil.copy2(path,OUT/(label+'.png'))
 if check and failed:raise RuntimeError(r)
 return r
base=Path(tempfile.mkdtemp(prefix='macpilot-input-fixture-'));env=dict(os.environ,MACPILOT_FIXTURE_DIR=str(base/'fixture'))
log=(OUT/'fixture-events.log').open('w');p=subprocess.Popen([str(fixture)],env=env,stdout=log,stderr=log)
checks=[]
def state():return json.loads((base/'fixture/state.json').read_text())
def ck(n,v):checks.append({'check':n,'passed':bool(v)});assert v,(n,state())
def observe():return call('mac_observe',identity)['observation']
def node(o,name):return next(n for n in o['nodes'] if n.get('identifier')==name)
def ax(name,op,**kw):
 o=observe();return call('mac_ax',dict(observation=o['id'],node=node(o,name)['id'],operation=op,**kw))
def key(k,mods=[]):
 o=observe();return call('mac_key',dict(observation=o['id'],node=node(o,'literal-text')['id'],route='process',key=k,modifiers=mods))
try:
 for _ in range(50):
  if (base/'fixture/state.json').exists():break
  time.sleep(.1)
 app=next(x for x in call('mac_apps',{})['apps'] if x['pid']==p.pid);identity={k:app[k] for k in ['pid','processStartID']}
 for _ in range(30):
  found=call('mac_observe',identity,check=False)
  if 'observation' in found:break
  time.sleep(.1)
 else:raise RuntimeError(found)
 o=found['observation'];call('mac_focus',{'observation':o['id']})
 ax('literal-text','set_value',text='preserved fixture');ax('literal-text','focus');key('a',['command']);time.sleep(.5)
 ck('command_select_all',state()['selection']['length']==len('preserved fixture'))
 o=observe();r=call('mac_type',{'observation':o['id'],'node':node(o,'literal-text')['id'],'text':'Save As 한글 😀 e\u0301','route':'process'},'fixture-type');time.sleep(.2)
 ck('scalar_text_exact',state()['text']=='Save As 한글 😀 e\u0301')
 reused=call('mac_type',{'observation':o['id'],'node':node(o,'literal-text')['id'],'text':'duplicate'},'fixture-retry',check=False)
 ck('consumed_snapshot_no_duplicate',reused.get('code')=='stale_observation' and state()['text']=='Save As 한글 😀 e\u0301')
 o=observe();bad=call('mac_key',{'observation':o['id'],'node':node(o,'increment')['id'],'key':'a','modifiers':['command']},'fixture-wrong-node',False)
 ck('wrong_focused_target_rejected',bad.get('code')=='focus_mismatch')
 ax('arm-focus-shift','action');o=observe();r=call('mac_type',{'observation':o['id'],'node':node(o,'literal-text')['id'],'text':'z'*60},'fixture-interrupted');time.sleep(.2)
 ck('secure_focus_interruption',r['status']=='dispatch_interrupted' and 0<r['eventsPosted']<120 and state()['secureUnchanged'])
 ax('literal-text','focus');older=observe()
 o=observe();shown=call('mac_ax',dict(observation=o['id'],node=node(o,'show-sheet')['id'],operation='action'),'fixture-sheet-open',False)
 for _ in range(40):
  if state()['sheetOpen']:break
  time.sleep(.1)
 ck('modal_open_reconciled',state()['sheetOpen'])
 blocked=call('mac_key',{'observation':older['id'],'node':node(older,'literal-text')['id'],'key':'a','modifiers':['command']},'fixture-modal',False)
 ck('modal_blocks_old_target',blocked.get('code') in ['modal_sheet','stale_observation'])
 o=observe();buttons=[n for n in o['nodes'] if n['role']=='AXButton' and n.get('title')=='닫기'];assert len(buttons)==1
 call('mac_ax',{'observation':o['id'],'node':buttons[0]['id'],'operation':'action'});time.sleep(.2)
 ck('modal_closed_once',not state()['sheetOpen'] and state()['events'].get('sheetClosed')==1)
 o=observe();focused=call('mac_focus',{'observation':o['id']})
 ax('literal-text','focus');o=observe()
 selected=call('mac_key',{'observation':o['id'],'node':node(o,'literal-text')['id'],'key':'a','modifiers':['command'],'route':'global','inputSource':'ascii'},'fixture-ascii-key')
 ck('ascii_shortcut_source_restored',selected['keyboardInputSource']['restored'])
 o=observe();typed=call('mac_type',{'observation':o['id'],'node':node(o,'literal-text')['id'],'text':'ASCII 한글 🚀','route':'global','inputSource':'ascii'},'fixture-ascii-type');time.sleep(.2)
 ck('ascii_text_and_source_restored',state()['text']=='ASCII 한글 🚀' and typed['keyboardInputSource']['restored'])
 o=observe();invalid=call('mac_type',{'observation':o['id'],'node':node(o,'literal-text')['id'],'text':'forbidden route','route':'process','inputSource':'ascii'},'fixture-ascii-process-reject',False)
 ck('ascii_process_route_rejected',invalid.get('code')=='invalid_argument' and state()['text']=='ASCII 한글 🚀')
 ax('literal-text','set_value',text='');ax('literal-text','focus');o=observe()
 letters=call('mac_game_input',{'observation':o['id'],'node':node(o,'literal-text')['id'],'keys':['d','u','i'],'durationMs':100,'route':'global','inputSource':'ascii'},'fixture-game-letters');time.sleep(.2)
 ck('ascii_game_key_characters_match_physical_keys',state()['text']=='dui' and letters['keyboardInputSource']['restored'])
 ax('literal-text','set_value',text='');ax('literal-text','focus');o=observe()
 hid=call('mac_game_input',{'observation':o['id'],'node':node(o,'literal-text')['id'],'keys':['u','i'],'durationMs':100,'route':'global','inputSource':'ascii','eventSource':'hid'},'fixture-game-hid');time.sleep(.2)
 ck('explicit_hid_source_delivers_and_releases_fixture_keys',state()['text']=='ui' and hid['eventSource']=='hid' and not state()['heldKeys'])
 o=observe();invalid_hid=call('mac_game_input',{'observation':o['id'],'node':node(o,'literal-text')['id'],'keys':['u'],'durationMs':100,'route':'process','eventSource':'hid'},'fixture-game-hid-process-reject',False)
 ck('hid_system_state_requires_global_route',invalid_hid.get('code')=='invalid_argument' and state()['text']=='ui' and not state()['heldKeys'])
 o=observe();held=call('mac_game_input',{'observation':o['id'],'node':node(o,'literal-text')['id'],'keys':['left','up'],'durationMs':300,'route':'process'},'fixture-game-hold');time.sleep(.2)
 ck('simultaneous_keys_hold_and_release',held['releaseEventsPosted']==2 and state()['maximumHeldKeys']>=2 and not state()['heldKeys'] and state()['lastHoldSeconds']>=.25)
 ax('literal-text','set_value',text='');ax('literal-text','focus');o=observe()
 pulsed=call('mac_game_input',{'observation':o['id'],'node':node(o,'literal-text')['id'],'keys':['left'],'tapKeys':['z'],'tapIntervalMs':150,'durationMs':400,'route':'global','inputSource':'ascii'},'fixture-game-pulse');time.sleep(.2)
 ck('held_movement_with_repeated_taps',2<=pulsed['tapCount']<=4 and state()['text']=='z'*pulsed['tapCount'] and not state()['heldKeys'])
 o=observe();seq+=1;cancel_id=seq
 rpc.stdin.write(json.dumps({'jsonrpc':'2.0','id':cancel_id,'method':'tools/call','params':{'name':'mac_game_input','arguments':{'observation':o['id'],'node':node(o,'literal-text')['id'],'keys':['right','down'],'tapKeys':['z'],'durationMs':5000,'route':'process'}}})+'\n');rpc.stdin.flush()
 time.sleep(.6)
 rpc.stdin.write(json.dumps({'jsonrpc':'2.0','method':'notifications/cancelled','params':{'requestId':cancel_id,'reason':'owned input cancellation regression'}})+'\n');rpc.stdin.flush()
 # MCP suppresses the cancelled request's response. A fresh call proves the
 # execution lease was released; the fixture proves balanced key releases.
 time.sleep(.2)
 followup=call('mac_doctor',{},'fixture-game-cancel-followup')
 time.sleep(.2)
 ck('cancelled_hold_releases_all_keys',followup['status']=='ok' and not state()['heldKeys'] and .25<state()['lastHoldSeconds']<2)
 print(checks)
finally:
 (OUT/'report.json').write_text(json.dumps({'checks':checks,'binary':BIN,'binarySHA256':hashlib.sha256(Path(BIN).read_bytes()).hexdigest(),'state':state() if (base/'fixture/state.json').exists() else {},'fixturePID':p.pid,'fixtureData':str(base)},ensure_ascii=False,indent=2))
 if p.poll() is None:
  # Standard app termination request, never force terminate or kill.
  if identity and rpc is not None and rpc.poll() is None:
   try:call('mac_app',dict(identity,action='terminate'),check=False)
   except Exception:p.terminate()
  else:p.terminate()
  p.wait(timeout=5)
 log.close();rpc_log.close()
