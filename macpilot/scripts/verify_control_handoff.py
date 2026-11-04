#!/usr/bin/env python3
"""Owned-fixture handoff verification. AX acceptance here is TEST AUTOMATION,
not human consent. There is no production auto-accept API or environment flag.
Run serially on an unlocked desktop; any outside input remains a real failure.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time
import traceback

p = argparse.ArgumentParser()
p.add_argument('--binary', type=Path, required=True)
p.add_argument('--fixture', type=Path, required=True)
p.add_argument('--evidence', type=Path, required=True)
a = p.parse_args()
binary = str(a.binary.resolve())
out = a.evidence.resolve()
out.mkdir(parents=True, exist_ok=False)
root = Path(tempfile.mkdtemp(prefix='macpilot-handoff-'))
env = dict(os.environ, MACPILOT_STATE_DIR=str(root/'state'), MACPILOT_FIXTURE_DIR=str(root/'fixture'))
checks = []
processes = []
host = None
fixture = None
identity = None
completed = False
suite_error = None
cleanup_errors = []
receipt_number = 0
launch_receipts = {}
collected = {}
(out/"calls").mkdir()
# This helper can operate ONLY the test-owned PIDs passed by this runner. Its
# AXPress route exists only in this verification artifact, outside the product.
helper_source = r'''
import AppKit
import ApplicationServices
import Darwin
let pid = Int32(CommandLine.arguments[1])!
let operation = CommandLine.arguments[2]
let expectedIdentity = CommandLine.arguments[3]
let permissions: [String: Any] = ["accessibility": AXIsProcessTrusted(), "postEvent": CGPreflightPostEventAccess(),
    "inputMonitoring": CGPreflightListenEventAccess(), "operation": operation]
print(String(data: try! JSONSerialization.data(withJSONObject: permissions, options: [.sortedKeys]), encoding: .utf8)!)
if operation == "preflight" { exit(0) }
if ["return", "escape", "foreign"].contains(operation) {
 guard AXIsProcessTrusted(), CGPreflightPostEventAccess() else { exit(10) }
}
func requireIdentity() {
 var info = proc_bsdinfo()
 let bytes = proc_pidinfo(pid, PROC_PIDTBSDINFO, 0, &info, Int32(MemoryLayout<proc_bsdinfo>.size))
 guard bytes == Int32(MemoryLayout<proc_bsdinfo>.size), Int32(info.pbi_pid) == pid,
       "\(info.pbi_start_tvsec).\(info.pbi_start_tvusec)" == expectedIdentity else { exit(8) }
}
func requireForeground() {
 requireIdentity()
 guard NSWorkspace.shared.frontmostApplication?.processIdentifier == pid else { exit(9) }
}
requireIdentity()
let app = AXUIElementCreateApplication(pid)
func value(_ node: AXUIElement, _ name: String) -> CFTypeRef? {
 var result: CFTypeRef?; AXUIElementCopyAttributeValue(node, name as CFString, &result); return result
}
func find(_ node: AXUIElement, _ identifier: String, _ depth: Int = 0) -> AXUIElement? {
 if depth > 16 { return nil }
 if value(node, "AXIdentifier") as? String == identifier { return node }
 for child in value(node, "AXChildren") as? [AXUIElement] ?? [] {
  if let result = find(child, identifier, depth + 1) { return result }
 }
 return nil
}
if operation == "activate" { _ = NSRunningApplication(processIdentifier: pid)?.activate(options: []) }
else if operation == "focus-fixture" {
 requireForeground()
 guard let node = find(app, "literal-text") else { exit(3) }
 guard AXUIElementSetAttributeValue(node, "AXFocused" as CFString, kCFBooleanTrue) == .success else { exit(4) }
} else if operation == "start" || operation == "later" {
 requireForeground()
 guard let node = find(app, "macpilot-control-" + operation) else { exit(5) }
 guard AXUIElementPerformAction(node, kAXPressAction as CFString) == .success else { exit(6) }
} else if operation == "return" || operation == "escape" {
 let code: CGKeyCode = operation == "return" ? 36 : 53
 requireForeground()
 let source = CGEventSource(stateID: .privateState)
 let down = CGEvent(keyboardEventSource: source, virtualKey: code, keyDown: true)!
 down.flags = []; down.post(tap: .cghidEventTap)
 // Balance the owned key even when Escape legitimately restores prior focus.
 requireIdentity()
 let up = CGEvent(keyboardEventSource: source, virtualKey: code, keyDown: false)!
 up.flags = []; up.post(tap: .cghidEventTap)
 RunLoop.current.run(until: Date().addingTimeInterval(0.1))
} else if operation == "foreign" {
 requireForeground()
 var point = CGEvent(source: nil)!.location
 point.x += 1
 let event = CGEvent(mouseEventSource: CGEventSource(stateID: .privateState), mouseType: .mouseMoved, mouseCursorPosition: point, mouseButton: .left)!
 event.flags = []; event.post(tap: .cghidEventTap)
 RunLoop.current.run(until: Date().addingTimeInterval(0.1))
 requireForeground()
} else { exit(7) }
'''
(root/'helper.swift').write_text(helper_source)

def read(name):
    try:
        return json.loads((root/'state'/name).read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def fixture_state():
    try:
        return json.loads((root/'fixture/state.json').read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def wait(predicate, seconds=5):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if predicate():
            return True
        time.sleep(.04)
    return False

def ck(name, condition):
    checks.append({'check': name, 'passed': bool(condition)})
    assert condition, (name, read('control-handoff-status.json'), read('input-activity-status.json'), fixture_state())

def receipt(name, args):
    global receipt_number
    receipt_number += 1
    prefix = out/'calls'/('%03d-' % receipt_number + name)
    prefix.with_suffix('.request.json').write_text(json.dumps(args, ensure_ascii=False, indent=2))
    return prefix

def raw(prefix, stdout, stderr, returncode):
    prefix.with_suffix('.stdout.txt').write_text(stdout or '')
    prefix.with_suffix('.stderr.txt').write_text(stderr or '')
    prefix.with_suffix('.exit.json').write_text(json.dumps({'returncode': returncode}))

def call(name, args, check=True):
    prefix = receipt(name, args)
    try:
        r = subprocess.run([binary, 'call', name, '--json', '-'], input=json.dumps(args), capture_output=True, text=True, env=env, timeout=20)
    except subprocess.TimeoutExpired as error:
        raw(prefix, str(error.stdout or ''), str(error.stderr or ''), None)
        raise
    raw(prefix, r.stdout, r.stderr, r.returncode)
    data = json.loads(r.stdout)
    if check and r.returncode:
        raise RuntimeError(data)
    return data

def launch(name, args):
    prefix = receipt(name, args)
    proc = subprocess.Popen([binary, 'call', name, '--json', '-'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
    launch_receipts[proc.pid] = prefix
    prefix.with_suffix('.pid.json').write_text(json.dumps({'pid': proc.pid}))
    proc.stdin.write(json.dumps(args)); proc.stdin.close(); proc.stdin = None
    processes.append(proc)
    return proc

def collect(proc, timeout=15):
    if proc.pid not in collected:
        stdout, stderr = proc.communicate(timeout=timeout)
        raw(launch_receipts[proc.pid], stdout, stderr, proc.returncode)
        collected[proc.pid] = (stdout, stderr)
    return collected[proc.pid]

def finish(proc):
    stdout, stderr = collect(proc)
    return json.loads(stdout)

def helper(pid, operation):
    # Only the owned fixture or exact isolated handoff host is eligible.
    assert pid in {proc.pid for proc in [fixture, host] if proc is not None}
    metadata = next(x for x in call('mac_apps', {})['apps'] if x['pid'] == pid)
    expected = identity['processStartID'] if pid == fixture.pid else read('control-handoff-status.json')['hostStartID']
    assert metadata['processStartID'] == expected
    if operation in ['start', 'later', 'return', 'escape']:
        request = read('control-handoff-request.json')
        status = read('control-handoff-status.json')
        assert status['phase'] == 'pending' and status['id'] == request['id'] and status['taskID'] == request['taskID']
        assert request['goal'] == 'Owned fixture control handoff verification'
    prefix = receipt('fixture-'+operation, {'pid': pid, 'processStartID': expected, 'operation': operation})
    result = subprocess.run([str(root/'helper'), str(pid), operation, expected], capture_output=True, text=True)
    raw(prefix, result.stdout, result.stderr, result.returncode)
    result.check_returncode()

def pending_begin(resume=None):
    old = read('control-handoff-request.json').get('id')
    args = {'operation': 'resume', 'taskID': resume} if resume else {'operation': 'begin', 'goal': 'Owned fixture control handoff verification', 'preserveForeground': False, 'durationSeconds': 90}
    proc = launch('mac_task', args)
    if not wait(lambda: read('control-handoff-request.json').get('id') not in [None, old] or proc.poll() is not None):
        raise AssertionError('New pending handoff request did not publish before timeout')
    if proc.poll() is not None:
        result = finish(proc)
        raise AssertionError('Foreground admission exited before pending: '+repr(result))
    tid = read('control-handoff-request.json')['taskID']
    return proc, tid

def pending_ui():
    return read('control-handoff-status.json').get('phase') == 'pending'

def accept(proc, tid):
    assert wait(pending_ui)
    helper(host.pid, 'start')
    result = finish(proc)
    ck('explicit_fixture_AX_start_grants_exact_task', result.get('controlHandoff') == 'granted_by_user' and read('control-handoff-status.json').get('taskID') == tid)
    assert wait(lambda: read('input-activity-status.json').get('visible'))

def hold(tid, duration=3000):
    observation = call('mac_observe', dict(identity, screenshot=False, taskID=tid))['observation']
    node = next(x for x in observation['nodes'] if x.get('identifier') == 'literal-text')
    return launch('mac_game_input', {'taskID': tid, 'observation': observation['id'], 'node': node['id'], 'route': 'global', 'keys': ['left', 'up'], 'durationMs': duration})

def interrupted_within_bound(name, proc, began, tid, epoch, task_status, host_lost=False):
    # A natural ten-second completion must never satisfy interruption coverage.
    try:
        stdout, stderr = collect(proc, timeout=max(.01, 2 - (time.monotonic() - began)))
    except BaseException as error:
        (out/(name+'-timing.json')).write_text(json.dumps({'check': name, 'triggerMonotonic': began,
            'processCompletionSeconds': time.monotonic() - began, 'failure': repr(error),
            'fixtureState': fixture_state(), 'task': read('task-'+tid+'.json'),
            'grant': read('control-handoff-status.json'), 'expectedEpoch': epoch}, indent=2))
        raise
    result = json.loads(stdout)
    process_seconds = time.monotonic() - began
    remaining = max(0, 2 - process_seconds)
    released = wait(lambda: not fixture_state()['heldKeys'], seconds=remaining)
    remaining = max(0, 2 - (time.monotonic() - began))
    terminal = wait(lambda: read('task-'+tid+'.json').get('status') == task_status
        and (host.poll() is not None if host_lost else
             read('control-handoff-status.json').get('id') == epoch
             and read('control-handoff-status.json').get('phase') == 'revoked'), seconds=remaining)
    elapsed = time.monotonic() - began
    snapshot = fixture_state()
    detail = {'check': name, 'triggerMonotonic': began, 'processCompletionSeconds': process_seconds,
        'releaseAndTerminalSeconds': elapsed, 'lastHoldSeconds': snapshot.get('lastHoldSeconds'),
        'result': result, 'fixtureState': snapshot, 'task': read('task-'+tid+'.json'),
        'grant': read('control-handoff-status.json'), 'expectedEpoch': epoch,
        'hostExited': host.poll() is not None, 'hostLoss': host_lost}
    (out/(name+'-timing.json')).write_text(json.dumps(detail, ensure_ascii=False, indent=2))
    ck(name, proc.returncode is not None and process_seconds < 2 and elapsed < 2 and released and terminal
        and snapshot.get('lastHoldSeconds', 10) < 2
        and result.get('status') in ['error', 'dispatch_interrupted'])
    return result

def capture(display, filename):
    result = call('mac_capture', {'displayID': display, 'maxDimension': 1600})
    shutil.copy2(result['screenshot'], out/filename)

try:
    compiled = subprocess.run(['xcrun', 'swiftc', str(root/'helper.swift'), '-o', str(root/'helper')], capture_output=True, text=True)
    (out/'helper-build.log').write_text(compiled.stdout + compiled.stderr)
    compiled.check_returncode()
    log = (out/'fixture.log').open('w')
    fixture = subprocess.Popen([str(a.fixture.resolve())], env=env, stdout=log, stderr=log)
    assert wait(lambda: fixture_state().get('pid') == fixture.pid, 12)
    app = next(x for x in call('mac_apps', {})['apps'] if x['pid'] == fixture.pid)
    identity = {k: app[k] for k in ['pid', 'processStartID']}
    helper(fixture.pid, 'activate'); assert wait(lambda: fixture_state().get('active'))
    helper(fixture.pid, 'focus-fixture')
    denied = call('mac_app', dict(identity, action='activate'), False)
    ck('no_task_foreground_rejected_before_dispatch', denied.get('code') == 'foreground_task_required')
    denied = call('mac_key', {'route': 'global', 'observation': 'unused', 'node': 'unused', 'key': 'left'}, False)
    ck('no_task_global_rejected_before_observation_or_input', denied.get('code') == 'foreground_task_required' and not fixture_state()['heldKeys'])
    display = call('mac_doctor', {})['displays'][0]['id']
    host = subprocess.Popen([binary, 'input-activity-host', str(root/'state')], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    assert wait(lambda: read('input-activity-status.json').get('pid') == host.pid, 8)
    os.kill(host.pid, signal.SIGSTOP)
    proc, tid = pending_begin()
    time.sleep(2.4)
    ck('delayed_host_never_dispatches_or_activates_target', proc.poll() is None and not fixture_state()['heldKeys'] and fixture_state()['active'])
    os.kill(host.pid, signal.SIGCONT)
    assert wait(pending_ui)
    capture(display, 'pending-handoff.png')
    helper(host.pid, 'return'); time.sleep(.25)
    ck('return_sender_does_not_start_control_delivery_unverified', pending_ui() and proc.poll() is None and not fixture_state()['heldKeys'])
    helper(host.pid, 'later'); denied = finish(proc)
    ck('later_declines_and_restores_previous_focus', denied.get('code') == 'control_handoff_declined' and wait(lambda: fixture_state()['active']))
    proc, tid = pending_begin(); assert wait(pending_ui)
    escape_epoch = read('control-handoff-status.json')['id']
    helper(host.pid, 'escape'); escaped = finish(proc)
    ck('escape_declines_without_input', escaped.get('status') == 'error'
        and escaped.get('code') in ['control_handoff_declined', 'control_handoff_cancelled']
        and escaped.get('disposition', {}).get('delivery') == 'not_delivered'
        and escaped.get('outcome', {}).get('dispatch') == 'not_sent'
        and read('control-handoff-status.json').get('id') == escape_epoch
        and read('control-handoff-status.json').get('phase') == 'declined'
        and read('task-'+tid+'.json').get('status') == 'interrupted'
        and wait(lambda: fixture_state()['active']) and not fixture_state()['heldKeys'])
    proc, tid = pending_begin(); assert wait(pending_ui)
    cancelled = call('mac_task', {'operation': 'cancel', 'taskID': tid}); finish(proc)
    ck('awaiting_task_cancel_is_available_and_restores_focus', cancelled['status'] == 'task_cancelled' and wait(lambda: fixture_state()['active']) and not fixture_state()['heldKeys'])
    proc, tid = pending_begin(); accept(proc, tid)
    active = read('input-activity-status.json'); (out/'active-status.json').write_text(json.dumps(active, indent=2))
    ck('active_feedback_on_all_displays_is_transparent', active['inputTransparent'] and not active['takesFocus'] and active['noticePanelCount'] == active['screenCount'] and active['edgePanelCount'] == 4*active['screenCount'])
    capture(display, 'active-handoff.png')
    observation = call('mac_observe', dict(identity, screenshot=False, taskID=tid))['observation']
    button = next(x for x in observation['nodes'] if x.get('identifier') == 'increment')['frame']
    before = fixture_state()['buttonCount']
    clicked = call('mac_click', {'taskID': tid, 'observation': observation['id'], 'space': 'screen', 'route': 'global',
        'x': button['x'] + button['width']/2, 'y': button['y'] + button['height']/2})
    ck('short_mouse_click_passes_through_session_feedback', clicked['status'] == 'dispatched_unverified' and wait(lambda: fixture_state()['buttonCount'] == before + 1))
    helper(fixture.pid, 'focus-fixture')
    input_proc = hold(tid)
    ck('owned_keyboard_events_are_attributed_without_revocation', wait(lambda: len(fixture_state()['heldKeys']) == 2) and read('control-handoff-status.json')['phase'] == 'granted')
    result = finish(input_proc)
    ck('normal_action_release_keeps_session_notice', result['status'] == 'dispatched_unverified' and not fixture_state()['heldKeys'] and read('input-activity-status.json')['controlActive'])
    input_proc = hold(tid, 10000); assert wait(lambda: len(fixture_state()['heldKeys']) == 2)
    cancel_epoch = read('control-handoff-status.json')['id']; triggered = time.monotonic()
    call('mac_task', {'operation': 'cancel', 'taskID': tid})
    interrupted_within_bound('task_cancel_interrupts_before_natural_completion', input_proc, triggered, tid, cancel_epoch, 'cancelled')
    ck('task_cancel_releases_keys_and_ends_active_feedback', wait(lambda: not fixture_state()['heldKeys'] and read('input-activity-status.json').get('presentationPhase') == 'ended'
        and not read('input-activity-status.json').get('controlActive') and read('input-activity-status.json').get('edgePanelCount') == 0))
    capture(display, 'ended-handoff.png')
    proc, tid = pending_begin(); accept(proc, tid)
    helper(fixture.pid, 'foreign')
    ck('foreign_input_while_idle_revokes_task', wait(lambda: read('control-handoff-status.json').get('phase') == 'revoked'))
    rejected = call('mac_activate', dict(identity, taskID=tid), False)
    ck('next_action_cannot_reuse_revoked_grant', rejected.get('code') in ['task_interrupted', 'control_handoff_required'])
    old_epoch = read('control-handoff-status.json')['id']
    proc, _ = pending_begin(resume=tid); assert wait(pending_ui)
    ck('resume_requires_new_explicit_handoff', read('control-handoff-status.json')['id'] != old_epoch and proc.poll() is None)
    accept(proc, tid); helper(fixture.pid, 'focus-fixture')
    input_proc = hold(tid, 10000); assert wait(lambda: len(fixture_state()['heldKeys']) == 2)
    foreign_epoch = read('control-handoff-status.json')['id']; triggered = time.monotonic()
    helper(fixture.pid, 'foreign')
    interrupted_within_bound('foreign_input_interrupts_before_natural_completion', input_proc, triggered, tid, foreign_epoch, 'interrupted')
    ck('inflight_revoke_releases_owned_keys', wait(lambda: not fixture_state()['heldKeys']))
    assert wait(lambda: read('task-'+tid+'.json').get('status') == 'interrupted')
    proc, _ = pending_begin(resume=tid); accept(proc, tid); helper(fixture.pid, 'focus-fixture')
    input_proc = hold(tid, 10000); assert wait(lambda: len(fixture_state()['heldKeys']) == 2)
    lost_epoch = read('control-handoff-status.json')['id']; triggered = time.monotonic()
    os.kill(host.pid, signal.SIGTERM)
    interrupted_within_bound('host_loss_interrupts_before_natural_completion', input_proc, triggered, tid, lost_epoch, 'interrupted', host_lost=True)
    ck('host_loss_stops_dispatch_and_releases_keys', wait(lambda: not fixture_state()['heldKeys']))
    capture(display, 'after-handoff.png')
    completed = True
except BaseException as error:
    suite_error = repr(error)
    (out/'failure.log').write_text(traceback.format_exc())
finally:
    def cleanup(name, action):
        try:
            action()
        except BaseException as error:
            cleanup_errors.append({'operation': name, 'error': repr(error)})
            with (out/'cleanup-failures.log').open('a') as stream:
                stream.write(name + '\n' + traceback.format_exc() + '\n')
    if host and host.poll() is None:
        cleanup('resume owned host', lambda: os.kill(host.pid, signal.SIGCONT))
    for proc in processes:
        if proc.poll() is None:
            request = read('control-handoff-request.json')
            if request.get('taskID'):
                cleanup('cancel owned pending task', lambda: call('mac_task', {'operation': 'cancel', 'taskID': request['taskID']}, False))
            def stop_worker(proc=proc):
                try:
                    collect(proc, timeout=8)
                except subprocess.TimeoutExpired:
                    proc.terminate(); collect(proc, timeout=5)
            cleanup('stop owned worker', stop_worker)
        elif proc.pid not in collected:
            cleanup('collect exited owned worker', lambda proc=proc: collect(proc, timeout=1))
    if host and host.poll() is None:
        def stop_host():
            host.terminate(); host.wait(timeout=5)
        cleanup('stop owned host', stop_host)
    if fixture and fixture.poll() is None:
        def stop_fixture():
            fixture.terminate(); fixture.wait(timeout=5)
        cleanup('stop owned fixture', stop_fixture)
    if 'log' in locals():
        cleanup('close fixture log', log.close)
    report = {'checks': checks, 'binary': binary, 'binarySHA256': hashlib.sha256(Path(binary).read_bytes()).hexdigest(),
              'isolatedState': str(root), 'acceptance': 'fixture AX automation; not human consent',
              'completed': completed, 'suiteStatus': 'passed' if completed and suite_error is None and not cleanup_errors else 'failed',
              'bodyFailure': suite_error, 'cleanupFailures': cleanup_errors,
              'displayCoverage': 'actual current screen count; other layouts require unit/physical evidence'}
    (out/'report.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
if report['suiteStatus'] != 'passed':
    raise SystemExit(1)
