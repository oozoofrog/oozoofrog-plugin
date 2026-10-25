"""Exercise the real offline installer, integrity rejection, and installed MCP."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
manifest = json.loads((ROOT / 'runtime/distribution.json').read_text())
archive = ROOT / f"evidence/release/winpilot-{manifest['version']}-win-x64.zip"
assert hashlib.sha256(archive.read_bytes()).hexdigest() == manifest['sha256']

with tempfile.TemporaryDirectory(prefix='install-test-', dir=ROOT / 'evidence') as temporary:
    folder = Path(temporary)
    def install(zip_path, target):
        return subprocess.run(['powershell.exe', '-NoProfile', '-File', str(ROOT / 'scripts/install-runtime.ps1'),
                               '-Archive', str(zip_path), '-InstallRoot', str(target)],
                              capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120, creationflags=0x08000000)
    bad = folder / 'bad.zip'
    bad.write_bytes(b'not a release')
    result = install(bad, folder / 'rejected')
    assert result.returncode != 0 and not (folder / 'rejected' / manifest['version']).exists(), result.stdout
    assert not list((folder / 'rejected').glob('.staging-*'))
    target = folder / 'installed'
    result = install(archive, target)
    assert result.returncode == 0, result.stderr
    exe = target / manifest['version'] / 'windows-pilot.exe'
    environment = os.environ | {'DOTNET_ROOT': str(folder / 'no-runtime'), 'DOTNET_MULTILEVEL_LOOKUP': '0'}
    check = subprocess.run([str(exe), '--self-test'], capture_output=True, text=True, env=environment, timeout=30, creationflags=0x08000000)
    assert check.returncode == 0, check.stderr
    assert json.loads(check.stdout)['checks'] == 43
    import integration
    integration.EXE = exe
    client = integration.Client(['powershell.exe', '-NoProfile', '-File', str(ROOT / 'scripts/install-runtime.ps1'),
                                 '-InstallRoot', str(target), '-Stdio'])
    try:
        tools = client.rpc('tools/list', {})['tools']
        assert len(tools) == 7
        assert 'windows' in client.tool('windows_list')[0]
    finally:
        client.close()
    before = exe.stat().st_mtime_ns
    assert install(archive, target).returncode == 0
    assert exe.stat().st_mtime_ns == before, 'Reinstall replaced a matching runtime'
    sample = exe.parent / 'settings-icon.png'
    sample.write_bytes(b'changed')
    assert install(archive, target).returncode != 0, 'Modified install was trusted'
    assert sample.read_bytes() == b'changed', 'Modified install was overwritten'
print(json.dumps({'status': 'passed', 'checks': ['reject bad ZIP', 'clean staging', 'offline install',
    'installed self-test 43', 'installed MCP 7 tools and windows_list', 'idempotent install', 'reject modified installation']}))
