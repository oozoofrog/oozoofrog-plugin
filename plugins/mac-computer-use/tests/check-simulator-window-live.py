#!/usr/bin/env python3
"""Build/run a separate native LCD test app; never install, boot or erase a device.

Requires an explicit booted UDID already claimed by this session. Evidence and the
app stay in the requested output directory. Run foreground checks serially.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--udid', required=True)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--backend-only', action='store_true', help='No foreground activation or Mac input; test the background simulator backend and native presentation separately.')
    parser.add_argument('--preview', action='store_true', help='Open a persistent isolated app with the production menu bar and actual LCD; do not run automatic device actions.')
    args = parser.parse_args()
    if args.preview and args.backend_only:
        parser.error('--preview and --backend-only are mutually exclusive')
    pilot = Path.home() / '.local/bin/sim-pilot'
    devices = json.loads(subprocess.check_output([str(pilot), 'devices'], text=True))
    chosen = next((d for d in devices if d.get('udid') == args.udid), None)
    if not chosen or not chosen.get('mine'):
        parser.error('The explicit UDID must be booted and claimed by this session (sim-pilot claim).')
    output = args.output.expanduser().resolve()
    output.mkdir(parents=True, exist_ok=False)
    here = Path(__file__).resolve().parent
    source = here.parent / 'skills/mac-computer-use/scripts/mac-cu-src'
    app = output / 'LCD Window Check.app'
    executable = app / 'Contents/MacOS/lcd-window-check'
    executable.parent.mkdir(parents=True)
    info = {'CFBundleIdentifier': 'org.oozoofrog.mac-cu.lcd-window-check',
            'CFBundleName': 'LCD Window Check', 'CFBundleExecutable': executable.name,
            'CFBundlePackageType': 'APPL', 'NSHighResolutionCapable': True}
    if args.preview:
        info['CFBundleIdentifier'] = 'org.oozoofrog.mac-cu.device-preview-final'
        info['CFBundleName'] = 'Mac CU Device Preview'
    (app / 'Contents/Info.plist').write_bytes(plistlib.dumps(info))
    sources = sorted(source.glob('*.swift'))
    (output / 'source-hashes.json').write_text(json.dumps({p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}, indent=2))
    # Keep all production definitions; replace only executable dispatch in a temporary main.
    # The tested SimulatorWindow, input, backend and lifecycle classes are unmodified.
    with tempfile.TemporaryDirectory(prefix='mac-cu-lcd-build-') as build:
        entry = Path(build) / 'main.swift'
        main_source = (source / 'main.swift').read_text()
        marker = '// Chrome starts mac-cu as the native messaging host'
        if main_source.count(marker) != 1:
            raise RuntimeError('Production dispatch marker changed; inspect main.swift before updating the harness.')
        dispatch = (f'runSimulatorWindowPreview(id: {json.dumps(args.udid)}, output: URL(fileURLWithPath: {json.dumps(str(output))}))'
                    if args.preview else 'runSimulatorWindowLiveCheck()')
        entry.write_text(main_source.split(marker)[0] + '\n' + dispatch + '\n')
        command = ['swiftc', '-g', *[str(p) for p in sources if p.name != 'main.swift'],
                   str(entry), str(here / 'simulator-window-live-check.swift'), '-o', str(executable)]
        with (output / 'build.log').open('w') as log:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
    subprocess.run(['codesign', '--force', '--sign', '-', str(app)], check=True)
    subprocess.run(['codesign', '--verify', '--deep', '--strict', str(app)], check=True)
    if args.preview:
        subprocess.run(['open', '-n', str(app)], check=True)
        print(f'Preview app: {app}')
        print(f'Readiness: {output / "ready.json"}')
        return
    environment = dict(os.environ, LCD_CHECK_UDID=args.udid, LCD_CHECK_OUTPUT=str(output), LCD_CHECK_BACKEND_ONLY='1' if args.backend_only else '0')
    # Launch only this app executable, not the installed mac-cu daemon/client or setup.py.
    with (output / 'live.log').open('w') as log:
        result = subprocess.run([str(executable)], env=environment, stdout=log, stderr=subprocess.STDOUT)
    print((output / 'live.log').read_text())
    print(f'Evidence: {output}')
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
