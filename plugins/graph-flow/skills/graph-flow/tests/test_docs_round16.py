"""Role-sized guidance and links remain usable after the contract split."""
from pathlib import Path
import re
import unittest
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT.parents[1]


class ReaderDocsTests(unittest.TestCase):
    def test_role_entrypoints_and_identity_rule_have_one_home(self):
        skill = (ROOT / 'SKILL.md').read_text()
        worker = (ROOT / 'references/worker.md').read_text()
        self.assertLessEqual(len(skill.encode()), 4000)
        rule = next(p for p in skill.split('\n\n') if p.startswith('Never set or change'))
        self.assertEqual(worker.count(rule), 1)
        self.assertIn('.graph-flow/runs/**', rule)
        for file in (ROOT / 'references').glob('*.md'):
            if file.name != 'worker.md':
                self.assertNotIn('Never set or change', file.read_text())
        for name in ('SKILL.md', 'references/leader.md', 'references/worker.md'):
            self.assertNotRegex((ROOT/name).read_text(), r'0\.[23](?:\.x)?')
        splitter = (PLUGIN / 'agents/gf-splitter.md').read_text()
        self.assertIn('references/plan.md', splitter)
        self.assertIn('principles.md', splitter)
        self.assertNotIn('records.md', splitter)
        self.assertNotIn('docs/implementation', splitter)
        records = (ROOT / 'references/records.md').read_text()
        self.assertNotIn('## 11. Modules', records)
        self.assertNotIn('## 12. Dashboard presentation view', records)
        developer = (PLUGIN / 'docs/implementation.md').read_text()
        self.assertIn('## 11. Modules', developer)
        self.assertIn('## 12. Dashboard presentation view', developer)
        section11 = (ROOT / 'references/leader.md').read_text().split('## 11.', 1)[1]
        for misplaced in ('A check title', 'Gate scope checks', 'key repin', 'max_attempts'):
            self.assertNotIn(misplaced, section11)
        principles = (ROOT / 'references/principles.md').read_text()
        self.assertIn('deliberate, user-mandated addition', principles)
        self.assertIn('machinery is frozen', principles)
        self.assertIn('must name the principle it serves', principles)

    def test_all_local_document_links_and_anchors_resolve(self):
        documents = [ROOT/'SKILL.md', *(ROOT/'references').glob('*.md'),
                     *(PLUGIN/'agents').glob('*.md'), *(PLUGIN/'docs').glob('*.md')]
        def prose(text):
            return re.sub(r'^```[^\n]*\n.*?^```\s*$', '', text, flags=re.M | re.S)
        def anchors(text):
            titles = re.findall(r'^#{1,6}\s+(.+)', prose(text), re.M)
            return {re.sub(r'[^\w\- ]', '', title.lower()).replace(' ', '-') for title in titles}
        for document in documents:
            text = prose(document.read_text())
            for target in re.findall(r'\[[^\]\n]*\]\(([^\s)]+)\)', text):
                url = urlsplit(target)
                if url.scheme or url.netloc:
                    continue
                path = (document.parent / unquote(url.path)).resolve() if url.path else document
                with self.subTest(document=document.name, target=target):
                    self.assertTrue(path.is_file(), str(path))
                    if url.fragment:
                        self.assertIn(unquote(url.fragment), anchors(path.read_text()))
