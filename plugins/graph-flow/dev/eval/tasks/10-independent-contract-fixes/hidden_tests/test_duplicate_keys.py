"""Behavioral checks for the public task contract."""

import unittest
from textkit.config import parse_config

class ContractTests(unittest.TestCase):
    def test_later_values_keep_key_positions(self):
        self.assertEqual(list(parse_config('a=first\nB=upper\nb=lower\na=last==#x\nb=').items()), [('a', 'last==#x'), ('B', 'upper'), ('b', '')])
        self.assertEqual(parse_config(' x = old \nx=new'), {'x': 'new'})
