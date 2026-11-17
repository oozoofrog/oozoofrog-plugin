"""Order-preserving sequence operations, including unhashable values."""


def unique(items):
    """Return a new list retaining the first of each equal item, in order.

    Accept any finite iterable, use equality rather than hashing, and never
    mutate input items. Returned items are the original objects, not copies.
    """
    result = []
    for item in items:
        if item not in result:
            result.append(item)
    return result


def chunked(items, size):
    """Return lists of at most size items from a finite iterable, in order.

    Retain a final partial chunk; empty input returns []. Raise ValueError
    unless size is a positive int (bool is rejected). Do not copy item objects.
    """
    if type(size) is not int or size <= 0:
        raise ValueError('size must be a positive integer')
    result = []
    for item in items:
        if not result or len(result[-1]) == size:
            result.append([])
        result[-1].append(item)
    return result


def config_batches(text, size):
    """Chunk parsed (key, value) pairs with leading-BOM support enabled.

    Preserve mapping order and literal entries. Use chunked's size checks
    and partial chunks; propagate parser errors.
    """
    from textkit.config import parse_config

    return chunked(parse_config(text, strip_bom=True).items(), size)
