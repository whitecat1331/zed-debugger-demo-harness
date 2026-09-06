// C adapter feature test (GDB).
//
// Compile with debug symbols before launching, e.g.:
//   gcc -g -O0 main.c -o main      (or `cl /Zi main.c` on MSVC)
// Run normally to see three wrong results; run with `--hang` to exercise the
// `pause` control on an infinite loop.
//
// This file exists specifically to exercise the GDB adapter (the C++ test
// defaults to CodeLLDB). Launch it with `adapter: "GDB"`.

#include <stddef.h>
#include <stdio.h>
#include <string.h>

// apply_discount returns price after a percent discount.
//
// BUG: the sign is backwards — it adds the discount instead of subtracting it.
// Exercise step_in/step_out: breakpoint on the call in main, step_in, snapshot
// price/percent, then step_out.
double apply_discount(double price, double percent) {
    return price * (1 + percent / 100);
}

// sum_even returns the sum of the first n even numbers (0 + 2 + ... + 2*(n-1)).
//
// BUG: off-by-one — `<=` runs one iteration too many. Exercise
// breakpoint + snapshot on the `total +=` line.
int sum_even(int n) {
    int total = 0;
    for (int i = 0; i <= n; ++i) {
        total += 2 * i;
    }
    return total;
}

// process doubles each input value into `out`.
//
// BUG (run_to_line target): the line `out[n - 1] += 1000` corrupts the last
// element. Use run_to_line straight to it (no breakpoint).
void process(const int* values, int* out, size_t n) {
    for (size_t i = 0; i < n; ++i) {
        out[i] = values[i] * 2;
    }
    out[n - 1] += 1000;
}

// find_divisor hangs because the loop counter never advances.
//
// BUG: missing `++i`. Run with `--hang`, then use the `pause` control.
int find_divisor(int n) {
    int i = 2;
    while (i < n) {
        if (n % i == 0) {
            return i;
        }
        // BUG: missing ++i
    }
    return -1;
}

int main(int argc, char** argv) {
    if (argc > 1 && strcmp(argv[1], "--hang") == 0) {
        printf("hanging... (use the debugger 'pause')\n");
        find_divisor(9);
        return 0;
    }

    printf("apply_discount(100, 20) = %.0f (expected 80)\n", apply_discount(100, 20));
    printf("sum_even(5) = %d (expected 20)\n", sum_even(5));

    int values[3] = {1, 2, 3};
    int result[3] = {0, 0, 0};
    process(values, result, 3);
    printf("process([1,2,3]) = [%d, %d, %d] (expected [2, 4, 6])\n",
           result[0], result[1], result[2]);
    return 0;
}
