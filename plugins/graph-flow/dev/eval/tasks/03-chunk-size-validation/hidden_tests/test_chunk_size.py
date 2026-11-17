"""Behavioral checks for the public task contract."""

import unittest
from textkit.sequences import chunked

class ContractTests(unittest.TestCase):
    def test_invalid_sizes_even_when_empty(self):
        for size in (True, False, 0, -4, 2.0, '2', None):
            for values in ([], [1, 2]):
                with self.subTest(size=size, values=values):
                    with self.assertRaises(ValueError):
                        chunked(iter(values), size)

    def test_valid_sizes_keep_references(self):
        first, second, third = [], {}, ['x']
        result = chunked(iter([first, second, third]), 2)
        self.assertEqual([len(part) for part in result], [2, 1])
        self.assertIs(result[0][0], first)
        self.assertIs(result[0][1], second)
        self.assertIs(result[1][0], third)
        self.assertEqual(chunked([], 3), [])
