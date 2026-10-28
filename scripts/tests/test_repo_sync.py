from __future__ import annotations

import argparse
import importlib.util
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('auto_sync_daemon', SCRIPTS / 'auto_sync_daemon.py')
daemon = importlib.util.module_from_spec(spec)
spec.loader.exec_module(daemon)


class RepoSyncTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'repo'
        self.root.mkdir()
        self.git('init', '-b', 'main')
        self.git('config', 'user.email', 'test@example.invalid')
        self.git('config', 'user.name', 'Test')
        (self.root / 'scripts').mkdir()
        shutil.copy2(SCRIPTS / 'sync_repo.sh', self.root / 'scripts/sync_repo.sh')
        self.file = self.root / 'file.txt'
        self.file.write_text('base')
        self.git('add', '.')
        self.git('commit', '-m', 'initial')

    def git(self, *args):
        return subprocess.check_output(['git', *args], cwd=self.root, stderr=subprocess.PIPE, text=True).strip()

    def test_repeated_edits_wait_for_quiet_window_even_when_initially_dirty(self):
        self.check_quiet_window(initially_dirty=True)

    def test_repeated_edits_from_clean_start_do_not_sync_while_editing(self):
        self.check_quiet_window(initially_dirty=False)

    def check_quiet_window(self, initially_dirty):
        if initially_dirty:
            self.file.write_text('initial dirty')
        clock = [0]
        sync_times = []
        def sleep(seconds):
            clock[0] += seconds
            if clock[0] <= 8:
                self.file.write_text(f'edit {clock[0]}')
            if clock[0] >= 16:
                daemon.RUNNING = False
        def sync(*args):
            sync_times.append(clock[0])
            self.git('add', '.')
            self.git('commit', '-m', 'synced')
            return 0
        args = argparse.Namespace(repo_root=str(self.root), sync_script=str(self.root / 'scripts/sync_repo.sh'), branch='', interval=2, debounce=4, retry_cooldown=6)
        daemon.RUNNING = True
        with mock.patch.object(daemon, 'parse_args', return_value=args), mock.patch.object(daemon, 'acquire_lock'), mock.patch.object(daemon.signal, 'signal'), mock.patch.object(daemon.time, 'sleep', side_effect=sleep), mock.patch.object(daemon.time, 'monotonic', side_effect=lambda: clock[0]), mock.patch.object(daemon, 'run_sync', side_effect=sync):
            self.assertEqual(daemon.main(), 0)
        self.assertEqual(sync_times, [12])

    def test_same_status_untracked_content_changes_snapshot(self):
        unusual = self.root / 'new\nname.txt'
        unusual.write_text('first')
        before = daemon.git_status(self.root)
        unusual.write_text('other')
        self.assertNotEqual(before, daemon.git_status(self.root))

    def test_staged_changes_and_symlink_targets_affect_snapshot(self):
        self.file.write_text('staged one')
        self.git('add', 'file.txt')
        before = daemon.git_status(self.root)
        self.file.write_text('staged two')
        self.git('add', 'file.txt')
        self.assertNotEqual(before, daemon.git_status(self.root))
        link = self.root / 'link'
        link.symlink_to('/does-not-exist-one')
        before = daemon.git_status(self.root)
        link.unlink()
        link.symlink_to('/does-not-exist-two')
        self.assertNotEqual(before, daemon.git_status(self.root))

    def test_untracked_nested_repository_does_not_break_observation(self):
        nested = self.root / 'nested'
        nested.mkdir()
        subprocess.run(['git', 'init', str(nested)], check=True, capture_output=True)
        (nested / 'file').write_text('first')
        before = daemon.git_status(self.root)
        (nested / 'file').write_text('other')
        self.assertNotEqual(before, daemon.git_status(self.root))

    def test_matching_branch_publishes_new_commit(self):
        remote = Path(self.tmp.name) / 'remote.git'
        subprocess.run(['git', 'init', '--bare', str(remote)], check=True, capture_output=True)
        self.git('remote', 'add', 'origin', str(remote))
        self.git('push', 'origin', 'main')
        self.file.write_text('pending')
        result = subprocess.run(['bash', str(self.root / 'scripts/sync_repo.sh'), '--branch', 'main', '--auto'], cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        remote_head = subprocess.check_output(['git', '--git-dir', str(remote), 'rev-parse', 'main'], text=True).strip()
        self.assertEqual(self.git('rev-parse', 'HEAD'), remote_head)
        self.assertEqual(self.git('status', '--porcelain'), '')

    def test_requested_other_branch_rejected_before_mutation(self):
        remote = Path(self.tmp.name) / 'remote.git'
        subprocess.run(['git', 'init', '--bare', str(remote)], check=True, capture_output=True)
        self.git('remote', 'add', 'origin', str(remote))
        self.git('push', 'origin', 'main')
        self.git('checkout', '-b', 'feature')
        self.file.write_text('pending')
        head = self.git('rev-parse', 'HEAD')
        status = self.git('status', '--porcelain')
        result = subprocess.run(['bash', str(self.root / 'scripts/sync_repo.sh'), '--branch', 'main', '--auto'], cwd=self.root, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertEqual(self.git('rev-parse', 'HEAD'), head)
        self.assertEqual(self.git('status', '--porcelain'), status)
        self.assertFalse((self.root / '.git/FETCH_HEAD').exists())

    def test_explicit_branch_does_not_allow_detached_head(self):
        self.git('checkout', '--detach')
        result = subprocess.run(['bash', str(self.root / 'scripts/sync_repo.sh'), '--branch', 'main', '--dry-run'], cwd=self.root, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)


if __name__ == '__main__':
    unittest.main()
