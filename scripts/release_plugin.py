#!/usr/bin/env python3
"""Version, verify, publish and install one repository Plugin without global reloads."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


class ReleaseError(RuntimeError):
    pass


def run(args, *, cwd=ROOT, env=None, timeout=300, input=None, log_path=None):
    result = subprocess.run([str(x) for x in args], cwd=cwd, env=env,
                            capture_output=True, text=True, timeout=timeout, input=input)
    if log_path:
        log_path.write_text(json.dumps([str(x) for x in args]) + '\nstdout:\n' + result.stdout + '\nstderr:\n' + result.stderr)
    if result.returncode:
        raise ReleaseError(f"Command failed ({result.returncode}): {args!r}\n{result.stdout}\n{result.stderr}")
    return result.stdout


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def package_runtime(app, archive, command=run):
    """Exclude filesystem metadata and verify both supported extraction paths."""
    command(['codesign', '--verify', '--deep', '--strict', str(app)])
    command(['ditto', '--norsrc', '-c', '-k', '--keepParent', str(app), str(archive)])
    expected = {str(p.relative_to(app)): (digest(p), bool(p.stat().st_mode & 0o111))
                for p in app.rglob('*') if p.is_file()}
    for extractor in ('ditto', 'unzip'):
        with tempfile.TemporaryDirectory(prefix='plugin-archive-check-') as temporary:
            if extractor == 'ditto':
                command(['ditto', '-x', '-k', str(archive), temporary])
            else:
                command(['unzip', '-q', str(archive), '-d', temporary])
            extracted = Path(temporary) / app.name
            if any(p.name.startswith('._') or p.name == '__MACOSX'
                   for p in Path(temporary).rglob('*')):
                raise ReleaseError('Runtime archive contains AppleDouble metadata')
            actual = {str(p.relative_to(extracted)): (digest(p), bool(p.stat().st_mode & 0o111))
                      for p in extracted.rglob('*') if p.is_file()}
            if actual != expected:
                raise ReleaseError(f'{extractor} changed runtime bytes or executable modes')
            command(['codesign', '--verify', '--deep', '--strict', str(extracted)])


def runtime_receipt(root, evidence, binary, name, feature_report, runtime_report, feature_contract):
    manifest = json.loads((evidence / 'source-manifest.json').read_text())
    selected = {p: sha for p, sha in manifest.items() if p.startswith((name + '/', f'plugins/{name}/'))}
    if not selected:
        raise ReleaseError('Runtime evidence contains no selected source hashes')
    tracked = set(run(['git', 'ls-files', '-z', '--', name, f'plugins/{name}'], cwd=root).strip('\0').split('\0'))
    if set(selected) != tracked:
        raise ReleaseError('Runtime source manifest does not cover the exact staged package inventory')
    for path, sha in selected.items():
        if digest(root / path) != sha:
            raise ReleaseError(f'Runtime evidence stale: {path}')
        committed = subprocess.run(['git', 'show', f':{path}'], cwd=root, capture_output=True, check=True).stdout
        if hashlib.sha256(committed).hexdigest() != sha:
            raise ReleaseError(f'Runtime evidence differs from index: {path}')
    feature_path = evidence / feature_report
    runtime_path = evidence / runtime_report
    feature, runtime = (json.loads(p.read_text()) for p in (feature_path, runtime_path))
    sha = digest(binary)
    if feature.get('binarySHA256') != sha or runtime.get('installedBinary', {}).get('sha256') != sha:
        raise ReleaseError('Tested binary hash differs from packaged binary')
    contract_path = root / feature_contract
    spec = importlib.util.spec_from_file_location('release_capability_contract', contract_path)
    contract = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(contract)
    try:
        contract.validate_report(feature, required_stage='all')
    except ValueError as error:
        raise ReleaseError(str(error)) from error
    if runtime.get('status') != 'passed' or not runtime.get('checks') or any(x.get('passed') is not True for x in runtime['checks']):
        raise ReleaseError('Runtime regression did not pass')
    return dict(path=str(evidence.resolve()), source_files=len(selected), binary_sha256=sha,
                feature_checks=len(feature['checks']), runtime_checks=len(runtime['checks']),
                reports={str(p.relative_to(evidence)): digest(p) for p in (feature_path, runtime_path)})


def replace_once(text, pattern, replacement):
    result, count = re.subn(pattern, replacement, text, flags=re.MULTILINE)
    if count != 1:
        raise ReleaseError(f"Expected one version field, found {count}: {pattern}")
    return result


def replace_launcher(launcher, target):
    if not launcher.is_symlink() or not target.is_file():
        raise ReleaseError('Launcher replacement requires an existing symlink and a valid target')
    temporary = launcher.with_name(launcher.name + '.release-tmp')
    if temporary.exists() or temporary.is_symlink():
        raise ReleaseError('Temporary launcher already exists')
    temporary.symlink_to(target)
    os.replace(temporary, launcher)


def bump_macpilot(root, version):
    """Narrow substitutions preserve unrelated working-tree hunks; same version is a no-op."""
    manifest = root / 'plugins/macpilot/.codex-plugin/plugin.json'
    old = json.loads(manifest.read_text())['version']
    if tuple(map(int, version.split('.'))) < tuple(map(int, old.split('.'))):
        raise ReleaseError('Version downgrade refused')
    changes = {}
    data = manifest.read_text()
    changes[manifest] = replace_once(data, r'("version": ")[^"]+("\s*,)', rf'\g<1>{version}\2')
    browser = root / 'macpilot/browser/extension/manifest.json'
    changes[browser] = replace_once(browser.read_text(), r'("version": ")[^"]+("\s*,)', rf'\g<1>{version}\2')
    swift = root / 'macpilot/tool/Sources/MacPilotCore/ConnectionDiagnostics.swift'
    changes[swift] = replace_once(swift.read_text(), r'(public static let version = ")[^"]+("\s*)$', rf'\g<1>{version}\2')
    build = root / 'macpilot/scripts/build.sh'
    text = replace_once(build.read_text(), r'(<key>CFBundleShortVersionString</key><string>)[^<]+(</string>)', rf'\g<1>{version}\2')
    if old != version:
        text = replace_once(text, r'(<key>CFBundleVersion</key><string>)(\d+)(</string>)',
                            lambda m: m[1] + str(int(m[2]) + 1) + m[3])
    changes[build] = text
    distribution = root / 'macpilot/runtime/distribution.json'
    if distribution.exists():
        pins = json.loads(distribution.read_text())
        if pins.get('version') != version:
            pins.update(version=version, asset=f'MacPilot-{version}-macos-universal.zip', mainSHA256='', helperSHA256='')
            changes[distribution] = json.dumps(pins, indent=2) + '\n'
    for name in ('README.md', 'README.ko.md', 'docs/plugin-installation.md'):
        path = root / name
        text = path.read_text()
        start = text.index('## MacPilot\n')
        end = text.find('\n## ', start + 1)
        end = len(text) if end < 0 else end
        section = text[start:end]
        if f'`{old}`' not in section:
            raise ReleaseError(f'Missing current MacPilot version in {name}')
        changes[path] = text[:start] + section.replace(f'`{old}`', f'`{version}`') + text[end:]
    test = root / 'scripts/tests/test_plugin_distribution.py'
    changes[test] = replace_once(test.read_text(), r'(self.assertEqual\(")[\d.]+(", manifest\["version"\]\))', rf'\g<1>{version}\2')
    # Validate every substitution before the first write. Do not create backup copies.
    for path, text in changes.items():
        if path.read_text() != text:
            path.write_text(text)
    return old


class Release:
    def __init__(self, args):
        self.args = args
        self.name, self.version = args.plugin, args.version
        self.profile = json.loads((ROOT / 'scripts/releases' / f'{self.name}.json').read_text())
        self.tag = f'{self.name}-v{self.version}'
        self.selector = f'{self.name}@{self.profile["marketplace"]}'
        self.output = args.evidence.resolve()
        self.output.mkdir(parents=True, exist_ok=True)
        self.receipt_path = self.output / 'receipt.json'
        self.receipt = json.loads(self.receipt_path.read_text()) if self.receipt_path.exists() else {}
        identity = dict(plugin=self.name, version=self.version, repository=str(ROOT))
        if self.receipt and any(self.receipt.get(k) != v for k, v in identity.items()):
            raise ReleaseError('Receipt belongs to a different release')
        self.receipt.update(identity)
        self.counter = len(list(self.output.glob('command-*.log')))

    def save(self):
        temporary = self.receipt_path.with_suffix('.tmp')
        temporary.write_text(json.dumps(self.receipt, indent=2, ensure_ascii=False) + '\n')
        os.replace(temporary, self.receipt_path)

    def command(self, args, **kwargs):
        self.counter += 1
        log = self.output / f'command-{self.counter:03}.log'
        try:
            return run(args, log_path=log, **kwargs)
        except Exception as exc:
            if not log.exists():
                log.write_text(json.dumps([str(x) for x in args]) + '\n' + str(exc))
            raise

    def git(self, *args):
        return self.command(['git', *args]).strip()

    def prepare(self):
        if self.name != 'macpilot':
            raise ReleaseError('No version adapter for this Plugin')
        old = bump_macpilot(ROOT, self.version)
        self.command([sys.executable, 'scripts/sync_skill_mirrors.py', '--package', self.name, '--write'])
        self.receipt['prepared'] = dict(previous=old, target=self.version)

    def check_version(self, root):
        manifest = json.loads((root / f'plugins/{self.name}/.codex-plugin/plugin.json').read_text())
        if manifest['version'] != self.version:
            raise ReleaseError('Manifest version differs from release')
        catalog = json.loads((root / '.agents/plugins/marketplace.json').read_text())
        if catalog['name'] != self.profile['marketplace'] or not any(
                x['name'] == self.name and x['source']['path'] == f'./plugins/{self.name}' for x in catalog['plugins']):
            raise ReleaseError('Marketplace does not point to selected Plugin')
        if self.name == 'macpilot':
            if json.loads((root / 'macpilot/browser/extension/manifest.json').read_text())['version'] != self.version:
                raise ReleaseError('Browser version mismatch')
            if f'let version = "{self.version}"' not in (root / 'macpilot/tool/Sources/MacPilotCore/ConnectionDiagnostics.swift').read_text():
                raise ReleaseError('Runtime version mismatch')
            if f'<key>CFBundleShortVersionString</key><string>{self.version}</string>' not in (root / 'macpilot/scripts/build.sh').read_text():
                raise ReleaseError('App version mismatch')
            for name in ('README.md', 'README.ko.md', 'docs/plugin-installation.md'):
                text = (root / name).read_text()
                start = text.index('## MacPilot\n')
                end = text.find('\n## ', start + 1)
                if f'`{self.version}`' not in text[start:end if end >= 0 else len(text)]:
                    raise ReleaseError(f'Documented MacPilot version mismatch: {name}')
            if f'## MacPilot [{self.version}]' not in (root / 'CHANGELOG.md').read_text():
                raise ReleaseError('Missing release changelog')

    def verify(self):
        self.receipt.pop('verified_tree', None)
        self.receipt.pop('runtime_evidence', None)
        staged = self.git('diff', '--cached', '--name-only', '-z').split('\0')
        allowed = self.profile['commit_paths']
        for path in filter(None, staged):
            if not any(path == prefix or path.startswith(prefix.rstrip('/') + '/') for prefix in allowed):
                raise ReleaseError(f'Unrelated staged path: {path}')
        self.git('diff', '--cached', '--check')
        tree = self.git('write-tree')
        with tempfile.TemporaryDirectory(prefix='plugin-release-verify-') as temporary:
            target = Path(temporary)
            archive = subprocess.run(['git', 'archive', tree], cwd=ROOT, capture_output=True, check=True).stdout
            subprocess.run(['tar', '-xf', '-', '-C', str(target)], input=archive, check=True)
            self.check_version(target)
            for command in self.profile['checks']:
                self.command(command, cwd=target)
        runtime = self.args.runtime_evidence
        if runtime:
            if not self.args.feature_report or not self.args.runtime_report:
                raise ReleaseError('Supply --feature-report and --runtime-report relative to --runtime-evidence')
            self.receipt['runtime_evidence'] = runtime_receipt(
                ROOT, runtime, ROOT / self.profile['binary'], self.name, self.args.feature_report, self.args.runtime_report,
                self.profile['feature_contract'])
        self.receipt['verified_tree'] = tree
        self.receipt['verified_at'] = time.time()

    def commit(self):
        if self.git('write-tree') != self.receipt.get('verified_tree'):
            raise ReleaseError('Verify the exact staged tree before committing')
        if self.git('diff', '--cached', '--name-only'):
            options = []
            if getattr(self.args, 'amend', False):
                if self.receipt.get('release') or self.receipt.get('commit') != self.git('rev-parse', 'HEAD'):
                    raise ReleaseError('Amend only this receipt\'s unpublished HEAD')
                options.append('--amend')
            self.git('commit', *options, '-m', f'Release {self.profile["display_name"]} {self.version}')
        if self.git('rev-parse', 'HEAD^{tree}') != self.receipt['verified_tree']:
            raise ReleaseError('Committed tree differs from verified tree')
        commit = self.git('rev-parse', 'HEAD')
        if self.receipt.get('commit') != commit:
            for key in ('assets', 'packaged_commit', 'release', 'published_commit', 'installation'):
                self.receipt.pop(key, None)
        self.receipt['commit'] = commit

    def frozen(self):
        commit = self.receipt.get('commit')
        if not commit or self.git('rev-parse', f'{commit}^{{tree}}') != self.receipt.get('verified_tree'):
            raise ReleaseError('Missing verified commit')
        self.check_version(ROOT)
        # Never package unstaged or post-verification changes to the selected source.
        for prefix in (self.name, f'plugins/{self.name}', 'scripts/release_plugin.py',
                       f'scripts/releases/{self.name}.json', 'scripts/tests/test_release_plugin.py', 'docs/plugin-release.md'):
            if self.git('diff', commit, '--', prefix):
                raise ReleaseError(f'Source changed since verification: {prefix}')
        return commit

    def pin_runtime(self):
        """Pin final signed executable bytes before mirroring/staging runtime evidence."""
        binary = ROOT / self.profile['binary']
        helper = binary.with_name('macpilot-simulator-hid')
        import plistlib
        app = binary.parents[2]
        self.command(['codesign', '--verify', '--deep', '--strict', str(app)])
        actual = plistlib.loads((app / 'Contents/Info.plist').read_bytes())['CFBundleShortVersionString']
        if actual != self.version:
            raise ReleaseError('Build the requested version before pin-runtime')
        expected = set(self.profile.get('architectures', ['arm64']))
        for path in (binary, helper):
            if set(self.command(['lipo', '-archs', str(path)]).split()) != expected:
                raise ReleaseError('Runtime architecture mismatch')
        manifest = dict(version=self.version,
                        asset=f'{self.profile["display_name"]}-{self.version}-{self.profile.get("asset_platform", "macos-arm64")}.zip',
                        mainSHA256=digest(binary), helperSHA256=digest(helper))
        path = ROOT / self.name / 'runtime/distribution.json'
        path.write_text(json.dumps(manifest, indent=2) + '\n')
        self.receipt['runtime_pins'] = manifest

    def package(self):
        commit = self.frozen()
        assets = self.output / 'assets'
        assets.mkdir(exist_ok=True)
        plugin = assets / f'{self.name}-plugin-{self.version}.tar.gz'
        self.git('archive', '--format=tar.gz', f'--output={plugin}', commit, f'plugins/{self.name}')
        binary = ROOT / self.profile['binary']
        expected = self.receipt.get('runtime_evidence', {}).get('binary_sha256')
        if not expected or digest(binary) != expected:
            raise ReleaseError('Exact tested binary required; supply --runtime-evidence during verify')
        app = binary.parents[2]
        self.command(['codesign', '--verify', '--strict', str(app)])
        for path in (binary, binary.with_name('macpilot-simulator-hid')):
            if set(self.command(['lipo', '-archs', str(path)]).split()) != set(self.profile.get('architectures', ['arm64'])):
                raise ReleaseError('Runtime archive architecture mismatch')
        pins = json.loads((ROOT / self.name / 'runtime/distribution.json').read_text())
        if pins['mainSHA256'] != digest(binary) or pins['helperSHA256'] != digest(binary.with_name('macpilot-simulator-hid')):
            raise ReleaseError('Runtime pins differ from packaged executables')
        import plistlib
        if plistlib.loads((app / 'Contents/Info.plist').read_bytes())['CFBundleShortVersionString'] != self.version:
            raise ReleaseError('App bundle version mismatch')
        archive = assets / f'{self.profile["display_name"]}-{self.version}-{self.profile.get("asset_platform", "macos-arm64")}.zip'
        package_runtime(app, archive, self.command)
        hashes = {p.name: digest(p) for p in (plugin, archive)}
        (assets / 'SHA256SUMS.txt').write_text(''.join(f'{sha}  {name}\n' for name, sha in hashes.items()))
        self.receipt['assets'] = {**hashes, 'SHA256SUMS.txt': digest(assets / 'SHA256SUMS.txt')}
        self.receipt['packaged_commit'] = commit

    def publish(self):
        commit = self.frozen()
        if self.receipt.get('packaged_commit') != commit:
            raise ReleaseError('Package the exact verified commit before publishing')
        if self.git('branch', '--show-current') != self.profile['branch'] or self.git('rev-parse', 'HEAD') != commit:
            raise ReleaseError('Publish only from the verified branch HEAD')
        assets = self.output / 'assets'
        for name, sha in self.receipt.get('assets', {}).items():
            if digest(assets / name) != sha:
                raise ReleaseError(f'Release asset changed: {name}')
        if len(self.receipt.get('assets', {})) < 3:
            raise ReleaseError('Package assets first')
        notes = self.args.notes
        if not notes or not notes.is_file():
            raise ReleaseError('--notes with reviewed release notes is required')
        remote, branch = self.profile['remote'], self.profile['branch']
        if self.git('remote', 'get-url', remote).removesuffix('.git') not in self.profile['marketplace_sources']:
            raise ReleaseError('Git remote differs from the release repository')
        self.git('fetch', remote, branch)
        self.git('merge-base', '--is-ancestor', f'{remote}/{branch}', commit)
        self.git('push', remote, f'{commit}:refs/heads/{branch}')
        if self.git('ls-remote', remote, f'refs/heads/{branch}').split()[0] != commit:
            raise ReleaseError('Remote branch verification failed')
        tags = self.git('tag', '--list', self.tag)
        if tags:
            if self.git('rev-parse', f'{self.tag}^{{}}') != commit:
                raise ReleaseError('Existing tag targets another commit')
        else:
            self.git('tag', '-a', self.tag, commit, '-m', f'{self.profile["display_name"]} {self.version}')
        self.git('push', remote, f'refs/tags/{self.tag}')
        if self.git('ls-remote', remote, f'refs/tags/{self.tag}^{{}}').split()[0] != commit:
            raise ReleaseError('Remote tag verification failed')
        gh = ['gh', 'release', '--repo', self.profile['github_repository']]
        try:
            existing = json.loads(run([*gh, 'view', self.tag, '--json', 'url,isDraft,tagName']))
        except ReleaseError:
            self.command([*gh, 'create', self.tag, '--verify-tag', '--draft', '--title',
                          f'{self.profile["display_name"]} {self.version}', '--notes-file', str(notes)])
            existing = {'isDraft': True}
        if existing['isDraft']:
            self.command([*gh, 'upload', self.tag, *[str(assets / n) for n in self.receipt['assets']], '--clobber'])
        # Compare downloaded bytes even after an uncertain previous publish. Never overwrite a public release.
        with tempfile.TemporaryDirectory(prefix='plugin-release-download-') as temporary:
            self.command([*gh, 'download', self.tag, '--dir', temporary])
            for name, sha in self.receipt['assets'].items():
                if digest(Path(temporary) / name) != sha:
                    raise ReleaseError(f'Published asset mismatch: {name}')
        if existing['isDraft']:
            self.command([*gh, 'edit', self.tag, '--draft=false'])
        release = json.loads(self.command([*gh, 'view', self.tag, '--json', 'url,isDraft']))
        if release['isDraft']:
            raise ReleaseError('Release remains a draft')
        self.receipt['release'] = release['url']
        self.receipt['published_commit'] = commit

    def install(self):
        commit = self.frozen()
        if not self.receipt.get('release') or self.receipt.get('published_commit') != commit:
            raise ReleaseError('Publish before installation')
        cli = self.args.codex
        marketplace = self.profile['marketplace']
        sources = json.loads(self.command([cli, 'plugin', 'marketplace', 'list', '--json']))['marketplaces']
        source = next((x for x in sources if x['name'] == marketplace), None)
        if not source or source.get('marketplaceSource', {}).get('sourceType') != 'git':
            raise ReleaseError('Register the intended Git marketplace before installation')
        if source['marketplaceSource']['source'].removesuffix('.git') not in self.profile['marketplace_sources']:
            raise ReleaseError('Configured marketplace source differs from release repository')
        before = json.loads(self.command([cli, 'plugin', 'list', '--json']))['installed']
        prior = next((x for x in before if x['pluginId'] == self.selector), None)
        old_path = None
        if prior:
            codex_home = Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex')))
            old_path = codex_home / 'plugins/cache' / marketplace / self.name / prior['version']
            if old_path.exists():
                self.receipt['previous_install'] = str(old_path)
        upgrade = json.loads(self.command([cli, 'plugin', 'marketplace', 'upgrade', marketplace, '--json']))
        if upgrade.get('errors'):
            raise ReleaseError(f'Marketplace upgrade failed: {upgrade["errors"]}')
        snapshot = Path(source['root'])
        self.check_version(snapshot)
        committed_manifest = json.loads(self.git('show', f'{commit}:plugins/{self.name}/.codex-plugin/plugin.json'))
        if json.loads((snapshot / f'plugins/{self.name}/.codex-plugin/plugin.json').read_text()) != committed_manifest:
            raise ReleaseError('Marketplace snapshot manifest differs from release')
        result = json.loads(self.command([cli, 'plugin', 'add', self.selector, '--json']))
        if result['version'] != self.version or result['pluginId'] != self.selector:
            raise ReleaseError('Installed version/selector mismatch')
        installed = Path(result['installedPath'])
        if old_path and old_path != installed and not old_path.exists() and not old_path.is_symlink():
            old_path.symlink_to(installed, target_is_directory=True)
            self.receipt['compatibility_alias'] = dict(path=str(old_path), target=str(installed))
            self.save()
        # Compare every published file and its executable mode against the verified Git tree.
        prefix = f'plugins/{self.name}/'
        files = self.git('ls-tree', '-r', commit, '--', f'plugins/{self.name}').splitlines()
        for row in files:
            metadata, path = row.split('\t', 1)
            mode, kind, object_id = metadata.split()
            actual = installed / path[len(prefix):]
            if kind != 'blob' or actual.is_symlink() or not actual.is_file():
                raise ReleaseError(f'Invalid installed file: {actual}')
            if self.git('hash-object', str(actual)) != object_id or bool(actual.stat().st_mode & 0o111) != (mode == '100755'):
                raise ReleaseError(f'Installed bytes/mode mismatch: {actual}')
        # Install the exact tested app from the published asset, rather than building a
        # different binary at first launch. No original cache or process is stopped.
        asset_name = f'{self.profile["display_name"]}-{self.version}-{self.profile.get("asset_platform", "macos-arm64")}.zip'
        with tempfile.TemporaryDirectory(prefix='plugin-installed-app-') as temporary:
            self.command(['gh', 'release', 'download', self.tag, '--repo', self.profile['github_repository'],
                          '--pattern', asset_name, '--dir', temporary])
            archive = Path(temporary) / asset_name
            if digest(archive) != self.receipt['assets'][asset_name]:
                raise ReleaseError('Downloaded app hash mismatch')
            self.command(['ditto', '-x', '-k', str(archive), temporary])
            app = Path(temporary) / (self.profile['display_name'] + '.app')
            self.command(['codesign', '--verify', '--strict', str(app)])
            relative = f'Contents/MacOS/{self.name}'
            expected = self.receipt['runtime_evidence']['binary_sha256']
            if digest(app / relative) != expected:
                raise ReleaseError('Downloaded executable hash mismatch')
            destination = installed / f'skills/{self.name}/bin/{app.name}'
            if destination.exists():
                if digest(destination / relative) != expected:
                    raise ReleaseError('Existing installed app differs; refusing overwrite')
            else:
                destination.parent.mkdir(exist_ok=True)
                self.command(['ditto', str(app), str(destination)])
            self.command(['codesign', '--verify', '--strict', str(destination)])
            # The launcher verifies pinned runtime bytes; source timestamps do not trigger compilation.
        if self.args.launcher:
            launcher = self.args.launcher.expanduser()
            target = installed / f'skills/{self.name}/scripts/{self.name}'
            replace_launcher(launcher, target)
        after = json.loads(self.command([cli, 'plugin', 'list', '--json']))['installed']
        others = lambda rows: sorted((x['pluginId'], x['version'], x.get('enabled')) for x in rows if x['pluginId'] != self.selector)
        if others(before) != others(after):
            raise ReleaseError('Other Plugin installation state changed')
        selected = next(x for x in after if x['pluginId'] == self.selector)
        if not selected.get('enabled') or selected['version'] != self.version:
            raise ReleaseError('New Plugin is not enabled')
        launcher = installed / f'skills/{self.name}/scripts/{self.name}'
        connection = json.loads(self.command([str(launcher), 'connection-check']))
        if connection.get('status') != 'probe_passed' or connection.get('hostConnectionVerified') is not False:
            raise ReleaseError(f'Installed isolated connection failed: {connection}')
        status = json.loads(self.command([str(launcher), 'call', 'mac_connection', '--json', '-'],
                                        input=json.dumps({'operation': 'status'})))
        if status.get('version') != self.version:
            raise ReleaseError('Installed CLI runtime version mismatch')
        if digest(destination / relative) != expected:
            raise ReleaseError('Installed launch rebuilt or changed the tested binary')
        self.receipt['installation'] = dict(path=str(installed), version=self.version,
                                            enabled=True, files_verified=len(files), current_chat_reloaded=False,
                                            isolated_connection=connection)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=['prepare', 'pin-runtime', 'verify', 'commit', 'package', 'publish', 'install'])
    parser.add_argument('--plugin', required=True, choices=['macpilot'])
    parser.add_argument('--version', required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--runtime-evidence', type=Path)
    parser.add_argument('--feature-report', type=Path)
    parser.add_argument('--runtime-report', type=Path)
    parser.add_argument('--notes', type=Path)
    parser.add_argument('--codex', default='codex')
    parser.add_argument('--launcher', type=Path)
    parser.add_argument('--amend', action='store_true', help='Amend only this receipt\'s unpublished commit')
    args = parser.parse_args(argv)
    if not re.fullmatch(r'\d+\.\d+\.\d+', args.version):
        parser.error('--version must be MAJOR.MINOR.PATCH')
    release = Release(args)
    lock = Path(run(['git', 'rev-parse', '--git-path', 'plugin-release.lock']).strip())
    if not lock.is_absolute():
        lock = ROOT / lock
    try:
        lock.mkdir()
    except FileExistsError:
        raise SystemExit(f'Another release phase owns {lock}; reconcile it before retrying')
    try:
        getattr(release, args.phase.replace('-', '_'))()
        release.receipt['last_successful_phase'] = args.phase
        release.receipt.pop('error', None)
        release.save()
        print(json.dumps(release.receipt, indent=2, ensure_ascii=False))
    except Exception as exc:
        release.receipt['error'] = dict(phase=args.phase, message=str(exc))
        release.save()
        print(str(exc), file=sys.stderr)
        return 1
    finally:
        lock.rmdir()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
