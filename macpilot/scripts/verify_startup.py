#!/usr/bin/env python3
"""Read-only startup regression in the caller's actual execution session."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path, required=True)
    args = parser.parse_args()
    binary = args.binary.resolve(strict=True)
    checks = []
    with tempfile.TemporaryDirectory(prefix='macpilot-startup-') as root:
        env = dict(os.environ, MACPILOT_STATE_DIR=str(Path(root) / "state"))
        def call(*arguments, stdin=None):
            result = subprocess.run([str(binary), *arguments], input=stdin, capture_output=True,
                                    text=True, env=env, timeout=15)
            assert result.returncode in (0, 2), (arguments, result.returncode, result.stderr)
            return result
        assert 'macpilot' in call('--help').stdout
        checks.append('help survives actual execution context')
        assert any(item['name'] == 'mac_connection' for item in json.loads(call('tools').stdout))
        checks.append('tool catalog needs no AppKit application')
        assert json.loads(call('invalid-command').stdout)['code'] == 'invalid_argument'
        checks.append('invalid CLI command retains structured argument error')
        doctor = json.loads(call('doctor').stdout)
        session = doctor['desktopSession']
        assert isinstance(session['available'], bool)
        checks.append('doctor reports actual desktop session preflight')
        status = json.loads(call('call', 'mac_connection', '--json', '-', stdin='{"operation":"status"}').stdout)
        assert status['status'] == 'connection_responding'
        assert status['desktopSession'] == session
        checks.append('connection status survives unavailable desktop')
        messages = [dict(jsonrpc='2.0', id=1, method='initialize', params={}),
                    dict(jsonrpc='2.0', id=2, method='tools/list', params={}),
                    dict(jsonrpc='2.0', id=3, method='ping', params={})]
        replies = [json.loads(line) for line in call('mcp', stdin=''.join(json.dumps(m)+'\n' for m in messages)).stdout.splitlines()]
        assert [r['id'] for r in replies] == [1, 2, 3]
        assert 'tools' in replies[1]['result']
        checks.append('MCP handshake and catalog survive unavailable desktop')
        if not session['available']:
            assert doctor['permissionsStatus'] == 'not_probed'
            assert all(value is None for value in doctor['permissions'].values())
            failure = json.loads(call('call', 'mac_activate', '--json', '-', stdin='{}').stdout)
            assert failure['code'] == 'gui_session_unavailable', failure
            assert failure['outcome']['dispatch'] == 'not_sent', failure
            checks.append('desktop request fails before dispatch without inferring TCC denial')
        print(json.dumps(dict(status='passed', desktopSession=session, checks=checks), indent=2))


if __name__ == '__main__':
    main()
