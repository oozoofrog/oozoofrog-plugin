from __future__ import annotations
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / 'tools/codex-team-harness'

class TeamHarnessDistributionTests(unittest.TestCase):
    def test_public_payload_manifest_and_complete_skill_copies(self):
        manifest = json.loads((BUNDLE / 'manifest.json').read_text())
        self.assertEqual('0.5.7', manifest['version'])
        payload = BUNDLE / 'payload/team-coordination'
        for relative, expected in manifest['files'].items():
            path = BUNDLE / relative
            self.assertFalse(path.is_symlink(), relative)
            self.assertEqual(expected, hashlib.sha256(path.read_bytes()).hexdigest(), relative)
        source = ROOT / 'team-coordination'
        mirror = ROOT / 'plugins/team-coordination/skills/team-coordination'
        for path in payload.rglob('*'):
            if path.is_file():
                relative = path.relative_to(payload)
                self.assertEqual(path.read_bytes(), (source / relative).read_bytes(), str(relative))
                self.assertEqual(path.read_bytes(), (mirror / relative).read_bytes(), str(relative))
        self.assertEqual((source / 'agents/openai.yaml').read_bytes(), (mirror / 'agents/openai.yaml').read_bytes())
        package = json.loads((ROOT / 'plugins/team-coordination/.codex-plugin/plugin.json').read_text())
        self.assertEqual('team-coordination', package['name'])
        self.assertEqual(manifest['version'], package['version'])
        self.assertIn('description: ' + package['description'], (source / 'SKILL.md').read_text())
        for key in ('hooks', 'mcpServers', 'apps'):
            self.assertNotIn(key, package)

    def test_relocated_cli_install_doctor_idempotence_rollback_restore(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            home = work / 'isolated-codex-home'
            home.mkdir()
            baseline = b'Unmanaged synthetic guidance\n'
            (home / 'AGENTS.md').write_bytes(baseline)
            old_policy = home / 'skills/team-coordination/policy.json'
            old_policy.parent.mkdir(parents=True)
            old_policy.write_bytes(b'{"legacy":true}\n')
            original_policy = old_policy.read_bytes()
            plan = work / 'plan.json'
            def call(*args):
                command = [sys.executable, '-I', '-S', '-B', str(BUNDLE / 'bootstrap.py'), '--codex-home', str(home), *args]
                result = subprocess.run(command, capture_output=True, text=True)
                self.assertEqual(0, result.returncode, result.stdout + result.stderr)
                return json.loads(result.stdout)
            first = call('--save-plan', str(plan), 'dry-run')
            self.assertGreater(len(first['changes']), 0)
            self.assertEqual(baseline, (home / 'AGENTS.md').read_bytes())
            self.assertEqual(original_policy, old_policy.read_bytes())
            self.assertGreater(call('--plan', str(plan), 'apply')['changed'], 0)
            self.assertTrue(call('doctor')['integrity_ok'])
            self.assertTrue((home / 'AGENTS.md').read_bytes().startswith(baseline))
            self.assertEqual([], call('--save-plan', str(plan), 'dry-run')['changes'])
            self.assertEqual(0, call('--plan', str(plan), 'apply')['changed'])
            call('rollback')
            self.assertEqual(baseline, (home / 'AGENTS.md').read_bytes())
            self.assertEqual(original_policy, old_policy.read_bytes())
            self.assertFalse((home / 'team-coordination-install.json').exists())
            call('--save-plan', str(plan), 'dry-run')
            self.assertGreater(call('--plan', str(plan), 'apply')['changed'], 0)
            self.assertTrue(call('doctor')['integrity_ok'])
            self.assertFalse(call('doctor')['clean_mac_verified'])

if __name__ == '__main__':
    unittest.main()
