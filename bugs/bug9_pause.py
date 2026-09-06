"""Bug 9: an infinite loop (requires pause).

`find_divisor(n)` should return the smallest divisor > 1 of n, or None
if prime. The loop never advances, so it hangs forever. Run it, then use
`pause` to see where it is stuck.
"""


def find_divisor(n):
    i = 2
    while i < n:
        if n % i == 0:
            return i
    return None

if __name__ == "__main__":
    print(find_divisor(9))
