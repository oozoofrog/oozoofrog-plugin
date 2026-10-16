#!/usr/bin/env python3
"""Development-only GUI Chrome setup verification on a new owned profile.

Opens a native five-second approval dialog and lets it expire. The subsequent
AX enable test injects simulated consent through XCTest's internal seam.
No personal profile or Safari setting is changed. May change foreground.
"""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time

skill = Path(__file__).resolve().parent.parent
stamp = time.strftime('%Y%m%d-%H%M%S')
evidence = skill / 'evidence' / ('developer-settings-' + stamp)
evidence.mkdir(parents=True, exist_ok=False)
root = Path(tempfile.mkdtemp(prefix='macpilot-developer-verify-'))
chrome = Path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
profile = root / 'profile'
environment = dict(os.environ, MACPILOT_STATE_DIR=str(root / 'state'))
process = None
report = {'status': 'running', 'profile': str(profile), 'checks': [],
          'approvalEvidence': 'Native prompt expiry and XCTest simulated consent; no human acceptance claimed'}


def call(tool, arguments):
    result = subprocess.run([str(skill / 'scripts/macpilot'), 'call', tool, '--json', '-'],
                            input=json.dumps(arguments), capture_output=True, text=True,
                            env=environment, timeout=150)
    value = json.loads(result.stdout)
    if result.returncode:
        raise RuntimeError(value)
    return value


try:
    # Build first, so UI is open only while verification runs.
    subprocess.run([str(skill / 'scripts/macpilot'), 'tools'], check=True, stdout=subprocess.DEVNULL)
    before = {app['pid'] for app in call('mac_apps', {})['apps']}
    with (evidence / 'chrome.stdout').open('w') as out, (evidence / 'chrome.stderr').open('w') as err:
        process = subprocess.Popen([str(chrome), '--user-data-dir=' + str(profile), '--no-first-run',
                                    '--no-default-browser-check', '--disable-search-engine-choice-screen',
                                    '--force-renderer-accessibility', 'about:blank'], stdout=out, stderr=err)
    deadline = time.monotonic() + 15
    selected = None
    while time.monotonic() < deadline:
        apps = call('mac_apps', {})['apps']
        candidates = [a for a in apps if a['pid'] == process.pid and a['pid'] not in before and a['bundleID'] == 'com.google.Chrome']
        if candidates:
            windows = call('mac_windows', {'pid': process.pid})['windows']
            visible = [w for w in windows if w['onScreen'] and w['layer'] == 0 and w['frame']['width'] > 500]
            if len(visible) == 1:
                selected = dict(browser='chrome', setting='extension_developer_mode', pid=process.pid,
                                processStartID=candidates[0]['processStartID'], windowID=visible[0]['windowID'])
                break
        time.sleep(.15)
    if selected is None:
        raise RuntimeError('Owned Chrome did not expose one unambiguous test window')
    report['target'] = selected
    report['prepared'] = call('mac_browser_developer', dict(selected, operation='prepare'))
    if report['prepared']['enabled'] is not False:
        raise AssertionError('Fresh owned profile must begin with developer mode off')
    report['checks'].append('prepare opens extensions in the exact owned Chrome window without enabling')
    config = dict(arguments=selected, stateDirectory=str(root / 'unit-state'), reportPath=str(evidence / 'runtime.json'))
    config_path = root / 'test-config.json'
    config_path.write_text(json.dumps(config))
    with (evidence / 'xctest.log').open('w') as log:
        result = subprocess.run(['xcrun', 'swift', 'test', '--package-path', str(skill / 'tool'), '--filter',
                                 'BrowserDeveloperTests/testOwnedChromeRuntime'],
                                env=dict(environment, MACPILOT_DEVELOPER_TEST_CONFIG=str(config_path)),
                                stdout=log, stderr=subprocess.STDOUT, timeout=120)
    if result.returncode:
        raise RuntimeError('Owned Chrome XCTest failed; see xctest.log')
    report['checks'] += ['decline leaves developer mode off', 'native approval expiry leaves developer mode off',
                         'simulated test consent changes actual AX toggle to on', 'already enabled does not prompt or toggle']
    report['status'] = 'passed'
except Exception as error:
    report['status'] = 'failed'
    report['error'] = str(error)
    raise
finally:
    # Stop only our exact Popen child. Keep profile/logs as evidence, not a backup.
    if process is not None and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
    report['ownedBrowserStopped'] = process is not None and process.poll() is not None
    (evidence / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(evidence / 'report.json')
