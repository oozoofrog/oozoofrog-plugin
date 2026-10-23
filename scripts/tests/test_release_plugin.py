from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('release_plugin', SOURCE / 'scripts/release_plugin.py')
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)
contract_spec = importlib.util.spec_from_file_location('capability_report', SOURCE / 'macpilot/scripts/capability_report.py')
capability_report = importlib.util.module_from_spec(contract_spec)
contract_spec.loader.exec_module(capability_report)


class VersionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in ('plugins/macpilot/.codex-plugin/plugin.json', 'macpilot/browser/extension/manifest.json',
                     'macpilot/tool/Sources/MacPilotCore/ConnectionDiagnostics.swift', 'macpilot/scripts/build.sh',
                     'README.md', 'README.ko.md', 'docs/plugin-installation.md', 'scripts/tests/test_plugin_distribution.py'):
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(SOURCE / name, target)
        self.old = json.loads((self.root / 'plugins/macpilot/.codex-plugin/plugin.json').read_text())['version']
        major, minor, micro = map(int, self.old.split('.'))
        self.target = f'{major}.{minor + 1}.0'

    def contents(self):
        return {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}

    def test_same_version_does_not_write_or_increment_build(self):
        before = self.contents()
        release.bump_macpilot(self.root, self.old)
        self.assertEqual(before, self.contents())

    def test_bump_updates_surfaces_and_preserves_other_sections(self):
        readme = self.root / 'README.md'
        readme.write_text(readme.read_text() + '\n## Unrelated draft\nKEEP THIS\n')
        release.bump_macpilot(self.root, self.target)
        self.assertEqual(self.target, json.loads((self.root / 'plugins/macpilot/.codex-plugin/plugin.json').read_text())['version'])
        self.assertIn('KEEP THIS', readme.read_text())
        self.assertIn(f'let version = "{self.target}"', (self.root / 'macpilot/tool/Sources/MacPilotCore/ConnectionDiagnostics.swift').read_text())
        first = self.contents()
        release.bump_macpilot(self.root, self.target)
        self.assertEqual(first, self.contents())

    def test_downgrade_refuses_before_writes(self):
        before = self.contents()
        with self.assertRaisesRegex(release.ReleaseError, 'downgrade'):
            release.bump_macpilot(self.root, '0.0.1')
        self.assertEqual(before, self.contents())

    def test_missing_field_refuses_before_writes(self):
        swift = self.root / 'macpilot/tool/Sources/MacPilotCore/ConnectionDiagnostics.swift'
        swift.write_text('field removed\n')
        before = self.contents()
        with self.assertRaisesRegex(release.ReleaseError, 'Expected one'):
            release.bump_macpilot(self.root, self.target)
        self.assertEqual(before, self.contents())

    def test_duplicate_field_refuses(self):
        with self.assertRaises(release.ReleaseError):
            release.replace_once('version=1\nversion=2', r'version=\d', 'version=3')


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        subprocess.run(['git', 'init', '-q', self.root], check=True)
        for key, value in [('user.name', 'Fixture'), ('user.email', 'fixture@example.invalid')]:
            self.git('config', key, value)
        (self.root / 'owned').mkdir()
        (self.root / 'owned/file').write_text('original\n')
        (self.root / 'other').write_text('unrelated\n')
        self.git('add', '.')
        self.git('commit', '-qm', 'initial')
        self.patcher = patch.object(release, 'ROOT', self.root)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.job = object.__new__(release.Release)
        self.job.args = argparse.Namespace(runtime_evidence=None)
        self.job.name, self.job.version = 'macpilot', '1.0.0'
        self.job.profile = dict(commit_paths=['owned'], checks=[], display_name='Fixture')
        self.job.receipt = {}
        self.job.command = lambda args, **kwargs: release.run(args, cwd=kwargs.pop('cwd', self.root), **kwargs)
        self.job.check_version = lambda root: None

    def git(self, *args):
        return release.run(['git', *args], cwd=self.root).strip()

    def test_pin_runtime_records_both_universal_executables(self):
        import hashlib
        import plistlib
        binary = self.root / 'macpilot/bin/MacPilot.app/Contents/MacOS/macpilot'
        binary.parent.mkdir(parents=True)
        binary.write_bytes(b'exact main binary')
        helper = binary.with_name('macpilot-simulator-hid')
        helper.write_bytes(b'exact isolated driver')
        (binary.parent.parent / 'Info.plist').write_bytes(plistlib.dumps(dict(CFBundleShortVersionString=self.job.version)))
        (self.root / 'macpilot/runtime').mkdir()
        self.job.profile.update(binary=str(binary.relative_to(self.root)), architectures=['arm64','x86_64'], asset_platform='macos-universal')
        self.job.command = lambda args, **kw: 'x86_64 arm64' if args[0] == 'lipo' else ''
        self.job.pin_runtime()
        pins = json.loads((self.root / 'macpilot/runtime/distribution.json').read_text())
        self.assertEqual(hashlib.sha256(binary.read_bytes()).hexdigest(), pins['mainSHA256'])
        self.assertEqual(hashlib.sha256(helper.read_bytes()).hexdigest(), pins['helperSHA256'])
        self.assertEqual('Fixture-1.0.0-macos-universal.zip', pins['asset'])
        self.assertEqual(self.job.version, pins['version'])

    def test_unrelated_staged_file_stops_release(self):
        (self.root / 'other').write_text('user changes\n')
        self.git('add', 'other')
        with self.assertRaisesRegex(release.ReleaseError, 'Unrelated staged'):
            self.job.verify()
        self.assertEqual('other', self.git('diff', '--cached', '--name-only'))

    def test_verify_exports_staged_tree_not_working_tree(self):
        (self.root / 'owned/file').write_text('staged\n')
        self.git('add', 'owned')
        (self.root / 'owned/file').write_text('unstaged\n')
        self.job.profile['checks'] = [['python3', '-c', "from pathlib import Path; assert Path('owned/file').read_text() == 'staged\\n'"]]
        self.job.verify()
        self.assertEqual(self.git('write-tree'), self.job.receipt['verified_tree'])
        self.assertEqual('unstaged\n', (self.root / 'owned/file').read_text())

    def test_changed_index_refuses_commit(self):
        self.job.verify()
        head = self.git('rev-parse', 'HEAD')
        (self.root / 'owned/file').write_text('changed\n')
        self.git('add', 'owned')
        with self.assertRaisesRegex(release.ReleaseError, 'exact staged tree'):
            self.job.commit()
        self.assertEqual(head, self.git('rev-parse', 'HEAD'))

    def test_commit_preserves_unstaged_other_work(self):
        (self.root / 'owned/file').write_text('released\n')
        (self.root / 'other').write_text('user changes\n')
        self.git('add', 'owned')
        self.job.verify()
        self.job.commit()
        self.assertEqual('unrelated', self.git('show', 'HEAD:other'))
        self.assertEqual('user changes\n', (self.root / 'other').read_text())
        self.assertEqual('other', self.git('diff', '--name-only'))

    def test_failed_validation_records_no_verified_tree(self):
        self.job.profile['checks'] = [['python3', '-c', 'raise SystemExit(17)']]
        with self.assertRaises(release.ReleaseError):
            self.job.verify()
        self.assertNotIn('verified_tree', self.job.receipt)

    def test_failed_recheck_revokes_previous_verification(self):
        self.job.verify()
        self.job.profile['checks'] = [['python3', '-c', 'raise SystemExit(9)']]
        with self.assertRaises(release.ReleaseError):
            self.job.verify()
        with self.assertRaisesRegex(release.ReleaseError, 'exact staged tree'):
            self.job.commit()

    def test_publish_requires_verified_commit(self):
        with self.assertRaisesRegex(release.ReleaseError, 'Missing verified commit'):
            self.job.publish()


class RuntimeEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        subprocess.run(['git', 'init', '-q', self.root], check=True)
        (self.root / 'macpilot').mkdir()
        self.source = self.root / 'macpilot/source.swift'
        self.source.write_text('source\n')
        self.contract = self.root / 'macpilot/scripts/capability_report.py'
        self.contract.parent.mkdir()
        shutil.copyfile(SOURCE / 'macpilot/scripts/capability_report.py', self.contract)
        subprocess.run(['git', 'add', '.'], cwd=self.root, check=True)
        self.evidence = self.root / 'evidence'
        self.evidence.mkdir()
        self.binary = self.root / 'binary'
        self.binary.write_bytes(b'tested binary')
        (self.evidence / 'source-manifest.json').write_text(json.dumps({str(p.relative_to(self.root)): release.digest(p) for p in (self.source, self.contract)}))
        (self.evidence / 'features.json').write_text(json.dumps(dict(schema='macpilot-capability-check/2', stage='all',
            suiteStatus='passed', completed=True, binarySHA256=release.digest(self.binary),
            checks=[dict(feature=feature, id=name, status='PASS') for feature, name in capability_report.FULL_CHECKS])))
        (self.evidence / 'runtime.json').write_text(json.dumps({'status': 'passed', 'installedBinary': {'sha256': release.digest(self.binary)}, 'checks': [{'passed': True}]}))

    def verify(self):
        return release.runtime_receipt(self.root, self.evidence, self.binary, 'macpilot', Path('features.json'), Path('runtime.json'), self.contract.relative_to(self.root))

    def test_exact_runtime_evidence_is_reused(self):
        self.assertEqual(1, self.verify()['runtime_checks'])

    def test_new_staged_source_refuses_old_runtime_inventory(self):
        (self.root / 'macpilot/new.swift').write_text('new code')
        subprocess.run(['git', 'add', 'macpilot'], cwd=self.root, check=True)
        with self.assertRaisesRegex(release.ReleaseError, 'inventory'):
            self.verify()

    def test_changed_source_refuses_runtime_reuse(self):
        self.source.write_text('changed source\n')
        with self.assertRaisesRegex(release.ReleaseError, 'stale'):
            self.verify()

    def test_changed_binary_refuses_runtime_reuse(self):
        self.binary.write_bytes(b'different build')
        with self.assertRaisesRegex(release.ReleaseError, 'binary hash'):
            self.verify()

    def test_failed_feature_check_refuses(self):
        data = json.loads((self.evidence / 'features.json').read_text())
        data['checks'][0]['status'] = 'FAIL'
        (self.evidence / 'features.json').write_text(json.dumps(data))
        with self.assertRaisesRegex(release.ReleaseError, 'did not all pass'):
            self.verify()

    def test_missing_runtime_checks_refuses(self):
        data = json.loads((self.evidence / 'runtime.json').read_text())
        data['checks'] = []
        (self.evidence / 'runtime.json').write_text(json.dumps(data))
        with self.assertRaisesRegex(release.ReleaseError, 'did not pass'):
            self.verify()

    def test_aborted_all_pass_prefix_is_not_complete_feature_evidence(self):
        data = json.loads((self.evidence / 'features.json').read_text())
        data.update(schema='macpilot-capability-check/2', stage='all', suiteStatus='failed', completed=False)
        data['checks'] = [dict(feature='image', id=f'prefix_{n}', status='PASS') for n in range(40)]
        (self.evidence / 'features.json').write_text(json.dumps(data))
        with self.assertRaises(release.ReleaseError):
            self.verify()

    def test_image_only_pass_is_not_full_feature_evidence(self):
        data = json.loads((self.evidence / 'features.json').read_text())
        data.update(schema='macpilot-capability-check/2', stage='image', suiteStatus='passed', completed=True)
        (self.evidence / 'features.json').write_text(json.dumps(data))
        with self.assertRaises(release.ReleaseError):
            self.verify()

    def test_missing_duplicate_unexpected_and_legacy_feature_reports_refuse(self):
        original = json.loads((self.evidence / 'features.json').read_text())
        for failure in ('missing', 'duplicate', 'unexpected', 'legacy', 'incomplete', 'cleanup'):
            with self.subTest(failure=failure):
                data = json.loads(json.dumps(original))
                if failure == 'missing': data['checks'].pop()
                elif failure == 'duplicate': data['checks'][-1] = data['checks'][0]
                elif failure == 'unexpected': data['checks'][-1]['id'] = 'not_in_the_trusted_contract'
                elif failure == 'legacy': data.pop('completed')
                elif failure == 'incomplete': data['suiteStatus'] = 'incomplete'
                else: data['cleanupError'] = dict(type='RuntimeError')
                (self.evidence / 'features.json').write_text(json.dumps(data))
                with self.assertRaises(release.ReleaseError): self.verify()


class CapabilityReportTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / 'result.json'

    def checks(self, stage='all'):
        return [dict(feature=feature, id=name, status='PASS') for feature, name in capability_report.required_checks(stage)]

    def test_canonical_inventory_requires_intentional_contract_updates(self):
        from collections import Counter
        self.assertEqual(45, len(capability_report.FULL_CHECKS))
        self.assertEqual(45, len(set(capability_report.FULL_CHECKS)))
        self.assertEqual(12, len(capability_report.required_checks('image')))
        self.assertEqual(dict(wait=11, outcome=2, trace=8, workflow=7, interrupt=5, image=12),
                         dict(Counter(feature for feature, _ in capability_report.FULL_CHECKS)))

    def test_checkpoint_is_incomplete_until_body_and_cleanup_finish(self):
        report = capability_report.CapabilityReport(self.path, 'all', 'binary', self.checks())
        with report.run(cleanup=lambda: None):
            report.checkpoint()
            self.assertEqual('incomplete', json.loads(self.path.read_text())['suiteStatus'])
            with self.assertRaises(ValueError): capability_report.validate_report(json.loads(self.path.read_text()))
        capability_report.validate_report(json.loads(self.path.read_text()))

    def test_all_pass_then_body_error_cannot_leave_passed_report(self):
        report = capability_report.CapabilityReport(self.path, 'all', 'binary', self.checks())
        with self.assertRaises(RuntimeError):
            with report.run(cleanup=lambda: None): raise RuntimeError('must not copy private exception arguments')
        data = json.loads(self.path.read_text())
        self.assertEqual('failed', data['suiteStatus'])
        self.assertFalse(data['completed'])
        self.assertEqual(dict(type='RuntimeError'), data['bodyError'])
        self.assertNotIn('private exception', self.path.read_text())

    def test_cleanup_error_fails_and_does_not_mask_body_error(self):
        def cleanup(): raise ValueError('cleanup failure')
        for body_fails in (False, True):
            with self.subTest(body_fails=body_fails):
                report = capability_report.CapabilityReport(self.path, 'all', 'binary', self.checks())
                expected = RuntimeError if body_fails else ValueError
                with self.assertRaises(expected):
                    with report.run(cleanup=cleanup):
                        if body_fails: raise RuntimeError('primary failure')
                data = json.loads(self.path.read_text())
                self.assertEqual('failed', data['suiteStatus'])
                self.assertFalse(data['completed'])
                self.assertEqual(dict(type='ValueError'), data['cleanupError'])
                if body_fails: self.assertEqual(dict(type='RuntimeError'), data['bodyError'])

    def test_terminal_base_exceptions_cannot_leave_passed_report(self):
        for error in (KeyboardInterrupt(), SystemExit(5)):
            report = capability_report.CapabilityReport(self.path, 'all', 'binary', self.checks())
            with self.assertRaises(type(error)):
                with report.run(cleanup=lambda: None): raise error
            data = json.loads(self.path.read_text())
            self.assertEqual('failed', data['suiteStatus'])
            self.assertFalse(data['completed'])

    def test_missing_tail_or_not_run_never_completes(self):
        checks = self.checks()[:40]
        report = capability_report.CapabilityReport(self.path, 'all', 'binary', checks)
        with report.run(cleanup=lambda: None): pass
        self.assertEqual('incomplete', json.loads(self.path.read_text())['suiteStatus'])
        checks = self.checks(); checks[-1]['status'] = 'NOT_RUN'
        report = capability_report.CapabilityReport(self.path, 'all', 'binary', checks)
        with report.run(cleanup=lambda: None): pass
        self.assertFalse(json.loads(self.path.read_text())['completed'])

    def test_aborted_prefix_preserves_nonzero_process_exit(self):
        code = """import importlib.util, pathlib
spec=importlib.util.spec_from_file_location('report', %r)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
checks=[dict(feature=f,id=n,status='PASS') for f,n in module.FULL_CHECKS[:40]]
report=module.CapabilityReport(pathlib.Path(%r),'all','binary',checks)
with report.run(cleanup=lambda: None): raise RuntimeError('synthetic abort')
""" % (str(SOURCE / 'macpilot/scripts/capability_report.py'), str(self.path))
        process = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True)
        self.assertNotEqual(0, process.returncode)
        data = json.loads(self.path.read_text())
        self.assertEqual(40, len(data['checks']))
        self.assertTrue(all(item['status'] == 'PASS' for item in data['checks']))
        self.assertEqual('failed', data['suiteStatus'])
        with self.assertRaises(ValueError): capability_report.validate_report(data)

    def test_runner_terminal_output_failure_is_inside_completion_guard(self):
        spec = importlib.util.spec_from_file_location('capability_runner_test', SOURCE / 'macpilot/scripts/verify_capabilities.py')
        runner = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'capability_report': capability_report}): spec.loader.exec_module(runner)
        closed = []
        class Fixture:
            def __init__(self, args): pass
            def observe(self): return dict(id='synthetic')
            def call(self, *args): return dict(code='image_search_disabled')
            def close(self): closed.append(True)
        binary = Path(self.temporary.name) / 'binary'
        binary.write_bytes(b'synthetic binary')
        evidence = Path(self.temporary.name) / 'terminal-output'
        argv = ['verify_capabilities.py', '--binary', str(binary), '--fixture', str(binary),
                '--evidence', str(evidence), '--stage', 'image']
        with patch.object(runner, 'Fixture', Fixture), patch.object(sys, 'argv', argv), \
             patch('builtins.print', side_effect=BrokenPipeError('synthetic terminal closure')):
            with self.assertRaises(BrokenPipeError): runner.main()
        data = json.loads((evidence / 'result.json').read_text())
        self.assertEqual('failed', data['suiteStatus'])
        self.assertEqual(dict(type='BrokenPipeError'), data['bodyError'])
        self.assertFalse(data['completed'])
        self.assertEqual([True], closed)


