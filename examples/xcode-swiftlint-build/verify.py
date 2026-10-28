"""Verify a real Xcode Run Script using a private copy of SwiftLint 0.65.1."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import time


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--swiftlint', required=True, type=Path, help='Actual SwiftLint 0.65.1 executable to copy')
    parser.add_argument('--output', type=Path, help='New directory outside this example')
    args = parser.parse_args()
    fixture = Path(__file__).resolve().parent
    if args.output and args.output.resolve().is_relative_to(fixture):
        parser.error('--output must be outside the example directory')
    tool = args.swiftlint.resolve()
    if not tool.is_file():
        parser.error('--swiftlint must be an existing executable')
    evidence = args.output or Path(tempfile.mkdtemp(prefix='xcode-swiftlint-proof-'))
    if args.output:
        evidence.mkdir(parents=True, exist_ok=False)
    evidence = evidence.resolve()
    project = evidence / 'project'
    shutil.copytree(fixture, project, ignore=shutil.ignore_patterns('.tools', 'DerivedData', '__pycache__', 'xcuserdata'))
    binary = project / '.tools/swiftlint'
    binary.parent.mkdir()
    shutil.copy2(tool, binary)
    source, config = project / 'Sources/main.swift', project / '.swiftlint.yml'
    original_source, original_config = source.read_bytes(), config.read_bytes()
    binary_mode = binary.stat().st_mode & 0o777
    backup = binary.with_name('swiftlint.verification-backup')
    derived = evidence / 'DerivedData'
    results = []

    def run(name, command, exit_code=0, contains=(), phase=False):
        start = time.monotonic()
        proc = subprocess.run(command, cwd=project, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True)
        (evidence / (name + '.log')).write_text(proc.stdout)
        checks = [proc.returncode == exit_code] + [s in proc.stdout for s in contains]
        if phase:
            checks.append(proc.stdout.count('\nSWIFTLINT_RUN\n') == 1)
        objects = {str(p.relative_to(derived)):dict(mtime_ns=p.stat().st_mtime_ns, sha256=digest(p))
                   for p in derived.rglob('main.o')}
        entry = dict(name=name, command=command, exit_code=proc.returncode,
                     passed=all(checks), seconds=round(time.monotonic() - start, 3),
                     source_sha256=digest(source), config_sha256=digest(config),
                     lint_runs=proc.stdout.count('\nSWIFTLINT_RUN\n'), objects=objects)
        results.append(entry)
        (evidence / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
        print(f"{name}: exit={proc.returncode}, passed={entry['passed']}", flush=True)
        if not entry['passed']:
            raise RuntimeError(f"Unexpected result; see {evidence / (name + '.log')}")
        return entry

    build = ['xcodebuild', '-project', 'HelloLintXcode.xcodeproj', '-scheme', 'HelloLintXcode',
             '-configuration', 'Debug', '-destination', 'platform=macOS,arch=arm64',
             '-derivedDataPath', str(derived), 'build']
    try:
        run('00-xcode-version', ['xcodebuild', '-version'])
        run('01-swiftlint-version', [str(binary), 'version'], contains=('0.65.1',))
        baseline = run('02-normal', build, contains=('** BUILD SUCCEEDED **',), phase=True)
        unchanged = run('03-unchanged', build, contains=('** BUILD SUCCEEDED **',), phase=True)
        source.write_text('let greeting: String? = "Hello, SwiftLint"\nprint(greeting!)\n')
        bad_source = run('04-source-error', build, 65, ('error:', 'force_unwrapping', '** BUILD FAILED **'), True)
        config.write_text(original_config.decode().replace('severity: error', 'severity: warning'))
        warning = run('05-config-warning', build, contains=('warning:', 'force_unwrapping', '** BUILD SUCCEEDED **'), phase=True)
        config.write_bytes(original_config)
        bad_config = run('06-config-error', build, 65, ('error:', 'force_unwrapping'), True)
        source.write_bytes(original_source)
        run('07-source-recovery', build, contains=('** BUILD SUCCEEDED **',), phase=True)
        binary.chmod(0o644)
        run('08-not-executable', build, 65, ('error: SwiftLint executable is not executable',), True)
        binary.chmod(binary_mode)
        run('09-execution-recovery', build, contains=('** BUILD SUCCEEDED **',), phase=True)
        binary.rename(backup)
        run('10-missing-tool', build, 65, ('error: SwiftLint executable is missing',), True)
        backup.rename(binary)
        run('11-final-build', build, contains=('** BUILD SUCCEEDED **',), phase=True)
        run('12-program', [str(derived / 'Build/Products/Debug/HelloLintXcode')], contains=('Hello, SwiftLint',))
        if not baseline['objects'] or baseline['objects'] != unchanged['objects']:
            raise RuntimeError('Unchanged build unexpectedly recompiled main.o')
        if not bad_source['objects'] or not (bad_source['objects'] == warning['objects'] == bad_config['objects']):
            raise RuntimeError('Configuration-only check unexpectedly recompiled main.o')
        (evidence / 'incremental-proof.json').write_text(json.dumps(dict(
            unchanged_object_reused=True, config_changes_object_reused=True,
            same_derived_data=True, clean_after_first_build=False), indent=2) + '\n')
    finally:
        source.write_bytes(original_source)
        config.write_bytes(original_config)
        if backup.exists():
            backup.rename(binary)
        if binary.exists():
            binary.chmod(binary_mode)
    print(f'Evidence: {evidence}', flush=True)


if __name__ == '__main__':
    main()
