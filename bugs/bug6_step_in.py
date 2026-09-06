"""Bug 6: a bug hidden inside a helper function (requires step_in).

`final_price(price, is_member)` should apply a discount: 20% off for
members, 10% off for non-members. The bug is inside `apply_discount`.
"""


def apply_discount(price: float, percent: float) -> float:
    return price * (1 + percent / 100)


def final_price(price: float, is_member: bool) -> float:
    percent = 20 if is_member else 10
    return apply_discount(price, percent)
