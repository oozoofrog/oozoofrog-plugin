"""Order-preserving sequence operations, including unhashable values."""


def unique(items, key=None):
    """Return a new list retaining the first of each equal item, in order.

    Accept any finite iterable, use equality rather than hashing, and never
    mutate input items.
    Returned items are the original objects, not copies. With optional
    key=None, compare items as before; otherwise compare key(item) values by
    equality. Projected keys may be unhashable. Keep the first original item
    for each equal key, even when equal keys have different types.
    """
    result = []
    seen = []
    for item in items:
        marker = item if key is None else key(item)
        if marker not in seen:
            seen.append(marker)
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
