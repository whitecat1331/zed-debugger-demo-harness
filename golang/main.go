// Go adapter feature test (Delve).
//
// Run normally to see three wrong results; run with `--hang` to exercise the
// `pause` control on an infinite loop. Every defect maps to a debugger
// capability described in the repository README.
package main

import (
	"fmt"
	"os"
)

// applyDiscount returns price after a percent discount.
//
// BUG: the sign is backwards — it adds the discount instead of subtracting it.
// Exercise step_in/step_out: breakpoint on the call in main, step_in, snapshot
// price/percent, then step_out.
func applyDiscount(price float64, percent float64) float64 {
	return price * (1 + percent/100)
}

// sumEven returns the sum of the first n even numbers (0 + 2 + ... + 2*(n-1)).
//
// BUG: off-by-one — the loop runs one iteration too many. Exercise
// breakpoint + snapshot on the `total` update line.
func sumEven(n int) int {
	total := 0
	for i := 0; i <= n; i++ {
		total += 2 * i
	}
	return total
}

// process doubles each input value.
//
// BUG (run_to_line target): the line `result[len(result)-1] += 1000` corrupts
// the last element. Use run_to_line straight to it (no breakpoint) and snapshot.
func process(values []int) []int {
	result := make([]int, len(values))
	for i, v := range values {
		result[i] = v * 2
	}
	result[len(result)-1] += 1000
	return result
}

// findDivisor hangs because the loop counter never advances.
//
// BUG: missing `i++`. Run with `--hang`, then use the `pause` control.
func findDivisor(n int) int {
	i := 2
	for i < n {
		if n%i == 0 {
			return i
		}
		// BUG: missing i++
	}
	return -1
}

func main() {
	if len(os.Args) > 1 && os.Args[1] == "--hang" {
		fmt.Println("hanging... (use the debugger 'pause')")
		findDivisor(9)
		return
	}

	fmt.Println("applyDiscount(100, 20) =", applyDiscount(100, 20), "(expected 80)")
	fmt.Println("sumEven(5) =", sumEven(5), "(expected 20)")
	fmt.Println("process([1 2 3]) =", process([]int{1, 2, 3}), "(expected [2 4 6])")
}
