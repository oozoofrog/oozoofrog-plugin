#!/usr/bin/env python3
"""Development-only silent capture, saved-media inspection, and live MCP cancellation.

Uses an owned native fixture and private state. Does not record personal apps.
"""
import hashlib
import json
import os
from pathlib import Path
import select
import subprocess
import tempfile
import time

skill = Path(__file__).resolve().parent.parent
root = Path(tempfile.mkdtemp(prefix='macpilot-recording-lifecycle-'))
evidence = skill / 'evidence' / ('recording-lifecycle-' + str(time.time_ns()))
evidence.mkdir(mode=0o700)
launcher = skill / 'scripts/macpilot'
environment = dict(os.environ, MACPILOT_STATE_DIR=str(root / 'state'), MACPILOT_FIXTURE_DIR=str(root / 'fixture'))
report = dict(status='running', checks=[], privateRoot=str(root))
fixture = server = None


def call(tool, arguments):
    result = subprocess.run([str(launcher), 'call', tool, '--json', '-'], input=json.dumps(arguments),
                            capture_output=True, text=True, env=environment, timeout=60)
    value = json.loads(result.stdout)
    if result.returncode:
        raise RuntimeError(value)
    return value


def check(name, condition, detail=None):
    report['checks'].append(dict(name=name, passed=bool(condition), detail=detail))
    print(name, 'PASS' if condition else 'FAIL', flush=True)
    assert condition, (name, detail)


def send(value):
    server.stdin.write(json.dumps(value) + '\n')
    server.stdin.flush()


def receive(timeout=3):
    ready, _, _ = select.select([server.stdout], [], [], timeout)
    return json.loads(server.stdout.readline()) if ready else None


try:
    subprocess.run([str(launcher), 'tools'], check=True, stdout=subprocess.DEVNULL)
    subprocess.run(['xcrun', 'swift', 'build', '--package-path', str(skill / 'tool'), '--product', 'macpilot-fixture'], check=True)
    products = Path(subprocess.check_output(['xcrun', 'swift', 'build', '--package-path', str(skill / 'tool'), '--show-bin-path'], text=True).strip())
    with (evidence / 'fixture.log').open('w') as log:
        fixture = subprocess.Popen([str(products / 'macpilot-fixture')], env=environment, stdout=log, stderr=log)
    state = root / 'fixture/state.json'
    deadline = time.monotonic() + 10
    while not state.exists() and time.monotonic() < deadline:
        time.sleep(.05)
    fixture_state = json.loads(state.read_text())
    app = next(a for a in call('mac_apps', {})['apps'] if a['pid'] == fixture.pid)
    target = dict(source='window', pid=fixture.pid, processStartID=app['processStartID'], windowID=fixture_state['windowNumber'])
    silent = call('mac_record', dict(target, operation='record', durationSeconds=1.5, systemAudio=False, maxDimension=640))
    report['silent'] = silent
    bounded = call('mac_task', dict(operation='begin', goal='Keep movie capture in fixture window', pid=fixture.pid,
                                   processStartID=app['processStartID'], windowID=target['windowID'], preserveForeground=False))['task']['id']
    try:
        call('mac_record', dict(operation='record', source='display', displayID=call('mac_doctor', {})['displays'][0]['id'], taskID=bounded))
        raise AssertionError('A bound window task widened to a display')
    except RuntimeError as error:
        check('window_bound_task_cannot_expand_to_full_display', error.args[0].get('code') == 'task_target_mismatch', error.args[0])
    call('mac_task', dict(operation='finish', taskID=bounded))
    check('video_only_capture_has_no_audio_track', silent['status'] == 'recorded' and silent['videoTracks'] == 1 and silent['audioTracks'] == 0 and not silent['microphoneCaptured'], silent)
    checked = call('mac_record', dict(operation='inspect', path=silent['path'], frames=0))
    check('saved_movie_inspection_matches_duration_and_has_no_requested_frame_files', checked['frames'] == [] and checked['videoTracks'] == 1 and abs(checked['durationSeconds'] - silent['durationSeconds']) < .01)
    server = subprocess.Popen([str(skill / 'bin/MacPilot.app/Contents/MacOS/macpilot'), 'mcp'], env=environment,
                              stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=(evidence / 'mcp.stderr').open('w'), text=True)
    send(dict(jsonrpc='2.0', id=1, method='initialize', params=dict(protocolVersion='2025-11-25')))
    initialized = receive()
    check('MCP_is_live_before_recording', initialized is not None and 'result' in initialized)
    task = call('mac_task', dict(operation='begin', goal='Cancel owned fixture movie', preserveForeground=False))['task']['id']
    request = dict(target, operation='record', durationSeconds=30, systemAudio=False, maxDimension=640, taskID=task)
    send(dict(jsonrpc='2.0', id='record', method='tools/call', params=dict(name='mac_record', arguments=request)))
    directory = root / 'state' / ('task-' + task)
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline and not list(directory.glob('*.mp4')):
        time.sleep(.05)
    check('actual_movie_output_exists_before_cancel', bool(list(directory.glob('*.mp4'))))
    time.sleep(1)
    began = time.monotonic()
    send(dict(jsonrpc='2.0', method='notifications/cancelled', params=dict(requestId='record', reason='Owned recording cancellation test')))
    deadline = time.monotonic() + 12
    records = []
    while time.monotonic() < deadline:
        records = list(directory.glob('recording-*.json'))
        if records:
            break
        time.sleep(.05)
    check('cancellation_persists_incomplete_receipt_within_bound', len(records) == 1 and time.monotonic() - began < 12)
    receipt = json.loads(records[0].read_text())
    report['cancelled'] = receipt
    check('cancelled_capture_never_reports_success', receipt['status'] == 'incomplete', receipt)
    cancelled_path = Path(receipt['path'])
    size = cancelled_path.stat().st_size
    time.sleep(.5)
    check('movie_file_stops_growing_after_cancellation', size > 0 and cancelled_path.stat().st_size == size)
    cancelled = call('mac_record', dict(operation='inspect', path=str(cancelled_path), frames=0))
    check('cancelled_movie_is_finalized_and_short', cancelled['videoTracks'] == 1 and cancelled['durationSeconds'] < 10, cancelled)
    send(dict(jsonrpc='2.0', id='after', method='tools/call', params=dict(name='mac_doctor', arguments={})))
    after = receive()
    check('MCP_suppresses_cancelled_response_and_accepts_next_call', after is not None and after.get('id') == 'after' and not after.get('result', {}).get('isError'), after)
    call('mac_task', dict(operation='finish', taskID=task))
    server.stdin.close()
    check('MCP_exits_cleanly_after_capture_cleanup', server.wait(timeout=5) == 0)
    report['binarySHA256'] = hashlib.sha256((skill / 'bin/MacPilot.app/Contents/MacOS/macpilot').read_bytes()).hexdigest()
    report['status'] = 'passed'
except Exception as error:
    report['status'] = 'failed'
    report['error'] = str(error)
    raise
finally:
    for process in [server, fixture]:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
    (evidence / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print('Evidence:', evidence, flush=True)
