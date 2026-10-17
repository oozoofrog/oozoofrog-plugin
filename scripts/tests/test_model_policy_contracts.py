"""Static packaging/policy contracts, not live Codex behavior evaluation."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VERSIONS = {'gptplease': '0.3.0'}
PAIRS = {'gptplease': ('README.md', 'references/model-selection.md')}

class ModelPolicyContracts(unittest.TestCase):
    def test_versions_and_skills_only_manifests(self):
        notes = (ROOT / 'docs/model-routing-changelog.md').read_text()
        for name, version in VERSIONS.items():
            with self.subTest(name=name):
                manifest = json.loads((ROOT / 'plugins' / name / '.codex-plugin/plugin.json').read_text())
                self.assertEqual(manifest['name'], name)
                self.assertEqual(manifest['version'], version)
                self.assertEqual(manifest['skills'], './skills/')
                self.assertIn(version, notes)
                for key in ('mcpServers', 'apps', 'hooks'):
                    self.assertNotIn(key, manifest)
                prompts = manifest['interface']['defaultPrompt']
                self.assertTrue(1 <= len(prompts) <= 3)
                for prompt in prompts:
                    self.assertIn('$' + name, prompt)
                    self.assertLessEqual(len(prompt), 128)

    def test_changed_mirror_files_are_byte_and_mode_identical(self):
        for name, relatives in PAIRS.items():
            for relative in relatives:
                with self.subTest(name=name, relative=relative):
                    source = ROOT / name / relative
                    mirror = ROOT / 'plugins' / name / 'skills' / name / relative
                    self.assertFalse(source.is_symlink())
                    self.assertFalse(mirror.is_symlink())
                    self.assertEqual(source.read_bytes(), mirror.read_bytes())
                    self.assertEqual(source.stat().st_mode & 0o777, mirror.stat().st_mode & 0o777)

    def test_operator_scenarios_are_inputs_not_live_results(self):
        scenario = json.loads((ROOT / 'tests/model-routing/scenarios.json').read_text())
        self.assertEqual(scenario['schema_version'], 1)
        self.assertEqual(scenario['kind'], 'operator_scenarios_not_live_results')
        required = {'chat-work-only', 'work-current', 'partial-explicit',
                    'keep-and-recommend', 'pro-and-unknown-send', 'budget-conflict'}
        self.assertEqual(required, {case['id'] for case in scenario['cases']})
        self.assertEqual(len(required), len(scenario['cases']))
        for case in scenario['cases']:
            self.assertEqual(set(case), {'id', 'scope', 'request', 'setup', 'expected_evidence', 'forbidden', 'policy_document'})
            self.assertTrue(case['request'] and case['setup'] and case['expected_evidence'] and case['forbidden'])
            self.assertTrue((ROOT / case['policy_document']).is_file())

    def test_fixture_explicitly_labels_synthetic_runs(self):
        fixture = json.loads((ROOT / 'tests/model-routing/evaluation.fixture.json').read_text())
        self.assertEqual(fixture['origin'], 'fixture')
        self.assertEqual({run['arm'] for run in fixture['runs']}, {'single-astra', 'astra-only', 'mixed-model'})
        self.assertIn('합성', (ROOT / 'docs/model-routing-review.md').read_text())

if __name__ == '__main__':
    unittest.main()
