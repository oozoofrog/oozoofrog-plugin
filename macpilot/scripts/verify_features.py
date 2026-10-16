#!/usr/bin/env python3
"""Run MacPilot acceptance checks against owned apps and synthetic data only."""
import argparse
import concurrent.futures
import hashlib
import json
import os
import shutil
from pathlib import Path
import subprocess
import tempfile
import sys
import threading
import time
import uuid

skill = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--stage', choices=['tasks', 'preview', 'files', 'browser', 'safari', 'codex', 'all'], default='tasks')
parser.add_argument('--binary', type=Path)
args = parser.parse_args()
binary = args.binary or skill / 'bin/MacPilot.app/Contents/MacOS/macpilot'
out = skill / 'evidence' / ('features-' + time.strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:6])
out.mkdir(parents=True, mode=0o700)
private_temporary = tempfile.TemporaryDirectory(prefix='macpilot-acceptance-')
environment = dict(os.environ, MACPILOT_STATE_DIR=str(Path(private_temporary.name) / 'state'))
checks = []
processes = []
sequence = 0
sequence_lock = threading.Lock()
preview_tasks = []


def check(name, condition, detail=None):
    checks.append(dict(check=name, passed=bool(condition), detail=detail))
    print(name, 'PASS' if condition else 'FAIL', flush=True)
    assert condition, (name, detail)


def call(name, **arguments):
    global sequence
    with sequence_lock:
        sequence += 1
        request_sequence = sequence
    result = subprocess.run([str(binary), 'call', name, '--json', '-'], input=json.dumps(arguments, ensure_ascii=False),
                            text=True, capture_output=True, env=environment, timeout=180)
    (out / f'{request_sequence:03}-{name}.json').write_text(result.stdout)
    (out / f'{request_sequence:03}-{name}.stderr').write_text(result.stderr)
    data = json.loads(result.stdout)
    if result.returncode:
        raise RuntimeError(data)
    return data


def rejected(name, code, **arguments):
    try:
        call(name, **arguments)
    except RuntimeError as error:
        check(name + '_rejects_' + code, error.args[0].get('code') == code, error.args[0])
    else:
        raise AssertionError('Expected rejection: ' + code)


def observe(task):
    record = call('mac_task', operation='status', taskID=task)['task']
    for attempt in range(3):
        try:
            return call('mac_observe', taskID=task, pid=record['pid'], processStartID=record['processStartID'], screenshot=False)['observation']
        except RuntimeError as error:
            if error.args[0].get('code') != 'foreground_changed' or attempt == 2:
                raise
            report.setdefault('externalForegroundChanges',[]).append(error.args[0])
            time.sleep(.1)


def node(observation, identifier):
    return next(n for n in observation['nodes'] if n['identifier'] == identifier)


def fixture_state(directory):
    return json.loads((directory / 'state.json').read_text())


