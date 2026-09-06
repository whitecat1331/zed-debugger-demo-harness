"""Bug 3: logic error in a condition.

`is_in_range(value, low, high)` should return True only when
low <= value <= high (inclusive).
"""


def is_in_range(value: int, low: int, high: int) -> bool:
    return value >= low or value <= high
