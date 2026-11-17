"""Behavioral checks for the public task contract."""

import unittest
from textkit.words import slugify

class ContractTests(unittest.TestCase):
    def test_compatibility_forms(self):
        for text, expected in [('Ｆｏｏ １２', 'foo-12'), ('oﬃce', 'office'), ('① Café', '1-cafe'), ('Kelvin', 'kelvin')]:
            with self.subTest(text=text):
                self.assertEqual(slugify(text), expected)

    def test_separator_and_empty_contract(self):
        for text, expected in [(' -- Déjà___Vu -- ', 'deja-vu'), ('한국어', ''), ('', ''), ('...42...', '42')]:
            with self.subTest(text=text):
                self.assertEqual(slugify(text), expected)
