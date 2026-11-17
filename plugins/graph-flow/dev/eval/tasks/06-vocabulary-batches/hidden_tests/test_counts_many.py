"""Behavioral checks for the public task contract."""

import unittest
from textkit.words import word_counts_many

class ContractTests(unittest.TestCase):
    def test_totals_and_first_seen_order(self):
        texts = iter(['Été_blue BLUE', '', "blue été Can't", 'new_42 new'])
        self.assertEqual(list(word_counts_many(texts).items()), [('été', 2), ('blue', 3), ('can', 1), ('t', 1), ('new', 2), ('42', 1)])
        self.assertEqual(word_counts_many(iter([])), {})
        self.assertEqual(word_counts_many(['_', '!!!']), {})