@unittest.skipUnless(sys.platform == 'darwin', 'macOS signing and archive tools required')
class RuntimeArchiveTests(unittest.TestCase):
    def test_signed_app_with_filesystem_metadata_survives_both_extractors(self):
        import plistlib
        import zipfile
        with tempfile.TemporaryDirectory(prefix='runtime-archive-test-') as temporary:
            root = Path(temporary)
            app = root / 'Fixture.app'
            executable = app / 'Contents/MacOS/fixture'
            executable.parent.mkdir(parents=True)
            shutil.copyfile('/usr/bin/true', executable)
            executable.chmod(0o755)
            (app / 'Contents/Info.plist').write_bytes(plistlib.dumps(dict(
                CFBundleIdentifier='local.macpilot.archive-fixture', CFBundleExecutable='fixture',
                CFBundleName='Fixture', CFBundlePackageType='APPL', CFBundleVersion='1')))
            release.run(['xattr', '-w', 'com.apple.metadata:kMDItemFinderComment',
                         'archive regression fixture', str(app)])
            release.run(['codesign', '--force', '--sign', '-', str(app)])
            before = release.digest(executable)
            archive = root / 'fixture.zip'
            release.package_runtime(app, archive)
            self.assertEqual(before, release.digest(executable))
            self.assertEqual('archive regression fixture', release.run(
                ['xattr', '-p', 'com.apple.metadata:kMDItemFinderComment', str(app)]).strip())
            with zipfile.ZipFile(archive) as contents:
                self.assertFalse(any('__MACOSX' in name or Path(name).name.startswith('._')
                                     for name in contents.namelist()))

class PublishTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.assets = self.root / 'assets'
        self.assets.mkdir()
        self.names = ['plugin.tar.gz', 'app.zip', 'SHA256SUMS.txt']
        for name in self.names:
            (self.assets / name).write_bytes(name.encode())
        notes = self.root / 'notes.md'
        notes.write_text('reviewed notes')
        self.job = object.__new__(release.Release)
        self.job.args = argparse.Namespace(notes=notes)
        self.job.name, self.job.version, self.job.tag = 'macpilot', '1.0.0', 'macpilot-v1.0.0'
        self.job.output = self.root
        self.job.profile = dict(branch='main', remote='origin', marketplace_sources=['https://example.invalid/owned'],
                                github_repository='fixture/owned', display_name='MacPilot')
        self.job.receipt = dict(packaged_commit='COMMIT', assets={n: release.digest(self.assets / n) for n in self.names})
        self.job.frozen = lambda: 'COMMIT'
        self.commands = []
        self.job.git = self.git
        self.job.command = self.command
        self.public = dict(isDraft=False, url='https://example.invalid/release')

    def git(self, *args):
        self.commands.append(('git', *args))
        if args[:2] == ('branch', '--show-current'): return 'main'
        if args[:2] == ('rev-parse', 'HEAD'): return 'COMMIT'
        if args[:2] == ('remote', 'get-url'): return 'https://example.invalid/owned'
        if args[0] == 'ls-remote': return 'COMMIT\tref'
        if args[0] == 'tag' and '--list' in args: return 'macpilot-v1.0.0'
        if args[0] == 'rev-parse': return 'COMMIT'
        return ''

    def command(self, args, **kwargs):
        self.commands.append(tuple(args))
        if 'download' in args:
            target = Path(args[args.index('--dir') + 1])
            for name in self.names:
                shutil.copy2(self.assets / name, target / name)
        if 'view' in args: return json.dumps(self.public)
        return ''

    def test_public_same_assets_reconciles_without_overwrite(self):
        with patch.object(release, 'run', return_value=json.dumps(self.public)):
            self.job.publish()
        self.assertEqual(self.public['url'], self.job.receipt['release'])
        self.assertFalse(any(any(verb in c for verb in ['create', 'upload', 'edit']) for c in self.commands))

    def test_assets_from_another_commit_never_publish(self):
        self.job.receipt['packaged_commit'] = 'OLD'
        with self.assertRaisesRegex(release.ReleaseError, 'exact verified commit'):
            self.job.publish()
        self.assertFalse(any('push' in c for c in self.commands))

    def test_changed_asset_stops_before_push(self):
        (self.assets / 'app.zip').write_bytes(b'changed')
        with self.assertRaisesRegex(release.ReleaseError, 'asset changed'):
            self.job.publish()
        self.assertFalse(any('push' in c for c in self.commands))

    def test_foreign_remote_stops_before_push(self):
        original = self.git
        self.job.git = lambda *args: 'https://example.invalid/other' if args[:2] == ('remote', 'get-url') else original(*args)
        with self.assertRaisesRegex(release.ReleaseError, 'remote differs'):
            self.job.publish()
        self.assertFalse(any('push' in c for c in self.commands))

    def test_other_commit_tag_is_not_retargeted(self):
        original = self.git
        self.job.git = lambda *args: 'OTHER' if args == ('rev-parse', 'macpilot-v1.0.0^{}') else original(*args)
        with self.assertRaisesRegex(release.ReleaseError, 'another commit'):
            self.job.publish()
        self.assertFalse(any('tag' in c and '-a' in c for c in self.commands))

    def test_draft_is_published_only_after_download_comparison(self):
        self.public['isDraft'] = False
        with patch.object(release, 'run', return_value=json.dumps(dict(isDraft=True))):
            self.job.publish()
        operations = [c for c in self.commands if c and c[0] == 'gh']
        upload = next(i for i,c in enumerate(operations) if 'upload' in c)
        download = next(i for i,c in enumerate(operations) if 'download' in c)
        edit = next(i for i,c in enumerate(operations) if 'edit' in c)
        self.assertLess(upload, download)
        self.assertLess(download, edit)

    def test_public_different_download_refuses_without_edit(self):
        original = self.command
        def corrupt(args, **kwargs):
            result = original(args, **kwargs)
            if 'download' in args:
                (Path(args[args.index('--dir') + 1]) / 'app.zip').write_bytes(b'foreign bytes')
            return result
        self.job.command = corrupt
        with patch.object(release, 'run', return_value=json.dumps(self.public)):
            with self.assertRaisesRegex(release.ReleaseError, 'Published asset mismatch'):
                self.job.publish()
        self.assertFalse(any('edit' in c or 'upload' in c for c in self.commands))

