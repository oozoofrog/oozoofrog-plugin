#!/usr/bin/env python3
"""Serial desktop regression on isolated fixture/state; never touches live sessions.

Exercises actual helper process exit while the target app/window stays alive.
No keyboard, mouse, native consent, installed cache or TCC changes are used.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import select
import shutil
import subprocess
import tempfile
import time
import traceback

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--binary', type=Path, required=True)
parser.add_argument('--fixture', type=Path, required=True)
parser.add_argument('--evidence', type=Path, required=True)
args = parser.parse_args()
binary = str(args.binary.resolve())
out = args.evidence.resolve()
out.mkdir(parents=True, exist_ok=False)
root = Path(tempfile.mkdtemp(prefix='macpilot-overlay-lifecycle-'))
env = dict(os.environ, MACPILOT_STATE_DIR=str(root/'state'), MACPILOT_FIXTURE_DIR=str(root/'fixture'))
checks, cleanup_errors, responses = [], [], []
completed, body_error = False, None
fixture, identity, helper = None, None, None
servers, owned_overlays, owned_previews, pointer_hashes = [], [], [], {}
sequence = 0

IDENTITY_SOURCE = r'''
import Foundation
import CoreGraphics
import Darwin
let pid = Int32(CommandLine.arguments[1])!
var info = proc_bsdinfo()
let size = Int32(MemoryLayout<proc_bsdinfo>.size)
let alive = proc_pidinfo(pid, PROC_PIDTBSDINFO, 0, &info, size) == size && Int32(info.pbi_pid) == pid
let rows = CGWindowListCopyWindowInfo([.optionAll, .excludeDesktopElements], kCGNullWindowID) as? [[String: Any]] ?? []
let windows = rows.filter { ($0[kCGWindowOwnerPID as String] as? Int32) == pid }
var result: [String: Any] = ["pid": pid, "processStartID": alive ? "\(info.pbi_start_tvsec).\(info.pbi_start_tvusec)" : NSNull(),
    "windowIDs": windows.compactMap { ($0[kCGWindowNumber as String] as? NSNumber)?.intValue }]
print(String(data: try! JSONSerialization.data(withJSONObject: result), encoding: .utf8)!)
'''


def dump(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2))


def state(name, directory=None):
    try:
        return json.loads(((directory or root/'state')/name).read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def wait(predicate, seconds=4):
    deadline = time.monotonic()+seconds
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(.04)
    return False


def check(name, value, **detail):
    checks.append(dict(check=name, passed=bool(value), **detail))
    save_report()
    if not value:
        raise AssertionError((name, detail))


def save_report():
    dump(out/'report.json', dict(schema='macpilot-overlay-lifecycle/1', suiteStatus='passed' if completed and not body_error and not cleanup_errors else 'failed',
        completed=completed and not cleanup_errors, bodyFailure=body_error, cleanupFailures=cleanup_errors,
        checks=checks, binary=binary, binarySHA256=hashlib.sha256(Path(binary).read_bytes()).hexdigest(),
        isolatedState=str(root), stateRetained=root.exists(), coverage='owned fixture; real CLI 30-second idle expiry; no physical input or human acceptance'))


def receipt(name, arguments):
    global sequence
    sequence += 1
    prefix = out/('%03d-' % sequence + name)
    dump(prefix.with_suffix('.request.json'), arguments)
    return prefix


def call(name, arguments, allow_error=False):
    prefix = receipt(name, arguments)
    result = subprocess.run([binary, 'call', name, '--json', '-'], input=json.dumps(arguments), capture_output=True,
                            text=True, env=env, timeout=20)
    prefix.with_suffix('.stdout.txt').write_text(result.stdout)
    prefix.with_suffix('.stderr.txt').write_text(result.stderr)
    dump(prefix.with_suffix('.exit.json'), dict(exitCode=result.returncode))
    value = json.loads(result.stdout)
    if result.returncode and not allow_error:
        raise RuntimeError(value)
    return value


def process(pid):
    result = subprocess.run([str(helper), str(pid)], capture_output=True, text=True, timeout=5)
    result.check_returncode()
    return json.loads(result.stdout)


def remember(status, kind='overlay'):
    record = {key: status[key] for key in ['pid', 'processStartID']}
    record['windowIDs'] = process(record['pid'])['windowIDs']
    destination = owned_overlays if kind == 'overlay' else owned_previews
    if record not in destination:
        destination.append(record)
    return record


def exited(record):
    value = process(record['pid'])
    return value.get('processStartID') != record['processStartID'] and not set(record['windowIDs']).intersection(value['windowIDs'])


def pointer(observation, task_id=None):
    value = dict(observation=observation['id'], x=.5, y=.5, space='normalized', label='수명 검증')
    if task_id:
        value['taskID'] = task_id
    result = call('mac_pointer', value)
    directory = root/'state'/('task-'+task_id) if task_id else root/'state'
    pointer_hashes[str(directory/'pointer.json')] = hashlib.sha256((directory/'pointer.json').read_bytes()).hexdigest()
    return remember(result['desktopOverlay'])


def observe(task_id=None, server=None):
    value = dict(identity, screenshot=False)
    if task_id:
        value['taskID'] = task_id
    result = server.tool('mac_observe', value) if server else call('mac_observe', value)
    return result['observation']


class MCP:
    def __init__(self):
        self.proc = subprocess.Popen([binary, 'mcp'], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=(out/('mcp-'+str(len(servers))+'.stderr.log')).open('w'), env=env)
        self.buffer = b''
        self.id = 0
        servers.append(self)
        self.send(dict(jsonrpc='2.0', id=0, method='initialize', params=dict(protocolVersion='2025-11-25')))
        response = self.read()
        if response.get('id') != 0 or 'result' not in response:
            raise RuntimeError(response)

    def send(self, value):
        self.proc.stdin.write((json.dumps(value)+'\n').encode()); self.proc.stdin.flush()

    def read(self, timeout=15):
        deadline = time.monotonic()+timeout
        while time.monotonic() < deadline:
            if b'\n' in self.buffer:
                line, self.buffer = self.buffer.split(b'\n', 1)
                return json.loads(line)
            ready, _, _ = select.select([self.proc.stdout], [], [], max(0, deadline-time.monotonic()))
            if ready:
                chunk = os.read(self.proc.stdout.fileno(), 65536)
                if not chunk:
                    break
                self.buffer += chunk
        raise TimeoutError('Owned MCP did not respond')

    def tool(self, name, arguments):
        self.id += 1
        prefix = receipt('mcp-'+name, arguments)
        self.send(dict(jsonrpc='2.0', id=self.id, method='tools/call', params=dict(name=name, arguments=arguments)))
        response = self.read()
        dump(prefix.with_suffix('.response.json'), response)
        if response.get('id') != self.id or response.get('result', {}).get('isError'):
            raise RuntimeError(response)
        return response['result']['structuredContent']


try:
    source = root/'identity.swift'; source.write_text(IDENTITY_SOURCE); helper = root/'identity'
    build = subprocess.run(['xcrun', 'swiftc', str(source), '-o', str(helper)], capture_output=True, text=True)
    (out/'identity-build.log').write_text(build.stdout+build.stderr); build.check_returncode()
    fixture_log = (out/'fixture.log').open('w')
    fixture = subprocess.Popen([str(args.fixture.resolve())], env=env, stdout=fixture_log, stderr=fixture_log)
    assert wait(lambda: (root/'fixture/state.json').exists(), 12)
    app = next(item for item in call('mac_apps', {})['apps'] if item['pid'] == fixture.pid)
    identity = {key: app[key] for key in ['pid', 'processStartID']}

    # A synthetic old observation in private test state proves cleanup cannot
    # depend on its freshness. The actual target window remains alive.
    observation = observe(); live = pointer(observation)
    path = root/'state'/(observation['id']+'.json')
    old = json.loads(path.read_text()); old['created'] -= 31; dump(path, old)
    rejected = call('mac_cursors', dict(operation='list', observation=observation['id']), allow_error=True)
    check('stale_observation_really_rejected', rejected.get('code') == 'stale_observation', response=rejected)
    stopped = call('mac_cursors', dict(operation='stop'))
    check('explicit_stop_confirms_hidden_ack_and_exact_exit', stopped.get('status') == 'overlay_stopped'
          and stopped.get('processExited') and stopped.get('pid') == live['pid']
          and stopped.get('processStartID') == live['processStartID'] and exited(live), response=stopped)
    again = call('mac_cursors', dict(operation='stop'))
    check('stop_is_idempotent_without_observation', again.get('status') == 'overlay_not_running' and not again.get('running'), response=again)
    observation = observe(); restarted = pointer(observation)
    check('immediate_ensure_restarts_after_confirmed_exit', restarted != live and process(restarted['pid'])['processStartID'] == restarted['processStartID'])

    preview = call('mac_preview', dict(operation='start', observation=observation['id']))
    preview_record = remember(preview, 'preview')
    call('mac_preview', dict(operation='stop'))
    check('preview_stop_keeps_independent_feedback', wait(lambda: exited(preview_record))
          and process(restarted['pid'])['processStartID'] == restarted['processStartID']
          and state('overlay-status.json').get('running', True) and state('overlay-status.json').get('highlightVisible'))
    call('mac_cursors', dict(operation='stop'))

    for end_mode in ['finish', 'cancel', 'deadline']:
        created = call('mac_task', dict(operation='begin', durationSeconds=4 if end_mode == 'deadline' else 90))
        task_id = created['task']['id']; task_observation = observe(task_id); task_overlay = pointer(task_observation, task_id)
        if end_mode != 'deadline':
            call('mac_task', dict(operation=end_mode, taskID=task_id))
        check('task_'+end_mode+'_stops_host', wait(lambda: exited(task_overlay), 5), host=task_overlay)
        stopped = call('mac_cursors', dict(operation='stop', taskID=task_id))
        check('terminal_task_'+end_mode+'_cleanup_is_idempotent', stopped.get('status') == 'overlay_not_running', response=stopped)

    for end_mode in ['eof', 'owner_termination']:
        server = MCP(); observation = observe(server=server)
        result = server.tool('mac_pointer', dict(observation=observation['id'], x=.5, y=.5, space='normalized', label='MCP 수명 검증'))
        owned = remember(result['desktopOverlay']); target = state('overlay-target.json')
        check('mcp_'+end_mode+'_binds_exact_owner', target.get('ownerPID') == server.proc.pid
              and target.get('ownerStartID') == process(server.proc.pid)['processStartID'] and target.get('ownerTransport') == 'mcp_stdio')
        began = time.monotonic()
        if end_mode == 'eof':
            server.proc.stdin.close()
        else:
            server.proc.terminate()
        server.proc.wait(timeout=3)
        check('mcp_'+end_mode+'_ends_feedback_with_target_alive', wait(lambda: exited(owned), 2)
              and process(fixture.pid)['processStartID'] == identity['processStartID'], elapsedSeconds=time.monotonic()-began)

    # Real thirty-second expiry, once. Listing, hiding/showing through the
    # control endpoint, and audit writes must not extend the actual ensure lease.
    observation = observe(); cli_overlay = pointer(observation)
    original_target = state('overlay-target.json'); activity = original_target['activityAt']
    time.sleep(15)
    call('mac_doctor', {})
    call('mac_cursors', dict(operation='list', observation=observation['id']))
    call('mac_cursors', dict(operation='hide', observation=observation['id']))
    call('mac_preview', dict(operation='overlay', enabled=True))
    check('read_control_and_audit_do_not_renew_lease', state('overlay-target.json') == original_target)
    check('one_shot_cli_exit_is_not_owner_failure', process(cli_overlay['pid'])['processStartID'] == cli_overlay['processStartID'])
    assert wait(lambda: exited(cli_overlay), max(.1, activity+33-time.time()))
    ended = state('overlay-status.json')
    check('actual_cli_idle_expires_after_thirty_seconds', ended.get('status') == 'stopped' and ended.get('stopReason') == 'idle_expired'
          and time.time()-activity >= 30 and not ended.get('highlightVisible') and ended.get('overlayCount') == 0, elapsedSeconds=time.time()-activity, status=ended)
    check('target_window_stays_alive_after_all_feedback_exits', process(fixture.pid)['processStartID'] == identity['processStartID'])
    check('persisted_pointer_files_are_not_deleted_or_modified_by_stop', all(Path(path).exists() and hashlib.sha256(Path(path).read_bytes()).hexdigest() == value for path, value in pointer_hashes.items()))
    completed = True
except BaseException as error:
    body_error = repr(error)
    (out/'failure.log').write_text(traceback.format_exc())
finally:
    # Save body evidence before cleanup can itself fail.
    save_report()
    def cleanup(name, action):
        try:
            action()
        except BaseException as error:
            cleanup_errors.append(dict(operation=name, error=repr(error)))
            (out/('cleanup-'+str(len(cleanup_errors))+'.log')).write_text(traceback.format_exc())
    for server in servers:
        if server.proc.poll() is None:
            cleanup('owned MCP close', server.proc.stdin.close)
            cleanup('owned MCP exit', lambda server=server: server.proc.wait(timeout=3))
    if helper:
        # State-scoped normal stop; never kill a helper by name or unrelated PID.
        directories = [root/'state'] + list((root/'state').glob('task-*'))
        for directory in directories:
            if directory.is_dir() and state('overlay-status.json', directory).get('status') == 'running':
                if directory == root/'state':
                    cleanup('owned overlay stop', lambda: call('mac_cursors', dict(operation='stop')))
                else:
                    tid = directory.name[5:]
                    cleanup('owned task overlay stop', lambda tid=tid: call('mac_cursors', dict(operation='stop', taskID=tid)))
        for record in owned_overlays:
            cleanup('verify owned overlay exit', lambda record=record: (_ for _ in ()).throw(AssertionError(record)) if not wait(lambda: exited(record), 3) else None)
        for record in owned_previews:
            if not exited(record):
                cleanup('owned preview stop', lambda: call('mac_preview', dict(operation='stop')))
                cleanup('verify owned preview exit', lambda record=record: (_ for _ in ()).throw(AssertionError(record)) if not wait(lambda: exited(record), 3) else None)
    if fixture and fixture.poll() is None:
        cleanup('owned fixture terminate', fixture.terminate)
        cleanup('owned fixture exit', lambda: fixture.wait(timeout=5))
    if 'fixture_log' in locals():
        fixture_log.close()
    if completed and not body_error and not cleanup_errors:
        cleanup('remove isolated state after verified exits', lambda: shutil.rmtree(root))
    save_report()
if not completed or body_error or cleanup_errors:
    raise SystemExit(1)
print((out/'report.json').read_text())
