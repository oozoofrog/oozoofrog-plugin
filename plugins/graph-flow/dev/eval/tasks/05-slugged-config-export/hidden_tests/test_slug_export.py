"""Behavioral checks for the public task contract."""

import unittest
from textkit.config import slug_config, parse_config

class ContractTests(unittest.TestCase):
    def test_export_is_ordered_and_lossless(self):
        values = {'Ｆｏｏ': 'x=y#literal', 'Café': '', 'oﬃce': 'desk'}
        before = dict(values)
        self.assertEqual(slug_config(values), 'foo=x=y#literal\ncafe=\noffice=desk')
        self.assertEqual(list(parse_config(slug_config(values)).items()), [('foo', 'x=y#literal'), ('cafe', ''), ('office', 'desk')])
        self.assertEqual(values, before)
        self.assertEqual(slug_config({}), '')

    def test_invalid_exports_raise(self):
        for values in ({'Café': 'x', 'Cafe': 'y'}, {'!!!': 'x'}, {'한국어': 'x'}, {'a': ' padded'}, {'a': 'x\u2028y'}):
            with self.subTest(values=values):
                with self.assertRaises(ValueError):
                    slug_config(values)
