#!/usr/bin/env python3
"""Safari Apple Events acceptance with an owned HTTP page and synthetic files.

Requires Automation consent and Safari's Allow JavaScript from Apple Events.
Does not change those settings or edit pre-existing tabs.
"""
import hashlib
import http.server
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import uuid

skill = Path(__file__).resolve().parent.parent
binary = Path(sys.argv[1]) if len(sys.argv) > 1 else skill / 'bin/MacPilot.app/Contents/MacOS/macpilot'
out = skill / 'evidence' / ('safari-' + str(int(time.time())))
out.mkdir(parents=True, mode=0o700)
checks, owned, uploaded = [], [], []
serial = 0
root = tempfile.TemporaryDirectory(prefix='macpilot-safari-')
env = dict(os.environ, MACPILOT_STATE_DIR=str(Path(root.name) / 'state'))


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_POST(self):
        uploaded.append(self.rfile.read(int(self.headers['Content-Length'])))
        self.send_response(200)
        self.end_headers()
        self.wfile.write(hashlib.sha256(uploaded[-1]).hexdigest().encode())

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        if self.path.startswith('/frame'):
            page = '<h2 id="frame-proof">Safari frame 한글</h2><input id="frame-input">'
        elif self.path.startswith('/second'):
            page = '<title>MacPilot second fixture</title><h1 id="second">Second</h1>'
        else:
            page = '''<title>MacPilot Safari fixture</title><h1 id="heading">Safari fixture</h1>
<input id="answer" value="초기 값"><input id="password" type="password" value="synthetic-safari-secret">
<button id="increment" onclick="document.querySelector('#counter').textContent=Number(document.querySelector('#counter').textContent)+1">Increment</button>
<p id="counter">0</p><select id="choice"><option value="a">A</option><option value="b">B</option></select>
<input id="upload" type="file"><p id="upload-result">Waiting</p><iframe src="/frame"></iframe>
<script>document.querySelector('#upload').onchange=async e=>{document.querySelector('#upload-result').textContent=await fetch('/upload',{method:'POST',body:e.target.files[0]}).then(r=>r.text())}</script>'''
        self.wfile.write(('<!doctype html>' + page).encode())


def check(name, condition, detail=None):
    checks.append(dict(check=name, passed=bool(condition), detail=detail))
    print(name, 'PASS' if condition else 'FAIL', flush=True)
    assert condition, (name, detail)


def call(operation, **fields):
    global serial
    serial += 1
    fields = dict(operation=operation, browser='safari', **fields)
    if operation == 'receipt':
        fields.pop('browser')
    result = subprocess.run([str(binary), 'call', 'mac_browser', '--json', '-'], input=json.dumps(fields),
                            text=True, capture_output=True, env=env, timeout=80)
    (out / f'{serial:03}-{operation}.json').write_text(result.stdout)
    (out / f'{serial:03}-{operation}.stderr').write_text(result.stderr)
    data = json.loads(result.stdout)
    if result.returncode:
        raise RuntimeError(data)
    return data


def observe(tab, frame=0):
    latest = None
    for _ in range(30):
        try:
            latest = call('observe', tabID=tab, frameID=frame)
            if latest.get('nodes'):
                return latest
        except RuntimeError as error:
            latest = error.args[0]
            if latest.get('code') == 'permission_required':
                raise
        time.sleep(.1)
    raise AssertionError(latest)


def by_id(observation, identifier):
    return next(n['id'] for n in observation['nodes'] if n['identifier'] == identifier)


def current(window, url):
    for _ in range(40):
        rows = call('tabs')['tabs']
        row = next((r for r in rows if r['windowID'] == window and r['url'] == url), None)
        if row:
            return row['tabID']
        time.sleep(.1)
    raise AssertionError('Owned Safari navigation did not complete')


