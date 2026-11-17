"""A deliberately small key=value configuration format."""


def parse_config(text):
    """Parse stripped key=value lines into a dict; later duplicate keys win.

    Skip blank lines and lines whose first nonspace character is '#'. Split
    only at the first '='; values may be empty and '#' within values is literal.
    Raise ValueError with a 1-based line number for missing '=' or empty keys.
    Keys are case-sensitive and quotes/escapes have no special meaning.
    """
    result = {}
    for number, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        key, separator, value = line.partition('=')
        if not separator or not key.strip():
            raise ValueError('invalid config at line %d' % number)
        result[key.strip()] = value.strip()
    return result


def format_config(values):
    """Join string key/value pairs in mapping order as key=value lines.

    No trailing newline is added. Raise ValueError for empty or untrimmed
    keys, keys containing '=' or starting '#', untrimmed values, or any line
    boundary in keys/values, so parse_config can round-trip the result.
    """
    lines = []
    for key, value in values.items():
        if (not key or key != key.strip() or '=' in key or key.startswith('#')
                or value != value.strip() or len(key.splitlines()) != 1
                or (value and len(value.splitlines()) != 1)
                or any(c in key + value for c in '\r\n\v\f\x1c\x1d\x1e\x85\u2028\u2029')):
            raise ValueError('unrepresentable config entry')
        lines.append(key + '=' + value)
    return '\n'.join(lines)


def merge_configs(texts):
    """Merge a finite iterable of configuration texts into a new dict.

    Parse each text with parse_config; later values win both within and
    across texts, while keys keep their first insertion order. Keys remain
    case-sensitive. Accept a one-shot iterable. Empty input returns {}.
    Malformed text raises parse_config's ValueError with a line number local
    to that text, including its blank and comment lines.
    """
    raise NotImplementedError


def merged_config(texts):
    """Return format_config text for merge_configs(texts), without a newline.

    Keep merged key order and literal values, including '=' and '#'. Empty
    input yields ''. Propagate parsing and representability ValueErrors.
    """
    raise NotImplementedError
