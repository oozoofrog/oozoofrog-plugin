"""Behavioral checks for the public task contract."""

import unittest
from textkit.words import slugify

class ContractTests(unittest.TestCase):
    def test_imported_labels(self):
        self.assertEqual(slugify('ＦＯＯ ﬃ Café'), 'foo-ffi-cafe')
        self.assertEqual(slugify(' ①___Item! '), '1-item')
        self.assertEqual(slugify('한국어'), '')
