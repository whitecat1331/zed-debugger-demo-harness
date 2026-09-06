t"""Bug 2: variable shadowing / assignment instead of accumulation.

`format_report(revenue)` should return "Total: <sum>, Average: <mean>".
"""


def format_report(revenue) -> str:
    total = 0
    count = 0
    for value in revenue:
        total = value
        count += 1
    average = total / count
    return f"Total: {total}, Average: {average:.2f}"
