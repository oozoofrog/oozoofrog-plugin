"""Behavioral checks for the public task contract."""

import unittest
from textkit.sequences import unique
from textkit.words import slug_catalog
from textkit.config import value_catalog

class ContractTests(unittest.TestCase):
    def test_unhashable_projected_values_keep_first_objects(self):
        first = {'labels': ['red'], 'id': 1}
        repeated = {'labels': ['red'], 'id': 2}
        other = {'labels': ['blue'], 'id': 3}
        source = [first, repeated, other]
        result = unique(iter(source), key=lambda row: row['labels'])
        self.assertEqual(result, [first, other])
        self.assertIs(result[0], first)
        self.assertIs(result[1], other)
        self.assertEqual(source, [first, repeated, other])
        self.assertEqual(unique([{'a': 1}, {'a': 1}, {'a': 2}], key=lambda row: row), [{'a': 1}, {'a': 2}])

    def test_equal_keys_and_default_behavior(self):
        first = ['a']
        self.assertIs(unique([first, ['a']], key=None)[0], first)
        self.assertEqual(unique([('first', 1), ('second', True), ('third', 2)], key=lambda pair: pair[1]), [('first', 1), ('third', 2)])
        self.assertEqual(unique(iter([]), key=lambda value: [value]), [])

    def test_title_catalog(self):
        titles = ['Café', 'CAFE!', 'Ｆｏｏ', 'foo', '!!!', '한국어']
        self.assertEqual(slug_catalog(iter(titles)), ['Café', 'Ｆｏｏ', '!!!'])
        self.assertEqual(titles, ['Café', 'CAFE!', 'Ｆｏｏ', 'foo', '!!!', '한국어'])

    def test_value_catalog(self):
        self.assertEqual(value_catalog('a=old\nb=x=y#z\na=x=y#z\nc=\nd='), [('a', 'x=y#z'), ('c', '')])
        self.assertEqual(value_catalog(''), [])
