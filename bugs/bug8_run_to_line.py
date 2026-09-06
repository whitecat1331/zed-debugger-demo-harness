"""Bug 8: a bug on a specific line (requires run_to_line).

`process(values)` should double each value. A later line corrupts the
result. Use run_to_line to jump straight to the corrupting line.
"""


def process(values):
    result = []
    for value in values:
        doubled = value * 2
        result.append(doubled)
        result[-1] += 1000
    return result
