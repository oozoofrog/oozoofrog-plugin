"""Development-only AX interaction with a new, isolated, test-owned handoff.

This is fixture automation, not human consent. The product has no auto-accept
argument or environment variable. Import only from serial desktop test runners.
"""
import json
import os
import signal
from pathlib import Path
import subprocess
import time


SOURCE = r'''
import AppKit
import ApplicationServices
import Darwin
let pid = Int32(CommandLine.arguments[1])!
let expected = CommandLine.arguments[2]
var info = proc_bsdinfo()
let size = Int32(MemoryLayout<proc_bsdinfo>.size)
guard proc_pidinfo(pid, PROC_PIDTBSDINFO, 0, &info, size) == size,
      Int32(info.pbi_pid) == pid,
      "\(info.pbi_start_tvsec).\(info.pbi_start_tvusec)" == expected else { exit(8) }
if CommandLine.arguments.count > 3 && CommandLine.arguments[3] == "identity" { exit(0) }
guard NSWorkspace.shared.frontmostApplication?.processIdentifier == pid else { exit(8) }
func value(_ node: AXUIElement, _ name: String) -> CFTypeRef? {
 var result: CFTypeRef?; AXUIElementCopyAttributeValue(node, name as CFString, &result); return result
}
func find(_ node: AXUIElement, _ depth: Int = 0) -> AXUIElement? {
 if depth > 16 { return nil }
 if value(node, "AXIdentifier") as? String == "macpilot-control-start" { return node }
 for child in value(node, "AXChildren") as? [AXUIElement] ?? [] {
  if let result = find(child, depth + 1) { return result }
 }
 return nil
}
guard let button = find(AXUIElementCreateApplication(pid)),
      NSWorkspace.shared.frontmostApplication?.processIdentifier == pid,
      AXUIElementPerformAction(button, kAXPressAction as CFString) == .success else { exit(9) }
'''


def read_state(directory, name):
    try:
        return json.loads((Path(directory)/name).read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


class OwnedHandoffFixture:
    def __init__(self, evidence):
        self.evidence = Path(evidence)
        self.helper = self.evidence/'owned-handoff-helper'
        source = self.evidence/'owned-handoff-helper.swift'
        source.write_text(SOURCE)
        result = subprocess.run(['xcrun', 'swiftc', str(source), '-o', str(self.helper)], capture_output=True, text=True)
        (self.evidence/'owned-handoff-helper-build.log').write_text(result.stdout + result.stderr)
        result.check_returncode()
        self.hosts = {}

    def start(self, state_directory, request_owner_pid, goal, seconds=10):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            request = read_state(state_directory, 'control-handoff-request.json')
            status = read_state(state_directory, 'control-handoff-status.json')
            if (request.get('ownerPID') == request_owner_pid and request.get('goal') == goal
                    and status.get('id') == request.get('id') and status.get('taskID') == request.get('taskID')
                    and status.get('phase') == 'pending'):
                pid = status['hostPID']
                identity = status['hostStartID']
                self.hosts[pid] = identity
                # Python binds the test owner/goal/epoch. Swift rechecks exact
                # host process generation and foreground immediately before AX.
                result = subprocess.run([str(self.helper), str(pid), identity], capture_output=True, text=True)
                (self.evidence/('handoff-'+request['id']+'.json')).write_text(json.dumps({
                    'request': request, 'status': status, 'fixtureAutomation': True,
                    'humanConsent': False, 'helperExitCode': result.returncode,
                    'helperStdout': result.stdout, 'helperStderr': result.stderr}, indent=2))
                result.check_returncode()
                return request['taskID']
            time.sleep(.04)
        raise AssertionError('Owned handoff did not become pending: '+repr((request, status)))

    def stop_hosts(self):
        errors = []
        for pid, identity in self.hosts.items():
            # Identity-only validation permits cleanup after the overlay has
            # returned focus. It never posts an input event or activates an app.
            try:
                checked = subprocess.run([str(self.helper), str(pid), identity, 'identity'], capture_output=True, text=True)
                if checked.returncode == 0:
                    os.kill(pid, signal.SIGTERM)
                    deadline = time.monotonic() + 3
                    while time.monotonic() < deadline:
                        alive = subprocess.run([str(self.helper), str(pid), identity, 'identity'], capture_output=True, text=True)
                        if alive.returncode != 0:
                            break
                        time.sleep(.04)
                    else:
                        errors.append({'pid': pid, 'error': 'owned host did not exit after SIGTERM'})
            except ProcessLookupError:
                pass
            except BaseException as error:
                errors.append({'pid': pid, 'error': repr(error)})
        return errors
