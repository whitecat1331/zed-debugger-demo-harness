"""Bug 7: a wrong return value (requires step_out).

`report(scores)` should print the average.
"""


def compute_average(values):
    total = sum(values)
    count = len(values) - 1
    return total / count


def report(scores):
    return f"Average: {compute_average(scores):.2f}"
