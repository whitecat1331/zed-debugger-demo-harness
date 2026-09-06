"""Bug 4: mutating a list while iterating over it.

`filter_even(values)` should return a new list with only the even
numbers, preserving order.
"""


def filter_even(values):
    for value in values:
        if value % 2 != 0:
            values.remove(value)
    return values