def desktop():
    original_foreground=call('mac_doctor')['foregroundPID']
    original_app=next((a for a in call('mac_apps')['apps'] if a['pid']==original_foreground),None)
    product_dir = Path(subprocess.check_output(['/usr/bin/xcrun', 'swift', 'build', '--package-path', str(skill / 'tool'), '--show-bin-path'], text=True).strip())
    fixture = product_dir / 'macpilot-fixture'
    fixtures = []
    for index in range(2):
        directory = out / f'fixture-{index}'
        log = (out / f'fixture-{index}.log').open('w')
        process = subprocess.Popen([str(fixture)], env=dict(environment, MACPILOT_FIXTURE_DIR=str(directory)), stdout=log, stderr=log)
        processes.append(process)
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            if (directory / 'state.json').exists() and fixture_state(directory).get('pid') == process.pid:
                break
            assert process.poll() is None, 'Fixture exited'
            time.sleep(.1)
        else:
            raise AssertionError('Fixture did not start')
        app = next(a for a in call('mac_apps')['apps'] if a['pid'] == process.pid)
        task = call('mac_task', operation='begin', pid=process.pid, processStartID=app['processStartID'],
                    windowID=fixture_state(directory)['windowNumber'], goal=f'Fixture {index}',
                    expected='Independent input and virtual cursor')['task']['id']
        fixtures.append((directory, app, task))
    first, second = fixtures
    if original_app:
        call('mac_app',pid=original_app['pid'],processStartID=original_app['processStartID'],action='activate')
    directory, app, task = first
    foreground_before = call('mac_doctor')['foregroundPID']
    cursor_before = call('mac_doctor')['systemCursor']
    for index, (_, _, task_id) in enumerate(fixtures):
        observation = observe(task_id)
        for cursor in ('red', 'blue'):
            result = call('mac_pointer', taskID=task_id, cursorID=cursor, observation=observation['id'], x=.2 + index * .2,
                          y=.5 if cursor == 'red' else .7, space='normalized')
            check('virtual_cursor_posts_no_system_events_' + str(index) + '_' + cursor, result['eventsPosted'] == 0, result)
        cursors = call('mac_cursors', taskID=task_id, observation=observation['id'], operation='list')['cursors']
        check('two_independent_cursors_' + str(index), len(cursors) == 2, cursors)
    observation = observe(task)
    call('mac_ax', taskID=task, observation=observation['id'], node=node(observation, 'literal-text')['id'],
         operation='set_value', text='작업별 백그라운드 😀')
    deadline = time.monotonic() + 2
    while fixture_state(directory)['text'] != '작업별 백그라운드 😀' and time.monotonic() < deadline:
        time.sleep(.05)
    check('background_value_reaches_only_owned_target', fixture_state(directory)['text'] == '작업별 백그라운드 😀'
          and fixture_state(second[0])['text'] == '초기 값', [fixture_state(directory), fixture_state(second[0])])
    after = call('mac_doctor')
    check('background_preserves_foreground', after['foregroundPID'] == foreground_before, dict(before=foreground_before,after=after['foregroundPID']))
    report['cursorActivity'] = dict(before=cursor_before, after=after['systemCursor'],
                                  changedDuringTest=cursor_before != after['systemCursor'],
                                  note='User input remains enabled; coordinate changes across CLI calls are not attributed to MacPilot.')
    observation = observe(task)
    rejected('mac_focus', 'foreground_required', taskID=task, observation=observation['id'])

    # A live wait holds this app's lease while a different target remains usable.
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        wait = pool.submit(call, 'mac_wait', taskID=task, observation=observation['id'],
                           node=node(observation, 'literal-text')['id'], equals='will-not-match', timeoutMs=1400, pollMs=100)
        time.sleep(.2)
        began = time.monotonic()
        other = observe(second[2])
        check('different_targets_execute_concurrently', time.monotonic() - began < .9 and not wait.done())
        collision = call('mac_task', operation='begin', pid=app['pid'], processStartID=app['processStartID'])['task']['id']
        rejected('mac_observe', 'busy', taskID=collision, pid=app['pid'], processStartID=app['processStartID'], screenshot=False)
        call('mac_task', operation='cancel', taskID=task)
        try:
            wait.result(timeout=3)
        except RuntimeError:
            check('task_cancellation_interrupts_active_call', True)
        else:
            raise AssertionError('Task cancellation did not interrupt the call')
        check('other_task_survives_cancellation', call('mac_task', operation='status', taskID=second[2])['task']['status'] == 'active')
    focus_task = call('mac_task', operation='begin', pid=app['pid'], processStartID=app['processStartID'],
                      windowID=fixture_state(directory)['windowNumber'], preserveForeground=False)['task']['id']
    observation = observe(focus_task)
    focused = call('mac_focus', taskID=focus_task, observation=observation['id'], node=node(observation, 'literal-text')['id'])
    check('app_window_and_node_focus_are_verified', focused['status'] == 'focus_verified', focused)
    private = call('mac_private', operation='window_ids', enabled=True, pid=app['pid'], processStartID=app['processStartID'])
    check('private_window_ID_matches_fixture_and_WindowServer', fixture_state(directory)['windowNumber'] in [w['windowID'] for w in private['windows']], private)
    private_observation = call('mac_observe', taskID=focus_task, pid=app['pid'], processStartID=app['processStartID'],
                               windowID=fixture_state(directory)['windowNumber'], privateAPI=True, screenshot=False)['observation']
    check('private_identity_observation_can_resolve_live_nodes', call('mac_verify', taskID=focus_task,
          observation=private_observation['id'], node=node(private_observation,'counter')['id'], equals='0')['matches'])
    call('mac_menu', pid=app['pid'], processStartID=app['processStartID'], operation='press', titlePath=['Edit','Twin Window'])
    deadline = time.monotonic() + 3
    while fixture_state(directory)['twinWindowNumber'] <= 0 and time.monotonic() < deadline:
        time.sleep(.1)
    twin = fixture_state(directory)['twinWindowNumber']
    check('twin_fixture_window_has_WindowServer_identity', twin > 0)
    rejected('mac_observe', 'ambiguous_ax_window', pid=app['pid'], processStartID=app['processStartID'],
             windowID=fixture_state(directory)['windowNumber'], screenshot=False)
    primary = call('mac_observe', taskID=focus_task, pid=app['pid'], processStartID=app['processStartID'], privateAPI=True, screenshot=False)['observation']
    check('task_bound_window_applies_when_windowID_is_omitted', primary['windowID'] == fixture_state(directory)['windowNumber'])
    rejected('mac_observe', 'task_target_mismatch', taskID=focus_task, pid=app['pid'], processStartID=app['processStartID'], windowID=twin, privateAPI=True, screenshot=False)
    twin_observation = call('mac_observe', pid=app['pid'], processStartID=app['processStartID'], windowID=twin, privateAPI=True, screenshot=False)['observation']
    check('private_ID_resolves_identical_title_and_geometry_windows', any(n['identifier'] == 'twin-proof' for n in twin_observation['nodes'])
          and not any(n['identifier'] == 'twin-proof' for n in primary['nodes']))
    call('mac_window', observation=twin_observation['id'], operation='close')
    if args.stage in ('preview', 'all'):
        preview(task=focus_task, directory=directory, other=second[1])


