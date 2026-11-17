"""Behavioral checks for the public task contract."""

import unittest
from textkit.words import word_counts

class ContractTests(unittest.TestCase):
    def test_underscore_boundaries_and_order(self):
        self.assertEqual(list(word_counts('RED_blue red__GREEN BLUE').items()), [('red', 2), ('blue', 2), ('green', 1)])
        self.assertEqual(word_counts('___'), {})

    def test_unicode_numbers_and_punctuation(self):
        self.assertEqual(list(word_counts("Été_été １２_１２ can't 한국어").items()), [('été', 2), ('１２', 2), ('can', 1), ('t', 1), ('한국어', 1)])
        self.assertEqual(word_counts(''), {})
