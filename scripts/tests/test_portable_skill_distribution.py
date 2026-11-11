from __future__ import annotations
import json
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
PACKAGES = ('korean-product-writing','refactor','openai-decisions','handoff','model-advisor')
class PortableSkillDistributionTests(unittest.TestCase):
    def test_complete_sources_and_metadata(self):
        for name in PACKAGES:
            with self.subTest(name=name):
                source=ROOT/'plugins'/name/'skills'/name
                self.assertTrue((source/'SKILL.md').is_file())
                self.assertTrue((source/'agents/openai.yaml').is_file())
                package=json.loads((ROOT/'plugins'/name/'.codex-plugin/plugin.json').read_text())
                self.assertEqual(name,package['name'])
                self.assertIn(package['description'],(source/'SKILL.md').read_text())
                self.assertIn('$'+name,package['interface']['defaultPrompt'][0])
                self.assertLessEqual(len(package['interface']['defaultPrompt'][0]),128)
                for key in ('hooks','mcpServers','apps'):self.assertNotIn(key,package)
    def test_historical_draft_stays_inactive_and_current_source_matches_reviewed_guide(self):
        draft=ROOT/'drafts/korean-product-writing'
        self.assertTrue((draft/'SKILL.draft.md').is_file())
        self.assertEqual([],list(draft.rglob('SKILL.md')))
        self.assertFalse((draft/'agents').exists())
        self.assertIn('NOT PASSED',(draft/'STATUS.md').read_text())
        current=ROOT/'plugins/korean-product-writing/skills/korean-product-writing'
        for old,new in [('SKILL.draft.md','SKILL.md'),('references/examples.md','references/examples.md'),('references/sources.md','references/sources.md')]:
            self.assertEqual((draft/old).read_bytes(),(current/new).read_bytes())
        self.assertIn('regression-v4/results.md',(draft/'STATUS.md').read_text())
if __name__=='__main__':unittest.main()