def preview(task, directory, other):
    observation = observe(task)
    for cursor, x in [('red', .3), ('blue', .7)]:
        call('mac_pointer', taskID=task, cursorID=cursor, observation=observation['id'], x=x, y=.5, space='normalized')
    before = call('mac_doctor')['foregroundPID']
    current = call('mac_preview', taskID=task, operation='start', observation=observation['id'])
    preview_tasks.append(task)
    check('live_preview_has_real_frames_without_stealing_focus', current['presentation'] == 'borderless_overlay' and current['titlebar'] is False and current['frameCount'] > 0
          and call('mac_doctor')['foregroundPID'] == before, current)
    windows = call('mac_windows', pid=current['pid'])['windows']
    check('live_preview_window_is_actually_on_screen', any(w['onScreen'] for w in windows), windows)
    preview_window=next(w for w in windows if w['onScreen'] and w['title']=='MacPilot Preview')
    dragged=subprocess.run(['/usr/bin/xcrun','swift',str(skill/'scripts/verify_preview_drag.swift'),str(current['pid']),str(preview_window['windowID'])],text=True,capture_output=True,timeout=30)
    (out/'preview-drag.json').write_text(dragged.stdout)
    (out/'preview-drag.stderr').write_text(dragged.stderr)
    check('borderless_preview_drags_without_keyboard_focus',dragged.returncode==0,dragged.stdout+dragged.stderr)

    initial_hash = current['frameSHA256']
    observation = observe(task)
    call('mac_ax', taskID=task, observation=observation['id'], node=node(observation,'literal-text')['id'],
         operation='set_value', text='라이브 화면 변화 12345')
    deadline = time.monotonic() + 4
    while time.monotonic() < deadline:
        current = call('mac_preview', taskID=task, operation='status')
        if current['frameSHA256'] != initial_hash:
            break
        time.sleep(.15)
    check('live_preview_pixels_change_after_real_app_edit', current['frameSHA256'] != initial_hash, current)
    Path(out/'preview-live.png').write_bytes(Path(current['screenshot']).read_bytes())
    call('mac_focus',taskID=task,observation=observe(task)['id'])
    overlays = call('mac_preview', taskID=task, operation='overlay', enabled=True)
    check('two_desktop_cursor_overlays_are_visible', overlays['overlayCount'] == 2 and overlays['cursorSurface']=='desktop' and overlays['cursorStyle']=='arrow', overlays)
    o=observe(task)
    before_position=overlays['positions']['red']
    moved=call('mac_pointer',taskID=task,cursorID='red',observation=o['id'],x=.75,y=.72,space='normalized',label='스크롤')
    samples=[moved['desktopOverlay']]
    deadline=time.monotonic()+2
    while time.monotonic()<deadline:
        state=call('mac_cursors',taskID=task,operation='list',observation=o['id'])['desktopOverlay']
        samples.append(state)
        if not state['animationCount']:
            break
        time.sleep(.04)
    final=moved['virtualPointer']
    positions=[s['positions']['red'] for s in samples]
    dx,dy=final['x']-before_position['x'],final['y']-before_position['y']
    curved=any(abs((p['x']-before_position['x'])*dy-(p['y']-before_position['y'])*dx)>5 for p in positions)
    check('desktop_cursor_follows_smooth_curved_motion',any(s['animationCount'] for s in samples) and curved
          and abs(positions[-1]['x']-final['x'])<1 and abs(positions[-1]['y']-final['y'])<1,samples)

    call('mac_app',pid=other['pid'],processStartID=other['processStartID'],action='activate')
    time.sleep(.15)
    occluded=call('mac_cursors',taskID=task,operation='list',observation=observe(task)['id'])['desktopOverlay']
    check('covered_target_has_no_ghost_outline_or_cursors',not occluded['highlightVisible'] and occluded['overlayCount']==0,occluded)
    call('mac_focus',taskID=task,observation=observe(task)['id'])
    window = next((w for w in call('mac_windows',pid=current['pid'])['windows'] if w['title'].startswith('MacPilot')),None)
    if window:
        proof = call('mac_observe',pid=current['pid'],processStartID=current['processStartID'],windowID=window['windowID'],screenshot=True)
        Path(out/'preview-panel.png').write_bytes(Path(proof['observation']['screenshot']).read_bytes())
    hidden = call('mac_preview', taskID=task, operation='hide')
    deadline=time.monotonic()+2
    while any(w['onScreen'] and w['title']=='MacPilot Preview' for w in call('mac_windows',pid=current['pid'])['windows']) and time.monotonic()<deadline:
        time.sleep(.05)
    check('preview_hide_is_acknowledged_and_not_on_screen', not hidden['visible']
          and not any(w['onScreen'] and w['title']=='MacPilot Preview' for w in call('mac_windows',pid=current['pid'])['windows']))
    shown = call('mac_preview', taskID=task, operation='show')
    check('desktop_cursors_and_target_highlight_survive_preview_hide', hidden['overlayEnabled'])
    check('preview_reopens_without_new_process', shown['visible'] and shown['pid'] == current['pid'])
    paused = call('mac_preview', taskID=task, operation='pause')
    time.sleep(.35)
    stable = call('mac_preview', taskID=task, operation='status')
    check('preview_pause_stops_frame_updates', paused['paused'] and stable['frameCount'] == paused['frameCount'])
    resumed = call('mac_preview', taskID=task, operation='resume')
    deadline=time.monotonic()+3
    while resumed['frameCount']<=paused['frameCount'] and time.monotonic()<deadline:
        time.sleep(.1)
        resumed=call('mac_preview',taskID=task,operation='status')
    check('preview_resume_is_acknowledged_and_receives_new_frames', not resumed['paused'] and resumed['frameCount']>paused['frameCount'])
    stopped = call('mac_preview', taskID=task, operation='stop')
    check('preview_stop_is_acknowledged', stopped['status'] == 'stopped')
    check('desktop_cursors_survive_preview_stop', call('mac_cursors', taskID=task, observation=observe(task)['id'], operation='list')['desktopOverlay']['running'])
    reopened=call('mac_preview',taskID=task,operation='start',observation=observe(task)['id'])
    call('mac_app',pid=other['pid'],processStartID=other['processStartID'],action='activate')
    window=next(w for w in call('mac_windows',pid=reopened['pid'])['windows'] if w['onScreen'] and w['title']=='MacPilot Preview')
    opened=subprocess.run(['/usr/bin/xcrun','swift',str(skill/'scripts/verify_preview_drag.swift'),str(reopened['pid']),str(window['windowID']),str(fixture_state(directory)['pid'])],text=True,capture_output=True,timeout=30)
    (out/'preview-open.json').write_text(opened.stdout)
    (out/'preview-open.stderr').write_text(opened.stderr)
    result_path=Path(environment['MACPILOT_STATE_DIR'])/('task-'+task)/'preview-open-result.json'
    if result_path.exists():
        (out/'preview-open-receipt.json').write_bytes(result_path.read_bytes())
    gesture=json.loads(opened.stdout) if opened.stdout.strip() else {}
    receipt=json.loads(result_path.read_text()) if result_path.exists() else {}
    verified_at_completion=receipt.get('status')=='focus_verified' and receipt.get('foregroundVerified') and receipt.get('windowVerified') and receipt.get('pid')==fixture_state(directory)['pid']
    if gesture.get('previewHidden') and verified_at_completion and not gesture.get('doubleClickRaisedTargetAndClosedPreview'):
        report['externalForegroundChangeAfterVerifiedFocus']=gesture
    check('double_click_preview_raises_target_and_closes_preview',gesture.get('dragMovedPreview') and gesture.get('foregroundPreserved')
          and gesture.get('previewHidden') and verified_at_completion,dict(gesture=gesture,receipt=receipt))
    preview_tasks.remove(task)


