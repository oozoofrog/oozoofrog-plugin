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


def word_batches(texts, size):
    """Batch distinct words from texts in global first-seen order.

    Use words.word_counts_many's words, ignoring their counts, and chunked's
    size validation and partial-chunk rules. Accept a one-shot iterable of
    texts. An empty vocabulary returns [], but still validate size.
    """
    raise NotImplementedError
