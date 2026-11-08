"""Run real SwiftLint builds in a disposable copy; preserve logs and outcomes."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='New evidence directory (must not exist)')
    args = parser.parse_args()
    fixture = Path(__file__).resolve().parent
    if args.output and args.output.resolve().is_relative_to(fixture):
        parser.error('--output must be outside the example directory')
    evidence = args.output or Path(tempfile.mkdtemp(prefix='swiftlint-build-proof-'))
    if args.output:
        evidence.mkdir(parents=True, exist_ok=False)
    evidence = evidence.resolve()
    project = evidence / 'project'
    shutil.copytree(fixture, project, ignore=shutil.ignore_patterns('.build', '__pycache__'))
    source = project / 'Sources/HelloLint/main.swift'
    config = project / '.swiftlint.yml'
    original_source, original_config = source.read_bytes(), config.read_bytes()
    results = []

    def run(name, command, expected_success, contains=()):
        start = time.monotonic()
        proc = subprocess.run(command, cwd=project, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True)
        (evidence / (name + '.log')).write_text(proc.stdout)
        checks = [((proc.returncode == 0) == expected_success)]
        checks += [part in proc.stdout for part in contains]
        entry = dict(name=name, command=command, exit_code=proc.returncode,
                     seconds=round(time.monotonic() - start, 3), passed=all(checks),
                     source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                     config_sha256=hashlib.sha256(config.read_bytes()).hexdigest())
        results.append(entry)
        (evidence / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
        print(f"{name}: exit={proc.returncode}, passed={entry['passed']}", flush=True)
        if not entry['passed']:
            raise RuntimeError(f"Unexpected result; see {evidence / (name + '.log')}")
        return proc.stdout

    build = ['swift', 'build', '-v']
    binary = None
    binary_backup = None
    binary_mode = None
    try:
        run('00-toolchain', ['swift', '--version'], True)
        run('01-clean', build, True, ('Build complete!',))
        binary = project / '.build/artifacts/swiftlintplugins/SwiftLintBinary/SwiftLintBinary.artifactbundle/macos/swiftlint'
        # Mutation is permitted only on this disposable package's own artifact.
        assert binary.resolve().is_relative_to(project.resolve())
        assert not binary.is_symlink()
        binary_mode = binary.stat().st_mode & 0o777
        run('02-swiftlint-version', [str(binary), 'version'], True, ('0.65.1',))
        run('03-unchanged', build, True, ('Running SwiftLint',))
        source.write_text('let greeting: String? = "Hello, SwiftLint"\nprint(greeting!)\n')
        run('04-source-error', build, False, ('error:', 'force_unwrapping'))
        config.write_text(original_config.decode().replace('severity: error', 'severity: warning'))
        run('05-config-warning', build, True, ('Running SwiftLint',))
        run('05a-warning-diagnostic', [str(binary), 'lint', '--config', str(config), str(source)],
            True, ('warning:', 'force_unwrapping'))
        config.write_bytes(original_config)
        run('06-config-error', build, False, ('error:', 'force_unwrapping'))
        source.write_bytes(original_source)
        run('07-source-recovery', build, True, ('Build complete!',))
        binary.chmod(0o644)
        run('08-not-executable', build, False, ('Permission denied',))
        binary.chmod(binary_mode)
        run('09-execution-recovery', build, True, ('Build complete!',))
        binary_backup = binary.with_name('swiftlint.verification-backup')
        binary.rename(binary_backup)
        run('10-missing-tool', build, False, ('No such file or directory',))
        binary_backup.rename(binary)
        binary_backup = None
        run('11-final-build', build, True, ('Build complete!',))
        bin_path = run('12-bin-path', ['swift', 'build', '--show-bin-path'], True).strip().splitlines()[-1]
        run('13-run', [str(Path(bin_path) / 'HelloLint')], True, ('Hello, SwiftLint',))
    finally:
        source.write_bytes(original_source)
        config.write_bytes(original_config)
        if binary_backup and binary_backup.exists():
            binary_backup.rename(binary)
        if binary and binary.exists() and binary_mode is not None:
            binary.chmod(binary_mode)
    print(f'Evidence: {evidence}', flush=True)


if __name__ == '__main__':
    main()