def files():
    folder = Path(private_temporary.name) / 'files'
    call('mac_files', operation='mkdir', path=str(folder))
    original, copied, moved = (folder / name for name in ('한글😀.txt', 'copy.txt', 'moved.txt'))
    value = 'MacPilot 한글 😀 e\u0301\n'
    written = call('mac_files', operation='write', path=str(original), text=value)
    check('native_file_write_is_hash_verified', written['status'] == 'file_write_verified')
    rejected('mac_files', 'destination_exists', operation='write', path=str(original), text='must not overwrite')
    copied_result = call('mac_files', operation='copy', path=str(original), destination=str(copied))
    check('native_file_copy_matches_original_bytes', copied_result['contentHashVerified'] and original.read_bytes() == copied.read_bytes())
    moved_result = call('mac_files', operation='move', path=str(copied), destination=str(moved))
    check('native_file_move_is_verified', moved_result['contentHashVerified'] and not copied.exists() and moved.read_bytes() == original.read_bytes())
    check('native_UTF8_file_read_roundtrip', call('mac_files', operation='read', path=str(moved))['text'] == value)
    tags = call('mac_files', operation='tags', path=str(moved), tags=['MacPilot 검증'])
    check('Finder_tags_roundtrip_on_real_file', tags['status'] == 'tags_verified', tags)
    found = call('mac_files', operation='search', path=str(folder), query='moved')
    check('native_file_search_uses_selected_scope', len(found['items']) == 1 and Path(found['items'][0]['path']).resolve() == moved.resolve())
    system = call('mac_system', operation='info')
    check('native_system_info_has_actual_displays', len(system['screens']) > 0, system)
    audio = call('mac_system', operation='audio')
    check('CoreAudio_output_is_read', audio['status'] == 'audio_verified', audio)
    if audio['muteSupported']:
        written_audio = call('mac_system', operation='audio', muted=audio['muted'])
        check('CoreAudio_mute_write_and_reread_without_changing_user_state', written_audio['muted'] == audio['muted'])
    volumes = [c['volume'] for c in audio['channels']]
    if volumes and max(volumes) - min(volumes) < .001:
        written_audio = call('mac_system', operation='audio', volume=volumes[0])
        check('CoreAudio_volume_write_and_reread_without_changing_user_state', written_audio['status'] == 'audio_verified')
    rejected('mac_system', 'invalid_argument', operation='audio', volume=2)


