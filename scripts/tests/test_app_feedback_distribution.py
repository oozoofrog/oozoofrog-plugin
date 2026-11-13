"""Check that the integration skill ships its usable library and matching host metadata."""
import json
from pathlib import Path
import unittest

from test_document_links import local_targets

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / 'plugins/app-feedback'
SKILL = PLUGIN / 'skills/app-feedback'


class AppFeedbackDistributionTests(unittest.TestCase):
    def test_metadata_and_documented_resources_ship_together(self):
        manifest = json.loads((PLUGIN / '.codex-plugin/plugin.json').read_text())
        document = (SKILL / 'SKILL.md').read_text()
        description = document.split('description: ', 1)[1].splitlines()[0]
        self.assertEqual(manifest['version'], '0.1.0')
        self.assertEqual(manifest['description'], description)
        self.assertEqual(manifest['interface']['longDescription'], description)
        for readme in ('README.md', 'README.ko.md'):
            self.assertIn(description, (ROOT / readme).read_text())
        metadata = {}
        for line in (SKILL / 'agents/openai.yaml').read_text().splitlines():
            if line.startswith('  '):
                key, value = line.strip().split(': ', 1)
                metadata[key] = json.loads(value)
        self.assertEqual(metadata['display_name'], manifest['interface']['displayName'])
        self.assertEqual(metadata['short_description'], manifest['interface']['shortDescription'])
        self.assertEqual([metadata['default_prompt']], manifest['interface']['defaultPrompt'])
        for document in SKILL.rglob('*.md'):
            for target in local_targets(document.read_text()):
                self.assertTrue((document.parent / target).exists(), target)
        self.assertTrue((SKILL / 'assets/AppFeedback/Package.swift').is_file())
        self.assertTrue((SKILL / 'assets/AppFeedback/Tests/AppFeedbackTests/FeedbackTests.swift').is_file())
        self.assertTrue((SKILL / 'scripts/feedback_diagnostics.swift').is_file())
        self.assertFalse((ROOT / 'Package.swift').exists())

    def test_example_is_extractable_without_private_configuration(self):
        text = (SKILL / 'references/integration.md').read_text()
        source = text.split('```swift\n', 1)[1].split('\n```', 1)[0]
        self.assertIn('feedback@example.com', source)
        self.assertIn('import AppFeedback', source)
        self.assertNotIn('PRIVATE KEY', source)


if __name__ == '__main__':
    unittest.main()
