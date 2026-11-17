"""Behavioral checks for the public task contract."""

import unittest
from textkit.sequences import chunked

class ContractTests(unittest.TestCase):
    def test_partial_chunks_and_identity(self):
        last = []
        result = chunked(iter([1, 2, last]), 2)
        self.assertEqual(result, [[1, 2], [last]])
        self.assertIs(result[-1][0], last)
        self.assertEqual(chunked([1], 5), [[1]])
        self.assertEqual(chunked([], 3), [])
        self.assertEqual(chunked(range(4), 2), [[0, 1], [2, 3]])
