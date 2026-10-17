"""Historical evaluator fixture integrity, not live model behavior evaluation."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

class ModelRoutingFixtureContracts(unittest.TestCase):
    def test_fixture_explicitly_labels_synthetic_runs(self):
        fixture = json.loads((ROOT / 'tests/model-routing/evaluation.fixture.json').read_text())
        self.assertEqual(fixture['origin'], 'fixture')
        self.assertEqual({run['arm'] for run in fixture['runs']}, {'single-astra', 'astra-only', 'mixed-model'})
        self.assertIn('합성', (ROOT / 'docs/model-routing-review.md').read_text())

if __name__ == '__main__':
    unittest.main()