class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.old = self.root / 'old'
        self.new = self.root / 'new'
        self.old.write_text('old runtime')
        self.new.write_text('new runtime')
        self.launcher = self.root / 'launcher'
        self.launcher.symlink_to(self.old)

    def test_atomic_symlink_switch_preserves_old_runtime(self):
        release.replace_launcher(self.launcher, self.new)
        self.assertEqual(self.new.resolve(), self.launcher.resolve())
        self.assertEqual('old runtime', self.old.read_text())

    def test_regular_user_file_is_never_replaced(self):
        self.launcher.unlink()
        self.launcher.write_text('user script')
        with self.assertRaises(release.ReleaseError):
            release.replace_launcher(self.launcher, self.new)
        self.assertEqual('user script', self.launcher.read_text())

    def test_missing_new_target_preserves_current_launcher(self):
        with self.assertRaises(release.ReleaseError):
            release.replace_launcher(self.launcher, self.root / 'absent')
        self.assertEqual(self.old.resolve(), self.launcher.resolve())

    def test_foreign_temporary_link_is_preserved(self):
        temporary = self.launcher.with_name(self.launcher.name + '.release-tmp')
        temporary.symlink_to(self.root / 'absent')
        with self.assertRaises(release.ReleaseError):
            release.replace_launcher(self.launcher, self.new)
        self.assertTrue(temporary.is_symlink())
        self.assertEqual(self.old.resolve(), self.launcher.resolve())