def codex():
    executable = shutil.which('codex')
    check('explicit_Codex_executable_exists', bool(executable))
    workspace = Path(private_temporary.name) / 'diagnostic-workspace'
    workspace.mkdir(mode=0o700)
    (workspace / 'AGENTS.md').write_text('This is a synthetic MacPilot diagnostic fixture. Do not modify files or run UI actions. Return the requested JSON.\n')
    configured = call('mac_improvement', operation='configure', codexPath=executable, cwd=str(workspace), ephemeral=True, automaticSend=False)
    check('Codex_destination_is_configured_without_sending', configured['status'] == 'improvement_destination_configured')
    report = call('mac_improvement', operation='report', title='MacPilot synthetic diagnostic acceptance',
                  goal='Verify delivery of this synthetic report', expected='Diagnose the report and return its requestID',
                  actual='A synthetic marker failed; no user data or application failure is involved')['request']
    duplicate = call('mac_improvement', operation='report', title='MacPilot synthetic diagnostic acceptance',
                     goal='Verify delivery of this synthetic report', expected='Diagnose the report and return its requestID',
                     actual='A synthetic marker failed; no user data or application failure is involved')['request']
    check('improvement_requests_are_durably_deduplicated', report['id'] == duplicate['id'] and duplicate['occurrences'] == 2)
    delivered = call('mac_improvement', operation='send', requestID=report['id'], timeoutMs=150000)['request']
    check('real_Codex_receives_and_completes_diagnostic', delivered['status'] == 'completed' and report['id'] in delivered.get('response', ''), delivered)
    again = call('mac_improvement', operation='send', requestID=report['id'])['request']
    check('completed_diagnostic_is_not_sent_again', again['threadID'] == delivered['threadID'] and again['turnID'] == delivered['turnID'])
    call('mac_improvement', operation='configure', automaticSend=True)
    try:
        call('mac_acceptance_unknown_tool', source='This private argument must not appear in the failure report')
    except RuntimeError as error:
        request_id = error.args[0]['improvementRequestID']
    else:
        raise AssertionError('Synthetic tool failure did not fail')
    deadline = time.monotonic() + 150
    automated = None
    while time.monotonic() < deadline:
        automated = call('mac_improvement', operation='status', requestID=request_id)['request']
        if automated['status'] in ('completed', 'connection_failed', 'turn_failed', 'unconfirmed'):
            break
        time.sleep(.5)
    check('actual_tool_failure_automatically_reaches_Codex', automated['status'] == 'completed'
          and request_id in automated.get('response', '') and 'private argument' not in json.dumps(automated), automated)
    call('mac_improvement', operation='configure', codexPath='/usr/bin/false', automaticSend=False)
    offline = call('mac_improvement', operation='report', title='MacPilot offline transport acceptance',
                   expected='Retain request when transport cannot initialize', actual='Synthetic offline endpoint')['request']
    retained = call('mac_improvement', operation='send', requestID=offline['id'], timeoutMs=2000)['request']
    check('offline_Codex_delivery_preserves_request', retained['status'] == 'connection_failed' and retained['id'] == offline['id'], retained)


