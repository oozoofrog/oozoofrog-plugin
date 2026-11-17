"""Word normalization helpers without locale or external state."""

import re
import unicodedata


def slugify(text):
    """NFKD-fold to ASCII lowercase; join runs of a-z/0-9 with hyphens.

    Discard non-ASCII characters after normalization and return '' if no
    letters or digits remain. Leading/trailing separators are removed.
    """
    ascii_text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]+', '-', ascii_text.lower()).strip('-')


def word_counts(text):
    """Count lowercase Unicode alphanumeric runs, excluding underscores.

    Punctuation (including apostrophes) separates words; preserve the order
    in which distinct lowercase words first appear in the returned dict.
    """
    counts = {}
    for word in re.findall(r'[^\W_]+', text.lower()):
        counts[word] = counts.get(word, 0) + 1
    return counts


def config_word_counts(text):
    """Count words in parsed config values with leading-BOM support enabled.

    Join values with spaces in mapping order, then use word_counts rules.
    Keep embedded literal characters and propagate parser errors.
    """
    from textkit.config import parse_config

    return word_counts(' '.join(parse_config(text, strip_bom=True).values()))
