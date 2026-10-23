#!/usr/bin/env python3
"""Production API checks on an owned synthetic AppKit fixture. No global install.

Build macpilot-capability-fixture first. Optional image checks need explicit
--python and --model paths; omission is reported as NOT_RUN, never as a pass.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import struct
import zlib
import plistlib
import time
import uuid

from capability_report import CapabilityReport


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


class Fixture:
    def __init__(self, args):
        self.args, self.out, self.sequence = args, args.evidence, 0
        self.root = Path(tempfile.mkdtemp(prefix='macpilot-capabilities-'))
        self.directory = self.root / 'fixture'; self.directory.mkdir()
        self.env = dict(os.environ, MACPILOT_STATE_DIR=str(self.root / 'controller'))
        self.log = (self.out / 'fixture.log').open('w')
        # AppKit lifecycle identity must come from an actual app bundle. A bare
        # SwiftPM executable can temporarily disappear from NSRunningApplication.
        bundle = self.root / 'CapabilityFixture.app'
        executable = bundle / 'Contents/MacOS/capability-fixture'
        executable.parent.mkdir(parents=True)
        shutil.copy2(args.fixture, executable)
        with (bundle/'Contents/Info.plist').open('wb') as stream:
            plistlib.dump(dict(CFBundleIdentifier='local.macpilot.capability-fixture.'+uuid.uuid4().hex,CFBundleExecutable=executable.name,
                               CFBundleName='MacPilot capability fixture',CFBundlePackageType='APPL',CFBundleVersion='1',
                               CFBundleShortVersionString='1.0',LSMinimumSystemVersion='14.0',NSHighResolutionCapable=True),stream)
        subprocess.run(['/usr/bin/codesign','--force','--sign','-',str(bundle)],check=True,capture_output=True)
        # launchd opens these paths itself. Keep them on the main disk: external
        # volume logs would require a new helper's independent file permission.
        for name in ['fixture.stdout.log','fixture.stderr.log']: (self.root/name).touch(mode=0o600)
        self.process = subprocess.Popen(['/usr/bin/open','-n','-W','--stdout',str(self.root/'fixture.stdout.log'),
                                         '--stderr',str(self.root/'fixture.stderr.log'),str(bundle),'--args',str(self.directory)],
                                        stdout=self.log,stderr=self.log)
        self.wait(lambda: (self.directory / 'state.json').exists(), 8)
        self.fixture_pid = self.state()['pid']
        app = next(a for a in self.call('mac_apps', {})['apps'] if a['pid'] == self.fixture_pid)
        self.identity = {k: app[k] for k in ['pid', 'processStartID']}
        self.identity['windowID'] = self.state()['windowID']

    @staticmethod
    def wait(predicate, seconds=3):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if predicate(): return
            time.sleep(.03)
        raise TimeoutError('Owned fixture did not settle')

    def state(self): return json.loads((self.directory / 'state.json').read_text())

    def command(self, action, delay=0):
        value = dict(id=str(uuid.uuid4()), action=action, delay=delay)
        path = self.directory / 'command.json'
        dump(path.with_suffix('.tmp'), value); path.with_suffix('.tmp').replace(path)
        if delay == 0 and action != 'quit': self.wait(lambda: self.state()['command'] == value['id'])

    def start(self, tool, arguments):
        process = subprocess.Popen([str(self.args.binary), 'call', tool, '--json', '-'], stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=self.env)
        process.stdin.write(json.dumps(arguments, ensure_ascii=False)); process.stdin.close(); process.stdin = None
        return process

    def finish(self, tool, process, allow_error=False):
        stdout, stderr = process.communicate(timeout=75)
        self.sequence += 1
        (self.out / f'{self.sequence:03}-{tool}.stderr').write_text(stderr)
        value = json.loads(stdout); dump(self.out / f'{self.sequence:03}-{tool}.json', value)
        if process.returncode and not allow_error:
            dump(self.out/'failure-target-state.json',dict(exitCode=self.process.poll(),state=self.state(),error=value))
            raise RuntimeError(value)
        return value

    def call(self, tool, arguments, allow_error=False): return self.finish(tool, self.start(tool, arguments), allow_error)

    def external_input(self):
        sender = subprocess.Popen([str(self.args.fixture),'--external-input'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=self.env)
        return self.finish('foreign-input-probe',sender)

    def observe(self, screenshot=False, task=None):
        args = dict(self.identity, screenshot=screenshot, maxNodes=500, maxDepth=20)
        if task: args['taskID'] = task
        deadline = time.monotonic() + 3
        while True:
            value = self.call('mac_observe', args, True)
            if 'observation' in value: return value['observation']
            if value.get('code') not in ['ambiguous_ax_window','stale_observation','window_unavailable','app_metadata_unavailable'] or time.monotonic() > deadline: raise RuntimeError(value)
            time.sleep(.06)

    @staticmethod
    def node(observation, identifier):
        nodes = [n for n in observation['nodes'] if n.get('identifier') == identifier]
        assert len(nodes) == 1, (identifier, nodes)
        return nodes[0]

    def ax(self, identifier, operation='action', **kwargs):
        observation = self.observe()
        return self.call('mac_ax', dict(observation=observation['id'], node=self.node(observation, identifier)['id'], operation=operation, **kwargs))

    def close(self):
        dump(self.out / 'fixture-final.json', self.state())
        self.command('quit') if self.process.poll() is None else None
        self.process.wait(timeout=5); self.log.close()
        for name in ['fixture.stdout.log','fixture.stderr.log']:
            if (self.root/name).exists(): shutil.copy2(self.root/name,self.out/name)
        # Own UI host finishes asynchronously after the selected target exits.
        path = self.root / 'controller/overlay-status.json'
        deadline = time.monotonic() + 4
        while path.exists() and json.loads(path.read_text()).get('status') != 'stopped' and time.monotonic() < deadline:
            time.sleep(.05)
        shutil.rmtree(self.root)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--binary', type=Path, required=True); p.add_argument('--fixture', type=Path, required=True)
    p.add_argument('--evidence', type=Path, required=True)
    p.add_argument('--stage', choices=['all','image'], default='all')
    p.add_argument('--python', type=Path); p.add_argument('--model', type=Path)
    args = p.parse_args(); args.binary = args.binary.resolve(); args.fixture = args.fixture.resolve(); args.evidence = args.evidence.resolve()
    # Do not resolve the interpreter: a symlink is part of a Python venv's identity.
    if args.python: args.python = args.python.absolute()
    if args.model: args.model = args.model.resolve()
    args.evidence.mkdir(parents=True, exist_ok=False)
    checks = []; f = None
    def ck(feature, name, condition, **detail):
        checks.append(dict(feature=feature, id=name, status='PASS' if condition else 'FAIL', **detail))
        dump(args.evidence / 'checks.json', checks)
        report.checkpoint()
        if not condition: raise AssertionError((feature, name, detail))
    def condition(identifier, predicate, **kw): return dict(selector={'identifier': identifier}, predicate=predicate, **kw)
    report = CapabilityReport(args.evidence / 'result.json', args.stage, hashlib.sha256(args.binary.read_bytes()).hexdigest(), checks)
    with report.run(cleanup=lambda: f.close() if f else None):
        f = Fixture(args)
        if args.stage == 'all':
            def wait(c, **kw): return f.call('mac_wait_for', dict(f.identity, condition=c, timeoutMs=2500, **kw))
            r = wait(condition('ready', 'disabled')); ck('wait','disabled',r['matches'])
            f.command('enable', .4); r = wait(condition('ready','enabled')); ck('wait','delayed_enabled',r['matches'] and r['attempts'] > 1)
            f.command('replace', .3); ck('wait','replaced_node',wait(condition('status','equals',text='complete'))['matches'])
            f.command('replace_silent', .3); ck('wait','poll_without_notification',wait(condition('status','contains',text='silent'))['matches'])
            ck('wait','focused',wait(condition('literal','focused'))['matches'])
            f.command('hide', .3); ck('wait','disappeared',wait(condition('status','absent'))['matches'])
            f.command('replace', .3); ck('wait','appeared',wait(condition('status','exists'))['matches'])
            f.command('move'); r = wait({'predicate':'stable','stableMs':250}); ck('wait','geometry_settled',r['matches'] and r['elapsedMilliseconds'] >= 400)
            # Use one explicit poll interval to test a completed false predicate at
            # the same 200ms deadline, rather than relying on a late scan fitting.
            # AX notifications may still wake early; partial coverage must fail.
            r = f.call('mac_wait_for',dict(f.identity,condition=condition('not-there','exists'),timeoutMs=200,pollMs=200))
            ck('wait','timeout_is_not_success',r['status']=='predicate_timeout' and r['matches'] is False
               and r['outcome']['effect']=='predicate_not_met'
               and r['observation']['coverage']=='collected_window_tree' and r['observation']['diagnostics']==[])
            r = f.call('mac_wait_for',dict(f.identity,condition=condition('not-there','absent'),maxNodes=1),True)
            ck('wait','partial_cannot_prove_absence',r.get('code')=='partial_coverage')
            f.command('duplicate'); r = f.call('mac_wait_for',dict(f.identity,condition=condition('ready','exists')),True)
            ck('wait','duplicate_rejected',r.get('code')=='ambiguous_target')
            r = f.ax('noop'); ck('outcome','noop_unverified',r['status']=='action_requested' and r['outcome']['effect']=='unverified' and f.state()['clicks']==0)
            r = f.ax('literal','set_value',text='literal 한글 😀'); ck('outcome','value_postcondition_scoped',r['outcome']['scope']=='operation_postcondition')
            # Tracing is opt-in. Default records omit values; screenshots require another opt-in.
            r = f.call('mac_trace',{'operation':'status'}); ck('trace','default_disabled',not r['settings']['enabled'] and r['count']==0)
            f.call('mac_trace',{'operation':'configure','enabled':True,'maxEntries':2})
            r = f.ax('increment'); trace = f.call('mac_trace',{'operation':'read','traceID':r['traceID']})['trace']
            ck('trace','before_after_no_text',trace['before'] is not None and trace['after'] is not None and 'literal 한글' not in json.dumps(trace,ensure_ascii=False))
            f.call('mac_trace',{'operation':'configure','captureText':True,'captureScreenshots':True})
            r = f.ax('increment'); trace = f.call('mac_trace',{'operation':'read','traceID':r['traceID']})['trace']
            ck('trace','secure_values_omitted','PROBE_SECRET_MUST_NOT_APPEAR' not in json.dumps(trace))
            for phase in ['before','after']:
                entry = trace[phase]; image = f.root / 'controller' / entry['screenshot']
                ck('trace',f'{phase}_frame_integrity',hashlib.sha256(image.read_bytes()).hexdigest()==entry['screenshotSHA256'])
                shutil.copy2(image,args.evidence / f'trace-{phase}.png')
            r = f.call('mac_trace',{'operation':'export','traceID':trace['id']})
            shutil.copy2(r['path'],args.evidence / 'trace.html')
            ck('trace','html_export',Path(r['path']).read_text().startswith('<!doctype html>'))
            f.ax('noop'); r = f.call('mac_trace',{'operation':'list'}); ck('trace','bounded_retention',r['count']==2)
            (f.root/'controller/trace-settings.json').write_text('invalid')
            before=f.state()['noops']; r=f.ax('noop')
            ck('trace','failed_trace_does_not_repeat_action',f.state()['noops']==before+1 and r['trace']['status']=='preparation_failed' and r['outcome']['effect']=='unverified')
            f.call('mac_trace',{'operation':'configure','enabled':False})
            # Workflow parameters are literals. Entire plan validation precedes mutations.
            def press(expected): return dict(action='press',selector={'identifier':'increment'},postcondition=condition('counter','equals',text=str(expected)))
            plan = dict(name='fixture_recipe',parameters=['text'],steps=[dict(action='set_value',selector={'identifier':'literal'},parameter='text',postcondition=dict(selector={'identifier':'literal'},predicate='equals',textParameter='text')),press(3)])
            f.call('mac_workflow',{'operation':'save','definition':plan})
            run_id = str(uuid.uuid4()); literal = 'literal $(not executed) `x` 한글 😀'
            run = dict(f.identity, operation='run',name='fixture_recipe',parameters={'text':literal},runID=run_id)
            r = f.call('mac_workflow',run); ck('workflow','parameterized_recipe',r['status']=='workflow_verified' and f.state()['text']==literal and f.state()['clicks']==3, result=r)
            r = f.call('mac_workflow',run); ck('workflow','same_run_not_replayed',r['status']=='workflow_run_exists' and f.state()['clicks']==3)
            r = f.call('mac_workflow',dict(run,parameters={'text':'different'}),True); ck('workflow','run_mismatch_rejected',r.get('code')=='workflow_run_mismatch' and f.state()['clicks']==3)
            bad = dict(name='invalid_late',steps=[press(4),{'action':'shell'}]); r = f.call('mac_workflow',dict(f.identity,operation='run',definition=bad),True)
            ck('workflow','late_invalid_no_mutation',r.get('code')=='invalid_workflow' and f.state()['clicks']==3)
            fail_plan = dict(name='failed_postcondition',steps=[press(99),press(5)])
            r = f.call('mac_workflow',dict(f.identity,operation='run',definition=fail_plan)); ck('workflow','failed_postcondition_stops',r['status']=='workflow_postcondition_failed' and f.state()['clicks']==4 and r['run']['mutationsDispatched']==1)
            r = f.call('mac_workflow',{'operation':'run_status','runID':run_id}); ck('workflow','durable_receipt',r['run']['status']=='verified' and r['run']['stepsCompleted']==2)
            task = f.call('mac_task',dict(f.identity,operation='begin',goal='cancel owned wait',expected='no mutation',preserveForeground=False))['task']['id']
            pending = f.start('mac_workflow',dict(f.identity,taskID=task,operation='run',definition={'name':'cancel_wait','steps':[dict(action='wait',condition=condition('not-there','exists'),timeoutMs=10000),press(5)]},runID=str(uuid.uuid4())))
            time.sleep(.4); f.call('mac_task',{'operation':'cancel','taskID':task}); r=f.finish('mac_workflow',pending,True)
            runs=f.call('mac_workflow',{'operation':'runs','taskID':task})['runs']
            ck('workflow','cancellation_receipt',len(runs)==1 and runs[0]['status']=='cancelled' and f.state()['clicks']==4,result=r)
            # Real event tap with a controlled second process. This is not a physical-device claim.
            f.call('mac_app',dict(pid=f.identity['pid'],processStartID=f.identity['processStartID'],action='activate')); f.ax('literal','focus')
            task = f.call('mac_task',dict(f.identity,operation='begin',goal='yield fixture keys',expected='balanced releases',preserveForeground=False))['task']['id']
            o=f.observe(task=task); key_args=dict(taskID=task,observation=o['id'],node=f.node(o,'literal')['id'],route='global',keys=['right'],durationMs=2000)
            pending=f.start('mac_game_input',key_args); f.wait(lambda:124 in f.state()['held'],8)
            f.external_input(); r=f.finish('mac_game_input',pending,True); f.wait(lambda:not f.state()['held'])
            ck('interrupt','foreign_event_stops_and_releases',r.get('code')=='user_input_interrupted' and f.state()['held']==[],result=r)
            status=f.call('mac_task',{'operation':'status','taskID':task}); ck('interrupt','task_interrupted',status['task']['status']=='interrupted')
            r=f.call('mac_observe',dict(f.identity,taskID=task),True); ck('interrupt','blocked_until_explicit_resume',r.get('code')=='task_interrupted')
            f.call('mac_task',{'operation':'resume','taskID':task})
            stale=f.call('mac_game_input',dict(key_args,durationMs=100),True)
            ck('interrupt','resume_invalidates_old_observation',stale.get('code')=='missing_observation',result=stale)
            o=f.observe(task=task)
            r=f.call('mac_game_input',dict(key_args,observation=o['id'],node=f.node(o,'literal')['id'],durationMs=200))
            ck('interrupt','owned_events_do_not_self_interrupt',r['status']=='dispatched_unverified' and f.state()['held']==[],result=r)
            f.call('mac_task',{'operation':'finish','taskID':task})
        # Image search stays disabled without importing optional Python modules.
        r=f.call('mac_image_search',{'operation':'search','observation':f.observe()['id'],'query':'folder'},True)
        ck('image','disabled_by_default',r.get('code')=='image_search_disabled')
        if args.python and args.model:
            f.call('mac_image_search',dict(operation='configure',enabled=True,pythonPath=str(args.python),modelPath=str(args.model),device='mps'))
            control=f.observe(True); button=f.node(control,'increment')['frame']; frame=control['windowFrame']
            sx=control['pixelWidth']/frame['width']; sy=control['pixelHeight']/frame['height']
            region=dict(x=int((button['x']-frame['x'])*sx),y=int((button['y']-frame['y'])*sy),width=int(button['width']*sx),height=int(button['height']*sy))
            recognized=f.call('mac_image_search',dict(operation='search',observation=control['id'],query='Increment',regions=[region]))
            ck('image','visionkit_transcript_reaches_hybrid_ranker',recognized['candidates'][0]['text'].strip()=='Increment' and recognized['vectorsComputed']==3,result=recognized)
            f.command('image_grid'); time.sleep(.5); o=f.observe(True)
            shutil.copy2(o['screenshot'],args.evidence/'image-grid.png')
            def search(query,**kw):
                image=f.observe(True)
                return f.call('mac_image_search',dict(operation='search',observation=image['id'],query=query,**kw))
            r=search('folder'); target=next(v for v in f.state()['gridCenters'] if v['id']=='folder'); rect=r['candidates'][0]['imageRect']
            ck('image','real_model_locates_folder',r['accepted'] and abs((rect['x']+rect['width']/2)/o['pixelWidth']-target['x'])<.03 and abs((rect['y']+rect['height']/2)/o['pixelHeight']-target['y'])<.03,result=r)
            template=f.root/'folder-template.png'
            subprocess.run([str(args.python),'-I','-c','from PIL import Image; import sys,json; r=json.loads(sys.argv[2]); im=Image.open(sys.argv[1]); im.crop((r["x"],r["y"],r["x"]+r["width"],r["y"]+r["height"])).save(sys.argv[3])',o['screenshot'],json.dumps(rect),str(template)],check=True)
            image=f.observe(True)
            matched=f.call('mac_image_search',dict(operation='search',observation=image['id'],templatePath=str(template)))
            ck('image','template_retrieval',matched['accepted'] and matched['candidates'][0]['score']>.99,result=matched)
            image=f.observe(True)
            roi=f.call('mac_image_search',dict(operation='search',observation=image['id'],query='folder',regions=[rect]))
            ck('image','explicit_region_scope',roi['accepted'] and roi['candidateCount']==1 and roi['candidates'][0]['source']=='explicit_region')
            # Valid PNG with a compressed, oversized canvas; reject metadata before decoding.
            def chunk(kind,data): return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
            oversized=f.root/'oversized.png'
            oversized.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',9000,1,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(b'\0'+b'\0'*27000))+chunk(b'IEND',b''))
            image=f.observe(True)
            invalid=f.call('mac_image_search',dict(operation='search',observation=image['id'],templatePath=str(oversized),regions=[rect]),True)
            ck('image','oversized_template_rejected',invalid.get('code')=='invalid_image_template',result=invalid)
            r=search('folder'); ck('image','vector_cache_reused',r['model']['cacheOnly'] and r['vectorsComputed']==0 and r['cacheHits']>0,result=r)
            r=search('play button'); target=next(v for v in f.state()['gridCenters'] if v['id']=='play'); rect=r['candidates'][0]['imageRect']
            ck('image','second_query_reuses_candidates',r['accepted'] and r['cacheHits']>=12 and abs((rect['x']+rect['width']/2)/o['pixelWidth']-target['x'])<.03 and abs((rect['y']+rect['height']/2)/o['pixelHeight']-target['y'])<.03,result=r)
            r=search('a red double decker bus'); ck('image','absent_object_abstention',not r['accepted'],result=r)
            r=search('folder',minimumScore=1); ck('image','threshold_abstention',not r['accepted'])
            f.command('duplicate_images'); time.sleep(.2); r=search('folder'); ck('image','duplicate_locations_abstain',not r['accepted'],result=r)
            o=f.observe(True); pending=f.start('mac_image_search',dict(operation='search',observation=o['id'],query='unseen folder query'))
            time.sleep(.3); f.command('change_image'); r=f.finish('mac_image_search',pending,True)
            ck('image','changed_pixels_invalidate',r.get('code')=='image_changed_during_search',result=r)
            f.call('mac_image_search',{'operation':'configure','enabled':False})
        else: checks.append(dict(feature='image',id='real_model_checks',status='NOT_RUN',reason='Explicit local Python/model not supplied'))
        print(json.dumps(dict(passed=sum(c['status']=='PASS' for c in checks),failed=sum(c['status']=='FAIL' for c in checks),notRun=sum(c['status']=='NOT_RUN' for c in checks))), flush=True)


if __name__=='__main__': main()
