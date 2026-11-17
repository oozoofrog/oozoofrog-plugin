"""Behavioral checks for the public task contract."""

import unittest
from textkit.config import parse_config, format_config
from textkit.words import config_word_counts
from textkit.sequences import config_batches

class ContractTests(unittest.TestCase):
    def test_opt_in_removes_only_one_initial_bom(self):
        self.assertEqual(parse_config('\ufeffa=x\ufeffy\nb=\ufeff', strip_bom=True), {'a': 'x\ufeffy', 'b': '\ufeff'})
        self.assertEqual(parse_config('\ufeff\ufeffa=1', strip_bom=True), {'\ufeffa': '1'})
        self.assertEqual(parse_config(' \ufeffa=1', strip_bom=True), {'\ufeffa': '1'})
        self.assertEqual(parse_config('a=1\n\ufeffb=2', strip_bom=True), {'a': '1', '\ufeffb': '2'})
        self.assertEqual(parse_config('\ufeff', strip_bom=True), {})

    def test_default_and_roundtrip_keep_literals(self):
        values = {'\ufeffa': 'x\ufeffy', 'b': ''}
        self.assertEqual(parse_config(format_config(values)), values)
        self.assertEqual(parse_config('\ufeffa=1', strip_bom=False), {'\ufeffa': '1'})
        self.assertEqual(parse_config('\ufeffa=1'), {'\ufeffa': '1'})

    def test_shared_consumers_keep_embedded_bom(self):
        text = '\ufeff# exported\na=ice\ufeffcream\nb=ice'
        self.assertEqual(list(config_word_counts(text).items()), [('ice', 2), ('cream', 1)])
        self.assertEqual(config_batches(text, 1), [[('a', 'ice\ufeffcream')], [('b', 'ice')]])
        self.assertEqual(config_batches('', 2), [])

    def test_original_line_numbers_and_chunk_validation(self):
        for parser in (lambda text: parse_config(text, strip_bom=True), config_word_counts, lambda text: config_batches(text, 2)):
            with self.assertRaisesRegex(ValueError, 'line 3'):
                parser('\ufeff# heading\n\nbad')
        with self.assertRaises(ValueError):
            config_batches('', True)
