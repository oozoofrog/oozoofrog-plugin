"""Boundary examples for the public helpers; no filesystem or network I/O."""

import unittest

from textkit.config import format_config, parse_config
from textkit.sequences import chunked, unique
from textkit.words import slugify, word_counts


class TextkitTests(unittest.TestCase):
    """Each case exercises one documented behavior."""

    def test_slug_separators(self):
        """Punctuation runs collapse and edge separators disappear."""
        self.assertEqual(slugify('  Hello___WORLD! 42 '), 'hello-world-42')

    def test_slug_accents(self):
        """Compatibility decomposition preserves ASCII accent bases."""
        self.assertEqual(slugify('Café déjà vu'), 'cafe-deja-vu')

    def test_slug_empty(self):
        """Inputs without ASCII letters or digits yield empty slugs."""
        for text in ('', '!!!', '한국어'):
            self.assertEqual(slugify(text), '')

    def test_counts_case(self):
        """Counts combine lowercase equivalents in first-seen order."""
        counts = word_counts('Two ONE two')
        self.assertEqual(list(counts.items()), [('two', 2), ('one', 1)])

    def test_counts_unicode(self):
        """Unicode letters and digits count, punctuation separates."""
        self.assertEqual(word_counts("Été_été can't 42"),
                         {'été': 2, 'can': 1, 't': 1, '42': 1})

    def test_counts_empty(self):
        """Only punctuation produces no words."""
        self.assertEqual(word_counts(' --_ '), {})

    def test_config_comments(self):
        """Blank lines and whole-line comments are ignored."""
        self.assertEqual(parse_config('\n # comment\n a = b \n'), {'a': 'b'})

    def test_config_values(self):
        """Equals and inline hashes remain literal value content."""
        self.assertEqual(parse_config('x=a=b#c\nempty='), {'x': 'a=b#c', 'empty': ''})

    def test_config_duplicates(self):
        """Duplicate keys overwrite values without changing order or case."""
        self.assertEqual(list(parse_config('a=1\nA=2\na=3').items()),
                         [('a', '3'), ('A', '2')])

    def test_config_invalid(self):
        """Malformed entries report the original line number."""
        for text in ('# comment\nbad', '\n =value'):
            with self.assertRaisesRegex(ValueError, 'line 2'):
                parse_config(text)

    def test_format_roundtrip(self):
        """Formatting preserves mapping order and parseable string values."""
        values = {'b': 'x=y#z', 'a': ''}
        self.assertEqual(format_config(values), 'b=x=y#z\na=')
        self.assertEqual(parse_config(format_config(values)), values)
        self.assertEqual(format_config({}), '')

    def test_format_invalid(self):
        """Unrepresentable keys, values, and line separators are rejected."""
        for key, value in [('', 'x'), (' a', 'x'), ('#a', 'x'), ('a=b', 'x'),
                           ('a', ' x'), ('a', 'x\n'), ('a', 'x\u2028y')]:
            with self.assertRaises(ValueError):
                format_config({key: value})

    def test_unique_order(self):
        """Deduplication accepts generators and keeps first-seen order."""
        self.assertEqual(unique(x for x in [3, 1, 3, 2, 1]), [3, 1, 2])
        self.assertEqual(unique([]), [])

    def test_unique_unhashable(self):
        """Unhashable values work and original objects remain untouched."""
        first = [1]
        values = [first, [1], [2]]
        result = unique(values)
        self.assertEqual(result, [[1], [2]])
        self.assertIs(result[0], first)
        self.assertEqual(values, [[1], [1], [2]])

    def test_chunks_partial(self):
        """Chunking preserves order and the final incomplete group."""
        self.assertEqual(chunked(iter(range(5)), 2), [[0, 1], [2, 3], [4]])
        self.assertEqual(chunked([], 2), [])
        self.assertEqual(chunked([1, 2], 2), [[1, 2]])

    def test_chunks_invalid(self):
        """Invalid sizes fail even for empty inputs."""
        for size in (0, -1, True, 1.5, '2'):
            with self.assertRaises(ValueError):
                chunked([], size)
