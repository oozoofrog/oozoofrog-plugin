from __future__ import annotations
import json
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
PACKAGES = ('korean-travel-guidebook','obsidian-projects','outcome-brief','verify-work','audit','choice-interview','korean-product-writing','refactor')
class PortableSkillDistributionTests(unittest.TestCase):
    def test_complete_sources_mirrors_metadata_and_font_license(self):
        for name in PACKAGES:
            with self.subTest(name=name):
                source=ROOT/name;mirror=ROOT/'plugins'/name/'skills'/name
                files=lambda p:{str(q.relative_to(p)):q.read_bytes() for q in p.rglob('*') if q.is_file() and q.suffix not in ('.pyc','.pyo') and '__pycache__' not in q.parts}
                self.assertEqual(files(source),files(mirror))
                package=json.loads((ROOT/'plugins'/name/'.codex-plugin/plugin.json').read_text())
                self.assertEqual(name,package['name'])
                self.assertIn(package['description'],(source/'SKILL.md').read_text())
                self.assertIn('$'+name,package['interface']['defaultPrompt'][0])
                self.assertLessEqual(len(package['interface']['defaultPrompt'][0]),128)
                for key in ('hooks','mcpServers','apps'):self.assertNotIn(key,package)
        self.assertIn('SIL OPEN FONT LICENSE', (ROOT/'korean-travel-guidebook/assets/OFL.txt').read_text().upper())
        self.assertFalse((ROOT/'obsidian-projects/references/local-vault.md').exists())
    def test_historical_draft_stays_inactive_and_current_source_matches_reviewed_guide(self):
        draft=ROOT/'drafts/korean-product-writing'
        self.assertTrue((draft/'SKILL.draft.md').is_file())
        self.assertEqual([],list(draft.rglob('SKILL.md')))
        self.assertFalse((draft/'agents').exists())
        self.assertIn('NOT PASSED',(draft/'STATUS.md').read_text())
        current=ROOT/'korean-product-writing'
        for old,new in [('SKILL.draft.md','SKILL.md'),('references/examples.md','references/examples.md'),('references/sources.md','references/sources.md')]:
            self.assertEqual((draft/old).read_bytes(),(current/new).read_bytes())
        self.assertIn('regression-v4/results.md',(draft/'STATUS.md').read_text())
if __name__=='__main__':unittest.main()
