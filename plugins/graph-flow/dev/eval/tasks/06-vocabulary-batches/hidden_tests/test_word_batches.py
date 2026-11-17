"""Behavioral checks for the public task contract."""

import unittest
from textkit.sequences import word_batches

class ContractTests(unittest.TestCase):
    def test_vocabulary_batches(self):
        self.assertEqual(word_batches(iter(['red blue red', 'green_blue', '한국어 42']), 2), [['red', 'blue'], ['green', '한국어'], ['42']])
        self.assertEqual(word_batches(['a a', 'a'], 1), [['a']])
        self.assertEqual(word_batches(iter([]), 4), [])

    def test_invalid_sizes(self):
        for size in (True, 0, -1, 1.5, '2'):
            with self.subTest(size=size):
                with self.assertRaises(ValueError):
                    word_batches(iter([]), size)
