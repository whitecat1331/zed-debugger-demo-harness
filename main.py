"""Runs every buggy function and prints the result.

Usage: python main.py

Each bug lives in bugs/. See README.md for hints on finding and
fixing each one using the debugger. Bug 9 (pause) hangs, so it is
debugged separately by running bugs/bug9_pause.py in a debug session.
"""

from bugs import (
    bug1_off_by_one,
    bug2_shadowing,
    bug3_condition,
    bug4_mutation,
    bug5_exception,
    bug6_step_in,
    bug7_step_out,
    bug8_run_to_line,
    bug10_final_boss,
)


def main():
    print("Bug 1 (off-by-one):")
    print("  sum_first_n_evens(5) =", bug1_off_by_one.sum_first_n_evens(5), "(expected 20)")
    print()

    print("Bug 2 (shadowing):")
    print("  format_report([10, 20, 30]) =", bug2_shadowing.format_report([10.0, 20.0, 30.0]))
    print()

    print("Bug 3 (condition):")
    print("  is_in_range(5, 0, 10) =", bug3_condition.is_in_range(5, 0, 10), "(expected True)")
    print("  is_in_range(50, 0, 10) =", bug3_condition.is_in_range(50, 0, 10), "(expected False)")
    print()

    print("Bug 4 (mutation):")
    print("  filter_even([1, 3, 2, 5, 4]) =", bug4_mutation.filter_even([1, 3, 2, 5, 4]), "(expected [2, 4])")
    print()

    print("Bug 5 (exception):")
    try:
        print("  safe_divide(10, 0) =", bug5_exception.safe_divide(10, 0))
    except Exception as exc:
        print("  safe_divide(10, 0) raised:", type(exc).__name__, exc)
    print()

    print("Bug 6 (step_in):")
    print("  final_price(100, True) =", bug6_step_in.final_price(100.0, True), "(expected 80.0)")
    print()

    print("Bug 7 (step_out):")
    print("  report([10, 20, 30]) =", bug7_step_out.report([10.0, 20.0, 30.0]), "(expected Average: 20.00)")
    print()

    print("Bug 8 (run_to_line):")
    print("  process([1, 2, 3]) =", bug8_run_to_line.process([1, 2, 3]), "(expected [2, 4, 6])")
    print()

    print("Bug 10 (final boss):")
    print("  max_product_subarray([2, 3, -2, 4]) =", bug10_final_boss.max_product_subarray([2, 3, -2, 4]), "(expected 6)")
    print("  max_product_subarray([-2, 3, -4]) =", bug10_final_boss.max_product_subarray([-2, 3, -4]), "(expected 24)")
    print()

    print("Bug 9 (pause): hangs - debug bugs/bug9_pause.py::find_divisor(9) separately.")


if __name__ == "__main__":
    main()
