"""Test the Swift package and a real library-to-Keychain-tool round trip on macOS."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    skill = Path(__file__).resolve().parents[1]
    if sys.platform != 'darwin' or output.is_relative_to(skill):
        parser.error('requires macOS and a new --output directory outside the skill')
    if output.is_relative_to('/Volumes/eyedisk') and not Path('/Volumes/eyedisk').is_dir():
        parser.error('/Volumes/eyedisk is unavailable')
    output.mkdir(parents=True, exist_ok=False)
    package = skill / 'assets/AppFeedback'
    environment = dict(os.environ)
    for name, folder in [('TMPDIR', 'tmp'), ('CLANG_MODULE_CACHE_PATH', 'modules'),
                         ('SWIFTPM_MODULECACHE_OVERRIDE', 'modules'), ('XDG_CACHE_HOME', 'cache')]:
        (output / folder).mkdir(exist_ok=True)
        environment[name] = str(output / folder)
    results = []

    def run(name, command, expected=0, extra_env=None, build=False):
        actual = list(command)
        if build and shutil.which('eyebuild'):
            actual = ['eyebuild', '-p', 'oozoofrog-plugin', 'run', 'app-feedback-validation', '--'] + actual
        proc = subprocess.run(actual, cwd=skill, env=environment | (extra_env or {}),
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        (output / (name + '.log')).write_text(proc.stdout)
        warnings = len(re.findall(r'\bwarning:', proc.stdout))
        result = dict(name=name, command=actual, exit=proc.returncode, warnings=warnings,
                      passed=proc.returncode == expected and (not build or warnings == 0))
        results.append(result)
        (output / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
        print(f'{name}: exit={proc.returncode}, warnings={warnings}, passed={result["passed"]}', flush=True)
        if not result['passed']:
            raise RuntimeError(f'see {output / (name + ".log")}')
        return proc.stdout

    run('swift-version', ['swift', '--version'])
    tool = output / 'feedback-diagnostics'
    run('tool-build', ['xcrun', 'swiftc', '-swift-version', '6', '-module-cache-path', str(output / 'modules'),
                       str(skill / 'scripts/feedback_diagnostics.swift'), '-o', str(tool)], build=True)
    service = 'AppFeedback-verification-' + str(uuid.uuid4())
    account = 'temporary-test-only'
    selection = ['--service', service, '--account', account]
    cleanup = ['security', 'delete-generic-password', '-s', service, '-a', account]
    # Retain recovery instructions if interrupted, with no private key bytes.
    (output / 'cleanup-keychain.json').write_text(json.dumps(cleanup) + '\n')
    created = False
    try:
        public = json.loads(run('generate-key', [str(tool), 'generate-key'] + selection))
        created = True
        exported = json.loads(run('public-key', [str(tool), 'public-key'] + selection))
        assert public == exported
        run('duplicate-key-refused', [str(tool), 'generate-key'] + selection, expected=1)
        assert json.loads(run('key-unchanged', [str(tool), 'public-key'] + selection)) == public
        common = ['--package-path', str(package), '--scratch-path', str(output / 'swiftpm'),
                  '--cache-path', str(output / 'cache'), '--config-path', str(output / 'configuration'),
                  '--security-path', str(output / 'security'), '--disable-sandbox']
        run('debug-tests', ['swift', 'test'] + common, build=True, extra_env={
            'APP_FEEDBACK_TEST_PUBLIC_KEY': public['publicKeyBase64'],
            'APP_FEEDBACK_TEST_OUTPUT': str(output)})
        run('release-tests', ['swift', 'test', '-c', 'release'] + common, build=True)
        sealed = output / 'roundtrip.afdiag'
        plain = output / 'roundtrip.json'
        run('decrypt', [str(tool), 'decrypt', str(sealed), '--out', str(plain)] + selection)
        assert json.loads(plain.read_bytes()) == {
            'format': 1, 'diagnostics': {'event': 'sampleOpened'}, 'checklist': []}
        assert plain.stat().st_mode & 0o777 == 0o600
        before = plain.read_bytes()
        run('overwrite-refused', [str(tool), 'decrypt', str(sealed), '--out', str(plain)] + selection, expected=1)
        assert plain.read_bytes() == before
        for name, offset in [('tampered-header', 0), ('wrong-key-id', 8), ('tampered-ciphertext', -1)]:
            data = bytearray(sealed.read_bytes())
            data[offset] ^= 1
            path = output / (name + '.afdiag')
            path.write_bytes(data)
            destination = output / (name + '.json')
            run(name, [str(tool), 'decrypt', str(path), '--out', str(destination)] + selection, expected=1)
            assert not destination.exists()
        # The Release library object must not retain Debug-only provider/sealing/checklist symbols.
        objects = list((output / 'swiftpm').glob('*/release/AppFeedback.build/*.swift.o'))
        if not objects:
            objects = list((output / 'swiftpm').glob('out/Products/Release/AppFeedback.o'))
        assert objects, 'Release objects not found'
        symbols = run('release-symbols', ['nm'] + [str(path) for path in objects])
        assert not any(name in symbols for name in ('FeedbackSealing', 'FeedbackDiagnostics', 'FeedbackCheck'))
    finally:
        if created:
            run('delete-temporary-key', cleanup)
            run('temporary-key-absent', ['security', 'find-generic-password', '-s', service, '-a', account], expected=44)
            (output / 'cleanup-keychain.json').unlink()
    print('Library/tool round trip, corruption rejection, private output, and cleanup passed.', flush=True)


if __name__ == '__main__':
    main()
