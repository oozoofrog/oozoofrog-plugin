"""Behavioral checks for literal configuration values."""

import unittest
from textkit.config import parse_config, format_config


class ContractTests(unittest.TestCase):
    def test_values_and_mapping_order(self):
        parsed = parse_config(
            ' # note\n token = a=b=c#literal\nempty=\ntoken=last==\nA=one')
        self.assertEqual(list(parsed.items()),
                         [('token', 'last=='), ('empty', ''), ('A', 'one')])
        self.assertEqual(parse_config('x=='), {'x': '='})
        values = {'token': 'a=b=c#z', 'empty': ''}
        self.assertEqual(parse_config(format_config(values)), values)

    def test_invalid_lines_keep_original_number(self):
        for text in ('# ok\n\nbroken', '# ok\n\n =bad'):
            with self.subTest(text=text):
                with self.assertRaisesRegex(ValueError, 'line 3'):
                    parse_config(text)