report = dict(binary=str(binary), binarySHA256=hashlib.sha256(binary.read_bytes()).hexdigest(), checks=checks)
try:
    if args.stage in ('tasks','preview','all'):
        desktop()
    if args.stage in ('files','all'):
        files()
    if args.stage in ('codex','all'):
        codex()
    if args.stage in ('browser','all'):
        subprocess.run(['node', str(skill / 'scripts/verify_browser.mjs'), str(binary)], check=True)
    if args.stage in ('safari','all'):
        subprocess.run([sys.executable, str(skill / 'scripts/verify_safari.py'), str(binary)], check=True)
    report['status'] = 'passed'
except BaseException as error:
    report['status'] = 'failed'
    report['error'] = repr(error)
    raise
finally:
    for task in preview_tasks:
        try:
            call('mac_preview', taskID=task, operation='stop')
        except Exception as error:
            print('Preview cleanup:', error, flush=True)
    for process in reversed(processes):
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
    # Wait for feedback children to release private state before removing it.
    state_root=Path(private_temporary.name)/'state'
    hosts=[]
    for status in list(state_root.rglob('overlay-status.json'))+list(state_root.rglob('preview-status.json')):
        try:
            value=json.loads(status.read_text())
            if value.get('status') != 'stopped':
                hosts.append(value)
        except (OSError,ValueError):
            pass
    for host in hosts:
        try:
            call('mac_app',pid=host['pid'],processStartID=host['processStartID'],action='force_terminate')
        except RuntimeError:
            pass
    time.sleep(.2)
    (out / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print('Evidence:', out, flush=True)
    private_temporary.cleanup()