server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
url = f'http://127.0.0.1:{server.server_port}/?macpilot={uuid.uuid4()}'
report = dict(binary=str(binary), binarySHA256=hashlib.sha256(binary.read_bytes()).hexdigest(), checks=checks)
try:
    opened = call('open', url=url, activate=False)
    owned.append(opened['windowID'])
    tab = current(opened['windowID'], url)
    o = observe(tab)
    check('Safari_DOM_observation_redacts_password', any(n['secure'] for n in o['nodes']) and 'synthetic-safari-secret' not in json.dumps(o))
    filled = call('fill', tabID=tab, observation=o['observation'], node=by_id(o, 'answer'), text='Safari 한글 😀')
    check('Safari_DOM_fill_roundtrip', filled['status'] == 'value_verified', filled)
    try:
        call('fill', tabID=tab, observation=o['observation'], node=by_id(o, 'answer'), text='stale')
    except RuntimeError as error:
        check('Safari_consumed_observation_is_rejected', error.args[0]['code'] == 'stale_observation', error.args[0])
    else:
        raise AssertionError('Consumed observation was accepted')
    o = observe(tab)
    try:
        call('fill', tabID=tab, observation=o['observation'], node=by_id(o, 'password'), text='forbidden')
    except RuntimeError as error:
        check('Safari_secure_input_is_rejected', error.args[0]['code'] == 'secure_or_inert_node')
    else:
        raise AssertionError('Secure input was accepted')
    o = observe(tab)
    call('click', tabID=tab, observation=o['observation'], node=by_id(o, 'increment'))
    o = observe(tab)
    check('Safari_click_changes_actual_DOM', call('verify', tabID=tab, observation=o['observation'], node=by_id(o, 'counter'), equals='1')['matches'])
    began = time.monotonic()
    unmatched = call('wait', tabID=tab, observation=o['observation'], node=by_id(o, 'counter'), equals='unmatched', timeoutMs=700)
    check('Safari_native_wait_polls_until_deadline', not unmatched['matches'] and time.monotonic() - began >= .7)
    frame = next(f for f in call('frames', tabID=tab)['frames'] if f['frameID'] > 0 and f['accessible'])
    o = observe(tab, frame['frameID'])
    check('Safari_same_origin_child_frame_is_observed', any(n['identifier'] == 'frame-proof' for n in o['nodes']))
    frame_fill = call('fill', tabID=tab, frameID=frame['frameID'], observation=o['observation'], node=by_id(o, 'frame-input'), text='Frame 😀')
    check('Safari_child_frame_fill_roundtrip', frame_fill['status'] == 'value_verified')
    o = observe(tab)
    selected = call('select_option', tabID=tab, observation=o['observation'], node=by_id(o, 'choice'), text='b')
    check('Safari_selection_roundtrip', selected['status'] == 'value_verified')
    original = 'Safari actual HTTP upload 한글 😀\n'.encode()
    path = Path(root.name) / 'upload.txt'
    path.write_bytes(original)
    o = observe(tab)
    attached = call('upload', tabID=tab, observation=o['observation'], node=by_id(o, 'upload'), path=str(path), mime='text/plain')
    for _ in range(30):
        if uploaded:
            break
        time.sleep(.1)
    check('Safari_HTTP_upload_matches_original_bytes', uploaded == [original] and attached['sha256'] == hashlib.sha256(original).hexdigest(), attached)
    receipt = call('receipt', requestID=filled['requestID'])
    check('Safari_response_receipt_is_durable', receipt['status'] == 'response_received')
    call('select', tabID=tab, activate=False)
    call('navigate', tabID=tab, url=url.split('/?')[0] + '/second')
    tab2 = current(opened['windowID'], url.split('/?')[0] + '/second')
    check('Safari_navigation_targets_owned_tab', any(n['identifier'] == 'second' for n in observe(tab2)['nodes']))
    call('back', tabID=tab2)
    tab_back = current(opened['windowID'], url)
    try:
        call('observe', tabID=tab2)
    except RuntimeError as error:
        check('Safari_old_URL_handle_is_rejected', error.args[0]['code'] == 'stale_tab')
    else:
        raise AssertionError('Old URL handle was accepted after history navigation')
    tab = tab_back
    check('Safari_history_back_roundtrip', any(n['identifier'] == 'heading' for n in observe(tab)['nodes']))
    call('reload', tabID=tab)
    o = observe(current(opened['windowID'], url))
    check('Safari_reload_keeps_owned_page', any(n['identifier'] == 'heading' for n in o['nodes']))
    report['status'] = 'passed'
except BaseException as error:
    report['status'] = 'failed'
    report['error'] = repr(error)
    raise
finally:
    for window in owned:
        try:
            rows = call('tabs')['tabs']
            owned_rows = [r for r in rows if r['windowID'] == window and r['url'].startswith(url.split('/?')[0])]
            for row in owned_rows:
                call('close', tabID=row['tabID'])
            check('Safari_owned_window_cleanup_verified', not any(r['windowID'] == window for r in call('tabs')['tabs']))
        except Exception as error:
            print('Safari cleanup:', error, flush=True)
    server.shutdown()
    server.server_close()
    root.cleanup()
    (out / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print('Evidence:', out, flush=True)
