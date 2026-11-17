"""Behavioral checks for the public task contract."""

import unittest
from textkit.config import merge_configs

class ContractTests(unittest.TestCase):
    def test_merge_precedence_and_order(self):
        texts = iter(['b=first\na=x=y#z\nb=last-in-layer', '# layer two\na=override\nB=upper\nempty=', 'b=final'])
        self.assertEqual(list(merge_configs(texts).items()), [('b', 'final'), ('a', 'override'), ('B', 'upper'), ('empty', '')])
        self.assertEqual(merge_configs(iter([])), {})
        self.assertEqual(merge_configs(['# only comments', '']), {})

    def test_line_number_is_local_to_bad_layer(self):
        with self.assertRaisesRegex(ValueError, 'line 3'):
            merge_configs(iter(['a=ok', '# comment\n\nbad']))
