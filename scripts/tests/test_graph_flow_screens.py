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
        self.assertEqual(list(range(1, 98)), [row['number'] for row in rows])
        self.assertEqual(len(rows), len({row['name'] for row in rows}))
        self.assertEqual(set(scenarios), {row['scenario'] for row in rows})
        for row in rows:
            self.assertIn(row['group'], {'EVERYDAY', 'OCCASIONAL', 'RARE', 'FIRST-SENTENCE', 'LONG-TEXT', 'DECISIONS'})
            viewport = row['viewport']
            self.assertEqual((viewport['width'], viewport['height']),
                             {'desktop': (1440, 900), 'compact-desktop': (1280, 900), 'phone': (390, 844)}[viewport['name']])
            self.assertRegex(row['name'], r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
            self.assertTrue(row['url'].startswith('/?t={token}#project={project}&run={run}'))
            for action in row['interactions']:
                self.assertIn(action['action'], {'click', 'button', 'scroll', 'into', 'open', 'live-plan', 'change-file', 'lower-rows'})
        plugin = SCREENS.parents[1]
        manifest = json.loads((plugin / '.codex-plugin/plugin.json').read_text())
        self.assertEqual(manifest['skills'], './skills/')
        self.assertNotIn('skills', SCREENS.relative_to(plugin).parts)
        self.assertEqual({'build_fixtures.py', 'capture.mjs', 'screens.json', 'README.md'},
                         {p.name for p in SCREENS.iterdir() if p.is_file()})

    def test_round17_scenes_distinguish_state_and_fit(self):
        rows = {r['number']:r for r in json.loads((SCREENS / 'screens.json').read_text())}
        self.assertEqual(rows[27]['interactions'][0]['selector'], '#home-tab')
        self.assertEqual(rows[50]['interactions'][0]['selector'], '#home-tab')
        self.assertNotEqual(rows[33]['viewport'], rows[41]['viewport'])
        self.assertFalse(rows[41]['interactions'])
        self.assertNotEqual(rows[17]['scenario'], rows[44]['scenario'])
        builder = (SCREENS / 'build_fixtures.py').read_text()
        self.assertIn("if scenario == 'large-run':", builder)
        self.assertIn("f.submit('n2', True)", builder)
        self.assertIn("'html':'검색 화면 검토'", builder)
        self.assertIn("'guide':'배포 안내 검토'", builder)
        capture = (SCREENS / 'capture.mjs').read_text()
        self.assertIn('41,44,52,53,58,59,61,62,63', capture)

    def test_e13_named_scenes_and_complete_r18_verification_set(self):
        rows = {r['number']:r for r in json.loads((SCREENS / 'screens.json').read_text())}
        self.assertEqual(rows[11]['interactions'][-1]['action'], 'lower-rows')
        self.assertIn({'action':'button','text':'+'}, rows[11]['interactions'])
        self.assertEqual(rows[27]['interactions'][-1]['selector'], '#home')
        self.assertFalse(rows[36]['interactions'])
        self.assertIn({'action':'click','selector':'.key-recovery button'}, rows[56]['interactions'])
        self.assertEqual(rows[56]['interactions'][-1]['selector'], '#map [data-node="_run_checks"] .node-header')
        capture = (SCREENS / 'capture.mjs').read_text()
        self.assertIn('1,2,3,5,7,10,15,17,18,19,20,21,22,23,24,29,33,34,37,38,41,44,52,53,58,59,61,62,63,64,65,66,67,68,69', capture)
        self.assertIn('lower rows require vertical movement without sideways movement', capture)
        self.assertIn("f.answer(f.decision, 'rejected',", (SCREENS / 'build_fixtures.py').read_text())
