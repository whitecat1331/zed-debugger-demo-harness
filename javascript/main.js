// JavaScript adapter feature test (vscode-js-debug / pwa-node).
//
// Run normally to see three wrong results; run with `--hang` to exercise the
// `pause` control on an infinite loop.
"use strict";

// applyDiscount returns price after a percent discount.
//
// BUG: the sign is backwards — it adds the discount instead of subtracting it.
// Exercise step_in/step_out: breakpoint on the call in main, step_in, snapshot
// price/percent, then step_out.
function applyDiscount(price, percent) {
  return price * (1 + percent / 100);
}

// sumEven returns the sum of the first n even numbers (0 + 2 + ... + 2*(n-1)).
//
// BUG: off-by-one — the loop runs one iteration too many. Exercise
// breakpoint + snapshot on the `total +=` line.
function sumEven(n) {
  let total = 0;
  for (let i = 0; i <= n; i++) {
    total += 2 * i;
  }
  return total;
}

// processValues doubles each input value.
//
// BUG (run_to_line target): the line `result[result.length - 1] += 1000`
// corrupts the last element. Use run_to_line straight to it (no breakpoint).
//
// Named `processValues` (not `process`) to avoid shadowing Node's global
// `process` object.
function processValues(values) {
  const result = values.map((v) => v * 2);
  result[result.length - 1] += 1000;
  return result;
}

// findDivisor hangs because the loop counter never advances.
//
// BUG: missing `i++`. Run with `--hang`, then use the `pause` control.
function findDivisor(n) {
  let i = 2;
  while (i < n) {
    if (n % i === 0) return i;
    // BUG: missing i++
  }
  return -1;
}

if (process.argv.includes("--hang")) {
  console.log("hanging... (use the debugger 'pause')");
  findDivisor(9);
} else {
  console.log("applyDiscount(100, 20) =", applyDiscount(100, 20), "(expected 80)");
  console.log("sumEven(5) =", sumEven(5), "(expected 20)");
  console.log("processValues([1,2,3]) =", processValues([1, 2, 3]), "(expected [2,4,6])");
}
