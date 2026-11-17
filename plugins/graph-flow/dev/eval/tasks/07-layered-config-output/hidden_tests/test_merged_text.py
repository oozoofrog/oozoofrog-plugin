"""Behavioral checks for the public task contract."""

import unittest
from textkit.config import merged_config, parse_config

class ContractTests(unittest.TestCase):
    def test_export_and_roundtrip(self):
        self.assertEqual(merged_config(iter(['b=x=y#z\na=old', 'a=\nB=UP'])), 'b=x=y#z\na=\nB=UP')
        self.assertEqual(parse_config(merged_config(['a=1', 'a=2\nb=3'])), {'a': '2', 'b': '3'})
        self.assertEqual(merged_config(iter([])), '')

    def test_errors_propagate(self):
        with self.assertRaisesRegex(ValueError, 'line 2'):
            merged_config(['a=ok', '# comment\n=bad'])
