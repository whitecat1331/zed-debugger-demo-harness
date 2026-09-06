"""Bug 5: a crash caused by checking the wrong variable.

`safe_divide(numerator, denominator)` should return 0 when the
denominator is zero, otherwise numerator / denominator.
"""


def safe_divide(numerator, denominator):
    if numerator == 0:
        return 0
    return numerator / denominator
