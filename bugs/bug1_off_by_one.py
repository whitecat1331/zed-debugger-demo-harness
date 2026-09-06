"""Bug 1: an off-by-one error.

`sum_first_n_evens(n)` should return the sum of the first `n` even
numbers: 0 + 2 + 4 + ... + 2*(n-1).

For n=5 the correct answer is 0+2+4+6+8 = 20.
"""


def sum_first_n_evens(n: int) -> int:
    total = 0
    for i in range(n):
        total += 2 * (i + 1)
    return total
