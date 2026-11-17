"""Cheap capture contract: no browser, server, imports with side effects, or fixtures."""
import ast
import json
from pathlib import Path
import unittest

SCREENS = Path(__file__).resolve().parents[2] / 'plugins/graph-flow/dev/screens'


class ScreenManifestTests(unittest.TestCase):
    def test_complete_manifest_matches_builder_and_distribution_boundary(self):
        rows = json.loads((SCREENS / 'screens.json').read_text())
        tree = ast.parse((SCREENS / 'build_fixtures.py').read_text())
        scenarios = next(ast.literal_eval(node.value) for node in tree.body
                         if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'SCENARIOS' for t in node.targets))
        self.assertEqual(list(range(1, 70)), [row['number'] for row in rows])
        self.assertEqual(len(rows), len({row['name'] for row in rows}))
        self.assertEqual(set(scenarios), {row['scenario'] for row in rows})
        for row in rows:
            self.assertIn(row['group'], {'EVERYDAY', 'OCCASIONAL', 'RARE'})
            viewport = row['viewport']
            self.assertEqual((viewport['width'], viewport['height']),
                             {'desktop': (1440, 900), 'phone': (390, 844)}[viewport['name']])
            self.assertRegex(row['name'], r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
            self.assertTrue(row['url'].startswith('/?t={token}#project={project}&run={run}'))
            for action in row['interactions']:
                self.assertIn(action['action'], {'click', 'button', 'scroll', 'into', 'open', 'live-plan', 'change-file'})
        plugin = SCREENS.parents[1]
        manifest = json.loads((plugin / '.codex-plugin/plugin.json').read_text())
        self.assertEqual(manifest['skills'], './skills/')
        self.assertNotIn('skills', SCREENS.relative_to(plugin).parts)
        self.assertEqual({'build_fixtures.py', 'capture.mjs', 'screens.json', 'README.md'},
                         {p.name for p in SCREENS.iterdir() if p.is_file()})
