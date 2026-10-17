#!/usr/bin/env python3
"""Send one bounded command to an owned no-permission GUI probe."""
import argparse
import json
from pathlib import Path
import time
import uuid

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('evidence_directory', type=Path)
parser.add_argument('operation', choices=['inspect', 'next', 'previous', 'select', 'auto_add', 'request', 'replay', 'quit'])
parser.add_argument('--kind', choices=['all','accessibility','screenCapture','postEvent','inputMonitoring','automation','fullDiskAccess','files','clipboard'])
args = parser.parse_args()
output = args.evidence_directory.resolve()
manifest = json.loads((output / 'manifest.json').read_text())
assert manifest['bundleID'].startswith('local.macpilot.permissionprobe.')
assert Path(manifest['evidenceDirectory']).resolve() == output
live = Path(manifest.get('liveEvidenceDirectory', str(output)))
command_id = str(uuid.uuid4())
command = {'id': command_id, 'operation': args.operation}
if args.kind is not None:
    command['kind'] = args.kind
staged = live / ('command-' + command_id + '.json')
staged.write_text(json.dumps(command) + '\n')
staged.replace(live / 'command.json')
response = live / ('final.json' if args.operation == 'quit' else f'response-{command_id}.json')
for _ in range(100):
    if response.exists():
        if live.resolve() != output:
            (output / response.name).write_bytes(response.read_bytes())
        print(response.read_text())
        break
    time.sleep(.1)
else:
    raise RuntimeError('Owned probe did not acknowledge the command within 10 seconds')
