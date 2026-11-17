"""Behavioral checks for the public task contract."""

import unittest
from textkit.words import slugify

class ContractTests(unittest.TestCase):
    def test_edge_separators(self):
        for text, expected in [('...Hello___World!!!', 'hello-world'), ('---42', '42'), ('foo---', 'foo'), ('!!!', ''), ('', '')]:
            with self.subTest(text=text):
                self.assertEqual(slugify(text), expected)