class InstallPreflightTests(unittest.TestCase):
    def setUp(self):
        self.job = object.__new__(release.Release)
        self.job.frozen = lambda: 'COMMIT'
        self.job.args = argparse.Namespace(codex='fixture-codex')
        self.job.profile = dict(marketplace='owned', marketplace_sources=['https://example.invalid/owned'])
        self.job.receipt = dict(release='https://example.invalid/release', published_commit='COMMIT')
        self.job.selector = 'macpilot@owned'
        self.commands = []
        self.sources = [dict(name='owned', root='/nonexistent-fixture', marketplaceSource=dict(sourceType='git', source='https://example.invalid/owned'))]
        self.job.command = self.command

    def command(self, args, **kwargs):
        self.commands.append(tuple(args))
        if 'marketplace' in args and 'list' in args:
            return json.dumps(dict(marketplaces=self.sources))
        if 'upgrade' in args:
            return json.dumps(dict(errors=['network unavailable']))
        if 'list' in args:
            return json.dumps(dict(installed=[]))
        raise AssertionError(args)

    def test_unpublished_release_never_installs(self):
        self.job.receipt.clear()
        with self.assertRaisesRegex(release.ReleaseError, 'Publish before'):
            self.job.install()
        self.assertEqual([], self.commands)

    def test_foreign_marketplace_never_installs(self):
        self.sources[0]['marketplaceSource']['source'] = 'https://example.invalid/other'
        with self.assertRaisesRegex(release.ReleaseError, 'source differs'):
            self.job.install()
        self.assertFalse(any('add' in c or 'upgrade' in c for c in self.commands))

    def test_upgrade_failure_never_installs(self):
        with self.assertRaisesRegex(release.ReleaseError, 'upgrade failed'):
            self.job.install()
        self.assertFalse(any('add' in c for c in self.commands))


class LogTests(unittest.TestCase):
    def test_successful_stderr_is_preserved_without_polluting_json(self):
        with tempfile.TemporaryDirectory() as temporary:
            log = Path(temporary) / 'command.log'
            result = release.run(['python3', '-c', 'import sys; print("{\\"ok\\":true}"); print("validation details", file=sys.stderr)'], log_path=log)
            self.assertEqual({'ok': True}, json.loads(result))
            self.assertIn('validation details', log.read_text())
            self.assertIn('stderr:', log.read_text())


if __name__ == '__main__':
    unittest.main()
